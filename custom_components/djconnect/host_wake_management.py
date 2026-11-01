"""Actual original paired negative/history capture; no positive restoration.

This returns local journal metadata only. Native challenge/job semantics,
remote withdrawal acknowledgement and public response publication are separate.
"""
from __future__ import annotations

import asyncio

from .direct_rich_runtime import _binding
from .direct_rich_wire import require
from .host_wake_proxy_attempt import HostWakeAttempt
from .host_wake_proxy_wire import validate


class _Management:
    def __init__(self, registry, attempt, payload, operation):
        from .profile_observation import capture_committed

        self.closed = False
        self.attempt = self.registry = self.snapshot = self.child = self.task = None
        self.owner = self.session_id = self.operation = None
        require(type(attempt) is HostWakeAttempt, "rich_unavailable", 503)
        try:
            attempt.check_body_budget()
            require(type(operation) is str and operation in {"status", "withdraw"})
            validate(operation, payload)
            require(attempt.service is registry.service
                and registry.service.host_wake_children is registry and not registry.closed
                and attempt.parent is None and attempt.request is None, "rich_unavailable", 503)
            pair = attempt.pair
            require(payload["device_id"] == pair.device_id and payload["client_type"] == pair.client_type,
                "unauthorized", 401)
            # A single actual inbound body cannot be rebound to another scope.
            attempt.request = tuple(payload[key] for key in ("device_id", "client_type", "session_id",
                "surface", "purpose_id", "operation_id"))
            snapshot = capture_committed(registry.service.hass)
            require(snapshot is not None and snapshot.current(), "rich_unavailable", 503)
            device = snapshot.household.devices.get(pair.device_id)
            require(device is not None and device.client_type == pair.client_type
                and str(device.pairing_state) == "paired"
                and device.linked_profile_id in snapshot.household.profiles, "rich_not_allowed", 403)
            scope, ownership = _binding(pair, device.linked_profile_id, payload["session_id"], payload["surface"])
            child = registry.children.get(payload["purpose_id"])
            require(child is not None, "rich_history_unknown", 404)
            # Never inspect child.parent/context/current: they may be retired.
            # SQL DATA or an equal caller tuple cannot manufacture this child.
            original = child.reservation.parent
            require(scope == original.scope_hash and ownership == tuple(getattr(original, name) for name in
                ("owner_hash", "device_hash", "entry_hash", "pair_hash", "session_hash", "surface"))
                and child.reservation.native_operation_id == payload["operation_id"], "rich_not_allowed", 403)
            self.registry, self.attempt, self.snapshot, self.child = registry, attempt, snapshot, child
            self.task, self.owner = asyncio.current_task(), device.linked_profile_id
            self.session_id, self.operation = payload["session_id"], operation
            attempt.dependents.add(self)
            self.current()
        except BaseException:
            self.close()
            attempt.close()  # Only this new request, never the original child.
            raise

    def close(self):
        if self.closed:
            return
        self.closed = True
        attempt, self.attempt = self.attempt, None
        if attempt is not None:
            attempt.dependents.discard(self)
        self.registry = self.snapshot = self.child = self.task = None
        self.owner = self.session_id = self.operation = None

    def current(self, *, storage=False):
        try:
            require(not self.closed and self.task is not None and not self.task.done()
                and not self.task.cancelling(), "rich_unavailable", 503)
            if storage:
                self.attempt.storage_current(self.task)
            else:
                require(asyncio.current_task() is self.task, "rich_unavailable", 503)
                self.attempt.check()
            registry = self.registry
            require(not registry.closed and self.attempt.service is registry.service
                and registry.service.host_wake_children is registry
                and registry.children.get(self.child.reservation.parent.purpose_id) is self.child
                and self.snapshot.current(), "rich_unavailable", 503)
            return True
        except BaseException:
            self.close()
            raise

    async def run(self):
        """Local history/withdrawal DATA; not a remote or native success ACK."""
        require(not self.closed and self.task is asyncio.current_task(), "rich_purpose_consumed", 409)
        try:
            self.current()
            child, registry, owner, session_id = self.child, self.registry, self.owner, self.session_id
            withdraw = self.operation == "withdraw"
            if withdraw:
                child.close()  # Matching child only, BEFORE any bookkeeping await.
            result = await registry.journal.history(child.reservation, session_id=session_id, owner_id=owner,
                current=lambda: self.current(storage=True), withdraw=withdraw)
            self.current()
            return result  # No re-creation of a parent, child, secret or remote ACK.
        finally:
            self.close()
