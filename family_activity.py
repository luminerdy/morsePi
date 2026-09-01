import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from message_store import atomic_write_json, load_json


EVENT_FORMAT = "morsepi-family-activity-v1"
CACHE_FORMAT = "morsepi-family-activity-cache-v1"
MAX_CACHE_EVENTS = 500
STATION_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
EVENT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
EVENT_TYPES = {
    "software_update_succeeded": {
        "category": "updates",
        "level": "success",
        "detail_fields": {"starting_commit", "target_commit", "ending_commit", "reason"},
    },
    "software_update_failed": {
        "category": "problems",
        "level": "error",
        "detail_fields": {"starting_commit", "target_commit", "ending_commit", "reason", "status"},
    },
    "progress_uploaded": {
        "category": "progress",
        "level": "success",
        "detail_fields": {"uploaded", "downloaded", "cloud_attempts"},
    },
    "message_sent": {
        "category": "messages",
        "level": "success",
        "detail_fields": {"message_id", "sender_student_id", "recipient_student_id"},
    },
    "message_received": {
        "category": "messages",
        "level": "success",
        "detail_fields": {"message_id", "sender_student_id", "recipient_student_id"},
    },
    "message_opened": {
        "category": "messages",
        "level": "info",
        "detail_fields": {"message_id", "sender_student_id", "recipient_student_id"},
    },
    "message_decoded": {
        "category": "messages",
        "level": "success",
        "detail_fields": {"message_id", "sender_student_id", "recipient_student_id"},
    },
}
DEFAULT_FAMILY_STATIONS = [
    {"id": "pappy-test-station", "name": "Pappy"},
    {"id": "astrid-liara-station", "name": "Astrid / Liara"},
    {"id": "campbell-olivea-station", "name": "Campbell / Olivea"},
]


class ActivityValidationError(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError as error:
        raise ActivityValidationError("Activity timestamp is invalid.") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def require_station_id(value):
    station_id = str(value or "").strip().lower()
    if not STATION_ID_PATTERN.fullmatch(station_id):
        raise ActivityValidationError("Activity station ID is invalid.")
    return station_id


def compact_scalar(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 3)
    return str(value or "").strip()[:120]


def sanitize_details(event_type, details):
    allowed = EVENT_TYPES[event_type]["detail_fields"]
    source = details if isinstance(details, dict) else {}
    return {
        key: compact_scalar(source[key])
        for key in sorted(allowed)
        if key in source and source[key] not in (None, "")
    }


def activity_event_id(station_id, event_type, source_id):
    payload = f"{station_id}|{event_type}|{str(source_id or '').strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def new_activity_event(station_id, event_type, source_id, occurred_at=None, details=None):
    station_id = require_station_id(station_id)
    event_type = str(event_type or "").strip().lower()
    if event_type not in EVENT_TYPES:
        raise ActivityValidationError("Activity event type is not allowed.")
    source_id = str(source_id or "").strip()[:160]
    if not source_id:
        raise ActivityValidationError("Activity source identity is required.")
    occurred = parse_utc(occurred_at or utc_now())
    metadata = EVENT_TYPES[event_type]
    return {
        "category": metadata["category"],
        "details": sanitize_details(event_type, details),
        "event_id": activity_event_id(station_id, event_type, source_id),
        "event_type": event_type,
        "format": EVENT_FORMAT,
        "level": metadata["level"],
        "occurred_at": occurred.isoformat(),
        "source_id": source_id,
        "station_id": station_id,
    }


def validate_activity_event(value, expected_station_id=None, expected_event_id=None):
    if not isinstance(value, dict) or value.get("format") != EVENT_FORMAT:
        raise ActivityValidationError("Activity event format is invalid.")
    station_id = require_station_id(value.get("station_id"))
    if expected_station_id and station_id != require_station_id(expected_station_id):
        raise ActivityValidationError("Activity station path does not match payload.")
    event_type = str(value.get("event_type") or "").strip().lower()
    if event_type not in EVENT_TYPES:
        raise ActivityValidationError("Activity event type is not allowed.")
    source_id = str(value.get("source_id") or "").strip()
    expected_id = activity_event_id(station_id, event_type, source_id)
    event_id = str(value.get("event_id") or "").strip().lower()
    if not EVENT_ID_PATTERN.fullmatch(event_id) or event_id != expected_id:
        raise ActivityValidationError("Activity event ID is invalid.")
    if expected_event_id and event_id != str(expected_event_id).strip().lower():
        raise ActivityValidationError("Activity event path does not match payload.")
    occurred = parse_utc(value.get("occurred_at"))
    metadata = EVENT_TYPES[event_type]
    return {
        "category": metadata["category"],
        "details": sanitize_details(event_type, value.get("details")),
        "event_id": event_id,
        "event_type": event_type,
        "format": EVENT_FORMAT,
        "level": metadata["level"],
        "occurred_at": occurred.isoformat(),
        "source_id": source_id[:160],
        "station_id": station_id,
    }


def activity_event_key(event):
    event = validate_activity_event(event)
    day = parse_utc(event["occurred_at"])
    return (
        f"stations/{event['station_id']}/activity/"
        f"{day:%Y/%m/%d}/{event['event_id']}.json"
    )


def activity_dir(data_dir):
    return Path(data_dir) / "family_activity"


def queue_activity_event(data_dir, event):
    event = validate_activity_event(event)
    root = activity_dir(data_dir)
    pending = root / "pending" / f"{event['event_id']}.json"
    sent = root / "sent" / f"{event['event_id']}.json"
    if sent.exists() or pending.exists():
        return {"event": event, "path": sent if sent.exists() else pending, "queued": False}
    atomic_write_json(pending, event)
    return {"event": event, "path": pending, "queued": True}


def flush_activity_events(data_dir, store):
    root = activity_dir(data_dir)
    pending_dir = root / "pending"
    sent_dir = root / "sent"
    sent_dir.mkdir(parents=True, exist_ok=True)
    uploaded = 0
    errors = []
    for path in sorted(pending_dir.glob("*.json")) if pending_dir.exists() else []:
        try:
            event = validate_activity_event(load_json(path, None), expected_event_id=path.stem)
            store.put_json(activity_event_key(event), event)
            path.replace(sent_dir / path.name)
            uploaded += 1
        except Exception as error:
            errors.append({"event_id": path.stem, "error": str(error)[:240]})
    return {"errors": errors, "pending": len(list(pending_dir.glob("*.json"))) if pending_dir.exists() else 0, "uploaded": uploaded}


def record_activity_event(data_dir, config, store, event_type, source_id, occurred_at=None, details=None):
    event = new_activity_event(
        config.get("station_id"),
        event_type,
        source_id,
        occurred_at=occurred_at,
        details=details,
    )
    queued = queue_activity_event(data_dir, event)
    flushed = flush_activity_events(data_dir, store) if store is not None else {"errors": [], "pending": 1, "uploaded": 0}
    return {"event": event, "queued": queued["queued"], "flush": flushed}


def configured_family_stations(config):
    configured = config.get("family_stations", []) if isinstance(config, dict) else []
    stations = []
    for item in configured:
        if not isinstance(item, dict):
            continue
        try:
            station_id = require_station_id(item.get("id"))
        except ActivityValidationError:
            continue
        name = str(item.get("name") or station_id).strip()[:60] or station_id
        if station_id not in {station["id"] for station in stations}:
            stations.append({"id": station_id, "name": name})
    return stations or [dict(station) for station in DEFAULT_FAMILY_STATIONS]


def sanitize_station_status(value, expected_station_id):
    if not isinstance(value, dict):
        raise ActivityValidationError("Station status is invalid.")
    station_id = require_station_id(value.get("station_id"))
    if station_id != require_station_id(expected_station_id):
        raise ActivityValidationError("Station status path does not match payload.")
    checked_at = parse_utc(value.get("checked_at")).isoformat()
    update = value.get("update") if isinstance(value.get("update"), dict) else {}
    return {
        "checked_at": checked_at,
        "git_branch": str(value.get("git_branch") or "")[:80],
        "git_commit": str(value.get("git_commit") or "")[:40],
        "station_id": station_id,
        "update": {
            key: str(update.get(key) or "")[:120]
            for key in ("status", "reason", "updated_at", "ending_commit")
            if update.get(key) not in (None, "")
        },
    }


def empty_activity_cache(stations=None):
    stations = stations or DEFAULT_FAMILY_STATIONS
    return {
        "events": [],
        "format": CACHE_FORMAT,
        "refreshed_at": "",
        "refresh_errors": [],
        "stations": [
            {"id": station["id"], "name": station["name"], "status": None}
            for station in stations
        ],
    }


def load_activity_cache(data_dir, stations=None):
    path = activity_dir(data_dir) / "cache.json"
    loaded = load_json(path, None)
    if not isinstance(loaded, dict) or loaded.get("format") != CACHE_FORMAT:
        return empty_activity_cache(stations)
    return loaded


def event_from_cloud_key(store, key, station_id):
    parts = PurePosixPath(key).parts
    if len(parts) < 7 or parts[0] != "stations" or parts[2] != "activity" or not key.endswith(".json"):
        raise ActivityValidationError("Activity cloud path is invalid.")
    if parts[1] != station_id:
        raise ActivityValidationError("Activity cloud station path is invalid.")
    return validate_activity_event(
        store.get_json(key),
        expected_station_id=station_id,
        expected_event_id=PurePosixPath(key).stem,
    )


def refresh_family_activity(data_dir, config, store):
    stations = configured_family_stations(config)
    previous = load_activity_cache(data_dir, stations)
    events = {
        event.get("event_id"): event
        for event in previous.get("events", [])
        if isinstance(event, dict) and event.get("event_id")
    }
    previous_status = {
        item.get("id"): item.get("status")
        for item in previous.get("stations", [])
        if isinstance(item, dict)
    }
    station_rows = []
    errors = []

    for station in stations:
        station_id = station["id"]
        status = previous_status.get(station_id)
        try:
            keys = store.list_keys(f"stations/{station_id}/activity/")
            for key in keys:
                try:
                    event = event_from_cloud_key(store, key, station_id)
                    events[event["event_id"]] = event
                except Exception as error:
                    errors.append({"station_id": station_id, "kind": "event", "error": str(error)[:240]})
            cloud_status = store.get_json(
                f"stations/{station_id}/status/station_status.json",
                default=None,
            )
            if cloud_status is not None:
                status = sanitize_station_status(cloud_status, station_id)
        except Exception as error:
            errors.append({"station_id": station_id, "kind": "refresh", "error": str(error)[:240]})
        station_rows.append({"id": station_id, "name": station["name"], "status": status})

    ordered_events = sorted(
        events.values(),
        key=lambda event: (str(event.get("occurred_at", "")), str(event.get("event_id", ""))),
        reverse=True,
    )[:MAX_CACHE_EVENTS]
    cache = {
        "events": ordered_events,
        "format": CACHE_FORMAT,
        "refreshed_at": utc_now(),
        "refresh_errors": errors,
        "stations": station_rows,
    }
    atomic_write_json(activity_dir(data_dir) / "cache.json", cache)
    return cache
