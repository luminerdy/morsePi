import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import remote_update_iot


class FakeJobsClient:
    def __init__(self, execution):
        self.execution = execution
        self.updates = []

    def start_next_pending_job(self):
        return self.execution

    def update_job_execution(self, job_id, status, details=None):
        self.updates.append((job_id, status, details or {}))
        return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}


def write_config(path, **values):
    path.write_text(json.dumps(values), encoding="utf-8")


def write_update_report(root, status="succeeded", reason="updated", ending_commit="abc1234", returncode=0):
    path = root / "data" / "update" / "latest_update.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "format": "morsepi-update-status-v1",
                "status": status,
                "reason": reason,
                "updated_at": (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat(),
                "starting_commit": "old1234",
                "target_commit": ending_commit,
                "ending_commit": ending_commit,
                "returncode": returncode,
            }
        ),
        encoding="utf-8",
    )


class RemoteUpdateIotTests(unittest.TestCase):
    def test_missing_config_skips_without_aws_or_local_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "latest.json"
            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

            status = remote_update_iot.run_once(
                config_path=root / "missing.json",
                output_path=output,
                runner=runner,
            )

            self.assertEqual("skipped", status["status"])
            self.assertEqual("remote-update-disabled", status["reason"])
            self.assertEqual([], commands)
            self.assertEqual(status["reason"], json.loads(output.read_text(encoding="utf-8"))["reason"])

    def test_update_app_job_starts_only_local_update_service(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "station_config.json"
            output = root / "latest.json"
            write_config(
                config,
                station_id="pappy-test-station",
                remote_update_enabled=True,
                iot_jobs_endpoint="abc-ats.iot.us-east-1.amazonaws.com",
            )
            client = FakeJobsClient(
                {
                    "jobId": "job-123",
                    "jobDocument": {"action": "update-app", "expected_commit": "abc1234"},
                }
            )
            commands = []

            def runner(command, **kwargs):
                commands.append((command, kwargs))
                write_update_report(root)
                return {"ok": True, "returncode": 0, "stdout": "started", "stderr": ""}

            status = remote_update_iot.run_once(
                config_path=config,
                output_path=output,
                client=client,
                runner=runner,
                app_dir=root,
            )

            self.assertEqual("succeeded", status["status"])
            self.assertEqual(
                [(["systemctl", "--user", "start", "morse-station-update.service"], {"cwd": None, "timeout": 900})],
                commands,
            )
            self.assertEqual(
                [
                    ("job-123", "IN_PROGRESS", {"action": "update-app"}),
                    (
                        "job-123",
                        "SUCCEEDED",
                        {"action": "update-app", "result": "succeeded", "returncode": "0", "reason": "updated"},
                    ),
                ],
                client.updates,
            )
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("job-123", saved["job_id"])
            self.assertEqual("update-app", saved["action"])

    def test_update_app_job_accepts_aws_string_document(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "station_config.json"
            write_config(
                config,
                station_id="pappy-test-station",
                remote_update_enabled=True,
                iot_jobs_endpoint="abc-ats.iot.us-east-1.amazonaws.com",
            )
            client = FakeJobsClient(
                {
                    "jobId": "job-string-doc",
                    "jobDocument": '{"action":"update-app"}',
                }
            )
            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                write_update_report(root)
                return {"ok": True, "returncode": 0, "stdout": "started", "stderr": ""}

            status = remote_update_iot.run_once(
                config_path=config,
                output_path=root / "latest.json",
                client=client,
                runner=runner,
                app_dir=root,
            )

            self.assertEqual("succeeded", status["status"])
            self.assertEqual([["systemctl", "--user", "start", "morse-station-update.service"]], commands)

    def test_update_app_fails_when_service_returns_without_update_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "station_config.json"
            write_config(
                config,
                station_id="astrid-liara-station",
                remote_update_enabled=True,
                iot_jobs_endpoint="abc-ats.iot.us-east-1.amazonaws.com",
            )
            client = FakeJobsClient({"jobId": "job-missing", "jobDocument": {"action": "update-app"}})

            status = remote_update_iot.run_once(
                config_path=config,
                output_path=root / "latest.json",
                client=client,
                runner=lambda command, **kwargs: {
                    "ok": True,
                    "returncode": 0,
                    "stdout": "started",
                    "stderr": "",
                },
                app_dir=root,
            )

            self.assertEqual("failed", status["status"])
            self.assertEqual("missing-update-result", status["reason"])
            self.assertEqual("FAILED", client.updates[-1][1])
            self.assertEqual("missing-update-result", client.updates[-1][2]["reason"])

    def test_update_app_fails_for_blocked_dirty_checkout_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "station_config.json"
            write_config(
                config,
                station_id="astrid-liara-station",
                remote_update_enabled=True,
                iot_jobs_endpoint="abc-ats.iot.us-east-1.amazonaws.com",
            )
            client = FakeJobsClient({"jobId": "job-blocked", "jobDocument": {"action": "update-app"}})

            def runner(command, **kwargs):
                write_update_report(root, "blocked", "tracked-local-changes", "old1234", 20)
                return {"ok": False, "returncode": 1, "stdout": "", "stderr": "service failed"}

            status = remote_update_iot.run_once(
                config_path=config,
                output_path=root / "latest.json",
                client=client,
                runner=runner,
                app_dir=root,
            )

            self.assertEqual("failed", status["status"])
            self.assertEqual("tracked-local-changes", status["reason"])
            self.assertEqual(20, status["returncode"])

    def test_update_app_fails_when_expected_commit_does_not_match(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "station_config.json"
            write_config(
                config,
                station_id="pappy-test-station",
                remote_update_enabled=True,
                iot_jobs_endpoint="abc-ats.iot.us-east-1.amazonaws.com",
            )
            client = FakeJobsClient(
                {
                    "jobId": "job-mismatch",
                    "jobDocument": {"action": "update-app", "expected_commit": "wanted123"},
                }
            )

            def runner(command, **kwargs):
                write_update_report(root, ending_commit="other456")
                return {"ok": True, "returncode": 0, "stdout": "started", "stderr": ""}

            status = remote_update_iot.run_once(
                config_path=config,
                output_path=root / "latest.json",
                client=client,
                runner=runner,
                app_dir=root,
            )

            self.assertEqual("failed", status["status"])
            self.assertEqual("ending-commit-mismatch", status["reason"])
            self.assertEqual("FAILED", client.updates[-1][1])

    def test_diagnose_update_uses_only_fixed_read_only_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "station_config.json"
            write_config(
                config,
                station_id="pappy-test-station",
                remote_update_enabled=True,
                iot_jobs_endpoint="abc-ats.iot.us-east-1.amazonaws.com",
            )
            client = FakeJobsClient({"jobId": "job-diagnostic", "jobDocument": {"action": "diagnose-update"}})
            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                return {"ok": True, "returncode": 0, "stdout": "diagnosed", "stderr": ""}

            status = remote_update_iot.run_once(
                config_path=config,
                output_path=root / "latest.json",
                client=client,
                runner=runner,
                app_dir=root,
            )

            self.assertEqual("succeeded", status["status"])
            self.assertEqual("python3", commands[0][0])
            self.assertIn("scripts/update_diagnostics.py", commands[0])
            self.assertIn("--diagnose", commands[0])

    def test_unknown_action_fails_job_without_local_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "station_config.json"
            output = root / "latest.json"
            write_config(
                config,
                station_id="pappy-test-station",
                remote_update_enabled=True,
                iot_jobs_endpoint="abc-ats.iot.us-east-1.amazonaws.com",
            )
            client = FakeJobsClient(
                {
                    "jobId": "job-456",
                    "jobDocument": {"action": "run-shell"},
                }
            )
            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

            status = remote_update_iot.run_once(
                config_path=config,
                output_path=output,
                client=client,
                runner=runner,
                app_dir=root,
            )

            self.assertEqual("failed", status["status"])
            self.assertEqual("unknown remote maintenance action", status["error"])
            self.assertEqual([], commands)
            self.assertEqual(
                [("job-456", "FAILED", {"reason": "unknown remote maintenance action"})],
                client.updates,
            )

    def test_no_pending_job_skips_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "station_config.json"
            output = root / "latest.json"
            write_config(
                config,
                station_id="pappy-test-station",
                remote_update_enabled=True,
                iot_jobs_endpoint="abc-ats.iot.us-east-1.amazonaws.com",
            )

            status = remote_update_iot.run_once(
                config_path=config,
                output_path=output,
                client=FakeJobsClient(None),
                app_dir=root,
            )

            self.assertEqual("skipped", status["status"])
            self.assertEqual("no-pending-job", status["reason"])


if __name__ == "__main__":
    unittest.main()
