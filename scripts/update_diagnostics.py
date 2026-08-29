import argparse
import json
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paths import data_path


DEFAULT_APP_DIR = Path("/home/morse/morse-station")
DEFAULT_OUTPUT_PATH = data_path("update", "latest_update.json")
DEFAULT_DIAGNOSTIC_PATH = data_path("update", "latest_diagnostic.json")
DEFAULT_ARTIFACT_DIR = data_path("update", "diagnostics")
TERMINAL_STATUSES = {"blocked", "current", "failed", "rolled-back", "succeeded"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run_command(command, cwd=None, timeout=30):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(error)}
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def command_text(command, cwd=None):
    result = run_command(command, cwd=cwd)
    return result["stdout"] if result["ok"] else ""


def service_state(service_name):
    value = command_text(["systemctl", "--user", "is-active", service_name])
    return value or "unknown"


def tracked_changes(app_dir):
    output = command_text(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=app_dir,
    )
    return [line.rstrip() for line in output.splitlines() if line.strip()][:100]


def preserve_patch(app_dir, artifact_dir=DEFAULT_ARTIFACT_DIR):
    unstaged = run_command(["git", "diff", "--binary", "HEAD"], cwd=app_dir)
    staged = run_command(["git", "diff", "--binary", "--cached", "HEAD"], cwd=app_dir)
    content = "\n".join(part["stdout"] for part in (staged, unstaged) if part["stdout"])
    if not content:
        return ""

    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = artifact_dir / f"{timestamp}-tracked-changes.patch"
    path.write_text(content + "\n", encoding="utf-8")
    return str(path)


def build_diagnostic(app_dir=DEFAULT_APP_DIR, artifact_dir=DEFAULT_ARTIFACT_DIR, preserve=False):
    app_dir = Path(app_dir)
    changes = tracked_changes(app_dir)
    try:
        free_mb = round(shutil.disk_usage(app_dir).free / (1024 * 1024))
    except OSError:
        free_mb = None

    return {
        "app_dir": str(app_dir),
        "branch": command_text(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=app_dir),
        "browser_service_state": service_state("morse-station-browser.service"),
        "checked_at": utc_now(),
        "commit": command_text(["git", "rev-parse", "--short", "HEAD"], cwd=app_dir),
        "dirty": bool(changes),
        "disk_free_mb": free_mb,
        "format": "morsepi-update-diagnostic-v1",
        "hostname": socket.gethostname(),
        "patch_path": preserve_patch(app_dir, artifact_dir) if preserve and changes else "",
        "service_state": service_state("morse-station.service"),
        "tracked_changes": changes,
    }


def write_json(payload, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output_path)
    return output_path


def load_previous(output_path):
    try:
        value = json.loads(Path(output_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def record_update(
    status,
    reason="",
    starting_commit="",
    target_commit="",
    returncode=None,
    app_dir=DEFAULT_APP_DIR,
    output_path=DEFAULT_OUTPUT_PATH,
    artifact_dir=DEFAULT_ARTIFACT_DIR,
    preserve=False,
):
    now = utc_now()
    previous = load_previous(output_path)
    diagnostic = build_diagnostic(app_dir, artifact_dir, preserve)
    report = {
        "format": "morsepi-update-status-v1",
        "status": status,
        "reason": str(reason or ""),
        "started_at": (
            now
            if status == "in-progress" and reason == "starting"
            else str(previous.get("started_at") or now)
        ),
        "updated_at": now,
        "starting_commit": str(starting_commit or previous.get("starting_commit") or diagnostic["commit"]),
        "target_commit": str(target_commit or previous.get("target_commit") or ""),
        "ending_commit": diagnostic["commit"],
        "branch": diagnostic["branch"],
        "dirty": diagnostic["dirty"],
        "tracked_changes": diagnostic["tracked_changes"],
        "patch_path": diagnostic["patch_path"] or str(previous.get("patch_path") or ""),
        "disk_free_mb": diagnostic["disk_free_mb"],
        "service_state": diagnostic["service_state"],
        "browser_service_state": diagnostic["browser_service_state"],
    }
    if returncode is not None:
        report["returncode"] = int(returncode)
    if status in TERMINAL_STATUSES:
        report["finished_at"] = now
    write_json(report, output_path)
    return report


def parse_args():
    parser = argparse.ArgumentParser(description="Record safe MorsePi update diagnostics and results.")
    parser.add_argument("--app-dir", default=str(DEFAULT_APP_DIR))
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--output", default="")
    parser.add_argument("--status", default="diagnostic")
    parser.add_argument("--reason", default="")
    parser.add_argument("--starting-commit", default="")
    parser.add_argument("--target-commit", default="")
    parser.add_argument("--returncode", type=int)
    parser.add_argument("--preserve-patch", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.diagnose:
        diagnostic = build_diagnostic(args.app_dir, args.artifact_dir, args.preserve_patch)
        write_json(diagnostic, args.output or DEFAULT_DIAGNOSTIC_PATH)
        print(json.dumps(diagnostic, indent=2, sort_keys=True))
        return 0

    report = record_update(
        args.status,
        args.reason,
        args.starting_commit,
        args.target_commit,
        args.returncode,
        args.app_dir,
        args.output or DEFAULT_OUTPUT_PATH,
        args.artifact_dir,
        args.preserve_patch,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
