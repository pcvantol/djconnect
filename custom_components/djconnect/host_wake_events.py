"""Content-free wakes from the SAME registered child's actual Broadcast.

No HTTP caller creates these event attempts. Original context, registration ACK,
callback clocks and once SQL own each bounded send; no replay or grant renewal.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from fractions import Fraction
import time
import uuid
import weakref

from .direct_rich_frame import final_current, project
from .direct_rich_wire import RichError, digest, require, safe_integer
from .surface_push_events import CHANGES, ENDED

MAX_WORKERS = 8


class _EventExpired(RichError):
    """An unsent callback expired, not a loss of its registered parent."""


@dataclass(frozen=True)
class _Event:
    sequence: int
    signature: str
    operation: str
    wall: float
    mono: float


class _BroadcastAttempt:
    """Read-only borrow of the actual registered parent's ORIGINAL pair.

    It never calls capture_pair or reads inbound headers. Only a live registered
    watch's selected original event can construct this private transport owner.
    """
    def __init__(self, watch, event):
        require(type(watch) is _Watch and watch.active is event, "rich_not_allowed", 403)
        watch.current()
        self.closed = False
        self.watch, self.event = watch, event
        self.task = asyncio.current_task()
        self.wall, self.mono = event.wall, event.mono
        self.last_wall, self.last_mono = self.wall, self.mono
        self.service = watch.registry.service
        self.parent, self.context = watch.child.parent, watch.child.context
        self.pair = self.context.pair  # Borrow only: close never retires this pair.
        self.dependents = weakref.WeakSet()
        self.check()

    def close(self):
        if self.closed:
            return
        self.closed = True
        for dependent in tuple(self.dependents):
            dependent.close()
        self.dependents.clear()
        self.watch = self.event = self.service = self.parent = self.context = self.pair = self.task = None

    def _current(self):
        require(not self.closed and self.task is not None and not self.task.done()
            and not self.task.cancelling(), "rich_unavailable", 503)
        watch = self.watch
        watch.current()
        child = watch.child
        require(watch.active is self.event and child.parent is self.parent
            and child.context is self.context and self.context.pair is self.pair
            and watch.registry.service is self.service and self.pair.current(), "rich_not_allowed", 403)
        wall, mono = time.time(), time.monotonic()
        require(wall >= self.last_wall and mono >= self.last_mono, "rich_not_allowed", 403)
        if not (0 <= Fraction(wall) - Fraction(self.wall) < 30
                and 0 <= Fraction(mono) - Fraction(self.mono) < 30):
            raise _EventExpired("rich_unavailable", 503)
        self.last_wall, self.last_mono = wall, mono
        return min(30 - (wall - self.wall), 30 - (mono - self.mono))

    def check(self):
        require(asyncio.current_task() is self.task, "rich_unavailable", 503)
        return self._current()

    def storage_current(self, task):
        require(task is self.task, "rich_unavailable", 503)
        return self._current()

    async def wait(self, work):
        try:
            async with asyncio.timeout(self.check()):
                result = await work()
            self.check()
            return result
        except asyncio.CancelledError:
            self.close()
            raise
        except (TimeoutError, _EventExpired):
            self.close()
            raise _EventExpired("rich_unavailable", 503) from None
        except Exception:
            self.close()
            raise RichError("rich_unavailable", 503) from None


class _Watch:
    def __init__(self, child):
        self.child, self.registry = child, child.registry
        self.broadcast = child.context.broadcast
        self.closed = False
        self.pending = self.active = self.task = None
        self.subscription = None
        self.callback = self.changed
        self.sequence = self.broadcast.delivery_sequence
        self.signature = self._signature()
        self.subscription = self.broadcast.register_subscription(self.callback)

    def current(self):
        child, registry = self.child, self.registry
        require(not self.closed and child is not None and not child.closed
            and child._watch is self and child.registry is registry and not registry.closed
            and registry.children.get(child.reservation.parent.purpose_id) is child
            and child.context.broadcast is self.broadcast and child.metadata.phase == "registered"
            and child._credential is not None and child._private_purpose is not None
            and child._native_receipt is not None and child._native_receipt["state"] == "native_verified"
            and child._native_receipt["original_sha256"] == digest(child._original),
            "rich_not_allowed", 403)
        registry.service._current()
        require(child._owner_attestation(child) is None, "rich_not_allowed", 403)
        child._check_clocks()
        if self.subscription is not None:
            registered = self.broadcast._subscribers.get(self.subscription)
            require(registered is not None and registered[0] is self.callback,
                "rich_not_allowed", 403)

    def _signature(self):
        child = self.child
        attempt = child.context.attempt()
        try:
            frame, _assets = project(attempt, purpose_id=child.reservation.parent.purpose_id,
                generation=child.reservation.generation, expires_ms=child.reservation.parent.expires_ms)
            require(final_current(attempt, frame), "rich_frame_unavailable", 503)
            def semantic(value):
                if type(value) is dict:
                    return {key: semantic(item) for key, item in value.items()
                        if key not in {"observed_at", "expires_at"}}
                if type(value) is list:
                    return [semantic(item) for item in value]
                return value
            return digest(semantic({key: frame[key] for key in ("state", "playback_state", "mood",
                "presence", "persona", "contribution", "now_playing", "artwork",
                "contribution_status", "now_playing_status", "artwork_status")}))
        finally:
            attempt.retire()

    def stop(self):
        """Local synchronous retirement; one prebound negative port only."""
        if self.closed:
            return
        self.closed = True
        broadcast, subscription = self.broadcast, self.subscription
        child, task = self.child, self.task
        self.pending = self.active = None
        if subscription is not None:
            broadcast.unsubscribe(subscription)
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
        self.child = self.registry = self.broadcast = self.callback = self.subscription = self.task = None
        if child is not None:
            port = child._withdrawal
            if port is not None and not port.used:
                try:
                    port.schedule()
                except Exception:
                    pass  # No replacement negative identity or secret capture.

    def changed(self, event):
        # Original callback capture BEFORE projection, task creation or await.
        wall, mono = time.time(), time.monotonic()
        try:
            require(not self.closed and self.child is not None and not self.child.closed
                and self.child._watch is self and self.child.context.broadcast is self.broadcast,
                "rich_not_allowed", 403)
            kind = event.get("event_type")
            if kind in ENDED:
                self.child.close()
                return
            if kind not in CHANGES:
                return
            sequence = event.get("delivery_sequence")
            require(event.get("session_id") == self.child.context.session_id
                and safe_integer(sequence, 1) and sequence == self.broadcast.delivery_sequence,
                "rich_not_allowed", 403)
            if sequence <= self.sequence:
                return
            self.sequence = sequence
            # Broadcast publishes while the actual manager lock is held.
            # Capture dirtiness only; the worker projects after that lock, with
            # the SAME callback clocks and full original owner checks.
            # Coalescing replaces an UNSENT event only with a different actual
            # callback. It never refreshes the active attempt's original window.
            self.pending = _Event(sequence, "", str(uuid.uuid4()), wall, mono)
            if self.task is None or self.task.done():
                if len(self.registry.tasks) >= MAX_WORKERS:
                    self.pending = None  # Unsent capacity loss is not parent withdrawal.
                    return
                self.task = self.registry.service.hass.async_create_background_task(
                    self.work(), "djconnect-original-host-wake")
                registry = self.registry
                registry.tasks.add(self.task)
                def finished(task, registry=registry):
                    registry.tasks.discard(task)  # Also after stop scrubs this watch.
                    self._finished(task)
                self.task.add_done_callback(finished)
        except Exception:
            if self.child is not None:
                self.child.close()

    def _finished(self, task):
        if not self.closed and (task.cancelled() or task.exception() is not None):
            self.child.close()

    async def work(self):
        from .host_wake_runtime import _Exchange

        try:
            while not self.closed and self.pending is not None:
                self.active, self.pending = self.pending, None
                attempt, exchange = None, None
                try:
                    event = self.active
                    remaining = min(30 - (time.time() - event.wall),
                        30 - (time.monotonic() - event.mono))
                    if not 0 < remaining <= 30:
                        raise _EventExpired("rich_unavailable", 503)
                    lock = self.child.context.manager._lock
                    try:
                        async with asyncio.timeout(remaining):
                            await lock.acquire()
                        lock.release()
                    except TimeoutError:
                        raise _EventExpired("rich_unavailable", 503) from None
                    attempt = _BroadcastAttempt(self, self.active)
                    # Waiting consumes THIS callback's original 30s; never
                    # cancel a foreground request or recapture its owner.
                    while self.child.pending is not None:
                        pending = self.child.pending
                        async def wait_original():
                            return await asyncio.shield(pending)
                        await attempt.wait(wait_original)
                    self.current()
                    signature = self._signature()
                    if signature == self.signature:
                        continue
                    self.signature = signature
                    exchange = _Exchange.from_broadcast(attempt)
                    try:
                        await exchange.wake(self.active.operation)
                    except _EventExpired:
                        if exchange.entered_journal:
                            exchange.fail()
                            raise
                        exchange.abandon_unstarted()
                    except BaseException:
                        exchange.fail()
                        raise
                except _EventExpired:
                    # No durable attempt/IO began: discard just this original
                    # signal without cancelling a busy foreground request.
                    if exchange is not None and exchange.entered_journal:
                        raise
                except RichError as error:
                    if (error.code != "rich_frame_unavailable"
                            or (exchange is not None and exchange.entered_journal)):
                        raise
                    # An uncommitted projection is not fresh permission and
                    # is not evidence that the original parent was revoked.
                    if exchange is not None:
                        exchange.abandon_unstarted()
                finally:
                    if attempt is not None:
                        attempt.close()
                    self.active = None
        except asyncio.CancelledError:
            if self.child is not None:
                self.child.close()
            raise
        except Exception:
            if self.child is not None:
                self.child.close()


def attach(child):
    """Once, after the real native+registration SQL/API ACK and RAM release."""
    require(child._watch is None and child.pending is None and child.metadata.phase == "registered",
        "rich_not_allowed", 403)
    watch = _Watch(child)
    child._watch = watch
    try:
        watch.current()
    except BaseException:
        child.close()
        raise
