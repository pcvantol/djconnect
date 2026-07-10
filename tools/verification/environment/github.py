"""GitHub and GitHub Actions inspection helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.verification.models import GateResult, GateState, GitHubWorkflowInfo


class GitHubInspector:
    def __init__(self, root: Path) -> None:
        self.root = root

    def workflows(self) -> tuple[GitHubWorkflowInfo, ...]:
        workflow_dir = self.root / ".github/workflows"
        if not workflow_dir.exists():
            return ()
        workflows: list[GitHubWorkflowInfo] = []
        for path in sorted((*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml"))):
            text = path.read_text(encoding="utf-8")
            workflows.append(
                GitHubWorkflowInfo(
                    path=path,
                    name=_workflow_name(text, path.stem),
                    triggers=_workflow_triggers(text),
                )
            )
        return tuple(workflows)

    def validate_workflows(self) -> GateResult:
        workflows = self.workflows()
        state = GateState.PASS if workflows else GateState.WARNING
        return GateResult(
            "github_workflow_discovery",
            state,
            f"{len(workflows)} workflows discovered",
            {"workflows": [workflow.name for workflow in workflows]},
        )

    def commit_status(self, sha: str | None = None) -> GateResult:
        sha = sha or _git(self.root, "rev-parse", "HEAD")
        if not sha:
            return GateResult("github_ci_status", GateState.WARNING, "Git SHA unavailable")
        result = _gh(self.root, "run", "list", "--commit", sha, "--limit", "20", "--json", "status,conclusion,name")
        if result is None:
            return GateResult("github_ci_status", GateState.SKIPPED, "GitHub CLI unavailable or unauthenticated")
        try:
            runs = json.loads(result)
        except json.JSONDecodeError:
            runs = []
        failing = [run.get("name") for run in runs if run.get("conclusion") not in {None, "success"}]
        pending = [run.get("name") for run in runs if run.get("status") != "completed"]
        state = GateState.FAIL if failing else GateState.WARNING if pending else GateState.PASS if runs else GateState.SKIPPED
        return GateResult(
            "github_ci_status",
            state,
            f"{len(runs)} GitHub Actions runs inspected",
            {"sha": sha, "failing": failing, "pending": pending},
        )


def _workflow_name(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return fallback


def _workflow_triggers(text: str) -> tuple[str, ...]:
    triggers: list[str] = []
    in_on = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "on:" or stripped.startswith("on: "):
            in_on = True
            if stripped.startswith("on: "):
                triggers.append(stripped.split(":", 1)[1].strip())
            continue
        if in_on and line and not line.startswith((" ", "-")):
            break
        if in_on and stripped.endswith(":"):
            triggers.append(stripped.removesuffix(":"))
    return tuple(filter(None, triggers))


def _git(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(("git", *args), cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _gh(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(("gh", *args), cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=20).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
