# Privacy And Family Data

MorsePi uses real student identities on deployed family stations so progress,
messages, and cross-station sync can match the same person everywhere. Those
real identities should live in station-local data, not in public examples.

## Private Files

Important: ignored live data does not mean the whole repository is anonymous.
The tracked fallback registry still contains deployed identities, and historical
docs/tests/configuration include family names. Earlier screenshots exposed names
and progress; the July screenshot set and unused portrait concepts were removed
from the current tree on 2026-09-08. Git history still retains them.

### Cleanup Status - 2026-09-08

- No live files under `data/` are tracked.
- The local station's private registry was confirmed present over SSH.
- Latest remote backup evidence, dated September 6 and August 29, respectively,
  contains no `data/family_registry.json`. This is not proof of current device
  absence, but is insufficient evidence to replace the public fallback.
- Pending package-update jobs run the registry migration. After reconnection,
  inspect a new backup for a valid private registry before anonymizing it.
- Active boot/desktop assets remain deployed resources and use family-derived
  cartoon artwork. Replace public defaults with generic artwork in a separate
  compatibility-safe change; do not remove installer source assets blindly.
- No history rewrite or force-push has been performed. That requires a separate
  coordinated decision for clones and deployed branches, and cannot guarantee
  deletion of externally retained copies.

### Remaining Sequence

1. Confirm private registries from each remote station after its update.
2. Move family station lists out of operational defaults into private config;
   ensure status/activity/sync and policy tooling consume that config.
3. Make cloud packaging accept the private deployment registry rather than
   accidentally shipping fictional identities to the existing family router.
4. Replace public registry, configuration examples, tests, documentation names,
   UUIDs, and station identifiers with a consistent fictional family.
5. Review remaining images and printable artifacts visually; publish only sample
   progress and generic artwork. Decide separately about repository history.

Do not change live student IDs or UUIDs as an anonymization shortcut.

These files are station-specific and ignored by Git:

- `data/station_config.json`
- `data/family_registry.json`
- `data/students/`
- `data/student_profiles.json`
- `data/backups/`
- `data/family_activity/`

`data/family_registry.json` is the preferred registry for real family student
IDs, display names, and UUIDs. The tracked `config/family_registry.json` remains
as a fallback until every deployed station has copied its real registry into
`data/family_registry.json`.

## Safe Anonymization Sequence

1. Deploy the private-registry migration to every station.
2. Confirm each station has `data/family_registry.json`.
3. Confirm practice, messaging, backup, and sync still work.
4. Replace tracked examples, docs, screenshots, and tests with sample names.
5. Keep real names, real UUIDs, and real family rosters only in ignored
   station-local files.

Do not replace `config/family_registry.json` with sample data until deployed
stations have completed step 2. Otherwise identity checks may lose the canonical
UUID mapping for existing student progress and messages.

## Screenshot Guidance

Screenshots committed to GitHub should use sample operator names such as
`Alex`, `Jordan`, `Taylor`, `Morgan`, and `Riley`. Network screenshots should
use sample values such as `Home-WiFi`, `Station-01`, and `192.168.x.x`.

If a screenshot was captured from a real station, review it visually before
committing. Text search cannot detect names or Wi-Fi details inside images.

## Family Activity Feed

The Pappy-only activity feed stores operational milestones, not student work.
Its cloud events may contain stable station/student IDs needed to explain a
message route, but they exclude student display names, message text, attempt
answers, raw key timing, rhythm samples, credentials, and admin PINs. Display
names are resolved locally on Pappy after the adult unlocks the view.
