#!/usr/bin/env python3
"""Build deterministic, repository-tracked DJConnect onboarding artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent


def manifest_value(key: str) -> str:
    for line in (PACKAGE_ROOT / "manifest.yml").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}: "):
            return line.split(": ", 1)[1]
    raise ValueError(f"missing manifest key: {key}")


def package_files() -> list[Path]:
    return sorted(
        path
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file() and "dist" not in path.parts and "__pycache__" not in path.parts and path.name != ".DS_Store"
    )


def build(output: Path) -> list[Path]:
    version = manifest_value("package.version")
    name = f"djconnect-developer-onboarding-{version}"
    archive = output / f"{name}.zip"
    checksum = output / f"{name}.zip.sha256"
    metadata = output / f"{name}.json"
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in package_files():
            info = zipfile.ZipInfo(f"onboarding/{path.relative_to(PACKAGE_ROOT).as_posix()}")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.external_attr = 0o100755 << 16 if path.stat().st_mode & 0o111 else 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    metadata.write_text(json.dumps({"name": name, "version": version, "sha256": digest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return [archive, checksum, metadata]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PACKAGE_ROOT / "dist")
    parser.add_argument("--check", action="store_true", help="fail when tracked artifacts differ from a fresh build")
    args = parser.parse_args()
    if not args.check:
        build(args.output)
        return 0
    with tempfile.TemporaryDirectory() as directory:
        expected = build(Path(directory))
        for artifact in expected:
            tracked = args.output / artifact.name
            if not tracked.is_file() or tracked.read_bytes() != artifact.read_bytes():
                print(f"onboarding dist artifact is missing or stale: {tracked}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
