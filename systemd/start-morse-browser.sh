#!/bin/sh
set -eu

URL="http://localhost:5000/"

if pgrep -f "chromium.*localhost:5000" >/dev/null 2>&1; then
    exit 0
fi

for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    if curl -fsS "$URL" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

exec /usr/bin/chromium --new-window --start-fullscreen "$URL"
