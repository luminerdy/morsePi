# Family Activity

The Pappy station provides a private, read-only Family Activity screen for
checking whether each MorsePi is communicating successfully. This view favors
operational confirmation over comparison between students: it does not rank
students, show message text, or expose detailed practice timing.

## What it shows

- station check-in time and installed commit
- successful or failed software-update results
- confirmation that new practice records were uploaded
- message sent, received, opened, and decoded milestones

The screen is available from **Admin System > Activity** on Pappy and requires
the adult admin PIN on every visit. The event list can be filtered by Updates,
Progress, Messages, or Problems.

## Cloud contract

Each station writes immutable, privacy-limited events below its own prefix:

```text
stations/<station-id>/activity/YYYY/MM/DD/<event-id>.json
```

Event IDs are deterministic, so retrying an upload does not duplicate the
event. Events contain station and student identifiers where needed, but never
message text, student display names, raw key timing, rhythm samples, AWS
credentials, or admin PINs.

The station queues events under `data/family_activity/pending/` while offline.
The next progress, message, or status sync retries them. Successfully uploaded
events move to `data/family_activity/sent/`.

Pappy reads the three family activity/status prefixes into
`data/family_activity/cache.json`. A failed station refresh preserves that
station's last known cache and displays a warning rather than erasing history.

## Schedule and confirmation semantics

The standard `morse-station-sync.timer` runs approximately every 30 minutes
and now publishes station status and refreshes Pappy's activity cache. Message
events are also published by the message-sync worker on its shorter schedule.
Opening the PIN-gated Activity screen performs a fresh cloud read.

An event means the named operation reached its confirmed checkpoint:

- **Software updated**: the station completed its update and health checks.
- **Practice progress uploaded**: new immutable attempt records reached S3.
- **Message sent**: the sending station uploaded the message to its outbox.
- **Message received**: the receiving station saved the routed message locally.
- **Message opened/decoded**: the receiving station uploaded that receipt.

## Permissions

- Every station may write only its own activity prefix.
- Pappy may list/read activity and status objects for all three stations.
- Grandkid stations cannot read the family activity feed.
- No station policy grants S3 delete access.

Apply the generated policies with the setup-admin profile:

```powershell
python scripts/apply_station_sync_policies.py --profile morsepi-setup-admin
```

Email notifications remain a later, optional layer. The on-device history is
the first source of truth and does not introduce SES, Lambda, or recurring
notification cost.
