"""Evidence-driven readiness evaluation without executing verification."""

from __future__ import annotations

from .discovery import RepositoryNode
from .planner import mode_policy
from .versioning import PlatformVersion, RepositoryVersion, VersionError
from tools.trusted_delivery.post_merge_reconciliation import validate_release_evidence


def evaluate_readiness(
    nodes: list[RepositoryNode],
    platform_version: PlatformVersion,
    versions: dict[str, str],
    shas: dict[str, str],
    evidence: dict[str, str],
    mode: str,
    profile: str | None = None,
    reconciliations: dict[str, object] | None = None,
    component_conditions: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Return READY, NOT_READY or BLOCKED and every contributing condition."""

    conditions: list[dict[str, str]] = []
    for node in nodes:
        if not node.mandatory:
            continue
        raw_version = versions.get(node.name)
        if not raw_version:
            conditions.append(_condition("NOT_READY", "version_missing", node.name, "repository version is required"))
        else:
            try:
                version = RepositoryVersion.parse(raw_version)
                if not version.compatible_with(platform_version):
                    conditions.append(
                        _condition("BLOCKED", "platform_misalignment", node.name, f"{version} is not aligned to {platform_version}")
                    )
            except VersionError as error:
                conditions.append(_condition("BLOCKED", "version_invalid", node.name, str(error)))
        if not shas.get(node.name):
            conditions.append(_condition("NOT_READY", "sha_missing", node.name, "repository SHA is required"))
        else:
            reconciliation = (reconciliations or {}).get(node.name)
            if not isinstance(reconciliation, dict):
                conditions.append(_condition("NOT_READY", "post_merge_evidence_missing", node.name, "exact-main-SHA reconciliation evidence is required"))
            else:
                for error in validate_release_evidence(reconciliation, node.name, shas[node.name]):
                    conditions.append(_condition("BLOCKED", "post_merge_evidence_invalid", node.name, error))

    conditions.extend(component_conditions or [])
    for evidence_name in mode_policy(mode, profile)["required_evidence"]:
        value = evidence.get(str(evidence_name), "MISSING")
        if value != "PASS":
            state = "NOT_READY" if value in {"MISSING", "UNKNOWN"} else "BLOCKED"
            conditions.append(_condition(state, "evidence_not_qualified", str(evidence_name), f"state is {value}"))
    state = "BLOCKED" if any(item["state"] == "BLOCKED" for item in conditions) else "NOT_READY" if conditions else "READY"
    return {"state": state, "conditions": conditions}


def _condition(state: str, code: str, subject: str, message: str) -> dict[str, str]:
    return {"state": state, "code": code, "subject": subject, "message": message}
