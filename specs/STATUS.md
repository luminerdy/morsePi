# Spec Compliance Status — Legacy Codebase

Tracks how far the **current legacy code** satisfies the spec, so the rebuild
knows what it inherits. This file is updated on each re-review; requirement
files only carry *(Delta: …)* notes, not status history.

- **Baseline review:** `33df851` (2026-07-02)
- **Latest legacy-code re-review:** working tree after `3f20d03` (2026-08-01)
- **Spec package location:** root `specs/`

## Changes landed since baseline (`33df851..7818254`)

| Change | Commits | Spec impact |
|---|---|---|
| Input caps: 16 KB request body (`MAX_CONTENT_LENGTH`), message ≤ 160, Morse ≤ 600, answer ≤ 20, word ≤ 20, student name ≤ 40 chars | `7818254` | FR-012, SEC-004 — largely met (see note 1) |
| All `next` redirects routed through `safe_next_url()`, with tests | `7818254` | SEC-005 — **met**; AC-005 passes |
| Unlock table unified: `letter_unlock_groups` in `app.py` now generates steps + letter list | `7818254` | FR-022 — partial (duplicate `LETTER_UNLOCKS` remains in `practice_progress.py`) |
| Update channel: default branch now `release/pi`; post-restart HTTP health check (30 s) | `5e835d3` | FR-035, SEC-010 — partial (no rollback, no pre-restart tests, no signed tags) |
| `app.run(..., threaded=False)` | `7818254` | NFR-004 — mitigated by serializing requests; global-state root cause remains |
| `scripts/check_dependencies.py` (manual required/optional binary + module check) | `7818254` | TR-008 — partial (manual script, not startup detection) |
| Rhythm timing summaries per attempt + `/admin/rhythm` trends page; timing events capped at 240 | `674fdd8` | New scope — now FR-036/FR-037, API-017, AC-013 |
| Learn-mode score display fix; screenshots; doc updates | `89f73eb` etc. | No spec impact |
| Touch System recovery page with Wi-Fi/IP status, on-screen keyboard availability/launch, admin-PIN-gated app update, Wi-Fi restart, and admin-PIN-gated kiosk exit | after `3f20d03` | FR-038, API-018, AC-014 — met in legacy |

**Note 1 (FR-012):** over-limit text is silently **truncated** (`limited_text`),
not rejected; only bodies > 16 KB get a hard 413. The OOM DoS is closed
(Morse capped at 600 chars before synthesis), but FR-012's
"reject, don't truncate" behavior is still open — see AC-002.

## Requirement status at `7818254`

Legend: ✅ met · 🟡 partial/mitigated · ❌ open · — not applicable to legacy
(rebuild-only requirement).

| Requirement | Status | Notes |
|---|---|---|
| FR-001…FR-011 | ✅ | Long-standing behavior, unchanged |
| FR-012 input caps | 🟡 | Caps exist; truncates instead of rejecting |
| FR-013…FR-021, FR-023…FR-034 | ✅ | Implemented in legacy (tiering is for the rebuild) |
| FR-022 single unlock table | 🟡 | Unified in `app.py`; `practice_progress.py:LETTER_UNLOCKS` duplicate remains |
| FR-035 hardened updater | 🟡 | `release/pi` branch + health check; **no rollback**, py_compile only |
| FR-036/FR-037 rhythm analysis | ✅ | New feature, spec'd retroactively |
| FR-038 touch System recovery | ✅ | `/touch/system` shows local status, keyboard availability, and update state; `/touch/system/action` gates recovery/update actions behind admin PIN |
| FR-039...FR-050 family Morse messages | — | Planned Phase 7; specified before implementation. The legacy desktop text composer is not family messaging. |
| NFR-004 concurrency safety | 🟡 | `threaded=False` serializes requests; module-global state remains, will regress under any threaded server |
| NFR-005 runs off-Pi w/o env vars | ❌ | Still needs `GPIOZERO_PIN_FACTORY=mock` |
| NFR-006 atomic writes | ❌ | Plain `write_text`, no temp+rename |
| SEC-001 CSRF | ❌ | No tokens anywhere |
| SEC-002/003 mandatory PIN + lockout | ❌ | PIN optional, `==` compare, no rate limit |
| SEC-004 input validation | 🟡 | See FR-012 note |
| SEC-005 safe redirects | ✅ | Fixed + tested at `7818254` |
| SEC-006 production WSGI | ❌ | Flask dev server (now single-threaded) |
| SEC-007 systemd sandboxing | ❌ | No hardening directives |
| SEC-009 subprocess hygiene | ✅ | Arg arrays, no shell (was already true) |
| SEC-010 update trust | 🟡 | Pinned `release/pi` + health check; no signing/rollback |
| SEC-013 cookie flags | 🟡 | `SameSite=Lax` set; `HttpOnly` not set |
| SEC-014/015, TR-011 | ❌ | No secret scan, pip-audit, lint, or dependency automation in CI |
| TR-002 package layout | ❌ | `app.py` still a ~3,180-line monolith |
| TR-008 binary detection | 🟡 | Manual `check_dependencies.py`; not run at app startup |
| API-017 `/admin/rhythm` PIN gate | ❌ | Page is unauthenticated in legacy (read-only, but exposes practice data) |
| API-018 touch system recovery action | ✅ | Implemented as `/touch/system/action` |
| API-019...API-023 family Morse messages | — | Planned Phase 7; not implemented |

## Acceptance criteria at `7818254`

| AC | Baseline | Now | Notes |
|---|---|---|---|
| AC-001 concurrency | ❌ | 🟡 | Passes only because server is single-threaded; root cause open |
| AC-002 oversize → 413 | ❌ | 🟡 | OOM closed by truncation; 413-rejection semantics still fail |
| AC-003 CSRF | ❌ | ❌ | |
| AC-004 mandatory PIN + lockout | ❌ | ❌ | |
| AC-005 external redirect rejected | ❌ | ✅ | Covered by new legacy tests |
| AC-006…AC-012 | n/a | n/a | Rebuild-phase criteria |
| AC-013 rhythm scoring | — | ✅ | Covered by `tests/test_practice_attempts.py` |
| AC-014 touch System recovery | — | ✅ | Covered by `tests/test_routes.py` |
| AC-015...AC-020 family Morse messages | — | — | Planned Phase 7; tests not implemented |
