"""Widget first-key enrollment from the existing ordinary pair acknowledgement."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
import hashlib
import json
from pathlib import Path
import re
import time
import uuid
from weakref import WeakValueDictionary

from .const import CONF_HA_INSTALL_ID, VERSION
from .direct_rich_pair import capture_pair
from .direct_rich_wire import one_header
from .native_pair_retirement import NativePairRetirementJournal
from .native_widget_consent import read_widget_consent, write_widget_consent
from .persistence import PERSISTENCE_SERVICE_KEY, PersistenceError, PersistenceService
from .surface_push_contract import SurfacePushError, require
from .surface_push_wire import canonical

KEY = "native_pair_enrollment"
_AUDIENCE = "djc-native-push-ha-dev/1"
_BINDINGS = ("pairing_generation", "pair_binding", "owner_binding", "device_binding",
             "core_key_thumbprint")
_CHALLENGE = ("contract_version", "api_audience", "operation_id", "api_installation_id",
              "install_credential_id", "challenge_id", "challenge_nonce", "expires_at_ms",
              "expected_key_revision")
_IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,128}")


def _matches(pattern, value):
    return type(value) is str and re.fullmatch(pattern, value) is not None


def _read_entry(path, entry_id, coordinates):
    try:
        with Path(path).open("rb") as stream:
            document = json.load(stream)
        rows = [row for row in document["data"]["entries"] if row["entry_id"] == entry_id]
        if len(rows) != 1 or rows[0]["domain"] != "djconnect":
            return False
        row = rows[0]
        config = {**row["data"], **row["options"]}
        return tuple(config.get(key) for key in
                     ("device_id", "client_type", "device_token", CONF_HA_INSTALL_ID)) == coordinates[:4]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


async def _durable_pair(pair):
    """Recheck the loaded pairing against native config and the pair journal."""
    require(pair.current(), "native_pair_changed", 403)
    registration = pair.registration
    acknowledgement = pair.acknowledgement
    entry = pair.entry
    hass = pair.hass
    path = hass.config.path(".storage", "core.config_entries")
    saved = await hass.async_add_executor_job(
        _read_entry, path, entry.entry_id, pair.coordinates)
    require(pair.current() and saved, "native_install_credential_unavailable", 503)

    def read(tx):
        identity = tx.fetchone("SELECT instance_id FROM djconnect_surface_pair_store WHERE singleton=1")
        row = tx.fetchone(
            "SELECT entry_id,auth_generation,state FROM djconnect_surface_pairs WHERE binding=?",
            (registration.binding,),
        )
        return bool(identity and identity[0] == acknowledgement.instance_id
                    and row and tuple(row) == (entry.entry_id, acknowledgement.auth_generation, "recorded"))

    recorded = await pair.persistence.async_in_transaction(read)
    require(recorded and pair.current(), "native_pair_changed", 403)


def _install_store(pair):
    from homeassistant.helpers.storage import Store

    return Store(pair.hass, 1, "djconnect_native_install." + pair.entry.entry_id,
                 private=True, atomic_writes=True)


def _read_install(path, key, binding):
    try:
        with Path(path).open("rb") as stream:
            document = json.load(stream)
        if document["key"] != key or document["version"] != 1:
            return None
        data = document["data"]
        if set(data) != {*binding, "install_token", "credential_id"} or any(
                data[name] != value for name, value in binding.items()):
            return None
        token = data["install_token"]
        credential_id = data["credential_id"]
        if _matches(r"djci_[A-Za-z0-9_-]{1,256}", token) and _matches(_IDENTIFIER, credential_id):
            return token, credential_id
        return None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


class ConsentFence:
    """Identity held by an in-flight operation until a consent write supersedes it."""


@dataclass(repr=False)
class EnrollmentOperation:
    pair: object
    authority: object
    consent_current: object
    spki: bytes
    challenge: dict
    bindings: dict
    statement: bytes
    digest: str
    credential: tuple
    recoverable: bool = False

    def receipt(self, body):
        expected = {key: self.challenge[key] for key in
                    ("contract_version", "operation_id", "api_installation_id",
                     "install_credential_id", "expires_at_ms")}
        expected.update(pairing_generation=self.bindings["pairing_generation"],
                        core_key_thumbprint=self.bindings["core_key_thumbprint"],
                        key_revision=1, transcript_sha256=self.digest, state="registered")
        require(set(body) == {*expected, "registry_generation"}
                and canonical({key: body[key] for key in expected}) == canonical(expected)
                and _matches(_IDENTIFIER, body["registry_generation"]), "native_pair_receipt_invalid", 502)
        return body

    def sign(self, statement):
        signature = self.authority.sign(statement)
        require(type(signature) is bytes and len(signature) == 64, "native_key_unavailable", 503)
        return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


class NativePairEnrollment:
    """One pending WidgetKit operation per device under an explicit server selection.

    The selection supplies the current owner and consent, opaque binding
    derivation and Core signing custody. It is never selected by the app.
    """

    def __init__(self, hass, transport, selection, *, publisher=None, wall=time.time, monotonic=time.monotonic):
        self.hass = hass
        self.transport = transport
        self.selection = selection
        self.publisher = publisher
        self.wall = wall
        self.monotonic = monotonic
        self.pending = {}
        self.bootstrap_pending = set()
        self.consent_writes = set()
        self.consent_fences = WeakValueDictionary()
        self._retirement_unsubscribe = None
        self._retirement_polling = False

    def start_retirement_delivery(self):
        """Resume this selected service's pending deliveries after HA setup."""
        if self._retirement_unsubscribe is not None:
            return
        from homeassistant.helpers.event import async_track_time_interval

        self._retirement_unsubscribe = async_track_time_interval(
            self.hass, self.poll_retirements, timedelta(seconds=30))

    def stop_retirement_delivery(self):
        unsubscribe, self._retirement_unsubscribe = self._retirement_unsubscribe, None
        if unsubscribe is not None:
            unsubscribe()

    async def poll_retirements(self, _now):
        subscription = self._retirement_unsubscribe
        if self._retirement_polling or subscription is None:
            return
        self._retirement_polling = True
        try:
            persistence = self.hass.data.get("djconnect", {}).get(PERSISTENCE_SERVICE_KEY)
            if not isinstance(persistence, PersistenceService):
                return
            deadline = self.monotonic() + 10
            transport = self.transport
            publisher = self.publisher

            def guard():
                domain = self.hass.data.get("djconnect", {})
                require(not self.hass.is_stopping and domain.get(KEY) is self
                        and self._retirement_unsubscribe is subscription
                        and self.transport is transport and self.publisher is publisher and self.monotonic() < deadline
                        and persistence.readiness.ready and domain.get(PERSISTENCE_SERVICE_KEY) is persistence,
                        "native_retirement_authority_changed", 503)

            journal = NativePairRetirementJournal(persistence)
            if publisher is not None:
                try:
                    await journal.deliver_withdrawals(publisher, transport.origin, guard=guard, deadline=deadline)
                except (SurfacePushError, PersistenceError):
                    pass
            await journal.deliver(transport, guard=guard, deadline=deadline)
        except (SurfacePushError, PersistenceError):
            # The exact event remains on disk for the next scheduled attempt.
            pass
        finally:
            self._retirement_polling = False

    def install_binding(self, pair):
        return {"origin": self.transport.origin, "installation": pair.coordinates[3],
                "pair_store": pair.acknowledgement.instance_id,
                "pair_generation": pair.acknowledgement.auth_generation}

    async def read_selected_install(self, pair, store, binding):
        token = await pair.hass.async_add_executor_job(_read_install, store.path, store.key, binding)
        require(pair.current(), "native_pair_changed", 403)
        return token

    async def credential(self, pair):
        await _durable_pair(pair)
        token = await self.read_selected_install(pair, _install_store(pair), self.install_binding(pair))
        require(token is not None, "native_install_credential_unavailable", 503)
        return token

    async def bootstrap(self, headers, *, device_id, client_type):
        """Provision an origin-bound credential after the ordinary pair settles."""
        pair = capture_pair(self.hass, headers, device_id=device_id, client_type=client_type)
        require(client_type == "ios", "native_platform_unavailable", 503)
        deadline = self.monotonic() + 10

        def guard():
            require(self.hass.data.get("djconnect", {}).get(KEY) is self
                    and self.monotonic() < deadline and pair.current(),
                    "native_pair_changed", 403)

        install_id = pair.coordinates[3]
        require(install_id not in self.bootstrap_pending and len(self.bootstrap_pending) < 32,
                "native_install_bootstrap_pending", 409)
        self.bootstrap_pending.add(install_id)
        try:
            await _durable_pair(pair)
            guard()
            binding = self.install_binding(pair)
            store = _install_store(pair)
            existing = await self.read_selected_install(pair, store, binding)
            guard()
            if existing is not None:
                return {"contract_version": 1, "ready": True}
            identity = {"ha_install_id": install_id, "integration": "djconnect_hacs",
                        "integration_version": VERSION, "device_id": device_id, "client_type": client_type}
            require(self.publisher is not None, "native_publisher_unavailable", 503)
            await self.publisher.publish("bind", {
                "contract_version": 1, "ha_install_id": install_id, "device_id": device_id,
            }, guard=guard, deadline=deadline)
            await _durable_pair(pair)
            guard()
            issuer = await self.transport.post_bootstrap_proof(identity, guard=guard, deadline=deadline)
            guard()
            proof = issuer.body.get("bootstrap_proof")
            expiry = issuer.body.get("expires_at")
            require(issuer.body.get("ok") is True and type(proof) is str and 1 <= len(proof) <= 4096
                    and proof.isascii() and proof == proof.strip() and type(expiry) is str,
                    "native_install_bootstrap_rejected", 502)
            try:
                expires = datetime.fromisoformat(expiry)
                if expires.tzinfo is None:
                    raise ValueError
                remaining = expires.timestamp() - self.wall()
            except (ValueError, OverflowError):
                raise SurfacePushError("native_install_bootstrap_rejected", 502) from None
            require(remaining > 0, "native_install_bootstrap_rejected", 502)
            exchange_deadline = min(deadline, self.monotonic() + remaining)

            def exchange_guard():
                guard()
                require(self.monotonic() < exchange_deadline, "native_install_bootstrap_expired", 403)

            await _durable_pair(pair)
            exchange_guard()
            reply = await self.transport.post_install_token({**identity, "bootstrap_proof": proof},
                guard=exchange_guard, deadline=exchange_deadline)
            guard()
            token = reply.body.get("install_token")
            credential_id = reply.body.get("id")
            require(reply.body.get("success") is True and _matches(_IDENTIFIER, credential_id)
                    and _matches(r"djci_[A-Za-z0-9_-]{1,256}", token),
                    "native_install_bootstrap_rejected", 502)
            await store.async_save({**binding, "install_token": token, "credential_id": credential_id})
            guard()
            persisted = await self.read_selected_install(pair, store, binding)
            guard()
            require(persisted == (token, credential_id), "native_install_credential_unavailable", 503)
            return {"contract_version": 1, "ready": True}
        finally:
            self.bootstrap_pending.remove(install_id)

    async def consent(self, headers, *, enabled=None, operation_id=None, expected_revision=None):
        device_id = one_header(headers, "X-DJConnect-Device-ID")
        client_type = one_header(headers, "X-DJConnect-Client-Type")
        require(client_type == "ios", "native_platform_unavailable", 503)
        pair = capture_pair(self.hass, headers, device_id=device_id, client_type=client_type)
        await _durable_pair(pair)
        require(self.hass.data.get("djconnect", {}).get(KEY) is self, "native_pair_changed", 403)
        if operation_id is None:
            result = await read_widget_consent(pair)
            require(self.hass.data.get("djconnect", {}).get(KEY) is self, "native_pair_changed", 403)
            return result.wire()

        binding = pair.registration.binding
        require(binding not in self.consent_writes, "native_widget_consent_pending", 409)
        self.consent_writes.add(binding)
        self.consent_fences.pop(binding, None)
        try:
            result = await write_widget_consent(
                pair, enabled=enabled, operation_id=operation_id, expected_revision=expected_revision)
            require(self.hass.data.get("djconnect", {}).get(KEY) is self, "native_pair_changed", 403)
            return {**result.wire(), "operation_id": operation_id}
        finally:
            self.consent_writes.remove(binding)

    def guard(self, pair, authority, deadline, consent_current):
        require(self.hass.data.get("djconnect", {}).get(KEY) is self
                and self.monotonic() < deadline and pair.current()
                and consent_current() and authority.current() and pair.current(), "native_pair_changed", 403)

    async def post_current(self, action, body, token, credential_id, bindings, *,
                           guard, deadline, operation_expiry=None, nonce_expiry=None):
        guard()
        now_ms = int(self.wall() * 1000)
        expiry = now_ms + min(10_000, int((deadline - self.monotonic()) * 1000))
        if operation_expiry is not None:
            expiry = min(expiry, operation_expiry)
        if nonce_expiry is not None:
            expiry = min(expiry, nonce_expiry)
        require(now_ms < expiry, "native_pair_changed", 403)
        currentness = {
            "contract_version": 1, "api_audience": _AUDIENCE, "action": action,
            "decision_id": str(uuid.uuid4()), "install_credential_id": credential_id,
            "operation_id": body["operation_id"], **bindings,
            "request_sha256": hashlib.sha256(canonical(body).encode("utf-8")).hexdigest(),
            "issued_at_ms": now_ms, "expires_at_ms": expiry,
            "operation_expires_at_ms": operation_expiry,
        }
        return await self.transport.post_first_key(
            action, body, token, currentness=currentness, guard=guard,
            deadline=min(deadline, self.monotonic() + (expiry - now_ms) / 1000))

    async def challenge(self, headers, *, device_id, client_type):
        pair = capture_pair(self.hass, headers, device_id=device_id, client_type=client_type)
        require(client_type == "ios", "native_platform_unavailable", 503)
        now = self.monotonic()
        for key, pending in tuple(self.pending.items()):
            if pending[0] <= now or (pending[1] is not None and not pending[1].consent_current()):
                del self.pending[key]
        require(device_id not in self.pending and len(self.pending) < 32,
                "native_pair_operation_pending", 409)
        deadline = now + 120
        reservation = (deadline, None)
        self.pending[device_id] = reservation
        try:
            token, credential_id = await self.credential(pair)
            require(self.hass.data.get("djconnect", {}).get(KEY) is self
                    and self.monotonic() < deadline, "native_pair_changed", 403)
            binding = pair.registration.binding
            fence = self.consent_fences.setdefault(binding, ConsentFence())

            def consent_current():
                return binding not in self.consent_writes and self.consent_fences.get(binding) is fence

            consent = await read_widget_consent(pair)
            require(consent.enabled and consent_current(), "native_widget_consent_required", 403)
            authority = await self.selection.capture(pair, channel="widgetkit")
            self.guard(pair, authority, deadline, consent_current)
            spki = authority.public_key_spki
            require(type(spki) is bytes and 1 <= len(spki) <= 160, "native_key_unavailable", 503)
            bindings = dict(authority.bindings)
            require(set(bindings) == set(_BINDINGS[:-1])
                    and _matches(_IDENTIFIER, bindings["pairing_generation"])
                    and all(_matches(r"[0-9a-f]{64}", bindings[key]) for key in _BINDINGS[1:-1]),
                    "native_pair_binding_invalid", 503)
            bindings["core_key_thumbprint"] = hashlib.sha256(spki).hexdigest()
            operation = str(uuid.uuid4())
            request = {"contract_version": 1, "operation_id": operation, **bindings}
            guard = partial(self.guard, pair, authority, deadline, consent_current)
            journal = NativePairRetirementJournal(pair.persistence)

            def current():
                try:
                    guard()
                except SurfacePushError:
                    return False
                return True

            require(self.publisher is not None, "native_publisher_unavailable", 503)
            publication = {**request, "install_credential_id": credential_id,
                           "request_expires_at_ms": int(self.wall() * 1000) + 120_000}
            await journal.stage(pair, self.transport.origin, {
                **publication, "api_audience": _AUDIENCE, "event_id": operation,
            }, consent, self.publisher.origin, current)
            guard()
            await self.publisher.publish("operation", {**publication, "consent_revision": consent.revision},
                                         guard=guard, deadline=deadline)
            guard()
            reply = await self.post_current("challenge", request, token, credential_id, bindings,
                                            guard=guard, deadline=deadline)
            guard()
            challenge = reply.body
            now_ms = int(self.wall() * 1000)
            expiry = challenge.get("expires_at_ms")
            require(set(challenge) == set(_CHALLENGE)
                    and type(challenge["contract_version"]) is int and challenge["contract_version"] == 1
                    and challenge["api_audience"] == _AUDIENCE and challenge["operation_id"] == operation
                    and challenge["install_credential_id"] == credential_id
                    and type(challenge["expected_key_revision"]) is int and challenge["expected_key_revision"] == 0
                    and all(_matches(_IDENTIFIER, challenge[key]) for key in _CHALLENGE[3:6])
                    and _matches(r"[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]", challenge["challenge_nonce"])
                    and type(expiry) is int and now_ms < expiry <= now_ms + 120_000,
                    "native_pair_challenge_invalid", 502)
            require(self.pending.get(device_id) is reservation, "native_pair_changed", 403)
            deadline = min(deadline, self.monotonic() + (expiry - now_ms) / 1000)
            statement = canonical([
                "djc-native-pair-witness/1", _AUDIENCE, "POST", "/v1/push/native/key/register",
                "widget-first-key", *(challenge[key] for key in _CHALLENGE[2:]),
                *(bindings[key] for key in _BINDINGS),
            ]).encode()
            digest = hashlib.sha256(statement).hexdigest()
            credential = (hashlib.sha256(token.encode("ascii")).digest(), credential_id)
            self.pending[device_id] = (deadline, EnrollmentOperation(
                pair, authority, consent_current, spki, challenge, bindings, statement, digest, credential))
            return {**challenge, **bindings, "client_data_hash_b64":
                    base64.b64encode(bytes.fromhex(digest)).decode("ascii")}
        finally:
            if self.pending.get(device_id) is reservation:
                del self.pending[device_id]

    def original(self, headers, device_id, client_type, operation_id, *, recoverable):
        caller = capture_pair(self.hass, headers, device_id=device_id, client_type=client_type)
        deadline, original = self.pending.get(device_id, (0, None))
        require(original is not None and original.recoverable is recoverable
                and caller.registration is original.pair.registration
                and caller.acknowledgement is original.pair.acknowledgement
                and original.challenge["operation_id"] == operation_id,
                "native_pair_operation_unavailable", 409)
        self.guard(original.pair, original.authority, deadline, original.consent_current)
        return deadline, original

    async def original_credential(self, original):
        token, credential_id = await self.credential(original.pair)
        credential = (hashlib.sha256(token.encode("ascii")).digest(), credential_id)
        require(credential == original.credential, "native_install_credential_changed", 403)
        return token

    async def register(self, headers, *, device_id, client_type, operation_id, apple_proof):
        deadline, original = self.original(headers, device_id, client_type, operation_id, recoverable=False)
        _validate_attestation(apple_proof)
        reservation = (deadline, None)
        self.pending[device_id] = reservation
        try:
            token = await self.original_credential(original)
            guard = partial(self.guard, original.pair, original.authority, deadline, original.consent_current)
            guard()
            body = {**original.challenge, **original.bindings, "apple_proof": apple_proof,
                    "core_public_key_spki_b64": base64.b64encode(original.spki).decode("ascii"),
                    "core_signature_b64url": original.sign(original.statement)}
            try:
                reply = await self.post_current(
                    "register", body, token, original.challenge["install_credential_id"], original.bindings,
                    guard=guard, deadline=deadline, operation_expiry=original.challenge["expires_at_ms"])
                guard()
                receipt = original.receipt(reply.body)
                original.recoverable = True
                self.pending[device_id] = (deadline, original)
                return receipt
            except (asyncio.CancelledError, SurfacePushError) as error:
                if isinstance(error, asyncio.CancelledError) or error.status == 502:
                    try:
                        guard()
                    except SurfacePushError:
                        pass
                    else:
                        original.recoverable = True
                        self.pending[device_id] = (deadline, original)
                raise
        finally:
            if self.pending.get(device_id) is reservation:
                del self.pending[device_id]

    async def status(self, headers, *, device_id, client_type, operation_id):
        deadline, original = self.original(headers, device_id, client_type, operation_id, recoverable=True)
        reservation = (deadline, None)
        self.pending[device_id] = reservation
        try:
            token = await self.original_credential(original)
            guard = partial(self.guard, original.pair, original.authority, deadline, original.consent_current)
            lookup = {key: original.challenge[key] for key in
                      ("contract_version", "operation_id", "api_installation_id")}
            lookup["transcript_sha256"] = original.digest
            reply = await self.post_current(
                "status/challenge", lookup, token, original.challenge["install_credential_id"], original.bindings,
                guard=guard, deadline=deadline, operation_expiry=original.challenge["expires_at_ms"])
            guard()
            status_challenge = reply.body
            expected = {**lookup, **{key: original.challenge[key] for key in
                        ("api_audience", "install_credential_id", "expires_at_ms")},
                        **{key: original.bindings[key] for key in ("pairing_generation", "core_key_thumbprint")}}
            nonce_fields = ("status_nonce_id", "status_nonce", "status_nonce_expires_at_ms")
            now_ms = int(self.wall() * 1000)
            expires = status_challenge.get("status_nonce_expires_at_ms")
            require(set(status_challenge) == {*expected, *nonce_fields}
                    and canonical({key: status_challenge[key] for key in expected}) == canonical(expected)
                    and _matches(_IDENTIFIER, status_challenge["status_nonce_id"])
                    and _matches(r"[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]", status_challenge["status_nonce"])
                    and type(expires) is int and now_ms < expires <= min(
                        now_ms + 15_000, original.challenge["expires_at_ms"]),
                    "native_pair_status_invalid", 502)
            status_deadline = min(deadline, self.monotonic() + (expires - now_ms) / 1000)
            status_guard = partial(self.guard, original.pair, original.authority, status_deadline, original.consent_current)
            keys = ("operation_id", "api_installation_id", "install_credential_id", "pairing_generation",
                    "core_key_thumbprint", "transcript_sha256", "expires_at_ms", *nonce_fields)
            statement = canonical([
                "djc-native-first-key-status/1", _AUDIENCE, "POST", "/v1/push/native/key/status",
                "widget-first-key", *(status_challenge[key] for key in keys),
            ]).encode()
            token = await self.original_credential(original)
            status_guard()
            body = {**status_challenge, "core_signature_b64url": original.sign(statement)}
            reply = await self.post_current(
                "status", body, token, original.challenge["install_credential_id"], original.bindings,
                guard=status_guard, deadline=status_deadline,
                operation_expiry=original.challenge["expires_at_ms"], nonce_expiry=expires)
            status_guard()
            return original.receipt(reply.body)
        finally:
            if self.pending.get(device_id) is reservation:
                if self.monotonic() < deadline and original.pair.current():
                    self.pending[device_id] = (deadline, original)
                else:
                    del self.pending[device_id]


def _validate_attestation(proof):
    require(type(proof) is dict and set(proof) == {"kind", "key_id_b64", "proof_b64"}
            and proof["kind"] == "attestation", "native_apple_proof_invalid")
    for key, maximum in (("key_id_b64", 32), ("proof_b64", 16_384)):
        value = proof[key]
        require(type(value) is str and 0 < len(value) <= ((maximum + 2) // 3) * 4,
                "native_apple_proof_invalid")
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError:
            decoded = b""
        require((len(decoded) == 32 if key == "key_id_b64" else 0 < len(decoded) <= maximum)
                and base64.b64encode(decoded).decode("ascii") == value, "native_apple_proof_invalid")


def retirement_delivery_service(hass):
    selected = hass.data.get("djconnect", {}).get(KEY)
    return selected if type(selected) is NativePairEnrollment else None
