# 04 — Functional Requirements

Tier tags: *(MVP)*, *(V1)*, *(V2)*. *(Delta: …)* marks intentional differences
from the current code (legacy status per requirement is tracked in
[STATUS.md](STATUS.md)). Verification lives in
[10-acceptance-criteria.md](10-acceptance-criteria.md).

## Morse engine

- **FR-001** *(MVP)* The system SHALL convert text to Morse for A–Z, 0–9, and
  `. , ? !` using the ITU table currently in `morse.py`; unsupported
  characters are silently dropped; letters within a word are separated by a
  single space and words by ` / `.
- **FR-002** *(MVP)* The system SHALL decode Morse to text using the same
  table, rendering unknown symbol groups as `?`.
- **FR-003** *(MVP)* Timing SHALL be Farnsworth-style: element dot length =
  `1.2 / character_wpm` seconds; inter-letter gap = 3 × (`1.2 /
  effective_wpm`); inter-word gap = 7 × (`1.2 / effective_wpm`); dash = 3
  dots; intra-letter gap = 1 dot.
- **FR-004** *(MVP)* Timing settings SHALL be clamped: `character_wpm` ∈
  [5, 35] (default 12), `effective_wpm` ∈ [3, character_wpm] (default 6),
  `tone_hz` ∈ [400, 1000] (default 700). Settings persist across restarts.

## Key input

- **FR-005** *(MVP)* A key press/release on the configured GPIO input (default
  GPIO17, pull-up, 30 ms debounce) SHALL be classified as a dot if held
  < 2.5 dot-units, else a dash.
- **FR-006** *(MVP)* A release gap ≥ 0.80 s SHALL end the current letter; a
  gap ≥ 1.50 s SHALL insert a word break.
- **FR-007** *(MVP)* While the key is held, the station SHALL emit a
  continuous sidetone at the configured `tone_hz` and light the LED; both
  stop on release.
- **FR-008** *(MVP)* The browser SHALL poll (or subscribe to) the current
  keyed Morse and its live decode, and SHALL be able to clear the key buffer.
- **FR-009** *(MVP)* The spacebar SHALL act as a keyer in the browser with
  identical classification rules, for hardware-free practice.

## Playback

- **FR-010** *(MVP)* The station SHALL play any valid Morse string through the
  USB speaker and LED simultaneously using current timing settings; playback
  SHALL be stoppable mid-stream.
- **FR-011** *(MVP)* Station volume SHALL be adjustable 0–100% (default 35%),
  persist across app restarts, and require admin authorization to change.
  The 7-inch touch UI SHALL expose parent-friendly presets for Mute, Quiet,
  Normal, and Loud without requiring a physical keyboard. If the PIN is
  missing or invalid, volume and timing controls SHALL leave settings
  unchanged and return to the touch Timing screen with a visible instruction;
  they SHALL NOT strand the kiosk on a plain browser error page.
- **FR-012** *(MVP)* Playback input length SHALL be capped: message text
  ≤ 160 characters, Morse ≤ 600 characters after normalization, request body
  ≤ 16 KB (limits adopted from the legacy hardening at `7818254`). Over-limit
  requests SHALL be rejected with a clear error, not truncated silently.
  *(Delta: legacy caps these values but silently truncates; only the 16 KB
  body limit rejects with 413. See AC-002.)*

## Practice

- **FR-013** *(MVP)* Send practice: the system presents a target letter; the
  student keys it; the attempt is correct iff the normalized keyed Morse
  equals the expected Morse. Correctness SHALL be decided server-side.
- **FR-014** *(MVP)* Listen practice: the system plays a letter; the student
  picks from multiple choice; correctness decided server-side; answers
  normalized to one uppercase character.
- **FR-015** *(MVP)* Target selection SHALL be weighted toward weak letters
  (low strength/accuracy) rather than uniform random.
- **FR-016** *(V1)* Read practice: show Morse, student identifies the letter.
  Echo practice: play Morse, student keys it back. Learn mode: guided
  introduce-then-reinforce flow for new letters.
- **FR-017** *(MVP)* Every attempt SHALL be recorded with: mode, target,
  expected/actual Morse or answer, correctness, timing settings in effect,
  key timing events, station id, session id, student id, UTC timestamp.
- **FR-018** *(V1)* Attempts on letters outside the student's active set SHALL
  be recorded as ignored and not affect progress.

## Curriculum & progression *(V1)*

- **FR-019** New letters unlock in fixed groups in this order:
  (E,T,A,N,I,M start) → S,O → R,K → D,U → C,W,H,L → P,F,Y,G → B,V,J,X → Q,Z →
  1–5 → 6–0, each gated at 100% of the prior group's mastery threshold.
- **FR-020** A newly introduced letter SHALL require, before counting toward
  the next unlock: ≥ 10 Learn attempts, strength ≥ 70, a rest period ≥ 3 h,
  and (once words unlock) ≥ 5 correct word attempts.
- **FR-021** At most 2 new letter groups SHALL be introduced per calendar day.
- **FR-022** The unlock table SHALL exist in exactly one module consumed by
  all features. *(Delta: `7818254` unified the table within `app.py`
  (`letter_unlock_groups` now generates steps and the letter list), but a
  second table `LETTER_UNLOCKS` still lives in `practice_progress.py`.)*
- **FR-051** Once Words unlocks, its opening sequence SHALL mix familiar
  two-letter and three-letter words instead of exhausting all two-letter words
  first. The first six prompts SHALL include at least two three-letter words,
  while every prompt remains limited to the student's active letters.

## Students & sessions *(V1)*

- **FR-023** The station SHALL support multiple named student profiles with
  fully isolated progress, learning state, and attempt logs; active student
  selected via cookie (1-year lifetime); student IDs are slugs `[a-z0-9-]`.
- **FR-024** A station config MAY define a fixed roster; when set, only
  rostered students are selectable and self-serve student creation is
  disabled unless explicitly enabled. The touch Admin System SHALL provide a
  PIN-protected Manage Operators page where an adult can toggle local operators
  from the configured `family_students` directory without a keyboard. Saving
  SHALL preserve unrelated station settings and all student data, SHALL keep
  the disposable Guest behavior unchanged, and SHALL reject an empty named
  roster.
- **FR-025** A guest profile MAY be enabled; guest attempts are flagged
  disposable and excluded from messaging features.
- **FR-026** Each browser session SHALL carry a 32-hex session ID cookie
  (12 h lifetime) attached to every attempt record, enabling later
  reattribution.
- **FR-027** *(V2)* An admin SHALL be able to move all attempts of a session
  to another student or discard them, with a pre-operation backup.
- **FR-028** *(V2)* Resetting a student SHALL back up all their files to a
  timestamped directory before deletion. This SHALL include local and cached
  cloud learning summaries so a reset student cannot regain old active letters
  from message eligibility data.

## Missions & motivation

- **FR-029** *(V1)* Daily Mission: 20 attempts in a day completes the
  signal-practice portion of the mission. Once Words is unlocked, Daily Mission
  SHALL also require at least 3 correct Words attempts that day before the
  mission is considered complete. Completion triggers a one-time celebration
  (station plays `...-` and flashes LED) only when actually complete. The
  recommended Next Step action SHALL use a full-width touch target with its
  label centered.
- **FR-030** *(V2)* Bonus sprint: after mission completion, an optional
  20-target random round over active letters with accuracy and streak
  scoring, tracked per sprint-session ID.
- **FR-031** *(V1)* Adaptive slowdown: in Listen/Echo, if mode attempts < 10
  or accuracy < 70% (overall or for the target letter), reduce character WPM
  by 2 (floor 8) and effective WPM by 1 (floor 4), and tell the student why.
- **FR-032** *(V2)* Badges and coach recommendations SHALL be pure functions
  of stored attempt/progress data (derivable, never separately stored).

## Operations

- **FR-033** *(MVP)* A backup command SHALL zip profiles, timing settings, and
  all student data with a manifest (format id, station id, UTC created time,
  file list), keep the newest N archives (default 30), and support restore
  into a target directory.
- **FR-034** *(V2)* When configured, backups and a status document SHALL
  upload to `s3://<bucket>/stations/<station-id>/{backups,status,snapshots}/`.
- **FR-035** *(V2)* The auto-updater SHALL: pull only from the dedicated
  release branch (`release/pi`); refuse to update if the working tree is
  dirty; only fast-forward; run the test suite (not merely `py_compile`)
  before restart; restart the service; verify a post-restart health check;
  report status; and roll back to the previous commit if the health check
  fails. *(Delta: legacy now backs up first, tests before restart, rolls back
  on test/health failure, and refreshes status/snapshots; signed releases
  remain open.)*
- **FR-058** *(V2)* A deployed station MAY poll AWS IoT Jobs for adult-issued
  remote maintenance jobs while powered on. The first supported job action
  SHALL be `update-app`, which starts the existing local update service
  described by FR-035. Additional allowed actions MAY include `sync-progress`,
  `backup-data`, `write-status`, and `restart-app`; the worker SHALL reject any
  unknown action without running it. Jobs SHALL be durable while a station is
  offline, idempotent by AWS job id, and SHALL record a local status file with
  the latest job id, action, result, timestamps, and non-secret error summary.
  The remote worker SHALL never execute arbitrary shell text from AWS.
- **FR-038** *(V1)* The 7-inch touch UI SHALL provide an adult System page
  reachable without a keyboard. It SHALL show Wi-Fi/network status useful for
  troubleshooting, and SHALL provide admin-PIN-gated actions to restart Wi-Fi
  and exit the kiosk browser to the Raspberry Pi desktop. It SHALL also show
  whether an on-screen keyboard tool is installed and provide an admin-PIN-gated
  action to open it. When the local update service is installed, it SHALL
  provide an admin-PIN-gated action to start the station update wrapper. When
  the local student-attempt sync service is installed, it SHALL provide an
  admin-PIN-gated action to request a progress sync. It SHALL also show the
  current app version/branch, update timer/result, latest student sync status,
  and latest local backup age/name. A manual Sync Now request SHALL return a
  visible completed/skipped/finished outcome when the local service returns.
  These controls SHALL be
  available locally on the touchscreen even if internet access is down, though
  updating and syncing may require internet access. Touch admin PIN
  entry SHALL be possible without a physical keyboard and SHALL NOT trigger the
  speaker, LED, Morse playback, or keyer feedback. A local maintenance helper
  SHALL allow an adult to set or reset the station admin PIN without
  hand-editing JSON, creating a backup before changing the station config. The
  student-facing touch menu SHALL also provide a non-PIN shutdown flow with a
  confirmation screen and a clear instruction to wait until the display goes
  dark before using the station power switch.

## Rhythm analysis *(V2 — added retroactively; shipped in legacy `674fdd8`)*

- **FR-036** Every keyed attempt (practice, word, bonus) SHALL store a rhythm
  summary derived from its timing events: dot/dash counts and averages, gap
  averages by type (symbol/letter/word), dot and dash consistency scores,
  dash-to-dot and letter-gap ratios with 0–100 ratio scores, an overall
  rhythm score (mean of available sub-scores), and one primary feedback
  sentence. Timing events per attempt SHALL be capped at 240.
- **FR-037** An admin rhythm view SHALL show, per student: rhythm-scored
  attempt counts by source, recent averages of the FR-036 metrics, a trend
  delta comparing early vs. recent windows (≥ 4 scored attempts required;
  labels: "Improving +N" at ≥ +5, "Watch trend −N" at ≤ −5, else "Steady",
  "Need more data" below threshold), and the most recent attempts. This view
  SHALL be admin-PIN-protected. *(Delta: legacy `/admin/rhythm` is
  unauthenticated.)*

## Family Morse messages *(V2)*

- **FR-039** Messaging SHALL unlock for a non-guest student when Words
  practice is unlocked. A message SHALL contain only uppercase A-Z letters
  and single spaces, use at most 3 words and 20 letters, and use only letters
  that have graduated into the active sets of both sender and receiver.
- **FR-040** The sender SHALL choose a receiver from a preconfigured family
  directory. Messages SHALL be addressed to a stable `student_uuid`, with the
  current `student_id` retained as a compatible storage alias, not to one
  station, so the receiver may open the same inbox from any approved family
  station where that student is rostered.

- **FR-041** The 800x480 composer SHALL work without a keyboard. It SHALL
  support (a) touch word tiles filtered to the allowable letters and (b)
  physical-key entry that captures and decodes one complete word from the
  student's available Words practice set before adding it to the draft. Word
  boundaries SHALL be inserted automatically. It SHALL provide touch controls
  to retry the currently keyed word without changing the draft, undo the last
  completed word, and clear the complete message as distinct actions.
  Letter-at-a-time construction SHALL NOT be the primary message-keying flow.
- **FR-042** A draft SHALL render as ordered letter tiles showing the plain
  letter with its Morse code directly underneath. Selecting a tile SHALL let
  the sender re-key it, replace it from the allowable-letter picker, or delete
  it. The sender SHALL be able to play the complete draft through the speaker
  and LED before sending.
- **FR-043** Sending SHALL require a separate review screen that shows the
  receiver, complete text, letter-by-letter Morse, and a Play action. The
  message SHALL remain editable until an explicit receiver-named Send action;
  a sent message is immutable.
- **FR-044** The receiver inbox SHALL show sender, received time, and state
  without revealing unopened message text. Opening a message SHALL first show
  blank letter slots grouped into words and provide whole-message playback
  through the speaker and LED.
- **FR-045** Guided decoding SHALL advance one letter at a time. It SHALL offer
  four large touch choices drawn from the receiver's active letters and these
  progressive aids: replay letter, replay word, slower speaker/LED playback,
  show Morse, then reveal letter. Every playback SHALL synchronize speaker and
  LED per FR-010. Correct choices fill their slot; the full word remains hidden
  until its letters are completed or revealed.
- **FR-046** Completing a message SHALL preserve the decoded text, celebrate
  once, and offer Play Again. A later version MAY add a Key It Back activity.
  Message work SHALL count toward effort time and message badges but SHALL NOT
  change core letter mastery until student testing supports a later spec change.
- **FR-047** Each message SHALL have durable states for `queued`, `available`,
  `opened`, and `decoded`. State transitions SHALL be idempotent and SHALL sync
  across approved stations so a message decoded at Pappy's station does not
  remain falsely unread at the receiver's home station.
- **FR-048** The canonical message content SHALL be normalized plain text;
  Morse SHALL be recomputed with FR-001 rather than trusted from a client or
  cloud payload. Duplicate delivery of the same message ID SHALL create no
  duplicate inbox item, celebration, or effort credit.
- **FR-049** Local messaging SHALL function without AWS for UI and learning
  tests. When family delivery is enabled, S3 SHALL hold the durable outbox,
  inbox, and receipts so stations may remain powered off for days; AWS IoT MAY
  provide arrival notifications but SHALL NOT be the only message copy.
- **FR-050** A failed or unavailable internet connection SHALL leave the sent
  message visibly queued on the sender station and retry later without child
  intervention. A child-friendly status SHALL distinguish Queued from Sent;
  technical failure details belong only in logs/admin status.
- **FR-052** A station sync worker SHALL publish local learning snapshots and
  immutable outbox records, download only inbox/status records addressed to
  locally rostered students or the local station, and upload opened/decoded
  receipts. It SHALL run safely after boot, on a ten-minute timer, and on
  adult demand; repeated runs SHALL be idempotent.
- **FR-053** A cloud router SHALL independently validate outbox and receipt
  records against the family directory and current minimal learning summaries
  before writing inbox or status copies to approved station prefixes.
- **FR-054** Cross-station student progress sync SHALL preserve practice from
  every approved station by uploading and merging immutable attempt records.
  It SHALL not use newest-snapshot-wins for writes, SHALL not overwrite a
  student's derived progress file from another station, and SHALL quarantine
  conflicting duplicate attempt IDs for adult review.
- **FR-055** The 800x480 touch practice screens SHALL show a prominent,
  text-based result in the existing title bar after each checked answer.
  Correct answers SHALL show `Correct!` in a bold success state; incorrect
  answers SHALL show `Try Again` in a distinct needs-work state. The detailed
  feedback message SHALL remain available in the practice content, and the
  title-bar result SHALL not change scoring, playback, LED behavior, automatic
  advancement, or consume additional screen height.
- **FR-056** Once Words is unlocked, a new Words visit SHALL begin with an
  unfinished available word instead of always restarting at the first catalog
  word. Advancement SHALL use a repeating five-word learning cadence of three
  unfinished words followed by two completed review words. Missed words SHALL
  remain unfinished and return in later cycles; completed review words SHALL
  prioritize lower accuracy and fewer prior attempts. After every available
  word has been completed, all Words slots SHALL remain available for review.
  Student-facing Words percentage SHALL be distinct completed words divided by
  currently available words, making every available set capable of reaching
  100%. Progress wording SHALL identify the numerator as distinct words
  completed. Lifetime correct/attempt accuracy SHALL remain recorded and
  available to adult analysis but SHALL not be the primary student score. When
  a newly active letter group expands the available Words catalog, the newly
  available words SHALL start incomplete; for example, adding D and U after the
  prior 42-word set is complete SHALL show 42/56 words complete, not 100%, and
  adding C, W, H, and L after the prior 56-word set is complete SHALL show
  56/80 words complete, not 100%.

## Student identity

- **FR-057** Each named family student SHALL have one immutable RFC 4122 UUID
  shared by every approved station. Display names MAY change and legacy
  `student_id` slugs SHALL remain compatible storage/routing aliases. Guest is
  disposable and station-local and SHALL NOT receive a family UUID. Existing
  records without a UUID SHALL be mapped through the canonical family registry;
  records whose supplied UUID conflicts with their legacy ID SHALL be rejected.
  Canonical family legacy IDs SHALL be reserved: generic profile creation using
  the same display name SHALL receive a distinct suffixed ID and new UUID rather
  than assuming the existing family identity.
