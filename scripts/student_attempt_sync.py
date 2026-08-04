import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from message_sync import AwsCliObjectStore
from scripts.backup_data import DEFAULT_CONFIG_PATH, load_station_config


DEFAULT_DATA_DIR = Path("data")
DEFAULT_OUTPUT_PATH = DEFAULT_DATA_DIR / "sync_reports" / "latest_attempt_sync.json"
ATTEMPT_FILES = {
    "practice": "practice_attempts.jsonl",
    "words": "word_attempts.jsonl",
    "bonus": "bonus_attempts.jsonl",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default

    return loaded


def load_profiles(data_dir):
    profiles = read_json(Path(data_dir) / "student_profiles.json", [])
    if not isinstance(profiles, list):
        return []

    normalized = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        if profile.get("disposable") or profile.get("guest"):
            continue
        student_id = str(profile.get("id") or "").strip()
        if not student_id:
            continue
        normalized.append({
            "id": student_id,
            "name": str(profile.get("name") or student_id).strip() or student_id,
        })
    return normalized


def iter_jsonl(path):
    path = Path(path)
    if not path.exists():
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for line_number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            yield line_number, None
            continue
        yield line_number, record if isinstance(record, dict) else None


def canonical_payload(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def legacy_attempt_id(kind, station_id, student_id, line_number, record):
    parts = [
        "legacy",
        kind,
        str(record.get("station_id") or station_id),
        str(record.get("student_id") or student_id),
        str(record.get("practice_session_id") or record.get("session_id") or ""),
        str(record.get("timestamp") or ""),
        str(record.get("target") or record.get("word") or ""),
        str(record.get("correct")),
        str(line_number),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"legacy-{digest[:32]}"


def attempt_identity(kind, station_id, student_id, line_number, record):
    attempt_id = str(record.get("attempt_id") or "").strip()
    if attempt_id:
        return attempt_id, False
    return legacy_attempt_id(kind, station_id, student_id, line_number, record), True


def cloud_key(student_id, kind, attempt_id):
    return f"students/{student_id}/attempts/{kind}/{attempt_id}.json"


def local_attempts(data_dir, station_id):
    attempts = []
    malformed = []

    for profile in load_profiles(data_dir):
        student_id = profile["id"]
        student_dir = Path(data_dir) / "students" / student_id

        for kind, filename in ATTEMPT_FILES.items():
            for line_number, record in iter_jsonl(student_dir / filename):
                if record is None:
                    malformed.append({
                        "file": filename,
                        "line": line_number,
                        "student_id": student_id,
                    })
                    continue
                identity, legacy = attempt_identity(kind, station_id, student_id, line_number, record)
                payload = dict(record)
                payload.setdefault("attempt_id", identity)
                payload.setdefault("station_id", station_id)
                payload.setdefault("student_id", student_id)
                attempts.append({
                    "attempt_id": identity,
                    "canonical": canonical_payload(payload),
                    "kind": kind,
                    "key": cloud_key(student_id, kind, identity),
                    "legacy_identity": legacy,
                    "payload": payload,
                    "student_id": student_id,
                })

    return attempts, malformed


def summarize_local(attempts):
    by_key = {}
    duplicates = []
    conflicts = []

    for attempt in attempts:
        existing = by_key.get(attempt["key"])
        if existing is None:
            by_key[attempt["key"]] = attempt
            continue
        if existing["canonical"] == attempt["canonical"]:
            duplicates.append(attempt["key"])
        else:
            conflicts.append(attempt["key"])

    by_student = {}
    for attempt in by_key.values():
        student = by_student.setdefault(attempt["student_id"], {
            "bonus": 0,
            "legacy_identity": 0,
            "practice": 0,
            "words": 0,
        })
        student[attempt["kind"]] += 1
        if attempt["legacy_identity"]:
            student["legacy_identity"] += 1

    return by_key, by_student, sorted(set(duplicates)), sorted(set(conflicts))


def cloud_existing_keys(store, students):
    existing = set()
    errors = []

    if store is None:
        return existing, errors

    for student in students:
        student_id = student["id"]
        for kind in ATTEMPT_FILES:
            prefix = f"students/{student_id}/attempts/{kind}/"
            try:
                existing.update(key for key in store.list_keys(prefix) if key.endswith(".json"))
            except Exception as exc:
                errors.append({
                    "kind": kind,
                    "student_id": student_id,
                    "error": str(exc).splitlines()[-1][:240],
                })

    return existing, errors


def build_report(data_dir=DEFAULT_DATA_DIR, config_path=DEFAULT_CONFIG_PATH, check_cloud=True, store=None):
    data_dir = Path(data_dir)
    config = load_station_config(config_path)
    station_id = str(config.get("station_id") or "unknown-station")
    attempts, malformed = local_attempts(data_dir, station_id)
    by_key, by_student, duplicates, conflicts = summarize_local(attempts)
    students = load_profiles(data_dir)
    s3_uri = config.get("progress_s3_uri") or config.get("backup_s3_uri") or ""
    if store is None and check_cloud and s3_uri:
        store = AwsCliObjectStore(s3_uri)
    existing, cloud_errors = cloud_existing_keys(store, students)
    upload_keys = sorted(key for key in by_key if key not in existing)

    return {
        "app": "morsePi",
        "cloud_checked": bool(store),
        "cloud_errors": cloud_errors,
        "conflicts": conflicts,
        "duplicate_local_records": duplicates,
        "format": "morsepi-attempt-sync-dry-run-v1",
        "generated_at": utc_now(),
        "malformed_records": malformed,
        "station_id": station_id,
        "students": by_student,
        "summary": {
            "cloud_existing": len(existing),
            "local_conflicts": len(conflicts),
            "local_duplicates": len(duplicates),
            "local_unique_attempts": len(by_key),
            "malformed_records": len(malformed),
            "would_upload": len(upload_keys),
        },
        "would_upload": upload_keys[:200],
    }


def write_report(report, output_path=DEFAULT_OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def parse_args():
    parser = argparse.ArgumentParser(description="Dry-run student attempt sync without writing student files.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Station config JSON path.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Data directory to inspect.")
    parser.add_argument("--no-cloud", action="store_true", help="Do not query S3; report local upload candidates only.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Report JSON output path.")
    return parser.parse_args()


def main():
    args = parse_args()
    report = build_report(args.data_dir, args.config, check_cloud=not args.no_cloud)
    output = write_report(report, args.output)

    print(f"Wrote sync dry-run report: {output}")
    print(f"Station id: {report['station_id']}")
    print(f"Local unique attempts: {report['summary']['local_unique_attempts']}")
    print(f"Would upload: {report['summary']['would_upload']}")
    print(f"Cloud errors: {len(report['cloud_errors'])}")
    print(f"Conflicts: {report['summary']['local_conflicts']}")


if __name__ == "__main__":
    main()
