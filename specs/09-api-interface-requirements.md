# 09 — API / Interface Requirements

General rules:

- These are target rebuild interfaces. The rebuild MAY keep today's legacy
  HTML/JSON routes as wrappers during migration, but new code should expose the
  `/api/*` contract below.
- JSON endpoints return `{"status": …}` envelopes.
- Errors use proper HTTP codes: 400 validation, 403 auth, 409 state conflict,
  413 too large.
- All POSTs are CSRF-protected (SEC-001).
- 🔒 marks PIN-protected endpoints (SEC-002/003).

## Pages (HTML)

- **API-001** *(MVP)* `GET /` message composer; `GET /practice?mode=`,
  `GET /progress`, `GET /students`
- **API-002** *(V1)* `GET /touch`, `/touch/daily`, `/touch/practice`,
  `/touch/words`, `/touch/progress`, `/touch/students`, `/touch/timing`,
  `/touch/system`
- **API-003** *(V2)* `GET /admin/sessions` 🔒
- **API-017** *(V2)* `GET /admin/rhythm` 🔒 — per-student rhythm trend report
  (FR-037). *(Delta: legacy page added in `674fdd8` is unauthenticated; the
  rebuild PIN-gates it.)*
- **API-018** *(V1)* `POST /touch/system/action` 🔒 — local touchscreen
  operations `{action: restart-wifi|open-keyboard|update-app|exit-kiosk}` for
  FR-038. The response MAY redirect back to `/touch/system` because these
  actions can interrupt the browser or network.

## Station control (JSON unless noted)

- **API-004** *(MVP)* `POST /api/message` — set message (≤ 160 chars),
  returns Morse
- **API-005** *(MVP)* `POST /api/play` — play current message or supplied
  Morse (≤ 600 normalized Morse characters); `POST /api/stop`;
  `POST /api/audio/reset`
- **API-006** *(MVP)* `POST /api/volume` 🔒; `POST /api/timing` 🔒 — clamped
  per FR-004
- **API-007** *(MVP)* `GET /api/key` — `{morse, decoded}` live buffer;
  `POST /api/key/clear`

## Practice

- **API-008** *(MVP)* `POST /api/practice/next` and `/retry` — returns
  `{mode, target, expected_morse, read_choices, timing, progress, score,
  overall}`
- **API-009** *(MVP)* `POST /api/practice/result` — body
  `{mode, target, answer | actual_morse, timing_events}`; server decides
  correctness (FR-013/014); returns recorded attempt + updated summaries
- **API-010** *(V1)* `POST /api/practice/prompt` — play/flash the current
  target on station hardware; only valid in listen/echo/learn
- **API-011** *(V2)* `POST /api/words/result`, `POST /api/bonus/result` —
  same envelope pattern, session-scoped for bonus

## Students & admin

- **API-012** *(V1/V2)* `POST /api/students/select`;
  `POST /api/students/create` 🔒 (when roster allows);
  `POST /api/students/reset` 🔒 requires typed confirmation token
- **API-013** *(V2)* `POST /api/admin/sessions/recover` 🔒 —
  `{session_id, action: move|discard, target_student_id}`
- **API-014** *(MVP)* `GET /healthz` — unauthenticated
  `{status, version, git_sha, hardware: {key, led, audio}}` for
  updater/monitoring

## Hardware interfaces

- **API-015** *(MVP)*
  - Telegraph key: GPIO17, internal pull-up, active-low, 30 ms debounce.
  - LED: GPIO27, active-high.
  - Both GPIO numbers configurable.
  - Audio: ALSA device by name, default `default:CARD=UACDemoV10`, override
    via `MORSE_AUDIO_DEVICE`.

## CLI

- **API-016** *(MVP/V2)* `morsepi-backup` (create/rotate/restore/S3 flags per
  FR-033/034); `morsepi-status`; `update_station.sh` per FR-035. Flags keep
  today's names (`--label`, `--keep`, `--station-id`, `--s3-uri`,
  `--restore`, `--restore-root`, `--dry-run-s3`) for runbook compatibility.
