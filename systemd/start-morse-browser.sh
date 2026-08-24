#!/bin/sh
set -eu

URL="${MORSE_BROWSER_URL:-http://localhost:5000/touch}"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
WAYLAND_SOCKET="${WAYLAND_DISPLAY:-wayland-0}"
READY=0

export XDG_RUNTIME_DIR="$RUNTIME_DIR"
export WAYLAND_DISPLAY="$WAYLAND_SOCKET"

for _ in $(seq 1 120); do
    if [ -S "$RUNTIME_DIR/$WAYLAND_SOCKET" ] && curl -fsS "$URL" >/dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done

if [ "$READY" -ne 1 ]; then
    echo "Morse browser prerequisites were not ready within 120 seconds." >&2
    exit 1
fi

exec /usr/bin/chromium --ozone-platform=wayland --kiosk --new-window "$URL"
