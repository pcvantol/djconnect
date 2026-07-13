"""Fail-closed workflow orchestration for the Platform Release Runtime.

This module has no release mutation capability.  It validates an approved
release request, dispatches an existing GitHub Actions workflow through an
adapter, and accepts only workflow-produced evidence.  GitHub Actions is the
exclusive execution engine for tags, releases, publication, deployment and
rollback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import json
import re
from typing import Protocol


class ExecutionError(RuntimeError):
    """Raised when release orchestration cannot safely continue."""


_WORKFLOW = re.compile(r"^[A-Za-z0-9_.-]+\.(?:ya?ml)$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_INPUTS = frozenset({"action", "candidate_sha", "execution_mode", "manifest_id", "platform_version", "release_profile"})
_ACTIONS = frozenset({"build", "artifact_publication", "deployment", "post_release", "rollback"})


@dataclass(frozen=True)
class ExecutionAction:
    """One bounded workflow dispatch from an approved release plan."""

    repository: str
    category: str
    workflow: str
    ref: str
    inputs: dict[str, str] = field(default_factory=dict)
    wait_for_completion: bool = True


@dataclass(frozen=True)
class ExecutionRequest:
    """An INTERNAL_RELEASE request containing workflow dispatches only."""

    release_profile: str
    actions: tuple[ExecutionAction, ...]
    requested_by: str
    non_production: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "ExecutionRequest":
        if raw.get("release_profile") != "INTERNAL_RELEASE":
            raise ExecutionError("execution request must use release_profile INTERNAL_RELEASE")
        requested_by = raw.get("requested_by")
        if not isinstance(requested_by, str) or not requested_by.strip():
            raise ExecutionError("execution request requires requested_by")
        raw_actions = raw.get("actions")
        if not isinstance(raw_actions, list) or not raw_actions:
            raise ExecutionError("execution request requires at least one action")
        actions: list[ExecutionAction] = []
        for index, item in enumerate(raw_actions):
            if not isinstance(item, dict):
                raise ExecutionError(f"action {index} must be an object")
            if item.get("operation") != "workflow_dispatch":
                raise ExecutionError(f"action {index} must use workflow_dispatch; runtime mutations are forbidden")
            repository, category, workflow, ref = (item.get(name) for name in ("repository", "category", "workflow", "ref"))
            if not all(isinstance(value, str) and value for value in (repository, category, workflow, ref)):
                raise ExecutionError(f"action {index} requires repository, category, workflow and ref")
            if category not in _ACTIONS:
                raise ExecutionError(f"action {index} has unsupported category")
            if not _WORKFLOW.fullmatch(workflow):
                raise ExecutionError(f"action {index} workflow must be a workflow file name")
            inputs = item.get("inputs")
            if not isinstance(inputs, dict) or set(inputs) != _INPUTS or not all(isinstance(key, str) and isinstance(value, str) and value for key, value in inputs.items()):
                raise ExecutionError(f"action {index} must use the complete bounded workflow input contract")
            if inputs["action"] != category:
                raise ExecutionError(f"action {index} input action must match category")
            if inputs["execution_mode"] not in {"dry_run", "execute"}:
                raise ExecutionError(f"action {index} execution_mode is invalid")
            if item.get("wait_for_completion", True) is not True:
                raise ExecutionError(f"action {index} must wait for workflow evidence")
            actions.append(ExecutionAction(repository, category, workflow, ref, dict(inputs), True))
        return cls("INTERNAL_RELEASE", tuple(actions), requested_by, bool(raw.get("non_production", False)))


class ExecutionClient(Protocol):
    """Read/dispatch-only boundary; it deliberately has no mutation methods."""

    def dispatch_workflow(self, action: ExecutionAction) -> dict[str, object]: ...


class EvidenceOnlyExecutionClient:
    """Safe client for rehearsing orchestration without contacting GitHub."""

    def dispatch_workflow(self, action: ExecutionAction) -> dict[str, object]:
        return {
            "kind": "workflow_dispatch", "workflow": action.workflow, "ref": action.ref,
            "workflow_run": {"id": f"rehearsal-{action.repository.replace('/', '-')}", "conclusion": "success"},
            "evidence": _evidence_for(action, "rehearsal", "PASS"),
            "channel": "non_production_rehearsal", "simulated": True,
        }


class ReleaseExecutor:
    """Dispatch approved workflows, collect their evidence, and stop on failure."""

    def __init__(self, client: ExecutionClient) -> None:
        self.client = client

    def execute(self, manifest: dict[str, object], request: ExecutionRequest) -> dict[str, object]:
        _validate_execution_gate(manifest, request)
        repositories = {str(item["name"]): item for item in manifest["repositories"] if isinstance(item, dict) and item.get("included")}
        evidence: list[dict[str, object]] = []
        started_at = _timestamp()
        for index, action in enumerate(request.actions):
            repository = repositories.get(action.repository)
            reason = _validate_action_scope(action, repository, manifest, request)
            if reason:
                return _failed_outcome(manifest, request, evidence, started_at, index, action, reason)
            try:
                receipt = self.client.dispatch_workflow(action)
                workflow_evidence = _validate_workflow_evidence(receipt, action, manifest)
            except Exception as error:
                return _failed_outcome(manifest, request, evidence, started_at, index, action, str(error))
            evidence.append({"index": index, "timestamp": _timestamp(), "operation": "workflow_dispatch", "repository": action.repository, "category": action.category, "status": "PASS", "receipt": receipt, "workflow_evidence": workflow_evidence})
        return _outcome(manifest, request, evidence, started_at, "PASS")


def write_execution_evidence(outcome: dict[str, object], output_dir: Path) -> list[Path]:
    """Persist redaction-safe evidence collected from workflows."""
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {"release-execution-report.json": outcome, "release-deployment-evidence.json": outcome.get("deployment_evidence", []), "release-publication-evidence.json": outcome.get("publication_evidence", [])}
    return [_write_json(output_dir / name, content) for name, content in files.items()]


def _validate_execution_gate(manifest: dict[str, object], request: ExecutionRequest) -> None:
    if manifest.get("release_mode") not in {"production", "hotfix"}:
        raise ExecutionError("operational orchestration requires production or hotfix release mode")
    readiness = manifest.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("state") != "READY":
        raise ExecutionError("operational orchestration requires READY release readiness")
    if manifest.get("qualification_status") not in {"QUALIFIED", "PASS"}:
        raise ExecutionError("operational orchestration requires qualified candidate evidence")
    if request.release_profile != "INTERNAL_RELEASE" or not isinstance(manifest.get("repositories"), list):
        raise ExecutionError("operational orchestration requires canonical INTERNAL_RELEASE scope")


def _validate_action_scope(action: ExecutionAction, repository: object, manifest: dict[str, object], request: ExecutionRequest) -> str | None:
    if not isinstance(repository, dict):
        return "repository is not in the qualified release scope"
    candidate_sha = repository.get("sha")
    if not isinstance(candidate_sha, str) or not _SHA.fullmatch(candidate_sha):
        return "repository has no qualified full candidate SHA"
    expected = {"candidate_sha": candidate_sha, "platform_version": str(manifest["platform_version"]), "release_profile": request.release_profile, "manifest_id": str(manifest["manifest_id"])}
    if any(action.inputs[key] != value for key, value in expected.items()):
        return "workflow inputs do not match the qualified immutable release scope"
    if action.ref != candidate_sha:
        return "workflow ref must equal the qualified immutable candidate SHA"
    if action.inputs["execution_mode"] == "execute" and request.non_production:
        return "non-production rehearsal cannot request execution mode"
    return None


def _validate_workflow_evidence(receipt: dict[str, object], action: ExecutionAction, manifest: dict[str, object]) -> dict[str, object]:
    evidence = receipt.get("evidence")
    if not isinstance(evidence, dict):
        raise ExecutionError("workflow did not produce canonical execution evidence")
    expected = {"workflow": action.workflow, "repository": action.repository, "candidate_sha": action.inputs["candidate_sha"], "platform_version": str(manifest["platform_version"]), "action": action.category, "status": "PASS"}
    if any(evidence.get(key) != value for key, value in expected.items()):
        raise ExecutionError("workflow evidence does not match the dispatched qualified action")
    if not evidence.get("workflow_run_id") or not evidence.get("timestamp"):
        raise ExecutionError("workflow evidence is incomplete")
    return evidence


def _evidence_for(action: ExecutionAction, run_id: str, status: str) -> dict[str, object]:
    return {"workflow": action.workflow, "workflow_run_id": run_id, "repository": action.repository, "candidate_sha": action.inputs["candidate_sha"], "platform_version": action.inputs["platform_version"], "action": action.category, "artifact_hashes": {}, "deployment_result": "NOT_APPLICABLE", "rollback": "PREPARED", "timestamp": _timestamp(), "status": status}


def _failed_outcome(manifest: dict[str, object], request: ExecutionRequest, evidence: list[dict[str, object]], started_at: str, index: int, action: ExecutionAction, reason: str) -> dict[str, object]:
    outcome = _outcome(manifest, request, evidence, started_at, "FAILED")
    outcome["failure"] = {"index": index, "repository": action.repository, "category": action.category, "reason": reason}
    outcome["rollback_evidence"]["state"] = "PRESERVE_AND_STOP"
    return outcome


def _outcome(manifest: dict[str, object], request: ExecutionRequest, evidence: list[dict[str, object]], started_at: str, status: str) -> dict[str, object]:
    return {"schema_version": 1, "manifest_kind": "platform_release_execution", "execution_id": f"release-exec-{manifest['manifest_id']}", "source_manifest_id": manifest["manifest_id"], "platform_version": manifest["platform_version"], "release_profile": request.release_profile, "requested_by": request.requested_by, "non_production": request.non_production, "started_at": started_at, "completed_at": _timestamp(), "status": status, "operations": evidence, "deployment_evidence": [item for item in evidence if item["category"] == "deployment"], "publication_evidence": [item for item in evidence if item["category"] == "artifact_publication"], "post_release_evidence": [item for item in evidence if item["category"] == "post_release"], "rollback_evidence": {"state": "PREPARED", "preserved_operations": len(evidence), "source_rollback_plan": manifest["rollback_plan"]}}


def _write_json(path: Path, content: object) -> Path:
    path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
