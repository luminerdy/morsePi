# Family Morse Messaging

## Current Scope

Phase 7A provides kid-friendly Morse messages between students whose progress
is available on the same station. It proves the complete learning experience
without depending on the network or AWS. Phase 7B will carry the same message
records between homes using durable cloud delivery.

Messaging unlocks after a student has unlocked Words practice (`S` and `O`).
Guest Operator cannot send or receive messages.

## Student Flow

### Compose and Send

1. Open Messages from Daily or the touch menu.
2. Choose an eligible recipient.
3. Add short known words with touch tiles, or key one complete practiced word
   and tap Add Word.
4. Tap a letter tile to replace or remove it; Undo and Clear are also available.
5. Review the letters and Morse code, then use Play to hear the message and see
   it on the station LED.
6. Tap Send.

Keyed words must already be available in Words practice, and the composer adds
the space between completed words automatically. Undo removes the most recently
added word. The message is limited to three words and 20 letters. Every letter must be
active for both the sender and receiver. The server repeats all validation at
send time so a changed or tampered draft cannot bypass these rules.

### Receive and Decode

1. Open Messages and choose an unread inbox item.
2. Tap Play Again to hear the message and watch the LED.
3. Decode one signal at a time using four large letter choices.
4. Use Hint when needed. Hints progress from slower playback, to showing the
   Morse pattern, to revealing the letter.
5. Continue until the complete message is visible.

Plaintext is hidden until each position is solved or revealed. Decoding effort,
elapsed time, attempts, and hint use are logged. Message work counts as effort
and can earn `First Message Sent` and `Secret Message Decoded` badges, but it
does not change letter mastery.

## Station Configuration

`data/station_config.json` has two separate student lists:

- `students`: operators allowed to sign in on this station.
- `family_students`: approved message recipients across the family.

In Phase 7A, a family member is eligible only when their local progress is
available and both students have unlocked messaging. A missing or stale remote
learning summary will become a friendly Try Later state in Phase 7B.

## Local Data

Messaging uses `morsepi-message-v1` records and stores data under each student:

```text
data/students/<student-id>/message_draft.json
data/students/<student-id>/message_events.jsonl
data/students/<student-id>/message_inbox/<message-id>.json
data/students/<student-id>/message_outbox/<message-id>.json
```

Writes use a temporary file and atomic replacement. Delivery is duplicate-safe
by message ID. Student reset backs up and removes this data, and normal station
backups include it because the whole `data/` tree is archived.

## Phase 7B Boundary

Phase 7A does not deliver a message to another physical station. Phase 7B will
add:

- minimal student learning summaries for eligibility checks;
- durable S3 outbox, validated inbox, and receipt objects;
- retry-safe upload and download while stations are intermittently powered;
- optional AWS IoT notifications that prompt a station to check S3;
- kid-friendly queued, available, opened, and decoded states across homes.

S3 remains the durable source of truth. IoT notifications are an optimization,
not the only delivery path.
