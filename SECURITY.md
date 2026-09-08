# Security And Family Data

## Scope

morsePi stores learning and family-message data for children. The stations are
private family devices, not public accounts. Children choose a preconfigured
operator name and do not use passwords.

## Data Stored Locally

- stable student ID and display name;
- practice progress, attempts, timing, and rhythm summaries;
- learning state, daily effort, badges, and session-recovery records;
- message drafts, immutable sent/received text, decode state, and effort events;
- station configuration, timing settings, backups, and operational status.

## Data Sent To AWS

- encrypted private station backups and operational status;
- stable station and student IDs;
- minimal active-letter summaries with curriculum version and generated time;
- family message text, required letters, sender/receiver IDs, and timestamps;
- message-state receipts containing IDs, state, station, and timestamp.

Display names, detailed practice history, raw key timing, scores, and rankings
are not included in cloud message or learning-summary records. Morse code is
derived locally and is not authoritative cloud data.

## Access Controls

- S3 public access is blocked, default encryption and versioning are enabled.
- Every Pi uses a unique least-privilege IAM identity.
- A Pi reads/writes only its station prefix and reads sanitized family records.
- Only the cloud router can copy accepted records between station prefixes.
- Guest Operator cannot send, receive, or synchronize messages.
- Adult actions remain protected by the local admin PIN.
- Browser forms and background write requests require a signed, browser-bound
  CSRF token. A restart invalidates open-page tokens; reload before retrying.
  Rejected actions are never automatically replayed.
- Five failed PIN attempts within 15 minutes block new admin authentication
  for 15 minutes, including across restarts. Private `data/admin_lockout.json`
  stores only failure times and expiry. A damaged file fails closed; the station
  owner can remove that file locally over SSH and restart to recover access.
  This local security state is not synchronized between stations.

## Retention And Recovery

Messages remain available as family learning records until an adult resets or
deletes the student's data. S3 versioning and backups may retain prior copies
for recovery. Before a student reset, the station creates a timestamped backup.
An adult may remove a student's local data, cloud messages, summaries, receipts,
and backup versions when deletion rather than recovery is intended.

## Incident Response

If a station or credential is lost, deactivate that station's access key,
create a replacement key only for the same station policy, inspect S3 access
and message records, and rebuild the Pi from the documented setup process. Do
not place AWS keys, admin PINs, child data, or account identifiers in GitHub.
