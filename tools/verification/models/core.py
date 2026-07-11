"""Platform-independent verification data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class ResultState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_TESTED = "NOT TESTED"
    SKIPPED = "SKIPPED"


class GateState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class AdapterKind(StrEnum):
    HOME_ASSISTANT = "home_assistant"
    APPLE = "apple"
    WINDOWS_CATALYST = "windows_catalyst"
    WINDOWS_NATIVE_ARM64 = "windows_native_arm64"
    RASPBERRY_PI = "raspberry_pi"
    ESP32 = "esp32"
    VOICE_ENDPOINT = "voice_endpoint"
    WEBSITE = "website"
    RELEASE = "release"
    SPOTIFY_DIRECT = "spotify_direct"
    MUSIC_ASSISTANT = "music_assistant"
    ANDROID_FUTURE = "android_future"
    CLOUD_FUTURE = "cloud_future"
    RUNTIME_FUTURE = "runtime_future"


class EvidenceKind(StrEnum):
    LOG = "log"
    SCREENSHOT = "screenshot"
    REQUEST = "request"
    RESPONSE = "response"
    SERIAL_LOG = "serial_log"
    ARTIFACT = "artifact"
    REPORT = "report"
    ENVIRONMENT = "environment"
    CHECKSUM = "checksum"


class CleanupMode(StrEnum):
    SOFT = "soft"
    DESTRUCTIVE = "destructive"


class ResourceState(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PrimitiveAction:
    name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = None


@dataclass(frozen=True)
class PrimitiveResult:
    action: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    evidence: tuple["EvidenceItem", ...] = ()
    message: str = ""


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    description: str
    category: str
    priority: str
    verification_level: str
    automation_level: str
    required_components: tuple[str, ...]
    raw: dict[str, Any]
    source: Path | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any], source: Path | None = None) -> "Scenario":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            category=str(data.get("category", "")),
            priority=str(data.get("priority", "")),
            verification_level=str(data.get("verification_level", "")),
            automation_level=str(data.get("automation_level", "")),
            required_components=tuple(str(item) for item in data.get("required_components") or ()),
            raw=dict(data),
            source=source,
        )


@dataclass(frozen=True)
class HarnessConfig:
    root: Path
    scenario_paths: tuple[Path, ...]
    evidence_dir: Path
    report_dir: Path
    environment_file: Path | None = None
    secrets_file: Path | None = None
    ci: bool = False
    dry_run: bool = False
    test_mode: str = "stable"
    parallel_execution: bool = False
    parallel_workers: int = 1
    overrides: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SecretBundle:
    names: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    message: str
    source: Path | None = None


@dataclass(frozen=True)
class GateResult:
    name: str
    state: GateState
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.state in {GateState.PASS, GateState.WARNING, GateState.SKIPPED}


@dataclass(frozen=True)
class EvidenceItem:
    kind: str
    path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceIndex:
    run_id: str
    items: tuple[EvidenceItem, ...]


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    state: ResultState
    message: str
    evidence: tuple[EvidenceItem, ...] = ()
    duration_seconds: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioExecutionPlan:
    scenario_id: str
    actions: tuple[PrimitiveAction, ...]
    assertions: dict[str, Any] = field(default_factory=dict)
    expected_results: dict[str, Any] = field(default_factory=dict)
    evidence_requirements: tuple[dict[str, Any], ...] = ()
    cleanup_policy: tuple[Any, ...] = ()
    retry_policy: dict[str, Any] = field(default_factory=dict)
    timeouts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlannedCase:
    case_id: str
    scenario_id: str
    scenario_category: str
    mode: str
    policy: str
    matrix_profile: str
    data_profile: str
    platform: str
    adapter: str
    batch_id: str
    priority: str
    estimated_seconds: int
    depends_on: tuple[str, ...] = ()
    retry_policy: dict[str, Any] = field(default_factory=dict)
    traceability: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanBatch:
    batch_id: str
    case_ids: tuple[str, ...]
    execution: str
    required_resources: tuple[str, ...] = ()
    estimated_seconds: int = 0


@dataclass(frozen=True)
class PlanGraph:
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ResourcePlan:
    required_hardware: tuple[str, ...] = ()
    required_builds: tuple[str, ...] = ()
    required_services: tuple[str, ...] = ()
    exclusive_resources: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnvironmentPlan:
    environments: tuple[str, ...]
    capabilities: tuple[str, ...]
    configuration: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CoverageReport:
    scenario_count: int
    case_count: int
    by_mode: dict[str, int] = field(default_factory=dict)
    by_platform: dict[str, int] = field(default_factory=dict)
    by_data_profile: dict[str, int] = field(default_factory=dict)
    by_matrix_profile: dict[str, int] = field(default_factory=dict)
    by_policy: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    strategy: str
    policy: str
    cases: tuple[PlannedCase, ...]
    batches: tuple[PlanBatch, ...]
    graph: PlanGraph
    resource_plan: ResourcePlan
    environment_plan: EnvironmentPlan
    coverage: CoverageReport
    estimated_seconds: int
    required_evidence: tuple[str, ...] = ()
    expected_reports: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    run_id: str
    state: ResultState
    scenario_results: tuple[ScenarioResult, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArtifactMetadata:
    path: Path
    name: str
    version: str | None = None
    build_type: str | None = None
    sha256: str | None = None
    signing: dict[str, Any] = field(default_factory=dict)
    entitlements: dict[str, Any] = field(default_factory=dict)
    configuration: dict[str, Any] = field(default_factory=dict)
    release_equivalent: bool = False
    instrumented: bool = False
    ci: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnvironmentSnapshot:
    timestamp: str
    host: str
    os: str
    architecture: str
    toolchain: dict[str, str]
    locale: str
    timezone: str
    git_sha: str | None
    git_branch: str | None
    dependency_versions: dict[str, str]
    configuration_fingerprint: str
    capabilities: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunIdentity:
    run_id: str
    environment_id: str
    correlation_id: str
    scenario_ids: tuple[str, ...] = ()
    artifact_prefix: str = ""


@dataclass(frozen=True)
class ToolchainInfo:
    name: str
    executable: str | None
    version: str | None
    state: ResourceState


@dataclass(frozen=True)
class DependencyInspection:
    ecosystem: str
    manifest: Path
    lockfile: Path | None = None
    package_count: int = 0
    security_advisories_checked: bool = False
    drift_checked: bool = False


@dataclass(frozen=True)
class GitHubWorkflowInfo:
    path: Path
    name: str
    triggers: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManagedPlatform:
    name: str
    state: ResourceState
    metadata: dict[str, Any] = field(default_factory=dict)
