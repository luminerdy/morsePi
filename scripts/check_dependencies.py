#!/usr/bin/env python3
"""Check the Raspberry Pi runtime dependencies for MorsePi."""

import importlib.util
import shutil
import sys


REQUIRED_COMMANDS = [
    ("git", "Repo update and release deployment"),
    ("systemctl", "User services for app, browser, backup, and update timers"),
    ("aplay", "Morse playback through ALSA"),
    ("speaker-test", "Key-down tone feedback through ALSA"),
]

OPTIONAL_COMMANDS = [
    ("aws", "S3 backup/status upload and future AWS work"),
]

REQUIRED_PYTHON_MODULES = [
    ("flask", "Web app"),
    ("gpiozero", "Telegraph key and LED GPIO"),
]

OPTIONAL_PYTHON_MODULES = [
    ("paho.mqtt.client", "Future MQTT/IoT messaging"),
]


def command_available(name):
    return shutil.which(name) is not None


def module_available(name):
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def check_command(name, purpose, required=True):
    ok = command_available(name)
    status = "OK" if ok else ("MISSING" if required else "optional missing")
    print(f"{status:16} command {name:14} {purpose}")
    return ok or not required


def check_module(name, purpose, required=True):
    ok = module_available(name)
    status = "OK" if ok else ("MISSING" if required else "optional missing")
    print(f"{status:16} python  {name:14} {purpose}")
    return ok or not required


def main():
    checks = []

    print("MorsePi dependency check")
    print("------------------------")

    for name, purpose in REQUIRED_COMMANDS:
        checks.append(check_command(name, purpose, required=True))

    for name, purpose in OPTIONAL_COMMANDS:
        checks.append(check_command(name, purpose, required=False))

    for name, purpose in REQUIRED_PYTHON_MODULES:
        checks.append(check_module(name, purpose, required=True))

    for name, purpose in OPTIONAL_PYTHON_MODULES:
        checks.append(check_module(name, purpose, required=False))

    if all(checks):
        print("\nReady: required station dependencies are installed.")
        return 0

    print("\nFix the MISSING required items, then run this check again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
