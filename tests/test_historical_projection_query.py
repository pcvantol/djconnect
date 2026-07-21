"""Contract tests for the transport-independent historical projection queries."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import tempfile
import types
import unittest

package = types.ModuleType("custom_components.djconnect")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")]
sys.modules.setdefault("custom_components.djconnect", package)

from custom_components.djconnect.historical_projection_query import (  # noqa: E402
    HistoricalProjectionAccessDenied,
    HistoricalProjectionQueryService,
    HistoricalProjectionVersionUnsupported,
)
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.sessions import (  # noqa: E402
    ACTIVE,
    ENDED,
    PersistentSessionRepository,
)


class HistoricalProjectionQueryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.service = PersistenceService(
            Path(self.temp.name) / "djconnect.sqlite3", SQLitePersistenceProvider()
        )
        asyncio.run(self.service.async_initialize())
        self.sessions = PersistentSessionRepository(self.service)
        self.repository = HistoricalProjectionRepository(self.service)
        self.queries = HistoricalProjectionQueryService(self.repository)

    def tearDown(self) -> None:
        asyncio.run(self.service.async_close())
        self.temp.cleanup()

    def _project_session(self, session_id: str, owner: str, created_at: str):
        asyncio.run(self.sessions.async_create(owner, session_id=session_id))
        active = asyncio.run(self.sessions.async_transition(owner, session_id, ACTIVE))
        ended = asyncio.run(self.sessions.async_transition(owner, active.session_id, ENDED))
        projection = asyncio.run(self.repository.async_project_session(ended))
        asyncio.run(self.service.async_in_transaction(
            lambda tx: tx.execute(
                "UPDATE djconnect_historical_sessions SET created_at=? "
                "WHERE historical_session_id=?", (created_at, projection.historical_session_id)
            )
        ))
        return asyncio.run(self.repository.async_get_session(projection.historical_session_id))

    def test_owner_session_lookup_and_recent_ordering(self) -> None:
        older = self._project_session("session-old", "profile-a", "2026-01-01T00:00:00+00:00")
        newer = self._project_session("session-new", "profile-a", "2026-01-02T00:00:00+00:00")
        by_id = asyncio.run(self.queries.async_get_session("profile-a", newer.historical_session_id))
        by_source = asyncio.run(self.queries.async_get_owner_session("profile-a", "session-old"))
        recent = asyncio.run(self.queries.async_list_recent_owner_sessions("profile-a"))
        self.assertEqual(by_id, newer)
        self.assertEqual(by_source, older)
        self.assertEqual([item.historical_session_id for item in recent], [newer.historical_session_id, older.historical_session_id])

    def test_owner_moment_lookup_and_canonical_ordering(self) -> None:
        session = self._project_session("session-a", "profile-a", "2026-01-01T00:00:00+00:00")
        later = asyncio.run(self.repository.async_project_moment(
            session_id="session-a", moment_id="later", owner_profile_id="profile-a",
            moment_type="track", rendered_text="Later", presentation_metadata="{}", ordering=2,
            created_at="2026-01-01T00:00:02+00:00",
        ))
        first = asyncio.run(self.repository.async_project_moment(
            session_id="session-a", moment_id="first", owner_profile_id="profile-a",
            moment_type="track", rendered_text="First", presentation_metadata="{}", ordering=1,
            created_at="2026-01-01T00:00:01+00:00",
        ))
        moment = asyncio.run(self.queries.async_get_moment("profile-a", later))
        moments = asyncio.run(self.queries.async_list_session_moments("profile-a", session.historical_session_id))
        self.assertEqual(moment.historical_moment_id, later)
        self.assertEqual([item.historical_moment_id for item in moments], [first, later])

    def test_unauthorized_owner_access_is_rejected(self) -> None:
        session = self._project_session("session-a", "profile-a", "2026-01-01T00:00:00+00:00")
        moment = asyncio.run(self.repository.async_project_moment(
            session_id="session-a", moment_id="moment-a", owner_profile_id="profile-a",
            moment_type="track", rendered_text="Safe", presentation_metadata="{}", ordering=0,
            created_at="2026-01-01T00:00:00+00:00",
        ))
        with self.assertRaises(HistoricalProjectionAccessDenied):
            asyncio.run(self.queries.async_get_session("profile-b", session.historical_session_id))
        with self.assertRaises(HistoricalProjectionAccessDenied):
            asyncio.run(self.queries.async_get_moment("profile-b", moment))

    def test_non_owner_visibility_is_not_yet_exposed(self) -> None:
        moment = asyncio.run(self.repository.async_project_moment(
            session_id="session-a", moment_id="shared-moment", owner_profile_id="profile-a",
            moment_type="track", rendered_text="Safe", presentation_metadata="{}", ordering=0,
            created_at="2026-01-01T00:00:00+00:00", visibility="household",
        ))
        with self.assertRaises(HistoricalProjectionAccessDenied):
            asyncio.run(self.queries.async_get_moment("profile-a", moment))

    def test_only_compatible_immutable_owner_projections_are_returned(self) -> None:
        session = self._project_session("session-a", "profile-a", "2026-01-01T00:00:00+00:00")
        projection = asyncio.run(self.queries.async_get_session("profile-a", session.historical_session_id))
        with self.assertRaises(FrozenInstanceError):
            projection.lifecycle_outcome = "changed"  # type: ignore[misc]
        asyncio.run(self.service.async_in_transaction(
            lambda tx: tx.execute(
                "UPDATE djconnect_historical_sessions SET projection_version=99 "
                "WHERE historical_session_id=?", (session.historical_session_id,)
            )
        ))
        with self.assertRaises(HistoricalProjectionVersionUnsupported):
            asyncio.run(self.queries.async_get_session("profile-a", session.historical_session_id))

    def test_query_service_preserves_repository_abstraction(self) -> None:
        source = Path(
            Path(__file__).resolve().parents[1]
            / "custom_components/djconnect/historical_projection_query.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("SELECT ", source)
        self.assertNotIn("PersistenceTransaction", source)
