import argparse
import subprocess
import sys


DEFAULT_STATIONS = {
    "astrid-liara": "10.10.10.129",
    "campbell-olivea": "10.10.10.157",
}
REMOTE_UPDATE_COMMAND = "cd /home/morse/morse-station && /home/morse/bin/update-morse-station.sh"


def station_targets(selected, custom_hosts):
    targets = []
    selected_names = selected or sorted(DEFAULT_STATIONS)
    for name in selected_names:
        if name not in DEFAULT_STATIONS:
            raise ValueError(f"Unknown station: {name}")
        targets.append((name, DEFAULT_STATIONS[name]))

    for value in custom_hosts or []:
        if "=" not in value:
            raise ValueError("Custom hosts must use name=host format.")
        name, host = value.split("=", 1)
        name = name.strip()
        host = host.strip()
        if not name or not host:
            raise ValueError("Custom hosts require both name and host.")
        targets.append((name, host))

    return targets


def run_station_update(name, host, user, dry_run=False, runner=subprocess.run):
    target = f"{user}@{host}"
    command = ["ssh", target, REMOTE_UPDATE_COMMAND]
    if dry_run:
        return {
            "command": command,
            "host": host,
            "name": name,
            "returncode": 0,
            "skipped": True,
        }

    result = runner(command, capture_output=True, text=True)
    return {
        "command": command,
        "host": host,
        "name": name,
        "returncode": result.returncode,
        "skipped": False,
        "stderr": result.stderr,
        "stdout": result.stdout,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Trigger the installed MorsePi updater on reachable stations."
    )
    parser.add_argument(
        "--station",
        action="append",
        choices=sorted(DEFAULT_STATIONS),
        help="Station name to update. Repeat to update more than one. Defaults to both grandkid stations.",
    )
    parser.add_argument(
        "--host",
        action="append",
        help="Extra station as name=host, for temporary LAN testing.",
    )
    parser.add_argument("--user", default="morse", help="SSH user for the station.")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without running them.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        targets = station_targets(args.station, args.host)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    failures = 0
    for name, host in targets:
        print(f"== {name} ({host}) ==")
        result = run_station_update(name, host, args.user, dry_run=args.dry_run)
        if result["skipped"]:
            print(subprocess.list2cmdline(result["command"]))
            continue
        if result["stdout"]:
            print(result["stdout"].rstrip())
        if result["stderr"]:
            print(result["stderr"].rstrip(), file=sys.stderr)
        if result["returncode"] != 0:
            failures += 1
            print(f"FAILED: {name} returned {result['returncode']}", file=sys.stderr)
        else:
            print(f"OK: {name} update command completed")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
