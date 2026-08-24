# 05 — Non-Functional Requirements

- **NFR-001** *(MVP)* Target hardware: Raspberry Pi 4 (1 GB worst case),
  Raspberry Pi OS, Python ≥ 3.11. Steady-state RSS ≤ 200 MB.
- **NFR-002** *(MVP)* Key press → sidetone start latency ≤ 50 ms; key press →
  LED ≤ 50 ms. (This is the product's core feel.)
- **NFR-003** *(MVP)* Any page or JSON endpoint SHALL respond in ≤ 500 ms with
  5 students × 10,000 attempts of history. Summaries MUST NOT re-parse full
  attempt logs per request (incremental or cached aggregation).
- **NFR-004** *(MVP)* The app SHALL be correct under concurrent requests from
  ≥ 2 clients (touchscreen + remote browser): no shared mutable module state
  keyed to "the current request." *(Delta: the global-path design corrupts
  cross-student data under threads; `7818254` mitigates by forcing the dev
  server single-threaded (`threaded=False`), which serializes requests but
  leaves the root cause — the requirement stands for the rebuild, since any
  threaded WSGI server would regress.)*
- **NFR-005** *(MVP)* The app SHALL run on non-Pi hosts (dev, CI) with a null
  hardware backend selected automatically — no env-var incantations required.
- **NFR-006** *(MVP)* Power loss at any moment SHALL NOT corrupt stored state:
  all JSON writes atomic (write-temp + rename); JSONL appends are
  line-atomic; a torn final line is skipped on read, not fatal.
- **NFR-007** *(MVP)* The service SHALL auto-start on boot and auto-restart on
  crash (systemd, `Restart=on-failure`).
- **NFR-008** *(MVP)* Absence of speaker, LED, or key SHALL degrade gracefully
  (feature disabled + logged) — never crash the web app.
- **NFR-009** *(V1)* Touch UI: all tap targets ≥ 48 px, readable at 800×480,
  usable by a non-reading 5-year-old for the daily flow.
- **NFR-010** *(MVP)* Structured logging to journald: startup config summary,
  hardware detection results, every admin action, every rejected request
  (with reason).
- **NFR-011** *(V2)* A station SHALL be remotely diagnosable from its uploaded
  status document alone: app version, uptime, disk free, last backup time,
  per-student attempt counts.
- **NFR-012** *(MVP)* Kid-facing failure modes: any 4xx/5xx reachable from the
  student UI renders a friendly retry page, never a stack trace.
- **NFR-013** *(V2)* Every message compose, review, inbox, and decode screen
  SHALL fit 800x480 without page scrolling, use tap targets >= 48 px, and keep
  the active student and sender/receiver identity visible in large text.
- **NFR-014** *(V2)* A station SHALL retain queued outbound messages and
  downloaded inbox messages through restart, network loss, and power loss;
  cloud availability SHALL NOT be required to finish decoding a downloaded
  message.
- **NFR-015** *(V2)* Creating, editing, opening, or answering a local message
  SHALL meet NFR-003. Send SHALL confirm local queuing within 1 second and
  SHALL NOT block the child interface while waiting for cloud delivery.
- **NFR-016** *(V2)* The primary messaging path SHALL require no physical or
  on-screen keyboard and no reading of technical status text. Color SHALL NOT
  be the only indicator of message state or a correct/incorrect answer.
- **NFR-017** *(V1)* Kid-facing Morse SHALL render dots and dashes as
  optically centered geometric marks on one horizontal axis, with consistent
  symbol and letter spacing across Learn, practice, Words, Progress, Messages,
  live key displays, and printable student materials. Canonical stored,
  transmitted, and compared Morse SHALL remain ASCII `.` and `-`. The visual
  renderer SHALL expose an accessible dot/dash text label. Student-facing
  feedback text SHALL NOT embed raw ASCII Morse patterns in prose, because
  sentence punctuation can be confused for Morse dots.
- **NFR-018** *(V1)* A deployed station SHOULD show morsePi branding during
  boot and on the adult recovery desktop. Boot branding SHALL use a static
  Plymouth-compatible image, keep a restorable copy of the original OS splash,
  and not add a new boot dependency that can block app startup.
- **NFR-019** *(V2)* Remote maintenance for three family stations SHOULD stay
  below `$1/month` in normal use, excluding S3 storage/transfer and optional
  human-troubleshooting services. The preferred update trigger SHALL be AWS IoT
  Jobs or an equally low-cost outbound polling mechanism whose cost is driven
  by occasional remote actions, not by a fixed per-device monthly fee. Systems
  Manager or another fixed monthly remote-admin service MAY be used only as an
  explicit temporary troubleshooting choice, with the expected per-device cost
  documented before activation.
- **NFR-020** *(V1)* The idle screensaver SHALL remain smooth and fully visible
  at 800x480, keep its letter and Morse pattern inside the viewport at every
  allowed position, and avoid storing or displaying student names, progress,
  messages, or other personal data. Its timers and animation SHALL add no
  server-side dependency and negligible steady-state CPU use; physical-keyer
  polling MAY run only while the screensaver is visible.
- **NFR-021** *(V1)* An unexpected Chromium exit on a logged-in station SHALL
  return to the kiosk automatically within 15 seconds without restarting the
  Morse app, changing student data, or requiring a keyboard. Browser startup
  failures and restart attempts SHALL be retained in the user journal for
  remote diagnosis, and repeated failures SHALL not create multiple kiosk
  processes.
