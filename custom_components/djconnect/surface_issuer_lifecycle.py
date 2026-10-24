"""Original-owner issuer phases; no default owner or automatic service admission.

Every constructor dependency is required. An abstract port is not enrollment:
there is intentionally no actual key custodian, operator grant or discovery here.
Only separately qualified owning code can supply those dependencies and adopt
the returned RAM credential into a matching service/target.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import math
import time

from .surface_issuer_journal import IssuerStageJournal, MAX_IDENTITIES
from .surface_issuer_owner import EnrolledIssuerOwner, IssuerOwnerCapture
from .surface_issuer_responses import (challenge_winner, issue_winner,
    status_unavailable, withdrawal_ack)
from .surface_issuer_transport import IssuerHTTPReply, IssuerTransport
from .surface_issuer_wire import PREFIX, signing_bytes, verify_envelope
from .surface_push_contract import SurfacePushError, require
from .surface_push_purpose import SurfacePurposeCredential
from .surface_push_wire import safe_integer
from .transport_operations import operation_created_ms


@dataclass(repr=False)
class _OriginalAttempt:
    capture: IssuerOwnerCapture = field(repr=False)
    handle: IssuerManagementHandle = field(repr=False)
    wall: int
    mono: float
    deadline_wall: int
    deadline_mono: float
    last_wall: int
    last_mono: float
    local_guard: object = field(default=None, repr=False)
    closed: bool = False
    purpose: SurfacePurposeCredential | None = field(default=None, repr=False)

    def close(self):
        self.closed = True
        if self.purpose is not None:
            self.purpose.withdraw()
            self.purpose = None


def _cancelled():
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise asyncio.CancelledError


def _digest(message):
    return hashlib.sha256(message).hexdigest()


@dataclass(frozen=True, repr=False)
class IssuerManagementHandle:
    """Original in-process management only; clones/restarts confer no authority."""
    capture: IssuerOwnerCapture = field(repr=False)
    owner: object = field(repr=False)


class IssuerLifecycle:
    """Retained original RAM captures only; restart performs zero issuer requests."""
    def __init__(self, owner, journal, transport, *, wall=lambda: int(time.time()*1000),
            monotonic=time.monotonic):
        require(isinstance(owner, EnrolledIssuerOwner)
            and type(journal) is IssuerStageJournal
            and isinstance(transport, IssuerTransport), 'surface_issuer_owner_unavailable', 503)
        self.owner, self.journal, self.transport = owner, journal, transport
        self.wall, self.monotonic = wall, monotonic
        self._attempts = {}
        self._handle_owner = object()
        self.closed = False

    def close(self):
        """Synchronous unload/owner-stop fence, including outstanding late ACKs."""
        self.closed = True
        for attempt in self._attempts.values():
            attempt.close()

    def _validate(self, attempt, action, *, live):
        _cancelled()
        capture = attempt.capture
        if action == 'live' and attempt.local_guard is not None:
            require(attempt.local_guard() is None, 'surface_issuer_owner_unavailable', 503)
        capture.comparisons()
        validate = {'live': self.owner.validate_live, 'status': self.owner.validate_status,
            'withdraw': self.owner.validate_withdrawal}[action]
        # None-or-raise contract. A truthy boolean is not owner admission.
        require(validate(capture) is None, 'surface_issuer_owner_unavailable', 503)
        require(not self.closed, 'surface_issuer_owner_unavailable', 503)
        now, mono = self.wall(), self.monotonic()
        require(safe_integer(now, 1) and type(mono) in (int, float) and math.isfinite(mono)
            and now >= attempt.last_wall and mono >= attempt.last_mono,
            'surface_issuer_clock_quarantined', 503)
        attempt.last_wall, attempt.last_mono = now, mono
        if live:
            require(not attempt.closed and now < attempt.deadline_wall
                and mono < attempt.deadline_mono, 'surface_issuer_reply_expired')
            capture.expected.live(now, mono)
            capture.expected.live_operation(now)
        if action == 'live' and attempt.local_guard is not None:
            require(attempt.local_guard() is None, 'surface_issuer_owner_unavailable', 503)
        _cancelled()

    def _retained(self, handle):
        require(type(handle) is IssuerManagementHandle and handle.owner is self._handle_owner,
            'surface_issuer_original_capture_required', 503)
        capture = handle.capture
        identity = capture.journal_keys()[0]
        attempt = self._attempts.get(identity)
        require(attempt is not None and attempt.capture is capture and attempt.handle is handle,
            'surface_issuer_original_capture_required', 503)
        return attempt

    def _payload(self, capture, action, *, operation_id=None, challenge=None):
        expected = capture.expected
        payload = {'contract_version': 1, 'purpose': 'surface_push', 'action': action,
            'operation_id': operation_id or expected.operation_id,
            'delegation_id': expected.delegation_id, 'delegation_revision': 1,
            'key_thumbprint': expected.key_thumbprint}
        if action == 'issue':
            payload.update(challenge_id=challenge.challenge_id, nonce=challenge.nonce,
                scope_digest=expected.scope_digest)
        return payload

    async def _send(self, attempt, action, payload, guard, deadline):
        guard()
        remaining = min(10.0, deadline - self.monotonic())
        require(remaining > 0, 'surface_issuer_reply_expired')
        try:
            async with asyncio.timeout(remaining):
                return await self._signed_send(attempt, action, payload, guard, deadline)
        except TimeoutError:
            raise SurfacePushError('surface_issuer_outcome_unknown', 502) from None

    async def _signed_send(self, attempt, action, payload, guard, deadline):
        capture = attempt.capture
        path = PREFIX + action
        message = signing_bytes(path, payload)
        guard()
        signature = await self.owner.sign(capture, path, message, action=action)
        guard()
        envelope = {'payload': payload, 'signature': signature}
        # Always independently check real ES256 against the original public key.
        jwk, _ = capture.comparisons()
        verify_envelope(path, envelope, jwk)
        guard()
        reply = await self.transport.post_once(capture, action, envelope,
            guard=guard, deadline=deadline)
        guard()
        require(type(reply) is IssuerHTTPReply, 'surface_issuer_reply_invalid')
        return reply

    def begin(self, operation_id, *, local_guard=None):
        """Capture original admission synchronously, BEFORE caller scheduling."""
        _cancelled()
        require(local_guard is None or callable(local_guard), 'surface_issuer_owner_unavailable', 503)
        require(not self.closed, 'surface_issuer_owner_unavailable', 503)
        capture = self.owner.capture_live(operation_id)
        require(type(capture) is IssuerOwnerCapture
            and capture.expected.operation_id == operation_id,
            'surface_issuer_owner_capture_invalid', 503)
        identity, binding, operation = capture.journal_keys()
        now, mono = self.wall(), self.monotonic()
        capture.expected.live(now, mono)
        capture.expected.live_operation(now)
        end = min(now + 120000, operation_created_ms(operation_id) + 300000,
            capture.expected.original_grant_expires_ms)
        handle = IssuerManagementHandle(capture, self._handle_owner)
        attempt = _OriginalAttempt(capture, handle, now, mono, end, mono + (end-now)/1000, now, mono,
            local_guard=local_guard)
        require(identity not in self._attempts and len(self._attempts) < MAX_IDENTITIES,
            'surface_issuer_stage_consumed', 503)
        self._attempts[identity] = attempt
        try:
            self._validate(attempt, 'live', live=True)
        except BaseException:
            attempt.close()
            raise
        return handle

    async def acquire(self, handle):
        attempt = self._retained(handle)
        capture = attempt.capture
        identity, binding, operation = capture.journal_keys()
        now, mono, end = attempt.wall, attempt.mono, attempt.deadline_wall
        def guard():
            self._validate(attempt, 'live', live=True)
        challenge, issued = None, None
        try:
            guard()
            await self.journal.initialize()
            guard()
            payload = self._payload(capture, 'challenge')
            receipt = await self.journal.reserve_challenge(identity, binding, operation,
                _digest(signing_bytes(PREFIX + 'challenge', payload)), now=self.wall())
            guard()
            reply = await self._send(attempt, 'challenge', payload, guard, attempt.deadline_mono)
            challenge = challenge_winner(reply.body, capture.expected, status=reply.status,
                request_wall_ms=now, request_monotonic=mono,
                now_ms=self.wall(), monotonic=self.monotonic())
            # Tighten to the actual original challenge expiry. Never renew it.
            attempt.deadline_wall = min(end, challenge.expires_at_ms)
            attempt.deadline_mono = min(attempt.deadline_mono,
                mono + (challenge.expires_at_ms-now)/1000)
            guard()
            await self.journal.complete_challenge(receipt, accepted=True, now=self.wall())
            guard()
            payload = self._payload(capture, 'issue', challenge=challenge)
            await self.journal.reserve_issue(receipt,
                _digest(signing_bytes(PREFIX + 'issue', payload)), now=self.wall())
            guard()
            reply = await self._send(attempt, 'issue', payload, guard, attempt.deadline_mono)
            issued = issue_winner(reply.body, capture.expected, challenge=challenge,
                status=reply.status, now_ms=self.wall(), monotonic=self.monotonic())
            await self.journal.complete_issue(receipt, accepted=True, now=self.wall())
            guard()
            # The challenge window only gates issuance. Original grant anchors
            # remain unchanged for the RAM purpose, never reply/adoption time.
            purpose = SurfacePurposeCredential(issued.bearer, capture.origin, issued.capability_id,
                capture.expected.delegation_id, capture.expected.scope_digest,
                capture.binding_id, capture.device_binding, capture.owner_binding,
                capture.grant_binding, capture.source_binding, capture.policy_json,
                capture.expected.original_grant_wall_ms, capture.expected.original_grant_monotonic,
                current=lambda: self._purpose_current(attempt), wall=self.wall, monotonic=self.monotonic)
            attempt.purpose = purpose
            guard()
            require(purpose.is_current(), 'surface_issuer_owner_unavailable', 503)
            return purpose
        except BaseException:
            attempt.close()
            raise
        finally:
            # Secrets are returned only inside a RAM purpose, never kept for
            # retries/status or persisted. No error includes their values.
            challenge, issued = None, None

    def _purpose_current(self, attempt):
        try:
            require(not attempt.closed, 'surface_issuer_stage_withdrawn', 503)
            self._validate(attempt, 'live', live=False)
            attempt.capture.expected.live(self.wall(), self.monotonic())
            return True
        except BaseException:
            attempt.close()
            raise

    async def status(self, handle):
        attempt = self._retained(handle)
        capture = attempt.capture
        def guard():
            self._validate(attempt, 'status', live=False)
        guard()
        deadline = self.monotonic() + 10
        reply = await self._send(attempt, 'status', self._payload(capture, 'status'), guard, deadline)
        require(reply.status == 200, 'surface_issuer_reply_invalid')
        return status_unavailable(reply.body, capture.expected)

    def fence(self, handle):
        """Immediately retire the exact RAM attempt before any scheduling/await."""
        self._retained(handle).close()

    async def withdraw(self, handle, operation_id):
        attempt = self._retained(handle)
        capture = attempt.capture
        # Local fencing is synchronous and precedes cancellation, lock, signer
        # and storage awaits, including a caller already being cancelled.
        attempt.close()
        def guard_owner():
            self._validate(attempt, 'withdraw', live=False)
        guard_owner()
        now, mono = self.wall(), self.monotonic()
        created = operation_created_ms(operation_id)
        require(operation_id != capture.expected.operation_id
            and created <= now + 30000 and now < created + 300000,
            'surface_issuer_operation_clock_invalid')
        deadline_wall, deadline_mono = created + 300000, mono + (created + 300000-now)/1000
        def guard():
            guard_owner()
            require(self.wall() < deadline_wall and self.monotonic() < deadline_mono,
                'surface_issuer_reply_expired')
        payload = self._payload(capture, 'withdraw', operation_id=operation_id)
        identity, binding, operation = capture.journal_keys()
        await self.journal.terminal(identity, binding, operation,
            _digest(signing_bytes(PREFIX + 'withdraw', payload)), now=now)
        guard()
        reply = await self._send(attempt, 'withdraw', payload, guard, deadline_mono)
        require(reply.status == 200, 'surface_issuer_reply_invalid')
        # Withdrawal response echoes its fresh operation UUID, not issue UUID.
        from dataclasses import replace
        return withdrawal_ack(reply.body, replace(capture.expected, operation_id=operation_id))
