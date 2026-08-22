import importlib
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


os.environ.setdefault("GPIOZERO_PIN_FACTORY", "mock")

try:
    app_module = importlib.import_module("app")
    student_identity = importlib.import_module("student_identity")
    student_profiles = importlib.import_module("student_profiles")
except ModuleNotFoundError as error:
    app_module = None
    student_identity = None
    student_profiles = None
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None


@unittest.skipIf(app_module is None, f"app dependencies unavailable: {IMPORT_ERROR}")
class RouteRenderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.data_dir = self.base / "data"
        self.students_dir = self.data_dir / "students"

        self.original_student_paths = {
            "DATA_DIR": student_profiles.DATA_DIR,
            "STUDENTS_DIR": student_profiles.STUDENTS_DIR,
            "PROFILES_PATH": student_profiles.PROFILES_PATH,
        }
        self.original_timing_path = app_module.TIMING_SETTINGS_PATH
        self.original_volume_path = app_module.VOLUME_SETTINGS_PATH
        self.original_family_progress_path = app_module.FAMILY_PROGRESS_PATH
        self.original_shutdown_sync_status_path = app_module.SHUTDOWN_SYNC_STATUS_PATH
        self.original_sync_status_path = app_module.SYNC_STATUS_PATH
        self.original_attempt_sync_report_path = app_module.ATTEMPT_SYNC_REPORT_PATH
        self.original_station_config_path = app_module.STATION_CONFIG_PATH
        self.original_admin_pin_path = app_module.ADMIN_PIN_PATH
        self.original_play_daily = app_module.play_daily_celebration_in_background
        self.original_last_message = app_module.last_message
        self.original_last_morse = app_module.last_morse
        self.original_station_volume = app_module.station_volume
        self.original_system_status = app_module.system_status
        self.original_restart_wifi = app_module.restart_wifi_in_background
        self.original_exit_kiosk = app_module.exit_kiosk_in_background
        self.original_shutdown_pi = app_module.shutdown_pi_in_background
        self.original_launch_keyboard = app_module.launch_keyboard_in_background
        self.original_start_update_service = app_module.start_update_service
        self.original_start_sync_service = app_module.start_sync_service
        self.original_get_current_key_morse = app_module.get_current_key_morse
        self.original_practice_target = app_module.practice_target
        self.original_practice_feedback = app_module.practice_feedback

        student_profiles.DATA_DIR = self.data_dir
        student_profiles.STUDENTS_DIR = self.students_dir
        student_profiles.PROFILES_PATH = self.data_dir / "student_profiles.json"
        app_module.TIMING_SETTINGS_PATH = self.data_dir / "timing_settings.json"
        app_module.VOLUME_SETTINGS_PATH = self.data_dir / "volume_settings.json"
        app_module.FAMILY_PROGRESS_PATH = self.data_dir / "family_progress" / "latest.json"
        app_module.SHUTDOWN_SYNC_STATUS_PATH = self.data_dir / "sync_reports" / "latest_shutdown_sync.json"
        app_module.SYNC_STATUS_PATH = self.data_dir / "sync_reports" / "latest_sync_status.json"
        app_module.ATTEMPT_SYNC_REPORT_PATH = self.data_dir / "sync_reports" / "latest_attempt_sync.json"
        app_module.STATION_CONFIG_PATH = self.data_dir / "station_config.json"
        app_module.ADMIN_PIN_PATH = self.data_dir / "admin_pin.txt"
        app_module.reset_admin_pin_lockout()
        app_module.station_volume = app_module.DEFAULT_STATION_VOLUME
        app_module.play_daily_celebration_in_background = self.record_daily_celebration
        self.daily_celebration_called = False
        self.daily_celebration_count = 0

        student_profiles.save_profiles(
            [
                {"id": "pappy", "name": "Pappy"},
                {"id": "astrid", "name": "Astrid"},
            ]
        )
        self.client = app_module.app.test_client()

    def tearDown(self):
        student_profiles.DATA_DIR = self.original_student_paths["DATA_DIR"]
        student_profiles.STUDENTS_DIR = self.original_student_paths["STUDENTS_DIR"]
        student_profiles.PROFILES_PATH = self.original_student_paths["PROFILES_PATH"]
        app_module.TIMING_SETTINGS_PATH = self.original_timing_path
        app_module.VOLUME_SETTINGS_PATH = self.original_volume_path
        app_module.FAMILY_PROGRESS_PATH = self.original_family_progress_path
        app_module.SHUTDOWN_SYNC_STATUS_PATH = self.original_shutdown_sync_status_path
        app_module.SYNC_STATUS_PATH = self.original_sync_status_path
        app_module.ATTEMPT_SYNC_REPORT_PATH = self.original_attempt_sync_report_path
        app_module.STATION_CONFIG_PATH = self.original_station_config_path
        app_module.ADMIN_PIN_PATH = self.original_admin_pin_path
        app_module.play_daily_celebration_in_background = self.original_play_daily
        app_module.last_message = self.original_last_message
        app_module.last_morse = self.original_last_morse
        app_module.station_volume = self.original_station_volume
        app_module.system_status = self.original_system_status
        app_module.restart_wifi_in_background = self.original_restart_wifi
        app_module.exit_kiosk_in_background = self.original_exit_kiosk
        app_module.shutdown_pi_in_background = self.original_shutdown_pi
        app_module.launch_keyboard_in_background = self.original_launch_keyboard
        app_module.start_update_service = self.original_start_update_service
        app_module.start_sync_service = self.original_start_sync_service
        app_module.get_current_key_morse = self.original_get_current_key_morse
        app_module.practice_target = self.original_practice_target
        app_module.practice_feedback = self.original_practice_feedback
        app_module.reset_admin_pin_lockout()
        self.temp_dir.cleanup()

    def record_daily_celebration(self):
        self.daily_celebration_called = True
        self.daily_celebration_count += 1

    def student_file(self, student_id, filename):
        return self.students_dir / student_id / filename

    def write_json(self, student_id, filename, value):
        path = self.student_file(student_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")

    def write_text_file(self, student_id, filename, value):
        path = self.student_file(student_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def write_legacy_text_file(self, filename, value):
        path = self.data_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def write_station_config(self, value):
        app_module.STATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        app_module.STATION_CONFIG_PATH.write_text(json.dumps(value), encoding="utf-8")

    def write_attempts(self, student_id, total, correct, target="E", mode="send"):
        path = self.student_file(student_id, "practice_attempts.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        for index in range(total):
            lines.append(
                json.dumps(
                    {
                        "correct": index < correct,
                        "target": target,
                        "mode": mode,
                        "timestamp": f"{app_module.today_key()}T00:{index:02d}:00+00:00",
                    },
                    sort_keys=True,
                )
            )

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_word_attempts(self, student_id, total, correct, word="AM", timestamp="2026-06-21T00:00:00+00:00"):
        path = self.student_file(student_id, "word_attempts.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        for index in range(total):
            lines.append(
                json.dumps(
                    {
                        "correct": index < correct,
                        "word": word,
                        "timestamp": timestamp,
                    },
                    sort_keys=True,
                )
            )

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def complete_starter_progress(self, student_id):
        progress = {}
        for letter in app_module.starter_practice_letters:
            progress[letter] = {
                mode: {
                    "attempts": 10,
                    "correct": 10,
                    "last_seen": "2026-06-21T00:00:00+00:00",
                    "streak": 10,
                    "strength": 1.0,
                }
                for mode in app_module.practice_modes
            }

        self.write_json(student_id, "practice_progress.json", progress)

    def complete_progress(self, student_id, letters):
        progress = {}
        for letter in letters:
            progress[letter] = {
                mode: {
                    "attempts": 10,
                    "correct": 10,
                    "last_seen": "2026-06-23T00:00:00+00:00",
                    "streak": 10,
                    "strength": 1.0,
                }
                for mode in app_module.practice_modes
            }

        self.write_json(student_id, "practice_progress.json", progress)
        return progress

    def unlock_messages(self, student_id):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress(student_id, active_letters)
        self.set_learning_state(
            student_id,
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2000-01-01",
        )
        return active_letters

    def set_learning_state(self, student_id, groups, last_learning_start_date="2026-06-23"):
        self.write_json(
            student_id,
            "learning_state.json",
            {
                "groups": groups,
                "last_learning_start_date": last_learning_start_date,
            },
        )

    def set_student_cookie(self, student_id):
        self.client.set_cookie(app_module.STUDENT_COOKIE, student_id)

    def set_practice_session_cookie(self, session_id):
        self.client.set_cookie(app_module.SESSION_COOKIE, session_id)

    def test_touch_start_redirects_to_student_selection_with_multiple_profiles(self):
        response = self.client.get("/touch")

        self.assertEqual(302, response.status_code)
        self.assertEqual("/touch/students", response.headers["Location"])

    def test_touch_start_redirects_to_daily_with_one_profile(self):
        student_profiles.save_profiles([{"id": "pappy", "name": "Pappy"}])
        shutil.rmtree(self.students_dir / "astrid")

        response = self.client.get("/touch")

        self.assertEqual(302, response.status_code)
        self.assertEqual("/touch/daily", response.headers["Location"])

    def test_touch_menu_remains_available(self):
        response = self.client.get("/touch/menu")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Touch Menu", html)
        self.assertIn("/touch/students?next=/touch/daily", html)
        self.assertIn("/touch/system", html)
        self.assertIn("/touch/shutdown", html)

    def test_touch_timing_includes_speaker_volume_presets(self):
        self.write_station_config({"admin_pin": "1234"})

        response = self.client.get("/touch/timing")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Speaker", html)
        self.assertIn('action="/station-volume"', html)
        self.assertIn('name="station_volume" value="0"', html)
        self.assertIn('name="station_volume" value="35"', html)
        self.assertIn("data-touch-pin-copy", html)
        self.assertIn('class="touch-pin-pad compact wide"', html)

    def test_touch_settings_pin_failure_returns_to_usable_timing_screen(self):
        self.write_station_config({"admin_pin": "1234"})

        denied_volume = self.client.post(
            "/station-volume",
            data={
                "station_volume": "0",
                "admin_pin": "",
                "next": "/touch/timing",
            },
        )
        denied_timing = self.client.post(
            "/timing-settings",
            data={
                "character_wpm": "35",
                "effective_wpm": "35",
                "tone_hz": "1000",
                "admin_pin": "0000",
                "next": "/touch/timing",
            },
        )
        timing_page = self.client.get(denied_volume.headers["Location"])
        html = timing_page.get_data(as_text=True)

        self.assertEqual(302, denied_volume.status_code)
        self.assertEqual(
            "/touch/timing?settings_error=admin-pin",
            denied_volume.headers["Location"],
        )
        self.assertEqual(302, denied_timing.status_code)
        self.assertEqual(
            "/touch/timing?settings_error=admin-pin",
            denied_timing.headers["Location"],
        )
        self.assertEqual(200, timing_page.status_code)
        self.assertIn("Enter the admin PIN, then choose a setting.", html)
        self.assertIn('href="/touch/menu"', html)
        self.assertEqual(35, app_module.station_volume_percent())

    def test_touch_shutdown_confirm_page_does_not_require_admin_pin(self):
        self.write_station_config({"admin_pin": "1234"})

        response = self.client.get("/touch/shutdown")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Power Off Station", html)
        self.assertIn("Keep Practicing", html)
        self.assertIn('name="confirm" value="shutdown"', html)
        self.assertNotIn("data-touch-pin-pad", html)

    def test_touch_shutdown_cancel_does_not_start_shutdown(self):
        called = {"shutdown": False}
        app_module.shutdown_pi_in_background = lambda: called.__setitem__("shutdown", True)

        response = self.client.post("/touch/shutdown", data={"confirm": "no"})

        self.assertEqual(302, response.status_code)
        self.assertEqual("/touch/menu", response.headers["Location"])
        self.assertFalse(called["shutdown"])

    def test_touch_shutdown_confirm_starts_shutdown_worker(self):
        called = {"shutdown": False}
        app_module.shutdown_pi_in_background = lambda: called.__setitem__("shutdown", True)

        response = self.client.post("/touch/shutdown", data={"confirm": "shutdown"})
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertTrue(called["shutdown"])
        self.assertIn("Powering Off", html)
        self.assertIn("Wait for the screen to go dark", html)
        self.assertIn("PiSwitch", html)

    def test_shutdown_sync_cycle_creates_backup_and_snapshot(self):
        calls = []

        def fake_run_system_command(command, timeout=4):
            calls.append((command, timeout))
            return {"ok": True, "stdout": "ok", "stderr": ""}

        with patch.object(app_module, "run_system_command", fake_run_system_command):
            status = app_module.run_shutdown_sync_cycle()

        self.assertTrue(status["ok"])
        self.assertEqual(
            [
                "backup_data.py",
                "progress_snapshot.py",
                "station_status.py",
            ],
            [Path(call[0][1]).name for call in calls],
        )
        self.assertIn("--label", calls[0][0])
        self.assertIn("shutdown", calls[0][0])
        saved = json.loads(app_module.SHUTDOWN_SYNC_STATUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual("morsepi-shutdown-sync-status-v1", saved["format"])
        self.assertTrue(saved["ok"])

    def test_station_audio_samples_start_with_preroll_silence(self):
        timing = {
            "dash_seconds": 0.3,
            "dot_seconds": 0.1,
            "letter_gap_seconds": 0.6,
            "symbol_gap_seconds": 0.1,
            "tone_hz": 700,
            "word_gap_seconds": 1.4,
        }

        samples = app_module.morse_to_audio_samples(".", 0.5, timing, preroll_seconds=0.01)
        preroll_samples = int(app_module.SAMPLE_RATE * 0.01)

        self.assertTrue(all(sample == 0 for sample in samples[:preroll_samples]))
        self.assertTrue(any(sample != 0 for sample in samples[preroll_samples:]))

    def test_touch_practice_menu_shows_locked_words_for_fresh_student(self):
        response = self.client.get("/touch/practice")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("<strong>Warm Up</strong>", html)
        self.assertIn("Quick review", html)
        self.assertIn('href="/touch/practice/run?mode=warmup"', html)
        self.assertIn("<strong>Words</strong>", html)
        self.assertIn("Unlock after S O", html)
        self.assertIn('href="/touch/progress"', html)

    def test_touch_warmup_shows_letter_without_morse_answer(self):
        app_module.practice_target = "A"

        response = self.client.get("/touch/practice/run?mode=warmup")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn('data-practice-mode="warmup"', html)
        self.assertIn('data-practice-target="A"', html)
        self.assertIn('<div class="target-letter" id="targetLetter">A</div>', html)
        self.assertIn('id="expectedMorse">\n                        ?', html)
        self.assertNotIn('morse-symbol dot', html)
        self.assertNotIn('morse-symbol dash', html)

    def test_home_message_is_limited_before_encoding(self):
        response = self.client.post("/", data={"message": "A" * (app_module.MAX_MESSAGE_CHARS + 25)})

        self.assertEqual(200, response.status_code)
        self.assertEqual(app_module.MAX_MESSAGE_CHARS, len(app_module.last_message))

    def test_safe_next_url_rejects_external_redirect(self):
        response = self.client.post(
            "/practice/new?mode=send",
            data={"next": "https://example.com/not-local"},
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual("/practice?mode=send", response.headers["Location"])

    def test_safe_next_url_allows_local_redirect(self):
        response = self.client.post(
            "/practice/new?mode=send",
            data={"next": "/touch/daily"},
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual("/touch/daily", response.headers["Location"])

    def test_touch_system_shows_network_status(self):
        app_module.system_status = lambda: {
            "hostname": "PiMorse",
            "ip_addresses": ["10.10.10.141"],
            "wifi_ssid": "FamilyWifi",
            "wifi_signal": "82%",
            "wifi_state": "connected",
            "connectivity": "full",
            "nmcli_available": True,
            "iwgetid_available": True,
            "keyboard_available": True,
            "keyboard_command": "matchbox-keyboard",
            "update_service_available": True,
            "update_service": "morse-station-update.service",
            "update_service_state": "inactive",
            "update_status": {
                "service": "morse-station-update.service",
                "service_state": "inactive",
                "timer": "morse-station-update.timer",
                "timer_enabled": "enabled",
                "timer_state": "active",
                "last_result": "success",
            },
            "sync_service_available": True,
            "sync_service": "morse-station-sync.service",
            "sync_service_state": "inactive",
            "sync_status": {
                "label": "Completed",
                "relative": "5 min ago",
                "detail": "2 up, 3 down",
                "updated_at": "2026-08-06T21:00:00+00:00",
            },
            "sync_timer": "morse-station-sync.timer",
            "git": {
                "branch": "release/pi",
                "commit": "abc1234",
                "version": "abc1234",
            },
            "backup": {
                "label": "Last backup",
                "name": "20260806-test.zip",
                "relative": "2 hr ago",
            },
        }

        response = self.client.get("/touch/system")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Admin System", html)
        self.assertIn("PiMorse", html)
        self.assertIn("FamilyWifi", html)
        self.assertIn("10.10.10.141", html)
        self.assertIn("Restart Wi-Fi", html)
        self.assertIn("Open Keyboard", html)
        self.assertIn("matchbox-keyboard", html)
        self.assertIn("Update App", html)
        self.assertIn("App updater", html)
        self.assertIn("active timer", html)
        self.assertIn("enabled", html)
        self.assertIn("success", html)
        self.assertIn("Sync Now", html)
        self.assertNotIn("morse-station-sync.service", html)
        self.assertIn("Completed", html)
        self.assertIn("5 min ago", html)
        self.assertIn("2 up, 3 down", html)
        self.assertIn("Scheduled", html)
        self.assertIn("job Idle", html)
        self.assertIn("App Version", html)
        self.assertIn("abc1234", html)
        self.assertIn("release/pi", html)
        self.assertIn("Backup", html)
        self.assertIn("2 hr ago", html)
        self.assertIn("20260806-test.zip", html)
        self.assertIn("Exit Kiosk", html)

    def test_sync_status_summary_reports_completed_sync(self):
        app_module.SYNC_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        app_module.SYNC_STATUS_PATH.write_text(
            json.dumps({
                "status": "completed",
                "updated_at": "2026-08-06T21:00:00+00:00",
                "result": {
                    "uploaded": 2,
                    "downloaded": 3,
                },
            }),
            encoding="utf-8",
        )

        summary = app_module.load_sync_status_summary(
            now=app_module.datetime(2026, 8, 6, 21, 5, tzinfo=app_module.timezone.utc)
        )

        self.assertEqual("Completed", summary["label"])
        self.assertEqual("5 min ago", summary["relative"])
        self.assertEqual("2 up, 3 down", summary["detail"])

    def test_sync_status_summary_reports_skipped_sync_reason(self):
        app_module.SYNC_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        app_module.SYNC_STATUS_PATH.write_text(
            json.dumps({
                "status": "skipped",
                "updated_at": "2026-08-06T21:00:00+00:00",
                "reason": "recent-activity",
            }),
            encoding="utf-8",
        )

        summary = app_module.load_sync_status_summary()

        self.assertEqual("Skipped", summary["label"])
        self.assertEqual("recent activity", summary["detail"])

    def test_sync_status_summary_falls_back_to_attempt_report(self):
        app_module.ATTEMPT_SYNC_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        app_module.ATTEMPT_SYNC_REPORT_PATH.write_text(
            json.dumps({
                "generated_at": "2026-08-06T21:00:00+00:00",
                "summary": {
                    "local_unique_attempts": 717,
                    "would_upload": 0,
                    "local_conflicts": 0,
                },
                "cloud_errors": [],
            }),
            encoding="utf-8",
        )

        summary = app_module.load_sync_status_summary(
            now=app_module.datetime(2026, 8, 6, 21, 5, tzinfo=app_module.timezone.utc)
        )

        self.assertEqual("Report ready", summary["label"])
        self.assertEqual("5 min ago", summary["relative"])
        self.assertEqual("717 attempts checked", summary["detail"])

    def test_first_command_line_keeps_stdout_from_nonzero_status_command(self):
        original_runner = app_module.run_system_command
        app_module.run_system_command = lambda command: {
            "ok": False,
            "stdout": "inactive\n",
            "stderr": "",
            "returncode": 3,
        }

        try:
            value = app_module.first_command_line(["systemctl", "--user", "is-active", "example.service"], "unknown")
        finally:
            app_module.run_system_command = original_runner

        self.assertEqual("inactive", value)

    def test_touch_system_shows_sync_completed_feedback(self):
        app_module.system_status = lambda: {
            "hostname": "PiMorse",
            "ip_addresses": [],
            "wifi_ssid": "FamilyWifi",
            "wifi_signal": "82%",
            "wifi_state": "connected",
            "connectivity": "full",
            "nmcli_available": True,
            "iwgetid_available": True,
            "keyboard_available": True,
            "keyboard_command": "matchbox-keyboard",
            "update_service_available": True,
            "update_service": "morse-station-update.service",
            "update_service_state": "inactive",
            "update_status": {"timer_state": "active", "timer_enabled": "enabled", "last_result": "success"},
            "sync_service_available": True,
            "sync_service": "morse-station-sync.service",
            "sync_service_state": "inactive",
            "sync_status": {"label": "Completed", "relative": "just now", "detail": "0 up, 0 down"},
            "sync_timer": "morse-station-sync.timer",
            "git": {"branch": "release/pi", "commit": "abc1234", "version": "abc1234"},
            "backup": {"label": "Last backup", "name": "backup.zip", "relative": "1 hr ago"},
        }

        response = self.client.get("/touch/system?system_status=sync-completed")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Sync complete. Last Sync is updated.", html)

    def test_touch_system_shows_silent_touch_pin_pad_when_pin_required(self):
        self.write_station_config({"admin_pin": "1234"})

        response = self.client.get("/touch/system")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("data-touch-pin-pad", html)
        self.assertIn("data-touch-pin-input", html)
        self.assertIn("data-touch-pin-digit=\"1\"", html)
        self.assertIn("data-touch-pin-clear", html)
        self.assertIn("data-touch-pin-back", html)
        self.assertNotIn("data-test-sound", html)
        self.assertIn('href="/touch/system/operators"', html)

    def test_touch_operator_manager_lists_family_with_current_roster_checked(self):
        self.write_station_config({
            "admin_pin": "1234",
            "allow_student_create": False,
            "students": [
                {"id": "campbell", "name": "Campbell"},
                {"id": "olivea", "name": "Olivea"},
            ],
            "family_students": [
                {"id": "pappy", "name": "Pappy"},
                {"id": "campbell", "name": "Campbell"},
                {"id": "olivea", "name": "Olivea"},
            ],
            "guest_profile": {
                "id": "guest",
                "name": "Guest Operator",
                "guest": True,
                "disposable": True,
            },
        })

        response = self.client.get("/touch/system/operators")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Manage Operators", html)
        self.assertIn('value="pappy"', html)
        self.assertIn('value="campbell" checked', html)
        self.assertIn('value="olivea" checked', html)
        self.assertNotIn('value="guest"', html)
        self.assertIn("data-touch-pin-pad", html)

    def test_touch_operator_manager_rejects_bad_pin_without_changes(self):
        config = {
            "admin_pin": "1234",
            "students": [{"id": "pappy", "name": "Pappy"}],
            "family_students": [
                {"id": "pappy", "name": "Pappy"},
                {"id": "campbell", "name": "Campbell"},
            ],
        }
        self.write_station_config(config)

        response = self.client.post(
            "/touch/system/operators",
            data={"admin_pin": "0000", "student_ids": "campbell"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("operator_error=admin-pin", response.headers["Location"])
        self.assertEqual(config, json.loads(app_module.STATION_CONFIG_PATH.read_text(encoding="utf-8")))
        self.assertEqual([], list(self.data_dir.glob("station_config.json.pre-roster-*")))

    def test_touch_operator_manager_rejects_empty_or_unknown_roster(self):
        config = {
            "admin_pin": "1234",
            "students": [{"id": "pappy", "name": "Pappy"}],
            "family_students": [
                {"id": "pappy", "name": "Pappy"},
                {"id": "campbell", "name": "Campbell"},
            ],
        }
        self.write_station_config(config)

        empty = self.client.post(
            "/touch/system/operators",
            data={"admin_pin": "1234"},
        )
        unknown = self.client.post(
            "/touch/system/operators",
            data={"admin_pin": "1234", "student_ids": "unknown-student"},
        )

        self.assertIn("operator_error=choose-one", empty.headers["Location"])
        self.assertIn("operator_error=invalid-selection", unknown.headers["Location"])
        self.assertEqual(config, json.loads(app_module.STATION_CONFIG_PATH.read_text(encoding="utf-8")))
        self.assertEqual([], list(self.data_dir.glob("station_config.json.pre-roster-*")))

    def test_touch_operator_manager_saves_roster_and_preserves_student_data(self):
        self.write_station_config({
            "station_id": "campbell-olivea-station",
            "admin_pin": "1234",
            "custom_setting": "preserved",
            "students": [{"id": "pappy", "name": "Pappy"}],
            "family_students": [
                {"id": "pappy", "name": "Pappy"},
                {"id": "campbell", "name": "Campbell"},
                {"id": "olivea", "name": "Olivea"},
            ],
            "guest_profile": {
                "id": "guest",
                "name": "Guest Operator",
                "guest": True,
                "disposable": True,
            },
        })
        self.write_text_file("pappy", "practice_attempts.jsonl", "saved-progress\n")

        response = self.client.post(
            "/touch/system/operators",
            data={
                "admin_pin": "1234",
                "student_ids": ["campbell", "olivea"],
            },
        )
        saved = json.loads(app_module.STATION_CONFIG_PATH.read_text(encoding="utf-8"))
        picker = self.client.get("/touch/students").get_data(as_text=True)

        self.assertEqual(302, response.status_code)
        self.assertEqual("/touch/students", response.headers["Location"])
        self.assertEqual(["campbell", "olivea"], [item["id"] for item in saved["students"]])
        self.assertEqual("preserved", saved["custom_setting"])
        self.assertEqual("1234", saved["admin_pin"])
        self.assertEqual(1, len(list(self.data_dir.glob("station_config.json.pre-roster-*"))))
        self.assertEqual(
            "saved-progress\n",
            self.student_file("pappy", "practice_attempts.jsonl").read_text(encoding="utf-8"),
        )
        self.assertTrue((self.students_dir / "campbell").is_dir())
        self.assertTrue((self.students_dir / "olivea").is_dir())
        self.assertNotIn("Pappy</strong>", picker)
        self.assertIn("Campbell</strong>", picker)
        self.assertIn("Olivea</strong>", picker)

    def test_touch_system_action_requires_admin_pin(self):
        self.write_station_config({"admin_pin": "1234"})
        called = {"restart": False}
        app_module.restart_wifi_in_background = lambda: called.__setitem__("restart", True)

        response = self.client.post(
            "/touch/system/action",
            data={"admin_pin": "0000", "action": "restart-wifi"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_error=admin-pin", response.headers["Location"])
        self.assertFalse(called["restart"])

    def test_admin_pin_lockout_after_repeated_failures(self):
        self.write_station_config({"admin_pin": "1234"})

        for _ in range(app_module.ADMIN_PIN_MAX_FAILURES):
            self.assertFalse(app_module.admin_pin_valid("0000"))

        self.assertTrue(app_module.admin_pin_locked())
        self.assertFalse(app_module.admin_pin_valid("1234"))

        app_module.admin_pin_lockout["locked_until"] = app_module.time() - 1
        self.assertTrue(app_module.admin_pin_valid("1234"))
        self.assertFalse(app_module.admin_pin_locked())

    def test_touch_system_action_starts_exit_kiosk_with_valid_pin(self):
        self.write_station_config({"admin_pin": "1234"})
        called = {"exit": False}
        app_module.exit_kiosk_in_background = lambda: called.__setitem__("exit", True)

        response = self.client.post(
            "/touch/system/action",
            data={"admin_pin": "1234", "action": "exit-kiosk"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_status=desktop-opening", response.headers["Location"])
        self.assertTrue(called["exit"])

    def test_touch_system_action_starts_keyboard_with_valid_pin(self):
        self.write_station_config({"admin_pin": "1234"})
        called = {"keyboard": False}
        app_module.launch_keyboard_in_background = lambda: called.__setitem__("keyboard", True) or True

        response = self.client.post(
            "/touch/system/action",
            data={"admin_pin": "1234", "action": "open-keyboard"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_status=keyboard-opening", response.headers["Location"])
        self.assertTrue(called["keyboard"])

    def test_touch_system_action_reports_missing_keyboard(self):
        app_module.launch_keyboard_in_background = lambda: False

        response = self.client.post(
            "/touch/system/action",
            data={"action": "open-keyboard"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_error=missing-keyboard", response.headers["Location"])

    def test_touch_system_action_starts_update_with_valid_pin(self):
        self.write_station_config({"admin_pin": "1234"})
        called = {"update": False}
        app_module.start_update_service = lambda: called.__setitem__("update", True) or True

        response = self.client.post(
            "/touch/system/action",
            data={"admin_pin": "1234", "action": "update-app"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_status=update-started", response.headers["Location"])
        self.assertTrue(called["update"])

    def test_touch_system_action_reports_update_start_failure(self):
        app_module.start_update_service = lambda: False

        response = self.client.post(
            "/touch/system/action",
            data={"action": "update-app"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_error=update-start-failed", response.headers["Location"])

    def test_touch_system_action_reports_completed_sync_with_valid_pin(self):
        self.write_station_config({"admin_pin": "1234"})
        called = {"sync": False}
        app_module.start_sync_service = lambda: called.__setitem__("sync", True) or {
            "ok": True,
            "status": "completed",
        }

        response = self.client.post(
            "/touch/system/action",
            data={"admin_pin": "1234", "action": "sync-now"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_status=sync-completed", response.headers["Location"])
        self.assertTrue(called["sync"])

    def test_touch_system_action_reports_skipped_sync_with_valid_pin(self):
        self.write_station_config({"admin_pin": "1234"})
        app_module.start_sync_service = lambda: {
            "ok": True,
            "status": "skipped",
        }

        response = self.client.post(
            "/touch/system/action",
            data={"admin_pin": "1234", "action": "sync-now"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_status=sync-skipped", response.headers["Location"])

    def test_touch_system_action_reports_sync_start_failure(self):
        app_module.start_sync_service = lambda: False

        response = self.client.post(
            "/touch/system/action",
            data={"action": "sync-now"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("system_error=sync-start-failed", response.headers["Location"])

    def test_touch_words_unlocks_after_s_o_active(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2000-01-01",
        )

        menu_response = self.client.get("/touch/practice")
        menu_html = menu_response.get_data(as_text=True)
        words_response = self.client.get("/touch/words?i=0")
        words_html = words_response.get_data(as_text=True)

        self.assertEqual(200, menu_response.status_code)
        self.assertIn('href="/touch/words"', menu_html)
        self.assertIn("known-letter words", menu_html)
        self.assertEqual(200, words_response.status_code)
        self.assertIn("<strong>AM</strong>", words_html)
        self.assertIn("0% · 0/42 words complete", words_html)
        self.assertIn('data-word-morse=".- --"', words_html)
        self.assertIn('data-word-target="AM"', words_html)
        self.assertIn('id="liveMorse"', words_html)
        self.assertIn('id="wordFeedback"', words_html)
        self.assertIn('id="touchResultBanner"', words_html)
        self.assertIn('aria-live="polite"', words_html)
        self.assertIn("data-word-clear", words_html)
        self.assertIn('/touch/words?word=ME&phase=1', words_html)
        self.assertNotIn("autoplay=1", words_html)
        self.assertIn('app.js?v=20260807-1', words_html)
        self.assertNotIn(">Read</a>", words_html)
        self.assertIn('class="morse-visual"', words_html)
        self.assertIn('aria-label="dot dash"', words_html)

    def test_touch_words_starts_with_first_unfinished_word(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2000-01-01",
        )
        self.write_word_attempts("pappy", total=1, correct=1, word="AM")

        response = self.client.get("/touch/words")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn('data-word-target="ME"', html)
        self.assertIn("2% · 1/42 words complete", html)
        self.assertIn('/touch/words?word=NOT&phase=1', html)

    def test_touch_words_completion_drops_when_d_u_adds_new_words(self):
        so_letters = app_module.starter_practice_letters + ["S", "O"]
        du_letters = so_letters + ["R", "K", "D", "U"]
        self.complete_progress("pappy", du_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                },
                "RK": {
                    "first_learning_date": "2000-01-02",
                    "letters": ["R", "K"],
                },
                "DU": {
                    "first_learning_date": "2000-01-03",
                    "letters": ["D", "U"],
                },
            },
            last_learning_start_date="2000-01-03",
        )
        so_words = app_module.available_word_practice_words(so_letters)
        path = self.student_file("pappy", "word_attempts.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        word_attempts = [
            {
                "correct": True,
                "word": word,
                "timestamp": "2026-06-21T00:00:00+00:00",
            }
            for word in so_words
        ]
        path.write_text(
            "\n".join(json.dumps(attempt, sort_keys=True) for attempt in word_attempts) + "\n",
            encoding="utf-8",
        )

        summary = app_module.word_progress_summary(du_letters, word_attempts)
        response = self.client.get("/touch/words")
        html = response.get_data(as_text=True)

        self.assertEqual(42, len(so_words))
        self.assertEqual(56, summary["available"])
        self.assertEqual(42, summary["unique_correct"])
        self.assertEqual(75, summary["completion"])
        self.assertIn("75% · 42/56 words complete", html)
        self.assertIn('data-word-target="AND"', html)

    def test_touch_words_completion_drops_when_c_w_h_l_adds_new_words(self):
        du_letters = app_module.starter_practice_letters + ["S", "O", "R", "K", "D", "U"]
        cwhl_letters = du_letters + ["C", "W", "H", "L"]
        self.complete_progress("pappy", cwhl_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                },
                "RK": {
                    "first_learning_date": "2000-01-02",
                    "letters": ["R", "K"],
                },
                "DU": {
                    "first_learning_date": "2000-01-03",
                    "letters": ["D", "U"],
                },
                "CWHL": {
                    "first_learning_date": "2000-01-04",
                    "letters": ["C", "W", "H", "L"],
                },
            },
            last_learning_start_date="2000-01-04",
        )
        du_words = app_module.available_word_practice_words(du_letters)
        path = self.student_file("pappy", "word_attempts.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        word_attempts = [
            {
                "correct": True,
                "word": word,
                "timestamp": "2026-06-21T00:00:00+00:00",
            }
            for word in du_words
        ]
        path.write_text(
            "\n".join(json.dumps(attempt, sort_keys=True) for attempt in word_attempts) + "\n",
            encoding="utf-8",
        )

        summary = app_module.word_progress_summary(cwhl_letters, word_attempts)
        response = self.client.get("/touch/words")
        html = response.get_data(as_text=True)

        self.assertEqual(56, len(du_words))
        self.assertEqual(80, summary["available"])
        self.assertEqual(56, summary["unique_correct"])
        self.assertEqual(70, summary["completion"])
        self.assertIn("70% · 56/80 words complete", html)
        self.assertIn('data-word-target="COW"', html)

    def test_desktop_practice_retry_does_not_print_raw_morse(self):
        app_module.practice_target = "A"
        app_module.get_current_key_morse = lambda: ".."

        response = self.client.post("/practice/check")

        self.assertEqual(302, response.status_code)
        self.assertEqual(
            "Good try. Clear, then follow the centered example for A. "
            "Try again and listen to the rhythm.",
            app_module.practice_feedback,
        )
        self.assertNotIn("..", app_module.practice_feedback)
        self.assertNotIn(".-", app_module.practice_feedback)

    def test_touch_words_locked_before_s_o_active(self):
        response = self.client.get("/touch/words")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Words Unlock", html)
        self.assertIn("Finish S and O", html)

    def test_touch_messages_unlocks_and_lists_eligible_recipient(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")

        menu_response = self.client.get("/touch/menu")
        messages_response = self.client.get("/touch/messages")
        compose_response = self.client.get("/touch/messages/compose")

        self.assertEqual(200, messages_response.status_code)
        self.assertIn("Messages", menu_response.get_data(as_text=True))
        self.assertIn("New Message", messages_response.get_data(as_text=True))
        self.assertIn("Astrid", compose_response.get_data(as_text=True))
        self.assertIn("8 shared signals", compose_response.get_data(as_text=True))

    def test_touch_message_draft_review_and_local_delivery(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")

        add_response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-word", "word": "ME"},
        )
        review_response = self.client.get("/touch/messages/review?to=astrid")
        send_response = self.client.post("/touch/messages/send", data={"recipient_id": "astrid"})

        self.assertEqual(302, add_response.status_code)
        review_html = review_response.get_data(as_text=True)
        self.assertIn("Review For Astrid", review_html)
        self.assertIn("Send to Astrid", review_html)
        self.assertIn('class="morse-visual"', review_html)
        self.assertIn('aria-label="dash dash"', review_html)
        self.assertEqual(302, send_response.status_code)
        self.assertIn("sent=Astrid", send_response.headers["Location"])
        self.assertEqual(1, len(list((self.students_dir / "pappy" / "message_outbox").glob("*.json"))))
        self.assertEqual(1, len(list((self.students_dir / "astrid" / "message_inbox").glob("*.json"))))

    def test_touch_message_word_bank_browses_and_appends_known_words(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")
        self.write_text_file(
            "pappy",
            "word_attempts.jsonl",
            "\n".join([
                json.dumps({
                    "correct": True,
                    "timestamp": "2026-06-21T00:00:00+00:00",
                    "word": "ME",
                }, sort_keys=True),
                json.dumps({
                    "correct": False,
                    "timestamp": "2026-06-21T00:01:00+00:00",
                    "word": "SO",
                }, sort_keys=True),
            ]) + "\n",
        )

        browse_response = self.client.get("/touch/messages/word-bank")
        choose_response = self.client.get("/touch/messages/word-bank?to=astrid")
        add_response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-word", "word": "ME"},
        )
        draft = json.loads(self.student_file("pappy", "message_draft.json").read_text(encoding="utf-8"))

        browse_html = browse_response.get_data(as_text=True)
        choose_html = choose_response.get_data(as_text=True)

        self.assertEqual(200, browse_response.status_code)
        self.assertIn("Words I Know", browse_html)
        self.assertIn("42", browse_html)
        self.assertIn("First Words", browse_html)
        self.assertIn("word-status-done", browse_html)
        self.assertIn("word-status-tried", browse_html)
        self.assertIn(">Done<", browse_html)
        self.assertIn(">Tried<", browse_html)
        self.assertEqual(200, choose_response.status_code)
        self.assertIn("Words With Astrid", choose_html)
        self.assertIn('name="action" value="append-word"', choose_html)
        self.assertIn('name="word" value="ME"', choose_html)
        self.assertEqual(302, add_response.status_code)
        self.assertEqual("ME", draft["text"])

    def test_touch_message_word_level_edit_controls_update_draft(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")
        for word in ["ME", "SO", "IN"]:
            self.client.post(
                "/touch/messages/draft",
                data={"recipient_id": "astrid", "action": "append-word", "word": word},
            )

        edit_response = self.client.get("/touch/messages/compose?to=astrid&edit_word=1")
        replace_response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "replace-word", "word_index": "1", "word": "AM"},
        )
        move_response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "move-word-left", "word_index": "2"},
        )
        delete_response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "delete-word", "word_index": "1"},
        )
        draft = json.loads(self.student_file("pappy", "message_draft.json").read_text(encoding="utf-8"))

        edit_html = edit_response.get_data(as_text=True)

        self.assertEqual(200, edit_response.status_code)
        self.assertIn("Change SO", edit_html)
        self.assertIn("Replace", edit_html)
        self.assertIn("Move Left", edit_html)
        self.assertEqual(302, replace_response.status_code)
        self.assertEqual(302, move_response.status_code)
        self.assertEqual(302, delete_response.status_code)
        self.assertEqual("ME AM", draft["text"])

    def test_cloud_enabled_message_starts_queued_and_writes_learning_summary(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")
        self.write_station_config({
            "station_id": "pappy-test-station",
            "message_sync_enabled": True,
            "students": [{"id": "pappy", "name": "Pappy"}, {"id": "astrid", "name": "Astrid"}],
            "family_students": [{"id": "pappy", "name": "Pappy"}, {"id": "astrid", "name": "Astrid"}],
        })
        self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-word", "word": "ME"},
        )

        response = self.client.post("/touch/messages/send", data={"recipient_id": "astrid"})
        messages_html = self.client.get("/touch/messages").get_data(as_text=True)
        outbox_path = next((self.students_dir / "pappy" / "message_outbox").glob("*.json"))
        message = json.loads(outbox_path.read_text(encoding="utf-8"))
        summary_path = self.data_dir / "message_sync" / "local_summaries" / "pappy.json"

        self.assertEqual(302, response.status_code)
        self.assertEqual("queued", message["cloud_state"])
        self.assertIn("Queued for delivery", messages_html)
        self.assertTrue(summary_path.exists())

    def test_touch_message_keyed_word_is_decoded_and_added_to_draft(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")

        response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-keyed-word", "morse": "-- ."},
        )
        draft = json.loads(self.student_file("pappy", "message_draft.json").read_text(encoding="utf-8"))

        self.assertEqual(302, response.status_code)
        self.assertEqual("ME", draft["text"])

        second_response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-keyed-word", "morse": "... ---"},
        )
        draft = json.loads(self.student_file("pappy", "message_draft.json").read_text(encoding="utf-8"))

        self.assertEqual(302, second_response.status_code)
        self.assertEqual("ME SO", draft["text"])

    def test_touch_message_composer_separates_word_retry_from_message_clear(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")

        response = self.client.get("/touch/messages/compose?to=astrid")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("data-message-retry-word", html)
        self.assertIn("Try Word Again", html)
        self.assertIn("Clear Message", html)

    def test_touch_message_rejects_keyed_letter_or_unknown_word(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")

        letter_response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-keyed-word", "morse": "--"},
        )
        unknown_response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-keyed-word", "morse": "......"},
        )
        draft = json.loads(self.student_file("pappy", "message_draft.json").read_text(encoding="utf-8"))

        self.assertIn("available+Words", letter_response.headers["Location"])
        self.assertIn("available+Words", unknown_response.headers["Location"])
        self.assertEqual("", draft["text"])

    def test_touch_message_undo_removes_the_last_word(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")
        self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-word", "word": "ME"},
        )
        self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-word", "word": "SO"},
        )

        response = self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "undo"},
        )
        draft = json.loads(self.student_file("pappy", "message_draft.json").read_text(encoding="utf-8"))

        self.assertEqual(302, response.status_code)
        self.assertEqual("ME", draft["text"])

    def test_touch_message_send_revalidates_tampered_draft(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")
        self.write_json(
            "pappy",
            "message_draft.json",
            {
                "format": "morsepi-message-draft-v1",
                "draft_id": "a" * 32,
                "sender_student_id": "pappy",
                "recipient_student_id": "astrid",
                "text": "MORE",
            },
        )

        response = self.client.post("/touch/messages/send", data={"recipient_id": "astrid"})

        self.assertEqual(302, response.status_code)
        self.assertIn("not+ready", response.headers["Location"])
        self.assertFalse((self.students_dir / "pappy" / "message_outbox").exists())

    def test_touch_message_decode_hides_text_and_records_effort(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")
        self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-word", "word": "ME"},
        )
        self.client.post("/touch/messages/send", data={"recipient_id": "astrid"})
        inbox_path = next((self.students_dir / "astrid" / "message_inbox").glob("*.json"))
        message_id = inbox_path.stem
        self.set_student_cookie("astrid")

        open_response = self.client.get(f"/touch/messages/inbox/{message_id}")
        open_html = open_response.get_data(as_text=True)
        first_response = self.client.post(
            f"/touch/messages/inbox/{message_id}/answer",
            data={"position": "0", "answer": "M"},
        )
        second_response = self.client.post(
            f"/touch/messages/inbox/{message_id}/answer",
            data={"position": "1", "answer": "E"},
        )
        duplicate_response = self.client.post(
            f"/touch/messages/inbox/{message_id}/answer",
            data={"position": "1", "answer": "E"},
        )
        complete_response = self.client.get(f"/touch/messages/inbox/{message_id}")

        self.assertEqual(200, open_response.status_code)
        self.assertNotIn("You decoded ME", open_html)
        self.assertIn("__", open_html)
        self.assertEqual(302, first_response.status_code)
        self.assertEqual(302, second_response.status_code)
        self.assertEqual(302, duplicate_response.status_code)
        complete_html = complete_response.get_data(as_text=True)
        self.assertIn("You decoded ME", complete_html)
        events = (self.students_dir / "astrid" / "message_events.jsonl").read_text(encoding="utf-8")
        self.assertEqual(2, events.count('"event": "decode_attempt"'))
        self.assertEqual(1, self.daily_celebration_count)
        sender_copy = json.loads(next((self.students_dir / "pappy" / "message_outbox").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual("decoded", sender_copy["state"])

    def test_touch_message_playback_uses_station_output(self):
        self.unlock_messages("pappy")
        self.unlock_messages("astrid")
        self.client.post(
            "/touch/messages/draft",
            data={"recipient_id": "astrid", "action": "append-word", "word": "ME"},
        )
        self.client.post("/touch/messages/send", data={"recipient_id": "astrid"})
        message_id = next((self.students_dir / "astrid" / "message_inbox").glob("*.json")).stem
        self.set_student_cookie("astrid")
        played = []
        original_play = app_module.play_in_background
        app_module.play_in_background = lambda morse: played.append(morse)
        try:
            response = self.client.post(
                f"/touch/messages/inbox/{message_id}/play",
                data={"scope": "message"},
            )
        finally:
            app_module.play_in_background = original_play

        self.assertEqual(200, response.status_code)
        self.assertEqual(["-- ."], played)

    def test_touch_progress_shows_message_badges_from_events(self):
        self.unlock_messages("pappy")
        self.write_text_file(
            "pappy",
            "message_events.jsonl",
            json.dumps({"event": "message_sent", "timestamp": "2026-08-02T12:00:00+00:00"}) + "\n"
            + json.dumps({"event": "decode_attempt", "completed": True, "timestamp": "2026-08-02T12:01:00+00:00"}) + "\n",
        )

        response = self.client.get("/touch/progress")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("First Message Sent", html)
        self.assertIn("Secret Message Decoded", html)

    def test_guest_cannot_open_family_messages(self):
        student_profiles.save_profiles(
            [
                {"id": "pappy", "name": "Pappy"},
                {"id": "astrid", "name": "Astrid"},
                {"id": "guest", "name": "Guest Operator", "guest": True, "disposable": True},
            ]
        )
        self.set_student_cookie("guest")

        response = self.client.get("/touch/messages")

        self.assertEqual(302, response.status_code)
        self.assertEqual("/touch/daily", response.headers["Location"])

    def test_word_station_prompt_plays_and_stops_station_output(self):
        played = []
        stopped = []
        original_play = app_module.play_in_background
        original_stop = app_module.stop_station_playback
        app_module.play_in_background = lambda morse: played.append(morse)
        app_module.stop_station_playback = lambda: stopped.append(True)

        try:
            play_response = self.client.post("/words/prompt-station", json={"morse": ".- --"})
            stop_response = self.client.post("/words/stop")
        finally:
            app_module.play_in_background = original_play
            app_module.stop_station_playback = original_stop

        self.assertEqual(200, play_response.status_code)
        self.assertEqual({"status": "playing"}, play_response.get_json())
        self.assertEqual([".- --"], played)
        self.assertEqual(200, stop_response.status_code)
        self.assertEqual({"status": "stopped"}, stop_response.get_json())
        self.assertEqual([True], stopped)

    def test_word_result_records_attempt_without_practice_progress(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2000-01-01",
        )

        response = self.client.post(
            "/words/result",
            json={
                "word": "AM",
                "correct": True,
                "expected_morse": ".- --",
                "actual_morse": ".- --",
                "decoded": "AM",
                "elapsed_ms": 2400,
                "timing_events": [
                    {"type": "symbol", "symbol": ".", "duration_ms": 100},
                    {"type": "gap", "gap_type": "symbol", "duration_ms": 100},
                    {"type": "symbol", "symbol": "-", "duration_ms": 310},
                    {"type": "gap", "gap_type": "letter", "duration_ms": 320},
                    {"type": "symbol", "symbol": "-", "duration_ms": 310},
                    {"type": "gap", "gap_type": "symbol", "duration_ms": 100},
                    {"type": "symbol", "symbol": "-", "duration_ms": 310},
                ],
            },
        )
        payload = response.get_json()
        word_attempts = self.student_file("pappy", "word_attempts.jsonl").read_text(encoding="utf-8").splitlines()
        word_record = json.loads(word_attempts[0])

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", payload["status"])
        self.assertEqual("AM", payload["attempt"]["word"])
        self.assertEqual(2400, payload["attempt"]["elapsed_ms"])
        self.assertTrue(payload["attempt"]["correct"])
        self.assertEqual(32, len(payload["attempt"]["attempt_id"]))
        self.assertEqual(32, len(word_record["attempt_id"]))
        self.assertEqual("AM", word_record["decoded"])
        self.assertEqual(4, word_record["timing_summary"]["symbol_count"])
        self.assertEqual("Great rhythm.", payload["rhythm"]["message"])
        self.assertTrue(payload["rhythm"]["target"])
        self.assertTrue(payload["rhythm"]["actual"])
        self.assertFalse(self.student_file("pappy", "practice_attempts.jsonl").exists())

    def test_word_result_recomputes_correctness_server_side(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2000-01-01",
        )

        response = self.client.post(
            "/words/result",
            json={
                "word": "AM",
                "correct": True,
                "expected_morse": ".- --",
                "actual_morse": ".",
                "decoded": "AM",
            },
        )
        payload = response.get_json()

        self.assertEqual(200, response.status_code)
        self.assertFalse(payload["attempt"]["correct"])
        self.assertEqual(".- --", payload["attempt"]["expected_morse"])
        self.assertEqual(".", payload["attempt"]["actual_morse"])
        self.assertEqual("E", payload["attempt"]["decoded"])

    def test_touch_student_selection_defaults_to_daily(self):
        response = self.client.get("/touch/students")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn('name="next" value="/touch/daily"', html)

    def test_touch_student_selection_uses_station_roster_and_hides_add(self):
        self.write_station_config({
            "station_id": "astrid-liara-station",
            "allow_student_create": False,
            "students": [
                {"id": "astrid", "name": "Astrid"},
                {"id": "liara", "name": "Liara"},
            ],
            "guest_profile": {
                "id": "guest",
                "name": "Guest Operator",
                "guest": True,
                "disposable": True,
            },
        })

        response = self.client.get("/touch/students")
        html = response.get_data(as_text=True)
        profiles = student_profiles.load_profiles()
        profile_ids = {profile["id"] for profile in profiles}
        guest = next(profile for profile in profiles if profile["id"] == "guest")

        self.assertEqual(200, response.status_code)
        self.assertIn("Astrid", html)
        self.assertIn("Liara", html)
        self.assertIn("Guest Operator", html)
        self.assertNotIn("Pappy</strong>", html)
        self.assertNotIn('name="action" value="create"', html)
        self.assertIn("liara", profile_ids)
        self.assertIn("guest", profile_ids)
        self.assertTrue(guest["disposable"])
        self.assertTrue(guest["guest"])

    def test_touch_student_selection_redirects_to_daily_after_select(self):
        response = self.client.post(
            "/touch/students",
            data={"action": "select", "student_id": "astrid"},
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual("/touch/daily", response.headers["Location"])

    def test_station_roster_blocks_student_creation(self):
        self.write_station_config({
            "station_id": "astrid-liara-station",
            "allow_student_create": False,
            "students": [
                {"id": "astrid", "name": "Astrid"},
                {"id": "liara", "name": "Liara"},
            ],
        })

        response = self.client.post(
            "/students",
            data={
                "action": "create",
                "student_name": "New Student",
            },
        )
        profile_ids = {profile["id"] for profile in student_profiles.load_profiles()}

        self.assertEqual(302, response.status_code)
        self.assertIn("reset_error=create-disabled", response.headers["Location"])
        self.assertNotIn("new-student", profile_ids)

    def test_guest_attempts_are_marked_disposable(self):
        self.write_station_config({
            "station_id": "pappy-station",
            "students": [
                {"id": "pappy", "name": "Pappy"},
            ],
            "guest_profile": {
                "id": "guest",
                "name": "Guest Operator",
                "guest": True,
                "disposable": True,
            },
        })
        self.set_student_cookie("guest")

        response = self.client.post(
            "/practice/result",
            json={
                "mode": "send",
                "target": "E",
                "actual_morse": ".",
            },
        )
        payload = response.get_json()

        self.assertEqual(200, response.status_code)
        self.assertTrue(payload["attempt"]["student_disposable"])
        self.assertEqual("guest", payload["attempt"]["student_id"])

    def test_guest_cannot_use_message_routes(self):
        played = []
        original_play = app_module.play_in_background
        app_module.play_in_background = lambda morse: played.append(morse)
        self.write_station_config({
            "station_id": "pappy-station",
            "students": [
                {"id": "pappy", "name": "Pappy"},
            ],
            "guest_profile": {
                "id": "guest",
                "name": "Guest Operator",
                "guest": True,
                "disposable": True,
            },
        })
        self.set_student_cookie("guest")

        try:
            home_response = self.client.post("/", data={"message": "HI"})
            touch_response = self.client.get("/touch/message")
            play_response = self.client.post("/play", data={"next": "/"})
        finally:
            app_module.play_in_background = original_play

        home_html = home_response.get_data(as_text=True)
        self.assertEqual(200, home_response.status_code)
        self.assertIn("Guest can practice Morse", home_html)
        self.assertNotIn(".... ..", home_html)
        self.assertEqual(302, touch_response.status_code)
        self.assertEqual("/touch/daily", touch_response.headers["Location"])
        self.assertEqual(302, play_response.status_code)
        self.assertEqual("/", play_response.headers["Location"])
        self.assertEqual([], played)

    def test_touch_daily_fresh_student_shows_no_learning_now(self):
        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("6/26", html)
        self.assertIn("Learning Now", html)
        self.assertIn("<strong>None</strong>", html)
        self.assertNotIn("New: S O", html)
        self.assertNotIn("Learn S O", html)

    def test_touch_daily_recommends_warmup_after_practice_gap(self):
        path = self.student_file("pappy", "practice_attempts.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "correct": True,
                    "target": "E",
                    "mode": "send",
                    "timestamp": "2026-08-10T12:00:00+00:00",
                },
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Warm Up First", html)
        self.assertIn("/touch/practice/run?mode=warmup", html)
        self.assertIn("Warm up with letters you already know", html)

    def test_touch_daily_stops_recommending_warmup_after_review_goal(self):
        path = self.student_file("pappy", "practice_attempts.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        attempts = [
            {
                "correct": True,
                "target": "E",
                "mode": "send",
                "timestamp": "2026-08-10T12:00:00+00:00",
            }
        ]
        attempts.extend(
            {
                "correct": True,
                "target": "E",
                "mode": "warmup",
                "review_only": True,
                "timestamp": f"{app_module.today_key()}T00:{index:02d}:00+00:00",
            }
            for index in range(app_module.warmup_review_goal)
        )
        path.write_text(
            "\n".join(json.dumps(attempt, sort_keys=True) for attempt in attempts) + "\n",
            encoding="utf-8",
        )

        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertNotIn("Warm Up First", html)
        self.assertNotIn("/touch/practice/run?mode=warmup", html)

    def test_touch_daily_prioritizes_learning_now_next_step(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        progress = {}
        for letter in active_letters:
            progress[letter] = {
                mode: {
                    "attempts": 10,
                    "correct": 10,
                    "last_seen": "2026-06-23T00:00:00+00:00",
                    "streak": 10,
                    "strength": 1.0,
                }
                for mode in app_module.practice_modes
            }
        progress["R"] = {
            "learn": {
                "attempts": 7,
                "correct": 7,
                "last_seen": "2026-06-23T00:00:00+00:00",
                "streak": 7,
                "strength": 1.0,
            }
        }
        progress["K"] = {
            "learn": {
                "attempts": 9,
                "correct": 9,
                "last_seen": "2026-06-23T00:00:00+00:00",
                "streak": 5,
                "strength": 1.0,
            }
        }
        self.write_json("pappy", "practice_progress.json", progress)
        self.write_json(
            "pappy",
            "learning_state.json",
            {
                "groups": {
                    "SO": {
                        "first_learning_date": "2026-06-20",
                        "letters": ["S", "O"],
                    }
                },
                "last_learning_start_date": "2026-06-20",
            },
        )
        self.write_word_attempts("pappy", total=app_module.word_ready_correct_attempts, correct=app_module.word_ready_correct_attempts)

        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Next Step", html)
        self.assertIn("Learn R K", html)
        self.assertIn("R needs 3 more correct Learn tries", html)
        self.assertIn("4 Learn left", html)
        self.assertIn("R 7/10", html)
        self.assertIn("K 9/10", html)
        self.assertIn("R K are not in Send, Read, Listen, or Echo yet.", html)
        self.assertIn("Progress So Far", html)
        self.assertIn("100%</strong> current-set mastery", html)

    def test_touch_daily_summarizes_long_letter_sets(self):
        self.complete_progress("pappy", app_module.alphabet_letters)
        self.set_learning_state(
            "pappy",
            {
                app_module.step_key(step): {
                    "first_learning_date": "2000-01-01",
                    "letters": step["letters"],
                }
                for step in app_module.letter_unlock_steps
                if all(letter.isalpha() for letter in step["letters"])
            },
            last_learning_start_date="2000-01-01",
        )
        self.write_text_file(
            "pappy",
            "practice_attempts.jsonl",
            "\n".join(
                json.dumps(
                    {
                        "correct": True,
                        "target": letter,
                        "mode": "send",
                        "timestamp": f"{app_module.today_key()}T00:00:00+00:00",
                    },
                    sort_keys=True,
                )
                for letter in app_module.alphabet_letters
            )
            + "\n",
        )

        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("9 min", html)
        self.assertIn("<strong>+14</strong>", html)
        self.assertIn("<strong>+18</strong>", html)

    def test_touch_progress_renders_letters_mastered_and_current_set(self):
        response = self.client.get("/touch/progress")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("6/26 letters mastered", html)
        self.assertIn("current set", html)
        self.assertIn("Words", html)
        self.assertIn("Unlock after S O", html)
        self.assertNotIn("% overall", html)

    def test_touch_progress_renders_words_progress_when_unlocked(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2000-01-01",
        )
        self.write_word_attempts("pappy", total=24, correct=19, word="AM")

        response = self.client.get("/touch/progress")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Words", html)
        self.assertIn("2%", html)
        self.assertIn("1/42 words complete", html)
        self.assertNotIn("19/24 correct", html)

    def test_touch_progress_renders_badges_and_next_badge(self):
        self.complete_progress("pappy", app_module.all_practice_letters)
        self.set_learning_state(
            "pappy",
            {
                "".join(step["letters"]): {
                    "first_learning_date": "2000-01-01",
                    "letters": step["letters"],
                }
                for step in app_module.letter_unlock_steps
            },
            last_learning_start_date="2000-01-01",
        )
        self.write_attempts("pappy", total=20, correct=19)
        self.write_word_attempts("pappy", total=3, correct=3, timestamp=f"{app_module.today_key()}T00:00:00+00:00")

        response = self.client.get("/touch/progress")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Daily Signal Complete", html)
        self.assertIn("Clean Copy", html)
        self.assertIn("First Signals Mastered", html)
        self.assertIn("practice time", html)
        self.assertIn("Next badge: Try Again Champ", html)

    def test_touch_progress_shows_learning_now_progress_separate_from_current_set(self):
        self.complete_starter_progress("pappy")
        progress_path = self.student_file("pappy", "practice_progress.json")
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        progress["S"] = {
            "learn": {
                "attempts": 7,
                "correct": 7,
                "last_seen": "2026-06-21T00:00:00+00:00",
                "streak": 7,
                "strength": 1.0,
            }
        }
        progress["O"] = {
            "learn": {
                "attempts": 7,
                "correct": 7,
                "last_seen": "2026-06-21T00:00:00+00:00",
                "streak": 2,
                "strength": 1.0,
            }
        }
        progress_path.write_text(json.dumps(progress), encoding="utf-8")
        self.write_json(
            "pappy",
            "learning_state.json",
            {
                "groups": {
                    "SO": {
                        "first_learning_date": app_module.today_key(),
                        "letters": ["S", "O"],
                    }
                },
                "last_learning_start_date": app_module.today_key(),
            },
        )

        response = self.client.get("/touch/progress")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("70% Learning Now", html)
        self.assertIn("Learning S O", html)
        self.assertIn("14/20 Learn", html)
        self.assertIn("Current set is 100%, but S O are still Learn-only.", html)
        self.assertIn("S O are not in Send, Read, Listen, or Echo yet.", html)

    def test_touch_learn_score_uses_learning_now_burn_in_not_strength_only(self):
        completed_letters = app_module.starter_practice_letters + ["S", "O", "R", "K"]
        self.complete_progress("pappy", completed_letters)
        progress_path = self.student_file("pappy", "practice_progress.json")
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        progress["D"] = {
            "learn": {
                "attempts": 6,
                "correct": 6,
                "last_seen": "2026-06-21T00:00:00+00:00",
                "streak": 6,
                "strength": 1.0,
            }
        }
        progress["U"] = {
            "learn": {
                "attempts": 8,
                "correct": 7,
                "last_seen": "2026-06-21T00:00:00+00:00",
                "streak": 7,
                "strength": 1.0,
            }
        }
        progress_path.write_text(json.dumps(progress), encoding="utf-8")
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2026-06-20",
                    "letters": ["S", "O"],
                },
                "RK": {
                    "first_learning_date": "2026-06-22",
                    "letters": ["R", "K"],
                },
                "DU": {
                    "first_learning_date": "2026-06-25",
                    "letters": ["D", "U"],
                }
            },
            last_learning_start_date="2026-06-25",
        )

        response = self.client.get("/touch/practice/run?mode=learn")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("65%</strong>", html)
        self.assertIn("Learning Now", html)
        self.assertIn("13/20", html)
        self.assertIn("D needs 4 more correct Learn tries", html)
        self.assertNotIn("Mode complete. Go to Daily for the next step.", html)

        result = self.client.post(
            "/practice/result",
            json={
                "mode": "learn",
                "target": "D",
                "actual_morse": "-..",
            },
        )
        payload = result.get_json()

        self.assertEqual(200, result.status_code)
        self.assertEqual("recorded", payload["status"])
        self.assertEqual(70, payload["score"]["mastery"])
        self.assertEqual("14/20 Learn", payload["score"]["completion_label"])
        self.assertEqual("D needs 3 more correct Learn tries", payload["score"]["next_goal"])

    def test_touch_learn_does_not_show_next_letters_before_gate(self):
        response = self.client.get("/touch/practice/run?mode=learn")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("6/26", html)
        self.assertNotIn("New: S O", html)
        self.assertNotIn("Learn S O", html)

    def test_touch_practice_has_direct_daily_navigation(self):
        response = self.client.get("/touch/practice/run?mode=echo")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn('href="/touch/daily">Daily</a>', html)
        self.assertIn('href="/touch/practice">Modes</a>', html)
        self.assertIn('id="touchResultBanner"', html)
        self.assertIn('role="status"', html)

    def test_touch_practice_mastered_mode_points_back_to_daily(self):
        self.complete_starter_progress("pappy")
        self.set_learning_state("pappy", {}, last_learning_start_date=app_module.today_key())

        response = self.client.get("/touch/practice/run?mode=echo")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("100%</strong>", html)
        self.assertIn("Mode complete. Go to Daily for the next step.", html)

    def test_render_keeps_started_learning_now_state(self):
        self.write_json(
            "pappy",
            "learning_state.json",
            {
                "groups": {
                    "SO": {
                        "first_learning_date": "2026-06-21",
                        "letters": ["S", "O"],
                    }
                },
                "last_learning_start_date": "2026-06-21",
            },
        )

        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)
        saved_state = json.loads(self.student_file("pappy", "learning_state.json").read_text(encoding="utf-8"))

        self.assertEqual(200, response.status_code)
        self.assertIn("<strong>S O</strong>", html)
        self.assertIn("Learn S O", html)
        self.assertEqual(["S", "O"], saved_state["groups"]["SO"]["letters"])
        self.assertEqual("2026-06-21", saved_state["last_learning_start_date"])

    def test_practice_next_mixes_review_and_learning_now_letters_for_learn_mode(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.write_word_attempts("pappy", total=app_module.word_ready_correct_attempts, correct=app_module.word_ready_correct_attempts)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2026-06-20",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2026-06-20",
        )

        with patch.object(app_module.random, "random", return_value=0.8):
            review_response = self.client.post("/practice/next?mode=learn")
        review_payload = review_response.get_json()

        with patch.object(app_module.random, "random", return_value=0.2):
            learning_response = self.client.post("/practice/next?mode=learn")
        learning_payload = learning_response.get_json()

        self.assertEqual(200, review_response.status_code)
        self.assertEqual("learn", review_payload["mode"])
        self.assertIn(review_payload["target"], active_letters)
        self.assertEqual(active_letters + ["R", "K"], [item["letter"] for item in review_payload["progress"]])
        self.assertEqual(["R", "K"], review_payload["overall"]["learning_letters"])

        self.assertEqual(200, learning_response.status_code)
        self.assertEqual("learn", learning_payload["mode"])
        self.assertIn(learning_payload["target"], ["R", "K"])
        self.assertEqual(active_letters + ["R", "K"], [item["letter"] for item in learning_payload["progress"]])
        self.assertEqual(["R", "K"], learning_payload["overall"]["learning_letters"])

    def test_practice_next_keeps_send_on_current_set_when_learning_now_exists(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2026-06-20",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2026-06-20",
        )

        response = self.client.post("/practice/next?mode=send")
        payload = response.get_json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("send", payload["mode"])
        self.assertIn(payload["target"], active_letters)
        self.assertNotIn(payload["target"], ["R", "K"])
        self.assertEqual(active_letters, [item["letter"] for item in payload["progress"]])

    def test_practice_retry_replaces_target_not_available_in_mode(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2026-06-20",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2026-06-20",
        )
        app_module.practice_target = "R"

        response = self.client.post("/practice/retry?mode=send")
        payload = response.get_json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("send", payload["mode"])
        self.assertIn(payload["target"], active_letters)
        self.assertNotEqual("R", payload["target"])

    def test_practice_result_records_attempt_and_progress_for_active_letter(self):
        self.write_station_config({"station_id": "pappy-station"})
        self.set_practice_session_cookie("0123456789abcdef0123456789abcdef")

        response = self.client.post(
            "/practice/result",
            json={
                "mode": "send",
                "target": "E",
                "correct": True,
                "expected_morse": ".",
                "actual_morse": ".",
                "timing_events": [
                    {"type": "symbol", "symbol": ".", "duration_ms": 110}
                ],
            },
        )
        payload = response.get_json()
        progress = json.loads(self.student_file("pappy", "practice_progress.json").read_text(encoding="utf-8"))
        attempts = self.student_file("pappy", "practice_attempts.jsonl").read_text(encoding="utf-8").splitlines()
        attempt_record = json.loads(attempts[0])

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", payload["status"])
        self.assertEqual("E", payload["attempt"]["target"])
        self.assertTrue(payload["attempt"]["correct"])
        self.assertEqual("pappy-station", payload["attempt"]["station_id"])
        self.assertEqual("pappy", payload["attempt"]["student_id"])
        self.assertEqual("0123456789abcdef0123456789abcdef", payload["attempt"]["practice_session_id"])
        self.assertEqual(32, len(payload["attempt"]["attempt_id"]))
        self.assertEqual(1, progress["E"]["send"]["attempts"])
        self.assertEqual(1, progress["E"]["send"]["correct"])
        self.assertEqual("E", attempt_record["target"])
        self.assertEqual("pappy-station", attempt_record["station_id"])
        self.assertEqual("pappy", attempt_record["student_id"])
        self.assertEqual("0123456789abcdef0123456789abcdef", attempt_record["practice_session_id"])
        self.assertEqual(32, len(attempt_record["attempt_id"]))
        self.assertEqual(110, attempt_record["timing_summary"]["avg_dot_ms"])
        self.assertIsNone(attempt_record["timing_summary"]["avg_dash_ms"])
        self.assertEqual(1, attempt_record["timing_summary"]["dot_count"])
        self.assertEqual(0, attempt_record["timing_summary"]["gap_count"])
        self.assertIn("overall_rhythm_score", attempt_record["timing_summary"])
        self.assertIn("primary_rhythm_feedback", attempt_record["timing_summary"])

    def test_warmup_result_records_review_without_changing_mastery_progress(self):
        self.write_station_config({"station_id": "pappy-station"})
        self.write_json(
            "pappy",
            "practice_progress.json",
            {
                "E": {
                    "send": {
                        "attempts": 4,
                        "correct": 4,
                        "last_seen": "2026-08-10T12:00:00+00:00",
                        "streak": 4,
                        "strength": 0.8,
                    }
                }
            },
        )

        response = self.client.post(
            "/practice/result",
            json={
                "mode": "warmup",
                "target": "E",
                "expected_morse": ".",
                "actual_morse": ".",
                "timing_events": [
                    {"type": "symbol", "symbol": ".", "duration_ms": 100}
                ],
            },
        )
        payload = response.get_json()
        progress = json.loads(self.student_file("pappy", "practice_progress.json").read_text(encoding="utf-8"))
        attempts = self.student_file("pappy", "practice_attempts.jsonl").read_text(encoding="utf-8").splitlines()
        attempt_record = json.loads(attempts[0])

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", payload["status"])
        self.assertEqual("warmup", payload["attempt"]["mode"])
        self.assertTrue(payload["attempt"]["review_only"])
        self.assertEqual(10, payload["score"]["mastery"])
        self.assertEqual(4, progress["E"]["send"]["attempts"])
        self.assertNotIn("warmup", progress["E"])
        self.assertEqual("warmup", attempt_record["mode"])

    def test_practice_result_recomputes_keyed_correctness_server_side(self):
        response = self.client.post(
            "/practice/result",
            json={
                "mode": "send",
                "target": "T",
                "correct": True,
                "expected_morse": "-",
                "actual_morse": ".",
            },
        )
        payload = response.get_json()
        progress = json.loads(self.student_file("pappy", "practice_progress.json").read_text(encoding="utf-8"))

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", payload["status"])
        self.assertFalse(payload["attempt"]["correct"])
        self.assertEqual("-", payload["attempt"]["expected_morse"])
        self.assertEqual(".", payload["attempt"]["actual_morse"])
        self.assertEqual(1, progress["T"]["send"]["attempts"])
        self.assertEqual(0, progress["T"]["send"]["correct"])

    def test_practice_result_recomputes_read_answer_server_side(self):
        response = self.client.post(
            "/practice/result",
            json={
                "mode": "read",
                "target": "E",
                "correct": True,
                "answer": "T",
            },
        )
        payload = response.get_json()
        progress = json.loads(self.student_file("pappy", "practice_progress.json").read_text(encoding="utf-8"))

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", payload["status"])
        self.assertFalse(payload["attempt"]["correct"])
        self.assertEqual("T", payload["attempt"]["answer"])
        self.assertEqual("", payload["attempt"]["actual_morse"])
        self.assertEqual(1, progress["E"]["read"]["attempts"])
        self.assertEqual(0, progress["E"]["read"]["correct"])

    def test_practice_result_ignores_learning_now_letter_in_send_mode(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.complete_progress("pappy", active_letters)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": "2026-06-20",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2026-06-20",
        )

        response = self.client.post(
            "/practice/result",
            json={
                "mode": "send",
                "target": "R",
                "correct": True,
                "expected_morse": ".-.",
                "actual_morse": ".-.",
            },
        )
        payload = response.get_json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("ignored", payload["status"])
        self.assertFalse(self.student_file("pappy", "practice_attempts.jsonl").exists())

    def test_daily_celebrate_blocks_before_completion(self):
        response = self.client.post("/touch/daily/celebrate")

        self.assertEqual(409, response.status_code)
        self.assertFalse(self.daily_celebration_called)
        self.assertEqual({"status": "not-complete"}, response.get_json())

    def test_daily_celebrate_runs_after_twenty_attempts(self):
        self.write_attempts("pappy", total=20, correct=17)

        response = self.client.post("/touch/daily/celebrate")

        self.assertEqual(200, response.status_code)
        self.assertTrue(self.daily_celebration_called)
        self.assertEqual({"status": "celebrating"}, response.get_json())

    def test_touch_daily_complete_links_to_signal_sprint(self):
        self.write_attempts("pappy", total=20, correct=18)
        self.write_word_attempts("pappy", total=3, correct=3, timestamp=f"{app_module.today_key()}T00:00:00+00:00")
        self.complete_progress("pappy", app_module.all_practice_letters)
        self.set_learning_state(
            "pappy",
            {
                "".join(step["letters"]): {
                    "first_learning_date": "2000-01-01",
                    "letters": step["letters"],
                }
                for step in app_module.letter_unlock_steps
            },
            last_learning_start_date="2000-01-01",
        )

        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Bonus Round", html)
        self.assertIn("/touch/bonus/sprint", html)
        self.assertIn("Signal Sprint", html)

    def test_touch_daily_complete_with_learning_now_short_break_instead_of_bonus(self):
        self.write_attempts("pappy", total=20, correct=18)
        progress = {}

        for letter in app_module.starter_practice_letters:
            progress[letter] = {
                mode: {
                    "attempts": 10,
                    "correct": 10,
                    "last_seen": "2026-06-21T00:00:00+00:00",
                    "streak": 10,
                    "strength": 1.0,
                }
                for mode in app_module.practice_modes
            }

        for letter in ["S", "O"]:
            progress[letter] = {
                "learn": {
                    "attempts": 10,
                    "correct": 10,
                    "last_seen": "2026-06-21T00:00:00+00:00",
                    "streak": 10,
                    "strength": 1.0,
                }
            }

        self.write_json("pappy", "practice_progress.json", progress)
        self.set_learning_state(
            "pappy",
            {
                "SO": {
                    "first_learning_date": app_module.today_key(),
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date=app_module.today_key(),
        )

        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Take A Break", html)
        self.assertIn("Daily complete. Take a short break", html)
        self.assertNotIn("Bonus Round", html)

    def test_touch_daily_signal_goal_points_to_words_when_words_are_unfinished(self):
        self.set_student_cookie("astrid")
        self.write_attempts("astrid", total=20, correct=17)
        progress = {}

        for letter in app_module.starter_practice_letters:
            progress[letter] = {
                mode: {
                    "attempts": 10,
                    "correct": 10,
                    "last_seen": "2026-06-21T00:00:00+00:00",
                    "streak": 10,
                    "strength": 1.0,
                }
                for mode in app_module.practice_modes
            }

        for letter in ["S", "O"]:
            progress[letter] = {
                "learn": {
                    "attempts": 10,
                    "correct": 10,
                    "last_seen": "2026-06-21T00:00:00+00:00",
                    "streak": 10,
                    "strength": 1.0,
                }
            }

        self.write_json("astrid", "practice_progress.json", progress)
        self.set_learning_state(
            "astrid",
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2000-01-01",
        )

        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Daily mission: 3 correct Words left.", html)
        self.assertIn("/touch/words", html)
        self.assertNotIn("autoplay=1", html)
        self.assertNotIn("Bonus Round", html)
        self.assertIn("8/26", html)

    def test_touch_bonus_sprint_renders_active_letter_keying_round(self):
        response = self.client.get("/touch/bonus/sprint?session=test-session")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Signal Sprint", html)
        self.assertIn('data-bonus-kind="signal-sprint"', html)
        self.assertIn('data-bonus-session="test-session"', html)
        self.assertIn('id="bonusAttempts">0</span>/20 signals', html)
        self.assertIn('id="touchResultBanner"', html)

    def test_bonus_result_records_without_changing_practice_progress(self):
        response = self.client.post(
            "/bonus/result",
            json={
                "session_id": "sprint-1",
                "target": "E",
                "correct": True,
                "expected_morse": ".",
                "actual_morse": ".",
                "timing_events": [
                    {"type": "symbol", "symbol": ".", "duration_ms": 120}
                ],
            },
        )
        payload = response.get_json()
        bonus_attempts = self.student_file("pappy", "bonus_attempts.jsonl").read_text(encoding="utf-8").splitlines()
        bonus_record = json.loads(bonus_attempts[0])

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", payload["status"])
        self.assertEqual(1, payload["bonus"]["attempts"])
        self.assertEqual(100, payload["bonus"]["accuracy"])
        self.assertEqual(1, payload["bonus"]["streak"])
        self.assertEqual(32, len(payload["attempt"]["attempt_id"]))
        self.assertEqual(32, len(bonus_record["attempt_id"]))
        self.assertEqual("sprint-1", bonus_record["session_id"])
        self.assertIn("timing_summary", bonus_record)
        self.assertEqual(1, bonus_record["timing_summary"]["dot_count"])
        self.assertEqual(1, bonus_record["timing_summary"]["symbol_count"])
        self.assertFalse(self.student_file("pappy", "practice_progress.json").exists())
        self.assertFalse(self.student_file("pappy", "practice_attempts.jsonl").exists())

    def test_bonus_result_recomputes_correctness_server_side(self):
        response = self.client.post(
            "/bonus/result",
            json={
                "session_id": "sprint-1",
                "target": "T",
                "correct": True,
                "expected_morse": "-",
                "actual_morse": ".",
            },
        )
        payload = response.get_json()
        bonus_attempts = self.student_file("pappy", "bonus_attempts.jsonl").read_text(encoding="utf-8").splitlines()
        bonus_record = json.loads(bonus_attempts[0])

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", payload["status"])
        self.assertFalse(payload["attempt"]["correct"])
        self.assertEqual(0, payload["bonus"]["accuracy"])
        self.assertFalse(bonus_record["correct"])

    def test_student_cookie_keeps_progress_separate(self):
        self.complete_starter_progress("astrid")
        self.set_student_cookie("astrid")

        astrid_response = self.client.get("/touch/daily")
        astrid_html = astrid_response.get_data(as_text=True)

        self.set_student_cookie("pappy")
        pappy_response = self.client.get("/touch/daily")
        pappy_html = pappy_response.get_data(as_text=True)

        self.assertIn("Astrid", astrid_html)
        self.assertIn("Next Step", astrid_html)
        self.assertIn("Learn S O", astrid_html)
        self.assertIn("20 Learn left", astrid_html)
        self.assertIn("S O are not in Send, Read, Listen, or Echo yet.", astrid_html)
        self.assertIn("6/26", pappy_html)
        self.assertNotIn("Learn S O", pappy_html)

    def test_reset_requires_confirmation(self):
        self.write_text_file("pappy", "practice_attempts.jsonl", "pappy data\n")

        response = self.client.post(
            "/students",
            data={
                "action": "reset",
                "student_id": "pappy",
                "reset_confirm": "nope",
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("reset_error=type-reset", response.headers["Location"])
        self.assertTrue(self.student_file("pappy", "practice_attempts.jsonl").exists())

    def test_reset_requires_admin_pin_when_configured(self):
        self.write_station_config({"admin_pin": "1234"})
        self.write_text_file("pappy", "practice_attempts.jsonl", "pappy data\n")

        response = self.client.post(
            "/students",
            data={
                "action": "reset",
                "student_id": "pappy",
                "reset_confirm": "RESET",
                "admin_pin": "9999",
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("reset_error=admin-pin", response.headers["Location"])
        self.assertTrue(self.student_file("pappy", "practice_attempts.jsonl").exists())

    def test_add_student_requires_admin_pin_and_reserves_family_identity(self):
        self.write_station_config({"admin_pin": "1234"})

        denied = self.client.post(
            "/students",
            data={
                "action": "create",
                "student_name": "Campbell",
                "admin_pin": "9999",
            },
        )
        allowed = self.client.post(
            "/students",
            data={
                "action": "create",
                "student_name": "Campbell",
                "admin_pin": "1234",
            },
        )
        profiles = student_profiles.load_profiles()

        self.assertEqual(302, denied.status_code)
        self.assertIn("reset_error=admin-pin", denied.headers["Location"])
        self.assertEqual(302, allowed.status_code)
        created = next(profile for profile in profiles if profile["id"] == "campbell-2")
        self.assertNotEqual(
            student_identity.student_uuid_for_id("campbell"),
            created.get("student_uuid"),
        )

    def test_settings_require_admin_pin_when_configured(self):
        self.write_station_config({"admin_pin": "1234"})

        denied_volume = self.client.post(
            "/station-volume",
            data={
                "station_volume": "10",
                "admin_pin": "9999",
            },
        )
        allowed_volume = self.client.post(
            "/station-volume",
            data={
                "station_volume": "15",
                "admin_pin": "1234",
                "next": "/touch/timing",
            },
        )
        allowed_timing = self.client.post(
            "/timing-settings",
            data={
                "character_wpm": "10",
                "effective_wpm": "5",
                "tone_hz": "600",
                "admin_pin": "1234",
            },
        )

        self.assertEqual(403, denied_volume.status_code)
        self.assertEqual(302, allowed_volume.status_code)
        self.assertEqual("/touch/timing", allowed_volume.headers["Location"])
        self.assertEqual(15, app_module.station_volume_percent())
        saved_volume = json.loads(app_module.VOLUME_SETTINGS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(15, saved_volume["station_volume"])
        self.assertEqual(302, allowed_timing.status_code)
        saved_timing = json.loads(app_module.TIMING_SETTINGS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(10, saved_timing["character_wpm"])

    def test_admin_sessions_lists_recent_practice_sessions(self):
        session_id = "0123456789abcdef0123456789abcdef"
        self.write_text_file(
            "pappy",
            "practice_attempts.jsonl",
            json.dumps({
                "correct": True,
                "mode": "send",
                "practice_session_id": session_id,
                "station_id": "pappy-station",
                "student_id": "pappy",
                "target": "E",
                "timestamp": "2026-07-01T12:00:00+00:00",
            }, sort_keys=True) + "\n",
        )

        response = self.client.get("/admin/sessions")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Session Recovery", html)
        self.assertIn(session_id, html)
        self.assertIn("Pappy", html)
        self.assertIn("pappy-station", html)

    def test_admin_rhythm_summarizes_timing_across_attempt_logs(self):
        self.write_text_file(
            "pappy",
            "practice_attempts.jsonl",
            "\n".join([
                json.dumps({
                    "correct": True,
                    "mode": "send",
                    "student_id": "pappy",
                    "target": "E",
                    "timestamp": "2026-07-01T12:00:00+00:00",
                    "timing_events": [
                        {"type": "symbol", "symbol": ".", "duration_ms": 100},
                        {"type": "gap", "gap_type": "symbol", "duration_ms": 100},
                        {"type": "symbol", "symbol": "-", "duration_ms": 300},
                        {"type": "gap", "gap_type": "letter", "duration_ms": 300},
                        {"type": "symbol", "symbol": ".", "duration_ms": 110},
                    ],
                }, sort_keys=True),
                json.dumps({
                    "correct": True,
                    "mode": "send",
                    "student_id": "pappy",
                    "target": "T",
                    "timestamp": "2026-07-01T12:01:00+00:00",
                    "timing_events": [
                        {"type": "symbol", "symbol": "-", "duration_ms": 310},
                        {"type": "gap", "gap_type": "symbol", "duration_ms": 100},
                        {"type": "symbol", "symbol": ".", "duration_ms": 100},
                    ],
                }, sort_keys=True),
            ]) + "\n",
        )
        self.write_text_file(
            "pappy",
            "word_attempts.jsonl",
            json.dumps({
                "correct": True,
                "student_id": "pappy",
                "timestamp": "2026-07-01T12:02:00+00:00",
                "word": "AM",
                "timing_events": [
                    {"type": "symbol", "symbol": ".", "duration_ms": 100},
                    {"type": "gap", "gap_type": "symbol", "duration_ms": 100},
                    {"type": "symbol", "symbol": "-", "duration_ms": 300},
                    {"type": "gap", "gap_type": "letter", "duration_ms": 300},
                    {"type": "symbol", "symbol": "-", "duration_ms": 300},
                ],
            }, sort_keys=True) + "\n",
        )

        response = self.client.get("/admin/rhythm")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Rhythm Trends", html)
        self.assertIn("Pappy", html)
        self.assertIn("3 keyed attempts", html)
        self.assertIn("Words 1", html)
        self.assertIn("Practice 2", html)
        self.assertIn("100%", html)

    def test_admin_sessions_move_session_updates_attempts_and_rebuilds_progress(self):
        session_id = "0123456789abcdef0123456789abcdef"
        self.write_text_file(
            "pappy",
            "practice_attempts.jsonl",
            "\n".join([
                json.dumps({
                    "correct": True,
                    "mode": "send",
                    "practice_session_id": session_id,
                    "student_id": "pappy",
                    "target": "E",
                    "timestamp": "2026-07-01T12:00:00+00:00",
                }, sort_keys=True),
                json.dumps({
                    "correct": False,
                    "mode": "send",
                    "practice_session_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "student_id": "pappy",
                    "target": "T",
                    "timestamp": "2026-07-01T12:01:00+00:00",
                }, sort_keys=True),
            ]) + "\n",
        )
        self.write_json("pappy", "practice_progress.json", {"E": {"send": {"attempts": 99, "correct": 99, "streak": 99, "strength": 1}}})

        response = self.client.post(
            "/admin/sessions",
            data={
                "action": "move",
                "session_id": session_id,
                "target_student_id": "astrid",
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("recovery_status=moved", response.headers["Location"])
        pappy_attempts = self.student_file("pappy", "practice_attempts.jsonl").read_text(encoding="utf-8")
        astrid_attempts = self.student_file("astrid", "practice_attempts.jsonl").read_text(encoding="utf-8")
        pappy_progress = json.loads(self.student_file("pappy", "practice_progress.json").read_text(encoding="utf-8"))
        astrid_progress = json.loads(self.student_file("astrid", "practice_progress.json").read_text(encoding="utf-8"))

        self.assertNotIn(session_id, pappy_attempts)
        self.assertIn(session_id, astrid_attempts)
        self.assertIn('"student_id": "astrid"', astrid_attempts)
        self.assertNotIn("E", pappy_progress)
        self.assertEqual(1, pappy_progress["T"]["send"]["attempts"])
        self.assertEqual(1, astrid_progress["E"]["send"]["attempts"])
        self.assertEqual(1, astrid_progress["E"]["send"]["correct"])
        backups = list((self.data_dir / "session_recovery_backups").glob(f"*-{session_id}"))
        self.assertEqual(1, len(backups))

    def test_admin_sessions_discard_session_updates_attempts_and_rebuilds_progress(self):
        session_id = "0123456789abcdef0123456789abcdef"
        self.write_text_file(
            "pappy",
            "practice_attempts.jsonl",
            json.dumps({
                "correct": True,
                "mode": "send",
                "practice_session_id": session_id,
                "student_id": "pappy",
                "target": "E",
                "timestamp": "2026-07-01T12:00:00+00:00",
            }, sort_keys=True) + "\n",
        )
        self.write_json("pappy", "practice_progress.json", {"E": {"send": {"attempts": 99, "correct": 99, "streak": 99, "strength": 1}}})

        response = self.client.post(
            "/admin/sessions",
            data={
                "action": "discard",
                "session_id": session_id,
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("recovery_status=discarded", response.headers["Location"])
        self.assertFalse(self.student_file("pappy", "practice_attempts.jsonl").exists())
        pappy_progress = json.loads(self.student_file("pappy", "practice_progress.json").read_text(encoding="utf-8"))
        self.assertEqual({}, pappy_progress)

    def test_admin_sessions_requires_admin_pin_when_configured(self):
        session_id = "0123456789abcdef0123456789abcdef"
        self.write_station_config({"admin_pin": "1234"})
        self.write_text_file(
            "pappy",
            "practice_attempts.jsonl",
            json.dumps({
                "correct": True,
                "mode": "send",
                "practice_session_id": session_id,
                "student_id": "pappy",
                "target": "E",
                "timestamp": "2026-07-01T12:00:00+00:00",
            }, sort_keys=True) + "\n",
        )

        response = self.client.post(
            "/admin/sessions",
            data={
                "action": "discard",
                "session_id": session_id,
                "admin_pin": "9999",
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("recovery_error=admin-pin", response.headers["Location"])
        self.assertTrue(self.student_file("pappy", "practice_attempts.jsonl").exists())

    def test_admin_family_renders_latest_progress_snapshot(self):
        app_module.FAMILY_PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        app_module.FAMILY_PROGRESS_PATH.write_text(
            json.dumps({
                "format": "morsepi-family-progress-v1",
                "generated_at": "2026-08-04T02:30:00+00:00",
                "station_status": [
                    {
                        "available": True,
                        "generated_at": "2026-08-04T02:20:00+00:00",
                        "health_label": "Current",
                        "health_level": "current",
                        "station_id": "pappy-test-station",
                    },
                ],
                "students": [
                    {
                        "active_letters": ["E", "T"],
                        "bonus": {"attempts": 1},
                        "latest_activity_at": "2026-08-04T02:25:00+00:00",
                        "learning_letters": ["S", "O"],
                        "modes": [
                            {"label": "Learn", "mastery": 80, "attempts": 10},
                        ],
                        "name": "Astrid",
                        "source_count": 2,
                        "source_station_id": "pappy-test-station",
                        "words": {"attempts": 3},
                    },
                ],
            }),
            encoding="utf-8",
        )

        response = self.client.get("/admin/family")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Family Progress", html)
        self.assertIn("Astrid", html)
        self.assertIn("pappy-test-station", html)
        self.assertIn("Current", html)
        self.assertIn("S O", html)

    def test_admin_family_refresh_requires_admin_pin_when_configured(self):
        self.write_station_config({"admin_pin": "1234"})

        response = self.client.post(
            "/admin/family",
            data={"admin_pin": "9999"},
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("refresh_error=admin-pin", response.headers["Location"])

    def test_reset_pappy_backs_up_student_and_legacy_without_touching_other_students(self):
        self.write_text_file("pappy", "practice_attempts.jsonl", "pappy attempts\n")
        self.write_json("pappy", "practice_progress.json", {"E": {"send": {"attempts": 1}}})
        self.write_json("pappy", "learning_state.json", {"groups": {"SO": {}}, "last_learning_start_date": "2026-06-21"})
        self.write_text_file("pappy", "bonus_attempts.jsonl", "pappy bonus\n")
        self.write_text_file("pappy", "word_attempts.jsonl", "pappy words\n")
        self.write_text_file("pappy", "message_events.jsonl", "pappy message\n")
        message_inbox = self.student_file("pappy", "message_inbox")
        message_inbox.mkdir(parents=True, exist_ok=True)
        (message_inbox / f"{'a' * 32}.json").write_text("{}", encoding="utf-8")
        local_summary = self.data_dir / "message_sync" / "local_summaries" / "pappy.json"
        family_summary = self.data_dir / "message_sync" / "family_summaries" / "pappy.json"
        local_summary.parent.mkdir(parents=True, exist_ok=True)
        family_summary.parent.mkdir(parents=True, exist_ok=True)
        local_summary.write_text(json.dumps({
            "format": "morsepi-learning-summary-v1",
            "student_id": "pappy",
            "station_id": "morsepi-station",
            "active_letters": app_module.starter_practice_letters + ["S", "O"],
            "curriculum_version": "morsepi-curriculum-v1",
            "generated_at": "2026-08-02T00:00:00+00:00",
        }), encoding="utf-8")
        family_summary.write_text("{}", encoding="utf-8")
        self.write_text_file("astrid", "practice_attempts.jsonl", "astrid attempts\n")
        self.write_legacy_text_file("practice_attempts.jsonl", "legacy attempts\n")
        self.write_legacy_text_file("practice_progress.json", "{}")
        self.write_legacy_text_file("learning_state.json", "{}")

        response = self.client.post(
            "/students",
            data={
                "action": "reset",
                "student_id": "pappy",
                "reset_confirm": "RESET",
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertIn("reset_student=Pappy", response.headers["Location"])
        self.assertFalse(self.student_file("pappy", "practice_attempts.jsonl").exists())
        self.assertFalse(self.student_file("pappy", "practice_progress.json").exists())
        self.assertFalse(self.student_file("pappy", "learning_state.json").exists())
        self.assertFalse(self.student_file("pappy", "bonus_attempts.jsonl").exists())
        self.assertFalse(self.student_file("pappy", "word_attempts.jsonl").exists())
        self.assertFalse(self.student_file("pappy", "message_events.jsonl").exists())
        self.assertFalse(self.student_file("pappy", "message_inbox").exists())
        self.assertTrue(local_summary.exists())
        reset_summary = json.loads(local_summary.read_text(encoding="utf-8"))
        self.assertEqual(app_module.starter_practice_letters, reset_summary["active_letters"])
        self.assertNotIn("S", reset_summary["active_letters"])
        self.assertNotIn("O", reset_summary["active_letters"])
        self.assertFalse(family_summary.exists())
        self.assertFalse((self.data_dir / "practice_attempts.jsonl").exists())
        self.assertFalse((self.data_dir / "practice_progress.json").exists())
        self.assertFalse((self.data_dir / "learning_state.json").exists())
        self.assertTrue(self.student_file("astrid", "practice_attempts.jsonl").exists())

        backups = list((self.data_dir / "student_backups").glob("*-pappy-reset"))
        self.assertEqual(1, len(backups))
        backup = backups[0]
        self.assertTrue((backup / "student" / "practice_attempts.jsonl").exists())
        self.assertTrue((backup / "student" / "practice_progress.json").exists())
        self.assertTrue((backup / "student" / "learning_state.json").exists())
        self.assertTrue((backup / "student" / "bonus_attempts.jsonl").exists())
        self.assertTrue((backup / "student" / "word_attempts.jsonl").exists())
        self.assertTrue((backup / "student" / "message_events.jsonl").exists())
        self.assertTrue((backup / "student" / "message_inbox" / f"{'a' * 32}.json").exists())
        self.assertTrue((backup / "message_sync" / "local_summaries" / "pappy.json").exists())
        self.assertTrue((backup / "message_sync" / "family_summaries" / "pappy.json").exists())
        self.assertTrue((backup / "legacy" / "practice_attempts.jsonl").exists())
        self.assertTrue((backup / "legacy" / "practice_progress.json").exists())
        self.assertTrue((backup / "legacy" / "learning_state.json").exists())


if __name__ == "__main__":
    unittest.main()
