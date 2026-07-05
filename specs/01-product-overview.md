# 01 — Product Overview

- **Product name:** Pappy's Internet Telegraph (morsePi)
- **Spec status:** Draft v1.0 for rebuild — supersedes behavior implicit in the legacy Flask app.
- **Package index:** [../README.md](../README.md)
- **Legacy compliance status:** [STATUS.md](STATUS.md)

## What it is

A Raspberry Pi–based Morse code learning station for children, deployed as
unattended kiosks in family members' homes ("grandkid stations") and
administered remotely by one maintainer ("Pappy").

## Users

| User | Description | Trust level |
|---|---|---|
| **Student (child, ~5–12)** | Practices Morse via a physical telegraph key, touchscreen, or browser. | Cannot be trusted to configure anything; must not be able to destroy progress. |
| **Local adult** | Powers the station on/off, occasionally selects a student. | No technical skill assumed. |
| **Remote admin** | Deploys stations, monitors status, restores data, ships updates. | Full trust; never has physical access after deployment. |

## Value proposition

Immediate multi-sensory feedback (tone, LED, on-screen decode) plus a gated
curriculum that introduces letters gradually and rewards consistent effort,
not just accuracy.

## Deployment reality that shapes everything

The device sits on someone else's home LAN, runs unattended for months, has
1–4 GB RAM, and is used by children — so it must be:

- **Safe by default** — see [06-security-requirements.md](06-security-requirements.md);
  the LAN is treated as untrusted.
- **Self-healing** — survives power loss, crashes, and missing peripherals
  (see NFR-006, NFR-007, NFR-008).
- **Remotely observable** — diagnosable from uploaded status documents alone
  (see NFR-011).

## Current hardware target

- Raspberry Pi 4, Raspberry Pi OS
- TGKY01 telegraph key (or similar switch) on GPIO17
- Status LED with resistor on GPIO27
- USB speaker (ALSA device)
- Optional 7-inch touchscreen (800×480)
