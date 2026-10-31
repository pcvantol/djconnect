"""Actual disposable SQLite once history; synthetic owner checks, no display."""
import asyncio
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository, ACTIVE, ENDED
from custom_components.djconnect import direct_rich_store as store
from custom_components.djconnect.direct_rich_wire import RichError, digest


class DirectRichStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'synthetic-rich.sqlite'
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.sessions = PersistentSessionRepository(self.service)
        session = await self.sessions.async_create('synthetic-owner', initial_mood='chill')
        await self.sessions.async_transition('synthetic-owner', session.session_id, ACTIVE)
        self.session = session.session_id
        self.journal = store.RichPurposeJournal(self.service)
        self.original = store.RichOriginal('a' * 64, str(uuid4()), str(uuid4()),
            digest(['DJC-DIRECT-RICH-OWNER-V1', 'synthetic-owner']),
            'c' * 64, 'd' * 64, 'e' * 64,
            digest(['DJC-DIRECT-RICH-SESSION-V1', self.session]),
            'live_activity', '1' * 64, 1000000, 29800000)
        self.current = True

    async def asyncTearDown(self):
        await self.service.async_close()
        self.temp.cleanup()

    def allowed(self):
        return self.current

    def ownership(self, original=None):
        o = original or self.original
        return o.owner_hash, o.device_hash, o.entry_hash, o.pair_hash, o.session_hash, o.surface

    async def reserve(self, original=None):
        return await self.journal.reserve(original or self.original, session_id=self.session,
            owner_id='synthetic-owner', current=self.allowed)

    async def phase(self):
        return await self.service.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT phase FROM djconnect_rich_purposes WHERE scope_hash=?',
            (self.original.scope_hash,)))

    async def test_actual_reserve_issue_terminal_metadata_has_no_secret_or_recovery(self):
        self.assertEqual(await self.reserve(), self.original)
        self.assertEqual(await self.phase(), ('reserved',))
        await self.journal.issued(self.original, session_id=self.session,
            owner_id='synthetic-owner', current=self.allowed)
        self.assertEqual(await self.phase(), ('issued',))
        original, phase = await self.journal.history(self.original.operation_id,
            self.ownership(), current=self.allowed, withdraw=True)
        self.assertEqual((original, phase), (self.original, 'withdrawn'))
        columns = await self.service.async_in_transaction(lambda tx: tx.fetchall(
            'PRAGMA table_info(djconnect_rich_purposes)'))
        self.assertEqual({row[1] for row in columns}, set(store.FIELDS) | {'phase'})
        self.assertTrue(all('secret' not in row[1] and 'credential' not in row[1] for row in columns))

    async def test_new_uuid_or_lifetime_does_not_evade_original_unique_scope(self):
        await self.reserve()
        for replacement in (self.original, replace(self.original, operation_id=str(uuid4()),
                purpose_id=str(uuid4()), issued_ms=2000000, expires_ms=30800000)):
            with self.subTest(operation=replacement.operation_id), self.assertRaises(RichError) as caught:
                await self.reserve(replacement)
            self.assertEqual(caught.exception.code, 'rich_purpose_consumed')
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.journal = store.RichPurposeJournal(self.service)
        with self.assertRaises(RichError) as caught:
            await self.reserve(replace(self.original, operation_id=str(uuid4()), purpose_id=str(uuid4())))
        self.assertEqual(caught.exception.code, 'rich_purpose_consumed')

    async def test_negative_history_after_real_session_end_and_wrong_generation_denial(self):
        await self.reserve()
        await self.sessions.async_transition('synthetic-owner', self.session, ENDED)
        for wrong in (replace(self.original, pair_hash='2' * 64),
                replace(self.original, owner_hash='3' * 64), replace(self.original, session_hash='4' * 64)):
            with self.subTest(wrong=wrong), self.assertRaises(RichError) as caught:
                await self.journal.history(self.original.operation_id,
                    self.ownership(wrong), current=self.allowed, withdraw=True)
            self.assertEqual(caught.exception.code, 'rich_history_unknown')
            self.assertEqual(await self.phase(), ('reserved',))
        _, phase = await self.journal.history(self.original.operation_id,
            self.ownership(), current=self.allowed, withdraw=True)
        self.assertEqual(phase, 'withdrawn')
        _, phase = await self.journal.history(self.original.operation_id,
            self.ownership(), current=self.allowed, withdraw=True)
        self.assertEqual(phase, 'withdrawn')

    async def test_actual_session_owner_and_lifecycle_are_checked_in_issue_transaction(self):
        with self.assertRaises(RichError):
            await self.journal.reserve(self.original, session_id=self.session,
                owner_id='different-owner', current=self.allowed)
        self.assertIsNone(await self.phase())
        await self.reserve()
        await self.sessions.async_transition('synthetic-owner', self.session, ENDED)
        with self.assertRaises(RichError):
            await self.journal.issued(self.original, session_id=self.session,
                owner_id='synthetic-owner', current=self.allowed)
        self.assertEqual(await self.phase(), ('reserved',))

    async def test_original_capacity_keeps_terminal_rows_and_refuses_new_scope(self):
        with patch.object(store, 'MAX_ROWS', 1):
            await self.reserve()
            await self.journal.history(self.original.operation_id,
                self.ownership(), current=self.allowed, withdraw=True)
            with self.assertRaises(RichError) as caught:
                await self.reserve(replace(self.original, scope_hash='5' * 64,
                    operation_id=str(uuid4()), purpose_id=str(uuid4())))
            self.assertEqual(caught.exception.code, 'rich_capacity')
        self.assertEqual(await self.phase(), ('withdrawn',))

    async def test_real_commit_lost_ack_never_reissues_original_scope(self):
        actual = self.service.async_in_transaction

        async def lost(operation, **options):
            await actual(operation, **options)
            raise OSError('synthetic_lost_ack')

        with patch.object(self.service, 'async_in_transaction', side_effect=lost):
            with self.assertRaises(RichError) as caught:
                await self.reserve()
            self.assertEqual(caught.exception.code, 'rich_unavailable')
        self.assertEqual(await self.phase(), ('reserved',))
        with self.assertRaises(RichError) as caught:
            await self.reserve()
        self.assertEqual(caught.exception.code, 'rich_purpose_consumed')

    async def test_actual_commit_then_cancel_preserves_row_and_propagates_cancel(self):
        actual = self.service.async_in_transaction

        async def cancelled(operation, **options):
            value = await actual(operation, **options)
            asyncio.current_task().cancel()
            return value

        with patch.object(self.service, 'async_in_transaction', side_effect=cancelled):
            task = asyncio.create_task(self.reserve())
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(task.cancelled())
        self.assertEqual(await self.phase(), ('reserved',))
        with self.assertRaises(RichError):
            await self.reserve()

    async def test_commit_owner_loss_and_false_or_nonboolean_guard_stay_closed(self):
        actual = self.service.async_in_transaction

        async def owner_lost(operation, **options):
            value = await actual(operation, **options)
            self.current = False
            return value

        with patch.object(self.service, 'async_in_transaction', side_effect=owner_lost):
            with self.assertRaises(RichError):
                await self.reserve()
        self.assertEqual(await self.phase(), ('reserved',))
        for value in (False, 1, 'true', None):
            with self.subTest(value=value), self.assertRaises(RichError):
                await self.journal.history(self.original.operation_id, self.ownership(),
                    current=lambda: value)

    async def test_malformed_stored_metadata_is_unavailable_not_client_input_error(self):
        await self.reserve()
        await self.service.async_in_transaction(lambda tx: tx.execute(
            "UPDATE djconnect_rich_purposes SET owner_hash=?", ('Z' * 64,)))
        with self.assertRaises(RichError) as caught:
            await self.journal.history(self.original.operation_id,
                self.ownership(), current=self.allowed)
        self.assertEqual((caught.exception.code, caught.exception.status), ('rich_unavailable', 503))

    async def test_actual_reservation_commit_uses_WAL_FULL_then_restores_normal(self):
        seen = []
        provider = self.service._provider
        actual = provider._async_guarded_transaction

        async def inspect(operation, finalize):
            def read_and_write(tx):
                seen.append((tx.fetchone('PRAGMA journal_mode')[0],
                    tx.fetchone('PRAGMA synchronous')[0]))
                return operation(tx)
            return await actual(read_and_write, finalize)

        with patch.object(provider, '_async_guarded_transaction', side_effect=inspect):
            await self.reserve()
        self.assertEqual(seen, [('wal', 2)])
        self.assertEqual(await self.service.async_in_transaction(lambda tx:
            tx.fetchone('PRAGMA synchronous')[0]), 1)
        self.assertEqual(self.service.readiness.schema_version, 20)

    async def test_actual_postcommit_close_reopen_cannot_acknowledge_under_new_store_lifetime(self):
        actual = self.service.async_in_transaction

        async def reopened(operation, **options):
            value = await actual(operation, **options)
            await self.service.async_close()
            await self.service.async_initialize()
            return value

        with patch.object(self.service, 'async_in_transaction', side_effect=reopened):
            with self.assertRaises(RichError) as caught:
                await self.reserve()
            self.assertEqual((caught.exception.code, caught.exception.status), ('rich_unavailable', 503))
        self.assertEqual(await self.phase(), ('reserved',))
        with self.assertRaises(RichError):
            await self.journal.history(self.original.operation_id,
                self.ownership(), current=self.allowed)
        self.journal = store.RichPurposeJournal(self.service)
        with self.assertRaises(RichError) as caught:
            await self.reserve()
        self.assertEqual(caught.exception.code, 'rich_purpose_consumed')

    async def test_other_active_session_cannot_issue_original_ended_session_reservation(self):
        await self.reserve()
        await self.sessions.async_transition('synthetic-owner', self.session, ENDED)
        other = await self.sessions.async_create('synthetic-other-owner', initial_mood='chill')
        await self.sessions.async_transition('synthetic-other-owner', other.session_id, ACTIVE)
        with self.assertRaises(RichError):
            await self.journal.issued(self.original, session_id=other.session_id,
                owner_id='synthetic-other-owner', current=self.allowed)
        self.assertEqual(await self.phase(), ('reserved',))

    async def test_other_session_owner_cannot_supply_original_reservation_SQL_coordinates(self):
        other = await self.sessions.async_create('synthetic-other-owner', initial_mood='chill')
        await self.sessions.async_transition('synthetic-other-owner', other.session_id, ACTIVE)
        with self.assertRaises(RichError):
            await self.journal.reserve(self.original, session_id=other.session_id,
                owner_id='synthetic-other-owner', current=self.allowed)
        self.assertIsNone(await self.phase())

    async def test_same_owner_new_active_session_cannot_issue_original_ended_scope(self):
        await self.reserve()
        await self.sessions.async_transition('synthetic-owner', self.session, ENDED)
        other = await self.sessions.async_create('synthetic-owner', initial_mood='chill')
        await self.sessions.async_transition('synthetic-owner', other.session_id, ACTIVE)
        with self.assertRaises(RichError):
            await self.journal.issued(self.original, session_id=other.session_id,
                owner_id='synthetic-owner', current=self.allowed)
        self.assertEqual(await self.phase(), ('reserved',))

    async def test_actual_issue_commit_then_close_reopen_keeps_consumed_metadata_without_ACK(self):
        await self.reserve()
        actual = self.service.async_in_transaction

        async def reopened(operation, **options):
            value = await actual(operation, **options)
            await self.service.async_close()
            await self.service.async_initialize()
            return value

        with patch.object(self.service, 'async_in_transaction', side_effect=reopened):
            with self.assertRaises(RichError):
                await self.journal.issued(self.original, session_id=self.session,
                    owner_id='synthetic-owner', current=self.allowed)
        self.assertEqual(await self.phase(), ('issued',))
        self.journal = store.RichPurposeJournal(self.service)
        with self.assertRaises(RichError):
            await self.reserve()


if __name__ == '__main__':
    unittest.main()
