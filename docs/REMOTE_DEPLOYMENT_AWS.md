# Remote Deployment With AWS

This document describes the first remote-deployment plan for grandkid morsePi stations.

For the operational checklist and commands, see [REMOTE_BACKUP_STATUS_RUNBOOK.md](REMOTE_BACKUP_STATUS_RUNBOOK.md).
For preparing a station before it leaves Pappy's house, see [GRANDKID_STATION_DEPLOYMENT.md](GRANDKID_STATION_DEPLOYMENT.md).
For credential-free AWS setup steps, see [AWS_SETUP_REFERENCE.md](AWS_SETUP_REFERENCE.md).

Goal:

```text
Each Pi should work locally, back itself up, report status, and accept a safe update trigger when it is online.
```

## Recommended Direction

Use this shape first:

```text
GitHub          source code
S3              station backups and status files
Systems Manager optional remote-admin bridge
AWS IoT Jobs    lower-cost remote update/status trigger
Pi scripts      actual update, backup, and status work
```

The Pi should stay self-sufficient. AWS should trigger known local scripts, not become the only way the station can be maintained.

## Why Systems Manager First

Systems Manager is the first remote-admin bridge because it gives Pappy a practical way to connect to a deployed Pi, troubleshoot, and run the local backup/update/status scripts without port forwarding or asking the family to open the home network.

Use Systems Manager only when we need interactive remote hands:

- remote shell access when a station is online
- manual update triggers
- service status checks
- emergency troubleshooting

Do not make Systems Manager the normal app sync path. S3 handles backups and
shared family summaries, and AWS IoT Jobs is now the preferred lightweight
command trigger for app updates.

## Why AWS IoT Jobs Is The Preferred Update Trigger

AWS IoT Jobs fits the long-term station experience better than full server
management because the devices may be off most of the time.

Good fit:

- The Pi connects outbound when it is powered on.
- No home router port forwarding is needed.
- Each station can have its own certificate and policy.
- The same MQTT foundation can later carry family Morse messages.
- Commands can be simple: update, backup, restart, status.
- A pending Job waits for an offline station and is picked up when the station
  boots or the timer runs.

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
s3://morsepi-backups-luminerdy/
  stations/
    pappy-test-station/
      backups/
      status/
      snapshots/
      inbox/
    astrid-liara-station/
      backups/
      status/
      snapshots/
      inbox/
    campbell-olivea-station/
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
pappy-station
astrid-liara-station
campbell-olivea-station
```

On the Pi, copy the sample config:

```bash
cd /home/morse/morse-station
cp config.station.example.json data/station_config.json
```

Tracked examples are available:

```text
config/stations/pappy-test-station.example.json
config/stations/pappy-station.example.json
config/stations/astrid-liara-station.example.json
config/stations/campbell-olivea-station.example.json
```

Edit `data/station_config.json`:

```json
{
  "station_id": "astrid-liara-station",
  "backup_s3_uri": "s3://morsepi-backups-luminerdy",
  "admin_pin": ""
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
python3 scripts/backup_data.py --label manual --s3-uri s3://morsepi-backups-luminerdy
```

Expected S3 path:

```text
s3://morsepi-backups-luminerdy/stations/<station-id>/backups/<timestamp>-<station-id>-manual.zip
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
python3 scripts/station_status.py --s3-uri s3://morsepi-backups-luminerdy
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
s3://morsepi-backups-luminerdy/stations/<station-id>/status/station_status.json
```

## Update Flow

Local command:

```bash
cd /home/morse/morse-station
scripts/update_station.sh
```

App update is separate from data sync. `Sync Now` and `sync-progress` move
practice data, backups, station status, snapshots, and messages. `Update App`
and `update-app` install code from `release/pi` through the local update
wrapper. This separation matters when explaining why a station may have current
student progress but not yet have a newly released screen or feature.

The update script:

1. Creates a pre-update backup.
2. Uploads that backup if `MORSE_BACKUP_S3_URI` is set.
3. Skips update if tracked local changes exist.
4. Fetches `origin/release/pi` by default.
5. Applies only fast-forward updates.
6. Compile-checks the app and support scripts.
7. Restarts `morse-station.service`.
8. Verifies the local app responds at `http://127.0.0.1:5000/touch`.
9. Writes station status.
10. Uploads status if `MORSE_BACKUP_S3_URI` is set.

Deployment branch model:

```text
main        development and tested work
release/pi  deployed station update branch
```

Promote a tested release from the laptop:

```bash
git fetch origin
git checkout release/pi
git merge --ff-only main
git push origin release/pi
git checkout main
```

Useful environment variables:

```bash
export MORSE_STATION_ID=astrid-liara-station
export MORSE_BACKUP_S3_URI=s3://morsepi-backups-luminerdy
export MORSE_APP_DIR=/home/morse/morse-station
```

## AWS Setup Sketch

First AWS pieces:

- S3 bucket: `morsepi-backups-luminerdy`
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

AWS IoT remote-update pieces:

- IoT Thing per station, named the same as `station_id`
- least-privilege Jobs data-plane policy per station
- `scripts/remote_update_iot.py`, run by `morse-station-remote-update.timer`
- allowed job actions:
  - `update-app`
  - `sync-progress`
  - `enable-message-sync`
  - `backup-data`
  - `write-status`
  - `restart-app`

The station worker rejects unknown actions and never executes shell text from
AWS. The first production job should be `update-app`, which starts the existing
local `morse-station-update.service`.

`enable-message-sync` is a fixed enrollment/recovery action for a station whose
local message experience is active but cloud message sync remains disabled. It
accepts no job-supplied command or setting. The helper preserves a private
configuration backup, atomically enables the flag, installs/enables the known
message-sync timer, and starts one immediate sync so saved outbox messages are
not discarded.

## Remote Update Job Flow

On the laptop, create a Job document such as:

```json
{
  "action": "update-app",
  "requested_by": "pappy",
  "reason": "release pi update"
}
```

Create a snapshot Job for one station:

```bash
aws iot create-job \
  --job-id morsepi-update-<station-id>-<yyyymmddhhmm> \
  --targets arn:aws:iot:<region>:<account-id>:thing/<station-id> \
  --document file://remote-update-job.json \
  --target-selection SNAPSHOT \
  --profile morsepi-setup-admin
```

When the station is online, its timer runs:

```bash
python3 /home/morse/morse-station/scripts/remote_update_iot.py --once
```

The worker:

1. asks AWS IoT Jobs for the next pending job for its Thing name;
2. writes `data/remote_update/latest_iot_job.json`;
3. rejects unknown actions;
4. marks accepted jobs `IN_PROGRESS`;
5. starts the known local system command; and
6. marks the job `SUCCEEDED` or `FAILED`.

Install the timer on a station:

```bash
mkdir -p /home/morse/.config/systemd/user
install -m 0644 /home/morse/morse-station/systemd/morse-station-remote-update.service /home/morse/.config/systemd/user/morse-station-remote-update.service
install -m 0644 /home/morse/morse-station/systemd/morse-station-remote-update.timer /home/morse/.config/systemd/user/morse-station-remote-update.timer
systemctl --user daemon-reload
systemctl --user enable --now morse-station-remote-update.timer
```

Check locally:

```bash
systemctl --user start morse-station-remote-update.service
journalctl --user -u morse-station-remote-update.service -n 80 --no-pager
cat /home/morse/morse-station/data/remote_update/latest_iot_job.json
```

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
- Decide whether to activate AWS IoT Jobs on all stations immediately or only
  after one more local soak on Pappy's station.
- Decide whether status should live only in S3, IoT Device Shadow, or both.
- Decide backup retention in S3.
- Decide whether station data should be encrypted with a per-station KMS key later.
- Decide whether remote updates should be manual-only or allowed on a timer.
