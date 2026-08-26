"""Token-free readiness checks for Engineering Platform host providers.

The result is intentionally small and safe to persist or project.  Repairs are
always explicit dashboard actions; this module never opens a login flow or
retries authentication on behalf of an execution.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from .providers import CodexCliProvider, LocalProcessProvider


def _classify(result: subprocess.CompletedProcess[str] | None) -> str:
    if result is None:
        return "CHECK_FAILED"
    if result.returncode == 0:
        return "READY"
    detail = f"{result.stdout}\n{result.stderr}".casefold()
    return "AUTH_REQUIRED" if any(word in detail for word in ("login", "auth", "credential", "token")) else "CHECK_FAILED"


def status(root: Path, *, require_github: bool = True) -> dict[str, dict[str, str]]:
    """Return provider readiness without session details, tokens, or diagnostics."""
    codex = CodexCliProvider()
    codex_installed = codex.status().qualified
    try:
        codex_result = codex.command("login", "status") if codex_installed else None
    except OSError:
        codex_result = None
    result = {
        "codex": {"provider": "CODEX", "state": "UNAVAILABLE" if not codex_installed else _classify(codex_result)},
    }
    if not require_github:
        return result
    if shutil.which("gh") is None:
        result["github"] = {"provider": "GITHUB", "state": "UNAVAILABLE"}
        return result
    try:
        github_result = LocalProcessProvider().execute(root, ("gh", "auth", "status", "--hostname", "github.com"))
    except OSError:
        github_result = None
    result["github"] = {"provider": "GITHUB", "state": _classify(github_result)}
    return result


def failures(root: Path, *, require_github: bool) -> tuple[str, ...]:
    """Return the provider names that must be repaired before admission."""
    return tuple(
        value["provider"]
        for value in status(root, require_github=require_github).values()
        if value["state"] != "READY"
    )
