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
- Continuous Send practice loop with automatic feedback and advancement
- Read practice mode for identifying letters from visible Morse patterns
- Spacebar keyer for testing and keyboard-based practice
- JSON-backed per-letter, per-mode progress tracking
- Student-facing level/mastery score card on Practice Mode
- Detailed Progress page with per-letter Morse reinforcement
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

Status: In Progress

Goal: Save practice attempts locally so the app can show progress, motivate students, and later adapt lessons.

Completed work:

- Store progress in `data/practice_progress.json`
- Track progress per letter and per practice mode
- Track attempts, correct answers, streak, accuracy, and strength
- Weight next prompts toward weak or new letters
- Add Practice score card with level, mastery, streak, accuracy, tries, and next goal
- Add detailed `/progress` page

Still planned:

- Add student/profile support
- Decide whether/when to migrate JSON progress to SQLite
- Capture raw key timing data for future feedback
- Add session history and recent-attempt summaries

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

Status: In Progress

Goal: Make practice smarter and more useful based on saved student performance.

Completed work:

- Add Send mode: show a letter and have the student key Morse
- Add Learn mode: show letter, show Morse, play sound, and let the student key along
- Add Read mode: show Morse and have the student identify the letter
- Add Listen mode: play Morse and have the student type/select the letter
- Track Learn, Send, Read, and Listen progress separately
- Add overall Operator Level, rank, mastery, and unlocked-letter display
- Recommend next prompts using simple rule-based weighting

Planned work:

- Add dot/dash timing feedback
- Add letter gap feedback
- Add more beginner letters
- Enforce unlocked letters in the active practice set
- Add word practice
- Add Mixed mode that rotates through weak skills
- Add copy-rhythm activity

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

Create or refine these GitHub issues next:

1. Test Learn, Send, Read, and Listen modes with a real student session
2. Tune overall Operator Level thresholds, rank names, and unlock messaging
3. Decide when to enforce unlocked letters in the active practice set
4. Tune Listen/Learn audio speed, replay behavior, and feedback wording
5. Add Mixed mode that selects weak mode+letter combinations
6. Add settings for active letter set and difficulty
7. Capture raw key timing events for dot/dash and spacing feedback
8. Add student/profile support
9. Decide whether JSON progress should migrate to SQLite
10. Add web app tutorial documentation
11. Move hardware/audio code out of `app.py`
12. Test Kindle Fire/Silk browser compatibility for Practice modes, audio playback, and touch layout

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
- Added delayed auto-check feedback for individual-letter Practice Mode.

### 2026-06-10

- Changed Practice Mode into a continuous hands-on loop that advances after correct letters and retries after missed letters.
- Added Spacebar Keyer for testing and keyboard-only practice.
- Added JSON-backed progress tracking in `data/practice_progress.json`.
- Added mode-aware progress for Send and Read skills.
- Added Read mode: show Morse, answer with a letter.
- Replaced detailed Practice sidebar with a student-friendly score card.
- Added `/progress` details page with per-letter stats and Morse code reinforcement.
- Added Home Spacebar Keyer so the browser keyboard can act like a telegraph key outside Practice.
- Added Listen mode: play Morse audio, replay it, and answer by choosing or typing the letter.
- Added mode-aware progress for Listen, including Practice score card and Progress detail support.
- Verified Send, Read, Listen, and Progress routes on the live Pi at `10.10.10.129`.

### Ready for 2026-06-11

- Test the full student flow in Chrome on the laptop: Send, Read, Listen, Progress details, Home keyer.
- Watch whether Listen should autoplay the first prompt or stay click-to-play.
- Watch whether audio timing is too slow, too fast, or just right for beginner letters.
- Decide whether feedback should reveal the answer immediately in Listen misses or offer one replay first.
- Decide the next learning feature: Learn mode, Mixed mode, more letters, or timing feedback.

### 2026-06-11

- Started the Pi app after finding Flask was not running.
- Verified Send, Read, and Listen practice pages were live on the Pi.
- Added Kindle Fire/Silk browser compatibility to the backlog.
- Decided Learn mode should be the next learning feature after the first three practice loops.
- Added Learn mode: show the letter, show the Morse pattern, play the browser tone, and let the student key along.
- Added Learn-specific progress tracking and Progress detail support.
- Verified Learn, Send, Read, Listen, and Learn Progress routes on the live Pi at `10.10.10.129`.
- Added overall Operator Level with rank, mastery, accuracy, attempts, and best streak.
- Added unlocked-letter display and next-unlock messaging to Practice and Progress.
- Added live browser updates for the overall score after practice responses.
- Verified the overall score card and JSON response on the live Pi at `10.10.10.129`.
- Reset Pi practice progress by deleting `/home/morse/morse-station/data/practice_progress.json` so the next test starts fresh.
- Confirmed the live Progress page returned to Operator Level 1, 0% mastery, 0 tries, unlocked `E T`, and next unlock `A N`.

### 2026-06-12

- Configured the Pi app to autostart with a `morse` user systemd service.
- Added a browser startup helper and desktop autostart entry so Chromium opens to `http://localhost:5000/`.
- Updated the fresh Pi setup guide with the service and browser autostart steps.

### 2026-06-14

- Added a browser `Test Sound` button on Home and Practice screens to manually wake or verify browser audio.
- Changed browser Morse playback to reuse a single audio context instead of creating a new context for every prompt.
- Added Home playback stop controls for long phrases: `Stop Here` cancels browser playback and `Stop Station` cancels Pi speaker/LED playback.

### 2026-06-15

- Moved active station testing to the replacement Pi at `10.10.10.141` with a 7-inch Raspberry Pi touchscreen.
- Found the USB speaker moved from numeric ALSA device `plughw:3,0` to card 1 on the new Pi.
- Changed the app default USB speaker device to named ALSA device `plughw:UACDemoV10,0` so it is less sensitive to USB port/card ordering.
- Tested the current UI on the 7-inch Pi touchscreen and confirmed the existing screens are too crowded to fit comfortably.
- Decided to preserve the current desktop/laptop layout while planning a smaller-screen layout with additional pages and smaller text.
- Added a separate 7-inch touchscreen option under `/touch` and `/touch/practice` so the current desktop/laptop UI can remain unchanged while the touchscreen flow is tested.
- Added Morse timing settings using beginner Farnsworth-style defaults: 15 WPM character speed, 7 WPM effective spacing, and 700 Hz tone.
- Updated browser and Pi speaker playback to share the same timing settings.
- User liked the Morse timing addition; next step is hands-on testing tomorrow.
- Confirmed the 7-inch Pi touchscreen resolution is `800x480` at 60 Hz with no scaling.
- Decided the touchscreen option should become a no-scroll experience sized for `800x480`, likely with a menu/dashboard and more focused pages.

### 2026-06-16

- Reworked the optional touch UI into a no-scroll `800x480` menu flow.
- Split touch screens into focused routes: `/touch`, `/touch/progress`, `/touch/key`, `/touch/timing`, `/touch/practice`, and `/touch/practice/run`; `/touch/message` remains available as a hidden utility.
- Kept the desktop/laptop pages unchanged while iterating on touch-specific templates and CSS.
- Verified the touch menu, message, timing, and active practice screens with Chromium screenshots at `800x480` on the Pi.
- Fixed Pi browser startup to open `/touch` in Chromium kiosk mode instead of the desktop Home page.
- Removed the duplicate XDG browser autostart path on the Pi; Labwc autostart is now the single browser launch path.
- Confirmed after reboot there is one Flask app process running from `morse-station.service`.
- Removed Spacebar Keyer from the touch screens so the 7-inch station stays focused on the physical telegraph key; desktop/laptop pages still keep Spacebar Keyer for testing.
- Replaced the student-facing touch Message menu item with touch Progress because typing longer phrases on the 7-inch display is awkward and less central to the learning flow.
- Added a `Touch` navigation link to desktop Home, Practice, and Progress so users can return to the touch menu after tapping `Desktop`.
- Added browser-side touch UI selection for small/coarse-pointer screens, with `?view=desktop` preserving the desktop view for the current browser session.

### Ready Next

- Test the no-scroll touch menu flow directly on the physical 7-inch touchscreen.
- Tune any touch screen labels, button sizes, or spacing after physical testing.
- Decide whether `/touch/message` should stay as a hidden utility or be removed entirely from the touch experience.
- Test automatic touch UI selection on the Pi touchscreen, a laptop browser, and Kindle Fire/Silk when available.
- Test whether the 15/7 WPM Farnsworth-style beginner timing feels easier than the old slow 4.8 WPM character timing.
- Start from a clean progress slate and test Learn, Send, Read, and Listen by hand with the physical key on touch, plus Spacebar Keyer on desktop/laptop.
- Tune Operator Level thresholds, rank names, and unlock messaging after student testing.
- Decide whether and when unlocked letters should control the active practice set.
- Decide whether Learn should count progress the same way as Send or stay more forgiving.
- Tune browser audio speed and replay behavior for Learn and Listen.
- Implement and test touch layout changes on the 7-inch Raspberry Pi touchscreen.
- Test on Kindle Fire/Silk when a device is available.
- Choose next build: Mixed mode, more letters, or timing feedback.
