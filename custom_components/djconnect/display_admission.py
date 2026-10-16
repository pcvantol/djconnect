"""Bounded B authority state, owned exclusively by SessionRuntimeManager's lock.

No rendezvous A, HA routes, owner-token conversion, publication or persistence.
Callers authenticate owners and provide synchronous current-authority fences.
Every principal and pending claim dies with this Runtime-manager instance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
import secrets
import time
from typing import Callable

CLAIM_TTL = 120
LEASE_TTL = 60
MAX_CLAIMS = 64
MAX_PER_SOURCE = 3
MAX_SHARES = 16
MAX_DISPLAYS = 64
MAX_PER_SHARE = 8


class DisplayAdmissionError(ValueError):
    def __init__(self, code: str, status: int = 403):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True, slots=True, repr=False)
class DisplayOwnerBinding:
    """Private immutable owner stamp; fence must not retain request credentials."""

    profile_id: str
    session_id: str
    entry_id: str
    stamp: str
    current: Callable[[], bool] = field(compare=False)

    def valid(self) -> bool:
        try:
            return self.current() is True
        except Exception:
            return False


@dataclass(slots=True, repr=False)
class _Claim:
    claim_id: str
    secret_hash: str
    nonce_hash: str
    code: str
    generation: str
    source: str
    deadline: float
    failures: int = 0
    owner: DisplayOwnerBinding | None = None
    share_id: str = ""
    display_id: str = ""
    approval_key: tuple = ()


@dataclass(slots=True, repr=False)
class _Share:
    share_id: str
    owner: DisplayOwnerBinding
    deadline: float
    generation: int = 1


@dataclass(slots=True, repr=False)
class _Display:
    display_id: str
    token_hash: str
    owner: DisplayOwnerBinding
    share_id: str
    claim_id: str
    approval_key: tuple
    lease_deadline: float
    lease_revision: int = 0
    connection_generation: int = 0
    invalidated: Callable[[], None] | None = None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest() if isinstance(value, str) else ""


def _same(left: str, right: str) -> bool:
    return isinstance(left, str) and isinstance(right, str) and secrets.compare_digest(left, right)


class DisplayAdmissionState:
    """Synchronous state transitions; the existing Runtime lock is the owner."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self.issuer_epoch = secrets.token_urlsafe(32)
        self._claims: dict[str, _Claim] = {}
        self._shares: dict[str, _Share] = {}
        self._displays: dict[str, _Display] = {}
        self._attempts: dict[str, tuple[int, float]] = {}

    def _drop_display(self, display_id: str) -> None:
        display = self._displays.pop(display_id, None)
        if display is not None and display.invalidated is not None:
            # This synchronous hook may wake the bounded writer, never publish.
            # Invalidation cannot be rolled back by a failed transport callback.
            try:
                display.invalidated()
            except Exception:
                pass

    def _drop_share(self, share_id: str) -> None:
        self._shares.pop(share_id, None)
        for claim_id, claim in tuple(self._claims.items()):
            if claim.share_id == share_id:
                del self._claims[claim_id]
        for display_id, display in tuple(self._displays.items()):
            if display.share_id == share_id:
                self._drop_display(display_id)

    def prune(self) -> None:
        now = self._clock()
        for claim_id, claim in tuple(self._claims.items()):
            if claim.deadline <= now or (claim.owner is not None and not claim.owner.valid()):
                del self._claims[claim_id]
        for share_id, share in tuple(self._shares.items()):
            if share.deadline <= now or not share.owner.valid():
                self._drop_share(share_id)
        for display_id, display in tuple(self._displays.items()):
            if display.lease_deadline <= now or not display.owner.valid():
                self._drop_display(display_id)
        self._attempts = {key: item for key, item in self._attempts.items() if item[1] > now}

    def clear(self) -> None:
        for display_id in tuple(self._displays):
            self._drop_display(display_id)
        self._claims.clear()
        self._shares.clear()
        self._attempts.clear()
        self.issuer_epoch = secrets.token_urlsafe(32)

    def revoke_session(self, session_id: str) -> None:
        for share_id, share in tuple(self._shares.items()):
            if share.owner.session_id == session_id:
                self._drop_share(share_id)

    def revoke_entry(self, entry_id: str) -> None:
        for share_id, share in tuple(self._shares.items()):
            if share.owner.entry_id == entry_id:
                self._drop_share(share_id)
        for claim_id, claim in tuple(self._claims.items()):
            if claim.owner is not None and claim.owner.entry_id == entry_id:
                del self._claims[claim_id]
        for display_id, display in tuple(self._displays.items()):
            if display.owner.entry_id == entry_id:
                self._drop_display(display_id)

    def _owner(self, owner: DisplayOwnerBinding) -> None:
        if not isinstance(owner, DisplayOwnerBinding) or not owner.valid():
            raise DisplayAdmissionError("display_context_changed")

    def _throttle(self, owner: DisplayOwnerBinding, *, failure: bool = False) -> None:
        count, deadline = self._attempts.get(owner.profile_id, (0, self._clock() + 60))
        if count >= 10 or (owner.profile_id not in self._attempts and len(self._attempts) >= 256):
            raise DisplayAdmissionError("display_rate_limited", 429)
        if failure:
            self._attempts[owner.profile_id] = (count + 1, deadline)

    def create_claim(self, *, source: str, browser_nonce: str) -> dict:
        self.prune()
        if not isinstance(browser_nonce, str) or re.fullmatch(r"[A-Za-z0-9_-]{43}", browser_nonce) is None:
            raise DisplayAdmissionError("display_code_invalid", 400)
        source = str(source)[:128]
        if len(self._claims) >= MAX_CLAIMS or sum(c.source == source for c in self._claims.values()) >= MAX_PER_SOURCE:
            raise DisplayAdmissionError("display_capacity", 429)
        used = {c.code for c in self._claims.values()}
        code = ""
        for _ in range(32):
            candidate = f"{secrets.randbelow(1_000_000):06d}"
            if candidate not in used:
                code = candidate
                break
        if not code:
            raise DisplayAdmissionError("display_capacity", 429)
        claim_id, secret, generation = (secrets.token_urlsafe(32) for _ in range(3))
        self._claims[claim_id] = _Claim(claim_id, _digest(secret), _digest(browser_nonce), code,
                                       generation, source, self._clock() + CLAIM_TTL)
        return {"success": True, "contract_version": 1, "issuer_epoch": self.issuer_epoch,
                "claim_id": claim_id, "claim_secret": secret, "code": code,
                "browser_generation": generation, "expires_in": CLAIM_TTL}

    def resolve(self, *, code: str, owner: DisplayOwnerBinding) -> dict:
        self.prune()
        self._owner(owner)
        self._throttle(owner)
        for claim in self._claims.values():
            if _same(claim.code, code) and claim.owner is None:
                return {"claim_id": claim.claim_id, "browser_generation": claim.generation,
                        "issuer_epoch": self.issuer_epoch, "expires_in": max(0, claim.deadline - self._clock())}
        self._throttle(owner, failure=True)
        raise DisplayAdmissionError("display_claim_unavailable", 404)

    def _summary(self, share: _Share, display_id: str) -> dict:
        return {"success": True, "state": "approved", "display_id": display_id,
                "session_id": share.owner.session_id, "share_id": share.share_id,
                "share_generation": share.generation, "share_expires_in": max(0, share.deadline - self._clock())}

    def approve(self, *, owner: DisplayOwnerBinding, issuer_epoch: str, claim_id: str,
                browser_generation: str, code: str, share: dict) -> dict:
        self.prune()
        self._owner(owner)
        self._throttle(owner)
        if not _same(self.issuer_epoch, issuer_epoch):
            raise DisplayAdmissionError("display_context_changed", 409)
        if not isinstance(share, dict):
            raise DisplayAdmissionError("display_code_invalid", 400)
        mode = share.get("mode")
        lifetime = share.get("lifetime_seconds", 7200)
        if mode not in {"create", "existing"} or (mode == "create" and
                (share.get("consent") is not True or type(lifetime) is not int or not 120 <= lifetime <= 28800)):
            raise DisplayAdmissionError("display_code_invalid", 400)
        allowed = {"mode", "consent", "lifetime_seconds"} if mode == "create" else {"mode", "share_id", "share_generation"}
        if set(share) - allowed or (mode == "existing" and
                (not isinstance(share.get("share_id"), str) or type(share.get("share_generation")) is not int)):
            raise DisplayAdmissionError("display_code_invalid", 400)
        key = (owner.profile_id, owner.session_id, owner.entry_id, owner.stamp, issuer_epoch,
               claim_id, browser_generation, code, mode, share.get("share_id"), share.get("share_generation"),
               lifetime if mode == "create" else None)
        claim = self._claims.get(claim_id)
        if claim is None:
            for display in self._displays.values():
                if display.claim_id == claim_id and display.approval_key == key:
                    return self._summary(self._shares[display.share_id], display.display_id)
            raise DisplayAdmissionError("display_claim_unavailable", 404)
        if claim.owner is not None:
            if claim.approval_key == key:
                return self._summary(self._shares[claim.share_id], claim.display_id)
            raise DisplayAdmissionError("display_context_changed", 409)
        if not _same(claim.generation, browser_generation) or not _same(claim.code, code):
            claim.failures += 1
            self._throttle(owner, failure=True)
            if claim.failures >= 5:
                del self._claims[claim_id]
            raise DisplayAdmissionError("display_claim_unavailable", 404)
        reservations = len(self._displays) + sum(c.owner is not None for c in self._claims.values())
        if reservations >= MAX_DISPLAYS:
            raise DisplayAdmissionError("display_capacity", 429)
        if mode == "create":
            if any(s.owner.session_id == owner.session_id for s in self._shares.values()):
                raise DisplayAdmissionError("display_context_changed", 409)
            if len(self._shares) >= MAX_SHARES:
                raise DisplayAdmissionError("display_capacity", 429)
            # No writes have happened yet: checks precede this atomic transition.
            selected = _Share(secrets.token_urlsafe(32), owner, self._clock() + lifetime)
        else:
            selected = self._shares.get(share.get("share_id"))
            if selected is None or selected.owner.profile_id != owner.profile_id or selected.owner.session_id != owner.session_id:
                raise DisplayAdmissionError("display_share_unavailable", 404)
            if share.get("share_generation") != selected.generation:
                raise DisplayAdmissionError("display_context_changed", 409)
        count = sum(d.share_id == selected.share_id for d in self._displays.values())
        count += sum(c.share_id == selected.share_id for c in self._claims.values())
        if count >= MAX_PER_SHARE:
            raise DisplayAdmissionError("display_capacity", 429)
        display_id = secrets.token_urlsafe(32)
        self._shares[selected.share_id] = selected
        claim.owner, claim.share_id = owner, selected.share_id
        claim.display_id, claim.approval_key = display_id, key
        return self._summary(selected, claim.display_id)

    def _browser_claim(self, *, issuer_epoch: str, claim_id: str, claim_secret: str,
                       browser_generation: str, browser_nonce: str) -> _Claim:
        self.prune()
        claim = self._claims.get(claim_id)
        if (not _same(self.issuer_epoch, issuer_epoch) or claim is None or
                not _same(claim.secret_hash, _digest(claim_secret)) or
                not _same(claim.nonce_hash, _digest(browser_nonce)) or
                not _same(claim.generation, browser_generation)):
            raise DisplayAdmissionError("display_claim_unavailable", 404)
        return claim

    def cancel(self, **binding) -> None:
        claim = self._browser_claim(**binding)
        del self._claims[claim.claim_id]

    def collect(self, **binding) -> dict:
        claim = self._browser_claim(**binding)
        if claim.owner is None:
            return {"success": True, "state": "pending"}
        share = self._shares[claim.share_id]
        token = "djcd_" + secrets.token_urlsafe(32)
        display = _Display(claim.display_id, _digest(token), claim.owner, claim.share_id,
                           claim.claim_id, claim.approval_key, min(self._clock() + LEASE_TTL, share.deadline))
        self._displays[display.display_id] = display
        del self._claims[claim.claim_id]
        return {"success": True, "state": "admitted", "contract_version": 1,
                "issuer_epoch": self.issuer_epoch, "display_id": display.display_id,
                "grant_token": token, "session_id": display.owner.session_id,
                "share_id": share.share_id, "share_generation": share.generation,
                "lease_revision": 0, "lease_expires_in": max(0, display.lease_deadline - self._clock()),
                "share_expires_in": max(0, share.deadline - self._clock()),
                "capabilities": {"view_display": True, "owner_controls": False, "audience_signals": False,
                                 "ask_dj": False, "session_end": False, "share_close": False}}

    def authorize(self, *, token: str, display_id: str, issuer_epoch: str) -> _Display:
        self.prune()
        display = self._displays.get(display_id)
        if (not _same(self.issuer_epoch, issuer_epoch) or display is None or
                not isinstance(token, str) or not token.startswith("djcd_") or
                not _same(display.token_hash, _digest(token))):
            raise DisplayAdmissionError("display_grant_invalid", 401)
        return display

    def renew(self, *, renew_sequence: int, **binding) -> dict:
        display = self.authorize(**binding)
        if type(renew_sequence) is not int or renew_sequence < 1:
            raise DisplayAdmissionError("display_context_changed", 409)
        if renew_sequence == display.lease_revision + 1:
            share = self._shares[display.share_id]
            display.lease_deadline = min(self._clock() + LEASE_TTL, share.deadline)
            display.lease_revision = renew_sequence
        elif renew_sequence != display.lease_revision:
            raise DisplayAdmissionError("display_context_changed", 409)
        return {"success": True, "lease_revision": display.lease_revision,
                "lease_expires_in": max(0, display.lease_deadline - self._clock())}

    def leave(self, **binding) -> None:
        display = self.authorize(**binding)
        self._drop_display(display.display_id)

    def revoke(self, *, owner: DisplayOwnerBinding, share_id: str, display_id: str = "") -> None:
        self.prune()
        self._owner(owner)
        share = self._shares.get(share_id)
        if share is None or (share.owner.profile_id, share.owner.session_id) != (owner.profile_id, owner.session_id):
            raise DisplayAdmissionError("display_share_unavailable", 404)
        if not display_id:
            self._drop_share(share_id)
        else:
            display = self._displays.get(display_id)
            if display is None or display.share_id != share_id:
                raise DisplayAdmissionError("display_grant_invalid", 404)
            self._drop_display(display_id)
