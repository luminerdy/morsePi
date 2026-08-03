#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/morse/morse-station}"
SOURCE_WALLPAPER="${1:-$PROJECT_DIR/docs/assets/morsepi-desktop-wallpaper.png}"
DEST_DIR="${HOME}/Pictures/morsePi"
DEST_WALLPAPER="${DEST_DIR}/morsepi-desktop-wallpaper.png"
PCMANFM_CONFIG_DIR="${HOME}/.config/pcmanfm/default"

if [ ! -f "$SOURCE_WALLPAPER" ]; then
    echo "Wallpaper image not found: $SOURCE_WALLPAPER" >&2
    exit 1
fi

mkdir -p "$DEST_DIR" "$PCMANFM_CONFIG_DIR" "${HOME}/Desktop"
install -m 0644 "$SOURCE_WALLPAPER" "$DEST_WALLPAPER"

write_config() {
    local config_path="$1"
    cat > "$config_path" <<EOF
[*]
desktop_bg=#D6D3DE
desktop_shadow=#D6D3DE
desktop_fg=#E8E8E8
desktop_font=Nunito Sans Light 12
wallpaper=${DEST_WALLPAPER}
wallpaper_mode=crop
show_home=0
show_trash=1
show_mounts=1
folder=${HOME}/Desktop
EOF
}

connectors=()
while IFS= read -r status_path; do
    if [ "$(cat "$status_path" 2>/dev/null || true)" = "connected" ]; then
        connector="$(basename "$(dirname "$status_path")")"
        connector="${connector#card*-}"
        connectors+=("$connector")
    fi
done < <(find /sys/class/drm -maxdepth 2 -name status 2>/dev/null | sort)

if [ "${#connectors[@]}" -eq 0 ]; then
    connectors=("HDMI-A-1" "HDMI-A-2" "DSI-1")
fi

for connector in "${connectors[@]}"; do
    write_config "${PCMANFM_CONFIG_DIR}/desktop-items-${connector}.conf"
done

if pgrep -u "$USER" pcmanfm >/dev/null 2>&1; then
    pcmanfm --reconfigure >/dev/null 2>&1 || true
fi

echo "Installed morsePi wallpaper at ${DEST_WALLPAPER}."
echo "Configured PCManFM desktop profiles for: ${connectors[*]}."
echo "If the old wallpaper remains visible, reboot or log out/in once."
