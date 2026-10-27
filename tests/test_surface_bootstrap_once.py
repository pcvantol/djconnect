"""Real disposable SQLite CAS; synthetic comparison data, no permission grant.

DDL below is a TEST fixture, not a runtime migration or power-loss proof.
"""
import asyncio
from dataclasses import astuple, replace
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from custom_components.djconnect.surface_bootstrap_once import (
    BootstrapOnceError, BootstrapOnceJournal, BootstrapOnceStore, OnceRow,
)

IDENTITY, BINDING, ORIGINAL_ACTION, VIEW_ACTION, APPROVAL_ACTION, CLAIM_ACTION = [c * 64 for c in 'abcdef']


class SQLiteFixtureStore(BootstrapOnceStore):
    """Actual platform transaction adapter for this test-only table, not authority."""
    def __init__(self, persistence):
        super().__init__()
        self.persistence = persistence
        self.after_commit = None

    async def insert(self, row):
        row.validate()
        def run(tx):
            count = tx.fetchone('SELECT COUNT(*) FROM bootstrap_once_test')[0]
            if count >= 64:
                raise BootstrapOnceError('full')
            try:
                tx.execute('INSERT INTO bootstrap_once_test VALUES (?,?,?,?,?)', astuple(row))
            except sqlite3.IntegrityError:
                raise BootstrapOnceError('conflict') from None
        await self.persistence.async_in_transaction(run)
        if self.after_commit:
            await self.after_commit()

    async def compare_and_swap(self, original, successor):
        original.validate()
        successor.validate()
        def run(tx):
            current = tx.fetchone('SELECT * FROM bootstrap_once_test WHERE identity=?', (original.identity,))
            if current != astuple(original):
                raise BootstrapOnceError('conflict')
            tx.execute('UPDATE bootstrap_once_test SET revision=?,phase=?,action=? WHERE identity=?',
                (successor.revision, successor.phase, successor.action, original.identity))
        await self.persistence.async_in_transaction(run)
        if self.after_commit:
            await self.after_commit()


class BootstrapOnceSQLiteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.persistence = PersistenceService(Path(self.directory.name) / 'once.sqlite', SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        await self.persistence.async_in_transaction(lambda tx: tx.execute(
            'CREATE TABLE bootstrap_once_test(identity TEXT PRIMARY KEY,binding TEXT NOT NULL,'
            'revision INTEGER NOT NULL,phase TEXT NOT NULL,action TEXT NOT NULL)'))
        self.store = SQLiteFixtureStore(self.persistence)
        self.journal = BootstrapOnceJournal(self.store)

    async def asyncTearDown(self):
        await self.persistence.async_close()
        self.directory.cleanup()

    async def row(self):
        return await self.persistence.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT * FROM bootstrap_once_test WHERE identity=?', (IDENTITY,)))

    async def candidate(self):
        p = self.journal.begin(IDENTITY, BINDING, ORIGINAL_ACTION)
        await self.journal.commit_candidate(p)
        return p

    async def approved(self):
        p = await self.candidate()
        await self.journal.advance(p, 'view_reserved', VIEW_ACTION)
        await self.journal.advance(p, 'approval_recorded', APPROVAL_ACTION)
        return p

    async def test_reservation_is_synchronous_and_original_identity_not_new_uuid(self):
        p = self.journal.begin(IDENTITY, BINDING, ORIGINAL_ACTION)
        with self.assertRaises(BootstrapOnceError):
            self.journal.begin(IDENTITY, BINDING, CLAIM_ACTION)
        self.assertIsNone(await self.row())
        await self.journal.commit_candidate(p)
        self.assertEqual((await self.row())[2:], (0, 'candidate', ORIGINAL_ACTION))

    async def test_claim_consumed_once_and_no_status_recovery_or_secret_store(self):
        p = await self.approved()
        await self.journal.advance(p, 'claim_reserved', CLAIM_ACTION)
        before = await self.row()
        with self.assertRaises(BootstrapOnceError):
            await self.journal.advance(p, 'claim_reserved', ORIGINAL_ACTION)
        self.assertEqual(await self.row(), before)
        self.assertEqual(before, (IDENTITY, BINDING, 3, 'claim_reserved', CLAIM_ACTION))

    async def test_cannot_skip_view_approval_or_candidate_commit(self):
        p = self.journal.begin(IDENTITY, BINDING, ORIGINAL_ACTION)
        with self.assertRaises(BootstrapOnceError):
            await self.journal.advance(p, 'claim_reserved', CLAIM_ACTION)
        await self.journal.commit_candidate(p)
        with self.assertRaises(BootstrapOnceError):
            await self.journal.advance(p, 'approval_recorded', APPROVAL_ACTION)

    async def test_restart_cannot_reuse_receipt_or_reissue_new_action(self):
        p = await self.approved()
        fresh = BootstrapOnceJournal(SQLiteFixtureStore(self.persistence))
        with self.assertRaises(BootstrapOnceError):
            await fresh.advance(p, 'claim_reserved', CLAIM_ACTION)
        replacement = fresh.begin(IDENTITY, BINDING, CLAIM_ACTION)
        with self.assertRaises(BootstrapOnceError):
            await fresh.commit_candidate(replacement)
        self.assertEqual((await self.row())[3], 'approval_recorded')

    async def test_two_independent_adapters_have_one_sqlite_insert_winner(self):
        other = BootstrapOnceJournal(SQLiteFixtureStore(self.persistence))
        p = self.journal.begin(IDENTITY, BINDING, ORIGINAL_ACTION)
        q = other.begin(IDENTITY, BINDING, APPROVAL_ACTION)
        result = await asyncio.gather(self.journal.commit_candidate(p), other.commit_candidate(q), return_exceptions=True)
        self.assertEqual(sum(x is None for x in result), 1)
        self.assertEqual(sum(isinstance(x, BootstrapOnceError) for x in result), 1)
        self.assertEqual((await self.row())[2], 0)

    async def test_stale_binding_or_revision_cannot_update_existing_row(self):
        p = await self.candidate()
        original = p.row
        successor = replace(original, revision=1, phase='view_reserved', action=VIEW_ACTION)
        with self.assertRaises(BootstrapOnceError):
            await SQLiteFixtureStore(self.persistence).compare_and_swap(replace(original, binding=CLAIM_ACTION), successor)
        await self.journal.advance(p, 'view_reserved', VIEW_ACTION)
        with self.assertRaises(BootstrapOnceError):
            await SQLiteFixtureStore(self.persistence).compare_and_swap(original, successor)

    async def test_retire_before_pending_commit_ack_is_terminal(self):
        committed, release = asyncio.Event(), asyncio.Event()
        async def hold():
            committed.set()
            await release.wait()
        self.store.after_commit = hold
        p = self.journal.begin(IDENTITY, BINDING, ORIGINAL_ACTION)
        task = asyncio.create_task(self.journal.commit_candidate(p))
        await committed.wait()
        self.journal.retire(p)
        release.set()
        with self.assertRaises(BootstrapOnceError):
            await task
        self.assertEqual((await self.row())[3], 'candidate')  # Committed, never rolled back.
        with self.assertRaises(BootstrapOnceError):
            await self.journal.advance(p, 'view_reserved', VIEW_ACTION)

    async def test_lost_claim_reply_preserves_committed_consumption(self):
        p = await self.approved()
        async def lost():
            raise OSError('synthetic lost acknowledgement')
        self.store.after_commit = lost
        with self.assertRaises(OSError):
            await self.journal.advance(p, 'claim_reserved', CLAIM_ACTION)
        self.assertEqual((await self.row())[3], 'claim_reserved')
        self.store.after_commit = None
        with self.assertRaises(BootstrapOnceError):
            await self.journal.advance(p, 'claim_reserved', ORIGINAL_ACTION)

    async def test_consumed_cancellation_after_actual_commit_does_not_allow_reply(self):
        p = await self.approved()
        async def consume_delivery():
            task = asyncio.current_task()
            task.cancel()
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                pass  # Simulate acknowledged SQLite commit consuming cancellation delivery.
        self.store.after_commit = consume_delivery
        task = asyncio.create_task(self.journal.advance(p, 'claim_reserved', CLAIM_ACTION))
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual((await self.row())[3], 'claim_reserved')
        with self.assertRaises(BootstrapOnceError):
            await self.journal.advance(p, 'claim_reserved', ORIGINAL_ACTION)

    async def test_terminal_fence_and_persisted_retirement_never_rearm(self):
        p = await self.approved()
        self.journal.retire(p)
        with self.assertRaises(BootstrapOnceError):
            await self.journal.advance(p, 'claim_reserved', CLAIM_ACTION)
        await self.journal.persist_retirement(p, CLAIM_ACTION)
        self.assertEqual((await self.row())[3], 'retired')
        with self.assertRaises(BootstrapOnceError):
            self.journal.begin(IDENTITY, BINDING, ORIGINAL_ACTION)

    async def test_forged_receipt_and_shared_adapter_rejected(self):
        p = await self.candidate()
        with self.assertRaises(BootstrapOnceError):
            await self.journal.advance(replace(p), 'view_reserved', VIEW_ACTION)
        with self.assertRaises(BootstrapOnceError):
            BootstrapOnceJournal(self.store)

    async def test_capacity_never_evicts_original_identity(self):
        for n in range(64):
            p = self.journal.begin(f'{n:064x}', BINDING, ORIGINAL_ACTION)
            await self.journal.commit_candidate(p)
        with self.assertRaises(BootstrapOnceError):
            self.journal.begin('f' * 64, BINDING, ORIGINAL_ACTION)
        count = await self.persistence.async_in_transaction(lambda tx: tx.fetchone('SELECT COUNT(*) FROM bootstrap_once_test'))
        self.assertEqual(count, (64,))

    async def test_grammar_rejects_raw_ids_and_boolean_revision(self):
        with self.assertRaises(BootstrapOnceError):
            self.journal.begin('private-session-id', BINDING, ORIGINAL_ACTION)
        with self.assertRaises(BootstrapOnceError):
            OnceRow(IDENTITY, BINDING, True, 'candidate', ORIGINAL_ACTION).validate()
