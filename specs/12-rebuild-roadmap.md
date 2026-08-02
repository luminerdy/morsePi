# 12 — Rebuild Roadmap

Principles: each phase ships a working station; family data survives every
phase (DR-008); no big-bang cutover — old `app.py` keeps running on deployed
stations until Phase 3 exit.

## Phase 0 — Freeze & harvest (~½ day)

- Tag current main as `v0-legacy`.
- Copy a real `data/` tree as the migration fixture (anonymize names).
- Land this spec package as root `specs/` in the repo.

## Phase 1 — Skeleton + engine (MVP core)

- `pyproject.toml`, package layout (TR-002), app factory.
- Hardware interface with null/mock backends (TR-003).
- `morse.py` + timing module.
- CI green on all OSes with TEST-001.
- **Exit:** AC-006, AC-007, AC-012.

## Phase 2 — Secure web core

- Blueprints for message/playback/key/timing.
- CSRF, mandatory PIN + lockout, input caps, safe redirects
  (SEC-001…005, SEC-013).
- waitress + hardened systemd unit (SEC-006, SEC-007).
- **Exit:** AC-002, AC-003, AC-004, AC-005.

## Phase 3 — Practice + storage (MVP complete)

- `StudentStore` (TR-006), atomic persistence (NFR-006).
- Send/Listen modes, progress page, backup CLI (FR-033).
- **Exit:** AC-001, AC-009; **deployable to one station as the daily
  driver.**

## Phase 4 — Curriculum (V1)

- Single curriculum module (FR-022), unlock gates (FR-019…021).
- Learn/Read/Echo modes, adaptive slowdown (FR-031).
- Multi-student + touch flow + Daily Mission.
- Data migration (DR-008).
- **Exit:** AC-008, AC-010, AC-011; deploy to all stations.

## Phase 5 — Motivation layer (V2)

- Word practice, badges, coach, sprint, session recovery — all as pure
  derivations (DR-009) with contract tests.
- Rhythm analysis (FR-036/FR-037): port `timing_summary` scoring and the
  admin rhythm view from legacy (`674fdd8`), adding the PIN gate (API-017)
  and porting `tests/test_practice_attempts.py` (AC-013).

## Phase 6 — Fleet ops (V2)

- S3 sync with per-station IAM (SEC-011), status document (NFR-011).
- Hardened auto-update with health-check rollback (FR-035, SEC-010).
- **Exit:** TEST-009 green; runbook (DOC-07) updated.

## Phase 7A — Local family messages (V2)

- Message domain, drafts, and local inbox/outbox (FR-039...FR-048).
- No-keyboard touch composer with word tiles and physical-key entry.
- Review/edit/play flow and guided receiver decoding with progressive hints.
- Message effort and badge events remain separate from core mastery.
- **Exit:** AC-015...AC-017 and TEST-014 pass on a real 800x480 station;
  children can test the complete learning flow without AWS.

## Phase 7B — Durable family delivery (V2)

- Student-addressed family directory and minimal active-letter summaries.
- Per-station least-privilege identities, S3 outbox/router/inbox/receipts, and
  optional AWS IoT arrival notifications (FR-047...FR-050).
- Offline queueing, retry, cross-station read state, audit/status reporting,
  backup coverage, and a delivery runbook.
- **Exit:** AC-018...AC-020 and TEST-013 pass with all three stations; a Pi
  may remain off for several days and receive exactly one durable message when
  it returns.

## Cutover rule

A deployed station switches from legacy to rebuilt code only when: the phase's
exit ACs pass in CI, the migration test (AC-010) passes against that station's
backed-up data, and a fresh backup was taken immediately before the switch.
