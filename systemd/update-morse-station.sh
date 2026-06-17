#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MORSE_APP_DIR:-/home/morse/morse-station}"
BRANCH="${MORSE_UPDATE_BRANCH:-main}"
REMOTE="${MORSE_UPDATE_REMOTE:-origin}"
SERVICE="${MORSE_UPDATE_SERVICE:-morse-station.service}"

cd "$APP_DIR"

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Tracked local changes are present; skipping update."
    exit 0
fi

git fetch "$REMOTE" "$BRANCH"

LOCAL_COMMIT="$(git rev-parse HEAD)"
REMOTE_COMMIT="$(git rev-parse "$REMOTE/$BRANCH")"

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "Already up to date at $LOCAL_COMMIT."
    exit 0
fi

if ! git merge-base --is-ancestor "$LOCAL_COMMIT" "$REMOTE_COMMIT"; then
    echo "Remote branch is not a fast-forward from local checkout; skipping update."
    exit 1
fi

git merge --ff-only "$REMOTE/$BRANCH"
python3 -m py_compile app.py practice_progress.py practice_attempts.py
systemctl --user restart "$SERVICE"

echo "Updated Morse station to $REMOTE_COMMIT and restarted $SERVICE."
