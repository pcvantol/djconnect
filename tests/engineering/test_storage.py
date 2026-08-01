"""Regression coverage for the versioned Engineering SQLite schema."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from tools.engineering.storage import (
    DATABASE_FILENAME,
    ENGINEERING_STORAGE_SCHEMA_VERSION,
    EngineeringStorageError,
    WORKSPACE_DIRECTORY,
    database_path,
    open_storage,
)


class EngineeringStorageTest(unittest.TestCase):
    def test_creates_private_versioned_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_storage(root) as connection:
                version = connection.execute(
                    "SELECT MAX(version) FROM engineering_schema_migrations"
                ).fetchone()[0]
                self.assertEqual(version, ENGINEERING_STORAGE_SCHEMA_VERSION)
                self.assertIsNotNone(
                    connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='engineering_artifacts'"
                    ).fetchone()
                )
            path = root / WORKSPACE_DIRECTORY / DATABASE_FILENAME
            self.assertEqual(database_path(root), path.resolve())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_refuses_unknown_non_versioned_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = database_path(root)
            path.parent.mkdir()
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE unrelated(value TEXT)")
            with self.assertRaisesRegex(EngineeringStorageError, "no recognized schema history"):
                open_storage(root)

    def test_upgrades_the_pre_release_schema_without_losing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = database_path(root)
            path.parent.mkdir()
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE ep_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute("CREATE TABLE ep_status(name TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
                connection.execute(
                    "INSERT INTO ep_status VALUES('canonical','{\"watcher_state\":\"WATCHER_IDLE\"}','now')"
                )
            with open_storage(root) as connection:
                self.assertEqual(
                    connection.execute("SELECT payload FROM engineering_status WHERE name='canonical'").fetchone()[0],
                    '{"watcher_state":"WATCHER_IDLE"}',
                )

    def test_refuses_newer_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_storage(root) as connection:
                connection.execute(
                    "INSERT INTO engineering_schema_migrations(version) VALUES(?)",
                    (ENGINEERING_STORAGE_SCHEMA_VERSION + 1,),
                )
            with self.assertRaisesRegex(EngineeringStorageError, "newer"):
                open_storage(root)
