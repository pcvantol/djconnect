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
from uuid import uuid4

_DOMAIN = b"DJC-WATCH-LIFECYCLE-V1\x00"
_IDENTIFIER = re.compile(r"[A-Za-z0-9._~-]{1,160}")
_FINGERPRINT = re.compile(r"[a-f0-9]{64}")
_MAX_COUNTER = (1 << 53) - 1
_RECEIPT = {"incarnation", "revision", "operation", "enabled", "sealed"}

PreferenceOutcome = Literal["confirmed", "superseded", "unknown", "discarded"]


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


def _validate(receiver: EnrolledWatchReceiver, intent: WatchPreferenceIntent) -> None:
    if (not isinstance(receiver.audience, str) or not re.fullmatch(r"[!-~]{1,160}", receiver.audience)
            or any(not isinstance(value, str) or not _IDENTIFIER.fullmatch(value)
                   for value in (receiver.installation, receiver.receiver, receiver.incarnation, intent.operation))
            or not isinstance(receiver.key_fingerprint, str) or not _FINGERPRINT.fullmatch(receiver.key_fingerprint)
            or not _counter(receiver.epoch) or receiver.epoch == 0
            or not _counter(intent.expected_version) or intent.expected_version == _MAX_COUNTER
            or not _counter(intent.expiry) or type(intent.enabled) is not bool):
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
    body = json.dumps(claims, separators=(",", ":")).encode()
    fields = (
        receiver.audience, action, receiver.installation, receiver.receiver,
        str(receiver.epoch), receiver.key_fingerprint, receiver.incarnation, "",
        str(intent.expiry), operation, "" if read else str(intent.expected_version),
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
