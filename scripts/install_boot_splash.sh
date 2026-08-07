#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/morse/morse-station}"
SOURCE_SPLASH="${1:-$PROJECT_DIR/docs/assets/morsepi-boot-splash.png}"
PLYMOUTH_SPLASH="${PLYMOUTH_SPLASH:-/usr/share/plymouth/themes/pix/splash.png}"

if [ ! -f "$SOURCE_SPLASH" ]; then
  echo "Boot splash image not found: $SOURCE_SPLASH" >&2
  exit 1
fi

if [ ! -d "$(dirname "$PLYMOUTH_SPLASH")" ]; then
  echo "Plymouth pix theme folder not found: $(dirname "$PLYMOUTH_SPLASH")" >&2
  exit 1
fi

if [ -f "$PLYMOUTH_SPLASH" ] && [ ! -f "${PLYMOUTH_SPLASH}.morsepi-original" ]; then
  sudo install -m 0644 "$PLYMOUTH_SPLASH" "${PLYMOUTH_SPLASH}.morsepi-original"
  echo "Saved original splash: ${PLYMOUTH_SPLASH}.morsepi-original"
fi

if [ -f "$PLYMOUTH_SPLASH" ]; then
  BACKUP="${PLYMOUTH_SPLASH}.morsepi-backup-$(date -u +%Y%m%d-%H%M%S)"
  sudo install -m 0644 "$PLYMOUTH_SPLASH" "$BACKUP"
  echo "Saved current splash backup: $BACKUP"
fi

sudo install -m 0644 "$SOURCE_SPLASH" "$PLYMOUTH_SPLASH"
echo "Installed morsePi boot splash: $PLYMOUTH_SPLASH"

CMDLINE=""
for candidate in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
  if [ -f "$candidate" ]; then
    CMDLINE="$candidate"
    break
  fi
done

if [ -n "$CMDLINE" ] && ! grep -qw splash "$CMDLINE"; then
  echo "Warning: $CMDLINE does not include 'splash', so Plymouth may not show during boot." >&2
fi

if command -v update-initramfs >/dev/null 2>&1; then
  sudo update-initramfs -u || true
fi
