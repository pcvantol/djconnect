"""Disposable real SQLite stages; synthetic hashes, zero signer/provider calls."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import threading
import unittest

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from custom_components.djconnect.surface_push_contract import SurfacePushError
from custom_components.djconnect.surface_issuer_journal import (
    IssuerStageJournal, IssuerStageStore, MAX_IDENTITIES,
)

IDENTITY, BINDING, OPERATION, CHALLENGE, ISSUE, WITHDRAW = [c * 64 for c in 'abcdef']


class IssuerSQLiteStageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'issuer.sqlite'
        self.persistence = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        self.journal = IssuerStageJournal(IssuerStageStore(self.persistence))
        await self.journal.initialize()

    async def asyncTearDown(self):
        await self.persistence.async_close()
        self.directory.cleanup()

    async def row(self):
        return await self.persistence.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT revision,high_water_ms,body FROM djconnect_surface_issuer_journal WHERE singleton=1'))

    async def reserve(self, journal=None, *, identity=IDENTITY, operation=OPERATION, now=1000):
        return await (journal or self.journal).reserve_challenge(identity, BINDING,
            operation, CHALLENGE, now=now)

    async def test_same_original_operation_has_distinct_committed_challenge_and_issue_stages(self):
        receipt = await self.reserve()
        self.assertEqual(json.loads((await self.row())[2])['records'][IDENTITY]['phase'], 'challenge_reserved')
        await self.journal.complete_challenge(receipt, accepted=True, now=1001)
        await self.journal.reserve_issue(receipt, ISSUE, now=1002)
        row = json.loads((await self.row())[2])['records'][IDENTITY]
        self.assertEqual(row['operation'], OPERATION)
        self.assertEqual(row['challenge'], CHALLENGE)
        self.assertEqual(row['issue'], ISSUE)
        self.assertEqual(row['phase'], 'issue_reserved')
        await self.journal.complete_issue(receipt, accepted=True, now=1003)
        self.assertEqual(json.loads((await self.row())[2])['records'][IDENTITY]['phase'], 'credential_held')
        self.assertFalse(self.journal._live)
        for forbidden in ('djcs_', 'nonce', 'private_key', 'session_id', 'delegation_id', 'signature'):
            self.assertNotIn(forbidden, (await self.row())[2])

    async def test_new_uuid_or_binding_cannot_reissue_same_original_identity(self):
        await self.reserve()
        before = await self.row()
        with self.assertRaises(SurfacePushError):
            await self.reserve(operation='1' * 64, now=1001)
        self.assertEqual(await self.row(), before)

    async def test_issue_cannot_skip_challenge_or_move_to_another_receipt(self):
        receipt = await self.reserve()
        with self.assertRaises(SurfacePushError):
            await self.journal.reserve_issue(receipt, ISSUE, now=1001)
        await self.journal.complete_challenge(receipt, accepted=True, now=1002)
        for forged in (replace(receipt), replace(receipt, operation='1' * 64)):
            with self.assertRaises(SurfacePushError):
                await self.journal.reserve_issue(forged, ISSUE, now=1003)
        with self.assertRaises(SurfacePushError):
            await self.journal.reserve_issue(receipt, CHALLENGE, now=1004)
        await self.journal.reserve_issue(receipt, ISSUE, now=1005)
        with self.assertRaises(SurfacePushError):
            await self.journal.reserve_issue(receipt, ISSUE, now=1006)

    async def test_restart_has_no_ram_nonce_receipt_and_cannot_send_issue_or_reissue(self):
        receipt = await self.reserve()
        await self.journal.complete_challenge(receipt, accepted=True, now=1001)
        fresh = IssuerStageJournal(IssuerStageStore(self.persistence))
        await fresh.initialize()
        before = await self.row()
        with self.assertRaises(SurfacePushError):
            await fresh.reserve_issue(receipt, ISSUE, now=1002)
        with self.assertRaises(SurfacePushError):
            await self.reserve(fresh, operation='1' * 64, now=1003)
        self.assertEqual(await self.row(), before)
        self.assertFalse(fresh._live)

    async def test_unknown_challenge_or_issue_consumes_without_retry(self):
        receipt = await self.reserve()
        await self.journal.complete_challenge(receipt, accepted=False, now=1001)
        with self.assertRaises(SurfacePushError):
            await self.journal.reserve_issue(receipt, ISSUE, now=1002)
        second = await self.reserve(identity='1' * 64, now=1003)
        await self.journal.complete_challenge(second, accepted=True, now=1004)
        await self.journal.reserve_issue(second, ISSUE, now=1005)
        await self.journal.complete_issue(second, accepted=False, now=1006)
        with self.assertRaises(SurfacePushError):
            await self.reserve(identity='1' * 64, operation='2' * 64, now=1007)

    async def test_stale_store_revision_cannot_overwrite_original_consumed_operation(self):
        stale = IssuerStageJournal(IssuerStageStore(self.persistence))
        await stale.initialize()
        await self.reserve()
        before = await self.row()
        with self.assertRaises(SurfacePushError):
            await self.reserve(stale, operation='1' * 64, now=1001)
        self.assertTrue(stale._failed)
        self.assertEqual(await self.row(), before)

    async def test_two_journals_sharing_one_mutable_adapter_cannot_advance_each_others_cas_view(self):
        shared = IssuerStageStore(self.persistence)
        first = IssuerStageJournal(shared)
        await first.initialize()
        second, rejected = None, False
        try:
            second = IssuerStageJournal(shared)
            await second.initialize()
        except SurfacePushError:
            rejected = True  # Exclusive ownership may reject before the first save.
        await self.reserve(first)
        before = await self.row()
        if second is not None:
            try:
                await self.reserve(second, operation='1' * 64, now=1001)
            except SurfacePushError:
                rejected = True
        with self.subTest(boundary='second_owner_rejected'):
            self.assertTrue(rejected)
        with self.subTest(boundary='original_consumed_row_unchanged'):
            self.assertEqual(await self.row(), before)

    async def test_terminal_fence_precedes_lock_wait_and_late_issue_completion(self):
        receipt = await self.reserve()
        await self.journal.complete_challenge(receipt, accepted=True, now=1001)
        await self.journal.reserve_issue(receipt, ISSUE, now=1002)
        await self.journal._lock.acquire()
        task = asyncio.create_task(self.journal.terminal(IDENTITY, BINDING, OPERATION, WITHDRAW, now=1003))
        await asyncio.sleep(0)
        self.assertIn(IDENTITY, self.journal._withdrawn)
        self.assertNotIn(IDENTITY, self.journal._live)
        self.journal._lock.release()
        await task
        with self.assertRaises(SurfacePushError):
            await self.journal.complete_issue(receipt, accepted=True, now=1004)
        self.assertEqual(json.loads((await self.row())[2])['records'][IDENTITY]['phase'], 'withdrawn')

    async def test_terminal_before_any_local_attempt_is_durable_and_cannot_create_new_budget(self):
        await self.journal.terminal(IDENTITY, BINDING, OPERATION, WITHDRAW, now=1000, expired=True)
        fresh = IssuerStageJournal(IssuerStageStore(self.persistence))
        await fresh.initialize()
        with self.assertRaises(SurfacePushError):
            await self.reserve(fresh, now=1001)

    async def test_cancelled_terminal_caller_still_withdraws_original_ram_receipt_before_await(self):
        await self.reserve()
        async def cancel_then_withdraw():
            asyncio.current_task().cancel()
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                pass  # Cancellation count remains set; no uncancel.
            with self.assertRaises(asyncio.CancelledError):
                await self.journal.terminal(IDENTITY, BINDING, OPERATION, WITHDRAW, now=1001)
        await asyncio.create_task(cancel_then_withdraw())
        self.assertIn(IDENTITY, self.journal._withdrawn)
        self.assertNotIn(IDENTITY, self.journal._live)

    async def test_duplicate_sql_json_and_impossible_phase_cannot_load_as_valid_journal(self):
        await self.reserve()
        before = await self.row()
        data = json.loads(before[2])
        data['records'][IDENTITY]['issue'] = ISSUE
        invalid_phase = json.dumps(data)
        duplicate = before[2].replace('"version":1', '"version":1,"version":1')
        for body in (invalid_phase, duplicate):
            await self.persistence.async_in_transaction(lambda tx: tx.execute(
                'UPDATE djconnect_surface_issuer_journal SET body=? WHERE singleton=1', (body,)))
            fresh = IssuerStageJournal(IssuerStageStore(self.persistence))
            with self.subTest(body=body[:40]):
                with self.assertRaises(SurfacePushError):
                    await fresh.initialize()
                self.assertTrue(fresh._failed)

    async def test_capacity_never_evicts_consumed_or_expired_identity(self):
        for n in range(MAX_IDENTITIES):
            await self.reserve(identity=f'{n:064x}', now=1000 + n)
        before = await self.row()
        with self.assertRaises(SurfacePushError):
            await self.reserve(identity='f' * 64, now=99999999)
        self.assertEqual(await self.row(), before)

    async def test_backward_wall_clock_quarantines_without_repair_or_write(self):
        await self.reserve()
        before = await self.row()
        with self.assertRaises(SurfacePushError):
            await self.reserve(identity='1' * 64, now=999)
        self.assertTrue(self.journal._failed)
        self.assertEqual(await self.row(), before)

    async def test_real_sql_abort_keeps_original_empty_state_and_never_acknowledges(self):
        await self.persistence.async_in_transaction(lambda tx: tx.execute(
            "CREATE TRIGGER reject_issuer BEFORE UPDATE ON djconnect_surface_issuer_journal "
            "BEGIN SELECT RAISE(ABORT,'synthetic'); END"))
        with self.assertRaises(Exception):
            await self.reserve()
        self.assertTrue(self.journal._failed)
        self.assertEqual(json.loads((await self.row())[2])['records'], {})

    async def test_cancel_during_definitive_real_commit_retains_reservation_and_zero_next_effects(self):
        entered, release = threading.Event(), threading.Event()
        provider = self.persistence._provider
        original = provider._run_transaction
        effects = []
        def held(operation):
            def run(tx):
                result = operation(tx)
                row = tx.fetchone('SELECT revision FROM djconnect_surface_issuer_journal WHERE singleton=1')
                if row[0] == 1 and not entered.is_set():
                    entered.set()
                    if not release.wait(3):
                        raise RuntimeError('synthetic hold timed out')
                return result
            return original(run)
        provider._run_transaction = held
        async def lifecycle():
            await self.reserve()
            effects.append('synthetic-sign-or-HTTP-would-start')
        task = asyncio.create_task(lifecycle())
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(effects, [])
            self.assertFalse(self.journal._live)
            row = json.loads((await self.row())[2])['records'][IDENTITY]
            self.assertEqual(row['phase'], 'challenge_reserved')
            self.assertEqual(row['operation'], OPERATION)
        finally:
            release.set()
            provider._run_transaction = original
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_missing_table_is_not_lazily_recreated(self):
        await self.persistence.async_in_transaction(lambda tx: tx.execute('DROP TABLE djconnect_surface_issuer_journal'))
        fresh = IssuerStageJournal(IssuerStageStore(self.persistence))
        with self.assertRaises(Exception):
            await fresh.initialize()
        self.assertTrue(fresh._failed)
        count = await self.persistence.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT count(*) FROM sqlite_master WHERE name='djconnect_surface_issuer_journal'"))
        self.assertEqual(count[0], 0)
