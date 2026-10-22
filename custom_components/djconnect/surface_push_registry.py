"""One bounded owner for native surface registration, not an APNs token store.

The existing durable operation journal fences remote registration effects. Only
opaque target metadata and limited background credentials survive in RAM. The
relay owns encryption/APNs and must acknowledge the exact CAS coordinates.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
import hashlib
import hmac
import secrets
from typing import Callable

from .surface_push_contract import RegistrationIntent, SurfacePushError, require
from .surface_push_wire import acknowledged, operation_body
from .surface_push_purpose import SurfacePurposeCredential

MAX_REGISTRATIONS = 64
MAX_OWNER_REGISTRATIONS = 16
GRANT_SECONDS = 8 * 60 * 60
RELAY_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class SurfaceAdmission:
    owner: str
    device: str
    binding: str
    session_id: str = field(repr=False)
    current: Callable[[], bool] = field(repr=False)
    projection: Callable[[], dict] = field(repr=False)
    purpose: object = field(default=None, repr=False)
    runtime: object = field(default=None, repr=False)
    broadcast: object = field(default=None, repr=False)

    def is_current(self):
        try:
            return (self.current() is True and type(self.purpose) is SurfacePurposeCredential
                and self.purpose.is_current())
        except Exception:
            return False

    def validate(self):
        require(self.is_current(), "surface_authority_changed", 403)


@dataclass
class SurfaceRegistration:
    registration_id: str
    generation: str
    revision: int
    key: str = field(repr=False)
    admission: SurfaceAdmission = field(repr=False)
    metadata: dict = field(repr=False)
    expires_ms: int
    read_secret: str = field(repr=False)
    phase: str = "pending"
    last_error: str | None = None
    mutation_pending: bool = False
    retire_callback: object = field(default=None, repr=False)

    def coordinate(self):
        return {
            "registration_id": self.registration_id,
            "generation": self.generation,
            "revision": self.revision,
        }

    def live(self, now_ms):
        live = (self.phase == "registered" and not self.mutation_pending
            and now_ms < self.expires_ms and self.admission.is_current())
        if not live and self.phase == "registered" and not self.mutation_pending:
            self.phase = "expired" if now_ms >= self.expires_ms else "withdrawn"
            self.read_secret = ""
        return live

    def receipt(self, now_ms):
        state = self.phase
        if now_ms >= self.expires_ms:
            state = "expired"
        elif not self.admission.is_current():
            state = "withdrawn"
        return {
            **self.coordinate(),
            "state": state,
            "expires_at_ms": self.expires_ms,
            "token_role": self.metadata["token_role"],
            "platform": self.metadata["platform"],
            "last_error": self.last_error,
            "cache_policy": "private,no-store",
        }


class SurfacePushRegistry:
    def __init__(self, journal, relay):
        self.journal, self.relay = journal, relay
        self._entries: dict[str, SurfaceRegistration] = {}
        self._by_target: dict[str, str] = {}
        self._operation_results: dict[str, tuple[str, int, int]] = {}
        self._lock = asyncio.Lock()
        self.closed = False

    @staticmethod
    def _target(admission, metadata):
        # The public paired request cannot choose an owner, installation binding
        # or another Session. Roles and Session grants never overwrite each other.
        raw = "\0".join(
            (
                admission.owner,
                admission.device,
                admission.binding,
                admission.session_id,
                admission.purpose.delegation_id,
                admission.purpose.scope_digest,
                metadata["token_role"],
                metadata["target"]["instance_id"],
            )
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def _require_open(self):
        require(not self.closed, "surface_registry_unavailable", 503)

    def _collect(self):
        now = self.journal.now_ms()
        for identifier, row in list(self._entries.items()):
            if now >= row.expires_ms:
                # No Broadcast callback is required to retire a stopped/idle
                # owner's expired watch before admitting another registration.
                self._latch_mutation(row,"expired")
                self._entries.pop(identifier)
                if self._by_target.get(row.key) == identifier:
                    self._by_target.pop(row.key, None)
        # Operation receipts have their original journal lifetime, not a new TTL.
        for identifier, (_, _, until) in list(self._operation_results.items()):
            if now >= until:
                self._operation_results.pop(identifier, None)

    @staticmethod
    def _latch_mutation(row, phase=None):
        row.mutation_pending = True
        row.read_secret = ""
        if phase is not None:
            row.phase = phase
        retire,row.retire_callback = row.retire_callback,None
        if retire is not None:
            retire()

    def _original_dispatch(self, admission, row, coordinate, phase):
        return replace(admission,current=lambda:(not self.closed
            and self._entries.get(row.registration_id) is row and row.coordinate()==coordinate
            and row.phase==phase and not row.mutation_pending
            and self.journal.now_ms()<row.expires_ms and admission.is_current()))

    async def _send(self, action, request, admission):
        self._require_open()
        admission.validate()
        task = asyncio.current_task()
        if task is not None and task.cancelling():
            raise asyncio.CancelledError
        # Include registry shutdown in the HTTP adapter's own pre/post-await
        # authority fence, without persisting or forwarding paired headers or app bearer.
        guarded = replace(admission, current=lambda: not self.closed and admission.is_current())
        return await self.relay(action, request, guarded)

    async def _terminal(self, key, phase, **fields):
        try:
            return await self.journal.transition(key, phase, **fields)
        finally:
            self.journal.release(key)

    async def register(self, intent: RegistrationIntent, admission: SurfaceAdmission):
        self._require_open()
        admission.validate()
        metadata = intent.metadata()
        require(metadata["session_id"] == admission.session_id, "surface_session_changed", 409)
        operation_id = metadata["operation_id"]
        key = hashlib.sha256(operation_id.encode()).hexdigest()
        target = self._target(admission, metadata)
        rotating = None
        prior = self._entries.get(self._by_target.get(target,""))
        if (prior is not None and metadata["expected_registration"]==prior.coordinate()
                and key not in self.journal._state["records"]):
            self.journal._validate_time(operation_id)
            require(prior.phase=="registered" and prior.live(self.journal.now_ms()),
                "surface_registration_not_current",409)
            self._latch_mutation(prior)
            rotating = prior
        async with self._lock:
            self._require_open()
            self._collect()
            admission.validate()
            key, operation, fresh = await self.journal.reserve(
                owner=admission.owner,
                device=admission.device,
                binding=admission.binding,
                identifier=operation_id,
                epoch=self.journal.epoch,
                operation="push/surface/register",
                digest=hashlib.sha256((intent.fingerprint+"\0"+admission.purpose.scope_digest).encode()).hexdigest(),
            )
            if not fresh:
                record = self._operation_results.get(operation_id)
                row = self._entries.get(record[0]) if record else None
                self._require_open()
                admission.validate()
                response = {
                    "success": bool(operation["phase"] == "confirmed" and row is not None
                        and record[1] == row.revision and row.admission.purpose is admission.purpose
                        and row.live(self.journal.now_ms())),
                    "replayed": True,
                    "operation": operation,
                    "registration": (row.receipt(self.journal.now_ms())
                        if row is not None and record[1] == row.revision else None),
                }
                # Recover the same RAM credential after a lost response, only for
                # this original accepted revision. Replay never rotates or renews.
                if response["success"]:
                    self._include_background_read(response, row)
                return response
            row = None
            try:
                self._require_open()
                admission.validate()
                existing = self._entries.get(self._by_target.get(target, ""))
                expected = metadata["expected_registration"]
                require(
                    (existing is None and expected is None)
                    or (existing is not None and expected == existing.coordinate()),
                    "surface_registration_conflict",
                    409,
                )
                if existing is not None:
                    require(
                        existing.phase == "registered" and existing.admission.is_current()
                        and (not existing.mutation_pending or existing is rotating)
                        and self.journal.now_ms()<existing.expires_ms,
                        "surface_registration_not_current",
                        409,
                    )
                require(
                    existing is not None
                    or (
                        len(self._entries) < MAX_REGISTRATIONS
                        and sum(
                            r.admission.owner == admission.owner for r in self._entries.values()
                        )
                        < MAX_OWNER_REGISTRATIONS
                    ),
                    "surface_registration_capacity",
                    429,
                )
                row = SurfaceRegistration(
                    existing.registration_id if existing else "surface-" + secrets.token_hex(16),
                    existing.generation if existing else secrets.token_hex(16),
                    existing.revision + 1 if existing else 1,
                    target,
                    admission,
                    metadata,
                    existing.expires_ms if existing else admission.purpose.original_expiry_ms(),
                    "djcsurface_" + secrets.token_urlsafe(32),
                )
                self._entries[row.registration_id] = row
                self._by_target[target] = row.registration_id
                self._operation_results[operation_id] = (
                    row.registration_id,
                    row.revision,
                    operation["expires_at_ms"],
                )
                await self.journal.transition(key, "sent_unknown")
                self._require_open()
                admission.validate()
            except BaseException:
                if row is not None:
                    row.phase = "withdrawn"
                    row.read_secret = ""
                # No network call occurred. Leave the durable reservation fenced
                # even if the journal itself failed while recording rejection.
                try:
                    await self.journal.transition(
                        key,
                        "rejected",
                        response_status=409,
                        error="surface_registration_not_sent",
                    )
                finally:
                    self.journal.release(key)
                raise
        request = {}
        try:
            coordinate = {"contract_version":1, **row.coordinate(), "operation_id":operation_id,
                "binding_id":admission.binding,"device_binding":admission.device,"owner_binding":admission.owner}
            registration = {k:metadata[k] for k in ("token_role","platform","apns_environment","target")}
            request = operation_body("register",coordinate,now_ms=self.journal.now_ms(),
                registration={**registration,"expires_at_ms":row.expires_ms,"apns_token":intent.apns_token})
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            result = await asyncio.wait_for(
                self._send("register", request, self._original_dispatch(
                    admission,row,row.coordinate(),"pending")), RELAY_TIMEOUT_SECONDS
            )
        except asyncio.CancelledError:
            if row.phase == "pending":
                row.phase = "unknown"
            row.read_secret = ""
            self.journal.release(key)
            raise
        except Exception:
            result = {"success": False, "error": "surface_relay_outcome_unknown"}
        finally:
            # No native token is copied into the registry or durable journal.
            request.pop("apns_token", None)
        async with self._lock:
            current = self._entries.get(row.registration_id)
            if (
                current is not row
                or row.phase != "pending"
                or not admission.is_current()
                or self.closed
                or self.journal.now_ms() >= row.expires_ms
                or self.journal.now_ms() >= operation["expires_at_ms"]
            ):
                if row.phase == "pending":
                    row.phase = "withdrawn"
                row.read_secret = ""
                if self.journal.now_ms() < operation["expires_at_ms"]:
                    await self._terminal(key, "unknown", error="surface_authority_changed")
                else:
                    self.journal.release(key)
                raise SurfacePushError("surface_authority_changed", 403)
            matched = self._acknowledged(result, request, "register", row.expires_ms)
            if not matched:
                row.phase = "unknown"
                row.read_secret = ""
                row.last_error = "surface_relay_outcome_unknown"
                operation = await self._terminal(key, "unknown", error=row.last_error)
                return {
                    "success": False,
                    "replayed": False,
                    "operation": operation,
                    "registration": row.receipt(self.journal.now_ms()),
                }
            try:
                operation = await self._terminal(key, "confirmed", response_status=200)
                admission.validate()
                require(
                    not self.closed and self.journal.now_ms() < row.expires_ms,
                    "surface_registration_not_current",
                    409,
                )
            except BaseException:
                row.phase = "withdrawn"
                row.read_secret = ""
                raise
            row.phase = "registered"
            response = {
                "success": True,
                "replayed": False,
                "operation": operation,
                "registration": row.receipt(self.journal.now_ms()),
            }
            self._include_background_read(response, row)
            return response

    @staticmethod
    def _include_background_read(response, row):
        if row.metadata["consent"]["background_read"]:
            response["background_read"] = {
                "credential": row.read_secret,
                "expires_at_ms": row.expires_ms,
                "registration_id": row.registration_id,
                "scope": "exact_original_surface_read_only",
                "cache_policy": "private,no-store",
            }

    def read(self, registration_id, credential):
        self._require_open()
        require(
            type(registration_id) is str and type(credential) is str,
            "surface_read_unauthorized",
            401,
        )
        row = self._entries.get(registration_id)
        require(
            row is not None and hmac.compare_digest(row.read_secret, credential),
            "surface_read_unauthorized",
            401,
        )
        require(
            row.metadata["consent"]["background_read"] and row.live(self.journal.now_ms()),
            "surface_read_withdrawn",
            403,
        )
        frame = row.admission.projection()
        require(row.live(self.journal.now_ms()), "surface_read_withdrawn", 403)
        return {
            "success": True,
            "contract_version": 1,
            "registration": row.receipt(self.journal.now_ms()),
            "passive_session": frame,
            "cache_policy": "private,no-store",
        }

    def status(self, admission, registration_id):
        self._require_open()
        admission.validate()
        row = self._entries.get(registration_id)
        require(
            row is not None
            and row.admission.owner == admission.owner
            and row.admission.device == admission.device
            and row.admission.binding == admission.binding
            and row.admission.session_id == admission.session_id
            and row.admission.purpose is admission.purpose,
            "surface_registration_unavailable",
            404,
        )
        return {
            "success": True,
            "contract_version": 1,
            "registration": row.receipt(self.journal.now_ms()),
        }

    async def revoke(self, admission, expected, *, operation_id, digest):
        self._require_open()
        admission.validate()
        # An authenticated original revoke latches before waiting for either
        # registry/journal lock. A queued send-child must see this withdrawal.
        original = self._entries.get(expected.get("registration_id")) if type(expected) is dict else None
        require(original is not None and original.coordinate()==expected
            and (original.admission.owner,original.admission.device,original.admission.binding,
                original.admission.session_id,original.admission.purpose)
                == (admission.owner,admission.device,admission.binding,admission.session_id,admission.purpose)
            and original.admission.purpose is admission.purpose,"surface_registration_conflict",409)
        self.journal._validate_time(operation_id)
        if self.journal._key(operation_id) not in self.journal._state["records"]:
            self._latch_mutation(original,"revoked")
        async with self._lock:
            self._require_open()
            row = self._entries.get(expected["registration_id"])
            require(
                row is not None
                and row.coordinate() == expected
                and row.admission.owner == admission.owner
                and row.admission.device == admission.device
                and row.admission.binding == admission.binding
                and row.admission.session_id == admission.session_id
            and row.admission.purpose is admission.purpose,
                "surface_registration_conflict",
                409,
            )
            self.journal._validate_time(operation_id)
            if self.journal._key(operation_id) not in self.journal._state["records"]:
                self._latch_mutation(row,"revoked")
            key, operation, fresh = await self.journal.reserve(
                owner=admission.owner,
                device=admission.device,
                binding=admission.binding,
                identifier=operation_id,
                epoch=self.journal.epoch,
                operation="push/surface/revoke",
                digest=digest,
            )
            if not fresh:
                self._require_open()
                admission.validate()
                return {
                    "success": operation["phase"] == "confirmed",
                    "replayed": True,
                    "operation": operation,
                    "registration": row.receipt(self.journal.now_ms()),
                }
            try:
                self._require_open()
                admission.validate()
                # Local read access is terminal before the remote await; old register
                # replies cannot re-enable it. The relay must tombstone this CAS first.
                row.phase = "revoked"
                row.read_secret = ""
                await self.journal.transition(key, "sent_unknown")
                self._require_open()
                admission.validate()
            except BaseException:
                self.journal.release(key)
                raise
        try:
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            result = await asyncio.wait_for(
                self._send(
                    "revoke",
                    operation_body("revoke", {
                        "contract_version":1, **row.coordinate(), "operation_id":operation_id,
                        "binding_id":admission.binding,"device_binding":admission.device,
                        "owner_binding":admission.owner,
                    }, now_ms=self.journal.now_ms()),
                    admission,
                ),
                RELAY_TIMEOUT_SECONDS,
            )
        except asyncio.CancelledError:
            self.journal.release(key)
            raise
        except Exception:
            result = {"success": False}
        async with self._lock:
            matched = self._acknowledged(result, {
                **row.coordinate(), "operation_id": operation_id,
            }, "revoke", row.expires_ms)
            operation = await self._terminal(
                key,
                "confirmed" if matched else "unknown",
                response_status=200 if matched else None,
                error=None if matched else "surface_relay_outcome_unknown",
            )
            self._require_open()
            admission.validate()
            return {
                "success": matched,
                "replayed": False,
                "operation": operation,
                "registration": row.receipt(self.journal.now_ms()),
            }

    async def signal_widget(self, admission, expected, *, operation_id):
        """One original internal widget signal, never content or a retry loop.

        No public event route invokes this. A future issuer-bound producer must
        capture an original semantic change and reuse its operation ID; polling
        and transport reconnect must not manufacture fresh events.
        """
        import json
        self._require_open()
        admission.validate()
        async with self._lock:
            self._collect()
            row = self._entries.get(expected.get("registration_id")) if type(expected) is dict else None
            require(row is not None and row.coordinate()==expected
                and row.admission.purpose is admission.purpose
                and (row.admission.owner,row.admission.device,row.admission.binding,row.admission.session_id)
                    == (admission.owner,admission.device,admission.binding,admission.session_id)
                and row.metadata["token_role"]=="widget" and row.live(self.journal.now_ms()),
                "surface_registration_not_current",409)
            request = operation_body("event",{"contract_version":1,**row.coordinate(),
                "operation_id":operation_id,"binding_id":admission.binding,
                "device_binding":admission.device,"owner_binding":admission.owner},
                now_ms=self.journal.now_ms())
            key,operation,fresh = await self.journal.reserve(owner=admission.owner,
                device=admission.device,binding=admission.binding,identifier=operation_id,
                epoch=self.journal.epoch,operation="push/surface/event",
                digest=hashlib.sha256(canonical_event(request,admission.purpose.scope_digest).encode()).hexdigest())
            if not fresh:
                admission.validate()
                return {"success":operation["phase"]=="confirmed" and row.live(self.journal.now_ms()),
                    "replayed":True,"operation":operation,"registration":row.receipt(self.journal.now_ms())}
            try:
                # Conservatively count original attempts, including unknown
                # outcomes. Never restore a local event budget after failure.
                count = getattr(admission.purpose,"_event_attempts",0)
                maximum = json.loads(admission.purpose.policy_json)["max_events"]
                require(type(maximum) is int and 1<=maximum<=1000 and count<maximum,
                    "surface_event_budget_exhausted",429)
                object.__setattr__(admission.purpose,"_event_attempts",count+1)
                admission.validate()
                await self.journal.transition(key,"sent_unknown")
                admission.validate()
                require(row.live(self.journal.now_ms()) and row.coordinate()==expected,
                    "surface_registration_not_current",409)
            except BaseException:
                try:
                    await self.journal.transition(key,"rejected",response_status=409,error="surface_event_not_sent")
                finally:
                    self.journal.release(key)
                raise
        try:
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            result = await asyncio.wait_for(self._send("event",request,self._original_dispatch(
                admission,row,expected,"registered")),RELAY_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            self.journal.release(key)
            raise
        except Exception:
            result = {}
        async with self._lock:
            current = (not self.closed and self._entries.get(row.registration_id) is row
                and row.coordinate()==expected and row.live(self.journal.now_ms())
                and admission.is_current() and self.journal.now_ms()<operation["expires_at_ms"])
            matched = current and self._acknowledged(result,request,"event",row.expires_ms)
            if self.journal.now_ms()>=operation["expires_at_ms"]:
                self.journal.release(key)
                raise SurfacePushError("surface_event_outcome_unknown",409)
            operation = await self._terminal(key,"confirmed" if matched else "unknown",
                response_status=200 if matched else None,
                **({} if matched else {"error":"surface_event_outcome_unknown"}))
            # A durable completion await can itself overlap withdrawal/rotation.
            matched = bool(matched and not self.closed and self._entries.get(row.registration_id) is row
                and row.coordinate()==expected and row.live(self.journal.now_ms()) and admission.is_current())
            return {"success":matched,"replayed":False,"provider_accepted":matched,
                "operation":operation,"registration":row.receipt(self.journal.now_ms())}

    @staticmethod
    def _acknowledged(result, request, kind, original_expiry):
        try:
            return acknowledged(result, request, original_kind=kind,
                original_expiry_ms=original_expiry)
        except SurfacePushError:
            # A malformed/mismatched 2xx response is a terminal unknown effect,
            # never a usable read credential or a reason to resend the mutation.
            return False

    async def close(self):
        self.closed = True
        for row in self._entries.values():
            row.phase = "withdrawn"
            row.read_secret = ""
            if type(row.admission.purpose) is SurfacePurposeCredential:
                row.admission.purpose.withdraw()
        self._entries.clear()
        self._by_target.clear()
        self._operation_results.clear()


def canonical_event(request,scope_digest):
    from .surface_push_wire import canonical
    return canonical(["widget_reload",scope_digest,request])
