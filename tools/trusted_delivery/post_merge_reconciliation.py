"""Fail-closed post-merge evidence reconciliation.

The release identity is always the exact commit pushed to ``main``.  A squash
merge is therefore validated as a *derivation* of a qualified pull-request
head, never as SHA equality with that head.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any


_SHA = re.compile(r"^[0-9a-f]{40}$")
_PASS = "PASS"
_QUALIFIED = "POST_MERGE_RELEASE_EVIDENCE_QUALIFIED"
_NOT_QUALIFIED = "POST_MERGE_RELEASE_EVIDENCE_NOT_QUALIFIED"


class ReconciliationError(ValueError):
    """Raised when reconciliation input is malformed or not trustworthy."""


def reconcile(request: dict[str, Any]) -> dict[str, Any]:
    """Return immutable exact-main-SHA evidence without weakening any gate.

    All input is expected to be read back from GitHub by the workflow. Missing
    or ambiguous provenance is represented by a NOT_QUALIFIED evidence record
    instead of an inferred pass.
    """

    repository = _required_text(request, "repository")
    main_sha = _required_sha(request, "main_sha")
    timestamp = str(request.get("timestamp") or _now())
    findings: list[str] = []

    parents = request.get("main_parents")
    if not isinstance(parents, list) or not parents or not all(isinstance(parent, str) and _SHA.fullmatch(parent) for parent in parents):
        findings.append("main commit parents are missing or invalid")

    pr = request.get("originating_pr")
    if not isinstance(pr, dict):
        findings.append("no originating pull request was resolved")
        pr = {}
    else:
        _validate_provenance(pr, main_sha, parents, findings)

    _validate_pre_merge(request.get("pre_merge"), pr, findings)
    _validate_post_merge(request.get("post_merge"), main_sha, findings)

    decision = _QUALIFIED if not findings else _NOT_QUALIFIED
    evidence = {
        "schema_version": 1,
        "kind": "post_merge_release_evidence",
        "repository": repository,
        "main_sha": main_sha,
        "main_parents": parents if isinstance(parents, list) else [],
        "originating_pr": _public_pr(pr),
        "source_qualified_pr_sha": pr.get("head_sha"),
        "merge_strategy": pr.get("merge_strategy"),
        "merge_actor": pr.get("merge_actor"),
        "pre_merge": request.get("pre_merge") if isinstance(request.get("pre_merge"), dict) else {},
        "post_merge": request.get("post_merge") if isinstance(request.get("post_merge"), dict) else {},
        "provenance_result": _PASS if not any("pull request" in item or "derivation" in item or "merge" in item or "changed-file" in item for item in findings) else "FAIL",
        "findings": findings,
        "decision": decision,
        "timestamp": timestamp,
    }
    evidence["evidence_digest"] = _digest(evidence)
    return evidence


def validate_release_evidence(evidence: dict[str, Any], repository: str, main_sha: str) -> list[str]:
    """Validate the exact-SHA evidence a release manifest is allowed to use."""

    errors: list[str] = []
    if evidence.get("schema_version") != 1:
        errors.append("unsupported reconciliation evidence schema")
    if evidence.get("kind") != "post_merge_release_evidence":
        errors.append("evidence kind is not post_merge_release_evidence")
    if evidence.get("repository") != repository:
        errors.append("evidence repository does not match release repository")
    if evidence.get("main_sha") != main_sha:
        errors.append("evidence main SHA does not match release SHA")
    if evidence.get("decision") != _QUALIFIED:
        errors.append("post-merge evidence is not qualified")
    if evidence.get("source_qualified_pr_sha") == main_sha:
        errors.append("evidence incorrectly claims PR and main SHA identity")
    if not evidence.get("evidence_digest"):
        errors.append("evidence digest is missing")
    return errors


def _validate_provenance(pr: dict[str, Any], main_sha: str, parents: object, findings: list[str]) -> None:
    if pr.get("state") != "MERGED" or pr.get("base_ref") != "main":
        findings.append("originating pull request was not merged into main")
    if not _is_sha(pr.get("head_sha")):
        findings.append("originating pull request final head SHA is invalid")
    if pr.get("merge_commit_sha") != main_sha:
        findings.append("main SHA is not the GitHub-recorded merge commit for the originating pull request")
    if pr.get("merge_strategy") not in {"SQUASH", "MERGE", "REBASE"}:
        findings.append("merge strategy is unsupported")
    if not pr.get("merge_actor") or not pr.get("merged_at"):
        findings.append("merge actor or timestamp is missing")
    pr_files = pr.get("changed_files")
    main_files = pr.get("main_changed_files")
    if not isinstance(pr_files, list) or not isinstance(main_files, list):
        findings.append("changed-file provenance is missing")
    elif sorted(set(pr_files)) != sorted(set(main_files)):
        findings.append("main commit changed-file set is not solely derived from the pull request")
    if isinstance(parents, list) and pr.get("merge_strategy") == "SQUASH" and len(parents) != 1:
        findings.append("squash merge must have exactly one main parent")


def _validate_pre_merge(value: object, pr: dict[str, Any], findings: list[str]) -> None:
    if not isinstance(value, dict):
        findings.append("pre-merge qualification evidence is missing")
        return
    if value.get("candidate_sha") != pr.get("head_sha"):
        findings.append("pre-merge evidence is stale or bound to a different PR SHA")
    for key in ("verification", "software_assurance", "trusted_delivery", "workflow_integrity", "required_checks"):
        if value.get(key) != _PASS:
            findings.append(f"pre-merge {key} is not PASS")
    if value.get("risk_classification") == "HIGH_RISK" and value.get("owner_authorization") != _PASS:
        findings.append("HIGH_RISK pull request lacks owner authorization")
    if value.get("risk_classification") not in {"LOW_RISK", "NORMAL_RISK", "HIGH_RISK"}:
        findings.append("pre-merge risk classification is invalid")


def _validate_post_merge(value: object, main_sha: str, findings: list[str]) -> None:
    if not isinstance(value, dict):
        findings.append("post-merge evidence is missing")
        return
    if value.get("sha") != main_sha:
        findings.append("post-merge evidence SHA does not match main SHA")
    for key in ("ci", "tests", "lint", "static_analysis", "build_validation", "governance", "coverage"):
        if value.get(key) != _PASS:
            findings.append(f"post-merge {key} is not PASS")
    if not value.get("coverage_artifact_sha") or value.get("coverage_report_sha") != main_sha:
        findings.append("coverage is not bound to the exact main SHA")
    if not value.get("workflow_run_ids"):
        findings.append("post-merge workflow run IDs are missing")


def _public_pr(pr: dict[str, Any]) -> dict[str, Any]:
    return {key: pr.get(key) for key in ("number", "state", "base_ref", "head_sha", "merge_commit_sha", "merge_strategy", "merge_actor", "merged_at", "changed_files", "main_changed_files")}


def _required_text(value: dict[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ReconciliationError(f"{key} is required")
    return result


def _required_sha(value: dict[str, Any], key: str) -> str:
    result = _required_text(value, key)
    if not _SHA.fullmatch(result):
        raise ReconciliationError(f"{key} must be a full lowercase SHA")
    return result


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _digest(value: dict[str, Any]) -> str:
    source = {key: item for key, item in value.items() if key != "evidence_digest"}
    return hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
