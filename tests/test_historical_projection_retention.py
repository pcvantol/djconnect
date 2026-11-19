"""Focused lifecycle tests for historical projection retention."""

from __future__ import annotations
import asyncio
from datetime import UTC, datetime
from pathlib import Path
import sys
import tempfile
import types
import unittest

package = types.ModuleType("custom_components.djconnect")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")]
sys.modules.setdefault("custom_components.djconnect", package)
from custom_components.djconnect.historical_projection_retention import (  # noqa: E402
    HistoricalProjectionRetentionService,
    HistoricalRetentionPolicy,
)
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402


class HistoricalProjectionRetentionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = PersistenceService(
            Path(self.tmp.name) / "history.db", SQLitePersistenceProvider()
        )
        asyncio.run(self.service.async_initialize())
        self.repo = HistoricalProjectionRepository(self.service)

    def tearDown(self):
        asyncio.run(self.service.async_close())
        self.tmp.cleanup()

    def _seed(self):
        asyncio.run(
            self.service.async_in_transaction(
                lambda tx: (
                    tx.execute(
                        "INSERT INTO djconnect_historical_sessions (historical_session_id,originating_session_id,owner_profile_id,lifecycle_outcome,created_at,projection_version) VALUES ('old','s-old','p','INTERRUPTED','2020-01-01T00:00:00+00:00',1)"
                    ),
                    tx.execute(
                        "INSERT INTO djconnect_historical_moments (historical_moment_id,originating_session_id,originating_moment_id,owner_profile_id,moment_type,rendered_text,ordering,created_at,projection_version) VALUES ('old-m','s-old','m','p','track','safe',0,'2020-01-01T00:00:00+00:00',1)"
                    ),
                    tx.execute(
                        "INSERT INTO djconnect_historical_sessions (historical_session_id,originating_session_id,owner_profile_id,lifecycle_outcome,created_at,projection_version) VALUES ('new','s-new','p','ENDED','2030-01-01T00:00:00+00:00',1)"
                    ),
                )
            )
        )

    def test_cleanup_is_ordered_idempotent_and_preserves_recent(self):
        self._seed()
        cleanup = HistoricalProjectionRetentionService(
            self.repo, HistoricalRetentionPolicy(retention_days=1)
        )
        result = asyncio.run(cleanup.async_cleanup(now=datetime(2026, 1, 1, tzinfo=UTC)))
        again = asyncio.run(cleanup.async_cleanup(now=datetime(2026, 1, 1, tzinfo=UTC)))
        self.assertEqual((result.deleted_sessions, result.deleted_moments), (1, 1))
        self.assertEqual((again.deleted_sessions, again.deleted_moments), (0, 0))
        self.assertIsNone(asyncio.run(self.repo.async_get_session("old")))
        self.assertIsNotNone(asyncio.run(self.repo.async_get_session("new")))

    def test_empty_cleanup_reports_zero_statistics(self):
        result = asyncio.run(
            HistoricalProjectionRetentionService(self.repo).async_cleanup(
                now=datetime(2026, 1, 1, tzinfo=UTC)
            )
        )
        self.assertEqual(
            (result.deleted_sessions, result.deleted_moments, result.result), (0, 0, "ok")
        )
