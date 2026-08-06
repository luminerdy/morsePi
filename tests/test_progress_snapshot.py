import json
import tempfile
import unittest
from pathlib import Path

from scripts.progress_snapshot import build_snapshot, write_snapshot


class ProgressSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.data_dir = self.base / "data"
        self.student_dir = self.data_dir / "students" / "astrid"
        self.student_dir.mkdir(parents=True)

        (self.data_dir / "student_profiles.json").write_text(
            json.dumps([
                {"id": "astrid", "name": "Astrid"},
                {"id": "guest", "name": "Guest", "disposable": True},
            ]),
            encoding="utf-8",
        )
        (self.student_dir / "practice_progress.json").write_text(
            json.dumps({
                "E": {
                    "learn": {
                        "attempts": 3,
                        "correct": 3,
                        "strength": 0.9,
                        "last_seen": "2026-08-03T12:00:00+00:00",
                    },
                    "send": {
                        "attempts": 2,
                        "correct": 1,
                        "strength": 0.4,
                        "last_seen": "2026-08-03T12:05:00+00:00",
                    },
                },
                "T": {
                    "learn": {
                        "attempts": 1,
                        "correct": 1,
                        "strength": 0.5,
                        "last_seen": "2026-08-03T12:10:00+00:00",
                    },
                },
            }),
            encoding="utf-8",
        )
        (self.student_dir / "learning_state.json").write_text(
            json.dumps({"learning_letters": ["S", "O"]}),
            encoding="utf-8",
        )
        (self.student_dir / "word_attempts.jsonl").write_text(
            json.dumps({
                "word": "TO",
                "correct": True,
                "timestamp": "2026-08-03T12:15:00+00:00",
            }) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_snapshot_summarizes_students_without_guest(self):
        snapshot = build_snapshot(
            self.data_dir,
            station_id="pappy-test-station",
            config_path=self.data_dir / "missing-config.json",
        )

        self.assertEqual("morsepi-progress-snapshot-v1", snapshot["format"])
        self.assertEqual("pappy-test-station", snapshot["station_id"])
        self.assertEqual(1, len(snapshot["students"]))
        student = snapshot["students"][0]
        self.assertEqual("astrid", student["student_id"])
        self.assertEqual(["E", "T"], student["active_letters"])
        self.assertEqual(["S", "O"], student["learning_state"]["learning_letters"])
        self.assertEqual(4, student["practice"]["modes"]["learn"]["attempts"])
        self.assertEqual(100, student["practice"]["modes"]["learn"]["accuracy"])
        self.assertEqual(50, student["practice"]["modes"]["send"]["accuracy"])
        self.assertEqual(1, student["words"]["attempts"])
        self.assertEqual("2026-08-03T12:15:00+00:00", student["latest_activity_at"])

    def test_build_snapshot_prefers_ready_learning_state_over_stale_message_summary(self):
        progress = json.loads((self.student_dir / "practice_progress.json").read_text(encoding="utf-8"))
        for letter in ("S", "O"):
            progress[letter] = {
                "learn": {
                    "attempts": 10,
                    "correct": 10,
                    "strength": 0.85,
                    "last_seen": "2026-08-03T14:00:00+00:00",
                },
            }
        (self.student_dir / "practice_progress.json").write_text(
            json.dumps(progress),
            encoding="utf-8",
        )
        (self.student_dir / "learning_state.json").write_text(
            json.dumps({
                "groups": {
                    "SO": {
                        "letters": ["S", "O"],
                        "first_learning_date": "2026-08-03",
                        "first_learning_started_at": "2026-08-03T12:00:00+00:00",
                    },
                },
                "last_learning_start_date": "2026-08-03",
            }),
            encoding="utf-8",
        )
        summary_dir = self.data_dir / "message_sync" / "local_summaries"
        summary_dir.mkdir(parents=True)
        (summary_dir / "astrid.json").write_text(
            json.dumps({
                "active_letters": ["E", "T", "A", "N", "I", "M"],
                "student_id": "astrid",
            }),
            encoding="utf-8",
        )

        snapshot = build_snapshot(
            self.data_dir,
            station_id="pappy-test-station",
            config_path=self.data_dir / "missing-config.json",
        )

        student = snapshot["students"][0]
        self.assertEqual(["E", "T", "A", "N", "I", "M", "S", "O"], student["active_letters"])

    def test_write_snapshot_creates_parent_directory(self):
        output = self.base / "out" / "latest_progress.json"
        snapshot = {"format": "morsepi-progress-snapshot-v1"}

        result = write_snapshot(snapshot, output)

        self.assertEqual(output, result)
        self.assertEqual(snapshot, json.loads(output.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
