"""Actual warm parent-owned child RAM latch and SQL lifetime, not native admission.

Normal DirectRichService setup owns one registry. The original loaded
installation may resolve its role; no issuer/provider effect, native/clock
factory, HTTP registration or positive credential is created here.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import uuid

from .direct_rich_frame import utc_ms
from .direct_rich_wire import canonical, digest, require
from . import host_wake_api_wire as api
from .host_wake_child_store import ChildAttempt, ChildMetadata, ChildReservation, HostWakeChildJournal
from .host_wake_proxy_wire import request_sha256, validate

MAX_CHILDREN = 32


class HostWakeChildren:
    def __init__(self, service):
        self.service = service
        self.journal = HostWakeChildJournal(service.journal.persistence)
        self.children = {}  # Includes every closed/spent scope; never evict/refund.
        self.closed = False

    def close(self):
        self.closed = True
        from .host_wake_withdrawal import close_service
        close_service(self.service)
        for child in self.children.values():
            child.close()

    def capture(self, attempt, prepare):
        """Actual original pending latch BEFORE any SQL/role/network await."""
        from .host_wake_proxy_attempt import HostWakeAttempt

        require(type(attempt) is HostWakeAttempt, "rich_unavailable", 503)
        attempt.check()
        validate("prepare", prepare)
        require(not self.closed and self.service.host_wake_children is self
            and attempt.service is self.service and attempt.parent is not None
            and attempt.context is attempt.parent.context, "rich_not_allowed", 403)
        coordinates = tuple(prepare[k] for k in ("device_id", "client_type", "session_id",
            "surface", "purpose_id", "operation_id"))
        require(attempt.request == coordinates, "rich_not_allowed", 403)
        parent = attempt.parent
        require(parent.original.purpose_id not in self.children, "rich_purpose_consumed", 409)
        require(len(self.children) < MAX_CHILDREN, "rich_capacity", 409)
        reservation = ChildReservation(parent.original, prepare["operation_id"], parent.generation,
            request_sha256("prepare", prepare), utc_ms(attempt.wall, upper=True))
        reservation.validate()
        child = _Child(self, parent, reservation, attempt, deepcopy(prepare))
        self.children[parent.original.purpose_id] = child
        parent.dependents.add(child)
        attempt.dependents.add(child)
        # No await between original capture, registration, latch and this check.
        child.current()
        return child

    def capture_management(self, attempt, payload, *, operation):
        from .host_wake_management import _Management
        return _Management(self, attempt, payload, operation)


class _Child:
    """Original live context and exclusive pending task; never SQL restoration."""
    def __init__(self, registry, parent, reservation, attempt, prepare):
        self.registry, self.parent, self.context = registry, parent, parent.context
        self.reservation = reservation
        self.initial_attempt = attempt
        self.closed = False
        self.pending = asyncio.current_task()
        self.pending.add_done_callback(self._request_finished)
        self.reserved = False
        self.metadata = None
        self._prepare = prepare
        self._resolved_request = self._resolved_role = None
        self._original = self._role = self._issuer_request = self._issuer_claim = None
        self._withdrawal = None

    def _request_finished(self, task):
        if self.pending is task or task.cancelled() or task.cancelling():
            self.close()  # Includes cancellation before reserve's first run.

    def close(self):
        if self.closed:
            return
        self.closed = True
        parent, self.parent = self.parent, None
        if parent is not None:
            parent.dependents.discard(self)
        pending, self.pending = self.pending, None
        self.registry = self.context = None
        self._prepare = self._resolved_request = self._resolved_role = None
        self._original = self._role = self._issuer_request = self._issuer_claim = None
        attempt, self.initial_attempt = self.initial_attempt, None
        if attempt is not None:
            attempt.dependents.discard(self)
        if pending is not None and not pending.done():
            pending.cancel()

    def current(self):
        return self._current(asyncio.current_task(), storage=False)

    def storage_current(self):
        # SQLite's FULL-sync finalizer runs in its own guard task. The inbound
        # task identity remains the original pending task, not that helper.
        return self._current(self.pending, storage=True)

    def _current(self, task, *, storage):
        try:
            require(not self.closed and self.registry is not None and not self.registry.closed,
                "rich_not_allowed", 403)
            registry, parent = self.registry, self.parent
            service = registry.service
            require(task is not None and not task.done() and not task.cancelling()
                and (self.pending is None or self.pending is task), "rich_unavailable", 503)
            if self.initial_attempt is not None:
                if storage:
                    self.initial_attempt.storage_current(task)
                else:
                    self.initial_attempt.check()  # SAME original pre-body 30s.
            require(service.host_wake_children is registry
                and registry.children.get(self.reservation.parent.purpose_id) is self
                and service.purposes.get(self.reservation.parent.purpose_id) is parent
                and parent.original is self.reservation.parent and parent.generation == self.reservation.generation
                and parent.context is self.context and parent.issued
                and service._purpose_current(parent), "rich_not_allowed", 403)
            self.context._inspect()
            return True
        except BaseException:
            self.close()
            raise

    def _continue_prepare(self):
        # Deny another task BEFORE a close-on-failure/currentness check. This
        # task owns the initial prepare; SQL success is never its handoff.
        task = asyncio.current_task()
        require(self.pending is task and task is not None and self.reserved,
            "rich_purpose_consumed", 409)
        self.current()
        return task

    async def resolve(self):
        """Actual original installation-authenticated role lookup, DATA only.

        Caller supplies no owner, policy hash, role, URL or replacement pair.
        The retained response is not clock/enrollment/positive admission.
        """
        from .host_wake_api import HostWakeApiChannel
        from .host_wake_proxy_wire import decode_json

        task = self._claim()
        channel = None
        try:
            require(not self.reserved, "rich_purpose_consumed", 409)
            context, pair = self.context, self.initial_attempt.pair
            scope = {key: deepcopy(self._prepare[key]) for key in
                ("target", "platform", "apns_environment", "native_key_id_b64")}
            scope.update(owner_binding=self.reservation.parent.owner_hash,
                device_binding=self.reservation.parent.device_hash,
                source_binding=digest(["DJC-DIRECT-RICH-SOURCE-V1", dict(context.source)]),
                paired_subject_binding_sha256=digest(["DJC-DIRECT-RICH-PAIRED-SUBJECT-V1",
                    pair.acknowledgement.instance_id, pair.acknowledgement.auth_generation,
                    pair.entry.entry_id, pair.device_id, pair.client_type]))
            sent = {"version": api.VERSION, "scope": scope}
            role_hash = api.request_hash("authorization/resolve", sent)
            channel = HostWakeApiChannel(self.initial_attempt)
            await self.reserve(role_request_hash=role_hash, attempt_id=str(uuid.uuid4()))
            status, raw = await channel.post("authorization/resolve", canonical(sent))
            self.current()
            value = decode_json(raw)
            if status != 200:
                api.error(status, value)
                require(False, "rich_unavailable", 503)
            api.resolved(value, sent)
            self.current()
            # No await between final original guards and custody publication.
            self._resolved_request, self._resolved_role = sent, value
            return deepcopy(value)  # Never export the retained mutable mapping.
        except BaseException:
            if self.pending is task:
                self.pending = None
            self.close()
            raise
        finally:
            if channel is not None:
                channel.close()

    async def seal(self, *, prepare, sent_resolve, role, original):
        """Join frozen DATA under the SAME original prepare, without admission."""
        task = self._continue_prepare()
        try:
            require(all(type(value) is dict for value in (prepare, sent_resolve, role, original)))
            # SQL finalize guards execute after awaits. Neither caller mutation
            # nor a late role mapping may change their bytes or our RAM cache.
            prepare, sent_resolve, role, original = (deepcopy(value)
                for value in (prepare, sent_resolve, role, original))
            if self._resolved_role is not None:
                require(digest(sent_resolve) == digest(self._resolved_request)
                    and digest(role) == digest(self._resolved_role), "rich_not_allowed", 403)
            context, registry = self.context, self.registry
            result = await registry.journal.seal(self.reservation, session_id=context.session_id,
                owner_id=context.owner, prepare=prepare, sent_resolve=sent_resolve, role=role,
                original=original, current=self.storage_current)
            self.current()
            require(type(result) is ChildMetadata and result.phase == "sealed" and result.cas_revision == 1
                and result.consumed_attempts == 1 and result.original_hash == digest(original)
                and result.role_hash == digest(role) and result.expires_ms == original["original_wake_expires_at_ms"],
                "rich_unavailable", 503)
            # No await after final same-task/current/deadline check and joins.
            self._original, self._role, self.metadata = original, role, result
            return result
        except BaseException:
            if self.pending is task:
                self.pending = None
            self.close()
            raise

    async def seal_resolved(self, *, original):
        """Use only this child's retained authenticated reply, no caller role.

        The original mapping is still DATA: genuine clock/native admission is
        independently required before any later positive issuer/network effect.
        """
        self._continue_prepare()
        require(type(self._resolved_request) is dict and type(self._resolved_role) is dict,
            "rich_unavailable", 503)
        return await self.seal(prepare=self._prepare, sent_resolve=self._resolved_request,
            role=self._resolved_role, original=original)

    async def begin_issuer(self):
        """Consume the owner's own issuer UUID/SQL claim BEFORE any API effect.

        This produces consumed DATA only, not clock/native/API permission. The
        next negative-only installation port must use this exact owned object;
        resolve metadata supplies no issuer-operation ID.
        """
        task = self._continue_prepare()
        try:
            require(type(self.metadata) is ChildMetadata and self.metadata.phase == "sealed"
                and self._issuer_claim is None and type(self._role) is dict and type(self._original) is dict,
                "rich_purpose_consumed", 409)
            require(self.metadata.original_hash == digest(self._original) and self.metadata.role_hash == digest(self._role),
                "rich_unavailable", 503)
            operation = str(uuid.uuid4())
            sent = {"version": api.VERSION, "authorization_id": self._role["authorization_id"],
                "core_purpose_id": self.reservation.parent.purpose_id,
                "issuer_operation_id": operation, "original": deepcopy(self._original)}
            request_hash = api.request_hash("issuer/issue", sent)
            semantic = digest(["DJC-HOST-WAKE-ONCE-V1", self.reservation.parent.purpose_id, "issuer_issue"])
            revision = self.metadata.cas_revision
            context, registry = self.context, self.registry
            claim = await registry.journal.begin(self.reservation, expected_revision=revision,
                kind="issuer_issue", semantic_hash=semantic, request_hash=request_hash, attempt_id=operation,
                session_id=context.session_id, owner_id=context.owner, current=self.storage_current)
            self.current()
            require(type(claim) is ChildAttempt and (claim.ordinal, claim.attempt_id, claim.kind,
                claim.semantic_hash, claim.request_hash, claim.pending_revision, claim.pending_phase)
                == (self.metadata.consumed_attempts + 1, operation, "issuer_issue", semantic, request_hash,
                    revision + 1, "issuing"), "rich_unavailable", 503)
            self._issuer_request, self._issuer_claim = sent, claim
            self.metadata = ChildMetadata(self.metadata.original_hash, self.metadata.role_hash,
                self.metadata.expires_ms, "issuing", claim.pending_revision, claim.ordinal)
            return claim  # Exact SQL object, not a reconstructed positive receipt.
        except BaseException:
            if self.pending is task:
                self.pending = None
            self.close()
            raise

    def _claim(self):
        # A competing request is denied without retiring the first request.
        require(self.pending is None or (self.pending is asyncio.current_task() and not self.reserved),
            "rich_purpose_consumed", 409)
        self.current()
        task = asyncio.current_task()
        self.pending = task  # Synchronous before first transaction await.
        return task

    def capture_withdrawal(self):
        """Attenuate this actual owned claim before future issuer IO."""
        from .host_wake_withdrawal import _IssuerWithdrawal

        self._continue_prepare()
        require(self._withdrawal is None, "rich_purpose_consumed", 409)
        self._withdrawal = _IssuerWithdrawal(self)
        return self._withdrawal

    def withdraw(self):
        """Fence local state synchronously BEFORE any negative task scheduling."""
        withdrawal = self._withdrawal
        self.close()
        require(withdrawal is not None, "rich_unavailable", 503)
        return withdrawal.schedule()

    async def reserve(self, *, role_request_hash, attempt_id):
        """Consume SQL without releasing the ORIGINAL prepare request.

        This is not its HTTP handoff. The later actual role/issuer/ACK/final RAM
        composition must still share this task, dependency and original budget.
        Until genuine prepared handoff exists, taskdone/close always scrubs it.
        """
        task = self._claim()
        try:
            require(not self.reserved, "rich_purpose_consumed", 409)
            self.reserved = True  # Lost/cancelled SQL ACK never refunds the latch.
            context, registry = self.context, self.registry
            result = await registry.journal.reserve(self.reservation, session_id=context.session_id,
                owner_id=context.owner, role_request_hash=role_request_hash, attempt_id=attempt_id,
                current=self.storage_current)
            self.current()
            if task.cancelling():
                raise asyncio.CancelledError
            self.metadata = result  # No await after final original-context check.
            return result
        except BaseException:
            if self.pending is task:
                self.pending = None
            self.close()
            raise
