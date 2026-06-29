# AWS Backup And Sync Design

This note captures the first cloud design for the family Morse stations.

## Goals

- Back up every deployed Pi when it is online.
- Keep each device credential narrow and revocable.
- Consolidate safe progress snapshots across stations.
- Show family progress around practice and persistence, not ranking.
- Give Pappy a practical way to connect and update deployed stations.
- Leave room for future station-to-station messages.

## Phase 1 Shape

```text
S3                  backups, station status, progress snapshots, family summary
Systems Manager     first remote-admin and manual update path
GitHub              source code
Pi scripts          backup, status, and safe update execution
```

Systems Manager is for remote hands. It should not become the normal app sync layer.

## Phase 2 Shape

```text
AWS IoT Core         lightweight commands, online presence, future messages
S3                  backup and family summary history
```

IoT can eventually replace most Systems Manager day-to-day command needs if it proves cheaper and simpler for always-available station commands.

## S3 Layout

```text
s3://morsepi-backups/
  stations/
    <station-id>/
      backups/
      status/
      snapshots/
      inbox/
  family/
    family_summary.json
    recent_wins.json
```

Examples:

```text
stations/astrid-station/backups/
stations/astrid-station/status/station_status.json
stations/astrid-station/snapshots/latest_progress.json
family/family_summary.json
```

## Device Credential Rule

Each Pi gets its own credential. Never share one AWS key across stations.

A station may:

- write to `stations/<its-station-id>/`
- read `stations/<its-station-id>/inbox/`
- read `family/`

A station may not:

- read or overwrite another station's raw backups
- delete bucket contents broadly
- create AWS resources
- manage IAM

## Family Progress Philosophy

The shared view should celebrate visibility into practice, not perfection.

Good shared metrics:

- practice minutes this week
- Daily Missions completed
- new letters learned
- words attempted
- recent wins
- personal bests
- family total practice time
- family total signals completed

Avoid a simple ranked leaderboard. Use a Family Signal Board or Grand Operator Board that shows effort, progress, and recent wins without creating a last-place student.

## Temporary Setup User

Create a temporary AWS user such as `morsepi-setup-admin` for initial setup only.

Needed setup abilities:

- `sts:GetCallerIdentity`
- create and configure the MorsePi S3 bucket
- create IAM users, policies, and access keys for each station
- create Systems Manager hybrid activations

After setup:

- delete the setup access key, or
- disable the setup user, or
- replace it with a narrower maintenance identity

## Tomorrow's First AWS Tasks

1. Confirm AWS account and Region.
2. Create/configure the temporary setup user.
3. Configure an AWS CLI profile on the laptop.
4. Create the S3 bucket with public access blocked, encryption enabled, and versioning enabled.
5. Create one narrow station credential for `pappy-test-station`.
6. Test one backup upload and one status upload from the active Pi.
7. Create the first family summary file shape.
8. Prepare Systems Manager activation notes for the first deployed Pi.
