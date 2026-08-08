import re
from datetime import datetime, timedelta, timezone

from message_store import (
    MESSAGE_FORMAT,
    MESSAGE_STATES,
    MessageValidationError,
    decode_state,
    letter_positions,
    normalize_message_text,
    required_letters,
)
from student_identity import StudentIdentityError, validate_identity_pair


CLOUD_MESSAGE_FORMAT = "morsepi-cloud-message-v1"
LEARNING_SUMMARY_FORMAT = "morsepi-learning-summary-v1"
FAMILY_SUMMARY_FORMAT = "morsepi-family-learning-summary-v1"
FAMILY_DIRECTORY_FORMAT = "morsepi-family-directory-v1"
RECEIPT_FORMAT = "morsepi-message-receipt-v1"
CURRICULUM_VERSION = "morsepi-curriculum-v1"
SUMMARY_MAX_AGE_DAYS = 30
STATE_RANK = {state: index for index, state in enumerate(MESSAGE_STATES)}
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MESSAGE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise MessageValidationError("Invalid UTC timestamp.") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def require_slug(value, label):
    normalized = str(value or "").strip().lower()
    if not SLUG_PATTERN.fullmatch(normalized):
        raise MessageValidationError(f"Invalid {label}.")
    return normalized


def require_message_id(value):
    normalized = str(value or "").strip().lower()
    if not MESSAGE_ID_PATTERN.fullmatch(normalized):
        raise MessageValidationError("Invalid message ID.")
    return normalized


def station_ids_for_student(directory, student_id):
    if not isinstance(directory, dict) or directory.get("format") != FAMILY_DIRECTORY_FORMAT:
        raise MessageValidationError("Invalid family directory.")
    students = directory.get("students", {})
    entry = students.get(require_slug(student_id, "student ID")) if isinstance(students, dict) else None
    if not isinstance(entry, dict):
        raise MessageValidationError("Unknown family student.")
    stations = []
    for station_id in entry.get("station_ids", []):
        station_id = require_slug(station_id, "station ID")
        if station_id not in stations:
            stations.append(station_id)
    if not stations:
        raise MessageValidationError("Student has no approved station.")
    return stations


def new_learning_summary(student_id, station_id, active_letters, generated_at=None):
    ordered = []
    for value in active_letters:
        letter = str(value or "").strip().upper()
        if len(letter) == 1 and letter.isalnum() and letter not in ordered:
            ordered.append(letter)
    return {
        "format": LEARNING_SUMMARY_FORMAT,
        "student_id": require_slug(student_id, "student ID"),
        "station_id": require_slug(station_id, "station ID"),
        "active_letters": ordered,
        "curriculum_version": CURRICULUM_VERSION,
        "generated_at": generated_at or utc_now(),
    }


def validate_learning_summary(summary, expected_student_id="", expected_station_id="", now=None):
    if not isinstance(summary, dict) or summary.get("format") != LEARNING_SUMMARY_FORMAT:
        raise MessageValidationError("Invalid learning summary format.")
    student_id = require_slug(summary.get("student_id"), "student ID")
    station_id = require_slug(summary.get("station_id"), "station ID")
    if expected_student_id and student_id != require_slug(expected_student_id, "student ID"):
        raise MessageValidationError("Learning summary student mismatch.")
    if expected_station_id and station_id != require_slug(expected_station_id, "station ID"):
        raise MessageValidationError("Learning summary station mismatch.")
    if summary.get("curriculum_version") != CURRICULUM_VERSION:
        raise MessageValidationError("Unsupported curriculum version.")
    generated_at = parse_utc(summary.get("generated_at"))
    reference = now or datetime.now(timezone.utc)
    if generated_at < reference - timedelta(days=SUMMARY_MAX_AGE_DAYS):
        raise MessageValidationError("Learning summary is stale.")
    normalized = new_learning_summary(student_id, station_id, summary.get("active_letters", []), generated_at.isoformat())
    if normalized["active_letters"] != summary.get("active_letters"):
        raise MessageValidationError("Learning summary letters are not canonical.")
    return normalized


def aggregate_learning_summaries(student_id, snapshots, directory, generated_at=None, now=None):
    approved = set(station_ids_for_student(directory, student_id))
    ordered = []
    sources = []
    for snapshot in snapshots:
        try:
            validated = validate_learning_summary(snapshot, expected_student_id=student_id, now=now)
        except MessageValidationError:
            continue
        if validated["station_id"] not in approved:
            continue
        sources.append(validated["station_id"])
        for letter in validated["active_letters"]:
            if letter not in ordered:
                ordered.append(letter)
    if not sources:
        raise MessageValidationError("No current learning summary is available.")
    return {
        "format": FAMILY_SUMMARY_FORMAT,
        "student_id": require_slug(student_id, "student ID"),
        "active_letters": ordered,
        "curriculum_version": CURRICULUM_VERSION,
        "source_station_ids": sorted(set(sources)),
        "generated_at": generated_at or utc_now(),
    }


def validate_family_summary(summary, expected_student_id="", now=None):
    if not isinstance(summary, dict) or summary.get("format") != FAMILY_SUMMARY_FORMAT:
        raise MessageValidationError("Invalid family summary format.")
    student_id = require_slug(summary.get("student_id"), "student ID")
    if expected_student_id and student_id != require_slug(expected_student_id, "student ID"):
        raise MessageValidationError("Family summary student mismatch.")
    if summary.get("curriculum_version") != CURRICULUM_VERSION:
        raise MessageValidationError("Unsupported curriculum version.")
    generated_at = parse_utc(summary.get("generated_at"))
    reference = now or datetime.now(timezone.utc)
    if generated_at < reference - timedelta(days=SUMMARY_MAX_AGE_DAYS):
        raise MessageValidationError("Family summary is stale.")
    letters = new_learning_summary(student_id, "summary", summary.get("active_letters", []))["active_letters"]
    if letters != summary.get("active_letters"):
        raise MessageValidationError("Family summary letters are not canonical.")
    return dict(summary)


def cloud_message_from_local(message, enrich_legacy=True):
    if not isinstance(message, dict) or message.get("format") != MESSAGE_FORMAT:
        raise MessageValidationError("Invalid local message format.")
    text = normalize_message_text(message.get("text"))
    canonical_required = required_letters(text)
    if canonical_required != message.get("required_letters"):
        raise MessageValidationError("Message required letters do not match text.")
    try:
        sender_uuid = validate_identity_pair(
            message.get("sender_student_id"), message.get("sender_student_uuid"), allow_legacy=True
        )
        recipient_uuid = validate_identity_pair(
            message.get("recipient_student_id"), message.get("recipient_student_uuid"), allow_legacy=True
        )
    except StudentIdentityError as error:
        raise MessageValidationError(str(error)) from error
    payload = {
        "format": CLOUD_MESSAGE_FORMAT,
        "message_id": require_message_id(message.get("message_id")),
        "sender_student_id": require_slug(message.get("sender_student_id"), "sender student ID"),
        "sender_station_id": require_slug(message.get("sender_station_id"), "sender station ID"),
        "recipient_student_id": require_slug(message.get("recipient_student_id"), "recipient student ID"),
        "text": text,
        "required_letters": canonical_required,
        "created_at": parse_utc(message.get("created_at")).isoformat(),
    }
    if sender_uuid and (enrich_legacy or message.get("sender_student_uuid")):
        payload["sender_student_uuid"] = sender_uuid
    if recipient_uuid and (enrich_legacy or message.get("recipient_student_uuid")):
        payload["recipient_student_uuid"] = recipient_uuid
    return payload


def validate_cloud_message(payload, expected_sender_station, directory, sender_summary, recipient_summary):
    if not isinstance(payload, dict) or payload.get("format") != CLOUD_MESSAGE_FORMAT:
        raise MessageValidationError("Invalid cloud message format.")
    canonical = {
        "format": MESSAGE_FORMAT,
        "message_id": payload.get("message_id"),
        "sender_student_id": payload.get("sender_student_id"),
        "sender_station_id": payload.get("sender_station_id"),
        "recipient_student_id": payload.get("recipient_student_id"),
        "sender_student_uuid": payload.get("sender_student_uuid"),
        "recipient_student_uuid": payload.get("recipient_student_uuid"),
        "text": payload.get("text"),
        "required_letters": payload.get("required_letters"),
        "created_at": payload.get("created_at"),
    }
    validated = cloud_message_from_local(canonical, enrich_legacy=False)
    expected_station = require_slug(expected_sender_station, "station ID")
    if validated["sender_station_id"] != expected_station:
        raise MessageValidationError("Sender station path mismatch.")
    if validated["sender_student_id"] == validated["recipient_student_id"]:
        raise MessageValidationError("Sender and recipient must differ.")
    if expected_station not in station_ids_for_student(directory, validated["sender_student_id"]):
        raise MessageValidationError("Sender is not approved for this station.")
    station_ids_for_student(directory, validated["recipient_student_id"])
    sender = validate_family_summary(sender_summary, validated["sender_student_id"])
    recipient = validate_family_summary(recipient_summary, validated["recipient_student_id"])
    allowed = set(sender["active_letters"]) & set(recipient["active_letters"])
    unavailable = [letter for letter in validated["required_letters"] if letter not in allowed]
    if unavailable:
        raise MessageValidationError(f"Message uses unavailable letters: {' '.join(unavailable)}.")
    if validated != payload:
        raise MessageValidationError("Cloud message is not canonical.")
    return validated


def validate_station_inbox_message(payload, recipient_student_id, family_student_ids, sender_summary, recipient_summary):
    if not isinstance(payload, dict) or payload.get("format") != CLOUD_MESSAGE_FORMAT:
        raise MessageValidationError("Invalid cloud message format.")
    canonical = cloud_message_from_local({
        "format": MESSAGE_FORMAT,
        "message_id": payload.get("message_id"),
        "sender_student_id": payload.get("sender_student_id"),
        "sender_station_id": payload.get("sender_station_id"),
        "recipient_student_id": payload.get("recipient_student_id"),
        "sender_student_uuid": payload.get("sender_student_uuid"),
        "recipient_student_uuid": payload.get("recipient_student_uuid"),
        "text": payload.get("text"),
        "required_letters": payload.get("required_letters"),
        "created_at": payload.get("created_at"),
    }, enrich_legacy=False)
    if canonical != payload:
        raise MessageValidationError("Cloud message is not canonical.")
    recipient_id = require_slug(recipient_student_id, "recipient student ID")
    if canonical["recipient_student_id"] != recipient_id:
        raise MessageValidationError("Inbox recipient mismatch.")
    family_ids = {require_slug(value, "family student ID") for value in family_student_ids}
    if canonical["sender_student_id"] not in family_ids or recipient_id not in family_ids:
        raise MessageValidationError("Message is outside the family directory.")
    sender = validate_family_summary(sender_summary, canonical["sender_student_id"])
    recipient = validate_family_summary(recipient_summary, recipient_id)
    allowed = set(sender["active_letters"]) & set(recipient["active_letters"])
    unavailable = [letter for letter in canonical["required_letters"] if letter not in allowed]
    if unavailable:
        raise MessageValidationError(f"Message uses unavailable letters: {' '.join(unavailable)}.")
    return canonical


def local_message_from_cloud(payload, available_at=None):
    message = {
        "format": MESSAGE_FORMAT,
        "message_id": require_message_id(payload.get("message_id")),
        "sender_student_id": require_slug(payload.get("sender_student_id"), "sender student ID"),
        "sender_station_id": require_slug(payload.get("sender_station_id"), "sender station ID"),
        "recipient_student_id": require_slug(payload.get("recipient_student_id"), "recipient student ID"),
        "text": normalize_message_text(payload.get("text")),
        "required_letters": required_letters(normalize_message_text(payload.get("text"))),
        "created_at": parse_utc(payload.get("created_at")).isoformat(),
        "state": "available",
        "available_at": available_at or utc_now(),
        "opened_at": "",
        "decoded_at": "",
        "decode": {"solved_positions": [], "revealed_positions": [], "hint_levels": {}},
    }
    for field in ("sender_student_uuid", "recipient_student_uuid"):
        if payload.get(field):
            message[field] = payload[field]
    return message


def new_receipt(message, state, station_id, occurred_at=None):
    state = str(state or "").strip().lower()
    if state not in ("available", "opened", "decoded"):
        raise MessageValidationError("Invalid receipt state.")
    return {
        "format": RECEIPT_FORMAT,
        "message_id": require_message_id(message.get("message_id")),
        "sender_station_id": require_slug(message.get("sender_station_id"), "sender station ID"),
        "recipient_student_id": require_slug(message.get("recipient_student_id"), "recipient student ID"),
        "reporting_station_id": require_slug(station_id, "reporting station ID"),
        "state": state,
        "occurred_at": occurred_at or utc_now(),
    }


def validate_receipt(receipt, expected_station, directory, message):
    if not isinstance(receipt, dict) or receipt.get("format") != RECEIPT_FORMAT:
        raise MessageValidationError("Invalid receipt format.")
    canonical = new_receipt(
        message,
        receipt.get("state"),
        receipt.get("reporting_station_id"),
        parse_utc(receipt.get("occurred_at")).isoformat(),
    )
    if canonical != receipt:
        raise MessageValidationError("Receipt is not canonical.")
    station_id = require_slug(expected_station, "station ID")
    if canonical["reporting_station_id"] != station_id:
        raise MessageValidationError("Receipt station path mismatch.")
    if station_id not in station_ids_for_student(directory, canonical["recipient_student_id"]):
        raise MessageValidationError("Station cannot report for this recipient.")
    return canonical


def advance_message_state(message, receipt):
    current = str(message.get("state") or "queued")
    requested = str(receipt.get("state") or "")
    if requested not in STATE_RANK:
        raise MessageValidationError("Invalid message state.")
    if STATE_RANK[requested] <= STATE_RANK.get(current, 0):
        return dict(message), False

    updated = dict(message)
    updated["state"] = requested
    timestamp = parse_utc(receipt.get("occurred_at")).isoformat()
    if requested == "available":
        updated["available_at"] = timestamp
    elif requested == "opened":
        updated["opened_at"] = timestamp
    elif requested == "decoded":
        updated["decoded_at"] = timestamp
        state = decode_state(updated)
        state["solved_positions"] = letter_positions(updated)
        updated["decode"] = state
    return updated, True
