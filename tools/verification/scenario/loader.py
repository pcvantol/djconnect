"""Scenario catalog loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.verification.models import HarnessConfig, Scenario


class ScenarioLoader:
    def __init__(self, config: HarnessConfig) -> None:
        self.config = config

    def load(self) -> list[Scenario]:
        scenarios: list[Scenario] = []
        for path in self.config.scenario_paths:
            for scenario_file in scenario_files(path):
                scenarios.append(Scenario.from_mapping(read_mapping(scenario_file), scenario_file))
        return sorted(scenarios, key=lambda scenario: scenario.id)


def scenario_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.suffix.lower() in {".json", ".yaml", ".yml"}
    )


def read_mapping(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PyYAML is required to load YAML scenarios") from exc
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Scenario file must contain a mapping: {path}")
    return value
