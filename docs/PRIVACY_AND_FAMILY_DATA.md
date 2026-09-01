# Privacy And Family Data

MorsePi uses real student identities on deployed family stations so progress,
messages, and cross-station sync can match the same person everywhere. Those
real identities should live in station-local data, not in public examples.

## Private Files

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
