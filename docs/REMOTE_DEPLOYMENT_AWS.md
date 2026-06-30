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
Systems Manager first remote-admin/update bridge
AWS IoT Core    future lower-cost command/status/message layer
Pi scripts      actual update, backup, and status work
```

The Pi should stay self-sufficient. AWS should trigger known local scripts, not become the only way the station can be maintained.

## Why Systems Manager First

Systems Manager is the first remote-admin bridge because it gives Pappy a practical way to connect to a deployed Pi, troubleshoot, and run the local backup/update/status scripts without port forwarding or asking the family to open the home network.

Use Systems Manager for:

- remote shell access when a station is online
- manual update triggers
- service status checks
- emergency troubleshooting

Do not make Systems Manager the normal app sync path. S3 should handle backups and shared family summaries, and IoT can take over lightweight commands later if the cost and complexity make sense.

## Why AWS IoT Still Looks Promising

AWS IoT fits the long-term station experience better than full server management because the devices may be off most of the time.

Good fit:

- The Pi connects outbound when it is powered on.
- No home router port forwarding is needed.
- Each station can have its own certificate and policy.
- The same MQTT foundation can later carry family Morse messages.
- Commands can be simple: update, backup, restart, status.

Systems Manager advanced hybrid-device access may cost roughly `$5/month/device` when a device is registered continuously. That can be acceptable for the first two deployed stations while we need remote hands, but the longer-term command path should remain open to AWS IoT if it reduces monthly cost.

## Backup, Sync, And Family Visibility

The cloud data path should support more than raw backup. It should also consolidate safe progress snapshots so each station can eventually show family progress without ranking kids against each other.

Use this effort-first model:

- each station uploads its own backup and progress snapshot
- a family summary combines practice minutes, daily missions, new letters, words attempted, recent wins, and family totals
- stations can read the shared family summary
- avoid ranked leaderboards; emphasize practice, persistence, personal bests, and family milestones

Example S3 layout:

```text
s3://morsepi-backups/
  stations/
    pappy-test-station/
      backups/
      status/
      snapshots/
      inbox/
    astrid-station/
      backups/
      status/
      snapshots/
      inbox/
    liara-station/
      backups/
      status/
      snapshots/
      inbox/
  family/
    family_summary.json
    recent_wins.json
```

Each device must have its own narrow credential. A station can write only under its own station prefix and read only shared family files plus its own future inbox.

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
s3://morsepi-backups/stations/<station-id>/backups/<timestamp>-<station-id>-manual.zip
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
s3://morsepi-backups/stations/<station-id>/status/station_status.json
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
- IAM setup user for initial provisioning only
- IAM user or role per station with limited access to one station prefix
- AWS CLI installed on each Pi
- One station config file per Pi
- Systems Manager hybrid activation for each deployed station

Temporary setup user permissions needed for tomorrow's AWS work:

- S3 bucket creation and configuration for the MorsePi bucket
- IAM user/policy/access-key creation for each station
- Systems Manager activation creation for deployed Pi registration
- `sts:GetCallerIdentity` for safety checks

After setup, disable or delete the temporary setup access key.

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

- Exact AWS Region and final bucket name.
- Whether the first station credentials should be IAM users with access keys or a more managed credential pattern later.
- Use AWS IoT Jobs or a small custom MQTT command agent for update triggers.
- Decide whether status should live only in S3, IoT Device Shadow, or both.
- Decide backup retention in S3.
- Decide whether station data should be encrypted with a per-station KMS key later.
- Decide whether remote updates should be manual-only or allowed on a timer.
