import ast
import importlib
import os
from pathlib import Path
import runpy
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from morsepi.storage.paths import APP_ROOT, data_dir
from morsepi.students.student_identity import TRACKED_REGISTRY_PATH


ROOT = Path(__file__).resolve().parents[1]


class PackageLayoutTests(unittest.TestCase):
    def test_data_and_registry_paths_stay_at_repository_root(self):
        self.assertEqual(APP_ROOT, ROOT)
        self.assertEqual(TRACKED_REGISTRY_PATH, ROOT / "config" / "family_registry.json")
        with patch.dict(os.environ, {"MORSE_DATA_DIR": ""}):
            self.assertEqual(data_dir(), ROOT / "data")
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"MORSE_DATA_DIR": temporary}):
                self.assertEqual(data_dir(), Path(temporary).resolve())

    def test_compatibility_imports_share_state_not_copies(self):
        pairs = {
            "practice_progress": "morsepi.learning.practice_progress",
            "student_profiles": "morsepi.students.student_profiles",
            "durable_storage": "morsepi.storage.durable_storage",
            "message_sync": "morsepi.messaging.message_sync",
        }
        for old, new in pairs.items():
            with self.subTest(module=old):
                self.assertIs(importlib.import_module(old), importlib.import_module(new))

    def test_legacy_launcher_delegates_to_package_main(self):
        stub = ModuleType("morsepi.app")
        calls = []
        stub.main = lambda: calls.append("started")
        with patch.dict(sys.modules, {"morsepi.app": stub}):
            runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
        self.assertEqual(calls, ["started"])

    def test_package_does_not_depend_on_root_compatibility_bridges(self):
        legacy = {path.stem for path in ROOT.glob("*.py")}
        for path in (ROOT / "morsepi").rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""]
                self.assertFalse(legacy.intersection(names), str(path))

    def test_browser_assets_are_packaged(self):
        self.assertTrue((ROOT / "morsepi" / "templates" / "touch_daily.html").is_file())
        self.assertTrue((ROOT / "morsepi" / "static" / "app.js").is_file())
        self.assertFalse((ROOT / "templates").exists())
        self.assertFalse((ROOT / "static").exists())
