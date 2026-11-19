"""Canonical verification lab capability, service and profile catalog."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tools.verification.models import Scenario


LOCAL_RESOURCE_TYPES = {"local", "virtual"}


@dataclass(frozen=True)
class LabExecutionPlan:
    scenario_ids: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    optional_capabilities: tuple[str, ...]
    selected_profile: str
    selected_services: tuple[str, ...]
    compose_fragments: tuple[str, ...]
    bootstrap_actions: tuple[str, ...]
    required_secrets: tuple[str, ...]
    required_hardware: tuple[str, ...]
    external_resources: tuple[str, ...]
    persistence: str
    readiness_gates: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    estimated_startup_seconds: int
    unresolved_requirements: tuple[str, ...] = ()
    qualified_capabilities: tuple[str, ...] = ()
    missing_capabilities: tuple[str, ...] = ()
    status: str = "PLANNED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LabCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.capabilities = _load_yaml(root / "verification/lab/capabilities.yaml").get("capabilities", {})
        self.services = {
            str(data["service_id"]): data
            for data in (_load_yaml(path) for path in sorted((root / "verification/lab/services").glob("*.yaml")))
        }
        self.profiles = {
            str(data["profile_id"]): data
            for data in (_load_yaml(path) for path in sorted((root / "verification/lab/profiles").glob("*.yaml")))
        }

    def capability_ids(self) -> set[str]:
        return set(self.capabilities)

    def service_ids(self) -> set[str]:
        return set(self.services)

    def profile_ids(self) -> set[str]:
        return set(self.profiles)

    def validate_catalog(self) -> list[str]:
        errors: list[str] = []
        for capability_id, capability in self.capabilities.items():
            for dependency in capability.get("dependencies") or []:
                if dependency not in self.capabilities:
                    errors.append(f"Capability {capability_id} depends on unknown capability {dependency}")
            for service in capability.get("provided_by") or []:
                if service in {"docker", "github", "external_network", "evidence_store", "external_spotify", "docker_network", "apple_device", "windows_vm", "raspberry_pi", "esp32", "voice_endpoint", "browser", "release_repo"}:
                    continue
                if service not in self.services:
                    errors.append(f"Capability {capability_id} references unknown provider {service}")
        for service_id, service in self.services.items():
            for capability in service.get("provided_capabilities") or []:
                if capability not in self.capabilities:
                    errors.append(f"Service {service_id} provides unknown capability {capability}")
            for capability in service.get("required_capabilities") or []:
                if capability not in self.capabilities:
                    errors.append(f"Service {service_id} requires unknown capability {capability}")
        for profile_id in self.profiles:
            provided = self.profile_capabilities(profile_id)
            profile = self.profiles[profile_id]
            for parent in profile.get("inherits") or []:
                if parent not in self.profiles:
                    errors.append(f"Profile {profile_id} inherits unknown profile {parent}")
            for service in self.profile_services(profile_id):
                if service not in self.services:
                    errors.append(f"Profile {profile_id} references unknown service {service}")
            for capability in provided:
                if capability not in self.capabilities:
                    errors.append(f"Profile {profile_id} provides unknown capability {capability}")
        errors.extend(self._dependency_cycles())
        return errors

    def validate_scenario(self, scenario: Scenario) -> list[str]:
        errors: list[str] = []
        requirements = scenario.raw.get("requires")
        if not isinstance(requirements, dict):
            return ["Scenario has no requires declaration"]
        capabilities = _as_tuple(requirements.get("capabilities"))
        if not capabilities:
            errors.append("Scenario requires.capabilities must not be empty")
        for capability in capabilities + _as_tuple(requirements.get("optional_capabilities")):
            if capability not in self.capabilities:
                errors.append(f"Scenario references unknown capability {capability}")
        for service in _as_tuple(requirements.get("services")):
            if service not in self.services:
                errors.append(f"Scenario references unknown service {service}")
        for secret in _as_tuple(requirements.get("secrets")):
            if not secret.endswith(".access_token") and "token" not in secret and "secret" not in secret and "credential" not in secret:
                errors.append(f"Scenario secret name is not explicit: {secret}")
        hardware = _as_tuple(requirements.get("hardware"))
        components = set(scenario.required_components)
        if scenario.category == "Hardware" and {"ESP32", "Pi", "Voice Endpoint"} & components and not hardware:
            errors.append("Hardware scenario must declare requires.hardware")
        resources = requirements.get("resources") or {}
        if resources and not isinstance(resources, dict):
            errors.append("Scenario requires.resources must be a mapping")
        plan = self.plan_for_scenarios([scenario])
        if not plan.selected_profile and not plan.external_resources and not plan.required_hardware:
            errors.append("No lab profile or external resource can satisfy scenario requirements")
        return errors

    def plan_for_scenarios(self, scenarios: list[Scenario]) -> LabExecutionPlan:
        scenario_ids = tuple(scenario.id for scenario in scenarios)
        required = set()
        optional = set()
        requested_services = set()
        required_secrets = set()
        required_hardware = set()
        external_resources = set()
        persistence_required = False
        for scenario in scenarios:
            requirements = scenario.raw.get("requires") or {}
            required.update(_as_tuple(requirements.get("capabilities")))
            optional.update(_as_tuple(requirements.get("optional_capabilities")))
            requested_services.update(_as_tuple(requirements.get("services")))
            required_secrets.update(_as_tuple(requirements.get("secrets")))
            required_hardware.update(_as_tuple(requirements.get("hardware")))
            resources = requirements.get("resources") or {}
            if resources.get("persistent_storage"):
                persistence_required = True
        expanded = self.resolve_dependencies(required)
        external_resources.update(
            capability
            for capability in expanded
            if self.capabilities.get(capability, {}).get("resource_type") not in LOCAL_RESOURCE_TYPES
        )
        lab_provided = set().union(*(set(self.profile_capabilities(profile_id)) for profile_id in self.profiles)) if self.profiles else set()
        external_resources.update(capability for capability in expanded if capability not in lab_provided)
        local_required = {
            capability
            for capability in expanded
            if capability in lab_provided and self.capabilities.get(capability, {}).get("resource_type") in LOCAL_RESOURCE_TYPES
        }
        selected_profile = self.select_profile(local_required)
        profile_services = set(self.profile_services(selected_profile)) if selected_profile else set()
        profile_capabilities = set(self.profile_capabilities(selected_profile)) if selected_profile else set()
        missing = tuple(sorted(local_required - profile_capabilities))
        services = tuple(sorted(profile_services | requested_services))
        fragments = self.profile_compose_fragments(selected_profile) if selected_profile else ()
        bootstrap = self.profile_bootstrap_actions(selected_profile) if selected_profile else ()
        gates = tuple(sorted(local_required & profile_capabilities))
        evidence = tuple(sorted({item for capability in expanded for item in self.capabilities.get(capability, {}).get("evidence") or []}))
        unresolved = tuple(sorted(missing))
        status = "BLOCKED" if unresolved else "PLANNED"
        return LabExecutionPlan(
            scenario_ids=scenario_ids,
            required_capabilities=tuple(sorted(expanded)),
            optional_capabilities=tuple(sorted(optional)),
            selected_profile=selected_profile,
            selected_services=services,
            compose_fragments=fragments,
            bootstrap_actions=bootstrap,
            required_secrets=tuple(sorted(required_secrets)),
            required_hardware=tuple(sorted(required_hardware)),
            external_resources=tuple(sorted(external_resources)),
            persistence="persistent" if persistence_required else (self.profiles.get(selected_profile, {}).get("persistence") or "ephemeral"),
            readiness_gates=gates,
            evidence_requirements=evidence,
            estimated_startup_seconds=int((self.profiles.get(selected_profile, {}).get("cost") or {}).get("startup_seconds") or 0),
            unresolved_requirements=unresolved,
            missing_capabilities=missing,
            status=status,
        )

    def resolve_dependencies(self, capabilities: set[str]) -> set[str]:
        resolved: set[str] = set()
        visiting: set[str] = set()

        def visit(capability: str) -> None:
            if capability in resolved:
                return
            if capability in visiting:
                raise ValueError(f"Cyclic capability dependency at {capability}")
            visiting.add(capability)
            for dependency in self.capabilities.get(capability, {}).get("dependencies") or []:
                visit(str(dependency))
            visiting.remove(capability)
            resolved.add(capability)

        for capability in sorted(capabilities):
            visit(capability)
        return resolved

    def select_profile(self, capabilities: set[str]) -> str:
        candidates: list[tuple[int, int, str]] = []
        for profile_id, profile in self.profiles.items():
            provided = set(self.profile_capabilities(profile_id))
            if capabilities <= provided:
                service_count = len(self.profile_services(profile_id))
                startup = int((profile.get("cost") or {}).get("startup_seconds") or 9999)
                candidates.append((service_count, startup, profile_id))
        return sorted(candidates)[0][2] if candidates else ""

    def profile_capabilities(self, profile_id: str) -> tuple[str, ...]:
        return tuple(sorted(self._collect_profile_values(profile_id, "provided_capabilities")))

    def profile_services(self, profile_id: str) -> tuple[str, ...]:
        return tuple(sorted(self._collect_profile_values(profile_id, "services")))

    def profile_compose_fragments(self, profile_id: str) -> tuple[str, ...]:
        return tuple(self._collect_profile_values(profile_id, "compose_fragments", preserve_order=True))

    def profile_bootstrap_actions(self, profile_id: str) -> tuple[str, ...]:
        return tuple(self._collect_profile_values(profile_id, "bootstrap_actions", preserve_order=True))

    def _collect_profile_values(self, profile_id: str, key: str, *, preserve_order: bool = False) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        def collect(current: str) -> None:
            profile = self.profiles.get(current) or {}
            for parent in profile.get("inherits") or []:
                collect(str(parent))
            for item in profile.get(key) or []:
                value = str(item)
                if value not in seen:
                    seen.add(value)
                    result.append(value)

        if profile_id:
            collect(profile_id)
        return result if preserve_order else sorted(result)

    def _dependency_cycles(self) -> list[str]:
        try:
            self.resolve_dependencies(set(self.capabilities))
            return []
        except ValueError as exc:
            return [str(exc)]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _as_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if value:
        return (str(value),)
    return ()
