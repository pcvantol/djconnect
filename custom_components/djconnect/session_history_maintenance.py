"""Lifecycle housekeeping through existing history, Profile and Store owners."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from .persistence import persistence_service
from .persistence.history import HistoricalProjectionRepository
from .historical_projection_retention import HistoricalProjectionRetentionService


async def async_purge_profile_history(hass, profile_id: str) -> None:
    domain = getattr(hass, "data", {}).get("djconnect", {})
    if "persistence_service" in domain:
        await HistoricalProjectionRepository(persistence_service(hass)).async_purge_profile_history(
            profile_id
        )
    from .http import _history_manager

    await _history_manager(hass).async_clear("profile:" + profile_id)


async def async_maintain_session_history(hass, *, now=None, revoked_entry_id: str = "") -> None:
    """One bounded source scan plus canonical retention; no new storage authority."""
    domain = getattr(hass, "data", {}).get("djconnect", {})
    if "persistence_service" not in domain:
        return
    lock = domain.setdefault("session_history_maintenance_lock", asyncio.Lock())
    async with lock:
        current = now or datetime.now(UTC)
        repository = HistoricalProjectionRepository(persistence_service(hass))
        if revoked_entry_id:
            await repository.async_withdraw_source_entry(revoked_entry_id)
        await HistoricalProjectionRetentionService(repository).async_cleanup(now=current)
        from .session_conversation import async_qualify_history_source, query_service
        from .profile_context import profile_storage
        from .http import _history_manager

        household = await profile_storage(hass).async_load()
        valid = set(household.profiles)
        after = domain.get("session_history_maintenance_after", "")
        rows = await repository.async_playback_maintenance_records(after=after)
        remove = {}
        import json

        for row in rows:
            owner = row["owner_profile_id"]
            try:
                captured = json.loads(row["body"]).get("source_context", {})
            except (TypeError, ValueError, AttributeError):
                remove.setdefault(owner, []).append(row["entry_id"])
                continue
            revoked = revoked_entry_id and captured.get("provider_entry_id") == revoked_entry_id
            if revoked or not await async_qualify_history_source(hass, owner, row):
                remove.setdefault(owner, []).append(row["entry_id"])
        for owner, identifiers in remove.items():
            await repository.async_remove_entry_records(owner, identifiers)
        domain["session_history_maintenance_after"] = (
            rows[-1]["entry_id"] if len(rows) == 250 else ""
        )
        manager = _history_manager(hass)
        query = query_service(hass, manager)

        async def retained_dependency(owner, target):
            try:
                await query.async_open_entry(owner, target["session_id"], target["entry_id"])
            except PermissionError:
                return False
            return True

        await manager.async_prune_session_history(
            valid,
            cutoff=(current - timedelta(days=90)).isoformat(),
            dependency_validator=retained_dependency,
        )


def schedule_history_maintenance(hass) -> None:
    """Coalesce metadata-change maintenance, retaining HA's normal task ownership."""
    if "persistence_service" not in getattr(hass, "data", {}).get("djconnect", {}):
        return
    create_task = getattr(hass, "async_create_task", None)
    domain = hass.data["djconnect"]
    pending = domain.get("session_history_maintenance_task")
    if callable(create_task) and (pending is None or pending.done()):
        domain["session_history_maintenance_task"] = create_task(
            async_maintain_session_history(hass)
        )
