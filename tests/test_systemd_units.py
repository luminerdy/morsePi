from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SystemdUnitTests(unittest.TestCase):
    def test_updater_runs_pending_migrations_before_current_release_exit(self):
        updater = (ROOT / "scripts" / "update_station.sh").read_text(encoding="utf-8")

        pre_update_call = updater.index(
            'python3 scripts/backup_data.py "${backup_args[@]}"\nrun_pending_migrations'
        )
        already_current = updater.index('if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]')
        self.assertLess(pre_update_call, already_current)
        self.assertGreaterEqual(updater.count("run_pending_migrations"), 3)

    def test_student_sync_service_refreshes_progress_views(self):
        service = (ROOT / "systemd" / "morse-station-sync.service").read_text(encoding="utf-8")

        self.assertIn("scripts/student_attempt_sync.py --sync", service)
        self.assertIn("scripts/progress_snapshot.py", service)
        self.assertIn("scripts/family_progress.py", service)

    def test_student_sync_timer_catches_up_after_boot(self):
        timer = (ROOT / "systemd" / "morse-station-sync.timer").read_text(encoding="utf-8")

        self.assertIn("OnUnitActiveSec=30min", timer)
        self.assertIn("Persistent=true", timer)

    def test_remote_update_timer_polls_iot_jobs(self):
        service = (ROOT / "systemd" / "morse-station-remote-update.service").read_text(encoding="utf-8")
        timer = (ROOT / "systemd" / "morse-station-remote-update.timer").read_text(encoding="utf-8")

        self.assertIn("scripts/remote_update_iot.py --once", service)
        self.assertIn("OnUnitActiveSec=15min", timer)
        self.assertIn("Persistent=true", timer)


if __name__ == "__main__":
    unittest.main()
