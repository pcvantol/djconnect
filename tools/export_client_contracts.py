#!/usr/bin/env python3
"""Export DJConnect client contract fixtures for client repository tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "examples" / "client_contracts"
SOURCE_MANIFEST = "contract_manifest.json"
EXPORTED_MANIFEST = "manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        help="Directory that should receive the client contract fixtures.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing JSON/README files in the output directory before exporting.",
    )
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    manifest = json.loads((SOURCE_DIR / SOURCE_MANIFEST).read_text(encoding="utf-8"))
    fixture_files = [entry["file"] for entry in manifest["fixtures"]]
    files = ["README.md", *fixture_files]

    output.mkdir(parents=True, exist_ok=True)
    if args.clean:
        for pattern in ("*.json", "README.md"):
            for path in output.glob(pattern):
                if path.is_file():
                    path.unlink()

    shutil.copy2(SOURCE_DIR / SOURCE_MANIFEST, output / EXPORTED_MANIFEST)

    for name in files:
        source = SOURCE_DIR / name
        if not source.is_file():
            raise SystemExit(f"Missing client contract fixture: {source}")
        shutil.copy2(source, output / name)

    print(f"Exported {len(files) + 1} DJConnect client contract files to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
