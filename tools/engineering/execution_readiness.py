"""Typed readiness profiles selected before an Execution Host lifecycle starts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable


class ReadinessProfile(StrEnum):
    PLATFORM_HOST = "platform_host"
    MANAGED_REPOSITORY = "managed_repository"
    GENESIS_TARGET = "genesis_target"


@dataclass(frozen=True)
class ReadinessResult:
    profile: ReadinessProfile
    ready: bool
    diagnostic: str | None = None


def selected_profile(execution_mode: str) -> ReadinessProfile:
    if execution_mode == "GENESIS":
        return ReadinessProfile.GENESIS_TARGET
    return ReadinessProfile.MANAGED_REPOSITORY


def evaluate(
    profile: ReadinessProfile,
    *,
    host_root: Path,
    target_root: Path | None,
    managed_clean: Callable[[Path], bool],
    genesis_preflight: Callable[[Path | None], str | None],
) -> ReadinessResult:
    """Evaluate only the selected profile; never mix Genesis and Managed checks."""
    if profile is ReadinessProfile.PLATFORM_HOST:
        return ReadinessResult(profile, host_root.is_dir(), None if host_root.is_dir() else "Execution Host repository is unavailable.")
    if profile is ReadinessProfile.GENESIS_TARGET:
        diagnostic = genesis_preflight(target_root)
        return ReadinessResult(profile, diagnostic is None, diagnostic)
    if managed_clean(host_root):
        return ReadinessResult(profile, True)
    return ReadinessResult(profile, False, "working tree is not clean; unrelated work will not be touched")
