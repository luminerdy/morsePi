# Storage Recovery

The station preserves damaged JSON instead of replacing it with empty progress.
If it reports stored data needs recovery, stop the app and sync/message workers
before repairing or restoring data. Back up the current data directory first.

Each malformed JSON file remains in place. A byte-identical copy is saved under
its sibling `quarantine/` directory with a content digest. Restore the affected
file from a verified backup, or rebuild derived progress from validated attempt
logs. Do not delete student history to dismiss the error.

A torn final JSONL record blocks new appends. Preserve the entire file before
recovering its complete records; inspect the incomplete record rather than
assuming it was already synchronized. Sync refuses malformed logs.

The `.storage.lock` file is permanent. Linux/Windows releases ownership when
the process exits. A normal busy response means retry shortly; never delete
the lock file while processes are running, which would defeat exclusion.

Atomic replacement protects one file at a time. A power failure during several
replacements can leave derived summaries behind the attempt logs. Pre-sync
backups and a subsequent validated rebuild remain the recovery mechanism.
The remaining migration and standalone administrative tools should run with
the app stopped until they explicitly participate in the station transaction.
