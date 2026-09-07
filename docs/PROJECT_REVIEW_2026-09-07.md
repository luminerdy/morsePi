# Project Review - 2026-09-07

## Assessment and scope

MorsePi is a working family learning product, but not yet a reproducible,
independently maintainable public kit. An experienced Pi developer could build
from it with investigation; a new builder cannot yet rely on the documented
sequence alone. Feature breadth is ahead of installation, security, and recovery
assurance. Do not equate feature completeness with the rebuild MVP's acceptance
criteria: that MVP explicitly requires security work still open in the code.

Reviewed the public repository at main `a4f504e` and release/pi `d6a6016`.
GitHub remote heads match the local review. Latest GitHub CI passed:
https://github.com/luminerdy/morsePi/actions/runs/33978941150
The preceding message-word commit failed CI, consistent with the test correction.
Local test discovery found 293 tests: 130 passed, 163 skipped because app runtime
dependencies are unavailable. This is not a fresh full-platform validation.
The September 5 station update and conversation provide previous Pi validation;
no stations were contacted or changed for this review. User confirms the remote
unit left September 6 and several bidirectional messages worked before departure.

## Implementation checkpoint

The first P1 hardening block was implemented after this review. It standardizes
the documented user-service and cherry-pick release paths; gates all adult
reporting pages with the bounded admin session; requires a configured PIN in
deployed service units; expands runtime-data exclusions; creates checksum-backed
v2 recovery archives with station identity/private registry; preserves safe
legacy-v1 restore; and runs zero-skip CI on both `main` and `release/pi`.
All 299 tests pass locally with the pinned dependencies and in both GitHub
branch checks. Pappy completed the `15591e1` canary with active app/browser,
installed required-PIN setting, protected adult route, and a checksum-backed
37-file backup restored with matching station identity. REV-001, REV-002,
REV-003, REV-004, and REV-006 are improved but remain open until their stated
end-to-end completion criteria (blank-SD, CSRF, anonymization, spare-SD restore,
and repeatable fleet release proof) are met.

This was a targeted source, configuration, workflow, and documentation review,
not a penetration test, dependency vulnerability scan, exhaustive Git-history
secret scan, cloud IAM audit, or blank-SD installation rehearsal. No percentage
of overall completion is assigned because current product and rebuild scope differ.

## What is good

- The learning loop is substantial: five modes, Words, warm-up, games, Daily,
  effort, rhythm coaching, progressive letters, and touch/keyer interaction.
- Real family use has shaped the interface, including recoverable message
  composition, supported keying, and attainable progress indicators.
- Progress uses stable identities and immutable attempt records across devices;
  messaging has local persistence, duplicate handling, and delivery receipts.
- Updater safeguards include backups, fast-forward checks, tests, rollback,
  explicit reports, and IoT result validation. Rollback has protected a station
  during a real failed release. Browser supervision improves unattended recovery.
- Tests cover consequential domain behavior, not just page rendering: learning
  gates, replay, identity, sync recovery, messages, and admin sessions.
- The repository includes an MIT license, requirements with IDs, architecture,
  hardware BOM, setup and operation guides, student instructions, and a history.
- Recent admin sessions use opaque tokens, HttpOnly/SameSite cookies, expiry,
  explicit exit, constant-time PIN comparison, and failed-PIN throttling.

## Findings and recommendations

Priority: P1 = next reliability/security work; P2 = next maintainability milestone;
P3 = later improvement. Effort is relative: S localized, M several modules/docs,
L a staged change with migration or hardware rehearsals. These are estimates.

### REV-001 - P1: Fresh setup can select incompatible service and release paths

Evidence: `docs/SETUP_AND_CONFIGURE_PI.md:116` clones default main; line 642
recommends a system service and treats the user service as a fallback. The
updater (`scripts/update_station.sh:277`) restarts a user service and the browser
unit wants that user service. Following both paths risks duplicate app processes
or an updater restarting the wrong instance. The release instructions at line
537 require a fast-forward merge from main, but the branches currently diverge;
`git merge-base --is-ancestor main release/pi` returned 1.

Recommendation: one supported station installation using the user service,
explicit release selection, desktop auto-login and linger setup, and an
idempotent installer that detects conflicting services. Document a tested Pi OS
release and display stack; validate Chromium, curl, flock, and NetworkManager
in the dependency checker as appropriate. Distinguish development from install.
Benefit: a new builder can follow the guide without discovering our history.
Effort: M. Done: another person builds a blank SD, reboots, updates, and operates
the key/speaker/LED without undocumented commands or duplicate app instances.

### REV-002 - P1: Adult access protection is incomplete

Evidence: `app.py:5292` serves rhythm data without an admin gate. GET paths for
`/admin/sessions` and `/admin/family` also render without authentication.
`app.py:620` and `app.py:649` grant access when no PIN is configured, while
`config.station.example.json` supplies an empty PIN. The app binds to every
network interface at `app.py:6013`; this makes these gaps relevant to LAN access,
not just the physical touchscreen. No CSRF validation was found in the request
hooks or forms; SameSite cookies alone do not cover every unauthenticated form
action or same-site request scenario.

Recommendation: apply one adult-session boundary to sensitive reads and writes;
require explicit first-run adult setup on production stations; add CSRF tokens
and tests for browser mutations. Keep passwordless student selection as a
deliberate family-device choice. Do not add child passwords as the default fix.
Benefit: adult-only data and controls behave consistently on the LAN and kiosk.
Effort: M. Done: unauthorized reads/actions fail, missing configuration fails
closed, and valid touch administration still works without repeated PIN entry.

### REV-003 - P1: Public family data and incomplete ignore rules

Evidence: `config/family_registry.json` tracks real names and stable UUIDs;
`cloud/family_directory.json` tracks family routing. Named screenshots and
family artwork are tracked. `.gitignore` does not ignore new runtime paths such
as `data/family_activity/`, `data/update/`, or `data/volume_settings.json` despite
the privacy guide claiming the activity directory is ignored. No data files
are currently tracked under `data/`, but future broad staging can include them.

Recommendation: finish the documented private-registry migration, verify all
deployed stations, then publish synthetic examples and generic artwork. Ignore
runtime data comprehensively and place fixtures outside it. Scan repository
history and images before deciding whether history cleanup is warranted.
Do not replace canonical identities on deployed stations to anonymize examples.
Benefit: protects family privacy and prevents other builders copying live IDs.
Effort: M. Done: clean public checkout contains only intentional sample data;
operational family mapping survives upgrades and restores. No exposed credential
or account compromise is asserted by this finding.

### REV-004 - P1: Backup is not yet complete station disaster recovery

Evidence: `scripts/backup_data.py:22` includes student profiles, timing, volume,
and student folders, but excludes private family registry and station config.
Its manifest lists files, not per-file hashes; restore tests exercise extraction.
The setup guide at line 496 requires manual copy-back. Loss of an SD still
requires reconstructing identity/configuration and separately provisioning keys.

Recommendation: define a recovery bundle for nonsecret station configuration,
canonical registry, student work, and essential durable queues; document separate
secret re-provisioning. Add integrity validation and a stopped-service restore
procedure with pre-restore backup and identity checks. Account for writers while
creating a backup so it represents a consistent recovery point.
Benefit: a successful backup has a proven path to a usable replacement device.
Effort: M. Done: restore to a spare SD and prove UUIDs, progress, drafts, pending
messages, and sync survive without duplicate records or replacement identities.

### REV-005 - P1: Persistence can lose or overwrite data around interruption

Evidence: `practice_progress.py:82`, `student_profiles.py:118` and `:158`, and
`app.py:3110` write important JSON directly. Invalid progress JSON is treated
as empty at `practice_progress.py:56`. The sync worker also rewrites attempt
and derived files (`scripts/student_attempt_sync.py:667`, `:727`, `:821`). Its
own lock and initial idle check do not exclude later writes by the app.
Single-threaded HTTP does not serialize a separate sync process.

Recommendation: atomic temp-file replacement, validation/quarantine of damaged
files, shared locking or append-safe merge boundaries, and explicit student
storage paths. Add interruption and app-resumes-during-sync fixtures.
Benefit: protects accumulated effort and prevents apparent progress resets.
Effort: L, staged. Done: faults at write/merge boundaries retain all confirmed
attempts and recover derived data without silently starting from empty state.

### REV-006 - P1: Release validation does not gate the deployed branch

Evidence: `.github/workflows/ci.yml:5` runs for main pushes and PRs, not direct
release/pi pushes. `tests/test_routes.py:16` catches missing dependencies and
skips its suite. Local green discovery skipped 163 tests. September 5 promotion
reached the Pi before its erroneous count assertion was discovered.

Recommendation: run required checks on the exact promoted revision, fail the
designated full-test job on unexpected skips, and publish only after success.
Keep a Pi canary before fleet rollout. Add dependency and secret scanning;
verify existing branch protections before choosing their required checks.
Use one documented promotion workflow with immutable release identifiers.
Benefit: failures surface before devices download a release, and green means
the intended suite actually ran. Effort: M. Done: deliberately broken imports
and failing tests prevent release eligibility, with visible test/skip counts.

### REV-007 - P2: Rollback and update trust need a stronger release boundary

Evidence: `scripts/update_station.sh:235` changes the active checkout before
validation. Migrations and installed service helpers can change before health
checks, but rollback mainly resets Git and restarts the app. Existing rollback
is valuable, but does not establish transactional restoration of migrated data
or previously installed service definitions. Release signature verification is
not present. Dependency installation is not part of this updater either.

Recommendation: stage code and validate it before activation; define backward
compatible migrations and rollback of runtime helpers. Specify how dependency
changes are delivered. Add trusted immutable release manifests or signatures
after the gated promotion path is stable.
The September 7 canary also showed that updater changes take effect in the
installed wrapper only after the first run; an already-current second pass was
needed to apply newly added app-unit installation logic. Remove this one-run
lag as part of the staged activation design.
Benefit: future changes to dependencies, storage, or services do not strand a
remote station. Effort: L. Done: failed migration/helper/health rehearsals restore
a known working combination of code, services, and compatible data.

### REV-008 - P2: Code organization increases maintenance and rebuild risk

Evidence: `app.py` is 6,018 lines and `static/app.js` 2,625. Request setup changes
module-level progress/attempt paths (`app.py:119`). GPIO initializes at import.
An additional unlock table exists in `practice_progress.py:27`. The app uses the
Flask development server and service files have no sandboxing directives.

Recommendation: incremental extraction of pure curriculum/scoring, student
storage, hardware/audio, and administration modules; document invariants beside
their owners. Introduce app creation with injectable hardware for development.
Only switch to a concurrent production server after removing shared-request
state hazards. Harden services while preserving GPIO/audio/desktop permissions.
Benefit: contributors can reason about changes and test without a live Pi.
Effort: L, several small deliveries. Done: two student contexts cannot share
storage state and domain tests run without hardware side effects.

### REV-009 - P2: Specs mix historical rollout, delivered behavior, and rebuild goals

Evidence: README's next focus still proposes adding an IoT command already
implemented. `specs/STATUS.md` still says Astrid needs checkout recovery despite
September 5 completion, and refers to an approximately 3,180-line app. The
rebuild roadmap describes implementing features already delivered in legacy.
These are useful historical records but an ambiguous current build contract.

Recommendation: current support matrix and prioritized backlog separate from
the dated journal; clearly label implemented behavior versus future rebuild
requirements. Refresh the documentation release stamp and API/requirement
traceability. Add a contributor guide covering development setup, test runtime,
storage ownership, GPIO/audio boundaries, and release promotion.
Benefit: builders know what exists and contributors know what must be preserved.
Effort: M. Done: an outside reader can identify the supported setup, current
behavior, open requirements, and next work without mining old daily logs.

### REV-010 - P2: Independent AWS deployment remains too family-specific

Evidence: root station example defaults to this project's bucket, tracked family
directory supplies this family's routes, rollout tooling defaults to old LAN
addresses, and AWS guides span multiple manual deployment phases. Templates are
useful but do not constitute a parameterized fresh-account installation.

Recommendation: separate standalone/offline setup from optional family-cloud
setup. Generate new family identities, station config, and routing from one
private input. Provide repeatable AWS infrastructure deployment with bounded
station roles and a verification command for backup, messaging, and IoT.
Benefit: a new builder owns an independent family environment without editing
our identities throughout the source. Effort: L. Done: a new family deploys
to a separate account/bucket with no dependency on luminerdy resources.

## Recommended delivery sequence

1. Close adult-route gaps and prevent accidental publication of runtime data.
2. Repair the supported setup/release instructions and CI promotion gate.
3. Prove spare-SD recovery; then strengthen atomic persistence and sync exclusion.
4. Complete public example anonymization after private-registry verification.
5. Produce a generic standalone installer and have an outside builder rehearse it.
6. Extract code incrementally and make optional AWS setup reproducible.
7. Resume feature backlog: learned-name words and further message/game refinements.

Continue observing real home-network updates and sync in parallel. Existing
successful back-and-forth messages do not need to be repeated merely to count
them as tested; delayed offline delivery and actual remote update completion
are separate operational evidence. No new fleet jobs were created in this review.
