import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import update_diagnostics


class UpdateDiagnosticsTests(unittest.TestCase):
    def make_repo(self, root):
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        tracked = root / "tracked.txt"
        tracked.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=root, check=True)
        return tracked

    def test_blocked_report_preserves_tracked_patch_without_student_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tracked = self.make_repo(root)
            tracked.write_text("changed\n", encoding="utf-8")
            output = root / "data" / "update" / "latest_update.json"
            artifacts = root / "data" / "update" / "diagnostics"

            with mock.patch("scripts.update_diagnostics.service_state", return_value="active"):
                report = update_diagnostics.record_update(
                    "blocked",
                    "tracked-local-changes",
                    returncode=20,
                    app_dir=root,
                    output_path=output,
                    artifact_dir=artifacts,
                    preserve=True,
                )

            self.assertTrue(report["dirty"])
            self.assertEqual("tracked-local-changes", report["reason"])
            self.assertEqual(20, report["returncode"])
            self.assertTrue(Path(report["patch_path"]).is_file())
            self.assertIn("tracked.txt", report["tracked_changes"][0])
            self.assertNotIn("students", json.dumps(report).lower())

    def test_terminal_report_preserves_start_and_records_ending_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_repo(root)
            output = root / "latest_update.json"

            with mock.patch("scripts.update_diagnostics.service_state", return_value="active"):
                started = update_diagnostics.record_update(
                    "in-progress",
                    "starting",
                    app_dir=root,
                    output_path=output,
                )
                finished = update_diagnostics.record_update(
                    "succeeded",
                    "updated",
                    target_commit=started["ending_commit"],
                    app_dir=root,
                    output_path=output,
                )

            self.assertEqual(started["started_at"], finished["started_at"])
            self.assertEqual("succeeded", finished["status"])
            self.assertEqual(finished["target_commit"], finished["ending_commit"])
            self.assertIn("finished_at", finished)


if __name__ == "__main__":
    unittest.main()
