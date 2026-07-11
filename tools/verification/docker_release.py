"""Helpers for building the generic verification platform runtime image."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
from pathlib import Path

from tools.verification.runtime import RUNTIME_VERSION

DEFAULT_IMAGE = "pcvantol/djconnect-verification-platform"
DEFAULT_BASE_IMAGE = "python:3.12-slim"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verification-docker-release")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--image", default=os.getenv("DJCONNECT_VERIFICATION_PLATFORM_IMAGE", DEFAULT_IMAGE))
    parser.add_argument("--base-image", default=os.getenv("DJCONNECT_VERIFICATION_PLATFORM_BASE_IMAGE", DEFAULT_BASE_IMAGE))
    parser.add_argument("--release-sha", default=None)
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    release_sha = args.release_sha or _git_sha(root)
    tags = _tags(args.image, release_sha)
    command = [
        "docker",
        "build",
        "-f",
        str(root / "docker/verification-platform/Dockerfile"),
        "--build-arg",
        f"BASE_IMAGE={args.base_image}",
        "--build-arg",
        f"VERIFICATION_RUNTIME_VERSION={RUNTIME_VERSION}",
        "--build-arg",
        f"RELEASE_SHA={release_sha}",
        "--build-arg",
        f"BUILD_DATE={dt.datetime.now(dt.timezone.utc).isoformat()}",
    ]
    for tag in tags:
        command.extend(["-t", tag])
    command.append(str(root))
    commands = [command]
    if args.push:
        commands.extend(["docker", "push", tag] for tag in tags)
    for item in commands:
        print(" ".join(item))
        if not args.dry_run:
            subprocess.check_call(item, cwd=root)
    return 0


def _tags(image: str, release_sha: str) -> list[str]:
    short_sha = release_sha[:12] if release_sha and release_sha != "unknown" else "unknown"
    return [
        f"{image}:{RUNTIME_VERSION}",
        f"{image}:{RUNTIME_VERSION}-{short_sha}",
        f"{image}:sha-{short_sha}",
    ]


def _git_sha(root: Path) -> str:
    try:
        return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
