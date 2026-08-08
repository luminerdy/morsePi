import json
from pathlib import Path
from uuid import UUID


REGISTRY_PATH = Path(__file__).resolve().parent / "config" / "family_registry.json"


class StudentIdentityError(ValueError):
    pass


def normalize_student_uuid(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return str(UUID(raw))
    except ValueError as error:
        raise StudentIdentityError("Invalid student UUID.") from error


def load_family_registry(path=REGISTRY_PATH):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StudentIdentityError("Family registry is unavailable or invalid.") from error
    if payload.get("format") != "morsepi-family-registry-v1":
        raise StudentIdentityError("Unsupported family registry format.")

    students = []
    ids = set()
    uuids = set()
    for item in payload.get("students", []):
        if not isinstance(item, dict):
            raise StudentIdentityError("Invalid family registry student.")
        student_id = str(item.get("id") or "").strip().lower()
        student_uuid = normalize_student_uuid(item.get("student_uuid"))
        if not student_id or not student_uuid or student_id in ids or student_uuid in uuids:
            raise StudentIdentityError("Family registry identities must be unique.")
        students.append({
            "id": student_id,
            "name": str(item.get("name") or student_id).strip() or student_id,
            "student_uuid": student_uuid,
        })
        ids.add(student_id)
        uuids.add(student_uuid)
    return students


def family_registry_by_id(path=REGISTRY_PATH):
    return {student["id"]: student for student in load_family_registry(path)}


def family_registry_by_uuid(path=REGISTRY_PATH):
    return {student["student_uuid"]: student for student in load_family_registry(path)}


def enrich_student_identity(profile, registry=None, strict=True):
    enriched = dict(profile or {})
    student_id = str(enriched.get("id") or enriched.get("student_id") or "").strip().lower()
    supplied_uuid = normalize_student_uuid(enriched.get("student_uuid"))
    entry = (registry or family_registry_by_id()).get(student_id)
    expected_uuid = entry.get("student_uuid", "") if entry else ""
    if supplied_uuid and expected_uuid and supplied_uuid != expected_uuid:
        if strict:
            raise StudentIdentityError("Student ID and UUID do not match the family registry.")
        return enriched
    if expected_uuid:
        enriched["student_uuid"] = expected_uuid
    elif supplied_uuid:
        enriched["student_uuid"] = supplied_uuid
    return enriched


def student_uuid_for_id(student_id, registry=None):
    entry = (registry or family_registry_by_id()).get(str(student_id or "").strip().lower(), {})
    return entry.get("student_uuid", "")


def validate_identity_pair(student_id, student_uuid, registry=None, allow_legacy=True):
    expected = student_uuid_for_id(student_id, registry)
    supplied = normalize_student_uuid(student_uuid)
    if not supplied:
        if allow_legacy:
            return expected
        raise StudentIdentityError("Student UUID is required.")
    if expected and supplied != expected:
        raise StudentIdentityError("Student ID and UUID do not match the family registry.")
    return supplied
