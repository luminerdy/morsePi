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
UPDATE_REPORT="$APP_DIR/data/update/latest_update.json"
UPDATE_ARTIFACT_DIR="$APP_DIR/data/update/diagnostics"
UPDATE_LOCK="$APP_DIR/data/update/update.lock"
UPDATE_DIAGNOSTIC_HELPER="$APP_DIR/data/update/update_diagnostics_runtime.py"
STARTING_COMMIT=""
TARGET_COMMIT=""

record_update() {
    local status="$1"
    local reason="$2"
    local returncode="$3"
    local preserve_patch="${4:-0}"
    local args=(
        --app-dir "$APP_DIR"
        --artifact-dir "$UPDATE_ARTIFACT_DIR"
        --output "$UPDATE_REPORT"
        --status "$status"
        --reason "$reason"
        --returncode "$returncode"
    )

    if [ -n "$STARTING_COMMIT" ]; then
        args+=(--starting-commit "$STARTING_COMMIT")
    fi
    if [ -n "$TARGET_COMMIT" ]; then
        args+=(--target-commit "$TARGET_COMMIT")
    fi
    if [ "$preserve_patch" = "1" ]; then
        args+=(--preserve-patch)
    fi

    PYTHONPATH="$APP_DIR" python3 "$UPDATE_DIAGNOSTIC_HELPER" "${args[@]}"
}

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

mkdir -p "$(dirname "$UPDATE_LOCK")" "$UPDATE_ARTIFACT_DIR"
install -m 0644 "$APP_DIR/scripts/update_diagnostics.py" "$UPDATE_DIAGNOSTIC_HELPER"
STARTING_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || true)"

if ! command -v flock >/dev/null 2>&1; then
    record_update "blocked" "update-lock-unavailable" 21
    exit 21
fi

exec 9>"$UPDATE_LOCK"
if ! flock -n 9; then
    record_update "blocked" "update-already-running" 21
    exit 21
fi

record_update "in-progress" "starting" 0

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

install_browser_supervisor() {
    local installed_unit="$HOME/.config/systemd/user/morse-station-browser.service"

    if [ ! -x "$BROWSER_INSTALLER" ]; then
        return 0
    fi

    if [ ! -f "$installed_unit" ] || systemctl --user is-active --quiet morse-station-browser.service; then
        "$BROWSER_INSTALLER" --start
        return
    fi

    "$BROWSER_INSTALLER"
}

install_update_services() {
    local user_unit_dir="$HOME/.config/systemd/user"
    local bin_dir="$HOME/bin"
    local source

    mkdir -p "$user_unit_dir" "$bin_dir"
    install -m 0755 "$APP_DIR/systemd/update-morse-station.sh" "$bin_dir/update-morse-station.sh"

    for source in \
        morse-station-update.service \
        morse-station-update.timer \
        morse-station-remote-update.service \
        morse-station-remote-update.timer \
        morse-station-sync.service \
        morse-station-sync.timer; do
        install -m 0644 "$APP_DIR/systemd/$source" "$user_unit_dir/$source"
    done

    systemctl --user daemon-reload
}

if ! python3 scripts/backup_data.py "${backup_args[@]}"; then
    record_update "failed" "pre-update-backup-failed" 30
    exit 30
fi
if ! run_pending_migrations; then
    record_update "failed" "pre-update-migration-failed" 31
    write_status_and_snapshots || true
    exit 31
fi

if ! install_browser_supervisor; then
    echo "Browser supervision preflight failed."
    record_update "failed" "browser-supervision-preflight-failed" 32
    write_status_and_snapshots || true
    exit 32
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Tracked local changes are present; blocking update."
    record_update "blocked" "tracked-local-changes" 20 1
    write_status_and_snapshots || true
    exit 20
fi

if ! git fetch "$REMOTE" "$BRANCH"; then
    record_update "failed" "release-fetch-failed" 33
    write_status_and_snapshots || true
    exit 33
fi

LOCAL_COMMIT="$(git rev-parse HEAD)"
REMOTE_COMMIT="$(git rev-parse "$REMOTE/$BRANCH")"
STARTING_COMMIT="$LOCAL_COMMIT"
TARGET_COMMIT="$REMOTE_COMMIT"
record_update "in-progress" "release-fetched" 0

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "Already up to date at $LOCAL_COMMIT."
    if ! install_update_services; then
        record_update "failed" "update-service-install-failed" 42
        write_status_and_snapshots || true
        exit 42
    fi
    record_update "current" "already-current" 0
    write_status_and_snapshots || true
    exit 0
fi

if ! git merge-base --is-ancestor "$LOCAL_COMMIT" "$REMOTE_COMMIT"; then
    echo "Remote branch is not a fast-forward from local checkout; blocking update."
    record_update "blocked" "release-not-fast-forward" 34
    write_status_and_snapshots || true
    exit 34
fi

if ! git merge --ff-only "$REMOTE/$BRANCH"; then
    record_update "failed" "fast-forward-merge-failed" 35
    write_status_and_snapshots || true
    exit 35
fi

if ! run_update_checks; then
    echo "Update checks failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    record_update "rolled-back" "update-checks-failed" 36
    write_status_and_snapshots || true
    exit 36
fi

if ! run_pending_migrations; then
    echo "Student identity migration failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    record_update "rolled-back" "post-update-migration-failed" 37
    write_status_and_snapshots || true
    exit 37
fi

if ! install_browser_supervisor; then
    echo "Browser supervision installation failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    systemctl --user restart "$SERVICE"
    check_health
    record_update "rolled-back" "browser-supervision-install-failed" 38
    write_status_and_snapshots || true
    exit 38
fi

if ! install_update_services; then
    echo "Update service installation failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    systemctl --user restart "$SERVICE" || true
    record_update "rolled-back" "update-service-install-failed" 42
    write_status_and_snapshots || true
    exit 42
fi

if ! systemctl --user restart "$SERVICE"; then
    git reset --hard "$LOCAL_COMMIT"
    systemctl --user restart "$SERVICE" || true
    record_update "rolled-back" "app-restart-failed" 39
    write_status_and_snapshots || true
    exit 39
fi
if ! check_health; then
    echo "Health check failed; rolling back to $LOCAL_COMMIT."
    git reset --hard "$LOCAL_COMMIT"
    systemctl --user restart "$SERVICE"
    check_health
    record_update "rolled-back" "health-check-failed" 40
    write_status_and_snapshots || true
    exit 40
fi

ENDING_COMMIT="$(git rev-parse HEAD)"
if [ "$ENDING_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo "Ending commit does not match the fetched release; rolling back."
    git reset --hard "$LOCAL_COMMIT"
    systemctl --user restart "$SERVICE"
    check_health
    record_update "rolled-back" "ending-commit-mismatch" 41
    write_status_and_snapshots || true
    exit 41
fi

record_update "succeeded" "updated" 0
write_status_and_snapshots || true

echo "Updated Morse station to $REMOTE_COMMIT and restarted $SERVICE."
