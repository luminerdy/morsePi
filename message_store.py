import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from morse import MORSE_CODE, text_to_morse


MESSAGE_FORMAT = "morsepi-message-v1"
MAX_MESSAGE_WORDS = 3
MAX_MESSAGE_LETTERS = 20
MESSAGE_STATES = ("queued", "available", "opened", "decoded")


class MessageValidationError(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def load_json(path, default=None):
    try:
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default
    return loaded


def normalize_message_text(value):
    raw = str(value or "").upper()
    unsupported = sorted({character for character in raw if not (character.isalpha() or character.isspace())})
    if unsupported:
        raise MessageValidationError("Use letters and spaces only.")

    text = " ".join(raw.split())
    if not text:
        raise MessageValidationError("Add at least one letter.")

    words = text.split()
    if len(words) > MAX_MESSAGE_WORDS:
        raise MessageValidationError(f"Use {MAX_MESSAGE_WORDS} words or fewer.")

    letter_count = sum(len(word) for word in words)
    if letter_count > MAX_MESSAGE_LETTERS:
        raise MessageValidationError(f"Use {MAX_MESSAGE_LETTERS} letters or fewer.")

    return text


def required_letters(text):
    return sorted({character for character in text if character != " "})


def validate_message_text(value, allowed_letters):
    text = normalize_message_text(value)
    allowed = {str(letter).upper() for letter in allowed_letters}
    unavailable = [letter for letter in required_letters(text) if letter not in allowed]
    if unavailable:
        raise MessageValidationError(f"These letters are not ready: {' '.join(unavailable)}.")
    return text


def message_tiles(text):
    return [
        {
            "index": index,
            "letter": character,
            "morse": text_to_morse(character),
            "space": character == " ",
        }
        for index, character in enumerate(text)
    ]


def available_words(word_bank, allowed_letters):
    allowed = {str(letter).upper() for letter in allowed_letters}
    return [
        word
        for word in word_bank
        if word and all(character in allowed for character in word)
    ]


def draft_path(data_dir, student_id):
    return Path(data_dir) / "students" / student_id / "message_draft.json"


def inbox_dir(data_dir, student_id):
    return Path(data_dir) / "students" / student_id / "message_inbox"


def outbox_dir(data_dir, student_id):
    return Path(data_dir) / "students" / student_id / "message_outbox"


def events_path(data_dir, student_id):
    return Path(data_dir) / "students" / student_id / "message_events.jsonl"


def new_draft(sender_student_id, recipient_student_id=""):
    return {
        "format": "morsepi-message-draft-v1",
        "draft_id": uuid4().hex,
        "sender_student_id": sender_student_id,
        "recipient_student_id": recipient_student_id,
        "text": "",
        "updated_at": utc_now(),
    }


def load_draft(data_dir, student_id):
    loaded = load_json(draft_path(data_dir, student_id), {})
    if not isinstance(loaded, dict) or loaded.get("sender_student_id") != student_id:
        return new_draft(student_id)
    return loaded


def save_draft(data_dir, draft):
    saved = dict(draft)
    saved["updated_at"] = utc_now()
    atomic_write_json(draft_path(data_dir, saved["sender_student_id"]), saved)
    return saved


def clear_draft(data_dir, student_id, recipient_student_id=""):
    return save_draft(data_dir, new_draft(student_id, recipient_student_id))


def create_message(
    sender_student_id,
    recipient_student_id,
    station_id,
    text,
    allowed_letters,
    sender_student_uuid="",
    recipient_student_uuid="",
):
    normalized = validate_message_text(text, allowed_letters)
    now = utc_now()
    message = {
        "format": MESSAGE_FORMAT,
        "message_id": uuid4().hex,
        "sender_student_id": sender_student_id,
        "sender_station_id": station_id,
        "recipient_student_id": recipient_student_id,
        "text": normalized,
        "required_letters": required_letters(normalized),
        "created_at": now,
        "state": "available",
        "available_at": now,
        "opened_at": "",
        "decoded_at": "",
        "decode": {
            "solved_positions": [],
            "revealed_positions": [],
            "hint_levels": {},
        },
    }
    if sender_student_uuid:
        message["sender_student_uuid"] = str(sender_student_uuid)
    if recipient_student_uuid:
        message["recipient_student_uuid"] = str(recipient_student_uuid)
    return message


def message_copy_path(directory, message_id):
    safe_id = str(message_id or "").lower()
    if len(safe_id) != 32 or any(character not in "0123456789abcdef" for character in safe_id):
        raise MessageValidationError("Invalid message ID.")
    return Path(directory) / f"{safe_id}.json"


def save_message_copy(directory, message):
    path = message_copy_path(directory, message.get("message_id"))
    atomic_write_json(path, message)
    return path


def deliver_local_message(data_dir, message):
    message_id = message["message_id"]
    out_path = message_copy_path(outbox_dir(data_dir, message["sender_student_id"]), message_id)
    in_path = message_copy_path(inbox_dir(data_dir, message["recipient_student_id"]), message_id)

    if not out_path.exists():
        atomic_write_json(out_path, message)
    if not in_path.exists():
        atomic_write_json(in_path, message)
    return message


def load_message(directory, message_id):
    try:
        path = message_copy_path(directory, message_id)
    except MessageValidationError:
        return None
    loaded = load_json(path)
    if not isinstance(loaded, dict) or loaded.get("format") != MESSAGE_FORMAT:
        return None
    return loaded


def list_messages(directory):
    directory = Path(directory)
    messages = []
    if not directory.exists():
        return messages

    for path in directory.glob("*.json"):
        loaded = load_json(path)
        if isinstance(loaded, dict) and loaded.get("format") == MESSAGE_FORMAT:
            messages.append(loaded)
    return sorted(messages, key=lambda item: str(item.get("created_at", "")), reverse=True)


def decode_state(message):
    state = message.get("decode")
    if not isinstance(state, dict):
        state = {}
    return {
        "solved_positions": sorted({int(index) for index in state.get("solved_positions", []) if str(index).isdigit()}),
        "revealed_positions": sorted({int(index) for index in state.get("revealed_positions", []) if str(index).isdigit()}),
        "hint_levels": {
            str(index): max(0, min(3, int(level)))
            for index, level in state.get("hint_levels", {}).items()
            if str(index).isdigit()
        },
    }


def letter_positions(message):
    return [index for index, character in enumerate(message.get("text", "")) if character != " "]


def next_unsolved_position(message):
    solved = set(decode_state(message)["solved_positions"])
    return next((index for index in letter_positions(message) if index not in solved), None)


def decoded_words(message):
    solved = set(decode_state(message)["solved_positions"])
    display = "".join(
        character if character == " " or index in solved else "_"
        for index, character in enumerate(message.get("text", ""))
    )
    return display.split(" ") if display else []


def open_message(message):
    updated = dict(message)
    if updated.get("state") == "available":
        updated["state"] = "opened"
        updated["opened_at"] = utc_now()
    return updated


def answer_message(message, position, answer):
    updated = dict(message)
    state = decode_state(updated)
    expected_position = next_unsolved_position(updated)
    if expected_position is None:
        return updated, {"correct": True, "completed": True, "position": None}
    if int(position) != expected_position:
        raise MessageValidationError("Answer the highlighted letter first.")

    normalized_answer = str(answer or "").strip().upper()[:1]
    expected = updated["text"][expected_position]
    correct = normalized_answer == expected
    if correct:
        state["solved_positions"] = sorted(set(state["solved_positions"]) | {expected_position})

    updated["decode"] = state
    completed = next_unsolved_position(updated) is None
    if completed and updated.get("state") != "decoded":
        updated["state"] = "decoded"
        updated["decoded_at"] = utc_now()

    return updated, {
        "correct": correct,
        "completed": completed,
        "position": expected_position,
        "expected": expected,
        "answer": normalized_answer,
    }


def advance_hint(message, position):
    updated = dict(message)
    state = decode_state(updated)
    expected_position = next_unsolved_position(updated)
    if expected_position is None or int(position) != expected_position:
        raise MessageValidationError("Use a hint on the highlighted letter.")

    key = str(expected_position)
    level = min(3, state["hint_levels"].get(key, 0) + 1)
    state["hint_levels"][key] = level
    revealed = False
    completed = False
    if level >= 3:
        state["solved_positions"] = sorted(set(state["solved_positions"]) | {expected_position})
        state["revealed_positions"] = sorted(set(state["revealed_positions"]) | {expected_position})
        revealed = True

    updated["decode"] = state
    completed = next_unsolved_position(updated) is None
    if completed and updated.get("state") != "decoded":
        updated["state"] = "decoded"
        updated["decoded_at"] = utc_now()

    return updated, {
        "level": level,
        "position": expected_position,
        "morse": text_to_morse(updated["text"][expected_position]) if level >= 2 else "",
        "revealed": revealed,
        "completed": completed,
    }


def append_event(data_dir, student_id, event):
    record = dict(event)
    record.setdefault("timestamp", utc_now())
    path = events_path(data_dir, student_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def choice_letters(target, active_letters, seed_value=""):
    import random

    active = sorted({str(letter).upper() for letter in active_letters if str(letter).upper() in MORSE_CODE})
    others = [letter for letter in active if letter != target]
    randomizer = random.Random(f"{seed_value}:{target}")
    choices = [target] + randomizer.sample(others, min(3, len(others)))
    randomizer.shuffle(choices)
    return choices
