import json
import random
from datetime import datetime, timezone
from pathlib import Path


PROGRESS_PATH = Path("data/practice_progress.json")
DEFAULT_MODE = "send"


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
        progress[letter] = normalize_letter_progress(progress.get(letter, {}))

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


def normalize_letter_progress(value):
    if not isinstance(value, dict):
        value = {}

    if "attempts" in value or "correct" in value or "strength" in value:
        return {DEFAULT_MODE: normalize_record(value)}

    modes = {}

    for mode, record in value.items():
        if isinstance(record, dict):
            modes[mode] = normalize_record(record)

    if DEFAULT_MODE not in modes:
        modes[DEFAULT_MODE] = empty_record()

    return modes


def get_record(progress, letter, mode):
    letter_progress = progress.get(letter, {})
    record = letter_progress.get(mode)

    if record is None:
        record = empty_record()
        letter_progress[mode] = record
        progress[letter] = letter_progress

    return record


def record_attempt(letter, is_correct, letters, mode=DEFAULT_MODE):
    progress = load_progress(letters)
    record = get_record(progress, letter, mode)

    record["attempts"] += 1
    record["last_seen"] = datetime.now(timezone.utc).isoformat()

    if is_correct:
        record["correct"] += 1
        record["streak"] += 1
        record["strength"] = min(1.0, record["strength"] + 0.18 + min(record["streak"], 4) * 0.02)
    else:
        record["streak"] = 0
        record["strength"] = max(0.0, record["strength"] - 0.35)

    progress[letter][mode] = normalize_record(record)
    save_progress(progress)
    return progress


def choose_next_letter(letters, current_letter="", mode=DEFAULT_MODE):
    progress = load_progress(letters)
    candidates = [letter for letter in letters if letter != current_letter] or list(letters)
    weights = []

    for letter in candidates:
        record = get_record(progress, letter, mode)
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


def progress_summary(letters, mode=DEFAULT_MODE):
    progress = load_progress(letters)
    summary = []

    for letter in letters:
        record = get_record(progress, letter, mode)
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


def mode_score(letters, mode=DEFAULT_MODE):
    summary = progress_summary(letters, mode)
    total_attempts = sum(item["attempts"] for item in summary)
    total_correct = sum(item["correct"] for item in summary)
    mastery = int(round(sum(item["strength_percent"] for item in summary) / len(summary))) if summary else 0
    best_streak = max((item["streak"] for item in summary), default=0)
    accuracy = int(round((total_correct / total_attempts) * 100)) if total_attempts else 0
    level = min(5, mastery // 20 + 1)
    next_level_mastery = min(level * 20, 100)
    points_to_next = max(0, next_level_mastery - mastery)

    if mastery >= 80:
        title = "Sharp Copy"
    elif mastery >= 60:
        title = "Getting Strong"
    elif mastery >= 40:
        title = "Finding Rhythm"
    elif mastery >= 20:
        title = "Warming Up"
    else:
        title = "First Signals"

    return {
        "mode": mode,
        "level": level,
        "title": title,
        "mastery": mastery,
        "accuracy": accuracy,
        "streak": best_streak,
        "attempts": total_attempts,
        "next_goal": "Level complete" if mastery == 100 else f"{points_to_next} mastery points to Level {min(level + 1, 5)}"
    }


def all_mode_details(letters, modes):
    return {
        mode: {
            "score": mode_score(letters, mode),
            "letters": progress_summary(letters, mode)
        }
        for mode in modes
    }
