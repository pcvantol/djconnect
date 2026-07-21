"""Forward-only schema metadata and migrations for the persistence platform."""

from __future__ import annotations

from datetime import UTC, datetime

from .provider import ProviderTransaction


CURRENT_SCHEMA_VERSION = 1


def apply_migration(transaction: ProviderTransaction, version: int) -> None:
    """Apply one known forward-only platform migration."""
    if version != 1:
        raise ValueError(f"Unknown DJConnect persistence migration: {version}")
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
    timestamp = datetime.now(UTC).isoformat()
    transaction.execute(
        "INSERT OR REPLACE INTO djconnect_schema_metadata "
        "(singleton, schema_version, updated_at) VALUES (1, ?, ?)",
        (version, timestamp),
    )
    transaction.execute(
        "INSERT OR IGNORE INTO djconnect_schema_migrations "
        "(schema_version, applied_at) VALUES (?, ?)",
        (version, timestamp),
    )
