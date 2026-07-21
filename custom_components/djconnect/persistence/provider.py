"""Storage-provider contract owned by the persistence platform."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar


ResultT = TypeVar("ResultT")


class ProviderTransaction(Protocol):
    """Private transaction primitive for platform migrations and repositories."""

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> None:
        """Execute one provider statement inside the active transaction."""


class PersistenceProvider(Protocol):
    """Provider-neutral durable storage lifecycle contract."""

    async def async_open(self, database_path: str) -> None:
        """Open the provider at the configured durable storage location."""

    async def async_close(self) -> None:
        """Release provider resources."""

    async def async_integrity_check(self) -> None:
        """Raise when durable storage is not internally consistent."""

    async def async_read_schema_version(self) -> int:
        """Return the installed schema version, or zero for a new database."""

    async def async_run_transaction(
        self,
        operation: Callable[[ProviderTransaction], ResultT],
    ) -> ResultT:
        """Run one short platform-owned transaction."""
