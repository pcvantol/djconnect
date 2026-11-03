"""Closed Core client for the signed Watch preference protocol.

The caller supplies an enrolled server-side receiver, its currentness check,
and approved signing and transport ports. This module does not resolve a
receiver from client input or provision a key.
"""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
import hashlib
import json
import re
import struct
import time
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

_DOMAIN = b"DJC-WATCH-LIFECYCLE-V1\x00"
_IDENTIFIER = re.compile(r"[A-Za-z0-9._~-]{1,160}")
_FINGERPRINT = re.compile(r"[a-f0-9]{64}")
_MAX_COUNTER = (1 << 53) - 1
_RECEIPT = {"incarnation", "revision", "operation", "enabled", "sealed"}

PreferenceOutcome = Literal["confirmed", "superseded", "unknown", "discarded"]
RetirementOutcome = Literal["committed", "denied", "unknown", "discarded"]


@dataclass(frozen=True)
class EnrolledWatchReceiver:
    audience: str
    installation: str
    receiver: str
    incarnation: str
    epoch: int
    key_fingerprint: str


@dataclass(frozen=True)
class WatchPreferenceIntent:
    operation: str
    expected_version: int
    enabled: bool
    expiry: int


def _counter(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_COUNTER


def _validate_binding(receiver: EnrolledWatchReceiver, operation: str, expiry: int) -> None:
    if (not isinstance(receiver.audience, str) or not re.fullmatch(r"[!-~]{1,160}", receiver.audience)
            or any(not isinstance(value, str) or not _IDENTIFIER.fullmatch(value)
                   for value in (receiver.installation, receiver.receiver, receiver.incarnation, operation))
            or not isinstance(receiver.key_fingerprint, str) or not _FINGERPRINT.fullmatch(receiver.key_fingerprint)
            or not _counter(receiver.epoch) or receiver.epoch == 0 or not _counter(expiry)):
        raise ValueError("invalid_watch_preference_binding")


def _validate(receiver: EnrolledWatchReceiver, intent: WatchPreferenceIntent) -> None:
    _validate_binding(receiver, intent.operation, intent.expiry)
    if (not _counter(intent.expected_version) or intent.expected_version == _MAX_COUNTER
            or type(intent.enabled) is not bool):
        raise ValueError("invalid_watch_preference_binding")


def _request(receiver: EnrolledWatchReceiver, intent: WatchPreferenceIntent, *, read: bool):
    action = "preference-read" if read else "preference-write"
    operation = uuid4().hex if read else intent.operation
    claims = {
        "audience": receiver.audience, "action": action,
        "installation": receiver.installation, "receiver": receiver.receiver,
        "epoch": receiver.epoch, "key_fingerprint": receiver.key_fingerprint,
        "expiry": intent.expiry, "operation": operation, "incarnation": receiver.incarnation,
    }
    if not read:
        claims.update(expected_version=intent.expected_version, enabled=intent.enabled)
    return _frame(claims)


def _frame(claims: dict) -> tuple[bytes, bytes]:
    body = json.dumps(claims, separators=(",", ":")).encode()
    fields = (
        claims["audience"], claims["action"], claims["installation"], claims["receiver"],
        str(claims["epoch"]), claims["key_fingerprint"], claims["incarnation"], "",
        str(claims["expiry"]), claims["operation"], str(claims.get("expected_version", "")),
        hashlib.sha256(body).hexdigest(),
    )
    frame = bytearray(_DOMAIN)
    for field in fields:
        raw = field.encode()
        frame.extend(struct.pack(">I", len(raw)))
        frame.extend(raw)
    return body, bytes(frame)


def _outcome(receipt, receiver, intent) -> PreferenceOutcome:
    if not isinstance(receipt, dict) or set(receipt) != _RECEIPT:
        return "unknown"
    revision = receipt["revision"]
    if (receipt["incarnation"] != receiver.incarnation or not _counter(revision)
            or type(receipt["enabled"]) is not int or receipt["enabled"] not in (0, 1)
            or type(receipt["sealed"]) is not int or receipt["sealed"] not in (0, 1)
            or not (receipt["operation"] is None or isinstance(receipt["operation"], str))):
        return "unknown"
    if revision > intent.expected_version + 1:
        return "superseded"
    if (revision == intent.expected_version + 1 and receipt["operation"] == intent.operation
            and receipt["enabled"] == int(intent.enabled)
            and (not intent.enabled or not receipt["sealed"])):
        return "confirmed"
    return "unknown"


async def update_watch_preference(
    receiver: EnrolledWatchReceiver, intent: WatchPreferenceIntent, *,
    require_current, sign_frame, post_signed, wall=time.time,
) -> PreferenceOutcome:
    """Submit once and reconcile uncertainty with at most one signed read.

    `require_current` must synchronously validate the original binding and
    local intent or raise PermissionError. Both async ports are called inside
    the original expiry, with no intent rebase or write retry.
    """
    _validate(receiver, intent)

    def guard():
        if require_current(receiver, intent) is not None:
            raise PermissionError("watch_preference_authority_unavailable")
        remaining = intent.expiry - wall()
        if not 0 < remaining <= 30:
            raise TimeoutError
        return remaining

    async def attempt(*, read: bool):
        guard()
        body, frame = _request(receiver, intent, read=read)
        raw = await sign_frame(frame)
        guard()
        if type(raw) is not bytes or len(raw) != 64:
            raise PermissionError("watch_preference_signer_unavailable")
        signature = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        reply = await post_signed(body, signature)
        guard()
        return _outcome(reply, receiver, intent)

    try:
        async with asyncio.timeout(guard()):
            try:
                result = await attempt(read=False)
            except PermissionError:
                raise
            except OSError:
                result = "unknown"
            return await attempt(read=True) if result == "unknown" else result
    except PermissionError:
        return "discarded"
    except (OSError, TimeoutError):
        return "unknown"


async def retire_watch_receiver(
    receiver: EnrolledWatchReceiver, *, operation: str, expiry: int,
    require_current, sign_frame, post_signed, wall=time.time,
) -> RetirementOutcome:
    """Submit one retirement and reconcile ambiguity with one exact signed status request."""
    _validate_binding(receiver, operation, expiry)
    claims = {
        "audience": receiver.audience, "action": "retire",
        "installation": receiver.installation, "receiver": receiver.receiver,
        "epoch": receiver.epoch, "key_fingerprint": receiver.key_fingerprint,
        "expiry": expiry, "operation": operation, "incarnation": receiver.incarnation,
    }

    def guard():
        if require_current(receiver) is not None:
            raise PermissionError("watch_retirement_authority_unavailable")
        remaining = expiry - wall()
        if not 0 < remaining <= 30:
            raise TimeoutError
        return remaining

    async def send(request_claims):
        guard()
        body, frame = _frame(request_claims)
        raw = await sign_frame(frame)
        guard()
        if type(raw) is not bytes or len(raw) != 64:
            raise PermissionError("watch_preference_signer_unavailable")
        signature = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        try:
            outcome = await post_signed(body, signature)
        except PermissionError:
            raise
        except (OSError, TimeoutError):
            outcome = "unknown"
        guard()
        return body, outcome

    try:
        async with asyncio.timeout(guard()):
            body, outcome = await send(claims)
            if outcome in ("committed", "denied"):
                return outcome
            status_claims = {
                **claims, "action": "lifecycle-status", "operation": uuid4().hex,
                "target_operation": operation, "target_body_sha256": hashlib.sha256(body).hexdigest(),
            }
            _, outcome = await send(status_claims)
            return "committed" if outcome == "committed" else "unknown"
    except PermissionError:
        return "discarded"
    except (OSError, TimeoutError):
        return "unknown"


def watch_preference_https(endpoint: str):
    """Bind the signed transport to a provisioned API endpoint.

    No ambient authentication, proxy, cookie, or redirect can move a signed
    request away from this destination. Endpoint selection belongs to the
    enrolled server composition, not the paired client.
    """
    from .surface_issuer_owner import DNS_HOST

    if type(endpoint) is not str or len(endpoint) > 2048:
        raise ValueError("invalid_watch_preference_endpoint")
    try:
        parsed = urlsplit(endpoint)
        valid = (
            parsed.scheme == "https" and parsed.hostname is not None
            and DNS_HOST.fullmatch(parsed.hostname) is not None
            and re.fullmatch(r"(?:/[A-Za-z0-9_-]+)+", parsed.path) is not None
            and endpoint == f"https://{parsed.hostname}{parsed.path}"
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("invalid_watch_preference_endpoint")

    async def post_signed(body: bytes, signature: str):
        import aiohttp

        from .surface_issuer_transport import strict_body

        if (type(body) is not bytes or not 0 < len(body) <= 2048
                or type(signature) is not str
                or not re.fullmatch(r"[A-Za-z0-9_-]{85}[AQgw]", signature)):
            raise ValueError("invalid_watch_preference_request")
        try:
            async with aiohttp.ClientSession(
                cookie_jar=aiohttp.DummyCookieJar(), trust_env=False, auto_decompress=False,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as session:
                async with session.post(endpoint, data=body, allow_redirects=False, headers={
                    "Content-Type": "application/json", "Accept": "application/json",
                    "Accept-Encoding": "identity", "DJC-Watch-Lifecycle-Signature": signature,
                }) as response:
                    media = response.headers.getall("Content-Type", [])
                    if (response.status != 200 or response.headers.getall("Content-Encoding", [])
                            not in ([], ["identity"]) or len(media) != 1
                            or not re.fullmatch(r"application/json(?:;\s*charset=utf-8)?", media[0], re.I)):
                        return None
                    raw = bytearray()
                    async for chunk in response.content.iter_chunked(1024):
                        raw.extend(chunk)
                        if len(raw) > 2048:
                            return None
                    return strict_body(bytes(raw))
        except (aiohttp.ClientError, ValueError, TimeoutError):
            return None

    return post_signed


def watch_retirement_https(endpoint: str):
    """Bind retirement to a provisioned HTTPS endpoint and require an exact commit receipt."""
    request = watch_preference_https(endpoint)

    async def post_signed(body: bytes, signature: str) -> RetirementOutcome:
        reply = await request(body, signature)
        if isinstance(reply, dict) and reply == {"outcome": "committed"}:
            return "committed"
        return "unknown"

    return post_signed
