# morsePi

**Learn Morse code. Practice with a real telegraph key. Send messages to family.**

morsePi, also known as Pappy's Internet Telegraph, is a Raspberry Pi learning
station designed for children and families. A touchscreen, physical key,
speaker, and LED make learning hands-on without requiring a keyboard.

Students build from letters to words and family messages. Daily missions,
guided practice, warm-ups, games, and progress feedback encourage consistent
effort, not just perfect scores.

## Start Here

| I want to... | Start with... |
|---|---|
| Build a station | [Parts, wiring, and installation](docs/getting-started/README.md) |
| Learn or help a student | [Student and family guide](docs/user-guide/README.md) |
| Maintain a station | [Administration and recovery](docs/administration/README.md) |
| Understand the system | [Architecture and AWS](docs/architecture/README.md) |
| Improve the project | [Contributing](CONTRIBUTING.md) and [requirements](specs/README.md) |
| See what is next | [Product roadmap](docs/product/ROADMAP.md) |

## The Experience

- **Learn and practice:** Learn, Send, Read, Listen, and Echo reinforce different
  skills; guided progression introduces new letters alongside familiar ones.
- **Make it meaningful:** key whole words, build and review messages, and decode
  messages from family members.
- **Keep going:** Daily Mission, warm-up, Signal Sprint, Signal Drop, and progress
  views offer different ways to practice.
- **Share a station:** separate student profiles keep practice histories apart;
  an adult PIN protects administration.

## Standalone or Connected

**Standalone:** local learning and practice work without AWS or an internet
connection. Student data stays on the station; local backup tools are included.

**Connected family stations:** optional AWS services provide off-site backups,
progress synchronization, message delivery, activity reporting, and remote
software updates. Cloud services require separate setup and may incur charges.
Offline stations reconnect to exchange pending data; delivery is not immediate
or guaranteed while a station remains offline.

## Hardware and Readiness

The current target is a Raspberry Pi 4 running Raspberry Pi OS, an 800 x 480
7-inch touchscreen, a straight telegraph key, USB speaker, and LED with resistor.
See the [bill of materials](docs/BILL_OF_MATERIALS.md) for budget and optional
hardware choices, and the [setup guide](docs/SETUP_AND_CONFIGURE_PI.md) for wiring.

The product is in **family pilot use**, with automated regression tests and
working remote services. It is not yet a certified appliance or a public hosted
service. Fresh-SD recovery rehearsal and further update/rollback hardening remain
on the [roadmap](docs/product/ROADMAP.md). GPIO and sound still need real-hardware
testing in addition to automated tests.

## Project Resources

- [Documentation index](docs/README.md)
- [Changes](CHANGELOG.md) and [release policy](docs/product/RELEASES.md)
- [Security](SECURITY.md) and [privacy](docs/PRIVACY_AND_FAMILY_DATA.md)
- [Requirements and implementation status](specs/README.md)

The code remains in the existing root Python modules, with `templates/`,
`static/`, `tests/`, `scripts/`, `systemd/`, and `cloud/` supporting the station.
Documentation navigation does not change installation paths.

Licensed under the [MIT License](LICENSE).
