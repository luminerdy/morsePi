import argparse
import json
import subprocess
import sys


BUCKET = "morsepi-backups-luminerdy"
POLICY_NAME = "morsepi-station-progress-sync"
READER_GROUP = "morsepi-family-activity-readers"
READER_POLICY_NAME = "morsepi-family-activity-read"
FAMILY_STUDENTS = ["pappy", "astrid", "liara", "campbell", "olivea"]
STATIONS = {
    "pappy-test-station": {
        "user": "morsepi-pappy-test-station",
        "students": FAMILY_STUDENTS,
    },
    "astrid-liara-station": {
        "user": "morsepi-astrid-liara-station",
        "students": FAMILY_STUDENTS,
    },
    "campbell-olivea-station": {
        "user": "morsepi-campbell-olivea-station",
        "students": FAMILY_STUDENTS,
    },
}


def snapshot_list_prefixes():
    return [f"stations/{station_id}/snapshots/*" for station_id in STATIONS]


def snapshot_object_arns(bucket):
    return [
        f"arn:aws:s3:::{bucket}/stations/{station_id}/snapshots/latest_progress.json"
        for station_id in STATIONS
    ]


def student_list_prefixes(student_ids):
    prefixes = []
    for student_id in student_ids:
        prefixes.append(f"students/{student_id}/attempts/*")
    return prefixes


def student_object_arns(bucket, student_ids):
    arns = []
    for student_id in student_ids:
        arns.append(f"arn:aws:s3:::{bucket}/students/{student_id}/attempts/*")
    return arns


def family_activity_list_prefixes():
    prefixes = []
    for station_id in STATIONS:
        prefixes.extend([
            f"stations/{station_id}/activity",
            f"stations/{station_id}/activity/*",
        ])
    return prefixes


def family_activity_object_arns(bucket):
    arns = []
    for station_id in STATIONS:
        arns.extend([
            f"arn:aws:s3:::{bucket}/stations/{station_id}/activity/*",
            f"arn:aws:s3:::{bucket}/stations/{station_id}/status/station_status.json",
        ])
    return arns


def build_family_activity_reader_policy(bucket):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ListFamilyActivityAndStatus",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": f"arn:aws:s3:::{bucket}",
                "Condition": {"StringLike": {"s3:prefix": family_activity_list_prefixes()}},
            },
            {
                "Sid": "ReadFamilyActivityAndStatus",
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": family_activity_object_arns(bucket),
            },
        ],
    }


def build_policy(bucket, student_ids, station_id=None):
    statements = [
        {
            "Sid": "ListFamilySnapshotsAndRosteredStudentAttempts",
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": f"arn:aws:s3:::{bucket}",
            "Condition": {
                "StringLike": {
                    "s3:prefix": snapshot_list_prefixes() + student_list_prefixes(student_ids)
                }
            },
        },
        {
            "Sid": "ReadFamilyProgressSnapshots",
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": snapshot_object_arns(bucket),
        },
        {
            "Sid": "ReadWriteRosteredStudentAttempts",
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject"],
            "Resource": student_object_arns(bucket, student_ids),
        },
    ]
    if station_id:
        statements.append({
            "Sid": "WriteOwnStationActivity",
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": f"arn:aws:s3:::{bucket}/stations/{station_id}/activity/*",
        })
    return {
        "Version": "2012-10-17",
        "Statement": statements,
    }


def apply_reader_group_policy(
    bucket,
    profile,
    dry_run=False,
    runner=subprocess.run,
    aws_executable="aws",
):
    policy = build_family_activity_reader_policy(bucket)
    commands = [
        [aws_executable, "iam", "create-group", "--group-name", READER_GROUP, "--profile", profile],
        [
            aws_executable,
            "iam",
            "put-group-policy",
            "--group-name",
            READER_GROUP,
            "--policy-name",
            READER_POLICY_NAME,
            "--policy-document",
            json.dumps(policy, separators=(",", ":")),
            "--profile",
            profile,
        ],
        [
            aws_executable,
            "iam",
            "add-user-to-group",
            "--group-name",
            READER_GROUP,
            "--user-name",
            STATIONS["pappy-test-station"]["user"],
            "--profile",
            profile,
        ],
    ]
    if dry_run:
        return {"commands": commands, "policy": policy, "returncode": 0, "skipped": True}

    results = []
    for index, command in enumerate(commands):
        result = runner(command, capture_output=True, text=True)
        results.append(result)
        group_already_exists = index == 0 and "EntityAlreadyExists" in (result.stderr or "")
        if result.returncode != 0 and not group_already_exists:
            return {
                "commands": commands,
                "policy": policy,
                "results": results,
                "returncode": result.returncode,
                "skipped": False,
            }
    return {"commands": commands, "policy": policy, "results": results, "returncode": 0, "skipped": False}


def put_user_policy(
    station_id,
    station,
    bucket,
    profile,
    dry_run=False,
    runner=subprocess.run,
    aws_executable="aws",
):
    policy = build_policy(bucket, station["students"], station_id=station_id)
    command = [
        aws_executable,
        "iam",
        "put-user-policy",
        "--user-name",
        station["user"],
        "--policy-name",
        POLICY_NAME,
        "--policy-document",
        json.dumps(policy, separators=(",", ":")),
        "--profile",
        profile,
    ]
    if dry_run:
        return {"command": command, "policy": policy, "station_id": station_id, "skipped": True}
    result = runner(command, capture_output=True, text=True)
    return {
        "command": command,
        "policy": policy,
        "returncode": result.returncode,
        "skipped": False,
        "station_id": station_id,
        "stderr": result.stderr,
        "stdout": result.stdout,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Apply narrow S3 snapshot and student-attempt sync policies to MorsePi station users."
    )
    parser.add_argument("--bucket", default=BUCKET, help="S3 bucket name.")
    parser.add_argument("--profile", default="morsepi-setup-admin", help="AWS CLI setup profile.")
    parser.add_argument("--aws-executable", default="aws", help="AWS CLI executable path.")
    parser.add_argument("--dry-run", action="store_true", help="Print policies without changing AWS.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    failures = 0
    for station_id, station in STATIONS.items():
        print(f"== {station_id} -> {station['user']} ==")
        result = put_user_policy(
            station_id,
            station,
            args.bucket,
            args.profile,
            args.dry_run,
            aws_executable=args.aws_executable,
        )
        if result["skipped"]:
            print(json.dumps(result["policy"], indent=2, sort_keys=True))
            continue
        if result["stdout"]:
            print(result["stdout"].rstrip())
        if result["stderr"]:
            print(result["stderr"].rstrip(), file=sys.stderr)
        if result["returncode"] != 0:
            failures += 1
            print(f"FAILED: {station_id} returned {result['returncode']}", file=sys.stderr)
        else:
            print(f"OK: policy applied to {station['user']}")

    print(f"== Pappy family activity reader group: {READER_GROUP} ==")
    reader = apply_reader_group_policy(
        args.bucket,
        args.profile,
        args.dry_run,
        aws_executable=args.aws_executable,
    )
    if reader["skipped"]:
        print(json.dumps(reader["policy"], indent=2, sort_keys=True))
    elif reader["returncode"] != 0:
        failures += 1
        failed = reader["results"][-1]
        if failed.stderr:
            print(failed.stderr.rstrip(), file=sys.stderr)
        print("FAILED: Pappy reader group policy", file=sys.stderr)
    else:
        print("OK: Pappy reader group policy applied")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
