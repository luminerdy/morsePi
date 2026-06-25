# morsePi

Last updated: 2026-06-25

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
- Burn-in progression gates so new letters require Learn repetitions, strength, a short rest, and word practice before the next group opens
- Spacebar keyer for browser testing and keyboard-only practice
- Operator Level with current-set mastery, letters mastered, active practice letters, and Learning Now letters
- Student score card with level, mastery, streak, accuracy, and next goal
- Detailed Progress page with per-letter Morse reinforcement
- Local student profiles with separate progress, learning state, and attempt logs
- Desktop admin reset for student progress with timestamped backup
- Local JSON progress tracking under `data/students/<student>/practice_progress.json`
- JSONL practice attempt logging under `data/students/<student>/practice_attempts.jsonl`
- JSONL word practice attempt logging under `data/students/<student>/word_attempts.jsonl`
- Local data backup script and optional daily systemd user timer
- Optional 7-inch touchscreen flow at `/touch`
- Touch start flow that opens student selection for multi-student stations and Daily Mission for single-student stations
- Touch inactivity timeout that returns idle screens to the touch start flow after 10 minutes
- Touch Daily Mission page for a per-student daily practice goal
- Daily Mission completion reward with station sound, LED flash, and next-action guidance
- Optional Signal Sprint bonus round after Daily completion: 20 random active letters with accuracy and streak scoring
- Known-letter Words practice after `S O`, with Pi speaker/LED playback, full-word keying feedback, visual correct reward, and separate word logging
- Daily Practice Coach with practice-next, strong-signal, and signal-boost recommendations
- Derived student badges on touch Daily and Progress, including daily completion, clean copy, first signals mastered, and new signals ready
- Clear current-set versus Learning Now progress so new letters do not look mastered too early
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

## Regression Tests

Run the regression test bank on the Pi with mock GPIO:

```bash
cd /home/morse/morse-station
GPIOZERO_PIN_FACTORY=mock python3 -m unittest tests.test_backup_data tests.test_learning_gates tests.test_routes
```

These tests use temporary progress files and do not modify student practice data. The current bank covers data backups, learning gates, alphabet progress, stale Learning Now cleanup, Daily Mission summary rules, Practice Coach recommendations, derived badges, rendered touch pages, profile cookie separation, admin reset behavior, practice POST routes, Signal Sprint bonus routes, and the Daily celebration endpoint.

## Repository Layout

```text
app.py                  Current Flask application
morse.py                Morse conversion helpers
templates/              Flask HTML templates
static/                 CSS and browser JavaScript
tests/                  Regression tests for learning gates and progress rules
scripts/                Maintenance scripts, including local data backups
hardware_tests/         Standalone GPIO/audio test scripts
archive/                Earlier prototypes kept for reference
docs/                   Project plan, setup guide, requirements, tutorials
systemd/                Optional Linux service file
```

## Project Plan

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for milestones and next steps.

Current next focus: test the faster-but-controlled unlock gate, Words practice requirements, and 7-inch touch Daily guidance with real student-style sessions.

## License

This project is licensed under the [MIT License](LICENSE).
