"""Private seven-port DATA: API03323cd kinds, original51f3028/first033 vectors.

No reply creates an original parent, role, clock qualification or native right.
The owning service must retain its actual original tuple across every await.
"""
from __future__ import annotations

import hashlib
import re

from .direct_rich_wire import HASH, IDENTIFIER, SAFE, canonical, digest, domain, original_uuid, require
from .host_wake_proxy_wire import BODY_BYTES, PROOF_KINDS, decoded_base64

PREFIX = "/v1/push/host-app-wake/"
ROUTES = frozenset({"authorization/resolve", "issuer/issue", "issuer/status",
    "issuer/withdraw", "native/challenge", "native/complete", "native/status"})
SCOPE_HEADERS = {"authorization_id": "X-DJConnect-Host-Wake-Authorization-ID",
    "core_purpose_id": "X-DJConnect-Host-Wake-Core-Purpose-ID",
    "issuer_operation_id": "X-DJConnect-Host-Wake-Issuer-Operation-ID"}
VERSION = "djc-host-app-wake-receiving/1"
NATIVE = "djc-host-app-wake-native/1"
DOMAIN = b"DJC-HOST-APP-WAKE-TARGET-REGISTER-V1\n"
BINDINGS = {"paired_subject_binding_sha256", "owner_binding", "device_binding", "source_binding"}
POLICY = {"selected_ha_origin_sha256", "identity_policy_sha256", "deployment_policy_sha256"}
TIMES = {"original_wake_issued_at_ms", "original_wake_expires_at_ms", "original_display_expires_at_ms"}
BASE_REPLY = {"version", "authorization_id", "issuer_operation_id", "core_purpose_id",
    "request_sha256", "generation", "revision", "state"} | TIMES
ERRORS = {
    400: {"host_wake_invalid"},
    401: {"host_wake_core_auth", "host_wake_operator_hmac_required", "auth_required"},
    403: {"host_wake_principal_scope", "host_wake_native_authority", "host_wake_header_body_scope",
        "host_wake_original_scope", "host_wake_original_native_token", "host_wake_native_proof_rejected"},
    404: {"host_wake_receiving_route", "host_wake_operator_route", "host_wake_history_unknown"},
    409: {"host_wake_native_policy_consumed_or_capacity", "host_wake_intent_consumed", "host_wake_intent_capacity_or_authority",
        "host_wake_authorization_consumed_or_capacity", "host_wake_issuer_consumed_or_capacity",
        "host_wake_issuer_consumed", "host_wake_native_job_consumed_or_capacity", "host_wake_native_job_consumed",
        "host_wake_native_job_expired", "host_wake_transport_expired", "host_wake_body_timeout", "host_wake_cancelled"},
    413: {"host_wake_size"}, 415: {"host_wake_media"},
    503: {"host_wake_native_status_unavailable", "host_wake_native_receipt_unavailable",
        "host_wake_receiving_unavailable", "host_wake_authorization_unavailable",
        "host_wake_native_enrollment_unavailable", "host_wake_native_policy_unavailable",
        "host_wake_native_attestation_unavailable", "host_wake_native_deployment_mismatch"},
}


def exact(value, keys):
    require(type(value) is dict and value.keys() == keys)
    domain(value)


def identifier(value):
    require(type(value) is str and IDENTIFIER.fullmatch(value))


def integer(value, minimum=0, maximum=SAFE):
    require(type(value) is int and minimum <= value <= maximum)


def hashes(value, keys):
    for key in keys:
        require(type(value[key]) is str and HASH.fullmatch(value[key]))


def target(value):
    exact(value, {"host_bundle_id", "installation_id"})
    identifier(value["installation_id"])
    bundle = value["host_bundle_id"]
    require(type(bundle) is str and len(bundle) <= 200
        and re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", bundle))


def original(value):
    exact(value, {"version", "core_purpose_id", "operation_id", "generation", "revision", "token_role",
        "target", "platform", "apns_environment", "native_key_id_b64", "native_token_sha256"} | BINDINGS | POLICY | TIMES)
    require(value["version"] == NATIVE and value["token_role"] == "host_app_wake")
    identifier(value["core_purpose_id"])
    identifier(value["generation"])
    require(original_uuid(value["operation_id"]))
    integer(value["revision"], 1, 256)
    target(value["target"])
    require(type(value["platform"]) is str and value["platform"] in {"ios", "ipados"})
    require(type(value["apns_environment"]) is str and value["apns_environment"] in {"sandbox", "production"})
    decoded_base64(value["native_key_id_b64"], 1, 1024)  # Structural DATA, not enrolled identity.
    hashes(value, BINDINGS | POLICY | {"native_token_sha256"})
    issued, expires, display = (value[k] for k in ("original_wake_issued_at_ms",
        "original_wake_expires_at_ms", "original_display_expires_at_ms"))
    integer(issued)
    integer(expires, issued + 1, min(SAFE, issued + 28800000))
    integer(display, expires)
    return value


def challenge(value, retained):
    exact(value, {"challenge_id", "nonce_b64url", "captured_at_ms", "expires_at_ms"})
    require(original_uuid(value["challenge_id"]))
    nonce = value["nonce_b64url"]
    require(type(nonce) is str and re.fullmatch(r"[A-Za-z0-9_-]{43}", nonce))
    decoded_base64(nonce.replace("-", "+").replace("_", "/") + "=", 32, 32)
    integer(value["captured_at_ms"], retained["original_wake_issued_at_ms"])
    integer(value["expires_at_ms"], value["captured_at_ms"] + 1,
        min(value["captured_at_ms"] + 30000, retained["original_wake_expires_at_ms"]))
    return value


def request(route, value):
    require(type(route) is str and route in ROUTES)
    if route == "authorization/resolve":
        exact(value, {"version", "scope"})
        scope = value["scope"]
        exact(scope, BINDINGS | {"target", "platform", "apns_environment", "native_key_id_b64"})
        hashes(scope, BINDINGS)
        target(scope["target"])
        require(type(scope["platform"]) is str and scope["platform"] in {"ios", "ipados"})
        require(type(scope["apns_environment"]) is str and scope["apns_environment"] in {"sandbox", "production"})
        decoded_base64(scope["native_key_id_b64"], 32, 32)
    else:
        extra = ({"original"} if route == "issuer/issue" else
            {"challenge_id", "native_proof"} if route == "native/complete" else
            {"challenge_id"} if route.startswith("native/") else set())
        exact(value, {"version"} | SCOPE_HEADERS.keys() | extra)
        for key in SCOPE_HEADERS:
            identifier(value[key])
        if "original" in extra:
            require(original(value["original"])["core_purpose_id"] == value["core_purpose_id"])
        if "challenge_id" in extra:
            require(original_uuid(value["challenge_id"]))
        if "native_proof" in extra:
            proof = value["native_proof"]
            exact(proof, {"kind", "bytes_b64"})
            require(type(proof["kind"]) is str and proof["kind"] in PROOF_KINDS)
            decoded_base64(proof["bytes_b64"], 1, 9216)
    require(value["version"] == VERSION)
    require(len(canonical(value)) <= BODY_BYTES)
    return value


def request_hash(route, value):
    request(route, value)
    return digest(["DJC-HOST-WAKE-API-REQUEST-V1", "POST", PREFIX + route, value])


def resolved(value, sent):
    request("authorization/resolve", sent)
    exact(value, {"version", "resolution", "authorization_id", "request_sha256", "scope_sha256",
        "original_authorization_issued_at_ms", "original_authorization_expires_at_ms", "max_original_purpose_ms",
        "max_operations", "max_reserved_sends", "native_proof_kind", "registration_mode"} | POLICY)
    require(value["version"] == VERSION and value["resolution"] == "existing")
    identifier(value["authorization_id"])
    require(value["request_sha256"] == request_hash("authorization/resolve", sent)
        and value["scope_sha256"] == digest(sent["scope"]))
    integer(value["original_authorization_issued_at_ms"])
    integer(value["original_authorization_expires_at_ms"], value["original_authorization_issued_at_ms"] + 1)
    integer(value["max_original_purpose_ms"], 1, 28800000)
    integer(value["max_operations"], 1, 256)
    integer(value["max_reserved_sends"], 1, 64)
    hashes(value, POLICY)
    require(type(value["native_proof_kind"]) is str and value["native_proof_kind"] in PROOF_KINDS
        and value["registration_mode"] == "single_original_no_rotation")
    return value


def reply(route, value, sent, retained, proof_kind, retained_challenge=None, private_purpose=None):
    request(route, sent)
    require(route != "authorization/resolve")
    original(retained)
    if route == "issuer/issue":
        require(canonical(sent["original"]) == canonical(retained))
    require(type(proof_kind) is str and proof_kind in PROOF_KINDS)
    extra = ({"purpose_id", "credential_state", "credential", "expires_at_ms", "native_proof_kind", "registration_mode", "original"}
        if route == "issuer/issue" else {"purpose_id", "credential_state"} if route == "issuer/status" else
        set() if route == "issuer/withdraw" else
        {"native_proof_kind", "original", "challenge", "canonical_transcript_utf8", "client_data_sha256"}
        if route == "native/challenge" else {"challenge_id", "native_proof_kind", "original_sha256"}
        | ({"native_verified_at_ms"} if type(value) is dict and value.get("state") == "native_verified" else set()))
    exact(value, BASE_REPLY | extra)
    require(value["version"] == VERSION and value["request_sha256"] == request_hash(route, sent))
    for key in SCOPE_HEADERS:
        require(value[key] == sent[key])
    require(value["core_purpose_id"] == retained["core_purpose_id"] and value["generation"] == retained["generation"])
    integer(value["revision"], 1, 256)
    require(value["revision"] == retained["revision"])
    for key in TIMES:
        integer(value[key])
        require(value[key] == retained[key])
    states = ({"issued"} if route == "issuer/issue" else {"pending", "issued", "withdrawn", "expired", "unknown"}
        if route == "issuer/status" else {"withdrawn", "expired", "unknown"} if route == "issuer/withdraw" else
        {"pending"} if route == "native/challenge" else {"pending", "native_verified", "withdrawn", "expired", "unknown"})
    require(type(value["state"]) is str and value["state"] in states)
    if "native_proof_kind" in extra:
        require(value["native_proof_kind"] == proof_kind)
    if "original" in extra:
        require(canonical(original(value["original"])) == canonical(retained))
    if route == "issuer/issue":
        identifier(value["purpose_id"])
        require(value["registration_mode"] == "single_original_no_rotation" and value["credential_state"] == "available")
        require(type(value["credential"]) is str and re.fullmatch(r"djchw_[A-Za-z0-9_-]{43}", value["credential"]))
        integer(value["expires_at_ms"])
        require(value["expires_at_ms"] == retained["original_wake_expires_at_ms"])
    elif route == "issuer/status":
        identifier(value["purpose_id"])
        require(value["credential_state"] == "unavailable")
    if "purpose_id" in extra and private_purpose is not None:
        require(value["purpose_id"] == private_purpose)
    if route == "native/challenge":
        current = challenge(value["challenge"], retained)
        require(current["challenge_id"] == sent["challenge_id"])
        transcript = canonical({"original": retained, "challenge": current})
        require(type(value["canonical_transcript_utf8"]) is str and value["canonical_transcript_utf8"].encode() == transcript)
        require(value["client_data_sha256"] == hashlib.sha256(DOMAIN + transcript).hexdigest())
    elif route in {"native/complete", "native/status"}:
        require(value["challenge_id"] == sent["challenge_id"] and value["original_sha256"] == digest(retained))
        if route == "native/complete":
            require(sent["native_proof"]["kind"] == proof_kind)
        if value["state"] == "native_verified":
            current = challenge(retained_challenge, retained)
            require(current["challenge_id"] == sent["challenge_id"])
            integer(value["native_verified_at_ms"], current["captured_at_ms"], current["expires_at_ms"] - 1)
    return value


def error(status, value):
    exact(value, {"version", "success", "error"})
    require(type(status) is int and status in ERRORS and value["version"] == VERSION
        and value["success"] is False and type(value["error"]) is str and value["error"] in ERRORS[status])
    return value
