# 08 — Data Requirements

- **DR-001** Data root: `data/` beside the app by default, anchored to the
  application directory rather than the process working directory. Deployments
  MAY override it with `MORSE_DATA_DIR`. Layout:
  `data/station_config.json`, `data/timing_settings.json`,
  `data/volume_settings.json`,
  `data/student_profiles.json`, `data/family_registry.json`,
  `data/students/<id>/…`, `data/backups/`, `data/student_backups/`.
- **DR-002** Per-student files: `profile.json`, `practice_progress.json`,
  `learning_state.json`, `practice_attempts.jsonl`, `word_attempts.jsonl`,
  `bonus_attempts.jsonl`. Every file's schema SHALL be documented (DOC-06)
  and carry a `format`/version field. *(Delta: today schemas are implicit.)*
- **DR-003** Progress record per letter: `attempts`, `correct`, `streak`,
  `strength` (0–100 float), `last_seen` (UTC ISO). Strength decay/growth
  formula SHALL be specified in DOC-06, not just implemented.
- **DR-004** Attempt records (JSONL, append-only, one JSON object per line):
  fields per FR-017 plus stable `attempt_id`, `station_id`, `student_id`,
  `student_uuid` for named family students, and
  `practice_session_id`. For keyed attempts, records also include
  `timing_events` (capped at 240 entries) and a derived `timing_summary` per
  FR-036 (counts, per-type gap averages, consistency/ratio scores,
  `overall_rhythm_score`, `primary_rhythm_feedback`); unknown fields preserved
  on rewrite; readers tolerate a torn last line (NFR-006). Rhythm readers SHALL
  prefer recomputing from `timing_events` and fall back to the stored
  `timing_summary` for older records.
- **DR-005** Station config schema: `station_id` (slug, required),
  `timezone`, `students[]`, `family_students[]`, `guest_profile`, `allow_student_create`,
  `backup_s3_uri`. `admin_pin` **must not** be stored here in plaintext
  post-MVP (env/file per SEC-014) — the field is accepted for migration only
  and warned about.
  `students[]` defines who can sign in locally; `family_students[]` defines the
  approved messaging directory and MAY include students who normally use a
  different station.
  Named entries SHALL carry the UUID assigned by the canonical family registry.
  Real deployed-family registry data SHOULD live in ignored
  `data/family_registry.json`; tracked `config/family_registry.json` is only a
  fallback/template after stations have migrated.
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
  `message_id`, `sender_student_id`, `sender_student_uuid`, `sender_station_id`,
  `recipient_student_id`, `recipient_student_uuid`, normalized `text`, `required_letters[]`,
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
- **DR-017** Station progress snapshot format `morsepi-progress-snapshot-v1`
  SHALL be a read-only visibility record, not a merge source. It MAY include
  station ID, hostname, generated-at UTC, legacy student ID, canonical
  `student_uuid`, display name, active letters,
  learning-state summary, mode totals, word totals, bonus totals, and latest
  activity timestamps. It SHALL NOT include raw key timing events or detailed
  answer histories.
- **DR-018** Family progress format `morsepi-family-progress-v1` SHALL combine
  station progress snapshots into one read-only visibility file. For each
  student, the default row SHALL use the latest `latest_activity_at` snapshot
  while preserving source-station metadata. Missing or unauthorized station
  snapshots SHALL be reported as unavailable instead of blocking the view.
- **DR-019** Cross-station student progress sync SHALL merge append-only
  attempt logs by `attempt_id`, never by copying `practice_progress.json`.
  Duplicate IDs with different payloads SHALL be quarantined for adult review;
  older records without `attempt_id` SHALL use a deterministic legacy fallback
  key. The detailed merge contract is documented in
  `docs/STUDENT_PROGRESS_SYNC_DESIGN.md`.
- **DR-020** The canonical family registry SHALL assign exactly one immutable,
  unique RFC 4122 UUID to each named family student. Deployed stations SHALL
  prefer ignored `data/family_registry.json` for real family identities and MAY
  fall back to tracked `config/family_registry.json` only during transition or
  setup. UUIDs are canonical person identity; legacy IDs remain folder, cookie,
  and cloud-path aliases during the compatibility phase. Migration SHALL be
  idempotent, create timestamped metadata/config backups, copy the tracked
  registry into private station data when needed, never rename student
  directories, and preserve old records. Readers SHALL enrich UUID-less records
  through the registry and reject a supplied ID/UUID conflict. Display-name
  edits SHALL not change UUIDs.
- **DR-021** Signal Drop SHALL append records to the student's bonus attempt
  log with a stable `attempt_id`, UTC timestamp, station/student identity,
  `kind=signal-drop`, session ID, game mode, target, expected and actual Morse
  or selected answer, correctness, clear count, miss reason, timing events,
  and derived timing summary. These records SHALL be syncable and count toward
  effort reporting, but SHALL not be replayed into `practice_progress.json`.
- **DR-022** Curriculum-group migration SHALL preserve legacy learning-state
  records and derive a canonical group's effective introduction time when older
  records collectively cover every letter in that group. For each letter, use
  its earliest recorded introduction; the canonical group begins when the last
  of its letters was first introduced. The migration SHALL be idempotent and
  SHALL never move an introduction time forward.
