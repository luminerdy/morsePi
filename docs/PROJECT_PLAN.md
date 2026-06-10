# Pappy's Internet Telegraph Project Plan

## Vision

Build a Raspberry Pi Morse code learning station where students can see, hear, tap, decode, and eventually send Morse messages. The project should stay hands-on, encouraging, and easy to grow in small tested steps.

Core learning loop:

```text
See Morse -> Hear Morse -> Tap Morse -> Decode Morse -> Send Morse
```

## Current Status

The current app is a working local Morse station MVP.

Completed:

- Raspberry Pi GPIO setup for telegraph key, LED, and passive piezo buzzer
- Text-to-Morse conversion
- Morse-to-text decoding
- Browser Morse playback
- Pi hardware playback using LED and buzzer
- Live telegraph key input in the web app
- Beginner Practice Mode for `E`, `T`, `A`, `N`, `I`, and `M`
- Project pushed to GitHub at `luminerdy/morsePi`
- Fresh Raspberry Pi setup guide added
- Repository structure cleaned up

## Milestones

### MVP 1: Working Pi Morse Station

Status: Complete

Goal: A student can type a message, see Morse, play it in the browser, play it on the Pi station, tap the physical key, and use basic Practice Mode.

Completed work:

- Create Flask app
- Add Morse conversion
- Add browser playback
- Add Pi LED and buzzer playback
- Add physical key input
- Add live key display
- Add basic Practice Mode
- Document hardware baby steps

### MVP 2: Logging and Progress

Status: Next

Goal: Save practice attempts locally so the app can show recent progress and later adapt lessons.

Planned work:

- Create `db.py`
- Create SQLite database `morse_station.db`
- Add default student profile
- Add `practice_attempts` table
- Log every Practice Mode check
- Capture actual Morse and correctness
- Preserve raw timing data for future feedback
- Show recent attempts on Practice page

### MVP 3: Student Profiles

Status: Planned

Goal: Allow multiple students to use the same station and track progress separately.

Planned work:

- Add profile selection page
- Add simple student records
- Track current selected student
- Store known letters, weak letters, playback speed, and input settings

### MVP 4: Morse Login

Status: Planned

Goal: Let students log in by tapping a Morse password.

Planned work:

- Add Morse password setup
- Store salted hash of normalized Morse password
- Add beginner mode that shows the password pattern
- Add challenge mode that hides the pattern
- Add adult/admin password reset

### MVP 5: Better Practice and Adaptive Lessons

Status: Planned

Goal: Make practice smarter and more useful based on saved student performance.

Planned work:

- Add dot/dash timing feedback
- Add letter gap feedback
- Add more beginner letters
- Add word practice
- Add listen-and-choose activity
- Add copy-rhythm activity
- Recommend next practice using rule-based logic

### MVP 6: Messaging

Status: Future

Goal: Let family stations send and receive Morse messages.

Planned work:

- Add local inbox and outbox
- Add listen-before-reveal message flow
- Add station names
- Add secure MQTT messaging later
- Evaluate AWS IoT Core for remote station communication

## Tracking Workflow

Use this repo plan for the big picture.

Use GitHub Issues for specific work items.

Recommended issue labels:

- `feature`
- `bug`
- `hardware`
- `docs`
- `practice`
- `database`
- `student-progress`
- `future`

Recommended GitHub Project columns:

- Backlog
- Ready
- In Progress
- Testing
- Done

## Immediate Next Issues

Create these GitHub issues next:

1. Add SQLite database setup
2. Log Practice Mode attempts
3. Show recent attempts on Practice page
4. Capture raw key timing events
5. Add default student profile
6. Add web app tutorial documentation
7. Move hardware/audio code out of `app.py`

## Progress Log

### 2026-06-07

- Created initial Raspberry Pi Morse station.
- Added telegraph key, LED, and buzzer hardware tests.
- Added Flask web app.
- Added browser and Pi hardware playback.
- Added live physical key input.
- Added beginner Practice Mode.
- Created GitHub repository `luminerdy/morsePi`.
- Added project plan.

### 2026-06-08

- Added fresh Raspberry Pi setup and configuration guide.
- Moved hardware test scripts into `hardware_tests/`.
- Moved earlier app prototypes into `archive/`.
- Moved project requirements and tutorial docs into `docs/`.
- Added `README.md`, shared browser JavaScript, and a reusable systemd service file.

### 2026-06-09

- Cleaned up the web UI to feel more like a production station console.
