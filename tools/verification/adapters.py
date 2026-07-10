"""Adapter interfaces for future platform execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import ArtifactMetadata, EnvironmentSnapshot, PrimitiveAction, PrimitiveResult


class VerificationAdapter(ABC):
    """Abstract platform adapter contract.

    The core owns orchestration only. Implementations may target any platform,
    but platform-specific code must stay behind this interface.
    """

    name: str

    @abstractmethod
    def initialize(self) -> None:
        """Initialize adapter resources."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release adapter resources."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return sanitized health metadata."""

    @abstractmethod
    def prepare_environment(self) -> None:
        """Prepare platform-specific environment state."""

    @abstractmethod
    def launch(self, target: str | None = None) -> PrimitiveResult:
        """Launch the platform or application under test."""

    @abstractmethod
    def stop(self) -> PrimitiveResult:
        """Stop the platform or application under test."""

    @abstractmethod
    def restart(self) -> PrimitiveResult:
        """Restart the platform or application under test."""

    @abstractmethod
    def click(self, target: str, **kwargs: Any) -> PrimitiveResult:
        """Perform a primitive click/tap action."""

    @abstractmethod
    def type(self, text: str, **kwargs: Any) -> PrimitiveResult:
        """Perform primitive text input."""

    @abstractmethod
    def execute_service(self, name: str, payload: dict[str, Any] | None = None) -> PrimitiveResult:
        """Execute a platform service call."""

    @abstractmethod
    def execute_rest(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> PrimitiveResult:
        """Execute a REST request."""

    @abstractmethod
    def execute_websocket(self, message: dict[str, Any]) -> PrimitiveResult:
        """Execute a websocket request."""

    @abstractmethod
    def execute_action(self, action: PrimitiveAction) -> PrimitiveResult:
        """Execute one core-interpreted primitive action."""

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up adapter-owned temporary state."""

    @abstractmethod
    def collect_logs(self) -> tuple:
        """Collect sanitized logs."""

    @abstractmethod
    def collect_artifacts(self) -> tuple:
        """Collect adapter artifacts."""

    @abstractmethod
    def capture_screenshot(self, name: str | None = None) -> PrimitiveResult:
        """Capture a screenshot when the platform supports it."""

    @abstractmethod
    def capture_serial(self) -> tuple:
        """Capture serial output when the platform supports it."""

    @abstractmethod
    def collect_environment(self) -> EnvironmentSnapshot | dict[str, Any]:
        """Collect adapter-scoped environment metadata."""

    @abstractmethod
    def collect_artifact_metadata(self) -> tuple[ArtifactMetadata, ...]:
        """Return raw artifact metadata for core qualification."""

    @abstractmethod
    def reset(self) -> None:
        """Reset adapter runtime state between scenarios."""


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, VerificationAdapter] = {}

    def register(self, adapter: VerificationAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> VerificationAdapter | None:
        return self._adapters.get(name)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def available(self) -> tuple[str, ...]:
        return self.names()


AdapterManager = AdapterRegistry
