# AWS Setup Reference

This document is the credential-free setup reference for the morsePi AWS foundation. It explains what to create and why, but it does not store account numbers, access keys, secret keys, activation codes, or passwords.

Related docs:

- [AWS_BACKUP_SYNC_DESIGN.md](AWS_BACKUP_SYNC_DESIGN.md)
- [REMOTE_DEPLOYMENT_AWS.md](REMOTE_DEPLOYMENT_AWS.md)
- [REMOTE_BACKUP_STATUS_RUNBOOK.md](REMOTE_BACKUP_STATUS_RUNBOOK.md)
- [GRANDKID_STATION_DEPLOYMENT.md](GRANDKID_STATION_DEPLOYMENT.md)

## Target Shape

```text
GitHub              source code
S3                  backups, station status, progress snapshots, family summary
Systems Manager     first remote-admin bridge
AWS IoT Core         later lower-cost command/status/message layer
Pi scripts           actual backup, status, update, and restart work
```

Use S3 first. Add Systems Manager for remote hands. Add AWS IoT later only after backup/status works reliably.

## Setup Values

Fill these in while setting up AWS. Do not commit the filled-in copy if it includes account-specific details.

```text
AWS account id:          <account-id>
AWS region:              <region>
S3 bucket name:          <bucket-name>
Setup profile name:      morsepi-setup-admin
SSM managed role name:   morsepi-ssm-hybrid-role
```

Recommended station ids:

```text
pappy-test-station
pappy-station
astrid-liara-station
campbell-olivea-station
```

## Phase 1 Checklist

1. Choose Region and final bucket name.
2. Create temporary setup identity.
3. Configure a temporary AWS CLI profile on Pappy's laptop.
4. Create and harden the S3 bucket.
5. Create one narrow station identity for `pappy-test-station`.
6. Configure AWS CLI on the active Pi with only that station identity.
7. Test one real backup upload.
8. Test one real status upload.
9. Create the Systems Manager hybrid role and first activation.
10. Register the active Pi with Systems Manager if we decide to test SSM before sending units out.
11. Disable or delete the temporary setup access key.

## Current AWS Foundation

Created on 2026-07-02 local time:

```text
AWS account id:          674620572451
AWS region:              us-east-1
S3 bucket name:          morsepi-backups-luminerdy
Active test station:     pappy-test-station
Station IAM user:        morsepi-pappy-test-station
Station IAM policy:      morsepi-pappy-test-station-s3
Setup IAM user:          morsepi-setup-admin
Setup IAM policy:        morsepi-setup-admin-policy
Laptop setup profile:    morsepi-setup-admin
```

Verified:

- bucket public access is blocked
- bucket versioning is enabled
- bucket default encryption uses AES256
- active Pi can write to `stations/pappy-test-station/`
- active Pi cannot list another station's raw prefix
- active Pi uploaded one backup and one station status file
- broad local `admin` access key used during initial setup was deactivated after `morsepi-setup-admin` was verified

Do not commit AWS access keys, secret keys, session tokens, activation IDs/codes, or real admin PINs.

Reminder for later IoT work: keep the broad `admin` access key deactivated during normal operation. If AWS IoT setup needs permissions beyond `morsepi-setup-admin`, first prefer creating a purpose-limited IoT setup policy/user. Reactivate the broad `admin` key only if it is truly needed, and deactivate it again immediately after that setup task.

## Temporary Setup Identity

Use a temporary identity such as `morsepi-setup-admin` for provisioning only.

It needs enough permission to:

- verify identity with `sts:GetCallerIdentity`
- create/configure the S3 bucket
- create IAM users, policies, and access keys for station credentials
- create the Systems Manager hybrid service role
- create Systems Manager hybrid activations

After setup, disable or delete its access key. Keep normal station operation on narrow per-station credentials.

## AWS CLI Profile

Configure the laptop with a temporary setup profile:

```bash
aws configure --profile morsepi-setup-admin
```

Verify the identity before making resources:

```bash
aws sts get-caller-identity --profile morsepi-setup-admin
```

Do not commit CLI config files or credentials. On Windows they normally live under `%USERPROFILE%\.aws\`. On Linux/Pi they normally live under `~/.aws/`.

## S3 Bucket

Create one private bucket for backups, status, snapshots, inbox files, and family summaries.

```bash
aws s3api create-bucket \
  --bucket <bucket-name> \
  --region <region> \
  --create-bucket-configuration LocationConstraint=<region> \
  --profile morsepi-setup-admin
```

For `us-east-1`, AWS uses a slightly different create-bucket call:

```bash
aws s3api create-bucket \
  --bucket <bucket-name> \
  --region us-east-1 \
  --profile morsepi-setup-admin
```

Block public access:

```bash
aws s3api put-public-access-block \
  --bucket <bucket-name> \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
  --profile morsepi-setup-admin
```

Enable bucket versioning:

```bash
aws s3api put-bucket-versioning \
  --bucket <bucket-name> \
  --versioning-configuration Status=Enabled \
  --profile morsepi-setup-admin
```

Set default encryption with S3-managed keys:

```bash
aws s3api put-bucket-encryption \
  --bucket <bucket-name> \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
  --profile morsepi-setup-admin
```

Recommended S3 layout:

```text
s3://<bucket-name>/
  stations/
    <station-id>/
      backups/
      status/station_status.json
      snapshots/
      inbox/
  family/
    family_summary.json
    recent_wins.json
```

## Station IAM Policy

Each Pi gets its own station credential. Do not share credentials across stations.

Policy intent for one station:

- write only under `stations/<station-id>/`
- read only its own `stations/<station-id>/inbox/`
- read shared `family/`
- no bucket creation
- no IAM access
- no broad delete

Template policy for one station:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOnlyNeededPrefixes",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::<bucket-name>",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "stations/<station-id>/*",
            "family/*"
          ]
        }
      }
    },
    {
      "Sid": "WriteOwnStationObjects",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::<bucket-name>/stations/<station-id>/*"
      ]
    },
    {
      "Sid": "ReadFamilySummaryObjects",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": [
        "arn:aws:s3:::<bucket-name>/family/*"
      ]
    }
  ]
}
```

Create one IAM user per station:

```bash
aws iam create-user \
  --user-name morsepi-<station-id> \
  --profile morsepi-setup-admin
```

Create and attach the station policy:

```bash
aws iam create-policy \
  --policy-name morsepi-<station-id>-s3 \
  --policy-document file://station-policy.json \
  --profile morsepi-setup-admin

aws iam attach-user-policy \
  --user-name morsepi-<station-id> \
  --policy-arn arn:aws:iam::<account-id>:policy/morsepi-<station-id>-s3 \
  --profile morsepi-setup-admin
```

Create one access key for that station user:

```bash
aws iam create-access-key \
  --user-name morsepi-<station-id> \
  --profile morsepi-setup-admin
```

Store the station key only on the matching Pi. AWS only shows the secret access key when it is created; if it is lost, delete the old key and create a new one.

## Station Progress Sync Policy

After the three station identities exist, apply the additional narrow progress
sync policy from the laptop setup profile:

```bash
python scripts/apply_station_sync_policies.py --dry-run
python scripts/apply_station_sync_policies.py
```

The script uses `iam put-user-policy` to attach one inline policy named
`morsepi-station-progress-sync` to each existing station IAM user:

- `morsepi-pappy-test-station`
- `morsepi-astrid-liara-station`
- `morsepi-campbell-olivea-station`

The policy allows:

- listing the three station progress snapshot prefixes
- reading only each station's `snapshots/latest_progress.json`
- listing, reading, and writing immutable attempt objects only for the five
  configured family operator IDs. This lets the PIN-protected Manage Operators
  page enable a family member on any station without breaking progress sync.

The policy does not allow:

- deleting S3 objects
- reading raw backups from other stations
- writing another station's station-owned prefix
- managing IAM

The app still syncs only the operators currently enabled in that station's
local `students` roster. The broader family attempt-prefix permission is present
so a PIN-authorized roster change works immediately; it does not grant backup,
delete, message-content, or general bucket access.

Rostered student attempt access:

| Station user | Student attempt prefixes |
|---|---|
| `morsepi-pappy-test-station` | `pappy`, `astrid`, `liara`, `campbell`, `olivea` |
| `morsepi-astrid-liara-station` | `pappy`, `astrid`, `liara` |
| `morsepi-campbell-olivea-station` | `pappy`, `campbell`, `olivea` |

`pappy` is intentionally included on the grandkid station sync policies so the
adult operator can practice on any unit and confirm that progress merges back
to the shared Pappy record.

## Configure One Pi

Install AWS CLI if needed:

```bash
sudo apt update
sudo apt install -y awscli
```

Configure the station's own credential on the Pi:

```bash
aws configure
```

Set the station config:

```bash
cd /home/morse/morse-station
cp config/stations/<station-id>.example.json data/station_config.json
```

Edit `data/station_config.json`:

```json
{
  "station_id": "<station-id>",
  "backup_s3_uri": "s3://<bucket-name>",
  "admin_pin": ""
}
```

Test identity:

```bash
aws sts get-caller-identity
```

Test S3 prefix access:

```bash
aws s3 ls s3://<bucket-name>/stations/<station-id>/
```

## Backup And Status Test

Dry run first:

```bash
cd /home/morse/morse-station
python3 scripts/backup_data.py --label aws-test --dry-run-s3
python3 scripts/station_status.py --dry-run-s3
```

Real upload:

```bash
python3 scripts/backup_data.py --label aws-test --s3-uri s3://<bucket-name>
python3 scripts/station_status.py --s3-uri s3://<bucket-name>
```

Expected paths:

```text
s3://<bucket-name>/stations/<station-id>/backups/<timestamp>-<station-id>-aws-test.zip
s3://<bucket-name>/stations/<station-id>/status/station_status.json
```

Verify from laptop:

```bash
aws s3 ls s3://<bucket-name>/stations/<station-id>/backups/ --profile morsepi-setup-admin
aws s3 cp s3://<bucket-name>/stations/<station-id>/status/station_status.json - --profile morsepi-setup-admin
```

## Systems Manager Hybrid Activation

Systems Manager is for remote hands: shell access, manual update, backup/status checks, and troubleshooting.

Create an IAM role for hybrid managed nodes. The role must trust `ssm.amazonaws.com` and needs the AWS managed policy for SSM managed instances.

Trust policy shape:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ssm.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Create role and attach managed policy:

```bash
aws iam create-role \
  --role-name morsepi-ssm-hybrid-role \
  --assume-role-policy-document file://ssm-trust-policy.json \
  --profile morsepi-setup-admin

aws iam attach-role-policy \
  --role-name morsepi-ssm-hybrid-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore \
  --profile morsepi-setup-admin
```

Create one activation per station:

```bash
aws ssm create-activation \
  --default-instance-name <station-id> \
  --iam-role morsepi-ssm-hybrid-role \
  --registration-limit 1 \
  --tags Key=Project,Value=morsePi Key=StationId,Value=<station-id> \
  --profile morsepi-setup-admin
```

Treat the activation id and activation code like temporary secrets. Do not commit them.

On the Pi, install/register SSM Agent following the current AWS instructions for Raspberry Pi OS/Debian. Then verify the managed node appears in Systems Manager and can run a command while the station is online.

Useful first SSM command after registration:

```bash
cd /home/morse/morse-station
python3 scripts/station_status.py --s3-uri s3://<bucket-name>
```

## Cleanup

After the first station works:

1. Delete or disable the `morsepi-setup-admin` access key.
2. Confirm each station has only its own credential.
3. Confirm no credentials or activation codes were committed.
4. Confirm the S3 bucket has public access blocked, versioning enabled, and encryption configured.
5. Confirm at least one backup and one status file exist for the test station.

## Later

After backup/status is proven:

- Create `family/family_summary.json`.
- Add progress snapshot upload.
- Add a small summarizer that combines station snapshots into family progress.
- Evaluate AWS IoT Core for lower-cost command triggers and future family Morse messages.

## Phase 7B Message Router

The message transport keeps every Pi on its existing station policy. A Pi
writes snapshots, outbox messages, and receipts only below its own
`stations/<station-id>/` prefix. The Lambda router independently validates and
copies accepted inbox/status objects to other approved station prefixes.

Repository assets:

```text
cloud/family_directory.json
cloud/router-trust-policy.json
cloud/router-policy.template.json
cloud/s3-notification.template.json
cloud/lambda_function.py
cloud/message_router.py
scripts/package_message_router.py
```

Package the router:

```bash
python3 scripts/package_message_router.py
```

The deployment identity needs only these additional setup capabilities:

- create/get/tag/pass `morsepi-message-router-role`;
- attach or put the router's narrow S3/CloudWatch policy;
- create/get/update/invoke `morsepi-message-router` Lambda;
- add an S3-scoped Lambda invoke permission; and
- get/put the notification configuration on the MorsePi bucket.

The current `morsepi-setup-admin` policy intentionally does **not** include
Lambda creation, the new router role, or bucket-notification changes. Do not
self-expand that identity. Temporarily reactivate the broad setup administrator
or have an AWS administrator grant the exact capabilities above, deploy and
verify the router, then deactivate the broad key again.

Deployment order:

1. Replace placeholders in `cloud/router-policy.template.json` and create the
   `morsepi-message-router-role` with the trust policy.
2. Package the Lambda and create `morsepi-message-router` in `us-east-1` with
   handler `cloud.lambda_function.lambda_handler`, Python 3.13, 128 MB, a
   15-second timeout, and `MORSEPI_BUCKET=morsepi-backups-luminerdy`.
3. Upload `cloud/family_directory.json` to
   `family/messaging/directory.json`.
4. Grant `s3.amazonaws.com` permission to invoke the Lambda, restricted by
   bucket ARN and AWS account.
5. Preserve any existing bucket notifications, then add the three
   non-overlapping station-prefix rules from
   `cloud/s3-notification.template.json`.
6. Install the disabled message-sync timer on each Pi.
7. Upload current learning snapshots and verify sanitized family summaries.
8. Run the three-station offline delivery/receipt rehearsal before setting
   `message_sync_enabled` to true for normal use.

Deployment status on 2026-08-02:

- `morsepi-message-router-role` and `morsepi-message-router` are deployed in
  `us-east-1` with the narrow router policy and bucket-scoped invoke permission.
- The family directory and three non-overlapping station notification rules are
  installed in `morsepi-backups-luminerdy`.
- The ten-minute message-sync timer is installed and enabled on all three Pis.
- A live isolated Pappy-to-Astrid message completed routing, download, decode,
  and receipt return; the unrelated Campbell/Olivea station received nothing.
- `message_sync_enabled` is true on Pappy and Astrid/Liara for the initial
  ten-minute live test. It remains false on Campbell/Olivea until that station
  joins the test.

The Lambda reads and writes the same bucket. Input and output sub-prefixes are
different, and the router ignores inbox/status objects, so an output event can
cause at most one ignored invocation rather than a recursive write loop. AWS
documents both the same-bucket recursion risk and the requirement that S3
notification prefixes for the same event type must not overlap:

- https://docs.aws.amazon.com/lambda/latest/dg/with-s3-example.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-filtering.html

## Official References

- AWS CLI `s3api put-public-access-block`: https://docs.aws.amazon.com/cli/latest/reference/s3api/put-public-access-block.html
- AWS CLI `s3api put-bucket-encryption`: https://docs.aws.amazon.com/cli/latest/reference/s3api/put-bucket-encryption.html
- AWS CLI `iam create-access-key`: https://docs.aws.amazon.com/cli/latest/reference/iam/create-access-key.html
- AWS CLI `ssm create-activation`: https://docs.aws.amazon.com/cli/latest/reference/ssm/create-activation.html
