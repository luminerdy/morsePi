# Grandkid Station Deployment Checklist

Use this checklist before a morsePi station leaves Pappy's house.

Primary references:

- Fresh Pi setup: [SETUP_AND_CONFIGURE_PI.md](SETUP_AND_CONFIGURE_PI.md)
- Remote backup/update notes: [REMOTE_DEPLOYMENT_AWS.md](REMOTE_DEPLOYMENT_AWS.md)
- Hardware list: [BILL_OF_MATERIALS.md](BILL_OF_MATERIALS.md)
- Kid handout: [KIDS_QUICK_START_HANDOUT.pdf](KIDS_QUICK_START_HANDOUT.pdf)

## Station Plan

Fill this out before configuring the Pi.

| Field | Value |
|---|---|
| Student/home |  |
| Station id |  |
| Pi hostname |  |
| Pi username | `morse` |
| Project path | `/home/morse/morse-station` |
| Wi-Fi network |  |
| Local test IP |  |
| Notes |  |

Recommended first station ids:

| Station | Config example |
|---|---|
| Pappy's house | `config/stations/pappy-station.example.json` |
| Astrid and Liara's house | `config/stations/astrid-liara-station.example.json` |
| Campbell and Olivea's house | `config/stations/campbell-olivea-station.example.json` |
| Active test station | `config/stations/pappy-test-station.example.json` |

## 1. Fresh Pi Build

- Install Raspberry Pi OS with desktop, 64-bit.
- Set hostname, user `morse`, SSH, locale, timezone, and Wi-Fi.
- Boot the Pi and confirm SSH works.
- Run OS updates.
- Install required packages from the setup guide.
- Clone `https://github.com/luminerdy/morsePi` to `/home/morse/morse-station`.
- Reboot once after updates and package install.

Validation commands:

```bash
ssh morse@<pi-ip-address>
cd /home/morse/morse-station
git status --short
```

Expected result: clean Git checkout.

## 2. Station Identity

Copy the right example config to the station-local data folder:

```bash
cd /home/morse/morse-station
mkdir -p data
cp config/stations/astrid-liara-station.example.json data/station_config.json
```

For Campbell and Olivea's house, use:

```bash
cp config/stations/campbell-olivea-station.example.json data/station_config.json
```

Open the file and confirm:

```bash
cat data/station_config.json
```

Expected:

- `station_id` is unique.
- `backup_s3_uri` is set if cloud backup/status will be used.
- `admin_pin` is set before the station leaves home if adult controls should be protected.

`data/station_config.json` is ignored by Git because it is station-specific.

## 3. Hardware Assembly

- Attach the Raspberry Pi 4 to the back of the 7-inch touchscreen.
- Connect the DSI ribbon cable without sharp bends.
- Connect the USB mini speaker.
- Wire the telegraph key to GPIO17 / Pin 11 and GND / Pin 9.
- Wire the LED to GPIO27 / Pin 13 through a resistor, then to GND / Pin 14.
- Confirm the power cable and USB speaker cable have strain relief.

Hardware tests:

```bash
cd /home/morse/morse-station
python3 hardware_tests/key_reader.py
python3 hardware_tests/test_led.py
aplay -l
speaker-test -D default:CARD=UACDemoV10 -t sine -f 700 -l 1
```

Stop each GPIO test with `Ctrl+C` before starting another test.

## 4. App Boot And Touchscreen

Install the user service and browser autostart from the setup guide.

Then reboot:

```bash
sudo reboot
```

After reboot, confirm:

- The Flask app starts automatically.
- The touchscreen opens `/touch`.
- The screen shows student selection if more than one profile exists.
- The screen goes to Daily if only one profile exists.
- Touch buttons are large enough on the 800x480 display.

Validation commands:

```bash
systemctl --user status morse-station
curl -I http://localhost:5000/touch
```

Expected result: service is active and `/touch` responds.

## 5. Student Profiles

- Create the student profile.
- Keep `Pappy` only if adult testing is useful on that station.
- Select the student and confirm Daily opens.
- Do one quick Learn attempt and one Send attempt.
- Confirm progress is saved after switching away and back.

Important data paths:

```text
data/student_profiles.json
data/students/<student-id>/practice_progress.json
data/students/<student-id>/learning_state.json
data/students/<student-id>/practice_attempts.jsonl
data/students/<student-id>/word_attempts.jsonl
data/students/<student-id>/bonus_attempts.jsonl
```

## 6. Local Backup And Status

Create a local backup:

```bash
cd /home/morse/morse-station
python3 scripts/backup_data.py --label pre-deploy
```

Write local status:

```bash
python3 scripts/station_status.py
```

Expected:

- Backup zip appears in `data/backups/`.
- `data/station_status.json` is created.
- Backup filename includes the station id.
- Status JSON includes the station id, hostname, Git commit, latest backup, and service state.

Note: the active lab Pi may show blank Git branch/commit if it was updated by file copy instead of a Git clone. Grandkid deployment stations should be cloned from GitHub so status can report the branch and commit.

## 7. Cloud Backup And Status

If AWS CLI credentials are installed, dry-run first:

```bash
python3 scripts/backup_data.py --label pre-deploy --dry-run-s3
python3 scripts/station_status.py --dry-run-s3
```

Then upload for real:

```bash
python3 scripts/backup_data.py --label pre-deploy
python3 scripts/station_status.py
```

Expected S3 paths:

```text
s3://morsepi-backups/stations/<station-id>/backups/<timestamp>-<station-id>-pre-deploy.zip
s3://morsepi-backups/stations/<station-id>/status/station_status.json
```

## 8. Update Path

Run the conservative update wrapper once before deployment:

```bash
cd /home/morse/morse-station
scripts/update_station.sh
```

Expected:

- A pre-update backup is created.
- Git fast-forwards only if GitHub has newer commits.
- Python compile check passes.
- `morse-station.service` restarts.
- Station status is written.

Recommendation for first deployed units:

- Keep automatic update timer disabled until the station has been tested in the new home.
- Use manual update checks first.
- Add AWS IoT command triggers later when cloud backup/status is proven.

## 9. Kid Readiness

- Print [KIDS_QUICK_START_HANDOUT.pdf](KIDS_QUICK_START_HANDOUT.pdf) two-sided.
- Put the handout with the station.
- Confirm the student can:
  - choose their name
  - open Daily
  - press Play Again
  - use Clear
  - get back to Daily
  - stop practicing without needing a keyboard

## 10. Final Leave-The-House Checklist

- Pi boots to the touch app.
- Only one app instance is running.
- USB speaker plays system prompts and keyer feedback.
- LED flashes for system playback and keying.
- Telegraph key input works.
- Touchscreen fits without awkward scrolling on the main student flow.
- Student profile is created.
- Local backup works.
- Cloud backup/status works, or is intentionally deferred.
- Update wrapper has been tested.
- Printed handout is included.
- Power supply, speaker, key, and case/mount are packed.
- Wi-Fi plan for the destination home is known.
