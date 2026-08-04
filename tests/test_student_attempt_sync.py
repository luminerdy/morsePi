import json
import tempfile
import unittest
from pathlib import Path

from scripts.student_attempt_sync import build_report, full_sync_attempts, write_report
from scripts.student_attempt_sync import upload_attempts


class MemoryStoreUnavailable:
    def list_keys(self, prefix):
        raise RuntimeError(f"denied {prefix}")


class MemoryStore:
    def __init__(self, keys=None):
        self.objects = {}
        if isinstance(keys, dict):
            self.objects.update(keys)
        else:
            for key in keys or []:
                self.objects[key] = {}

    def list_keys(self, prefix):
        return [key for key in self.objects if key.startswith(prefix)]

    def put_json(self, key, value):
        self.objects[key] = value

    def get_json(self, key):
        return self.objects[key]


class RecordingStore:
    def __init__(self):
        self.prefixes = []

    def list_keys(self, prefix):
        self.prefixes.append(prefix)
        return []


class StudentAttemptSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.data_dir = self.base / "data"
        self.student_dir = self.data_dir / "students" / "astrid"
        self.student_dir.mkdir(parents=True)
        self.config = self.data_dir / "station_config.json"
        self.config.write_text(
            json.dumps({
                "station_id": "pappy-test-station",
                "backup_s3_uri": "s3://morsepi-backups-luminerdy",
            }),
            encoding="utf-8",
        )
        (self.data_dir / "student_profiles.json").write_text(
            json.dumps([
                {"id": "pappy", "name": "Pappy"},
                {"id": "astrid", "name": "Astrid"},
                {"id": "guest", "name": "Guest", "disposable": True},
            ]),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_jsonl(self, filename, records):
        path = self.student_dir / filename
        path.write_text(
            "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
            encoding="utf-8",
        )

    def test_build_report_counts_local_attempts_without_cloud(self):
        self.write_jsonl("practice_attempts.jsonl", [
            {
                "attempt_id": "a" * 32,
                "correct": True,
                "mode": "send",
                "station_id": "pappy-test-station",
                "student_id": "astrid",
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
        ])
        self.write_jsonl("word_attempts.jsonl", [
            {
                "correct": True,
                "station_id": "pappy-test-station",
                "student_id": "astrid",
                "timestamp": "2026-08-04T12:01:00+00:00",
                "word": "TO",
            },
        ])

        report = build_report(self.data_dir, self.config, check_cloud=False)

        self.assertFalse(report["cloud_checked"])
        self.assertEqual(2, report["summary"]["local_unique_attempts"])
        self.assertEqual(2, report["summary"]["would_upload"])
        self.assertEqual(1, report["students"]["astrid"]["practice"])
        self.assertEqual(1, report["students"]["astrid"]["words"])
        self.assertEqual(1, report["students"]["astrid"]["legacy_identity"])

    def test_build_report_uses_station_roster_for_cloud_checks(self):
        self.config.write_text(
            json.dumps({
                "station_id": "astrid-liara-station",
                "backup_s3_uri": "s3://morsepi-backups-luminerdy",
                "students": [
                    {"id": "astrid", "name": "Astrid"},
                    {"id": "liara", "name": "Liara"},
                ],
            }),
            encoding="utf-8",
        )
        store = RecordingStore()

        build_report(self.data_dir, self.config, check_cloud=True, store=store)

        self.assertIn("students/astrid/attempts/practice/", store.prefixes)
        self.assertIn("students/liara/attempts/practice/", store.prefixes)
        self.assertNotIn("students/pappy/attempts/practice/", store.prefixes)

    def test_build_report_detects_duplicate_id_conflict(self):
        self.write_jsonl("practice_attempts.jsonl", [
            {
                "attempt_id": "b" * 32,
                "correct": True,
                "mode": "send",
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
            {
                "attempt_id": "b" * 32,
                "correct": False,
                "mode": "send",
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
        ])

        report = build_report(self.data_dir, self.config, check_cloud=False)

        self.assertEqual(1, report["summary"]["local_unique_attempts"])
        self.assertEqual(1, report["summary"]["local_conflicts"])
        self.assertEqual(
            ["students/astrid/attempts/practice/" + "b" * 32 + ".json"],
            report["conflicts"],
        )

    def test_build_report_preserves_cloud_errors(self):
        self.write_jsonl("bonus_attempts.jsonl", [
            {
                "attempt_id": "c" * 32,
                "correct": True,
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
        ])

        report = build_report(self.data_dir, self.config, check_cloud=True, store=MemoryStoreUnavailable())

        self.assertTrue(report["cloud_checked"])
        self.assertEqual(6, len(report["cloud_errors"]))
        self.assertEqual(1, report["summary"]["would_upload"])

    def test_write_report_creates_file(self):
        self.write_jsonl("bonus_attempts.jsonl", [
            {
                "attempt_id": "c" * 32,
                "correct": True,
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
        ])

        report = build_report(self.data_dir, self.config, check_cloud=False)
        output = write_report(report, self.data_dir / "sync_reports" / "latest.json")

        self.assertTrue(output.exists())
        saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual("morsepi-attempt-sync-dry-run-v1", saved["format"])

    def test_upload_attempts_writes_missing_objects(self):
        attempt_id = "d" * 32
        self.write_jsonl("practice_attempts.jsonl", [
            {
                "attempt_id": attempt_id,
                "correct": True,
                "mode": "read",
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
        ])
        store = MemoryStore()

        result = upload_attempts(self.data_dir, self.config, store=store)

        key = f"students/astrid/attempts/practice/{attempt_id}.json"
        self.assertEqual(1, result["uploaded"])
        self.assertIn(key, store.objects)
        self.assertEqual("morsepi-student-attempt-v1", store.objects[key]["format"])
        self.assertEqual("astrid", store.objects[key]["student_id"])

    def test_upload_attempts_refuses_cloud_errors(self):
        self.write_jsonl("practice_attempts.jsonl", [
            {
                "attempt_id": "e" * 32,
                "correct": True,
                "mode": "read",
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
        ])

        with self.assertRaises(RuntimeError):
            upload_attempts(self.data_dir, self.config, store=MemoryStoreUnavailable())

    def test_full_sync_downloads_cloud_attempts_and_rebuilds_progress(self):
        local_id = "f" * 32
        cloud_id = "g" * 32
        self.write_jsonl("practice_attempts.jsonl", [
            {
                "attempt_id": local_id,
                "correct": True,
                "mode": "send",
                "station_id": "pappy-test-station",
                "student_id": "astrid",
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
        ])
        cloud_key = f"students/astrid/attempts/practice/{cloud_id}.json"
        store = MemoryStore({
            cloud_key: {
                "attempt": {
                    "attempt_id": cloud_id,
                    "correct": False,
                    "mode": "send",
                    "station_id": "astrid-liara-station",
                    "student_id": "astrid",
                    "target": "E",
                    "timestamp": "2026-08-04T12:01:00+00:00",
                },
                "format": "morsepi-student-attempt-v1",
                "kind": "practice",
                "student_id": "astrid",
            }
        })

        result = full_sync_attempts(self.data_dir, self.config, store=store)

        lines = (self.student_dir / "practice_attempts.jsonl").read_text(encoding="utf-8").splitlines()
        progress = json.loads((self.student_dir / "practice_progress.json").read_text(encoding="utf-8"))
        self.assertEqual(2, len(lines))
        self.assertEqual(1, result["uploaded"])
        self.assertEqual(1, result["downloaded"])
        self.assertEqual(2, progress["E"]["send"]["attempts"])
        self.assertEqual(1, progress["E"]["send"]["correct"])

    def test_full_sync_refuses_cloud_conflict_without_rewriting_logs(self):
        attempt_id = "h" * 32
        self.write_jsonl("practice_attempts.jsonl", [
            {
                "attempt_id": attempt_id,
                "correct": True,
                "mode": "send",
                "station_id": "pappy-test-station",
                "student_id": "astrid",
                "target": "E",
                "timestamp": "2026-08-04T12:00:00+00:00",
            },
        ])
        original = (self.student_dir / "practice_attempts.jsonl").read_text(encoding="utf-8")
        cloud_key = f"students/astrid/attempts/practice/{attempt_id}.json"
        store = MemoryStore({
            cloud_key: {
                "attempt": {
                    "attempt_id": attempt_id,
                    "correct": False,
                    "mode": "send",
                    "station_id": "other-station",
                    "student_id": "astrid",
                    "target": "E",
                    "timestamp": "2026-08-04T12:00:00+00:00",
                },
                "format": "morsepi-student-attempt-v1",
                "kind": "practice",
                "student_id": "astrid",
            }
        })

        with self.assertRaises(RuntimeError):
            full_sync_attempts(self.data_dir, self.config, store=store)

        self.assertEqual(original, (self.student_dir / "practice_attempts.jsonl").read_text(encoding="utf-8"))
        self.assertTrue((self.data_dir / "sync_conflicts").exists())


if __name__ == "__main__":
    unittest.main()
