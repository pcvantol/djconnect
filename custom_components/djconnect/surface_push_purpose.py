"""RAM-only admitted surface capability; no enrolment/key/config/bootstrap path.

Construction belongs exclusively to a separately qualified issuer adoption.
Neither paired client JSON nor an installation bearer can create this object.
Until such adoption is connected the relay is deliberately unavailable.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import re
import time
from typing import Callable
from urllib.parse import urlsplit

from .surface_push_contract import require
from .surface_push_wire import canonical, safe_integer

TOKEN = re.compile(r"djcs_[A-Za-z0-9_-]{43}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
POLICY = frozenset({"token_role", "platform", "apns_environment", "target", "activity_profile",
    "external_content_allowed", "original_grant_expires_at_ms", "max_operations", "max_events", "max_challenges"})


@dataclass(frozen=True, repr=False)
class SurfacePurposeCredential:
    # The issuer must supply immutable, already-validated operator scope plus
    # original pre-await anchors. This class does not establish human approval.
    bearer: str = field(repr=False)
    origin: str
    capability_id: str
    delegation_id: str
    scope_digest: str
    binding_id: str
    device_binding: str
    owner_binding: str
    grant_binding: str
    source_binding: str
    policy_json: str = field(repr=False)
    original_wall_ms: int
    original_monotonic: float
    current: Callable[[], bool] = field(repr=False)
    delegation_revision: int = 1
    wall: Callable[[], int] = field(default=lambda: int(time.time() * 1000), repr=False)
    monotonic: Callable[[], float] = field(default=time.monotonic, repr=False)
    _withdrawn: bool = field(default=False, init=False, repr=False)
    _event_attempts: int = field(default=0, init=False, repr=False)

    def withdraw(self):
        object.__setattr__(self, "_withdrawn", True)
        object.__setattr__(self, "bearer", "")

    def is_current(self):
        try:
            self.authorize("status", {key:getattr(self,key) for key in
                ("binding_id","device_binding","owner_binding")})
            return True
        except Exception:
            self.withdraw()
            return False

    def original_expiry_ms(self):
        import json
        require(self.is_current(), "surface_purpose_withdrawn", 403)
        return json.loads(self.policy_json)["original_grant_expires_at_ms"]

    def authorize(self, action, payload):
        """Consume only exact current scope, never return this object to a client."""
        import json
        try:
            require(not self._withdrawn and self.current() is True,
                "surface_purpose_withdrawn", 403)
            require(type(self.bearer) is str and TOKEN.fullmatch(self.bearer),
                "surface_purpose_invalid", 403)
            raw = base64.urlsafe_b64decode(self.bearer[5:] + "=")
            require(len(raw) == 32 and base64.urlsafe_b64encode(raw).decode().rstrip("=") == self.bearer[5:],
                "surface_purpose_invalid", 403)
            require(type(self.delegation_revision) is int and self.delegation_revision == 1,
                "surface_purpose_invalid", 403)
            require(all(type(v) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", v)
                for v in (self.capability_id, self.delegation_id)), "surface_purpose_invalid", 403)
            require(all(type(v) is str and HEX.fullmatch(v) for v in (self.scope_digest,
                self.binding_id, self.device_binding, self.owner_binding, self.grant_binding,
                self.source_binding)), "surface_purpose_invalid", 403)
            parsed = urlsplit(self.origin)
            require(parsed.scheme == "https" and bool(parsed.hostname) and parsed.path == ""
                and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                "surface_purpose_invalid", 403)
            policy = json.loads(self.policy_json)
            require(type(policy) is dict and set(policy) == POLICY
                and canonical(policy) == self.policy_json, "surface_purpose_invalid", 403)
            expires = policy["original_grant_expires_at_ms"]
            require(safe_integer(self.original_wall_ms, 1) and safe_integer(expires, 1)
                and self.original_wall_ms < expires <= self.original_wall_ms + 28800000
                and self.wall() < expires
                and self.monotonic() < self.original_monotonic + (expires-self.original_wall_ms)/1000,
                "surface_purpose_expired", 403)
            for key in ("binding_id", "device_binding", "owner_binding"):
                require(payload.get(key) == getattr(self, key), "surface_purpose_scope_mismatch", 403)
            require(type(action) is str and action in {"register", "revoke", "event", "status"},
                "surface_purpose_scope_mismatch", 403)
            if action == "register":
                require(all(payload.get(k) == policy[k] for k in
                    ("token_role", "platform", "apns_environment"))
                    and payload.get("expires_at_ms") == expires,
                    "surface_purpose_scope_mismatch", 403)
                target = payload.get("target")
                require(type(target) is dict and type(policy["target"]) is dict
                    and {k:v for k,v in target.items() if k not in {"instance_id", "activity_id"}}
                        == policy["target"], "surface_purpose_scope_mismatch", 403)
            if action == "event":
                from .surface_push_wire import COORDINATE
                require(set(payload)==COORDINATE|{"event"} and payload.get("event")=="widget_reload",
                    "surface_purpose_scope_mismatch",403)
            # Exact Activity external-content profiles are not admitted yet.
            # Widget signal-only use is the only current consumer path.
            require(policy["token_role"] == "widget" and policy["activity_profile"] is None
                and policy["external_content_allowed"] is False,
                "surface_activity_profile_pending", 409)
            return self.bearer
        except BaseException:
            # No resurrection after a failed current-scope or deadline check.
            self.withdraw()
            raise
