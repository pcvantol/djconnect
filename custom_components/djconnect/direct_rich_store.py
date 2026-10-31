"""Original direct-rich metadata reservation on actual platform SQLite.

No secrets, rich payloads or recoverable live permission are stored/returned.
Only the actual runtime service may independently select original owner/source
permission. FULL-sync commit acknowledgement is not physical restore proof.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .direct_rich_wire import HASH, PURPOSE_MS, RichError, digest, original_uuid, require, safe_integer

MAX_ROWS = 4096
FIELDS = ("scope_hash", "operation_id", "purpose_id", "owner_hash", "device_hash",
    "entry_hash", "pair_hash", "session_hash", "surface", "request_hash", "issued_ms", "expires_ms")
BY_SCOPE = (
    "SELECT scope_hash,operation_id,purpose_id,owner_hash,device_hash,entry_hash,"
    "pair_hash,session_hash,surface,request_hash,issued_ms,expires_ms,phase "
    "FROM djconnect_rich_purposes WHERE scope_hash=?"
)
BY_OPERATION = (
    "SELECT scope_hash,operation_id,purpose_id,owner_hash,device_hash,entry_hash,"
    "pair_hash,session_hash,surface,request_hash,issued_ms,expires_ms,phase "
    "FROM djconnect_rich_purposes WHERE operation_id=?"
)


def owner_hash(owner_id):
    require(type(owner_id) is str and 0 < len(owner_id) <= 128)
    return digest(["DJC-DIRECT-RICH-OWNER-V1", owner_id])


def session_hash(session_id):
    require(type(session_id) is str and 0 < len(session_id) <= 128)
    return digest(["DJC-DIRECT-RICH-SESSION-V1", session_id])


@dataclass(frozen=True, repr=False)
class RichOriginal:
    scope_hash: str
    operation_id: str
    purpose_id: str
    owner_hash: str
    device_hash: str
    entry_hash: str
    pair_hash: str
    session_hash: str
    surface: str
    request_hash: str
    issued_ms: int
    expires_ms: int

    def values(self):
        return tuple(getattr(self, name) for name in FIELDS)

    def validate(self):
        for name in ("scope_hash", "owner_hash", "device_hash", "entry_hash", "pair_hash",
                "session_hash", "request_hash"):
            value = getattr(self, name)
            require(type(value) is str and HASH.fullmatch(value) is not None)
        require(original_uuid(self.operation_id) and original_uuid(self.purpose_id))
        require(type(self.surface) is str and self.surface in {"widget", "live_activity"}
            and safe_integer(self.issued_ms, 1) and safe_integer(self.expires_ms, 1)
            and 0 < self.expires_ms - self.issued_ms <= PURPOSE_MS)


class RichPurposeJournal:
    def __init__(self, persistence):
        self.persistence = persistence
        self._provider = persistence._provider
        self._readiness = persistence.readiness
        self._path = persistence._database_path
        self._retired = False
        self._storage()

    def _storage(self):
        if (self._retired or self.persistence._provider is not self._provider
                or self.persistence.readiness is not self._readiness
                or not self._readiness.ready or self.persistence._database_path != self._path):
            self._retired = True  # Equality later cannot revive the original lifetime.
            raise RichError("rich_unavailable", 503)

    @staticmethod
    def _session_binding(original, session_id, owner_id):
        require(original.owner_hash == owner_hash(owner_id)
            and original.session_hash == session_hash(session_id), "rich_not_allowed", 403)

    async def _settle(self, operation, current):
        self._storage()
        task = asyncio.current_task()

        def allowed():
            self._storage()
            return not task.cancelling() and current() is True

        try:
            value = await self.persistence.async_in_transaction(operation,
                authorize=allowed, finalize_authorize=allowed, require_full_sync=True)
        except Exception as error:
            if task.cancelling():
                raise asyncio.CancelledError from None
            if isinstance(error, RichError):
                raise
            raise RichError("rich_unavailable", 503) from None
        if task.cancelling():
            raise asyncio.CancelledError
        self._storage()
        require(allowed(), "rich_unavailable", 503)
        return value

    @staticmethod
    def _original(row):
        require(row is not None and len(row) == len(FIELDS) + 1,
            "rich_unavailable", 503)
        result = RichOriginal(*row[:-1])
        try:
            result.validate()
        except RichError:
            raise RichError("rich_unavailable", 503) from None
        require(row[-1] in {"reserved", "issued", "withdrawn"}, "rich_unavailable", 503)
        return result

    async def reserve(self, original, *, session_id, owner_id, current):
        """One immutable original scope, even after expiry or an uncertain ACK."""
        require(type(original) is RichOriginal)
        original.validate()
        self._session_binding(original, session_id, owner_id)

        def write(tx):
            require(tx.fetchone("SELECT 1 FROM djconnect_rich_purposes "
                "WHERE scope_hash=? OR operation_id=? OR purpose_id=?",
                (original.scope_hash, original.operation_id, original.purpose_id)) is None,
                "rich_purpose_consumed", 409)
            require(tx.fetchone("SELECT count(*) FROM djconnect_rich_purposes")[0] < MAX_ROWS,
                "rich_capacity", 409)
            # Same transaction observes actual Session owner/lifecycle. The
            # owning runtime still supplies the independent original source check.
            require(tx.fetchone("SELECT owner_profile_id,lifecycle_status FROM "
                "djconnect_persistent_sessions WHERE session_id=?", (session_id,)) == (owner_id, "ACTIVE"),
                "rich_not_allowed", 403)
            tx.execute("INSERT INTO djconnect_rich_purposes "
                "(scope_hash,operation_id,purpose_id,owner_hash,device_hash,entry_hash,"
                "pair_hash,session_hash,surface,request_hash,issued_ms,expires_ms,phase) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'reserved')", original.values())
            return original

        return await self._settle(write, current)

    async def issued(self, original, *, session_id, owner_id, current):
        """Acknowledgement before secret emission, not a recoverable permission."""
        require(type(original) is RichOriginal)
        original.validate()
        self._session_binding(original, session_id, owner_id)

        def write(tx):
            row = tx.fetchone(BY_SCOPE, (original.scope_hash,))
            stored = self._original(row)
            require(stored == original and row[-1] == "reserved", "rich_purpose_consumed", 409)
            require(tx.fetchone("SELECT owner_profile_id,lifecycle_status FROM "
                "djconnect_persistent_sessions WHERE session_id=?", (session_id,)) == (owner_id, "ACTIVE"),
                "rich_not_allowed", 403)
            tx.execute("UPDATE djconnect_rich_purposes SET phase='issued' "
                "WHERE scope_hash=? AND phase='reserved'",
                (original.scope_hash,))
            return original

        return await self._settle(write, current)

    async def history(self, operation_id, ownership, *, current, withdraw=False, scope_hash=None):
        """Negative access needs current original owner, never active Session.

        The real service synchronously fences its own RAM scope BEFORE calling
        withdraw. Metadata cannot release capacity or resurrect any secret.
        """
        require(type(ownership) is tuple and len(ownership) == 6)
        require(original_uuid(operation_id) if scope_hash is None else operation_id is None
            and type(scope_hash) is str and HASH.fullmatch(scope_hash) is not None)

        def read_or_withdraw(tx):
            row = tx.fetchone(BY_OPERATION if scope_hash is None else BY_SCOPE,
                (operation_id if scope_hash is None else scope_hash,))
            require(row is not None, "rich_history_unknown", 404)
            stored = self._original(row)
            require((stored.owner_hash, stored.device_hash, stored.entry_hash, stored.pair_hash,
                stored.session_hash, stored.surface) == ownership, "rich_history_unknown", 404)
            phase = row[-1]
            if withdraw and phase != "withdrawn":
                tx.execute("UPDATE djconnect_rich_purposes SET phase='withdrawn' WHERE operation_id=?", (stored.operation_id,))
                phase = "withdrawn"
            return stored, phase

        return await self._settle(read_or_withdraw, current)
