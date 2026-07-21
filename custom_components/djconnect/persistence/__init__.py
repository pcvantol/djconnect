"""DJConnect-owned durable persistence platform.

This package owns storage-provider lifecycle, schema migration and integrity
validation. Domain capabilities interact with repositories built on this
boundary; they never open a database connection themselves.
"""

from .bootstrap import (
    PERSISTENCE_SERVICE_KEY,
    async_initialize_persistence,
    async_shutdown_persistence,
    persistence_service,
)
from .service import (
    PersistenceError,
    PersistenceIntegrityError,
    PersistenceReadiness,
    PersistenceRepository,
    PersistenceSchemaError,
    PersistenceService,
    PersistenceTransaction,
)
from .sessions import PersistentSession, PersistentSessionRepository, SessionLifecycleError, SessionOwnershipError

__all__ = [
    "PERSISTENCE_SERVICE_KEY",
    "PersistenceError",
    "PersistenceIntegrityError",
    "PersistenceReadiness",
    "PersistenceRepository",
    "PersistenceSchemaError",
    "PersistenceService",
    "PersistenceTransaction",
    "PersistentSession",
    "PersistentSessionRepository",
    "SessionLifecycleError",
    "SessionOwnershipError",
    "async_initialize_persistence",
    "async_shutdown_persistence",
    "persistence_service",
]
