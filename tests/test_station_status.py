import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from scripts.station_status import build_status, latest_update_summary, main, queue_update_activity, write_status


class StationStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.backup_dir = self.base / "backups"
        self.backup_dir.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_status_includes_station_id_and_latest_backup(self):
        older = self.backup_dir / "older.zip"
        newer = self.backup_dir / "newer.zip"
        older.write_text("older", encoding="utf-8")
        newer.write_text("newer", encoding="utf-8")
        os.utime(older, (1, 1))
        os.utime(newer, (2, 2))

        status = build_status(
            "liara-station",
            self.backup_dir,
            service_name="",
            browser_service_name="",
        )

        self.assertEqual("morsePi", status["app"])
        self.assertEqual("liara-station", status["station_id"])
        self.assertEqual("newer.zip", status["last_backup"])
        self.assertEqual("unknown", status["service"]["state"])
        self.assertEqual("", status["browser_service"]["name"])
        self.assertEqual("unknown", status["browser_service"]["state"])

    def test_write_status_creates_parent_directory(self):
        output_path = self.base / "status" / "station_status.json"
        status = {"station_id": "astrid-station"}

        write_status(status, output_path)
        saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(status, saved)

    def test_latest_update_summary_exposes_only_safe_result_fields(self):
        update_path = self.base / "latest_update.json"
        update_path.write_text(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "tracked-local-changes",
                    "updated_at": "2026-08-29T15:00:00+00:00",
                    "ending_commit": "abc1234",
                    "tracked_changes": [" M secret-looking-file"],
                    "patch_path": "/private/path.patch",
                }
            ),
            encoding="utf-8",
        )

        summary = latest_update_summary(update_path)

        self.assertEqual("blocked", summary["status"])
        self.assertEqual("tracked-local-changes", summary["reason"])
        self.assertEqual("abc1234", summary["ending_commit"])
        self.assertNotIn("tracked_changes", summary)
        self.assertNotIn("patch_path", summary)

    def test_status_dry_run_uploads_to_status_prefix(self):
        output_path = self.base / "station_status.json"

        with mock.patch(
            "sys.argv",
            [
                "station_status.py",
                "--station-id",
                "astrid-station",
                "--service",
                "",
                "--browser-service",
                "",
                "--backup-dir",
                str(self.backup_dir),
                "--output",
                str(output_path),
                "--s3-uri",
                "s3://morsepi-backups",
                "--dry-run-s3",
            ],
        ), mock.patch("builtins.print") as mock_print:
            main()

        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("s3://morsepi-backups/stations/astrid-station/status/station_status.json", printed)

    def test_successful_update_queues_private_safe_activity(self):
        event = queue_update_activity(self.base, {
            "station_id": "astrid-liara-station",
            "update": {
                "status": "succeeded",
                "reason": "updated",
                "updated_at": "2026-09-01T12:00:00+00:00",
                "ending_commit": "abcdef123456",
                "tracked_changes": ["private-file"],
            },
        })

        self.assertEqual("software_update_succeeded", event["event_type"])
        self.assertNotIn("tracked_changes", event["details"])
        pending = list((self.base / "family_activity" / "pending").glob("*.json"))
        self.assertEqual(1, len(pending))


if __name__ == "__main__":
    unittest.main()
