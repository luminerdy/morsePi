# morsePi

Last updated: 2026-08-23

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
- Local family Morse messages with touch/keyer composition, review, speaker/LED playback, inbox, and guided letter-by-letter decoding
- Message effort logging plus First Message Sent and Secret Message Decoded badges
- Phase 7B cloud-message contract, station S3 sync worker, deployed Lambda router, and idempotent cross-station receipts (Pappy and Astrid/Liara enabled for testing)
- Raw key timing events and timing summaries for practice and Words attempts, preserving dot/dash/gap rhythm history for future coaching
- Adult/admin Rhythm Trends page for reviewing timing consistency and spacing trends over time
- Local data backup script and optional daily systemd user timer
- Station identity, status reporting, S3 backup upload support, and remote-update foundation scripts
- Optional 7-inch touchscreen flow at `/touch`
- Touch start flow that opens student selection for multi-student stations and Daily Mission for single-student stations
- Touch inactivity timeout that returns idle screens to the touch start flow after 10 minutes
- Silent idle Morse recall screensaver after 3 minutes: Morse-only for 10 seconds, then a 5-second answer reveal, with wake-only touchscreen and physical-keyer input
- Touch System page for adult Wi-Fi/IP status checks, on-screen keyboard launch, app update, Wi-Fi restart, and PIN-gated kiosk exit
- Touch Daily Mission page for a per-student daily practice goal
- Practice-time effort tracking on Daily and Progress so students see that time spent learning matters
- Daily Mission completion reward with station sound, LED flash, and next-action guidance
- Optional Signal Sprint bonus round after Daily completion: 20 random active letters with accuracy and streak scoring
- Known-letter Words practice after `S O`, with Pi speaker/LED playback, full-word keying feedback, visual correct reward, and separate word logging
- Daily Practice Coach with practice-next, strong-signal, and signal-boost recommendations
- Derived student badges on touch Daily and Progress, including daily completion, clean copy, first signals mastered, and new signals ready
- Grit-focused motivation with Focused Practice and Try Again Champ badges plus short coach messages connecting effort to improvement
- Clear current-set versus Learning Now progress so new letters do not look mastered too early
- Beginner Morse timing controls using Farnsworth-style character/effective WPM settings
- Centered geometric Morse dots and dashes across learning, Words, Messages, live keying, Progress, and the printable handout
- Station branding for the recovery desktop and simple Raspberry Pi boot splash
- Printable two-sided kid quick-start handout and student instructions under `docs/`
- Grandkid station deployment checklist, remote backup/status runbook, and 3D printed case measurement worksheet under `docs/`

## Hardware

Current target hardware:

- Raspberry Pi 4
- TGKY01 telegraph key, or similar switch/key
- LED with resistor
- USB speaker

GPIO layout:

| Function | GPIO | Physical Pin |
|---|---:|---:|
| Telegraph key input | GPIO17 | Pin 11 |
| Status LED | GPIO27 | Pin 13 |

## Key Docs

- [Rebuild specs](specs/README.md)
- [Project and AWS architecture](docs/ARCHITECTURE.md)
- [Fresh Pi setup](docs/SETUP_AND_CONFIGURE_PI.md)
- [Grandkid station deployment checklist](docs/GRANDKID_STATION_DEPLOYMENT.md)
- [Home Wi-Fi setup checklist](docs/HOME_WIFI_SETUP_CHECKLIST.md)
- [Privacy and family data](docs/PRIVACY_AND_FAMILY_DATA.md)
- [Remote backup, status, and update runbook](docs/REMOTE_BACKUP_STATUS_RUNBOOK.md)
- [AWS setup reference](docs/AWS_SETUP_REFERENCE.md)
- [AWS backup and sync design](docs/AWS_BACKUP_SYNC_DESIGN.md)
- [Bill of materials](docs/BILL_OF_MATERIALS.md)
- [7-inch case measurement worksheet](docs/CASE_MEASUREMENT_WORKSHEET.md)
- [Kids station instructions](docs/KIDS_STATION_INSTRUCTIONS.md)
- [Family Morse messaging](docs/MESSAGING.md)
- [Cloud messaging design](docs/CLOUD_MESSAGING_DESIGN.md)
- [Security and family data](SECURITY.md)
- [Pappy's Operators handout](docs/KIDS_QUICK_START_HANDOUT.pdf)

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
For remote grandkid-station planning, see [docs/REMOTE_DEPLOYMENT_AWS.md](docs/REMOTE_DEPLOYMENT_AWS.md).
For the current AWS backup/sync design, see [docs/AWS_BACKUP_SYNC_DESIGN.md](docs/AWS_BACKUP_SYNC_DESIGN.md).
For credential-free AWS setup steps, see [docs/AWS_SETUP_REFERENCE.md](docs/AWS_SETUP_REFERENCE.md).
For student-facing rules and expectations, see [docs/KIDS_STATION_INSTRUCTIONS.md](docs/KIDS_STATION_INSTRUCTIONS.md).

## Regression Tests

Run the regression test bank on the Pi with mock GPIO:

```bash
cd /home/morse/morse-station
GPIOZERO_PIN_FACTORY=mock python3 -m unittest discover -s tests
```

These tests use temporary progress files and do not modify student practice data. The current bank covers data backups, station status reporting, timing summaries, learning gates, alphabet progress, stale Learning Now cleanup, Daily Mission summary rules, Practice Coach recommendations, derived badges, rendered touch pages, profile cookie separation, admin reset behavior, practice POST routes, Signal Sprint bonus routes, Daily celebration, local messaging, duplicate-safe three-station cloud delivery contracts, family progress snapshots, admin PIN tooling, rollout/update helpers, rhythm coaching, and student-attempt sync.

## Repository Layout

```text
app.py                  Current Flask application
morse.py                Morse conversion helpers
morse_display.py        Shared centered-dot/dash visual renderer
message_store.py        Local message validation, drafts, inbox/outbox, and events
message_cloud.py        Cloud message, summary, receipt, and validation contracts
message_sync.py         Station-side S3 synchronization worker
cloud/                  AWS message router, family directory, and IAM templates
templates/              Flask HTML templates
static/                 CSS and browser JavaScript
tests/                  Regression tests for learning gates and progress rules
scripts/                Maintenance scripts, including local data backups
specs/                  Rebuild specifications and requirement IDs
config.station.example.json  Example per-station deployment config
hardware_tests/         Standalone GPIO/audio test scripts
archive/                Earlier prototypes kept for reference
docs/                   Project plan, setup guide, requirements, tutorials
systemd/                Optional Linux service file
```

## Project Plan

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for milestones and next steps.

Current next focus: verify Campbell/Olivea catches up after reconnecting, let
students unlock the kid-facing Messages UI naturally through `S` and `O`, and
add a low-cost AWS IoT command that can request an immediate remote update.
Cross-station UUID progress merge and live S3 message/decoded-receipt delivery
have passed between Pappy and Astrid/Liara.

## License

This project is licensed under the [MIT License](LICENSE).
