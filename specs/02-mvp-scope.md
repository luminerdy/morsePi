# 02 — MVP Scope

The MVP is the smallest station a child can learn from and an admin can safely
leave unattended.

## In scope (MVP)

- Text→Morse and Morse→text conversion
- Physical key input on GPIO with live decode in the browser
- Morse playback through USB speaker and LED, with configurable Farnsworth timing
- One student profile, **Send** and **Listen** practice for the starter letter
  set (E, T, A, N, I, M)
- Per-letter progress persistence and a simple progress page
- Local daily backup with rotation
- Hardened service deployment (systemd + production WSGI server)
- **All SEC-\* requirements marked *(MVP)*** — security is not a later phase
  (see [06-security-requirements.md](06-security-requirements.md))

## Out of scope for MVP (V1/V2)

Delivered in later tiers per [03-feature-inventory.md](03-feature-inventory.md):

- Multi-student profiles, guest mode
- Read / Echo / Learn practice modes
- Letter-unlock curriculum gates
- Touchscreen flow
- Daily missions, badges, coach, effort tracking
- Word practice, bonus sprint
- Session recovery admin
- S3 sync, status reporting
- Unattended auto-update

## Rationale

The current repo's `archive/led_morse.py` (83 lines) shows the true original
MVP: convert, blink, beep, key. The rebuild MVP adds only what unattended
deployment demands (persistence, backup, hardening) so one station can run the
rebuilt code as a daily driver as early as possible (see
[12-rebuild-roadmap.md](12-rebuild-roadmap.md), Phase 3 exit).
