"""Closed Direct rich request wire; decoding never supplies source authority.

Separate from all legacy surface versions. The actual owner/source/persistence
service must independently authorize before using these validated intentions.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid

VERSION = 1
PROFILE = "djconnect-direct-rich-v1"
BASE = "/api/djconnect/v1/session/rich"
REQUEST_BYTES = 8192
RESPONSE_BYTES = 16384
SAFE = 9007199254740991
PURPOSE_MS = 28800000
MAX_DEPTH = 8
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
DEVICE = re.compile(r"djconnect-(ios|macos)-[A-Za-z0-9]{12}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
ASSET = re.compile(r"[A-Za-z0-9_-]{32}\Z")
IDENTITY = {"contract_version", "device_id", "client_type", "session_id", "surface"}
MANAGE = IDENTITY | {"operation_id"}
CONSENT = {"enabled", "os_snapshot_cache", "locked_display"}


class RichError(ValueError):
    """Only a fixed public code/status; never private request/exception text."""

    def __init__(self, code="invalid_request", status=400):
        super().__init__(code)
        self.code, self.status = code, status


def require(value, code="invalid_request", status=400):
    if not value:
        raise RichError(code, status)


def safe_integer(value, minimum=0):
    return type(value) is int and minimum <= value <= SAFE


def original_uuid(value):
    if type(value) is not str or len(value) != 36:
        return False
    try:
        parsed = uuid.UUID(value)
        return parsed.version == 4 and str(parsed) == value
    except (ValueError, AttributeError):
        return False


def domain(value, depth=0):
    require(depth <= MAX_DEPTH)
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(-SAFE <= value <= SAFE)
    elif type(value) is str:
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeError:
            raise RichError from None
    elif type(value) is list:
        for item in value:
            domain(item, depth + 1)
    elif type(value) is dict:
        require(all(type(k) is str and k.isascii() for k in value))
        for item in value.values():
            domain(item, depth + 1)
    else:
        raise RichError


def canonical(value):
    domain(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def parse(kind, raw):
    """Bound original bytes and reject duplicates before interpreting intent."""
    require(type(raw) is bytes and 0 < len(raw) <= REQUEST_BYTES)

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result

    def constant(_):
        raise RichError

    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise RichError from None
    validate(kind, value)
    return value


def validate(kind, value):
    expected = (MANAGE | CONSENT if kind == "authorize" else MANAGE
        if kind in {"status", "withdraw"} else {"contract_version", "purpose_id"}
        if kind == "read" else {"contract_version", "purpose_id", "frame_id", "asset_id"}
        if kind == "asset" else None)
    require(expected is not None and type(value) is dict and set(value) == expected)
    domain(value)
    require(type(value["contract_version"]) is int and value["contract_version"] == VERSION)
    if kind in {"authorize", "status", "withdraw"}:
        device = value["device_id"]
        require(type(device) is str and DEVICE.fullmatch(device) is not None)
        require(value["client_type"] == DEVICE.fullmatch(device)[1])
        require(type(value["session_id"]) is str and IDENTIFIER.fullmatch(value["session_id"]))
        require(type(value["surface"]) is str and value["surface"] in {"widget", "live_activity"})
        require(value["surface"] != "live_activity" or value["client_type"] == "ios")
        require(original_uuid(value["operation_id"]))
    else:
        require(original_uuid(value["purpose_id"]))
        if kind == "asset":
            require(type(value["frame_id"]) is str and HASH.fullmatch(value["frame_id"]))
            require(type(value["asset_id"]) is str and ASSET.fullmatch(value["asset_id"]))
    if kind == "authorize":
        require(all(type(value[k]) is bool for k in CONSENT))


def one_header(headers, name):
    values = headers.getall(name, []) if hasattr(headers, "getall") else [headers.get(name)]
    require(len(values) == 1 and type(values[0]) is str)
    return values[0]


def credential(headers, family):
    """Exact role credential; never token coercion or ordinary app fallback."""
    require(family in {"read", "asset"})
    value = one_header(headers, "Authorization")
    prefix = "Bearer djcrich" + family + "_"
    require(value.startswith(prefix) and re.fullmatch(r"[A-Za-z0-9_-]{43}", value[len(prefix):]),
        "unauthorized", 401)
    # 32-byte unpadded base64url has four significant final bits, then two zero bits.
    require(value[-1] in "AEIMQUYcgkosw048", "unauthorized", 401)
    return value[7:]
