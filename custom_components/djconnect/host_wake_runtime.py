"""Original warm Core/API composition; no default native or clock supplier.

Public callers select no owner, credential, private API identity or replacement
deadline. Real native verification and registration remain actual API ACKs.
"""
import asyncio
from copy import deepcopy
from fractions import Fraction
import hashlib
import time
import uuid

from . import host_wake_api_wire as api
from . import host_wake_target_wire as target
from .direct_rich_wire import canonical, digest, require
from .host_wake_api import HostWakeApiChannel
from .host_wake_child_store import ChildMetadata
from .host_wake_proxy_wire import BODY_BYTES, COMMON, decode_json, decoded_base64, request_sha256, validate


class _OriginalAttestation:
    """Retain the actual supplied owner identity, never manufacture an owner."""
    def __init__(self, service):
        self.service = service
        self.owner = service.host_wake_original_attestor
        require(callable(self.owner), "rich_unavailable", 503)

    def __call__(self, child):
        service, owner = self.service, self.owner
        service._current()
        require(service.host_wake_original_attestor is owner
            and child.registry is service.host_wake_children, "rich_unavailable", 503)
        require(owner(child) is None, "rich_unavailable", 503)
        service._current()
        require(service.host_wake_original_attestor is owner, "rich_unavailable", 503)


def _response(child, operation, payload, state, **extra):
    reservation, metadata = child.reservation, child.metadata
    require(type(metadata) is ChildMetadata and metadata.expires_ms is not None,
        "rich_history_unknown", 404)
    value = {"success": True, "contract_version": 1,
        "profile_id": "djconnect-direct-rich-host-wake-v1",
        "operation_id": reservation.native_operation_id,
        "request_sha256": request_sha256(operation, payload),
        "purpose_id": reservation.parent.purpose_id, "surface": reservation.parent.surface,
        "generation": reservation.generation, "revision": 1,
        "original_wake_issued_at_ms": reservation.created_ms,
        "original_wake_expires_at_ms": metadata.expires_ms,
        "original_display_expires_at_ms": reservation.parent.expires_ms,
        "state": state, **extra}
    encoded = canonical(value)
    require(len(encoded) <= BODY_BYTES, "rich_unavailable", 503)
    return encoded


class _Exchange:
    @classmethod
    def from_broadcast(cls, attempt):
        from .host_wake_events import _BroadcastAttempt
        require(type(attempt) is _BroadcastAttempt, "rich_not_allowed", 403)
        attempt.check()
        registry, child = attempt.watch.registry, attempt.watch.child
        require(child.pending is None and child.initial_attempt is None, "rich_purpose_consumed", 409)
        value = cls.__new__(cls)
        value.registry, value.child, value.attempt = registry, child, attempt
        value.operation, value.payload, value.task = "wake", None, asyncio.current_task()
        value.entered_journal = False
        child.pending = value.task
        # Background event resource expiry is guarded outside child.current;
        # before any durable claim it must not withdraw the existing parent.
        value.task.add_done_callback(child._request_finished)
        try:
            value.current()
        except BaseException:
            value.abandon_unstarted()
            raise
        return value

    def abandon_unstarted(self):
        require(self.operation == "wake" and not self.entered_journal, "rich_not_allowed", 403)
        if self.child.pending is self.task and self.child.initial_attempt is None:
            self.child.pending = None

    def __init__(self, registry, attempt, operation, payload):
        self.registry, self.attempt, self.operation, self.payload = registry, attempt, operation, payload
        attempt.bind_parent(operation, payload)
        child = registry.children.get(payload["purpose_id"])
        require(child is not None and not child.closed, "rich_history_unknown", 404)
        # A competing request cannot retire the first original in-flight task.
        require(child.pending is None, "rich_purpose_consumed", 409)
        require(child.reservation.parent is attempt.parent.original
            and child.reservation.native_operation_id == payload["operation_id"]
            and type(child._owner_attestation) is _OriginalAttestation
            and child._owner_attestation.owner is registry.service.host_wake_original_attestor
            and child._credential is not None and child._private_purpose is not None,
            "rich_not_allowed", 403)
        self.child, self.task = child, asyncio.current_task()
        child.pending, child.initial_attempt = self.task, attempt
        attempt.dependents.add(child)
        self.task.add_done_callback(child._request_finished)
        try:
            self.current()
        except BaseException:
            self.fail()
            raise

    def current(self):
        self.child.current()
        require(self.child.pending is self.task and self.child.initial_attempt is
            (None if self.operation == "wake" else self.attempt),
            "rich_unavailable", 503)
        self.attempt.check()
        self._challenge_resources_current()

    def _challenge_resources_current(self):
        if self.operation == "native/complete":
            original = self.child._challenge_resource_start
            require(type(original) is tuple and len(original) == 2, "rich_not_allowed", 403)
            wall, mono = time.time(), time.monotonic()
            # Independent ORIGINAL Core resource ceiling, captured before the
            # challenge's first await. No API UTC -> local-clock conversion or
            # server nonce/native admission is inferred by passing this check.
            require(0 <= Fraction(wall) - Fraction(original[0]) < 30
                and 0 <= Fraction(mono) - Fraction(original[1]) < 30,
                "rich_not_allowed", 403)

    def storage_current(self):
        self.child.storage_current()
        self.attempt.storage_current(self.task)
        self._challenge_resources_current()
        return True

    def release(self):
        self.current()
        if self.task.cancelling():
            raise asyncio.CancelledError
        self.attempt.dependents.discard(self.child)
        self.child.initial_attempt, self.child.pending = None, None

    def fail(self):
        child = self.child
        port = child._withdrawal
        if child.pending is self.task:
            child.pending = None
        child.close()
        if port is not None and not port.used:
            try:
                port.schedule()
            except Exception:
                pass  # Consumed original negative port; no replacement/retry.

    async def begin(self, kind, sent, *, target_route=False):
        child = self.child
        self.current()
        require(child.metadata.consumed_attempts < child._role["max_operations"], "rich_capacity", 409)
        identity = (self.payload.get("challenge_id") if kind == "native_complete" else
            sent["operation_id"] if kind == "target_wake" else
            str(uuid.uuid4()) if kind in {"native_status", "target_status"} else kind)
        if kind == "target_wake":
            self.entered_journal = True  # Commit-then-error must never replay.
        claim = await self.registry.journal.begin(child.reservation,
            expected_revision=child.metadata.cas_revision, kind=kind,
            semantic_hash=digest(["DJC-HOST-WAKE-ONCE-V1", child.reservation.parent.purpose_id, kind, identity]),
            request_hash=(target.request_hash(self.operation, sent) if target_route else
                api.request_hash(self.operation, sent)), attempt_id=str(uuid.uuid4()),
            session_id=child.context.session_id, owner_id=child.context.owner,
            current=self.storage_current, maximum_wakes=child._role["max_reserved_sends"])
        self.current()
        child.metadata = ChildMetadata(child.metadata.original_hash, child.metadata.role_hash,
            child.metadata.expires_ms, claim.pending_phase, claim.pending_revision, claim.ordinal)
        return claim

    async def post(self, route, sent, *, capability=None):
        self.current()
        channel = HostWakeApiChannel(self.attempt)
        try:
            scope = {key: self.child._issuer_request[key] for key in api.SCOPE_HEADERS}
            status, raw = await channel.post(route, canonical(sent), scope, capability=capability)
            self.current()
            value = decode_json(raw)
            if status not in {200, 202}:
                api.error(status, value)
                require(False, "rich_unavailable", 503)
            return status, value
        finally:
            channel.close()

    async def finish(self, claim, state, value):
        child = self.child
        metadata = await self.registry.journal.finish(child.reservation, claim,
            destination=state, result_hash=digest(value), session_id=child.context.session_id,
            owner_id=child.context.owner, current=self.storage_current)
        self.current()
        require(metadata.phase == state and metadata.cas_revision == claim.pending_revision + 1,
            "rich_unavailable", 503)
        require(metadata.original_hash == digest(child._original)
            and metadata.role_hash == digest(child._role)
            and metadata.expires_ms == child._original["original_wake_expires_at_ms"]
            and metadata.consumed_attempts == claim.ordinal, "rich_unavailable", 503)
        child.metadata = metadata

    async def terminal(self, state):
        """Actual negative ACK closes locally before independent bookkeeping."""
        child, registry = self.child, self.registry
        session_id, owner_id = child.context.session_id, child.context.owner
        self.fail()
        child.metadata = await registry.journal.unknown(child.reservation,
            session_id=session_id, owner_id=owner_id,
            current=lambda: self.attempt.storage_current(self.task))
        self.attempt.check()
        return _response(child, self.operation, self.payload, state)

    async def native(self):
        child, operation, payload = self.child, self.operation, self.payload
        original_local_start = (self.attempt.wall, self.attempt.mono)
        sent = {"version": api.VERSION,
            **{key: child._issuer_request[key] for key in api.SCOPE_HEADERS}}
        if operation == "native/challenge":
            require(child.metadata.phase == "prepared" and getattr(child, "_challenge", None) is None,
                "rich_purpose_consumed", 409)
            sent["challenge_id"] = str(uuid.uuid4())
            kind = "native_challenge"
        else:
            challenge = getattr(child, "_challenge", None)
            require(type(challenge) is dict and payload["challenge_id"] == challenge["challenge_id"],
                "rich_not_allowed", 403)
            sent["challenge_id"] = challenge["challenge_id"]
            kind = "native_status" if operation == "native/status" else "native_complete"
            if kind == "native_complete":
                require(payload["native_proof"]["kind"] == child._role["native_proof_kind"],
                    "rich_not_allowed", 403)
                sent["native_proof"] = payload["native_proof"]
        claim = await self.begin(kind, sent)
        status, value = await self.post(operation, sent)
        require(status == 200, "rich_unavailable", 503)
        api.reply(operation, value, sent, child._original, child._role["native_proof_kind"],
            retained_challenge=getattr(child, "_challenge", None))
        state = value["state"]
        if state in {"withdrawn", "expired", "unknown"}:
            return await self.terminal(state)
        destination = ("challenge_known" if kind == "native_challenge" else
            "native_verified" if state == "native_verified" and child.metadata.phase == "verifying" else
            "native_verified" if state == "native_verified" and kind == "native_complete" else
            "verifying" if kind == "native_complete" else child.metadata.phase)
        await self.finish(claim, destination, value)
        extra = {}
        if kind == "native_challenge":
            extra = {key: deepcopy(value[key]) for key in ("original", "native_proof_kind", "challenge",
                "canonical_transcript_utf8", "client_data_sha256")}
            child._challenge = deepcopy(value["challenge"])
            child._challenge_resource_start = original_local_start
        elif state == "native_verified":
            # Retain the actual validated ACK, never a caller's ready boolean.
            child._native_receipt = deepcopy(value)
        body = _response(child, operation, payload, state, **extra)
        self.release()
        return body

    async def wake(self, operation_id):
        child = self.child
        self.current()
        sent = {"version": target.VERSION, "purpose_id": child._private_purpose,
            "operation_id": operation_id, "generation": child._original["generation"],
            "revision": child._original["revision"], "event": "direct_rich_refresh"}
        claim = await self.begin("target_wake", sent, target_route=True)
        status, value = await self.post("wake", sent, capability=child._credential)
        target.reply("wake", status, value, sent, child._original, child._private_purpose)
        require(status == 200 and value["state"] == "registered"
            and value["operation_state"] == "provider_accepted" and value["provider_status"] == 200,
            "rich_unavailable", 503)
        await self.finish(claim, "registered", value)
        self.release()

    async def registered(self):
        child, operation, payload = self.child, self.operation, self.payload
        sent = {"version": target.VERSION, "purpose_id": child._private_purpose,
            "operation_id": child.reservation.native_operation_id}
        if operation == "register":
            receipt = getattr(child, "_native_receipt", None)
            require(child.metadata.phase == "native_verified" and type(receipt) is dict
                and receipt["state"] == "native_verified"
                and receipt["challenge_id"] == payload["challenge_id"]
                and receipt["original_sha256"] == digest(child._original), "rich_not_allowed", 403)
            token = decoded_base64(payload["native_token_b64"], 16, 2048)
            # The original token binding owns disclosure as well as the ACK.
            # Reject replacement bytes before a journal claim or network IO.
            require(hashlib.sha256(token).hexdigest() == child._original["native_token_sha256"],
                "rich_not_allowed", 403)
            sent.update(generation=child._original["generation"], revision=child._original["revision"],
                token_role="host_app_wake", target=deepcopy(child._original["target"]),
                apns_environment=child._original["apns_environment"], apns_token=token.hex())
            kind = "target_register"
        else:
            require(child.metadata.phase == "registered", "rich_not_allowed", 403)
            kind = "target_status"
        target.request(operation, sent)
        claim = await self.begin(kind, sent, target_route=True)
        status, value = await self.post(operation, sent, capability=child._credential)
        target.reply(operation, status, value, sent, child._original, child._private_purpose)
        if status != 200 or value["state"] != "registered" or value["operation_state"] != "registered":
            return await self.terminal(value.get("state")
                if value.get("state") in {"withdrawn", "expired"} else "unknown")
        await self.finish(claim, "registered", value)
        body = _response(child, operation, payload, "registered")
        self.release()
        if operation == "register":
            from .host_wake_events import attach
            attach(child)
        return body


async def _manage(registry, attempt, operation, payload):
    common = {key: payload[key] for key in COMMON}
    management = registry.capture_management(attempt, common,
        operation="withdraw" if operation == "withdraw" else "status")
    child = management.child
    port, remote = child._withdrawal, None
    if operation == "withdraw":
        child.close()  # Negative fence BEFORE SQL or remote scheduling.
        if port is not None:
            if not port.used:
                remote = port.schedule()
            elif port.task is not None:
                remote = port.task  # Same original task; never restart its window.
    metadata = await management.run()
    child.metadata = metadata
    state = "unknown" if child.closed else "pending"
    if remote is not None:
        async def result():
            return await asyncio.shield(remote)  # Independent original negative custody.
        try:
            status, value = await attempt.wait(result)
            if status == 200:
                state = value["state"]
                child._withdrawal_result = state
        except asyncio.CancelledError:
            raise
        except Exception:
            state = "unknown"
    elif getattr(child, "_withdrawal_result", None) in {"withdrawn", "expired", "unknown"}:
        state = child._withdrawal_result
    return _response(child, operation, payload, state)


async def execute(attempt, operation, payload):
    validate(operation, payload)
    payload = deepcopy(payload)
    registry = attempt.service.host_wake_children
    if operation == "prepare":
        owner = _OriginalAttestation(registry.service)
        attempt.bind_parent(operation, payload)
        child = registry.capture(attempt, payload)
        return await child.prepare(attest_original=owner)
    if operation in {"status", "withdraw", "native/status"}:
        child = registry.children.get(payload["purpose_id"])
        if operation == "status" and child is not None and not child.closed:
            require(type(child.metadata) is ChildMetadata, "rich_purpose_consumed", 409)
        if (operation == "withdraw" or child is None or child.closed
                or (operation == "status" and child.metadata.phase != "registered")):
            return await _manage(registry, attempt, operation, payload)
    exchange = _Exchange(registry, attempt, operation, payload)
    try:
        return await (exchange.native() if operation.startswith("native/") else exchange.registered())
    except BaseException:
        exchange.fail()
        raise
