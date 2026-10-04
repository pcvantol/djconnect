"""Short-lived, memory-only owner handoff to a VibeCast browser receiver.

The six-digit code identifies a pending receiver, but never authenticates it.
Only the browser's independent high-entropy claim secret can collect the
Runtime-scoped Broadcast token after an authenticated Session owner approves.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import secrets
import time
from typing import Any

from .const import DOMAIN

HANDOFF_TTL_SECONDS = 300
MAX_PENDING_HANDOFFS = 64
MAX_PENDING_PER_SOURCE = 3
MAX_APPROVAL_ATTEMPTS_PER_OWNER = 10
APPROVAL_WINDOW_SECONDS = 60


@dataclass(slots=True)
class _Claim:
    code: str
    secret: str
    source: str
    expires_at: float
    session_id: str = ""
    broadcast_token: str = ""


class BroadcastHandoffManager:
    """Bound anonymous receiver claims and deliver an approved token once."""

    def __init__(self) -> None:
        self._claims: dict[str, _Claim] = {}
        self._approval_attempts: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()

    def _prune(self, now: float) -> None:
        for claim_id, claim in tuple(self._claims.items()):
            if claim.expires_at <= now:
                del self._claims[claim_id]

    async def clear(self) -> None:
        """Forget every pending claim when the last DJConnect entry unloads."""
        async with self._lock:
            self._claims.clear()
            self._approval_attempts.clear()

    async def create(self, source: str) -> dict[str, Any] | None:
        """Return a new browser-only claim, or deny capacity without eviction."""
        async with self._lock:
            now = time.monotonic()
            self._prune(now)
            if len(self._claims) >= MAX_PENDING_HANDOFFS:
                return None
            source = source[:128]
            if (
                sum(claim.source == source for claim in self._claims.values())
                >= MAX_PENDING_PER_SOURCE
            ):
                return None
            used_codes = {claim.code for claim in self._claims.values()}
            code = ""
            for _ in range(20):
                candidate = f"{secrets.randbelow(900000) + 100000:06d}"
                if candidate not in used_codes:
                    code = candidate
                    break
            if not code:
                return None
            claim_id = secrets.token_urlsafe(24)
            secret = secrets.token_urlsafe(32)
            self._claims[claim_id] = _Claim(
                code=code, secret=secret, source=source, expires_at=now + HANDOFF_TTL_SECONDS
            )
            return {
                "success": True,
                "claim_id": claim_id,
                "claim_secret": secret,
                "code": code,
                "expires_in": HANDOFF_TTL_SECONDS,
            }

    async def approve(
        self, code: str, *, owner_profile_id: str, session_id: str, broadcast_token: str
    ) -> bool:
        """Bind the active owner's Runtime token to one unapproved code."""
        if len(code) != 6 or not code.isascii() or not code.isdigit():
            return False
        async with self._lock:
            now = time.monotonic()
            self._prune(now)
            self._approval_attempts = {
                owner: attempt
                for owner, attempt in self._approval_attempts.items()
                if attempt[1] > now
            }
            count, expires_at = self._approval_attempts.get(
                owner_profile_id, (0, now + APPROVAL_WINDOW_SECONDS)
            )
            if count >= MAX_APPROVAL_ATTEMPTS_PER_OWNER:
                return False
            for claim in self._claims.values():
                if secrets.compare_digest(claim.code, code) and not claim.session_id:
                    claim.session_id = session_id
                    claim.broadcast_token = broadcast_token
                    self._approval_attempts.pop(owner_profile_id, None)
                    return True
            self._approval_attempts[owner_profile_id] = (count + 1, expires_at)
            return False

    async def collect(self, claim_id: str, secret: str) -> tuple[str, dict[str, Any] | None]:
        """Collect an approved handoff once; never reveal a claim by its code."""
        async with self._lock:
            self._prune(time.monotonic())
            claim = self._claims.get(claim_id)
            if claim is None or not secret or not secrets.compare_digest(claim.secret, secret):
                return "not_found", None
            if not claim.session_id:
                return "pending", {"success": True, "state": "pending"}
            del self._claims[claim_id]
            return "approved", {
                "success": True,
                "state": "approved",
                "session_id": claim.session_id,
                "broadcast_token": claim.broadcast_token,
            }


def broadcast_handoff_manager(hass: Any) -> BroadcastHandoffManager:
    """Keep receiver claims inside the HA integration's process lifetime."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get("broadcast_handoff_manager")
    if manager is None:
        manager = BroadcastHandoffManager()
        domain_data["broadcast_handoff_manager"] = manager
    return manager
