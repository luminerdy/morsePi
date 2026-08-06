import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from message_sync import AwsCliObjectStore
from paths import data_path
from scripts.backup_data import DEFAULT_CONFIG_PATH, load_station_config


DEFAULT_DATA_DIR = data_path()
DEFAULT_OUTPUT_PATH = DEFAULT_DATA_DIR / "family_progress" / "latest.json"
DEFAULT_STATION_IDS = (
    "pappy-test-station",
    "astrid-liara-station",
    "campbell-olivea-station",
)
MODE_LABELS = {
    "learn": "Learn",
    "send": "Send",
    "read": "Read",
    "listen": "Listen",
    "echo": "Echo",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default

    return loaded


def station_ids_from_config(config):
    raw = config.get("family_stations")
    station_ids = []

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                station_id = item.strip()
            elif isinstance(item, dict):
                station_id = str(item.get("id") or item.get("station_id") or "").strip()
            else:
                station_id = ""
            if station_id and station_id not in station_ids:
                station_ids.append(station_id)

    return station_ids or list(DEFAULT_STATION_IDS)


def snapshot_key(station_id):
    return f"stations/{station_id}/snapshots/latest_progress.json"


def snapshot_is_valid(snapshot, station_id):
    return (
        isinstance(snapshot, dict)
        and snapshot.get("format") == "morsepi-progress-snapshot-v1"
        and snapshot.get("station_id") == station_id
        and isinstance(snapshot.get("students"), list)
    )


def local_snapshot_path(data_dir, station_id):
    return Path(data_dir) / "family_progress" / "station_snapshots" / f"{station_id}.json"


def load_station_snapshots(data_dir, config, store=None):
    data_dir = Path(data_dir)
    station_ids = station_ids_from_config(config)
    s3_uri = config.get("progress_s3_uri") or config.get("backup_s3_uri") or ""
    store = store or (AwsCliObjectStore(s3_uri) if s3_uri else None)
    snapshots = []
    station_status = []

    for station_id in station_ids:
        snapshot = None
        error = ""
        source = "s3"

        if store:
            try:
                snapshot = store.get_json(snapshot_key(station_id), default=None)
            except Exception as exc:  # AWS CLI and permission errors are reported as unavailable.
                error = str(exc).splitlines()[-1][:240]

        if snapshot is None:
            local_path = local_snapshot_path(data_dir, station_id)
            snapshot = load_json(local_path, None)
            source = "local-cache" if snapshot is not None else "unavailable"

        if snapshot_is_valid(snapshot, station_id):
            snapshots.append(snapshot)
            station_status.append({
                "error": "",
                "generated_at": snapshot.get("generated_at", ""),
                "source": source,
                "station_id": station_id,
                "students": len(snapshot.get("students", [])),
                "available": True,
            })
            local_path = local_snapshot_path(data_dir, station_id)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
            continue

        station_status.append({
            "error": error or "No valid snapshot found.",
            "generated_at": "",
            "source": source,
            "station_id": station_id,
            "students": 0,
            "available": False,
        })

    return snapshots, station_status


def mode_score(student, mode):
    modes = student.get("practice", {}).get("modes", {})
    score = modes.get(mode, {}) if isinstance(modes, dict) else {}
    return {
        "accuracy": int(score.get("accuracy", 0) or 0),
        "attempts": int(score.get("attempts", 0) or 0),
        "label": MODE_LABELS.get(mode, mode.title()),
        "mastery": int(score.get("mastery", 0) or 0),
        "mode": mode,
    }


def latest_key(item):
    return str(item.get("latest_activity_at") or item.get("generated_at") or "")


def student_rollup(snapshot, student):
    learning_state = student.get("learning_state") if isinstance(student.get("learning_state"), dict) else {}
    learning_letters = learning_state.get("learning_letters") or learning_state.get("current_letters") or []
    if not isinstance(learning_letters, list):
        learning_letters = []

    return {
        "active_letters": student.get("active_letters", []),
        "generated_at": snapshot.get("generated_at", ""),
        "latest_activity_at": student.get("latest_activity_at") or snapshot.get("generated_at", ""),
        "learning_letters": [str(letter).upper() for letter in learning_letters],
        "modes": [mode_score(student, mode) for mode in MODE_LABELS],
        "name": student.get("name") or student.get("student_id"),
        "source_hostname": snapshot.get("hostname", ""),
        "source_station_id": snapshot.get("station_id", ""),
        "student_id": student.get("student_id"),
        "words": student.get("words", {}),
        "bonus": student.get("bonus", {}),
    }


def build_family_progress(snapshots, station_status):
    latest_by_student = {}
    all_sources = {}

    for snapshot in snapshots:
        for student in snapshot.get("students", []):
            if not isinstance(student, dict) or not student.get("student_id"):
                continue
            rollup = student_rollup(snapshot, student)
            student_id = rollup["student_id"]
            all_sources.setdefault(student_id, []).append(rollup)
            current = latest_by_student.get(student_id)
            if current is None or latest_key(rollup) >= latest_key(current):
                latest_by_student[student_id] = rollup

    students = []
    for student_id, latest in sorted(latest_by_student.items(), key=lambda item: item[1]["name"]):
        sources = sorted(all_sources.get(student_id, []), key=latest_key, reverse=True)
        latest = dict(latest)
        latest["source_count"] = len(sources)
        latest["sources"] = [
            {
                "latest_activity_at": source["latest_activity_at"],
                "source_station_id": source["source_station_id"],
            }
            for source in sources
        ]
        students.append(latest)

    return {
        "app": "morsePi",
        "format": "morsepi-family-progress-v1",
        "generated_at": utc_now(),
        "station_status": station_status,
        "students": students,
    }


def write_family_progress(progress, output_path=DEFAULT_OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(progress, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def refresh_family_progress(data_dir=DEFAULT_DATA_DIR, config_path=DEFAULT_CONFIG_PATH, output_path=DEFAULT_OUTPUT_PATH, store=None):
    config = load_station_config(config_path)
    snapshots, station_status = load_station_snapshots(data_dir, config, store)
    progress = build_family_progress(snapshots, station_status)
    output = write_family_progress(progress, output_path)
    return progress, output


def parse_args():
    parser = argparse.ArgumentParser(description="Build a read-only family progress view from station snapshots.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Station config JSON path.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Data directory to use.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Family progress JSON output path.")
    return parser.parse_args()


def main():
    args = parse_args()
    progress, output = refresh_family_progress(args.data_dir, args.config, args.output)
    available = sum(1 for station in progress["station_status"] if station["available"])
    print(f"Wrote family progress: {output}")
    print(f"Stations available: {available}/{len(progress['station_status'])}")
    print(f"Students: {len(progress['students'])}")


if __name__ == "__main__":
    main()
