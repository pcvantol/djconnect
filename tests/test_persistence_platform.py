"""Focused tests for the DJConnect persistence foundation."""

from __future__ import annotations

import asyncio
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
    PersistenceSchemaError,
    PersistenceService,
)
from custom_components.djconnect.persistence.bootstrap import (  # noqa: E402
    PERSISTENCE_SERVICE_KEY,
    async_initialize_persistence,
    async_shutdown_persistence,
)
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402


class PersistenceFoundationTest(unittest.TestCase):
    """Validate provider lifecycle, migration, integrity and transaction boundaries."""

    def _service(self, directory: str) -> PersistenceService:
        return PersistenceService(Path(directory) / "djconnect.sqlite3", SQLitePersistenceProvider())

    def test_new_database_initializes_schema_and_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self._service(directory)
            readiness = asyncio.run(service.async_initialize())

            self.assertTrue(readiness.ready)
            self.assertEqual(readiness.schema_version, 2)
            self.assertEqual(readiness.last_migration_id, "0002_migration_identity")
            self.assertTrue((Path(directory) / "djconnect.sqlite3").exists())
            asyncio.run(service.async_close())
            self.assertFalse(service.readiness.ready)

    def test_empty_existing_database_follows_migration_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "djconnect.sqlite3"
            sqlite3.connect(path).close()
            service = self._service(directory)

            readiness = asyncio.run(service.async_initialize())

            self.assertEqual(readiness.schema_version, 2)
            connection = sqlite3.connect(path)
            try:
                applied = connection.execute(
                    "SELECT schema_version FROM djconnect_schema_migrations"
                ).fetchall()
            finally:
                connection.close()
            self.assertEqual(applied, [(1,), (2,)])
            asyncio.run(service.async_close())

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

            self.assertEqual(readiness.schema_version, 2)
            self.assertEqual(readiness.last_migration_id, "0002_migration_identity")

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


class _FakeConfig:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def path(self, *parts: str) -> str:
        return str(self._root.joinpath(*parts))


class _FakeHass:
    def __init__(self, root: str) -> None:
        self.data: dict[str, dict[str, object]] = {}
        self.config = _FakeConfig(root)


if __name__ == "__main__":
    unittest.main()
