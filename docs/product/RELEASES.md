# Release Policy

This is the manual policy for future numbered releases, not new updater code.
No numbered product release is claimed by this documentation change.

## Current Channels

- `main`: integrated development and current documentation.
- `release/pi`: station deployment branch. Keep its exact revision stable while
  pending IoT jobs expect that commit, or explicitly supersede those jobs.
- Station reports and IoT execution receipts establish installed versions.
  GitHub branch position alone does not establish fleet completion.

## First Numbered Pilot Release

Use a `v0.x.y` tag only after selecting and verifying a release commit. Future
release notes must include:

1. Exact commit, supported Pi/OS/display configuration, and test results.
2. User-visible improvements and known limitations.
3. Configuration or data-migration changes and backup requirements.
4. Upgrade steps, health checks, rollback limits, and recovery instructions.
5. Canary result and separately reported remote rollout status.

Before tagging: pass CI without skips, rehearse fresh installation and recovery,
check documentation links, and verify the candidate on a physical canary station.
Do not claim software rollback can reverse every data migration. Document when
a verified pre-update backup is required.

Tag the tested code revision, not an arbitrary later documentation commit.
Create GitHub release notes from the [changelog](../../CHANGELOG.md). Signed
artifacts, tag-based device selection, and automated publishing require separate
implementation and security review; they are not enabled by this policy.
