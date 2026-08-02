# Cloud Messaging Design

## Purpose

Phase 7B carries the existing local Morse message experience between family
stations without requiring both Raspberry Pis to be online at the same time.
S3 is the durable transport. A small validator/router copies accepted records
between station-owned prefixes. AWS IoT is not required for delivery.

## Trust Boundary

Each Pi keeps its current station-specific AWS credential. A station can read
and write only `stations/<its-station-id>/` and can read the sanitized
`family/` prefix. It cannot read another station's backups, messages, or raw
progress data.

Messages uploaded by a station are untrusted until the cloud router verifies:

- the object path and payload agree on station and message IDs;
- sender and receiver are in the family directory;
- the sender is allowed to use the originating station;
- text, word, and letter limits pass the server rules;
- `required_letters` exactly matches the normalized text; and
- every required letter is present in both students' current family summaries.

The receiving Pi validates the immutable message again before creating a local
inbox copy. Morse is always recomputed from plaintext and is never trusted from
the cloud.

## S3 Layout

```text
stations/<station-id>/
  snapshots/students/<student-id>.json
  messages/outbox/<message-id>.json
  messages/inbox/<student-id>/<message-id>.json
  messages/receipts/outgoing/<student-id>/<message-id>/<state>.json
  messages/status/sent/<message-id>/<state>.json
  messages/status/received/<student-id>/<message-id>/<state>.json

family/
  messaging/directory.json
  student-summaries/<student-id>.json
```

The router writes inbox and status copies only. Its output paths do not overlap
the outbox or outgoing-receipt inputs, preventing recursive routing.

## Delivery Flow

1. Sending freezes a local `morsepi-message-v1` record in the student's outbox.
2. The station sync worker uploads an immutable cloud envelope to its outbox.
3. S3 invokes the router for the station prefix.
4. The router validates the message and copies it to every approved station
   that hosts the receiver.
5. Each receiving station downloads the same message ID idempotently.
6. Opening or decoding creates a deterministic receipt in that station's
   outgoing-receipt path.
7. The router copies validated state to the sender and to the receiver's other
   approved stations.
8. Stations apply only forward state transitions: queued, available, opened,
   decoded.

Repeated uploads, S3 events, downloads, and receipts produce the same object
keys and must not create duplicate inbox entries, celebrations, or effort.

## Learning Summaries

Each station publishes only stable student ID, active letters, curriculum
version, station ID, and generated time. The router unions current snapshots
from approved stations and publishes one sanitized family summary. No display
name, scores, attempt history, timing, or ranking is included.

If a summary is missing, stale, or does not contain all required letters, the
message remains queued and the child sees a friendly Try Later status. The
technical reason is retained in station/router logs.

## Operation

The station worker runs shortly after boot and every five minutes. It is safe
to run manually. Cloud sync is disabled unless `message_sync_enabled` is true
in the station configuration, so the local message experience remains usable
during development and AWS outages.

The first deployment rehearsal uses all three stations on the local network:
send, power the receiver off, route the message, power it on, download exactly
one copy, decode it, and verify the decoded receipt reaches the sender and the
receiver's other station.
