#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${MORSE_APP_DIR:-/home/morse/morse-station}"
exec "$APP_DIR/scripts/update_station.sh"
