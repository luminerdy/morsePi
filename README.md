# morsePi

Last updated: 2026-06-20

Pappy's Internet Telegraph is a Raspberry Pi Morse code learning station. It lets students type messages, see Morse code, hear Morse code, tap a physical telegraph key, and practice beginner letters with immediate feedback.

## Current Features

- Flask web app for the Morse station
- Text-to-Morse conversion
- Morse-to-text decoding
- Browser audio playback
- Raspberry Pi station playback with LED and USB speaker
- Physical telegraph key input on GPIO17
- Live tapped Morse display in the browser
- Beginner Send practice starting with `E`, `T`, `A`, `N`, `I`, and `M`
- Learn practice for guided letter, Morse, sound, and key-along reinforcement
- Read practice for identifying letters from Morse patterns
- Listen practice for identifying letters from browser-played Morse audio
- Echo practice for hearing Morse and keying it back
- Learn-first letter unlocking so new letters are introduced in Learn before joining Send, Read, Listen, and Echo
- Burn-in progression gates so new letters require Learn repetitions, strength, and a next-day return before joining the full practice set
- Spacebar keyer for browser testing and keyboard-only practice
- Overall Operator Level with rank, mastery, active practice letters, and Learning Now letters
- Student score card with level, mastery, streak, accuracy, and next goal
- Detailed Progress page with per-letter Morse reinforcement
- Local student profiles with separate progress, learning state, and attempt logs
- Local JSON progress tracking under `data/students/<student>/practice_progress.json`
- JSONL practice attempt logging under `data/students/<student>/practice_attempts.jsonl`
- Optional 7-inch touchscreen flow at `/touch`
- Beginner Morse timing controls using Farnsworth-style character/effective WPM settings

## Hardware

Current target hardware:

- Raspberry Pi 4
- TGKY01 telegraph key, or similar switch/key
- LED with resistor
- USB speaker
- Optional passive piezo buzzer for hardware tests

GPIO layout:

| Function | GPIO | Physical Pin |
|---|---:|---:|
| Telegraph key input | GPIO17 | Pin 11 |
| Status LED | GPIO27 | Pin 13 |
| Passive piezo buzzer test | GPIO18 | Pin 12 |

## Quick Start on the Pi

```bash
cd /home/morse/morse-station
python3 app.py
```

Then open:

```text
http://<pi-ip-address>:5000
```

For a fresh Raspberry Pi setup, follow [docs/SETUP_AND_CONFIGURE_PI.md](docs/SETUP_AND_CONFIGURE_PI.md).
For current hardware parts, see [docs/BILL_OF_MATERIALS.md](docs/BILL_OF_MATERIALS.md).

## Repository Layout

```text
app.py                  Current Flask application
morse.py                Morse conversion helpers
templates/              Flask HTML templates
static/                 CSS and browser JavaScript
hardware_tests/         Standalone GPIO/audio test scripts
archive/                Earlier prototypes kept for reference
docs/                   Project plan, setup guide, requirements, tutorials
systemd/                Optional Linux service file
```

## Project Plan

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for milestones and next steps.

Current next focus: test the reset progress flow, burn-in unlock gate, Listen/Learn audio with LED reinforcement, and 7-inch touch flow in a fresh student-style practice session.

## License

This project is licensed under the [MIT License](LICENSE).
