import json
import tempfile
import unittest
from pathlib import Path

from morsepi.services.family_activity import (
    EVENT_FORMAT,
    activity_event_key,
    flush_activity_events,
    load_activity_cache,
    new_activity_event,
    queue_activity_event,
    refresh_family_activity,
    validate_activity_event,
    latest_update_outcomes,
    update_failure_recovered,
)
from scripts.family_activity import refresh_from_config


class MemoryStore:
    def __init__(self, objects=None, fail_prefixes=None, fail_put=False):
        self.objects = dict(objects or {})
        self.fail_prefixes = set(fail_prefixes or [])
        self.fail_put = fail_put

    def put_json(self, key, value):
        if self.fail_put:
            raise RuntimeError("offline")
        self.objects[key] = json.loads(json.dumps(value))

    def get_json(self, key, default=...):
        for prefix in self.fail_prefixes:
            if key.startswith(prefix):
                raise RuntimeError("offline")
        if key in self.objects:
            return json.loads(json.dumps(self.objects[key]))
        if default is not ...:
            return default
        raise KeyError(key)

    def list_keys(self, prefix):
        for failed in self.fail_prefixes:
            if prefix.startswith(failed):
                raise RuntimeError("offline")
        return sorted(key for key in self.objects if key.startswith(prefix))


class FamilyActivityTests(unittest.TestCase):
    def test_later_current_update_clears_older_failure_without_deleting_it(self):
        failed = {"station_id": "station-a", "event_type": "software_update_failed", "occurred_at": "2026-09-10T00:00:00Z"}
        cache = {"events": [failed], "stations": [{"id": "station-a", "status": {"update": {"status": "current", "updated_at": "2026-09-12T00:00:00Z"}}}]}
        self.assertTrue(update_failure_recovered(failed, latest_update_outcomes(cache)))
        self.assertEqual(cache["events"], [failed])

    def test_checkin_wrong_station_and_invalid_time_do_not_clear_failure(self):
        failed = {"station_id": "station-a", "event_type": "software_update_failed", "occurred_at": "2026-09-10T00:00:00Z"}
        for state in [
            {"checked_at": "2026-09-12T00:00:00Z"},
            {"update": {"status": "current", "updated_at": "bad"}},
            {"update": {"status": "current", "updated_at": "2026-09-09T00:00:00Z"}},
        ]:
            cache = {"events": [failed], "stations": [{"id": "station-a", "status": state}, {"id": "station-b", "status": {"update": {"status": "current", "updated_at": "2026-09-12T00:00:00Z"}}}]}
            self.assertFalse(update_failure_recovered(failed, latest_update_outcomes(cache)))

    def test_later_failure_overrides_success_even_when_events_are_unsorted(self):
        failed = {"station_id": "station-a", "event_type": "software_update_failed", "occurred_at": "2026-09-12T00:00:00Z"}
        success = {"station_id": "station-a", "event_type": "software_update_succeeded", "occurred_at": "2026-09-11T00:00:00Z"}
        for events in [[failed, success], [success, failed]]:
            self.assertFalse(update_failure_recovered(failed, latest_update_outcomes({"events": events})))

    def test_equal_time_is_not_recovery_and_later_success_is(self):
        failed = {"station_id": "station-a", "event_type": "software_update_failed", "occurred_at": "2026-09-10T00:00:00Z"}
        for stamp, expected in [("2026-09-10T00:00:00Z", False), ("2026-09-11T00:00:00Z", True)]:
            success = dict(failed, event_type="software_update_succeeded", occurred_at=stamp)
            self.assertEqual(update_failure_recovered(failed, latest_update_outcomes({"events": [failed, success]})), expected)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_event_identity_is_deterministic_and_details_are_allowlisted(self):
        first = new_activity_event(
            "pappy-test-station",
            "message_sent",
            "message-123",
            occurred_at="2026-09-01T12:00:00+00:00",
            details={
                "message_id": "message-123",
                "recipient_student_id": "astrid",
                "sender_student_id": "pappy",
                "message_text": "private words",
                "student_name": "Private Name",
                "timing": [1, 2, 3],
            },
        )
        second = new_activity_event(
            "pappy-test-station",
            "message_sent",
            "message-123",
            occurred_at="2026-09-02T12:00:00+00:00",
        )

        self.assertEqual(EVENT_FORMAT, first["format"])
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(
            {
                "message_id": "message-123",
                "recipient_student_id": "astrid",
                "sender_student_id": "pappy",
            },
            first["details"],
        )
        self.assertEqual(
            f"stations/pappy-test-station/activity/2026/09/01/{first['event_id']}.json",
            activity_event_key(first),
        )

    def test_offline_event_stays_pending_then_uploads_once(self):
        event = new_activity_event(
            "astrid-liara-station",
            "progress_uploaded",
            "upload-1",
            details={"uploaded": 14},
        )
        first_queue = queue_activity_event(self.data_dir, event)
        duplicate_queue = queue_activity_event(self.data_dir, event)
        failed = flush_activity_events(self.data_dir, MemoryStore(fail_put=True))

        self.assertTrue(first_queue["queued"])
        self.assertFalse(duplicate_queue["queued"])
        self.assertEqual(1, failed["pending"])
        self.assertEqual(1, len(failed["errors"]))

        store = MemoryStore()
        completed = flush_activity_events(self.data_dir, store)
        repeated = flush_activity_events(self.data_dir, store)

        self.assertEqual(1, completed["uploaded"])
        self.assertEqual(0, completed["pending"])
        self.assertEqual(0, repeated["uploaded"])
        self.assertIn(activity_event_key(event), store.objects)

    def test_refresh_preserves_offline_station_cache(self):
        old_event = new_activity_event(
            "campbell-olivea-station",
            "message_received",
            "old-message",
            occurred_at="2026-08-31T12:00:00+00:00",
            details={"message_id": "old-message"},
        )
        cache_path = self.data_dir / "family_activity" / "cache.json"
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text(json.dumps({
            "events": [old_event],
            "format": "morsepi-family-activity-cache-v1",
            "refreshed_at": "2026-08-31T12:01:00+00:00",
            "refresh_errors": [],
            "stations": [{
                "id": "campbell-olivea-station",
                "name": "Campbell / Olivea",
                "status": {
                    "checked_at": "2026-08-31T12:00:00+00:00",
                    "git_branch": "release/pi",
                    "git_commit": "abc1234",
                    "station_id": "campbell-olivea-station",
                    "update": {},
                },
            }],
        }), encoding="utf-8")
        config = {"family_stations": [
            {"id": "campbell-olivea-station", "name": "Campbell / Olivea"},
        ]}

        refreshed = refresh_family_activity(
            self.data_dir,
            config,
            MemoryStore(fail_prefixes={"stations/campbell-olivea-station/"}),
        )

        self.assertEqual(old_event["event_id"], refreshed["events"][0]["event_id"])
        self.assertEqual("abc1234", refreshed["stations"][0]["status"]["git_commit"])
        self.assertEqual("refresh", refreshed["refresh_errors"][0]["kind"])
        self.assertEqual(refreshed, load_activity_cache(self.data_dir))

    def test_validation_rejects_station_path_mismatch(self):
        event = new_activity_event("pappy-test-station", "message_sent", "message-1")
        with self.assertRaisesRegex(ValueError, "station path"):
            validate_activity_event(event, expected_station_id="astrid-liara-station")

    def test_refresh_cli_defaults_reader_to_pappy_only(self):
        config_path = self.data_dir / "station_config.json"
        config_path.write_text(json.dumps({
            "backup_s3_uri": "s3://example-bucket",
            "station_id": "pappy-test-station",
            "family_stations": [{"id": "pappy-test-station", "name": "Pappy"}],
        }), encoding="utf-8")
        pappy = refresh_from_config(self.data_dir, config_path, store=MemoryStore())

        config_path.write_text(json.dumps({
            "backup_s3_uri": "s3://example-bucket",
            "station_id": "astrid-liara-station",
        }), encoding="utf-8")
        grandkid = refresh_from_config(self.data_dir, config_path, store=MemoryStore())

        self.assertEqual("completed", pappy["status"])
        self.assertEqual("skipped", grandkid["status"])


if __name__ == "__main__":
    unittest.main()
