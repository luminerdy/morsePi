#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MORSE_APP_DIR:-/home/morse/morse-station}"
USER_HOME="${MORSE_USER_HOME:-/home/morse}"
UNIT_DIR="${MORSE_USER_UNIT_DIR:-$USER_HOME/.config/systemd/user}"
BIN_DIR="${MORSE_USER_BIN_DIR:-$USER_HOME/bin}"
SERVICE="${MORSE_BROWSER_SERVICE:-morse-station-browser.service}"
START_SERVICE=0

if [ "${1:-}" = "--start" ]; then
    START_SERVICE=1
fi

mkdir -p "$UNIT_DIR" "$BIN_DIR"
install -m 0755 "$APP_DIR/systemd/start-morse-browser.sh" "$BIN_DIR/start-morse-browser.sh"
install -m 0644 "$APP_DIR/systemd/morse-station-browser.service" "$UNIT_DIR/$SERVICE"

systemctl --user daemon-reload
systemctl --user enable "$SERVICE"

if [ "$START_SERVICE" -eq 1 ]; then
    systemctl --user stop "$SERVICE" 2>/dev/null || true
    pkill -x chromium 2>/dev/null || true
    sleep 2
    systemctl --user start "$SERVICE"

    browser_is_ready() {
        local main_pid
        main_pid="$(systemctl --user show "$SERVICE" -p MainPID --value 2>/dev/null || true)"
        systemctl --user is-active --quiet "$SERVICE" &&
            [ -n "$main_pid" ] &&
            [ "$main_pid" != "0" ] &&
            [ "$(cat "/proc/$main_pid/comm" 2>/dev/null || true)" = "chromium" ]
    }

    for _ in $(seq 1 15); do
        if browser_is_ready; then
            break
        fi
        sleep 1
    done

    if ! browser_is_ready; then
        systemctl --user disable --now "$SERVICE" 2>/dev/null || true
        echo "Supervised Morse browser did not become active; legacy autostart was preserved." >&2
        exit 1
    fi
fi

LABWC_AUTOSTART="$USER_HOME/.config/labwc/autostart"
if [ -f "$LABWC_AUTOSTART" ]; then
    sed -i '\|/home/morse/bin/start-morse-browser.sh &|d' "$LABWC_AUTOSTART"
fi

rm -f "$USER_HOME/.config/autostart/morse-station-browser.desktop"

echo "Installed $SERVICE and removed legacy browser autostart entries."
