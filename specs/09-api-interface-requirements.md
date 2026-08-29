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
  `/touch/system`, `/touch/system/operators`, `/touch/shutdown`
- **API-003** *(V2)* `GET /admin/sessions` 🔒
- **API-017** *(V2)* `GET /admin/rhythm` 🔒 — per-student rhythm trend report
  (FR-037). *(Delta: legacy page added in `674fdd8` is unauthenticated; the
  rebuild PIN-gates it.)*
- **API-025** *(V2)* `GET /admin/family`; `POST /admin/family` 🔒 — read the
  latest local family progress file and refresh it from cloud station
  snapshots on adult demand.
- **API-018** *(V1)* `POST /touch/system/action` 🔒 — local touchscreen
  operations `{action: restart-wifi|open-keyboard|update-app|exit-kiosk}` for
  FR-038. The response MAY redirect back to `/touch/system` because these
  actions can interrupt the browser or network.
- **API-024** *(V1)* `GET /touch/shutdown`, `POST /touch/shutdown` —
  kid-facing safe shutdown confirmation. POST starts OS shutdown only when the
  confirmation token is present and then renders the wait-for-screen-dark
  message.
- **API-019** *(V2)* `GET /touch/messages`, `/touch/messages/compose`,
  `/touch/messages/review`, `/touch/messages/inbox/<message_id>` — student
  message menu, no-keyboard composer, review, and guided decode pages for
  FR-039...FR-046. Guest receives 403 or a kid-friendly unavailable page.

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
- **API-026** *(V1)* `POST /touch/system/operators` 🔒 — replace the local
  named-student roster with a non-empty subset of configured family students;
  preserve unrelated station configuration and student data, then redirect to
  the touch operator picker.

## Family messages

- **API-020** *(V2)* `GET /api/messages/recipients` returns configured eligible
  recipients with legacy ID, canonical UUID, and active-letter availability;
  `POST /api/messages/draft`
  performs `{create|append-word|append-keyed-letter|space|undo|clear|replace|
  delete}` and returns the normalized draft plus letter/Morse tiles.
- **API-021** *(V2)* `POST /api/messages/play-draft`; `POST
  /api/messages/send` accepts the draft ID and a compatible recipient ID alias,
  resolves and validates its canonical UUID, revalidates FR-039/SEC-018,
  freezes the record, and returns `queued` or `available`.
- **API-022** *(V2)* `GET /api/messages/inbox`; `POST
  /api/messages/<message_id>/open`; `POST
  /api/messages/<message_id>/play` with scope `message|word|letter`; `POST
  /api/messages/<message_id>/answer` with slot and letter; `POST
  /api/messages/<message_id>/hint` with the requested progressive aid.
  Responses SHALL reveal only text already decoded or explicitly revealed.
- **API-023** *(V2)* The station message sync worker SHALL upload queued
  outbox objects, download validated inbox objects for locally rostered
  students, upload receipts, and optionally subscribe to its approved AWS IoT
  arrival topic. Reprocessing the same cloud object SHALL be idempotent.

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
- **API-027** *(V2)* `scripts/remote_update_iot.py --once` polls AWS IoT Jobs
  for the configured station Thing, accepts only the allow-listed maintenance
  actions from FR-058, updates the AWS job execution state to
  `IN_PROGRESS`/`SUCCEEDED`/`FAILED` when cloud access is available, and writes
  `data/remote_update/latest_iot_job.json` for local/Admin-System visibility.
  `update-app` job documents MAY include `expected_commit`; success requires a
  matching terminal `data/update/latest_update.json` report. The allow-listed
  `diagnose-update` action writes `data/update/latest_diagnostic.json` and
  SHALL run no command supplied by the job document. The fixed
  `enable-message-sync` action SHALL invoke only
  `scripts/enable_message_sync.py`; job documents SHALL NOT supply paths,
  service names, commands, or configuration values to that helper.
- **API-028** *(V1)* `POST /signal-drop/next` SHALL return one server-selected
  active letter, canonical Morse, and the student's ordered active-letter set.
  `POST /signal-drop/result` SHALL server-validate Send Morse or a Read answer,
  reject non-active targets, append DR-021, and return the authoritative result.
