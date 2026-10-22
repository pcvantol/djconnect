"""Confirmed, bounded push-effect journal on the existing SQLite provider.

No HA Store write acknowledgement, token/config/key persistence or lazy schema.
One adapter belongs to one OperationJournal; revision CAS rejects stale owners.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import re

from .surface_push_wire import canonical
from .transport_operations import OperationError, OperationJournal

MAX_BYTES = 524288
OPERATIONS = {"push/surface/" + kind for kind in ("register", "revoke", "event")}


async def validated_snapshot(data):
    snapshot = deepcopy(data)  # Capture before the first await.
    class Captured:
        async def async_load(self):
            return snapshot
    probe = OperationJournal(Captured(), wall_ms=lambda:0, monotonic=lambda:0)
    await probe._load()  # Reuse the existing closed receipt/state validator.
    for record in snapshot["records"].values():
        if (record["operation"] not in OPERATIONS
                or any(re.fullmatch("[a-f0-9]{64}", record[k]) is None
                    for k in ("owner", "device", "binding", "digest"))
                or re.fullmatch("[a-f0-9]{32}", record["epoch"]) is None):
            raise OperationError("surface_journal_invalid", 503)
    encoded = canonical(snapshot)
    if len(encoded.encode()) > MAX_BYTES:
        raise OperationError("surface_journal_invalid", 503)
    return snapshot, encoded


class SurfaceOperationStore:
    def __init__(self, persistence):
        self.persistence = persistence
        self._revision = None
        self._lock = asyncio.Lock()

    async def async_load(self):
        async with self._lock:
            row = await self.persistence.async_in_transaction(lambda tx:tx.fetchone(
                "SELECT revision,high_water_ms,body FROM djconnect_surface_journal WHERE singleton=1"))
            if row is None or (self._revision is not None and self._revision != row[0]):
                raise OperationError("surface_journal_unavailable", 503)
            data = json.loads(row[2])
            data["high_water_ms"] = max(data["high_water_ms"], row[1])
            snapshot, _ = await validated_snapshot(data)
            self._revision = row[0]
            return snapshot

    async def async_save(self, data):
        snapshot, encoded = await validated_snapshot(data)
        async with self._lock:
            expected = self._revision
            if type(expected) is not int:
                raise OperationError("surface_journal_unavailable", 503)
            def save(tx):
                row = tx.fetchone("SELECT revision FROM djconnect_surface_journal WHERE singleton=1")
                if row is None or row[0] != expected:
                    raise OperationError("surface_journal_owner_changed", 503)
                tx.execute("UPDATE djconnect_surface_journal SET revision=?,body=?,"
                    "high_water_ms=max(high_water_ms,?) WHERE singleton=1",
                    (expected+1, encoded, snapshot["high_water_ms"]))
            await self.persistence.async_in_transaction(save)
            self._revision = expected+1  # Only after definitive commit; exceptions never acknowledge.
