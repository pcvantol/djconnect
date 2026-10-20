"""Actual Runtime/SQLite/native/speech chain; external sources/model are fixtures.

No real-LLM writing-quality or installed-device PASS is implied by these tests.
"""
from dataclasses import replace
import asyncio
import json
import threading
import secrets
import time
import sys
import types
import unittest
from unittest.mock import patch

from tests import test_session_conversation_history as fixtures
from tests.context_variation_fixtures import source
from scripts.verification.source_fixture_urls import (
    fixture_host, fixture_location, wikipedia_api_fixture, WIKIPEDIA_HOSTS,
)


class PublicArtistNarrationTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = fixtures.SessionConversationHistoryTest()
        await self.fixture.asyncSetUp()
        self.hass, self.runtime, self.history, self.identity, self.headers = await self.fixture.transport_fixture()
        self.manager = self.fixture.manager
        self.r = self.fixture.runtime
        self.session = await self.manager.async_start(owner_profile_id='profile-a', locale='nl',
            selected_mood='energy', music_backend='spotify_direct',
            allowed_capability_intents=frozenset({'artist_story'}))
        self.catalog, fact = source('formation', 0)
        self.fact = replace(fact, public_artist_qid='Q1')
        await self.manager.async_update_playback_projection(owner_profile_id='profile-a',
            session_id=self.session.session_id, state='playing', media_identity=self.catalog['uri'],
            title=self.catalog['title'], artist=self.catalog['artist'], duration_ms=300000, position_ms=0)
        self.session = await self.manager.async_get_active('profile-a')
        from tests.test_personal_dj_narration import PersonalDJNarrationTest
        self.pipeline = PersonalDJNarrationTest.load_pipeline()
        from custom_components.djconnect.ask_dj import public_research
        self.research = public_research
        self.calls, self.urls = [], []
        self.answer = 'Bij Paper Lanterns werkte Nora Vale 1 samen met Ada Reed. Zo kijk ik graag even mee achter een naam.'
        self.fetch_qid = 'Q1'
        self.bad_review = False
        self.after_fetch = None
        self.debug = {}
        self.authorized = True
        self.source_index = 0
        self.second_only = False
        self.producer_mode = False
        self.composer_mode = False
        self.fetch_owners = []
        self.actor_name_override = None
        self.reciprocal_id_override = None
        self.producer_unsupported = False
        self.after_draft = None
        self.recording_focus_preserved = True
        self.article_fixture = None

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def fetch(self, fetch, url, **kwargs):
        await fetch.guard()
        if fetch.requests >= self.research.MAX_REQUESTS:
            raise self.research.ResearchUnavailable('public_research_budget')
        fetch.requests += 1
        self.fetch_owners.append(fetch)
        self.urls.append(url)
        host = fixture_host(url)
        if self.producer_mode or self.composer_mode:
            if host == 'musicbrainz.org' and fixture_location(url).path.startswith('/ws/2/'):
                return 200,json.dumps({'id':self.selected_credit.contributor_id,
                    'name':self.actor_name_override or self.selected_credit.name,'type':self.actor_type,
                    'relations':[{'type':'wikidata','url':{'resource':'https://www.wikidata.org/wiki/Q1'}}]}),url
            if host == 'www.wikidata.org':
                return 200,json.dumps({'entities':{'Q1':{'id':'Q1','claims':{'P434':[{
                    'mainsnak':{'datavalue':{'value':self.reciprocal_id_override or self.selected_credit.contributor_id}}}]}}}}),url
            if not wikipedia_api_fixture(url):
                return 404, '', url
            page = {'title':self.selected_credit.name,'pageprops':{'wikibase_item':self.fetch_qid,
                'wikibase-shortdesc':'music group' if self.actor_type=='Group' else 'musician'},
                'revisions':[{'revid':1234}], 'extract':f'<p>{self.selected_credit.name} is a '
                    +('music group' if self.actor_type=='Group' else 'musician')+'</p>'
                    +f'<p>{self.selected_credit.name} recorded <i>Paper Lanterns</i> with Nora Vale 1.</p>'}
            if self.article_fixture:
                page['extract'] = self.article_fixture
            if self.after_fetch:
                await self.after_fetch()
            return 200,json.dumps({'query':{'pages':[page]}}),url
        if not wikipedia_api_fixture(url):
            return 404, '', url
        page = {'title':'Nora Vale 1', 'pageprops':{'wikibase_item':self.fetch_qid,
            'wikibase-shortdesc':'music group'}, 'revisions':[{'revid':1234}],
            'extract':'<p>Nora Vale 1 is a music group.</p><p>The group recorded <i>Paper Lanterns</i> with Ada Reed.</p>'}
        if self.second_only and host == 'nl.wikipedia.org':
            page['extract'] = '<p>Nora Vale 1 is a music group.</p>'
        if self.after_fetch:
            await self.after_fetch()
        return 200, json.dumps({'query':{'pages':[page]}}), url

    async def model(self, hass, data, **kwargs):
        self.calls.append(data['text'])
        if len(self.calls) % 2:
            output = self.answer
            if self.after_draft:
                await self.after_draft()
        else:
            assessment = json.loads(data['text'].split('\nData:\n')[1])
            evidence = assessment['evidence']['public_music_research']
            wiki = evidence['sources'][self.source_index]
            span = next(s for s in wiki['evidence_spans'] if 'Paper Lanterns' in s['text'])
            first, second = assessment['answer'].split('. ', 1)
            if self.producer_mode or self.composer_mode:
                credit = evidence['sources'][-1]
                first_span = credit['evidence_spans'][0]
                checks = [
                    {'text':first+'.','kind':'relationship','evidence_ids':[first_span['id']],'quote':first_span['text']},
                    {'text':second,'kind':'relationship','evidence_ids':[span['id']],'quote':span['text']}]
            else:
                checks = [
                    {'text':first+'.','kind':'relationship','evidence_ids':[span['id']],'quote':span['text']},
                    {'text':second,'kind':'dj_appreciation','evidence_ids':[],'quote':''}]
            output = {'supported':not self.producer_unsupported,
                'unsupported_claims':['invented production influence'] if self.producer_unsupported else [], 'language_ok':True,
                **({'recording_focus_preserved':self.recording_focus_preserved,
                    'producer_episode_preserved':True} if self.producer_mode else {}),
                **({'work_focus_preserved':True,'composer_episode_preserved':True} if self.composer_mode else {}),
                **({'topic_preserved':True,'novel_episode':True} if 'published_artist_stories' in evidence else {}),
                'style_ok':not self.bad_review, 'temporal_claims':[], 'claim_checks':[
                    *checks]}
            if evidence['schema_version']==3:
                output['review_schema']='source_id_review_v1'
                output['claim_checks']=[{k:v for k,v in c.items() if k!='quote'} for c in checks]
            output=json.dumps(output)
        return {'response':{'speech':{'plain':{'speech':output}}}}

    async def publish(self):
        def authorize():
            if not self.authorized:
                raise PermissionError('fixture_source_owner_revoked')
        async def provider(brief, guard):
            return await self.pipeline.realize_session_narration(self.hass, narration=brief,
                admission=guard, fallback_text=brief.seed, conf=self.runtime.config, debug=self.debug)
        self.manager.connect_narration('profile-a', self.session.session_id, provider, authorize)
        async def insight():
            return {'_qualified_facts':(self.fact,)}
        async def network(fetch, url, **kwargs):
            return await self.fetch(fetch, url, **kwargs)
        with patch.object(self.research.PublicFetch, 'request', network), \
                patch.object(self.pipeline, '_assist_context', return_value={'agent_id':'fixture-agent'}), \
                patch.object(self.pipeline, 'call_conversation_process_with_agent_retry', self.model):
            return await self.manager.async_process_track_started(owner_profile_id='profile-a',
                session_id=self.session.session_id, media_identity=self.catalog['uri'],
                insight_provider=insight, require_current_playback=True, allow_initial_facts=True)

    async def test_complete_publication_reopen_sources_speech_and_selected_subject(self):
        from custom_components.djconnect import public_artist_narration as narration
        from custom_components.djconnect.session_conversation import query_service
        from custom_components.djconnect.session_speech import moment_projection, resolve_moment, resolve_retained
        from custom_components.djconnect.ask_dj.service import _live_reference
        from custom_components.djconnect.ask_dj.dialogue import model_source
        self.second_only, self.source_index = True, 1
        moment = await self.publish()
        self.assertIsNotNone(moment)
        self.assertEqual(moment.content, self.answer, self.debug)
        self.assertTrue(narration.admitted(moment))
        self.assertEqual(len(self.calls), 2)
        self.assertFalse(any(fixture_host(u) in {'duckduckgo.com', 'html.duckduckgo.com'} for u in self.urls))
        for prompt in self.calls:
            self.assertNotIn(self.catalog['uri'], prompt)
            self.assertNotIn(self.catalog['album_name'], prompt)
        self.assertEqual(dict(moment.source_attribution)['license'], 'CC-BY-SA-4.0')
        self.assertEqual({s['provider'] for s in moment.as_dict()['sources']}, {'Wikipedia','MusicBrainz'})
        self.assertNotIn('untrusted_excerpt', json.dumps(moment.as_dict()))
        self.assertIn(moment.moment_id, {m.moment_id for m in self.session.broadcast.state.dj_moments})
        self.assertEqual(self.session.presence_ledger.total_published, 1)
        self.assertNotIn('Ada Reed', repr(self.session.moment_engine._expression_forms))
        descriptor = moment_projection(self.session.broadcast, moment)
        self.assertTrue(descriptor['manual_allowed'])
        self.assertEqual({s['provider'] for s in descriptor['attribution']}, {'Wikipedia','MusicBrainz'})
        reference = {'session_id':self.session.session_id,'moment_id':moment.moment_id}
        _, guard = await resolve_moment(self.hass, 'profile-a', reference)
        self.assertEqual(guard.processor_basis, 'qualified_dialogue_v1')
        selected = await _live_reference(self.manager, 'profile-a', reference)
        context = model_source(selected)
        self.assertEqual(context['basis'], 'cc0_normalized_fields_v1')
        self.assertNotIn('Ada Reed', json.dumps(context))
        self.assertIn(self.fact.copy_for('nl')[1], context['qualified_excerpt'])
        from custom_components.djconnect.display_admission import DisplayAdmissionState, DisplayOwnerBinding
        from custom_components.djconnect.display_projection import shared_snapshot
        display_state = DisplayAdmissionState(time.monotonic)
        owner = DisplayOwnerBinding('profile-a',self.session.session_id,'entry','stamp',lambda:True)
        nonce = secrets.token_urlsafe(32)
        claim = display_state.create_claim(source='unit',browser_nonce=nonce)
        display_state.approve(owner=owner,**{k:claim[k] for k in (
            'issuer_epoch','claim_id','browser_generation','code')},share={'mode':'create','consent':True})
        collected = display_state.collect(**{k:claim[k] for k in (
            'issuer_epoch','claim_id','browser_generation','claim_secret')},browser_nonce=nonce)
        display = display_state._displays[collected['display_id']]
        snapshot = shared_snapshot(self.session,display,display_state)
        card = next(m for m in snapshot['dj_moments'] if m['moment_id'] == moment.moment_id)
        self.assertEqual(card['content'],self.answer)
        self.assertEqual(len(card['sources']),3)
        self.assertEqual({s['language'] for s in card['sources'] if s['provider']=='Wikipedia'},{'nl','en'})
        self.assertTrue(all(s['revision_url'] for s in card['sources'] if s['provider']=='Wikipedia'))
        for field in ('untrusted_excerpt','content_hash','wikidata_id','fetched_at','claim_checks','sources_json'):
            self.assertNotIn(field,json.dumps(snapshot))
        calls_before = (len(self.calls), len(self.urls))
        await self.manager.async_end(owner_profile_id='profile-a', session_id=self.session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        query = query_service(self.hass, self.history)
        page = await query.async_timeline_page('profile-a', self.session.session_id)
        entry = next(e for e in page['entries'] if e.get('moment_id') == moment.moment_id)
        self.assertEqual(entry['text'], self.answer)
        self.assertEqual(entry['archive_basis'], narration.BASIS)
        self.assertEqual(entry['sources'], moment.as_dict()['sources'])
        self.assertTrue(entry['session_speech']['manual_allowed'])
        descriptor, guard = await resolve_retained(self.hass, self.history, 'profile-a',
            {'session_id':self.session.session_id,'entry_id':entry['entry_id']})
        self.assertEqual(guard.processor_basis, 'qualified_dialogue_v1')
        self.assertTrue(descriptor['manual_allowed'])
        self.assertEqual(calls_before, (len(self.calls), len(self.urls)))

    def description(self):
        from custom_components.djconnect.session_facts import description_fact
        identity='00000000-0000-0000-0000-000000000042'
        catalog={**self.catalog,'artist_ids':['Z'*22]}
        person={'id':identity,'name':catalog['artist'],'type':'Group','relations':[
            {'type':'free streaming','url':{'resource':'https://open.spotify.com/artist/'+'Z'*22}},
            {'type':'wikidata','url':{'resource':'https://www.wikidata.org/wiki/Q1'}}]}
        entity={'id':'Q1','descriptions':{'nl':{'value':'Amerikaanse band'}},'claims':{
            'P434':[{'mainsnak':{'datavalue':{'value':identity}}}]}}
        return replace(description_fact(catalog,entity,'Q1',person=person),public_artist_qid='Q1')

    async def test_artist_description_keeps_spotlight_subject_in_published_and_reopened_flow(self):
        from types import SimpleNamespace
        from custom_components.djconnect import session_artwork as art
        from custom_components.djconnect.session_conversation import query_service
        self.fact=self.description()
        captured=dict.fromkeys(('backend_id','music_account_id','provider_entry_id','provider_account_id'),'fixture')
        self.manager._history_source_contexts[self.session.session_id]=captured
        moment=await self.publish()
        self.assertIsNotNone(moment,self.debug)
        self.assertEqual(moment.content,self.answer)
        self.assertNotIn('Amerikaanse band',moment.content)
        context=SimpleNamespace(profile_id='profile-a')
        from custom_components.djconnect.image_proxy import ManagedSessionImages
        self.hass.async_create_task=asyncio.create_task
        registry=ManagedSessionImages()
        self.hass.data['djconnect']['session_images']=registry
        self.addCleanup(registry.close)
        pixels=(__import__('pathlib').Path(__file__).resolve().parents[1]/
                'examples/client_contracts/session_artwork_v1/assets/cover.png').read_bytes()
        fetched=[]
        async def external_image(hass,backend,uri,*,guard,expected_album_uri):
            await guard()
            fetched.append(uri)
            self.assertEqual(expected_album_uri,'')
            return pixels,'image/png','https://open.spotify.com/artist/'+'Z'*22,'',64,64,self.catalog['artist']
        async def prepare_image(reference):
            with patch.object(art,'artist_authority',return_value=lambda:True), \
                    patch.object(art,'_fetch',external_image), \
                    patch('custom_components.djconnect.spotify_backend.SpotifyBackend',return_value=object()):
                prepared=await art.prepare(self.hass,self.runtime,context,
                    session_id=self.session.session_id,target=reference)
                image=prepared['artwork']
                self.assertEqual(image['state'],'ready',prepared)
                self.assertEqual(image['subject']['uri'],'spotify:artist:'+'Z'*22)
                self.assertEqual(image['role'],'contextual_artist')
                self.assertEqual(image['edition_basis'],'not_applicable')
                self.assertTrue(image['requires_device_auth'])
                body=await art.image(self.hass,context,self.session.session_id,
                    image['url'].rsplit('/',1)[-1],runtime=self.runtime)
                self.assertEqual(body,(pixels,'image/png'))
                return image
        live_image=await prepare_image({'moment_id':moment.moment_id})
        self.assertTrue(live_image['active_flow_display_allowed'])
        self.assertFalse(live_image['historical_display_allowed'])
        target=await art.resolve_target(self.hass,self.runtime,context,self.session.session_id,
            {'moment_id':moment.moment_id})
        self.assertEqual(target[0],'spotify:artist:'+'Z'*22)
        self.assertEqual(target[6],'contextual_artist')
        self.assertNotIn(self.catalog['uri'],self.calls[0])
        self.assertNotIn('spotify:artist:',self.calls[0])
        await self.manager.async_end(owner_profile_id='profile-a',session_id=self.session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        query=query_service(self.hass,self.history)
        page=await query.async_timeline_page('profile-a',self.session.session_id)
        entry=next(e for e in page['entries'] if e.get('moment_id')==moment.moment_id)
        self.assertEqual(entry['text'],self.answer)
        self.assertTrue(entry['session_speech']['manual_allowed'])
        target=await art.resolve_target(self.hass,self.runtime,context,self.session.session_id,
            {'entry_id':entry['entry_id']})
        self.assertEqual(target[0],'spotify:artist:'+'Z'*22)
        self.assertEqual(target[1],captured)
        self.assertTrue(target[4])
        self.assertEqual(target[6],'contextual_artist')
        old_image=await prepare_image({'entry_id':entry['entry_id']})
        self.assertTrue(old_image['historical_display_allowed'])
        self.assertFalse(old_image['current_display_allowed'])
        self.assertFalse(old_image['active_flow_display_allowed'])
        self.assertNotEqual(old_image['url'],live_image['url'])
        self.assertEqual(fetched,['spotify:artist:'+'Z'*22]*2)
        self.assertEqual(len(self.calls),2)

    async def test_unbound_artist_descriptor_declines_once_without_raw_card_or_symbolic_model_calls(self):
        self.fact=replace(self.description(),public_artist_qid='')
        self.assertIsNone(await self.publish())
        self.assertEqual(self.calls,[])
        self.assertEqual(self.urls,[])
        self.assertEqual(self.session.presence_ledger.total_published,0)
        self.assertIn('artist_description',self.manager._intra_track_opportunities['profile-a'].used_fact_keys)
        self.assertIsNone(await self.publish())
        self.assertEqual(self.calls,[])

    async def test_wrong_entity_no_entity_and_rejected_style_never_admit_rich_prose(self):
        self.fetch_qid = 'Q999'
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.calls, [])

    async def test_rejected_style_declines_original_once_without_extra_model_attempt(self):
        self.bad_review = True
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.session.presence_ledger.total_published, 0)

    async def test_absent_reciprocal_identity_does_not_fetch_or_admit_research(self):
        self.fact = replace(self.fact, public_artist_qid='')
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.urls, [])
        self.assertEqual(self.session.presence_ledger.total_published, 0)

    async def test_rejected_producer_story_never_publishes_raw_repeated_role_list_or_retries(self):
        await self.prepare_producer()
        from custom_components.djconnect.session_facts import recording_facts
        evidence=self.fact.recording_evidence
        performers=('Ellis Hart','Jules West','Rowan Vale')
        self.fact=recording_facts(self.catalog,{'id':evidence.recording_id,'title':self.catalog['title'],
            'artist-credit':[{'artist':{'name':self.catalog['artist']}}],
            'relations':[
                *[{'type':role,'target-type':'artist','artist':{
                    'id':f'00000000-0000-0000-0000-{80+i:012d}','name':name}}
                    for role in ('instrument','vocal') for i,name in enumerate(performers)],
                *[{'type':'producer','target-type':'artist','artist':{'id':p.contributor_id,'name':p.name}}
                    for p in evidence.producers]]})[0]
        self.bad_review=True
        self.assertIsNone(await self.publish())
        self.assertEqual(self.session.broadcast.state.dj_moments,())
        self.assertEqual(self.session.presence_ledger.total_published,0)
        self.assertEqual(len(self.calls),2)
        self.assertIsNone(await self.publish())
        self.assertEqual(len(self.calls),2)
        opportunity=self.manager._intra_track_opportunities['profile-a']
        self.assertIn('recording_credits',opportunity.used_fact_keys)
        self.assertFalse(opportunity.pending)
        from custom_components.djconnect.session_conversation import query_service
        page=await query_service(self.hass,self.history).async_timeline_page('profile-a',self.session.session_id)
        self.assertFalse(any(e.get('kind')=='dj_moment' for e in page['entries']))

    async def test_researched_story_has_bounded_time_for_sources_and_two_calls_with_live_guards(self):
        from custom_components.djconnect.public_artist_narration import PUBLIC_STORY_NARRATION_SECONDS
        seconds=[]
        original_timeout=asyncio.timeout
        def timeout(value):
            seconds.append(value)
            return original_timeout(value)
        with patch.object(asyncio,'timeout',timeout):
            moment=await self.publish()
        self.assertIsNotNone(moment)
        self.assertIn(PUBLIC_STORY_NARRATION_SECONDS,seconds)
        self.assertEqual(PUBLIC_STORY_NARRATION_SECONDS,40)
        self.assertEqual(len(self.calls),2)
        self.assertTrue(moment.narration_acceptance.accepted.valid(time.monotonic()))

    async def test_settings_change_during_fetch_rejects_original_and_researched_candidate(self):
        async def change():
            await self.manager.async_update_mood(owner_profile_id='profile-a',
                session_id=self.session.session_id, selected_mood='party')
        self.after_fetch = change
        self.assertIsNone(await self.publish())
        self.assertEqual(self.session.broadcast.state.dj_moments, ())
        self.assertEqual(self.session.presence_ledger.total_published, 0)

    async def test_cancellation_during_fetch_has_no_commit_or_extra_attempt(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def hold():
            entered.set()
            await release.wait()
        self.after_fetch = hold
        task = asyncio.create_task(self.publish())
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.calls, [])
        self.assertEqual(self.session.broadcast.state.dj_moments, ())
        self.assertEqual(self.session.presence_ledger.total_published, 0)

    async def test_owner_revocation_after_real_sql_stage_rolls_back_researched_text(self):
        provider = self.fixture.service._provider
        original = provider._async_guarded_transaction
        loop = asyncio.get_running_loop()
        staged, release = asyncio.Event(), threading.Event()
        async def held(operation, finalize_authorize):
            def stage(tx):
                result = operation(tx)
                loop.call_soon_threadsafe(staged.set)
                if not release.wait(3):
                    raise RuntimeError('fixture_stage_timeout')
                return result
            return await original(stage, finalize_authorize)
        with patch.object(provider, '_async_guarded_transaction', held):
            task = asyncio.create_task(self.publish())
            try:
                await asyncio.wait_for(staged.wait(), 1)
                self.authorized = False
            finally:
                release.set()
            self.assertIsNone(await asyncio.wait_for(task, 3))
        count = await self.fixture.service.async_in_transaction(lambda tx:tx.fetchone(
            "SELECT COUNT(*) FROM djconnect_session_acceptances WHERE session_id=? AND kind='dj_moment'",
            (self.session.session_id,))[0])
        self.assertEqual(count, 0)
        self.assertEqual(self.session.broadcast.state.dj_moments, ())
        self.assertEqual(self.session.presence_ledger.total_published, 0)

    async def test_long_complete_story_is_omitted_on_passive_surface_not_truncated(self):
        from custom_components.djconnect.passive_session import _text
        # Deliberately long boundary fixture, not a writing-quality exemplar.
        self.answer = self.answer.split('. ',1)[0]+'. Zo kijk ik graag '+('heel rustig, '*44)+'nog even mee.'
        moment = await self.publish()
        self.assertEqual(moment.content, self.answer, self.debug)
        self.assertGreater(len(moment.content), 640)
        self.assertIsNone(_text(self.session.broadcast, time.monotonic()))

    async def test_track_change_during_fetch_cannot_publish_or_consume_opportunity(self):
        async def change():
            await self.manager.async_update_playback_projection(owner_profile_id='profile-a',
                session_id=self.session.session_id,state='playing',media_identity='spotify:track:'+'Z'*22,
                title='Other recording',artist='Other artist',duration_ms=300000,position_ms=0)
        self.after_fetch = change
        self.assertIsNone(await self.publish())
        self.assertEqual(self.calls, [])
        self.assertEqual(self.session.broadcast.state.dj_moments, ())
        self.assertEqual(self.session.presence_ledger.total_published, 0)

    async def test_forged_changed_text_sources_style_identity_and_expiry_fail_native(self):
        from custom_components.djconnect import public_artist_narration as narration
        from custom_components.djconnect.native_moment_delivery import admission
        moment = await self.publish()
        self.assertTrue(narration.admitted(moment))
        altered = [replace(moment,content=moment.content+' Invented.'),
            replace(moment,source_attribution=(('provider','MusicBrainz'),)),
            replace(moment,source_fact=replace(self.fact,public_artist_qid='Q2')),
            replace(moment,moment_id='forged'),
            replace(moment,presentation_intent=replace(moment.presentation_intent,source_session_mood='party')),
            replace(moment,narration_acceptance=replace(moment.narration_acceptance,
                accepted=replace(moment.narration_acceptance.accepted,sources_json='[]')))]
        boundary = self.session.broadcast._moment_delivery_boundaries[moment.moment_id]
        for changed in altered:
            self.assertFalse(narration.admitted(changed))
            result = admission(changed,boundary,session_id=moment.session_id,active=True,
                flow_ids={changed.moment_id},playback_item_id=boundary.playback_item_id,
                playing=True,now=time.monotonic())
            self.assertNotEqual(result['qualification'], 'qualified')
        self.assertFalse(narration.admitted(moment, moment.narration_acceptance.accepted.expires_at))

    async def test_source_metadata_expiry_and_no_raw_research_in_accepted_receipt(self):
        moment = await self.publish()
        accepted = moment.narration_acceptance.accepted
        self.assertLessEqual(accepted.expires_at, self.fact.observed_at+1800)
        self.assertNotIn('The group recorded', repr(accepted))
        self.assertNotIn('claim_checks', repr(accepted))
        self.assertNotIn('untrusted_excerpt', repr(accepted))

    async def test_public_fetch_wrong_same_name_qid_is_not_replaced_by_web(self):
        async def guard():
            pass
        async def network(fetch,url,**kwargs):
            return await self.fetch(fetch,url,**kwargs)
        with patch.object(self.research.PublicFetch,'request',network):
            sources, _ = await self.research.research('Nora Vale 1','Introduce this music group','nl',guard,
                qualified_music=True,expected_entity_id='Q999',allow_web=False)
        self.assertEqual(sources, [])
        self.assertTrue(self.urls)
        self.assertTrue(all(fixture_host(u) in {*WIKIPEDIA_HOSTS,'www.wikidata.org'} for u in self.urls))
        self.assertTrue(any(fixture_host(u)=='www.wikidata.org' and 'props=sitelinks' in u for u in self.urls))

    async def test_source_fixture_rejects_hostnames_hidden_in_paths_queries_or_userinfo(self):
        async def guard():
            pass
        for url in ('https://unrelated.invalid/https://nl.wikipedia.org/w/api.php',
                    'https://unrelated.invalid/?source=https://www.wikidata.org/wiki/Q1',
                    'https://nl.wikipedia.org@unrelated.invalid/w/api.php',
                    'https://nl.wikipedia.org.unrelated.invalid/w/api.php',
                    'http://nl.wikipedia.org/w/api.php',
                    'https://nl.wikipedia.org:444/w/api.php'):
            with self.subTest(url=url):
                boundary = types.SimpleNamespace(guard=guard, requests=0)
                status, body, _ = await self.fetch(boundary, url)
                self.assertEqual((status, body), (404, ''))

    def test_source_fixture_classification_keeps_five_exact_hosts_and_english_probe_filter(self):
        from scripts.verification.source_fixture_urls import exclude_non_english_fixture
        for locale in ('en', 'nl', 'de', 'fr', 'es'):
            url = f'https://{locale}.wikipedia.org/w/api.php?action=query'
            self.assertTrue(wikipedia_api_fixture(url))
            self.assertEqual(exclude_non_english_fixture(url), locale != 'en')
        for url in ('https://duckduckgo.com/html/?q=music',
                    'https://html.duckduckgo.com/html/?q=music'):
            self.assertTrue(exclude_non_english_fixture(url))
            self.assertFalse(wikipedia_api_fixture(url))
        for url in ('https://unrelated.invalid/?next=https://en.wikipedia.org/w/api.php',
                    'https://en.wikipedia.org@unrelated.invalid/w/api.php',
                    'https://en.wikipedia.org.unrelated.invalid/w/api.php',
                    'http://en.wikipedia.org/w/api.php',
                    'https://en.wikipedia.org:bad/w/api.php',
                    'https://en.wikipedia.org:444/w/api.php'):
            self.assertFalse(wikipedia_api_fixture(url))

    async def test_musical_group_identity_accepts_five_language_descriptions_not_generic_group(self):
        async def guard():
            pass
        for locale, description in [('en','Dutch indie pop group'),('nl','Nederlandse popgroep'),
                ('de','niederländische Popgruppe'),('fr','groupe de pop néerlandais'),('es','grupo de pop neerlandés')]:
            async def network(fetch,url,**kwargs):
                await fetch.guard()
                fetch.requests += 1
                return 200,json.dumps({'query':{'pages':[{'title':'Nora Vale 1',
                    'pageprops':{'wikibase_item':'Q1','wikibase-shortdesc':description},
                    'extract':f'<p>Nora Vale 1: {description}.</p>','revisions':[{'revid':1}]}]}}),url
            with self.subTest(locale=locale), patch.object(self.research.PublicFetch,'request',network):
                async with self.research.PublicFetch(guard) as fetch:
                    page = await self.research.wikipedia(fetch,'Nora Vale 1','Introduce this group',locale,
                        expected_roles=('Group',),expected_entity_id='Q1')
                self.assertIsNotNone(page)
                self.assertEqual(page.entity_id,'Q1')
        self.assertIsNone(self.research.MUSICAL_GROUP.search('a research group'))

    async def test_episode_focus_binds_original_spans_and_full_review_offers_no_prefix(self):
        moment = await self.publish()
        self.assertIsNotNone(moment.narration_acceptance)
        generation = json.loads(self.calls[0].split('\nData:\n')[1])['public_music_research']
        focus = generation['editorial_focus']
        source = next(s for s in generation['sources'] if s['content_hash']==focus['source_id'])
        self.assertTrue(set(focus['episode_span_ids']) <= {s['id'] for s in source['evidence_spans']})
        self.assertEqual(generation['editorial_focus']['authority'],
            'telling_focus_only_full_original_context_remains_evidence')
        self.assertIn('Do not offer or return prefix recovery fields',self.calls[1])
        self.assertNotIn('you may additionally return supported_prefix',self.calls[1])
        assessment = json.loads(self.calls[1].split('\nData:\n')[1])
        self.assertEqual(set(assessment['allowed_evidence_ids']),
            {span['id'] for s in generation['sources'] for span in s['evidence_spans']})

    async def test_documented_interaction_wins_over_first_catalog_work_without_new_fact_authority(self):
        source = self.research.PublicSource('Wikipedia','Synthetic group','https://en.wikipedia.org/wiki/Synthetic_group',
            'Synthetic group released Debut then Second Album. During a tour, the group started playing together with Ada Reed.',
            'en','2026-10-17T00:00:00+00:00','2026-10-17T01:00:00+00:00','CC-BY-SA-4.0',
            revision_url='https://en.wikipedia.org/w/index.php?oldid=1',entity_id='Q1',
            source_anchors=('Debut','Second Album'))
        projection = self.research.research_projection('Synthetic group',[source],{'state':'available'})
        focus = self.research.documented_episode_focus(projection)
        spans = self.research.evidence_spans(projection['sources'][0])
        self.assertEqual(focus['episode_span_ids'],[spans[1]['id']])
        self.assertEqual(len(projection['sources'][0]['evidence_spans']),2)
        catalogue = replace(source,text='Synthetic group released Debut then Second Album.')
        self.assertIsNone(self.research.documented_episode_focus(
            self.research.research_projection('Synthetic group',[catalogue],{'state':'available'})))

    async def test_requested_live_episode_precedes_unrelated_recording_collaboration(self):
        source = self.research.PublicSource('Wikipedia','Synthetic group','https://en.wikipedia.org/wiki/Synthetic_group',
            'The group recorded First Work with Ada Reed. The group performed Second Work live at Town Hall.',
            'en','2026-10-17T00:00:00+00:00','2026-10-17T01:00:00+00:00','CC-BY-SA-4.0',
            revision_url='https://en.wikipedia.org/w/index.php?oldid=1',entity_id='Q1',
            source_anchors=('First Work','Second Work'))
        projection = self.research.research_projection('Synthetic group',[source],{'state':'available'})
        before = json.dumps(projection,sort_keys=True)
        focus = self.research.documented_episode_focus(projection,angle='live_history')
        spans = self.research.evidence_spans(projection['sources'][0])
        self.assertEqual(focus['episode_span_ids'],[spans[1]['id']])
        self.assertEqual(json.dumps(projection,sort_keys=True),before)
        self.assertEqual(focus['authority'],'telling_focus_only_full_original_context_remains_evidence')

    def test_short_quoted_single_keeps_work_episode_without_generic_quote_authority(self):
        from custom_components.djconnect.public_artist_narration import _has_public_work_episode
        for title in ('One','Up','DNA','I'):
            for prefix,expected in (('released the single',True),('said',False)):
                quote=f'Ada Reed {prefix} "{title}".'
                anchors=self.research.source_work_anchors(quote)
                source=self.research._source('Wikipedia','Ada Reed','https://en.wikipedia.org/wiki/Ada_Reed',
                    quote,'en',source_anchors=anchors)
                span=self.research.evidence_spans(source.model_data())[0]
                review={'supported':True,'claim_checks':[{'text':f'Ada Reed released “{title}”.',
                    'kind':'relationship','evidence_ids':[span['id']],'quote':span['text']}]}
                self.assertEqual(_has_public_work_episode(review,(source,)),expected,(title,prefix))
                self.assertEqual(source.text,quote)
                review['claim_checks'][0]['kind']='dj_appreciation'
                self.assertFalse(_has_public_work_episode(review,(source,)))
        for quote in ('She described it as "One".','single "Unclosed title',
                      'single “Mismatched title"','song " padded "','song ""'):
            self.assertEqual(self.research.source_work_anchors(quote),(),quote)
        self.assertEqual(self.research.source_work_anchors('the single «One».'),('One',))
        self.assertEqual(self.research.source_work_anchors(
            'Ada Reed wrote and produced "Amber Nights".'),('Amber Nights',))
        self.assertEqual(self.research.source_work_anchors('Ada Reed wrote "Amber Nights".'),())
        self.assertEqual(self.research.source_work_anchors('Ada Reed wrote and produced "I".'),())
        for title,ordinary in (('One','One musician invited Ada Reed to a studio.'),
                ('I','I invited Ada Reed to a studio.'),('Up','Ada Reed stood up.')):
            text=f'Ada Reed released the single "{title}". '+ordinary
            source=self.research._source('Wikipedia','Ada Reed','https://en.wikipedia.org/wiki/Ada_Reed',
                text,'en',source_anchors=self.research.source_work_anchors(text))
            span=self.research.evidence_spans(source.model_data())[-1]
            review={'supported':True,'claim_checks':[{'text':ordinary,'kind':'relationship',
                'evidence_ids':[span['id']],'quote':span['text']}]}
            self.assertFalse(_has_public_work_episode(review,(source,)))
            self.assertFalse(self.research._answer_mentions_anchor(title+' More',title,[title]))

    async def test_markdown_bubble_is_not_admitted_or_sent_to_an_extra_model_review(self):
        self.answer = '*'+self.answer+'*'
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.debug['block_reason'],'research_answer_format_invalid')

    async def test_story_without_named_artist_is_not_admitted_for_contextless_tts(self):
        self.answer = self.answer.replace('Nora Vale 1','deze artiest')
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(len(self.calls),1)

    async def test_wikipedia_excerpt_has_complete_sentences_without_heading_year_contamination(self):
        parser = self.research.PageText(omit_headings=True)
        parser.feed('<h2>Voorgeschiedenis (2005-2014)</h2>'
            '<p>Son Mieux begon in 2015 als soloproject van de Haagse Camiel Meiresonne.</p>'
            '<p>De groep nam een nummer opnieuw op.</p>')
        self.assertNotIn('2005',parser.text())
        self.assertTrue(parser.text().startswith('Son Mieux begon in 2015'))
        sentence = 'An exact complete source sentence about a named recording.'
        original = 'A musical group is identified here.\n'+sentence+'\n'+('A second complete sentence follows. '*20)
        selected = self.research.excerpt(original,'this recording',160)
        self.assertLessEqual(len(selected),160)
        self.assertIn(sentence,selected)
        self.assertTrue(all(part in self.research._sentences(original)
                            for part in self.research._sentences(selected)))

    async def test_recording_credit_needs_own_subject_qualification_not_artist_seed_promotion(self):
        from custom_components.djconnect.session_facts import recording_facts
        from custom_components.djconnect.narration_brief import qualify
        from custom_components.djconnect.public_artist_narration import eligible_subject
        fact = recording_facts(self.catalog,{'id':'00000000-0000-0000-0000-000000000001',
            'title':self.catalog['title'],'artist-credit':[{'artist':{'name':self.catalog['artist']}}],
            'relations':[{'type':'producer','target-type':'artist',
                'artist':{'id':'00000000-0000-0000-0000-000000000002','name':'Leo Abrahams'}},
                {'type':'producer','target-type':'artist',
                'artist':{'id':'00000000-0000-0000-0000-000000000003','name':'Editors'}}]})[0]
        brief = qualify(fact,locale='nl',persona='home_dj',mood='energy',seed=fact.copy_for('nl')[1])
        self.assertIsNotNone(brief)
        self.assertIsNone(eligible_subject(brief))
        self.assertEqual(fact.key,'recording_credits')

    async def prepare_composer(self):
        from custom_components.djconnect.session_facts import work_facts
        from custom_components.djconnect.public_artist_narration import composer_subject
        self.composer_mode = True
        self.fact=work_facts(self.catalog,{
            'id':'00000000-0000-0000-0000-000000000001','title':self.catalog['title'],
            'artist-credit':[{'artist':{'name':self.catalog['artist']}}],
            'relations':[{'type':'performance','target-type':'work','work':{
                'id':'00000000-0000-0000-0000-000000000010','relations':[
                    {'type':'composer','target-type':'artist','artist':{
                        'id':'00000000-0000-0000-0000-000000000020','name':'Ada Reed'}}]}}]})[0]
        self.selected_credit=composer_subject(self.fact)
        self.assertIsNotNone(self.selected_credit)
        self.actor_type='Person'
        self.answer=('Ada Reed is componist van het werk achter deze opname. '
            'Voor Paper Lanterns werkte Ada Reed samen met Nora Vale 1.')
        await self.manager.async_update_allowed_capability_intents(owner_profile_id='profile-a',
            session_id=self.session.session_id,allowed_capability_intents=frozenset({'track_context'}))
        self.session=await self.manager.async_get_active('profile-a')

    async def test_composer_story_publishes_reopens_and_keeps_exact_work_role_and_replay_sources(self):
        await self.prepare_composer()
        from custom_components.djconnect.public_artist_narration import admitted
        from custom_components.djconnect.session_conversation import query_service
        from custom_components.djconnect.session_speech import resolve_retained
        moment=await self.publish()
        self.assertIsNotNone(moment,self.debug)
        self.assertEqual(moment.content,self.answer)
        self.assertEqual(moment.moment_type.value,'track')
        self.assertTrue(admitted(moment))
        self.assertEqual(moment.narration_acceptance.accepted.subject_identity,
            ('composer',self.selected_credit.contributor_id,'Ada Reed','Person','Q1'))
        data=json.loads(self.calls[0].split('\nData:\n')[1])['public_music_research']
        self.assertEqual(data['work_credit_scope']['selected_contributor'],'Ada Reed')
        self.assertNotIn('recording_credit_scope',data)
        self.assertNotIn(self.catalog['title'],self.calls[0])
        self.assertNotIn(self.catalog['album_name'],self.calls[0])
        self.assertEqual((len(self.calls),len(self.urls)),(2,4))
        await self.manager.async_end(owner_profile_id='profile-a',session_id=self.session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        page=await query_service(self.hass,self.history).async_timeline_page('profile-a',self.session.session_id)
        entry=next(e for e in page['entries'] if e.get('moment_id')==moment.moment_id)
        self.assertEqual(entry['text'],self.answer)
        self.assertEqual(entry['sources'],moment.as_dict()['sources'])
        descriptor,guard=await resolve_retained(self.hass,self.history,'profile-a',
            {'session_id':self.session.session_id,'entry_id':entry['entry_id']})
        self.assertTrue(descriptor['manual_allowed'])
        self.assertEqual(guard.processor_basis,'qualified_dialogue_v1')
        self.assertEqual((len(self.calls),len(self.urls)),(2,4))

    async def test_name_only_composition_credit_does_not_publish_or_spend_on_symbolic_fallback(self):
        await self.prepare_composer()
        self.fact=replace(self.fact,work_evidence=None)
        self.assertIsNone(await self.publish())
        self.assertEqual((self.calls,self.urls),([],[]))
        self.assertEqual(self.session.presence_ledger.total_published,0)
        self.assertIn('work_composers',self.manager._intra_track_opportunities['profile-a'].used_fact_keys)

    async def test_rejected_composer_style_never_publishes_original_credit_template(self):
        await self.prepare_composer()
        self.bad_review=True
        self.assertIsNone(await self.publish())
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.session.presence_ledger.total_published,0)
        self.assertEqual(self.session.broadcast.state.dj_moments,())

    async def test_composer_cannot_be_promoted_to_recording_producer_by_true_review_flags(self):
        await self.prepare_composer()
        self.answer=self.answer.replace('componist van het werk achter','producer van')
        self.assertIsNone(await self.publish())
        self.assertEqual(len(self.calls),2)

    async def test_work_credit_proof_cannot_be_replaced_by_another_works_wikipedia_episode(self):
        await self.prepare_composer()
        original=self.model
        async def wrong_source(hass,data,**kwargs):
            result=await original(hass,data,**kwargs)
            if len(self.calls)%2==0:
                evidence=json.loads(data['text'].split('\nData:\n')[1])['evidence']['public_music_research']
                span=next(s for s in evidence['sources'][0]['evidence_spans'] if 'Paper Lanterns' in s['text'])
                review=json.loads(result['response']['speech']['plain']['speech'])
                review['claim_checks'][0]['evidence_ids']=[span['id']]
                result['response']['speech']['plain']['speech']=json.dumps(review)
            return result
        self.model=wrong_source
        self.assertIsNone(await self.publish())
        self.assertEqual(self.debug['block_reason'],'research_work_credit_evidence_missing')

    async def test_wrong_composer_identity_never_borrows_the_playback_performer(self):
        await self.prepare_composer()
        self.actor_name_override=self.catalog['artist']
        self.assertIsNone(await self.publish())
        self.assertEqual(len(self.urls),1)
        self.assertEqual(self.calls,[])
        self.assertEqual(self.debug['block_reason'],'composer_public_identity_unavailable')

    async def test_fetched_composer_biography_and_true_flags_do_not_upgrade_bare_credits(self):
        await self.prepare_composer()
        self.answer=('Ada Reed is componist van het werk achter deze opname. '
            'Ada Reed staat dus in de compositiecredits vermeld.')
        self.assertIsNone(await self.publish())
        self.assertEqual(self.debug['block_reason'],'research_composer_episode_unverified')
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.session.presence_ledger.total_published,0)

    async def test_composer_episode_needs_independent_verdict_in_addition_to_source_ids(self):
        await self.prepare_composer()
        original=self.model
        async def missing_episode(hass,data,**kwargs):
            result=await original(hass,data,**kwargs)
            if len(self.calls)%2==0:
                review=json.loads(result['response']['speech']['plain']['speech'])
                review.pop('composer_episode_preserved')
                result['response']['speech']['plain']['speech']=json.dumps(review)
            return result
        self.model=missing_episode
        self.assertIsNone(await self.publish())
        self.assertEqual(self.debug['block_reason'],'research_composer_episode_unverified')

    async def prepare_producer(self, *, group=False):
        """All source/model replies below are explicit synthetic external fixtures."""
        from custom_components.djconnect.session_facts import recording_facts
        self.producer_mode = True
        names = ['Lantern Quartet','Ada Reed'] if group else ['Ada Reed','Lantern Quartet']
        self.fact = recording_facts(self.catalog,{'id':'00000000-0000-0000-0000-000000000010',
            'title':self.catalog['title'],'artist-credit':[{'artist':{'name':self.catalog['artist']}}],
            'relations':[{'type':'producer','target-type':'artist',
                'artist':{'id':f'00000000-0000-0000-0000-{i+20:012d}','name':name}}
                for i,name in enumerate(names)]})[0]
        from custom_components.djconnect.public_artist_narration import producer_subject
        self.selected_credit = producer_subject(self.fact)
        self.assertIsNotNone(self.selected_credit)
        self.actor_type = 'Group' if group else 'Person'
        self.answer = f'{names[0]} en {names[1]} staan op deze opname als producers vermeld. '
        self.answer += f'Voor Paper Lanterns werkte {names[0]} samen met Nora Vale 1.'
        await self.manager.async_update_allowed_capability_intents(owner_profile_id='profile-a',
            session_id=self.session.session_id,allowed_capability_intents=frozenset({'track_context'}))
        self.session = await self.manager.async_get_active('profile-a')

    async def test_producer_track_actual_commit_reopen_and_speech_keep_roles_sources_and_identity(self):
        await self.prepare_producer()
        from custom_components.djconnect import public_artist_narration as narration
        from custom_components.djconnect.session_conversation import query_service
        from custom_components.djconnect.session_speech import resolve_retained
        moment = await self.publish()
        self.assertEqual(moment.content,self.answer,self.debug)
        self.assertEqual(moment.moment_type.value,'track')
        self.assertTrue(narration.admitted(moment))
        self.assertEqual(len(self.calls),2)
        self.assertEqual(len(self.urls),4)
        self.assertTrue(all(fetch is self.fetch_owners[0] for fetch in self.fetch_owners))
        accepted = moment.narration_acceptance.accepted
        self.assertEqual(accepted.subject_identity,
            ('producer',self.selected_credit.contributor_id,'Ada Reed','Person','Q1'))
        generation = json.loads(self.calls[0].split('\nData:\n')[1])['public_music_research']
        self.assertEqual(generation['recording_credit_scope']['selected_contributor'],'Ada Reed')
        self.assertNotIn(self.catalog['title'],self.calls[0])
        self.assertNotIn(self.catalog['album_name'],self.calls[0])
        self.assertFalse(narration.admitted(replace(moment,narration_acceptance=replace(
            moment.narration_acceptance,accepted=replace(accepted,subject_identity=
                ('producer',self.selected_credit.contributor_id,'Lantern Quartet','Group','Q2'))))))
        self.assertEqual(self.session.presence_ledger.total_published,1)
        await self.manager.async_end(owner_profile_id='profile-a',session_id=self.session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        page = await query_service(self.hass,self.history).async_timeline_page('profile-a',self.session.session_id)
        entry = next(e for e in page['entries'] if e.get('moment_id')==moment.moment_id)
        self.assertEqual(entry['text'],self.answer)
        self.assertEqual(entry['sources'],moment.as_dict()['sources'])
        descriptor,guard = await resolve_retained(self.hass,self.history,'profile-a',
            {'session_id':self.session.session_id,'entry_id':entry['entry_id']})
        self.assertTrue(descriptor['manual_allowed'])
        self.assertEqual(guard.processor_basis,'qualified_dialogue_v1')
        self.assertEqual((len(self.urls),len(self.calls)),(4,2))

    async def test_group_producer_is_not_forced_into_person_identity(self):
        await self.prepare_producer(group=True)
        moment = await self.publish()
        self.assertEqual(moment.content,self.answer,self.debug)
        self.assertEqual(moment.narration_acceptance.accepted.subject_identity[2:4],('Lantern Quartet','Group'))

    async def test_fetched_biography_does_not_upgrade_a_credit_only_answer_even_if_review_claims_episode(self):
        await self.prepare_producer()
        self.answer=('Ada Reed staat op deze opname als producer vermeld. '
                     'Lantern Quartet staat ook als producer op deze opname vermeld.')
        original_model=self.model
        async def credit_only(hass,data,**kwargs):
            result=await original_model(hass,data,**kwargs)
            if len(self.calls)%2==0:
                evidence=json.loads(data['text'].split('\nData:\n')[1])['evidence']['public_music_research']
                seed_id=evidence['sources'][-1]['evidence_spans'][0]['id']
                review=json.loads(result['response']['speech']['plain']['speech'])
                for check in review['claim_checks']:
                    check['evidence_ids']=[seed_id]
                result['response']['speech']['plain']['speech']=json.dumps(review)
            return result
        self.model=credit_only
        self.assertIsNone(await self.publish())
        self.assertEqual(self.debug['block_reason'],'research_producer_episode_unverified')
        self.assertEqual(len(self.calls),2)
        self.assertGreater(len(self.urls),2)  # A fetched page is not proof of use.
        self.assertEqual(self.session.presence_ledger.total_published,0)

    async def test_producer_episode_requires_its_own_independent_verdict(self):
        await self.prepare_producer()
        original_model=self.model
        async def missing_verdict(hass,data,**kwargs):
            result=await original_model(hass,data,**kwargs)
            if len(self.calls)%2==0:
                review=json.loads(result['response']['speech']['plain']['speech'])
                review.pop('producer_episode_preserved')
                result['response']['speech']['plain']['speech']=json.dumps(review)
            return result
        self.model=missing_verdict
        self.assertIsNone(await self.publish())
        self.assertEqual(self.debug['block_reason'],'research_producer_episode_unverified')
        self.assertEqual(len(self.calls),2)

    async def test_other_work_producer_credit_cannot_replace_current_recording_proof(self):
        await self.prepare_producer()
        self.article_fixture = ('<p>Ada Reed is a musician and producer.</p>'
            '<p>Ada Reed is the producer of Paper Lanterns and recorded Paper Lanterns with Nora Vale 1.</p>')
        self.answer = ('Op Paper Lanterns werkte Ada Reed als producer met Nora Vale 1. '
            'Ada Reed nam Paper Lanterns op met Nora Vale 1.')
        original_model = self.model

        async def wrong_focus_review(hass, data, **kwargs):
            result = await original_model(hass, data, **kwargs)
            if len(self.calls) % 2 == 0:
                evidence = json.loads(data['text'].split('\nData:\n')[1])['evidence']['public_music_research']
                span = next(s for s in evidence['sources'][0]['evidence_spans'] if 'Paper Lanterns' in s['text'])
                review = json.loads(result['response']['speech']['plain']['speech'])
                # The external assessor incorrectly says current focus is kept,
                # while both true claims cite only another work's biography.
                for check in review['claim_checks']:
                    check['evidence_ids'] = [span['id']]
                result['response']['speech']['plain']['speech'] = json.dumps(review)
            return result

        self.model = wrong_focus_review
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.debug['block_reason'], 'research_recording_credit_evidence_missing')
        self.assertEqual(len(self.calls), 2)

    async def test_current_recording_proof_uses_original_source_id_across_five_languages(self):
        await self.prepare_producer()
        from custom_components.djconnect.public_artist_narration import _has_recording_credit_evidence
        from custom_components.djconnect.ask_dj.public_research import PublicSource, evidence_spans
        claims = [('en','Ada Reed is credited as producer on this recording.'),
            ('en','Ada Reed is credited as producer on this song.'),
            ('nl','Op deze opname staat Ada Reed als producer vermeld.'),
            ('nl','Bij dit lied staat Ada Reed als producer vermeld.'),
            ('de','Ada Reed ist bei dieser Aufnahme als Produzent genannt.'),
            ('de','Ada Reed ist bei diesem Lied als Produzent genannt.'),
            ('fr','Ada Reed figure au générique de cet enregistrement comme producteur.'),
            ('fr','Ada Reed figure au générique de cette chanson comme producteur.'),
            ('fr','Ada Reed figure au générique de ce titre comme producteur.'),
            ('es','Ada Reed figura como productor de esta grabación.'),
            ('es','Ada Reed figura como productor de este tema.')]
        for locale, claim in claims:
            seed = PublicSource(self.fact.provider, 'Ada Reed', self.fact.source_url,
                self.fact.copy_for(locale)[1], locale, '2026-10-18T00:00:00+00:00',
                '2026-10-18T01:00:00+00:00', 'CC0-1.0')
            reference = evidence_spans(seed.model_data())[0]['id']
            check = {'text':claim, 'kind':'relationship', 'evidence_ids':[reference], 'quote':seed.text}
            with self.subTest(locale=locale):
                self.assertTrue(_has_recording_credit_evidence({'claim_checks':[check]}, seed, 'Ada Reed'))
                for changed in ({**check,'evidence_ids':[]}, {**check,'evidence_ids':['other-work:p0']},
                        {**check,'evidence_ids':[{}]}, {**check,'quote':'Another work.'},
                        {**check,'text':claim.replace('Ada Reed','Lantern Quartet')},
                        {**check,'text':claim.replace('Ada Reed','Ada Reedman')},
                        {**check,'text':claim.replace('Ada Reed','SuperAda Reed')},
                        {**check,'kind':'dj_appreciation'}):
                    self.assertFalse(_has_recording_credit_evidence({'claim_checks':[changed]}, seed, 'Ada Reed'))
                for general in ('Ada Reed works with Lantern Quartet.',
                        'Ada Reed is a producer.', 'Ada Reed is credited here.',
                        'Bei Lantern Quartet trägt Ada Reed den Produktionscredit.',
                        'Ada Reed figure au générique de Lantern Quartet.',
                        'Ada Reed figura como productor de Lantern Quartet.'):
                    self.assertFalse(_has_recording_credit_evidence({'claim_checks':[
                        {**check,'text':general}]}, seed, 'Ada Reed'))
        self.assertFalse(_has_recording_credit_evidence({'claim_checks':None}, seed, 'Ada Reed'))

    async def test_extended_other_person_name_is_not_the_resolved_producer(self):
        await self.prepare_producer()
        self.answer = self.answer.replace('Ada Reed', 'Ada Reedman')
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.debug['block_reason'], 'research_answer_format_invalid')
        self.assertEqual(len(self.calls), 1)

    async def test_band_level_credit_is_not_a_current_recording_connection(self):
        await self.prepare_producer()
        # Actual trial9 failure: the review asserted current-recording focus
        # and cited the original credit, but the words generalized it to a band.
        self.answer = ('Bij Lantern Quartet draagt Ada Reed de producentencredit, gedeeld met Lantern Quartet. '
            'Voor Paper Lanterns werkte Ada Reed samen met Nora Vale 1.')
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.debug['block_reason'], 'research_recording_credit_evidence_missing')
        self.assertEqual(len(self.calls), 2)

    async def test_wrong_same_name_producer_cannot_fetch_wikipedia_or_try_other_contributor(self):
        await self.prepare_producer()
        self.actor_name_override = 'Different person'
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.calls,[])
        self.assertEqual(len(self.urls),1)
        self.assertIn(self.selected_credit.contributor_id,self.urls[0])

    async def test_wrong_reciprocal_producer_id_does_not_promote_recording_credit(self):
        await self.prepare_producer()
        self.reciprocal_id_override = '00000000-0000-0000-0000-000000000099'
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.calls,[])
        self.assertEqual(len(self.urls),2)

    async def test_partial_or_conflicting_producer_credit_cannot_research(self):
        await self.prepare_producer()
        from custom_components.djconnect.public_artist_narration import producer_subject
        evidence = self.fact.recording_evidence
        changes = [replace(self.fact,recording_evidence=None),
            replace(self.fact,recording_evidence=replace(evidence,producers=evidence.producers[:1])),
            replace(self.fact,recording_evidence=replace(evidence,observed_at=evidence.observed_at+1)),
            replace(self.fact,recording_evidence=replace(evidence,producers=(evidence.producers[0],
                replace(evidence.producers[1],name=evidence.producers[0].name)))),
            replace(self.fact,recording_evidence=replace(evidence,producers=(
                replace(evidence.producers[0],qualifications=('additional',)),evidence.producers[1])))]
        for fact in changes:
            with self.subTest(fact=fact):
                self.assertIsNone(producer_subject(fact))

    async def test_other_credit_roles_are_preserved_but_ambiguous_producer_ids_cannot_research(self):
        await self.prepare_producer()
        from custom_components.djconnect.session_facts import recording_facts
        from custom_components.djconnect.public_artist_narration import producer_subject
        base = {'id':'00000000-0000-0000-0000-000000000010','title':self.catalog['title'],
            'artist-credit':[{'artist':{'name':self.catalog['artist']}}]}
        producer = {'type':'producer','target-type':'artist',
            'artist':{'id':'00000000-0000-0000-0000-000000000020','name':'Ada Reed'}}
        mixed = recording_facts(self.catalog,{**base,'relations':[producer,
            {'type':'vocal','target-type':'artist','artist':{
                'id':'00000000-0000-0000-0000-000000000021','name':'Nora Vale 1'}}]})[0]
        duplicate = recording_facts(self.catalog,{**base,'relations':[producer,
            {**producer,'artist':{**producer['artist'],'id':'00000000-0000-0000-0000-000000000021'}}]})[0]
        self.assertEqual(producer_subject(mixed).name,'Ada Reed')
        self.assertIsNone(producer_subject(duplicate))

    async def test_instrument_and_producer_credit_both_survive_actual_connected_publication(self):
        await self.prepare_producer()
        from custom_components.djconnect.session_facts import recording_facts
        credit = self.fact.recording_evidence
        self.fact = recording_facts(self.catalog,{'id':credit.recording_id,'title':self.catalog['title'],
            'artist-credit':[{'artist':{'name':self.catalog['artist']}}],
            'relations':[{'type':'instrument','target-type':'artist','artist':{
                'id':'00000000-0000-0000-0000-000000000099','name':'Ellis Hart'}},
                *[{'type':'producer','target-type':'artist','artist':{'id':p.contributor_id,'name':p.name}}
                  for p in credit.producers]]})[0]
        self.answer = 'Op deze opname staat Ellis Hart bij de instrumenten vermeld, Ada Reed en Lantern Quartet bij de productie. '
        self.answer += 'Voor Paper Lanterns werkte Ada Reed samen met Nora Vale 1.'
        moment = await self.publish()
        self.assertEqual(moment.content,self.answer,self.debug)
        self.assertIsNotNone(moment.narration_acceptance)
        assessment = json.loads(self.calls[1].split('\nData:\n')[1])['evidence']
        self.assertEqual(dict(assessment['required_recording_roles'])['instrument'],['Ellis Hart'])

    async def test_model_cannot_silently_reclassify_another_recording_role(self):
        await self.prepare_producer()
        self.recording_focus_preserved = False
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.debug['block_reason'],'research_recording_focus_unverified')

    async def test_recording_scope_is_typed_not_a_json_biography_or_activity_exemption(self):
        await self.prepare_producer()
        original = self.fact.copy_for('nl')[1]
        context = self.research.RecordingResearchContext({'qualified_context':{}},fact=self.fact,locale='nl')
        self.assertTrue(self.research._recording_credit_quote(context,original))
        self.assertFalse(self.research._recording_credit_quote(json.loads(json.dumps(context)),original))
        spoof = {'fact':self.fact,'locale':'nl','recording_credit':True}
        self.assertFalse(self.research._recording_credit_quote(spoof,original))
        self.assertFalse(self.research._recording_credit_quote(context,'Ada Reed is a record producer.'))
        self.assertFalse(self.research._recording_credit_quote(context,original+' Added.'))
        self.assertTrue(self.research._assertions_fit('Bij de productie van deze opname.',original,
            recording_credit=True))
        self.assertFalse(self.research._assertions_fit('Zij namen deze opname op.',original,
            recording_credit=True))
        self.assertFalse(self.research._assertions_fit('Zij produceerden dit album.',original,
            recording_credit=True))
        actions = {'en':['They recorded this recording.','They record this recording.'],
            'nl':['Zij namen deze opname op.','Zij nemen deze opname op.'],
            'de':['Sie nahmen diese Aufnahme auf.','Sie nehmen diese Aufnahme auf.'],
            'fr':['Ils ont enregistré cet enregistrement.','Ils enregistrent cet enregistrement.'],
            'es':['Ellos grabaron esta grabación.','Ellos graban esta grabación.']}
        for locale,sentences in actions.items():
            quote = self.fact.copy_for(locale)[1]
            for sentence in sentences:
                with self.subTest(locale=locale,sentence=sentence):
                    self.assertFalse(self.research._assertions_fit(sentence,quote,recording_credit=True))
        self.assertNotIn('fact',json.dumps(context))

    async def test_producer_research_cannot_invent_recording_sound_influence(self):
        await self.prepare_producer()
        self.producer_unsupported = True
        self.answer = 'Ada Reed en Lantern Quartet produceerden deze opname. Zij bepaalden daarmee het warme geluid.'
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(len(self.calls),2)

    async def test_focused_producer_story_keeps_all_original_credits_in_retained_context(self):
        await self.prepare_producer()
        self.answer = self.answer.replace(' en Lantern Quartet','')
        moment = await self.publish()
        self.assertEqual(moment.content,self.answer,self.debug)
        self.assertIsNotNone(moment.narration_acceptance)
        self.assertEqual(len(self.calls),2)
        self.assertIn('Lantern Quartet',moment.source_fact.copy_for('nl')[1])
        from custom_components.djconnect.ask_dj.service import _live_reference
        from custom_components.djconnect.ask_dj.dialogue import model_source
        selected = await _live_reference(self.manager, 'profile-a',
            {'session_id':self.session.session_id,'moment_id':moment.moment_id})
        context = model_source(selected)
        self.assertIn('Lantern Quartet',context['qualified_excerpt'])
        from custom_components.djconnect.session_conversation import query_service
        await self.manager.async_end(owner_profile_id='profile-a',session_id=self.session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        page = await query_service(self.hass,self.history).async_timeline_page('profile-a',self.session.session_id)
        entry = next(e for e in page['entries'] if e.get('moment_id')==moment.moment_id)
        self.assertEqual(entry['text'],self.answer)
        self.assertIn('Lantern Quartet',json.dumps(entry,ensure_ascii=False))

    async def test_missing_selected_producer_is_rejected_before_review(self):
        await self.prepare_producer()
        self.answer = self.answer.replace('Ada Reed','Lantern Quartet')
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(len(self.calls),1)

    async def test_focus_assessment_rejects_missing_credit_exclusivity_role_transfer_and_wrong_biography(self):
        await self.prepare_producer()
        cases = [
            'Ada Reed is muzikant. Voor Paper Lanterns werkte Ada Reed samen met Nora Vale 1.',
            'Ada Reed is de enige producer van deze opname. Voor Paper Lanterns werkte Ada Reed samen met Nora Vale 1.',
            'Ada Reed en Lantern Quartet zijn de volledige credits van deze opname. Voor Paper Lanterns werkte Ada Reed samen met Nora Vale 1.',
            'Ada Reed is hier producer en Lantern Quartet de zanger. Voor Paper Lanterns werkte Ada Reed samen met Nora Vale 1.',
            'Ada Reed is hier producer. Voor Paper Lanterns werkte Lantern Quartet samen met Nora Vale 1.',
        ]
        self.recording_focus_preserved = False
        from custom_components.djconnect.narration_brief import qualify
        from custom_components.djconnect.public_artist_narration import realize
        brief = qualify(self.fact,locale='nl',persona='home_dj',mood='energy',seed=self.fact.copy_for('nl')[1])
        async def ask(prompt):
            result = await self.model(self.hass,{'text':prompt})
            return result['response']['speech']['plain']['speech']
        async def network(fetch,url,**kwargs):
            return await self.fetch(fetch,url,**kwargs)
        for answer in cases:
            with self.subTest(answer=answer):
                self.calls.clear()
                self.answer = answer
                with patch.object(self.research.PublicFetch,'request',network):
                    result = await realize(brief,ask=ask,admission=lambda:None,debug=self.debug)
                self.assertIsNone(result)
                self.assertEqual(len(self.calls),2)
                self.assertEqual(self.debug['block_reason'],'research_recording_focus_unverified')
                prompt = self.calls[-1]
                self.assertIn('no exclusive/complete-credits claim',prompt)
                self.assertIn('transfer of biography',prompt)

    async def test_exact_source_title_emphasis_is_normalized_before_complete_assessment_and_commit(self):
        await self.prepare_producer()
        self.answer = self.answer.replace('Paper Lanterns','*Paper Lanterns*')
        moment = await self.publish()
        normalized = self.answer.replace('*Paper Lanterns*','Paper Lanterns')
        self.assertEqual(moment.content,normalized,self.debug)
        self.assertTrue(self.debug['source_title_emphasis_normalized'])
        self.assertEqual(len(self.calls),2)
        review_data = json.loads(self.calls[-1].split('\nData:\n')[1])
        self.assertEqual(review_data['answer'],normalized)
        self.assertEqual(moment.narration_acceptance.accepted.text,normalized)

    def test_title_normalization_never_strips_unknown_nested_unbalanced_or_link_emphasis(self):
        from custom_components.djconnect.public_artist_narration import plain_work_titles
        projection = {'sources':[{'source_anchors':['Paper Lanterns']}]}
        for text in ('***Paper Lanterns***','*Paper Lanterns**','**Paper Lanterns*',
                     '*Other Title*','[*Paper Lanterns*](https://example.org)',
                     '[see *Paper Lanterns*](https://example.org)','pre*Paper Lanterns*fix',
                     '*tekst **Paper Lanterns** tekst*','*Paper Lanterns* en *onbekend*'):
            with self.subTest(text=text):
                self.assertEqual(plain_work_titles(text,projection),text)
        self.assertEqual(plain_work_titles('Voor **Paper Lanterns** werkte Ada samen.',projection),
            'Voor Paper Lanterns werkte Ada samen.')

    def test_review_deduplication_requires_complete_literal_corpus_not_only_selected_24_spans(self):
        from custom_components.djconnect.public_artist_narration import complete_review_projection
        import hashlib
        def source(text):
            value={'untrusted_excerpt':text,'content_hash':hashlib.sha256(text.encode()).hexdigest()}
            value['evidence_spans']=self.research.evidence_spans(value)
            return value
        short=source('Ada recorded Paper Lanterns.\nNora played guitar.')
        long=source(' '.join(f'Original statement number {i}.' for i in range(25)))
        context={'public_music_research':{'sources':[short,long]}}
        result=complete_review_projection(context)['public_music_research']['sources']
        self.assertNotIn('untrusted_excerpt',result[0])
        self.assertEqual(result[0]['evidence_spans'],short['evidence_spans'])
        self.assertEqual(result[1]['untrusted_excerpt'],long['untrusted_excerpt'])
        self.assertEqual(context['public_music_research']['sources'][0],short)

    async def test_original_paragraph_keeps_quote_and_initial_contiguous_through_actual_publication(self):
        await self.prepare_producer()
        paragraph='Ada Reed met Nora Vale 1 in a shop. Nora said, "I saw Ada trying a guitar." They recorded Paper Lanterns with J. Peter Hall.'
        self.article_fixture='<p>Ada Reed is a musician.</p><p>'+paragraph.replace('Paper Lanterns','<i>Paper Lanterns</i>')+'</p>'
        moment=await self.publish()
        self.assertIsNotNone(moment.narration_acceptance,self.debug)
        generation=json.loads(self.calls[0].split('\nData:\n')[1])['public_music_research']
        self.assertEqual(generation['schema_version'],3)
        source=generation['sources'][0]
        self.assertEqual(source['evidence_schema'],'original_paragraphs_v1')
        self.assertEqual(source['evidence_spans'][-1]['text'],paragraph)
        self.assertIn('J. Peter Hall.',source['evidence_spans'][-1]['text'])
        self.assertNotIn('literal_passages',source)
        self.assertNotIn('original_text',json.dumps(moment.as_dict()))

    def test_original_paragraph_provenance_rejects_omitted_reordered_overlapping_or_changed_ranges(self):
        from custom_components.djconnect.ask_dj.public_research import paragraph_excerpt,PublicSource
        original='Ada is a musician.\nA short meeting in a shop.\n'+'Ignored material. '*60+'\nThey recorded Paper Lanterns with J. Peter Hall.'
        excerpt,ranges=paragraph_excerpt(original,'meeting recording',130)
        self.assertNotIn('Ignored',excerpt)
        source=PublicSource('Wikipedia','Ada','https://en.wikipedia.org/wiki/Ada',excerpt,'en','now','later',
            'CC-BY-SA-4.0',original_text=original,paragraph_ranges=ranges)
        data=source.model_data()
        spans=self.research.evidence_spans(data)
        self.assertEqual([s['text'] for s in spans],excerpt.splitlines())
        self.assertTrue(all(original[a:b]==s['text'] for s in spans for a,b in [s['original_range']]))
        self.assertGreater(ranges[-1][0],ranges[-2][1]+1)
        for changed in (replace(source,paragraph_ranges=tuple(reversed(ranges))),
                        replace(source,paragraph_ranges=(ranges[0],ranges[0])),
                        replace(source,text=excerpt+' Added.'),
                        replace(source,paragraph_ranges=((0,len(original)),)),
                        replace(source,paragraph_ranges=((ranges[0][0]+1,ranges[0][1]),))):
            with self.subTest(changed=changed.paragraph_ranges):
                with self.assertRaises(ValueError):
                    changed.model_data()
        for altered in ({**data,'literal_passages':list(reversed(data['literal_passages']))},
                        {**data,'untrusted_excerpt':excerpt+' Added.'},
                        {**data,'original_document_hash':'not-a-digest'}):
            self.assertEqual(self.research.evidence_spans(altered),[])
        answer='Ada recorded Paper Lanterns.'
        invalid={'supported':True,'claim_checks':[{'text':answer,'kind':'relationship',
            'evidence_ids':[spans[0]['id'],spans[-1]['id']],'quote':excerpt}]}
        self.assertFalse(self.research.supported(json.dumps(invalid),answer,
            {'public_music_research':{'schema_version':3,'sources':[data]}}))
        self.assertFalse(self.research.supported('{"supported":true}',answer,
            {'public_music_research':{'schema_version':4,'sources':[data]}}))

    def test_paragraph_context_cannot_transfer_another_works_activity_or_genre(self):
        from custom_components.djconnect.ask_dj.public_research import PublicSource
        from custom_components.djconnect.public_artist_narration import resolve_review_quotes
        paragraph='Ada Reed recorded Paper Lanterns. Nora Vale produced experimental Blue Room.'
        source=PublicSource('Wikipedia','Ada','https://en.wikipedia.org/wiki/Ada',paragraph,
            'en','now','later','CC-BY-SA-4.0',source_anchors=('Paper Lanterns','Blue Room'),
            original_text=paragraph,paragraph_ranges=((0,len(paragraph)),)).model_data()
        span=self.research.evidence_spans(source)[0]
        context={'public_music_research':{'schema_version':3,'sources':[source]}}
        for answer,expected in [('Ada Reed produced Paper Lanterns.',False),
                                ('Ada Reed recorded experimental Paper Lanterns.',False),
                                ('Ada Reed recorded Paper Lanterns.',True),
                                ('Nora Vale produced experimental Blue Room.',True)]:
            with self.subTest(answer=answer):
                data={'supported':True,'claim_checks':[{'text':answer,'kind':'relationship',
                    'evidence_ids':[span['id']],'quote':span['text']}]}
                self.assertEqual(self.research.supported(json.dumps(data),answer,context),expected)
                wire={**data,'review_schema':'source_id_review_v1','claim_checks':[
                    {k:v for k,v in c.items() if k!='quote'} for c in data['claim_checks']]}
                self.assertEqual(self.research.supported(json.dumps(resolve_review_quotes(wire,context)),
                    answer,context),expected)
                if 'Paper Lanterns' in answer:
                    cut=answer.index('Lanterns')
                    split=[{'text':part.strip(),'kind':'relationship','evidence_ids':[span['id']],
                        'quote':span['text']} for part in (answer[:cut],answer[cut:])]
                    self.assertEqual(self.research.supported(json.dumps({**data,'claim_checks':split}),
                        answer,context),expected)

    def test_id_review_preserves_exact_evidence_and_coverage_without_model_quote_echo(self):
        from custom_components.djconnect.public_artist_narration import resolve_review_quotes
        from custom_components.djconnect.ask_dj.public_research import PublicSource
        paragraph='Ada recorded Paper Lanterns.'
        source=PublicSource('Wikipedia','Ada','https://en.wikipedia.org/wiki/Ada',paragraph,'en',
            'now','later','CC-BY-SA-4.0',original_text=paragraph,paragraph_ranges=((0,len(paragraph)),)).model_data()
        context={'public_music_research':{'schema_version':3,'sources':[source]}}
        identifier=self.research.evidence_spans(source)[0]['id']
        check={'text':paragraph,'kind':'relationship','evidence_ids':[identifier]}
        wire={'review_schema':'source_id_review_v1','supported':True,'claim_checks':[check]}
        canonical=resolve_review_quotes(wire,context)
        self.assertEqual(canonical['claim_checks'][0]['quote'],paragraph)
        self.assertNotIn('quote',wire['claim_checks'][0])
        self.assertTrue(self.research.supported(json.dumps(canonical),paragraph,context))
        self.assertFalse(self.research.supported(json.dumps(canonical),paragraph+' Extra assertion.',context))
        for bad in ({**check,'evidence_ids':['unknown']},{**check,'evidence_ids':[identifier,identifier]},
                    {**check,'quote':'caller invented quote'},{**check,'kind':'dj_appreciation'},
                    {**check,'evidence_ids':identifier}):
            with self.subTest(check=bad):
                with self.assertRaises(ValueError):
                    resolve_review_quotes({**wire,'claim_checks':[bad]},context)
        with self.assertRaises(ValueError):
            resolve_review_quotes(wire,{'public_music_research':{**context['public_music_research'],'schema_version':2}})

    async def test_producer_wrong_wikipedia_entity_cannot_inherit_credit_acceptance(self):
        await self.prepare_producer()
        self.fetch_qid = 'Q999'
        moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.calls,[])

    async def test_producer_expiry_after_draft_prevents_review_and_publication(self):
        await self.prepare_producer()
        # The original immutable source really expires while the draft is
        # awaited; retrieval must not give it a new lifetime.
        deadline = time.monotonic()+1
        self.fact = replace(self.fact,source_expires_at=deadline)
        async def expire():
            await asyncio.sleep(max(0.01,deadline-time.monotonic()+0.01))
        self.after_draft = expire
        self.assertIsNone(await self.publish())
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.session.presence_ledger.total_published,0)

    async def test_producer_owner_revocation_after_sql_keeps_no_partial_flow(self):
        await self.prepare_producer()
        await self.test_owner_revocation_after_real_sql_stage_rolls_back_researched_text()

    async def test_producer_cancellation_keeps_original_opportunity_unconsumed(self):
        await self.prepare_producer()
        await self.test_cancellation_during_fetch_has_no_commit_or_extra_attempt()

    async def test_malformed_researched_original_fails_closed(self):
        await self.prepare_producer()
        from custom_components.djconnect.public_artist_narration import admitted
        moment = await self.publish()
        self.assertTrue(admitted(moment))
        changed = replace(moment,narration_acceptance=replace(moment.narration_acceptance,original=None))
        self.assertFalse(admitted(changed))

    def source_http_fixture(self):
        calls = []
        state = types.SimpleNamespace(status=200,on_enter=None)
        class Content:
            async def iter_chunked(self,size):
                yield b'{}'
        class Reply:
            status,headers,content_type,content_length = 200,{},'application/json',2
            content = Content()
            async def __aenter__(self):
                if state.on_enter:
                    await state.on_enter(self.url,self.status)
                return self
            async def __aexit__(self,*args):pass
        class Session:
            def get(inner,url,**kwargs):
                calls.append((asyncio.get_running_loop().time(),url))
                reply = Reply()
                reply.status,reply.url = state.status,url
                return reply
            async def close(inner):pass
        session = Session()
        aiohttp = types.ModuleType('aiohttp')
        aiohttp.ClientSession = lambda **kwargs:session
        aiohttp.ClientTimeout = lambda **kwargs:None
        aiohttp.ClientError = type('FixtureClientError',(Exception,),{})
        aiohttp.TCPConnector = lambda **kwargs:None
        aiohttp.DummyCookieJar = lambda:None
        helper = types.ModuleType('homeassistant.helpers.aiohttp_client')
        helper.async_get_clientsession = lambda hass:session
        return patch.dict(sys.modules,{'aiohttp':aiohttp,'homeassistant.helpers.aiohttp_client':helper}),session,calls,state

    async def test_catalog_resolver_and_public_research_share_actual_provider_rate_and_backoff(self):
        from custom_components.djconnect.session_facts import SessionFactsResolver
        boundary,session,calls,state = self.source_http_fixture()
        async def guard():pass
        with boundary:
            resolver = SessionFactsResolver(object())
            async with self.research.PublicFetch(guard) as fetch:
                await asyncio.gather(resolver._get('artist/00000000-0000-0000-0000-000000000001'),
                    fetch.request('https://musicbrainz.org/ws/2/artist/00000000-0000-0000-0000-000000000002'))
                self.assertEqual(len(calls),2)
                self.assertGreaterEqual(calls[1][0]-calls[0][0],1.09)
                state.status = 503
                await resolver._get('artist/00000000-0000-0000-0000-000000000003')
                before = len(calls)
                with self.assertRaises(self.research.ResearchUnavailable):
                    await fetch.request('https://musicbrainz.org/ws/2/artist/00000000-0000-0000-0000-000000000004')
                self.assertEqual(await SessionFactsResolver(object())._get(
                    'artist/00000000-0000-0000-0000-000000000005'),{})
                self.assertEqual(len(calls),before)

    async def test_rate_waiting_public_guard_cannot_be_overtaken_by_catalog_dispatch(self):
        from custom_components.djconnect.session_facts import SessionFactsResolver
        boundary,session,calls,state = self.source_http_fixture()
        entered,release = asyncio.Event(),asyncio.Event()
        guards = 0
        async def guard():
            nonlocal guards
            guards += 1
            if guards == 2:
                entered.set()
                await release.wait()
        with boundary:
            async with self.research.PublicFetch(guard) as fetch:
                first = asyncio.create_task(fetch.request('https://musicbrainz.org/ws/2/artist/public'))
                await asyncio.wait_for(entered.wait(),1)
                second = asyncio.create_task(SessionFactsResolver(object())._get('artist/catalog'))
                try:
                    await asyncio.sleep(1.15)
                    self.assertEqual(calls,[])
                finally:
                    release.set()
                    await asyncio.gather(first,second)
                self.assertEqual(len(calls),2)
                self.assertGreaterEqual(calls[1][0]-calls[0][0],1.09)

    async def test_rate_backoff_arriving_during_public_guard_prevents_dispatch(self):
        from custom_components.djconnect.session_facts import SessionFactsResolver
        boundary,session,calls,state = self.source_http_fixture()
        catalog_entered,catalog_release = asyncio.Event(),asyncio.Event()
        public_entered,public_release = asyncio.Event(),asyncio.Event()
        async def response(url,status):
            if url.endswith('/catalog'):
                catalog_entered.set()
                await catalog_release.wait()
        guards = 0
        async def guard():
            nonlocal guards
            guards += 1
            if guards == 2:
                public_entered.set()
                await public_release.wait()
        state.status,state.on_enter = 503,response
        with boundary:
            async with self.research.PublicFetch(guard) as fetch:
                first = asyncio.create_task(SessionFactsResolver(object())._get('artist/catalog'))
                await asyncio.wait_for(catalog_entered.wait(),1)
                second = asyncio.create_task(fetch.request('https://musicbrainz.org/ws/2/artist/public'))
                try:
                    await asyncio.wait_for(public_entered.wait(),2)
                    catalog_release.set()
                    self.assertEqual(await first,{})
                finally:
                    catalog_release.set()
                    public_release.set()
                with self.assertRaises(self.research.ResearchUnavailable):
                    await second
                self.assertEqual(len(calls),1)

    async def test_rate_received_public_503_blocks_catalog_while_response_guard_waits(self):
        from custom_components.djconnect.session_facts import SessionFactsResolver
        boundary,session,calls,state = self.source_http_fixture()
        entered,release = asyncio.Event(),asyncio.Event()
        guards = 0
        async def guard():
            nonlocal guards
            guards += 1
            if guards == 3:
                entered.set()
                await release.wait()
        state.status = 503
        with boundary:
            async with self.research.PublicFetch(guard) as fetch:
                task = asyncio.create_task(fetch.request('https://musicbrainz.org/ws/2/artist/public'))
                await asyncio.wait_for(entered.wait(),1)
                try:
                    self.assertEqual(await SessionFactsResolver(object())._get('artist/catalog'),{})
                    self.assertEqual(len(calls),1)
                finally:
                    release.set()
                    await task

    async def test_rate_received_public_503_keeps_backoff_after_owner_revocation(self):
        from custom_components.djconnect.session_facts import SessionFactsResolver
        boundary,session,calls,state = self.source_http_fixture()
        guards = 0
        async def guard():
            nonlocal guards
            guards += 1
            if guards == 3:
                raise PermissionError('fixture_owner_revoked')
        state.status = 503
        with boundary:
            async with self.research.PublicFetch(guard) as fetch:
                with self.assertRaises(PermissionError):
                    await fetch.request('https://musicbrainz.org/ws/2/artist/public')
            self.assertEqual(await SessionFactsResolver(object())._get('artist/catalog'),{})
            self.assertEqual(len(calls),1)

    async def test_producer_lookup_and_wikipedia_share_original_request_cap(self):
        await self.prepare_producer()
        with patch.object(self.research,'MAX_REQUESTS',2):
            moment = await self.publish()
        self.assertIsNone(moment)
        self.assertEqual(self.calls,[])
        self.assertEqual(len(self.urls),2)

    async def test_track_change_during_producer_research_prevents_publication(self):
        await self.prepare_producer()
        async def change():
            await self.manager.async_update_playback_projection(owner_profile_id='profile-a',
                session_id=self.session.session_id,state='playing',media_identity='spotify:track:'+'Z'*22,
                title='Another track',artist='Another artist',duration_ms=300000,position_ms=0)
        self.after_fetch = change
        self.assertIsNone(await self.publish())
        self.assertEqual(self.calls,[])
        self.assertEqual(self.session.presence_ledger.total_published,0)
