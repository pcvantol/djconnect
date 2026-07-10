"""Core data models for the DJConnect Verification Harness."""

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
            required_components=tuple(data.get("required_components") or ()),
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
    overrides: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceItem:
    kind: str
    path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    state: ResultState
    message: str
    evidence: tuple[EvidenceItem, ...] = ()


@dataclass(frozen=True)
class RunResult:
    run_id: str
    state: ResultState
    scenario_results: tuple[ScenarioResult, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
