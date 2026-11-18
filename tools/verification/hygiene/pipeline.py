"""Reusable repository hygiene checks."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

from tools.verification.models import GateResult, GateState
from tools.verification.environment.dependencies import DependencyInspector
from tools.verification.environment.github import GitHubInspector
from tools.verification.environment.toolchain import ToolchainInspector


class RepositoryHygiene:
    def __init__(self, root: Path) -> None:
        self.root = root

    def check(self) -> list[GateResult]:
        return [
            self.working_tree_validation(),
            self.open_pr_validation(),
            self.branch_validation(),
            self.sha_validation(),
            self.dependency_validation(),
            self.toolchain_validation(),
            self.github_ci_validation(),
            self.clean_build_directories(dry_run=True),
            self.clean_logs(dry_run=True),
            self.artifact_cleanup(dry_run=True),
            self.environment_fingerprint(),
        ]

    def working_tree_validation(self) -> GateResult:
        status = _git(self.root, "status", "--porcelain")
        if status is None:
            return GateResult("working_tree_validation", GateState.WARNING, "Git status unavailable")
        if status:
            return GateResult("working_tree_validation", GateState.WARNING, "Working tree has changes")
        return GateResult("working_tree_validation", GateState.PASS, "Working tree is clean")

    def fetch(self, *, dry_run: bool = True) -> GateResult:
        if dry_run:
            return GateResult("git_fetch", GateState.PASS, "Fetch planned", {"dry_run": True})
        result = _git(self.root, "fetch", "--all")
        state = GateState.PASS if result is not None else GateState.WARNING
        return GateResult("git_fetch", state, "Fetch complete" if result is not None else "Fetch unavailable")

    def prune(self, *, dry_run: bool = True) -> GateResult:
        if dry_run:
            return GateResult("git_prune", GateState.PASS, "Prune planned", {"dry_run": True})
        result = _git(self.root, "fetch", "--prune")
        state = GateState.PASS if result is not None else GateState.WARNING
        return GateResult("git_prune", state, "Prune complete" if result is not None else "Prune unavailable")

    def open_pr_validation(self) -> GateResult:
        return GateResult("open_pr_validation", GateState.SKIPPED, "No platform-neutral PR provider configured")

    def branch_validation(self) -> GateResult:
        branch = _git(self.root, "rev-parse", "--abbrev-ref", "HEAD")
        if not branch:
            return GateResult("branch_validation", GateState.WARNING, "Git branch unavailable")
        return GateResult("branch_validation", GateState.PASS, f"Current branch: {branch}", {"branch": branch})

    def sha_validation(self) -> GateResult:
        sha = _git(self.root, "rev-parse", "HEAD")
        if not sha:
            return GateResult("sha_validation", GateState.WARNING, "Git SHA unavailable")
        return GateResult("sha_validation", GateState.PASS, "Git SHA recorded", {"sha": sha})

    def dependency_validation(self) -> GateResult:
        return DependencyInspector().validate(self.root)[0]

    def toolchain_validation(self) -> GateResult:
        discovered = ToolchainInspector().discover()
        missing = [
            name for name in ("git", "python")
            if discovered.get(name) is None or discovered[name].executable is None
        ]
        if missing:
            return GateResult("toolchain_validation", GateState.FAIL, f"Missing tools: {', '.join(missing)}")
        return GateResult(
            "toolchain_validation",
            GateState.PASS,
            "Required generic tools available",
            {"available": sorted(name for name, info in discovered.items() if info.executable or name in {"operating_system", "architecture"})},
        )

    def github_ci_validation(self) -> GateResult:
        return GitHubInspector(self.root).commit_status()

    def clean_build_directories(self, *, dry_run: bool) -> GateResult:
        return _cleanup_gate(self.root, "clean_build_directories", (".pytest_cache", "build", "dist"), dry_run)

    def clean_logs(self, *, dry_run: bool) -> GateResult:
        return _cleanup_gate(self.root, "clean_logs", ("logs",), dry_run)

    def artifact_cleanup(self, *, dry_run: bool) -> GateResult:
        return _cleanup_gate(self.root, "artifact_cleanup", ("artifacts/verification/tmp",), dry_run)

    def environment_fingerprint(self) -> GateResult:
        payload = "|".join(
            value or "" for value in (_git(self.root, "rev-parse", "HEAD"), _git(self.root, "status", "--porcelain"))
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return GateResult(
            "environment_fingerprint",
            GateState.PASS,
            "Repository fingerprint recorded",
            {"sha256": digest},
        )


def _cleanup_gate(root: Path, name: str, relative_paths: tuple[str, ...], dry_run: bool) -> GateResult:
    existing = [str(Path(path)) for path in relative_paths if (root / path).exists()]
    if dry_run:
        return GateResult(name, GateState.PASS, "Cleanup planned", {"existing": existing, "dry_run": True})
    for relative in existing:
        path = root / relative
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    return GateResult(name, GateState.PASS, "Cleanup complete", {"removed": existing})


def _git(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(("git", *args), cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
