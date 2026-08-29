import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backup_data import DEFAULT_CONFIG_PATH


DEFAULT_APP_DIR = Path("/home/morse/morse-station")
MESSAGE_UNITS = (
    "morse-station-message-sync.service",
    "morse-station-message-sync.timer",
)


def atomic_write(path, content, mode):
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    os.chmod(temporary, mode)
    temporary.replace(path)


def run_command(command):
    subprocess.run(command, check=True, capture_output=True, text=True)


def enable_message_sync(config_path=DEFAULT_CONFIG_PATH, app_dir=DEFAULT_APP_DIR, home=None, runner=run_command):
    config_path = Path(config_path)
    app_dir = Path(app_dir)
    home = Path(home) if home else Path.home()
    original = config_path.read_bytes()
    original_mode = config_path.stat().st_mode & 0o777
    config = json.loads(original.decode("utf-8"))
    station_id = str(config.get("station_id") or "").strip()
    if not station_id:
        raise ValueError("station_id is required before message sync can be enabled")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = config_path.parent / "config_backups"
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup_path = backup_dir / f"station_config.before-message-sync-{stamp}.json"
    backup_path.write_bytes(original)
    os.chmod(backup_path, 0o600)

    unit_dir = home / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    for unit in MESSAGE_UNITS:
        source = app_dir / "systemd" / unit
        destination = unit_dir / unit
        shutil.copyfile(source, destination)
        os.chmod(destination, 0o644)

    runner(["systemctl", "--user", "daemon-reload"])
    config["message_sync_enabled"] = True
    updated = (json.dumps(config, indent=2, sort_keys=True) + "\n").encode("utf-8")
    atomic_write(config_path, updated, original_mode)

    try:
        runner(["systemctl", "--user", "enable", "--now", "morse-station-message-sync.timer"])
        runner(["systemctl", "--user", "start", "morse-station-message-sync.service"])
    except Exception:
        atomic_write(config_path, original, original_mode)
        raise

    return {
        "backup_path": str(backup_path),
        "message_sync_enabled": True,
        "station_id": station_id,
        "timer": "morse-station-message-sync.timer",
    }


def main():
    parser = argparse.ArgumentParser(description="Safely enable the fixed morsePi message-sync worker.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--app-dir", default=str(DEFAULT_APP_DIR))
    args = parser.parse_args()
    result = enable_message_sync(args.config, args.app_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
