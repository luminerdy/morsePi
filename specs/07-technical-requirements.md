# 07 — Technical Requirements

- **TR-001** Language/framework: Python ≥ 3.11, Flask 3.x, app-factory
  pattern (`create_app(config)`), blueprints per surface (home, practice,
  touch, admin).
- **TR-002** Package layout SHALL use a `morsepi/` package with `hardware/`,
  `learning/`, and `web/` subpackages; `pyproject.toml` SHALL pin runtime
  dependencies and expose a `dev` extra (ruff, pytest, pip-audit).
- **TR-003** Hardware access SHALL go through an interface (`Hardware`
  protocol: `key_events()`, `led_on/off`, `play_tone`, `play_samples`,
  `stop`) with three implementations: gpiozero-backed, mock (tests), null
  (dev). gpiozero SHALL be imported only inside the Pi implementation.
- **TR-004** Audio synthesis SHALL not build per-sample Python lists; use
  `array`/`numpy` or precomputed dot/dash/gap sample blocks concatenated per
  message.
- **TR-005** Configuration SHALL come from exactly one station config file
  (JSON, schema-validated at startup) plus environment overrides; startup
  SHALL fail loudly on invalid config, listing the errors.
- **TR-006** All persistence SHALL go through a `StudentStore` object holding
  the student's paths — constructed per request from the cookie, never via
  module globals.
- **TR-007** WSGI: single worker process, small thread pool; anything owning
  hardware state (key decoder, audio process handle) lives in one supervisor
  object guarded by its own lock.
- **TR-008** External binaries (`aplay`, `speaker-test`, `aws` when
  configured) SHALL be detected at startup; missing binaries disable their
  feature with a logged warning (ties to NFR-008). *(Status: legacy
  `7818254` added `scripts/check_dependencies.py` as a manual preflight
  check — keep the CLI, but the rebuild also performs detection at app
  startup.)*
- **TR-009** Time handling: all stored timestamps UTC ISO-8601; "calendar
  day" logic (missions, group limits) uses the station's local timezone from
  config.
- **TR-010** Frontend: server-rendered Jinja + vanilla JS; JS split by
  surface (`practice.js`, `touch.js`, shared `keyer.js`); no build step
  required.
- **TR-011** CI (GitHub Actions): ruff check + format, pytest with coverage
  gate (≥ 80% on `learning/` and `morse.py`), pip-audit, secret scan; runs
  on PR and main.
- **TR-012** Versioning: the app exposes its version + git SHA at `/healthz`
  for the updater's health check (FR-035).

## Target package layout

```
morsepi/
├── pyproject.toml
├── morsepi/
│   ├── __init__.py             # create_app() factory
│   ├── config.py               # ONE config loader (station json + env), validated
│   ├── morse.py
│   ├── hardware/
│   │   ├── gpio.py             # Key/LED behind an interface; NullHardware for dev
│   │   └── audio.py            # tone synthesis + player subprocess management
│   ├── learning/
│   │   ├── curriculum.py       # THE single unlock/progression table (FR-022)
│   │   ├── progress.py         # per-student store, path passed in (no globals)
│   │   ├── attempts.py
│   │   └── summaries.py        # badges, coach, daily mission, effort
│   ├── students.py
│   └── web/
│       ├── home.py             # blueprints: home, practice, touch, admin
│       ├── practice.py
│       ├── touch.py
│       └── admin.py
├── templates/  static/
├── scripts/                    # backup, status, update
├── deploy/                     # systemd units + install docs together
├── tests/
└── docs/
    └── journal/                # frozen legacy planning docs
```
