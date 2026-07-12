"""Canonical policy loading and reusable CI governance validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


POLICY_ROOT = Path(__file__).resolve().parents[2] / "software_assurance"
CANONICAL_POLICY_PATH = POLICY_ROOT / "policy" / "governance-policy.json"
REQUIRED_POLICY_SECTIONS = frozenset(
    {
        "schema_version",
        "policy_id",
        "policy_version",
        "ownership",
        "workflow_governance",
        "execution_profiles",
        "runner_governance",
        "retention_governance",
        "artifact_governance",
        "pull_request_governance",
        "repository_governance",
    }
)
REQUIRED_PROFILES = frozenset({"economy", "balanced", "release"})
REQUIRED_VALIDATORS = frozenset(
    {
        "policy",
        "workflow",
        "permissions",
        "runner",
        "retention",
        "artifact",
        "repository_rollout",
    }
)


class PolicyValidationError(ValueError):
    """Raised when policy or a future rollout candidate violates governance."""


def load_canonical_policy(path: Path = CANONICAL_POLICY_PATH) -> dict[str, Any]:
    """Load and validate the single canonical governance policy source."""
    with path.open(encoding="utf-8") as policy_file:
        policy = json.load(policy_file)
    validate_policy(policy)
    return policy


def validate_policy(policy: Mapping[str, Any]) -> None:
    """Validate the policy relationships required before any rollout occurs."""
    _require_keys(policy, REQUIRED_POLICY_SECTIONS, "policy")
    if policy["schema_version"] != 1:
        raise PolicyValidationError("Unsupported governance policy schema version.")
    if policy["policy_id"] != "djconnect.software_assurance.ci_governance":
        raise PolicyValidationError("Unexpected governance policy identifier.")

    ownership = _mapping(policy["ownership"], "ownership")
    if ownership.get("workflow_rollout_enabled") is not False:
        raise PolicyValidationError("Prompt 1 policy must not enable workflow rollout.")

    workflow = _mapping(policy["workflow_governance"], "workflow_governance")
    _require_keys(
        workflow,
        {
            "required_metadata",
            "permissions",
            "timeout_minutes",
            "concurrency",
            "action_pinning",
            "logging",
            "summaries",
            "retry",
        },
        "workflow_governance",
    )
    if not {"name", "execution_profile", "policy_version"}.issubset(
        _string_set(workflow["required_metadata"], "workflow required_metadata")
    ):
        raise PolicyValidationError("Workflow metadata must identify name, profile and policy version.")
    _validate_timeout(_mapping(workflow["timeout_minutes"], "timeout_minutes"))
    if workflow["action_pinning"] != "full_length_commit_sha":
        raise PolicyValidationError("Action pinning must require full-length commit SHAs.")
    _validate_retry(_mapping(workflow["retry"], "retry"))

    profiles = _mapping(policy["execution_profiles"], "execution_profiles")
    if set(profiles) != REQUIRED_PROFILES:
        raise PolicyValidationError("Execution profiles must be economy, balanced and release.")
    for name in REQUIRED_PROFILES:
        _require_keys(
            _mapping(profiles[name], f"execution profile {name}"),
            {
                "execution_targets",
                "parallelism",
                "artifact_retention_class",
                "evidence_level",
                "hardware_usage",
                "retry_policy",
            },
            f"execution profile {name}",
        )

    retention = _mapping(policy["retention_governance"], "retention_governance")
    for retention_class in ("routine", "failure", "qualification", "release"):
        _validate_retention_class(
            _mapping(retention[retention_class], f"retention {retention_class}"), retention_class
        )
    if retention["dry_run"].get("mutates_artifacts") is not False:
        raise PolicyValidationError("Dry-run support must not mutate artifacts.")

    repository = _mapping(policy["repository_governance"], "repository_governance")
    validators = _string_set(repository["validation"], "repository validation")
    if validators != REQUIRED_VALIDATORS:
        raise PolicyValidationError("The reusable validation framework is incomplete.")


def validate_rollout_candidate(
    candidate: Mapping[str, Any], policy: Mapping[str, Any] | None = None
) -> list[str]:
    """Return validation findings for a future repository rollout candidate.

    This intentionally validates supplied metadata only. It neither reads nor
    changes repository workflows, keeping Prompt 1 independent of rollout.
    """
    policy = policy or load_canonical_policy()
    validate_policy(policy)
    findings: list[str] = []
    workflow = _mapping(policy["workflow_governance"], "workflow_governance")
    required_metadata = _string_set(workflow["required_metadata"], "required_metadata")
    missing = sorted(required_metadata.difference(candidate))
    if missing:
        findings.append(f"missing workflow metadata: {', '.join(missing)}")

    profile = candidate.get("execution_profile")
    if profile not in policy["execution_profiles"]:
        findings.append("execution_profile must select economy, balanced or release")

    timeout = candidate.get("timeout_minutes")
    timeout_policy = _mapping(workflow["timeout_minutes"], "timeout_minutes")
    if not isinstance(timeout, int) or not (
        timeout_policy["minimum"] <= timeout <= timeout_policy["maximum"]
    ):
        findings.append("timeout_minutes is outside the canonical policy bounds")

    if candidate.get("permissions") in (None, "read-write"):
        findings.append("permissions must be explicitly declared and least-privilege")
    elif isinstance(candidate.get("permissions"), Mapping):
        findings.extend(validate_permission_declaration(candidate["permissions"], policy))
    if not candidate.get("concurrency_group"):
        findings.append("concurrency_group is required")
    if candidate.get("action_pinning") != workflow["action_pinning"]:
        findings.append("action_pinning must use full_length_commit_sha")
    if "runner" in candidate:
        findings.extend(validate_runner_selection(_mapping(candidate["runner"], "runner"), policy))
    if "retention" in candidate:
        findings.extend(validate_retention_selection(_mapping(candidate["retention"], "retention"), policy))
    if "artifact" in candidate:
        findings.extend(validate_artifact_selection(_mapping(candidate["artifact"], "artifact"), policy))
    if "repository_override" in candidate:
        findings.extend(
            validate_repository_override(_mapping(candidate["repository_override"], "repository_override"), policy)
        )
    return findings


def validate_permission_declaration(
    permissions: Mapping[str, Any], policy: Mapping[str, Any] | None = None
) -> list[str]:
    """Validate an explicit least-privilege permission declaration."""
    policy = policy or load_canonical_policy()
    policy_permissions = _mapping(
        _mapping(policy["workflow_governance"], "workflow_governance")["permissions"], "permissions"
    )
    allowed_write_scopes = _string_set(policy_permissions["allowed_write_scopes"], "allowed_write_scopes")
    findings: list[str] = []
    if not permissions:
        return ["permissions must be explicitly declared"]
    for scope, level in permissions.items():
        if level not in {"read", "write", "none"}:
            findings.append(f"permission {scope} has unsupported level {level}")
        if level == "write" and scope not in allowed_write_scopes:
            findings.append(f"permission {scope} is not approved for write access")
    return findings


def validate_runner_selection(
    runner: Mapping[str, Any], policy: Mapping[str, Any] | None = None
) -> list[str]:
    """Validate future runner metadata without scheduling any runner."""
    policy = policy or load_canonical_policy()
    runner_policy = _mapping(policy["runner_governance"], "runner_governance")
    runner_type = runner.get("type")
    if runner_type not in runner_policy:
        return ["runner type must be github_hosted, self_hosted or hybrid"]
    if runner_type == "self_hosted":
        labels = set(runner.get("labels", []))
        allowed_labels = _string_set(
            _mapping(runner_policy["self_hosted"], "self_hosted")["capability_labels"], "capability_labels"
        )
        findings = []
        if not labels:
            findings.append("self-hosted runner requires capability labels")
        if not labels.issubset(allowed_labels):
            findings.append("self-hosted runner uses unrecognized capability labels")
        if runner.get("qualified") is not True or runner.get("healthy") is not True:
            findings.append("self-hosted runner must be qualified and healthy")
        return findings
    if runner_type == "hybrid" and runner.get("execution_plan") is not True:
        return ["hybrid runner selection requires an execution plan"]
    return []


def validate_retention_selection(
    retention: Mapping[str, Any], policy: Mapping[str, Any] | None = None
) -> list[str]:
    """Validate a requested retention class and duration."""
    policy = policy or load_canonical_policy()
    governance = _mapping(policy["retention_governance"], "retention_governance")
    retention_class = retention.get("class")
    if retention_class not in {"routine", "failure", "qualification", "release"}:
        return ["retention class is not recognized"]
    days = retention.get("days")
    bounds = _mapping(governance[retention_class], f"retention {retention_class}")
    if not isinstance(days, int) or not bounds["minimum_days"] <= days <= bounds["maximum_days"]:
        return ["retention days are outside canonical bounds"]
    return []


def validate_artifact_selection(
    artifact: Mapping[str, Any], policy: Mapping[str, Any] | None = None
) -> list[str]:
    """Validate artifact category and redaction posture."""
    policy = policy or load_canonical_policy()
    artifact_policy = _mapping(policy["artifact_governance"], "artifact_governance")
    categories = _mapping(artifact_policy["categories"], "artifact categories")
    findings = []
    if artifact.get("category") not in categories:
        findings.append("artifact category is not recognized")
    if artifact.get("redacted") is not True:
        findings.append("artifact must be redacted before upload")
    return findings


def validate_repository_override(
    override: Mapping[str, Any], policy: Mapping[str, Any] | None = None
) -> list[str]:
    """Reject overrides that relax protected platform policy constraints."""
    policy = policy or load_canonical_policy()
    overrides = _mapping(
        _mapping(policy["repository_governance"], "repository_governance")["overrides"], "overrides"
    )
    protected = _string_set(overrides["may_not_relax"], "protected overrides")
    findings = []
    if not override.get("reason") or not override.get("owner"):
        findings.append("repository override requires explicit reason and owner")
    relaxed = set(override.get("relaxes", []))
    protected_relaxations = sorted(relaxed.intersection(protected))
    if protected_relaxations:
        findings.append(
            "repository override may not relax: " + ", ".join(protected_relaxations)
        )
    return findings


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PolicyValidationError(f"{name} must be an object.")
    return value


def _require_keys(value: Mapping[str, Any], required: set[str] | frozenset[str], name: str) -> None:
    missing = sorted(set(required).difference(value))
    if missing:
        raise PolicyValidationError(f"{name} is missing required keys: {', '.join(missing)}")


def _string_set(value: Any, name: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PolicyValidationError(f"{name} must be a list of strings.")
    return set(value)


def _validate_timeout(value: Mapping[str, Any]) -> None:
    minimum = value.get("minimum")
    default = value.get("default")
    maximum = value.get("maximum")
    if not all(isinstance(item, int) for item in (minimum, default, maximum)):
        raise PolicyValidationError("Workflow timeout policy must use integer minutes.")
    if not minimum <= default <= maximum:
        raise PolicyValidationError("Workflow timeout policy bounds are invalid.")


def _validate_retry(value: Mapping[str, Any]) -> None:
    if value.get("maximum_attempts") != 2:
        raise PolicyValidationError("Retry policy must bound attempts at two.")
    if value.get("preserve_failed_evidence") is not True:
        raise PolicyValidationError("Retry policy must preserve failed evidence.")
    if value.get("require_classification_before_repeat") is not True:
        raise PolicyValidationError("Retry policy must require failure classification.")


def _validate_retention_class(value: Mapping[str, Any], name: str) -> None:
    minimum = value.get("minimum_days")
    default = value.get("default_days")
    maximum = value.get("maximum_days")
    if not all(isinstance(item, int) for item in (minimum, default, maximum)):
        raise PolicyValidationError(f"Retention {name} must use integer day values.")
    if not 0 < minimum <= default <= maximum:
        raise PolicyValidationError(f"Retention {name} bounds are invalid.")
