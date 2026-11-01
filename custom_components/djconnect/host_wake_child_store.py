"""Schema21 once/history DATA on the actual FULL-sync platform SQLite.

No credential, APNs token, nonce or proof is stored. The real owning RAM child
must latch before calling this journal; a database row cannot recreate it.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .direct_rich_store import RichOriginal, RichPurposeJournal, BY_SCOPE
from .direct_rich_wire import HASH, digest, original_uuid, require, safe_integer
from . import host_wake_api_wire as api
from .host_wake_proxy_wire import request_sha256

MAX_CHILDREN = 4096
MAX_ATTEMPTS = 65536
PHASES = {"initial_reserved", "sealed", "issuing", "prepared", "challenging", "challenge_known",
    "completing", "verifying", "native_verified", "registering", "registered", "unknown", "withdrawn"}
COLUMNS = ("native_operation_id", "generation", "native_revision", "parent_binding_hash",
    "prepare_request_hash", "created_ms", "original_hash", "role_hash", "expires_ms",
    "phase", "cas_revision", "consumed_attempts")
SELECT = (
    "SELECT native_operation_id,generation,native_revision,parent_binding_hash,prepare_request_hash,"
    "created_ms,original_hash,role_hash,expires_ms,phase,cas_revision,consumed_attempts "
    "FROM djconnect_host_wake_children WHERE parent_purpose_id=?"
)
BEGIN = {
    "issuer_issue": ("sealed", "issuing"), "native_challenge": ("prepared", "challenging"),
    "native_complete": ("challenge_known", "completing"), "target_register": ("native_verified", "registering"),
    "target_wake": ("registered", "registered"),
}
FINISH = {
    "issuer_issue": {"prepared"}, "native_challenge": {"challenge_known"},
    "native_complete": {"verifying", "native_verified"}, "target_register": {"registered"},
    "target_wake": {"registered"},
}
READS = {"issuer_status", "native_status", "target_status"}


@dataclass(frozen=True, repr=False)
class ChildReservation:
    parent: RichOriginal
    native_operation_id: str
    generation: str
    prepare_request_hash: str
    created_ms: int

    @property
    def parent_hash(self):
        return digest(["DJC-HOST-WAKE-CHILD-PARENT-V1", *self.parent.values()])

    def validate(self):
        require(type(self.parent) is RichOriginal)
        self.parent.validate()
        require(original_uuid(self.native_operation_id) and self.native_operation_id != self.parent.operation_id
            and original_uuid(self.generation) and type(self.prepare_request_hash) is str
            and HASH.fullmatch(self.prepare_request_hash) and safe_integer(self.created_ms, 1)
            and self.parent.issued_ms <= self.created_ms < self.parent.expires_ms)


@dataclass(frozen=True, repr=False)
class ChildMetadata:
    """Historical metadata, deliberately no permission/credential/restore API."""
    original_hash: str | None
    role_hash: str | None
    expires_ms: int | None
    phase: str
    cas_revision: int
    consumed_attempts: int


@dataclass(frozen=True, repr=False)
class ChildAttempt:
    """Durable consumed attempt metadata, never effect permission by itself."""
    ordinal: int
    attempt_id: str
    kind: str
    semantic_hash: str
    request_hash: str
    pending_revision: int
    pending_phase: str


class HostWakeChildJournal:
    def __init__(self, persistence):
        self.storage = RichPurposeJournal(persistence)

    @staticmethod
    def _parent(tx, reservation, session_id, owner_id, *, positive):
        reservation.validate()
        parent = reservation.parent
        RichPurposeJournal._session_binding(parent, session_id, owner_id)
        row = tx.fetchone(BY_SCOPE, (parent.scope_hash,))
        require(RichPurposeJournal._original(row) == parent, "rich_not_allowed", 403)
        if positive:
            require(row[-1] == "issued" and tx.fetchone(
                "SELECT owner_profile_id,lifecycle_status FROM djconnect_persistent_sessions WHERE session_id=?",
                (session_id,)) == (owner_id, "ACTIVE"), "rich_not_allowed", 403)

    @staticmethod
    def _metadata(tx, reservation):
        row = tx.fetchone(SELECT, (reservation.parent.purpose_id,))
        require(row is not None and len(row) == len(COLUMNS), "rich_history_unknown", 404)
        require(row[:6] == (reservation.native_operation_id, reservation.generation, 1,
            reservation.parent_hash, reservation.prepare_request_hash, reservation.created_ms), "rich_not_allowed", 403)
        require(type(row[9]) is str and row[9] in PHASES
            and safe_integer(row[10]) and row[10] < api.SAFE
            and type(row[11]) is int and 1 <= row[11] <= 256,
            "rich_unavailable", 503)
        if row[6] is None or row[7] is None or row[8] is None:
            require(row[6:9] == (None, None, None) and row[9] in {"initial_reserved", "unknown", "withdrawn"},
                "rich_unavailable", 503)
        else:
            require(type(row[6]) is str and HASH.fullmatch(row[6]) and type(row[7]) is str and HASH.fullmatch(row[7])
                and safe_integer(row[8], reservation.created_ms + 1) and row[8] <= reservation.parent.expires_ms
                and row[9] != "initial_reserved", "rich_unavailable", 503)
        return ChildMetadata(*row[6:])

    async def reserve(self, reservation, *, session_id, owner_id, role_request_hash, attempt_id, current):
        """Persist the ORIGINAL pre-role reservation, never a placeholder tuple."""
        require(type(reservation) is ChildReservation)
        reservation.validate()
        require(type(role_request_hash) is str and HASH.fullmatch(role_request_hash) and original_uuid(attempt_id))

        def write(tx):
            self._parent(tx, reservation, session_id, owner_id, positive=True)
            require(tx.fetchone("SELECT 1 FROM djconnect_host_wake_children WHERE parent_purpose_id=? OR native_operation_id=?",
                (reservation.parent.purpose_id, reservation.native_operation_id)) is None, "rich_purpose_consumed", 409)
            require(tx.fetchone("SELECT count(*) FROM djconnect_host_wake_children")[0] < MAX_CHILDREN, "rich_capacity", 409)
            require(tx.fetchone("SELECT count(*) FROM djconnect_host_wake_attempts")[0] < MAX_ATTEMPTS, "rich_capacity", 409)
            tx.execute("INSERT INTO djconnect_host_wake_children (parent_purpose_id,native_operation_id,generation,"
                "native_revision,parent_binding_hash,prepare_request_hash,created_ms,phase,cas_revision,consumed_attempts) "
                "VALUES (?,?,?,1,?,?,?,'initial_reserved',0,1)", (reservation.parent.purpose_id,
                reservation.native_operation_id, reservation.generation, reservation.parent_hash,
                reservation.prepare_request_hash, reservation.created_ms))
            tx.execute("INSERT INTO djconnect_host_wake_attempts "
                "(parent_purpose_id,ordinal,attempt_id,kind,semantic_hash,request_hash,phase) "
                "VALUES (?,1,?,'role_resolve',?,?,'reserved')", (reservation.parent.purpose_id, attempt_id,
                digest(["DJC-HOST-WAKE-ONCE-V1", reservation.parent.purpose_id, "role_resolve"]), role_request_hash))
            return self._metadata(tx, reservation)

        return await self.storage._settle(write, current)

    async def seal(self, reservation, *, session_id, owner_id, prepare, sent_resolve, role, original, current):
        """One retained original after actual role reply, before issuer effect.

        This validates DATA joins. It is not a clock/native/operator supplier.
        The consuming service must have its independent genuine admission.
        """
        require(all(type(value) is dict for value in (prepare, sent_resolve, role, original)))
        prepare, sent_resolve, role, original = (deepcopy(value)
            for value in (prepare, sent_resolve, role, original))
        require(type(reservation) is ChildReservation)
        reservation.validate()
        api.request("authorization/resolve", sent_resolve)
        api.resolved(role, sent_resolve)
        api.original(original)
        require(request_sha256("prepare", prepare) == reservation.prepare_request_hash
            and prepare["purpose_id"] == reservation.parent.purpose_id
            and prepare["operation_id"] == reservation.native_operation_id
            and prepare["session_id"] == session_id and prepare["surface"] == reservation.parent.surface
            and digest(["DJC-DIRECT-RICH-DEVICE-V1", prepare["device_id"]]) == reservation.parent.device_hash
            and original["core_purpose_id"] == reservation.parent.purpose_id
            and original["operation_id"] == reservation.native_operation_id
            and original["generation"] == reservation.generation and original["revision"] == 1
            and original["owner_binding"] == reservation.parent.owner_hash
            and original["device_binding"] == reservation.parent.device_hash)
        for field in ("target", "platform", "apns_environment", "native_key_id_b64", "native_token_sha256"):
            require(original[field] == prepare[field])
        for field in api.BINDINGS | {"target", "platform", "apns_environment", "native_key_id_b64"}:
            require(original[field] == sent_resolve["scope"][field])
        for field in api.POLICY:
            require(original[field] == role[field])
        require(original["original_wake_issued_at_ms"] == reservation.created_ms
            and original["original_display_expires_at_ms"] == reservation.parent.expires_ms
            and role["original_authorization_issued_at_ms"] <= reservation.created_ms
            and original["original_wake_expires_at_ms"] <= min(reservation.parent.expires_ms,
                role["original_authorization_expires_at_ms"], reservation.created_ms + role["max_original_purpose_ms"]))

        def write(tx):
            self._parent(tx, reservation, session_id, owner_id, positive=True)
            stored = self._metadata(tx, reservation)
            require(stored.phase == "initial_reserved" and stored.cas_revision == 0
                and stored.original_hash is None, "rich_purpose_consumed", 409)
            row = tx.fetchone("SELECT request_hash,phase FROM djconnect_host_wake_attempts "
                "WHERE parent_purpose_id=? AND ordinal=1 AND kind='role_resolve'", (reservation.parent.purpose_id,))
            require(row == (api.request_hash("authorization/resolve", sent_resolve), "reserved"), "rich_not_allowed", 403)
            tx.execute("UPDATE djconnect_host_wake_attempts SET phase='completed',result_hash=? "
                "WHERE parent_purpose_id=? AND ordinal=1", (digest(role), reservation.parent.purpose_id))
            tx.execute("UPDATE djconnect_host_wake_children SET original_hash=?,role_hash=?,expires_ms=?,"
                "phase='sealed',cas_revision=1 WHERE parent_purpose_id=? AND cas_revision=0",
                (digest(original), digest(role), original["original_wake_expires_at_ms"], reservation.parent.purpose_id))
            return self._metadata(tx, reservation)

        return await self.storage._settle(write, current)

    async def begin(self, reservation, *, expected_revision, kind, semantic_hash, request_hash, attempt_id,
                    session_id, owner_id, current, maximum_wakes=64):
        """Consume exact stage/event BEFORE IO, under the original parent/CAS.

        The owning RAM child must independently select actual semantic event
        identities; callers cannot supply permission or repair a spent stage.
        """
        require(type(reservation) is ChildReservation)
        reservation.validate()
        require(safe_integer(expected_revision) and type(kind) is str and kind in BEGIN.keys() | READS
            and original_uuid(attempt_id))
        require(all(type(value) is str and HASH.fullmatch(value) for value in (semantic_hash, request_hash)))

        def write(tx):
            self._parent(tx, reservation, session_id, owner_id, positive=kind not in READS)
            stored = self._metadata(tx, reservation)
            require(stored.cas_revision == expected_revision and stored.original_hash is not None,
                "rich_purpose_consumed", 409)
            if kind in BEGIN:
                expected, phase = BEGIN[kind]
                require(stored.phase == expected, "rich_purpose_consumed", 409)
                if kind == "target_wake":
                    require(type(maximum_wakes) is int and 1 <= maximum_wakes <= 64
                        and tx.fetchone("SELECT count(*) FROM djconnect_host_wake_attempts "
                            "WHERE parent_purpose_id=? AND kind='target_wake'",
                            (reservation.parent.purpose_id,))[0] < maximum_wakes, "rich_capacity", 409)
            else:
                phase = stored.phase
            require(stored.consumed_attempts < 256 and stored.cas_revision < api.SAFE - 1
                and tx.fetchone("SELECT count(*) FROM djconnect_host_wake_attempts")[0] < MAX_ATTEMPTS,
                "rich_capacity", 409)
            require(tx.fetchone("SELECT 1 FROM djconnect_host_wake_attempts WHERE attempt_id=? OR "
                "(parent_purpose_id=? AND kind=? AND semantic_hash=?)",
                (attempt_id, reservation.parent.purpose_id, kind, semantic_hash)) is None, "rich_purpose_consumed", 409)
            ordinal, revision = stored.consumed_attempts + 1, stored.cas_revision + 1
            tx.execute("INSERT INTO djconnect_host_wake_attempts "
                "(parent_purpose_id,ordinal,attempt_id,kind,semantic_hash,request_hash,phase) "
                "VALUES (?,?,?,?,?,?,'reserved')", (reservation.parent.purpose_id, ordinal, attempt_id,
                    kind, semantic_hash, request_hash))
            tx.execute("UPDATE djconnect_host_wake_children SET phase=?,cas_revision=?,consumed_attempts=? "
                "WHERE parent_purpose_id=? AND cas_revision=?", (phase, revision, ordinal,
                    reservation.parent.purpose_id, expected_revision))
            return ChildAttempt(ordinal, attempt_id, kind, semantic_hash, request_hash, revision, phase)

        return await self.storage._settle(write, current)

    async def finish(self, reservation, attempt, *, destination, result_hash, session_id, owner_id, current):
        """Only the exact pending claim can record its validated original ACK.

        Status can finish only a known acknowledged pending native job, never
        issuer/cold/UNKNOWN history or a target without its registration ACK.
        """
        require(type(reservation) is ChildReservation and type(attempt) is ChildAttempt)
        reservation.validate()
        require(type(destination) is str and destination in PHASES
            and type(result_hash) is str and HASH.fullmatch(result_hash))

        def write(tx):
            self._parent(tx, reservation, session_id, owner_id,
                positive=attempt.kind not in READS or destination == "native_verified")
            stored = self._metadata(tx, reservation)
            require(stored.cas_revision == attempt.pending_revision and stored.phase == attempt.pending_phase,
                "rich_purpose_consumed", 409)
            row = tx.fetchone("SELECT attempt_id,kind,semantic_hash,request_hash,phase FROM djconnect_host_wake_attempts "
                "WHERE parent_purpose_id=? AND ordinal=?", (reservation.parent.purpose_id, attempt.ordinal))
            require(row == (attempt.attempt_id, attempt.kind, attempt.semantic_hash, attempt.request_hash, "reserved"),
                "rich_purpose_consumed", 409)
            if attempt.kind in FINISH:
                require(destination in FINISH[attempt.kind], "rich_not_allowed", 403)
            else:
                require(attempt.kind in READS, "rich_not_allowed", 403)
                # The only read-driven advance is completion of an ACKNOWLEDGED
                # original native pending job. No cold/unknown/issuer shortcut.
                allowed = {stored.phase, "unknown", "withdrawn"}
                if attempt.kind == "native_status" and stored.phase == "verifying":
                    require(tx.fetchone("SELECT 1 FROM djconnect_host_wake_attempts WHERE parent_purpose_id=? "
                        "AND kind='native_complete' AND phase='completed'", (reservation.parent.purpose_id,)) is not None,
                        "rich_not_allowed", 403)
                    allowed.add("native_verified")
                require(destination in allowed, "rich_not_allowed", 403)
                if stored.phase == "withdrawn":
                    require(destination == "withdrawn", "rich_not_allowed", 403)
            tx.execute("UPDATE djconnect_host_wake_attempts SET phase='completed',result_hash=? "
                "WHERE parent_purpose_id=? AND ordinal=? AND attempt_id=? AND phase='reserved'",
                (result_hash, reservation.parent.purpose_id, attempt.ordinal, attempt.attempt_id))
            tx.execute("UPDATE djconnect_host_wake_children SET phase=?,cas_revision=cas_revision+1 "
                "WHERE parent_purpose_id=? AND cas_revision=?", (destination, reservation.parent.purpose_id,
                    attempt.pending_revision))
            return self._metadata(tx, reservation)

        return await self.storage._settle(write, current)

    async def unknown(self, reservation, *, session_id, owner_id, current):
        """Local uncertainty spends the child; existing completed facts remain.

        Call only after synchronous RAM closure. This has no new attempt/quota
        and cannot reopen a withdrawn or original consumed stage.
        """
        require(type(reservation) is ChildReservation)
        reservation.validate()

        def write(tx):
            self._parent(tx, reservation, session_id, owner_id, positive=False)
            self._metadata(tx, reservation)
            tx.execute("UPDATE djconnect_host_wake_children SET phase='unknown',cas_revision=cas_revision+1 "
                "WHERE parent_purpose_id=? AND phase NOT IN ('unknown','withdrawn')", (reservation.parent.purpose_id,))
            tx.execute("UPDATE djconnect_host_wake_attempts SET phase='unknown',result_hash=NULL "
                "WHERE parent_purpose_id=? AND phase='reserved'", (reservation.parent.purpose_id,))
            return self._metadata(tx, reservation)

        return await self.storage._settle(write, current)

    async def history(self, reservation, *, session_id, owner_id, current, withdraw=False):
        """Prebound negative/history authority; no ACTIVE Session requirement.

        Withdrawal updates already reserved terminal space outside the positive
        attempt quota. Runtime must synchronously close RAM before this await.
        """
        require(type(reservation) is ChildReservation)
        reservation.validate()

        def write(tx):
            self._parent(tx, reservation, session_id, owner_id, positive=False)
            stored = self._metadata(tx, reservation)
            if withdraw and stored.phase != "withdrawn":
                tx.execute("UPDATE djconnect_host_wake_children SET phase='withdrawn',cas_revision=cas_revision+1 "
                    "WHERE parent_purpose_id=?", (reservation.parent.purpose_id,))
                tx.execute("UPDATE djconnect_host_wake_attempts SET phase='unknown',result_hash=NULL "
                    "WHERE parent_purpose_id=? AND phase='reserved'", (reservation.parent.purpose_id,))
            return self._metadata(tx, reservation)

        return await self.storage._settle(write, current)
