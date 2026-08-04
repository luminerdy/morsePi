import unittest

from scripts.rollout_release import (
    REMOTE_UPDATE_COMMAND,
    run_station_update,
    station_targets,
)


class RolloutReleaseTests(unittest.TestCase):
    def test_station_targets_defaults_to_grandkid_units(self):
        targets = station_targets(None, None)

        self.assertEqual([
            ("astrid-liara", "10.10.10.129"),
            ("campbell-olivea", "10.10.10.157"),
        ], targets)

    def test_station_targets_accepts_custom_host(self):
        targets = station_targets(["astrid-liara"], ["lab=10.10.10.200"])

        self.assertEqual([
            ("astrid-liara", "10.10.10.129"),
            ("lab", "10.10.10.200"),
        ], targets)

    def test_station_targets_rejects_unknown_station(self):
        with self.assertRaises(ValueError):
            station_targets(["unknown"], None)

    def test_run_station_update_dry_run_builds_ssh_command(self):
        result = run_station_update("astrid-liara", "10.10.10.129", "morse", dry_run=True)

        self.assertTrue(result["skipped"])
        self.assertEqual([
            "ssh",
            "morse@10.10.10.129",
            REMOTE_UPDATE_COMMAND,
        ], result["command"])


if __name__ == "__main__":
    unittest.main()
