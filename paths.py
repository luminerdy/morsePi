import os
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent


def data_dir():
    configured = os.environ.get("MORSE_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    return APP_ROOT / "data"


def data_path(*parts):
    return data_dir().joinpath(*parts)

