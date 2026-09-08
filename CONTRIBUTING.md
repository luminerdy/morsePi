# Contributing

Start with the [product roadmap](docs/product/ROADMAP.md),
[architecture](docs/ARCHITECTURE.md), and [requirements](specs/README.md).
The current app is a family pilot, not a completed rebuild.

## Develop and Test

CI currently tests Python 3.11 on Linux. Create an isolated environment and
install `requirements.txt`. For example, on Linux:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
GPIOZERO_PIN_FACTORY=mock python scripts/run_tests.py --fail-on-skips
```

On Windows PowerShell, after creating the environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GPIOZERO_PIN_FACTORY = 'mock'
.\.venv\Scripts\python.exe scripts/run_tests.py --fail-on-skips
```

Tests use temporary student data. Use a separate development checkout and
fictional profiles for manual app testing; never point experiments at a live
station's data. Mock GPIO tests do not verify actual key input, sound, LED,
touch layout, or power-loss recovery. Follow the Pi setup guide for hardware runs.

## Change Workflow

1. Describe the user benefit and scope; update the relevant requirement and
   acceptance criteria before changing behavior. Keep requirement IDs stable.
2. Make a focused change using existing patterns. Add regression tests for
   behavior, failure cases, and cross-station effects where relevant.
3. Run tests without skips and check changed documentation links.
4. Update spec status, the relevant user/admin guide, and the changelog.
   Record detailed evidence in the dated project log.
5. Submit the change for review. Deployment is a separate action following the
   [release policy](docs/product/RELEASES.md).

Do not commit credentials, PINs, private keys, actual student data, or identifiable
family screenshots. Use generic example names and station IDs. Report security
issues according to [SECURITY.md](SECURITY.md).

## Repository Boundaries

Root Python modules, `templates/`, and `static/` implement the app; `scripts/`
and `systemd/` operate stations; `cloud/` contains cloud components and policy
templates; `tests/` contains regression tests. `archive/` is reference material.
Do not move runtime files as part of documentation cleanup.
