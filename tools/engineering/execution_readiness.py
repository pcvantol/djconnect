"""Typed readiness profiles selected before an Execution Host lifecycle starts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable


class Requirement(StrEnum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class ReadinessProfile:
    profile_id: str
    version: int
    execution_mode: str
    repository: Requirement
    remote: Requirement
    upstream: Requirement
    clean_worktree: Requirement
    workspace_authorization: Requirement
    host_qualification: Requirement
    capability_qualification: Requirement
    datastore: Requirement
    active_run_lease: Requirement
    producer_contract: Requirement
    additional_constraints: tuple[str, ...] = ()


PLATFORM_HOST = ReadinessProfile("platform_host", 1, "ANY", Requirement.NOT_APPLICABLE, Requirement.NOT_APPLICABLE, Requirement.NOT_APPLICABLE, Requirement.NOT_APPLICABLE, Requirement.NOT_APPLICABLE, Requirement.REQUIRED, Requirement.NOT_APPLICABLE, Requirement.REQUIRED, Requirement.NOT_APPLICABLE, Requirement.NOT_APPLICABLE)
MANAGED_REPOSITORY = ReadinessProfile("managed_repository", 1, "MANAGED", Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED)
GENESIS_TARGET = ReadinessProfile("genesis_target", 1, "GENESIS", Requirement.REQUIRED, Requirement.NOT_APPLICABLE, Requirement.NOT_APPLICABLE, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED, Requirement.REQUIRED)


@dataclass(frozen=True)
class ReadinessResult:
    profile: ReadinessProfile
    ready: bool
    diagnostic: str | None = None


def selected_profile(execution_mode: str) -> ReadinessProfile:
    if execution_mode == "GENESIS":
        return GENESIS_TARGET
    return MANAGED_REPOSITORY


def evaluate(
    profile: ReadinessProfile,
    *,
    host_root: Path,
    target_root: Path | None,
    managed_clean: Callable[[Path], bool],
    genesis_preflight: Callable[[Path | None], str | None],
) -> ReadinessResult:
    """Evaluate only the selected profile; never mix Genesis and Managed checks."""
    if profile.profile_id == PLATFORM_HOST.profile_id:
        return ReadinessResult(profile, host_root.is_dir(), None if host_root.is_dir() else "Execution Host repository is unavailable.")
    if profile.profile_id == GENESIS_TARGET.profile_id:
        diagnostic = genesis_preflight(target_root)
        return ReadinessResult(profile, diagnostic is None, diagnostic)
    if managed_clean(host_root):
        return ReadinessResult(profile, True)
    return ReadinessResult(profile, False, "working tree is not clean; unrelated work will not be touched")
