import json
import tempfile
import unittest
from pathlib import Path

from message_cloud import MessageValidationError, cloud_message_from_local
from message_store import create_message
from scripts.migrate_student_uuids import migrate
from student_identity import (
    StudentIdentityError,
    enrich_student_identity,
    load_family_registry,
    student_uuid_for_id,
    validate_identity_pair,
)


class StudentIdentityTests(unittest.TestCase):
    def test_registry_has_unique_canonical_family_identities(self):
        students = load_family_registry()
        self.assertEqual(5, len(students))
        self.assertEqual(len(students), len({item["id"] for item in students}))
        self.assertEqual(len(students), len({item["student_uuid"] for item in students}))

    def test_station_examples_share_registry_uuids(self):
        root = Path(__file__).resolve().parents[1]
        registry = {item["id"]: item["student_uuid"] for item in load_family_registry()}
        for path in sorted((root / "config" / "stations").glob("*.json")):
            config = json.loads(path.read_text(encoding="utf-8"))
            for key in ("students", "family_students"):
                for profile in config.get(key, []):
                    self.assertEqual(
                        registry[profile["id"]],
                        profile.get("student_uuid"),
                        f"{path.name}:{key}:{profile['id']}",
                    )
            self.assertNotIn("student_uuid", config.get("guest_profile", {}))

    def test_rename_keeps_canonical_uuid(self):
        profile = enrich_student_identity({"id": "astrid", "name": "Astrid Operator"})
        self.assertEqual("Astrid Operator", profile["name"])
        self.assertEqual(student_uuid_for_id("astrid"), profile["student_uuid"])

    def test_conflicting_identity_fails_closed(self):
        with self.assertRaises(StudentIdentityError):
            validate_identity_pair("astrid", student_uuid_for_id("liara"))

        message = create_message(
            "pappy",
            "astrid",
            "pappy-station",
            "AM",
            list("ETANIMSO"),
            sender_student_uuid=student_uuid_for_id("liara"),
            recipient_student_uuid=student_uuid_for_id("astrid"),
        )
        with self.assertRaises(MessageValidationError):
            cloud_message_from_local(message)

    def test_legacy_message_is_enriched_for_new_upload(self):
        message = create_message(
            "pappy", "astrid", "pappy-station", "AM", list("ETANIMSO")
        )
        payload = cloud_message_from_local(message)
        self.assertEqual(student_uuid_for_id("pappy"), payload["sender_student_uuid"])
        self.assertEqual(student_uuid_for_id("astrid"), payload["recipient_student_uuid"])

    def test_migration_is_idempotent_and_preserves_history_and_guest(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir) / "data"
            student_dir = data_dir / "students" / "astrid"
            student_dir.mkdir(parents=True)
            config_path = data_dir / "station_config.json"
            config_path.write_text(json.dumps({
                "station_id": "test-station",
                "students": [{"id": "astrid", "name": "Astrid"}],
                "family_students": [{"id": "astrid", "name": "Astrid"}],
                "guest_profile": {"id": "guest", "name": "Guest", "guest": True},
            }), encoding="utf-8")
            profiles_path = data_dir / "student_profiles.json"
            profiles_path.write_text(json.dumps([
                {"id": "astrid", "name": "Astrid"},
                {"id": "guest", "name": "Guest", "guest": True, "disposable": True},
            ]), encoding="utf-8")
            profile_path = student_dir / "profile.json"
            profile_path.write_text(json.dumps({"id": "astrid", "name": "Astrid"}), encoding="utf-8")
            attempts_path = student_dir / "practice_attempts.jsonl"
            history = '{"attempt_id":"old","student_id":"astrid"}\n'
            attempts_path.write_text(history, encoding="utf-8")

            first = migrate(data_dir, config_path)
            first_config = config_path.read_bytes()
            first_profiles = profiles_path.read_bytes()
            first_profile = profile_path.read_bytes()
            second = migrate(data_dir, config_path)

            self.assertTrue(first["changed"])
            self.assertEqual([], second["changed"])
            self.assertEqual(first_config, config_path.read_bytes())
            self.assertEqual(first_profiles, profiles_path.read_bytes())
            self.assertEqual(first_profile, profile_path.read_bytes())
            self.assertEqual(history, attempts_path.read_text(encoding="utf-8"))
            self.assertTrue((data_dir / "students" / "astrid").is_dir())

            profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
            astrid = next(item for item in profiles if item["id"] == "astrid")
            guest = next(item for item in profiles if item["id"] == "guest")
            self.assertEqual(student_uuid_for_id("astrid"), astrid["student_uuid"])
            self.assertNotIn("student_uuid", guest)


if __name__ == "__main__":
    unittest.main()
