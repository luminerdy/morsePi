import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path


os.environ.setdefault("GPIOZERO_PIN_FACTORY", "mock")

try:
    app_module = importlib.import_module("app")
except ModuleNotFoundError as error:
    app_module = None
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None


@unittest.skipIf(app_module is None, f"app dependencies unavailable: {IMPORT_ERROR}")
class LearningGateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.progress_path = self.base / "practice_progress.json"
        self.learning_state_path = self.base / "learning_state.json"
        self.attempts_path = self.base / "practice_attempts.jsonl"

        app_module.set_progress_path(self.progress_path)
        app_module.set_attempts_path(self.attempts_path)
        app_module.learning_state_path = self.learning_state_path

    def tearDown(self):
        app_module.set_progress_path(Path("data/practice_progress.json"))
        app_module.set_attempts_path(Path("data/practice_attempts.jsonl"))
        app_module.learning_state_path = Path("data/learning_state.json")
        self.temp_dir.cleanup()

    def make_attempts(self, total, correct, target="E", mode="send"):
        attempts = []

        for index in range(total):
            attempts.append(
                {
                    "correct": index < correct,
                    "target": target,
                    "mode": mode,
                    "timestamp": f"{app_module.today_key()}T00:{index:02d}:00+00:00",
                }
            )

        return attempts

    def write_progress(self, letters, strength_by_mode):
        progress = {}

        for letter in letters:
            progress[letter] = {}
            for mode, strength in strength_by_mode.items():
                progress[letter][mode] = {
                    "attempts": 10,
                    "correct": 10,
                    "last_seen": "2026-06-21T00:00:00+00:00",
                    "streak": 10,
                    "strength": strength,
                }

        self.progress_path.write_text(json.dumps(progress), encoding="utf-8")

    def write_learning_state(self, groups, last_learning_start_date=""):
        self.learning_state_path.write_text(
            json.dumps(
                {
                    "groups": groups,
                    "last_learning_start_date": last_learning_start_date,
                }
            ),
            encoding="utf-8",
        )

    def all_modes(self, strength):
        return {mode: strength for mode in app_module.practice_modes}

    def test_fresh_student_starts_with_six_letters_and_no_learning_now(self):
        state = app_module.get_practice_letter_state()
        overall = app_module.get_learning_overall(state["active_letters"])

        self.assertEqual(["E", "T", "A", "N", "I", "M"], state["active_letters"])
        self.assertEqual([], state["learning_letters"])
        self.assertEqual("6/26", overall["alphabet_progress"])
        self.assertEqual(0, overall["current_mastery"])

    def test_next_letters_do_not_unlock_below_100_current_set_mastery(self):
        self.write_progress(app_module.starter_practice_letters, self.all_modes(0.99))

        state = app_module.get_practice_letter_state()
        overall = app_module.get_learning_overall(state["active_letters"])

        self.assertEqual([], state["learning_letters"])
        self.assertEqual(["S", "O"], overall["next_unlock"]["letters"])
        self.assertEqual(99, overall["current_mastery"])
        self.assertIn("current-set mastery", overall["next_goal"])

    def test_next_letters_enter_learning_now_at_100_current_set_mastery(self):
        self.write_progress(app_module.starter_practice_letters, self.all_modes(1.0))

        state = app_module.get_practice_letter_state()
        learn_letters = app_module.get_practice_letters_for_mode("learn")
        send_letters = app_module.get_practice_letters_for_mode("send")

        self.assertEqual(["S", "O"], state["learning_letters"])
        self.assertEqual(["S", "O"], learn_letters)
        self.assertEqual(["E", "T", "A", "N", "I", "M"], send_letters)

    def test_stale_learning_group_is_pruned_when_current_set_not_complete(self):
        self.write_progress(app_module.starter_practice_letters, self.all_modes(0.0))
        self.write_learning_state(
            {
                "SO": {
                    "first_learning_date": "2026-06-21",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2026-06-21",
        )

        state = app_module.get_practice_letter_state()
        saved_state = json.loads(self.learning_state_path.read_text(encoding="utf-8"))

        self.assertEqual([], state["learning_letters"])
        self.assertEqual({}, saved_state["groups"])
        self.assertEqual("", saved_state["last_learning_start_date"])

    def test_learning_group_graduates_after_burn_in(self):
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
                    "strength": 0.70,
                }
            }

        self.progress_path.write_text(json.dumps(progress), encoding="utf-8")
        self.write_learning_state(
            {
                "SO": {
                    "first_learning_date": "2000-01-01",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2000-01-01",
        )

        state = app_module.get_practice_letter_state()
        overall = app_module.get_learning_overall(state["active_letters"])

        self.assertEqual([], state["learning_letters"])
        self.assertEqual(["E", "T", "A", "N", "I", "M", "S", "O"], state["active_letters"])
        self.assertEqual("8/26", overall["alphabet_progress"])

    def test_daily_mission_summary_caps_display_and_marks_complete(self):
        original_loader = app_module.load_today_attempts
        app_module.load_today_attempts = lambda: self.make_attempts(total=22, correct=18)

        try:
            daily = app_module.daily_mission_summary()
        finally:
            app_module.load_today_attempts = original_loader

        self.assertEqual(22, daily["attempts"])
        self.assertEqual(20, daily["display_attempts"])
        self.assertEqual(0, daily["remaining"])
        self.assertEqual(100, daily["progress"])
        self.assertEqual(82, daily["accuracy"])
        self.assertTrue(daily["completed"])
        self.assertEqual("Daily mission complete.", daily["message"])

    def test_daily_mission_learning_now_keeps_mission_open_until_learn_ready(self):
        self.write_progress(app_module.starter_practice_letters, self.all_modes(1.0))
        progress = json.loads(self.progress_path.read_text(encoding="utf-8"))
        progress["S"] = {
            "learn": {
                "attempts": 6,
                "correct": 6,
                "last_seen": "2026-06-21T00:00:00+00:00",
                "streak": 6,
                "strength": 1.0,
            }
        }
        progress["O"] = {
            "learn": {
                "attempts": 5,
                "correct": 5,
                "last_seen": "2026-06-21T00:00:00+00:00",
                "streak": 5,
                "strength": 1.0,
            }
        }
        self.progress_path.write_text(json.dumps(progress), encoding="utf-8")

        original_loader = app_module.load_today_attempts
        app_module.load_today_attempts = lambda: self.make_attempts(total=22, correct=18)

        try:
            daily = app_module.daily_mission_summary()
        finally:
            app_module.load_today_attempts = original_loader

        self.assertEqual(["S", "O"], daily["learning_letters"])
        self.assertEqual(20, daily["learning_focus"]["goal"])
        self.assertEqual(11, daily["learning_focus"]["correct"])
        self.assertEqual(9, daily["learning_focus"]["remaining"])
        self.assertEqual(55, daily["learning_focus"]["progress"])
        self.assertEqual(78, daily["progress"])
        self.assertFalse(daily["completed"])
        self.assertIn("needs", daily["message"])

    def test_daily_mission_completed_learning_waits_for_next_practice_day(self):
        self.write_progress(app_module.starter_practice_letters, self.all_modes(1.0))
        progress = json.loads(self.progress_path.read_text(encoding="utf-8"))
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
        self.progress_path.write_text(json.dumps(progress), encoding="utf-8")

        original_loader = app_module.load_today_attempts
        app_module.load_today_attempts = lambda: self.make_attempts(total=22, correct=18)

        try:
            daily = app_module.daily_mission_summary()
        finally:
            app_module.load_today_attempts = original_loader

        self.assertEqual(["S", "O"], daily["learning_letters"])
        self.assertEqual(20, daily["learning_focus"]["correct"])
        self.assertTrue(daily["completed"])
        self.assertIn("Come back tomorrow", daily["message"])
        self.assertEqual("Tomorrow", daily["next_action"]["label"])
        self.assertEqual("Come Back Tomorrow", daily["next_action"]["title"])

    def test_daily_next_action_prefers_learning_now(self):
        state = {
            "active_letters": ["E", "T", "A", "N", "I", "M"],
            "learning_letters": ["S", "O"],
            "learning_status": None,
            "locked_until_tomorrow": False,
            "next_step": None,
        }

        action = app_module.daily_next_action(state)
        coach = app_module.daily_practice_coach(state)

        self.assertEqual("learn", action["mode"])
        self.assertEqual("Learn S O", action["title"])
        self.assertEqual("Practice Next", coach["headline"])
        self.assertEqual(["S", "O"], [item["letter"] for item in coach["practice_next"]])
        self.assertTrue(all(item["mode"] == "learn" for item in coach["practice_next"]))
        self.assertEqual("Learning", coach["boost_label"])
        self.assertEqual(["S", "O"], [item["letter"] for item in coach["signal_boost"]])

    def test_progress_details_show_learning_now_for_learn_mode(self):
        active_letters = app_module.starter_practice_letters + ["S", "O"]
        self.write_progress(active_letters, self.all_modes(1.0))
        progress = json.loads(self.progress_path.read_text(encoding="utf-8"))
        progress["R"] = {
            "learn": {
                "attempts": 7,
                "correct": 7,
                "last_seen": "2026-06-22T00:00:00+00:00",
                "streak": 7,
                "strength": 1.0,
            }
        }
        progress["K"] = {
            "learn": {
                "attempts": 9,
                "correct": 8,
                "last_seen": "2026-06-22T00:00:00+00:00",
                "streak": 5,
                "strength": 1.0,
            }
        }
        self.progress_path.write_text(json.dumps(progress), encoding="utf-8")
        self.write_learning_state(
            {
                "SO": {
                    "first_learning_date": "2026-06-20",
                    "letters": ["S", "O"],
                }
            },
            last_learning_start_date="2026-06-20",
        )

        details = app_module.get_progress_mode_details()

        self.assertEqual("Learning Now", details["learn"]["scope_label"])
        self.assertEqual("Learning R K", details["learn"]["summary_label"])
        self.assertEqual(["R", "K"], [item["letter"] for item in details["learn"]["letters"]])
        self.assertEqual(75, details["learn"]["score"]["mastery"])
        self.assertEqual("15/20 Learn", details["learn"]["score"]["completion_label"])
        self.assertEqual("R needs 3 more correct Learn tries", details["learn"]["score"]["next_goal"])
        self.assertEqual("Current Set", details["send"]["scope_label"])
        self.assertEqual(100, details["send"]["score"]["mastery"])

    def test_practice_coach_recommends_weakest_letter_and_mode(self):
        progress = {}

        for letter in app_module.starter_practice_letters:
            progress[letter] = {
                mode: {
                    "attempts": 8,
                    "correct": 8,
                    "last_seen": "2026-06-21T00:00:00+00:00",
                    "streak": 8,
                    "strength": 1.0,
                }
                for mode in app_module.practice_modes
            }

        progress["M"]["listen"] = {
            "attempts": 3,
            "correct": 1,
            "last_seen": "2026-06-21T00:00:00+00:00",
            "streak": 0,
            "strength": 0.0,
        }
        self.progress_path.write_text(json.dumps(progress), encoding="utf-8")

        state = {
            "active_letters": app_module.starter_practice_letters,
            "learning_letters": [],
        }
        coach = app_module.daily_practice_coach(state)
        first = coach["practice_next"][0]

        self.assertEqual("Practice Coach", coach["headline"])
        self.assertEqual("M", first["letter"])
        self.assertEqual("listen", first["mode"])
        self.assertEqual("Listen", first["mode_label"])
        self.assertEqual("0%", first["reason"])
        self.assertEqual("M", coach["signal_boost"][0]["letter"])

    def test_daily_next_action_points_to_weakest_mode_when_no_learning_now(self):
        progress = {}

        for letter in app_module.starter_practice_letters:
            progress[letter] = {
                mode: {
                    "attempts": 8,
                    "correct": 8,
                    "last_seen": "2026-06-21T00:00:00+00:00",
                    "streak": 8,
                    "strength": 1.0,
                }
                for mode in app_module.practice_modes
            }

        for letter in app_module.starter_practice_letters:
            progress[letter]["echo"]["strength"] = 0.25
        self.progress_path.write_text(json.dumps(progress), encoding="utf-8")

        state = {
            "active_letters": app_module.starter_practice_letters,
            "learning_letters": [],
            "locked_until_tomorrow": False,
            "next_step": {"letters": ["S", "O"], "threshold": 100, "label": "Signal Builder"},
        }
        action = app_module.daily_next_action(state)

        self.assertEqual("echo", action["mode"])
        self.assertEqual("Practice Echo", action["title"])
        self.assertIn("most room", action["detail"])


if __name__ == "__main__":
    unittest.main()
