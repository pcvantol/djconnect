"""Real SQLite atomicity, replay, failure, lifecycle and schema7 migration."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from uuid import UUID

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from custom_components.djconnect.domain.profile.dj_settings import DJSettings
from custom_components.djconnect.persistence.dj_settings import (
    ProfileDJSettingsRepository, SessionSettingsContext, SettingsCommitError,
    SettingsRevisionConflict,
)
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository, ACTIVE, ENDED
from custom_components.djconnect.persistence.schema import apply_migration


def operation(now, counter=1):
    return str(UUID(int=(now << 80) | (7 << 76) | (2 << 62) | counter))


class ProfileDJSettingsPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'settings.sqlite'
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.repo = ProfileDJSettingsRepository(self.service)
        self.sessions = PersistentSessionRepository(self.service)
        self.history = HistoricalProjectionRepository(self.service)
        session = await self.sessions.async_create('owner', initial_mood='chill')
        await self.sessions.async_transition('owner', session.session_id, ACTIVE)
        self.sid = session.session_id
        self.now = int(datetime.now(UTC).timestamp()*1000)+10
        self.binding = 'a'*64

    async def asyncTearDown(self):
        await self.service.async_close()
        self.directory.cleanup()

    def context(self, revision=0, effective=None):
        return SessionSettingsContext(self.sid, 'original-generation', revision,
                                      effective or DJSettings(mood='chill'))

    async def choose(self, patch_value, *, expected=0, op=None, binding=None,
                     now=None, context=None, authorize=lambda: True):
        return await self.repo.async_accept_user_choice('owner',
            operation_id=op or operation(self.now), binding=binding or self.binding,
            patch=patch_value, expected_defaults_revision=expected,
            now_ms=now or self.now, session=context, authorize=authorize)

    async def read(self):
        return await self.repo.async_read('owner', session_id=self.sid, authorize=lambda: True)

    async def test_combined_defaults_session_and_mood_acceptance_persists(self):
        accepted = await self.choose({'persona':'club_dj','mood':'party',
            'presence':'music_only','voice':{'kind':'provider_voice','provider_id':'p','voice_id':'v'},
            'gender':'female'}, context=self.context())
        snapshot = accepted['snapshot']
        self.assertEqual(snapshot['defaults'], snapshot['session']['settings'])
        self.assertEqual(snapshot['defaults_revision'], 1)
        self.assertEqual(snapshot['session']['revision'], 1)
        row = await self.service.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT mood_current FROM djconnect_session_summaries WHERE session_id=?',(self.sid,)))
        self.assertEqual(row, ('party',))
        await self.service.async_close()
        await self.service.async_initialize()
        self.assertEqual((await self.read())['defaults'], snapshot['defaults'])

    async def test_read_without_preferences_is_pure_and_no_session_edit_starts_nothing(self):
        before = await self.read()
        self.assertFalse(before['activated'])
        self.assertEqual(before['defaults_revision'],0)
        for _ in range(3):
            self.assertEqual(await self.read(),before)
        row = await self.service.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT COUNT(*) FROM djconnect_profile_dj_settings'))
        self.assertEqual(row,(0,))
        result = await self.choose({'persona':'festival_dj'})
        self.assertIsNone(result['snapshot']['session'])
        counts = await self.service.async_in_transaction(lambda tx:(
            tx.fetchone('SELECT COUNT(*) FROM djconnect_persistent_sessions')[0],
            tx.fetchone('SELECT COUNT(*) FROM djconnect_session_dj_settings')[0]))
        self.assertEqual(counts,(1,0))
        self.assertEqual(result['snapshot']['defaults']['mood'],'groove')

    async def test_replay_digest_scope_and_expiry_cannot_accept_twice(self):
        first = await self.choose({'persona':'radio_dj'})
        replay = await self.choose({'persona':'radio_dj'})
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['snapshot'],first['snapshot'])
        for extra in ({'binding':'b'*64},):
            with self.assertRaisesRegex(SettingsCommitError,'operation_scope_changed'):
                await self.choose({'persona':'radio_dj'},**extra)
        with self.assertRaisesRegex(SettingsCommitError,'operation_payload_conflict'):
            await self.choose({'mood':'party'})
        with self.assertRaisesRegex(SettingsCommitError,'operation_expired'):
            await self.choose({'persona':'radio_dj'},now=self.now+300000)
        later=self.now+300001
        await self.choose({'mood':'chill'},expected=1,op=operation(later),now=later)
        with self.assertRaisesRegex(SettingsCommitError,'operation_expired'):
            await self.choose({'persona':'radio_dj'},now=self.now)

    async def test_concurrent_edits_have_one_winner_and_require_fresh_revision(self):
        results = await asyncio.gather(
            self.choose({'persona':'club_dj'}),
            self.choose({'mood':'party'},op=operation(self.now,2)), return_exceptions=True)
        self.assertEqual(sum(isinstance(x,dict) for x in results),1)
        self.assertEqual(sum(isinstance(x,SettingsRevisionConflict) for x in results),1)
        current=await self.read()
        next_value=await self.choose({'gender':'female'},expected=1,op=operation(self.now,3))
        self.assertEqual(next_value['snapshot']['defaults']['persona'],current['defaults']['persona'])
        self.assertEqual(next_value['snapshot']['defaults']['mood'],current['defaults']['mood'])

    async def test_final_authority_refusal_rolls_back_defaults_session_and_summary(self):
        count=0
        def authorize():
            nonlocal count
            count+=1
            return count==1
        with self.assertRaises(PermissionError):
            await self.choose({'mood':'party'},context=self.context(),authorize=authorize)
        self.assertEqual((await self.read())['defaults_revision'],0)
        self.assertIsNone((await self.read())['session'])
        row=await self.service.async_in_transaction(lambda tx:tx.fetchone(
            'SELECT mood_current FROM djconnect_session_summaries WHERE session_id=?',(self.sid,)))
        self.assertEqual(row,('chill',))
        accepted=await self.choose({'mood':'party'},context=self.context())
        self.assertFalse(accepted['replayed'])

    async def test_capacity_failure_after_staged_mood_work_is_fully_rolled_back(self):
        with patch('custom_components.djconnect.persistence.dj_settings.MAX_OWNER_RECORDS',1):
            await self.choose({'persona':'club_dj'})
            with self.assertRaisesRegex(SettingsCommitError,'settings_operation_capacity'):
                await self.choose({'mood':'party'},expected=1,
                    op=operation(self.now,2),context=self.context())
            self.assertTrue((await self.choose({'persona':'club_dj'}))['replayed'])
        current=await self.read()
        self.assertIsNone(current['session'])
        self.assertEqual(current['defaults']['mood'],'groove')
        row=await self.service.async_in_transaction(lambda tx:tx.fetchone(
            'SELECT mood_current FROM djconnect_session_summaries WHERE session_id=?',(self.sid,)))
        self.assertEqual(row,('chill',))

    async def test_cancel_during_definitive_acceptance_keeps_one_recoverable_commit(self):
        reached=threading.Event()
        release=threading.Event()
        def staged(settings):
            reached.set()
            if not release.wait(5):
                raise AssertionError('test synchronization timeout')
        task=asyncio.create_task(self.repo.async_accept_user_choice('owner',
            operation_id=operation(self.now), binding=self.binding,
            patch={'persona':'festival_dj'}, expected_defaults_revision=0,
            now_ms=self.now, authorize=lambda: True, validate_choices=staged))
        self.assertTrue(await asyncio.to_thread(reached.wait,5))
        task.cancel()
        release.set()
        accepted=await task
        self.assertTrue(accepted['accepted'])
        self.assertTrue((await self.choose({'persona':'festival_dj'}))['replayed'])
        self.assertEqual((await self.read())['defaults_revision'],1)

    async def test_closed_or_wrong_generation_session_cannot_change_defaults(self):
        first=await self.choose({'mood':'energy'},context=self.context())
        effective=DJSettings.from_dict(first['snapshot']['session']['settings'])
        wrong=SessionSettingsContext(self.sid,'successor-generation',1,effective)
        with self.assertRaisesRegex(SettingsCommitError,'session_generation_changed'):
            await self.choose({'persona':'radio_dj'},expected=1,op=operation(self.now,2),context=wrong)
        await self.sessions.async_transition('owner',self.sid,ENDED,historical_projections=self.history)
        with self.assertRaisesRegex(SettingsCommitError,'session_context_changed'):
            await self.choose({'persona':'radio_dj'},expected=1,op=operation(self.now,2),
                              context=self.context(1,effective))
        self.assertEqual((await self.read())['defaults']['persona'],'home_dj')

    async def test_real_v6_upgrade_creates_no_invented_profile_choices(self):
        old_path=Path(self.directory.name)/'old-v6.sqlite'
        provider=SQLitePersistenceProvider()
        await provider.async_open(str(old_path))
        for version in range(1,7):
            await provider.async_run_transaction(lambda tx,v=version:apply_migration(tx,v))
        await provider.async_close()
        upgraded=PersistenceService(old_path,SQLitePersistenceProvider())
        try:
            await upgraded.async_initialize()
            result=await ProfileDJSettingsRepository(upgraded).async_read('owner',authorize=lambda:True)
            self.assertFalse(result['activated'])
            self.assertEqual(result['defaults_revision'],0)
            self.assertEqual(result['defaults'],DJSettings().as_dict())
        finally:
            await upgraded.async_close()

    async def test_authority_is_loop_owned_and_last_staged_revocation_rolls_back(self):
        loop = asyncio.get_running_loop()
        loop_thread = threading.get_ident()
        authorized = True
        checks = []
        def authority():
            self.assertEqual(threading.get_ident(), loop_thread)
            checks.append(True)
            return authorized
        def revoke():
            nonlocal authorized
            authorized = False
        def staged(settings):
            # Real SQL is staged in a worker; authority changes on HA's loop
            # before the final admission. No HA API is called by this callback.
            done = threading.Event()
            def revoked():
                revoke()
                done.set()
            loop.call_soon_threadsafe(revoked)
            self.assertTrue(done.wait(5))
        with self.assertRaises(PermissionError):
            await self.repo.async_accept_user_choice('owner',
                operation_id=operation(self.now), binding=self.binding,
                patch={'mood':'party'}, expected_defaults_revision=0,
                now_ms=self.now, session=self.context(), authorize=authority,
                validate_choices=staged)
        self.assertEqual(len(checks), 2)
        self.assertEqual((await self.read())['defaults_revision'], 0)
        self.assertIsNone((await self.read())['session'])

    async def test_expiry_during_provider_lock_wait_or_sql_stage_never_commits(self):
        clock = self.now
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.fromtimestamp(clock/1000, UTC)
        op = operation(self.now-299999)
        provider = self.service._provider
        with patch('custom_components.djconnect.persistence.dj_settings.datetime', Clock):
            await provider._write_lock.acquire()
            task = asyncio.create_task(self.choose({'mood':'party'}, op=op,
                                                   context=self.context()))
            await asyncio.sleep(0)
            clock += 2
            provider._write_lock.release()
            with self.assertRaisesRegex(SettingsCommitError, 'operation_expired'):
                await task
            self.assertEqual((await self.read())['defaults_revision'], 0)
            clock = self.now
            def expire_staged(settings):
                nonlocal clock
                clock += 2
            with self.assertRaisesRegex(SettingsCommitError, 'operation_expired'):
                await self.repo.async_accept_user_choice('owner', operation_id=op,
                    binding=self.binding, patch={'mood':'party'}, expected_defaults_revision=0,
                    now_ms=self.now, session=self.context(), authorize=lambda: True,
                    validate_choices=expire_staged)
        self.assertEqual((await self.read())['defaults_revision'], 0)
        self.assertIsNone((await self.read())['session'])
        row = await self.service.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT mood_current FROM djconnect_session_summaries WHERE session_id=?', (self.sid,)))
        self.assertEqual(row, ('chill',))

    async def test_mood_acceptance_timestamp_uses_clock_after_lock_wait(self):
        clock = self.now + 5000
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.fromtimestamp(clock/1000, UTC)
        with patch('custom_components.djconnect.persistence.dj_settings.datetime', Clock):
            result = await self.choose({'mood':'party'}, context=self.context())
        self.assertEqual(result['snapshot']['session']['updated_at'],
                         datetime.fromtimestamp(clock/1000, UTC).isoformat())
