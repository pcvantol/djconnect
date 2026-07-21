"""Profile-owned persistent Session lifecycle store."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4
from .service import PersistenceRepository, PersistenceTransaction

OPENING, ACTIVE, ENDED, INTERRUPTED = "OPENING", "ACTIVE", "ENDED", "INTERRUPTED"
_TRANSITIONS = {
    OPENING: {ACTIVE, INTERRUPTED},
    ACTIVE: {ENDED, INTERRUPTED},
    ENDED: set(),
    INTERRUPTED: set(),
}


class SessionLifecycleError(ValueError):
    pass


class SessionOwnershipError(SessionLifecycleError):
    pass


@dataclass(frozen=True)
class PersistentSession:
    session_id: str
    owner_profile_id: str
    lifecycle_status: str
    created_at: str
    started_at: str = ""
    ended_at: str = ""
    interrupted_at: str = ""
    interruption_reason: str = ""
    start_strategy: str = ""
    initial_mood: str = ""
    initial_direction: str = ""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class PersistentSessionRepository(PersistenceRepository):
    async def async_create(
        self,
        owner_profile_id: str,
        *,
        session_id: str | None = None,
        start_strategy: str = "",
        initial_mood: str = "",
        initial_direction: str = "",
    ) -> PersistentSession:
        identifier = session_id or f"session-{uuid4().hex}"
        now = _now()

        def operation(tx: PersistenceTransaction) -> PersistentSession:
            tx.execute(
                "INSERT INTO djconnect_persistent_sessions (session_id,owner_profile_id,lifecycle_status,created_at,updated_at,start_strategy,initial_mood,initial_direction) VALUES (?,?,?,?,?,?,?,?)",
                (
                    identifier,
                    owner_profile_id,
                    OPENING,
                    now,
                    now,
                    start_strategy,
                    initial_mood,
                    initial_direction,
                ),
            )
            return PersistentSession(
                identifier,
                owner_profile_id,
                OPENING,
                now,
                start_strategy=start_strategy,
                initial_mood=initial_mood,
                initial_direction=initial_direction,
            )

        return await self._async_in_transaction(operation)

    async def async_transition(
        self, owner_profile_id: str, session_id: str, target: str, *, reason: str = ""
    ) -> PersistentSession:
        def operation(tx: PersistenceTransaction) -> PersistentSession:
            row = tx.fetchone(
                "SELECT owner_profile_id,lifecycle_status,created_at,started_at,ended_at,interrupted_at,interruption_reason,start_strategy,initial_mood,initial_direction FROM djconnect_persistent_sessions WHERE session_id=?",
                (session_id,),
            )
            if row is None:
                raise SessionLifecycleError("unknown_session")
            if str(row[0]) != owner_profile_id:
                raise SessionOwnershipError("session_owner_mismatch")
            status = str(row[1])
            if status == target and status in {ENDED, INTERRUPTED}:
                return PersistentSession(
                    session_id,
                    owner_profile_id,
                    status,
                    str(row[2]),
                    str(row[3]),
                    str(row[4]),
                    str(row[5]),
                    str(row[6]),
                    str(row[7]),
                    str(row[8]),
                    str(row[9]),
                )
            if target not in _TRANSITIONS.get(status, set()):
                raise SessionLifecycleError(f"illegal_transition:{status}:{target}")
            now = _now()
            started = now if target == ACTIVE else str(row[3])
            ended = now if target == ENDED else str(row[4])
            interrupted = now if target == INTERRUPTED else str(row[5])
            interruption_reason = reason if target == INTERRUPTED else str(row[6])
            tx.execute(
                "UPDATE djconnect_persistent_sessions SET lifecycle_status=?,started_at=?,ended_at=?,interrupted_at=?,interruption_reason=?,updated_at=? WHERE session_id=?",
                (target, started, ended, interrupted, interruption_reason, now, session_id),
            )
            return PersistentSession(
                session_id,
                owner_profile_id,
                target,
                str(row[2]),
                started,
                ended,
                interrupted,
                interruption_reason,
                str(row[7]),
                str(row[8]),
                str(row[9]),
            )

        return await self._async_in_transaction(operation)

    async def async_non_terminal(self) -> list[str]:
        # Future reconciliation owns detailed processing; this bounded query exposes identifiers only.
        return await self._async_in_transaction(
            lambda tx: [
                str(row[0])
                for row in tx.fetchall(
                    "SELECT session_id FROM djconnect_persistent_sessions "
                    "WHERE lifecycle_status IN ('OPENING','ACTIVE') ORDER BY created_at"
                )
            ]
        )

    async def async_reconciliation_candidates(self) -> list[PersistentSession]:
        return await self._async_in_transaction(lambda tx: [
            PersistentSession(*[str(value) for value in row])
            for row in tx.fetchall("SELECT session_id,owner_profile_id,lifecycle_status,created_at,started_at,ended_at,interrupted_at,interruption_reason,start_strategy,initial_mood,initial_direction FROM djconnect_persistent_sessions WHERE lifecycle_status IN ('OPENING','ACTIVE') ORDER BY created_at")
        ])
