import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paths import data_path
from scripts.backup_data import DEFAULT_CONFIG_PATH, load_station_config


DEFAULT_OUTPUT_PATH = data_path("remote_update", "latest_iot_job.json")
DEFAULT_APP_DIR = Path("/home/morse/morse-station")
DEFAULT_UPDATE_REPORT = Path("data/update/latest_update.json")
DEFAULT_UPDATE_DIAGNOSTIC = Path("data/update/latest_diagnostic.json")
DEFAULT_UPDATE_SERVICE = "morse-station-update.service"
DEFAULT_SYNC_SERVICE = "morse-station-sync.service"
DEFAULT_APP_SERVICE = "morse-station.service"
AWS_JOB_STATUSES = {"IN_PROGRESS", "SUCCEEDED", "FAILED", "REJECTED"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def endpoint_url(endpoint):
    endpoint = str(endpoint or "").strip()
    if not endpoint:
        return ""
    if endpoint.startswith("https://"):
        return endpoint.rstrip("/")
    return f"https://{endpoint.rstrip('/')}"


def compact(value, limit=400):
    value = str(value or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def write_status(status, output_path=DEFAULT_OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def run_command(command, cwd=None, timeout=900):
    try:
        result = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(error),
        }

    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


class AwsJobsClient:
    def __init__(self, thing_name, endpoint, region=None, runner=run_command):
        self.thing_name = thing_name
        self.endpoint = endpoint_url(endpoint)
        self.region = str(region or "").strip()
        self.runner = runner

    def aws_args(self):
        args = ["--endpoint-url", self.endpoint, "--output", "json"]
        if self.region:
            args.extend(["--region", self.region])
        return args

    def start_next_pending_job(self):
        command = [
            "aws",
            "iot-jobs-data",
            "start-next-pending-job-execution",
            "--thing-name",
            self.thing_name,
            *self.aws_args(),
        ]
        result = self.runner(command, timeout=60)
        if not result["ok"]:
            raise RuntimeError(result["stderr"] or result["stdout"] or "unable to read pending IoT job")

        if not result["stdout"]:
            return None

        try:
            payload = json.loads(result["stdout"])
        except json.JSONDecodeError as error:
            raise RuntimeError(f"invalid IoT Jobs response: {error}") from error

        execution = payload.get("execution")
        return execution if isinstance(execution, dict) else None

    def update_job_execution(self, job_id, status, details=None):
        if status not in AWS_JOB_STATUSES:
            raise ValueError(f"Unsupported AWS job status: {status}")

        command = [
            "aws",
            "iot-jobs-data",
            "update-job-execution",
            "--thing-name",
            self.thing_name,
            "--job-id",
            job_id,
            "--status",
            status,
            *self.aws_args(),
        ]
        if details:
            command.extend(["--status-details", json.dumps(details, sort_keys=True)])

        result = self.runner(command, timeout=60)
        if not result["ok"]:
            raise RuntimeError(result["stderr"] or result["stdout"] or f"unable to mark IoT job {status}")
        return result


def document_dict(job_document):
    if isinstance(job_document, str):
        try:
            job_document = json.loads(job_document)
        except json.JSONDecodeError:
            return {}
    if not isinstance(job_document, dict):
        return {}
    return job_document


def action_from_document(job_document):
    document = document_dict(job_document)
    action = document.get("action") or document.get("operation")
    return str(action or "").strip().lower()


def action_command(action, app_dir=DEFAULT_APP_DIR):
    commands = {
        "update-app": (["systemctl", "--user", "start", DEFAULT_UPDATE_SERVICE], None),
        "diagnose-update": (
            [
                "python3",
                "scripts/update_diagnostics.py",
                "--diagnose",
                "--app-dir",
                str(app_dir),
                "--output",
                str(DEFAULT_UPDATE_DIAGNOSTIC),
            ],
            app_dir,
        ),
        "sync-progress": (["systemctl", "--user", "start", DEFAULT_SYNC_SERVICE], None),
        "enable-message-sync": (["python3", "scripts/enable_message_sync.py"], app_dir),
        "backup-data": (["python3", "scripts/backup_data.py", "--label", "remote"], DEFAULT_APP_DIR),
        "write-status": (["python3", "scripts/station_status.py"], DEFAULT_APP_DIR),
        "restart-app": (["systemctl", "--user", "restart", DEFAULT_APP_SERVICE], None),
    }
    return commands.get(action)


def load_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def commits_match(expected, actual):
    expected = str(expected or "").strip().lower()
    actual = str(actual or "").strip().lower()
    return bool(expected and actual and (expected.startswith(actual) or actual.startswith(expected)))


def verify_update_report(report_path, requested_at, expected_commit=""):
    report = load_json(report_path)
    if not report:
        return False, "missing-update-result", {}

    updated_at = parse_timestamp(report.get("updated_at"))
    requested = parse_timestamp(requested_at)
    if not updated_at or (requested and updated_at < requested):
        return False, "stale-update-result", report

    status = str(report.get("status") or "").strip().lower()
    if status not in {"current", "succeeded"}:
        reason = str(report.get("reason") or status or "update-not-successful")
        return False, reason, report

    ending_commit = str(report.get("ending_commit") or "")
    target_commit = str(report.get("target_commit") or "")
    required_commit = str(expected_commit or target_commit or "")
    if required_commit and not commits_match(required_commit, ending_commit):
        return False, "ending-commit-mismatch", report
    if not ending_commit:
        return False, "missing-ending-commit", report
    return True, str(report.get("reason") or status), report


def load_remote_config(config_path=DEFAULT_CONFIG_PATH):
    config = load_station_config(config_path)
    return {
        "enabled": bool(config.get("remote_update_enabled", False)),
        "thing_name": str(config.get("iot_thing_name") or config.get("station_id") or "").strip(),
        "endpoint": str(config.get("iot_jobs_endpoint") or "").strip(),
        "region": str(config.get("iot_jobs_region") or "").strip(),
    }


def skipped_status(reason):
    return {
        "format": "morsepi-remote-update-status-v1",
        "checked_at": utc_now(),
        "status": "skipped",
        "reason": reason,
    }


def run_once(config_path=DEFAULT_CONFIG_PATH, output_path=DEFAULT_OUTPUT_PATH, client=None, runner=run_command, app_dir=DEFAULT_APP_DIR):
    remote_config = load_remote_config(config_path)
    if not remote_config["enabled"]:
        status = skipped_status("remote-update-disabled")
        write_status(status, output_path)
        return status
    if not remote_config["thing_name"] or not remote_config["endpoint"]:
        status = skipped_status("remote-update-not-configured")
        write_status(status, output_path)
        return status

    client = client or AwsJobsClient(
        remote_config["thing_name"],
        remote_config["endpoint"],
        remote_config["region"],
        runner=runner,
    )

    execution = client.start_next_pending_job()
    if not execution:
        status = skipped_status("no-pending-job")
        status["thing_name"] = remote_config["thing_name"]
        write_status(status, output_path)
        return status

    job_id = str(execution.get("jobId") or "")
    job_document = document_dict(execution.get("jobDocument", {}))
    action = action_from_document(job_document)
    expected_commit = str(job_document.get("expected_commit") or "").strip()
    status = {
        "format": "morsepi-remote-update-status-v1",
        "checked_at": utc_now(),
        "thing_name": remote_config["thing_name"],
        "job_id": job_id,
        "action": action,
        "status": "in-progress",
    }
    write_status(status, output_path)

    command_info = action_command(action, app_dir)
    if not job_id or command_info is None:
        error = "unknown remote maintenance action" if action else "missing remote maintenance action"
        failed = {
            **status,
            "finished_at": utc_now(),
            "status": "failed",
            "error": error,
        }
        if job_id:
            client.update_job_execution(job_id, "FAILED", {"reason": error})
        write_status(failed, output_path)
        return failed

    client.update_job_execution(job_id, "IN_PROGRESS", {"action": action})
    command, cwd = command_info
    cwd = app_dir if cwd == DEFAULT_APP_DIR else cwd
    result = runner(command, cwd=cwd, timeout=900)

    verification_reason = ""
    update_report = {}
    if action == "update-app":
        report_path = Path(app_dir) / DEFAULT_UPDATE_REPORT
        verified, verification_reason, update_report = verify_update_report(
            report_path,
            status["checked_at"],
            expected_commit,
        )
        if not result["ok"] or not verified:
            result = {
                **result,
                "ok": False,
                "returncode": int(update_report.get("returncode", result.get("returncode", 1)) or 1),
                "stderr": verification_reason or result.get("stderr", ""),
            }

    finished = {
        **status,
        "finished_at": utc_now(),
        "returncode": result["returncode"],
        "stdout": compact(result["stdout"]),
        "stderr": compact(result["stderr"]),
        "status": "succeeded" if result["ok"] else "failed",
    }
    if verification_reason:
        finished["reason"] = verification_reason
    if update_report:
        finished["update_result"] = {
            key: update_report.get(key)
            for key in ("status", "reason", "starting_commit", "target_commit", "ending_commit")
        }
    aws_status = "SUCCEEDED" if result["ok"] else "FAILED"
    aws_details = {
        "action": action,
        "result": finished["status"],
        "returncode": str(result["returncode"]),
    }
    if verification_reason:
        aws_details["reason"] = compact(verification_reason, 100)
    client.update_job_execution(
        job_id,
        aws_status,
        aws_details,
    )
    write_status(finished, output_path)
    return finished


def parse_args():
    parser = argparse.ArgumentParser(description="Poll AWS IoT Jobs for MorsePi remote maintenance.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Station config JSON path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Local status JSON path.")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.once:
        raise SystemExit("Use --once. Repeated polling is handled by systemd timer.")

    status = run_once(args.config, args.output)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if status.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
