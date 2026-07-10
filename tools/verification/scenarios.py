"""Scenario loading, validation and scheduling."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import HarnessConfig, Scenario

SCENARIO_ID_PATTERN = re.compile(r"^[A-Z]+-[0-9]{3}$")
REQUIRED_FIELDS = {
    "id",
    "title",
    "description",
    "purpose",
    "owner",
    "category",
    "priority",
    "risk",
    "verification_level",
    "automation_level",
    "required_components",
    "supported_platforms",
    "required_locales",
    "required_build_types",
    "preconditions",
    "setup",
    "steps",
    "assertions",
    "expected_results",
    "cleanup",
    "timeouts",
    "retry_policy",
    "artifacts",
    "privacy_classification",
    "destructive",
    "tags",
    "estimated_duration",
    "version",
    "schema_version",
}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    message: str
    source: Path | None = None


class ScenarioLoader:
    def __init__(self, config: HarnessConfig) -> None:
        self.config = config

    def load(self) -> list[Scenario]:
        scenarios: list[Scenario] = []
        for path in self.config.scenario_paths:
            for scenario_file in _scenario_files(path):
                scenarios.append(Scenario.from_mapping(_read_mapping(scenario_file), scenario_file))
        return sorted(scenarios, key=lambda scenario: scenario.id)


class ScenarioValidator:
    def validate(self, scenario: Scenario) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        missing = sorted(REQUIRED_FIELDS - set(scenario.raw))
        for field in missing:
            issues.append(ValidationIssue("error", f"Missing required field: {field}", scenario.source))
        if not SCENARIO_ID_PATTERN.match(scenario.id):
            issues.append(ValidationIssue("error", f"Invalid scenario id: {scenario.id}", scenario.source))
        if not scenario.required_components:
            issues.append(
                ValidationIssue("error", "Scenario must require at least one component", scenario.source)
            )
        return issues


class ScenarioScheduler:
    def select(
        self,
        scenarios: list[Scenario],
        *,
        ids: set[str] | None = None,
        tags: set[str] | None = None,
        components: set[str] | None = None,
    ) -> list[Scenario]:
        selected = scenarios
        if ids:
            selected = [scenario for scenario in selected if scenario.id in ids]
        if tags:
            selected = [
                scenario
                for scenario in selected
                if tags.intersection(set(scenario.raw.get("tags") or ()))
            ]
        if components:
            selected = [
                scenario
                for scenario in selected
                if components.intersection(set(scenario.required_components))
            ]
        return selected


def _scenario_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.suffix.lower() in {".json", ".yaml", ".yml"}
    )


def _read_mapping(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("PyYAML is required to load YAML scenarios") from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Scenario file must contain a mapping: {path}")
    return value
