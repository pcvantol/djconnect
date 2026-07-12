"""Digital Test Laboratory orchestration around platform adapters."""

from __future__ import annotations

import os
from dataclasses import asdict, replace

from tools.verification.configuration import SecretLoader
from tools.verification.environment.cleanup import CleanupManager
from tools.verification.environment.dependencies import DependencyInspector
from tools.verification.environment.github import GitHubInspector
from tools.verification.environment.docker_ha import HADockerDiscovery, HALabConfig, HALocalVerificationLab
from tools.verification.environment.host_preflight import HostPreflight, HostPreflightConfig
from tools.verification.environment.identity import RunIdentityManager
from tools.verification.environment.platforms import (
    AppleDevelopmentEnvironment,
    ESP32Environment,
    HomeAssistantEnvironment,
    RaspberryPiEnvironment,
    WindowsDotnetMaintenance,
    WindowsDevelopmentEnvironment,
)
from tools.verification.environment.runtime_image import RuntimeImagePuller
from tools.verification.lab import LabCatalog
from tools.verification.environment.snapshot import EnvironmentSnapshotter
from tools.verification.environment.toolchain import ToolchainInspector
from tools.verification.models import GateResult, GateState, HarnessConfig, Scenario


class VerificationExecutionEnvironment:
    """Prepare, inspect and restore the world around scenario execution."""

    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.identity = RunIdentityManager()
        self.snapshotter = EnvironmentSnapshotter()
        self.toolchains = ToolchainInspector()
        self.dependencies = DependencyInspector()
        self.github = GitHubInspector(config.root)
        self.cleanup = CleanupManager(config.root)
        self.secrets = SecretLoader()
        self.ha_docker = HADockerDiscovery(config.root)
        self.runtime_image = RuntimeImagePuller()

    def prepare(self, scenarios: list[Scenario] | None = None) -> dict:
        selected_scenarios = scenarios or []
        run_identity = self.identity.create(selected_scenarios)
        snapshot = self.snapshotter.collect(self.config)
        ha_lab_config = _ha_lab_config_for_scenarios(self.config.root, selected_scenarios)
        requires_ha = _requires_home_assistant(selected_scenarios)
        requires_docker_runtime = _requires_docker_runtime(selected_scenarios)
        requires_windows_runtime = _requires_windows_runtime(selected_scenarios)
        ha_lab_refresh_gate = (
            HALocalVerificationLab(self.config.root, config=ha_lab_config).refresh_for_run()
            if requires_ha and _ha_lab_refresh_enabled(self.config)
            else _skipped_gate(
                "ha_lab_refresh",
                (
                    "Home Assistant lab refresh skipped; selected scenarios do not require the HA lab."
                    if not requires_ha
                    else "Home Assistant lab refresh skipped; enable with prepare --refresh-ha-lab or DJCONNECT_VERIFICATION_HA_REFRESH=1."
                ),
            )
        )
        ha_docker_gate = (
            self.ha_docker.qualify(expected_port=ha_lab_config.port, expected_name=ha_lab_config.name)
            if requires_ha
            else _skipped_gate(
                "ha_docker_discovery",
                "Home Assistant Docker discovery skipped; selected scenarios do not require the HA lab.",
            )
        )
        host_preflight_gate = (
            _skipped_gate(
                "host_preflight",
                "Existing Home Assistant lab runtime is already qualified; startup preflight skipped.",
                {"qualified_runtime": ha_docker_gate.metadata.get("runtime", {})},
            )
            if requires_ha and ha_docker_gate.state == GateState.PASS
            else (
                HostPreflight(
                    self.config.root,
                    HostPreflightConfig(ports=(ha_lab_config.port,), lab_root=ha_lab_config.lab_root),
                ).check()
                if requires_ha
                else _skipped_gate(
                    "host_preflight",
                    "Home Assistant lab host preflight skipped; selected scenarios do not require the HA lab.",
                )
            )
        )
        gates = [
            self.runtime_image.pull() if requires_docker_runtime else _skipped_gate(
                "verification_runtime_image_pull",
                "Docker runtime image pull skipped; selected scenarios do not require Docker runtime.",
            ),
            ha_lab_refresh_gate,
            host_preflight_gate,
            self.github.validate_workflows(),
            self.github.commit_status(snapshot.git_sha),
            ha_docker_gate,
            (
                WindowsDotnetMaintenance().ensure_current(root=self.config.root)
                if requires_windows_runtime
                else _skipped_gate(
                    "windows_dotnet_maintenance",
                    "Windows .NET maintenance skipped; selected scenarios do not require Windows runtime.",
                )
            ),
            *self.dependencies.validate(self.config.root),
            self.cleanup.clean(dry_run=True),
            self._secret_gate(),
        ]
        return {
            "run_identity": asdict(run_identity),
            "snapshot": asdict(snapshot),
            "toolchains": {name: asdict(info) for name, info in self.toolchains.discover().items()},
            "dependencies": [asdict(item) for item in self.dependencies.inspect(self.config.root)],
            "github": {"workflows": [asdict(item) for item in self.github.workflows()]},
            "platforms": {item.name: asdict(item) for item in self.discover_platforms()},
            "gates": [asdict(gate) for gate in gates],
        }

    def discover_platforms(self) -> tuple:
        return (
            HomeAssistantEnvironment().discover(),
            AppleDevelopmentEnvironment().discover(),
            WindowsDevelopmentEnvironment().discover(),
            RaspberryPiEnvironment().discover(),
            ESP32Environment().discover(),
        )

    def restore(self, *, dry_run: bool = True, allow_destructive: bool = False) -> GateResult:
        return self.cleanup.clean(dry_run=dry_run, allow_destructive=allow_destructive)

    def _secret_gate(self) -> GateResult:
        bundle = self.secrets.load(self.config.secrets_file)
        return GateResult(
            "secrets_loading",
            GateState.PASS,
            f"{len(bundle.names)} secret names loaded without values",
            {"source": bundle.source, "names": list(bundle.names)},
        )


def _requires_home_assistant(scenarios: list[Scenario]) -> bool:
    for scenario in scenarios:
        platforms = {str(item) for item in scenario.raw.get("supported_platforms") or ()}
        components = set(scenario.required_components)
        capabilities = _required_capabilities(scenario)
        if "Home Assistant" in platforms or "HA" in components:
            return True
        if any(capability.startswith(("ha.", "djconnect.", "assist.", "stt.", "tts.")) for capability in capabilities):
            return True
    return False


def _requires_docker_runtime(scenarios: list[Scenario]) -> bool:
    return any("docker.runtime" in _required_capabilities(scenario) for scenario in scenarios)


def _requires_windows_runtime(scenarios: list[Scenario]) -> bool:
    for scenario in scenarios:
        platforms = {str(item) for item in scenario.raw.get("supported_platforms") or ()}
        components = set(scenario.required_components)
        capabilities = _required_capabilities(scenario)
        if any(platform in {"Windows", "Windows ARM64", "Windows Native ARM64"} for platform in platforms):
            return True
        if "Windows Native ARM64" in components:
            return True
        if any(capability.startswith(("windows.", "windows_native_arm64.")) for capability in capabilities):
            return True
    return False


def _required_capabilities(scenario: Scenario) -> set[str]:
    requires = scenario.raw.get("requires") or {}
    if not isinstance(requires, dict):
        return set()
    return {str(item) for item in requires.get("capabilities") or ()}


def _skipped_gate(name: str, message: str, metadata: dict | None = None) -> GateResult:
    return GateResult(name, GateState.SKIPPED, message, metadata or {})


def _ha_lab_refresh_enabled(config: HarnessConfig) -> bool:
    value = config.overrides.get("ha_lab_refresh")
    if value is None:
        value = os.getenv("DJCONNECT_VERIFICATION_HA_REFRESH")
    return str(value).lower() in {"1", "true", "yes", "on"}


def _ha_lab_config_for_scenarios(root, scenarios: list[Scenario]) -> HALabConfig:
    config = HALabConfig.from_root(root)
    if os.getenv("DJCONNECT_VERIFICATION_LAB_PROFILE"):
        return config
    if not scenarios:
        return config
    selected_profile = LabCatalog(root).plan_for_scenarios(scenarios).selected_profile
    if not selected_profile or selected_profile == config.profile:
        return config
    catalog = LabCatalog(root)
    compose_files = tuple(root / fragment for fragment in catalog.profile_compose_fragments(selected_profile))
    if not compose_files:
        return config
    return replace(
        config,
        profile=selected_profile,
        compose_file=compose_files[0],
        compose_files=compose_files,
    )
