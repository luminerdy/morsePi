# 13 — Documentation Plan

Documentation files the rebuilt repository should carry. Several consolidate
or freeze existing docs rather than writing from scratch.

| ID | File | Contents |
|---|---|---|
| DOC-01 | `README.md` | What it is, photo, quick start, links. One screen. |
| DOC-02 | `specs/` | This spec package, one file per section, requirement IDs stable forever. |
| DOC-03 | `docs/ARCHITECTURE.md` | Package map, request lifecycle, hardware interface, threading model, "why one worker." |
| DOC-04 | `SECURITY.md` | Threat model (untrusted LAN, kids, remote update), SEC-* rationale, PII handling, reporting. |
| DOC-05 | `docs/DEPLOYMENT.md` | Fresh-Pi to running station (merge of today's `SETUP_AND_CONFIGURE_PI.md` + `GRANDKID_STATION_DEPLOYMENT.md`), systemd units, config schema reference. |
| DOC-06 | `docs/DATA.md` | Every file schema (DR-*), strength formula, versioning, migration notes. |
| DOC-07 | `docs/RUNBOOK.md` | Remote ops: reading status docs, restoring backups, session recovery, update rollback (evolves today's `REMOTE_BACKUP_STATUS_RUNBOOK.md`). |
| DOC-08 | `docs/CURRICULUM.md` | Letter groups, gate thresholds, and the pedagogy behind them (salvages `MORSE_LEARNING_BEST_PRACTICES.md`). |
| DOC-09 | `docs/HARDWARE.md` | BOM, GPIO pinout, wiring, case worksheet (merges `BILL_OF_MATERIALS.md`, GPIO table, `CASE_MEASUREMENT_WORKSHEET.md`). |
| DOC-10 | `CONTRIBUTING.md` | Dev setup without a Pi, test commands, style (ruff), how to add a requirement/AC before code. |
| DOC-11 | `docs/journal/` | Today's `PROJECT_PLAN.md` and `PROJECT_REQUIREMENTS_AND_STATUS.md` move here as history, frozen. |
| DOC-12 | `CHANGELOG.md` | Per-release; the updater's release-notes source. |
| DOC-13 | `docs/MESSAGING.md` | Kid-facing flow, message state machine, family directory, S3/IoT delivery, IAM boundaries, schemas, offline behavior, and operator troubleshooting. |

## Disposition of current docs

| Current file | Fate |
|---|---|
| `docs/SETUP_AND_CONFIGURE_PI.md` | Merge into DOC-05 |
| `docs/GRANDKID_STATION_DEPLOYMENT.md` | Merge into DOC-05 |
| `docs/REMOTE_BACKUP_STATUS_RUNBOOK.md` | Evolves into DOC-07 |
| `docs/AWS_SETUP_REFERENCE.md`, `docs/AWS_BACKUP_SYNC_DESIGN.md`, `docs/REMOTE_DEPLOYMENT_AWS.md` | Fold into DOC-05 + DOC-07; trust model into DOC-04 |
| `docs/BILL_OF_MATERIALS.md`, `docs/CASE_MEASUREMENT_WORKSHEET.md` | Merge into DOC-09 |
| `docs/MORSE_LEARNING_BEST_PRACTICES.md` | Salvage into DOC-08 |
| `docs/KIDS_STATION_INSTRUCTIONS.md`, `KIDS_QUICK_START_HANDOUT.html` | Keep as kid-facing docs; **untrack the PDF** (build or attach to releases) |
| `docs/PROJECT_PLAN.md`, `docs/PROJECT_REQUIREMENTS_AND_STATUS.md` | Freeze in DOC-11 `docs/journal/` |
