import copy
import tempfile
import unittest
from pathlib import Path

from cloud.message_router import DIRECTORY_KEY, route_key
from message_cloud import (
    FAMILY_DIRECTORY_FORMAT,
    MessageValidationError,
    cloud_message_from_local,
    local_message_from_cloud,
    new_learning_summary,
    new_receipt,
)
from message_store import (
    create_message,
    inbox_dir,
    load_message,
    open_message,
    outbox_dir,
    save_message_copy,
)
from message_sync import refresh_local_learning_summary, sync_station, write_local_learning_summary


class MemoryObjectStore:
    def __init__(self):
        self.objects = {}

    def put_json(self, key, value):
        self.objects[str(key)] = copy.deepcopy(value)

    def get_json(self, key, default=...):
        if key not in self.objects:
            if default is not ...:
                return default
            raise KeyError(key)
        return copy.deepcopy(self.objects[key])

    def list_keys(self, prefix):
        return sorted(key for key in self.objects if key.startswith(prefix))


class CloudMessageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = MemoryObjectStore()
        self.directory = {
            "format": FAMILY_DIRECTORY_FORMAT,
            "students": {
                "pappy": {"station_ids": ["pappy-test-station"]},
                "astrid": {"station_ids": ["pappy-test-station", "astrid-liara-station"]},
                "liara": {"station_ids": ["pappy-test-station", "astrid-liara-station"]},
                "campbell": {"station_ids": ["pappy-test-station", "campbell-olivea-station"]},
                "olivea": {"station_ids": ["pappy-test-station", "campbell-olivea-station"]},
            },
        }
        self.store.put_json(DIRECTORY_KEY, self.directory)
        self.active = list("ETANIMSO")

    def tearDown(self):
        self.temp_dir.cleanup()

    def publish_snapshot(self, student_id, station_id, active=None, generated_at=None):
        summary = new_learning_summary(
            student_id,
            station_id,
            active or self.active,
            generated_at=generated_at,
        )
        key = f"stations/{station_id}/snapshots/students/{student_id}.json"
        self.store.put_json(key, summary)
        route_key(self.store, key)
        return summary

    def publish_family_summaries(self):
        self.publish_snapshot("pappy", "pappy-test-station")
        self.publish_snapshot("astrid", "pappy-test-station")
        self.publish_snapshot("astrid", "astrid-liara-station")

    def cloud_message(self, text="ME"):
        local = create_message(
            "pappy",
            "astrid",
            "pappy-test-station",
            text,
            self.active,
        )
        return local, cloud_message_from_local(local)

    def test_router_replay_creates_one_inbox_copy_per_approved_station(self):
        self.publish_family_summaries()
        _, payload = self.cloud_message()
        key = f"stations/pappy-test-station/messages/outbox/{payload['message_id']}.json"
        self.store.put_json(key, payload)

        for _ in range(10):
            route_key(self.store, key)

        inbox_keys = [
            item
            for item in self.store.objects
            if f"/messages/inbox/astrid/{payload['message_id']}.json" in item
        ]
        self.assertEqual(2, len(inbox_keys))
        self.assertEqual(
            {
                f"stations/pappy-test-station/messages/inbox/astrid/{payload['message_id']}.json",
                f"stations/astrid-liara-station/messages/inbox/astrid/{payload['message_id']}.json",
            },
            set(inbox_keys),
        )
        status_key = (
            f"stations/pappy-test-station/messages/status/sent/"
            f"{payload['message_id']}/available.json"
        )
        self.assertIn(status_key, self.store.objects)

    def test_router_rejects_path_tampering_required_letters_and_unavailable_letter(self):
        self.publish_family_summaries()
        _, payload = self.cloud_message()
        wrong_path = f"stations/astrid-liara-station/messages/outbox/{payload['message_id']}.json"
        self.store.put_json(wrong_path, payload)
        with self.assertRaisesRegex(MessageValidationError, "station"):
            route_key(self.store, wrong_path)

        altered = dict(payload)
        altered["required_letters"] = ["M"]
        altered_key = f"stations/pappy-test-station/messages/outbox/{payload['message_id']}.json"
        self.store.put_json(altered_key, altered)
        with self.assertRaisesRegex(MessageValidationError, "required letters"):
            route_key(self.store, altered_key)

        _, unavailable = self.cloud_message("ME")
        unavailable["text"] = "MORE"
        unavailable["required_letters"] = ["E", "M", "O", "R"]
        unavailable_key = f"stations/pappy-test-station/messages/outbox/{unavailable['message_id']}.json"
        self.store.put_json(unavailable_key, unavailable)
        with self.assertRaisesRegex(MessageValidationError, "unavailable"):
            route_key(self.store, unavailable_key)

    def test_stale_snapshot_is_rejected(self):
        key = "stations/pappy-test-station/snapshots/students/pappy.json"
        self.store.put_json(
            key,
            new_learning_summary(
                "pappy",
                "pappy-test-station",
                self.active,
                generated_at="2000-01-01T00:00:00+00:00",
            ),
        )
        with self.assertRaisesRegex(MessageValidationError, "stale"):
            route_key(self.store, key)

    def test_opened_and_decoded_receipts_move_forward_without_duplicates(self):
        self.publish_family_summaries()
        _, payload = self.cloud_message()
        outbox_key = f"stations/pappy-test-station/messages/outbox/{payload['message_id']}.json"
        self.store.put_json(outbox_key, payload)
        route_key(self.store, outbox_key)
        local = local_message_from_cloud(payload)
        opened = open_message(local)
        receipt = new_receipt(opened, "opened", "pappy-test-station", opened["opened_at"])
        receipt_key = (
            f"stations/pappy-test-station/messages/receipts/outgoing/astrid/"
            f"{payload['message_id']}/opened.json"
        )
        self.store.put_json(receipt_key, receipt)

        for _ in range(10):
            route_key(self.store, receipt_key)

        received = [
            key
            for key in self.store.objects
            if f"/messages/status/received/astrid/{payload['message_id']}/opened.json" in key
        ]
        self.assertEqual(2, len(received))
        sender_status = (
            f"stations/pappy-test-station/messages/status/sent/"
            f"{payload['message_id']}/opened.json"
        )
        self.assertIn(sender_status, self.store.objects)

    def test_station_workers_rehearse_offline_delivery_and_receipt(self):
        self.publish_family_summaries()
        pappy_data = self.root / "pappy"
        astrid_data = self.root / "astrid"
        pappy_config = {
            "station_id": "pappy-test-station",
            "students": [{"id": "pappy"}, {"id": "astrid"}],
            "family_students": [{"id": "pappy"}, {"id": "astrid"}],
        }
        astrid_config = {
            "station_id": "astrid-liara-station",
            "students": [{"id": "astrid"}],
            "family_students": [{"id": "pappy"}, {"id": "astrid"}],
        }
        write_local_learning_summary(pappy_data, "pappy", "pappy-test-station", self.active)
        write_local_learning_summary(pappy_data, "astrid", "pappy-test-station", self.active)
        write_local_learning_summary(astrid_data, "astrid", "astrid-liara-station", self.active)
        local, payload = self.cloud_message()
        local["cloud_state"] = "queued"
        save_message_copy(outbox_dir(pappy_data, "pappy"), local)

        sync_station(pappy_data, pappy_config, self.store)
        outbox_key = f"stations/pappy-test-station/messages/outbox/{payload['message_id']}.json"
        route_key(self.store, outbox_key)
        result = sync_station(astrid_data, astrid_config, self.store)
        self.assertEqual(1, result["messages_downloaded"])

        downloaded = load_message(inbox_dir(astrid_data, "astrid"), payload["message_id"])
        opened = open_message(downloaded)
        save_message_copy(inbox_dir(astrid_data, "astrid"), opened)
        sync_station(astrid_data, astrid_config, self.store)
        receipt_key = (
            f"stations/astrid-liara-station/messages/receipts/outgoing/astrid/"
            f"{payload['message_id']}/opened.json"
        )
        route_key(self.store, receipt_key)
        sync_station(pappy_data, pappy_config, self.store)

        sender_copy = load_message(outbox_dir(pappy_data, "pappy"), payload["message_id"])
        self.assertEqual("opened", sender_copy["state"])
        self.assertEqual("opened", sender_copy["cloud_state"])

    def test_learning_snapshot_is_not_rewritten_when_current(self):
        first = write_local_learning_summary(
            self.root,
            "pappy",
            "pappy-test-station",
            self.active,
        )
        second = refresh_local_learning_summary(
            self.root,
            "pappy",
            "pappy-test-station",
            self.active,
        )
        changed = refresh_local_learning_summary(
            self.root,
            "pappy",
            "pappy-test-station",
            self.active + ["R"],
        )

        self.assertEqual(first["generated_at"], second["generated_at"])
        self.assertEqual(self.active + ["R"], changed["active_letters"])


if __name__ == "__main__":
    unittest.main()
