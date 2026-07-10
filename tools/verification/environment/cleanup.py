"""Reusable cleanup planning and execution for verification environments."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from tools.verification.models import CleanupMode, GateResult, GateState


@dataclass(frozen=True)
class CleanupTarget:
    name: str
    path: Path
    destructive: bool = False


class CleanupManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def default_targets(self) -> tuple[CleanupTarget, ...]:
        return (
            CleanupTarget("pytest_cache", self.root / ".pytest_cache"),
            CleanupTarget("verification_tmp", self.root / "artifacts/verification/tmp"),
            CleanupTarget("verification_logs", self.root / "artifacts/verification/logs"),
            CleanupTarget("build", self.root / "build"),
            CleanupTarget("dist", self.root / "dist"),
            CleanupTarget("derived_data_marker", self.root / "artifacts/verification/DerivedData"),
            CleanupTarget("obj", self.root / "obj"),
            CleanupTarget("bin", self.root / "bin"),
        )

    def plan(self, targets: tuple[CleanupTarget, ...] | None = None) -> list[Path]:
        return [target.path for target in targets or self.default_targets() if target.path.exists()]

    def clean(
        self,
        *,
        mode: CleanupMode = CleanupMode.SOFT,
        dry_run: bool = True,
        allow_destructive: bool = False,
        targets: tuple[CleanupTarget, ...] | None = None,
    ) -> GateResult:
        selected = targets or self.default_targets()
        blocked = [
            str(target.path)
            for target in selected
            if target.path.exists() and target.destructive and not allow_destructive
        ]
        if blocked:
            return GateResult("environment_cleanup", GateState.WARNING, "Destructive cleanup blocked", {"blocked": blocked})
        existing = [target for target in selected if target.path.exists()]
        if dry_run:
            return GateResult(
                "environment_cleanup",
                GateState.PASS,
                "Cleanup planned",
                {"mode": mode.value, "targets": [str(target.path) for target in existing], "dry_run": True},
            )
        for target in existing:
            if target.path.is_dir():
                shutil.rmtree(target.path)
            else:
                target.path.unlink()
        return GateResult(
            "environment_cleanup",
            GateState.PASS,
            "Cleanup complete",
            {"mode": mode.value, "removed": [str(target.path) for target in existing]},
        )
