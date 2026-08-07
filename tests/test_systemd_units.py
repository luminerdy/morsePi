from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SystemdUnitTests(unittest.TestCase):
    def test_student_sync_service_refreshes_progress_views(self):
        service = (ROOT / "systemd" / "morse-station-sync.service").read_text(encoding="utf-8")

        self.assertIn("scripts/student_attempt_sync.py --sync", service)
        self.assertIn("scripts/progress_snapshot.py", service)
        self.assertIn("scripts/family_progress.py", service)

    def test_student_sync_timer_catches_up_after_boot(self):
        timer = (ROOT / "systemd" / "morse-station-sync.timer").read_text(encoding="utf-8")

        self.assertIn("OnUnitActiveSec=30min", timer)
        self.assertIn("Persistent=true", timer)


if __name__ == "__main__":
    unittest.main()
