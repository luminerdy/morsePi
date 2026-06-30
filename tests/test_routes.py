import importlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


os.environ.setdefault("GPIOZERO_PIN_FACTORY", "mock")

try:
    app_module = importlib.import_module("app")
    student_profiles = importlib.import_module("student_profiles")
except ModuleNotFoundError as error:
    app_module = None
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
        self.original_play_daily = app_module.play_daily_celebration_in_background

        student_profiles.DATA_DIR = self.data_dir
        student_profiles.STUDENTS_DIR = self.students_dir
        student_profiles.PROFILES_PATH = self.data_dir / "student_profiles.json"
        app_module.TIMING_SETTINGS_PATH = self.data_dir / "timing_settings.json"
        app_module.play_daily_celebration_in_background = self.record_daily_celebration
        self.daily_celebration_called = False

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
        app_module.play_daily_celebration_in_background = self.original_play_daily
        self.temp_dir.cleanup()

    def record_daily_celebration(self):
        self.daily_celebration_called = True

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

    def test_touch_practice_menu_shows_locked_words_for_fresh_student(self):
        response = self.client.get("/touch/practice")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("<strong>Words</strong>", html)
        self.assertIn("Unlock after S O", html)
        self.assertIn('href="/touch/progress"', html)

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
        self.assertIn("0% · 0/42 words · No word tries yet", words_html)
        self.assertIn('data-word-morse=".- --"', words_html)
        self.assertIn('data-word-target="AM"', words_html)
        self.assertIn('id="liveMorse"', words_html)
        self.assertIn('id="wordFeedback"', words_html)
        self.assertIn("data-word-clear", words_html)
        self.assertIn('/touch/words?i=1&autoplay=1', words_html)
        self.assertNotIn(">Read</a>", words_html)
        self.assertIn("<small>.-</small>", words_html)

    def test_touch_words_locked_before_s_o_active(self):
        response = self.client.get("/touch/words")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Words Unlock", html)
        self.assertIn("Finish S and O", html)

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
        self.assertEqual("AM", word_record["decoded"])
        self.assertEqual(2, word_record["timing_summary"]["symbol_count"])
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

    def test_touch_student_selection_redirects_to_daily_after_select(self):
        response = self.client.post(
            "/touch/students",
            data={"action": "select", "student_id": "astrid"},
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual("/touch/daily", response.headers["Location"])

    def test_touch_daily_fresh_student_shows_no_learning_now(self):
        response = self.client.get("/touch/daily")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("6/26", html)
        self.assertIn("Learning Now", html)
        self.assertIn("<strong>None</strong>", html)
        self.assertNotIn("New: S O", html)
        self.assertNotIn("Learn S O", html)

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
        self.assertIn("16/20 Learn", html)
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
        self.assertIn("79%", html)
        self.assertIn("1/42 words", html)
        self.assertIn("19/24 correct", html)

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

        response = self.client.get("/touch/progress")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("Daily Signal Complete", html)
        self.assertIn("Clean Copy", html)
        self.assertIn("First Signals Mastered", html)
        self.assertIn("26 min practice time", html)
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
        self.assertIn("100% current-set mastery", html)
        self.assertIn("Learning Now: S O", html)
        self.assertIn("14/20 Learn", html)
        self.assertIn("current set", html)

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

    def test_practice_next_uses_learning_now_letters_for_learn_mode(self):
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

        response = self.client.post("/practice/next?mode=learn")
        payload = response.get_json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("learn", payload["mode"])
        self.assertIn(payload["target"], ["R", "K"])
        self.assertEqual(["R", "K"], [item["letter"] for item in payload["progress"]])
        self.assertEqual(["R", "K"], payload["overall"]["learning_letters"])

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
        self.assertEqual(1, progress["E"]["send"]["attempts"])
        self.assertEqual(1, progress["E"]["send"]["correct"])
        self.assertEqual("E", attempt_record["target"])
        self.assertEqual({"avg_dash_ms": None, "avg_dot_ms": 110, "avg_gap_ms": None, "dash_count": 0, "dot_count": 1, "gap_count": 0, "symbol_count": 1}, attempt_record["timing_summary"])

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

    def test_touch_daily_complete_points_to_practice_when_active_set_unfinished(self):
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
        self.assertIn("Daily complete. Send has the most room to improve today.", html)
        self.assertIn("/touch/practice/run?mode=send", html)
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
        self.assertEqual("sprint-1", bonus_record["session_id"])
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
        self.assertIn("0/20 Learn", astrid_html)
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

    def test_reset_pappy_backs_up_student_and_legacy_without_touching_other_students(self):
        self.write_text_file("pappy", "practice_attempts.jsonl", "pappy attempts\n")
        self.write_json("pappy", "practice_progress.json", {"E": {"send": {"attempts": 1}}})
        self.write_json("pappy", "learning_state.json", {"groups": {"SO": {}}, "last_learning_start_date": "2026-06-21"})
        self.write_text_file("pappy", "bonus_attempts.jsonl", "pappy bonus\n")
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
        self.assertTrue((backup / "legacy" / "practice_attempts.jsonl").exists())
        self.assertTrue((backup / "legacy" / "practice_progress.json").exists())
        self.assertTrue((backup / "legacy" / "learning_state.json").exists())


if __name__ == "__main__":
    unittest.main()
