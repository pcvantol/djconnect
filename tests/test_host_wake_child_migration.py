"""Actual SQLite20→21 and partial-DDL rollback; synthetic historical metadata."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_persistence_platform import (
    PersistenceError, PersistenceSchemaError, PersistenceService, SQLitePersistenceProvider,
)
from custom_components.djconnect.persistence import schema, service as service_module


class HostWakeChildMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def legacy20(self, path):
        # Explicit reconstruction from unchanged migrations1..20. This is not
        # an original installed HA20 database or an operational backup receipt.
        legacy = PersistenceService(path, SQLitePersistenceProvider())
        required = {k: v for k, v in schema.REQUIRED_TABLES.items() if not k.startswith("djconnect_host_wake_")}
        try:
            with patch.object(service_module, "CURRENT_SCHEMA_VERSION", 20), \
                    patch.object(service_module, "MIGRATIONS", schema.MIGRATIONS[:20]), \
                    patch.object(service_module, "REQUIRED_TABLES", required):
                readiness = await legacy.async_initialize()
                self.assertEqual(readiness.schema_version, 20)
            await legacy.async_in_transaction(lambda tx: tx.execute(
                "INSERT INTO djconnect_rich_purposes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("a" * 64, "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222",
                    "b" * 64, "c" * 64, "d" * 64, "e" * 64, "f" * 64, "widget", "9" * 64, 1000, 2000, "withdrawn")))
            return await legacy.async_in_transaction(lambda tx: (
                tx.fetchall("SELECT * FROM djconnect_rich_purposes"),
                tx.fetchall("SELECT * FROM djconnect_schema_migrations ORDER BY schema_version")))
        finally:
            await legacy.async_close()

    async def test_actual20_to21_preserves_old_rows_and_migration_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "migration.sqlite"
            old_rows, old_history = await self.legacy20(path)
            current = PersistenceService(path, SQLitePersistenceProvider())
            try:
                readiness = await current.async_initialize()
                self.assertEqual(readiness.schema_version, 21)
                rows, history, children = await current.async_in_transaction(lambda tx: (
                    tx.fetchall("SELECT * FROM djconnect_rich_purposes"),
                    tx.fetchall("SELECT * FROM djconnect_schema_migrations ORDER BY schema_version"),
                    tx.fetchone("SELECT count(*) FROM djconnect_host_wake_children")[0]))
                self.assertEqual(rows, old_rows)
                self.assertEqual(history[:20], old_history)
                self.assertEqual(len(history), 21)
                self.assertEqual(children, 0)
                self.assertEqual(readiness.last_migration_id, "0021_host_wake_child_once")
            finally:
                await current.async_close()

    async def test_failure_between_two21_tables_rolls_back_only_new_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "migration.sqlite"
            _, old_history = await self.legacy20(path)
            current = PersistenceService(path, SQLitePersistenceProvider())
            apply = service_module.apply_migration

            def fail_after_child(tx, version):
                if version == 21:
                    tx.execute(schema.HOST_WAKE_CHILD_DDL)
                    raise PersistenceError("planned SQL21 partial DDL failure")
                return apply(tx, version)

            with patch.object(service_module, "apply_migration", side_effect=fail_after_child), \
                    self.assertRaisesRegex(PersistenceError, "planned SQL21"):
                await current.async_initialize()
            self.assertFalse(current.readiness.ready)
            provider = SQLitePersistenceProvider()
            try:
                await provider.async_open(str(path))
                self.assertEqual(await provider.async_read_schema_version(), 20)
                history, tables = await provider.async_run_transaction(lambda tx: (
                    tx.fetchall("SELECT * FROM djconnect_schema_migrations ORDER BY schema_version"),
                    tx.fetchall("SELECT name FROM sqlite_master WHERE name LIKE 'djconnect_host_wake_%'")))
                self.assertEqual(history, old_history)
                self.assertEqual(tables, [])
            finally:
                await provider.async_close()

    async def test_changed21_identity_is_rejected_instead_of_repaired(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "migration.sqlite"
            current = PersistenceService(path, SQLitePersistenceProvider())
            try:
                await current.async_initialize()
                await current.async_in_transaction(lambda tx: tx.execute(
                    "UPDATE djconnect_schema_migrations SET checksum='not-the-reviewed21' WHERE schema_version=21"))
            finally:
                await current.async_close()
            reopened = PersistenceService(path, SQLitePersistenceProvider())
            with self.assertRaises(PersistenceSchemaError):
                await reopened.async_initialize()
            self.assertFalse(reopened.readiness.ready)


if __name__ == "__main__":
    unittest.main()
