import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "set_admin_pin.py"


class SetAdminPinScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "data" / "station_config.json"
        self.config_path.parent.mkdir(parents=True)
        self.config_path.write_text(
            json.dumps(
                {
                    "station_id": "test-station",
                    "admin_pin": "1111",
                    "allow_student_create": False,
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--config", str(self.config_path)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_sets_numeric_pin_without_printing_secret(self):
        result = self.run_script("2745")
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        backups = list(self.config_path.parent.glob("station_config.json.pre-admin-pin-*"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("2745", config["admin_pin"])
        self.assertEqual("test-station", config["station_id"])
        self.assertEqual(1, len(backups))
        self.assertNotIn("2745", result.stdout)

    def test_rejects_non_numeric_pin(self):
        result = self.run_script("27A5")
        config = json.loads(self.config_path.read_text(encoding="utf-8"))

        self.assertNotEqual(0, result.returncode)
        self.assertEqual("1111", config["admin_pin"])
        self.assertIn("numbers only", result.stderr)

    def test_clear_removes_pin(self):
        result = self.run_script("--clear")
        config = json.loads(self.config_path.read_text(encoding="utf-8"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", config["admin_pin"])


if __name__ == "__main__":
    unittest.main()
