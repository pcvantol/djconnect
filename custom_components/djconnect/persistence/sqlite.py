"""SQLite implementation hidden behind the DJConnect persistence provider."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
import sqlite3
from typing import TypeVar

from .service import PersistenceError, PersistenceIntegrityError


ResultT = TypeVar("ResultT")


class _SQLiteTransaction:
    """SQLite transaction implementation; never exposed outside persistence."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> None:
        self._connection.execute(statement, parameters)


class SQLitePersistenceProvider:
    """First local provider for the platform-owned persistence boundary."""

    def __init__(self) -> None:
        self._connection: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def async_open(self, database_path: str) -> None:
        """Open a private DJConnect database with the required connection policy."""
        async with self._lock:
            if self._connection is not None:
                return
            try:
                self._connection = await asyncio.to_thread(self._open, database_path)
            except sqlite3.Error as exc:
                raise PersistenceError("Unable to open DJConnect persistence") from exc

    @staticmethod
    def _open(database_path: str) -> sqlite3.Connection:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    async def async_close(self) -> None:
        """Close the provider connection when the last integration entry unloads."""
        async with self._lock:
            connection = self._connection
            self._connection = None
            if connection is not None:
                await asyncio.to_thread(connection.close)

    async def async_integrity_check(self) -> None:
        """Validate SQLite structural integrity without exposing provider details."""
        async with self._lock:
            result = await asyncio.to_thread(self._integrity_result)
        if result.lower() != "ok":
            raise PersistenceIntegrityError("DJConnect persistence integrity validation failed")

    def _integrity_result(self) -> str:
        connection = self._require_connection()
        row = connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row else "invalid"

    async def async_read_schema_version(self) -> int:
        """Read platform schema metadata, treating a new database as version zero."""
        async with self._lock:
            return await asyncio.to_thread(self._read_schema_version)

    def _read_schema_version(self) -> int:
        connection = self._require_connection()
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            ("djconnect_schema_metadata",),
        ).fetchone()
        if table is None:
            return 0
        row = connection.execute(
            "SELECT schema_version FROM djconnect_schema_metadata WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise PersistenceError("DJConnect persistence schema metadata is incomplete")
        return int(row[0])

    async def async_run_transaction(
        self,
        operation: Callable[[_SQLiteTransaction], ResultT],
    ) -> ResultT:
        """Run one short, serialized provider transaction."""
        async with self._lock:
            try:
                return await asyncio.to_thread(self._run_transaction, operation)
            except sqlite3.Error as exc:
                raise PersistenceError("DJConnect persistence transaction failed") from exc

    def _run_transaction(self, operation: Callable[[_SQLiteTransaction], ResultT]) -> ResultT:
        connection = self._require_connection()
        connection.execute("BEGIN IMMEDIATE")
        try:
            result = operation(_SQLiteTransaction(connection))
        except Exception:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")
        return result

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise PersistenceError("DJConnect persistence is not initialized")
        return self._connection
