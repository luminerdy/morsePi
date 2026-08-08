import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paths import data_path
from student_identity import enrich_student_identity, family_registry_by_id


def utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.student-uuid.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if path.exists():
        shutil.copymode(path, temporary)
    temporary.replace(path)


def enrich_roster(values, registry):
    if not isinstance(values, list):
        return values
    enriched = []
    for item in values:
        profile = {"id": item, "name": item} if isinstance(item, str) else dict(item)
        if profile.get("guest") or profile.get("disposable") or profile.get("id") == "guest":
            enriched.append(profile)
        else:
            enriched.append(enrich_student_identity(profile, registry=registry))
    return enriched


def migrate_file(path, transform, backup_dir):
    path = Path(path)
    if not path.exists():
        return False
    original = read_json(path, None)
    if original is None:
        raise ValueError(f"Cannot migrate invalid JSON: {path}")
    updated = transform(original)
    if updated == original:
        return False
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_dir / path.name)
    atomic_write_json(path, updated)
    return True


def migrate(data_dir, config_path):
    data_dir = Path(data_dir)
    config_path = Path(config_path)
    registry = family_registry_by_id()
    backup_dir = data_dir / "identity_migration_backups" / utc_stamp()
    changed = []

    def station_config_transform(config):
        updated = dict(config)
        updated["students"] = enrich_roster(config.get("students", []), registry)
        updated["family_students"] = enrich_roster(config.get("family_students", []), registry)
        return updated

    if migrate_file(config_path, station_config_transform, backup_dir):
        changed.append(str(config_path))

    profiles_path = data_dir / "student_profiles.json"
    if migrate_file(profiles_path, lambda profiles: enrich_roster(profiles, registry), backup_dir):
        changed.append(str(profiles_path))

    students_dir = data_dir / "students"
    for profile_path in sorted(students_dir.glob("*/profile.json")) if students_dir.exists() else []:
        def profile_transform(profile):
            if profile.get("guest") or profile.get("disposable") or profile.get("id") == "guest":
                return profile
            return enrich_student_identity(profile, registry=registry)

        student_backup = backup_dir / "students" / profile_path.parent.name
        if migrate_file(profile_path, profile_transform, student_backup):
            changed.append(str(profile_path))

    if not changed and backup_dir.exists():
        shutil.rmtree(backup_dir)
    return {"changed": changed, "backup_path": str(backup_dir) if changed else ""}


def main():
    parser = argparse.ArgumentParser(description="Add canonical student UUIDs without moving data.")
    parser.add_argument("--data-dir", default=str(data_path()))
    parser.add_argument("--config", default=str(data_path("station_config.json")))
    args = parser.parse_args()
    print(json.dumps(migrate(args.data_dir, args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
