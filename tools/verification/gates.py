"""Compatibility exports for verification gates."""

from __future__ import annotations

from pathlib import Path

from .build import BuildQualification
from .environment import EnvironmentSnapshotter
from .hygiene import RepositoryHygiene
from .models import GateResult


class EnvironmentManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def validate(self) -> list[GateResult]:
        return []

    def snapshot(self, config):
        return EnvironmentSnapshotter().collect(config)


__all__ = ["BuildQualification", "EnvironmentManager", "GateResult", "RepositoryHygiene"]
