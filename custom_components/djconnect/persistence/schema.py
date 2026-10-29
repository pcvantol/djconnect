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
    Migration(5, "0005_session_timeline_entries", "7d5e3142"),
    Migration(6, "0006_session_summary_acceptance", "aeb3dc41"),
    Migration(7, "0007_profile_session_dj_settings", "9e6b4a31"),
    Migration(8, "0008_profile_announcement_output", "32c0a4e7"),
    Migration(9, "0009_session_retention_policy", "71dbec42"),
    Migration(10, "0010_four_level_presence", "aceb4702"),
    Migration(11, "0011_history_deletion_intents", "9bf47a12"),
    Migration(12, "0012_content_deletion_fences", "54e23f9a"),
    Migration(13, "0013_bulletin_attempt_reservations", "d728b7e1"),
    Migration(14, "0014_surface_effect_journal", "36bf941a"),
    Migration(15, "0015_surface_issuer_stages", "59d7ac42"),
    Migration(16, "0016_surface_pair_registration", "8417b6e2"),
)
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version
REQUIRED_TABLES = {
    "djconnect_surface_pair_store": {"singleton", "instance_id"},
    "djconnect_surface_pairs": {"binding", "entry_id", "auth_generation", "state"},
    "djconnect_surface_issuer_journal": {"singleton", "revision", "high_water_ms", "body"},
    "djconnect_surface_journal": {"singleton", "revision", "high_water_ms", "body"},
    "djconnect_bulletin_attempts": {"story_hash", "expires_at"},
    "djconnect_bulletin_clock": {"singleton", "high_water"},
    "djconnect_content_tombstones": {"owner_profile_id", "session_id", "kind", "reference_id", "entry_id", "created_ms"},
    "djconnect_content_request_fences": {"owner_profile_id", "request_hash", "created_ms"},
    "djconnect_history_deletions": {
        "owner_profile_id", "operation_id", "binding", "digest", "targets",
        "state", "created_ms", "expires_ms", "receipt", "store_plan", "operation_kind", "content_scope",
    },
    "djconnect_history_deletion_targets": {"owner_profile_id", "session_id", "operation_id"},
    "djconnect_history_deletion_clock": {"singleton", "high_water_ms"},
    "djconnect_session_retention": {"singleton", "retention_days", "revision"},
    "djconnect_profile_dj_settings": {"owner_profile_id", "settings", "revision", "updated_at", "contract_version"},
    "djconnect_session_dj_settings": {
        "session_id", "owner_profile_id", "generation", "settings", "revision", "defaults_revision", "updated_at",
    },
    "djconnect_settings_operations": {
        "operation_key", "owner_profile_id", "binding", "digest", "expires_ms", "receipt",
    },
    "djconnect_settings_clock": {"singleton", "high_water_ms"},
    "djconnect_session_summaries": {
        "session_id",
        "tracks",
        "moments",
        "tracks_coverage",
        "moments_coverage",
        "mood_coverage",
        "mood_durations",
        "mood_current",
        "mood_since",
        "source_binding",
    },
    "djconnect_session_acceptances": {"session_id", "kind", "reference_id", "entry_id"},
    "djconnect_schema_metadata": {"singleton", "schema_version", "updated_at"},
    "djconnect_schema_migrations": {
        "schema_version",
        "migration_id",
        "checksum",
        "applied_at",
        "success",
    },
    "djconnect_persistent_sessions": {
        "session_id",
        "owner_profile_id",
        "lifecycle_status",
        "created_at",
        "started_at",
        "ended_at",
        "interrupted_at",
        "interruption_reason",
        "start_strategy",
        "initial_mood",
        "initial_direction",
        "updated_at",
        "history_revision",
        "history_enabled",
    },
    "djconnect_session_entries": {
        "entry_id",
        "session_id",
        "owner_profile_id",
        "entry_order",
        "kind",
        "reference_id",
        "body",
        "occurred_at",
        "retained_until",
        "visibility",
        "revoked_at",
    },
    "djconnect_historical_sessions": {
        "historical_session_id",
        "originating_session_id",
        "owner_profile_id",
        "lifecycle_outcome",
        "created_at",
        "projection_version",
    },
    "djconnect_historical_moments": {
        "historical_moment_id",
        "originating_session_id",
        "originating_moment_id",
        "owner_profile_id",
        "moment_type",
        "rendered_text",
        "visibility",
        "ordering",
        "created_at",
        "projection_version",
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
        transaction.execute(
            "CREATE INDEX idx_persistent_sessions_owner_created ON djconnect_persistent_sessions(owner_profile_id, created_at DESC)"
        )
        transaction.execute(
            "CREATE INDEX idx_persistent_sessions_non_terminal ON djconnect_persistent_sessions(lifecycle_status, created_at)"
        )
    elif version == 4:
        transaction.execute(
            "CREATE TABLE djconnect_historical_sessions (historical_session_id TEXT PRIMARY KEY, originating_session_id TEXT NOT NULL UNIQUE, owner_profile_id TEXT NOT NULL, lifecycle_outcome TEXT NOT NULL, started_at TEXT NOT NULL DEFAULT '', ended_at TEXT NOT NULL DEFAULT '', interrupted_at TEXT NOT NULL DEFAULT '', interruption_reason TEXT NOT NULL DEFAULT '', start_strategy TEXT NOT NULL DEFAULT '', session_mood TEXT NOT NULL DEFAULT '', session_direction TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, projection_version INTEGER NOT NULL)"
        )
        transaction.execute(
            "CREATE TABLE djconnect_historical_moments (historical_moment_id TEXT PRIMARY KEY, originating_session_id TEXT NOT NULL, originating_moment_id TEXT NOT NULL, owner_profile_id TEXT NOT NULL, moment_type TEXT NOT NULL, rendered_text TEXT NOT NULL, presentation_metadata TEXT NOT NULL DEFAULT '', visibility TEXT NOT NULL DEFAULT 'owner', ordering INTEGER NOT NULL, created_at TEXT NOT NULL, projection_version INTEGER NOT NULL, UNIQUE(originating_session_id, originating_moment_id))"
        )
        transaction.execute(
            "CREATE INDEX idx_historical_sessions_owner_created ON djconnect_historical_sessions(owner_profile_id, created_at DESC)"
        )
        transaction.execute(
            "CREATE INDEX idx_historical_moments_session_order ON djconnect_historical_moments(originating_session_id, ordering)"
        )
    elif version == 5:
        transaction.execute(
            "ALTER TABLE djconnect_persistent_sessions ADD COLUMN history_revision INTEGER NOT NULL DEFAULT 0"
        )
        transaction.execute(
            "ALTER TABLE djconnect_persistent_sessions ADD COLUMN history_enabled INTEGER NOT NULL DEFAULT 1"
        )
        transaction.execute(
            "CREATE TABLE djconnect_session_entries (entry_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES djconnect_persistent_sessions(session_id) ON DELETE CASCADE, owner_profile_id TEXT NOT NULL, entry_order INTEGER NOT NULL, kind TEXT NOT NULL, reference_id TEXT NOT NULL, body TEXT NOT NULL, occurred_at TEXT NOT NULL, retained_until TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'owner', revoked_at TEXT NOT NULL DEFAULT '', UNIQUE(session_id,entry_order), UNIQUE(session_id,kind,reference_id))"
        )
        transaction.execute(
            "CREATE INDEX idx_session_entries_owner_order ON djconnect_session_entries(owner_profile_id,session_id,entry_order)"
        )
        transaction.execute(
            "CREATE INDEX idx_session_entries_retention ON djconnect_session_entries(retained_until)"
        )
    elif version == 6:
        transaction.execute(
            "CREATE TABLE djconnect_session_summaries (session_id TEXT PRIMARY KEY REFERENCES djconnect_persistent_sessions(session_id) ON DELETE CASCADE, tracks INTEGER NOT NULL, moments INTEGER NOT NULL, tracks_coverage TEXT NOT NULL, moments_coverage TEXT NOT NULL, mood_coverage TEXT NOT NULL, mood_durations TEXT NOT NULL, mood_current TEXT NOT NULL, mood_since TEXT NOT NULL, source_binding TEXT NOT NULL)"
        )
        transaction.execute(
            "CREATE TABLE djconnect_session_acceptances (session_id TEXT NOT NULL REFERENCES djconnect_persistent_sessions(session_id) ON DELETE CASCADE,kind TEXT NOT NULL,reference_id TEXT NOT NULL,entry_id TEXT NOT NULL DEFAULT '',PRIMARY KEY(session_id,kind,reference_id))"
        )
    elif version == 7:
        transaction.execute(
            "CREATE TABLE djconnect_profile_dj_settings (owner_profile_id TEXT PRIMARY KEY,settings TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>0),updated_at TEXT NOT NULL)"
        )
        transaction.execute(
            "CREATE TABLE djconnect_session_dj_settings (session_id TEXT PRIMARY KEY REFERENCES djconnect_persistent_sessions(session_id) ON DELETE CASCADE,owner_profile_id TEXT NOT NULL,generation TEXT NOT NULL,settings TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>0),defaults_revision INTEGER NOT NULL CHECK(defaults_revision>=0),updated_at TEXT NOT NULL)"
        )
        transaction.execute(
            "CREATE TABLE djconnect_settings_operations (operation_key TEXT PRIMARY KEY,owner_profile_id TEXT NOT NULL,binding TEXT NOT NULL,digest TEXT NOT NULL,expires_ms INTEGER NOT NULL,receipt TEXT NOT NULL)"
        )
        transaction.execute(
            "CREATE INDEX idx_settings_operations_owner_expiry ON djconnect_settings_operations(owner_profile_id,expires_ms)"
        )
        transaction.execute(
            "CREATE TABLE djconnect_settings_clock (singleton INTEGER PRIMARY KEY CHECK(singleton=1),high_water_ms INTEGER NOT NULL CHECK(high_water_ms>=0))"
        )
        transaction.execute("INSERT INTO djconnect_settings_clock VALUES (1,0)")
    elif version == 8:
        # Preserve original receipts and acceptance revisions. Factory output
        # for a new parameter is not evidence of an explicit six-field choice.
        transaction.execute(
            "ALTER TABLE djconnect_profile_dj_settings ADD COLUMN contract_version INTEGER NOT NULL DEFAULT 2"
        )
        transaction.execute(
            "UPDATE djconnect_profile_dj_settings SET settings=json_insert(settings,'$.announcement_output','client_device')"
        )
        transaction.execute(
            "UPDATE djconnect_session_dj_settings SET settings=json_insert(settings,'$.announcement_output','client_device')"
        )
    elif version == 9:
        transaction.execute(
            "CREATE TABLE djconnect_session_retention (singleton INTEGER PRIMARY KEY CHECK(singleton=1),retention_days INTEGER NOT NULL CHECK(retention_days BETWEEN 1 AND 90),revision INTEGER NOT NULL CHECK(revision>0))"
        )
        transaction.execute("INSERT INTO djconnect_session_retention VALUES (1,90,1)")
        # Existing records retain their source/withdrawal state; only the
        # platform's own rolling cleanup deadline becomes Session-scoped.
        transaction.execute(
            "UPDATE djconnect_session_entries SET retained_until=COALESCE((SELECT strftime('%Y-%m-%dT%H:%M:%f+00:00',julianday(COALESCE(NULLIF(ended_at,''),NULLIF(interrupted_at,''),created_at))+90) FROM djconnect_persistent_sessions s WHERE s.session_id=djconnect_session_entries.session_id AND s.lifecycle_status IN ('ENDED','INTERRUPTED')), '9999-12-31T00:00:00+00:00')"
        )
    elif version == 10:
        # Compatibility spelling only. Acceptance revisions/timestamps and
        # immutable receipts/completed Session history keep their exact meaning.
        transaction.execute(
            "UPDATE djconnect_profile_dj_settings SET settings=json_set(settings,'$.presence','presenter') WHERE json_extract(settings,'$.presence')='talkative'"
        )
        transaction.execute(
            "UPDATE djconnect_session_dj_settings SET settings=json_set(settings,'$.presence','presenter') WHERE json_extract(settings,'$.presence')='talkative' AND session_id IN (SELECT session_id FROM djconnect_persistent_sessions WHERE lifecycle_status='ACTIVE')"
        )
    elif version == 11:
        transaction.execute(
            "CREATE TABLE djconnect_history_deletions ("
            "owner_profile_id TEXT NOT NULL,operation_id TEXT NOT NULL,"
            "binding TEXT NOT NULL,digest TEXT NOT NULL,targets TEXT NOT NULL,"
            "state TEXT NOT NULL CHECK(state IN ('pending','store_erased','completed')),"
            "created_ms INTEGER NOT NULL,expires_ms INTEGER NOT NULL,receipt TEXT,"
            "store_plan TEXT NOT NULL DEFAULT '{}',"
            "PRIMARY KEY(owner_profile_id,operation_id))"
        )
        transaction.execute(
            "CREATE TABLE djconnect_history_deletion_targets ("
            "owner_profile_id TEXT NOT NULL,session_id TEXT NOT NULL,operation_id TEXT NOT NULL,"
            "PRIMARY KEY(owner_profile_id,session_id),"
            "FOREIGN KEY(owner_profile_id,operation_id) REFERENCES "
            "djconnect_history_deletions(owner_profile_id,operation_id) ON DELETE CASCADE)"
        )
        transaction.execute(
            "CREATE TABLE djconnect_history_deletion_clock ("
            "singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
            "high_water_ms INTEGER NOT NULL CHECK(high_water_ms>=0))"
        )
        transaction.execute("INSERT INTO djconnect_history_deletion_clock VALUES (1,0)")
        transaction.execute(
            "CREATE INDEX djconnect_session_entry_message ON djconnect_session_entries "
            "(owner_profile_id,json_extract(body,'$.message_id')) "
            "WHERE kind IN ('conversation_user','conversation_dj') AND json_valid(body)"
        )
    elif version == 12:
        transaction.execute("ALTER TABLE djconnect_history_deletions ADD COLUMN operation_kind TEXT NOT NULL DEFAULT 'archive'")
        transaction.execute("ALTER TABLE djconnect_history_deletions ADD COLUMN content_scope TEXT NOT NULL DEFAULT '{}'")
        transaction.execute(
            "CREATE TABLE djconnect_content_tombstones ("
            "owner_profile_id TEXT NOT NULL,session_id TEXT NOT NULL,kind TEXT NOT NULL,"
            "reference_id TEXT NOT NULL,entry_id TEXT NOT NULL,created_ms INTEGER NOT NULL,"
            "PRIMARY KEY(owner_profile_id,session_id,kind,reference_id),"
            "FOREIGN KEY(session_id) REFERENCES djconnect_persistent_sessions(session_id) ON DELETE CASCADE)"
        )
        transaction.execute(
            "CREATE TABLE djconnect_content_request_fences ("
            "owner_profile_id TEXT NOT NULL,request_hash TEXT NOT NULL,created_ms INTEGER NOT NULL,"
            "PRIMARY KEY(owner_profile_id,request_hash))"
        )
    elif version == 13:
        transaction.execute(
            "CREATE TABLE djconnect_bulletin_attempts ("
            "story_hash TEXT PRIMARY KEY CHECK(length(story_hash)=64 AND story_hash NOT GLOB '*[^a-f0-9]*'),"
            "expires_at REAL NOT NULL CHECK(expires_at>0))"
        )
        transaction.execute(
            "CREATE TABLE djconnect_bulletin_clock ("
            "singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
            "high_water REAL NOT NULL CHECK(high_water>=0))"
        )
        transaction.execute("INSERT INTO djconnect_bulletin_clock VALUES (1,0)")
    elif version == 14:
        transaction.execute(
            "CREATE TABLE djconnect_surface_journal ("
            "singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
            "revision INTEGER NOT NULL CHECK(revision>=0),"
            "high_water_ms INTEGER NOT NULL CHECK(high_water_ms>=0),"
            "body TEXT NOT NULL CHECK(length(body)<=524288))"
        )
        transaction.execute("INSERT INTO djconnect_surface_journal VALUES (1,0,0,?)",
            ('{"version":1,"high_water_ms":0,"records":{}}',))
    elif version == 15:
        transaction.execute(
            "CREATE TABLE djconnect_surface_issuer_journal ("
            "singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
            "revision INTEGER NOT NULL CHECK(revision>=0),"
            "high_water_ms INTEGER NOT NULL CHECK(high_water_ms>=0),"
            "body TEXT NOT NULL CHECK(length(body)<=65536))"
        )
        transaction.execute("INSERT INTO djconnect_surface_issuer_journal VALUES (1,0,0,?)",
            ('{"high_water_ms":0,"records":{},"version":1}',))
    elif version == 16:
        transaction.execute(
            "CREATE TABLE djconnect_surface_pair_store ("
            "singleton INTEGER PRIMARY KEY CHECK(singleton=1),instance_id TEXT NOT NULL)"
        )
        transaction.execute(
            "CREATE TABLE djconnect_surface_pairs (binding TEXT PRIMARY KEY,"
            "entry_id TEXT NOT NULL,auth_generation TEXT NOT NULL,"
            "state TEXT NOT NULL CHECK(state IN ('recorded','retired')))"
        )
        transaction.execute(
            "CREATE INDEX idx_surface_pairs_entry ON djconnect_surface_pairs(entry_id)"
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
