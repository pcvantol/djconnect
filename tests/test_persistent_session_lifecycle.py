"""Tests for the Profile-owned durable Session lifecycle."""

from __future__ import annotations
import asyncio
from pathlib import Path
import sys
import tempfile
import types
import unittest

package = types.ModuleType("custom_components.djconnect")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")]
sys.modules.setdefault("custom_components.djconnect", package)
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.sessions import (  # noqa: E402
    ACTIVE,
    ENDED,
    INTERRUPTED,
    OPENING,
    PersistentSessionRepository,
    SessionLifecycleError,
    SessionOwnershipError,
)
from custom_components.djconnect.persistence.reconciliation import (  # noqa: E402
    PersistentSessionStartupReconciler,
)
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402


class PersistentSessionLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.service = PersistenceService(
            Path(self.temp.name) / "djconnect.sqlite3", SQLitePersistenceProvider()
        )
        asyncio.run(self.service.async_initialize())
        self.sessions = PersistentSessionRepository(self.service)

    def tearDown(self) -> None:
        asyncio.run(self.service.async_close())
        self.temp.cleanup()

    def test_legal_lifecycle_and_terminal_idempotency(self) -> None:
        created = asyncio.run(self.sessions.async_create("profile-a", session_id="session-a"))
        active = asyncio.run(
            self.sessions.async_transition("profile-a", created.session_id, ACTIVE)
        )
        ended = asyncio.run(self.sessions.async_transition("profile-a", created.session_id, ENDED))
        duplicate = asyncio.run(
            self.sessions.async_transition("profile-a", created.session_id, ENDED)
        )
        self.assertEqual(
            (created.lifecycle_status, active.lifecycle_status, ended.lifecycle_status),
            (OPENING, ACTIVE, ENDED),
        )
        self.assertEqual(duplicate.lifecycle_status, ENDED)
        with self.assertRaises(SessionLifecycleError):
            asyncio.run(self.sessions.async_transition("profile-a", created.session_id, ACTIVE))

    def test_interruption_ownership_and_non_terminal_lookup(self) -> None:
        opening = asyncio.run(self.sessions.async_create("profile-a", session_id="session-opening"))
        active = asyncio.run(self.sessions.async_create("profile-a", session_id="session-active"))
        asyncio.run(self.sessions.async_transition("profile-a", active.session_id, ACTIVE))
        self.assertEqual(
            asyncio.run(self.sessions.async_non_terminal()), [opening.session_id, active.session_id]
        )
        with self.assertRaises(SessionOwnershipError):
            asyncio.run(
                self.sessions.async_transition("profile-b", opening.session_id, INTERRUPTED)
            )
        interrupted = asyncio.run(
            self.sessions.async_transition(
                "profile-a", opening.session_id, INTERRUPTED, reason="startup_failed"
            )
        )
        self.assertEqual(interrupted.interruption_reason, "startup_failed")

    def test_startup_reconciliation_interrupts_candidates_once(self) -> None:
        asyncio.run(self.sessions.async_create("profile-a", session_id="opening"))
        active = asyncio.run(self.sessions.async_create("profile-b", session_id="active"))
        asyncio.run(self.sessions.async_transition("profile-b", active.session_id, ACTIVE))
        ended = asyncio.run(self.sessions.async_create("profile-c", session_id="ended"))
        asyncio.run(self.sessions.async_transition("profile-c", ended.session_id, ACTIVE))
        ended = asyncio.run(self.sessions.async_transition("profile-c", ended.session_id, ENDED))

        first = asyncio.run(PersistentSessionStartupReconciler(self.sessions).async_reconcile())
        second = asyncio.run(PersistentSessionStartupReconciler(self.sessions).async_reconcile())

        self.assertEqual((first.inspected, first.interrupted), (2, 2))
        self.assertEqual((second.inspected, second.interrupted), (0, 0))
        self.assertEqual(ended.lifecycle_status, ENDED)
        self.assertEqual(asyncio.run(self.sessions.async_non_terminal()), [])

    def test_terminal_session_projects_idempotently_without_runtime_state(self) -> None:
        created = asyncio.run(self.sessions.async_create("profile-a", session_id="session-history"))
        active = asyncio.run(self.sessions.async_transition("profile-a", created.session_id, ACTIVE))
        ended = asyncio.run(self.sessions.async_transition("profile-a", active.session_id, ENDED))
        history = HistoricalProjectionRepository(self.service)
        projection = asyncio.run(history.async_project_session(ended))
        duplicate = asyncio.run(history.async_project_session(ended))
        self.assertEqual(projection.originating_session_id, ended.session_id)
        self.assertEqual(projection.owner_profile_id, "profile-a")
        self.assertEqual(projection.historical_session_id, duplicate.historical_session_id)

    def test_historical_moment_projection_is_owner_scoped_and_idempotent(self) -> None:
        history = HistoricalProjectionRepository(self.service)
        first = asyncio.run(history.async_project_moment(session_id="session-a", moment_id="moment-a", owner_profile_id="profile-a", moment_type="track", rendered_text="Safe text", presentation_metadata="{}", ordering=0, created_at="2026-01-01T00:00:00+00:00"))
        duplicate = asyncio.run(history.async_project_moment(session_id="session-a", moment_id="moment-a", owner_profile_id="profile-a", moment_type="track", rendered_text="changed", presentation_metadata="{}", ordering=0, created_at="2026-01-01T00:00:00+00:00"))
        self.assertEqual(first, duplicate)
