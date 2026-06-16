import json
from datetime import datetime, timezone
from pathlib import Path


ATTEMPTS_PATH = Path("data/practice_attempts.jsonl")


def rounded_ms(seconds):
    return int(round(seconds * 1000))


def timing_summary(events):
    symbols = [event for event in events if event.get("type") == "symbol"]
    gaps = [event for event in events if event.get("type") == "gap"]
    dots = [event for event in symbols if event.get("symbol") == "."]
    dashes = [event for event in symbols if event.get("symbol") == "-"]

    def average_duration(items):
        if not items:
            return None
        return int(round(sum(item.get("duration_ms", 0) for item in items) / len(items)))

    return {
        "dot_count": len(dots),
        "dash_count": len(dashes),
        "symbol_count": len(symbols),
        "gap_count": len(gaps),
        "avg_dot_ms": average_duration(dots),
        "avg_dash_ms": average_duration(dashes),
        "avg_gap_ms": average_duration(gaps)
    }


def normalize_timing_events(events):
    normalized = []

    if not isinstance(events, list):
        return normalized

    for event in events:
        if not isinstance(event, dict):
            continue

        event_type = event.get("type")

        if event_type == "symbol":
            normalized.append({
                "type": "symbol",
                "symbol": event.get("symbol", ""),
                "duration_ms": max(0, int(round(float(event.get("duration_ms", 0)))))
            })
        elif event_type == "gap":
            normalized.append({
                "type": "gap",
                "gap_type": event.get("gap_type", "symbol"),
                "duration_ms": max(0, int(round(float(event.get("duration_ms", 0)))))
            })

    return normalized


def append_practice_attempt(record):
    ATTEMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    normalized = dict(record)
    normalized["timestamp"] = datetime.now(timezone.utc).isoformat()
    normalized["timing_events"] = normalize_timing_events(normalized.get("timing_events", []))
    normalized["timing_summary"] = timing_summary(normalized["timing_events"])

    with ATTEMPTS_PATH.open("a", encoding="utf-8") as attempts_file:
        attempts_file.write(json.dumps(normalized, sort_keys=True) + "\n")

    return normalized
