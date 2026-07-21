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
    Migration(3, "0003_persistent_session_lifecycle", "d16f024c"),
    Migration(4, "0004_historical_session_projections", "b745d401"),
)
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version
REQUIRED_TABLES = {
    "djconnect_schema_metadata": {"singleton", "schema_version", "updated_at"},
    "djconnect_schema_migrations": {
        "schema_version", "migration_id", "checksum", "applied_at", "success"
    },
    "djconnect_persistent_sessions": {
        "session_id", "owner_profile_id", "lifecycle_status", "created_at", "started_at",
        "ended_at", "interrupted_at", "interruption_reason", "start_strategy", "initial_mood",
        "initial_direction", "updated_at"
    },
    "djconnect_historical_sessions": {"historical_session_id", "originating_session_id", "owner_profile_id", "lifecycle_outcome", "created_at", "projection_version"},
    "djconnect_historical_moments": {"historical_moment_id", "originating_session_id", "originating_moment_id", "owner_profile_id", "moment_type", "rendered_text", "visibility", "ordering", "created_at", "projection_version"},
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
    elif version == 3:
        transaction.execute(
            "CREATE TABLE djconnect_persistent_sessions ("
            "session_id TEXT PRIMARY KEY, owner_profile_id TEXT NOT NULL, "
            "lifecycle_status TEXT NOT NULL CHECK (lifecycle_status IN ('OPENING','ACTIVE','ENDED','INTERRUPTED')), "
            "created_at TEXT NOT NULL, started_at TEXT NOT NULL DEFAULT '', ended_at TEXT NOT NULL DEFAULT '', "
            "interrupted_at TEXT NOT NULL DEFAULT '', interruption_reason TEXT NOT NULL DEFAULT '', "
            "start_strategy TEXT NOT NULL DEFAULT '', initial_mood TEXT NOT NULL DEFAULT '', "
            "initial_direction TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)"
        )
        transaction.execute("CREATE INDEX idx_persistent_sessions_owner_created ON djconnect_persistent_sessions(owner_profile_id, created_at DESC)")
        transaction.execute("CREATE INDEX idx_persistent_sessions_non_terminal ON djconnect_persistent_sessions(lifecycle_status, created_at)")
    elif version == 4:
        transaction.execute("CREATE TABLE djconnect_historical_sessions (historical_session_id TEXT PRIMARY KEY, originating_session_id TEXT NOT NULL UNIQUE, owner_profile_id TEXT NOT NULL, lifecycle_outcome TEXT NOT NULL, started_at TEXT NOT NULL DEFAULT '', ended_at TEXT NOT NULL DEFAULT '', interrupted_at TEXT NOT NULL DEFAULT '', interruption_reason TEXT NOT NULL DEFAULT '', start_strategy TEXT NOT NULL DEFAULT '', session_mood TEXT NOT NULL DEFAULT '', session_direction TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, projection_version INTEGER NOT NULL)")
        transaction.execute("CREATE TABLE djconnect_historical_moments (historical_moment_id TEXT PRIMARY KEY, originating_session_id TEXT NOT NULL, originating_moment_id TEXT NOT NULL, owner_profile_id TEXT NOT NULL, moment_type TEXT NOT NULL, rendered_text TEXT NOT NULL, presentation_metadata TEXT NOT NULL DEFAULT '', visibility TEXT NOT NULL DEFAULT 'owner', ordering INTEGER NOT NULL, created_at TEXT NOT NULL, projection_version INTEGER NOT NULL, UNIQUE(originating_session_id, originating_moment_id))")
        transaction.execute("CREATE INDEX idx_historical_sessions_owner_created ON djconnect_historical_sessions(owner_profile_id, created_at DESC)")
        transaction.execute("CREATE INDEX idx_historical_moments_session_order ON djconnect_historical_moments(originating_session_id, ordering)")
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
