import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from scripts.backup_data import (
    create_backup,
    resolve_station_id,
    restore_backup,
    rotate_backups,
    station_s3_destination,
    upload_backup_to_s3,
    upload_snapshot_to_s3,
    upload_status_to_s3,
)


class BackupDataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.data_dir = self.base / "data"
        self.backup_dir = self.data_dir / "backups"
        self.student_dir = self.data_dir / "students" / "pappy"
        self.student_dir.mkdir(parents=True)

        (self.data_dir / "student_profiles.json").write_text(
            json.dumps([{"id": "pappy", "name": "Pappy"}]),
            encoding="utf-8",
        )
        (self.data_dir / "timing_settings.json").write_text(
            json.dumps({"character_wpm": 12}),
            encoding="utf-8",
        )
        (self.student_dir / "practice_progress.json").write_text("{}", encoding="utf-8")
        (self.student_dir / "learning_state.json").write_text("{}", encoding="utf-8")
        (self.student_dir / "practice_attempts.jsonl").write_text("attempt\n", encoding="utf-8")
        (self.student_dir / "bonus_attempts.jsonl").write_text("bonus\n", encoding="utf-8")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        (self.backup_dir / "do-not-recurse.txt").write_text("skip", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_backup_includes_student_data_and_manifest(self):
        backup_path = create_backup(
            self.data_dir,
            self.backup_dir,
            "manual",
            config_path=self.base / "missing-station-config.json",
        )

        with zipfile.ZipFile(backup_path) as backup_zip:
            names = set(backup_zip.namelist())
            manifest = json.loads(backup_zip.read("manifest.json").decode("utf-8"))

        self.assertIn("data/student_profiles.json", names)
        self.assertIn("data/timing_settings.json", names)
        self.assertIn("data/students/pappy/practice_progress.json", names)
        self.assertIn("data/students/pappy/learning_state.json", names)
        self.assertIn("data/students/pappy/practice_attempts.jsonl", names)
        self.assertIn("data/students/pappy/bonus_attempts.jsonl", names)
        self.assertNotIn("data/backups/do-not-recurse.txt", names)
        self.assertEqual("morse-station-data-backup-v1", manifest["format"])
        self.assertEqual("unknown-station", manifest["station_id"])

    def test_create_backup_uses_station_id_in_manifest_and_filename(self):
        backup_path = create_backup(self.data_dir, self.backup_dir, "manual", station_id="liara-station")

        with zipfile.ZipFile(backup_path) as backup_zip:
            manifest = json.loads(backup_zip.read("manifest.json").decode("utf-8"))

        self.assertIn("liara-station-manual.zip", backup_path.name)
        self.assertEqual("liara-station", manifest["station_id"])

    def test_upload_backup_to_s3_builds_station_path_in_dry_run(self):
        backup_path = self.backup_dir / "backup.zip"
        backup_path.write_text("backup", encoding="utf-8")

        result = upload_backup_to_s3(backup_path, "s3://morsepi-backups/", "astrid-station", dry_run=True)

        self.assertFalse(result["uploaded"])
        self.assertEqual("s3://morsepi-backups/stations/astrid-station/backups/backup.zip", result["destination"])
        self.assertEqual(["aws", "s3", "cp", str(backup_path), result["destination"]], result["command"])

    def test_upload_status_to_s3_builds_status_path_in_dry_run(self):
        status_path = self.data_dir / "station_status.json"
        status_path.write_text("{}", encoding="utf-8")

        result = upload_status_to_s3(status_path, "s3://morsepi-backups/", "astrid-station", dry_run=True)

        self.assertFalse(result["uploaded"])
        self.assertEqual("s3://morsepi-backups/stations/astrid-station/status/station_status.json", result["destination"])
        self.assertEqual(["aws", "s3", "cp", str(status_path), result["destination"]], result["command"])

    def test_upload_snapshot_to_s3_builds_snapshot_path_in_dry_run(self):
        snapshot_path = self.data_dir / "latest_progress.json"
        snapshot_path.write_text("{}", encoding="utf-8")

        result = upload_snapshot_to_s3(snapshot_path, "s3://morsepi-backups/", "astrid-station", dry_run=True)

        self.assertFalse(result["uploaded"])
        self.assertEqual("s3://morsepi-backups/stations/astrid-station/snapshots/latest_progress.json", result["destination"])

    def test_station_s3_destination_sanitizes_station_id(self):
        destination = station_s3_destination("s3://morsepi-backups/", "Astrid Station!", "backups/file.zip")

        self.assertEqual("s3://morsepi-backups/stations/Astrid-Station/backups/file.zip", destination)

    def test_resolve_station_id_reads_station_config(self):
        config_path = self.data_dir / "station_config.json"
        config_path.write_text(json.dumps({"station_id": "astrid-station"}), encoding="utf-8")

        self.assertEqual("astrid-station", resolve_station_id(config_path=config_path))

    def test_restore_backup_extracts_data_folder(self):
        backup_path = create_backup(
            self.data_dir,
            self.backup_dir,
            "manual",
            config_path=self.base / "missing-station-config.json",
        )
        restore_root = self.base / "restore"

        restore_backup(backup_path, restore_root)

        self.assertTrue((restore_root / "data" / "student_profiles.json").exists())
        self.assertTrue((restore_root / "data" / "students" / "pappy" / "bonus_attempts.jsonl").exists())

    def test_rotate_backups_keeps_newest_files(self):
        for index in range(3):
            path = self.backup_dir / f"backup-{index}.zip"
            path.write_text(str(index), encoding="utf-8")
            path.touch()
            time.sleep(0.01)

        removed = rotate_backups(self.backup_dir, keep=2)
        remaining = {path.name for path in self.backup_dir.glob("*.zip")}

        self.assertEqual(1, len(removed))
        self.assertEqual({"backup-1.zip", "backup-2.zip"}, remaining)


if __name__ == "__main__":
    unittest.main()
