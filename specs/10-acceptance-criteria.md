# 10 — Acceptance Criteria

Every FR needs at least one acceptance criterion; the ones below are the
load-bearing criteria the **current code would fail** (marked) plus the core
correctness checks. Each is encoded as an automated test per
[11-testing-strategy.md](11-testing-strategy.md) unless noted.

- **AC-001** (verifies NFR-004) With two browsers as two different students
  submitting practice results simultaneously (100 interleaved requests),
  every attempt lands in the correct student's file and both progress files
  validate. ***Mitigated today*** (`7818254` forces a single-threaded
  server, serializing requests); the criterion MUST pass against a
  **threaded** server in the rebuild, where the global-state root cause
  would otherwise regress.
- **AC-002** (FR-012 / SEC-004) `POST /api/play` with 10,000 dots returns
  413 in < 100 ms; process RSS unchanged. ***Partially fails today:*** the
  OOM was closed at `7818254` (Morse truncated to 600 chars, body > 16 KB
  → 413), but sub-16 KB oversize input is silently truncated instead of
  rejected.
- **AC-003** (SEC-001) A cross-origin form POST to `/api/students/reset` with
  valid fields but no CSRF token returns 403 and no data changes.
  ***Fails today.***
- **AC-004** (SEC-002 / SEC-003) With no PIN configured, admin endpoints
  return 403 and startup logs a warning; 5 wrong PINs lock admin for 15 min.
  ***Partially passes today:*** configured PINs use constant-time comparison and
  5 wrong PINs trigger a short in-memory lockout. Mandatory PIN, persistent
  logging, and the full 15-minute production lockout remain open.
- **AC-005** (SEC-005) `POST /api/play` with `next=https://evil.example`
  redirects to `/`. ***Passes as of `7818254`*** (all routes use
  `safe_next_url`, covered by legacy tests).
- **AC-006** (FR-003 / FR-004) For char WPM 12 / effective 6: dot = 100 ms,
  dash = 300 ms, letter gap = 600 ms, word gap = 1400 ms, all ±1 ms in
  generated audio and LED schedules.
- **AC-007** (FR-005 / FR-006) A synthetic key sequence (150 ms down, 80 ms
  up, 350 ms down, 900 ms up) decodes as `.-` then letter break.
- **AC-008** (FR-020 / FR-021) A simulated student who aces everything still
  cannot unlock a group before the 3 h rest elapses, nor a third group in
  one local-time day. During that Learning Now period, Progress uses the new
  letters' Learn progress as its primary percentage and labels the already
  mastered current set separately so `100%` does not imply the new letters are
  already in Send/Read/Listen/Echo.
- **AC-009** (NFR-006) Kill -9 during a progress save leaves either the old
  or new file readable — 1,000-iteration crash test.
- **AC-010** (DR-008) A copy of a real current `data/` tree loads without
  error; migrated progress matches pre-migration summaries exactly.
- **AC-011** (FR-029) `POST` celebrate at 19 attempts returns 409 and plays
  nothing; at 20 it plays `...-` exactly once even if double-clicked.
- **AC-035** (FR-059) Given a student with prior normal practice activity more
  than 3 calendar days ago and no completed warm-up today, Daily Mission
  recommends `Warm Up First` and links to `/touch/practice/run?mode=warmup`.
  The Practice menu also shows a manual `Warm Up` button with the same link.
  Warm-Up prompts show both the target letter and its Morse pattern for memory
  reinforcement while the student keys it. Ten warm-up attempts today clear the
  Daily recommendation. A correct Warm-Up keying records the result and rotates
  to another learned-letter prompt after a readable pause, but completing the
  warm-up goal does not redirect or stop the review. Posting a correct warm-up
  result records a `warmup` attempt with `review_only=true`, counts it toward
  effort history, and leaves `practice_progress.json` unchanged for the reviewed
  letter.
- **AC-012** (NFR-005) `pip install -e . && pytest` passes on
  Windows/macOS/Linux CI with no GPIO env vars.
- **AC-013** (FR-036) For a synthetic event stream (known dot/dash durations
  and gap types), the rhythm summary reports the expected per-type gap
  averages, consistency and ratio scores, and overall score; streams with
  missing letter gaps produce no spurious spacing score. ***Passes today***
  (`tests/test_practice_attempts.py`); the rebuild ports these tests.
- **AC-014** (FR-038) On an 800x480 touch station, `/touch/system` displays
  hostname, IP address, Wi-Fi connection, Wi-Fi tool availability, and
  on-screen keyboard availability without a physical keyboard. It provides a
  silent touch PIN pad for admin actions; entering the PIN updates only the form
  field/display and does not call speaker, LED, playback, or keyer controls. `POST
  /touch/system/action` rejects a bad admin PIN and does not run the requested
  action; with a valid PIN it starts the requested local recovery action,
  including opening the on-screen keyboard, starting the local update service,
  or starting the local student-attempt sync service, and returns/redirects
  without exposing secrets. The local admin PIN helper
  updates `data/station_config.json`, preserves unrelated config fields,
  creates a timestamped backup, rejects non-numeric PINs, and does not print the
  PIN. The touch menu exposes a `Power` action; `GET /touch/shutdown` renders a
  confirmation page, POST without confirmation returns to the menu, and POST
  with confirmation starts the shutdown worker. Before powering off, the worker
  SHALL make a bounded best-effort attempt to create/upload a shutdown backup,
  publish a fresh progress snapshot, and publish station status, then tell the
  student to wait for the screen to go dark before using the station power
  switch.
- **AC-015** (FR-039...FR-043 / NFR-013 / NFR-016) On an 800x480 fixture,
  an eligible student can choose a family recipient, add a filtered word, key
  another complete available word with natural letter pauses, see
  letter-over-Morse tiles grouped by word, open a scrollable Word Bank with all
  shared available words grouped by unlock set, append a selected word, replace
  an existing word from the Word Bank, move and remove word tiles, play the
  draft, return from Review to edit, and explicitly send it without a keyboard
  or scrolling on the core compose/review screens. Primary message actions have
  centered labels. Words practice links to the same Word Bank, and the bank
  marks words as new, tried, or done from the student's Words-practice attempt
  log. An incomplete, unknown, or unavailable keyed word is not added.
  Retrying a partially keyed word clears only the live key buffer and preserves
  every completed word already in the draft. Live decoded readouts remain blank
  until the student keys input, then show the decoded character or `?` for an
  unknown pattern; they do not use dash placeholders that resemble Morse code.
- **AC-024** (FR-037 / NFR-016) Words practice SHALL show a compact Rhythm
  Coach after a keyed attempt. The coach SHALL compare Target and Yours as
  stacked, full-width rows that fit longer early words such as `NOT` on the
  800x480 touch screen. It SHALL use visible symbol, letter-pause, and
  word-pause markers, and SHALL highlight a too-long letter pause as a
  word-break style issue with friendly feedback. When a keyed word is not
  correct, the student-facing feedback SHALL explicitly remind the student to
  clear the attempt before trying again. Opening a Words prompt and selecting
  Next SHALL leave playback under student control; Play SHALL sound the word
  on the station speaker and light the LED.
- **AC-016** (FR-044...FR-046) Opening a two-word fixture reveals no plaintext.
  Whole-message, word, and letter playback drive mock audio and LED together;
  correct four-choice answers fill only the selected slots; progressive hints
  reveal Morse before the letter; completing all slots records one decoded
  event and one celebration even after refresh or double-submit.
- **AC-017** (FR-039 / SEC-016...SEC-018) Guest access is rejected. Attempts
  to send to an unknown recipient, exceed 3 words or 20 letters, include
  punctuation, or use a letter outside either student's active set fail
  server-side without creating an outbox object, even when the browser payload
  falsely claims the letter is allowed.
- **AC-018** (FR-047...FR-050 / NFR-014 / NFR-015 / SEC-017) With cloud
  access disabled, Send
  returns queued within 1 second and survives restart. When cloud access is
  restored, one validated inbox item appears; the receiver can disconnect and
  finish decoding it offline; later synchronization updates the sender-visible
  state without duplicate events or effort credit. A station identity cannot
  read an inbox or write an outbox outside its configured IAM prefixes.
- **AC-019** (FR-040 / FR-047) A message addressed to Astrid and downloaded at
  Pappy's station appears for Astrid but not another local student. After she
  decodes it there, her home station synchronizes the decoded receipt and does
  not present it as a new unread message.
- **AC-020** (FR-048 / SEC-019 / SEC-020 / DR-011...DR-014) Replaying the
  same S3 event and inbox download ten times leaves exactly one immutable
  message, one inbox entry, and one event per state/station. A payload whose
  cached Morse disagrees with normalized text is rejected or recomputed and
  never played as authoritative. Validated cloud records use stable student
  IDs and contain no display name, practice history, or detailed progress.
- **AC-021** (NFR-017) A fixture containing `A`, `SOS`, and a two-word message
  retains canonical `. -`, `... --- ...`, and `/` values in data attributes
  and server comparisons while every kid-facing rendering uses centered dot
  and dash elements with accessible labels. At 800x480 the marks remain
  aligned, letter groups do not split internally, and the printable handout
  uses the same centered geometry. Practice feedback/instruction text describes
  the next action without embedding raw ASCII Morse strings such as `.-`; the
  visible prompt owns the Morse pattern display.
- **AC-022** (FR-051) With `E T A N I M S O` active, Words still exposes the
  complete 42-word set, starts with `AM`, and presents `NOT` and `MOM` within
  the first six prompts. Every available word contains only active letters.
- **AC-025** (FR-029) After Words unlocks, a student with 20 signal-practice
  attempts but fewer than 3 correct Words attempts today sees Daily Mission
  point to Words instead of Bonus Round. After 3 correct Words attempts today,
  the Words portion is complete and Daily may recommend sprint or targeted
  practice as usual.
- **AC-023** (FR-052 / FR-053 / DR-014...DR-016) A three-station fixture
  uploads one message, replays its outbox event ten times, and produces exactly
  one validated inbox copy at each station hosting the recipient. An opened
  then decoded receipt advances sender and receiver copies without regression;
  replaying either receipt creates no duplicate local message or effort event.
  A mismatched station path, unknown family ID, stale summary, altered required
  letters, or unavailable letter is rejected.
- **AC-026** (FR-055 / NFR-016) Learn, Send, Read, Listen, Echo, Words, and
  Bonus Sprint touch screens render one title-bar result region without
  increasing the 800x480 page height. A correct answer displays bold
  `Correct!`; a missed answer displays `Try Again`; the existing detailed
  feedback remains visible. Loading the next prompt clears the title-bar
  result, and all existing answer timing and advancement delays remain
  unchanged.
- **AC-027** (FR-056) Given completed and unfinished Words fixtures, opening
  `/touch/words` selects the first unfinished available word. Five successive
  advancement phases select three unfinished words and then two completed
  review words; the lowest-accuracy completed word is reviewed first. A missed
  word remains eligible in the next unfinished cycle. The Next URL preserves
  the phase, legacy index URLs remain valid, and the progress label reads
  `<unique>/<available> words complete`. When all words are complete, the same
  cadence safely falls back to review words without an empty prompt. A fixture
  that completes all available words after earlier misses displays 100% on the
  student Words and Progress screens while retaining its lower lifetime
  accuracy in the underlying summary data.
- **AC-028** (FR-011) On an 800x480 station with an admin PIN configured,
  submitting Mute or timing changes with a missing or invalid PIN leaves the
  saved setting unchanged, redirects back to `/touch/timing`, displays a clear
  PIN instruction, and keeps the touch Menu and Save Timing controls visible.
  Direct requests without a touch return target remain forbidden with HTTP 403.
- **AC-029** (FR-024 / API-026 / SEC-002) On an 800x480 station, Admin System
  links to Manage Operators. The page lists configured family students as
  touch checkboxes and provides a silent PIN keypad. A missing or invalid PIN,
  an empty selection, or an unknown submitted student changes nothing and
  returns clear feedback. A valid non-empty selection atomically replaces only
  `station_config.json`'s `students` list, creates a timestamped config backup,
  preserves all unrelated fields and student folders, and returns to the
  operator picker where only the selected names plus Guest are visible.
- **AC-030** (FR-057 / DR-020 / SEC-021) Migrating three legacy station
  fixtures assigns the same UUID to each named family student on every station,
  leaves Guest without a family UUID, preserves all folders and attempt records,
  and is byte-stable on a second run except for the first-run backup files. New
  attempts, snapshots, and messages include both UUID and legacy ID. UUID-less
  historical records still merge, while a supplied mismatched UUID is rejected.
  Generic creation of a canonical family display name produces a separate
  suffixed legacy ID and UUID and cannot write as that family student.
- **AC-031** (FR-058 / API-027 / SEC-022) With a fake AWS IoT Jobs adapter, a
  pending `update-app` job starts only `morse-station-update.service`, records
  local in-progress and succeeded status, and marks the AWS job succeeded. A
  job with an unknown action is marked failed, writes a local status summary,
  and runs no local command. Missing IoT configuration skips cleanly without
  failing the station.
- **AC-032** (NFR-019) The remote-maintenance design document and AWS setup
  reference include a cost note showing the expected three-station remote
  update cost under normal use and explicitly compare it to any fixed
  per-device remote-admin option before that option is enabled.
- **AC-033** (FR-056) Given a student with the starter, S/O, R/K, and D/U
  groups active and all prior 42 Words prompts completed, opening
  `/touch/words` and Progress SHALL display `75%` and `42/56 words complete`.
  A D/U-enabled word such as `AND` SHALL be available for practice, and newly
  available D/U words SHALL not inherit completion credit from the prior
  catalog.
- **AC-034** (FR-056) Given a student with the starter, S/O, R/K, D/U, and
  C/W/H/L groups active and all prior 56 Words prompts completed, opening
  `/touch/words` and Progress SHALL display `70%` and `56/80 words complete`.
  A C/W/H/L-enabled word such as `COW` SHALL be available for practice, and
  newly available C/W/H/L words SHALL not inherit completion credit from the
  prior catalog.
- **AC-036** (FR-061 / NFR-020) At 800x480, an active touch page shows no
  screensaver before 3 minutes and then shows a black full-screen overlay with
  one A-Z or 0-9 shared centered Morse visual with its character hidden. After
  each cycle begins, the character element is empty and immediately hidden;
  neither the prior nor next answer flashes. After 5 seconds, the matching
  character is populated and appears without moving or hiding the
  Morse. After 3 more seconds, a different pattern begins at a safe
  in-viewport position with its character hidden again. No phase makes sound
  or LED requests. The first touch dismisses and does not activate the covered
  control. A physical keyer press dismisses, clears that wake signal, and
  creates no scored attempt. Continued inactivity still invokes the existing
  10-minute `/touch` redirect. The operator picker may display the screensaver
  but does not redirect itself, and the shutdown page never starts it.
- **AC-037** (FR-062 / NFR-021) On a Pi graphical session, exactly one enabled
  `morse-station-browser.service` owns the Chromium kiosk and the legacy Labwc
  and XDG browser entries are absent. Killing Chromium unexpectedly causes the
  service to restore `/touch` in kiosk mode within 15 seconds while the app
  service remains active and student data is unchanged. Stopping Chromium
  through the PIN-gated `Exit Kiosk` action leaves the desktop visible without
  an automatic relaunch. Restarting the browser service restores the kiosk.
  Running the installer twice remains successful and still produces one
  browser. A completed app update restarts an active browser, and the generated
  station status reports both app and browser service states.
- **AC-038** (FR-063 / NFR-022 / DR-021 / API-028) At 800x480, Signal Drop
  offers Send and Read without scrolling. A student with six active letters and
  two Learning Now letters receives only the six active letters. Correct Send
  Morse and correct Read choices clear all matching visible targets and append
  bonus records. Incorrect Send input turns the lowest target red for visible
  `MISS` feedback while that target remains in play; a bottom miss turns red
  and then leaves. Both return the target to review without changing practice
  mastery or Daily counts. Repeated success speeds
  play within a bounded range, a miss slows it, and pause/leave work by touch.
- **AC-039** (FR-054) A student-attempt sync with a lock owned by a running
  process skips without changing data. A lock whose recorded process no longer
  exists, or whose age exceeds two hours, is removed and the sync completes;
  normal completion removes its own lock. This recovery preserves immutable
  attempt merge, conflict quarantine, and recent-activity safeguards.

## Coverage rule

Before a phase of the [roadmap](12-rebuild-roadmap.md) is declared done, each
requirement scoped to that phase must reference at least one passing AC or
test ID. New requirements added later must arrive with their AC in the same
change.
