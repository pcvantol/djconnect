"""GitHub CLI adapter for controlled internal-release operations.

This adapter deliberately exposes only three mutation types: dispatch an
existing workflow, create a lightweight tag at an explicitly qualified SHA,
and create a draft prerelease.  It never uploads an artifact itself; artifact
creation and publication remain owned by the dispatched repository workflow.
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import Sequence

from .execution import ExecutionAction, ExecutionError


class GitHubCliExecutionClient:
    """Execute explicit internal-release actions through the authenticated gh CLI."""

    def __init__(self, executable: str = "gh") -> None:
        self.executable = executable

    def dispatch_workflow(self, action: ExecutionAction) -> dict[str, object]:
        command = [self.executable, "workflow", "run", str(action.workflow), "--repo", action.repository, "--ref", str(action.ref)]
        for key, value in sorted(action.inputs.items()):
            command.extend(["-f", f"{key}={value}"])
        self._run(command)
        receipt: dict[str, object] = {
            "kind": "workflow_dispatch",
            "workflow": action.workflow,
            "ref": action.ref,
            "inputs": action.inputs,
            "completion_wait_requested": action.wait_for_completion,
            "channel": "internal",
        }
        if action.wait_for_completion:
            receipt["workflow_run"] = self._wait_for_workflow(action)
        return receipt

    def create_tag(self, action: ExecutionAction) -> dict[str, object]:
        _validate_sha(str(action.target_sha))
        self._run([
            self.executable, "api", "--method", "POST", f"repos/{action.repository}/git/refs",
            "-f", f"ref=refs/tags/{action.tag}", "-f", f"sha={action.target_sha}",
        ])
        return {"kind": "git_tag", "tag": action.tag, "target_sha": action.target_sha, "channel": "internal"}

    def create_draft_release(self, action: ExecutionAction) -> dict[str, object]:
        output = self._run([
            self.executable, "api", "--method", "POST", f"repos/{action.repository}/releases",
            "-f", f"tag_name={action.tag}", "-f", f"name={action.release_name}",
            "-f", f"body={action.release_notes or ''}", "-F", "draft=true", "-F", "prerelease=true",
        ])
        try:
            response = json.loads(output)
        except json.JSONDecodeError as error:
            raise ExecutionError("GitHub did not return valid draft-release evidence") from error
        return {
            "kind": "draft_github_release",
            "id": response.get("id"),
            "url": response.get("html_url"),
            "tag": action.tag,
            "draft": response.get("draft"),
            "prerelease": response.get("prerelease"),
            "channel": "internal",
        }

    def _run(self, command: Sequence[str]) -> str:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "GitHub CLI command failed"
            raise ExecutionError(message)
        return completed.stdout

    def _wait_for_workflow(self, action: ExecutionAction, timeout_seconds: int = 900) -> dict[str, object]:
        """Wait for the dispatched workflow and fail closed on non-success."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            output = self._run([
                self.executable, "run", "list", "--repo", action.repository,
                "--workflow", str(action.workflow), "--branch", str(action.ref), "--limit", "1",
                "--json", "databaseId,status,conclusion,url,headSha",
            ])
            try:
                runs = json.loads(output)
            except json.JSONDecodeError as error:
                raise ExecutionError("GitHub did not return valid workflow-run evidence") from error
            if runs:
                run = runs[0]
                status = run.get("status")
                if status == "completed":
                    if run.get("conclusion") != "success":
                        raise ExecutionError(f"workflow {action.workflow} failed with conclusion {run.get('conclusion')}")
                    return {
                        "id": run.get("databaseId"), "url": run.get("url"), "head_sha": run.get("headSha"), "conclusion": "success",
                    }
            time.sleep(5)
        raise ExecutionError(f"workflow {action.workflow} did not complete within {timeout_seconds} seconds")


def _validate_sha(value: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value.lower()):
        raise ExecutionError("tag target_sha must be a full 40-character Git SHA")
