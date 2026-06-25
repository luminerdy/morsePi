import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.station_status import build_status, write_status


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

        status = build_status("liara-station", self.backup_dir, service_name="")

        self.assertEqual("morsePi", status["app"])
        self.assertEqual("liara-station", status["station_id"])
        self.assertEqual("newer.zip", status["last_backup"])
        self.assertEqual("unknown", status["service"]["state"])

    def test_write_status_creates_parent_directory(self):
        output_path = self.base / "status" / "station_status.json"
        status = {"station_id": "astrid-station"}

        write_status(status, output_path)
        saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(status, saved)


if __name__ == "__main__":
    unittest.main()
