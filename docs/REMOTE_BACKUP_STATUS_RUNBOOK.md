# Remote Backup, Status, And Update Runbook

This runbook is for deployed grandkid stations that may be powered off most of the time.

Goal:

```text
Every station should work locally first, then back up and report status when it is online.
```

## Current Recommendation

Use this order:

1. Local backup on each Pi.
2. Optional S3 backup/status upload.
3. Manual update wrapper.
4. Optional scheduled update timer after local testing.
5. AWS IoT command trigger later, after S3 backup/status is proven.

Avoid relying on AWS Systems Manager for the first deployment unless the added monthly per-device cost becomes worth it. AWS IoT should be the first remote-command path to test because it supports outbound device connections and should be lower cost for this project.

## Station Config

Each Pi should have:

```text
/home/morse/morse-station/data/station_config.json
```

Example:

```json
{
  "station_id": "astrid-station",
  "backup_s3_uri": "s3://morsepi-backups"
}
```

The backup and status Python scripts read this file automatically.

The shell update wrapper can also upload its pre-update backup/status, but it currently uses environment variables:

```bash
export MORSE_STATION_ID=astrid-station
export MORSE_BACKUP_S3_URI=s3://morsepi-backups
```

## Manual Local Backup

```bash
cd /home/morse/morse-station
python3 scripts/backup_data.py --label manual
```

Expected:

- A zip is created in `data/backups/`.
- The filename includes the station id.
- The manifest includes the station id and backed-up files.

Inspect the newest backup:

```bash
ls -lt data/backups | head
unzip -l data/backups/<backup-file>.zip | head -50
```

## Manual Cloud Backup

Dry-run:

```bash
python3 scripts/backup_data.py --label manual --dry-run-s3
```

Upload:

```bash
python3 scripts/backup_data.py --label manual
```

Expected destination:

```text
s3://morsepi-backups/stations/<station-id>/<timestamp>-<station-id>-manual.zip
```

## Manual Status

Local:

```bash
python3 scripts/station_status.py
cat data/station_status.json
```

Cloud dry-run:

```bash
python3 scripts/station_status.py --dry-run-s3
```

Cloud upload:

```bash
python3 scripts/station_status.py
```

Expected destination:

```text
s3://morsepi-backups/stations/<station-id>/station_status.json
```

Status should include:

- station id
- hostname
- Git branch and commit
- latest local backup
- user service name and state
- UTC check time

## Manual Update

Run:

```bash
cd /home/morse/morse-station
scripts/update_station.sh
```

The update wrapper:

1. Creates a pre-update backup.
2. Uploads that backup if `MORSE_BACKUP_S3_URI` is set.
3. Skips update if tracked local changes exist.
4. Fetches `origin/main`.
5. Applies only fast-forward updates.
6. Compile-checks the app and support scripts.
7. Restarts `morse-station.service`.
8. Writes station status.
9. Uploads status if `MORSE_BACKUP_S3_URI` is set.

Use environment variables when cloud upload is desired during update:

```bash
MORSE_STATION_ID=astrid-station \
MORSE_BACKUP_S3_URI=s3://morsepi-backups \
scripts/update_station.sh
```

## Optional Backup Timer

Install after the station is tested locally:

```bash
mkdir -p /home/morse/.config/systemd/user
install -m 0644 /home/morse/morse-station/systemd/morse-station-backup.service /home/morse/.config/systemd/user/morse-station-backup.service
install -m 0644 /home/morse/morse-station/systemd/morse-station-backup.timer /home/morse/.config/systemd/user/morse-station-backup.timer
systemctl --user daemon-reload
systemctl --user enable --now morse-station-backup.timer
```

Test once:

```bash
systemctl --user start morse-station-backup.service
journalctl --user -u morse-station-backup.service -n 50 --no-pager
```

## Optional Update Timer

First deployment recommendation:

- Leave disabled while the station is being tested in the new home.
- Enable only after manual update has worked at least once.

Install:

```bash
mkdir -p /home/morse/bin /home/morse/.config/systemd/user
install -m 0755 /home/morse/morse-station/systemd/update-morse-station.sh /home/morse/bin/update-morse-station.sh
install -m 0644 /home/morse/morse-station/systemd/morse-station-update.service /home/morse/.config/systemd/user/morse-station-update.service
install -m 0644 /home/morse/morse-station/systemd/morse-station-update.timer /home/morse/.config/systemd/user/morse-station-update.timer
systemctl --user daemon-reload
systemctl --user enable --now morse-station-update.timer
```

Test once:

```bash
systemctl --user start morse-station-update.service
journalctl --user -u morse-station-update.service -n 80 --no-pager
```

Disable:

```bash
systemctl --user disable --now morse-station-update.timer
```

## AWS IoT Later

After S3 backup/status works, the next remote-control step should be a small AWS IoT command agent.

Command topics:

```text
morsepi/<station-id>/commands/update
morsepi/<station-id>/commands/backup
morsepi/<station-id>/commands/status
morsepi/<station-id>/commands/restart
```

The agent should run only known local scripts. It should not accept arbitrary shell commands.

First allowed actions:

| Command | Local action |
|---|---|
| `backup` | `python3 scripts/backup_data.py --label remote` |
| `status` | `python3 scripts/station_status.py` |
| `update` | `scripts/update_station.sh` |
| `restart` | `systemctl --user restart morse-station.service` |

## Recovery Checks

When a station comes online after being off:

```bash
cd /home/morse/morse-station
git rev-parse --short HEAD
systemctl --user is-active morse-station.service
python3 scripts/backup_data.py --label check --dry-run-s3
python3 scripts/station_status.py --dry-run-s3
```

If the station has student progress that is not backed up yet, run a local backup before any update.
