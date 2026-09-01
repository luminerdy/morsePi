import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from family_activity import refresh_family_activity
from message_sync import AwsCliObjectStore
from paths import data_path
from scripts.backup_data import DEFAULT_CONFIG_PATH, load_station_config


def refresh_from_config(data_dir, config_path, store=None):
    config = load_station_config(config_path)
    reader_enabled = config.get("family_activity_reader")
    if reader_enabled is None:
        reader_enabled = config.get("station_id") == "pappy-test-station"
    if not reader_enabled:
        return {"status": "skipped", "reason": "family-activity-reader-disabled"}
    s3_uri = config.get("activity_s3_uri") or config.get("backup_s3_uri") or ""
    if not s3_uri:
        return {"status": "skipped", "reason": "family-activity-cloud-not-configured"}
    cache = refresh_family_activity(data_dir, config, store or AwsCliObjectStore(s3_uri))
    return {
        "status": "completed",
        "events": len(cache["events"]),
        "errors": len(cache["refresh_errors"]),
        "refreshed_at": cache["refreshed_at"],
        "stations": len(cache["stations"]),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Refresh the cached MorsePi family activity feed.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--data-dir", default=str(data_path()))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    result = refresh_from_config(args.data_dir, args.config)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
