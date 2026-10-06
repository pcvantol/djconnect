"""Home Assistant bootstrap for the integration-owned persistence platform."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..const import DOMAIN
from .service import PersistenceService
from .sqlite import SQLitePersistenceProvider
from .sessions import PersistentSessionRepository
from .reconciliation import PersistentSessionStartupReconciler
from .history import HistoricalProjectionRepository


PERSISTENCE_SERVICE_KEY = "persistence_service"
_PERSISTENCE_LOCK_KEY = "persistence_bootstrap_lock"
_RECONCILED_KEY = "persistence_startup_reconciled"
_DATABASE_FILENAME = "djconnect.sqlite3"


def _database_path(hass: Any) -> Path:
    """Return the private DJConnect database below HA's configuration storage."""
    config = getattr(hass, "config", None)
    path = getattr(config, "path", None)
    if callable(path):
        return Path(path(".storage", _DATABASE_FILENAME))
    return Path(".storage") / _DATABASE_FILENAME


async def async_initialize_persistence(hass: Any) -> PersistenceService:
    """Initialize the singleton platform service before entry business services run."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    lock = domain_data.get(_PERSISTENCE_LOCK_KEY)
    if not isinstance(lock, asyncio.Lock):
        lock = asyncio.Lock()
        domain_data[_PERSISTENCE_LOCK_KEY] = lock
    async with lock:
        service = domain_data.get(PERSISTENCE_SERVICE_KEY)
        if not isinstance(service, PersistenceService):
            service = PersistenceService(_database_path(hass), SQLitePersistenceProvider())
            domain_data[PERSISTENCE_SERVICE_KEY] = service
        await service.async_initialize()
        # Reconcile crash leftovers once, before any entry can start a Runtime.
        # Entry setup/reload must never interrupt another entry's live Session.
        if not domain_data.get(_RECONCILED_KEY):
            await PersistentSessionStartupReconciler(
                PersistentSessionRepository(service),
                history=HistoricalProjectionRepository(service),
            ).async_reconcile()
            domain_data[_RECONCILED_KEY] = True
        return service


def persistence_service(hass: Any) -> PersistenceService:
    """Return the initialized persistence service without creating hidden state."""
    service = getattr(hass, "data", {}).get(DOMAIN, {}).get(PERSISTENCE_SERVICE_KEY)
    if not isinstance(service, PersistenceService):
        raise RuntimeError("DJConnect persistence bootstrap has not completed")
    return service


async def async_shutdown_persistence(hass: Any, *, preserve_for_reload: bool = False) -> None:
    """Close the singleton provider after the final configured entry unloads."""
    domain_data = hass.data.get(DOMAIN, {})
    if preserve_for_reload:
        # Active Runtime repositories keep this exact singleton service.
        return
    service = domain_data.pop(PERSISTENCE_SERVICE_KEY, None)
    domain_data.pop(_PERSISTENCE_LOCK_KEY, None)
    # Keep the boot receipt for this HA process: a final-entry options reload
    # may close this provider while retaining the active Session Runtime.
    if isinstance(service, PersistenceService):
        await service.async_close()
