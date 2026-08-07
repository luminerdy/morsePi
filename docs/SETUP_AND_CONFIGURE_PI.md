# Setup and Configure a Raspberry Pi for morsePi

This guide starts with a fresh Raspberry Pi OS install and ends with Pappy's Internet Telegraph running on the Pi.

For the current hardware shopping list, see [BILL_OF_MATERIALS.md](BILL_OF_MATERIALS.md).
For a station that will leave Pappy's house, use [GRANDKID_STATION_DEPLOYMENT.md](GRANDKID_STATION_DEPLOYMENT.md) after this fresh setup guide.
For remote backup/status/update operations, use [REMOTE_BACKUP_STATUS_RUNBOOK.md](REMOTE_BACKUP_STATUS_RUNBOOK.md).

The app stores station data in `data/` beside the app by default. Advanced
deployments can override this with `MORSE_DATA_DIR`, but the standard Raspberry
Pi setup should leave it unset.

Target setup:

```text
Device: Raspberry Pi 4
Hostname: PiMorse
User: morse
Project path: /home/morse/morse-station
Web app URL: http://<pi-ip-address>:5000
GitHub repo: https://github.com/luminerdy/morsePi
```

Current test station notes:

```text
Active IP as of 2026-06-15: 10.10.10.141
7-inch Pi touchscreen resolution: 800x480, no scaling
```

## 1. Install Raspberry Pi OS

Use Raspberry Pi Imager.

Recommended OS:

```text
Raspberry Pi OS with desktop, 64-bit
```

In Raspberry Pi Imager, open advanced options and set:

- Hostname: `PiMorse`
- Username: `morse`
- Enable SSH
- Configure Wi-Fi, if needed
- Set locale, keyboard, and timezone

After writing the SD card, boot the Pi and confirm it is reachable on the network.

From another computer:

```bash
ssh morse@<pi-ip-address>
```

## 2. Update the Pi

Run:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Reconnect after reboot:

```bash
ssh morse@<pi-ip-address>
```

## 3. Install System Packages

This project intentionally uses system Python on the Raspberry Pi. That keeps GPIO access simpler for a dedicated hardware station.

Install the required packages:

```bash
sudo apt update
sudo apt install -y \
  python3 \
  python3-pip \
  git \
  alsa-utils \
  matchbox-keyboard \
  python3-flask \
  python3-gpiozero \
  python3-lgpio \
  python3-pytest \
  python3-rpi.gpio
```

The current app uses `aplay` for station playback and `speaker-test` for the key-down tone. Both commands come from `alsa-utils`. The touch System page can launch `matchbox-keyboard` when an adult needs to enter Wi-Fi settings or troubleshoot without a physical keyboard.

Optional package for future MQTT messaging:

```bash
sudo apt install -y python3-paho-mqtt
```

Optional package for cloud backups to S3:

```bash
sudo apt install -y awscli
```

Do not create a Python virtual environment for the current Raspberry Pi station setup. This project originally tried `.venv` and `pip install flask gpiozero`, but the station now uses system Python packages because GPIO libraries are simpler and more reliable that way.

## 4. Clone the Project

Clone the repo into the expected project path:

```bash
cd /home/morse
git clone https://github.com/luminerdy/morsePi.git morse-station
cd /home/morse/morse-station
```

Run the dependency checker after cloning:

```bash
python3 scripts/check_dependencies.py
```

Required items should show `OK`. The AWS CLI and MQTT package may show as optional missing until cloud backup or future messaging is configured for that station.

If the folder already exists, update it instead:

```bash
cd /home/morse/morse-station
git pull
```

## 5. Configure USB Speaker Output

The current station app defaults to:

```text
MORSE_AUDIO_DEVICE=default:CARD=UACDemoV10
```

Using the ALSA card name is preferred over a numeric card index because the card number can change when the SD card moves to another Pi or the USB speaker is plugged into a different port.

To inspect available audio devices:

```bash
aplay -l
```

To test the known USB speaker device:

```bash
speaker-test -D default:CARD=UACDemoV10 -t sine -f 700 -l 1
```

If a fresh Pi assigns a different card/device number, start the app with a different device:

```bash
MORSE_AUDIO_DEVICE=plughw:<card>,<device> python3 app.py
```

## 5A. Configure Morse Learning Timing

The web app defaults to beginner Farnsworth-style timing:

```text
Character speed: 12 WPM
Effective spacing: 6 WPM
Tone: 700 Hz
```

This makes each letter sound more like real Morse while keeping longer pauses between letters and words for beginners. The Home page includes Morse Timing controls. The same timing is used by browser playback and Raspberry Pi speaker playback.

Saved timing changes are stored locally in `data/timing_settings.json` on the Pi. This file is intentionally not committed because it is station-specific.

Student profiles are stored locally in `data/student_profiles.json`. Each student folder also stores a small `profile.json` safety copy so the roster can be rebuilt if the main profile list gets stale. Each student's progress, learning-gate state, and attempt timing logs are stored under `data/students/<student-id>/practice_progress.json`, `data/students/<student-id>/learning_state.json`, and `data/students/<student-id>/practice_attempts.jsonl`. These files are intentionally not committed because they contain station/student practice history.

Older single-student data files in `data/practice_progress.json`, `data/learning_state.json`, and `data/practice_attempts.jsonl` are copied into the default `Pappy` profile the first time the profile-aware app runs.

## 5B. Configure Station Identity

Each deployed station should have its own station id so backups and status reports are easy to identify.

Create the station config:

```bash
cd /home/morse/morse-station
cp config.station.example.json data/station_config.json
```

Edit `data/station_config.json`:

```json
{
  "station_id": "astrid-liara-station",
  "backup_s3_uri": "s3://morsepi-backups-luminerdy",
  "admin_pin": "",
  "allow_student_create": false,
  "students": [
    {
      "id": "astrid",
      "name": "Astrid"
    },
    {
      "id": "liara",
      "name": "Liara"
    }
  ],
  "family_students": [
    {"id": "pappy", "name": "Pappy"},
    {"id": "astrid", "name": "Astrid"},
    {"id": "liara", "name": "Liara"},
    {"id": "campbell", "name": "Campbell"},
    {"id": "olivea", "name": "Olivea"}
  ],
  "guest_profile": {
    "id": "guest",
    "name": "Guest Operator",
    "guest": true,
    "disposable": true
  }
}
```

Set `admin_pin` before a station leaves home to protect adult actions such as adding students, resetting progress, and changing timing or volume settings. Leave it blank only while the station is in local development or testing.

To set or reset the PIN without hand-editing JSON:

```bash
cd /home/morse/morse-station
python3 scripts/set_admin_pin.py
systemctl --user restart morse-station.service
```

The helper prompts for the new PIN without showing it, writes
`data/station_config.json`, and creates a timestamped backup beside the config.
For unattended setup, pass the new numeric PIN as an argument:

```bash
python3 scripts/set_admin_pin.py 1234
systemctl --user restart morse-station.service
```

For local development only, clear the PIN with:

```bash
python3 scripts/set_admin_pin.py --clear
systemctl --user restart morse-station.service
```

Set `allow_student_create` to `false` for deployed touch stations. The touch student screen will show only the configured student buttons and the disposable `Guest Operator` profile, so students do not need a keyboard. Guest is intended for demos, cannot send or receive messages, and should be excluded from future family progress summaries.

`students` is the local sign-in roster. `family_students` is the approved
message recipient directory. Phase 7A can deliver only when both students have
progress on the same station; Phase 7B will synchronize the minimal active-letter
summary needed to safely send between homes.

Use a unique id for each station, such as:

```text
pappy-station
astrid-liara-station
campbell-olivea-station
```

Tracked examples are available at:

```text
config/stations/pappy-test-station.example.json
config/stations/pappy-station.example.json
config/stations/astrid-liara-station.example.json
config/stations/campbell-olivea-station.example.json
```

`data/station_config.json` is intentionally ignored by Git because it is different for each Pi.

## 6. Wire the Hardware

GPIO layout:

| Function | GPIO | Physical Pin | Notes |
|---|---:|---:|---|
| Telegraph key input | GPIO17 | Pin 11 | Key connects GPIO17 to ground |
| Telegraph key ground | GND | Pin 9 | Shared ground |
| Status LED | GPIO27 | Pin 13 | Use resistor in series with LED |
| LED ground | GND | Pin 14 | Shared ground |

Wiring summary:

```text
GPIO17 / Pin 11 -> Telegraph Key -> GND / Pin 9
GPIO27 / Pin 13 -> Resistor -> LED + ; LED - -> GND / Pin 14
```

Use a resistor with the LED, usually `220` to `330` ohms. The active web app uses the USB speaker for sound.

## 7. Test the Hardware

Run each hardware test from the project folder.

Telegraph key:

```bash
cd /home/morse/morse-station
python3 hardware_tests/key_reader.py
```

LED:

```bash
python3 hardware_tests/test_led.py
```

Stop each test with `Ctrl+C` before starting the next one. Only one running script should own the GPIO pins at a time.

## 8. Run the Web App

Start the Flask app:

```bash
cd /home/morse/morse-station
python3 app.py
```

From another computer on the same network, open:

```text
http://<pi-ip-address>:5000
```

Example:

```text
http://10.10.10.141:5000
```

Important: run the app with `debug=False` and `use_reloader=False`. The current `app.py` already does this. The Flask debug reloader can start multiple processes and claim the GPIO pins twice.

## 9. Install Station Branding

Install the morsePi desktop wallpaper so the adult recovery desktop is clearly
part of the station:

```bash
cd /home/morse/morse-station
bash scripts/install_wallpaper.sh
```

Install the simple morsePi boot splash:

```bash
bash scripts/install_boot_splash.sh
```

The boot splash installer replaces the Raspberry Pi OS `pix` Plymouth splash
image and keeps backups at `/usr/share/plymouth/themes/pix/splash.png.morsepi-*`.
It will be visible on the next reboot.

## 10. Back Up Student Data

Student progress is local to the Pi and is not committed to GitHub. Backups should include:

- `data/student_profiles.json`
- `data/timing_settings.json`
- `data/students/<student-id>/practice_progress.json`
- `data/students/<student-id>/learning_state.json`
- `data/students/<student-id>/practice_attempts.jsonl`
- `data/students/<student-id>/bonus_attempts.jsonl`
- `data/students/<student-id>/word_attempts.jsonl`
- `data/students/<student-id>/message_draft.json`
- `data/students/<student-id>/message_events.jsonl`
- `data/students/<student-id>/message_inbox/`
- `data/students/<student-id>/message_outbox/`

Create a manual backup:

```bash
cd /home/morse/morse-station
python3 scripts/backup_data.py --label manual
```

Backups are stored as zip files in:

```text
/home/morse/morse-station/data/backups/
```

The backup script keeps the newest 30 backups by default. To keep a different number:

```bash
python3 scripts/backup_data.py --label manual --keep 60
```

If AWS CLI credentials are configured and `data/station_config.json` has `backup_s3_uri`, upload a backup to S3:

```bash
python3 scripts/backup_data.py --label manual --s3-uri s3://morsepi-backups-luminerdy
```

Dry-run the S3 path without uploading:

```bash
python3 scripts/backup_data.py --label manual --s3-uri s3://morsepi-backups-luminerdy --dry-run-s3
```

Write station status locally:

```bash
python3 scripts/station_status.py
```

Upload station status to S3:

```bash
python3 scripts/station_status.py --s3-uri s3://morsepi-backups-luminerdy
```

Install the optional daily backup timer. The service creates a local/S3 backup,
uploads station status, and uploads a read-only progress snapshot for family
visibility. It also refreshes `data/family_progress/latest.json` from any
station snapshots this Pi is allowed to read:

```bash
mkdir -p /home/morse/.config/systemd/user
install -m 0644 /home/morse/morse-station/systemd/morse-station-backup.service /home/morse/.config/systemd/user/morse-station-backup.service
install -m 0644 /home/morse/morse-station/systemd/morse-station-backup.timer /home/morse/.config/systemd/user/morse-station-backup.timer
systemctl --user daemon-reload
systemctl --user enable --now morse-station-backup.timer
```

Run one backup/status/snapshot cycle immediately:

```bash
systemctl --user start morse-station-backup.service
journalctl --user -u morse-station-backup.service -n 50 --no-pager
```

Check the timer:

```bash
systemctl --user list-timers morse-station-backup.timer
```

### Install the family message sync timer

Leave `message_sync_enabled` set to `false` until the cloud router and the
three-station rehearsal are complete. Install the worker now so enabling it
later requires only the station config change:

```bash
mkdir -p /home/morse/.config/systemd/user
install -m 0644 /home/morse/morse-station/systemd/morse-station-message-sync.service /home/morse/.config/systemd/user/morse-station-message-sync.service
install -m 0644 /home/morse/morse-station/systemd/morse-station-message-sync.timer /home/morse/.config/systemd/user/morse-station-message-sync.timer
systemctl --user daemon-reload
systemctl --user enable --now morse-station-message-sync.timer
systemctl --user list-timers morse-station-message-sync.timer
```

Run one manual check with:

```bash
cd /home/morse/morse-station
python3 -m scripts.message_sync
journalctl --user -u morse-station-message-sync.service -n 50 --no-pager
```

The disabled worker prints `Message sync disabled.` and exits successfully.

Restore into a temporary folder for inspection:

```bash
python3 scripts/backup_data.py --restore data/backups/<backup-file>.zip --restore-root /tmp/morse-restore-check
```

To restore onto a station, stop the app, inspect the extracted files, then copy the restored `data/` contents back into `/home/morse/morse-station/data/`. Do not overwrite live student data without first making a fresh manual backup.

## 10. Update the Station

To pull the latest GitHub changes onto the Pi:

```bash
cd /home/morse/morse-station
git pull
```

If the Flask app is running, stop it with `Ctrl+C` before updating. Start it again after the pull:

```bash
python3 app.py
```

### Optional automatic updates

For deployed stations at different homes, the Pi can periodically check GitHub for updates. The optional updater uses a user systemd timer and is intentionally conservative:

- It preserves local station data in `data/student_profiles.json`, `data/students/`, and `data/timing_settings.json` because those files are ignored by Git.
- It skips updates if tracked files were changed locally on the Pi.
- It only applies fast-forward updates from `origin/release/pi`.
- It compile-checks and runs the test suite before restarting the app.
- It restarts only the `morse-station.service` user service.
- It checks that the local app responds at `http://127.0.0.1:5000/touch` before declaring the update successful.
- It rolls back to the previous commit if tests or the health check fail.

Release flow:

```text
main        development and tested work
release/pi  deployed station update branch
```

Promote a tested release from the laptop:

```bash
git fetch origin
git checkout release/pi
git merge --ff-only main
git push origin release/pi
git checkout main
```

Install the updater script and timer:

```bash
mkdir -p /home/morse/bin /home/morse/.config/systemd/user
install -m 0755 /home/morse/morse-station/systemd/update-morse-station.sh /home/morse/bin/update-morse-station.sh
install -m 0644 /home/morse/morse-station/systemd/morse-station-update.service /home/morse/.config/systemd/user/morse-station-update.service
install -m 0644 /home/morse/morse-station/systemd/morse-station-update.timer /home/morse/.config/systemd/user/morse-station-update.timer
systemctl --user daemon-reload
systemctl --user enable --now morse-station-update.timer
```

Run one update manually:

```bash
systemctl --user start morse-station-update.service
journalctl --user -u morse-station-update.service -n 50 --no-pager
```

From the laptop, trigger all reachable grandkid stations after promoting a
release:

```bash
python scripts/rollout_release.py
```

Preview the SSH commands without changing anything:

```bash
python scripts/rollout_release.py --dry-run
```

Trigger just one station:

```bash
python scripts/rollout_release.py --station astrid-liara
python scripts/rollout_release.py --station campbell-olivea
```

Check the timer:

```bash
systemctl --user list-timers morse-station-update.timer
```

Disable automatic updates:

```bash
systemctl --user disable --now morse-station-update.timer
```

Recommended rollout: keep automatic updates disabled on brand-new stations until the app is tested locally, then enable it once the Pi is physically deployed.

Future remote rollout: once stations are connected to AWS, AWS IoT can trigger `/home/morse/morse-station/scripts/update_station.sh` on demand. Systems Manager could also trigger the same script if we decide the monthly device cost is worth the extra Linux fleet-management features.

The update script creates a pre-update backup, optionally uploads it to S3, fast-forwards from GitHub only when safe, compile-checks and tests the app, restarts the service, verifies health, rolls back on failure, and refreshes station status/progress snapshots.

## 11. Run the App at Boot with systemd

The station should run as a system service so it starts automatically after the Pi boots.

If you do not have sudo access during setup, use the user service instead:

```bash
mkdir -p /home/morse/.config/systemd/user
install -m 0644 /home/morse/morse-station/systemd/morse-station.user.service /home/morse/.config/systemd/user/morse-station.service
systemctl --user daemon-reload
systemctl --user enable morse-station
systemctl --user restart morse-station
systemctl --user status morse-station
```

The user service starts when the `morse` user session starts. On a station Pi with desktop auto-login enabled, that means the app and browser come up together after reboot.

Copy the service file from the repo:

```bash
sudo install -m 0644 /home/morse/morse-station/systemd/morse-station.service /etc/systemd/system/morse-station.service
```

If your USB speaker is not `default:CARD=UACDemoV10`, edit the service and add an environment line under `[Service]`:

```bash
sudo systemctl edit morse-station
```

Example override:

```ini
[Service]
Environment=MORSE_AUDIO_DEVICE=plughw:<card>,<device>
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable morse-station
sudo systemctl restart morse-station
```

Check status:

```bash
systemctl status morse-station
```

View logs:

```bash
journalctl -u morse-station -f
```

Stop it before running hardware test scripts:

```bash
sudo systemctl stop morse-station
```

## 12. Launch the Browser at Desktop Startup

The Pi desktop can also open Chromium directly to the Morse Station web app after login.

Install the morsePi desktop wallpaper:

```bash
cd /home/morse/morse-station
bash scripts/install_wallpaper.sh
```

The helper copies the wallpaper to `/home/morse/Pictures/morsePi/`, writes the
Raspberry Pi desktop wallpaper config for the connected display, and asks
PCManFM to reconfigure if it is running. This matters when an adult exits kiosk
mode to troubleshoot Wi-Fi or updates.

Install the browser helper script:

```bash
mkdir -p /home/morse/bin
install -m 0755 /home/morse/morse-station/systemd/start-morse-browser.sh /home/morse/bin/start-morse-browser.sh
```

On Raspberry Pi OS Bookworm with Labwc, add the helper to the Labwc autostart file:

```bash
mkdir -p /home/morse/.config/labwc
grep -qxF '/home/morse/bin/start-morse-browser.sh &' /home/morse/.config/labwc/autostart 2>/dev/null || \
  printf '\n/home/morse/bin/start-morse-browser.sh &\n' >> /home/morse/.config/labwc/autostart
```

Do not also install the XDG desktop autostart entry on the same Pi, because Raspberry Pi OS may generate a second browser autostart service from it. The helper waits for `http://localhost:5000/touch` to answer before launching Chromium in kiosk mode. On Labwc/Wayland sessions, the helper passes Chromium the Wayland platform flag. If graphical auto-login is disabled, Chromium opens after the `morse` user signs in to the desktop.

The touch menu includes a kid-facing `Power` button. Students can tap it,
confirm `Power Off`, wait for the screen to go dark, and then turn off the
CanaKit USB-C PiSwitch safely.

The touch menu also includes a `System` page for adult recovery. Use it to check hostname, IP address, Wi-Fi connection, Wi-Fi signal, NetworkManager tool availability, on-screen keyboard availability, and update service state without a physical keyboard. The page also has admin-PIN-gated buttons to open the on-screen keyboard, start the app update service, restart Wi-Fi, and exit Chromium kiosk mode so the Raspberry Pi desktop is visible for troubleshooting.

For a non-Labwc desktop environment only, use the fallback desktop autostart entry instead of the Labwc line:

```bash
mkdir -p /home/morse/.config/autostart
install -m 0644 /home/morse/morse-station/systemd/morse-station-browser.desktop /home/morse/.config/autostart/morse-station-browser.desktop
```

## 13. Troubleshooting

### GPIO busy

Another process is using the GPIO pins. Stop the web app or old test scripts.

If using manual app startup, press `Ctrl+C` in the terminal running `app.py`.

If using systemd:

```bash
sudo systemctl stop morse-station
```

You can also check for Python processes:

```bash
ps aux | grep python
```

### Flask is not installed

Install the Debian package:

```bash
sudo apt install -y python3-flask
```

### GPIO Zero cannot access pins

Install the GPIO packages:

```bash
sudo apt install -y python3-gpiozero python3-lgpio python3-rpi.gpio
```

### USB speaker does not play

Make sure `alsa-utils` is installed:

```bash
sudo apt install -y alsa-utils
```

List audio devices:

```bash
aplay -l
```

Test the configured device:

```bash
speaker-test -D default:CARD=UACDemoV10 -t sine -f 700 -l 1
```

### App is not reachable in the browser

Check that the app is running:

```bash
ps aux | grep app.py
```

Check the Pi IP address:

```bash
hostname -I
```

Make sure the app is listening on all interfaces. The current app uses:

```python
app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=False)
```

### Hardware tests work, but web app does not

Make sure no other hardware test script is still running. The web app owns GPIO17 and GPIO27 while it runs.

## 14. Fresh Pi Done Checklist

- Raspberry Pi OS installed
- SSH enabled
- User `morse` created
- System packages installed
- `python3 scripts/check_dependencies.py` shows required items as `OK`
- `python3 -m pytest --version` works
- Repo cloned to `/home/morse/morse-station`
- Telegraph key wired to GPIO17
- LED wired to GPIO27 with resistor
- USB speaker tested with `speaker-test`
- Hardware tests pass
- `python3 app.py` starts successfully
- Browser can open `http://<pi-ip-address>:5000`
