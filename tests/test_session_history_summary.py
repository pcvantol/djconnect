"""Connected real-SQLite summary acceptance, snapshots, failure and migration guards."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from custom_components.djconnect.persistence.sessions import (
    PersistentSessionRepository,
    ACTIVE,
    ENDED,
    INTERRUPTED,
)
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
from custom_components.djconnect.persistence.summary import mood_tx
from custom_components.djconnect.historical_projection_query import HistoricalProjectionQueryService


class SummaryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "summary.sqlite"
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.sessions = PersistentSessionRepository(self.service)
        self.history = HistoricalProjectionRepository(self.service)
        self.query = HistoricalProjectionQueryService(self.history)
        self.session = await self.sessions.async_create("owner", initial_mood="chill")
        await self.sessions.async_transition("owner", self.session.session_id, ACTIVE)
        self.id = self.session.session_id

    async def asyncTearDown(self):
        await self.service.async_close()
        self.directory.cleanup()

    async def record(self):
        return await self.history.async_session_record(self.id)

    async def observation(self, ref, item):
        return await self.history.async_append_entries(
            "owner",
            self.id,
            [
                {
                    "kind": "playback_observed",
                    "reference_id": ref,
                    "body": {
                        "item_id": item,
                        "title": item,
                        "coverage": "observed_playing_not_full_listen",
                    },
                }
            ],
        )

    async def test_connected_counts_dedup_subset_and_reopen(self):
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], 0)
        await self.observation("a", "A")
        await self.observation("a", "A")
        await self.observation("same-track-other-poll", "A")
        await self.observation("b", "B")
        await self.observation("a2", "A")
        self.assertTrue(await self.history.async_accept_moment("owner", self.id, "m1"))
        self.assertFalse(await self.history.async_accept_moment("owner", self.id, "m1"))
        archive = {
            "kind": "dj_moment",
            "reference_id": "m2",
            "body": {
                "archive_basis": "cc0_normalized_fields_v1",
                "text": "Permitted subset",
                "moment_type": "artist",
            },
        }
        await self.history.async_accept_moment("owner", self.id, "m2", archive)
        await self.history.async_append_entries(
            "owner",
            self.id,
            [
                {
                    "kind": "conversation_user",
                    "reference_id": "turn",
                    "body": {"message_id": "only-ref"},
                }
            ],
        )
        await self.sessions.async_transition(
            "owner", self.id, ENDED, historical_projections=self.history
        )
        await self.service.async_close()
        await self.service.async_initialize()
        row = await self.record()
        self.assertEqual(row["summary"]["tracks_observed"]["value"], 3)
        self.assertEqual(row["summary"]["moments_published"]["value"], 2)
        entries = await self.history.async_entry_records("owner", self.id)
        self.assertEqual(sum(e["kind"] == "dj_moment" for e in entries), 1)
        page = await self.query.async_session_page("owner")
        self.assertEqual(page["sessions"][0]["summary"]["moments_published"]["state"], "final")
        detail = await self.query.async_timeline_page("owner", self.id)
        self.assertEqual(detail["session"]["summary"]["session_revision"], detail["revision"])
        with self.assertRaises(PermissionError):
            await self.history.async_accept_moment("owner", self.id, "late")
        with self.assertRaises(PermissionError):
            await self.query.async_timeline_page("other", self.id)

    async def test_real_sql_rollback_does_not_leave_counter_or_archive(self):
        connection = sqlite3.connect(self.path)
        connection.execute(
            "CREATE TRIGGER reject_summary BEFORE UPDATE OF moments ON djconnect_session_summaries BEGIN SELECT RAISE(ABORT,'injected'); END"
        )
        connection.close()
        with self.assertRaises(RuntimeError):
            await self.history.async_accept_moment(
                "owner",
                self.id,
                "fault",
                {"kind": "dj_moment", "reference_id": "fault", "body": {"text": "must roll back"}},
            )
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], 0)
        self.assertEqual(await self.history.async_entry_records("owner", self.id), [])
        connection = sqlite3.connect(self.path)
        connection.execute("DROP TRIGGER reject_summary")
        connection.close()
        self.assertTrue(await self.history.async_accept_moment("owner", self.id, "fault"))

    async def test_bound_does_not_evict_replay_keys(self):
        with patch("custom_components.djconnect.persistence.summary.MAX_ACCEPTED_EVENTS", 2):
            await self.history.async_accept_moment("owner", self.id, "one")
            await self.observation("a", "A")
            with self.assertRaises(ValueError):
                await self.history.async_accept_moment("owner", self.id, "three")
            self.assertFalse(await self.history.async_accept_moment("owner", self.id, "one"))
            self.assertEqual(await self.observation("b", "B"), [])
        row = await self.record()
        self.assertEqual(row["summary"]["tracks_observed"]["coverage"], "partial")
        self.assertEqual(row["summary"]["moments_published"]["value"], 1)
        connection = sqlite3.connect(self.path)
        self.assertEqual(
            connection.execute("SELECT COUNT(*) FROM djconnect_session_acceptances").fetchone()[0],
            2,
        )
        connection.close()

    async def test_mood_strict_majority_mixed_zero_and_gap(self):
        stamp = datetime.now(UTC)
        for durations, expected in [
            ({"chill": 6, "groove": 4}, "chill"),
            ({"chill": 5, "groove": 5}, "mixed"),
            ({"chill": 4, "groove": 3, "energy": 3}, "mixed"),
            ({"energy": 8, "party": 2}, "energy"),
            ({"party": 8, "groove": 2}, "party"),
            ({"groove": 10}, "groove"),
        ]:
            await self.service.async_in_transaction(
                lambda tx: tx.execute(
                    "UPDATE djconnect_session_summaries SET mood_durations=?,mood_since='',mood_current='',mood_coverage='complete' WHERE session_id=?",
                    (json.dumps(durations), self.id),
                )
            )
            self.assertEqual((await self.record())["summary"]["mood"]["value"], expected)
        await self.service.async_in_transaction(
            lambda tx: tx.execute(
                "UPDATE djconnect_session_summaries SET mood_durations='{}',mood_since='',mood_current='' WHERE session_id=?",
                (self.id,),
            )
        )
        self.assertIsNone((await self.record())["summary"]["mood"]["value"])
        # Real transaction reducer closes exact confirmed intervals, including paused elapsed time.
        await self.service.async_in_transaction(
            lambda tx: tx.execute(
                "UPDATE djconnect_session_summaries SET mood_durations=?,mood_current='chill',mood_since=?,mood_coverage='complete' WHERE session_id=?",
                (
                    json.dumps(dict.fromkeys(("chill", "groove", "energy", "party"), 0)),
                    stamp.isoformat(),
                    self.id,
                ),
            )
        )
        await self.service.async_in_transaction(
            lambda tx: mood_tx(tx, self.id, "groove", (stamp + timedelta(seconds=6)).isoformat())
        )
        await self.service.async_in_transaction(
            lambda tx: mood_tx(tx, self.id, "groove", (stamp + timedelta(seconds=6)).isoformat())
        )
        await self.service.async_in_transaction(
            lambda tx: mood_tx(
                tx, self.id, "", (stamp + timedelta(seconds=10)).isoformat(), terminal=True
            )
        )
        self.assertEqual((await self.record())["summary"]["mood"]["value"], "chill")
        await self.sessions.async_transition(
            "owner", self.id, INTERRUPTED, historical_projections=self.history
        )
        self.assertIsNone((await self.record())["summary"]["mood"]["value"])

    async def test_withdrawal_is_permanent_without_destroying_dedup(self):
        await self.history.async_accept_moment("owner", self.id, "one")
        ids = await self.observation("a", "A")
        await self.history.async_remove_entry_records("owner", ids)
        self.assertFalse(await self.history.async_accept_moment("owner", self.id, "one"))
        self.assertEqual(await self.observation("a", "A"), ids)
        row = await self.record()
        for m in ("tracks_observed", "moments_published"):
            self.assertEqual(row["summary"][m]["coverage"], "withdrawn")
            self.assertIsNone(row["summary"][m]["value"])

    async def test_page_queries_are_constant_and_legacy_unknown(self):
        for i in range(24):
            session = await self.sessions.async_create("owner", initial_mood="party")
            await self.sessions.async_transition("owner", session.session_id, ACTIVE)
            await self.sessions.async_transition("owner", session.session_id, ENDED)
        await self.service.async_in_transaction(
            lambda tx: tx.execute(
                "DELETE FROM djconnect_session_summaries WHERE session_id=?", (self.id,)
            )
        )
        self.assertIsNone((await self.record())["summary"]["moments_published"]["value"])
        counts = []
        provider = self.service._provider
        original = provider._run_transaction

        def counted(operation):
            class Counting:
                def __init__(self, tx):
                    self.tx = tx

                def execute(self, s, p=()):
                    counts.append(s)
                    return self.tx.execute(s, p)

                def fetchone(self, s, p=()):
                    counts.append(s)
                    return self.tx.fetchone(s, p)

                def fetchall(self, s, p=()):
                    counts.append(s)
                    return self.tx.fetchall(s, p)

            return original(lambda tx: operation(Counting(tx)))

        provider._run_transaction = counted
        page = await self.query.async_session_page("owner", limit=20)
        self.assertEqual(len(page["sessions"]), 20)
        self.assertEqual(len(counts), 4)
        self.assertFalse(any("djconnect_session_entries" in q for q in counts))
        self.assertEqual(len({s["summary"]["as_of"] for s in page["sessions"]}), 1)

    async def test_cancellation_during_short_real_transaction_commits_once_and_keeps_lock(self):
        import threading
        from custom_components.djconnect.persistence.summary import record_event_tx

        entered, release = threading.Event(), threading.Event()

        def blocked(tx):
            entered.set()
            if not release.wait(3):
                raise AssertionError("qualification transaction release timeout")
            record_event_tx(tx, self.id, "dj_moment", "cancelled-commit")
            return "committed"

        task = asyncio.create_task(self.service.async_in_transaction(blocked))
        await asyncio.wait_for(asyncio.to_thread(entered.wait), 1)
        task.cancel()
        concurrent = asyncio.create_task(
            self.history.async_accept_moment("owner", self.id, "cancelled-commit")
        )
        await asyncio.sleep(0)
        self.assertFalse(concurrent.done())
        release.set()
        self.assertEqual(await task, "committed")
        self.assertFalse(await concurrent)
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], 1)

    async def test_end_race_acceptance_has_single_ordered_outcome(self):
        results = await asyncio.gather(
            self.history.async_accept_moment("owner", self.id, "end-race"),
            self.sessions.async_transition(
                "owner", self.id, ENDED, historical_projections=self.history
            ),
            return_exceptions=True,
        )
        count = (await self.record())["summary"]["moments_published"]["value"]
        self.assertEqual(count, 1 if results[0] is True else 0)
        self.assertIn(type(results[0]), (bool, PermissionError))
        with self.assertRaises(PermissionError):
            await self.history.async_accept_moment("owner", self.id, "after-end")
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], count)

    async def test_source_rights_withdrawal_is_read_only_and_owner_scoped(self):
        await self.history.async_accept_moment("owner", self.id, "permitted")
        await self.observation("a", "A")

        async def withdrawn(owner, binding):
            self.assertEqual(owner, "owner")
            return False

        query = HistoricalProjectionQueryService(self.history, summary_validator=withdrawn)
        before = await self.record()
        page = await query.async_session_page("owner", include_active=True)
        summary = page["sessions"][0]["summary"]
        self.assertIsNone(summary["tracks_observed"]["value"])
        self.assertEqual(summary["moments_published"]["coverage"], "withdrawn")
        after = await self.record()
        self.assertEqual(before["revision"], after["revision"])
        self.assertEqual(after["summary"]["moments_published"]["value"], 1)
        self.assertEqual(
            (await query.async_session_page("other", include_active=True))["sessions"], []
        )

    async def test_oversized_identity_rolls_back_and_repeated_capacity_reads_do_not_rev(self):
        with self.assertRaises(ValueError):
            await self.history.async_accept_moment("owner", self.id, "x" * 257)
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], 0)
        with patch("custom_components.djconnect.persistence.summary.MAX_ACCEPTED_EVENTS", 1):
            await self.observation("a", "A")
            await self.observation("b", "B")
            first = await self.record()
            await self.observation("b", "B")
            second = await self.record()
            self.assertEqual(first["revision"], second["revision"])

    async def test_real_v5_upgrade_keeps_old_session_unknown_and_new_session_known_zero(self):
        await self.sessions.async_transition(
            "owner", self.id, ENDED, historical_projections=self.history
        )
        await self.service.async_close()
        connection = sqlite3.connect(self.path)
        connection.execute("DROP TABLE djconnect_session_acceptances")
        connection.execute("DROP TABLE djconnect_session_summaries")
        connection.execute("DELETE FROM djconnect_schema_migrations WHERE schema_version=6")
        connection.execute("UPDATE djconnect_schema_metadata SET schema_version=5")
        connection.commit()
        connection.close()
        await self.service.async_initialize()
        self.assertEqual(self.service.readiness.schema_version, 6)
        old = await self.record()
        for metric in ("tracks_observed", "moments_published", "mood"):
            self.assertIsNone(old["summary"][metric]["value"])
            self.assertEqual(old["summary"][metric]["coverage"], "unknown")
            self.assertEqual(old["summary"][metric]["state"], "final")
        new = await self.sessions.async_create("owner", initial_mood="chill")
        row = await self.history.async_session_record(new.session_id)
        self.assertEqual(row["summary"]["tracks_observed"]["value"], 0)
        self.assertEqual(row["summary"]["moments_published"]["value"], 0)

    async def test_partial_schema_does_not_become_ready_or_repair_itself(self):
        await self.service.async_close()
        connection = sqlite3.connect(self.path)
        connection.execute("DELETE FROM djconnect_schema_migrations WHERE schema_version=6")
        connection.execute("UPDATE djconnect_schema_metadata SET schema_version=5")
        connection.execute("DROP TABLE djconnect_session_acceptances")
        connection.commit()
        connection.close()
        with self.assertRaises(RuntimeError):
            await self.service.async_initialize()
        self.assertFalse(self.service.readiness.ready)
        connection = sqlite3.connect(self.path)
        self.assertEqual(
            connection.execute("SELECT COUNT(*) FROM djconnect_persistent_sessions").fetchone()[0],
            1,
        )
        self.assertEqual(
            connection.execute("SELECT schema_version FROM djconnect_schema_metadata").fetchone()[
                0
            ],
            5,
        )
        connection.close()
