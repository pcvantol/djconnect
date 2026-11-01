"""API18ff private Source181 target DATA; never native permission or receipt recovery."""
from __future__ import annotations

import hashlib
import re

from . import host_wake_api_wire as receiving
from .direct_rich_wire import canonical, digest, require

VERSION = "djc-host-app-wake/1"
ROUTES = frozenset({"register", "wake", "status", "revoke"})
CAPABILITY_HEADER = "X-DJConnect-Host-Wake-Capability"
OPERATION_HEADER = "X-DJConnect-Host-Wake-Operation-ID"
CORRELATION_HEADER = "X-DJConnect-Host-Wake-Request-SHA256"


def request(route, value):
    require(type(route) is str and route in ROUTES)
    extra = ({"generation", "revision", "token_role", "target", "apns_environment", "apns_token"}
        if route == "register" else {"generation", "revision", "event"} if route == "wake" else set())
    receiving.exact(value, {"version", "purpose_id", "operation_id"} | extra)
    require(value["version"] == VERSION)
    for key in ("purpose_id", "operation_id"):
        receiving.identifier(value[key])
    if route in {"register", "wake"}:
        receiving.identifier(value["generation"])
        receiving.integer(value["revision"], 1, 256)
    if route == "register":
        receiving.target(value["target"])
        require(value["token_role"] == "host_app_wake" and type(value["apns_environment"]) is str
            and value["apns_environment"] in {"sandbox", "production"})
        require(type(value["apns_token"]) is str and re.fullmatch(r"(?:[a-f0-9]{2}){16,2048}", value["apns_token"]))
    elif route == "wake":
        require(value["event"] == "direct_rich_refresh")
    require(len(canonical(value)) <= 8192)
    return value


def request_hash(route, sent):
    request(route, sent)
    return digest(["DJC-HOST-WAKE-API-REQUEST-V1", "POST", receiving.PREFIX + route, sent])


def reply(route, status, value, sent, retained, private_purpose):
    """Join original child/request before exposing historical DATA to its owner.

    UNKNOWN has no registration permission. Terminal child state always wins
    over an old operation_state=registered; no boolean ready/native factory.
    """
    request(route, sent)
    receiving.original(retained)
    receiving.identifier(private_purpose)
    require(sent["purpose_id"] == private_purpose)
    if route in {"register", "wake"}:
        require(sent["generation"] == retained["generation"] and sent["revision"] == retained["revision"])
    if route == "register":
        require(sent["operation_id"] == retained["operation_id"]
            and canonical(sent["target"]) == canonical(retained["target"])
            and sent["apns_environment"] == retained["apns_environment"]
            and hashlib.sha256(bytes.fromhex(sent["apns_token"])).hexdigest() == retained["native_token_sha256"])
    require(type(status) is int and status in {200, 202})
    base = {"version", "purpose_id", "operation_id", "operation_state"}
    if status == 202:
        receiving.exact(value, base)
        require(value["operation_state"] == "unknown")
    else:
        receiving.exact(value, base | {"state", "generation", "revision", "expires_at_ms",
            "transport_expires_at_ms", "provider_status"})
        require(type(value["state"]) is str and value["state"] in {"registered", "unregistered", "withdrawn", "expired"})
        require(value["expires_at_ms"] == retained["original_wake_expires_at_ms"])
        receiving.integer(value["expires_at_ms"])
        receiving.integer(value["revision"], 0, 256)
        require((value["generation"] is None and value["revision"] == 0)
            or (value["generation"] == retained["generation"] and value["revision"] == retained["revision"]))
        require(value["state"] != "registered" or value["generation"] == retained["generation"])
        require(type(value["operation_state"]) is str and value["operation_state"] in {
            "unknown", "registered", "conflict", "expired", "provider_accepted", "provider_rejected", "not_sent"})
        if value["transport_expires_at_ms"] is not None:
            receiving.integer(value["transport_expires_at_ms"], retained["original_wake_issued_at_ms"],
                retained["original_wake_expires_at_ms"])
        if value["provider_status"] is not None:
            receiving.integer(value["provider_status"], 100, 599)
    require(value["version"] == VERSION and value["purpose_id"] == private_purpose
        and value["operation_id"] == sent["operation_id"])
    if route == "revoke":
        require(status == 200 and value["state"] == "withdrawn")
    return value
