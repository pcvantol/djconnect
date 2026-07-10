"""Adapter interfaces for future platform execution."""

from __future__ import annotations

from typing import Protocol

from .models import AdapterKind, Scenario, ScenarioResult


class VerificationAdapter(Protocol):
    kind: AdapterKind

    def prepare(self) -> None:
        """Prepare runtime-specific state before execution."""

    def execute(self, scenario: Scenario) -> ScenarioResult:
        """Execute a scenario without defining expected platform behavior."""

    def collect_evidence(self, scenario: Scenario) -> None:
        """Collect sanitized adapter evidence for the active scenario."""

    def cleanup(self, scenario: Scenario) -> None:
        """Clean up adapter-owned temporary state."""


class AdapterManager:
    def __init__(self) -> None:
        self._adapters: dict[AdapterKind, VerificationAdapter] = {}

    def register(self, adapter: VerificationAdapter) -> None:
        self._adapters[adapter.kind] = adapter

    def get(self, kind: AdapterKind) -> VerificationAdapter | None:
        return self._adapters.get(kind)

    def available(self) -> tuple[AdapterKind, ...]:
        return tuple(sorted(self._adapters, key=str))
