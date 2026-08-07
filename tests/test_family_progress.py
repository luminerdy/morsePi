import json
import tempfile
import unittest
from pathlib import Path

from scripts.family_progress import refresh_family_progress


class MemoryStore:
    def __init__(self, objects):
        self.objects = dict(objects)

    def get_json(self, key, default=...):
        if key not in self.objects:
            if default is not ...:
                return default
            raise KeyError(key)
        return self.objects[key]


def snapshot(station_id, student_id, latest, mastery=80):
    return {
        "format": "morsepi-progress-snapshot-v1",
        "generated_at": latest,
        "hostname": station_id,
        "station_id": station_id,
        "students": [
            {
                "active_letters": ["E", "T"],
                "latest_activity_at": latest,
                "learning_state": {"learning_letters": ["S", "O"]},
                "name": student_id.title(),
                "practice": {
                    "modes": {
                        "learn": {
                            "accuracy": 100,
                            "attempts": 10,
                            "mastery": mastery,
                        },
                    },
                },
                "student_id": student_id,
                "words": {"attempts": 2, "accuracy": 100},
                "bonus": {"attempts": 1, "accuracy": 100},
            }
        ],
    }


class FamilyProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.data_dir = self.base / "data"
        self.data_dir.mkdir()
        self.config = self.data_dir / "station_config.json"
        self.output = self.data_dir / "family_progress" / "latest.json"
        self.config.write_text(
            json.dumps({
                "backup_s3_uri": "s3://morsepi-backups-luminerdy",
                "family_stations": [
                    "pappy-test-station",
                    "astrid-liara-station",
                    "campbell-olivea-station",
                ],
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_refresh_family_progress_chooses_latest_student_snapshot(self):
        store = MemoryStore({
            "stations/pappy-test-station/snapshots/latest_progress.json": snapshot(
                "pappy-test-station",
                "astrid",
                "2026-08-03T10:00:00+00:00",
                mastery=40,
            ),
            "stations/astrid-liara-station/snapshots/latest_progress.json": snapshot(
                "astrid-liara-station",
                "astrid",
                "2026-08-03T12:00:00+00:00",
                mastery=90,
            ),
        })

        progress, output = refresh_family_progress(self.data_dir, self.config, self.output, store)

        self.assertEqual(self.output, output)
        self.assertEqual("morsepi-family-progress-v1", progress["format"])
        self.assertEqual(1, len(progress["students"]))
        self.assertEqual("astrid-liara-station", progress["students"][0]["source_station_id"])
        self.assertEqual(2, progress["students"][0]["source_count"])
        self.assertEqual(90, progress["students"][0]["modes"][0]["mastery"])
        self.assertTrue(output.exists())

    def test_refresh_family_progress_reports_unavailable_station(self):
        store = MemoryStore({
            "stations/pappy-test-station/snapshots/latest_progress.json": snapshot(
                "pappy-test-station",
                "pappy",
                "2026-08-03T10:00:00+00:00",
            ),
        })

        progress, _ = refresh_family_progress(self.data_dir, self.config, self.output, store)

        unavailable = [
            station["station_id"]
            for station in progress["station_status"]
            if not station["available"]
        ]
        self.assertEqual(["astrid-liara-station", "campbell-olivea-station"], unavailable)
        self.assertEqual(1, len(progress["students"]))
        missing = [station for station in progress["station_status"] if station["station_id"] == "astrid-liara-station"][0]
        self.assertEqual("Missing", missing["health_label"])
        self.assertEqual("missing", missing["health_level"])

    def test_refresh_family_progress_marks_old_snapshot_stale(self):
        store = MemoryStore({
            "stations/pappy-test-station/snapshots/latest_progress.json": snapshot(
                "pappy-test-station",
                "pappy",
                "2000-01-01T10:00:00+00:00",
            ),
        })

        progress, _ = refresh_family_progress(self.data_dir, self.config, self.output, store)

        pappy = [station for station in progress["station_status"] if station["station_id"] == "pappy-test-station"][0]
        self.assertEqual("Needs attention", pappy["health_label"])
        self.assertEqual("stale", pappy["health_level"])


if __name__ == "__main__":
    unittest.main()
