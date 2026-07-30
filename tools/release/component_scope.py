"""Fail-closed component-release selection and evidence closure.

The Platform Release Runtime owns this internal contract.  It records a
component candidate only; it never enables publication or execution.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .versioning import PlatformVersion, RepositoryVersion, VersionError


_SHA = re.compile(r"^[0-9a-f]{40}$")
_CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
_EVIDENCE = (
    "source_qualification",
    "build_test",
    "software_assurance",
    "trusted_delivery",
    "artifact_provenance",
    "manifest_validation",
    "channel_validation",
    "durable_post_merge",
    "owner_authorization",
)


@dataclass(frozen=True)
class ComponentProfile:
    """One registered component boundary from the scope-refinement contract."""

    component_id: str
    component_owner: str
    source_repository: str | None
    participants: tuple[str, ...]
    release_channel: str | None
    target_distribution: str | None
    artifact_kind: str | None
    selectable: bool = True


COMPONENT_PROFILES = {
    "hacs-integration": ComponentProfile("hacs-integration", "DJConnect Home Assistant integration", "pcvantol/djconnect", ("pcvantol/djconnect",), "hacs", "HACS", "home_assistant_integration_tarball"),
    "api-worker": ComponentProfile("api-worker", "DJConnect API", "pcvantol/djconnect-api", ("pcvantol/djconnect-api",), "api-production", "API worker deployment", "worker_bundle"),
    "website": ComponentProfile("website", "DJConnect Website", "pcvantol/djconnect-website", ("pcvantol/djconnect-website",), "website-production", "DJConnect website", "static_site_bundle"),
    "esp32-firmware": ComponentProfile("esp32-firmware", "DJConnect ESP32 firmware", "pcvantol/djconnect-esp32", ("pcvantol/djconnect-esp32", "pcvantol/djconnect-firmware"), "firmware-public", "pcvantol/djconnect-firmware", "firmware_bundle"),
    "apple-ios-watchos": ComponentProfile("apple-ios-watchos", "DJConnect Apple Client", "pcvantol/djconnect-app", ("pcvantol/djconnect-app", "pcvantol/djconnect-app-releases"), "apple-ios-watchos-internal", "Apple iOS/watchOS internal distribution", "ios_watchos_artifact"),
    "apple-macos": ComponentProfile("apple-macos", "DJConnect Apple Client", "pcvantol/djconnect-app", ("pcvantol/djconnect-app", "pcvantol/djconnect-app-releases"), "apple-macos-internal", "Apple macOS internal distribution", "macos_artifact"),
    "windows-client": ComponentProfile("windows-client", "DJConnect Windows Client", "pcvantol/djconnect-windows", ("pcvantol/djconnect-windows", "pcvantol/djconnect-app-releases"), "windows-internal", "Windows internal distribution", "windows_artifact"),
    "pi-renderer-family": ComponentProfile("pi-renderer-family", "DJConnect Raspberry Pi Renderer", "pcvantol/djconnect-pi", ("pcvantol/djconnect-pi", "pcvantol/djconnect-pi-releases"), "pi-public", "pcvantol/djconnect-pi-releases", "pi_renderer_bundle"),
    "pi-4-inch": ComponentProfile("pi-4-inch", "DJConnect Raspberry Pi Renderer", None, (), None, None, None, selectable=False),
    "pi-10-inch": ComponentProfile("pi-10-inch", "DJConnect Raspberry Pi Renderer", None, (), None, None, None, selectable=False),
}


def validate_component_selection(
    selection: object,
    platform: PlatformVersion,
    versions: dict[str, str],
    shas: dict[str, str],
) -> dict[str, object]:
    """Normalize one registered selection and return all fail-closed findings."""

    conditions: list[dict[str, str]] = []
    if not isinstance(selection, dict):
        return _result(None, conditions, "NOT_SELECTED")
    component_id = selection.get("component_id")
    if not isinstance(component_id, str) or component_id not in COMPONENT_PROFILES:
        conditions.append(_condition("BLOCKED", "component_profile_unknown", "component_id", "one registered component profile is required"))
        return _result(None, conditions, "INVALID")
    profile = COMPONENT_PROFILES[component_id]
    if not profile.selectable:
        conditions.append(_condition("BLOCKED", "component_profile_not_selectable", component_id, "this product profile has no independent artifact, manifest or target evidence"))
        return _result(profile, conditions, "INVALID")

    _exact(selection, "component_owner", profile.component_owner, conditions)
    _exact(selection, "source_repository", profile.source_repository, conditions)
    _exact(selection, "release_channel", profile.release_channel, conditions)
    _exact(selection, "target_distribution", profile.target_distribution, conditions)
    _exact(selection, "artifact_kind", profile.artifact_kind, conditions)
    _participants(selection.get("participants"), profile.participants, conditions)

    source_sha = selection.get("source_sha")
    if not isinstance(source_sha, str) or not _SHA.fullmatch(source_sha):
        conditions.append(_condition("BLOCKED", "source_sha_invalid", component_id, "source_sha must be one immutable 40-character SHA"))
    elif source_sha != shas.get(profile.source_repository):
        conditions.append(_condition("BLOCKED", "source_sha_mismatch", component_id, "source_sha must match the selected source repository candidate SHA"))

    version = selection.get("version")
    if not isinstance(version, str):
        conditions.append(_condition("NOT_READY", "component_version_missing", component_id, "component version is required"))
    else:
        try:
            parsed = RepositoryVersion.parse(version)
            if not parsed.compatible_with(platform):
                conditions.append(_condition("BLOCKED", "component_platform_misalignment", component_id, "component version is outside the requested platform train"))
            if version != versions.get(profile.source_repository):
                conditions.append(_condition("BLOCKED", "component_version_mismatch", component_id, "component version must match the selected source repository version"))
        except VersionError as error:
            conditions.append(_condition("BLOCKED", "component_version_invalid", component_id, str(error)))
    _exact(selection, "platform_train", str(platform), conditions)
    _identifier(selection, "artifact_identity", conditions)
    _checksum(selection, "artifact_sha256", conditions)
    _identifier(selection, "manifest_id", conditions)
    _checksum(selection, "manifest_sha256", conditions)
    _evidence_closure(selection, profile, conditions)
    return _result(profile, conditions, "SELECTED")


def _result(profile: ComponentProfile | None, conditions: list[dict[str, str]], state: str) -> dict[str, object]:
    readiness = "BLOCKED" if any(item["state"] == "BLOCKED" for item in conditions) else "NOT_READY" if conditions else "READY"
    return {
        "state": state,
        "readiness": readiness,
        "profile": profile,
        "participants": list(profile.participants) if profile and profile.selectable else [],
        "conditions": conditions,
    }


def _exact(selection: dict[str, object], field: str, expected: str | None, conditions: list[dict[str, str]]) -> None:
    if selection.get(field) != expected:
        conditions.append(_condition("BLOCKED", f"{field}_mismatch", field, "value does not match the registered component profile"))


def _participants(value: object, expected: tuple[str, ...], conditions: list[dict[str, str]]) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value) or len(value) != len(set(value)) or set(value) != set(expected):
        conditions.append(_condition("BLOCKED", "participants_mismatch", "participants", "participants must be exactly the registered closure-required participants"))


def _identifier(selection: dict[str, object], field: str, conditions: list[dict[str, str]]) -> None:
    value = selection.get(field)
    if not isinstance(value, str) or not value.strip():
        conditions.append(_condition("NOT_READY", f"{field}_missing", field, f"{field} must identify one immutable value"))


def _checksum(selection: dict[str, object], field: str, conditions: list[dict[str, str]]) -> None:
    value = selection.get(field)
    if not isinstance(value, str) or not _CHECKSUM.fullmatch(value):
        conditions.append(_condition("BLOCKED", f"{field}_invalid", field, f"{field} must be a 64-character SHA-256 checksum"))


def _evidence_closure(selection: dict[str, object], profile: ComponentProfile, conditions: list[dict[str, str]]) -> None:
    records = selection.get("evidence")
    if not isinstance(records, dict):
        conditions.append(_condition("NOT_READY", "component_evidence_missing", profile.component_id, "component evidence closure is required"))
        return
    if set(records) != set(_EVIDENCE):
        conditions.append(_condition("BLOCKED", "component_evidence_set_mismatch", profile.component_id, "component evidence must contain exactly the canonical closure records"))
        return
    bindings = {name: selection.get(name) for name in ("component_id", "source_sha", "artifact_identity", "artifact_sha256", "manifest_id", "manifest_sha256", "version")}
    for name in _EVIDENCE:
        record = records.get(name)
        if not isinstance(record, dict) or record.get("status") != "PASS":
            conditions.append(_condition("NOT_READY", "component_evidence_not_qualified", name, "evidence record must be PASS"))
            continue
        for key, expected in bindings.items():
            if record.get(key) != expected:
                conditions.append(_condition("BLOCKED", "component_evidence_binding_mismatch", name, f"evidence {key} does not bind the selected component"))


def _condition(state: str, code: str, subject: str, message: str) -> dict[str, str]:
    return {"state": state, "code": code, "subject": subject, "message": message}
