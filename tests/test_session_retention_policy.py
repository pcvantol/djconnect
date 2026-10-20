"""Real SQLite Session-scoped retention; no source or auth grant is inferred."""
import unittest
import tempfile
from pathlib import Path
from datetime import UTC, datetime, timedelta
from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository, ACTIVE, ENDED
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
from custom_components.djconnect.historical_projection_query import HistoricalProjectionQueryService
from custom_components.djconnect.historical_projection_retention import HistoricalProjectionRetentionService


class SessionRetentionPolicyTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = PersistenceService(Path(self.tmp.name)/'history.sqlite', SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.sessions = PersistentSessionRepository(self.service)
        self.repo = HistoricalProjectionRepository(self.service)
        self.query = HistoricalProjectionQueryService(self.repo)

    async def asyncTearDown(self):
        await self.service.async_close()
        self.tmp.cleanup()

    async def start(self, owner='owner'):
        s = await self.sessions.async_create(owner)
        await self.sessions.async_transition(owner,s.session_id,ACTIVE)
        return s

    async def append(self, s, ref, stamp):
        await self.repo.async_append_entries(s.owner_profile_id,s.session_id,[{
            'kind':'dj_silence','reference_id':ref,'occurred_at':stamp,
            'body':{'moment_id':ref,'moment_type':'silence','content_state':'silence'}}])

    async def test_active_old_entries_survive_and_terminal_entries_share_one_deadline(self):
        s = await self.start()
        now = datetime.now(UTC)
        await self.append(s,'old',(now-timedelta(days=100)).isoformat())
        await self.append(s,'new',now.isoformat())
        self.assertEqual(len((await self.query.async_timeline_page('owner',s.session_id))['entries']),2)
        await self.sessions.async_transition('owner',s.session_id,ENDED,historical_projections=self.repo)
        record = await self.repo.async_session_record(s.session_id)
        rows = await self.repo.async_entry_records('owner',s.session_id)
        self.assertEqual({r['retained_until'] for r in rows},
            {(datetime.fromisoformat(record['ended_at'])+timedelta(days=90)).isoformat()})
        await self.service.async_close()
        await self.service.async_initialize()
        self.assertEqual(len((await self.query.async_timeline_page('owner',s.session_id))['entries']),2)

    async def test_policy_is_global_durable_admin_guarded_and_does_not_resurrect(self):
        s = await self.start()
        await self.append(s,'entry',datetime.now(UTC).isoformat())
        await self.sessions.async_transition('owner',s.session_id,ENDED,historical_projections=self.repo)
        old = (datetime.now(UTC)-timedelta(days=2)).isoformat()
        await self.service.async_in_transaction(lambda tx:(
            tx.execute('UPDATE djconnect_persistent_sessions SET ended_at=? WHERE session_id=?',(old,s.session_id)),
            tx.execute('UPDATE djconnect_historical_sessions SET created_at=? WHERE originating_session_id=?',(old,s.session_id))))
        for invalid in (0,91,True,1.5,'30'):
            with self.assertRaises(ValueError):
                await self.repo.async_set_retention_days(invalid,authorize=lambda:True)
        with self.assertRaises(PermissionError):
            await self.repo.async_set_retention_days(1,authorize=lambda:False)
        self.assertEqual(await self.repo.async_retention_policy(),(90,1))
        self.assertEqual(await self.repo.async_set_retention_days(1,authorize=lambda:True),(1,2))
        self.assertEqual((await self.query.async_session_page('owner'))['sessions'],[])
        await self.repo.async_set_retention_days(90,authorize=lambda:True)
        self.assertEqual((await self.query.async_session_page('owner'))['sessions'],[])
        other = await self.start('other')
        self.assertEqual((await self.query.async_session_page('other',include_active=True))['retention_days'],90)
        await self.service.async_close()
        await self.service.async_initialize()
        self.assertEqual(await self.repo.async_retention_policy(),(90,3))
        await self.repo.async_set_retention_days(1,authorize=lambda:True)
        result = await HistoricalProjectionRetentionService(self.repo).async_cleanup()
        self.assertEqual(result.deleted_sessions,1)
        self.assertEqual(await self.repo.async_entry_records('owner',s.session_id),[])
        self.assertEqual((await self.repo.async_session_record(other.session_id))['lifecycle_status'],ACTIVE)

    async def test_policy_change_during_last_grant_await_rejects_stale_response(self):
        from custom_components.djconnect.session_history_projection import HistoryQueryError
        s = await self.start()
        await self.sessions.async_transition('owner',s.session_id,ENDED,historical_projections=self.repo)
        old = (datetime.now(UTC)-timedelta(days=2)).isoformat()
        await self.service.async_in_transaction(lambda tx:tx.execute(
            'UPDATE djconnect_persistent_sessions SET ended_at=? WHERE session_id=?',(old,s.session_id)))
        async def grant(_owner):
            await self.repo.async_set_retention_days(1,authorize=lambda:True)
            return 'unchanged-source-grant'
        self.query._grant_revision = grant
        with self.assertRaises(HistoryQueryError):
            await self.query.async_timeline_page('owner',s.session_id)

    async def test_natural_expiry_during_last_source_grant_await_rejects_original_body(self):
        import asyncio
        from unittest.mock import patch
        from custom_components.djconnect.historical_projection_query import HistoricalProjectionAccessDenied
        now = datetime.now(UTC)
        deadline = now + timedelta(seconds=1)
        clock = [now]
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock[0]
        s = await self.start()
        await self.append(s, 'original-body', now.isoformat())
        await self.sessions.async_transition('owner', s.session_id, ENDED, historical_projections=self.repo)
        await self.service.async_in_transaction(lambda tx: (
            tx.execute('UPDATE djconnect_persistent_sessions SET ended_at=? WHERE session_id=?',
                ((deadline-timedelta(days=90)).isoformat(), s.session_id)),
            tx.execute('UPDATE djconnect_session_entries SET retained_until=? WHERE session_id=?',
                (deadline.isoformat(), s.session_id))))
        entry = (await self.repo.async_entry_records('owner', s.session_id))[0]['entry_id']
        entered, release = asyncio.Event(), asyncio.Event()
        grants = []
        async def grant(_owner):
            grants.append(True)
            if len(grants) == 2:
                entered.set()
                await release.wait()
            return 'unchanged-source-grant'
        self.query._grant_revision = grant
        with patch('custom_components.djconnect.session_history_projection.datetime', Clock):
            task = asyncio.create_task(self.query.async_open_source_entry('owner', s.session_id, entry))
            try:
                await asyncio.wait_for(entered.wait(), 2)
                clock[0] = deadline
            finally:
                release.set()
            with self.assertRaises(HistoricalProjectionAccessDenied):
                await task
        self.assertEqual(len(grants), 2)
        self.assertEqual(await self.repo.async_retention_policy(), (90, 1))

    async def test_retention_write_blocks_pending_and_existing_historical_image_grants(self):
        from custom_components.djconnect.image_proxy import ManagedSessionImages
        registry = ManagedSessionImages()
        self.service.session_image_owner = registry
        key = ('owner','session',(('entry_id','entry'),))
        invalidated = []
        registry.work_guards[key] = (None, lambda: invalidated.append(True))
        registry.assets[key] = {'body':b'old-image'}
        checks = []
        def authorize():
            checks.append(registry.history_blocked(key,{},None))
            self.assertNotIn(key,registry.assets)
            return True
        try:
            await self.repo.async_set_retention_days(1,authorize=authorize)
            self.assertTrue(checks)
            self.assertTrue(all(checks))
            self.assertTrue(invalidated)
            self.assertEqual(registry.history_barriers,{})
            self.assertEqual(self.repo.retention_fence[1],0)
        finally:
            registry.close()
