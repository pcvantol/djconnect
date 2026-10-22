"""Closed offline issuer wire; validation confers no enrolment or live authority.

API source 2a6cd1240fe86581dea7810c1f62ce094d725639. No private key,
operator endpoint, HTTP caller, credential adoption or lifecycle is supplied here.
An enrolled-key owner must independently admit every actual use.
"""
from __future__ import annotations

import base64
import hashlib
import re

from .surface_push_contract import SurfacePushError, require
from .surface_push_wire import canonical
from .transport_operations import operation_created_ms

DOMAIN = "djc-surface-issuer/1"
PREFIX = "/v1/push/surface/issuer/"
ACTIONS = frozenset({"challenge", "issue", "status", "withdraw"})
COMMON = frozenset({"contract_version", "purpose", "action", "operation_id",
    "delegation_id", "delegation_revision", "key_thumbprint"})
ISSUE = frozenset({"challenge_id", "nonce", "scope_digest"})


def _closed(value, fields):
    require(type(value) is dict and set(value) == fields, "surface_issuer_wire_invalid")


def _identifier(value):
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value),
        "surface_issuer_wire_invalid")


def _hex(value):
    require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value),
        "surface_issuer_wire_invalid")


def decoded(value, size):
    """Canonical unpadded base64url only; reject DER and alternative encodings."""
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]+", value),
        "surface_issuer_wire_invalid")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except ValueError:
        raise SurfacePushError("surface_issuer_wire_invalid") from None
    require(len(raw) == size and base64.urlsafe_b64encode(raw).decode().rstrip("=") == value,
        "surface_issuer_wire_invalid")
    return raw


def public_key_thumbprint(jwk):
    """Domain-array hash, deliberately distinct from an RFC7638 thumbprint.

    This checks closed encoding only. Curve-point validity is checked by the
    standard crypto implementation in verify_envelope, never by custom crypto.
    """
    _closed(jwk, {"kty", "crv", "x", "y"})
    require(jwk["kty"] == "EC" and jwk["crv"] == "P-256", "surface_issuer_key_invalid")
    decoded(jwk["x"], 32)
    decoded(jwk["y"], 32)
    return hashlib.sha256(canonical([DOMAIN, "public-key", jwk]).encode()).hexdigest()


def signing_bytes(path, payload):
    """Exact POST route/action binding; original UUID syntax, not live admission.

    Expired public vectors can be verified offline. Real challenge/issue/status/
    withdrawal deadlines and ownership must be enforced by their lifecycle owner.
    """
    require(type(path) is str and path.startswith(PREFIX), "surface_issuer_wire_invalid")
    action = path[len(PREFIX):]
    require(action in ACTIONS, "surface_issuer_wire_invalid")
    _closed(payload, COMMON | (ISSUE if action == "issue" else frozenset()))
    require(type(payload["contract_version"]) is int and payload["contract_version"] == 1
        and payload["purpose"] == "surface_push" and payload["action"] == action
        and type(payload["delegation_revision"]) is int and payload["delegation_revision"] == 1,
        "surface_issuer_wire_invalid")
    _identifier(payload["delegation_id"])
    _hex(payload["key_thumbprint"])
    try:
        operation_created_ms(payload["operation_id"])
    except Exception:
        raise SurfacePushError("surface_issuer_wire_invalid") from None
    if action == "issue":
        _identifier(payload["challenge_id"])
        decoded(payload["nonce"], 32)
        _hex(payload["scope_digest"])
    result = canonical([DOMAIN, "POST", path, payload]).encode("utf-8")
    require(len(result) <= 16384, "surface_issuer_wire_invalid")
    return result


def verify_envelope(path, envelope, jwk):
    """Offline standard ES256 verification, never a purpose credential grant.

    cryptography is supplied by HA. Import lazily so non-crypto wire validation
    stays independent of a test harness's optional HA dependency stubs.
    """
    _closed(envelope, {"payload", "signature"})
    message = signing_bytes(path, envelope["payload"])
    signature = decoded(envelope["signature"], 64)
    require(envelope["payload"]["key_thumbprint"] == public_key_thumbprint(jwk),
        "surface_issuer_key_mismatch")
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, utils

    try:
        public = ec.EllipticCurvePublicNumbers(
            int.from_bytes(decoded(jwk["x"], 32)),
            int.from_bytes(decoded(jwk["y"], 32)), ec.SECP256R1()).public_key()
        # P1363 raw r||s is the ONLY wire format. DER exists solely inside the
        # cryptography API; a DER signature from the wire cannot enter this path.
        der = utils.encode_dss_signature(int.from_bytes(signature[:32]), int.from_bytes(signature[32:]))
        public.verify(der, message, ec.ECDSA(hashes.SHA256()))
    except (ValueError, InvalidSignature):
        raise SurfacePushError("surface_issuer_signature_invalid") from None
    return True
