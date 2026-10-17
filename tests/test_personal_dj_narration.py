"""Connected publication/race tests; explicit model outputs, no paid quality claim."""
import asyncio
from dataclasses import replace
import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module
from tests.context_variation_fixtures import source


class PersonalDJNarrationTest(unittest.TestCase):
    @staticmethod
    def load_pipeline():
        from tests.test_native_moment_delivery import NativeMomentDeliveryTest
        NativeMomentDeliveryTest.load_owner_handlers()
        name='custom_components.djconnect.const'
        canonical=types.ModuleType(name)
        path=Path(__file__).resolve().parents[1]/'custom_components/djconnect/const.py'
        exec(compile(path.read_bytes(),str(path),'exec'),canonical.__dict__)
        previous=sys.modules.get(name)
        sys.modules[name]=canonical
        try:
            pipeline=importlib.import_module('custom_components.djconnect.pipeline')
            importlib.import_module('custom_components.djconnect.ask_dj')
            importlib.import_module('custom_components.djconnect.ask_dj.dialogue')
            return pipeline
        finally:
            if previous is None:
                sys.modules.pop(name,None)
            else:
                sys.modules[name]=previous

    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()
        cls.briefs = importlib.import_module('custom_components.djconnect.narration_brief')

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if cls.previous_const is not None:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const

    async def setup_runtime(self, *, presence='presenter', family='birth', history=None):
        manager = self.runtime.SessionRuntimeManager(historical_projections=history)
        session = await manager.async_start(owner_profile_id='narration-owner', selected_mood='energy',
            dj_persona=self.runtime.DJPersona.HOME_DJ, locale='nl', music_backend='spotify_direct',
            allowed_capability_intents=frozenset({'artist_story','album_story'}))
        session = await manager.async_update_presence(owner_profile_id=session.owner_profile_id,
            session_id=session.session_id, selected_presence=presence)
        catalog, fact = source(family, 0)
        await manager.async_update_playback_projection(owner_profile_id=session.owner_profile_id,
            session_id=session.session_id, state='playing', media_identity=catalog['uri'],
            title=catalog['title'], artist=catalog['artist'], album=catalog['album_name'],
            duration_ms=300000, position_ms=0)
        session = await manager.async_get_active(session.owner_profile_id)
        async def provide():
            return {'_qualified_facts':(fact,)}
        async def run():
            return await manager.async_process_track_started(owner_profile_id=session.owner_profile_id,
                session_id=session.session_id, media_identity=catalog['uri'], insight_provider=provide,
                require_current_playback=True, allow_initial_facts=True)
        return manager, session, fact, run

    def frame(self, brief):
        return f'{brief.anchors[0]} werd geboren op {brief.anchors[1]}. Zo krijgt de naam even een gezicht; de muziek mag zo weer verder vertellen.'

    def text(self, brief):
        return brief.render(self.frame(brief))

    def test_model_projection_separates_public_cc0_fields_from_catalog_and_private_values(self):
        for family in ('birth','formation','description','edition'):
            with self.subTest(family=family):
                catalog, fact = source(family,0)
                brief = self.briefs.qualify(fact, locale='nl', persona='home_dj',mood='energy',seed=fact.copy_for('nl')[1])
                self.assertIsNotNone(brief)
                prompt = brief.prompt()
                self.assertNotIn(catalog['uri'],prompt)
                if family == 'edition':
                    self.assertNotIn(catalog['artist'],prompt)
                    self.assertNotIn('1960',prompt)
                    self.assertIsNone(brief.public_context())
                else:
                    self.assertEqual(brief.public_context()['basis'],'qualified_public_cc0_fields_v1')
                    self.assertIn(catalog['artist'],prompt)
                self.assertNotIn(catalog['album_name'],prompt)
                self.assertNotIn('source_expires_at',prompt)
                self.assertNotIn('device_id',prompt)
                self.assertNotIn('artwork',prompt)
                self.assertIn('required_placeholders',prompt)
                self.assertIn('Mood shading',prompt)
                denied = self.briefs.qualify(replace(fact, source_expires_at=0),
                    locale='nl',persona='home_dj',mood='energy',seed='Fallback')
                self.assertIsNone(denied)

    def test_candidates_require_exact_anchors_shape_and_no_extra_numbers(self):
        _,fact=source('birth',0)
        brief=self.briefs.qualify(fact,locale='nl',persona='home_dj',mood='energy',seed=fact.copy_for('nl')[1])
        valid=self.frame(brief)
        self.assertEqual(self.briefs.candidate(brief,json.dumps({'text':valid})),valid)
        # Exact public CC0 literals may be normalized to a value-free frame;
        # changed/missing dates and extra claims still fail admission.
        self.assertEqual(self.briefs.candidate(brief,json.dumps({'text':brief.render(valid)})),valid)
        invalid=[json.dumps({'text':valid.replace(brief.anchors[0],'Another person')}),
            json.dumps({'text':valid+' Ook won hij in 1999 een prijs.'}),
            json.dumps({'text':valid,'sources':['invented']}),
            '{"text":"first","text":'+json.dumps(valid)+'}',
            json.dumps({'text':valid+' https://example.com'}),json.dumps({'text':valid*10}),
            json.dumps({'text':True}), 'not json']
        for response in invalid:
            with self.subTest(response=response[:50]):
                self.assertIsNone(self.briefs.candidate(brief,response))
        self.assertTrue(self.briefs.assessed('{"supported":true,"language_ok":true,"style_ok":true}'))
        for response in ('{"supported":1,"language_ok":true,"style_ok":true}',
                '{"supported":false,"language_ok":true,"style_ok":true}',
                '{"supported":true,"language_ok":true}',
                '{"supported":true,"language_ok":true,"style_ok":true,"other":true}'):
            self.assertFalse(self.briefs.assessed(response))

    def test_model_realization_reaches_same_immutable_flow_broadcast_and_budget(self):
        async def scenario():
            manager,session,fact,run=await self.setup_runtime()
            called=[]
            async def provider(brief,guard):
                self.assertFalse(manager._lock.locked())
                guard()
                called.append(brief)
                return self.briefs.NarratedText(self.text(brief),self.frame(brief))
            manager.connect_narration(session.owner_profile_id,session.session_id,provider,lambda:None)
            moment=await run()
            self.assertEqual(len(called),1)
            self.assertEqual(moment.content,self.text(called[0]))
            self.assertEqual(dict(moment.generation_metadata)['realization'],'qualified_ha_narration_v1')
            self.assertEqual(moment.source_fact,fact)
            self.assertEqual(moment.source_attribution,(('provider',fact.provider),('url',fact.source_url),('license',fact.license)))
            current=await manager.async_get_active(session.owner_profile_id)
            self.assertEqual(current.moment_engine.moments[-1],moment)
            self.assertEqual(current.broadcast.state.dj_moments[-1],moment)
            self.assertIn(moment.moment_id,[i.moment_id for i in current.planner.output.session_flow.items])
            self.assertEqual(current.presence_ledger.total_published,1)
            self.assertEqual(len(current.moment_engine._expression_forms),1)
            frames=self.briefs.recent_frames(current.moment_engine._expression_forms)
            self.assertEqual(frames,(self.frame(called[0]),))
            self.assertNotIn(fact.display_core.subject,json.dumps(frames))
            self.assertIsInstance(current.moment_engine.next_expression_form(current.dj_persona,fact.key),int)
            self.assertIsNone(await run())
            self.assertEqual(len(called),1)
        asyncio.run(scenario())

    def test_inflight_settings_track_end_and_owner_changes_cannot_publish(self):
        for change in ('presence','mood','persona','track','end','owner'):
            async def scenario():
                manager,session,_,run=await self.setup_runtime()
                entered,release=asyncio.Event(),asyncio.Event()
                authorized=[True]
                def authorize():
                    if not authorized[0]:
                        raise PermissionError('revoked')
                async def provider(brief,guard):
                    self.assertFalse(manager._lock.locked())
                    entered.set()
                    await release.wait()
                    return self.text(brief)
                manager.connect_narration(session.owner_profile_id,session.session_id,provider,authorize)
                task=asyncio.create_task(run())
                await asyncio.wait_for(entered.wait(),1)
                args={'owner_profile_id':session.owner_profile_id,'session_id':session.session_id}
                if change=='presence':
                    await asyncio.wait_for(manager.async_update_presence(**args,selected_presence='music_only'),1)
                    await manager.async_update_presence(**args,selected_presence='presenter')
                elif change=='mood':
                    await manager.async_update_mood(**args,selected_mood='chill')
                elif change=='persona':
                    await manager.async_update_persona(**args,dj_persona=self.runtime.DJPersona.CLUB_DJ)
                elif change=='track':
                    await manager.async_update_playback_projection(**args,state='playing',media_identity='spotify:track:'+('9'*22),
                        title='Other track',artist='Other artist',duration_ms=300000,position_ms=0)
                elif change=='end':
                    await manager.async_end(**args)
                else:
                    authorized[0]=False
                release.set()
                self.assertIsNone(await task)
                self.assertEqual(session.presence_ledger.total_published,0)
                self.assertEqual(session.broadcast.state.dj_moments,())
                self.assertEqual(session.moment_engine._expression_forms,())
            with self.subTest(change=change):
                asyncio.run(scenario())

    def test_cancelled_generation_releases_pending_without_consuming_opportunity(self):
        async def scenario():
            manager,session,_,run=await self.setup_runtime()
            entered=asyncio.Event()
            async def provider(brief,guard):
                entered.set()
                await asyncio.Event().wait()
            manager.connect_narration(session.owner_profile_id,session.session_id,provider,lambda:None)
            task=asyncio.create_task(run())
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            opportunity=manager._intra_track_opportunities[session.owner_profile_id]
            self.assertFalse(opportunity.pending)
            self.assertEqual(opportunity.used_fact_keys,set())
            self.assertEqual(session.presence_ledger.total_published,0)
            async def recovered(brief,guard):
                return self.text(brief)
            manager.connect_narration(session.owner_profile_id,session.session_id,recovered,lambda:None)
            result=await manager.async_maybe_publish_intra_track_moment(owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,media_identity=opportunity.media_identity)
            self.assertIsNotNone(result)
            self.assertEqual(session.presence_ledger.total_published,1)
        asyncio.run(scenario())

    def test_no_model_for_music_only(self):
        for presence,family in (('music_only','birth'),('music_only','edition')):
            async def scenario():
                manager,session,_,run=await self.setup_runtime(presence=presence,family=family)
                async def forbidden(*args):
                    self.fail('Unqualified model call')
                manager.connect_narration(session.owner_profile_id,session.session_id,forbidden,lambda:None)
                result=await run()
                if presence=='music_only':
                    self.assertIsNone(result)
                    self.assertEqual(session.presence_ledger.total_published,0)
                else:
                    self.assertIsNotNone(result)
                    self.assertNotIn('realization',dict(result.generation_metadata))
            with self.subTest(presence=presence,family=family):
                asyncio.run(scenario())

    def test_provider_failure_keeps_approved_local_fallback(self):
        async def scenario():
            manager,session,_,run=await self.setup_runtime()
            async def unavailable(*args):
                raise RuntimeError('provider failure')
            manager.connect_narration(session.owner_profile_id,session.session_id,unavailable,lambda:None)
            result=await run()
            self.assertIsNotNone(result)
            self.assertNotIn('realization',dict(result.generation_metadata))
            self.assertNotIn('provider failure',result.content)
            self.assertEqual(session.presence_ledger.total_published,1)
        asyncio.run(scenario())

    def test_noop_mood_preserves_inflight_publication_and_duplicate_observation_does_not_join(self):
        async def scenario():
            manager,session,_,run=await self.setup_runtime()
            entered,release=asyncio.Event(),asyncio.Event()
            calls=[]
            async def provider(brief,guard):
                calls.append(brief)
                entered.set()
                await release.wait()
                return self.text(brief)
            manager.connect_narration(session.owner_profile_id,session.session_id,provider,lambda:None)
            task=asyncio.create_task(run())
            await entered.wait()
            current=await manager.async_get_active(session.owner_profile_id)
            self.assertIs(current,await manager.async_update_mood(owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,selected_mood='energy'))
            self.assertIsNone(await run())
            opportunity=manager._intra_track_opportunities[session.owner_profile_id]
            self.assertIsNone(await manager.async_maybe_publish_intra_track_moment(owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,media_identity=opportunity.media_identity))
            release.set()
            self.assertIsNotNone(await task)
            self.assertEqual(len(calls),1)
            self.assertEqual(session.presence_ledger.total_published,1)
        asyncio.run(scenario())

    def test_shared_style_matrix_has_independent_persona_and_mood_instructions(self):
        from custom_components.djconnect.narration_style import instructions, PERSONAS, MOODS
        rows=[]
        for persona in PERSONAS:
            for mood in MOODS:
                for locale in ('en','nl','de','fr','es'):
                    prompt=instructions(persona=persona,mood=mood,locale=locale)
                    self.assertIn(PERSONAS[persona],prompt)
                    self.assertIn(MOODS[mood],prompt)
                    self.assertIn('Never invent biography',prompt)
                    rows.append(prompt)
        self.assertEqual(len(rows),80)
        self.assertEqual(len(set(rows)),80)
        # This asserts instruction plumbing, not generated prose quality.

    def test_existing_ha_transport_runs_realization_and_assessment_without_raw_debug(self):
        pipeline=self.load_pipeline()
        _,fact=source('birth',0)
        brief=self.briefs.qualify(fact,locale='nl',persona='home_dj',mood='energy',seed=fact.copy_for('nl')[1])
        frame=self.frame(brief)
        text=self.text(brief)
        calls=[]
        class Services:
            async def async_call(self,domain,service,data,**kwargs):
                calls.append((domain,service,data,kwargs))
                reply=json.dumps({'text':frame}) if len(calls)==1 else '{"supported":true,"language_ok":true,"style_ok":true}'
                return {'response':{'speech':{'plain':{'speech':reply}}}}
        hass=types.SimpleNamespace(services=Services())
        debug={}
        with patch.object(pipeline,'_assist_context',return_value={'agent_id':'scoped-agent','language':'nl'}):
            result=asyncio.run(pipeline.generate_dj_response_with_assist(hass,media={},
                fallback_text=brief.seed,conf={},narration=brief,admission=lambda:None,debug=debug))
        self.assertEqual(result,text,(debug,len(calls)))
        self.assertEqual(len(calls),2)
        self.assertTrue(all(c[0:2]==('conversation','process') for c in calls))
        self.assertTrue(all(c[2]['agent_id']=='scoped-agent' for c in calls))
        self.assertEqual(debug,{'fallback_used':False,'block_reason':None,'model_attempts':2})
        self.assertNotIn('prompt',debug)
        self.assertNotIn('generated_text',debug)
        self.assertNotIn(fact.media_identity,json.dumps(calls))

    def test_existing_ha_transport_rejects_bad_candidate_or_assessment(self):
        pipeline=self.load_pipeline()
        _,fact=source('birth',0)
        brief=self.briefs.qualify(fact,locale='nl',persona='home_dj',mood='energy',seed=fact.copy_for('nl')[1])
        for failure in ('wrong_anchor','unsupported','wrong_language','too_flat','provider_failure','pipeline_changed'):
            calls=[]
            selected=[{'agent_id':'scoped-agent','language':'nl'}]
            class Services:
                async def async_call(self,domain,service,data,**kwargs):
                    calls.append(data)
                    if failure=='provider_failure':
                        raise RuntimeError('secret-looking provider detail must not reach debug')
                    if failure=='pipeline_changed':
                        selected[0]={'agent_id':'changed-agent','language':'nl'}
                    if len(calls)==1:
                        reply=json.dumps({'text':self_test.frame(brief).replace(brief.anchors[0],'Wrong subject')
                                          if failure=='wrong_anchor' else self_test.frame(brief)})
                    else:
                        reply=json.dumps({'supported':failure!='unsupported',
                            'language_ok':failure!='wrong_language','style_ok':failure!='too_flat'})
                    return {'response':{'speech':{'plain':{'speech':reply}}}}
            self_test=self
            debug={}
            with self.subTest(failure=failure),patch.object(pipeline,'_assist_context',side_effect=lambda *args:selected[0]):
                result=asyncio.run(pipeline.generate_dj_response_with_assist(types.SimpleNamespace(services=Services()),
                    media={},fallback_text=brief.seed,conf={},narration=brief,admission=lambda:None,debug=debug))
                self.assertEqual(result,brief.seed)
                self.assertTrue(debug['fallback_used'])
                self.assertLessEqual(len(calls),2)
                self.assertNotIn('secret-looking',json.dumps(debug))

    def test_source_expiry_during_generation_discards_without_style_or_budget_write(self):
        async def scenario():
            manager,session,_,run=await self.setup_runtime()
            entered,release=asyncio.Event(),asyncio.Event()
            async def provider(brief,guard):
                entered.set()
                await release.wait()
                return self.text(brief)
            manager.connect_narration(session.owner_profile_id,session.session_id,provider,lambda:None)
            task=asyncio.create_task(run())
            await entered.wait()
            opportunity=manager._intra_track_opportunities[session.owner_profile_id]
            # Advancing the source clock is a provider-validity boundary, not a new observation.
            with patch('time.monotonic',return_value=opportunity.qualified_facts[0].observed_at+1801):
                release.set()
                self.assertIsNone(await task)
            self.assertEqual(session.presence_ledger.total_published,0)
            self.assertEqual(session.moment_engine._expression_forms,())
            self.assertFalse(opportunity.pending)
        asyncio.run(scenario())
