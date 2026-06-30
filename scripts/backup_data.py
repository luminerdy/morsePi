import argparse
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_KEEP = 30
DEFAULT_DATA_DIR = Path("data")
DEFAULT_BACKUP_DIR = DEFAULT_DATA_DIR / "backups"
DEFAULT_CONFIG_PATH = DEFAULT_DATA_DIR / "station_config.json"

INCLUDE_PATHS = [
    "student_profiles.json",
    "timing_settings.json",
    "students",
]


def timestamp_key():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def load_station_config(config_path=DEFAULT_CONFIG_PATH):
    config_path = Path(config_path)
    if not config_path.exists():
        return {}

    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return loaded if isinstance(loaded, dict) else {}


def resolve_station_id(station_id=None, config_path=DEFAULT_CONFIG_PATH):
    if station_id:
        return station_id

    config = load_station_config(config_path)
    return str(config.get("station_id") or "unknown-station")


def normalize_s3_uri(value):
    if not value:
        return ""

    value = str(value).strip()
    if not value.startswith("s3://"):
        raise ValueError("S3 URI must start with s3://")

    return value.rstrip("/")


def iter_backup_sources(data_dir):
    for relative in INCLUDE_PATHS:
        source = data_dir / relative
        if not source.exists():
            continue

        if source.is_file():
            yield source, Path("data") / relative
            continue

        for path in sorted(source.rglob("*")):
            if path.is_file():
                yield path, Path("data") / relative / path.relative_to(source)


def build_manifest(data_dir, files, station_id="unknown-station"):
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(data_dir),
        "files": [str(archive_path).replace("\\", "/") for archive_path in files],
        "format": "morse-station-data-backup-v1",
        "station_id": station_id,
    }


def create_backup(data_dir=DEFAULT_DATA_DIR, backup_dir=DEFAULT_BACKUP_DIR, label="auto", station_id=None, config_path=DEFAULT_CONFIG_PATH):
    data_dir = Path(data_dir)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    station_id = resolve_station_id(station_id, config_path)
    safe_label = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in label).strip("-") or "auto"
    safe_station = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in station_id).strip("-") or "unknown-station"
    backup_path = backup_dir / f"{timestamp_key()}-{safe_station}-{safe_label}.zip"
    sources = list(iter_backup_sources(data_dir))
    archive_paths = [archive_path for _, archive_path in sources]

    with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as backup_zip:
        for source, archive_path in sources:
            backup_zip.write(source, archive_path.as_posix())

        backup_zip.writestr(
            "manifest.json",
            json.dumps(build_manifest(data_dir, archive_paths, station_id), indent=2, sort_keys=True),
        )

    return backup_path


def station_s3_destination(s3_uri, station_id, key):
    s3_uri = normalize_s3_uri(s3_uri)
    safe_station = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in (station_id or "unknown-station")).strip("-") or "unknown-station"
    clean_key = str(key).replace("\\", "/").lstrip("/")
    return f"{s3_uri}/stations/{safe_station}/{clean_key}"


def upload_file_to_s3(source_path, s3_uri, station_id=None, key=None, dry_run=False):
    source_path = Path(source_path)
    key = key or source_path.name
    destination = station_s3_destination(s3_uri, station_id, key)
    command = ["aws", "s3", "cp", str(source_path), destination]

    if dry_run:
        return {
            "command": command,
            "destination": destination,
            "uploaded": False,
        }

    subprocess.run(command, check=True)
    return {
        "command": command,
        "destination": destination,
        "uploaded": True,
    }


def upload_backup_to_s3(backup_path, s3_uri, station_id=None, dry_run=False):
    key = f"backups/{Path(backup_path).name}"
    return upload_file_to_s3(backup_path, s3_uri, station_id, key, dry_run)


def upload_status_to_s3(status_path, s3_uri, station_id=None, dry_run=False):
    return upload_file_to_s3(status_path, s3_uri, station_id, "status/station_status.json", dry_run)


def upload_snapshot_to_s3(snapshot_path, s3_uri, station_id=None, dry_run=False):
    key = f"snapshots/{Path(snapshot_path).name}"
    return upload_file_to_s3(snapshot_path, s3_uri, station_id, key, dry_run)


def rotate_backups(backup_dir=DEFAULT_BACKUP_DIR, keep=DEFAULT_KEEP):
    backup_dir = Path(backup_dir)
    if keep <= 0 or not backup_dir.exists():
        return []

    backups = sorted(
        [path for path in backup_dir.glob("*.zip") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    removed = []

    for old_backup in backups[keep:]:
        old_backup.unlink()
        removed.append(old_backup)

    return removed


def restore_backup(backup_path, restore_root):
    backup_path = Path(backup_path)
    restore_root = Path(restore_root)
    restore_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(backup_path) as backup_zip:
        backup_zip.extractall(restore_root)

    return restore_root


def parse_args():
    parser = argparse.ArgumentParser(description="Back up Morse station local data.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Data directory to back up.")
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Directory where backup zips are stored.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Station config JSON path.")
    parser.add_argument("--label", default="auto", help="Short label added to the backup filename.")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="Number of backup zips to keep.")
    parser.add_argument("--station-id", help="Station id for manifests and cloud backup paths.")
    parser.add_argument("--s3-uri", help="Optional S3 URI such as s3://morsepi-backups.")
    parser.add_argument("--dry-run-s3", action="store_true", help="Print the S3 upload destination without uploading.")
    parser.add_argument("--restore", help="Restore a backup zip into --restore-root instead of creating a backup.")
    parser.add_argument("--restore-root", default="restored-data", help="Directory used with --restore.")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.restore:
        restored = restore_backup(args.restore, args.restore_root)
        print(f"Restored {args.restore} into {restored}")
        return

    station_id = resolve_station_id(args.station_id, args.config)
    config = load_station_config(args.config)
    s3_uri = args.s3_uri or config.get("backup_s3_uri", "")
    backup_path = create_backup(args.data_dir, args.backup_dir, args.label, station_id, args.config)
    removed = rotate_backups(args.backup_dir, args.keep)
    print(f"Created backup: {backup_path}")
    print(f"Station id: {station_id}")

    if removed:
        print("Removed old backups:")
        for path in removed:
            print(f"- {path}")

    if s3_uri:
        upload = upload_backup_to_s3(backup_path, s3_uri, station_id, args.dry_run_s3)
        action = "Would upload" if args.dry_run_s3 else "Uploaded"
        print(f"{action} backup to: {upload['destination']}")


if __name__ == "__main__":
    main()
