import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "morsepi-message-router.zip"
FILES = [
    ROOT / "cloud" / "__init__.py",
    ROOT / "cloud" / "lambda_function.py",
    ROOT / "cloud" / "message_router.py",
    ROOT / "message_cloud.py",
    ROOT / "message_store.py",
    ROOT / "student_identity.py",
    ROOT / "config" / "family_registry.json",
    ROOT / "morse.py",
]


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in FILES:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(OUTPUT)


if __name__ == "__main__":
    main()
