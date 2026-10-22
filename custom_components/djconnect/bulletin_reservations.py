"""Hash-only bulletin cache through confirmed platform SQLite transactions.

HA Store.async_save may swallow write errors or defer writes during shutdown.
This adapter uses the already initialized provider: no lazy schema/config writes.
"""
from __future__ import annotations

import math
import re

from .bulletin_builder import BuilderError, MAX_RESERVATIONS


def validate(data):
    if (type(data) is not dict or set(data) != {"schema", "clock", "reservations"}
            or type(data["schema"]) is not int or data["schema"] != 1
            or type(data["clock"]) not in (int, float) or not math.isfinite(data["clock"])
            or data["clock"] < 0 or type(data["reservations"]) is not dict
            or len(data["reservations"]) > MAX_RESERVATIONS):
        raise BuilderError("bulletin_reservation_invalid")
    for key, expires in data["reservations"].items():
        if (type(key) is not str or not re.fullmatch("[a-f0-9]{64}", key)
                or type(expires) not in (int, float) or not math.isfinite(expires) or expires <= 0):
            raise BuilderError("bulletin_reservation_invalid")


class BulletinReservationStore:
    def __init__(self, persistence):
        self.persistence = persistence

    async def async_load(self):
        def load(tx):
            clock = tx.fetchone("SELECT high_water FROM djconnect_bulletin_clock WHERE singleton=1")
            if clock is None:
                raise BuilderError("bulletin_reservation_unavailable")
            rows = tx.fetchall("SELECT story_hash,expires_at FROM djconnect_bulletin_attempts LIMIT ?",
                (MAX_RESERVATIONS + 1,))
            data = {"schema": 1, "clock": clock[0], "reservations": dict(rows)}
            validate(data)
            return data
        return await self.persistence.async_in_transaction(load)

    async def async_save(self, data):
        validate(data)
        # Capture exact values before the worker boundary, not a mutable builder graph.
        clock, rows = data["clock"], tuple(data["reservations"].items())
        def save(tx):
            tx.execute("DELETE FROM djconnect_bulletin_attempts")
            for key, expires in rows:
                tx.execute("INSERT INTO djconnect_bulletin_attempts(story_hash,expires_at) VALUES (?,?)", (key, expires))
            tx.execute("UPDATE djconnect_bulletin_clock SET high_water=max(high_water,?) WHERE singleton=1", (clock,))
        # Real failure propagates; cancellation follows the provider's definitive
        # commit/rollback policy. No model call starts on an unconfirmed outcome.
        await self.persistence.async_in_transaction(save)
