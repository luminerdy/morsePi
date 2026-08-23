import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paths import data_path


REMOVED_MESSAGE_IDS = {
    "c7674cf3029e402b90fc91e24602052c": "Remove 2026-08-08 Pappy-to-Astrid AM rehearsal from student history.",
}


def remove_message_files(students_dir, message_id):
    removed = []
    for folder_name in ("message_inbox", "message_outbox"):
        for path in sorted(students_dir.glob(f"*/{folder_name}/{message_id}.json")):
            path.unlink()
            removed.append(str(path))
    return removed


def filter_message_events(students_dir, message_id):
    changed = []
    for path in sorted(students_dir.glob("*/message_events.jsonl")):
        original = path.read_text(encoding="utf-8").splitlines()
        kept = []
        removed_count = 0
        for line in original:
            if not line.strip():
                kept.append(line)
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                kept.append(line)
                continue
            if str(record.get("message_id", "")).lower() == message_id:
                removed_count += 1
            else:
                kept.append(line)
        if removed_count:
            path.write_text(("\n".join(kept) + ("\n" if kept else "")), encoding="utf-8")
            changed.append({"path": str(path), "removed_events": removed_count})
    return changed


def cleanup(data_dir):
    students_dir = Path(data_dir) / "students"
    result = {"removed_files": [], "filtered_event_files": []}
    if not students_dir.exists():
        return result

    for message_id in REMOVED_MESSAGE_IDS:
        result["removed_files"].extend(remove_message_files(students_dir, message_id))
        result["filtered_event_files"].extend(filter_message_events(students_dir, message_id))
    return result


def main():
    parser = argparse.ArgumentParser(description="Remove known non-student message rehearsals from live history.")
    parser.add_argument("--data-dir", default=str(data_path()))
    args = parser.parse_args()
    print(json.dumps(cleanup(args.data_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
