"""Immutable renderer-safe historical Session and DJMoment projections."""

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


@dataclass(frozen=True)
class HistoricalDJMomentProjection:
    """A durable, renderer-safe historical DJMoment projection."""

    historical_moment_id: str
    originating_session_id: str
    originating_moment_id: str
    owner_profile_id: str
    moment_type: str
    rendered_text: str
    presentation_metadata: str
    visibility: str
    ordering: int
    created_at: str
    projection_version: int = 1


class HistoricalProjectionRepository(PersistenceRepository):
    async def async_cleanup_expired(
        self, *, cutoff: str, batch_size: int
    ) -> tuple[int, int, int, int]:
        """Delete expired Moments before Sessions, plus expired orphan Moments."""
        def cleanup(tx: PersistenceTransaction) -> tuple[int, int, int, int]:
            orphan_rows = tx.fetchall(
                "SELECT historical_moment_id FROM djconnect_historical_moments "
                "WHERE created_at < ? AND NOT EXISTS (SELECT 1 FROM djconnect_historical_sessions "
                "WHERE originating_session_id=djconnect_historical_moments.originating_session_id) "
                "ORDER BY created_at, historical_moment_id LIMIT ?",
                (cutoff, batch_size),
            )
            for row in orphan_rows:
                tx.execute("DELETE FROM djconnect_historical_moments WHERE historical_moment_id=?", (row[0],))
            session_rows = tx.fetchall(
                "SELECT originating_session_id FROM djconnect_historical_sessions WHERE created_at < ? "
                "ORDER BY created_at, historical_session_id LIMIT ?",
                (cutoff, batch_size),
            )
            deleted_moments = len(orphan_rows)
            for row in session_rows:
                session_id = str(row[0])
                moments = tx.fetchall(
                    "SELECT historical_moment_id FROM djconnect_historical_moments "
                    "WHERE originating_session_id=?", (session_id,)
                )
                for moment in moments:
                    tx.execute("DELETE FROM djconnect_historical_moments WHERE historical_moment_id=?", (moment[0],))
                deleted_moments += len(moments)
                tx.execute("DELETE FROM djconnect_historical_sessions WHERE originating_session_id=?", (session_id,))
            return len(session_rows), deleted_moments, len(orphan_rows), len(session_rows)

        return await self._async_in_transaction(cleanup)
    async def async_project_session(self, session: PersistentSession) -> HistoricalSessionProjection:
        projection = HistoricalSessionProjection(
            f"history-{uuid4().hex}",
            session.session_id,
            session.owner_profile_id,
            session.lifecycle_status,
            session.ended_at or session.interrupted_at or session.created_at,
        )

        def write(tx: PersistenceTransaction) -> HistoricalSessionProjection:
            existing = tx.fetchone(
                "SELECT historical_session_id, originating_session_id, owner_profile_id, "
                "lifecycle_outcome, created_at, projection_version "
                "FROM djconnect_historical_sessions WHERE originating_session_id=?",
                (session.session_id,),
            )
            if existing is not None:
                return self._session_from_row(existing)
            tx.execute(
                "INSERT OR IGNORE INTO djconnect_historical_sessions "
                "(historical_session_id, originating_session_id, owner_profile_id, "
                "lifecycle_outcome, started_at, ended_at, interrupted_at, interruption_reason, "
                "start_strategy, session_mood, session_direction, created_at, projection_version) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    projection.historical_session_id, session.session_id, session.owner_profile_id,
                    session.lifecycle_status, session.started_at, session.ended_at, session.interrupted_at,
                    session.interruption_reason, session.start_strategy, session.initial_mood,
                    session.initial_direction, projection.created_at, 1,
                ),
            )
            return projection

        return await self._async_in_transaction(write)

    async def async_project_moment(
        self,
        *,
        session_id: str,
        moment_id: str,
        owner_profile_id: str,
        moment_type: str,
        rendered_text: str,
        presentation_metadata: str,
        ordering: int,
        created_at: str,
        visibility: str = "owner",
    ) -> str:
        """Persist one already-canonical renderer-safe Moment projection once."""
        identifier = f"historical-moment-{uuid4().hex}"
        def write(tx: PersistenceTransaction) -> str:
            existing = tx.fetchone(
                "SELECT historical_moment_id FROM djconnect_historical_moments "
                "WHERE originating_session_id=? AND originating_moment_id=?",
                (session_id, moment_id),
            )
            if existing is not None:
                return str(existing[0])
            tx.execute(
                "INSERT INTO djconnect_historical_moments "
                "(historical_moment_id, originating_session_id, originating_moment_id, owner_profile_id, "
                "moment_type, rendered_text, presentation_metadata, visibility, ordering, created_at, "
                "projection_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (identifier, session_id, moment_id, owner_profile_id, moment_type, rendered_text,
                 presentation_metadata, visibility, ordering, created_at),
            )
            return identifier

        return await self._async_in_transaction(write)

    async def async_get_session(
        self, historical_session_id: str
    ) -> HistoricalSessionProjection | None:
        """Load one historical Session projection without applying policy."""
        return await self._async_in_transaction(
            lambda tx: self._optional_session(
                tx.fetchone(
                    "SELECT historical_session_id, originating_session_id, owner_profile_id, "
                    "lifecycle_outcome, created_at, projection_version "
                    "FROM djconnect_historical_sessions WHERE historical_session_id=?",
                    (historical_session_id,),
                )
            )
        )

    async def async_get_session_for_originating_id(
        self, originating_session_id: str
    ) -> HistoricalSessionProjection | None:
        """Load one historical Session by its durable source identifier."""
        return await self._async_in_transaction(
            lambda tx: self._optional_session(
                tx.fetchone(
                    "SELECT historical_session_id, originating_session_id, owner_profile_id, "
                    "lifecycle_outcome, created_at, projection_version "
                    "FROM djconnect_historical_sessions WHERE originating_session_id=?",
                    (originating_session_id,),
                )
            )
        )

    async def async_list_sessions_for_owner(
        self, owner_profile_id: str
    ) -> tuple[HistoricalSessionProjection, ...]:
        """Load one owner's Sessions in canonical recent-first order."""
        return await self._async_in_transaction(
            lambda tx: tuple(
                self._session_from_row(row)
                for row in tx.fetchall(
                    "SELECT historical_session_id, originating_session_id, owner_profile_id, "
                    "lifecycle_outcome, created_at, projection_version "
                    "FROM djconnect_historical_sessions WHERE owner_profile_id=? "
                    "ORDER BY created_at DESC, historical_session_id DESC",
                    (owner_profile_id,),
                )
            )
        )

    async def async_get_moment(
        self, historical_moment_id: str
    ) -> HistoricalDJMomentProjection | None:
        """Load one historical DJMoment projection without applying policy."""
        return await self._async_in_transaction(
            lambda tx: self._optional_moment(
                tx.fetchone(
                    self._MOMENT_SELECT + " WHERE historical_moment_id=?",
                    (historical_moment_id,),
                )
            )
        )

    async def async_list_moments_for_session(
        self, originating_session_id: str
    ) -> tuple[HistoricalDJMomentProjection, ...]:
        """Load one Session's Moments in canonical renderer order."""
        return await self._async_in_transaction(
            lambda tx: tuple(
                self._moment_from_row(row)
                for row in tx.fetchall(
                    self._MOMENT_SELECT
                    + " WHERE originating_session_id=? "
                    "ORDER BY ordering ASC, created_at ASC, historical_moment_id ASC",
                    (originating_session_id,),
                )
            )
        )

    _MOMENT_SELECT = (
        "SELECT historical_moment_id, originating_session_id, originating_moment_id, "
        "owner_profile_id, moment_type, rendered_text, presentation_metadata, visibility, "
        "ordering, created_at, projection_version FROM djconnect_historical_moments"
    )

    @staticmethod
    def _session_from_row(row: tuple[object, ...]) -> HistoricalSessionProjection:
        return HistoricalSessionProjection(
            *(str(value) if index < 5 else int(value) for index, value in enumerate(row))
        )

    @classmethod
    def _optional_session(
        cls, row: tuple[object, ...] | None
    ) -> HistoricalSessionProjection | None:
        return cls._session_from_row(row) if row is not None else None

    @staticmethod
    def _moment_from_row(row: tuple[object, ...]) -> HistoricalDJMomentProjection:
        return HistoricalDJMomentProjection(
            *(str(value) if index < 10 else int(value) for index, value in enumerate(row))
        )

    @classmethod
    def _optional_moment(
        cls, row: tuple[object, ...] | None
    ) -> HistoricalDJMomentProjection | None:
        return cls._moment_from_row(row) if row is not None else None
