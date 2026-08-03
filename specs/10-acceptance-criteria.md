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
  ***Fails today.***
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
  one local-time day.
- **AC-009** (NFR-006) Kill -9 during a progress save leaves either the old
  or new file readable — 1,000-iteration crash test.
- **AC-010** (DR-008) A copy of a real current `data/` tree loads without
  error; migrated progress matches pre-migration summaries exactly.
- **AC-011** (FR-029) `POST` celebrate at 19 attempts returns 409 and plays
  nothing; at 20 it plays `...-` exactly once even if double-clicked.
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
  including opening the on-screen keyboard or starting the local update service,
  and returns/redirects without exposing secrets. The local admin PIN helper
  updates `data/station_config.json`, preserves unrelated config fields,
  creates a timestamped backup, rejects non-numeric PINs, and does not print the
  PIN. The touch menu exposes a `Power` action; `GET /touch/shutdown` renders a
  confirmation page, POST without confirmation returns to the menu, and POST
  with confirmation starts the shutdown worker and tells the student to wait for
  the screen to go dark before using the station power switch.
- **AC-015** (FR-039...FR-043 / NFR-013 / NFR-016) On an 800x480 fixture,
  an eligible student can choose a family recipient, add a filtered word, key
  another complete available word with natural letter pauses, see
  letter-over-Morse tiles grouped by word, replace and delete a tile, play the
  draft, return from Review to edit, and explicitly send it without a keyboard
  or page scrolling. Primary message actions have centered labels. An
  incomplete, unknown, or unavailable keyed word is not added.
  Retrying a partially keyed word clears only the live key buffer and preserves
  every completed word already in the draft.
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
  uses the same centered geometry.
- **AC-022** (FR-051) With `E T A N I M S O` active, Words still exposes the
  complete 42-word set, starts with `AM`, and presents `NOT` and `MOM` within
  the first six prompts. Every available word contains only active letters.
- **AC-023** (FR-052 / FR-053 / DR-014...DR-016) A three-station fixture
  uploads one message, replays its outbox event ten times, and produces exactly
  one validated inbox copy at each station hosting the recipient. An opened
  then decoded receipt advances sender and receiver copies without regression;
  replaying either receipt creates no duplicate local message or effort event.
  A mismatched station path, unknown family ID, stale summary, altered required
  letters, or unavailable letter is rejected.

## Coverage rule

Before a phase of the [roadmap](12-rebuild-roadmap.md) is declared done, each
requirement scoped to that phase must reference at least one passing AC or
test ID. New requirements added later must arrive with their AC in the same
change.
