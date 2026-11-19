"""One actual pre-body paired lifetime and its original warm display parent.

This capture is necessary currentness, not native/clock/operator admission.
There are no restored-parent, caller-context or boolean qualification ports.
"""
from __future__ import annotations

import asyncio
from fractions import Fraction
import time
import weakref

from .direct_rich_pair import capture_pair
from .direct_rich_runtime import KEY, DirectRichService, _binding
from .direct_rich_wire import RichError, one_header, require
from .host_wake_proxy_wire import validate


class HostWakeAttempt:
    """Capture before body awaits; bind body-only coordinates exactly once."""

    def __init__(self, hass, headers):
        self.closed = False
        self.dependents = weakref.WeakSet()
        self.parent = self.context = self.request = None
        self.pair = None
        self.wall = time.time()
        self.mono = self.last_mono = time.monotonic()
        self.last_wall = self.wall
        self.task = asyncio.current_task()
        self.service = hass.data.get("djconnect", {}).get(KEY)
        try:
            require(type(self.service) is DirectRichService, "rich_unavailable", 503)
            require(self.task is not None, "rich_unavailable", 503)
            self.pair = capture_pair(hass, headers,
                device_id=one_header(headers, "X-DJConnect-Device-ID"),
                client_type=one_header(headers, "X-DJConnect-Client-Type"))
            self.pair.on_retire = self.close
            require(self.pair.client_type == "ios", "unauthorized", 401)
            self.check()
            self.task.add_done_callback(self._finished)
        except BaseException:
            self.close()
            raise

    def _finished(self, task):
        if task is self.task:
            self.close()  # Original request custody, even after a helper returned.

    def close(self):
        """Release only this request's pair/graphs, never withdraw its parent."""
        if self.closed:
            return
        self.closed = True
        if self.task is not None:
            self.task.remove_done_callback(self._finished)
        for dependent in tuple(self.dependents):
            dependent.close()
        self.dependents.clear()
        if self.pair is not None:
            self.pair.retire()
        self.pair = self.parent = self.context = self.request = self.task = self.service = None

    def check(self):
        try:
            require(asyncio.current_task() is self.task, "rich_unavailable", 503)
            return self._original_current()
        except BaseException:
            self.close()
            raise

    def storage_current(self, original_task):
        """Owned SQL finalize callback may run in the provider's guard task.

        It must still inspect THIS original inbound task, never adopt the
        provider task as its owner or acquire another deadline/pair/context.
        """
        try:
            require(original_task is self.task, "rich_unavailable", 503)
            return self._original_current()
        except BaseException:
            self.close()
            raise

    def _original_current(self):
        try:
            require(not self.closed and self.task is not None
                and not self.task.cancelling() and not self.task.done(), "rich_unavailable", 503)
            self.service._current()
            require(self.pair.current(), "unauthorized", 401)
            mono, wall = time.monotonic(), time.time()
            require(mono >= self.last_mono and wall >= self.last_wall
                and Fraction(mono) - Fraction(self.mono) < 30
                and Fraction(wall) - Fraction(self.wall) < 30, "rich_unavailable", 503)
            self.last_mono, self.last_wall = mono, wall
            if self.parent is not None:
                require(self.service.purposes.get(self.parent.original.purpose_id) is self.parent
                    and self.parent.context is self.context and self.parent.issued
                    and self.service._purpose_current(self.parent), "rich_not_allowed", 403)
                self.context._inspect()  # SAME original context; no new owner/source.
            return min(30 - (mono - self.mono), 30 - (wall - self.wall))
        except BaseException:
            self.close()  # A later equal-looking pair/service cannot revive this request.
            raise

    def check_body_budget(self):
        try:
            self.check()
            require(Fraction(time.monotonic()) - Fraction(self.mono) < 10
                and Fraction(time.time()) - Fraction(self.wall) < 10, "rich_unavailable", 503)
        except BaseException:
            self.close()
            raise

    def bind_parent(self, operation, payload):
        """Positive path only, after decode and before child SQL/API/latch.

        Negative/history operations must use their separate paired authority;
        this method cannot restore them by acquiring a positive parent.
        """
        self.check_body_budget()
        validate(operation, payload)
        require(self.request is None, "rich_not_allowed", 403)
        require(payload["device_id"] == self.pair.device_id
            and payload["client_type"] == self.pair.client_type, "unauthorized", 401)
        parent = self.service.purposes.get(payload["purpose_id"])
        require(parent is not None and parent.context is not None and parent.issued
            and self.service._purpose_current(parent), "rich_not_allowed", 403)
        context = parent.context
        context._inspect()
        scope, ownership = _binding(self.pair, context.owner, payload["session_id"], payload["surface"])
        original = parent.original
        require(self.service.scopes.get(scope) is parent
            and (original.owner_hash, original.device_hash, original.entry_hash,
                original.pair_hash, original.session_hash, original.surface) == ownership
            and original.operation_id != payload["operation_id"], "rich_not_allowed", 403)
        self.parent, self.context = parent, context
        # Only immutable nonsecret public request coordinates are retained here.
        self.request = tuple(payload[k] for k in ("device_id", "client_type", "session_id",
            "surface", "purpose_id", "operation_id"))
        self.check()
        return parent

    async def wait(self, work):
        """One remaining original budget; no await can refresh the lifetime."""
        remaining = self.check()
        try:
            async with asyncio.timeout(remaining):
                result = await work()
            self.check()
            return result
        except asyncio.CancelledError:
            self.close()
            raise
        except Exception:
            self.close()
            raise RichError("rich_unavailable", 503) from None
