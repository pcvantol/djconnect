"""Digital Test Laboratory orchestration around platform adapters."""

from __future__ import annotations

from dataclasses import asdict

from tools.verification.configuration import SecretLoader
from tools.verification.environment.cleanup import CleanupManager
from tools.verification.environment.dependencies import DependencyInspector
from tools.verification.environment.github import GitHubInspector
from tools.verification.environment.docker_ha import HADockerDiscovery
from tools.verification.environment.identity import RunIdentityManager
from tools.verification.environment.platforms import (
    AppleDevelopmentEnvironment,
    ESP32Environment,
    HomeAssistantEnvironment,
    RaspberryPiEnvironment,
    WindowsDevelopmentEnvironment,
)
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

    def prepare(self, scenarios: list[Scenario] | None = None) -> dict:
        run_identity = self.identity.create(scenarios or [])
        snapshot = self.snapshotter.collect(self.config)
        gates = [
            self.github.validate_workflows(),
            self.github.commit_status(snapshot.git_sha),
            self.ha_docker.qualify(),
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
