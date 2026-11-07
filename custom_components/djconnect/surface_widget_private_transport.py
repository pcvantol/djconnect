"""Private WidgetKit transport selected by the original server-side owner."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import stat
import time

from .surface_issuer_owner import DNS_HOST, IssuerOwnerCapture
from .surface_issuer_transport import IssuerHTTPS
from .surface_issuer_wire import PREFIX, signing_bytes
from .surface_push_contract import SurfacePushError, require
from .surface_push_purpose import SurfacePurposeCredential

_REDEEM = "/v1/push/surface/enrollment/redeem"
_RELAY = {name: "/v1/push/surface/" + name for name in ("register", "revoke", "event", "status")}


@dataclass(frozen=True, repr=False)
class WidgetAccessBinding:
    origin: str
    generation: object
    current_generation: object = field(repr=False)
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)

    def validate(self):
        require(type(self.origin) is str and self.origin.startswith("https://")
            and DNS_HOST.fullmatch(self.origin.removeprefix("https://")) is not None,
            "surface_widget_origin_invalid", 503)
        require(self.generation is not None and self.current_generation() is self.generation,
            "surface_widget_access_changed", 503)
        require(all(type(value) is str and re.fullmatch(r"[!-~]{1,256}", value)
            for value in (self.client_id, self.client_secret)),
            "surface_widget_access_invalid", 503)


class PrivateWidgetHTTPS(IssuerHTTPS):
    """Bound to one server-selected origin and one Access credential generation."""

    def __init__(self, binding, *, monotonic=time.monotonic):
        super().__init__(monotonic=monotonic)
        require(type(binding) is WidgetAccessBinding, "surface_widget_access_invalid", 503)
        binding.validate()
        self._binding = binding

    def validate_origin(self, origin):
        require(origin == self._binding.origin, "surface_widget_origin_changed", 503)
        self._binding.validate()

    async def post_once(self, capture, action, envelope, *, guard, deadline):
        require(type(capture) is IssuerOwnerCapture,
            "surface_issuer_owner_capture_invalid", 503)
        capture.comparisons()
        require(type(action) is str and action in {"challenge", "issue", "status", "withdraw"},
            "surface_widget_operation_invalid")
        require(type(envelope) is dict and set(envelope) == {"payload", "signature"},
            "surface_issuer_wire_invalid")
        path = PREFIX + action
        signing_bytes(path, envelope["payload"])
        return await self._send(capture.origin, path, envelope, None, guard, deadline)

    async def redeem(self, capture, envelope, enrollment_bearer, *, guard, deadline):
        require(type(capture) is IssuerOwnerCapture,
            "surface_issuer_owner_capture_invalid", 503)
        capture.comparisons()
        require(type(enrollment_bearer) is str
            and re.fullmatch(r"djce_[A-Za-z0-9_-]{43}", enrollment_bearer),
            "surface_widget_enrollment_proof_invalid", 403)
        return await self._send(capture.origin, _REDEEM, envelope,
            enrollment_bearer, guard, deadline)

    async def relay(self, admission, action, body, *, deadline):
        require(type(action) is str and action in _RELAY, "surface_widget_operation_invalid")
        purpose = admission.purpose
        require(type(purpose) is SurfacePurposeCredential and purpose.private_transport is self,
            "surface_purpose_unavailable", 503)

        def guard():
            admission.validate()
            require(admission.purpose is purpose, "surface_widget_access_changed", 503)
            return purpose.authorize(action, body)

        bearer = guard()
        require(json.loads(purpose.policy_json)["token_role"] == "widget",
            "surface_widget_access_invalid", 503)
        return await self._send(purpose.origin, _RELAY[action], body, bearer, guard, deadline)

    async def _send(self, origin, path, body, bearer, guard, deadline):
        binding = self._binding

        def require_current():
            guard()
            require(self._binding is binding and origin == binding.origin,
                "surface_widget_origin_changed", 503)
            binding.validate()
            require(self.monotonic() < deadline, "surface_issuer_reply_expired", 503)

        require_current()
        headers = {"CF-Access-Client-Id": binding.client_id,
            "CF-Access-Client-Secret": binding.client_secret}
        if bearer is not None:
            headers["Authorization"] = "Bearer " + bearer
        result = await self._post(binding.origin, path, body, headers,
            guard=require_current, deadline=deadline)
        require_current()
        return result


ACCESS_FILE_ENV = "DJCONNECT_WIDGET_HA_DEV_ACCESS_FILE"
_WIDGET_ORIGIN = "https://widget-ha-dev.djconnect.dev"
_MAX_BYTES = 2048


def _unique_fields(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate credential field")
    return result


def load_widget_access_file(path: str) -> tuple[str, str, int]:
    """Run off the HA event loop. Never expose file data or parse errors."""
    try:
        if not Path(path).is_absolute():
            raise ValueError
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as credential_file:
            info = os.fstat(credential_file.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) not in (0o400, 0o600)
                or not 0 < info.st_size <= _MAX_BYTES
            ):
                raise ValueError
            raw = credential_file.read(_MAX_BYTES + 1)
        if len(raw) != info.st_size:
            raise ValueError
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)
        if type(document) is not dict or document.keys() != {
            "client_id", "client_secret", "expires_at_ms",
        }:
            raise ValueError
        client_id, client_secret = document["client_id"], document["client_secret"]
        expires_at_ms = document["expires_at_ms"]
        if type(expires_at_ms) is not int or not 0 < expires_at_ms <= 2**53 - 1:
            raise ValueError
        return client_id, client_secret, expires_at_ms
    except (OSError, ValueError, RecursionError):
        raise SurfacePushError("surface_widget_access_invalid", 503) from None


class WidgetAccessCustody:
    """One selected generation per HA service, with irreversible retirement."""

    def __init__(self, *, wall_ms=None, monotonic=time.monotonic):
        self._wall_ms = wall_ms or (lambda: time.time_ns() // 1_000_000)
        self._monotonic = monotonic
        self._generation = None
        self._sealed = False

    def bind(self, client_id, client_secret, expires_at_ms):
        if self._sealed:
            raise SurfacePushError("surface_widget_access_changed", 503)
        self._sealed = True
        remaining_ms = expires_at_ms - self._wall_ms()
        if remaining_ms <= 0:
            raise SurfacePushError("surface_widget_access_changed", 503)
        deadline = self._monotonic() + remaining_ms / 1000
        generation = self._generation = object()

        def current_generation():
            if self._wall_ms() >= expires_at_ms or self._monotonic() >= deadline:
                self.retire()
            return self._generation

        return PrivateWidgetHTTPS(
            WidgetAccessBinding(
                _WIDGET_ORIGIN, generation, current_generation, client_id, client_secret,
            ),
            monotonic=self._monotonic,
        )

    def retire(self):
        self._sealed = True
        self._generation = None
