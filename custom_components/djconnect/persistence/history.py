"""Immutable renderer-safe historical Session projections."""
from __future__ import annotations
from dataclasses import dataclass
from uuid import uuid4
from .service import PersistenceRepository, PersistenceTransaction
from .sessions import PersistentSession
@dataclass(frozen=True)
class HistoricalSessionProjection:
    historical_session_id: str
    originating_session_id: str
    owner_profile_id: str
    lifecycle_outcome: str
    created_at: str
    projection_version: int = 1
class HistoricalProjectionRepository(PersistenceRepository):
    async def async_project_session(self, session: PersistentSession) -> HistoricalSessionProjection:
        projection = HistoricalSessionProjection(f"history-{uuid4().hex}", session.session_id, session.owner_profile_id, session.lifecycle_status, session.ended_at or session.interrupted_at or session.created_at)
        def write(tx: PersistenceTransaction) -> HistoricalSessionProjection:
            existing = tx.fetchone("SELECT historical_session_id,originating_session_id,owner_profile_id,lifecycle_outcome,created_at,projection_version FROM djconnect_historical_sessions WHERE originating_session_id=?", (session.session_id,))
            if existing is not None:
                return HistoricalSessionProjection(*[str(value) if index < 5 else int(value) for index, value in enumerate(existing)])
            tx.execute("INSERT OR IGNORE INTO djconnect_historical_sessions (historical_session_id,originating_session_id,owner_profile_id,lifecycle_outcome,started_at,ended_at,interrupted_at,interruption_reason,start_strategy,session_mood,session_direction,created_at,projection_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (projection.historical_session_id,session.session_id,session.owner_profile_id,session.lifecycle_status,session.started_at,session.ended_at,session.interrupted_at,session.interruption_reason,session.start_strategy,session.initial_mood,session.initial_direction,projection.created_at,1))
            return projection
        return await self._async_in_transaction(write)

    async def async_project_moment(self, *, session_id: str, moment_id: str, owner_profile_id: str, moment_type: str, rendered_text: str, presentation_metadata: str, ordering: int, created_at: str, visibility: str = "owner") -> str:
        """Persist one already-canonical renderer-safe Moment projection once."""
        identifier = f"historical-moment-{uuid4().hex}"
        def write(tx: PersistenceTransaction) -> str:
            existing = tx.fetchone("SELECT historical_moment_id FROM djconnect_historical_moments WHERE originating_session_id=? AND originating_moment_id=?", (session_id, moment_id))
            if existing is not None:
                return str(existing[0])
            tx.execute("INSERT INTO djconnect_historical_moments (historical_moment_id,originating_session_id,originating_moment_id,owner_profile_id,moment_type,rendered_text,presentation_metadata,visibility,ordering,created_at,projection_version) VALUES (?,?,?,?,?,?,?,?,?,?,1)", (identifier, session_id, moment_id, owner_profile_id, moment_type, rendered_text, presentation_metadata, visibility, ordering, created_at))
            return identifier
        return await self._async_in_transaction(write)
