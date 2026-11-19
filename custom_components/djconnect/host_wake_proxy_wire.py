"""Closed public host-wake request DATA; never pairing/native authority.

The owning HTTP/service layer must capture the original lifetime before reading
these bytes. Decoding cannot select an owner, create a purpose or qualify clocks.
"""
from __future__ import annotations

import base64
import binascii
import json
import re

from .direct_rich_wire import (
    DEVICE, HASH, IDENTIFIER, MAX_DEPTH, SAFE, RichError, canonical, digest,
    domain, original_uuid, require,
)

BASE = "/api/djconnect/v1/session/rich/push/"
BODY_BYTES = 16384
OPERATIONS = frozenset({"prepare", "native/challenge", "native/complete",
    "native/status", "register", "status", "withdraw"})
COMMON = frozenset({"contract_version", "device_id", "client_type", "session_id",
    "surface", "purpose_id", "operation_id"})
PREPARE = frozenset({"target", "platform", "apns_environment", "native_key_id_b64",
    "native_token_sha256"})
PROOF_KINDS = frozenset({"app_attest_attestation", "app_attest_assertion"})
_BUNDLE = re.compile(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\Z")


def public_error(error):
    """Translate local failures into the frozen push-specific client contract.

    Unknown/internal error strings and mismatched statuses never reach clients.
    This does not change errors on the original direct-read routes.
    """
    known = {
        ("invalid_request", 400): ("invalid_request", 400),
        ("unauthorized", 401): ("unauthorized", 401),
        ("rich_not_allowed", 403): ("rich_push_not_allowed", 403),
        ("rich_history_unknown", 404): ("rich_push_history_unknown", 404),
        ("rich_purpose_consumed", 409): ("rich_push_consumed", 409),
        ("rich_capacity", 409): ("rich_push_capacity", 409),
        ("rich_stage_mismatch", 409): ("rich_push_stage_mismatch", 409),
        ("rich_body_too_large", 413): ("rich_push_body_too_large", 413),
        ("rich_frame_unavailable", 503): ("rich_push_unavailable", 503),
        ("rich_unavailable", 503): ("rich_push_unavailable", 503),
        ("rich_pending", 503): ("rich_push_pending", 503),
    }
    selected = (known.get((error.code, error.status)) if isinstance(error, RichError)
        and type(error.code) is str and type(error.status) is int else None)
    return RichError(*(selected or ("rich_push_unavailable", 503)))


def decoded_base64(value, minimum, maximum):
    """Canonical standard Base64, including padding bits and decoded bounds."""
    require(type(value) is str and len(value) <= 4 * ((maximum + 2) // 3))
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise RichError from None
    require(minimum <= len(raw) <= maximum
        and base64.b64encode(raw).decode("ascii") == value)
    return raw


def _exact(value, keys):
    require(type(value) is dict and value.keys() == keys)


def validate(operation, value):
    """Validate exactly one public request, without substituting private DTOs."""
    require(type(operation) is str and operation in OPERATIONS)
    extra = (PREPARE if operation == "prepare" else
        {"challenge_id", "native_proof"} if operation == "native/complete" else
        {"challenge_id", "native_token_b64"} if operation == "register" else
        {"challenge_id"} if operation == "native/status" else set())
    _exact(value, COMMON | extra)
    domain(value)
    require(type(value["contract_version"]) is int and value["contract_version"] == 1)
    require(type(value["device_id"]) is str and DEVICE.fullmatch(value["device_id"])
        and value["device_id"].startswith("djconnect-ios-") and value["client_type"] == "ios")
    require(type(value["session_id"]) is str and IDENTIFIER.fullmatch(value["session_id"]))
    require(type(value["surface"]) is str and value["surface"] in {"widget", "live_activity"})
    require(original_uuid(value["purpose_id"]) and original_uuid(value["operation_id"]))
    if "challenge_id" in extra:
        require(original_uuid(value["challenge_id"]))
    if operation == "prepare":
        target = value["target"]
        _exact(target, {"host_bundle_id", "installation_id"})
        require(type(target["host_bundle_id"]) is str and len(target["host_bundle_id"]) <= 200
            and _BUNDLE.fullmatch(target["host_bundle_id"]))
        require(type(target["installation_id"]) is str and IDENTIFIER.fullmatch(target["installation_id"]))
        require(type(value["platform"]) is str and value["platform"] in {"ios", "ipados"})
        require(type(value["apns_environment"]) is str and value["apns_environment"] in {"sandbox", "production"})
        decoded_base64(value["native_key_id_b64"], 1, 1024)  # DATA, not an enrolled SDK key.
        require(type(value["native_token_sha256"]) is str and HASH.fullmatch(value["native_token_sha256"]))
    elif operation == "native/complete":
        proof = value["native_proof"]
        _exact(proof, {"kind", "bytes_b64"})
        require(type(proof["kind"]) is str and proof["kind"] in PROOF_KINDS)
        decoded_base64(proof["bytes_b64"], 1, 9216)
    elif operation == "register":
        decoded_base64(value["native_token_b64"], 16, 2048)
    return value


def decode_json(raw):
    """Shared strict raw DATA decoder; no public or private operation selection."""
    require(type(raw) is bytes and 0 < len(raw) <= BODY_BYTES)
    try:
        text = raw.decode("utf-8", errors="strict")
        # Bound nesting before invoking the recursive JSON decoder. Quoted
        # braces and escaped quotes do not change structural depth.
        depth, quoted, escaped = 0, False, False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                require(depth <= MAX_DEPTH)
            elif char in "]}":
                depth -= 1
                require(depth >= 0)

        def pairs(items):
            result = {}
            for key, item in items:
                require(key not in result)
                result[key] = item
            return result

        def integer(lexeme):
            require(lexeme != "-0")
            number = int(lexeme)
            require(-SAFE <= number <= SAFE)
            return number

        def forbidden(_):
            raise RichError

        value = json.loads(text, object_pairs_hook=pairs, parse_int=integer,
            parse_float=forbidden, parse_constant=forbidden)
        domain(value)
        return value
    except (UnicodeError, ValueError, TypeError, RecursionError):
        raise RichError from None


def parse(operation, raw):
    return validate(operation, decode_json(raw))


def request_sha256(operation, value):
    validate(operation, value)
    return digest(["DJC-HOST-WAKE-CORE-REQUEST-V1", "POST", BASE + operation, value])


def request_bytes(operation, value):
    result = canonical(validate(operation, value))
    require(len(result) <= BODY_BYTES)
    return result
