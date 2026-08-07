import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from message_sync import AwsCliObjectStore
from paths import data_path
from scripts.backup_data import DEFAULT_CONFIG_PATH, load_station_config


DEFAULT_DATA_DIR = data_path()
DEFAULT_OUTPUT_PATH = DEFAULT_DATA_DIR / "sync_reports" / "latest_attempt_sync.json"
DEFAULT_STATUS_PATH = DEFAULT_DATA_DIR / "sync_reports" / "latest_sync_status.json"
DEFAULT_ACTIVITY_PATH = DEFAULT_DATA_DIR / "app_activity.json"
DEFAULT_LOCK_PATH = DEFAULT_DATA_DIR / "sync_reports" / "student_attempt_sync.lock"
DEFAULT_IDLE_MINUTES = 10
ATTEMPT_FILES = {
    "practice": "practice_attempts.jsonl",
    "words": "word_attempts.jsonl",
    "bonus": "bonus_attempts.jsonl",
}
PRACTICE_MODES = {"send", "read", "listen", "echo", "learn"}
LETTER_UNLOCK_STEPS = [
    {"letters": ["S", "O"], "threshold": 100},
    {"letters": ["R", "K"], "threshold": 85},
    {"letters": ["D", "U"], "threshold": 85},
    {"letters": ["C", "L"], "threshold": 85},
    {"letters": ["P", "F"], "threshold": 85},
    {"letters": ["W", "Y"], "threshold": 85},
    {"letters": ["B", "G"], "threshold": 85},
    {"letters": ["V", "H"], "threshold": 85},
    {"letters": ["Q", "Z"], "threshold": 85},
    {"letters": ["X", "J"], "threshold": 85},
    {"letters": ["1", "2", "3"], "threshold": 85},
    {"letters": ["4", "5", "6"], "threshold": 85},
    {"letters": ["7", "8", "9", "0"], "threshold": 85},
]
LEARN_READY_ATTEMPTS = 10
LEARN_READY_STRENGTH = 70


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


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default

    return loaded


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_sync_status(data_dir, status, output_path=None):
    payload = {
        "app": "morsePi",
        "format": "morsepi-student-sync-status-v1",
        "updated_at": utc_now(),
    }
    payload.update(status)
    return write_json(output_path or Path(data_dir) / "sync_reports" / "latest_sync_status.json", payload)


def activity_status(data_dir, idle_minutes=DEFAULT_IDLE_MINUTES, now=None):
    activity = read_json(Path(data_dir) / "app_activity.json", {})
    last_activity_at = parse_utc(activity.get("last_activity_at", ""))
    now = now or datetime.now(timezone.utc)
    if last_activity_at is None:
        return {
            "active": False,
            "idle_minutes": None,
            "last_activity_at": "",
            "reason": "no-activity-marker",
        }
    idle_for = now - last_activity_at
    idle_minutes_actual = max(0, int(idle_for.total_seconds() // 60))
    active = idle_for < timedelta(minutes=max(0, idle_minutes))
    return {
        "active": active,
        "idle_minutes": idle_minutes_actual,
        "last_activity_at": last_activity_at.isoformat(),
        "reason": "recent-activity" if active else "idle",
    }


class SyncSkipped(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(status.get("reason", "sync-skipped"))


class SyncLock:
    def __init__(self, path):
        self.path = Path(path)
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self.fd, json.dumps({
                "pid": os.getpid(),
                "started_at": utc_now(),
            }, sort_keys=True).encode("utf-8"))
        except FileExistsError as exc:
            raise SyncSkipped({
                "status": "skipped",
                "reason": "sync-lock-active",
                "lock_path": str(self.path),
            }) from exc
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            self.path.unlink()
        except OSError:
            pass
        return False


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


def load_station_students(config, fallback_profiles):
    configured = []
    for profile in config.get("students", []):
        if not isinstance(profile, dict):
            continue
        student_id = str(profile.get("id") or "").strip()
        if not student_id or student_id == "guest":
            continue
        configured.append({
            "id": student_id,
            "name": str(profile.get("name") or student_id).strip() or student_id,
        })
    return configured or fallback_profiles


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


def jsonl_payload(record):
    return json.dumps(record, sort_keys=True)


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


def local_attempts(data_dir, station_id, students):
    attempts = []
    malformed = []

    for profile in students:
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


def normalize_cloud_attempt(key, value):
    if not isinstance(value, dict):
        return None
    payload = value.get("attempt") if value.get("format") == "morsepi-student-attempt-v1" else value
    if not isinstance(payload, dict):
        return None
    parts = Path(key).parts
    if len(parts) >= 5:
        payload = dict(payload)
        payload.setdefault("student_id", parts[1])
        payload.setdefault("attempt_id", parts[-1].removesuffix(".json"))
    return payload


def download_cloud_attempts(store, students):
    if hasattr(store, "download_prefix"):
        return download_cloud_attempts_by_prefix(store, students)

    attempts = []
    errors = []
    keys, list_errors = cloud_existing_keys(store, students)
    errors.extend(list_errors)
    if errors:
        return attempts, errors

    for key in sorted(keys):
        parts = Path(key).parts
        if len(parts) < 5:
            continue
        kind = parts[3]
        student_id = parts[1]
        if kind not in ATTEMPT_FILES:
            continue
        try:
            value = store.get_json(key)
            payload = normalize_cloud_attempt(key, value)
        except Exception as exc:
            errors.append({
                "key": key,
                "error": str(exc).splitlines()[-1][:240],
            })
            continue
        if payload is None:
            errors.append({
                "key": key,
                "error": "Invalid cloud attempt payload.",
            })
            continue
        payload.setdefault("student_id", student_id)
        payload.setdefault("attempt_id", parts[-1].removesuffix(".json"))
        attempts.append({
            "canonical": canonical_payload(payload),
            "kind": kind,
            "key": key,
            "payload": payload,
            "student_id": student_id,
        })

    return attempts, errors


def download_cloud_attempts_by_prefix(store, students):
    attempts = []
    errors = []

    with tempfile.TemporaryDirectory() as temporary_dir:
        root = Path(temporary_dir)
        for student in students:
            student_id = student["id"]
            prefix = f"students/{student_id}/attempts/"
            destination = root / student_id
            try:
                store.download_prefix(prefix, destination)
            except Exception as exc:
                errors.append({
                    "student_id": student_id,
                    "error": str(exc).splitlines()[-1][:240],
                })
                continue

            for kind, filename in ATTEMPT_FILES.items():
                kind_dir = destination / kind
                if not kind_dir.exists():
                    continue
                for path in sorted(kind_dir.glob("*.json")):
                    key = f"students/{student_id}/attempts/{kind}/{path.name}"
                    try:
                        value = json.loads(path.read_text(encoding="utf-8"))
                        payload = normalize_cloud_attempt(key, value)
                    except (json.JSONDecodeError, OSError) as exc:
                        errors.append({
                            "key": key,
                            "error": str(exc).splitlines()[-1][:240],
                        })
                        continue
                    if payload is None:
                        errors.append({
                            "key": key,
                            "error": "Invalid cloud attempt payload.",
                        })
                        continue
                    payload.setdefault("student_id", student_id)
                    payload.setdefault("attempt_id", path.stem)
                    attempts.append({
                        "canonical": canonical_payload(payload),
                        "kind": kind,
                        "key": key,
                        "payload": payload,
                        "student_id": student_id,
                    })

    return attempts, errors


def sync_state(data_dir=DEFAULT_DATA_DIR, config_path=DEFAULT_CONFIG_PATH, check_cloud=True, store=None):
    data_dir = Path(data_dir)
    config = load_station_config(config_path)
    station_id = str(config.get("station_id") or "unknown-station")
    all_profiles = load_profiles(data_dir)
    students = load_station_students(config, all_profiles)
    attempts, malformed = local_attempts(data_dir, station_id, students)
    by_key, by_student, duplicates, conflicts = summarize_local(attempts)
    s3_uri = config.get("progress_s3_uri") or config.get("backup_s3_uri") or ""
    if store is None and check_cloud and s3_uri:
        store = AwsCliObjectStore(s3_uri)
    existing, cloud_errors = cloud_existing_keys(store, students)
    upload_keys = sorted(key for key in by_key if key not in existing)
    return {
        "attempts_by_key": by_key,
        "cloud_errors": cloud_errors,
        "cloud_checked": bool(store),
        "conflicts": conflicts,
        "duplicate_local_records": duplicates,
        "existing": existing,
        "malformed_records": malformed,
        "station_id": station_id,
        "roster": students,
        "students": by_student,
        "store": store,
        "upload_keys": upload_keys,
    }


def build_report(data_dir=DEFAULT_DATA_DIR, config_path=DEFAULT_CONFIG_PATH, check_cloud=True, store=None):
    state = sync_state(data_dir, config_path, check_cloud, store)

    return {
        "app": "morsePi",
        "cloud_checked": state["cloud_checked"],
        "cloud_errors": state["cloud_errors"],
        "conflicts": state["conflicts"],
        "duplicate_local_records": state["duplicate_local_records"],
        "format": "morsepi-attempt-sync-dry-run-v1",
        "generated_at": utc_now(),
        "malformed_records": state["malformed_records"],
        "station_id": state["station_id"],
        "students": state["students"],
        "summary": {
            "cloud_existing": len(state["existing"]),
            "local_conflicts": len(state["conflicts"]),
            "local_duplicates": len(state["duplicate_local_records"]),
            "local_unique_attempts": len(state["attempts_by_key"]),
            "malformed_records": len(state["malformed_records"]),
            "would_upload": len(state["upload_keys"]),
        },
        "would_upload": state["upload_keys"][:200],
    }


def upload_attempts(data_dir=DEFAULT_DATA_DIR, config_path=DEFAULT_CONFIG_PATH, store=None):
    state = sync_state(data_dir, config_path, check_cloud=True, store=store)
    store = state["store"]
    if not state["cloud_checked"]:
        raise RuntimeError("Cloud store is not configured; cannot upload attempts.")
    if state["cloud_errors"]:
        raise RuntimeError("Cloud access errors must be fixed before uploading attempts.")
    if state["conflicts"]:
        raise RuntimeError("Local attempt ID conflicts must be fixed before uploading attempts.")

    uploaded = []
    uploaded_at = utc_now()
    for key in state["upload_keys"]:
        attempt = state["attempts_by_key"][key]
        store.put_json(key, {
            "attempt": attempt["payload"],
            "format": "morsepi-student-attempt-v1",
            "kind": attempt["kind"],
            "student_id": attempt["student_id"],
            "uploaded_at": uploaded_at,
        })
        uploaded.append(key)
    return {
        "cloud_existing": len(state["existing"]),
        "local_unique_attempts": len(state["attempts_by_key"]),
        "uploaded": len(uploaded),
        "uploaded_keys": uploaded[:200],
    }


def backup_sync_files(data_dir, students):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_root = Path(data_dir) / "sync_backups" / timestamp
    copied = 0
    for student in students:
        student_id = student["id"]
        source_dir = Path(data_dir) / "students" / student_id
        for filename in list(ATTEMPT_FILES.values()) + ["practice_progress.json"]:
            source = source_dir / filename
            if not source.exists():
                continue
            target = backup_root / student_id / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
    return backup_root if copied else None


def merge_attempt_maps(local_attempts_by_key, cloud_attempts):
    merged = dict(local_attempts_by_key)
    conflicts = []
    downloaded = 0

    for attempt in cloud_attempts:
        existing = merged.get(attempt["key"])
        if existing is None:
            merged[attempt["key"]] = attempt
            downloaded += 1
            continue
        if existing["canonical"] != attempt["canonical"]:
            conflicts.append({
                "key": attempt["key"],
                "local": existing["payload"],
                "cloud": attempt["payload"],
            })

    return merged, conflicts, downloaded


def write_conflicts(data_dir, conflicts):
    if not conflicts:
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = Path(data_dir) / "sync_conflicts" / f"{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(conflicts, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_merged_attempt_logs(data_dir, students, merged_attempts):
    by_student_kind = {}
    roster_ids = {student["id"] for student in students}
    touched_students = set()
    for attempt in merged_attempts.values():
        student_id = attempt["student_id"]
        kind = attempt["kind"]
        if student_id not in roster_ids or kind not in ATTEMPT_FILES:
            continue
        touched_students.add(student_id)
        by_student_kind.setdefault((student_id, kind), []).append(attempt["payload"])

    written = {}
    for student in students:
        student_id = student["id"]
        if student_id not in touched_students:
            continue
        student_dir = Path(data_dir) / "students" / student_id
        student_dir.mkdir(parents=True, exist_ok=True)
        for kind, filename in ATTEMPT_FILES.items():
            records = sorted(
                by_student_kind.get((student_id, kind), []),
                key=lambda item: (str(item.get("timestamp", "")), str(item.get("attempt_id", ""))),
            )
            path = student_dir / filename
            if records:
                path.write_text(
                    "\n".join(jsonl_payload(record) for record in records) + "\n",
                    encoding="utf-8",
                )
            elif path.exists():
                path.unlink()
            written[f"{student_id}:{kind}"] = len(records)
    return written


def empty_progress_record():
    return {
        "attempts": 0,
        "correct": 0,
        "last_seen": "",
        "streak": 0,
        "strength": 0.0,
    }


def apply_practice_attempt_to_progress(progress, attempt):
    letter = str(attempt.get("target", "")).upper()
    mode = str(attempt.get("mode", "send")).lower()
    if not letter or mode not in PRACTICE_MODES:
        return

    letter_progress = progress.setdefault(letter, {})
    record = letter_progress.setdefault(mode, empty_progress_record())
    record["attempts"] += 1
    record["last_seen"] = str(attempt.get("timestamp", "")) or utc_now()
    if attempt.get("correct"):
        record["correct"] += 1
        record["streak"] += 1
        record["strength"] = min(1.0, record["strength"] + 0.18 + min(record["streak"], 4) * 0.02)
    else:
        record["streak"] = 0
        record["strength"] = max(0.0, record["strength"] - 0.35)


def build_practice_progress(attempts):
    progress = {}
    for attempt in sorted(attempts, key=lambda item: str(item.get("timestamp", ""))):
        apply_practice_attempt_to_progress(progress, attempt)
    return progress


def rebuild_practice_progress(data_dir, students):
    rebuilt = {}
    for student in students:
        student_id = student["id"]
        attempts = []
        student_dir = Path(data_dir) / "students" / student_id
        for _, record in iter_jsonl(student_dir / "practice_attempts.jsonl"):
            if record is not None:
                attempts.append(record)
        if not attempts:
            continue

        progress = build_practice_progress(attempts)
        output = student_dir / "practice_progress.json"
        output.write_text(json.dumps(progress, indent=2, sort_keys=True), encoding="utf-8")
        rebuilt[student_id] = len(attempts)
    return rebuilt


def step_key(step):
    return "".join(step["letters"])


def learn_record_ready(progress, letter):
    record = progress.get(letter, {}).get("learn", {})
    return (
        int(record.get("correct", 0)) >= LEARN_READY_ATTEMPTS
        and float(record.get("strength", 0)) * 100 >= LEARN_READY_STRENGTH
    )


def first_learn_attempt_time(attempts, letters):
    wanted = set(letters)
    timestamps = [
        str(attempt.get("timestamp", ""))
        for attempt in attempts
        if str(attempt.get("mode", "")).lower() == "learn"
        and str(attempt.get("target", "")).upper() in wanted
        and str(attempt.get("timestamp", ""))
    ]
    return min(timestamps) if timestamps else ""


def step_has_learn_attempts(progress, step):
    return any(letter in progress and "learn" in progress[letter] for letter in step["letters"])


def completed_learning_groups_from_attempts(attempts):
    progress = {}
    completed = {}
    sorted_attempts = sorted(attempts, key=lambda item: str(item.get("timestamp", "")))
    for attempt in sorted_attempts:
        apply_practice_attempt_to_progress(progress, attempt)
        for step in LETTER_UNLOCK_STEPS:
            key = step_key(step)
            if key in completed:
                continue
            if all(learn_record_ready(progress, letter) for letter in step["letters"]):
                completed[key] = learning_group_state(
                    step,
                    first_learn_attempt_time(sorted_attempts, step["letters"]),
                )
            break
    return completed


def learning_group_state(step, started_at):
    timestamp = started_at or utc_now()
    return {
        "letters": step["letters"],
        "first_learning_date": timestamp[:10],
        "first_learning_started_at": timestamp,
    }


def rebuild_learning_state(data_dir, students):
    rebuilt = {}
    for student in students:
        student_id = student["id"]
        student_dir = Path(data_dir) / "students" / student_id
        attempts = [
            record
            for _, record in iter_jsonl(student_dir / "practice_attempts.jsonl")
            if record is not None
        ]
        if not attempts:
            continue

        progress = build_practice_progress(attempts)
        completed_groups = completed_learning_groups_from_attempts(attempts)
        groups = {}
        last_learning_start_date = ""
        for step in LETTER_UNLOCK_STEPS:
            key = step_key(step)
            started_at = first_learn_attempt_time(attempts, step["letters"])

            if key in completed_groups:
                groups[key] = completed_groups[key]
                last_learning_start_date = groups[key]["first_learning_date"]
                continue

            if step_has_learn_attempts(progress, step):
                groups[key] = learning_group_state(step, started_at)
                last_learning_start_date = groups[key]["first_learning_date"]
            break

        output = student_dir / "learning_state.json"
        if groups:
            output.write_text(
                json.dumps({"groups": groups, "last_learning_start_date": last_learning_start_date}, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            rebuilt[student_id] = len(groups)
        elif output.exists():
            output.unlink()
            rebuilt[student_id] = 0
    return rebuilt


def full_sync_attempts(data_dir=DEFAULT_DATA_DIR, config_path=DEFAULT_CONFIG_PATH, store=None):
    state = sync_state(data_dir, config_path, check_cloud=True, store=store)
    store = state["store"]
    if not state["cloud_checked"]:
        raise RuntimeError("Cloud store is not configured; cannot sync attempts.")
    if state["cloud_errors"]:
        raise RuntimeError("Cloud access errors must be fixed before syncing attempts.")
    if state["conflicts"]:
        raise RuntimeError("Local attempt ID conflicts must be fixed before syncing attempts.")

    upload_result = upload_attempts(data_dir, config_path, store=store)
    cloud_attempts, cloud_errors = download_cloud_attempts(store, state["roster"])
    if cloud_errors:
        raise RuntimeError("Cloud download errors must be fixed before applying merged attempts.")

    merged, merge_conflicts, downloaded = merge_attempt_maps(state["attempts_by_key"], cloud_attempts)
    conflict_path = write_conflicts(data_dir, merge_conflicts)
    if merge_conflicts:
        raise RuntimeError(f"Cloud attempt conflicts written to {conflict_path}; merged logs were not applied.")

    backup_path = backup_sync_files(data_dir, state["roster"])
    written = write_merged_attempt_logs(data_dir, state["roster"], merged)
    rebuilt = rebuild_practice_progress(data_dir, state["roster"])
    rebuilt_learning = rebuild_learning_state(data_dir, state["roster"])
    return {
        "backup_path": str(backup_path) if backup_path else "",
        "cloud_attempts": len(cloud_attempts),
        "downloaded": downloaded,
        "rebuilt": rebuilt,
        "rebuilt_learning": rebuilt_learning,
        "uploaded": upload_result["uploaded"],
        "written": written,
    }


def guarded_full_sync(
    data_dir=DEFAULT_DATA_DIR,
    config_path=DEFAULT_CONFIG_PATH,
    store=None,
    force=False,
    idle_minutes=DEFAULT_IDLE_MINUTES,
    lock_path=None,
):
    data_dir = Path(data_dir)
    lock_path = lock_path or data_dir / "sync_reports" / "student_attempt_sync.lock"
    with SyncLock(lock_path):
        activity = activity_status(data_dir, idle_minutes)
        if activity["active"] and not force:
            status = {
                "activity": activity,
                "force": force,
                "status": "skipped",
                "reason": "recent-activity",
            }
            write_sync_status(data_dir, status)
            raise SyncSkipped(status)

        try:
            result = full_sync_attempts(data_dir, config_path, store)
        except Exception as exc:
            status = {
                "activity": activity,
                "error": str(exc),
                "force": force,
                "status": "error",
            }
            write_sync_status(data_dir, status)
            raise

        status = {
            "activity": activity,
            "force": force,
            "result": result,
            "status": "completed",
        }
        write_sync_status(data_dir, status)
        return result


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
    parser.add_argument("--upload", action="store_true", help="Upload missing local attempts after a clean cloud check.")
    parser.add_argument("--sync", action="store_true", help="Upload, download, merge, and rebuild local derived progress.")
    parser.add_argument("--force", action="store_true", help="Run sync even if recent app activity is detected.")
    parser.add_argument("--idle-minutes", type=int, default=DEFAULT_IDLE_MINUTES, help="Minutes without app activity required for sync.")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.sync and args.no_cloud:
        raise SystemExit("--sync cannot be combined with --no-cloud")
    if args.sync and args.upload:
        raise SystemExit("--sync already uploads; do not combine it with --upload")
    if args.sync:
        try:
            result = guarded_full_sync(
                args.data_dir,
                args.config,
                force=args.force,
                idle_minutes=args.idle_minutes,
            )
        except SyncSkipped as exc:
            print(f"Sync skipped: {exc.status['reason']}")
            return
        print(f"Uploaded attempts: {result['uploaded']}")
        print(f"Cloud attempts read: {result['cloud_attempts']}")
        print(f"Downloaded attempts added: {result['downloaded']}")
        print(f"Backup path: {result['backup_path'] or 'not needed'}")
        return

    report = build_report(args.data_dir, args.config, check_cloud=not args.no_cloud)
    output = write_report(report, args.output)

    print(f"Wrote sync dry-run report: {output}")
    print(f"Station id: {report['station_id']}")
    print(f"Local unique attempts: {report['summary']['local_unique_attempts']}")
    print(f"Would upload: {report['summary']['would_upload']}")
    print(f"Cloud errors: {len(report['cloud_errors'])}")
    print(f"Conflicts: {report['summary']['local_conflicts']}")
    if args.upload:
        if args.no_cloud:
            raise SystemExit("--upload cannot be combined with --no-cloud")
        result = upload_attempts(args.data_dir, args.config)
        print(f"Uploaded attempts: {result['uploaded']}")


if __name__ == "__main__":
    main()
