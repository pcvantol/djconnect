"""Real SQL/cancellation tests with explicitly synthetic source witnesses.

The separate actual-HA harness proves the genuine producer/source capture path.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()

from custom_components.djconnect.persistence import PersistenceService, PersistenceError  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.surface_status_samples import OriginalSample, StatusJournal, publish  # noqa: E402


class SyntheticSource:
    def __init__(self, scope="a" * 64):
        self.scope = scope
        self.alive = True
        self.active = SimpleNamespace(broadcast=SimpleNamespace(original_status_sample=None), session_id="synthetic-session")
        self.broadcast = self.active.broadcast
        self.observed = SimpleNamespace(session_id=self.active.session_id)

    def current(self, ending=None):
        return self.alive


class OriginalStatusSQLTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "source-status.sqlite3"
        self.provider = SQLitePersistenceProvider()
        self.service = PersistenceService(self.path, self.provider)
        await self.service.async_initialize()
        self.journal = StatusJournal(self.service)
        self.source = SyntheticSource()

    async def asyncTearDown(self):
        await self.service.async_close()
        self.directory.cleanup()

    def sample(self, ms=10000, state="playing", *, source=None, ended=False):
        return OriginalSample(source or self.source, ms, 10.0, state, ended, str(uuid.uuid4()))

    async def rows(self):
        return await self.service.async_in_transaction(lambda tx: tx.fetchall(
            "SELECT scope_hash,sample_id,ordinal,observed_ms,playback_state,ended FROM djconnect_status_samples"))

    async def test_latest_sample_keeps_original_time_and_advances_only_on_new_event(self):
        first = self.sample()
        result = await self.journal.record(first)
        self.assertEqual((result.ordinal, result.observed_ms), (1, 10000))
        self.assertIsNone(await self.journal.record(first))
        second = await self.journal.record(self.sample(ms=10000, state="paused"))
        self.assertEqual((second.ordinal, second.observed_ms, second.state), (2, 10000, "paused"))
        self.assertNotEqual(result.sample_id, second.sample_id)
        self.assertEqual(len(await self.rows()), 1)

    async def test_real_reopen_retains_ordinal_but_no_RAM_authority_adoption(self):
        await self.journal.record(self.sample())
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.journal = StatusJournal(self.service)
        self.assertIsNone(self.source.active.broadcast.original_status_sample)
        result = await self.journal.record(self.sample(ms=10001))
        self.assertEqual(result.ordinal, 2)

    async def test_clock_rollback_is_rejected_without_clamping_or_reissue(self):
        await self.journal.record(self.sample())
        old = self.sample(ms=9999)
        with self.assertRaises(PersistenceError):
            await self.journal.record(old)
        self.assertIsNone(await self.journal.record(old))
        self.assertEqual((await self.rows())[0][2:4], (1, 10000))

    async def test_ended_scope_never_reopens_and_requires_real_prior_source_row(self):
        with self.assertRaises(PersistenceError):
            await self.journal.record(self.sample(state=None, ended=True))
        await self.journal.record(self.sample())
        terminal = await self.journal.record(self.sample(ms=10001, state=None, ended=True))
        self.assertTrue(terminal.ended)
        self.assertIsNone(terminal.state)
        with self.assertRaises(PersistenceError):
            await self.journal.record(self.sample(ms=10002))
        self.assertEqual((await self.rows())[0][2], 2)

    async def test_invalid_active_null_and_bad_time_never_commit(self):
        for sample in [self.sample(state=None), self.sample(ms=True), self.sample(ms=0),
                       self.sample(ms=9007199254740992)]:
            with self.assertRaises(PersistenceError):
                await self.journal.record(sample)
        self.assertEqual(await self.rows(), [])
        with self.assertRaises(PersistenceError):
            await self.service.async_in_transaction(lambda tx: tx.execute(
                "INSERT INTO djconnect_status_samples VALUES (?,?,1,10000,NULL,0)",
                ("a" * 64, str(uuid.uuid4()))))

    async def test_capacity_preserves_old_rows_and_allows_existing_scope_update(self):
        with patch("custom_components.djconnect.surface_status_samples.MAX_SCOPES", 2):
            await self.journal.record(self.sample())
            await self.journal.record(self.sample(source=SyntheticSource("b" * 64)))
            with self.assertRaises(PersistenceError):
                await self.journal.record(self.sample(source=SyntheticSource("c" * 64)))
            self.assertEqual((await self.journal.record(self.sample(ms=10001))).ordinal, 2)
            self.assertEqual(len(await self.rows()), 2)

    async def test_safe_integer_exhaustion_is_closed_without_reset(self):
        await self.journal.record(self.sample())
        await self.service.async_in_transaction(lambda tx: tx.execute(
            "UPDATE djconnect_status_samples SET ordinal=9007199254740991"))
        with self.assertRaises(PersistenceError):
            await self.journal.record(self.sample(ms=10001))

    async def test_commit_requires_actual_full_sync_and_restores_existing_policy(self):
        policies = []
        original = self.service.async_in_transaction
        async def record_policy(operation, **kwargs):
            def checked(tx):
                policies.append(tx.fetchone("PRAGMA synchronous")[0])
                return operation(tx)
            return await original(checked, **kwargs)
        with patch.object(self.service, "async_in_transaction", record_policy):
            await self.journal.record(self.sample())
        self.assertEqual(policies, [2])
        self.assertEqual(await original(lambda tx: tx.fetchone("PRAGMA synchronous")[0]), 1)

    def block_connection(self, *, after_commit=False):
        connection = self.provider._connection
        entered, release = threading.Event(), threading.Event()
        class Hold:
            def execute(self, sql, *args):
                if not after_commit and sql.startswith("INSERT OR REPLACE INTO djconnect_status_samples"):
                    entered.set()
                    assert release.wait(5)
                result = connection.execute(sql, *args)
                if after_commit and sql == "COMMIT":
                    entered.set()
                    assert release.wait(5)
                return result
            def __getattr__(self, name):
                return getattr(connection, name)
        self.provider._connection = Hold()
        self.addCleanup(release.set)
        return entered, release

    async def test_retirement_during_staged_SQL_rolls_back_and_consumes_attempt(self):
        entered, release = self.block_connection()
        sample = self.sample()
        task = asyncio.create_task(self.journal.record(sample))
        self.assertTrue(await asyncio.to_thread(entered.wait, 3))
        self.source.alive = False
        release.set()
        with self.assertRaises(PermissionError):
            await task
        self.assertEqual(await self.rows(), [])
        self.assertIsNone(await self.journal.record(sample))

    async def test_cancelled_SQL_settles_before_return_and_does_not_publish(self):
        entered, release = self.block_connection()
        active = self.source.active
        manager = SimpleNamespace(_status_samples=self.journal)
        task = asyncio.create_task(publish(manager, active, self.sample()))
        self.assertTrue(await asyncio.to_thread(entered.wait, 3))
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertIsNone(active.broadcast.original_status_sample)
        self.assertEqual(await self.rows(), [])

    async def test_postcommit_retirement_preserves_SQL_truth_but_suppresses_RAM(self):
        entered, release = self.block_connection(after_commit=True)
        sample = self.sample()
        task = asyncio.create_task(publish(SimpleNamespace(_status_samples=self.journal),
                                          self.source.active, sample))
        self.assertTrue(await asyncio.to_thread(entered.wait, 3))
        self.source.alive = False
        release.set()
        await task
        self.assertEqual(len(await self.rows()), 1)
        self.assertIsNone(self.source.active.broadcast.original_status_sample)
        self.assertIsNone(await self.journal.record(sample))

    async def test_exact_event_identity_cannot_be_reused_with_different_body(self):
        sample = self.sample()
        await self.journal.record(sample)
        conflict = replace(sample, state="paused", _consumed=[False])
        with self.assertRaises(PersistenceError):
            await self.journal.record(conflict)

    async def test_lost_commit_ACK_keeps_SQL_truth_without_RAM_publication_or_retry(self):
        original = self.service.async_in_transaction
        async def lose_ack(operation, **kwargs):
            await original(operation, **kwargs)
            raise OSError("synthetic_lost_status_commit_ack")
        sample = self.sample()
        with patch.object(self.service, "async_in_transaction", lose_ack):
            await publish(SimpleNamespace(_status_samples=self.journal), self.source.active, sample)
        self.assertEqual(len(await self.rows()), 1)
        self.assertIsNone(self.source.active.broadcast.original_status_sample)
        self.assertIsNone(await self.journal.record(sample))
