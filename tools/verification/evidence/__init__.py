"""Evidence and artifact management for verification runs."""

from __future__ import annotations

from pathlib import Path

from .index import EvidenceCollector, checksum, redact
from .run_store import RunStore, RunStoreError
from tools.verification.artifacts import ArtifactManager
from tools.verification.models import EvidenceItem, EvidenceKind


class EvidenceManager:
    def checksum(self, path: Path) -> EvidenceItem:
        return EvidenceItem(EvidenceKind.CHECKSUM.value, path=path, metadata={"sha256": checksum(path)})


class LogManager:
    def redact(self, value: str) -> str:
        return redact(value)


class ScreenshotManager:
    pass


class SerialManager:
    pass


class PerformanceCollector:
    pass


__all__ = [
    "ArtifactManager",
    "EvidenceCollector",
    "EvidenceManager",
    "LogManager",
    "PerformanceCollector",
    "RunStore",
    "RunStoreError",
    "ScreenshotManager",
    "SerialManager",
    "checksum",
    "redact",
]
