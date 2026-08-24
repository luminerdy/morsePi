#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MORSE_APP_DIR:-/home/morse/morse-station}"
BRANCH="${MORSE_UPDATE_BRANCH:-release/pi}"
REMOTE="${MORSE_UPDATE_REMOTE:-origin}"
SERVICE="${MORSE_UPDATE_SERVICE:-morse-station.service}"
STATION_ID="${MORSE_STATION_ID:-}"
BACKUP_S3_URI="${MORSE_BACKUP_S3_URI:-}"
HEALTH_URL="${MORSE_HEALTH_URL:-http://127.0.0.1:5000/touch}"
HEALTH_TIMEOUT_SECONDS="${MORSE_HEALTH_TIMEOUT_SECONDS:-30}"
RUN_TESTS="${MORSE_UPDATE_RUN_TESTS:-1}"
BROWSER_INSTALLER="$APP_DIR/scripts/install_browser_supervisor.sh"

check_health() {
    python3 - "$HEALTH_URL" "$HEALTH_TIMEOUT_SECONDS" <<'PY'
import sys
import time
from urllib.request import urlopen

url = sys.argv[1]
timeout_seconds = float(sys.argv[2])
deadline = time.time() + timeout_seconds
last_error = ""

while time.time() < deadline:
    try:
        with urlopen(url, timeout=3) as response:
            if 200 <= response.status < 500:
                print(f"Health check OK: {url} returned {response.status}")
                sys.exit(0)
    except Exception as error:
        last_error = str(error)

    time.sleep(1)

print(f"Health check failed for {url}: {last_error}", file=sys.stderr)
sys.exit(1)
PY
}

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

write_status_and_snapshots() {
    python3 scripts/station_status.py "${status_args[@]}"
    python3 scripts/progress_snapshot.py
    python3 scripts/family_progress.py
}

run_update_checks() {
    python3 -m py_compile \
        app.py \
        morse.py \
        practice_progress.py \
        practice_attempts.py \
        student_profiles.py \
        student_identity.py \
        message_store.py \
        message_sync.py \
        scripts/backup_data.py \
        scripts/station_status.py \
        scripts/progress_snapshot.py \
        scripts/family_progress.py \
        scripts/cleanup_removed_messages.py \
        scripts/migrate_student_uuids.py

    if [ "$RUN_TESTS" = "1" ]; then
        python3 -m unittest discover -s tests
    fi
}

run_pending_migrations() {
    if [ -f scripts/cleanup_removed_messages.py ]; then
        python3 scripts/cleanup_removed_messages.py
    fi
    if [ -f scripts/migrate_student_uuids.py ]; then
        python3 scripts/migrate_student_uuids.py
    fi
}

python3 scripts/backup_data.py "${backup_args[@]}"
run_pending_migrations

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Tracked local changes are present; skipping update."
    write_status_and_snapshots
    exit 0
fi

git fetch "$REMOTE" "$BRANCH"

LOCAL_COMMIT="$(git rev-parse HEAD)"
REMOTE_COMMIT="$(git rev-parse "$REMOTE/$BRANCH")"

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "Already up to date at $LOCAL_COMMIT."
    write_status_and_snapshots
    exit 0
fi

if ! git merge-base --is-ancestor "$LOCAL_COMMIT" "$REMOTE_COMMIT"; then
    echo "Remote branch is not a fast-forward from local checkout; skipping update."
    write_status_and_snapshots
    exit 1
fi

git merge --ff-only "$REMOTE/$BRANCH"

if ! run_update_checks; then
    echo "Update checks failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    write_status_and_snapshots
    exit 1
fi

if ! run_pending_migrations; then
    echo "Student identity migration failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    write_status_and_snapshots
    exit 1
fi

if [ -x "$BROWSER_INSTALLER" ] && ! "$BROWSER_INSTALLER" --start; then
    echo "Browser supervision installation failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    systemctl --user restart "$SERVICE"
    check_health
    write_status_and_snapshots
    exit 1
fi

systemctl --user restart "$SERVICE"
if ! check_health; then
    echo "Health check failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    systemctl --user restart "$SERVICE"
    check_health
    write_status_and_snapshots
    exit 1
fi

write_status_and_snapshots

echo "Updated Morse station to $REMOTE_COMMIT and restarted $SERVICE."
