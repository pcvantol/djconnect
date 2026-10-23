"""Pinned API surface-push/1 wire; pure validation grants no relay authority.

API source a45fef1, wire SHA256 d4f255431b4429b724455e347841e992aef8f639a2b7799dfb510752cdb834b7.
Activity payload admission and purpose-credential issuance remain separate.
"""
from __future__ import annotations

import hashlib
import json
import re

from .surface_push_contract import IDENTIFIER, SurfacePushError, require
from .transport_operations import operation_created_ms

SAFE_INTEGER = 9007199254740991
COORDINATE = frozenset({"contract_version", "registration_id", "generation", "revision",
    "operation_id", "binding_id", "device_binding", "owner_binding"})
REGISTER = frozenset({"expires_at_ms", "token_role", "platform", "apns_environment",
    "target", "apns_token"})
ACK = frozenset({"contract_version", "success", "registration_id", "generation", "revision",
    "operation_id", "state", "operation_state", "replayed", "expires_at_ms",
    "current_revision", "provider_status"})


def safe_integer(value, minimum=0):
    return type(value) is int and minimum <= value <= SAFE_INTEGER


def _json_domain(value, depth=0):
    # The currently admitted widget/registration domain contains no floating
    # point values. Rich Activity profiles must separately settle number encoding.
    require(depth <= 16, "surface_wire_invalid")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(-SAFE_INTEGER <= value <= SAFE_INTEGER, "surface_wire_invalid")
    elif type(value) is str:
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeError:
            raise SurfacePushError("surface_wire_invalid") from None
    elif type(value) is list:
        for item in value:
            _json_domain(item, depth + 1)
    elif type(value) is dict:
        # All closed wire field names are ASCII. This also fixes key-order
        # equivalence with JavaScript's UTF-16 ordering for this admitted domain.
        require(all(type(k) is str and k.isascii() for k in value), "surface_wire_invalid")
        for item in value.values():
            _json_domain(item, depth + 1)
    else:
        raise SurfacePushError("surface_wire_invalid")


def canonical(value):
    _json_domain(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def request_digest(kind, payload):
    require(type(kind) is str and kind in {"register", "revoke", "event", "status"}, "surface_wire_invalid")
    return hashlib.sha256(canonical([kind, payload]).encode()).hexdigest()


def validate_coordinate(payload, *, now_ms, historical_status=False):
    require(type(payload) is dict and COORDINATE <= payload.keys(), "surface_wire_invalid")
    require(type(payload["contract_version"]) is int and payload["contract_version"] == 1,
        "unsupported_surface_push_version")
    require(all(type(payload[k]) is str and IDENTIFIER.fullmatch(payload[k])
        for k in ("registration_id", "generation")), "surface_wire_invalid")
    require(safe_integer(payload["revision"], 1) and payload["revision"] < SAFE_INTEGER,
        "surface_wire_invalid")
    for key in ("binding_id", "device_binding", "owner_binding"):
        require(type(payload[key]) is str and re.fullmatch("[a-f0-9]{64}", payload[key]),
            "surface_wire_invalid")
    try:
        created = operation_created_ms(payload["operation_id"])
    except Exception:
        raise SurfacePushError("invalid_operation_id") from None
    require(safe_integer(now_ms), "invalid_surface_clock")
    if not historical_status:
        require(created <= now_ms + 30000, "operation_clock_unqualified", 409)
        require(now_ms < created + 300000, "operation_expired", 409)


def operation_body(kind, coordinate, *, now_ms, registration=None):
    """Exact versioned fields, never append installation or personal identities."""
    require(type(kind) is str and kind in {"register", "revoke", "event", "status"}, "surface_wire_invalid")
    require(type(coordinate) is dict and set(coordinate) == COORDINATE, "surface_wire_invalid")
    validate_coordinate(coordinate, now_ms=now_ms, historical_status=kind == "status")
    body = dict(coordinate)
    if kind == "event":
        require(registration is None, "surface_wire_invalid")
        body["event"] = "widget_reload"
    if kind == "register":
        require(type(registration) is dict and set(registration) == REGISTER,
            "surface_wire_invalid")
        require(safe_integer(registration["expires_at_ms"], 1)
            and now_ms < registration["expires_at_ms"] <= now_ms + 28800000,
            "invalid_surface_expiry")
        role = registration["token_role"]
        require(type(role) is str and role in {"widget", "live_activity_update", "live_activity_start"},
            "surface_wire_invalid")
        require(type(registration["platform"]) is str and registration["platform"] in
            {"ios", "ipados", "maccatalyst", "macos", "watchos", "visionos"}, "surface_wire_invalid")
        require(type(registration["apns_environment"]) is str and
            registration["apns_environment"] in {"sandbox", "production"}, "surface_wire_invalid")
        require(type(registration["apns_token"]) is str and re.fullmatch(
            "(?:[a-f0-9]{2}){16,2048}", registration["apns_token"]), "surface_wire_invalid")
        target = registration["target"]
        fields = {"instance_id", "app_bundle_id"} | (
            {"extension_bundle_id", "widget_kind"} if role == "widget" else
            {"activity_id", "attributes_type"} if role == "live_activity_update" else {"attributes_type"})
        require(type(target) is dict and set(target) == fields, "surface_wire_invalid")
        for key, item in target.items():
            pattern = r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+" if key.endswith("bundle_id") else IDENTIFIER
            require(type(item) is str and len(item) <= 200 and re.fullmatch(pattern, item),
                "surface_wire_invalid")
        body.update(registration)
    else:
        require(registration is None, "surface_wire_invalid")
    # Native target/role/token validation belongs to the immutable admission
    # contract; the relay must additionally match its enrolled purpose policy.
    require(len(canonical(body).encode()) <= 16384, "surface_wire_oversized", 413)
    return body


def acknowledged(value, original, *, original_kind, original_expiry_ms):
    """Only the exact original operation/current revision can acknowledge success.

    A status response is checked as its original register/revoke/event kind;
    HTTP200, replayed or a historical registered outcome alone grants nothing.
    """
    require(type(value) is dict and set(value) == ACK, "surface_ack_invalid", 502)
    require(type(value["contract_version"]) is int and value["contract_version"] == 1
        and type(value["success"]) is bool and type(value["replayed"]) is bool,
        "surface_ack_invalid", 502)
    require(type(original_kind) is str and original_kind in {"register", "revoke", "event"}
        and safe_integer(original_expiry_ms, 1), "surface_ack_invalid", 502)
    for key in ("registration_id", "generation", "revision", "operation_id"):
        require(type(value[key]) is type(original[key]) and value[key] == original[key],
            "surface_ack_mismatch", 502)
    require(safe_integer(value["expires_at_ms"])
        and (value["current_revision"] is None or safe_integer(value["current_revision"], 1))
        and (value["provider_status"] is None or
            (type(value["provider_status"]) is int and 100 <= value["provider_status"] <= 599)),
        "surface_ack_invalid", 502)
    require(type(value["state"]) is str
        and value["state"] in {"unknown", "registered", "revoked", "expired", "withdrawn"}
        and type(value["operation_state"]) is str
        and value["operation_state"] in {"unknown", "registered", "revoked", "conflict",
            "provider_accepted", "provider_rejected", "not_sent"}, "surface_ack_invalid", 502)
    exact = (type(value["current_revision"]) is int
        and value["current_revision"] == original["revision"])
    if original_kind == "revoke":
        accepted = (value["state"] == value["operation_state"] == "revoked"
            and value["expires_at_ms"] in (0, original_expiry_ms)
            and value["provider_status"] is None)
    else:
        outcome = "registered" if original_kind == "register" else "provider_accepted"
        accepted = (value["state"] == "registered" and value["operation_state"] == outcome
            and value["expires_at_ms"] == original_expiry_ms
            and value["provider_status"] == (None if original_kind == "register" else 200))
    return value["success"] is True and exact and accepted
