import argparse
from pathlib import Path
import sys
import unittest


def parse_args():
    parser = argparse.ArgumentParser(description="Run the MorsePi regression suite.")
    parser.add_argument(
        "--fail-on-skips",
        action="store_true",
        help="Fail when any test is skipped (used by release CI).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    suite = unittest.defaultTestLoader.discover(
        str(project_root / "tests"),
        top_level_dir=str(project_root),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if not result.wasSuccessful():
        return 1
    if args.fail_on_skips and result.skipped:
        print(f"ERROR: {len(result.skipped)} tests were skipped in a full-test run.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
