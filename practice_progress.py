import json
import random
from datetime import datetime, timezone
from pathlib import Path


PROGRESS_PATH = Path("data/practice_progress.json")


def empty_record():
    return {
        "attempts": 0,
        "correct": 0,
        "streak": 0,
        "strength": 0.0,
        "last_seen": ""
    }


def load_progress(letters):
    progress = {}

    if PROGRESS_PATH.exists():
        try:
            progress = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            progress = {}

    for letter in letters:
        record = empty_record()
        record.update(progress.get(letter, {}))
        progress[letter] = normalize_record(record)

    return {letter: progress[letter] for letter in letters}


def save_progress(progress):
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_PATH.write_text(
        json.dumps(progress, indent=2, sort_keys=True),
        encoding="utf-8"
    )


def normalize_record(record):
    attempts = max(0, int(record.get("attempts", 0)))
    correct = max(0, min(int(record.get("correct", 0)), attempts))
    streak = max(0, int(record.get("streak", 0)))
    strength = max(0.0, min(float(record.get("strength", 0.0)), 1.0))

    return {
        "attempts": attempts,
        "correct": correct,
        "streak": streak,
        "strength": strength,
        "last_seen": str(record.get("last_seen", ""))
    }


def record_attempt(letter, is_correct, letters):
    progress = load_progress(letters)
    record = progress.get(letter, empty_record())

    record["attempts"] += 1
    record["last_seen"] = datetime.now(timezone.utc).isoformat()

    if is_correct:
        record["correct"] += 1
        record["streak"] += 1
        record["strength"] = min(1.0, record["strength"] + 0.18 + min(record["streak"], 4) * 0.02)
    else:
        record["streak"] = 0
        record["strength"] = max(0.0, record["strength"] - 0.35)

    progress[letter] = normalize_record(record)
    save_progress(progress)
    return progress


def choose_next_letter(letters, current_letter=""):
    progress = load_progress(letters)
    candidates = [letter for letter in letters if letter != current_letter] or list(letters)
    weights = []

    for letter in candidates:
        record = progress[letter]
        strength = record["strength"]
        attempts = record["attempts"]
        streak = record["streak"]

        weight = 0.35 + (1.0 - strength) * 2.0

        if attempts == 0:
            weight += 1.2

        if attempts > 0 and streak == 0:
            weight += 0.7

        if streak >= 3:
            weight *= 0.55

        weights.append(max(weight, 0.1))

    return random.choices(candidates, weights=weights, k=1)[0]


def progress_summary(letters):
    progress = load_progress(letters)
    summary = []

    for letter in letters:
        record = progress[letter]
        attempts = record["attempts"]
        accuracy = int(round((record["correct"] / attempts) * 100)) if attempts else 0

        summary.append({
            "letter": letter,
            "attempts": attempts,
            "correct": record["correct"],
            "streak": record["streak"],
            "strength": round(record["strength"], 2),
            "strength_percent": int(round(record["strength"] * 100)),
            "accuracy": accuracy
        })

    return summary
