# Pappy's Internet Telegraph Project Plan

## Vision

Build a Raspberry Pi Morse code learning station where students can see, hear, tap, decode, and eventually send Morse messages. The project should stay hands-on, encouraging, and easy to grow in small tested steps.

Learning-method research is captured in [Morse Learning Best Practices](MORSE_LEARNING_BEST_PRACTICES.md).

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
- Beginner Practice Mode starting with `E`, `T`, `A`, `N`, `I`, and `M`
- Continuous Send practice loop with automatic feedback and advancement
- Learn practice mode for guided letter, Morse, sound, and key-along reinforcement
- Read practice mode for identifying letters from visible Morse patterns
- Listen practice mode for identifying letters from browser-played Morse audio
- Echo practice mode for hearing Morse and keying it back
- Spacebar keyer for testing and keyboard-based practice
- JSON-backed per-letter, per-mode progress tracking
- JSONL attempt logging with raw key timing summaries
- Student-facing level/mastery score card on Practice Mode
- Detailed Progress page with per-letter Morse reinforcement
- Learn-first letter unlocking through A-Z and numbers
- Optional 7-inch touchscreen flow under `/touch`
- Farnsworth-style beginner timing controls
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
- Capture raw key timing data in `data/practice_attempts.jsonl`

Still planned:

- Add student/profile support
- Decide whether/when to migrate JSON progress to SQLite
- Add session history and recent-attempt summaries

### MVP 3: Student Profiles

Status: Started

Goal: Allow multiple students to use the same station and track progress separately.

Planned work:

- Add profile selection page - complete for local touch and desktop
- Add simple student records - complete with local JSON profile list
- Track current selected student - complete with local browser cookie
- Store known letters, weak letters, playback speed, and input settings
- Add adult/admin profile safety tools
- Add per-student export, backup, reset, archive, and restore
- Add Daily Mission practice loop with per-day progress

Profile admin design notes:

- Keep the touch screen simple: choose student, add student, return to practice.
- Put reset/export/archive tools on a desktop/admin page first.
- Create a timestamped backup before any progress reset.
- Prefer archive over delete so a grandkid's progress is not lost by accident.
- Keep timing settings station-wide for now because the hardware station is shared.
- Do not implement Morse password login until profile switching and profile safety are proven.

### MVP 3.5: Daily Mission

Status: Started and deployed; early student testing is positive.

Goal: Give each student a daily practice loop that reviews all learned letters so far and makes progress visible by day.

First version:

- Add a touch Daily Mission page.
- Count today's attempts from the active student's `practice_attempts.jsonl`.
- Use a 20-signal daily goal.
- Show today's attempts, accuracy, remaining signals, active letters, Learning Now letters, and letters practiced today.
- Link into the existing Learn, Send, Read, Listen, and Echo practice modes instead of creating a second practice engine.

Next refinements:

- Store earned daily badges after the first reward behavior is tested.
- Add a desktop/admin daily history view.

### MVP 3.6: Words And Rewards

Status: Planned

Goal: Move students from isolated letters toward practical Morse communication while preserving motivating mastery loops.

Planned work:

- Add Word Copy practice using only active/learned letters.
- Start with 2-3 letter words, then grow toward short messages.
- Favor touch word choices and telegraph-key input before typed answers.
- Add Signal Set Complete celebration when active letters reach 100%.
- Add New Mission Unlocked feedback when new letters enter Learning Now.
- Add Daily Mission completion celebration with short sound and LED flash.
- Track word progress separately from letter mastery.
- Consider a future game wrapper, such as Signal Quest or Message Rescue, after word practice is stable.

Design notes:

- Perfection-driven students should see clean mastery goals and badges.
- Practical-progress students should quickly see real words and message-like tasks.
- Avoid leaderboards for now; keep progress personal and encouraging.
- Treat 100% as a transition to the next mission, not the end of the app.

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
- Track Learn, Send, Read, Listen, and Echo progress separately
- Add overall Operator Level, rank, mastery, and unlocked-letter display
- Recommend next prompts using simple rule-based weighting
- Add Learn-first unlock gating before new letters enter Send, Read, Listen, and Echo
- Add the full planned unlock ladder through A-Z and numbers

Planned work:

- Add dot/dash timing feedback
- Add letter gap feedback
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
- Evaluate AWS Systems Manager for remote station operations, including triggering app updates after a station is deployed at a grandkid's house

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
3. Test whether Learn-first gating feels fair when `S O` unlock
4. Tune Listen/Learn audio speed, replay behavior, and feedback wording
5. Add first timing feedback from the logged key events
6. Add Mixed mode that selects weak mode+letter combinations
7. Add settings for active letter set and difficulty
8. Add student/profile support
9. Decide whether JSON progress should migrate to SQLite
10. Add web app tutorial documentation
11. Move hardware/audio code out of `app.py`
12. Test Kindle Fire/Silk browser compatibility for Practice modes, audio playback, and touch layout

## Progress Log

### Daily Wrap-Up Checklist

When asked to do the daily wrap-up, update:

- GitHub sync status
- Memory/progress log
- Accomplishments
- Decisions
- To-do list and ready-next items
- Local Pi state changes, such as progress resets or backups

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
- Added Morse timing settings using beginner Farnsworth-style defaults, now tuned to 12 WPM character speed, 6 WPM effective spacing, and 700 Hz tone after hands-on Listen testing.
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
- Added standalone Morse learning best-practices research notes covering Farnsworth timing, Koch-style progression, practice modes, feedback, progress, and timing feedback goals.
- Tuned beginner timing and key decoding after testing showed Listen prompts were too fast and a correctly imitated `M` could decode as `I`; dash detection now follows the configured Morse timing instead of a fixed 400 ms threshold.
- Added JSONL practice attempt logging with expected/actual Morse, selected answers, correctness, timing settings, and raw key timing summaries for future coaching and adaptive training.
- Added a first adaptive Listen rule: early, overall-struggling, or letter-specific struggling Listen practice plays one step slower than the station default, then returns to normal timing after accuracy improves.
- Enforced letter unlocking in practice: `E T A N I M` are the starter set, and later groups unlock after 100% current-set mastery across all five modes.
- Added Learn-first unlock gating: a newly unlocked group appears in Learn only, blocks later unlocks, and joins Send/Read/Listen after each new letter has at least 3 correct Learn attempts and 60% Learn strength.

### 2026-06-17

- Confirmed the connected GitHub app has admin, push, pull, maintain, and triage access to `luminerdy/morsePi`.
- Confirmed the local repository is clean and points to `https://github.com/luminerdy/morsePi.git`.
- Updated the main README date and current feature summary to include Learn-first unlock gating, attempt logging, touchscreen flow, and timing controls.
- Reviewed repo docs after the Learn-first unlock work and aligned the README, project plan, requirements/status, and learning best-practices notes with the current Active Practice/Learning Now model.
- Made the older `/practice/check` fallback route mode-aware so it records against the current mode and respects Learn-first practice sets if used.
- Confirmed hands-on testing reached the next active letter set; `S` is strong across modes, while `O` needs more Learn/Send/Listen reinforcement.
- Added Pi/browser sound reset behavior behind the existing Sound/Test Sound buttons: it clears stale key-tone and station playback processes, closes the browser audio context, then plays a fresh browser test beep.
- End-of-day decisions: keep the Learn-first unlock model, keep the active set progression moving after `S O`, use the Sound/Test Sound button as the audio recovery control, and use recent `O` timing misses as the first real timing-feedback candidate.
- End-of-day GitHub housekeeping: added MIT licensing to `morsePi` and confirmed the other accessible repos (`PathfinderV2`, `RCubed`, and `IoT`) now have MIT licenses too.
- Added an optional Raspberry Pi auto-update plan for deployed grandkid stations: a user systemd timer can periodically fast-forward from GitHub, preserve local practice/timing data, compile-check the app, and restart the station service.
- Captured AWS Systems Manager as the preferred future way to trigger an update on demand once remote stations are connected to AWS; the local updater script can be the command SSM runs.
- Tuned the Listen/Learn audio handoff after testing showed browser Play could temporarily hold the USB speaker before physical keyer feedback; prompt playback now releases the browser audio context and the Pi key tone retries once without blocking key timing.
- Updated Listen practice to auto-play prompts, relabeled replay to `Play Again`, and added Pi LED flashing with Listen/Learn prompt playback to reinforce the visible Morse rhythm.
- Updated Learn practice to also auto-play the code and flash the LED when the screen opens, with `Play Again` as the replay control.
- Removed the keyer panel from Listen practice so Listen stays focused on hearing the code and identifying the letter; a future Echo/Copy mode can handle hear-and-key-back practice separately.
- Tightened Listen/Learn LED synchronization by flashing with the same practice timing as browser audio and scheduling the LED start just after the browser's request is accepted.
- Slowed letter progression for better memory burn-in: new Learning Now groups now require 10 correct Learn tries per letter, 70% Learn strength, and at least two practice days before joining Send/Read/Listen; only one new group can open per calendar day.
- Added Echo/Copy as a separate practice mode: the station plays a hidden audio prompt, the student keys it back, and Echo gets its own progress tracking.
- Improved post-prompt keyer sound recovery by retrying the Pi USB speaker tone briefly while the physical key is still held, and kept Echo audio-first while revealing the letter/code after a miss.
- Started testing the USB speaker through ALSA `default:CARD=UACDemoV10` instead of direct `plughw` so browser prompt audio and physical keyer tone can share the same speaker more gracefully.
- Moved Listen/Learn/Echo prompt playback from browser audio to Pi station audio so the example sound, LED flash, and physical keyer tone all use the same backend audio path.
- Reset the active Pi's student progress for tomorrow by backing up local progress data to `/home/morse/morse-station/data/backups/20260617-221425/` and clearing `practice_progress.json`, `practice_attempts.jsonl`, and `learning_state.json`.
- Close-of-day GitHub status: code, documentation, Pi deployment, and progress-reset work are pushed to `main`.
- Close-of-day decision: call this recurring end-of-session work the `daily wrap-up`.

### 2026-06-18

- Added Echo/Copy mode to support hear-and-key-back practice as a separate skill from Listen recognition.
- Tested and improved USB speaker handoff by moving Learn, Listen, and Echo prompts to the Pi station audio path instead of browser audio.
- Confirmed prompt audio can be softer than physical keyer feedback while still using the same USB speaker.
- Kept Listen practice recognition-only by removing keyer input from the Listen screen.
- Added Pi station prompt playback for Learn and Echo so the LED flashes with the sound during examples.
- Added the project bill of materials in `docs/BILL_OF_MATERIALS.md`.
- Updated the bill of materials with the telegraph key, 32 GB microSD card, and jumper wires for the LED.
- Decisions: keep Echo audio-first, reveal the code only after a miss, keep station prompt playback on the backend audio path, and continue using the 7-inch touch experience as the main station flow.
- Close-of-day GitHub status: BOM, Echo, station prompt audio, and documentation changes are committed and pushed to `main`.

### 2026-06-20

- Added first-pass local student profiles with a default `Pappy` profile.
- Added desktop `/students` and touch `/touch/students` profile selection screens.
- Profile selection uses a local browser cookie and does not require passwords yet.
- Moved student-owned data paths to `data/students/<student-id>/practice_progress.json`, `learning_state.json`, and `practice_attempts.jsonl`.
- Kept station timing in `data/timing_settings.json` as shared station configuration.
- Preserved existing single-student progress by copying legacy data files into the default `Pappy` profile on first run.
- Added current student labels to the touch menu, touch practice screens, and progress pages.
- Deployed to the active Pi and confirmed the `Pappy` profile picker, cookie selection, and migrated progress files are working.
- Fixed student roster persistence so new students remain available after navigation and profile switching.
- Made the active student name more prominent on student-facing touch pages.
- Added a touch Daily Mission page that summarizes today's progress, accuracy, remaining signals, active letters, Learning Now letters, and practiced letters.
- Added Daily Mission to the touch menu as the likely student starting point.
- Confirmed hands-on testing with multiple students: profile creation/switching works, the larger student name works well, and the Daily screen data/screens are useful.
- Captured learning direction for words, rewards, and future game ideas: introduce known-letter words before the full alphabet, reward real mastery milestones, and use game concepts later as wrappers around real practice.
- Decided tomorrow's first build should focus on Daily Mission motivation: completion celebration, short sound/LED feedback, and a clear next action such as Learn new letters or practice the weakest mode.
- Close-of-day GitHub status: student profiles, Daily Mission, words/rewards/game notes, and documentation updates are committed and pushed to `main`.

### 2026-06-21

- Added Daily Mission completion reward on the 7-inch touch screen.
- Completed missions now show a `Mission Complete` reward panel with `Signal Clear`, today's accuracy, and the next recommended action.
- Added Pi station celebration playback using a short Morse `V` flourish through the USB speaker with synchronized LED flash.
- Added next-action guidance: prefer Learn when new letters are waiting, otherwise send the student to the weakest current practice mode or progress/next unlock guidance.
- Deployed the reward flow to the active Pi at `10.10.10.141` and confirmed the service is active.
- Added a Daily Practice Coach panel with `Practice Next`, `Strong`, and `Boost` recommendations.
- Coach recommendations use existing per-letter and per-mode strength data, prefer Learn when new letters are waiting, and otherwise point students toward weak letter/mode combinations.
- Deployed the Practice Coach to the active Pi and confirmed the Daily page renders the coach panel.
- Separated current-set mastery from full alphabet progress: the UI now shows letters mastered as `6/26`, `8/26`, etc. instead of implying the student is 100% done with Morse.
- Changed the unlock rule so new letters start only after the current active set reaches 100% across all five modes: Learn, Send, Read, Listen, and Echo.
- Added a Python `unittest` regression bank for learning gates, alphabet progress, stale Learning Now cleanup, Learn burn-in graduation, Daily Mission summary rules, and Practice Coach recommendations.
- Added Flask route/render regression tests for touch Daily/Progress/Learn pages, Daily celebration endpoint behavior, stale Learning Now pruning during render, and student cookie separation.
- Added a desktop-only Admin Reset form on `/students` that requires typing `RESET`, creates a timestamped backup, clears the selected student's progress files, and clears legacy top-level files for Pappy so they cannot re-seed progress.
- Added regression tests for reset confirmation, Pappy legacy cleanup, backup creation, and protecting other student profiles.
- Fixed the Daily Mission screen while new letters are in `Learning Now`: mission completion now includes Learn burn-in progress, shows remaining Learn tries, and changes the coach grouping from generic `Boost` to `Learning`.
- Clarified current-set versus Learning Now progress across touch and desktop Progress/Practice screens so `100%` mode scores do not imply new letters have joined every practice mode.
- Fixed the completed Learning Now handoff so `20/20 Learn` plus the two-day burn-in gate now points students to `Come Back Tomorrow` instead of asking them to keep learning the same letters.
- Forced Pappy's S/O learning date back one day on the active Pi for testing, with a backup at `/home/morse/morse-station/data/student_backups/20260621-pappy-force-next-day/`.
- Verified the forced-next-day state: Pappy now has `8/26` letters mastered, `S` and `O` in all five practice modes, no `Learning Now` letters, and about `80%` current-set mastery because S/O still need Send/Read/Listen/Echo practice.
- Close-of-day GitHub status: Daily Mission clarity, current-set/Learning Now wording, completed burn-in handoff, README update, and regression tests are committed and pushed to `main`.

### 2026-06-22

- Fixed Progress scoring for the Learning Now phase: when new letters such as `R K` are active in Learn, the Learn card/details now show the new-letter Learn mastery instead of the already-mastered current set.
- Kept Send, Read, Listen, and Echo Progress cards scoped to the current practice set while new letters remain Learn-only.
- Added a regression test for the S/O mastered plus R/K Learning Now state so Progress continues to point students toward the actual Learn work.
- Deployed the Progress fix to the active Pi and verified `/touch/progress` shows `Learning R K` with low Learn mastery while current-set modes can remain 100%.
- Corrected Learning Now mastery again so Learn progress is based on burn-in completion, such as `15/20 Learn` and `75%`, instead of strength-only scoring that could show 100% before the required correct reps are complete.

### 2026-06-23

- Changed the touch start flow so `/touch` is now a resolver: multi-student stations go to `/touch/students`, while one-student stations go directly to `/touch/daily`.
- Moved the old touch menu to `/touch/menu` so Daily Mission can be the student-centered start page without losing the full navigation menu.
- Updated touch student switching so selecting or creating a student defaults to that student's Daily Mission.
- Updated touch page navigation so student-name links return to Daily after switching users, while Menu links go to `/touch/menu`.
- Added a 10-minute touch inactivity timeout that redirects idle touch pages back to `/touch`; that then resolves to student selection or Daily based on profile count.
- Added regression tests for touch start routing, touch menu availability, and touch student-selection redirect behavior.
- Deployed to the active Pi and verified `/touch` redirects to `/touch/students`, `/touch/menu` renders the menu, `/touch/students` defaults to `/touch/daily`, and the full Pi regression suite passes.
- Redesigned the touch Daily Mission content hierarchy around the student's next action: Next Step, Today, Learning Now, Progress So Far, and Working / Needs Work.
- Made Learning Now the primary Daily focus when new letters are open, including per-letter burn-in counts and an explicit note that those letters are not yet in Send, Read, Listen, or Echo.
- Added route coverage for the Daily screen's Learning Now guidance so `R K` style states show the exact work remaining instead of emphasizing old current-set 100% scores.
- Aligned touch Daily and touch Progress wording/data for Learning Now so both show the same `16/20 Learn`, per-letter counts, and `current-set mastery` terminology.
- Added practice POST route regression coverage for `/practice/next`, `/practice/retry`, and `/practice/result`, including Learning Now scoping and ignored out-of-scope letters.
- Added the first derived badge layer: `Daily Signal Complete`, `Clean Copy`, `First Signals Mastered`, `New Signals Ready`, and `Signal Builder`.
- Added compact badge feedback on touch Daily and the earned badge list plus next badge target on touch Progress.
- Kept badges derived from current progress for now instead of writing earned badge history into student data; this avoids locking in labels or thresholds before student testing.
- Deployed the badge update to the active Pi and verified the 35-test Pi regression suite passes.
- Tightened the touch Daily layout for the 800x480 7-inch screen: shorter header/footer, taller bottom row, slightly smaller large text, and capped active/practiced letter chips with `+N` overflow summaries.
- Added regression coverage for long letter sets and verified an 800x480 worst-case Daily screenshot with all alphabet letters active and the next number group in Learning Now.
- Added the first optional Bonus Round: Signal Sprint appears after Daily completion and gives students 20 random active letters to key once each.
- Stored Signal Sprint attempts in `bonus_attempts.jsonl` so bonus play does not inflate Daily Mission counts or advance normal practice mastery/unlock gates.
- Added live sprint scoring for attempts, accuracy, current streak, best streak, and remaining signals.
- Added route coverage for the Daily sprint link, sprint screen rendering, and bonus result storage that leaves normal practice progress untouched.
- Close-of-day GitHub status: touch start flow, Daily clarity/layout, badges, practice POST tests, and Signal Sprint are deployed to the active Pi and pushed to `main`; latest Pi regression suite passed with 40 tests.

### 2026-06-24

- Added `scripts/backup_data.py` to create local zip backups of station data, including student profiles, timing settings, per-student progress, learning state, practice attempts, and Signal Sprint bonus attempts.
- Added backup manifests, restore-to-folder support, and retention cleanup so the newest backups are kept and old backup zips are rotated out.
- Added optional user systemd backup service/timer files for daily Pi backups.
- Updated the fresh Pi setup guide with manual backup, daily timer install, restore inspection, and restore safety steps.
- Added backup regression tests for zip contents, manifest format, restore extraction, and retention cleanup.
- Deployed the backup script/docs/tests to the active Pi, ran the 43-test regression suite, and verified a manual backup zip at `data/backups/20260624-140412-manual-test.zip`.
- Added direct Daily navigation from touch practice screens so students do not have to go through Modes/Menu after a practice round.
- Added a 100% practice-mode guidance message: `Mode complete. Go to Daily for the next step.`

### Ready Next

- Install and test the optional daily backup timer on the active Pi.
- Decide whether Daily Mission rewards should be recorded as earned badges in student data.
- Test whether the direct Daily button and completion message solve the Echo/Practice navigation confusion.
- Test whether the first badge labels and next-badge target motivate students without making the Daily screen confusing.
- Test whether Signal Sprint feels like a useful post-Daily game and whether 20 signals is the right starting length.
- Decide whether to add Clean Streak, adaptive sprint goals, or best-sprint history next.
- Test whether the Daily Practice Coach wording feels encouraging for different student styles.
- Physically confirm the revised touch Daily screen no longer scrolls or crowds the footer on the 7-inch display.
- Decide whether to add a separate touch Letter Progress screen with per-letter cards and direct practice links.
- Continue testing Astrid/Liara-style profiles to confirm each keeps separate progress, learning state, and attempt logs.
- Run a fresh student-style session across Learn, Send, Read, Listen, Echo, and Daily Mission with one non-Pappy profile.
- Watch whether the burn-in gate feels motivating rather than blocking after a next-day return.
- Continue testing the forced-next-day S/O state to confirm new letters feel natural once they join Send/Read/Listen/Echo.
- Retest physical keyer sound immediately after Learn, Listen, and Echo station prompts.
- Confirm Listen remains recognition-only and that `Play Again` always plays sound and flashes the LED.
- Confirm Learn and Echo prompt LED flashes are synchronized well enough to reinforce the Morse rhythm.
- Test the no-scroll touch menu flow directly on the physical 7-inch touchscreen.
- Tune any touch screen labels, button sizes, or spacing after physical testing.
- Decide whether `/touch/message` should stay as a hidden utility or be removed entirely from the touch experience.
- Test automatic touch UI selection on the Pi touchscreen, a laptop browser, and Kindle Fire/Silk when available.
- Test whether the 12/6 WPM Farnsworth-style beginner timing is easier to hear and imitate than 15/7.
- Tune Operator Level thresholds, rank names, badges, and unlock messaging after student testing.
- Decide whether to enable the optional auto-update timer on the current test Pi, then test one manual update run before using it at remote locations.
- When AWS planning starts, compare periodic timer updates with AWS Systems Manager triggered updates for remote grandkid stations.
- Review logged attempt timing after hands-on testing and choose the first student-facing timing feedback message.
- Choose next core-practice build after Daily rewards: Mixed mode, more letters, timing feedback, or first known-letter word practice.
