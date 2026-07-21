"""Transport-independent owner query contracts for historical projections."""

from __future__ import annotations

from .persistence.history import (
    HistoricalDJMomentProjection,
    HistoricalProjectionRepository,
    HistoricalSessionProjection,
)


SUPPORTED_PROJECTION_VERSIONS = frozenset({1})


class HistoricalProjectionAccessDenied(PermissionError):
    """Raised when a caller tries to access another owner's history."""


class HistoricalProjectionVersionUnsupported(ValueError):
    """Raised when a durable projection cannot satisfy this app contract."""


class HistoricalProjectionQueryService:
    """Apply canonical owner-only history visibility above storage repositories."""

    def __init__(self, repository: HistoricalProjectionRepository) -> None:
        self._repository = repository

    async def async_get_session(
        self, requester_profile_id: str, historical_session_id: str
    ) -> HistoricalSessionProjection | None:
        """Load one owner-visible historical Session by its projection ID."""
        projection = await self._repository.async_get_session(historical_session_id)
        return self._authorize_session(requester_profile_id, projection)

    async def async_get_owner_session(
        self, requester_profile_id: str, originating_session_id: str
    ) -> HistoricalSessionProjection | None:
        """Load one owner-visible historical Session by its source Session ID."""
        projection = await self._repository.async_get_session_for_originating_id(
            originating_session_id
        )
        return self._authorize_session(requester_profile_id, projection)

    async def async_list_recent_owner_sessions(
        self, requester_profile_id: str
    ) -> tuple[HistoricalSessionProjection, ...]:
        """List an owner's historical Sessions in canonical recent-first order."""
        projections = await self._repository.async_list_sessions_for_owner(requester_profile_id)
        return tuple(
            self._authorize_session(requester_profile_id, projection)
            for projection in projections
            if projection is not None
        )

    async def async_get_moment(
        self, requester_profile_id: str, historical_moment_id: str
    ) -> HistoricalDJMomentProjection | None:
        """Load one owner-visible, owner-only historical DJMoment."""
        projection = await self._repository.async_get_moment(historical_moment_id)
        return self._authorize_moment(requester_profile_id, projection)

    async def async_list_session_moments(
        self, requester_profile_id: str, historical_session_id: str
    ) -> tuple[HistoricalDJMomentProjection, ...]:
        """List owner-visible DJMoments for one owner-visible historical Session."""
        session = await self.async_get_session(requester_profile_id, historical_session_id)
        if session is None:
            return ()
        projections = await self._repository.async_list_moments_for_session(
            session.originating_session_id
        )
        return tuple(
            self._authorize_moment(requester_profile_id, projection)
            for projection in projections
            if projection is not None
        )

    @staticmethod
    def _authorize_session(
        requester_profile_id: str, projection: HistoricalSessionProjection | None
    ) -> HistoricalSessionProjection | None:
        if projection is None:
            return None
        HistoricalProjectionQueryService._authorize_owner(
            requester_profile_id, projection.owner_profile_id
        )
        HistoricalProjectionQueryService._ensure_supported_version(projection.projection_version)
        return projection

    @staticmethod
    def _authorize_moment(
        requester_profile_id: str, projection: HistoricalDJMomentProjection | None
    ) -> HistoricalDJMomentProjection | None:
        if projection is None:
            return None
        HistoricalProjectionQueryService._authorize_owner(
            requester_profile_id, projection.owner_profile_id
        )
        if projection.visibility != "owner":
            raise HistoricalProjectionAccessDenied("historical_moment_visibility_not_supported")
        HistoricalProjectionQueryService._ensure_supported_version(projection.projection_version)
        return projection

    @staticmethod
    def _authorize_owner(requester_profile_id: str, owner_profile_id: str) -> None:
        if requester_profile_id != owner_profile_id:
            raise HistoricalProjectionAccessDenied("historical_projection_owner_mismatch")

    @staticmethod
    def _ensure_supported_version(projection_version: int) -> None:
        if projection_version not in SUPPORTED_PROJECTION_VERSIONS:
            raise HistoricalProjectionVersionUnsupported(
                f"unsupported_historical_projection_version:{projection_version}"
            )
