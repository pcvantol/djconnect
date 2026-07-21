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
        self._database_path = ""
        self._write_lock = asyncio.Lock()

    async def async_open(self, database_path: str) -> None:
        """Open a private DJConnect database with the required connection policy."""
        async with self._write_lock:
            if self._connection is not None:
                return
            try:
                self._connection = await asyncio.to_thread(self._open, database_path)
                self._database_path = database_path
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
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    @staticmethod
    def _open_read(database_path: str) -> sqlite3.Connection:
        """Open an independent read connection without mutating provider settings."""
        connection = sqlite3.connect(database_path, check_same_thread=False, isolation_level=None)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    async def async_close(self) -> None:
        """Close the provider connection when the last integration entry unloads."""
        async with self._write_lock:
            connection = self._connection
            self._connection = None
            self._database_path = ""
            if connection is not None:
                await asyncio.to_thread(connection.close)

    async def async_integrity_check(self) -> None:
        """Validate SQLite structural integrity without exposing provider details."""
        try:
            result = await asyncio.to_thread(self._with_read_connection, self._integrity_result)
        except sqlite3.Error as exc:
            raise PersistenceIntegrityError("DJConnect persistence integrity validation failed") from exc
        if result.lower() != "ok":
            raise PersistenceIntegrityError("DJConnect persistence integrity validation failed")

    def _integrity_result(self, connection: sqlite3.Connection) -> str:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row else "invalid"

    async def async_read_schema_version(self) -> int:
        """Read platform schema metadata, treating a new database as version zero."""
        try:
            return await asyncio.to_thread(self._with_read_connection, self._read_schema_version)
        except sqlite3.Error as exc:
            raise PersistenceError("DJConnect persistence schema metadata is unreadable") from exc

    def _read_schema_version(self, connection: sqlite3.Connection) -> int:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            ("djconnect_schema_metadata",),
        ).fetchone()
        if table is None:
            migration_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                ("djconnect_schema_migrations",),
            ).fetchone()
            if migration_table is not None:
                raise PersistenceError("DJConnect persistence schema metadata is missing")
            return 0
        row = connection.execute(
            "SELECT schema_version FROM djconnect_schema_metadata WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise PersistenceError("DJConnect persistence schema metadata is incomplete")
        return int(row[0])

    async def async_read_migration_history(self) -> list[tuple[int, str, str, bool]]:
        """Return migration rows without exposing database objects to callers."""
        try:
            return await asyncio.to_thread(self._with_read_connection, self._read_migration_history)
        except sqlite3.Error as exc:
            raise PersistenceError("DJConnect persistence migration history is unreadable") from exc

    @staticmethod
    def _read_migration_history(connection: sqlite3.Connection) -> list[tuple[int, str, str, bool]]:
        rows = connection.execute(
            "SELECT schema_version, migration_id, checksum, success "
            "FROM djconnect_schema_migrations ORDER BY schema_version"
        ).fetchall()
        return [(int(row[0]), str(row[1]), str(row[2]), bool(row[3])) for row in rows]

    async def async_validate_schema(self, required_tables: dict[str, set[str]]) -> None:
        """Perform bounded startup checks for schema shape and SQLite invariants."""
        try:
            await asyncio.to_thread(self._with_read_connection, self._validate_schema, required_tables)
        except sqlite3.Error as exc:
            raise PersistenceError("DJConnect persistence schema validation failed") from exc

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection, required_tables: dict[str, set[str]]) -> None:
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
        if not foreign_keys or int(foreign_keys[0]) != 1:
            raise PersistenceError("DJConnect persistence foreign-key enforcement is unavailable")
        for table, required_columns in required_tables.items():
            columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
            if not required_columns.issubset(columns):
                raise PersistenceError("DJConnect persistence schema is incomplete")

    def _with_read_connection(self, operation: Callable[..., ResultT], *args: object) -> ResultT:
        if not self._database_path:
            raise PersistenceError("DJConnect persistence is not initialized")
        connection = self._open_read(self._database_path)
        try:
            return operation(connection, *args)
        finally:
            connection.close()

    async def async_run_transaction(
        self,
        operation: Callable[[_SQLiteTransaction], ResultT],
    ) -> ResultT:
        """Run one short, serialized provider transaction."""
        async with self._write_lock:
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
