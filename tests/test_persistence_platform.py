"""Focused tests for the DJConnect persistence foundation."""

from __future__ import annotations

import asyncio
from dataclasses import fields
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest


package = types.ModuleType("custom_components.djconnect")
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")
]
sys.modules.setdefault("custom_components.djconnect", package)

from custom_components.djconnect.persistence.service import (  # noqa: E402
    PersistenceError,
    PersistenceReadiness,
    PersistenceSchemaError,
    PersistenceService,
)
from custom_components.djconnect.persistence.bootstrap import (  # noqa: E402
    PERSISTENCE_SERVICE_KEY,
    async_initialize_persistence,
    async_shutdown_persistence,
)
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.schema import CURRENT_SCHEMA_VERSION, MIGRATIONS  # noqa: E402


class PersistenceFoundationTest(unittest.TestCase):
    """Validate provider lifecycle, migration, integrity and transaction boundaries."""

    def _service(self, directory: str) -> PersistenceService:
        return PersistenceService(Path(directory) / "djconnect.sqlite3", SQLitePersistenceProvider())

    def test_new_database_initializes_schema_and_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            readiness = asyncio.run(service.async_initialize())

            self.assertTrue(readiness.ready)
            self.assertEqual(readiness.schema_version, CURRENT_SCHEMA_VERSION)
            self.assertEqual(readiness.last_migration_id, MIGRATIONS[-1].migration_id)
            self.assertTrue((Path(directory) / "djconnect.sqlite3").exists())
            asyncio.run(service.async_close())
            self.assertFalse(service.readiness.ready)

    def test_empty_existing_database_follows_migration_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "djconnect.sqlite3"
            sqlite3.connect(path).close()
            service = self._service(directory)

            readiness = asyncio.run(service.async_initialize())

            self.assertEqual(readiness.schema_version, CURRENT_SCHEMA_VERSION)
            connection = sqlite3.connect(path)
            try:
                applied = connection.execute(
                    "SELECT schema_version FROM djconnect_schema_migrations"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(applied, [(migration.version,) for migration in MIGRATIONS])
            asyncio.run(service.async_close())

    def test_latest_schema_restarts_after_a_clean_shutdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = self._service(directory)
            asyncio.run(first.async_initialize())
            asyncio.run(first.async_close())

            restarted = self._service(directory)
            readiness = asyncio.run(restarted.async_initialize())

            self.assertTrue(readiness.ready)
            self.assertEqual(readiness.schema_version, CURRENT_SCHEMA_VERSION)
            asyncio.run(restarted.async_close())

    def test_missing_schema_metadata_with_migration_history_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "djconnect.sqlite3"
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "CREATE TABLE djconnect_schema_migrations "
                    "(schema_version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
                )
                connection.commit()
            finally:
                connection.close()

            service = self._service(directory)
            with self.assertRaises(PersistenceError):
                asyncio.run(service.async_initialize())
            self.assertFalse(service.readiness.ready)

    def test_future_schema_is_rejected_without_becoming_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "djconnect.sqlite3"
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "CREATE TABLE djconnect_schema_metadata "
                    "(singleton INTEGER PRIMARY KEY, schema_version INTEGER, updated_at TEXT)"
                )
                connection.execute(
                    "INSERT INTO djconnect_schema_metadata VALUES (1, 99, 'future')"
                )
                connection.commit()
            finally:
                connection.close()
            service = self._service(directory)

            with self.assertRaises(PersistenceSchemaError):
                asyncio.run(service.async_initialize())

            self.assertFalse(service.readiness.ready)

    def test_released_v1_database_upgrades_through_the_canonical_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "djconnect.sqlite3"
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "CREATE TABLE djconnect_schema_metadata "
                    "(singleton INTEGER PRIMARY KEY, schema_version INTEGER, updated_at TEXT)"
                )
                connection.execute(
                    "CREATE TABLE djconnect_schema_migrations "
                    "(schema_version INTEGER PRIMARY KEY, applied_at TEXT)"
                )
                connection.execute("INSERT INTO djconnect_schema_metadata VALUES (1, 1, 'old')")
                connection.execute("INSERT INTO djconnect_schema_migrations VALUES (1, 'old')")
                connection.commit()
            finally:
                connection.close()

            readiness = asyncio.run(self._service(directory).async_initialize())

            self.assertEqual(readiness.schema_version, CURRENT_SCHEMA_VERSION)
            self.assertEqual(readiness.last_migration_id, MIGRATIONS[-1].migration_id)

    def test_inconsistent_migration_history_fails_without_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            asyncio.run(service.async_initialize())
            asyncio.run(service.async_close())
            path = Path(directory) / "djconnect.sqlite3"
            connection = sqlite3.connect(path)
            try:
                connection.execute(
                    "UPDATE djconnect_schema_migrations SET checksum='wrong' WHERE schema_version=2"
                )
                connection.commit()
            finally:
                connection.close()

            restarted = self._service(directory)
            with self.assertRaises(PersistenceSchemaError):
                asyncio.run(restarted.async_initialize())
            self.assertFalse(restarted.readiness.ready)

    def test_transaction_is_unavailable_before_bootstrap_and_has_no_connection_handle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            with self.assertRaises(PersistenceError):
                asyncio.run(service.async_in_transaction(lambda transaction: transaction.transaction_id))

            asyncio.run(service.async_initialize())
            transaction_id = asyncio.run(
                service.async_in_transaction(
                    lambda transaction: self._assert_transaction_boundary(transaction)
                )
            )

            self.assertTrue(transaction_id)
            asyncio.run(service.async_close())

    def test_failed_transaction_rolls_back_without_leaking_schema_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            asyncio.run(service.async_initialize())

            def fail(transaction) -> None:
                transaction.execute("CREATE TABLE persistence_transaction_probe (value TEXT NOT NULL)")
                raise RuntimeError("planned transaction failure")

            with self.assertRaisesRegex(RuntimeError, "planned transaction failure"):
                asyncio.run(service.async_in_transaction(fail))

            path = Path(directory) / "djconnect.sqlite3"
            connection = sqlite3.connect(path)
            try:
                row = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='persistence_transaction_probe'"
                ).fetchone()
            finally:
                connection.close()
            self.assertIsNone(row)
            asyncio.run(service.async_close())

    def test_successful_transaction_commits_its_schema_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            asyncio.run(service.async_initialize())
            asyncio.run(
                service.async_in_transaction(
                    lambda transaction: transaction.execute(
                        "CREATE TABLE persistence_commit_probe (value TEXT NOT NULL)"
                    )
                )
            )

            path = Path(directory) / "djconnect.sqlite3"
            connection = sqlite3.connect(path)
            try:
                row = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='persistence_commit_probe'"
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(row, ("persistence_commit_probe",))
            asyncio.run(service.async_close())

    def test_provider_allows_concurrent_reads_and_serialized_short_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = SQLitePersistenceProvider()
            service = PersistenceService(Path(directory) / "djconnect.sqlite3", provider)
            asyncio.run(service.async_initialize())

            async def exercise_provider() -> tuple[list[int], list[None]]:
                reads = await asyncio.gather(
                    provider.async_read_schema_version(),
                    provider.async_read_schema_version(),
                    provider.async_read_schema_version(),
                )
                writes = await asyncio.gather(
                    service.async_in_transaction(
                        lambda transaction: transaction.execute(
                            "CREATE TABLE persistence_write_probe_one (value TEXT NOT NULL)"
                        )
                    ),
                    service.async_in_transaction(
                        lambda transaction: transaction.execute(
                            "CREATE TABLE persistence_write_probe_two (value TEXT NOT NULL)"
                        )
                    ),
                )
                return reads, writes

            reads, writes = asyncio.run(exercise_provider())

            self.assertEqual(reads, [CURRENT_SCHEMA_VERSION] * 3)
            self.assertEqual(writes, [None, None])
            asyncio.run(service.async_close())

    def test_failed_initialization_can_retry_from_the_same_service(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = PersistenceService(
                Path(directory) / "djconnect.sqlite3", _FailOnceTransactionProvider()
            )
            with self.assertRaisesRegex(PersistenceError, "planned migration failure"):
                asyncio.run(service.async_initialize())
            self.assertFalse(service.readiness.ready)

            readiness = asyncio.run(service.async_initialize())

            self.assertTrue(readiness.ready)
            self.assertEqual(readiness.schema_version, CURRENT_SCHEMA_VERSION)
            asyncio.run(service.async_close())

    @staticmethod
    def _assert_transaction_boundary(transaction) -> str:
        if hasattr(transaction, "connection"):
            raise AssertionError("A repository transaction must not expose a raw connection")
        return transaction.transaction_id

    def test_corrupt_database_fails_integrity_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "djconnect.sqlite3"
            path.write_bytes(b"not a sqlite database")
            service = self._service(directory)

            with self.assertRaises(PersistenceError):
                asyncio.run(service.async_initialize())

            self.assertFalse(service.readiness.ready)

    def test_bootstrap_uses_one_hass_owned_service_at_the_canonical_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hass = _FakeHass(directory)

            first = asyncio.run(async_initialize_persistence(hass))
            second = asyncio.run(async_initialize_persistence(hass))

            self.assertIs(first, second)
            self.assertIs(hass.data["djconnect"][PERSISTENCE_SERVICE_KEY], first)
            self.assertTrue((Path(directory) / ".storage" / "djconnect.sqlite3").exists())
            asyncio.run(async_shutdown_persistence(hass))
            self.assertNotIn(PERSISTENCE_SERVICE_KEY, hass.data["djconnect"])

    def test_bootstrap_serializes_concurrent_startup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            hass = _FakeHass(directory)

            async def initialize_twice() -> tuple[PersistenceService, PersistenceService]:
                return await asyncio.gather(
                    async_initialize_persistence(hass), async_initialize_persistence(hass)
                )

            first, second = asyncio.run(initialize_twice())

            self.assertIs(first, second)
            self.assertTrue(first.readiness.ready)
            asyncio.run(async_shutdown_persistence(hass))

    def test_readiness_and_source_boundary_expose_no_credentials_or_connections(self) -> None:
        readiness_fields = {field.name for field in fields(PersistenceReadiness)}
        self.assertNotIn("database_path", readiness_fields)
        self.assertNotIn("connection", readiness_fields)
        persistence_root = Path(__file__).resolve().parents[1] / "custom_components" / "djconnect"
        python_sources = {
            path.relative_to(persistence_root).as_posix(): path.read_text()
            for path in persistence_root.rglob("*.py")
        }
        sqlite_users = {
            name for name, source in python_sources.items() if "sqlite3.connect" in source
        }
        self.assertEqual(sqlite_users, {"persistence/sqlite.py"})
        public_sources = "\n".join(
            source
            for name, source in python_sources.items()
            if name.startswith("persistence/") and name != "persistence/sqlite.py"
        )
        self.assertNotIn("sqlite3.connect", public_sources)
        self.assertNotIn("spotify_refresh_token", public_sources)
        self.assertNotIn("device_token", public_sources)


class _FakeConfig:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def path(self, *parts: str) -> str:
        return str(self._root.joinpath(*parts))


class _FakeHass:
    def __init__(self, root: str) -> None:
        self.data: dict[str, dict[str, object]] = {}
        self.config = _FakeConfig(root)


class _FailOnceTransactionProvider(SQLitePersistenceProvider):
    """Test-only provider double for startup retry behaviour."""

    def __init__(self) -> None:
        super().__init__()
        self._fail_next_transaction = True

    async def async_run_transaction(self, operation):
        if self._fail_next_transaction:
            self._fail_next_transaction = False
            raise PersistenceError("planned migration failure")
        return await super().async_run_transaction(operation)


if __name__ == "__main__":
    unittest.main()
