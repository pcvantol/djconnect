"""Redacted, durable qualification-evidence records.

The record deliberately projects only the formal decision from the existing
post-merge reconciliation evidence.  It is not a CI-log archive.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


_SHA = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID = re.compile(r"^[0-9]+$")
_FORBIDDEN = re.compile(
    r"(?i)(?:gh[pousr]_[a-z0-9_]+|github_pat_[a-z0-9_]+|bearer\s+\S+|"
    r"(?:token|password|secret|credential|authorization)\s*[:=])"
)
_PASS = "PASS"
_QUALIFIED = "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED"
_REQUIRED_PRE_MERGE = (
    "verification",
    "software_assurance",
    "trusted_delivery",
    "workflow_integrity",
    "required_checks",
)
_REQUIRED_POST_MERGE = (
    "ci",
    "tests",
    "lint",
    "static_analysis",
    "build_validation",
    "governance",
    "coverage",
)


class EvidencePreservationError(ValueError):
    """Raised when a durable record cannot safely represent formal evidence."""


def build_record(
    source: dict[str, Any],
    *,
    policy_source_revision: str,
    timestamp: str,
    workflow_run_id: str,
) -> dict[str, Any]:
    """Create one minimal, redacted, SHA-bound durable record.

    Only a qualified post-merge decision is publishable. Missing or malformed
    source data is an error rather than a best-effort archive.
    """

    _required_text(source, "repository")
    main_sha = _required_sha(source, "main_sha")
    _required_sha({"value": policy_source_revision}, "value")
    if not _RUN_ID.fullmatch(workflow_run_id):
        raise EvidencePreservationError("workflow run ID is invalid")
    if source.get("decision") != _QUALIFIED:
        raise EvidencePreservationError("only qualified post-merge evidence is publishable")
    source_digest = source.get("evidence_digest")
    if not isinstance(source_digest, str) or not _DIGEST.fullmatch(source_digest):
        raise EvidencePreservationError("source evidence digest is invalid")

    pre_merge = _required_mapping(source, "pre_merge")
    post_merge = _required_mapping(source, "post_merge")
    _require_passes(pre_merge, _REQUIRED_PRE_MERGE, "pre-merge")
    _require_passes(post_merge, _REQUIRED_POST_MERGE, "post-merge")
    if post_merge.get("sha") != main_sha:
        raise EvidencePreservationError("post-merge SHA does not match main SHA")
    if post_merge.get("coverage_report_sha") != main_sha:
        raise EvidencePreservationError("coverage report SHA does not match main SHA")
    coverage_artifact_digest = _normalized_digest(
        post_merge.get("coverage_artifact_sha"),
        "coverage artifact digest",
    )
    run_ids = post_merge.get("workflow_run_ids")
    if not isinstance(run_ids, list) or not run_ids or not all(isinstance(item, str) and _RUN_ID.fullmatch(item) for item in run_ids):
        raise EvidencePreservationError("post-merge workflow run IDs are invalid")

    required_checks = {
        **{key: pre_merge[key] for key in _REQUIRED_PRE_MERGE},
        **{f"post_merge_{key}": post_merge[key] for key in _REQUIRED_POST_MERGE},
    }
    record: dict[str, Any] = {
        "schema_version": 1,
        "kind": "durable_qualification_evidence",
        "record_id": f"{source['repository']}@{main_sha}:post-merge-release-evidence",
        "revision": 1,
        "retention_class": "LONG_TERM",
        "repository": source["repository"],
        "repository_role": source.get("repository_role"),
        "commit_sha": main_sha,
        "source_revision": policy_source_revision,
        "release_identifier": f"internal-ha-{main_sha}",
        "qualification": {
            "profile": "post_merge_release_evidence",
            "outcome": source["decision"],
            "required_checks": required_checks,
        },
        "workflow_references": {
            "producer_run_id": workflow_run_id,
            "post_merge_run_ids": run_ids,
        },
        "source_evidence_digest": source_digest,
        "redaction": {
            "status": "REDACTED",
            "policy_version": 1,
            "included_data": "formal allowlisted decision fields only",
        },
        "published_at": timestamp,
        "supplemental_evidence": [
            {"kind": "coverage_artifact_digest", "sha256": coverage_artifact_digest}
        ],
    }
    _reject_sensitive_content(record)
    record["integrity"] = {"algorithm": "sha256-canonical-json", "digest": _digest(record)}
    return record


def validate_record(record: dict[str, Any]) -> list[str]:
    """Return deterministic validation findings for a published record."""

    errors: list[str] = []
    if record.get("schema_version") != 1:
        errors.append("unsupported schema version")
    if record.get("kind") != "durable_qualification_evidence":
        errors.append("incorrect record kind")
    if record.get("retention_class") != "LONG_TERM":
        errors.append("incorrect retention class")
    if not isinstance(record.get("commit_sha"), str) or not _SHA.fullmatch(record["commit_sha"]):
        errors.append("invalid commit SHA")
    if record.get("redaction", {}).get("status") != "REDACTED":
        errors.append("redaction status is not REDACTED")
    qualification = record.get("qualification")
    if not isinstance(qualification, dict) or qualification.get("outcome") != _QUALIFIED:
        errors.append("qualification outcome is not qualified")
    checks = qualification.get("required_checks") if isinstance(qualification, dict) else None
    if not isinstance(checks, dict) or not checks or any(value != _PASS for value in checks.values()):
        errors.append("required formal check result is missing or not PASS")
    integrity = record.get("integrity")
    if not isinstance(integrity, dict) or integrity.get("algorithm") != "sha256-canonical-json" or not isinstance(integrity.get("digest"), str):
        errors.append("integrity metadata is invalid")
    elif integrity["digest"] != _digest(record):
        errors.append("integrity digest does not match canonical record")
    try:
        _reject_sensitive_content(record)
    except EvidencePreservationError as exc:
        errors.append(str(exc))
    return errors


def publication_asset_name(commit_sha: str) -> str:
    """Return the deterministic, collision-protected release-asset name."""

    if not _SHA.fullmatch(commit_sha):
        raise EvidencePreservationError("commit SHA is invalid")
    return f"qualification-evidence-{commit_sha}.json"


def _required_mapping(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise EvidencePreservationError(f"{key} is missing")
    return item


def _required_text(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise EvidencePreservationError(f"{key} is required")
    return item


def _required_sha(value: dict[str, Any], key: str) -> str:
    item = _required_text(value, key)
    if not _SHA.fullmatch(item):
        raise EvidencePreservationError(f"{key} must be a lowercase SHA")
    return item


def _normalized_digest(value: object, label: str) -> str:
    """Accept GitHub's ``sha256:`` artifact form and store canonical hex."""

    if not isinstance(value, str):
        raise EvidencePreservationError(f"{label} is invalid")
    digest = value.removeprefix("sha256:")
    if not _DIGEST.fullmatch(digest):
        raise EvidencePreservationError(f"{label} is invalid")
    return digest


def _require_passes(value: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    for key in keys:
        if value.get(key) != _PASS:
            raise EvidencePreservationError(f"{label} {key} is not PASS")


def _reject_sensitive_content(value: object) -> None:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if _FORBIDDEN.search(serialized):
        raise EvidencePreservationError("record contains a forbidden sensitive pattern")


def _digest(value: dict[str, Any]) -> str:
    source = {key: item for key, item in value.items() if key != "integrity"}
    return hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
