# morsePi

Last updated: 2026-06-17

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
- Learn-first letter unlocking so new letters are introduced in Learn before joining Send, Read, and Listen
- Spacebar keyer for browser testing and keyboard-only practice
- Overall Operator Level with rank, mastery, and unlocked letters
- Student score card with level, mastery, streak, accuracy, and next goal
- Detailed Progress page with per-letter Morse reinforcement
- Local JSON progress tracking in `data/practice_progress.json`
- JSONL practice attempt logging in `data/practice_attempts.jsonl`
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

Current next focus: test Learn, Send, Read, and Listen with a student session, then refine feedback, timing, and device compatibility.
