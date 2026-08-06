#!/usr/bin/env python3
"""Set or clear the local morsePi admin PIN."""

import argparse
import getpass
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from paths import data_path


DEFAULT_CONFIG_PATH = data_path("station_config.json")


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def load_config(path):
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def save_config(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def backup_config(path):
    if not path.exists():
        return None

    backup_path = path.with_name(f"{path.name}.pre-admin-pin-{timestamp()}")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_pin(pin):
    if not pin:
        raise ValueError("Admin PIN cannot be blank unless --clear is used.")

    if not pin.isdigit():
        raise ValueError("Admin PIN must use numbers only for the touch keypad.")

    if len(pin) < 4 or len(pin) > 12:
        raise ValueError("Admin PIN must be 4 to 12 digits.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Set the station-local admin PIN without hand-editing JSON."
    )
    parser.add_argument(
        "pin",
        nargs="?",
        help="New numeric admin PIN. Omit to be prompted without echo.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the admin PIN for local development only.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to station_config.json. Default: data/station_config.json",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config)

    if args.clear and args.pin:
        raise SystemExit("Use either a PIN or --clear, not both.")

    if args.clear:
        new_pin = ""
    else:
        new_pin = args.pin
        if new_pin is None:
            new_pin = getpass.getpass("New admin PIN: ")
            confirm_pin = getpass.getpass("Confirm admin PIN: ")
            if new_pin != confirm_pin:
                raise SystemExit("PIN values did not match.")
        try:
            validate_pin(new_pin)
        except ValueError as error:
            raise SystemExit(str(error)) from error

    config = load_config(config_path)
    backup_path = backup_config(config_path)
    config["admin_pin"] = new_pin
    save_config(config_path, config)

    if args.clear:
        print(f"Admin PIN cleared in {config_path}.")
    else:
        print(f"Admin PIN updated in {config_path}.")

    if backup_path:
        print(f"Backup created at {backup_path}.")
    else:
        print("No previous config existed; created a new config file.")

    print("Restart the app service for the change to take effect.")


if __name__ == "__main__":
    main()
