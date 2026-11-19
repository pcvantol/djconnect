"""Read/dispatch-only GitHub adapter for Platform Release orchestration."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Sequence

from .execution import ExecutionAction, ExecutionError


class GitHubCliExecutionClient:
    """Dispatch and inspect workflows; all mutations belong to those workflows."""

    def __init__(self, executable: str = "gh") -> None:
        self.executable = executable

    def dispatch_workflow(self, action: ExecutionAction) -> dict[str, object]:
        command = [self.executable, "workflow", "run", action.workflow, "--repo", action.repository, "--ref", action.ref]
        for key, value in sorted(action.inputs.items()):
            command.extend(["-f", f"{key}={value}"])
        self._run(command)
        run = self._wait_for_workflow(action) if action.wait_for_completion else {"id": "pending", "conclusion": "pending"}
        if run.get("conclusion") != "success":
            raise ExecutionError("workflow did not complete successfully")
        # The workflow must publish this canonical evidence as an artifact or
        # surface it through its run summary.  Until it is available, fail closed.
        evidence = self._read_workflow_evidence(action, str(run["id"]))
        return {"kind": "workflow_dispatch", "workflow": action.workflow, "ref": action.ref, "workflow_run": run, "evidence": evidence, "channel": "internal"}

    def _read_workflow_evidence(self, action: ExecutionAction, run_id: str) -> dict[str, object]:
        listing = self._run([self.executable, "api", f"repos/{action.repository}/actions/runs/{run_id}/artifacts", "--jq", ".artifacts[] | select(.name == \"platform-release-execution-evidence\") | .id"])
        if not listing.strip():
            raise ExecutionError("workflow did not publish platform-release-execution-evidence")
        with tempfile.TemporaryDirectory(prefix="djconnect-release-evidence-") as directory:
            self._run([self.executable, "run", "download", run_id, "--repo", action.repository, "--name", "platform-release-execution-evidence", "--dir", directory])
            evidence_files = list(Path(directory).rglob("*.json"))
            if len(evidence_files) != 1:
                raise ExecutionError("workflow evidence artifact must contain exactly one JSON document")
            try:
                evidence = json.loads(evidence_files[0].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ExecutionError("workflow evidence artifact is not valid JSON") from error
        if not isinstance(evidence, dict):
            raise ExecutionError("workflow evidence artifact must be a JSON object")
        return evidence

    def _run(self, command: Sequence[str]) -> str:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode:
            raise ExecutionError(completed.stderr.strip() or completed.stdout.strip() or "GitHub CLI command failed")
        return completed.stdout

    def _wait_for_workflow(self, action: ExecutionAction, timeout_seconds: int = 900) -> dict[str, object]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            output = self._run([self.executable, "run", "list", "--repo", action.repository, "--workflow", action.workflow, "--limit", "20", "--json", "databaseId,status,conclusion,url,headSha"])
            runs = json.loads(output)
            run = next((item for item in runs if item.get("headSha") == action.inputs["candidate_sha"]), None)
            if run and run.get("status") == "completed":
                if run.get("conclusion") != "success":
                    raise ExecutionError(f"workflow {action.workflow} failed with conclusion {run.get('conclusion')}")
                return {"id": run.get("databaseId"), "url": run.get("url"), "head_sha": run.get("headSha"), "conclusion": "success"}
            time.sleep(5)
        raise ExecutionError(f"workflow {action.workflow} did not complete within {timeout_seconds} seconds")
