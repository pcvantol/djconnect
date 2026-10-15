"""Bounded transport operation receipts; no domain execution or private bodies.

The journal serializes short HA Store transactions. Adapters must invoke the
existing application handlers only after a successful durable reservation.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import secrets
import re
import time
from uuid import UUID

VERSION = 1
LIFETIME_MS = 300_000
FUTURE_SKEW_MS = 30_000
MAX_RECORDS = 256
MAX_OWNER_RECORDS = 64
MAX_ACTIVE = 8
TERMINAL = frozenset({"confirmed", "rejected", "cancelled", "unknown"})
PHASES = TERMINAL | {"accepted", "sent_unknown"}


class OperationError(Exception):
    """Typed, content-free operation failure."""

    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.code, self.status = code, status


def operation_created_ms(identifier: str) -> int:
    """Read the immutable UUIDv7 timestamp; arbitrary retry strings are invalid."""
    try:
        value = UUID(identifier)
        if value.version != 7 or str(value) != identifier:
            raise ValueError
        return value.int >> 80
    except (ValueError, TypeError, AttributeError):
        raise OperationError("invalid_operation_id", 400) from None


class OperationJournal:
    """One lock/clock/Store owner; no eviction of unexpired dedup evidence."""

    def __init__(self, store, *, wall_ms=None, monotonic=None):
        self._store = store
        self._wall = wall_ms or (lambda: int(time.time() * 1000))
        self._mono = monotonic or time.monotonic
        self._anchor_wall = self._wall()
        self._anchor_mono = self._mono()
        self._high_water = 0
        self._state = None
        self._failed = False
        self._lock = asyncio.Lock()
        self._active: set[str] = set()
        self.epoch = secrets.token_hex(16)

    def now_ms(self):
        self._high_water = max(
            self._high_water,
            self._wall(),
            int(self._anchor_wall + max(0, self._mono() - self._anchor_mono) * 1000),
        )
        return self._high_water

    async def _load(self):
        if self._failed:
            raise OperationError("operation_unavailable", 503)
        if self._state is not None:
            return
        try:
            state = await self._store.async_load()
            if state is None:
                state = {"version": VERSION, "high_water_ms": 0, "records": {}}
            if (
                not isinstance(state, dict)
                or state.get("version") != VERSION
                or type(state.get("high_water_ms")) is not int
                or not isinstance(state.get("records"), dict)
                or len(state["records"]) > MAX_RECORDS
            ):
                raise ValueError
            for key, record in state["records"].items():
                if (
                    not isinstance(key, str)
                    or not isinstance(record, dict)
                    or record.get("phase") not in PHASES
                    or type(record.get("expires_ms")) is not int
                    or not all(
                        isinstance(record.get(k), str)
                        for k in (
                            "operation_id",
                            "epoch",
                            "owner",
                            "binding",
                            "operation",
                            "digest",
                        )
                    )
                    or record["expires_ms"]
                    != operation_created_ms(record["operation_id"]) + LIFETIME_MS
                ):
                    raise ValueError
            self._state = deepcopy(state)
            self._high_water = max(self._high_water, state["high_water_ms"])
        except Exception:
            self._failed = True
            raise OperationError("operation_unavailable", 503) from None

    def _validate_time(self, identifier):
        created, now = operation_created_ms(identifier), self.now_ms()
        if created > now + FUTURE_SKEW_MS:
            raise OperationError("operation_clock_unqualified", 400)
        if created + LIFETIME_MS <= now:
            raise OperationError("operation_expired")
        return created + LIFETIME_MS

    @staticmethod
    def _key(owner, device, identifier):
        return hashlib.sha256((owner + "\n" + device + "\n" + identifier).encode()).hexdigest()

    def _candidate(self):
        state = deepcopy(self._state)
        state["high_water_ms"] = self.now_ms()
        state["records"] = {
            k: v
            for k, v in state["records"].items()
            if v["expires_ms"] > state["high_water_ms"] or k in self._active
        }
        return state

    async def _commit(self, state):
        try:
            await self._store.async_save(deepcopy(state))
        except BaseException:
            # An exception can follow a successful atomic disk write. Never let
            # stale RAM reserve the same operation again after an uncertain save.
            self._failed = True
            raise
        self._state = state

    def receipt(self, record):
        phase = record["phase"]
        if record["epoch"] != self.epoch and phase not in TERMINAL:
            phase = "unknown"
        return {
            "contract_version": VERSION,
            "operation_id": record["operation_id"],
            "operation_epoch": record["epoch"],
            "phase": phase,
            "expires_at_ms": record["expires_ms"],
            "result_available": False,
            "response_status": record.get("response_status"),
            "error": record.get("error"),
        }

    async def reserve(self, *, owner, device, binding, identifier, epoch, operation, digest):
        async with self._lock:
            await self._load()
            expires = self._validate_time(identifier)
            if epoch != self.epoch:
                raise OperationError("operation_epoch_changed")
            key = self._key(owner, device, identifier)
            old = self._state["records"].get(key)
            if old is not None:
                if (old["binding"], old["epoch"], old["operation"], old["digest"]) != (
                    binding,
                    epoch,
                    operation,
                    digest,
                ):
                    raise OperationError("operation_conflict")
                return key, self.receipt(old), False
            state = self._candidate()
            if (
                len(state["records"]) >= MAX_RECORDS
                or sum(v["owner"] == owner for v in state["records"].values()) >= MAX_OWNER_RECORDS
                or len(self._active) >= MAX_ACTIVE
            ):
                raise OperationError("operation_capacity", 429)
            record = {
                "owner": owner,
                "binding": binding,
                "operation_id": identifier,
                "epoch": epoch,
                "operation": operation,
                "digest": digest,
                "expires_ms": expires,
                "phase": "accepted",
            }
            state["records"][key] = record
            try:
                await self._commit(state)
            except asyncio.CancelledError:
                raise
            except Exception:
                raise OperationError("operation_unavailable", 503) from None
            self._active.add(key)
            return key, self.receipt(record), True

    async def transition(self, key, phase, *, response_status=None, error=None):
        if phase not in PHASES:
            raise ValueError("invalid operation phase")
        if response_status is not None and (
            type(response_status) is not int or not 100 <= response_status <= 599
        ):
            raise ValueError("invalid response status")
        if error is not None and (
            not isinstance(error, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,79}", error)
        ):
            error = "operation_domain_error"
        async with self._lock:
            await self._load()
            old = self._state["records"].get(key)
            if old is None:
                raise OperationError("operation_unknown")
            if old["phase"] in TERMINAL:
                return self.receipt(old)
            state = self._candidate()
            record = state["records"][key]
            record.update(phase=phase, response_status=response_status, error=error)
            try:
                await self._commit(state)
            except asyncio.CancelledError:
                raise
            except Exception:
                raise OperationError("operation_unavailable", 503) from None
            return self.receipt(record)

    def release(self, key):
        self._active.discard(key)

    async def status(self, *, owner, device, binding, identifier, epoch):
        async with self._lock:
            await self._load()
            self._validate_time(identifier)
            record = self._state["records"].get(self._key(owner, device, identifier))
            if record is None:
                raise OperationError("operation_unknown")
            if record["binding"] != binding or record["epoch"] != epoch:
                raise OperationError("operation_context_changed")
            return self.receipt(record)

    async def collect_expired(self):
        async with self._lock:
            await self._load()
            # Commit the high-watermark with deletions. Reads never write it.
            try:
                await self._commit(self._candidate())
            except asyncio.CancelledError:
                raise
            except Exception:
                raise OperationError("operation_unavailable", 503) from None
