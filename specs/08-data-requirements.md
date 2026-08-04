# 08 — Data Requirements

- **DR-001** Data root: `data/` beside the app. Layout:
  `data/station_config.json`, `data/timing_settings.json`,
  `data/volume_settings.json`,
  `data/student_profiles.json`, `data/students/<id>/…`, `data/backups/`,
  `data/student_backups/`.
- **DR-002** Per-student files: `profile.json`, `practice_progress.json`,
  `learning_state.json`, `practice_attempts.jsonl`, `word_attempts.jsonl`,
  `bonus_attempts.jsonl`. Every file's schema SHALL be documented (DOC-06)
  and carry a `format`/version field. *(Delta: today schemas are implicit.)*
- **DR-003** Progress record per letter: `attempts`, `correct`, `streak`,
  `strength` (0–100 float), `last_seen` (UTC ISO). Strength decay/growth
  formula SHALL be specified in DOC-06, not just implemented.
- **DR-004** Attempt records (JSONL, append-only, one JSON object per line):
  fields per FR-017 plus, for keyed attempts, `timing_events` (capped at 240
  entries) and a derived `timing_summary` per FR-036 (counts, per-type gap
  averages, consistency/ratio scores, `overall_rhythm_score`,
  `primary_rhythm_feedback`); unknown fields preserved on rewrite; readers
  tolerate a torn last line (NFR-006). Rhythm readers SHALL prefer recomputing
  from `timing_events` and fall back to the stored `timing_summary` for older
  records.
- **DR-005** Station config schema: `station_id` (slug, required),
  `timezone`, `students[]`, `family_students[]`, `guest_profile`, `allow_student_create`,
  `backup_s3_uri`. `admin_pin` **must not** be stored here in plaintext
  post-MVP (env/file per SEC-014) — the field is accepted for migration only
  and warned about.
  `students[]` defines who can sign in locally; `family_students[]` defines the
  approved messaging directory and MAY include students who normally use a
  different station.
- **DR-006** Backup archive: zip named `<UTCstamp>-<station>-<label>.zip`
  containing `data/…` relative paths + `manifest.json`
  (`format: morse-station-data-backup-v1`); restore SHALL validate the
  manifest before extracting.
- **DR-007** Retention: 30 local backup zips (configurable); student reset
  backups kept indefinitely; attempt logs never truncated by the app (only
  by explicit admin export/archive — V2).
- **DR-008** Migration: the rebuild SHALL read all current v0 files unchanged
  (they are the family's real data); a one-time migration adds version
  fields and moves legacy root-level student files under `students/pappy/`.
- **DR-009** All derived views (badges, coach, mission status, sprint
  summaries) SHALL be computable purely from DR-002/DR-004 data — no derived
  state stored, so bugs are fixable retroactively.
- **DR-010** PII inventory: student display names, practice history, and family
  message content/metadata are personal data. Their collection, access,
  retention, export, and deletion rules SHALL be documented in `SECURITY.md`
  (SEC-012) before cloud messaging is enabled.
- **DR-011** Message record format `morsepi-message-v1` SHALL contain:
  `message_id`, `sender_student_id`, `sender_station_id`,
  `recipient_student_id`, normalized `text`, `required_letters[]`,
  `created_at` UTC, and `format`. Morse MAY be cached but is non-authoritative
  and MUST match FR-001 when read. Message text is immutable after acceptance.
- **DR-012** Per-student messaging data SHALL include atomic local draft and
  inbox/outbox indexes plus an append-only message event log. Events SHALL
  include `message_id`, state (`queued|available|opened|decoded`), station ID,
  student ID, UTC time, decode attempts, aids used, elapsed effort time, and
  optional Key It Back timing data. Duplicate `(message_id, state, station)`
  events SHALL be ignored for derived credit.
- **DR-013** The family directory SHALL map stable student IDs to approved
  station IDs and messaging eligibility. A separately synchronized learning
  summary SHALL contain only student ID, active letters, curriculum version,
  and generated-at UTC time; stale or missing summaries SHALL disable sending
  to that student with a friendly Try Later message, not guess eligibility.
- **DR-014** Cloud layout SHALL separate untrusted station-owned outbox and
  outgoing-receipt objects from router-validated station inbox and status
  objects. Paths SHALL follow `stations/<station-id>/messages/{outbox,inbox,
  receipts,status}/...`; minimal shared summaries and the family directory
  live under `family/`. Router output SHALL never use an input sub-prefix,
  preventing recursive routing.
- **DR-015** Cloud learning summary format `morsepi-learning-summary-v1` SHALL
  contain only stable student ID, source station ID, ordered active letters,
  curriculum version, and generated-at UTC. The family aggregate SHALL union
  only snapshots from directory-approved stations and SHALL contain no display
  name, score, timing, attempt history, or rank.
  Student reset SHALL back up and remove both
  `message_sync/local_summaries/<student-id>.json` and
  `message_sync/family_summaries/<student-id>.json` on that station.
- **DR-016** Cloud receipt format `morsepi-message-receipt-v1` SHALL contain
  message ID, sender station ID, recipient student ID, reporting station ID,
  forward-only state (`available|opened|decoded`), and UTC time. Deterministic
  state paths make retries idempotent.
