# Student Progress Sync Design

This design covers future cross-station student progress sync. It is not a
leaderboard and it is not a whole-file overwrite system.

## Goal

If a student practices on any MorsePi station, that effort should eventually be
visible and usable on the student's other approved stations.

Examples:

- Astrid practices at Pappy's house, then later uses the Astrid/Liara station.
- Campbell practices at home while Pappy's station is off.
- A station is powered off for days, comes back online, and catches up without
  losing another station's practice.

## Current State

Implemented:

- Each station uploads a daily raw backup and station status.
- Each station uploads a read-only progress snapshot.
- Pappy has an `/admin/family` read-only view that chooses the latest snapshot
  per student by `latest_activity_at`.
- New Practice, Words, and Signal Sprint attempts include `attempt_id`,
  `station_id`, `student_id`, and `practice_session_id`.

Not implemented:

- Cross-station practice attempt sync.
- Automatic merge back to home stations.
- Rebuild of Words or Sprint progress from a merged cloud log.
- Conflict resolution UI.

## Core Rule

Snapshots are for visibility. Attempt logs are the source of truth.

Do not sync by copying `practice_progress.json` from one station to another.
That file is derived state and can be rebuilt.

## Sync Source Files

For each permanent student:

- `practice_attempts.jsonl`
- `word_attempts.jsonl`
- `bonus_attempts.jsonl`

Future optional files:

- message effort events
- daily mission completion events
- coaching/reward events

## Attempt Identity

Every new attempt record should include:

- `attempt_id`: 32-character random hex ID
- `station_id`: station that recorded it
- `student_id`: student selected at the time
- `practice_session_id`: browser/session grouping for recovery
- `timestamp`: UTC ISO time from the recording station
- `kind` or source file type

Older records without `attempt_id` must still be accepted. For legacy records,
the sync worker can use a fallback identity:

```text
legacy:<source-file>:<station_id>:<student_id>:<practice_session_id>:<timestamp>:<target-or-word>:<correct>
```

The fallback is good enough for old records but should not be used for new
records.

## Cloud Layout

Use student-owned sync prefixes, not station-owned raw backup prefixes:

```text
s3://morsepi-backups-luminerdy/
  students/
    <student-id>/
      attempts/
        practice/
          <attempt-id>.json
        words/
          <attempt-id>.json
        bonus/
          <attempt-id>.json
      manifests/
        <station-id>.json
```

Station raw backups remain under:

```text
stations/<station-id>/backups/
```

Those backups are for recovery, not normal progress sync.

## Merge Rules

1. Upload local attempts one object per attempt ID.
2. Download all cloud attempts for students rostered on the local station.
3. Union records by attempt ID.
4. Exact duplicate ID and identical payload: keep one.
5. Duplicate ID with different payload: quarantine both and do not apply either
   automatically.
6. Never delete a local attempt because it is missing from cloud.
7. Never overwrite `practice_progress.json` from cloud.
8. Rebuild derived progress locally after a successful merge.

## Offline Scenario

If a station is off before uploading:

1. The local attempts remain in that station's JSONL files.
2. Another station may upload newer practice for the same student.
3. When the offline station returns, it uploads its missing attempts.
4. Other stations later download those attempts.
5. The student's merged history includes both sets of practice.

No practice is discarded because another station has a newer timestamp.

## Timestamp Rule

Timestamps are useful for ordering and display, not identity.

Clock skew is possible on Raspberry Pi devices. The merge worker should:

- sort attempts by timestamp when rebuilding progress
- preserve upload time separately in cloud metadata if needed
- avoid rejecting attempts only because their timestamp is older than another
  station's latest snapshot

## Rebuild Rules

After merge:

- `practice_progress.json` is rebuilt from merged `practice_attempts.jsonl`.
- Words and Sprint summaries are calculated from their merged attempt logs.
- Learning gates continue to use the same rules, but from merged logs.

Do not rebuild while a student is actively practicing. Prefer:

- run at app startup
- run from the daily timer
- run from adult refresh
- defer if a practice session is active

## Conflict Handling

Conflicts should be rare because `attempt_id` is random.

If a conflict happens:

- write conflicting records to `data/sync_conflicts/<student-id>/`
- show a count on the adult Family page
- do not apply conflicting attempts automatically
- keep practicing possible

## First Implementation Phase

Phase A: attempt ID foundation.

- Add `attempt_id` to new Practice, Words, and Sprint attempt records.
- Document the merge design.
- Do not upload/merge attempts yet.

Phase B: dry-run merge report.

- Add a script that reads local attempts and prints what would upload.
- Add a script that reads downloaded cloud attempts and prints what would merge.
- Do not write student files yet.

Phase C: upload-only.

- Upload attempts for the local station's local students.
- Use idempotent object keys.
- Keep local files unchanged.

Phase D: download and rebuild behind adult action.

- Download cloud attempts.
- Back up student files.
- Merge by attempt ID.
- Rebuild derived progress.
- Show summary before/after.

Phase E: safe automatic sync.

- Run only when app is idle.
- Keep backups.
- Report status on `/admin/family`.

## Why Not Newest Wins

Newest snapshot wins is acceptable for read-only visibility, but not for sync.

If a station is off, its snapshot may be old even though it contains practice
that has never been uploaded. A newest-wins file copy could erase valid work.
Attempt-log union preserves both stations' practice.
