import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from message_cloud import (
    MessageValidationError,
    advance_message_state,
    cloud_message_from_local,
    local_message_from_cloud,
    new_learning_summary,
    new_receipt,
    parse_utc,
    require_message_id,
    require_slug,
    validate_family_summary,
    validate_learning_summary,
    validate_receipt,
    validate_station_inbox_message,
)
from message_store import (
    atomic_write_json,
    inbox_dir,
    list_messages,
    load_json,
    load_message,
    outbox_dir,
    save_message_copy,
)


def parse_s3_uri(value):
    raw = str(value or "").strip().rstrip("/")
    if not raw.startswith("s3://"):
        raise ValueError("Message S3 URI must start with s3://")
    bucket_and_prefix = raw[5:].split("/", 1)
    bucket = bucket_and_prefix[0]
    prefix = bucket_and_prefix[1].strip("/") if len(bucket_and_prefix) > 1 else ""
    if not bucket:
        raise ValueError("Message S3 URI requires a bucket.")
    return bucket, prefix


class AwsCliObjectStore:
    def __init__(self, s3_uri, executable="aws", runner=None):
        self.bucket, self.root_prefix = parse_s3_uri(s3_uri)
        self.executable = executable
        self.runner = runner or subprocess.run

    def _key(self, key):
        clean = str(key or "").strip("/")
        return "/".join(part for part in (self.root_prefix, clean) if part)

    def _uri(self, key):
        return f"s3://{self.bucket}/{self._key(key)}"

    def _run(self, args):
        return self.runner(
            [self.executable, *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def put_json(self, key, value):
        with tempfile.TemporaryDirectory() as temporary_dir:
            source = Path(temporary_dir) / "object.json"
            source.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
            self._run(["s3", "cp", str(source), self._uri(key), "--only-show-errors"])

    def get_json(self, key, default=...):
        try:
            result = self._run(["s3", "cp", self._uri(key), "-", "--only-show-errors"])
        except subprocess.CalledProcessError:
            if default is not ...:
                return default
            raise
        return json.loads(result.stdout)

    def list_keys(self, prefix):
        result = self._run([
            "s3api",
            "list-objects-v2",
            "--bucket",
            self.bucket,
            "--prefix",
            self._key(prefix),
            "--output",
            "json",
        ])
        payload = json.loads(result.stdout or "{}")
        keys = []
        for item in payload.get("Contents", []):
            key = str(item.get("Key", ""))
            if self.root_prefix and key.startswith(f"{self.root_prefix}/"):
                key = key[len(self.root_prefix) + 1:]
            keys.append(key)
        return keys


def local_summary_path(data_dir, student_id):
    return Path(data_dir) / "message_sync" / "local_summaries" / f"{student_id}.json"


def family_summary_path(data_dir, student_id):
    return Path(data_dir) / "message_sync" / "family_summaries" / f"{student_id}.json"


def write_local_learning_summary(data_dir, student_id, station_id, active_letters):
    summary = new_learning_summary(student_id, station_id, active_letters)
    atomic_write_json(local_summary_path(data_dir, student_id), summary)
    return summary


def refresh_local_learning_summary(data_dir, student_id, station_id, active_letters, refresh_hours=1):
    path = local_summary_path(data_dir, student_id)
    existing = load_json(path, None)
    try:
        existing = validate_learning_summary(existing, student_id, station_id)
    except MessageValidationError:
        existing = None
    normalized_letters = new_learning_summary(student_id, station_id, active_letters)["active_letters"]
    if existing and existing["active_letters"] == normalized_letters:
        refreshed_after = datetime.now(timezone.utc) - timedelta(hours=max(0, refresh_hours))
        if parse_utc(existing["generated_at"]) >= refreshed_after:
            return existing
    return write_local_learning_summary(data_dir, student_id, station_id, normalized_letters)


def load_family_learning_summary(data_dir, student_id):
    summary = load_json(family_summary_path(data_dir, student_id), None)
    try:
        return validate_family_summary(summary, student_id)
    except MessageValidationError:
        return None


def configured_ids(config, key):
    values = []
    for item in config.get(key, []):
        raw = item.get("id") if isinstance(item, dict) else item
        try:
            student_id = require_slug(raw, "student ID")
        except MessageValidationError:
            continue
        if student_id != "guest" and student_id not in values:
            values.append(student_id)
    return values


def find_message(data_dir, student_ids, directory_function, message_id):
    for student_id in student_ids:
        message = load_message(directory_function(data_dir, student_id), message_id)
        if message:
            return message, student_id
    return None, ""


def apply_sender_receipt(message, receipt):
    updated, changed = advance_message_state(message, receipt)
    cloud_state = receipt["state"]
    if updated.get("cloud_state") != cloud_state:
        updated["cloud_state"] = cloud_state
        changed = True
    return updated, changed


def sync_station(data_dir, config, store):
    data_dir = Path(data_dir)
    station_id = require_slug(config.get("station_id"), "station ID")
    local_students = configured_ids(config, "students")
    family_students = configured_ids(config, "family_students") or list(local_students)
    counts = {
        "summaries_uploaded": 0,
        "summaries_downloaded": 0,
        "messages_uploaded": 0,
        "messages_downloaded": 0,
        "receipts_uploaded": 0,
        "statuses_applied": 0,
    }

    for student_id in local_students:
        summary = load_json(local_summary_path(data_dir, student_id), None)
        try:
            summary = validate_learning_summary(summary, student_id, station_id)
        except MessageValidationError:
            continue
        store.put_json(f"stations/{station_id}/snapshots/students/{student_id}.json", summary)
        counts["summaries_uploaded"] += 1

    family_summaries = {}
    for student_id in family_students:
        summary = store.get_json(f"family/student-summaries/{student_id}.json", default=None)
        try:
            summary = validate_family_summary(summary, student_id)
        except MessageValidationError:
            continue
        atomic_write_json(family_summary_path(data_dir, student_id), summary)
        family_summaries[student_id] = summary
        counts["summaries_downloaded"] += 1

    for student_id in local_students:
        for message in list_messages(outbox_dir(data_dir, student_id)):
            if message.get("sender_station_id") != station_id:
                continue
            payload = cloud_message_from_local(message)
            store.put_json(
                f"stations/{station_id}/messages/outbox/{payload['message_id']}.json",
                payload,
            )
            counts["messages_uploaded"] += 1

    for student_id in local_students:
        prefix = f"stations/{station_id}/messages/inbox/{student_id}/"
        for key in store.list_keys(prefix):
            if not key.endswith(".json"):
                continue
            payload = store.get_json(key)
            sender_id = str(payload.get("sender_student_id", ""))
            sender_summary = family_summaries.get(sender_id)
            recipient_summary = family_summaries.get(student_id)
            if not sender_summary or not recipient_summary:
                continue
            try:
                payload = validate_station_inbox_message(
                    payload,
                    student_id,
                    family_students,
                    sender_summary,
                    recipient_summary,
                )
            except MessageValidationError:
                continue
            message_id = payload["message_id"]
            if load_message(inbox_dir(data_dir, student_id), message_id):
                continue
            save_message_copy(inbox_dir(data_dir, student_id), local_message_from_cloud(payload))
            counts["messages_downloaded"] += 1

    for student_id in local_students:
        for message in list_messages(inbox_dir(data_dir, student_id)):
            if message.get("state") not in ("opened", "decoded"):
                continue
            occurred_at = message.get(f"{message['state']}_at") or message.get("created_at")
            receipt = new_receipt(message, message["state"], station_id, occurred_at)
            key = (
                f"stations/{station_id}/messages/receipts/outgoing/{student_id}/"
                f"{message['message_id']}/{message['state']}.json"
            )
            store.put_json(key, receipt)
            counts["receipts_uploaded"] += 1

    sent_prefix = f"stations/{station_id}/messages/status/sent/"
    for key in store.list_keys(sent_prefix):
        parts = PurePosixPath(key).parts
        if len(parts) < 2 or not key.endswith(".json"):
            continue
        try:
            message_id = require_message_id(parts[-2])
        except MessageValidationError:
            continue
        message, sender_id = find_message(data_dir, local_students, outbox_dir, message_id)
        if not message:
            continue
        receipt = store.get_json(key)
        try:
            receipt = validate_receipt(
                receipt,
                receipt.get("reporting_station_id"),
                {
                    "format": "morsepi-family-directory-v1",
                    "students": {
                        message["recipient_student_id"]: {
                            "station_ids": [receipt.get("reporting_station_id")]
                        }
                    },
                },
                message,
            )
        except MessageValidationError:
            continue
        updated, changed = apply_sender_receipt(message, receipt)
        if changed:
            save_message_copy(outbox_dir(data_dir, sender_id), updated)
            counts["statuses_applied"] += 1

    for student_id in local_students:
        received_prefix = f"stations/{station_id}/messages/status/received/{student_id}/"
        for key in store.list_keys(received_prefix):
            parts = PurePosixPath(key).parts
            if len(parts) < 2 or not key.endswith(".json"):
                continue
            try:
                message_id = require_message_id(parts[-2])
            except MessageValidationError:
                continue
            message = load_message(inbox_dir(data_dir, student_id), message_id)
            if not message:
                continue
            receipt = store.get_json(key)
            try:
                receipt = validate_receipt(
                    receipt,
                    receipt.get("reporting_station_id"),
                    {
                        "format": "morsepi-family-directory-v1",
                        "students": {
                            student_id: {"station_ids": [receipt.get("reporting_station_id")]}
                        },
                    },
                    message,
                )
            except MessageValidationError:
                continue
            updated, changed = advance_message_state(message, receipt)
            if changed:
                save_message_copy(inbox_dir(data_dir, student_id), updated)
                counts["statuses_applied"] += 1

    return counts
