import argparse
import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paths import data_path
from scripts.backup_data import DEFAULT_CONFIG_PATH, load_station_config, resolve_station_id, upload_snapshot_to_s3
from student_identity import enrich_student_identity


DEFAULT_DATA_DIR = data_path()
DEFAULT_OUTPUT_PATH = DEFAULT_DATA_DIR / "snapshots" / "latest_progress.json"
PRACTICE_MODES = ("learn", "send", "read", "listen", "echo")
STARTER_PRACTICE_LETTERS = ["E", "T", "A", "N", "I", "M"]
LEARN_READY_ATTEMPTS = 10
LEARN_READY_STRENGTH = 70
LEARN_READY_REST_HOURS = 3
LETTER_UNLOCK_GROUPS = [
    {"letters": ["S", "O"], "label": "Signal Builder"},
    {"letters": ["R", "K"], "label": "Rhythm Builder"},
    {"letters": ["D", "U"], "label": "Relay Builder"},
    {"letters": ["C", "W", "H", "L"], "label": "Word Builder"},
    {"letters": ["P", "F", "Y", "G"], "label": "Pattern Builder"},
    {"letters": ["B", "V", "J", "X"], "label": "Code Builder"},
    {"letters": ["Q", "Z"], "label": "Alphabet Builder"},
    {"letters": ["1", "2", "3", "4", "5"], "label": "Number Builder"},
    {"letters": ["6", "7", "8", "9", "0"], "label": "Full Station Operator"},
]
ALL_PRACTICE_LETTERS = STARTER_PRACTICE_LETTERS + [
    letter
    for group in LETTER_UNLOCK_GROUPS
    for letter in group["letters"]
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default

    return loaded


def load_profiles(data_dir):
    profiles = load_json(Path(data_dir) / "student_profiles.json", [])
    if not isinstance(profiles, list):
        profiles = []

    normalized = []
    seen = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        student_id = str(profile.get("id") or "").strip()
        if not student_id or student_id in seen:
            continue
        normalized.append(enrich_student_identity({
            "id": student_id,
            "name": str(profile.get("name") or student_id).strip() or student_id,
            "disposable": bool(profile.get("disposable") or profile.get("guest")),
            "student_uuid": profile.get("student_uuid", ""),
        }))
        seen.add(student_id)

    return normalized


def normalize_record(value):
    if not isinstance(value, dict):
        value = {}

    attempts = max(0, int(value.get("attempts", 0) or 0))
    correct = max(0, min(int(value.get("correct", 0) or 0), attempts))
    strength = max(0.0, min(float(value.get("strength", 0.0) or 0.0), 1.0))

    return {
        "attempts": attempts,
        "correct": correct,
        "last_seen": str(value.get("last_seen", "") or ""),
        "strength": strength,
    }


def iter_progress_records(progress):
    if not isinstance(progress, dict):
        return

    for letter, value in progress.items():
        if not isinstance(value, dict):
            continue
        if "attempts" in value or "correct" in value or "strength" in value:
            yield str(letter), "send", normalize_record(value)
            continue
        for mode, record in value.items():
            yield str(letter), str(mode), normalize_record(record)


def summarize_progress(progress):
    by_mode = {
        mode: {
            "attempts": 0,
            "correct": 0,
            "letters": 0,
            "last_seen": "",
            "mastery": 0,
        }
        for mode in PRACTICE_MODES
    }
    strengths = {mode: [] for mode in PRACTICE_MODES}
    letters_seen = set()

    for letter, mode, record in iter_progress_records(progress):
        letters_seen.add(letter)
        if mode not in by_mode:
            by_mode[mode] = {
                "attempts": 0,
                "correct": 0,
                "letters": 0,
                "last_seen": "",
                "mastery": 0,
            }
            strengths[mode] = []

        by_mode[mode]["attempts"] += record["attempts"]
        by_mode[mode]["correct"] += record["correct"]
        if record["attempts"] > 0:
            by_mode[mode]["letters"] += 1
            strengths[mode].append(record["strength"])
        if record["last_seen"] > by_mode[mode]["last_seen"]:
            by_mode[mode]["last_seen"] = record["last_seen"]

    latest_activity = ""
    for mode, summary in by_mode.items():
        attempts = summary["attempts"]
        summary["accuracy"] = int(round((summary["correct"] / attempts) * 100)) if attempts else 0
        summary["mastery"] = int(round((sum(strengths[mode]) / len(strengths[mode])) * 100)) if strengths[mode] else 0
        latest_activity = max(latest_activity, summary["last_seen"])

    return {
        "letters_seen": sorted(letters_seen),
        "latest_activity_at": latest_activity,
        "modes": by_mode,
    }


def summarize_jsonl(path, word_field="target"):
    summary = {
        "attempts": 0,
        "correct": 0,
        "last_seen": "",
        "recent_items": [],
    }
    recent = []

    path = Path(path)
    if not path.exists():
        summary["accuracy"] = 0
        return summary

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        summary["accuracy"] = 0
        return summary

    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        summary["attempts"] += 1
        if record.get("correct"):
            summary["correct"] += 1
        timestamp = str(record.get("timestamp") or record.get("created_at") or "")
        summary["last_seen"] = max(summary["last_seen"], timestamp)
        item = str(record.get(word_field) or record.get("word") or record.get("target") or "").strip()
        if item:
            recent.append(item)

    summary["accuracy"] = int(round((summary["correct"] / summary["attempts"]) * 100)) if summary["attempts"] else 0
    summary["recent_items"] = recent[-5:]
    return summary


def step_key(step):
    return "".join(step["letters"])


def learn_record_ready(progress, letter):
    letter_progress = progress.get(letter, {}) if isinstance(progress, dict) else {}
    learn_record = letter_progress.get("learn", {}) if isinstance(letter_progress, dict) else {}
    return (
        int(learn_record.get("correct", 0) or 0) >= LEARN_READY_ATTEMPTS
        and float(learn_record.get("strength", 0) or 0) * 100 >= LEARN_READY_STRENGTH
    )


def learning_rest_ready(group_state, now=None):
    started_at = parse_utc(group_state.get("first_learning_started_at", ""))
    if started_at is None:
        return False
    elapsed = (now or datetime.now(timezone.utc)) - started_at
    return elapsed.total_seconds() >= LEARN_READY_REST_HOURS * 60 * 60


def active_letters_from_learning(progress, learning_state):
    groups = learning_state.get("groups", {}) if isinstance(learning_state, dict) else {}
    active = list(STARTER_PRACTICE_LETTERS)

    for step in LETTER_UNLOCK_GROUPS:
        group_state = groups.get(step_key(step)) if isinstance(groups, dict) else None
        if not isinstance(group_state, dict):
            break
        if not learning_rest_ready(group_state):
            break
        if not all(learn_record_ready(progress, letter) for letter in step["letters"]):
            break
        active.extend(letter for letter in step["letters"] if letter not in active)

    return [letter for letter in ALL_PRACTICE_LETTERS if letter in active]


def load_active_letters(data_dir, student_id, progress, learning_state):
    active = active_letters_from_learning(progress, learning_state)
    if active != STARTER_PRACTICE_LETTERS:
        return active

    local_summary = load_json(
        Path(data_dir) / "message_sync" / "local_summaries" / f"{student_id}.json",
        {},
    )
    active_letters = local_summary.get("active_letters") if isinstance(local_summary, dict) else []
    if isinstance(active_letters, list):
        letters = [str(letter).upper() for letter in active_letters if str(letter).strip()]
        if letters:
            return [letter for letter in ALL_PRACTICE_LETTERS if letter in set(letters)]

    return summarize_progress(progress)["letters_seen"]


def student_snapshot(data_dir, profile):
    student_id = profile["id"]
    student_dir = Path(data_dir) / "students" / student_id
    progress = load_json(student_dir / "practice_progress.json", {})
    learning_state = load_json(student_dir / "learning_state.json", {})
    progress_summary = summarize_progress(progress)
    words = summarize_jsonl(student_dir / "word_attempts.jsonl", "word")
    bonus = summarize_jsonl(student_dir / "bonus_attempts.jsonl", "target")
    latest_activity = max(
        progress_summary["latest_activity_at"],
        words["last_seen"],
        bonus["last_seen"],
    )

    return {
        "active_letters": load_active_letters(data_dir, student_id, progress, learning_state),
        "disposable": profile["disposable"],
        "generated_at": utc_now(),
        "learning_state": learning_state if isinstance(learning_state, dict) else {},
        "latest_activity_at": latest_activity,
        "name": profile["name"],
        "practice": progress_summary,
        "student_id": student_id,
        "student_uuid": profile.get("student_uuid", ""),
        "words": words,
        "bonus": bonus,
    }


def build_snapshot(data_dir=DEFAULT_DATA_DIR, station_id=None, config_path=DEFAULT_CONFIG_PATH):
    data_dir = Path(data_dir)
    station_id = resolve_station_id(station_id, config_path)
    students = [
        student_snapshot(data_dir, profile)
        for profile in load_profiles(data_dir)
        if not profile["disposable"]
    ]

    return {
        "app": "morsePi",
        "format": "morsepi-progress-snapshot-v1",
        "generated_at": utc_now(),
        "hostname": socket.gethostname(),
        "station_id": station_id,
        "students": students,
    }


def write_snapshot(snapshot, output_path=DEFAULT_OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def parse_args():
    parser = argparse.ArgumentParser(description="Write a read-only Morse student progress snapshot.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Station config JSON path.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Data directory to inspect.")
    parser.add_argument("--dry-run-s3", action="store_true", help="Print the S3 snapshot destination without uploading.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Snapshot JSON output path.")
    parser.add_argument("--s3-uri", help="Optional S3 URI such as s3://morsepi-backups.")
    parser.add_argument("--station-id", help="Station id for snapshot and cloud path.")
    return parser.parse_args()


def main():
    args = parse_args()
    station_id = resolve_station_id(args.station_id, args.config)
    config = load_station_config(args.config)
    s3_uri = args.s3_uri or config.get("backup_s3_uri", "")
    snapshot = build_snapshot(args.data_dir, station_id, args.config)
    output_path = write_snapshot(snapshot, args.output)

    print(f"Wrote snapshot: {output_path}")
    print(f"Station id: {station_id}")
    print(f"Students: {len(snapshot['students'])}")

    if s3_uri:
        upload = upload_snapshot_to_s3(output_path, s3_uri, station_id, args.dry_run_s3)
        action = "Would upload" if args.dry_run_s3 else "Uploaded"
        print(f"{action} snapshot to: {upload['destination']}")


if __name__ == "__main__":
    main()
