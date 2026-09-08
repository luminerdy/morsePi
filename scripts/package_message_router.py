import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "morsepi-message-router.zip"
FILES = [
    ROOT / "cloud" / "__init__.py",
    ROOT / "cloud" / "lambda_function.py",
    ROOT / "cloud" / "message_router.py",
    ROOT / "morsepi" / "__init__.py",
    ROOT / "morsepi" / "messaging" / "__init__.py",
    ROOT / "morsepi" / "messaging" / "message_cloud.py",
    ROOT / "morsepi" / "messaging" / "message_store.py",
    ROOT / "morsepi" / "storage" / "__init__.py",
    ROOT / "morsepi" / "storage" / "durable_storage.py",
    ROOT / "morsepi" / "storage" / "paths.py",
    ROOT / "morsepi" / "students" / "__init__.py",
    ROOT / "morsepi" / "students" / "student_identity.py",
    ROOT / "config" / "family_registry.json",
    ROOT / "morsepi" / "morse" / "__init__.py",
    ROOT / "morsepi" / "morse" / "codec.py",
]


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in FILES:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(OUTPUT)


if __name__ == "__main__":
    main()
