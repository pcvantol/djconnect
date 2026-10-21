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
        # Two fixed singleton-policy reads fence changes while the page is
        # built; still no per-row timeline or policy requests.
        self.assertEqual(len(counts), 6)
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
        connection.execute("DROP INDEX djconnect_session_entry_message")
        # Reconstruct an actual v5 store, not v5 metadata over newer tables.
        for table in ('djconnect_profile_dj_settings', 'djconnect_session_dj_settings',
                      'djconnect_settings_operations', 'djconnect_settings_clock',
                      'djconnect_session_retention', 'djconnect_history_deletion_targets',
                      'djconnect_history_deletions', 'djconnect_history_deletion_clock',
                      'djconnect_content_tombstones', 'djconnect_content_request_fences'):
            connection.execute(f'DROP TABLE {table}')
        connection.execute("DELETE FROM djconnect_schema_migrations WHERE schema_version>=6")
        connection.execute("UPDATE djconnect_schema_metadata SET schema_version=5")
        connection.commit()
        connection.close()
        await self.service.async_initialize()
        from custom_components.djconnect.persistence.schema import CURRENT_SCHEMA_VERSION
        self.assertEqual(self.service.readiness.schema_version, CURRENT_SCHEMA_VERSION)
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

    async def test_history_optout_preserves_live_acceptance_without_persistent_summary(self):
        await self.sessions.async_transition(
            "owner", self.id, ENDED, historical_projections=self.history
        )
        session = await self.sessions.async_create(
            "owner", initial_mood="groove", history_enabled=False
        )
        await self.sessions.async_transition("owner", session.session_id, ACTIVE)
        self.assertTrue(
            await self.history.async_accept_moment("owner", session.session_id, "live-only")
        )
        record = await self.history.async_session_record(session.session_id)
        self.assertIsNone(record["summary"]["moments_published"]["value"])
        self.assertEqual(record["summary"]["moments_published"]["coverage"], "unknown")
        self.assertEqual(await self.history.async_entry_records("owner", session.session_id), [])
        connection = sqlite3.connect(self.path)
        self.assertEqual(
            connection.execute(
                "SELECT COUNT(*) FROM djconnect_session_acceptances WHERE session_id=?",
                (session.session_id,),
            ).fetchone()[0],
            0,
        )
        connection.close()

    async def test_runtime_publication_sql_failure_retry_and_broadcast_failure(self):
        import sys
        from tests.test_session_runtime import _load_runtime_module

        runtime, previous_const = _load_runtime_module()
        try:
            manager = runtime.SessionRuntimeManager(self.sessions, self.history)
            active = await manager.async_start(
                owner_profile_id="runtime-owner", selected_mood="chill"
            )

            async def insight():
                return {
                    "track": {"title": "Anchor", "artist": "Northline"},
                    "analysis": {"summary": "A measured texture."},
                }

            connection = sqlite3.connect(self.path)
            connection.execute(
                "CREATE TRIGGER reject_live_summary BEFORE UPDATE OF moments ON djconnect_session_summaries BEGIN SELECT RAISE(ABORT,'failure before commit'); END"
            )
            connection.close()
            with self.assertRaises(RuntimeError):
                await manager.async_process_track_started(
                    owner_profile_id="runtime-owner",
                    session_id=active.session_id,
                    insight_provider=insight,
                )
            record = await self.history.async_session_record(active.session_id)
            self.assertEqual(record["summary"]["moments_published"]["value"], 0)
            self.assertEqual(active.presence_ledger.total_published, 0)
            connection = sqlite3.connect(self.path)
            connection.execute("DROP TRIGGER reject_live_summary")
            connection.close()
            received = []

            def broken_transport(event):
                raise RuntimeError("failure after semantic commit")

            active.broadcast.subscribe(broken_transport)
            active.broadcast.subscribe(received.append)
            moment = await manager.async_process_track_started(
                owner_profile_id="runtime-owner",
                session_id=active.session_id,
                insight_provider=insight,
            )
            self.assertIsNotNone(moment)
            record = await self.history.async_session_record(active.session_id)
            self.assertEqual(record["summary"]["moments_published"]["value"], 1)
            self.assertEqual(active.presence_ledger.total_published, 1)
            self.assertTrue(received)
            self.assertFalse(await manager._async_persist_moment(active, moment))
            self.assertEqual(
                (await self.history.async_session_record(active.session_id))["summary"][
                    "moments_published"
                ]["value"],
                1,
            )
        finally:
            sys.modules.pop("custom_components.djconnect.session_runtime", None)
            if previous_const is None:
                sys.modules.pop("custom_components.djconnect.const", None)
            else:
                sys.modules["custom_components.djconnect.const"] = previous_const

    async def test_mood_authority_revoked_while_storage_lock_waits_has_no_commit(self):
        import sys
        from tests.test_session_runtime import _load_runtime_module

        runtime, previous_const = _load_runtime_module()
        try:
            manager = runtime.SessionRuntimeManager(self.sessions, self.history)
            active = await manager.async_start(
                owner_profile_id="runtime-owner", selected_mood="chill"
            )
            authority = [True]
            lock = self.service._provider._write_lock
            await lock.acquire()
            task = asyncio.create_task(
                manager.async_update_mood(
                    owner_profile_id="runtime-owner",
                    session_id=active.session_id,
                    selected_mood="party",
                    expected_revision=0,
                    authorize=lambda: authority[0],
                )
            )
            await asyncio.sleep(0.01)
            self.assertFalse(task.done())
            authority[0] = False
            lock.release()
            with self.assertRaises(PermissionError):
                await task
            self.assertEqual(
                (await manager.async_get_active("runtime-owner")).selected_mood, "chill"
            )
            row = await self.history.async_session_record(active.session_id)
            self.assertEqual(row["revision"], 0)
            self.assertEqual(row["summary"]["mood"]["value"], "chill")
        finally:
            sys.modules.pop("custom_components.djconnect.session_runtime", None)
            if previous_const is None:
                sys.modules.pop("custom_components.djconnect.const", None)
            else:
                sys.modules["custom_components.djconnect.const"] = previous_const

    async def test_relation_composer_before_commit_and_flow_failure_after_commit_retry_once(self):
        import sys
        from tests.test_session_runtime import _load_runtime_module
        from tests.test_narrative_album_continuity import NarrativeAlbumContinuityTest

        runtime, previous_const = _load_runtime_module()
        try:
            from custom_components.djconnect import session_facts

            await self.sessions.async_transition(
                "owner", self.id, ENDED, historical_projections=self.history
            )
            fixture = NarrativeAlbumContinuityTest()
            fixture.runtime, fixture.facts, fixture.clock = runtime, session_facts, [100.0]
            fixture.manager = runtime.SessionRuntimeManager(
                self.sessions, self.history, monotonic_source=lambda: fixture.clock[0]
            )
            active = await fixture.manager.async_start(
                owner_profile_id="owner",
                selected_mood="groove",
                music_backend="spotify_direct",
                session_start_strategy=runtime.SessionStartStrategy.DISCOVER,
            )
            fixture.session = active
            a = await fixture.track(0)
            self.assertEqual(a.moment_type.value, "album")
            with patch.object(
                type(active.presentation_composer),
                "compose_with_diagnostics",
                side_effect=RuntimeError("composer before commit"),
            ):
                with self.assertRaises(RuntimeError):
                    await fixture.track(1)
            row = await self.history.async_session_record(active.session_id)
            self.assertEqual(row["summary"]["moments_published"]["value"], 1)
            with patch.object(
                runtime.DJSessionBroadcastEngine,
                "publish_session_flow",
                side_effect=RuntimeError("Flow after commit"),
            ):
                with self.assertRaises(RuntimeError):
                    await fixture.manager.async_maybe_publish_intra_track_moment(
                        owner_profile_id="owner",
                        session_id=active.session_id,
                        media_identity=fixture.catalog(1)["uri"],
                    )
            row = await self.history.async_session_record(active.session_id)
            self.assertEqual(row["summary"]["moments_published"]["value"], 2)
            self.assertEqual(active.presence_ledger.total_published, 2)
            await fixture.manager.async_maybe_publish_intra_track_moment(
                owner_profile_id="owner",
                session_id=active.session_id,
                media_identity=fixture.catalog(1)["uri"],
            )
            row = await self.history.async_session_record(active.session_id)
            self.assertEqual(row["summary"]["moments_published"]["value"], 2)
            self.assertFalse(active.prepared_presentations)
        finally:
            sys.modules.pop("custom_components.djconnect.session_runtime", None)
            if previous_const is None:
                sys.modules.pop("custom_components.djconnect.const", None)
            else:
                sys.modules["custom_components.djconnect.const"] = previous_const

    async def test_source_withdrawal_without_archived_body_keeps_opaque_replay_key(self):
        await self.service.async_in_transaction(
            lambda tx: tx.execute(
                "UPDATE djconnect_session_summaries SET source_binding=? WHERE session_id=?",
                (json.dumps({"provider_entry_id": "source-entry"}), self.id),
            )
        )
        await self.history.async_accept_moment("owner", self.id, "no-text-archive")
        await self.history.async_withdraw_source_entry("source-entry")
        row = await self.record()
        self.assertIsNone(row["summary"]["moments_published"]["value"])
        self.assertEqual(row["summary"]["moments_published"]["coverage"], "withdrawn")
        self.assertFalse(
            await self.history.async_accept_moment("owner", self.id, "no-text-archive")
        )
        self.assertEqual(await self.history.async_entry_records("owner", self.id), [])

    async def test_restart_interruption_retains_counts_but_never_fills_unobserved_mood_gap(self):
        from custom_components.djconnect.persistence.reconciliation import (
            PersistentSessionStartupReconciler,
        )

        await self.observation("a", "A")
        await self.history.async_accept_moment("owner", self.id, "accepted-before-crash")
        await self.service.async_close()
        await self.service.async_initialize()
        result = await PersistentSessionStartupReconciler(
            self.sessions, history=self.history
        ).async_reconcile()
        self.assertEqual(result.interrupted, 1)
        row = await self.record()
        self.assertEqual(row["lifecycle_status"], "INTERRUPTED")
        self.assertEqual(row["summary"]["tracks_observed"]["value"], 1)
        self.assertEqual(row["summary"]["moments_published"]["value"], 1)
        self.assertEqual(row["summary"]["mood"]["coverage"], "unknown")
        self.assertIsNone(row["summary"]["mood"]["value"])
        self.assertEqual(row["summary"]["mood"]["state"], "final")
        self.assertEqual(
            (
                await PersistentSessionStartupReconciler(
                    self.sessions, history=self.history
                ).async_reconcile()
            ).interrupted,
            0,
        )

    async def test_profile_purge_erases_derived_totals_and_forbids_reassignment(self):
        await self.history.async_accept_moment("owner", self.id, "accepted")
        await self.history.async_purge_profile_history("owner")
        self.assertIsNone((await self.record())["summary"]["moments_published"]["value"])
        self.assertEqual(
            (await self.query.async_session_page("owner", include_active=True))["sessions"], []
        )
        self.assertEqual(
            (await self.query.async_session_page("replacement", include_active=True))["sessions"],
            [],
        )
        connection = sqlite3.connect(self.path)
        self.assertEqual(
            connection.execute("SELECT COUNT(*) FROM djconnect_session_acceptances").fetchone()[0],
            0,
        )
        connection.close()

    async def test_concurrent_list_detail_and_updates_never_mix_metric_revisions(self):
        from custom_components.djconnect.session_history_projection import HistoryQueryError

        async def read():
            for _ in range(20):
                for action in (
                    lambda: self.query.async_session_page("owner", include_active=True),
                    lambda: self.query.async_timeline_page("owner", self.id),
                ):
                    try:
                        result = await action()
                    except HistoryQueryError as exc:
                        self.assertEqual(str(exc), "invalid_history_cursor")
                        continue
                    records = result.get("sessions", [result.get("session")])
                    for row in records:
                        self.assertEqual(row["summary"]["session_revision"], row["revision"])
                        for key in ("tracks_observed", "moments_published", "mood"):
                            self.assertEqual(row["summary"][key]["revision"], row["revision"])
                            self.assertEqual(row["summary"][key]["as_of"], row["summary"]["as_of"])

        async def write():
            for number in range(20):
                await self.history.async_accept_moment(
                    "owner", self.id, "concurrent-" + str(number)
                )

        await asyncio.gather(read(), write())
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], 20)

    async def test_retention_erases_summary_and_keys_only_after_closed_session_expiry(self):
        await self.history.async_accept_moment("owner", self.id, "retained-neutral-count")
        await self.sessions.async_transition(
            "owner", self.id, ENDED, historical_projections=self.history
        )
        future = (datetime.now(UTC) + timedelta(days=91)).isoformat()
        await self.history.async_cleanup_expired(
            cutoff=future, batch_size=250, entry_deadline=future
        )
        record = await self.record()
        self.assertFalse(record["history_enabled"])
        self.assertIsNone(record["summary"]["moments_published"]["value"])
        connection = sqlite3.connect(self.path)
        self.assertEqual(
            connection.execute("SELECT COUNT(*) FROM djconnect_session_acceptances").fetchone()[0],
            0,
        )
        self.assertEqual(
            connection.execute("SELECT COUNT(*) FROM djconnect_session_summaries").fetchone()[0], 0
        )
        connection.close()
        with self.assertRaises(PermissionError):
            await self.history.async_accept_moment("owner", self.id, "retained-neutral-count")

    async def test_cancel_before_storage_admission_does_not_start_transaction(self):
        lock = self.service._provider._write_lock
        await lock.acquire()
        task = asyncio.create_task(
            self.history.async_accept_moment("owner", self.id, "cancel-before-admission")
        )
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        lock.release()
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], 0)

    async def test_real_commit_failure_rolls_back_aggregate_and_allows_retry(self):
        from custom_components.djconnect.persistence.summary import record_event_tx

        await self.service.async_in_transaction(
            lambda tx: (
                tx.execute("CREATE TABLE test_acceptance_parent (id INTEGER PRIMARY KEY)"),
                tx.execute(
                    "CREATE TABLE test_acceptance_child (id INTEGER REFERENCES test_acceptance_parent(id) DEFERRABLE INITIALLY DEFERRED)"
                ),
            )
        )

        def invalid_commit(tx):
            tx.execute("INSERT INTO test_acceptance_child VALUES (999)")
            record_event_tx(tx, self.id, "dj_moment", "commit-failed")

        with self.assertRaises(RuntimeError):
            await self.service.async_in_transaction(invalid_commit)
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], 0)
        self.assertTrue(await self.history.async_accept_moment("owner", self.id, "commit-failed"))
        self.assertEqual((await self.record())["summary"]["moments_published"]["value"], 1)

    async def test_all_rich_proactive_families_share_real_persistent_commit_and_off_is_zero(self):
        import sys
        from tests.test_session_runtime import _load_runtime_module
        from tests.test_session_presence import SessionPresenceTest

        runtime, previous_const = _load_runtime_module()
        try:
            await self.sessions.async_transition(
                "owner", self.id, ENDED, historical_projections=self.history
            )
            actual_manager_class = runtime.SessionRuntimeManager
            fixture = SessionPresenceTest()
            fixture.runtime = runtime

            def connected_manager(**kwargs):
                return actual_manager_class(self.sessions, self.history, **kwargs)

            with patch.object(runtime, "SessionRuntimeManager", connected_manager):
                receipts, active, manager = await fixture.rich_trace("presenter")
            proactive = [kind for _, kind in receipts if kind != "silence"]
            self.assertIn("artist", proactive)
            self.assertIn("album", proactive)
            row = await self.history.async_session_record(active.session_id)
            self.assertEqual(row["summary"]["moments_published"]["value"], len(proactive))
            self.assertEqual(row["summary"]["tracks_observed"]["value"], 4)
            self.assertEqual(active.presence_ledger.total_published, len(proactive))
            await manager.async_end(owner_profile_id="owner", session_id=active.session_id)
            with patch.object(runtime, "SessionRuntimeManager", connected_manager):
                silent, off, _manager = await fixture.rich_trace("music_only")
            self.assertFalse([kind for _, kind in silent if kind != "silence"])
            row = await self.history.async_session_record(off.session_id)
            self.assertEqual(row["summary"]["moments_published"]["value"], 0)
            self.assertEqual(row["summary"]["tracks_observed"]["value"], 4)
        finally:
            sys.modules.pop("custom_components.djconnect.session_runtime", None)
            if previous_const is None:
                sys.modules.pop("custom_components.djconnect.const", None)
            else:
                sys.modules["custom_components.djconnect.const"] = previous_const

    async def test_existing_genre_coordinator_commit_is_counted_once(self):
        import sys
        from tests.test_session_runtime import _load_runtime_module

        runtime, previous_const = _load_runtime_module()
        try:
            manager = runtime.SessionRuntimeManager(self.sessions, self.history)
            active = await manager.async_start(
                owner_profile_id="genre-owner",
                selected_mood="groove",
                allowed_capability_intents=frozenset({"genre_story"}),
            )

            async def qualified_insight():
                return {
                    "track": {"title": "Anchor", "artist": "Northline", "genres": ["jazz"]},
                    "analysis": {
                        "summary": "A measured texture.",
                        "full_text": "The current musical context has a measured texture.",
                        "genre": "jazz",
                    },
                }

            moment = await manager.async_process_track_started(
                owner_profile_id="genre-owner",
                session_id=active.session_id,
                insight_provider=qualified_insight,
            )
            self.assertIsNotNone(moment)
            self.assertEqual(moment.moment_type.value, "genre")
            row = await self.history.async_session_record(active.session_id)
            self.assertEqual(row["summary"]["moments_published"]["value"], 1)
            self.assertEqual(active.presence_ledger.total_published, 1)
            self.assertFalse(await manager._async_persist_moment(active, moment))
        finally:
            sys.modules.pop("custom_components.djconnect.session_runtime", None)
            if previous_const is None:
                sys.modules.pop("custom_components.djconnect.const", None)
            else:
                sys.modules["custom_components.djconnect.const"] = previous_const

    async def test_exact_microsecond_tie_never_becomes_false_majority_from_float_truncation(self):
        stamp = datetime.now(UTC)

        def confirmed(tx):
            tx.execute(
                "UPDATE djconnect_session_summaries SET mood_durations=?,mood_current='groove',mood_since=?,mood_coverage='complete' WHERE session_id=?",
                (
                    json.dumps(dict.fromkeys(("chill", "groove", "energy", "party"), 0)),
                    stamp.isoformat(),
                    self.id,
                ),
            )
            mood_tx(tx, self.id, "chill", (stamp + timedelta(microseconds=249)).isoformat())
            mood_tx(tx, self.id, "groove", (stamp + timedelta(microseconds=749)).isoformat())
            mood_tx(
                tx,
                self.id,
                "groove",
                (stamp + timedelta(microseconds=1000)).isoformat(),
                terminal=True,
            )

        await self.service.async_in_transaction(confirmed)
        self.assertEqual((await self.record())["summary"]["mood"]["value"], "mixed")
        connection = sqlite3.connect(self.path)
        durations = json.loads(
            connection.execute(
                "SELECT mood_durations FROM djconnect_session_summaries WHERE session_id=?",
                (self.id,),
            ).fetchone()[0]
        )
        connection.close()
        self.assertEqual(durations["groove"], 500)
        self.assertEqual(durations["chill"], 500)

    async def test_current_fact_admission_rechecks_age_expiry_and_read_fit_after_storage_wait(self):
        import sys
        import time
        from dataclasses import replace
        from tests.test_session_runtime import _load_runtime_module
        from tests.test_narrative_album_continuity import NarrativeAlbumContinuityTest

        runtime, previous_const = _load_runtime_module()
        try:
            from custom_components.djconnect import session_facts

            await self.sessions.async_transition(
                "owner", self.id, ENDED, historical_projections=self.history
            )
            for case in ("observation_age", "source_expiry", "remaining_read_fit"):
                fixture = NarrativeAlbumContinuityTest()
                fixture.runtime, fixture.facts, fixture.clock = runtime, session_facts, [100.0]
                fixture.manager = runtime.SessionRuntimeManager(
                    self.sessions, self.history, monotonic_source=lambda: fixture.clock[0]
                )
                active = await fixture.manager.async_start(
                    owner_profile_id="owner",
                    selected_mood="groove",
                    music_backend="spotify_direct",
                    session_start_strategy=runtime.SessionStartStrategy.DISCOVER,
                )
                fixture.session = active
                await fixture.track(0)
                fixture.clock[0] += 200
                catalog = fixture.catalog(1)
                await fixture.manager.async_update_playback_projection(
                    owner_profile_id="owner",
                    session_id=active.session_id,
                    state="playing",
                    media_identity=catalog["uri"],
                    title=catalog["title"],
                    artist=catalog["artist"],
                    album=catalog["album_name"],
                    duration_ms=70000 if case == "remaining_read_fit" else 300000,
                    position_ms=0,
                )
                facts = fixture.pool(1)
                if case == "source_expiry":
                    facts = tuple(replace(f, observed_at=time.monotonic() - 1799) for f in facts)

                async def provider():
                    return {"_qualified_facts": facts}

                lock = self.service._provider._write_lock
                await lock.acquire()
                pending = asyncio.create_task(
                    fixture.manager.async_process_track_started(
                        owner_profile_id="owner",
                        session_id=active.session_id,
                        media_identity=catalog["uri"],
                        insight_provider=provider,
                        require_current_playback=True,
                        allow_initial_facts=True,
                    )
                )
                for _ in range(100):
                    if fixture.manager._lock.locked():
                        break
                    await asyncio.sleep(0.001)
                self.assertTrue(fixture.manager._lock.locked())
                self.assertFalse(pending.done())
                if case == "source_expiry":
                    await asyncio.sleep(1.1)
                else:
                    fixture.clock[0] += 31 if case == "observation_age" else 29
                lock.release()
                self.assertIsNone(await pending, case)
                row = await self.history.async_session_record(active.session_id)
                self.assertEqual(row["summary"]["moments_published"]["value"], 1, case)
                self.assertEqual(active.presence_ledger.total_published, 1, case)
                self.assertFalse(active.published_album_context.used_relations, case)
                await fixture.manager.async_end(
                    owner_profile_id="owner", session_id=active.session_id
                )
        finally:
            sys.modules.pop("custom_components.djconnect.session_runtime", None)
            if previous_const is None:
                sys.modules.pop("custom_components.djconnect.const", None)
            else:
                sys.modules["custom_components.djconnect.const"] = previous_const
