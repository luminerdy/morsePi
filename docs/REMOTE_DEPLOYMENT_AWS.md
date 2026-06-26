# Remote Deployment With AWS

This document describes the first remote-deployment plan for grandkid morsePi stations.

For the operational checklist and commands, see [REMOTE_BACKUP_STATUS_RUNBOOK.md](REMOTE_BACKUP_STATUS_RUNBOOK.md).
For preparing a station before it leaves Pappy's house, see [GRANDKID_STATION_DEPLOYMENT.md](GRANDKID_STATION_DEPLOYMENT.md).

Goal:

```text
Each Pi should work locally, back itself up, report status, and accept a safe update trigger when it is online.
```

## Recommended Direction

Use this shape first:

```text
GitHub          source code
S3              station backups and status files
AWS IoT Core    future command/status layer
Pi scripts      actual update, backup, and status work
```

The Pi should stay self-sufficient. AWS should trigger known local scripts, not become the only way the station can be maintained.

## Why AWS IoT Looks Promising

AWS IoT fits the station better than full server management because the devices may be off most of the time.

Good fit:

- The Pi connects outbound when it is powered on.
- No home router port forwarding is needed.
- Each station can have its own certificate and policy.
- The same MQTT foundation can later carry family Morse messages.
- Commands can be simple: update, backup, restart, status.

Systems Manager is still useful if we later want Linux fleet management, but the advanced hybrid-device cost is roughly `$5/month/device` when a device is registered continuously. For two stations, that is about `$10/month` plus small S3 costs.

## Station Identity

Each deployed station should have a stable id:

```text
astrid-station
liara-station
```

On the Pi, copy the sample config:

```bash
cd /home/morse/morse-station
cp config.station.example.json data/station_config.json
```

For the active test station and first two planned grandkid stations, tracked examples are also available:

```text
config/stations/pappy-test-station.example.json
config/stations/astrid-station.example.json
config/stations/liara-station.example.json
```

Edit `data/station_config.json`:

```json
{
  "station_id": "astrid-station",
  "backup_s3_uri": "s3://morsepi-backups"
}
```

`data/station_config.json` is ignored by Git because it is station-specific.

## Backup Flow

Local command:

```bash
cd /home/morse/morse-station
python3 scripts/backup_data.py --label manual
```

Cloud upload:

```bash
python3 scripts/backup_data.py --label manual --s3-uri s3://morsepi-backups
```

Expected S3 path:

```text
s3://morsepi-backups/stations/<station-id>/<timestamp>-<station-id>-manual.zip
```

The backup zip includes:

- `data/student_profiles.json`
- `data/timing_settings.json`
- `data/students/`
- `manifest.json`

## Status Flow

Local command:

```bash
cd /home/morse/morse-station
python3 scripts/station_status.py
```

Cloud upload:

```bash
python3 scripts/station_status.py --s3-uri s3://morsepi-backups
```

Status includes:

- station id
- hostname
- Git branch and commit
- last local backup name
- `morse-station.service` state
- UTC timestamp

Expected S3 path:

```text
s3://morsepi-backups/stations/<station-id>/station_status.json
```

## Update Flow

Local command:

```bash
cd /home/morse/morse-station
scripts/update_station.sh
```

The update script:

1. Creates a pre-update backup.
2. Uploads that backup if `MORSE_BACKUP_S3_URI` is set.
3. Skips update if tracked local changes exist.
4. Fetches `origin/main`.
5. Applies only fast-forward updates.
6. Compile-checks the app and support scripts.
7. Restarts `morse-station.service`.
8. Writes station status.
9. Uploads status if `MORSE_BACKUP_S3_URI` is set.

Useful environment variables:

```bash
export MORSE_STATION_ID=astrid-station
export MORSE_BACKUP_S3_URI=s3://morsepi-backups
export MORSE_APP_DIR=/home/morse/morse-station
```

## AWS Setup Sketch

First AWS pieces:

- S3 bucket: `morsepi-backups`
- IAM user or role for station backups with limited access to one station prefix
- AWS CLI installed on each Pi
- One station config file per Pi

Future AWS IoT pieces:

- IoT Thing per station
- Certificate per station
- Least-privilege IoT policy
- Tiny Pi agent that subscribes to command topics
- Command topics:
  - `morsepi/<station-id>/commands/update`
  - `morsepi/<station-id>/commands/backup`
  - `morsepi/<station-id>/commands/status`
  - `morsepi/<station-id>/commands/restart`
- Event topics:
  - `morsepi/<station-id>/events`
  - `morsepi/<station-id>/status`

## First Rollout Checklist

Before a station leaves Pappy's house:

- Fresh Pi setup is complete.
- App boots to `/touch`.
- One local backup works.
- One S3 backup upload works.
- One status upload works.
- One update script run works with no changes pending.
- `station_id` is unique.
- Student profiles are created.
- Wi-Fi for the grandkid house is configured or documented.
- The SD card has been cloned or a fresh restore path is tested.

## Open Decisions

- Use AWS IoT Jobs or a small custom MQTT command agent for update triggers.
- Decide whether status should live only in S3, IoT Device Shadow, or both.
- Decide backup retention in S3.
- Decide whether station data should be encrypted with a per-station KMS key later.
- Decide whether remote updates should be manual-only or allowed on a timer.
