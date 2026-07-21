"""Forward-only schema metadata and migrations for the persistence platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .provider import ProviderTransaction


@dataclass(frozen=True)
class Migration:
    """Immutable identity for one ordered, platform-owned migration."""

    version: int
    migration_id: str
    checksum: str


MIGRATIONS = (
    Migration(1, "0001_persistence_metadata", "8c52f0c7"),
    Migration(2, "0002_migration_identity", "b0b063e2"),
)
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version
REQUIRED_TABLES = {
    "djconnect_schema_metadata": {"singleton", "schema_version", "updated_at"},
    "djconnect_schema_migrations": {
        "schema_version", "migration_id", "checksum", "applied_at", "success"
    },
}


def migration_for(version: int) -> Migration:
    """Return the immutable migration definition for one version."""
    for migration in MIGRATIONS:
        if migration.version == version:
            return migration
    raise ValueError(f"Unknown DJConnect persistence migration: {version}")


def apply_migration(transaction: ProviderTransaction, version: int) -> None:
    """Apply one known forward-only platform migration."""
    migration = migration_for(version)
    if version == 1:
        transaction.execute(
        """
        CREATE TABLE IF NOT EXISTS djconnect_schema_metadata (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            schema_version INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
        )
        transaction.execute(
        """
        CREATE TABLE IF NOT EXISTS djconnect_schema_migrations (
            schema_version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
        )
    elif version == 2:
        transaction.execute(
            "ALTER TABLE djconnect_schema_migrations ADD COLUMN migration_id TEXT NOT NULL DEFAULT ''"
        )
        transaction.execute(
            "ALTER TABLE djconnect_schema_migrations ADD COLUMN checksum TEXT NOT NULL DEFAULT ''"
        )
        transaction.execute(
            "ALTER TABLE djconnect_schema_migrations ADD COLUMN success INTEGER NOT NULL DEFAULT 1 "
            "CHECK (success IN (0, 1))"
        )
        initial = migration_for(1)
        transaction.execute(
            "UPDATE djconnect_schema_migrations SET migration_id=?, checksum=?, success=1 "
            "WHERE schema_version=1",
            (initial.migration_id, initial.checksum),
        )
    timestamp = datetime.now(UTC).isoformat()
    transaction.execute(
        "INSERT OR REPLACE INTO djconnect_schema_metadata "
        "(singleton, schema_version, updated_at) VALUES (1, ?, ?)",
        (version, timestamp),
    )
    if version == 1:
        transaction.execute(
            "INSERT OR IGNORE INTO djconnect_schema_migrations "
            "(schema_version, applied_at) VALUES (?, ?)",
            (version, timestamp),
        )
    else:
        transaction.execute(
            "INSERT INTO djconnect_schema_migrations "
            "(schema_version, migration_id, checksum, applied_at, success) VALUES (?, ?, ?, ?, 1)",
            (version, migration.migration_id, migration.checksum, timestamp),
        )
