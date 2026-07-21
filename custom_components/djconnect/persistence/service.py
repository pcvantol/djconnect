"""Provider-neutral persistence service and repository infrastructure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar
import uuid

from .provider import PersistenceProvider, ProviderTransaction
from .schema import CURRENT_SCHEMA_VERSION, MIGRATIONS, REQUIRED_TABLES, apply_migration


ResultT = TypeVar("ResultT")


class PersistenceError(RuntimeError):
    """Base failure for the DJConnect persistence platform."""


class PersistenceSchemaError(PersistenceError):
    """Raised for unsupported or invalid durable schema state."""


class PersistenceIntegrityError(PersistenceError):
    """Raised when provider integrity validation fails."""


@dataclass(frozen=True)
class PersistenceReadiness:
    """Safe readiness projection; it deliberately exposes no provider handle."""

    ready: bool
    schema_version: int = 0
    last_migration_id: str = ""


class PersistenceTransaction:
    """Repository-facing transaction boundary without a raw provider connection."""

    def __init__(self, transaction: ProviderTransaction) -> None:
        self._transaction = transaction
        self.transaction_id = str(uuid.uuid4())

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> None:
        """Run one repository-owned statement inside the platform transaction."""
        self._transaction.execute(statement, parameters)


class PersistenceRepository:
    """Base infrastructure for future domain repositories.

    Domain repositories inherit this boundary instead of opening connections,
    locating files or creating transactions themselves.
    """

    def __init__(self, persistence: "PersistenceService") -> None:
        self._persistence = persistence

    async def _async_in_transaction(
        self,
        operation: Callable[[PersistenceTransaction], ResultT],
    ) -> ResultT:
        return await self._persistence.async_in_transaction(operation)


class PersistenceService:
    """Own one durable storage provider, schema lifecycle and readiness state."""

    def __init__(self, database_path: str | Path, provider: PersistenceProvider) -> None:
        self._database_path = str(database_path)
        self._provider = provider
        self._readiness = PersistenceReadiness(ready=False)

    @property
    def readiness(self) -> PersistenceReadiness:
        """Return whether startup validation completed successfully."""
        return self._readiness

    async def async_initialize(self) -> PersistenceReadiness:
        """Open, validate and migrate the canonical DJConnect database once."""
        if self._readiness.ready:
            return self._readiness
        await self._provider.async_open(self._database_path)
        try:
            await self._provider.async_integrity_check()
            installed_version = await self._provider.async_read_schema_version()
            if installed_version > CURRENT_SCHEMA_VERSION:
                raise PersistenceSchemaError("DJConnect persistence schema is newer than this integration")
            for version in range(installed_version + 1, CURRENT_SCHEMA_VERSION + 1):
                await self._provider.async_run_transaction(
                    lambda transaction, version=version: apply_migration(transaction, version)
                )
            await self._provider.async_integrity_check()
            resolved_version = await self._provider.async_read_schema_version()
            if resolved_version != CURRENT_SCHEMA_VERSION:
                raise PersistenceSchemaError("DJConnect persistence schema migration did not complete")
            history = await self._provider.async_read_migration_history()
            expected = [(item.version, item.migration_id, item.checksum, True) for item in MIGRATIONS]
            if history != expected:
                raise PersistenceSchemaError("DJConnect persistence migration history is inconsistent")
            await self._provider.async_validate_schema(REQUIRED_TABLES)
        except Exception:
            await self._provider.async_close()
            raise
        self._readiness = PersistenceReadiness(
            ready=True, schema_version=resolved_version, last_migration_id=MIGRATIONS[-1].migration_id
        )
        return self._readiness

    async def async_close(self) -> None:
        """Release provider resources and remove readiness on integration shutdown."""
        await self._provider.async_close()
        self._readiness = PersistenceReadiness(ready=False)

    async def async_in_transaction(
        self,
        operation: Callable[[PersistenceTransaction], ResultT],
    ) -> ResultT:
        """Provide the sole transaction entry point for future repositories."""
        if not self._readiness.ready:
            raise PersistenceError("DJConnect persistence bootstrap has not completed")

        def run(transaction: ProviderTransaction) -> ResultT:
            return operation(PersistenceTransaction(transaction))

        return await self._provider.async_run_transaction(run)
