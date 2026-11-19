"""Scenario loading, validation and scheduling."""

from .loader import ScenarioLoader
from .engine import ScenarioEngine
from .scheduler import ScenarioScheduler


def __getattr__(name: str):
    if name in {"REQUIRED_FIELDS", "SCENARIO_ID_PATTERN", "ScenarioValidator"}:
        from . import validator

        return getattr(validator, name)
    raise AttributeError(name)

__all__ = [
    "REQUIRED_FIELDS",
    "SCENARIO_ID_PATTERN",
    "ScenarioLoader",
    "ScenarioEngine",
    "ScenarioScheduler",
    "ScenarioValidator",
]
