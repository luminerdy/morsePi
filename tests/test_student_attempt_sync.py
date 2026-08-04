import json
import tempfile
import unittest
from pathlib import Path

from scripts.student_attempt_sync import build_report, write_report


class MemoryStoreUnavailable:
    def list_keys(self, prefix):
        raise RuntimeError(f"denied {prefix}")


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
        self.assertEqual(3, len(report["cloud_errors"]))
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


if __name__ == "__main__":
    unittest.main()
