#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MORSE_APP_DIR:-/home/morse/morse-station}"
BRANCH="${MORSE_UPDATE_BRANCH:-main}"
REMOTE="${MORSE_UPDATE_REMOTE:-origin}"
SERVICE="${MORSE_UPDATE_SERVICE:-morse-station.service}"
STATION_ID="${MORSE_STATION_ID:-}"
BACKUP_S3_URI="${MORSE_BACKUP_S3_URI:-}"

cd "$APP_DIR"

backup_args=(--label pre-update)
status_args=()

if [ -n "$STATION_ID" ]; then
    backup_args+=(--station-id "$STATION_ID")
    status_args+=(--station-id "$STATION_ID")
fi

if [ -n "$BACKUP_S3_URI" ]; then
    backup_args+=(--s3-uri "$BACKUP_S3_URI")
    status_args+=(--s3-uri "$BACKUP_S3_URI")
fi

python3 scripts/backup_data.py "${backup_args[@]}"

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Tracked local changes are present; skipping update."
    python3 scripts/station_status.py "${status_args[@]}"
    exit 0
fi

git fetch "$REMOTE" "$BRANCH"

LOCAL_COMMIT="$(git rev-parse HEAD)"
REMOTE_COMMIT="$(git rev-parse "$REMOTE/$BRANCH")"

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "Already up to date at $LOCAL_COMMIT."
    python3 scripts/station_status.py "${status_args[@]}"
    exit 0
fi

if ! git merge-base --is-ancestor "$LOCAL_COMMIT" "$REMOTE_COMMIT"; then
    echo "Remote branch is not a fast-forward from local checkout; skipping update."
    python3 scripts/station_status.py "${status_args[@]}"
    exit 1
fi

git merge --ff-only "$REMOTE/$BRANCH"
python3 -m py_compile app.py morse.py practice_progress.py practice_attempts.py student_profiles.py scripts/backup_data.py scripts/station_status.py
systemctl --user restart "$SERVICE"
python3 scripts/station_status.py "${status_args[@]}"

echo "Updated Morse station to $REMOTE_COMMIT and restarted $SERVICE."
