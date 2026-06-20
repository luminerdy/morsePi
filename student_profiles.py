import json
import re
import shutil
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
    "practice_attempts.jsonl"
]


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

        student_id = slugify_student_id(str(profile.get("id") or profile.get("name") or "student"))
        if student_id in seen:
            continue

        name = str(profile.get("name") or student_id).strip() or student_id
        normalized.append({
            "id": student_id,
            "name": name
        })
        seen.add(student_id)

    if DEFAULT_STUDENT_ID not in seen:
        normalized.insert(0, {
            "id": DEFAULT_STUDENT_ID,
            "name": DEFAULT_STUDENT_NAME
        })

    save_profiles(normalized)
    return normalized


def save_profiles(profiles):
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(
        json.dumps(profiles, indent=2, sort_keys=True),
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
    return profile


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
