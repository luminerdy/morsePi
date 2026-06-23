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

    def test_touch_progress_renders_letters_mastered_and_current_set(self):
        response = self.client.get("/touch/progress")
        html = response.get_data(as_text=True)

        self.assertEqual(200, response.status_code)
        self.assertIn("6/26 letters mastered", html)
        self.assertIn("current set", html)
        self.assertNotIn("% overall", html)

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
        self.assertIn("100% current set mastery", html)
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

    def test_render_prunes_stale_learning_now_state(self):
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
        self.assertIn("<strong>None</strong>", html)
        self.assertNotIn("Learn S O", html)
        self.assertEqual({}, saved_state["groups"])
        self.assertEqual("", saved_state["last_learning_start_date"])

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
        self.assertTrue((backup / "legacy" / "practice_attempts.jsonl").exists())
        self.assertTrue((backup / "legacy" / "practice_progress.json").exists())
        self.assertTrue((backup / "legacy" / "learning_state.json").exists())


if __name__ == "__main__":
    unittest.main()
