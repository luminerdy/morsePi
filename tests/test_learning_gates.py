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


if __name__ == "__main__":
    unittest.main()
