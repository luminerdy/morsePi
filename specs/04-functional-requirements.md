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
- **FR-011** *(MVP)* Station volume SHALL be adjustable 0–100% (default 35%)
  and require admin authorization to change.
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

## Students & sessions *(V1)*

- **FR-023** The station SHALL support multiple named student profiles with
  fully isolated progress, learning state, and attempt logs; active student
  selected via cookie (1-year lifetime); student IDs are slugs `[a-z0-9-]`.
- **FR-024** A station config MAY define a fixed roster; when set, only
  rostered students are selectable and self-serve student creation is
  disabled unless explicitly enabled.
- **FR-025** A guest profile MAY be enabled; guest attempts are flagged
  disposable and excluded from messaging features.
- **FR-026** Each browser session SHALL carry a 32-hex session ID cookie
  (12 h lifetime) attached to every attempt record, enabling later
  reattribution.
- **FR-027** *(V2)* An admin SHALL be able to move all attempts of a session
  to another student or discard them, with a pre-operation backup.
- **FR-028** *(V2)* Resetting a student SHALL back up all their files to a
  timestamped directory before deletion.

## Missions & motivation

- **FR-029** *(V1)* Daily Mission: 20 attempts in a day completes the
  mission; completion triggers a one-time celebration (station plays `...-`
  and flashes LED) only when actually complete.
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
  fails. *(Delta: `5e835d3` added the `release/pi` branch and a 30 s HTTP
  health check; still missing: rollback on failure and pre-restart tests.)*
- **FR-038** *(V1)* The 7-inch touch UI SHALL provide an adult System page
  reachable without a keyboard. It SHALL show Wi-Fi/network status useful for
  troubleshooting, and SHALL provide admin-PIN-gated actions to restart Wi-Fi
  and exit the kiosk browser to the Raspberry Pi desktop. These controls SHALL
  be available locally on the touchscreen even if internet access is down.

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
