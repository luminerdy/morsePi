# 06 — Security Requirements

Threat model context: kid-facing kiosk on an **untrusted home LAN**, remotely
administered, holding children's data. Security requirements tagged *(MVP)*
ship with the MVP — they are not a later hardening phase. Full threat model
belongs in the rebuilt repo's `SECURITY.md` (DOC-04).

- **SEC-001** *(MVP)* All state-changing endpoints SHALL require a CSRF token.
  No exceptions for "it's just a kiosk."
- **SEC-002** *(MVP)* Admin PIN SHALL be mandatory (refuse to start admin
  features without one), compared with `secrets.compare_digest`, and never
  logged. *(Delta: legacy still allows optional-and-blank PIN for development,
  but configured PINs use constant-time comparison.)*
- **SEC-003** *(MVP)* PIN attempts SHALL be rate-limited: ≥ 5 failures in
  15 min locks admin actions. *(Delta: legacy now applies an in-memory
  60-second lockout after 5 failures in 15 minutes; persistent logging and a
  longer production lockout remain open.)*
- **SEC-004** *(MVP)* All user input SHALL be length-capped and validated
  server-side before processing (see FR-012; student names ≤ 40 chars;
  PIN ≤ 32; request bodies ≤ 16 KB). *(Status: largely implemented in legacy
  at `7818254` — see STATUS.md; rejection-vs-truncation semantics per
  FR-012 remain open.)*
- **SEC-005** *(MVP)* Redirect targets from request parameters SHALL be
  accepted only if they are same-origin relative paths (`/…` and not `//…`);
  otherwise fall back to a default route. Applied uniformly — one helper, no
  direct `redirect(request.form[...])`. *(Status: implemented and tested in
  legacy at `7818254`.)*
- **SEC-006** *(MVP)* The app SHALL run behind a production WSGI server
  (waitress/gunicorn), never the Flask dev server; `debug` mode SHALL be
  impossible in the deployed unit file.
- **SEC-007** *(MVP)* The systemd unit SHALL sandbox the service: dedicated
  non-login user, `NoNewPrivileges=yes`, `ProtectSystem=strict`,
  `ProtectHome=read-only`, `ReadWritePaths=` limited to the data directory,
  no shell.
- **SEC-008** *(MVP)* The web app SHALL bind to LAN by design but treat the
  LAN as untrusted: destructive actions (reset, session recovery, settings)
  require the PIN; purely kid-safe actions (practice, playback within caps)
  do not.
- **SEC-009** *(MVP)* Subprocess invocations (`aplay`, `speaker-test`, `aws`)
  SHALL use argument arrays only (no shell), with all variable arguments
  validated; audio child processes SHALL be reaped with timeouts (no zombie
  accumulation).
- **SEC-010** *(V2)* The update channel SHALL verify a signed git tag (or at
  minimum a pinned release branch from a repo with branch protection +
  required review) before applying; the trust model SHALL be documented
  (DOC-04 `SECURITY.md`). *(Status: legacy `5e835d3` pins `release/pi` and
  adds a post-restart health check; signing/branch-protection verification
  and rollback still open.)*
- **SEC-011** *(V2)* S3 credentials SHALL be per-station IAM with write-only
  access to that station's prefix; no long-lived admin keys on devices.
- **SEC-012** *(V2)* Uploaded data SHALL minimize child PII: student display
  names MAY be uploaded only with explicit config opt-in; default uploads use
  student IDs only. Family message text MAY be uploaded only for the messaging
  feature, SHALL be restricted to configured family recipients, and SHALL
  follow the retention rules documented in `SECURITY.md` and DOC-13. Tracked
  examples, documentation screenshots, and public rebuild artifacts SHOULD use
  sample names and sample network values instead of real child names, home
  SSIDs, or local IPs.
- **SEC-013** *(MVP)* Cookies: `SameSite=Lax`, `HttpOnly` for session/student
  cookies; session IDs from `uuid4`, validated as 32-hex on receipt.
- **SEC-014** *(MVP)* Secrets (PIN, any future tokens) SHALL live outside
  git — env file or `data/` — with examples containing placeholders only; CI
  SHALL run a secret scanner.
- **SEC-015** *(MVP)* Dependencies SHALL be audited in CI (`pip-audit`) and
  auto-update PRs enabled (Dependabot/Renovate).
- **SEC-016** *(V2)* Students SHALL send only to recipients in the configured
  family directory. The guest profile SHALL have no message pages, APIs,
  inbox, outbox, or cloud permissions.
- **SEC-017** *(V2)* Each station SHALL use its own AWS identity with least
  privilege: write only its designated outbox, read only inboxes for students
  rostered on that station, and read/write only the receipt paths required for
  those students. No station SHALL list or read another family's unrelated
  message content.
- **SEC-018** *(V2)* The server and cloud router SHALL independently validate
  sender, receiver, roster membership, content limits, allowed characters,
  and the sender/receiver active-letter intersection. Client-supplied Morse,
  delivery state, timestamps, and learned-letter claims SHALL not be trusted.
- **SEC-019** *(V2)* Message IDs SHALL be unguessable UUIDs. Message objects
  SHALL be immutable after acceptance; state changes and receipts SHALL be
  separate append-only or versioned records with sender station and UTC time.
- **SEC-020** *(V2)* Cloud message records SHALL contain stable student IDs,
  not display names, and SHALL not include practice history or detailed
  progress. The minimum active-letter snapshot needed for validation MAY be
  synchronized separately under SEC-012 handling rules.
- **SEC-021** *(V2)* Cross-station records SHALL validate any supplied student
  UUID against the canonical family registry. A UUID/legacy-ID conflict SHALL
  fail closed before upload, merge, delivery, or receipt processing. UUIDs are
  identifiers, not secrets, and SHALL not grant authorization by themselves.
- **SEC-022** *(V2)* Remote maintenance through AWS IoT SHALL use one Thing
  identity per station and least-privilege permissions scoped to that station's
  Jobs data-plane operations. A station SHALL be able to read and update only
  its own pending job executions and SHALL NOT receive permission to manage IoT
  resources, IAM, S3 bucket policy, Lambda, or arbitrary command execution.
  Job documents SHALL contain only declarative action names and optional
  validated parameters; no command line or script body from AWS SHALL be
  executed.
- **SEC-023** *(V2)* A station SHALL write activity events only below its own
  station prefix. Only the designated family activity reader SHALL list or read
  other approved station activity and status prefixes. Activity records and the
  Pappy cache SHALL omit message text, student display names, raw attempts,
  timing events, credentials, PINs, network names, and IP addresses. The Family
  Activity touch page SHALL require the adult PIN before any cached or cloud
  activity data is rendered.
