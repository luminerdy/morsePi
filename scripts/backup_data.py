import argparse
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_KEEP = 30
DEFAULT_DATA_DIR = Path("data")
DEFAULT_BACKUP_DIR = DEFAULT_DATA_DIR / "backups"

INCLUDE_PATHS = [
    "student_profiles.json",
    "timing_settings.json",
    "students",
]


def timestamp_key():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


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


def build_manifest(data_dir, files):
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(data_dir),
        "files": [str(archive_path).replace("\\", "/") for archive_path in files],
        "format": "morse-station-data-backup-v1",
    }


def create_backup(data_dir=DEFAULT_DATA_DIR, backup_dir=DEFAULT_BACKUP_DIR, label="auto"):
    data_dir = Path(data_dir)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    safe_label = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in label).strip("-") or "auto"
    backup_path = backup_dir / f"{timestamp_key()}-{safe_label}.zip"
    sources = list(iter_backup_sources(data_dir))
    archive_paths = [archive_path for _, archive_path in sources]

    with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as backup_zip:
        for source, archive_path in sources:
            backup_zip.write(source, archive_path.as_posix())

        backup_zip.writestr(
            "manifest.json",
            json.dumps(build_manifest(data_dir, archive_paths), indent=2, sort_keys=True),
        )

    return backup_path


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
    parser.add_argument("--label", default="auto", help="Short label added to the backup filename.")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="Number of backup zips to keep.")
    parser.add_argument("--restore", help="Restore a backup zip into --restore-root instead of creating a backup.")
    parser.add_argument("--restore-root", default="restored-data", help="Directory used with --restore.")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.restore:
        restored = restore_backup(args.restore, args.restore_root)
        print(f"Restored {args.restore} into {restored}")
        return

    backup_path = create_backup(args.data_dir, args.backup_dir, args.label)
    removed = rotate_backups(args.backup_dir, args.keep)
    print(f"Created backup: {backup_path}")

    if removed:
        print("Removed old backups:")
        for path in removed:
            print(f"- {path}")


if __name__ == "__main__":
    main()
