from pathlib import PurePosixPath

from message_cloud import (
    MessageValidationError,
    aggregate_learning_summaries,
    new_receipt,
    require_message_id,
    require_slug,
    station_ids_for_student,
    validate_cloud_message,
    validate_learning_summary,
    validate_receipt,
)


DIRECTORY_KEY = "family/messaging/directory.json"


def summary_key(student_id):
    return f"family/student-summaries/{student_id}.json"


def station_snapshot_key(station_id, student_id):
    return f"stations/{station_id}/snapshots/students/{student_id}.json"


def refresh_family_summary(store, student_id, directory):
    snapshots = []
    for station_id in station_ids_for_student(directory, student_id):
        snapshot = store.get_json(station_snapshot_key(station_id, student_id), default=None)
        if snapshot is not None:
            snapshots.append(snapshot)
    summary = aggregate_learning_summaries(student_id, snapshots, directory)
    store.put_json(summary_key(student_id), summary)
    return summary


def route_snapshot(store, parts, directory):
    if len(parts) != 5 or parts[0] != "stations" or parts[2:4] != ("snapshots", "students"):
        return None
    station_id = require_slug(parts[1], "station ID")
    student_id = require_slug(PurePosixPath(parts[4]).stem, "student ID")
    if station_id not in station_ids_for_student(directory, student_id):
        raise MessageValidationError("Snapshot station is not approved for this student.")
    snapshot = store.get_json("/".join(parts))
    validate_learning_summary(snapshot, student_id, station_id)
    summary = refresh_family_summary(store, student_id, directory)
    return {"action": "summary", "student_id": student_id, "summary": summary}


def route_outbox(store, parts, directory):
    if len(parts) != 5 or parts[0] != "stations" or parts[2:4] != ("messages", "outbox"):
        return None
    station_id = require_slug(parts[1], "station ID")
    message_id = require_message_id(PurePosixPath(parts[4]).stem)
    key = "/".join(parts)
    payload = store.get_json(key)
    if payload.get("message_id") != message_id:
        raise MessageValidationError("Message ID path mismatch.")
    sender_summary = refresh_family_summary(store, payload.get("sender_student_id"), directory)
    recipient_summary = refresh_family_summary(store, payload.get("recipient_student_id"), directory)
    message = validate_cloud_message(payload, station_id, directory, sender_summary, recipient_summary)
    recipient_stations = sorted(station_ids_for_student(directory, message["recipient_student_id"]))

    for recipient_station in recipient_stations:
        inbox_key = (
            f"stations/{recipient_station}/messages/inbox/"
            f"{message['recipient_student_id']}/{message_id}.json"
        )
        store.put_json(inbox_key, message)

    available = new_receipt(
        message,
        "available",
        recipient_stations[0],
        message["created_at"],
    )
    store.put_json(
        f"stations/{station_id}/messages/status/sent/{message_id}/available.json",
        available,
    )
    return {
        "action": "message",
        "message_id": message_id,
        "recipient_stations": recipient_stations,
    }


def route_receipt(store, parts, directory):
    if (
        len(parts) != 8
        or parts[0] != "stations"
        or parts[2:5] != ("messages", "receipts", "outgoing")
    ):
        return None
    reporting_station = require_slug(parts[1], "station ID")
    student_id = require_slug(parts[5], "student ID")
    message_id = require_message_id(parts[6])
    state = PurePosixPath(parts[7]).stem
    receipt = store.get_json("/".join(parts))
    if receipt.get("message_id") != message_id or receipt.get("state") != state:
        raise MessageValidationError("Receipt path mismatch.")
    inbox_key = f"stations/{reporting_station}/messages/inbox/{student_id}/{message_id}.json"
    message = store.get_json(inbox_key)
    validated = validate_receipt(receipt, reporting_station, directory, message)

    sender_station = require_slug(message.get("sender_station_id"), "sender station ID")
    store.put_json(
        f"stations/{sender_station}/messages/status/sent/{message_id}/{state}.json",
        validated,
    )
    recipient_stations = station_ids_for_student(directory, student_id)
    for station_id in recipient_stations:
        store.put_json(
            f"stations/{station_id}/messages/status/received/{student_id}/{message_id}/{state}.json",
            validated,
        )
    return {
        "action": "receipt",
        "message_id": message_id,
        "state": state,
        "recipient_stations": recipient_stations,
    }


def route_key(store, key):
    normalized = str(key or "").strip("/")
    parts = tuple(PurePosixPath(normalized).parts)
    directory = store.get_json(DIRECTORY_KEY)
    for handler in (route_snapshot, route_outbox, route_receipt):
        result = handler(store, parts, directory)
        if result is not None:
            return result
    return {"action": "ignored", "key": normalized}
