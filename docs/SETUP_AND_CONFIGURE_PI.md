# Setup and Configure a Raspberry Pi for morsePi

This guide starts with a fresh Raspberry Pi OS install and ends with Pappy's Internet Telegraph running on the Pi.

Target setup:

```text
Device: Raspberry Pi 4
Hostname: PiMorse
User: morse
Project path: /home/morse/morse-station
Web app URL: http://<pi-ip-address>:5000
GitHub repo: https://github.com/luminerdy/morsePi
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
  python3-flask \
  python3-gpiozero \
  python3-lgpio \
  python3-rpi.gpio
```

The current app uses `aplay` for station playback and `speaker-test` for the key-down tone. Both commands come from `alsa-utils`.

Optional package for future MQTT messaging:

```bash
sudo apt install -y python3-paho-mqtt
```

Do not create a Python virtual environment for the current Raspberry Pi station setup. This project originally tried `.venv` and `pip install flask gpiozero`, but the station now uses system Python packages because GPIO libraries are simpler and more reliable that way.

## 4. Clone the Project

Clone the repo into the expected project path:

```bash
cd /home/morse
git clone https://github.com/luminerdy/morsePi.git morse-station
cd /home/morse/morse-station
```

If the folder already exists, update it instead:

```bash
cd /home/morse/morse-station
git pull
```

## 5. Configure USB Speaker Output

The current station app defaults to:

```text
MORSE_AUDIO_DEVICE=plughw:3,0
```

To inspect available audio devices:

```bash
aplay -l
```

To test the known USB speaker device:

```bash
speaker-test -D plughw:3,0 -t sine -f 700 -l 1
```

If a fresh Pi assigns a different card/device number, start the app with a different device:

```bash
MORSE_AUDIO_DEVICE=plughw:<card>,<device> python3 app.py
```

## 6. Wire the Hardware

GPIO layout:

| Function | GPIO | Physical Pin | Notes |
|---|---:|---:|---|
| Telegraph key input | GPIO17 | Pin 11 | Key connects GPIO17 to ground |
| Telegraph key ground | GND | Pin 9 | Shared ground |
| Status LED | GPIO27 | Pin 13 | Use resistor in series with LED |
| LED ground | GND | Pin 14 | Shared ground |
| Passive piezo buzzer | GPIO18 | Pin 12 | Optional hardware test output |
| Buzzer ground | GND | Pin 20 | Shared ground |

Wiring summary:

```text
GPIO17 / Pin 11 -> Telegraph Key -> GND / Pin 9
GPIO27 / Pin 13 -> Resistor -> LED + ; LED - -> GND / Pin 14
GPIO18 / Pin 12 -> Passive Piezo + ; Piezo - -> GND / Pin 20
```

Use a resistor with the LED, usually `220` to `330` ohms. The active web app currently uses the USB speaker for sound; the passive piezo buzzer is still useful for standalone hardware tests.

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

Buzzer:

```bash
python3 hardware_tests/test_buzzer.py
```

Key, LED, and buzzer together:

```bash
python3 hardware_tests/key_reader_led_buzzer.py
```

Typed message playback:

```bash
python3 hardware_tests/morse_output.py
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
http://10.10.10.129:5000
```

Important: run the app with `debug=False` and `use_reloader=False`. The current `app.py` already does this. The Flask debug reloader can start multiple processes and claim the GPIO pins twice.

## 9. Update the Station

To pull the latest GitHub changes onto the Pi:

```bash
cd /home/morse/morse-station
git pull
```

If the Flask app is running, stop it with `Ctrl+C` before updating. Start it again after the pull:

```bash
python3 app.py
```

## 10. Optional: Run at Boot with systemd

The current station can be started manually with `python3 app.py`. Later, it can be configured to start automatically.

Copy the service file from the repo:

```bash
sudo cp /home/morse/morse-station/systemd/morse-station.service /etc/systemd/system/morse-station.service
```

If your USB speaker is not `plughw:3,0`, edit the service and add an environment line under `[Service]`:

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
sudo systemctl start morse-station
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

## 11. Troubleshooting

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
speaker-test -D plughw:3,0 -t sine -f 700 -l 1
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
app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
```

### Hardware tests work, but web app does not

Make sure no other hardware test script is still running. The web app owns GPIO17, GPIO27, and GPIO18 while it runs.

## 12. Fresh Pi Done Checklist

- Raspberry Pi OS installed
- SSH enabled
- User `morse` created
- System packages installed
- Repo cloned to `/home/morse/morse-station`
- Telegraph key wired to GPIO17
- LED wired to GPIO27 with resistor
- USB speaker tested with `speaker-test`
- Optional passive piezo buzzer wired to GPIO18
- Hardware tests pass
- `python3 app.py` starts successfully
- Browser can open `http://<pi-ip-address>:5000`
