import json
import tempfile
import unittest
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
                    "jobDocument": {"action": "update-app"},
                }
            )
            commands = []

            def runner(command, **kwargs):
                commands.append((command, kwargs))
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
                    ("job-123", "SUCCEEDED", {"action": "update-app", "result": "succeeded", "returncode": "0"}),
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
