# Pappy's Internet Telegraph Project Plan

## 2026-08-29 - Hardened and truthful remote updates

- Confirmed Astrid/Liara was online and syncing data but remained at `cecbb77`
  after repeated update attempts. Its older updater treated a dirty-checkout
  safety skip as exit code 0, so the IoT job incorrectly reported success.
- Hardened the updater contract before implementation: one update lock,
  preserved dirty-tree patch, nonzero blocked outcomes, starting/target/ending
  commits, explicit rollback reasons, and ending-commit verification.
- Added a sanitized cloud status summary. Admin System now shows Updated, Up to
  date, Update blocked, Update failed, Updating, or Rolled back with a
  plain-language reason and timestamp.
- Hardened AWS IoT Jobs so `update-app` requires a fresh successful/current
  local report and verifies optional `expected_commit`. Added fixed, read-only
  `diagnose-update`; arbitrary command text remains rejected.
- Added regression coverage for the observed false-success case, dirty blocks,
  stale/missing results, expected-commit mismatch, diagnostics, locking, and
  safe cloud status fields.
- The updater now refreshes its own wrapper and local/IoT service definitions
  after a successful merge or when already current, while preserving timer
  enablement. This prevents new updater code from remaining under an obsolete
  systemd timeout policy.
- Pappy live rehearsals proved rollback: Pi-only compatibility checks caught
  stale template assumptions and a platform-dependent rendered-text assertion.
  Each run restored the prior commit and left the app/browser healthy; the
  brittle assumptions were removed before retrying.
- Deployment constraint: Pappy and Campbell can receive the hardened release
  normally. Astrid/Liara needs one local checkout recovery because its existing
  old updater blocks before it can install the fix.
- Promoted the corrected release to `release/pi` at `4aa22f5`. Pappy passed all
  261 discovered Pi tests, restarted cleanly, returned HTTP 200 from the touch
  health check, and wrote a `current` report with matching start/target/end
  commits. The app and supervised browser remained active.
- Live AWS IoT Job `morsepi-hardened-pappy-20260829-1456` required commit
  `4aa22f5`, was consumed by Pappy, verified the fresh local report, and was
  marked `SUCCEEDED` by AWS with reason `already-current`. Both installed
  update services now report a 20-minute start timeout.

## 2026-08-28 - Spec and implementation reconciliation

- Compared the current code, route contracts, regression tests, and recent
  station releases with the requirements in `specs/`.
- Confirmed FR-054/AC-039/TEST-024 match the two-hour or abandoned-owner sync
  lock recovery implemented in `scripts/student_attempt_sync.py`.
- Confirmed FR-061/AC-036/TEST-021 match the current three-minute idle start,
  5-second Morse-only recall, 3-second answer reveal, and wake-only touch/keyer
  behavior.
- Confirmed FR-063/NFR-022/DR-021/API-028/AC-038/TEST-023 match the current
  Signal Drop selector, server validation, 800x480 layout, physical-key input,
  and persistent red retry feedback.
- Corrected stale compliance references to the initial Signal Drop release,
  obsolete physical-key follow-up, and older automated-test totals. No code
  changes were required. The local suite passes 252 tests.

## 2026-08-26 - Offline recovery and stale sync lock

- Confirmed Pappy retained progress during the internet outage and uploaded a
  full shutdown backup plus a current progress snapshot after connectivity
  returned at 11:26 AM.
- Found that cross-station attempt merge had skipped since August 8 because a
  power-interrupted process left `student_attempt_sync.lock` behind.
- Added automatic stale-lock recovery when the owner no longer exists or the
  lock is older than two hours, while preserving active-owner exclusion.
- Added AC-039 and TEST-024 coverage. Pappy updated through the protected
  release path at `179ae62` and passed 252 tests.
- The live forced recovery removed the abandoned lock, created sync backup
  `20260827-013739`, uploaded 907 missing immutable attempts, read 1,608 cloud
  attempts, and rebuilt Pappy from 1,192 practice attempts plus 239 Words and
  177 bonus attempts. The lock cleared and app/browser/sync services remained
  active.
- Follow-up performance work: batch missing attempt objects into one recursive
  S3 upload so a large offline backlog does not start one AWS CLI process per
  record. This is a speed improvement; the completed run proved data integrity.

## 2026-08-25 - Screensaver timing refinement

- Shortened each idle learning cycle from 10 seconds Morse-only plus 5 seconds
  revealed to 5 seconds Morse-only plus 3 seconds revealed.
- Kept the three-minute activation delay, no-sound/no-LED behavior, random safe
  movement, no-answer-flash protection, and touch/keyer wake behavior unchanged.
- Updated FR-061, AC-036, TEST-021, and the compliance status before deployment.

## 2026-08-24 - Signal Drop learning game

- Researched established typing-tutor game patterns, including falling-letter
  and invader-style drills, and selected a non-punitive Morse adaptation.
- Added Signal Drop to the touch Practice menu with two modes: Send shows a
  falling letter for physical-keyer or spacebar input; Read shows falling Morse
  with large touch letter choices.
- Kept curriculum boundaries authoritative: normal games use only the current
  student's active letters. Learning Now and locked letters cannot be returned
  by the selector or accepted by the result endpoint.
- Prompt selection uses approximately 60% established, 25% most recently
  activated, and 15% weak/overdue pools, with safe fallback when a pool is
  empty. Missed letters enter a local review queue and return soon.
- Correct input clears every visible duplicate. Four-answer streaks gradually
  increase bounded fall/spawn speed; misses lower speed, show the target's
  centered Morse pattern, and never remove points or end play.
- Game attempts are server-checked and written to `bonus_attempts.jsonl` as
  `kind=signal-drop`, preserving effort and timing history without changing
  practice mastery, Daily Mission counts, or unlock gates.
- Added FR-063, NFR-022, DR-021, API-028, AC-038, and TEST-023 before the code.
  The initial complete suite passed 250 tests. Send and Read passed an 800x480
  browser rehearsal with no scrolling, overlap, or browser errors; correct and
  needs-work feedback and touch pause/restart paths were exercised.
- Published main `f8aa8d7` and station release `a24ed0a`. Pappy's normal safe
  updater installed `a24ed0a`; the app and supervised browser are active, and
  the live Signal Drop route returns HTTP 200 with Pappy's active set through
  `L` while later letters remain excluded.

### Follow-up results and next steps

1. Physical straight-key testing is complete. Follow-up releases fixed repeated
   polling feedback, increased the playfield height, moved controls to the
   right, and keep incorrectly keyed targets visible in red for retry.
2. Continue observing whether the 60/25/15 mix feels balanced for students with
   newly activated letters, then tune using recorded game attempts rather than
   score alone.
3. After Send/Read settles, consider a Listen variant and known-letter Words
   round using the same game shell.

## 2026-08-24 - Screensaver answer-flash correction

- Observation: at the start of a new recall cycle, the prior letter remained
  visible briefly because CSS delayed `visibility: hidden` during its opacity
  transition.
- Decision: hide immediately, clear the character element for the entire
  10-second recall phase, and populate it only when the 5-second reveal begins.
  This prevents both prior-answer and next-answer flashes.
- Pi frame sampling found that an empty character element initially collapsed
  its grid row and moved the Morse pattern during reveal. Reserve a fixed
  answer-row height so Morse remains stationary in both phases.
- Pappy frame sampling across repeated shortened cycles found zero yellow
  answer pixels at every new-cycle boundary. Final release `79c8ebd` reserves
  the answer row, is deployed with fresh CSS/JavaScript asset versions, and
  leaves the supervised app/browser health checks passing.

## 2026-08-24 - Browser supervision hardening

- Decision: replace the one-shot Labwc Chromium launch with a supervised user
  service that waits for Wayland and the app, owns the kiosk process, restarts
  unexpected exits, and records failures in the user journal.
- Preserve adult recovery: the PIN-gated `Exit Kiosk` action stops supervision
  before closing Chromium, leaving the desktop available until service start
  or reboot.
- Integrate the idempotent installer into the normal update path, remove legacy
  browser autostart only after a successful supervised start, refresh Chromium
  after app updates, and add browser service health to station status uploads.
- Added FR-062, NFR-021, AC-037, and TEST-022 before implementation.
- First Pappy update exposed a self-update edge case: an updater process that
  began on the prior release could fetch the new installer but could not run
  newly added updater lines from its replaced script file. Added an idempotent
  supervision preflight before the already-current exit as well as after a
  merge, so a second update check repairs stations arriving from older code.
- Pappy live acceptance passed on `57c8b63`: supervision is enabled and owns
  exactly one kiosk; legacy Labwc/XDG entries are absent; a forced Chromium
  kill recovered in 6 seconds while the app PID and student-data fingerprint
  remained unchanged.
- The PIN-gated `Exit Kiosk` action left the desktop visible with Chromium and
  the browser service stopped. Two successive installer runs restored exactly
  one kiosk. Station status reports both app and browser services as active.
- Cold reboot acceptance passed without manual launch: app and browser services
  were active, `/touch/students` returned HTTP 200, zero user services were
  failed, and the physical display showed the normal operator picker.

## 2026-08-24 - Screensaver recall reveal

- Post-restart Pi inspection found the answer visible over an empty-looking
  Morse row. The shared `currentColor` marks rendered dark on the Pi Chromium
  compositor even though desktop-browser rehearsal showed cyan marks.
- Recovery: restarted only the Chromium kiosk, preserving the app and student
  data. The normal operator screen returned immediately.
- Fix: give screensaver dots and dashes an explicit cyan background and bump
  the touch stylesheet version so the kiosk cannot reuse the faulty CSS.
- Published as `352d91e` on `main` and `1067212` on `release/pi`; Pappy's
  updater installed `1067212` successfully.
- Live 800x480 Pi captures now verify both phases: cyan Morse alone, followed
  by the yellow answer above the unchanged cyan pattern. The standard
  three-minute launcher was restored and the normal operator screen verified.
- Live acceptance completed for both wake methods: the physical keyer and the
  touchscreen dismiss the screensaver correctly.
- Decision: turn each idle display into a gentle recall prompt. Show Morse
  alone for 10 seconds, reveal the matching letter or number for 5 seconds
  while keeping the Morse visible, then move to a new signal and position.
- Keep the saver silent and keep all wake-only, shutdown-exclusion, and
  10-minute operator-reset behavior unchanged.
- Local verification passes: 241 regression tests plus an 800x480 browser
  rehearsal covering Morse-only recall, fixed-position answer reveal, next-cycle
  reset, safe movement, and first-touch wake protection.
- Published as `f88f3ca` on `main` and `1f179db` on `release/pi`. Pappy's
  updater installed `1f179db`; the app service is active, the update result is
  successful, and the local touchscreen health check returns HTTP 200.
- Final live observation of the recall and reveal sequence now passes on Pappy.

## 2026-08-23 - Idle Morse screensaver

- Added an app-level screensaver for the 7-inch touch station. It starts after
  3 minutes without activity and keeps the existing 10-minute return to the
  operator flow.
- The saver uses a black background and the shared centered Morse renderer to
  show a random A-Z or 0-9 character. It changes character and safe screen
  position every 10 seconds without playing sound or lighting the LED.
- The first touch is wake-only and cannot activate a covered control. A
  physical keyer press also wakes the station, clears that wake signal, and
  does not submit a scored answer.
- Shutdown is excluded. The operator picker can remain safely on the saver
  until touched because it contains no student progress or message content.
- Added FR-061, NFR-020, AC-036, and TEST-021. The complete local suite passes
  240 tests, and an 800x480 browser rehearsal confirmed movement, layout,
  touch wake protection, shutdown exclusion, and the operator reset.
- Promoted the feature to `release/pi` at `5053f37` and deployed it through
  Pappy's normal update service. The updater passed, restarted the app, and
  refreshed the station snapshot; hands-on physical-keyer wake testing remains
  the final live acceptance check.

### Daily Wrap-Up

**Accomplishments**

- Removed the old Pappy-to-Astrid rehearsal message from local and cloud
  history and added a safe cleanup migration for stations that were offline.
- Added, specified, tested, released, and deployed the idle Morse screensaver.
- Verified the screensaver at 800x480, including movement, character rotation,
  first-touch wake protection, shutdown exclusion, and the existing operator
  reset. The complete regression suite passes 240 tests.
- Updated the functional, non-functional, acceptance, testing, status, README,
  and project-memory documentation. The screensaver was accepted in live use.

**Decisions**

- Keep the screensaver inside the app so normal remote software updates deliver
  it without separate Raspberry Pi desktop configuration.
- Start it after 3 idle minutes, rotate a random A-Z or 0-9 signal every 10
  seconds, and retain the 10-minute return to the operator flow.
- Keep automatic screensaver activity silent. Treat the first touch or physical
  keyer signal as wake-only input so it cannot submit an accidental answer.

**Next steps**

1. Perform the final live physical-keyer wake check on Pappy and confirm the
   wake signal does not appear as a scored attempt.
2. When the grandkid stations reconnect to Wi-Fi, verify they update to the
   current `release/pi` and report fresh sync/update status.
3. Continue Message Builder Slice 2: require students to key each selected word
   before sending while allowing an easy correction for a mistaken word.
4. Implement the backlog rule that adds an operator's name to `Words I Know`
   once all letters in that name are active.

## 2026-08-23 - Message history cleanup

- Removed the old Pappy-to-Astrid `AM` cloud message rehearsal from live Pappy
  message history and S3 message-sync storage because Astrid did not create or
  perform that test.
- Added a small updater migration, `scripts/cleanup_removed_messages.py`, so
  any station that still has the rehearsal message locally removes it during
  its next app update after the normal pre-update backup.
- Added regression coverage to verify the cleanup removes only the selected
  rehearsal message and preserves unrelated message history.

## 2026-08-21 - Warm-Up Review and update-path clarification

- Added Warm-Up Review as a Daily-driven catch-up activity for students who
  have been away from normal practice for at least 3 calendar days.
- Warm-Up reviews only letters the student already has active, uses a
  10-signal goal, and logs `warmup` attempts with `review_only=true` so effort
  and rhythm history are preserved.
- Kept Warm-Up review-only by design: it does not change Send/Read/Listen/Echo/
  Learn mastery, unlock gates, or the 20-signal Daily Mission count.
- Fixed Daily priority so active Learning Now letters remain ahead of Warm-Up;
  Warm-Up appears only when the student is otherwise ready to resume.
- Deployed the releases to Pappy through the normal `release/pi` update path.
  Early Warm-Up update attempts failed the Pi regression suite and
  automatically rolled back, which proved the safety wrapper. After the final
  fixes, Pappy updated to `9c62f70`, passed 232 Pi tests, passed the `/touch`
  health check, and refreshed station status/snapshots.
- Clarified operations language: `Sync Now` moves student progress, messages,
  station status, and backups; app features move through `Update App`, the
  local update timer, or an AWS IoT `update-app` Job pulling `release/pi`.
- Added a manual Warm-Up button to the Practice menu so students can start a
  quick review whenever they want, even when Daily has not automatically
  recommended it.
- Adjusted Warm-Up review to show both the target letter and its Morse pattern
  because this mode is meant to refresh memory before independent practice.
- Tuned Warm-Up rotation: after a correct key it pauses long enough to read the
  feedback, then rotates to another learned letter; reaching the 10-signal goal
  no longer forces the student out of Warm-Up.
- Cleaned up practice instruction text across Learn, Send, Read, Listen, Echo,
  and Warm-Up so the bottom-left feedback box gives plain next-step guidance
  instead of embedding raw Morse in a sentence. Decision: the main prompt owns
  the Morse display; feedback text should not include raw dot/dash strings
  where punctuation can look like an extra Morse dot.

### Daily Start Notes

- Pappy is current on `release/pi` at `8b0cc7c`; no manual app copy was needed.
- The remote grandkid stations will not receive the Warm-Up feature until they
  are powered on, online, and run their local update path or consume an IoT
  `update-app` Job.
- Data sync and software update are separate paths. Use `Sync Now` to move
  practice data; use `Update App` or remote update jobs to move new features.
- Warm-Up can now be started two ways: Daily suggests it after a long break,
  and the Practice menu lets a student start it on demand.
- Current Warm-Up behavior: show the letter and Morse pattern, key it, show the
  result briefly, rotate to another learned letter, and keep reviewing after
  the 10-signal goal until the student chooses to leave.
- Practice-mode feedback behavior: the bottom-left box now uses plain next-step
  instructions only; raw dot/dash Morse stays in the centered visual prompt.

**Next steps**

1. When Astrid/Liara is online, trigger or verify `update-app` so it catches up
   to the current `release/pi`.
2. Continue live-testing Warm-Up on Pappy for pacing and clarity.
3. Decide whether deployed stations should keep automatic app update timers
   active or rely mainly on adult-triggered IoT update jobs.
4. Continue Message Builder Slice 2: require students to key each selected word
   before sending.

### Daily Wrap-Up

**Accomplishments**

- Implemented and released Warm-Up Review with regression coverage.
- Verified the hardened updater's rollback behavior during a real Pappy update
  failure, then verified the corrected releases with the full Pi test suite.
- Updated specs/status and operations docs so Warm-Up, Sync Now, and app update
  behavior are explicit.
- Updated specs to require both automatic Daily Warm-Up and manual Practice
  menu Warm-Up.
- Iterated Warm-Up UX based on live testing: manual start, visible Morse
  review pattern, learned-letter rotation, readable success pause, and no
  forced exit at 10 review signals.
- Pappy is deployed on `release/pi` commit `8b0cc7c`; service is active and the
  Pi-local `/touch` health check passed.

**Next steps**

1. Use the remote update path to bring Astrid/Liara to the current release once
   it is online; Campbell/Olivea already showed fresh cloud activity today.
2. Watch whether Warm-Up's 1.8-second pause feels right or should be adjustable.
3. Keep specs updated before larger changes, especially Message Builder and
   remote update/sync work.
4. Continue Message Builder Slice 2 when Warm-Up testing feels settled.

## 2026-08-11 - Pappy Git update path

- Converted the Pappy station from a manual-file install into a Git checkout
  tracking `origin/release/pi` at `4fe2dbd`.
- Preserved Pappy's existing `data/` folder, student progress, station config,
  backup/sync state, and message data during the conversion.
- Kept timestamped safety copies on the Pi:
  `/home/morse/morse-station.pre-git-20260811T123104Z` and
  `/home/morse/morse-station.manual-20260811T123104Z`.
- Reinstalled the current user systemd app service, local update service/timer,
  and AWS IoT remote-update service/timer from the repo.
- Enabled `morse-station-update.timer` and
  `morse-station-remote-update.timer`; both timers are active.
- Ran the local update service successfully. It backed up, confirmed the
  checkout was current, wrote station status/snapshots, uploaded the latest
  progress snapshot, and left the app service healthy.
- Ran the IoT remote-update poller successfully. It reached AWS IoT Jobs and
  recorded `no-pending-job` for `pappy-test-station`.
- Confirmed least privilege: the station IAM user cannot create IoT Jobs
  (`iot:CreateJob` denied). That is expected; Pappy can consume update jobs,
  but jobs must be created by the admin/control-plane credentials.
- Live app check passed after conversion: `/touch` responds, the app service is
  active, and `Words I Know` still renders.
- Hardware decision captured: the Raspberry Pi 4 built-in 3.5 mm jack is output
  only. For a cleaner detachable key, use a separate panel-mount 3.5 mm jack
  wired to GPIO17 and GND as a switch connector.
- Operator visibility decision: it is safe to hide grandkids from Pappy's local
  picker when Pappy is being used as the test station. Hiding a student from a
  local picker does not delete their UUID, progress data, cloud backups,
  snapshots, or home-station sync identity.

### Daily Start Notes

- Pappy can now be used as the normal test station while exercising the same
  Git + local update + IoT poller path as the remote stations.
- To test a full remote update, create an AWS IoT Job from the admin AWS
  credentials with action `update-app`; Pappy should consume it within about 15
  minutes or immediately if `morse-station-remote-update.service` is started.
- Continue to treat `release/pi` as the deliberate deployment branch. Test on
  Pappy first, then push/trigger the grandkid stations when ready.

**Next steps**

1. Create one admin-side smoke `update-app` Job for Pappy to verify the full
   remote trigger path end to end.
2. Decide whether to keep Pappy's 6-hour local update timer active alongside
   IoT Jobs, or only use on-demand update jobs.
3. Continue Message Builder Slice 2: require students to key each selected word
   before sending.
4. When Campbell/Olivea reconnects, confirm it reaches the current
   `release/pi` and has the same update timers active.

### Daily Wrap-Up

**Accomplishments**

- Confirmed Pappy is now using the normal Git + local update + IoT poller path
  instead of direct file copy.
- Updated architecture/spec status to remove stale "Pappy manual install"
  language and reflect the current rollout.
- Captured the keyer connector decision in setup docs: Pi built-in 3.5 mm is
  output only; use GPIO17/GND for the key, optionally through a panel jack.
- Confirmed hiding grandkids from Pappy's local operator picker is an interface
  choice only; their home-station progress and cloud identity still sync when
  their stations are online.

**Next steps**

1. Use admin AWS credentials to create a Pappy `update-app` smoke Job and prove
   the full remote trigger path end to end.
2. Continue Message Builder Slice 2: require students to key each selected word
   before sending.
3. Decide whether Pappy should keep both the 6-hour local update timer and the
   on-demand IoT update trigger, or rely on IoT-triggered updates.
4. When the grandkid stations reconnect, verify they update to the current
   `release/pi` and continue uploading backup/sync data.

## 2026-08-10 - Home Wi-Fi checklist and family-data privacy groundwork

- Added a screenshot-based Home Wi-Fi setup checklist for stations arriving at
  a new house. The guide walks an adult through the operator picker, touch menu,
  Admin System status, Wi-Fi setup, sync expectations, and basic recovery.
- Sanitized the checklist screenshots so they use sample names (`Alex`,
  `Jordan`, `Taylor`, `Morgan`, `Riley`) and sample network values
  (`Home-WiFi`, `Station-01`, `192.168.x.x`) instead of family names, home
  network names, or local IPs.
- Linked the checklist from the README and grandkid deployment checklist.
- Reviewed the repo for family names. Confirmed real names remain in tracked
  config examples, AWS/station docs, specs/status history, tests, scripts, and
  older historical screenshots.
- Decided not to immediately replace every real name in GitHub because
  `config/family_registry.json` is still a live canonical UUID registry used by
  deployed stations, messaging, and progress sync.
- Added private family-registry support: the app now prefers ignored
  `data/family_registry.json` and falls back to tracked
  `config/family_registry.json` until a station has completed migration.
- Updated the student-UUID migration to copy the tracked registry into
  `data/family_registry.json` on each station if the private file does not
  already exist.
- Added `data/family_registry.json` to `.gitignore`.
- Added `docs/PRIVACY_AND_FAMILY_DATA.md` with the safe anonymization sequence
  and screenshot guidance.
- Updated setup docs and specs/status for the private-registry transition.
- Validation passed locally: `python -m unittest discover -s tests` ran 223
  tests successfully with 132 skipped.
- Added 14 D/U-enabled Words prompts (`AND`, `END`, `SAD`, `SUN`, `RUN`,
  `RED`, `KID`, `MUD`, `TUNE`, `DUNE`, `SEND`, `SAND`, `SOUND`, `ROUND`).
  Once D/U are active, Words expands from 42 to 56 available words, so a student
  who completed the earlier set should show 42/56, or 75%, until the new words
  are completed.
- Added 24 C/W/H/L-enabled Words prompts (`COW`, `HOW`, `LOW`, `LAW`, `CALL`,
  `WALL`, `WELL`, `HILL`, `COOL`, `COLD`, `HOLD`, `DUCK`, `LUCK`, `LOCK`,
  `ROCK`, `ROLL`, `TELL`, `HELLO`, `WORLD`, `WORD`, `CODE`, `HOME`, `HOUSE`,
  `CLOCK`). Once C/W/H/L are active, Words expands from 56 to 80 available
  words, so a student who completed the D/U set should show 56/80, or 70%,
  until the new words are completed.
- Started Message Builder Slice 1: added a scrollable touch Word Bank for
  `Words I Know` and shared recipient words, linked it from Messages and
  Compose, and added word-level draft controls so a selected word can be
  replaced, moved, or removed without clearing the whole message.
- Added a Words practice shortcut to `Words I Know`; Word Bank tiles now show
  whether each word is new, tried, or done based on the student's Words
  practice attempts.
- Decision: keep the normal compose/review screens fixed at 800x480, but allow
  the Word Bank to scroll because browsing is its purpose. Key-to-send
  validation is still Slice 2.

### Daily Wrap-Up

**Accomplishments**

- Created and pushed the Home Wi-Fi setup checklist with sanitized screenshots.
- Removed the visible real-name/network leak from the new checklist branch
  history by replacing the checklist commit on both `main` and `release/pi`.
- Built the first safe step toward anonymizing the broader GitHub repo:
  real family identity data can now live in ignored station-local
  `data/family_registry.json`.
- Added tests covering the private-registry migration behavior.
- Pushed privacy groundwork to `main` (`ac07658`) and `release/pi`
  (`7f1cc41`).
- Expanded Words practice for the D/U group and the C/W/H/L group. Words now
  grows from 42 to 56 after D/U and from 56 to 80 after C/W/H/L, with
  regression coverage for both completion drops.
- Fixed the C/W/H/L word eligibility leak where `MOUSE` became available too
  early at D/U; replaced it with `CLOCK` and added a lightweight curriculum
  word-bank count test.
- Added Message Builder Slice 1: a scrollable `Words I Know` / shared Word
  Bank, word-level draft editing, replace/remove/move controls, and a compact
  `More Words` path from Compose.
- Added a Words practice `Known` link into `Words I Know`, plus word status
  indicators: `New`, `Tried`, and `Done`.
- Deployed the updated release to Pappy and verified live pages: Words shows
  `42/56 words complete` after D/U, Messages shows `Words I Know`, and the
  Word Bank renders practice-status badges.
- Pushed the day's app work to `main` through `89121a4` and `release/pi`
  through `ea443f8`.

**Decisions**

- Do not replace the tracked family registry with sample names until deployed
  stations have copied the current real registry into ignored
  `data/family_registry.json`.
- Treat real names, UUIDs, and family rosters as operational private data.
  Public examples, screenshots, and future docs should use sample operators.
- Keep older public-name cleanup as a separate follow-up after the migration is
  deployed and verified on each station.
- Keep the Word Bank as the intentional scrollable reference screen while
  keeping Words practice, Compose, and Review fixed for the 800x480 station.
- Implement message building in slices: Slice 1 is word browse/pick/edit;
  Slice 2 should require students to key each drafted word before sending.

**Station and data state**

- Pappy: still a manual-file install, so it will need a direct update or later
  conversion to a Git checkout before it benefits from the same updater path.
  It was manually refreshed today from `release/pi` through `ea443f8`.
- Astrid/Liara: `release/pi` now contains the private-registry migration; next
  online update should create `data/family_registry.json`.
- Campbell/Olivea: `release/pi` contains the same migration; verify after the
  station reconnects.
- `release/pi` also contains the D/U and C/W/H/L Words expansions, Word Bank,
  and Words practice status indicators. Remote stations need their update path
  to run before those changes appear there.
- GitHub still contains real names in older docs/config/tests/history by
  design for now; the new privacy doc captures the safe sequence to finish the
  cleanup.

**Next steps**

1. Deploy or trigger update on each station so `data/family_registry.json` is
   created from the current real registry.
2. Verify `data/family_registry.json` exists on each station and that practice,
   backup, sync, and messages still work.
3. After verification, replace tracked examples/docs/screenshots/tests with
   sample names and sample station IDs where practical.
4. Review older historical screenshots under
   `docs/screenshots/current-app-2026-07-04/` and either sanitize, archive
   privately, or remove them from public docs.
5. Continue delivery readiness: confirm grandkid stations connect to home
   Wi-Fi, upload backup/status, sync progress, and remain remotely updateable.
6. Message Builder Slice 2: require students to key each selected word before
   sending, validate one word at a time, and allow retrying only the current
   word without clearing the draft.
7. Add later Words packs for P/F/Y/G, B/V/J/X, Q/Z, and numbers so each new
   unlock continues to create practical word practice.

## 2026-08-08 - AWS IoT remote update trigger

- Added the first AWS IoT Jobs based remote-update worker. A station can now
  poll for a durable pending maintenance job and start only known local actions:
  `update-app`, `sync-progress`, `backup-data`, `write-status`, or
  `restart-app`.
- Added `scripts/remote_update_iot.py`, the user systemd
  `morse-station-remote-update.service`, and a 15-minute
  `morse-station-remote-update.timer`.
- Added a least-privilege station policy template for IoT Jobs data-plane
  polling. The worker rejects unknown actions and never runs shell text from
  AWS.
- Created AWS IoT Things in `us-east-1` for `pappy-test-station`,
  `astrid-liara-station`, and `campbell-olivea-station`.
- Attached one narrow IoT Jobs inline policy to each existing station IAM user:
  `morsepi-pappy-test-station`, `morsepi-astrid-liara-station`, and
  `morsepi-campbell-olivea-station`.
- Confirmed the account Jobs endpoint:
  `l1dnyp15x2puh8.jobs.iot.us-east-1.amazonaws.com`.
- Deployed the remote-update worker and timer to the Astrid/Liara station.
  The first live smoke Job safely failed because AWS returns `jobDocument` as a
  JSON string; no local command ran. Fixed the parser and added regression
  coverage for the real AWS response shape.
- Ran a second live `update-app` IoT Job for Astrid/Liara:
  `morsepi-update-astrid-liara-20260808-0709`. The station consumed it,
  started the local update service, stayed healthy at commit `f806498`, wrote a
  local succeeded status, and AWS reports the Job execution as `SUCCEEDED`.
- Updated the station config examples, setup docs, remote deployment docs, and
  specs before implementation.
- Local validation passed: focused remote-update/systemd tests and full laptop
  test discovery.

### Daily Wrap-Up

**Accomplishments**

- Built and live-tested the AWS IoT Jobs remote-update path. Astrid/Liara
  consumed a real `update-app` Job and stayed healthy through the existing
  local update service.
- Added and pushed the remote-maintenance cost guardrail: normal three-station
  remote maintenance should stay under `$1/month` where practical, with
  Systems Manager kept as optional temporary remote-hands support.
- Updated the project architecture diagram for the current AWS design: S3
  backup/status/snapshots/messages/attempts, Lambda message routing, guarded
  student progress sync, AWS IoT Things/Jobs, rollout status, and optional SSM.
- Generated new Astrid/Liara cartoon artwork from the station photos. Selected
  option 2B for the boot splash and option 3 for the desktop wallpaper.
- Replaced `docs/assets/morsepi-boot-splash.png` and
  `docs/assets/morsepi-desktop-wallpaper.png`, kept selected concept source,
  transparent, and preview files in `docs/assets/wallpaper-concepts/`, and
  pushed the artwork to both `main` and `release/pi`.
- Deployed the new splash and wallpaper to Pappy and Astrid/Liara. Pappy was
  updated by direct asset copy because it is still a manual-file install.
  Astrid/Liara updated to artwork commit `cecbb77` through the normal updater.
- Verified Pappy and Astrid/Liara app services remained active after artwork
  install; Astrid/Liara's remote-update timer remained active.

**Decisions**

- Use AWS IoT Jobs as the normal low-cost remote update trigger. Do not use
  Systems Manager as the default maintenance channel because of fixed
  per-device monthly cost.
- Keep remote Jobs declarative and allow-listed. The station may run known
  local actions such as `update-app`; it must not execute arbitrary shell text
  from AWS.
- Use option 2B as the boot splash and option 3 as the desktop wallpaper.
- Before the Astrid/Liara station goes home, hide Pappy from the normal
  kid-facing operator picker while preserving his background data and identity
  so he can be re-enabled later if needed.

**Station and data state**

- Pappy: active, new wallpaper installed, new Plymouth boot splash installed.
  Remote update is not enabled because the station is still a manual-file
  install rather than a Git checkout.
- Astrid/Liara: active on `cecbb77`, new wallpaper installed, new Plymouth boot
  splash installed, AWS IoT remote-update timer enabled and active.
- Campbell/Olivea: AWS IoT Thing and policy are ready, but station rollout is
  pending reconnection at its home location.
- Broad AWS admin access was used for setup today and should be disabled again
  unless more AWS provisioning is planned immediately.

**Next steps**

1. Hide Pappy from Astrid/Liara's local roster before the station leaves, while
   keeping Astrid, Liara, and Guest visible.
2. Reboot Astrid/Liara once before delivery to visually confirm the new splash,
   wallpaper, kiosk launch, app service, sync timer, and remote-update timer.
3. At the grandkids' house, configure Wi-Fi if needed, then confirm the station
   comes online, uploads backup/status, and continues guarded progress sync.
4. After delivery, send one low-risk IoT `update-app` Job to Astrid/Liara after
   the next release to confirm the remote update path works off-site.
5. When Campbell/Olivea comes online, install/enable its remote-update timer
   and run the same live AWS IoT Job smoke test.
6. Decide later whether to convert Pappy to a Git checkout so it can use the
   same remote update path, or leave it as the local lab/manual station.

## 2026-08-07 - Permanent student identity

- Added immutable UUIDs for Pappy, Astrid, Liara, Campbell, and Olivea while
  retaining current display names and legacy IDs.
- Added compatibility enrichment for profiles, attempts, progress snapshots,
  and family messages without moving old folders or cloud paths.
- Added a backed-up, repeatable station migration to the remote update flow.
- Hardened offline rollout so pending migrations also run when a station is
  already on the current release; this covers a station whose first update ran
  the previous updater process before the new migration hook was loaded.
- Kept Guest disposable and UUID-free; conflicting ID/UUID records fail closed.
- Added regression coverage for migration safety, legacy enrichment, rename
  stability, registry uniqueness, and identity-conflict rejection.
- Updated the AWS `morsepi-message-router` Lambda first and verified an empty
  invocation returned HTTP 200 with no function error before releasing Pi code.
- Pappy was backed up to S3, manually updated and migrated, passed all 216
  Pi-side tests, and restarted healthy. A second migration changed nothing.
- Astrid/Liara fast-forwarded to `6e0080c`, migrated, passed all 217 Pi-side
  tests, restarted healthy, and completed an already-current updater rehearsal.
- Campbell/Olivea was offline after delivery. `release/pi` now runs pending
  migrations before the already-current exit, so it will catch up on its next
  update cycles without requiring progress-folder renames or history rewrites.
- Completed the live UUID progress rehearsal between Pappy and Astrid/Liara.
  Pappy's 515 Practice and 186 Words records had identical hashes on both
  stations, and all 701 records carried Pappy's canonical UUID with no cloud
  upload, duplicate, download, or conflict needed.
- Completed a live UUID-bearing `AM` cloud message rehearsal from Pappy to
  Astrid using only their shared starter letters. Lambda delivered exactly one
  inbox copy, Astrid/Liara returned one decoded receipt, and Pappy's outbox
  advanced to `state: decoded` and `cloud_state: decoded` with both UUIDs
  preserved. The controlled decode added no practice credit or mastery data.
- The normal kid-facing send flow correctly remained locked because Astrid's
  current family summary contains only the six starter letters. Her mastery was
  not altered to force the rehearsal; she will unlock Messages naturally after
  `S` and `O`.

### Daily Wrap-Up

**Accomplishments**

- Completed the permanent student identity rollout: one canonical UUID for
  each named family member, compatible legacy IDs and paths, UUID-bearing new
  attempts/snapshots/messages, backed-up migration, and conflict rejection.
- Updated and smoke-tested the AWS message router before releasing station code.
- Verified Pappy and Astrid/Liara migrations are idempotent and both app services
  are healthy. Pappy passed the 216-test Pi suite; Astrid/Liara passed the
  expanded 217-test Pi suite during release updates.
- Proved cross-station progress identity with exact matching hashes for Pappy's
  515 Practice and 186 Words records. All 701 records contain the same UUID.
- Proved the live UUID message round trip with one `AM` rehearsal: one Lambda
  delivery, one Astrid decoded receipt, and Pappy status advanced to decoded.
- Re-reviewed the specs through FR-057, DR-020, SEC-021, API-026, AC-030, and
  TEST-018. Made UUID explicit in DR-017 snapshots and API-020/021, restored
  numerical requirement order, refreshed compliance tables, and added a
  snapshot UUID regression assertion. Focused checks pass on both reachable Pis.

**Decisions**

- UUID is the permanent person identity. Display name is a label; legacy ID
  remains a compatibility alias for folders, cookies, and cloud paths.
- Guest remains local, disposable, UUID-free, and excluded from family sync and
  messaging. Canonical family ID aliases are reserved from generic user creation.
- Historical UUID-less records remain valid and are enriched during sync;
  supplied ID/UUID conflicts fail closed. Existing folders and history are not
  renamed or bulk-rewritten merely to introduce identity.
- Do not change a student's mastery to make a deployment test pass. Astrid's
  Messages UI will unlock naturally after `S` and `O`; the controlled cloud
  rehearsal added no practice credit.
- Keep pull-based `release/pi` updates as the reliable baseline. AWS IoT remains
  the preferred low-cost immediate remote update trigger; Systems Manager stays
  optional because of per-device cost.

**Station and data state**

- Pappy: active, backed up to S3 before migration/rehearsal, manually updated,
  migrated, and verified. The decoded `AM` rehearsal remains as an audit record.
- Astrid/Liara: active on `f5fdf87`, backed up to S3 before rehearsal, migrated,
  updated through the reviewed specs release, and verified.
- Campbell/Olivea: offline at its home. `release/pi` contains automatic pending-
  migration catch-up; verify its commit, migration, tests, and sync after it
  reconnects. No local intervention is required for normal offline app use.
- No student mastery, attempt totals, or unlocked letters were changed by the
  message rehearsal. No sync conflicts or duplicate attempts were found.

**Ready next**

1. Verify Campbell/Olivea reaches the current `release/pi` and completes its
   identity migration after it reconnects.
2. Build the narrow AWS IoT command path for an immediate remote update request,
   while retaining the station's backup, test, migration, and health checks.
3. Let Astrid unlock Messages naturally, then kid-test the normal compose,
   review, send, decode, and receipt UI without infrastructure shortcuts.
4. Continue normal Words/Daily practice observation and prioritize app-activity
   write throttling as the next small hardening change.
5. Deactivate the broad laptop AWS admin key now that router deployment is done;
   reactivate it only for approved AWS setup work.

**GitHub**

- `main` and `release/pi` include all implementation and spec work through
  `f5fdf87`; this wrap-up entry is the final documentation-only closeout commit.

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

- Raspberry Pi GPIO setup for telegraph key and LED
- Text-to-Morse conversion
- Morse-to-text decoding
- Browser Morse playback
- Pi hardware playback using LED and USB speaker
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
- Progress snapshots now compute active letters from rebuilt learning/progress data instead of trusting stale message-summary caches
- Daily and Progress screens explain why Learn-only letters have not joined practice yet, including per-letter strength gaps
- Admin System screen shows last student sync status, relative time, and upload/download counts
- Scheduled student sync now refreshes station snapshots and family progress after each guarded attempt sync, with a persistent timer for boot catch-up
- Family Progress station cards now flag current, stale, and missing station snapshots so Wi-Fi/offline issues are easier to spot
- Admin System screen shows app version/branch, update timer/result, and last local backup age/name
- PIN-gated Sync Now waits for the local sync service result and reports completed, skipped, or finished status on return

## Codebase Review Triage

A July 2026 codebase review correctly identified that the project has grown beyond its original single-file prototype shape. The main theme is valid: before expanding remote sync, messaging, or more stations too far, reduce the small security/reliability risks that come from `app.py` holding many routes and module-level mutable state.

Address soon:

- Add input size caps for typed messages and Morse prompt payloads. Reason: this is an easy, high-value protection against memory exhaustion on a small Pi.
- Route all `next` redirects through `safe_next_url()`. Reason: this is a small mechanical fix that closes open redirect behavior.
- Add short-term concurrency protection. Reason: current per-request path globals and practice globals are fragile if two browsers use the same station at once. Short-term mitigation can be single-thread serving; longer-term fix is passing student paths explicitly instead of mutating `set_progress_path()` and `set_attempts_path()`.
- Unify the curriculum/progression tables. Reason: `letter_unlock_steps`, sync rebuild rules, and snapshot rules duplicate curriculum ideas and can drift.
- Add dependency/tool checks for `speaker-test`, `aplay`, `aws`, `git`, and `systemctl`. Reason: the app and scripts depend on external binaries that should fail clearly during setup.

Defer:

- CSRF protection. Reason: valid concern for admin routes, but admin PINs are now configured on deployed stations and are not stored in cookies. Add after the simple safety fixes.
- WSGI server replacement for the Flask dev server. Reason: worthwhile before wider deployment, but input caps/redirect fixes/concurrency decision come first.
- Update-channel hardening with release branch, signed tags, and rollback. Reason: important before broad remote auto-update, less urgent while deployments are manual and S3 backup/status is the active remote milestone.
- Splitting `app.py` into packages/blueprints. Reason: needed eventually, but do after safety fixes so we do not spread current bugs into new files.
- Safe student progress snapshots and `family_summary.json`. Reason: still important, but design it after at least one more station exists so cross-station sync is grounded in real behavior.

Low priority / ignore for now:

- Rebuilding around a smaller MVP. Reason: true historically, but the current product value comes from the learning/progress layer.
- Removing `archive/` and untracking generated PDFs. Reason: repo hygiene, not operational risk.
- Treating the Flask dev server as an internet-production exposure. Reason: stations are LAN/kiosk devices, but serving should still be improved before grandkid deployment.
- Making admin PIN mandatory in every example. Reason: blank PIN is useful for local development; deployment docs require a real local PIN before a station leaves home.

Recommended remediation order:

1. Add input caps.
2. Fix unsafe redirects.
3. Add short-term single-thread/concurrency protection and tests.
4. Unify the curriculum tables.
5. Add dependency/tool checks.
6. Continue Astrid/Liara station build.

## Milestones

### MVP 1: Working Pi Morse Station

Status: Complete

Goal: A student can type a message, see Morse, play it in the browser, play it on the Pi station, tap the physical key, and use basic Practice Mode.

Completed work:

- Create Flask app
- Add Morse conversion
- Add browser playback
- Add Pi LED and USB speaker playback
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

Status: In progress

Goal: Move students from isolated letters toward practical Morse communication while preserving motivating mastery loops.

Planned work:

- Add Word Copy practice using only active/learned letters. Started for the `E T A N I M S O` active set.
- Start with 2-3 letter words, then grow toward short messages. Started with short known-letter words.
- Favor touch word choices and telegraph-key input before typed answers. First implementation uses touch controls and physical keying.
- Add Signal Set Complete celebration when active letters reach 100%.
- Add New Mission Unlocked feedback when new letters enter Learning Now.
- Add Daily Mission completion celebration with short sound and LED flash.
- Track word progress separately from letter mastery.
- Consider a future game wrapper, such as Signal Quest or Message Rescue, after word practice is stable.

Implemented so far:

- Touch Words practice unlocks once `S O` are active.
- Words are filtered to the student's active letters.
- Play uses Pi station USB speaker output and LED flash.
- Students key the whole word and see `Keyed`, `Read As`, and persistent Correct/retry feedback.
- Correct answers flash the word cards 10 times with no extra Morse-like reward sound.
- Wrong answers explicitly tell the student to tap Clear, then try again.
- Word attempts log separately in `word_attempts.jsonl` and do not affect normal letter mastery.

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
13. Add student/operator names to `Words I Know` once the student has learned
    every letter in that name; for example, `PAPPY` should appear as soon as
    `P` is learned because the remaining letters are already available.

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
- Added telegraph key and LED hardware tests.
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
- Slowed letter progression for better memory burn-in: new Learning Now groups were raised to 10 correct Learn tries per letter and 70% Learn strength before joining Send/Read/Listen/Echo; the original next-day pacing was later retuned to a shorter rest plus Words requirement after student testing.
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
- Fixed the completed Learning Now handoff so `20/20 Learn` plus a pacing gate points students to the right waiting/next-action message instead of asking them to keep learning the same letters.
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

### 2026-06-25

- Fixed Daily Mission guidance for the S/O transition: already-started Learning Now groups now stay active until they lock in or graduate, instead of being pruned if an older mode dips below 100%.
- Adjusted Daily so Bonus Round appears only when the Daily count is complete, the current set is complete, and no Learning Now group is still active.
- Bumped Astrid's S/O learning date forward on the active Pi for testing so S/O joined her active practice set.
- Added the first Words practice flow after S/O: known-letter words filtered to active letters, a touch Words tile, and a dedicated `/touch/words` screen.
- Added Pi station playback for Words so Play uses the USB speaker and LED.
- Added full-word keying feedback with Keyed, Read As, Correct, and retry messages.
- Removed the Read shortcut from Words and kept the right-side controls focused on Play, Stop, Clear, and Next.
- Changed Next to clear the old keyed input and auto-play the next word.
- Added visual-only correct feedback for Words: the word cards flash 10 times while the Correct message remains visible until Clear or Next.
- Removed the confusing Morse-like correct-answer reward sound.
- Added separate word attempt logging in `word_attempts.jsonl`, including word, expected/actual Morse, decoded text, correct flag, elapsed time, and timing summary.
- Added or updated regression coverage for Words unlock, rendering, station playback, word logging, and Daily guidance edge cases.
- Deployed all changes to the active Pi at `10.10.10.141`, restarted the app after each deployed fix, and kept GitHub `main` updated.
- Close-of-day GitHub status: all Words practice, Daily guidance, visual reward, retry feedback, and documentation changes are committed and pushed to `main`.
- Replaced the full next-day letter pacing rule with a faster controlled gate: Learning Now still needs 10 correct Learn tries per new letter, 70% Learn strength, and about 3 hours of rest before joining active practice.
- Added a next-group gate after `S O`: once the current active set is 100%, the student also needs 5 correct Words attempts since the latest group started before another new group can open.
- Added a daily pacing cap of 2 new Learning Now groups per calendar day so fast learners can continue after a break but cannot unlock the whole ladder in one sitting.
- Updated Daily next-action guidance so it can point students to `Practice Words`, `Take A Break`, or `Come Back Tomorrow` depending on which gate is blocking the next group.
- Added regression tests covering the new Words/rest unlock gates and updated route fixtures to match the new pacing model.
- Started the remote grandkid-station deployment foundation.
- Added station identity config support for unique ids such as `astrid-station` and `liara-station`.
- Extended local backups with station-aware filenames/manifests and optional S3 upload paths.
- Added station status reporting with station id, hostname, Git commit, latest backup, service state, and optional S3 upload.
- Added a safer remote-update wrapper that backs up first, fast-forwards from GitHub only when safe, compile-checks, restarts the service, and writes status.
- Added AWS remote deployment notes and kid-facing station instructions/rules to GitHub docs.
- Added student effort feedback: Daily and Progress now show estimated practice time so kids are encouraged by steady learning time, not only correctness.
- Effort time is estimated from logged practice, Words, and Signal Sprint attempts; close-together attempts count as active practice, while long idle gaps are ignored.
- Added first grit-focused motivation layer: `Focused Practice` rewards 10 active minutes, `Try Again Champ` rewards a miss followed by a later correct attempt, and Daily now shows a short coach line connecting effort to improvement.
- Removed the passive piezo buzzer hardware path from current docs/tests so the station sound model is now USB speaker plus LED.
- Fixed Daily Practice Coach overlap so a letter no longer appears in both Working Well and Needs Work on the Daily screen.
- Added 3D printed enclosure requirements to the BOM: the case needs to enclose the 7-inch display plus the Raspberry Pi 4 mounted on the back, with room for cables, DSI ribbon, GPIO wiring, USB speaker, service access, and airflow.
- Added enclosure next steps for measuring the display/Pi stack and printing a Bambu X1 Carbon test-fit plate before a full case print.
- Added a color, comic-style one-page kids quick-start handout as both editable HTML and printable PDF.
- Linked the handout from the student instructions and README so it is easy to find in GitHub.
- Close-of-day GitHub status: passive buzzer cleanup, Daily coach fix, enclosure notes, kids handout, and documentation updates are committed and pushed to `main`.

### 2026-06-26

- Renamed the printable kids handout to `Pappy's Operators`, changed the badge to `Grand Operator`, and regenerated the PDF.
- Added a second handout page for duplex printing: a comic-style `Signal Roadmap` showing the full learning order from starter letters through numbers.
- Added [GRANDKID_STATION_DEPLOYMENT.md](GRANDKID_STATION_DEPLOYMENT.md) as the leave-the-house checklist for fresh Pi setup, station identity, hardware tests, touch boot, student profiles, backup, status, update, and kid readiness.
- Added [REMOTE_BACKUP_STATUS_RUNBOOK.md](REMOTE_BACKUP_STATUS_RUNBOOK.md) with the recommended operations order: local backup, optional S3 backup/status, manual update wrapper, optional timer later, and AWS IoT command triggers after backup/status is proven.
- Added tracked station config examples for `astrid-station` and `liara-station` under `config/stations/`.
- Added a tracked `pappy-test-station` config example and applied it to the active Pi so test-station backups/status are no longer named `unknown-station`.
- Smoke-tested the active Pi backup/status path with `--dry-run-s3`; local backup/status worked, service state reported `active`, and dry-run destinations resolved under `s3://morsepi-backups/stations/pappy-test-station/`.
- Added [CASE_MEASUREMENT_WORKSHEET.md](CASE_MEASUREMENT_WORKSHEET.md) for measuring the 7-inch display/Pi stack before designing the Bambu X1 Carbon test-fit plate or full enclosure.
- Updated README, setup, AWS remote deployment, BOM, and student instruction docs to link the new handout/checklist/runbook/worksheet.
- Ran the grandkid deployment checklist rehearsal on the active Pi: station identity, service, touch routes, student folders, kiosk browser, display mode, USB audio device, compile check, backup/status dry-run, and practice prompt playback all passed.
- Rehearsal finding: the active Pi app folder is still file-deployed rather than a Git checkout, so the update-wrapper path cannot be fully rehearsed there. Grandkid units should be cloned from GitHub so status can report Git branch/commit and the update wrapper can fast-forward safely.
- Cleaned up the touch Progress screen for the 800x480 display: widened the left summary column, reduced Send/Read/Listen/Echo/Learn card size, fixed the `Telegraph Pro` overlap, and added a compact Words progress card.
- Added Words progress summary data from `word_attempts.jsonl`, including accuracy, unique words completed, available known-letter words, and correct/total word attempts.
- Deployed the Progress cleanup to the active Pi, verified the updated Pappy screen with an 800x480 screenshot, and ran the 66-test Pi regression suite successfully.
- Updated the touch Words screen to show the same Words progress summary as Progress, including percentage, unique words completed, and correct/total word attempts.
- Added Words auto-advance: after a correct keyed word, the Correct message remains visible briefly and the screen advances to the next word after about 2 seconds.
- Deployed the Words update to the active Pi, verified the Pappy Words screen at 800x480, and reran the 66-test Pi regression suite successfully.

### 2026-06-27

- Closed the day with the current app, touch UI, docs, handout, and Pi deployment changes committed and pushed to GitHub.
- Confirmed the latest GitHub work includes the touch Progress cleanup, Words progress summary, Words auto-advance, and the enlarged two-page `Pappy's Operators` handout roadmap.
- Active Pi status at close: latest app/static/template/test files are deployed to `10.10.10.141`, service was restarted after the Words update, and the Pi regression suite passed with 66 tests.
- Current learning/product decision: Words practice looks encouraging and should keep getting tested with the kids before deciding whether it stays a bonus activity or becomes part of Daily Mission.
- Current deployment decision: grandkid stations should be built as Git clones, not file-deployed folders, so the update wrapper, branch/commit status, and future remote update path can work cleanly.
- Current operations decision: local backups are ready; next cloud step is AWS S3 backup/status upload before adding AWS IoT command triggers.

### 2026-06-28

- Refined the AWS deployment direction for tomorrow's work.
- Decision: start with Systems Manager as the first remote-admin bridge so Pappy can connect, troubleshoot, and run update/status/backup scripts on deployed stations.
- Decision: keep normal app backup/sync independent of Systems Manager; S3 remains the backup, status, progress snapshot, and family-summary store.
- Decision: AWS IoT remains the likely later path for lower-cost lightweight commands, online presence, and family Morse messages after S3 backup/status is proven.
- Decision: each Pi must have its own narrow AWS identity. No shared device credentials.
- Product direction: shared progress should focus on practice visibility, effort, persistence, recent wins, and family milestones instead of ranked leaderboards that could discourage younger learners.
- Added [AWS_BACKUP_SYNC_DESIGN.md](AWS_BACKUP_SYNC_DESIGN.md) to capture the S3 layout, per-device credential rule, family progress philosophy, temporary setup user, and first AWS tasks.
- Updated the AWS deployment and remote backup/status docs to match the new SSM-first remote-admin plan.
- Close-of-day status: this was documentation and strategy work only; no app code changed and no regression suite was needed.

### 2026-06-30

- Started the pre-AWS hardening work from the adversarial review.
- Added GitHub Actions CI so GitHub installs project dependencies with mock GPIO and runs the regression test bank on every push and pull request.
- Aligned cloud upload destinations with the AWS backup/sync design: backups now target `stations/<station-id>/backups/`, status targets `stations/<station-id>/status/station_status.json`, and progress snapshots have a `stations/<station-id>/snapshots/` helper ready for the next phase.
- Updated backup/status tests and runbooks so IAM policies can be written against the same prefix layout the code uses.
- Hardened Practice, Words, and Signal Sprint result recording so the server recomputes correctness from the target and submitted Morse/answer instead of trusting the browser's `correct` flag.
- Added regression tests for browser-submitted false positives across keyed practice, read/listen answers, Words, and Signal Sprint.
- Decided the station model for the four grandkids: no kid passwords, shared student profiles across three family stations, progress belongs to students, and Pappy's station can host all four students.
- Added `station_id`, `student_id`, and `practice_session_id` metadata to Practice, Words, and Signal Sprint attempts so wrong-user recovery can later move or discard a whole session.
- Added optional admin PIN protection for adult actions: adding students, resetting progress, and changing timing or station volume.
- Replaced the old per-child station examples with the three planned station examples: `pappy-station`, `astrid-liara-station`, and `campbell-olivea-station`.
- Deployed the station/session/admin PIN update to the active Pi at `10.10.10.141`, restarted the app service, and verified the Pi regression suite passed with 77 tests.
- Confirmed GitHub Actions CI is green after the hardening work; latest successful run is for commit `abb75a2`.
- Close-of-day decision: start AWS work only after the local recovery/audit basics are in place enough to avoid syncing confusing or wrong-user practice data.

### 2026-07-01

- Implemented the wrong-user recovery tool at `/admin/sessions`.
- Added a desktop admin page that lists recent practice sessions by `practice_session_id`, student, station, attempt counts, accuracy, and latest timestamp.
- Added admin actions to move a full session to another student or discard a session, with optional admin PIN protection when configured.
- Recovery now updates Practice, Words, and Signal Sprint attempt logs and rebuilds `practice_progress.json` for affected students so Progress/Daily match the corrected logs.
- Recovery creates a local backup under `data/session_recovery_backups/` before changing affected student files.
- Added route tests for session listing, moving, discarding, admin PIN rejection, and progress rebuild behavior.
- Deployed the recovery tool to the active Pi at `10.10.10.141`, restarted the user-level `morse-station.service`, verified `/admin/sessions` renders, and confirmed the Pi regression suite passed with 81 tests.

### 2026-07-02

- Added [AWS_SETUP_REFERENCE.md](AWS_SETUP_REFERENCE.md) as a credential-free setup document for the AWS foundation.
- Captured the ordered setup flow: temporary setup identity, private/versioned/encrypted S3 bucket, one narrow credential per station, first backup/status upload, Systems Manager hybrid activation, and cleanup of setup credentials.
- Included placeholder-only CLI commands, S3 layout, per-station IAM policy template, Pi configuration steps, and Systems Manager role/activation notes.
- Linked the setup reference from README, AWS design, remote deployment, and backup/status runbook docs.
- Decision: keep real account IDs, access keys, secret keys, activation IDs/codes, and admin PINs out of GitHub.
- Configured the active Pi with a real local admin PIN and verified the app recognizes it without exposing the PIN.
- Decided deployed touch stations should use preloaded student rosters instead of an on-screen Add Student flow because the kids will not have a keyboard.
- Added station-config roster support with `allow_student_create`, `students`, and disposable `guest_profile`.
- Updated station config examples for Pappy, Astrid/Liara, Campbell/Olivea, and the active Pappy test station to include expected names plus disposable `Guest Operator`.
- Hid the Add Student form on touch and desktop screens when station creation is disabled, while preserving admin/reset/recovery flows.
- Added `student_disposable` to attempt metadata so future family summaries can ignore Guest practice.
- Restricted disposable Guest from message routes so Guest can practice/demo Morse but cannot send or receive messages.
- Created the AWS S3 backup foundation in `us-east-1` with bucket `morsepi-backups-luminerdy`.
- Hardened the bucket with public access blocked, versioning enabled, AES256 default encryption, and project tags.
- Created narrow station IAM user `morsepi-pappy-test-station` with policy `morsepi-pappy-test-station-s3`.
- Configured the active Pi with the station IAM credential without printing the secret, updated its `backup_s3_uri`, and verified its AWS identity.
- Verified least-privilege behavior: the active Pi can access `stations/pappy-test-station/` and is denied access to another station's raw prefix.
- Uploaded and verified one real backup and one real status file from the active Pi to S3.
- Created narrower setup IAM user `morsepi-setup-admin` with policy `morsepi-setup-admin-policy`, configured the laptop profile, verified it can manage MorsePi S3/IAM setup, and deactivated the broad default local `admin` access key.
- Close-of-day decision: keep the broad `admin` access key deactivated but available as a last-resort setup key for future IoT work; prefer creating purpose-limited setup identities first.
- Sync direction decision: raw backups stay station-owned, while future safe progress snapshots should become student-owned so practice done on Pappy's station can later sync back to each grandkid's home station.
- Deployment direction: build the Astrid/Liara station first, prove the checklist and S3 backup/status flow on a second unit, then repeat for Campbell/Olivea.

### 2026-07-03

- Hardened the remote app update path for grandkid stations.
- Changed the station updater default from `main` to `release/pi` so deployed Pis pull from a deliberate release branch instead of active development.
- Added a post-restart health check against `http://127.0.0.1:5000/touch` before the updater reports success.
- Updated the user systemd update service to use `release/pi` and the new health-check settings.
- Updated setup, AWS deployment, backup/status, and grandkid deployment docs to describe the release branch flow and timer rollout rules.
- Decision: deployed stations should be cloned from GitHub and checked out to `release/pi`; the optional timer should be enabled only after a manual update works.
- Decision: keep the active lab Pi file-deployed for now unless we intentionally rebuild it as a Git checkout; use the grandkid station builds to prove the real remote-update path.
- Created and pushed the `release/pi` branch so deployed stations have a stable pull-based update channel.
- Fixed a confusing Learning Now display issue where Learn mode could show `100%` from letter strength even though the burn-in rule still required more correct Learn tries.
- Pappy's live D/U Learning Now state now correctly shows `65%`, `13/20 Learn`, and the next needed Learn tries instead of `100%`.
- Added regression coverage so Learning Now Learn screens and JSON practice responses use burn-in progress rather than strength-only mastery.
- Deployed the Learn progress display fix to the active Pi at `10.10.10.141`, restarted `morse-station.service`, and verified the Pi route suite passed with 52 tests.
- Captured a presentation-oriented project prompt inventory covering the project arc from GitHub setup through Pi deployment, learning modes, AWS backup/update, and quality work.
- Close-of-day GitHub status: remote update channel hardening and the Learning Now progress fix are committed and pushed to both `main` and `release/pi`; active Pi service is running.

### 2026-07-04

- Captured current app screenshots from the active Pi at `10.10.10.141` using the 800x480 touch layout for presentation use.
- Added the screenshot set under [Current App Screenshots - 2026-07-04](screenshots/current-app-2026-07-04/README.md), including student selection, Daily, Progress, Words, Listen, Learn, and touch menu screens across Pappy, Astrid, and Liara.
- Clarified the data-capture strategy for practice timing and Words rhythm.
- Decision: keep raw timing events as the durable source of truth so future rhythm analysis can improve without losing historical student practice data.
- Decision: Words attempts are important rhythm evidence because they capture whole-word timing, letter spacing, elapsed time, and consistency over a real short message.
- Decision: future rhythm feedback should show progress over time and coach gently; it should not block correctness credit or make kids feel punished for imperfect timing.
- Close-of-day GitHub status: screenshots and rhythm data strategy documentation are committed and pushed to both `main` and `release/pi`.
- Close-of-day Pi status: no app code was changed today after the July 3 Learn progress fix; final SSH service check to `10.10.10.141` timed out, so active Pi service state was not re-verified during wrap-up.

### 2026-07-05

- Added richer timing summaries for keyed Practice and Words attempts.
- Added the same timing-event normalization and timing summary generation for Signal Sprint attempts so all keyed activity captures comparable rhythm data.
- New timing summary fields include separate symbol/letter/word gap counts and averages, min/max letter gaps, dot and dash consistency, dash-to-dot ratio, spacing score, overall rhythm score, and a primary rhythm feedback phrase.
- Added an adult/admin rhythm trend page at `/admin/rhythm`.
- The rhythm page summarizes each student's keyed attempts across Practice, Words, and Signal Sprint, including recent rhythm score, dot/dash consistency, spacing, average symbol/letter gap timing, Words accuracy, source counts, recent keyed attempts, and trend direction.
- Added regression tests for richer timing summaries, Sprint timing summaries, and the admin rhythm page.
- Deployed to the active Pi at `10.10.10.141`, restarted `morse-station.service`, verified `/admin/rhythm` returns 200, and confirmed the Pi regression suite passed with 55 tests.
- Added a hardening pass for the first multi-station rollout: request payload limit, typed message and Morse payload caps, timing-event caps, safe local-only `next` redirects, single-threaded Flask serving on the Pi, and one source of truth for the unlock curriculum.
- Added `scripts/check_dependencies.py` so a fresh Pi can quickly report required runtime tools (`git`, `systemctl`, `aplay`, `speaker-test`, Flask, GPIO Zero) and optional cloud/messaging tools (`aws`, MQTT).
- Added root `specs/` package for a future rebuild, including product overview, MVP scope, feature inventory, FR/NFR/SEC/API/TEST requirement IDs, acceptance criteria, testing strategy, rebuild roadmap, documentation plan, and legacy compliance status through `7818254`.

### 2026-08-01

- Added a touch System recovery page for local adult troubleshooting without a keyboard: Wi-Fi/IP status, NetworkManager tool visibility, admin-PIN-gated Wi-Fi restart, and admin-PIN-gated kiosk exit to the Raspberry Pi desktop.
- Updated specs before implementation with FR-038, API-018, AC-014, and feature inventory entry F-23.
- Deployed the change to the active Pi at `10.10.10.141`, restarted `morse-station.service`, verified `/touch/system` returns 200, and confirmed the Pi regression suite passed with 84 tests.
- Extended the touch System page with on-screen keyboard availability and an admin-PIN-gated `Open Keyboard` action for Wi-Fi or desktop troubleshooting without a physical keyboard.
- Started the Astrid/Liara station at `10.10.10.129`: installed required packages, cloned `release/pi`, configured station id `astrid-liara-station`, enabled the app service and local backup timer, verified the touch roster, and confirmed the Pi regression suite passed with 98 tests.
- Hardened the browser helper for new Raspberry Pi OS Labwc/Wayland sessions by passing Chromium the Wayland platform flag when `WAYLAND_DISPLAY` is present.
- Configured the Astrid/Liara station AWS credential as `morsepi-astrid-liara-station`, restored its S3 backup URI, verified real backup/status uploads, confirmed the backup timer uploads successfully, and confirmed the station credential is denied access to the Pappy test station prefix.
- Built the Campbell/Olivea station at `10.10.10.157`: installed required packages, cloned `release/pi`, configured station id `campbell-olivea-station`, set admin PIN locally, enabled the app service and backup timer, configured AWS credential `morsepi-campbell-olivea-station`, verified S3 backup/status uploads and cross-station access denial, confirmed the Pi regression suite passed with 98 tests, and reboot-verified app/kiosk startup.
- Added a PIN-gated `Update App` action to the touch System page that starts the existing `morse-station-update.service`, letting an adult trigger the tested release update wrapper locally without a keyboard.
- Confirmed the two new grandkid stations are physically working after hardware install: USB speakers detected, LEDs confirmed, and keyers confirmed.
- Deployed and tested the `Update App` action on both grandkid stations. Each station created a pre-update backup, confirmed it was current on `release/pi`, kept the app active, and uploaded fresh S3 station status.
- Close-of-day station status: Pappy/test (`10.10.10.141`), Astrid/Liara (`10.10.10.129`), and Campbell/Olivea (`10.10.10.157`) are online with active app services, running touch kiosks, working USB speakers, confirmed LEDs, and confirmed keyers.
- Close-of-day GitHub status: touch System recovery/update work, specs, setup docs, and station deployment notes are committed and pushed to both `main` and `release/pi`.
- Close-of-day decision: near-term deployed updates can be handled by a local PIN-gated `Update App` button; remote command triggering remains future work through AWS IoT or Systems Manager.

### 2026-08-02

- Implemented Phase 7A local family Morse messaging from the requirements added
  before development.
- Added server-validated drafts, shared active-letter eligibility, a three-word
  and 20-letter limit, atomic message storage, duplicate-safe local delivery,
  and separate per-student inbox/outbox/event data.
- Added an 800x480 touch flow for recipient selection, word-tile and physical-key
  composition, letter correction, Morse review, speaker/LED playback, sending,
  inbox browsing, and guided letter-by-letter decoding.
- Added progressive decode hints: slower playback, visible Morse, then letter
  reveal. Message plaintext remains hidden until each position is solved or
  revealed.
- Added message effort logging and the `First Message Sent` and
  `Secret Message Decoded` badges without changing letter mastery.
- Added message files to student reset/backup handling and added an explicit
  `family_students` station directory separate from the local sign-in roster.
- Added [MESSAGING.md](MESSAGING.md) and aligned README, setup, kid instructions,
  feature inventory, data requirements, and compliance status with the shipped
  Phase 7A boundary.
- Verified the complete Pi regression bank passes with 131 tests and visually
  rehearsed hub, compose, correction, review, playback, hints, and decode at
  the real 800x480 viewport on Pappy's test station.
- Refined message composition after hands-on feedback: physical-key entry now
  captures one complete available Words-practice word, adds the word and its
  boundary together, and rejects single-letter or unknown keyed entries.
- Changed composer Undo to remove the last complete word and removed the manual
  Space action; letter-tile correction remains available for fixing mistakes.
- Centered the Choose Operator action label on the Messages hub and verified
  its 42px touch target fits the 800x480 screen without scrolling.
- Separated message recovery controls after hands-on testing: Try Word Again
  clears only the live keyed word, Undo Word removes the last completed word,
  and Clear Message explicitly starts the whole draft over.
- Centered the composer Review link inside its full touch target to match the
  Choose Operator action and the adjacent message controls.
- Centered the Daily Next Step action, including Learn and Signal Sprint, so
  recommended practice buttons align consistently across the touch UI.
- Added one shared visual Morse renderer that keeps canonical ASCII data while
  drawing optically centered circles and bars across Learn/Read, Words,
  Progress, Messages, and live key displays.
- Added accessible dot/dash labels, renderer unit tests, route coverage, and the
  renderer test to GitHub Actions CI.
- Updated the two-page Pappy's Operators handout to use the same centered Morse
  geometry, regenerated its letter-size PDF, and visually inspected both pages.
- Completed a repository-wide Morse display audit: removed raw punctuation from
  the remaining desktop practice retry, updated learning-document feedback,
  labeled technical ASCII examples as canonical data, and marked the July 4
  screenshots and archived prototypes as historical rather than current UI.
- Improved early Words variety after hands-on testing showed twelve consecutive
  two-letter prompts felt like a hard length limit. The opening sequence now
  mixes two- and three-letter known words, including `NOT` third and `MOM`
  sixth, while retaining the same 42-word active-letter-filtered set.
- Began Phase 7B with a documented station-prefix S3 design, privacy/retention
  policy, minimal active-letter summaries, station sync worker, independently
  validated Lambda router, deterministic receipts, and a three-station
  in-memory replay test. Cloud sync remains disabled pending AWS deployment
  and the real three-station rehearsal.
- Decision: Phase 7A remains local-only. Cross-house delivery will preserve the
  same message format in Phase 7B, using S3 for durable storage and AWS IoT only
  as an optional notification path.
- Completed the Phase 7B AWS foundation: narrow Lambda execution role, packaged
  Python 3.13 router, family directory, S3 invoke permission, and three
  non-overlapping station-prefix notification rules.
- Installed and enabled the five-minute message-sync timer on all three Pis;
  normal message sync remains disabled by configuration until activation.
- Passed the live isolated three-station rehearsal: Pappy sent `ME` to Astrid,
  both authorized stations received one copy, Campbell/Olivea received none,
  Astrid decoded it, and Pappy's outbox advanced to decoded from the receipt.
- Added [ARCHITECTURE.md](ARCHITECTURE.md) with maintained project and AWS
  diagrams showing the three Pi stations, local hardware/software boundaries,
  S3 prefixes, Lambda routing, IAM boundaries, and optional future IoT/SSM paths.
- Retuned the disabled-by-default message polling timer from five to ten minutes
  for initial family testing, balancing delivery feedback with lower S3 request
  cost; fifteen minutes remains a later option after the workflow is trusted.
- Hardened student reset for cloud messaging by backing up and removing both
  local and cached family learning summaries, preventing old message eligibility
  data from restoring letters after a deliberate family progress reset.
- Created and uploaded named pre-reset backups for all three stations, then
  reset every permanent profile everywhere it was stored while preserving local
  timestamped reset backups and S3 version history.
- Cleared current cloud snapshots and test-message records without touching
  backups or station status, then published clean `E T A N I M` summaries for
  Pappy and Astrid.
- Enabled ten-minute message sync on Pappy and Astrid/Liara only. Both completed
  clean manual syncs with no messages or receipts; Campbell/Olivea stays off.

### 2026-08-03

- Added a silent touch number keypad for admin PIN entry so adult System,
  Timing, and touch Add Student admin actions can be used without a physical
  keyboard.
- Kept PIN entry out of the Morse learning/audio path: keypad taps only update a
  hidden form field and masked display; they do not trigger speaker, LED,
  playback, or keyer feedback.
- Bumped touch CSS/JavaScript version tags on the affected pages so Chromium
  kiosk loads the new keypad behavior instead of stale cached files.
- Deployed the runtime change to the Pappy test station at `10.10.10.141`,
  restarted `morse-station.service`, verified `/touch/system` serves the keypad
  and fresh static versions, and confirmed the Pi regression suite passed with
  132 tests.
- Added `scripts/set_admin_pin.py`, a local helper that sets, prompts for, or
  clears the station admin PIN with a timestamped config backup and without
  printing the PIN.
- Added a cartoon morsePi desktop wallpaper asset plus `scripts/install_wallpaper.sh`
  so each Pi recovery desktop can show the project background after exiting
  kiosk mode.
- Added a kid-facing safe shutdown flow from the touch menu with a confirmation
  screen and a wait-for-screen-dark instruction before turning off the CanaKit
  USB-C PiSwitch.
- Clarified touch Progress/Menu top-level mastery during Learning Now: when new
  letters such as `S O` are Learn-only, the prominent percentage now follows
  Learning Now progress and labels the old current-set 100% as supporting
  context instead of implying all new-letter work is complete.
- Added regression coverage for the `S O` Learn-only state: starter set 100%,
  S/O Learn in progress, Progress labels the primary percentage as
  `Learning Now` and states that S/O are still Learn-only.
- Added parent-friendly speaker volume controls to the touch Timing screen:
  Mute, Quiet, Normal, and Loud presets use the existing adult PIN keypad and
  save to `data/volume_settings.json` so the chosen level survives app restarts.
- Enabled Pappy's station to match the grandkid stations for user-service boot:
  `morse-station.service` is enabled/active and `Linger=yes`.
- Added `scripts/progress_snapshot.py`, a read-only station progress snapshot
  writer/uploader for family visibility. The daily backup service now runs
  backup, station status, and progress snapshot upload together.
- Installed the daily backup/status/snapshot timer on Pappy so all three
  stations have the same daily safety net. This does not yet merge practice
  data between stations.
- Added `scripts/family_progress.py` and `/admin/family`, a read-only family
  progress view that combines station snapshots into one latest-per-student
  page. It reports unavailable station snapshots instead of blocking the page
  and does not write to student practice files.
- Added [STUDENT_PROGRESS_SYNC_DESIGN.md](STUDENT_PROGRESS_SYNC_DESIGN.md) to
  define the future merge contract: snapshots are visibility-only, attempts are
  source-of-truth, merge by `attempt_id`, quarantine conflicts, and never copy
  `practice_progress.json` across stations.
- Added stable `attempt_id` values to new Practice, Words, and Signal Sprint
  attempt records so future cross-station sync can merge immutable records
  without relying on newest timestamp wins.
- Close-of-day verification:
  - GitHub `main` and `release/pi` are current through `922fdd5`.
  - Astrid/Liara and Campbell/Olivea are on `release/pi` at `922fdd5`.
  - Pappy was manually file-deployed to the same runtime changes because it is
    still not a Git checkout.
  - All three app services were restarted and `/admin/family` responded.
  - Route tests passed on all three stations for the attempt-ID change.
- Current known limitation: Pappy's station credential can upload its own
  progress snapshot, but cannot yet read the grandkid station snapshot files.
  `/admin/family` therefore shows Pappy as available and the two grandkid
  stations as unavailable until AWS permissions are widened narrowly.

### 2026-08-04

- Delivery-week priority: focus on keeping the grandkid stations current,
  backed up, and progress-sync ready before they leave Pappy's house.
- Hardened `scripts/update_station.sh` for deployed stations: still backs up
  first, refuses dirty/non-fast-forward updates, and pulls only `release/pi`,
  but now compile-checks, runs the full Pi test suite before restart, refreshes
  station status/progress snapshots, and rolls back to the previous commit if
  tests or the post-restart health check fail.
- Added `scripts/student_attempt_sync.py`, a no-write progress-sync dry run that
  reports local student attempts that would upload, duplicate/conflicting attempt
  IDs, malformed records, and cloud access errors before any real merge is
  enabled.
- Ran the dry-run report on all three active Pis. Pappy has 216 local attempt
  records ready for future upload and no conflicts; both grandkid stations have
  zero local attempts after clean setup. Cloud-aware mode shows current station
  IAM credentials do not yet have access to the future `students/.../attempts/`
  prefixes, so the next AWS step is a narrow student-sync read/write policy.
- Added a manual upload-only mode to `scripts/student_attempt_sync.py`. It
  uploads immutable attempt objects only after a clean cloud check, refuses to
  run when cloud access errors or local ID conflicts are present, and does not
  download, merge, rebuild, or overwrite student progress.
- Added `scripts/rollout_release.py` so Pappy can promote a tested release to
  `release/pi` and then trigger all reachable grandkid stations to run their
  installed hardened updater immediately. Offline stations still catch up from
  the automatic timer when they are powered on.
- Live-tested the rollout helper against both grandkid stations. Each station
  ran its installed updater, created/uploaded a pre-update backup, confirmed it
  was current at `1890ee9`, uploaded fresh status/progress snapshots, and kept
  the app service active.
- Added `scripts/apply_station_sync_policies.py`, a repeatable AWS IAM helper
  for the next progress-sync permission step. It applies one narrow inline
  policy per existing station user so stations can read the three family
  progress snapshots and read/write immutable attempt objects only for their
  rostered students. Dry-run and unit tests pass; actual AWS application is
  pending because this Codex task cannot see the laptop's `aws` CLI/profile.
- Applied the narrow station sync IAM policies using the default AWS admin
  profile after confirming the setup profile lacked `iam:PutUserPolicy`.
  Verification on all three Pis now shows family progress can read `3/3`
  station snapshots and student attempt sync dry-run reports `Cloud errors: 0`
  and `Conflicts: 0`. Pappy has 216 local attempts ready for upload; the two
  grandkid stations are clean at `Would upload: 0`.
- Fixed the attempt-sync dry-run boundary so each station checks only its
  configured local student roster, not every family profile cached on that Pi.
- Started full student progress sync with a manual `--sync` path. The sync
  uploads local attempts, downloads the cloud attempt union for the station
  roster, backs up attempt/progress files, rewrites merged logs, rebuilds
  `practice_progress.json`, and refuses to apply changes when cloud errors or
  conflicts exist.
- First real full-sync test completed on Pappy's station. The initial bulk
  upload moved 216 Pappy attempts to S3, then the batched download/rebuild pass
  read 216 cloud attempts, found zero conflicts, wrote a local backup at
  `data/sync_backups/20260804-160949`, rebuilt practice progress, and left
  `Would upload: 0`.
- Lesson from the first sync: one-object-per-attempt upload is acceptable for
  small daily deltas but slow for a first bulk load; download is now batched by
  student prefix. Before enabling a timer, add an idle/race guard so sync does
  not rewrite logs while a student is actively practicing.
- Added the automatic-sync safety layer: the app writes
  `data/app_activity.json`, guarded sync skips recent app activity unless
  `--force` is used, a lock prevents overlapping runs, and
  `data/sync_reports/latest_sync_status.json` records completed/skipped/error
  results.
- Added optional `morse-station-sync.service` and `morse-station-sync.timer`
  files for a future 30-minute guarded sync cadence. Do not enable broadly until
  the guard has been tested on real stations while students are using the app.
- Adjusted Learn mode for new-letter burn-in based on testing feedback: when
  new letters such as `S O` are in Learning Now, Learn prompts now mix review
  letters with the new group instead of showing almost only the new letters.
  The first implementation uses a 40% Learning Now / 60% current-set review
  prompt split while the completion gate still measures the new letters.
- Updated the route regression test to match the new Learn-mode mix so the Pi
  release gate verifies both behaviors: review letters can appear, and the
  current Learning Now letters remain the measured focus.
- Rolled the Learn-mode 40/60 review mix to the two Git-backed grandkid
  stations on `release/pi`; both stations passed the full Pi-side route suite
  and restarted with active services.
- Copied the same app/test updates to Pappy's file-deployed station; focused
  Pi-side route and learning-gate tests passed and the app service is active.
- Close-of-day GitHub status: Learn-mode review mix, tests, and documentation
  are committed and pushed to both `main` and `release/pi`.
- Close-of-day station status: Pappy, Astrid/Liara, and Campbell/Olivea are all
  updated with the Learn-mode mix and have active app services.

### 2026-08-05

- Cleaned up the live decoded readout across desktop keyer, touch keyer,
  Practice, Echo, Learn, Send, Sprint, Words, and message compose screens.
  Empty input now leaves the decoded box blank instead of showing `---`, which
  could be mistaken for the Morse pattern for `O`.
- Unknown keyed patterns still show `?` after input so students get feedback
  without confusing idle state with a real Morse character.
- Added a regression test to prevent `liveDecoded` placeholders from returning
  to dash-like Morse text in templates or shared JavaScript.
- Added Pappy as an adult/test operator on the two grandkid station rosters so
  Pappy can practice on any unit and verify cross-station progress sync.
- Updated the narrow AWS student-attempt sync policies so Astrid/Liara and
  Campbell/Olivea stations can read/write Pappy attempt records in addition to
  their household students.
- Seeded Pappy's current 320 cloud attempts onto both grandkid stations with a
  forced initial sync; both rebuilt Pappy progress locally without conflicts.
- Identified the first cross-station sync gap from hands-on testing: attempts
  and `practice_progress.json` synced, but `learning_state.json` did not, so a
  grandkid station could show Pappy ready to start `S O` again and keep Words
  locked even after Pappy had completed S/O elsewhere.
- Updated full progress sync to rebuild conservative learning-state records
  from merged Learn attempts. This keeps Daily, Learning Now, active letters,
  and Words unlocks aligned across stations without copying another station's
  learning file directly.
- Started the Words Rhythm Coach slice. `/words/result` now returns a target vs
  keyed rhythm comparison, the touch Words screen renders visible symbol,
  letter-pause, and word-pause markers after an attempt, and the first feedback
  message calls out spacing mistakes such as a letter pause that was long
  enough to sound like a word break.
- Added bounded shutdown sync to the touch `Power Off` flow. When a student
  powers off the station, the app creates/uploads a shutdown backup, publishes a
  fresh progress snapshot, publishes station status, records
  `data/sync_reports/latest_shutdown_sync.json`, and then powers off.
- Decision: shutdown sync should be a best-effort save of recent progress, not
  a full two-way per-attempt merge. Full attempt sync remains on the
  timer/manual path so kid-facing shutdown stays reasonably quick.
- Enabled the guarded 30-minute student-attempt sync timer on all three
  stations so stations can eventually merge practice history while powered on.
- Found and fixed a timer-sync inefficiency: `student_attempt_sync.py --sync`
  no longer runs the slower dry-run cloud scan before checking the idle guard.
  This lets active stations skip quickly instead of doing cloud work while a
  student is practicing.
- Tuned Pi station playback for Words and prompts by adding a short silent
  pre-roll before generated USB-speaker audio and delaying the LED by the same
  amount. This gives the USB speaker/ALSA path time to start cleanly so the
  first Morse symbol is less likely to be clipped.
- After testing showed manual Words Play sounded correct but first-entry
  autoplay could miss the first symbol, increased the Words autoplay startup
  delay so the page and station audio path settle before the initial prompt.
- Added a neutral `Get ready...` feedback message during the Words autoplay
  startup delay so the pause feels intentional before the station plays.
- Decision: Words practice is now part of the core Daily Mission path once
  unlocked, not just a side activity. After a student completes the 20
  signal-practice attempts, Daily now asks for 3 correct Words attempts before
  treating the mission as complete.
- Implemented the Daily Words decision in the app, touch Daily screen, specs,
  and regression tests. The Daily screen now points to Words after the 20 signal
  attempts are done when Words are unlocked but today's 3-correct-Words finish
  is incomplete.
- Deployed the Daily Words update to all three stations. The two Git-backed
  grandkid stations updated from `release/pi` to `49727f6`, restarted
  successfully, and each passed the 181-test Pi regression suite. Pappy's
  file-deployed station received the same changed files, restarted, and passed
  the focused 112-test Pi suite.
- Verified cross-station Pappy word progress after manual forced sync. The
  first pass showed normal timing lag because Astrid/Liara uploaded newer Pappy
  attempts after Pappy and Campbell/Olivea had already pulled. A second forced
  pull on Pappy and Campbell/Olivea aligned all three stations at
  `pappy:words = 90`.
- Decision: message delivery remains designed as eventual delivery. Messages
  should wait in cloud storage while a station is powered off and be delivered
  when the receiving station comes online and syncs, assuming AWS credentials,
  internet access, and the sync worker are healthy.
- Added a PIN-gated `Sync Now` action to the touch System page. It starts the
  existing guarded `morse-station-sync.service` so an adult can request progress
  sync locally without SSH before or after the stations leave the house.
- Reviewed the external `morsePi_review.md` recommendations. Accepted the CI
  coverage finding as immediate work: GitHub Actions and README now use
  `python -m unittest discover -s tests` so sync, family progress, rollout,
  admin PIN helper, and rhythm-coach tests run with the rest of the suite.
- Review triage: the "ladder stops at 12 letters" finding is stale because the
  current unlock ladder covers A-Z and 0-9; the monolithic `app.py`,
  global-path pattern, admin PIN lockout, data-path anchoring, app-activity
  write throttling, single Morse table, and release tagging remain valid future
  hardening items.
- Hardened configured admin PIN checks before weekend delivery: comparisons now
  use `hmac.compare_digest`, and 5 wrong PIN attempts within 15 minutes trigger
  a short 60-second in-memory lockout for adult actions.
- Anchored default data paths to the application directory through `paths.py`,
  with optional `MORSE_DATA_DIR` override for advanced deployments. This removes
  the fragile assumption that the app and maintenance scripts are always started
  from `/home/morse/morse-station`.
- Added a reversible morsePi boot splash installer and 800x480 splash image.
  Installed it on all three stations; Pappy reboot-tested it and confirmed the
  splash looks good.
- Recovered and clarified Pappy progress after the first reboot/sync confusion.
  Raw `S O` practice and Words attempts were present on all three stations, but
  sync/app-derived learning state was relocking Words after later O Learn
  mistakes lowered current strength.
- Fixed the sync rebuild rule so a learning group stays earned once historical
  attempts crossed the gate. Current strength can still dip for coaching, but
  unlock history does not fall backward.
- Fixed the app-side active-letter rule so Daily/Progress keep earlier earned
  groups active when a later learning group exists. Verified live: Pappy shows
  `R K` as Learning Now, `8/26` letters mastered, and Words unlocked with
  `22/42 words` and `69/98 correct`.
- Replaced the Words correct-answer flashing effect with a steady green success
  wash for the same feedback duration, and added a steady amber needs-work wash
  when the keyed word is not correct.
- Added a prominent title-bar result for every touch practice activity so a
  student immediately sees bold `Correct!` or `Try Again` while the detailed
  coaching message, timing, scoring, audio, and LED behavior remain unchanged.
- Fixed the Admin System Last Sync fallback discovered by the full Pi test bank
  so partial status records render as `Scheduled` and `Idle` instead of raising
  a template error.
- Aligned the Admin System regression expectation with its child-friendly sync
  wording and restored Pappy's missing rollout-release test module so all three
  stations run the same complete test bank.
- Completed a forced two-pass family progress sync before station testing.
  Pappy's shared totals match on all three units at 515 practice attempts and
  145 Words attempts; all family views report 3/3 stations available.
- Ran the complete Pi regression bank on every unit after sync. Pappy,
  Astrid/Liara, and Campbell/Olivea each pass all 201 tests. The run also
  corrected Pappy manual-install drift in the test bank, rollout helper, and
  station sync-policy helper without changing student data.
- Replaced the fixed Words restart with an adaptive five-step rotation: three
  unfinished words followed by two completed reviews. New visits begin with an
  unfinished word, lower-accuracy reviews come first, missed words return in a
  later cycle, and progress now explicitly says `words complete`.
- Changed the student-facing Words percentage from lifetime accuracy to
  distinct-word completion. A student who finishes all 42 available words now
  earns an attainable 100%; lifetime accuracy and correct/attempt totals remain
  stored for adult rhythm and progress analysis but are hidden on kid screens.
- Deployed the day's release to Pappy (`10.10.10.141`), Astrid/Liara
  (`10.10.10.129`), and Campbell/Olivea (`10.10.10.157`). App services are
  active on all three.
- GitHub status: pushed `main` and `release/pi` through `179aaa6` with splash,
  sync, app-gate, and Words feedback changes.

### Ready Next

- Let Pappy run normal practice tomorrow and watch both current learning loops:
  the Learn-mode 40/60 mix should keep review letters in rotation, and Daily
  should ask for 3 correct Words after the 20 signal attempts once Words is
  unlocked.
- Test shutdown sync on Pappy after a small practice session. Confirm the
  station writes `data/sync_reports/latest_shutdown_sync.json`, uploads the
  latest attempts/snapshot, and powers off cleanly.
- Watch the enabled 30-minute progress-sync timer on all three stations. Confirm
  it skips quickly during recent use, completes after idle time, and writes a
  clear `data/sync_reports/latest_sync_status.json`.
- Test the new touch System `Sync Now` action on all three stations: confirm the
  PIN gate, service start, and `latest_sync_status.json` result.
- Run the full discovered test suite on a Pi after the CI discovery change and
  confirm all 15 test modules pass before treating the next release as ready.
- Before weekend delivery, prioritize remaining small hardening only:
  app-activity write throttling. Defer the app factory/blueprint/global-path
  refactor until after the stations are delivered and stable.
- Run one kid-style smoke test on each grandkid unit before it leaves home:
  choose each student, complete one Daily/Learn/Send action with the physical
  keyer, verify progress sticks after switching users, then run a final
  backup/status/snapshot cycle.
- Decide the away-from-home command trigger after the stations leave Pappy's
  LAN. Preferred low-cost path remains AWS IoT triggering the same local updater;
  Systems Manager remains the fuller remote-admin option if we accept the device
  cost.
- Kid-test the complete local message flow on Pappy's station: choose a
  recipient, build and correct a short message, review/play/send it, switch
  users, and decode it with and without hints.
- Let Pappy and Astrid progress naturally through `S` and `O`, which unlocks the
  Messages UI, then send the first live S3 message and verify its decoded receipt.
- After the first online delivery passes, test delayed delivery with the
  receiving Pi powered off and confirm exactly one message after it returns.
- For future IoT work, prefer a narrow IoT setup identity; reactivate the broad
  `admin` access key only if truly needed, then deactivate it again after the
  task.
- Plan the longer-term removal of path-global progress/attempt storage before
  enabling a multi-worker production server.
- Decide whether to enable any automatic update timer on deployed stations, or keep updates as adult-triggered `Update App` only until the stations have been used at the grandkids' homes.
- Prepare the future remote command path after the first home deployment: AWS IoT preferred for lower-cost commands; Systems Manager remains the practical fallback if remote shell access becomes necessary.
- Keep testing Words/Daily with Astrid/Liara/Pappy/Campbell/Olivea, especially
  the new 3-correct-Words Daily finish, auto-advance, progress clarity, and
  whether the goal feels motivating without dragging the session too long.
- Measure the 7-inch display/Pi stack with [CASE_MEASUREMENT_WORKSHEET.md](CASE_MEASUREMENT_WORKSHEET.md), then design a Bambu X1 Carbon test-fit plate.
- Confirm the steady green/amber Words feedback feels good during hands-on
  practice and decide whether the same no-flash pattern should be applied to all
  practice modes.
- Words now opens silently by default from Daily, Progress, Practice menu, and
  Next; students press Play only when they want to hear the word.
- Reviewed the touch Admin System screen after seeing confusing sync status.
  Live station files showed recent guarded sync skips due to app activity, which
  is normal, but the UI exposed systemd-style `inactive`/`unknown` wording. The
  System page now labels one-shot jobs as `Idle`, timers as `Scheduled`, shows
  `Last Sync` first, and falls back to the detailed attempt-sync report when the
  compact sync status file is missing.
- Renamed the screen from Adult System to Admin System and tightened the 800x480
  status grid to prevent long service, backup, and network text from bleeding
  into neighboring cards.
- Reworded unreported Wi-Fi signal values as `Signal not reported` so the
  Admin System screen does not show `Unknown` for a connected network.
