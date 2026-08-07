# Spec Compliance Status — Legacy Codebase

Tracks how far the **current legacy code** satisfies the spec, so the rebuild
knows what it inherits. This file is updated on each re-review; requirement
files only carry *(Delta: …)* notes, not status history.

- **Baseline review:** `33df851` (2026-07-02)
- **Latest legacy-code re-review:** touch speaker volume update (2026-08-03)
- **Spec package location:** root `specs/`

## Changes landed since baseline (`33df851..7818254`)

| Change | Commits | Spec impact |
|---|---|---|
| Input caps: 16 KB request body (`MAX_CONTENT_LENGTH`), message ≤ 160, Morse ≤ 600, answer ≤ 20, word ≤ 20, student name ≤ 40 chars | `7818254` | FR-012, SEC-004 — largely met (see note 1) |
| All `next` redirects routed through `safe_next_url()`, with tests | `7818254` | SEC-005 — **met**; AC-005 passes |
| Unlock table unified: `letter_unlock_groups` in `app.py` now generates steps + letter list | `7818254` | FR-022 — partial (duplicate `LETTER_UNLOCKS` remains in `practice_progress.py`) |
| Update channel: default branch now `release/pi`; pre-restart tests; post-restart HTTP health check; rollback on test/health failure | `5e835d3` + 2026-08-04 working tree | FR-035, SEC-010 — mostly met; signed tags/releases remain open |
| `app.run(..., threaded=False)` | `7818254` | NFR-004 — mitigated by serializing requests; global-state root cause remains |
| `scripts/check_dependencies.py` (manual required/optional binary + module check) | `7818254` | TR-008 — partial (manual script, not startup detection) |
| Rhythm timing summaries per attempt + `/admin/rhythm` trends page; timing events capped at 240 | `674fdd8` | New scope — now FR-036/FR-037, API-017, AC-013 |
| Learn-mode score display fix; screenshots; doc updates | `89f73eb` etc. | No spec impact |
| Touch System recovery page with Wi-Fi/IP status, on-screen keyboard availability/launch, admin-PIN-gated app update, Wi-Fi restart, and admin-PIN-gated kiosk exit | after `3f20d03` | FR-038, API-018, AC-014 — met in legacy |
| Silent touch keypad for admin PIN entry | 2026-08-03 working tree | FR-038, AC-014 — touch admin actions can be unlocked without a physical keyboard and without speaker/LED feedback |
| Local admin PIN reset helper | 2026-08-03 working tree | FR-038, AC-014 — adult can reset the station PIN with a config backup and no JSON hand-editing |
| Kid-facing safe shutdown flow | 2026-08-03 working tree | FR-038, API-024, AC-014 — students can safely power off from the touch menu after a confirmation page |
| Touch speaker volume presets | 2026-08-03 working tree | FR-011 — parent-friendly Mute/Quiet/Normal/Loud controls are available from the touch Timing screen, require the adult PIN when configured, and persist in `data/volume_settings.json` |
| Read-only station progress snapshots | 2026-08-03 working tree | FR-034, DR-017 — daily backup service now also writes/uploads `morsepi-progress-snapshot-v1` to the station snapshot prefix for family visibility; no cross-station merge yet |
| Read-only family progress view | 2026-08-03 working tree | DR-018, API-025 — `scripts/family_progress.py` combines latest station snapshots into `data/family_progress/latest.json`; `/admin/family` shows the latest student source and unavailable station snapshots without writing student data |
| Student progress sync design, attempt IDs, dry-run report, full-sync path, and guarded timer foundation | 2026-08-04 working tree | FR-054, DR-019 — new Practice/Words/Sprint attempts include stable `attempt_id`; merge contract documented; dry-run report lists local upload candidates/conflicts/cloud errors without writing student files; manual upload-only and full `--sync` modes are available; guarded sync skips recent app activity, writes status, uses a lock, and has optional systemd timer files; production timer soak remains future work |
| Local family Morse messaging with shared-letter validation, word-tile/whole-word keyer composition, review, playback, inbox, guided decoding, effort, and badges | 2026-08-02 working tree | FR-039...FR-046 — met for Phase 7A; FR-047...FR-050 remain partial pending cross-station transport |
| Durable S3/Lambda message routing, station sync worker, remote receipts, and three-station rehearsal | `29a665d`; activated 2026-08-02 | FR-047...FR-050, FR-052, FR-053, API-023, and AC-018...AC-020/AC-023 — met; Pappy and Astrid/Liara enabled at ten minutes, Campbell/Olivea remains disabled |
| Project and AWS architecture diagrams | 2026-08-02 working tree | DOC-03 — implemented for the current three-station system, deployed AWS services, trust boundaries, and future optional services |
| Station boot splash branding | 2026-08-06 working tree | NFR-018 — static 800x480 boot splash asset and reversible Plymouth `pix` installer added; live reboot verification remains open |
| Student sync learning-state rebuild | 2026-08-06 working tree | FR-054/DR-019 — rebuild now treats completed learning groups as earned once historical attempts crossed the gate, while current skill strength may still regress for coaching |
| App learning-gate display after sync | 2026-08-06 working tree | FR-022/FR-051 — Daily/Progress active-letter calculation now keeps earlier earned groups active when a later learning group exists, preventing Words from relocking after sync-derived strength changes |
| Words feedback color state | 2026-08-06 working tree | UX polish — Words correct feedback now uses a steady green success wash for the existing feedback duration; incorrect feedback uses a steady amber needs-work wash |
| Admin System sync status wording | 2026-08-07 working tree | FR-038/FR-054 — touch System page now presents sync as Last Sync plus friendly job/timer labels and falls back to the attempt-sync report instead of showing an unhelpful unknown state |
| Admin System 800x480 layout polish | 2026-08-07 working tree | AC-014/UX polish — screen renamed from Adult System to Admin System; status cards use a compact three-column layout with wrapped/clamped text so long network, backup, and system labels do not bleed into neighboring cards; unreported Wi-Fi signal values show as `Signal not reported` instead of `Unknown` |
| Top-of-screen practice result | 2026-08-07 working tree | FR-055/AC-026 — Learn, Send, Read, Listen, Echo, Words, and Bonus Sprint now show bold `Correct!` or `Try Again` in the existing title bar while retaining detailed feedback and the established timing |
| Admin System partial-status compatibility | 2026-08-07 working tree | AC-014 — the Last Sync card uses friendly literal defaults when optional detailed service fields are absent, preventing Pi/Jinja rendering failures in reduced status fixtures |

**Note 1 (FR-012):** over-limit text is silently **truncated** (`limited_text`),
not rejected; only bodies > 16 KB get a hard 413. The OOM DoS is closed
(Morse capped at 600 chars before synthesis), but FR-012's
"reject, don't truncate" behavior is still open — see AC-002.

## Requirement status at `7818254`

Legend: ✅ met · 🟡 partial/mitigated · ❌ open · — not applicable to legacy
(rebuild-only requirement).

| Requirement | Status | Notes |
|---|---|---|
| FR-001…FR-011 | ✅ | Volume now includes persisted touch presets behind the adult PIN |
| FR-012 input caps | 🟡 | Caps exist; truncates instead of rejecting |
| FR-013…FR-021, FR-023…FR-034 | ✅ | Implemented in legacy (tiering is for the rebuild) |
| FR-022 single unlock table | 🟡 | Unified in `app.py`; `practice_progress.py:LETTER_UNLOCKS` duplicate remains |
| FR-035 hardened updater | ✅ | `release/pi` branch, dirty-tree guard, fast-forward only, pre-restart tests, health check, rollback on failure, and status/snapshot refresh |
| FR-036/FR-037 rhythm analysis | ✅ | New feature, spec'd retroactively |
| FR-038 touch System recovery | ✅ | `/touch/system` shows local status, keyboard availability, update state, app version/branch, latest backup, latest sync, and a silent touch keypad; `/touch/system/action` gates recovery/update actions behind admin PIN; `/touch/shutdown` provides kid-facing safe shutdown; `scripts/set_admin_pin.py` safely resets the local PIN |
| FR-039...FR-046 family Morse experience | ✅ | Phase 7A local flow implemented in `message_store.py` and `/touch/messages/*` |
| FR-047...FR-050 durable delivery | ✅ | S3 routing, duplicate-safe station download, durable offline storage, and decoded receipts passed the live three-station rehearsal |
| NFR-004 concurrency safety | 🟡 | `threaded=False` serializes requests; module-global state remains, will regress under any threaded server |
| NFR-005 runs off-Pi w/o env vars | ❌ | Still needs `GPIOZERO_PIN_FACTORY=mock` |
| NFR-006 atomic writes | ❌ | Plain `write_text`, no temp+rename |
| NFR-017 centered Morse display | ✅ | Shared server/browser renderer covers app displays and printable handout while preserving canonical ASCII Morse |
| FR-051 mixed Words opening | ✅ | The opening bank interleaves familiar two- and three-letter words; eligibility remains active-letter filtered |
| FR-052 station message sync | ✅ | Ten-minute worker/timer prepared for all three stations; tested live with isolated data; normal sync remains an explicit configuration switch |
| FR-028/DR-015 reset summary cleanup | ✅ | Student reset backs up and removes local and cached family learning summaries so old cloud eligibility cannot restore unlocked letters |
| DR-017 read-only progress snapshots | ✅ | `scripts/progress_snapshot.py` writes a safe station snapshot and the daily backup service uploads it; two-way student data merge remains future work |
| DR-018 family progress view | ✅ | Read-only local family progress file and `/admin/family` view implemented; live cross-station completeness depends on Pappy's AWS credential being allowed to read station snapshot objects |
| FR-054/DR-019 student progress sync | 🟡 | Merge strategy documented, new attempts get `attempt_id`, and `scripts/student_attempt_sync.py` produces a no-write dry-run report, upload-only path, guarded full sync with backup/merge/rebuild, status file, and lock; optional systemd timer exists but needs station soak testing |
| FR-053 cloud message router | ✅ | Narrow-role Lambda and three S3 notifications deployed in `us-east-1`; live routing and receipts verified |
| SEC-001 CSRF | ❌ | No tokens anywhere |
| SEC-002/003 mandatory PIN + lockout | 🟡 | PIN remains optional for development, but configured PINs now use constant-time comparison and a short in-memory lockout after repeated failures |
| SEC-004 input validation | 🟡 | See FR-012 note |
| SEC-005 safe redirects | ✅ | Fixed + tested at `7818254` |
| SEC-006 production WSGI | ❌ | Flask dev server (now single-threaded) |
| SEC-007 systemd sandboxing | ❌ | No hardening directives |
| SEC-009 subprocess hygiene | ✅ | Arg arrays, no shell (was already true) |
| SEC-010 update trust | 🟡 | Pinned `release/pi`, test/health rollback; no signed release/tag verification yet |
| SEC-013 cookie flags | 🟡 | `SameSite=Lax` set; `HttpOnly` not set |
| SEC-014/015, TR-011 | ❌ | No secret scan, pip-audit, lint, or dependency automation in CI |
| TR-002 package layout | ❌ | `app.py` still a ~3,180-line monolith |
| TR-008 binary detection | 🟡 | Manual `check_dependencies.py`; not run at app startup |
| API-017 `/admin/rhythm` PIN gate | ❌ | Page is unauthenticated in legacy (read-only, but exposes practice data) |
| API-018 touch system recovery action | ✅ | Implemented as `/touch/system/action` |
| API-019...API-022 family Morse messages | 🟡 | Equivalent server-validated touch form routes exist; the rebuild's versioned JSON API contract remains open |
| API-023 cross-station sync | ✅ | Versioned S3 object contract and station worker implemented and live-rehearsed |

## Acceptance criteria at `7818254`

| AC | Baseline | Now | Notes |
|---|---|---|---|
| AC-001 concurrency | ❌ | 🟡 | Passes only because server is single-threaded; root cause open |
| AC-002 oversize → 413 | ❌ | 🟡 | OOM closed by truncation; 413-rejection semantics still fail |
| AC-003 CSRF | ❌ | ❌ | |
| AC-004 mandatory PIN + lockout | ❌ | 🟡 | Constant-time compare and short lockout implemented; mandatory PIN, logging, and full production lockout remain open |
| AC-005 external redirect rejected | ❌ | ✅ | Covered by new legacy tests |
| AC-006…AC-012 | n/a | n/a | Rebuild-phase criteria |
| AC-013 rhythm scoring | — | ✅ | Covered by `tests/test_practice_attempts.py` |
| AC-014 touch System recovery | — | ✅ | Covered by `tests/test_routes.py` |
| AC-015 compose/review/send | — | ✅ | Route tests plus 800x480 browser rehearsal on the Pappy station |
| AC-016 hidden decode/hints | — | ✅ | Route tests verify progressive reveal and effort events |
| AC-017 guest/security rules | — | ✅ | Guest rejection and server-side tamper revalidation covered |
| AC-018...AC-020 cross-station delivery | — | ✅ | Unit replay/tamper tests plus live Pappy-to-Astrid delivery and decoded receipt |
| AC-021 centered Morse geometry | — | ✅ | Unit/template tests plus 800x480 geometry measurement and two-page PDF inspection |
| AC-022 mixed Words sequence | — | ✅ | Curriculum regression verifies 42 eligible words with `NOT` and `MOM` in the first six |
| AC-023 three-station cloud delivery | — | ✅ | Intended Pappy and Astrid/Liara stations received one copy; Campbell/Olivea received none; receipt returned to sender |
