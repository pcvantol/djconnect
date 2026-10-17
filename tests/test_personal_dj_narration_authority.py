"""Real Store/SQLite race fences; only HA model replies are explicit fixtures."""
import asyncio
from pathlib import Path
import json
import threading
import unittest
from unittest.mock import patch

from tests import test_session_conversation_history as fixtures
from tests.context_variation_fixtures import source


class NarrationAuthorityTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture=fixtures.SessionConversationHistoryTest()
        await self.fixture.asyncSetUp()
        self.hass,self.runtime,_,self.identity,self.headers=await self.fixture.transport_fixture()
        self.handlers=self.fixture.handlers
        self.manager=self.fixture.manager
        self.module=fixtures.SessionConversationHistoryTest.runtime
        self.session=await self.manager.async_start(owner_profile_id='profile-a',locale='nl',
            selected_mood='energy',music_backend='spotify_direct',
            allowed_capability_intents=frozenset({'artist_story'}))
        self.catalog,self.fact=source('birth',0)
        await self.manager.async_update_playback_projection(owner_profile_id='profile-a',
            session_id=self.session.session_id,state='playing',media_identity=self.catalog['uri'],
            title=self.catalog['title'],artist=self.catalog['artist'],duration_ms=300000,position_ms=0)
        self.session=await self.manager.async_get_active('profile-a')

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def run_publication(self):
        async def provide():
            return {'_qualified_facts':(self.fact,)}
        return await self.manager.async_process_track_started(owner_profile_id='profile-a',
            session_id=self.session.session_id,media_identity=self.catalog['uri'],insight_provider=provide,
            require_current_playback=True,allow_initial_facts=True)

    async def assert_not_accepted(self):
        count=await self.fixture.service.async_in_transaction(lambda tx:tx.fetchone(
            "SELECT COUNT(*) FROM djconnect_session_acceptances WHERE session_id=? AND kind='dj_moment'",
            (self.session.session_id,))[0])
        self.assertEqual(count,0)
        self.assertEqual(self.session.broadcast.state.dj_moments,())
        self.assertEqual(self.session.moment_engine._expression_forms,())
        self.assertEqual(self.session.presence_ledger.total_published,0)

    async def test_revocation_after_real_sql_stage_rolls_back_acceptance_and_text(self):
        provider=self.fixture.service._provider
        original=provider._async_guarded_transaction
        loop=asyncio.get_running_loop()
        staged=asyncio.Event()
        release=threading.Event()
        authorized=[True]
        def authorize():
            if not authorized[0]:
                raise PermissionError('owner_token_rotated')
        async def model(brief,guard):
            return brief.seed
        self.manager.connect_narration('profile-a',self.session.session_id,model,authorize)

        async def held(operation,finalize_authorize):
            def stage(tx):
                result=operation(tx)
                loop.call_soon_threadsafe(staged.set)
                if not release.wait(3):
                    raise RuntimeError('test_sql_stage_timeout')
                return result
            return await original(stage,finalize_authorize)

        with patch.object(provider,'_async_guarded_transaction',held):
            task=asyncio.create_task(self.run_publication())
            try:
                await asyncio.wait_for(staged.wait(),2)
                authorized[0]=False
            finally:
                release.set()
            self.assertIsNone(await asyncio.wait_for(task,3))
        await self.assert_not_accepted()

    async def test_revocation_while_waiting_for_provider_lock_prevents_sql_acceptance(self):
        provider=self.fixture.service._provider
        entered=asyncio.Event()
        authorized=[True]
        def authorize():
            if not authorized[0]:
                raise PermissionError('owner_unloaded')
        async def model(brief,guard):
            entered.set()
            return brief.seed
        self.manager.connect_narration('profile-a',self.session.session_id,model,authorize)
        async with provider._write_lock:
            task=asyncio.create_task(self.run_publication())
            await asyncio.wait_for(entered.wait(),2)
            await asyncio.sleep(0)
            authorized[0]=False
        self.assertIsNone(await asyncio.wait_for(task,3))
        await self.assert_not_accepted()

    async def test_store_source_a_b_a_and_live_pipeline_change_invalidate_model(self):
        from types import SimpleNamespace
        from custom_components.djconnect import pipeline
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.profile_context import async_resolve_device_bound_request_context
        context=await async_resolve_device_bound_request_context(self.hass,self.runtime,self.identity,
            request_source='narration-race-test')
        entered,release=asyncio.Event(),asyncio.Event()
        calls=[]
        async def process(domain,service,data,**kwargs):
            calls.append(data)
            entered.set()
            await release.wait()
            return {'response':{'speech':{'plain':{'speech':json.dumps({
                'text':'{subject} werd geboren op {date}. Een kleine voetnoot om even bij stil te staan.'})}}}}
        self.hass.services=SimpleNamespace(async_call=process)
        self.runtime.config['assist_pipeline_id']='pipeline-a'
        def selection(hass,conf):
            return {'agent_id':conf.get('assist_pipeline_id'),'language':'nl'}
        with patch.object(pipeline,'_assist_context',side_effect=selection):
            self.handlers._connect_session_narration(self.hass,self.runtime,context,self.session,
                self.identity,self.headers)
            task=asyncio.create_task(self.run_publication())
            await asyncio.wait_for(entered.wait(),2)
            storage=self.handlers.profile_storage(self.hass)
            before=storage.authority_revision
            for value in ('changed-source',''):
                await storage.async_upsert_music_account('source-account','source-spotify',
                    kind=MusicAccountKind.PERSONAL,display_name='Synthetic source account',
                    linked_profile_ids=frozenset({'profile-a'}),provider_account_id=value)
            self.assertGreater(storage.authority_revision,before)
            release.set()
            self.assertIsNone(await task)
        self.assertEqual(len(calls),1)
        await self.assert_not_accepted()

    async def test_config_change_after_first_model_call_prevents_second_call_and_publication(self):
        from types import SimpleNamespace
        from custom_components.djconnect import pipeline
        from custom_components.djconnect.profile_context import async_resolve_device_bound_request_context
        context=await async_resolve_device_bound_request_context(self.hass,self.runtime,self.identity,
            request_source='narration-config-race-test')
        entered,release=asyncio.Event(),asyncio.Event()
        calls=[]
        async def process(domain,service,data,**kwargs):
            calls.append(data)
            entered.set()
            await release.wait()
            return {'response':{'speech':{'plain':{'speech':json.dumps({
                'text':'{subject} werd geboren op {date}. Een kleine voetnoot om even bij stil te staan.'})}}}}
        self.hass.services=SimpleNamespace(async_call=process)
        self.runtime.config['assist_pipeline_id']='pipeline-a'
        def selection(hass,conf):
            return {'agent_id':conf.get('assist_pipeline_id'),'language':'nl'}
        with patch.object(pipeline,'_assist_context',side_effect=selection):
            self.handlers._connect_session_narration(self.hass,self.runtime,context,self.session,
                self.identity,self.headers)
            task=asyncio.create_task(self.run_publication())
            await asyncio.wait_for(entered.wait(),2)
            # Replace the configuration object as DJConnectRuntime.config does.
            self.runtime.config={**self.runtime.config,'assist_pipeline_id':'pipeline-b'}
            release.set()
            self.assertIsNone(await task)
        self.assertEqual(len(calls),1)
        await self.assert_not_accepted()

    async def slow_committed_delivery(self,elapsed,duration):
        provider=self.fixture.service._provider
        original=provider._async_guarded_transaction
        committed,release=asyncio.Event(),asyncio.Event()
        clock=[self.manager._monotonic_source()]
        self.manager._monotonic_source=lambda:clock[0]
        await self.manager.async_update_playback_projection(owner_profile_id='profile-a',
            session_id=self.session.session_id,state='playing',media_identity=self.catalog['uri'],
            title=self.catalog['title'],artist=self.catalog['artist'],duration_ms=duration,position_ms=0)
        async def model(brief,guard):
            return brief.seed
        self.manager.connect_narration('profile-a',self.session.session_id,model,lambda:None)
        async def held(operation,finalize_authorize):
            result=await original(operation,finalize_authorize)
            committed.set()
            await release.wait()
            return result
        with patch.object(provider,'_async_guarded_transaction',held):
            task=asyncio.create_task(self.run_publication())
            try:
                await asyncio.wait_for(committed.wait(),2)
                clock[0]+=elapsed
            finally:
                release.set()
            self.assertIsNone(await asyncio.wait_for(task,3))
        count=await self.fixture.service.async_in_transaction(lambda tx:tx.fetchone(
            "SELECT COUNT(*) FROM djconnect_session_acceptances WHERE session_id=? AND kind='dj_moment'",
            (self.session.session_id,))[0])
        self.assertEqual(count,1)
        self.assertEqual(self.session.presence_ledger.total_published,1)
        self.assertEqual(self.session.broadcast.state.dj_moments,())
        self.assertEqual(self.session.moment_engine._expression_forms,())
        self.assertEqual(self.session.prepared_presentations,{})

    async def test_committed_but_stale_observation_is_not_delivered(self):
        await self.slow_committed_delivery(31,300000)

    async def test_committed_but_insufficient_remaining_read_time_is_not_delivered(self):
        await self.slow_committed_delivery(20,60000)
