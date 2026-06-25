import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backup_data import DEFAULT_CONFIG_PATH, load_station_config, resolve_station_id, upload_backup_to_s3


DEFAULT_OUTPUT_PATH = Path("data/station_status.json")


def run_command(command):
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as error:
        return {
            "ok": False,
            "output": "",
            "error": str(error),
        }

    return {
        "ok": result.returncode == 0,
        "output": result.stdout.strip(),
        "error": result.stderr.strip(),
    }


def git_value(args):
    result = run_command(["git", *args])
    return result["output"] if result["ok"] else ""


def latest_backup_name(backup_dir):
    backup_dir = Path(backup_dir)
    backups = sorted(
        [path for path in backup_dir.glob("*.zip") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return backups[0].name if backups else ""


def service_state(service_name):
    if not service_name:
        return "unknown"

    result = run_command(["systemctl", "--user", "is-active", service_name])
    return result["output"] or ("inactive" if not result["ok"] else "unknown")


def build_status(station_id, backup_dir="data/backups", service_name="morse-station.service"):
    return {
        "app": "morsePi",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "git_branch": git_value(["rev-parse", "--abbrev-ref", "HEAD"]),
        "git_commit": git_value(["rev-parse", "--short", "HEAD"]),
        "hostname": socket.gethostname(),
        "last_backup": latest_backup_name(backup_dir),
        "service": {
            "name": service_name,
            "state": service_state(service_name),
        },
        "station_id": station_id,
    }


def write_status(status, output_path=DEFAULT_OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def parse_args():
    parser = argparse.ArgumentParser(description="Write Morse station status JSON.")
    parser.add_argument("--backup-dir", default="data/backups", help="Backup directory to inspect.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Station config JSON path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Status JSON output path.")
    parser.add_argument("--s3-uri", help="Optional S3 URI such as s3://morsepi-backups.")
    parser.add_argument("--service", default="morse-station.service", help="User systemd service name to check.")
    parser.add_argument("--station-id", help="Station id for status and cloud path.")
    parser.add_argument("--dry-run-s3", action="store_true", help="Print the S3 status destination without uploading.")
    return parser.parse_args()


def main():
    args = parse_args()
    station_id = resolve_station_id(args.station_id, args.config)
    config = load_station_config(args.config)
    s3_uri = args.s3_uri or config.get("backup_s3_uri", "")
    status = build_status(station_id, args.backup_dir, args.service)
    output_path = write_status(status, args.output)

    print(f"Wrote status: {output_path}")
    print(json.dumps(status, indent=2, sort_keys=True))

    if s3_uri:
        upload = upload_backup_to_s3(output_path, s3_uri, station_id, args.dry_run_s3)
        action = "Would upload" if args.dry_run_s3 else "Uploaded"
        print(f"{action} status to: {upload['destination']}")


if __name__ == "__main__":
    main()
