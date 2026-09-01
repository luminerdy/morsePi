from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SystemdUnitTests(unittest.TestCase):
    def test_browser_service_supervises_chromium(self):
        service = (ROOT / "systemd" / "morse-station-browser.service").read_text(encoding="utf-8")
        launcher = (ROOT / "systemd" / "start-morse-browser.sh").read_text(encoding="utf-8")

        self.assertIn("After=morse-station.service", service)
        self.assertIn("Restart=always", service)
        self.assertIn("RestartSec=5", service)
        self.assertIn("ExecStart=/home/morse/bin/start-morse-browser.sh", service)
        self.assertIn('curl -fsS "$URL"', launcher)
        self.assertIn('"$RUNTIME_DIR/$WAYLAND_SOCKET"', launcher)
        self.assertIn("exec /usr/bin/chromium", launcher)
        self.assertNotIn("pgrep", launcher)

    def test_browser_installer_retires_legacy_autostart_after_service_check(self):
        installer = (ROOT / "scripts" / "install_browser_supervisor.sh").read_text(encoding="utf-8")

        active_check = installer.index('systemctl --user is-active --quiet "$SERVICE"')
        labwc_cleanup = installer.index("LABWC_AUTOSTART=")
        self.assertLess(active_check, labwc_cleanup)
        self.assertIn('systemctl --user enable "$SERVICE"', installer)
        self.assertIn('pkill -x chromium', installer)
        self.assertIn('/proc/$main_pid/comm', installer)
        self.assertIn('= "chromium"', installer)
        self.assertIn("morse-station-browser.desktop", installer)

    def test_update_path_installs_browser_supervisor(self):
        updater = (ROOT / "scripts" / "update_station.sh").read_text(encoding="utf-8")

        self.assertIn('BROWSER_INSTALLER="$APP_DIR/scripts/install_browser_supervisor.sh"', updater)
        self.assertIn('"$BROWSER_INSTALLER" --start', updater)
        self.assertGreaterEqual(updater.count("install_browser_supervisor"), 3)
        preflight = updater.index("Browser supervision preflight failed.")
        already_current = updater.index('if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]')
        self.assertLess(preflight, already_current)

    def test_update_path_reports_blocked_state_and_serializes_runs(self):
        updater = (ROOT / "scripts" / "update_station.sh").read_text(encoding="utf-8")

        self.assertIn('flock -n 9', updater)
        self.assertIn('"blocked" "tracked-local-changes" 20 1', updater)
        self.assertIn('"blocked" "update-already-running" 21', updater)
        self.assertIn('"rolled-back" "ending-commit-mismatch" 41', updater)
        self.assertIn('"succeeded" "updated" 0', updater)
        self.assertNotIn('Tracked local changes are present; skipping update.', updater)

    def test_update_path_refreshes_its_own_service_definitions(self):
        updater = (ROOT / "scripts" / "update_station.sh").read_text(encoding="utf-8")

        self.assertIn("install_update_services()", updater)
        self.assertIn('install -m 0755 "$APP_DIR/systemd/update-morse-station.sh"', updater)
        self.assertIn("morse-station-update.service", updater)
        self.assertIn("morse-station-update.timer", updater)
        self.assertIn("morse-station-remote-update.service", updater)
        self.assertIn("morse-station-remote-update.timer", updater)
        self.assertIn("morse-station-sync.service", updater)
        self.assertIn("morse-station-sync.timer", updater)
        self.assertIn("systemctl --user daemon-reload", updater)
        self.assertGreaterEqual(updater.count("install_update_services"), 3)
        self.assertIn('"rolled-back" "update-service-install-failed" 42', updater)

    def test_exit_kiosk_stops_supervision_before_closing_chromium(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        function = app_source[app_source.index("def exit_kiosk_in_background()") :]
        function = function[: function.index("\ndef shutdown_sync_commands()")]

        stop_service = function.index('"morse-station-browser.service"')
        close_browser = function.index('["pkill", "-x", "chromium"]')
        self.assertLess(stop_service, close_browser)

    def test_updater_runs_pending_migrations_before_current_release_exit(self):
        updater = (ROOT / "scripts" / "update_station.sh").read_text(encoding="utf-8")

        backup_call = updater.index('python3 scripts/backup_data.py "${backup_args[@]}"')
        pre_update_call = updater.index("if ! run_pending_migrations", backup_call)
        already_current = updater.index('if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]')
        self.assertLess(backup_call, pre_update_call)
        self.assertLess(pre_update_call, already_current)
        self.assertGreaterEqual(updater.count("run_pending_migrations"), 3)

    def test_student_sync_service_refreshes_progress_views(self):
        service = (ROOT / "systemd" / "morse-station-sync.service").read_text(encoding="utf-8")

        self.assertIn("scripts/student_attempt_sync.py --sync", service)
        self.assertIn("scripts/progress_snapshot.py", service)
        self.assertIn("scripts/station_status.py", service)
        self.assertIn("scripts/family_progress.py", service)
        self.assertIn("scripts/family_activity.py", service)

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
        self.assertIn("TimeoutStartSec=20min", service)


if __name__ == "__main__":
    unittest.main()
