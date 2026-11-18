"""Private WidgetKit transport selected by the original server-side owner."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
import time

from .surface_issuer_owner import DNS_HOST, IssuerOwnerCapture
from .surface_issuer_transport import IssuerHTTPS
from .surface_issuer_wire import PREFIX, signing_bytes
from .surface_push_contract import require
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
