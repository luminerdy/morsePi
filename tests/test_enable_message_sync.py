import json
import tempfile
import unittest
from pathlib import Path

from scripts.enable_message_sync import MESSAGE_UNITS, enable_message_sync


class EnableMessageSyncTests(unittest.TestCase):
    def make_fixture(self, root):
        root = Path(root)
        app_dir = root / "app"
        config_path = root / "data" / "station_config.json"
        home = root / "home"
        (app_dir / "systemd").mkdir(parents=True)
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps({"station_id": "test-station", "message_sync_enabled": False, "admin_pin": "private"}),
            encoding="utf-8",
        )
        for unit in MESSAGE_UNITS:
            (app_dir / "systemd" / unit).write_text(f"unit={unit}\n", encoding="utf-8")
        return app_dir, config_path, home

    def test_enables_config_and_installs_fixed_units(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir, config_path, home = self.make_fixture(temp_dir)
            commands = []

            result = enable_message_sync(config_path, app_dir, home, runner=commands.append)

            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertTrue(config["message_sync_enabled"])
            self.assertEqual("test-station", result["station_id"])
            self.assertEqual(3, len(commands))
            self.assertEqual(["systemctl", "--user", "daemon-reload"], commands[0])
            self.assertIn("enable", commands[1])
            self.assertIn("morse-station-message-sync.service", commands[2])
            for unit in MESSAGE_UNITS:
                self.assertTrue((home / ".config" / "systemd" / "user" / unit).is_file())
            backups = list((config_path.parent / "config_backups").glob("*.json"))
            self.assertEqual(1, len(backups))
            self.assertFalse(json.loads(backups[0].read_text(encoding="utf-8"))["message_sync_enabled"])

    def test_restores_config_when_service_start_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir, config_path, home = self.make_fixture(temp_dir)
            original = config_path.read_bytes()

            def fail_start(command):
                if "start" in command:
                    raise RuntimeError("service failed")

            with self.assertRaisesRegex(RuntimeError, "service failed"):
                enable_message_sync(config_path, app_dir, home, runner=fail_start)

            self.assertEqual(original, config_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
