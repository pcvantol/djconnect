"""Internal lifecycle management for immutable historical projections."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import monotonic
from .persistence.history import HistoricalProjectionRepository


@dataclass(frozen=True)
class HistoricalRetentionPolicy:
    retention_days: int = 90
    batch_size: int = 100
    version: int = 1


@dataclass(frozen=True)
class HistoricalCleanupStatistics:
    retained_sessions: int
    retained_moments: int
    eligible_sessions: int
    eligible_moments: int
    deleted_sessions: int
    deleted_moments: int
    orphan_moments: int
    duration_ms: int
    result: str


class HistoricalProjectionRetentionService:
    """System-only application service for deterministic history cleanup."""

    def __init__(
        self,
        repository: HistoricalProjectionRepository,
        policy: HistoricalRetentionPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or HistoricalRetentionPolicy()

    async def async_cleanup(self, *, now: datetime | None = None) -> HistoricalCleanupStatistics:
        started = monotonic()
        current = now or datetime.now(UTC)
        cutoff = (current - timedelta(days=self._policy.retention_days)).isoformat()
        (
            sessions,
            moments,
            orphans,
            eligible_sessions,
        ) = await self._repository.async_cleanup_expired(
            cutoff=cutoff, batch_size=self._policy.batch_size
        )
        return HistoricalCleanupStatistics(
            0,
            0,
            eligible_sessions,
            moments,
            sessions,
            moments,
            orphans,
            int((monotonic() - started) * 1000),
            "ok",
        )
