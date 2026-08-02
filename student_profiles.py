import json
import re
import shutil
from datetime import datetime
from pathlib import Path


DATA_DIR = Path("data")
STUDENTS_DIR = DATA_DIR / "students"
PROFILES_PATH = DATA_DIR / "student_profiles.json"
DEFAULT_STUDENT_ID = "pappy"
DEFAULT_STUDENT_NAME = "Pappy"
STUDENT_COOKIE = "morse_student_id"
STUDENT_FILES = [
    "practice_progress.json",
    "learning_state.json",
    "practice_attempts.jsonl",
    "word_attempts.jsonl",
    "bonus_attempts.jsonl",
    "message_draft.json",
    "message_events.jsonl",
]
PROFILE_METADATA = "profile.json"
OPTIONAL_PROFILE_FLAGS = ("disposable", "guest")


def timestamp_key():
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def slugify_student_id(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "student"


def default_profiles():
    return [
        {
            "id": DEFAULT_STUDENT_ID,
            "name": DEFAULT_STUDENT_NAME
        }
    ]


def normalize_profile(profile):
    if not isinstance(profile, dict):
        profile = {}

    student_id = slugify_student_id(str(profile.get("id") or profile.get("name") or "student"))
    name = str(profile.get("name") or student_id).strip() or student_id
    normalized = {
        "id": student_id,
        "name": name
    }

    for flag in OPTIONAL_PROFILE_FLAGS:
        if profile.get(flag):
            normalized[flag] = True

    return normalized


def load_profiles():
    if not PROFILES_PATH.exists():
        save_profiles(default_profiles())

    try:
        profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        profiles = default_profiles()

    if not isinstance(profiles, list):
        profiles = default_profiles()

    normalized = []
    seen = set()

    for profile in profiles:
        if not isinstance(profile, dict):
            continue

        normalized_profile = normalize_profile(profile)
        student_id = normalized_profile["id"]
        if student_id in seen:
            continue

        normalized.append(normalized_profile)
        seen.add(student_id)

    for profile in load_student_profile_metadata():
        if profile["id"] not in seen:
            normalized.append(profile)
            seen.add(profile["id"])

    if DEFAULT_STUDENT_ID not in seen:
        default_profile = {
            "id": DEFAULT_STUDENT_ID,
            "name": DEFAULT_STUDENT_NAME
        }
        normalized.insert(0, default_profile)
        seen.add(DEFAULT_STUDENT_ID)

    save_profiles(normalized)
    return normalized


def save_profiles(profiles):
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(
        json.dumps(profiles, indent=2, sort_keys=True),
        encoding="utf-8"
    )

    for profile in profiles:
        write_student_profile_metadata(profile)


def load_student_profile_metadata():
    profiles = []

    if not STUDENTS_DIR.exists():
        return profiles

    for profile_path in sorted(STUDENTS_DIR.glob(f"*/{PROFILE_METADATA}")):
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(profile, dict):
            continue

        loaded_profile = profile
        student_id = slugify_student_id(str(loaded_profile.get("id") or profile_path.parent.name))
        name = str(loaded_profile.get("name") or student_id).strip() or student_id
        profile = {
            "id": student_id,
            "name": name
        }
        for flag in OPTIONAL_PROFILE_FLAGS:
            if loaded_profile.get(flag):
                profile[flag] = True

        profiles.append(normalize_profile(profile))

    return profiles


def write_student_profile_metadata(profile):
    student_id = slugify_student_id(str(profile.get("id", "")))
    if not student_id:
        return

    profile_path = student_dir(student_id) / PROFILE_METADATA
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(normalize_profile(profile), indent=2, sort_keys=True),
        encoding="utf-8"
    )


def profile_for_id(student_id):
    profiles = load_profiles()

    for profile in profiles:
        if profile["id"] == student_id:
            return profile

    return profiles[0]


def unique_student_id(name):
    profiles = load_profiles()
    existing = {profile["id"] for profile in profiles}
    base = slugify_student_id(name)
    student_id = base
    counter = 2

    while student_id in existing:
        student_id = f"{base}-{counter}"
        counter += 1

    return student_id


def add_profile(name):
    clean_name = " ".join(str(name).split()).strip()
    if not clean_name:
        clean_name = "Student"

    profiles = load_profiles()
    profile = {
        "id": unique_student_id(clean_name),
        "name": clean_name
    }
    profiles.append(profile)
    save_profiles(profiles)
    ensure_student_storage(profile["id"])
    write_student_profile_metadata(profile)
    return profile


def ensure_profiles(required_profiles):
    profiles = load_profiles()
    by_id = {profile["id"]: dict(profile) for profile in profiles}
    changed = False

    for required_profile in required_profiles:
        normalized = normalize_profile(required_profile)
        existing = by_id.get(normalized["id"])

        if existing is None:
            by_id[normalized["id"]] = normalized
            changed = True
            continue

        for key, value in normalized.items():
            if existing.get(key) != value:
                existing[key] = value
                changed = True

        by_id[normalized["id"]] = existing

    if changed:
        ordered = []
        seen = set()
        for profile in profiles:
            profile_id = profile["id"]
            ordered.append(by_id[profile_id])
            seen.add(profile_id)
        for required_profile in required_profiles:
            profile_id = normalize_profile(required_profile)["id"]
            if profile_id not in seen:
                ordered.append(by_id[profile_id])
                seen.add(profile_id)
        save_profiles(ordered)
        profiles = load_profiles()

    for profile in required_profiles:
        ensure_student_storage(normalize_profile(profile)["id"])

    return profiles


def student_dir(student_id):
    return STUDENTS_DIR / slugify_student_id(student_id)


def student_data_path(student_id, filename):
    return student_dir(student_id) / filename


def ensure_student_storage(student_id):
    target_dir = student_dir(student_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    if slugify_student_id(student_id) != DEFAULT_STUDENT_ID:
        return

    for filename in STUDENT_FILES:
        legacy_path = DATA_DIR / filename
        target_path = target_dir / filename

        if legacy_path.exists() and not target_path.exists():
            shutil.copy2(legacy_path, target_path)


def reset_student_storage(student_id):
    student_id = slugify_student_id(student_id)
    target_dir = student_dir(student_id)
    backup_root = DATA_DIR / "student_backups" / f"{timestamp_key()}-{student_id}-reset"
    removed = []

    def backup_and_remove(source, group):
        if not source.exists():
            return

        backup_dir = backup_root / group
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup_dir / source.name)
        source.unlink()
        removed.append(str(source))

    for filename in STUDENT_FILES:
        backup_and_remove(target_dir / filename, "student")

    for dirname in ("message_inbox", "message_outbox"):
        source_dir = target_dir / dirname
        if not source_dir.exists():
            continue
        backup_dir = backup_root / "student" / dirname
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, backup_dir)
        shutil.rmtree(source_dir)
        removed.append(str(source_dir))

    if student_id == DEFAULT_STUDENT_ID:
        for filename in STUDENT_FILES:
            backup_and_remove(DATA_DIR / filename, "legacy")

    backup_root.mkdir(parents=True, exist_ok=True)

    return {
        "student_id": student_id,
        "backup_path": str(backup_root),
        "removed": removed,
    }
