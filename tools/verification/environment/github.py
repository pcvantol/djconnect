"""GitHub and GitHub Actions inspection helpers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.verification.models import GateResult, GateState, GitHubWorkflowInfo

CI_PASS = "CI_PASS"
CI_PASS_WITH_NON_BLOCKING_WARNINGS = "CI_PASS_WITH_NON_BLOCKING_WARNINGS"
CI_RUNNING = "CI_RUNNING"
CI_FAIL = "CI_FAIL"
CI_NOT_CONFIGURED = "CI_NOT_CONFIGURED"
CI_AUTH_REQUIRED = "CI_AUTH_REQUIRED"
CI_NO_DATA = "CI_NO_DATA"
CI_SHA_MISMATCH = "CI_SHA_MISMATCH"


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
        decision = self.exact_sha_ci(sha)
        state = {
            CI_PASS: GateState.PASS,
            CI_PASS_WITH_NON_BLOCKING_WARNINGS: GateState.WARNING,
            CI_RUNNING: GateState.WARNING,
            CI_FAIL: GateState.FAIL,
            CI_NOT_CONFIGURED: GateState.WARNING,
            CI_AUTH_REQUIRED: GateState.FAIL,
            CI_NO_DATA: GateState.FAIL,
            CI_SHA_MISMATCH: GateState.FAIL,
        }.get(decision["decision"], GateState.FAIL)
        return GateResult(
            "github_ci_status",
            state,
            decision["message"],
            decision,
        )

    def auth_status(self, *, fix_auth: bool = False, interactive: bool | None = None) -> GateResult:
        status = _gh_status(self.root)
        if status.returncode == 0:
            return GateResult("github_auth", GateState.PASS, "GitHub CLI authentication valid")
        interactive = sys.stdin.isatty() and sys.stdout.isatty() if interactive is None else interactive
        if fix_auth and interactive:
            login = _gh_process(self.root, "auth", "login")
            if login.returncode == 0 and _gh_status(self.root).returncode == 0:
                return GateResult("github_auth", GateState.PASS, "GitHub CLI authentication repaired interactively")
        if os.getenv("GH_TOKEN"):
            return GateResult("github_auth", GateState.WARNING, "GH_TOKEN present; CLI auth unavailable")
        return GateResult(
            "github_auth",
            GateState.FAIL,
            "BLOCKED_CI_AUTH: GitHub authentication is required for exact-SHA CI qualification",
            {"interactive": interactive, "fix_auth": fix_auth},
        )

    def exact_sha_ci(self, sha: str | None = None) -> dict[str, Any]:
        sha = sha or _git(self.root, "rev-parse", "HEAD")
        if not sha:
            return {"decision": CI_SHA_MISMATCH, "message": "Git SHA unavailable", "sha": ""}
        workflows = self.workflows()
        if not workflows:
            return {"decision": CI_NOT_CONFIGURED, "message": "No GitHub workflows configured", "sha": sha}
        result = _gh(self.root, "run", "list", "--commit", sha, "--limit", "50", "--json", "databaseId,status,conclusion,name,event,headSha,workflowName,url")
        if result is None:
            return {"decision": CI_AUTH_REQUIRED, "message": "GitHub CLI unavailable or unauthenticated", "sha": sha}
        try:
            runs = json.loads(result)
        except json.JSONDecodeError:
            runs = []
        return self._decision_from_runs(runs, sha)

    def _decision_from_runs(self, runs: list[dict[str, Any]] | None, sha: str) -> dict[str, Any]:
        if runs is None:
            return {"decision": CI_AUTH_REQUIRED, "message": "GitHub CLI unavailable or unauthenticated", "sha": sha}
        if not runs:
            return {"decision": CI_NO_DATA, "message": "No GitHub Actions runs found for exact SHA", "sha": sha, "runs": []}
        mismatched = [run for run in runs if run.get("headSha") and run.get("headSha") != sha]
        if mismatched:
            return {"decision": CI_SHA_MISMATCH, "message": "Workflow run SHA mismatch", "sha": sha, "runs": runs}
        pending = [run.get("name") for run in runs if run.get("status") != "completed"]
        failing = [run.get("name") for run in runs if run.get("status") == "completed" and run.get("conclusion") not in {"success", "skipped", "neutral"}]
        decision = CI_FAIL if failing else CI_RUNNING if pending else CI_PASS
        return {
            "decision": decision,
            "message": f"{len(runs)} GitHub Actions runs inspected for exact SHA",
            "sha": sha,
            "workflow_names": [run.get("workflowName") or run.get("name") for run in runs],
            "run_ids": [run.get("databaseId") for run in runs],
            "events": [run.get("event") for run in runs],
            "failing": failing,
            "pending": pending,
            "runs": runs,
        }


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


def _gh_status(root: Path):
    return _gh_process(root, "auth", "status")


def _gh_process(root: Path, *args: str):
    try:
        return subprocess.run(
            ("gh", *args),
            cwd=root,
            text=True,
            capture_output=args != ("auth", "login"),
            timeout=None if args == ("auth", "login") else 20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(("gh", *args), 1, "", str(exc))
