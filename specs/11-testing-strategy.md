# 11 — Testing Strategy

- **TEST-001** Unit tests for the pure domain: `morse.py` round-trips,
  Farnsworth math (AC-006), dot/dash classification (AC-007), gate logic
  (AC-008), carryover and legacy curriculum-group timing normalization,
  strength formula, badge/coach derivations. Target ≥ 90% coverage
  of `learning/` — this is where the product lives.
- **TEST-002** Contract tests per API-* endpoint via Flask test client + mock
  hardware: happy path, validation rejection, auth rejection, oversize
  rejection. Every AC in
  [10-acceptance-criteria.md](10-acceptance-criteria.md) encoded as a test.
- **TEST-003** Concurrency test (AC-001) using a threaded test server — run
  in CI on every PR, not just locally.
- **TEST-004** Property-based tests (hypothesis) for `text→morse→text`
  (round-trips for the supported alphabet) and for Morse-input cleaners
  (never crash, output always within charset/length).
- **TEST-005** Crash-safety test for atomic writes (AC-009) and torn-JSONL
  tolerance.
- **TEST-006** Golden-data migration test: a fixture copy of a real
  anonymized `data/` tree (AC-010) checked into `tests/fixtures/`.
- **TEST-007** Hardware-in-the-loop smoke script (manual, on-Pi): key press →
  tone/LED, playback, volume — a one-command checklist runner replacing
  today's ad-hoc `hardware_tests/` scripts; results appended to the status
  document.
- **TEST-008** Security checks in CI: pip-audit, secret scan, and a small
  test asserting the dev server / debug mode cannot start from the packaged
  entry point.
- **TEST-009** *(V2)* Update-path test: container-based rehearsal that
  `update_station.sh` refuses dirty trees, refuses non-fast-forward, and
  rolls back on failed `/healthz`.
- **TEST-010** Performance guard: summary endpoints under a 10k-attempt
  fixture must stay < 500 ms (NFR-003) — asserted in CI with a generous 2×
  margin for runner noise.
- **TEST-011** *(V2)* Message-domain unit tests: normalization and limits,
  sender/receiver active-letter intersection, filtered word tiles, immutable
  records, complete keyed-word validation, state transitions, progressive
  hints, and duplicate-event credit.
- **TEST-012** *(V2)* Message route/template contract tests with mock key,
  audio, and LED backends cover AC-015...AC-017, including Guest denial,
  supported whole-word keying persistence and assistance gates, immutable
  reviewed text, and server-side rejection of forged eligibility or skipped
  keying.
- **TEST-013** *(V2)* Offline/sync integration tests use a fake S3/IoT adapter
  to cover AC-018...AC-020: queued restart recovery, delayed delivery,
  duplicate object events, cross-station receipts, stale learning summaries,
  and unauthorized-prefix rejection.
- **TEST-014** *(V2, manual + screenshot regression)* Run the complete compose,
  review, inbox, and decode flow at 800x480 with touch and the physical key.
  Assert no scrollbars or overlaps, minimum target sizes, visible identities,
  and synchronized speaker/LED playback before kid testing.
- **TEST-015** Morse display unit/template tests verify canonical ASCII input
  is unchanged, accessible labels name dots and dashes, generated markup uses
  only the shared centered-symbol classes, and representative Learn, Words,
  Progress, and Messages pages render that component. An 800x480 screenshot
  check and print-PDF inspection cover AC-021.
- **TEST-016** Words curriculum tests verify the unlocked bank retains all
  eligible words, filters out unknown letters, and interleaves two- and
  three-letter prompts so `NOT` and `MOM` appear in the first six.
- **TEST-017** Cloud-message contract tests use an in-memory S3 object store to
  replay snapshots, outbox objects, inbox downloads, and receipts across all
  three configured stations. They cover path/payload mismatches, family scope,
  active-letter enforcement, forward-only states, and duplicate delivery.
- **TEST-018** Student-identity tests validate canonical registry uniqueness,
  idempotent station/profile migration, preservation of legacy paths/history,
  UUID enrichment of new and historical records, stable rename behavior, Guest
  exclusion, and fail-closed handling of UUID/legacy-ID conflicts.
- **TEST-019** Remote-update tests use a fake AWS CLI/Jobs response layer to
  cover no-pending-job, missing configuration, accepted `update-app`, rejected
  unknown action, expected-commit verification, missing/blocked/rolled-back
  local reports, read-only diagnostics, local status writing, AWS job state
  updates, update-lock wiring, self-refreshing systemd unit wiring, fixed
  message-sync enablement with configuration rollback, and Admin System
  compatibility with older status payloads without contacting AWS.
- **TEST-020** Documentation review for remote operations verifies that any
  remote-maintenance design includes the NFR-019 cost guardrail, expected
  three-station normal-use cost, and a clear note before enabling a fixed
  monthly per-device service.
- **TEST-021** Touch idle tests verify the 3-minute screensaver, 5-second
  Morse-only recall phase, 3-second character reveal phase, A-Z/0-9 Morse
  mapping, wake-only touch/keyer handling, shutdown exclusion, and preservation
  of the 10-minute operator reset. A browser rehearsal at 800x480 uses
  shortened timers to verify the hidden/revealed character sequence, full
  coverage, immediate clearing with no transition flash, safe movement,
  readable centered marks, and that the first wake
  touch does not activate the control beneath it.
- **TEST-022** Browser-supervision contract tests verify the user unit restart
  policy, graphical/app readiness waits, absence of the old duplicate-process
  guard, idempotent installer wiring, update-path installation, intentional
  `Exit Kiosk` service stop, and browser state in station-status JSON. A live
  Pappy rehearsal kills Chromium, measures automatic recovery, confirms one
  kiosk process, exercises intentional exit and manual restoration, then
  reboot-checks the app and supervised browser together.
- **TEST-023** Signal Drop tests cover active-letter-only weighted selection,
  empty-pool fallback, Send and Read server validation, duplicate clear counts,
  bottom-miss records, unchanged mastery data, touch-menu entry, fixed-screen
  layout, persistent red keyed-miss feedback, bottom removal, adaptive speed
  bounds, pause/restart controls, and physical/spacebar keyer integration.
- **TEST-024** Student-attempt sync lock tests cover active-owner exclusion,
  abandoned-process recovery, maximum-age recovery, and lock cleanup after a
  successful merge.
- **TEST-025** Family activity tests cover schema/path validation, deterministic
  event IDs, offline pending retention, successful flush, replay idempotency,
  event-detail privacy allowlists, message/progress/update integration, partial
  cloud refresh with cache preservation, reader-only IAM policy generation,
  PIN-gated routes, immediate cached rendering, single-flight background
  refresh/status, client-side completion reload and filters, and an 800x480
  screenshot rehearsal.
- **TEST-026** Admin-session tests cover correct and incorrect unlocks, opaque
  cookie flags, route and action authorization, sliding activity renewal,
  timeout, explicit exit, student-flow relock, process-restart invalidation,
  no-PIN development behavior, and an 800x480 touch rehearsal across System,
  Activity, Operators, and Timing.

## CI pipeline (per TR-011)

On every PR and push to main:

1. `ruff check` + `ruff format --check`
2. `pytest` with coverage gate (≥ 80% on `learning/` and `morse.py`)
3. Concurrency test (TEST-003)
4. `pip-audit` + secret scan (TEST-008)
5. Performance guard (TEST-010)
6. Message unit/contract tests (TEST-011/012 when Phase 7 begins)
7. Message sync integration tests (TEST-013 when Phase 7B begins)

Matrix: Linux (primary), plus Windows/macOS import-and-unit smoke for AC-012.
