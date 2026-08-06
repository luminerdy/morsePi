import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from message_sync import AwsCliObjectStore, sync_station
from paths import data_path


def main():
    parser = argparse.ArgumentParser(description="Synchronize Morse family messages through S3.")
    parser.add_argument("--config", default=str(data_path("station_config.json")))
    parser.add_argument("--data-dir", default=str(data_path()))
    parser.add_argument("--force", action="store_true", help="Run even when message sync is disabled.")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if not args.force and not config.get("message_sync_enabled", False):
        print("Message sync disabled.")
        return 0
    s3_uri = config.get("message_s3_uri") or config.get("backup_s3_uri")
    counts = sync_station(args.data_dir, config, AwsCliObjectStore(s3_uri))
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
