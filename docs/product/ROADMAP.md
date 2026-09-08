# Product Roadmap

Status: family pilot. Updated 2026-09-08.

This is the prioritized forward plan. Requirements live in
[specs](../../specs/README.md), delivery history in the
[changelog](../../CHANGELOG.md), and detailed evidence in the
[project log](../PROJECT_PLAN.md).

## Now: Trustworthy Household Stations

| Priority | Outcome | Completion evidence |
|---|---|---|
| P0 | Verify remote rollout of the latest security/storage work | Both deployed stations confirm the expected commit and healthy services; queued jobs are not completion |
| P1 | Someone else can build and recover a station | Fresh spare-SD rehearsal follows published instructions, verifies key/audio/LED/touch, and restores a backup without losing identities or attempts |
| P1 | Updates fail safely | Exercise failed migration, interrupted activation, health-check failure, and rollback; coordinate migrations and consistent backups with app/sync writers |
| P1 | A clear product front door | Audience guides, current-versus-planned requirements, historical-document labels, and checked links; first navigation pass delivered September 8 |

## Next: Repeatable Releases

- Confirm package-aware updater adoption on every station, then retire temporary
  root import bridges. The domain package migration is implemented; do not remove
  compatibility files while older fleet updaters still check those paths.

- Define the first numbered pilot release after the installation/recovery
  rehearsal; publish exact revision, compatibility, known issues, and recovery steps.
- Apply the [release policy](RELEASES.md) to manual release preparation before
  adding automation. Do not silently change existing device update behavior.
- Consolidate overlapping guides one subject at a time, with redirects or
  updated links. Review public screenshots/assets for privacy before reuse.
- Close remaining maintenance-writer and multi-file recovery gaps described
  in NFR-006. Atomic individual files do not make a multi-file transaction.

## Later: Learning and Communication

- Continue message composition/keying improvements based on family testing.
- Consider student names as practice words once their letters are available.
- Expand encouragement-focused family visibility without competitive rankings.
- Revisit code modularization using the rebuild plan when supported by tests;
  no wholesale rewrite is required for this documentation transition.

Public web hosting, paid fleet-management alternatives, and broad hardware
support are deferred. Existing detailed ideas remain in the historical log;
inclusion there is not a delivery commitment.
