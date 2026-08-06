import os
import tempfile
import unittest
from pathlib import Path

import paths


class PathTests(unittest.TestCase):
    def test_default_data_dir_is_anchored_to_app_root(self):
        original = os.environ.pop("MORSE_DATA_DIR", None)
        try:
            self.assertEqual(paths.APP_ROOT / "data", paths.data_dir())
        finally:
            if original is not None:
                os.environ["MORSE_DATA_DIR"] = original

    def test_env_data_dir_overrides_default(self):
        original = os.environ.get("MORSE_DATA_DIR")
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.environ["MORSE_DATA_DIR"] = temp_dir
                self.assertEqual(Path(temp_dir).resolve(), paths.data_dir())
                self.assertEqual(Path(temp_dir).resolve() / "station_config.json", paths.data_path("station_config.json"))
            finally:
                if original is None:
                    os.environ.pop("MORSE_DATA_DIR", None)
                else:
                    os.environ["MORSE_DATA_DIR"] = original


if __name__ == "__main__":
    unittest.main()

