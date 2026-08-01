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
  on-screen keyboard availability without a physical keyboard. `POST
  /touch/system/action` rejects a bad admin PIN and does not run the requested
  action; with a valid PIN it starts the requested local recovery action,
  including opening the on-screen keyboard, and returns/redirects without
  exposing secrets.

## Coverage rule

Before a phase of the [roadmap](12-rebuild-roadmap.md) is declared done, each
requirement scoped to that phase must reference at least one passing AC or
test ID. New requirements added later must arrive with their AC in the same
change.
