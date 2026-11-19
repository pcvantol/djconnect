"""Release Manifest validation independent of a JSON Schema implementation."""

from __future__ import annotations

from .versioning import PlatformVersion


REQUIRED_FIELDS = {
    "schema_version",
    "manifest_kind",
    "manifest_id",
    "platform_version",
    "release_mode",
    "simulation_only",
    "repositories",
    "dependency_graph",
    "execution_plan",
    "qualification_plan",
    "readiness",
    "artifact_inventory",
    "rollback_plan",
    "certification_state",
}


def validate_manifest(manifest: dict[str, object]) -> list[str]:
    """Return schema-level violations without relying on optional packages."""

    issues = [f"missing required field: {field}" for field in sorted(REQUIRED_FIELDS - manifest.keys())]
    if manifest.get("schema_version") != 1:
        issues.append("schema_version must be 1")
    if manifest.get("manifest_kind") != "platform_release_simulation":
        issues.append("manifest_kind must be platform_release_simulation")
    if manifest.get("simulation_only") is not True:
        issues.append("simulation_only must be true")
    try:
        PlatformVersion.parse(str(manifest.get("platform_version", "")))
    except ValueError as error:
        issues.append(str(error))
    if not isinstance(manifest.get("repositories"), list):
        issues.append("repositories must be an array")
    readiness = manifest.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("state") not in {"READY", "NOT_READY", "BLOCKED"}:
        issues.append("readiness must contain a valid state")
    return issues
