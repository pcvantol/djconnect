"""Fail-closed operational execution for the Platform Release Runtime.

The executor consumes a qualified release manifest and an explicit, generic
execution request.  It never selects repositories, workflows, deployment
targets, or distribution channels by name: those are supplied by the approved
release plan.  Source builds remain GitHub Actions responsibilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import json
from typing import Protocol


class ExecutionError(RuntimeError):
    """Raised when an operational release cannot safely continue."""


@dataclass(frozen=True)
class ExecutionAction:
    """One explicit, auditable release operation from an approved plan."""

    operation: str
    repository: str
    category: str
    workflow: str | None = None
    ref: str | None = None
    inputs: dict[str, str] = field(default_factory=dict)
    tag: str | None = None
    target_sha: str | None = None
    release_name: str | None = None
    release_notes: str | None = None
    artifact_hashes: dict[str, str] = field(default_factory=dict)
    wait_for_completion: bool = True


@dataclass(frozen=True)
class ExecutionRequest:
    """Explicit internal-release operations; no public channel is representable."""

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
            operation = item.get("operation")
            repository = item.get("repository")
            category = item.get("category")
            if operation not in {"workflow_dispatch", "create_tag", "draft_release"}:
                raise ExecutionError(f"action {index} has unsupported operation")
            if not isinstance(repository, str) or not repository:
                raise ExecutionError(f"action {index} requires repository")
            if category not in {"build", "artifact_publication", "deployment", "post_release"}:
                raise ExecutionError(f"action {index} has unsupported category")
            inputs = item.get("inputs", {})
            if not isinstance(inputs, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in inputs.items()):
                raise ExecutionError(f"action {index} inputs must be a string map")
            artifact_hashes = item.get("artifact_hashes", {})
            if not isinstance(artifact_hashes, dict) or not all(
                isinstance(key, str) and isinstance(value, str) and len(value) == 64
                and all(character in "0123456789abcdef" for character in value.lower())
                for key, value in artifact_hashes.items()
            ):
                raise ExecutionError(f"action {index} artifact_hashes must be a SHA-256 string map")
            workflow = item.get("workflow")
            ref = item.get("ref")
            tag = item.get("tag")
            target_sha = item.get("target_sha")
            release_name = item.get("release_name")
            release_notes = item.get("release_notes")
            for name, value in {
                "workflow": workflow,
                "ref": ref,
                "tag": tag,
                "target_sha": target_sha,
                "release_name": release_name,
                "release_notes": release_notes,
            }.items():
                if value is not None and not isinstance(value, str):
                    raise ExecutionError(f"action {index} {name} must be a string")
            if operation == "workflow_dispatch" and (not workflow or not ref):
                raise ExecutionError(f"action {index} workflow_dispatch requires workflow and ref")
            if operation == "create_tag" and (not tag or not target_sha):
                raise ExecutionError(f"action {index} create_tag requires tag and target_sha")
            if operation == "draft_release" and (not tag or not release_name):
                raise ExecutionError(f"action {index} draft_release requires tag and release_name")
            actions.append(
                ExecutionAction(
                    operation=operation,
                    repository=repository,
                    category=category,
                    workflow=workflow,
                    ref=ref,
                    inputs=dict(inputs),
                    tag=tag,
                    target_sha=target_sha,
                    release_name=release_name,
                    release_notes=release_notes,
                    artifact_hashes=dict(artifact_hashes),
                    wait_for_completion=bool(item.get("wait_for_completion", True)),
                )
            )
        return cls(
            release_profile="INTERNAL_RELEASE",
            actions=tuple(actions),
            requested_by=requested_by,
            non_production=bool(raw.get("non_production", False)),
        )


class ExecutionClient(Protocol):
    """Side-effect boundary used by the executor and test doubles."""

    def dispatch_workflow(self, action: ExecutionAction) -> dict[str, object]: ...

    def create_tag(self, action: ExecutionAction) -> dict[str, object]: ...

    def create_draft_release(self, action: ExecutionAction) -> dict[str, object]: ...


class EvidenceOnlyExecutionClient:
    """Safe representative client that exercises orchestration without GitHub mutation."""

    def dispatch_workflow(self, action: ExecutionAction) -> dict[str, object]:
        return {
            "kind": "workflow_dispatch",
            "workflow": action.workflow,
            "ref": action.ref,
            "inputs": action.inputs,
            "channel": "non_production_rehearsal",
            "simulated": True,
        }

    def create_tag(self, action: ExecutionAction) -> dict[str, object]:
        return {
            "kind": "git_tag",
            "tag": action.tag,
            "target_sha": action.target_sha,
            "channel": "non_production_rehearsal",
            "simulated": True,
        }

    def create_draft_release(self, action: ExecutionAction) -> dict[str, object]:
        return {
            "kind": "draft_github_release",
            "tag": action.tag,
            "draft": True,
            "prerelease": True,
            "channel": "non_production_rehearsal",
            "simulated": True,
        }


class ReleaseExecutor:
    """Execute one approved internal release and preserve evidence on failure."""

    def __init__(self, client: ExecutionClient) -> None:
        self.client = client

    def execute(self, manifest: dict[str, object], request: ExecutionRequest) -> dict[str, object]:
        _validate_execution_gate(manifest, request)
        discovered = {str(item["name"]) for item in manifest["repositories"] if isinstance(item, dict) and item.get("included")}
        evidence: list[dict[str, object]] = []
        started_at = _timestamp()
        for index, action in enumerate(request.actions):
            if action.repository not in discovered:
                return _failed_outcome(manifest, request, evidence, started_at, index, action, "repository is not in the qualified release scope")
            try:
                receipt = self._perform(action)
            except Exception as error:  # Client errors are evidence, never a partial continuation.
                return _failed_outcome(manifest, request, evidence, started_at, index, action, str(error))
            evidence.append({
                "index": index,
                "timestamp": _timestamp(),
                "operation": action.operation,
                "repository": action.repository,
                "category": action.category,
                "status": "PASS",
                "receipt": receipt,
                "artifact_hashes": action.artifact_hashes,
            })
        return {
            "schema_version": 1,
            "manifest_kind": "platform_release_execution",
            "execution_id": f"release-exec-{manifest['manifest_id']}",
            "source_manifest_id": manifest["manifest_id"],
            "platform_version": manifest["platform_version"],
            "release_profile": request.release_profile,
            "requested_by": request.requested_by,
            "non_production": request.non_production,
            "started_at": started_at,
            "completed_at": _timestamp(),
            "status": "PASS",
            "operations": evidence,
            "deployment_evidence": [item for item in evidence if item["category"] == "deployment"],
            "publication_evidence": [item for item in evidence if item["category"] == "artifact_publication"],
            "post_release_evidence": [item for item in evidence if item["category"] == "post_release"],
            "rollback_evidence": {
                "state": "PREPARED",
                "preserved_operations": len(evidence),
                "source_rollback_plan": manifest["rollback_plan"],
            },
        }

    def _perform(self, action: ExecutionAction) -> dict[str, object]:
        if action.operation == "workflow_dispatch":
            return self.client.dispatch_workflow(action)
        if action.operation == "create_tag":
            return self.client.create_tag(action)
        return self.client.create_draft_release(action)


def write_execution_evidence(outcome: dict[str, object], output_dir: Path) -> list[Path]:
    """Persist redaction-safe operational evidence produced by an execution."""

    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "release-execution-report.json": outcome,
        "release-deployment-evidence.json": outcome.get("deployment_evidence", []),
        "release-publication-evidence.json": outcome.get("publication_evidence", []),
    }
    written: list[Path] = []
    for name, content in files.items():
        path = output_dir / name
        path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written


def _validate_execution_gate(manifest: dict[str, object], request: ExecutionRequest) -> None:
    if manifest.get("release_mode") not in {"production", "hotfix"}:
        raise ExecutionError("operational execution requires production or hotfix release mode")
    readiness = manifest.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("state") != "READY":
        raise ExecutionError("operational execution requires READY release readiness")
    if manifest.get("qualification_status") not in {"QUALIFIED", "PASS"}:
        raise ExecutionError("operational execution requires qualified candidate evidence")
    if not isinstance(manifest.get("repositories"), list):
        raise ExecutionError("operational execution requires a canonical repository manifest")
    if request.release_profile != "INTERNAL_RELEASE":
        raise ExecutionError("only INTERNAL_RELEASE execution is supported")


def _failed_outcome(
    manifest: dict[str, object],
    request: ExecutionRequest,
    evidence: list[dict[str, object]],
    started_at: str,
    index: int,
    action: ExecutionAction,
    reason: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "manifest_kind": "platform_release_execution",
        "execution_id": f"release-exec-{manifest['manifest_id']}",
        "source_manifest_id": manifest["manifest_id"],
        "platform_version": manifest["platform_version"],
        "release_profile": request.release_profile,
        "requested_by": request.requested_by,
        "non_production": request.non_production,
        "started_at": started_at,
        "completed_at": _timestamp(),
        "status": "FAILED",
        "operations": evidence,
        "failure": {
            "index": index,
            "operation": action.operation,
            "repository": action.repository,
            "category": action.category,
            "reason": reason,
        },
        "deployment_evidence": [item for item in evidence if item["category"] == "deployment"],
        "publication_evidence": [item for item in evidence if item["category"] == "artifact_publication"],
        "post_release_evidence": [item for item in evidence if item["category"] == "post_release"],
        "rollback_evidence": {
            "state": "PRESERVE_AND_STOP",
            "preserved_operations": len(evidence),
            "source_rollback_plan": manifest["rollback_plan"],
        },
    }


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
