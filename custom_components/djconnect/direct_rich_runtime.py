"""Actual warm, original Direct rich purpose owner on platform persistence.

Purpose secrets live only in this owning setup lifetime. SQLite metadata is
once/history, never a positive restoration or credential recovery mechanism.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from fractions import Fraction
import hmac
import secrets
import time
import uuid
import weakref

from .direct_rich_context import capture_context
from .direct_rich_frame import final_current, project, utc_ms
from .direct_rich_output import valid
from .direct_rich_pair import capture_pair
from .direct_rich_store import RichOriginal, RichPurposeJournal, owner_hash, session_hash
from .direct_rich_wire import PROFILE, PURPOSE_MS, RichError, canonical, credential, digest, require

KEY = "direct_rich_service"
MAX_PURPOSES = 32


@dataclass(eq=False, repr=False)
class _Purpose:
    original: RichOriginal
    generation: str
    context: object
    wall_start: float
    mono_start: float
    mono_end: Fraction
    read_secret: str = ""
    asset_secret: str = ""
    pending: object = None
    closed: bool = False
    issued: bool = False
    dependents: object = field(default_factory=weakref.WeakSet)

    def retire(self):
        if self.closed:
            return
        self.closed = True
        self.read_secret = self.asset_secret = ""
        for dependent in tuple(self.dependents):
            dependent.close()  # Original child fence BEFORE context/task cleanup.
        self.dependents.clear()
        context, self.context = self.context, None
        pending, self.pending = self.pending, None
        if context is not None:
            context.retire()
        if pending is not None and not pending.done():
            pending.cancel()


def _pair_identity(pair, session_id, surface):
    ack = pair.acknowledgement
    original_pair = [ack.instance_id, ack.auth_generation]
    return (digest(["DJC-DIRECT-RICH-DEVICE-V1", pair.device_id]),
        digest(["DJC-DIRECT-RICH-ENTRY-V1", pair.entry.entry_id]),
        digest(["DJC-DIRECT-RICH-PAIR-V1", *original_pair]), session_hash(session_id), surface)


def _binding(pair, owner, session_id, surface):
    ack = pair.acknowledgement
    original_pair = [ack.instance_id, ack.auth_generation]
    scope = digest(["DJC-DIRECT-RICH-PURPOSE-V1", *original_pair,
        pair.entry.entry_id, owner, session_id, surface])
    ownership = (owner_hash(owner), *_pair_identity(pair, session_id, surface))
    return scope, ownership


def _management(hass, headers, payload):
    """Original paired owner lookup without an ACTIVE Session/source demand."""
    from .profile_observation import capture_committed
    pair = capture_pair(hass, headers, device_id=payload["device_id"], client_type=payload["client_type"])
    try:
        snapshot = capture_committed(hass)
        require(snapshot is not None and snapshot.current(), "rich_unavailable", 503)
        device = snapshot.household.devices.get(payload["device_id"])
        require(device is not None and device.client_type == payload["client_type"]
            and str(device.pairing_state) == "paired"
            and device.linked_profile_id in snapshot.household.profiles, "rich_not_allowed", 403)
        scope, ownership = _binding(pair, device.linked_profile_id, payload["session_id"], payload["surface"])
        return pair, snapshot, scope, ownership
    except BaseException as error:
        pair.retire()
        if isinstance(error, Exception) and not isinstance(error, RichError):
            raise RichError("rich_unavailable", 503) from None
        raise


class DirectRichService:
    def __init__(self, hass, persistence):
        self.hass = hass
        self.domain = hass.data["djconnect"]
        self.journal = RichPurposeJournal(persistence)
        self.purposes = {}
        self.scopes = {}
        self.closed = False
        from .host_wake_child_runtime import HostWakeChildren
        self.host_wake_children = HostWakeChildren(self)

    def close(self):
        self.closed = True
        self.host_wake_children.close()
        for purpose in self.purposes.values():
            purpose.retire()

    def _current(self):
        try:
            require(not self.closed and not self.hass.is_stopping
                and self.hass.data.get("djconnect") is self.domain
                and self.domain.get(KEY) is self, "rich_unavailable", 503)
            self.journal._storage()
        except RichError:
            self.close()
            raise

    def _purpose_current(self, purpose):
        self._current()
        now, wall = time.monotonic(), time.time()
        if (purpose.closed or not purpose.mono_start <= now
                or Fraction(now) >= purpose.mono_end
                or not purpose.wall_start <= wall
                or Fraction(wall) * 1000 >= purpose.original.expires_ms):
            purpose.retire()
            return False
        return True

    @staticmethod
    def _response(purpose, request, frame):
        original = purpose.original
        return {"success": True, "contract_version": 1, "profile_id": PROFILE,
            "operation_id": original.operation_id, "request_sha256": digest(request),
            "purpose_id": original.purpose_id, "surface": original.surface, "state": "active",
            "purpose_issued_at_ms": original.issued_ms, "purpose_expires_at_ms": original.expires_ms,
            "frame": frame}

    def _negative_fence(self, payload, headers, *, exact_operation):
        """Genuine original pair may always close its known RAM scope first.

        A queued cosmetic Profile write can defer metadata lookup, but cannot
        defer this original device/entry/pair/Session/surface negative intent.
        No caller supplies owner identity or creates a replacement authority.
        """
        pair = capture_pair(self.hass, headers, device_id=payload["device_id"], client_type=payload["client_type"])
        try:
            identity = _pair_identity(pair, payload["session_id"], payload["surface"])
            for purpose in self.purposes.values():
                original = purpose.original
                if ((original.device_hash, original.entry_hash, original.pair_hash,
                        original.session_hash, original.surface) == identity
                        and (not exact_operation or original.operation_id == payload["operation_id"])):
                    purpose.retire()
        finally:
            pair.retire()

    async def authorize(self, payload, headers, captured, *, as_bytes=False):
        self._current()
        enabled = payload["enabled"] and payload["os_snapshot_cache"] and (
            payload["surface"] != "live_activity" or payload["locked_display"])
        if not enabled:
            self._negative_fence(payload, headers, exact_operation=False)
            pair, snapshot, scope, ownership = _management(self.hass, headers, payload)
            try:
                existing = self.scopes.get(scope)
                if existing is not None:
                    existing.retire()  # No await before local secret/cancellation fence.
                try:
                    await self.journal.history(None, ownership, scope_hash=scope,
                        current=lambda: pair.current() and snapshot.current(), withdraw=True)
                except RichError as error:
                    if error.code != "rich_history_unknown":
                        raise
            finally:
                pair.retire()
            raise RichError("rich_not_allowed", 403)
        wall, mono = captured
        context = capture_context(self.hass, headers, device_id=payload["device_id"],
            client_type=payload["client_type"], session_id=payload["session_id"])
        attempt = context.attempt()
        scope, ownership = _binding(context.pair, context.owner, context.session_id, payload["surface"])
        if scope in self.scopes or len(self.purposes) >= MAX_PURPOSES:
            context.retire()
            raise RichError("rich_purpose_consumed" if scope in self.scopes else "rich_capacity", 409)
        original = RichOriginal(scope, payload["operation_id"], str(uuid.uuid4()), *ownership,
            digest(payload), utc_ms(wall, upper=True),
            int((Fraction(wall) * 1000 + PURPOSE_MS).__floor__()))
        purpose = _Purpose(original, str(uuid.uuid4()), context, wall, mono,
            Fraction(mono) + Fraction(PURPOSE_MS, 1000), pending=asyncio.current_task())
        self.purposes[original.purpose_id] = purpose
        self.scopes[scope] = purpose  # Original pending latch before the first await.
        context.on_retire = purpose.retire

        def current():
            return self._purpose_current(purpose) and attempt.current()

        try:
            require(current(), "rich_frame_unavailable", 503)
            await self.journal.reserve(original, session_id=context.session_id, owner_id=context.owner, current=current)
            require(current(), "rich_frame_unavailable", 503)
            await self.journal.issued(original, session_id=context.session_id, owner_id=context.owner, current=current)
            require(current(), "rich_frame_unavailable", 503)
            frame, _ = project(attempt, purpose_id=original.purpose_id,
                generation=purpose.generation, expires_ms=original.expires_ms)
            purpose.read_secret = "djcrichread_" + secrets.token_urlsafe(32)
            purpose.asset_secret = "djcrichasset_" + secrets.token_urlsafe(32)
            result = self._response(purpose, payload, frame)
            result.update(read_credential=purpose.read_secret, asset_credential=purpose.asset_secret)
            encoded = canonical(result)
            require(valid("authorize_response", result) and len(encoded) <= 16384
                and current() and final_current(attempt, frame), "rich_frame_unavailable", 503)
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            purpose.issued, purpose.pending = True, None
            return encoded if as_bytes else result
        except BaseException:
            # The original scope stays consumed even if the durable ACK or
            # response is lost. No fresh UUID/read can reconstruct the secret.
            purpose.pending = None
            purpose.retire()
            raise
        finally:
            attempt.retire()

    def read(self, payload, headers, *, asset=False, as_bytes=False):
        self._current()
        require(not any(name in headers for name in ("X-DJConnect-Device-ID", "X-DJConnect-Client-Type")))
        secret = credential(headers, "asset" if asset else "read")
        purpose = self.purposes.get(payload["purpose_id"])
        expected = purpose.asset_secret if purpose is not None and asset else purpose.read_secret if purpose else ""
        require(bool(expected) and hmac.compare_digest(secret, expected), "unauthorized", 401)
        require(self._purpose_current(purpose) and purpose.issued, "rich_not_allowed", 403)
        attempt = purpose.context.attempt()
        try:
            frame, assets = project(attempt, purpose_id=purpose.original.purpose_id,
                generation=purpose.generation, expires_ms=purpose.original.expires_ms)
            if asset:
                require(payload["frame_id"] == frame["frame_id"], "rich_frame_changed", 409)
                require(payload["asset_id"] in assets, "rich_asset_unavailable", 404)
                result = assets[payload["asset_id"]]
            else:
                result = self._response(purpose, payload, frame)
                encoded = canonical(result)
                require(valid("read_response", result) and len(encoded) <= 16384, "rich_frame_unavailable", 503)
            require(self._purpose_current(purpose) and final_current(attempt, frame), "rich_frame_unavailable", 503)
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            return encoded if as_bytes and not asset else result
        finally:
            attempt.retire()

    async def manage(self, payload, headers, *, withdraw=False, as_bytes=False):
        self._current()
        if withdraw:
            self._negative_fence(payload, headers, exact_operation=True)
        pair, snapshot, scope, ownership = _management(self.hass, headers, payload)
        try:
            purpose = self.scopes.get(scope)
            if withdraw and purpose is not None and purpose.original.operation_id == payload["operation_id"]:
                purpose.retire()
            original, phase = await self.journal.history(payload["operation_id"], ownership,
                current=lambda: pair.current() and snapshot.current(), withdraw=withdraw)
            state = "withdrawn" if phase == "withdrawn" else "expired" if utc_ms(time.time()) >= original.expires_ms else (
                "active" if purpose is not None and purpose.original == original and purpose.issued
                and self._purpose_current(purpose) and not purpose.closed else "unknown")
            require(pair.current() and snapshot.current(), "rich_unavailable", 503)
            result = {"success": True, "contract_version": 1, "profile_id": PROFILE,
                "operation_id": original.operation_id, "purpose_id": original.purpose_id,
                "surface": original.surface, "state": state,
                "purpose_issued_at_ms": original.issued_ms, "purpose_expires_at_ms": original.expires_ms}
            require(valid("manage_response", result), "rich_unavailable", 503)
            encoded = canonical(result)
            require(pair.current() and snapshot.current(), "rich_unavailable", 503)
            return encoded if as_bytes else result
        finally:
            pair.retire()


def setup_service(hass):
    """Integration setup only. Reads never create or replace an owner lifetime."""
    from .persistence import PERSISTENCE_SERVICE_KEY
    domain = hass.data["djconnect"]
    existing = domain.get(KEY)
    if existing is None:
        domain[KEY] = DirectRichService(hass, domain[PERSISTENCE_SERVICE_KEY])
