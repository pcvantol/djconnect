"""Real Planner/Runtime/SQLite; declared external source and model fixtures.

These are sequence/admission regressions, not real LLM or installed quality.
"""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import time
import unittest
from unittest.mock import patch

from tests import test_personal_dj_narration_public_artist as owner
from custom_components.djconnect import session_story_variety as variety


class StoryVarietyPolicyTest(unittest.TestCase):
    def test_topic_rotation_is_published_only_and_not_a_fixed_output_template(self):
        rows=[]
        for topic in variety.TOPICS * 2:
            self.assertEqual(variety.next_topic(rows),topic)
            rows.append((topic,'Public accepted story',('a'*64,)))
        self.assertNotIn('Nirvana',repr(variety.PURPOSES))

    def test_credit_cooldown_is_shared_across_credit_kinds_but_exact_artist_scoped(self):
        from tests.context_variation_fixtures import source
        from custom_components.djconnect.session_facts import ArtistImageIdentity
        _,fact=source('formation',0)
        identity=ArtistImageIdentity('spotify:artist:'+'A'*22,'Q1','Fixture band','00000000-0000-0000-0000-000000000001')
        credit=replace(fact,key='recording_credits',artwork_artist_identity=identity)
        composer=replace(credit,key='work_composers')
        recent=(('Q1','credits'),('Q1','artist_begin'))
        self.assertTrue(variety.credit_cooldown(credit,recent))
        self.assertTrue(variety.credit_cooldown(composer,recent))
        self.assertTrue(variety.credit_cooldown(replace(composer,artwork_artist_identity=None,public_artist_qid='Q1'),recent))
        self.assertFalse(variety.credit_cooldown(replace(credit,artwork_artist_identity=replace(identity,wikidata_id='Q2')),recent))
        self.assertFalse(variety.credit_cooldown(fact,recent))
        self.assertFalse(variety.credit_cooldown(credit,(*recent,('Q1','album'),('Q1','artist'))))

    def test_topic_rank_preserves_original_passages_in_five_languages(self):
        from custom_components.djconnect.ask_dj.public_research import paragraph_excerpt
        for text in ('The group performed at the concert festival.', 'De band gaf een optreden op het festival.',
                'Die Band ist beim Festival aufgetreten.', 'Le groupe se produit en concert sur scène.',
                'La banda actuó en un concierto en el festival.'):
            original='A music group.\nThe band recorded a studio album.\n'+text
            selected,ranges=paragraph_excerpt(original,'one episode',len('A music group.\n')+len(text),story_topic='live_performance')
            self.assertIn(text,selected)
            self.assertEqual(selected,'\n'.join(original[a:b] for a,b in ranges))

    def test_focused_original_evidence_and_semantic_novelty_are_both_required(self):
        from custom_components.djconnect.ask_dj import public_research as research
        stamp=datetime.now(UTC).isoformat()
        source=research.PublicSource('Wikipedia','Band','https://en.wikipedia.org/wiki/Band',
            'The band performed at the concert festival.', 'en',stamp,stamp,'CC-BY-SA-4.0',entity_id='Q1')
        projection=research.research_projection('Band',[source],{'state':'available'})
        focus=variety.select_focus(projection,'live_performance',())
        span=research.evidence_spans(projection['sources'][0])[0]
        review={'topic_preserved':True,'novel_episode':True,'claim_checks':[{'kind':'relationship',
            'text':'A performance.','quote':span['text'],'evidence_ids':[span['id']]}]}
        keys=variety.reviewed_episode(review,projection,focus,())
        self.assertEqual(keys,(variety.span_key(span['text']),))
        for override in ({'topic_preserved':False},{'novel_episode':False},{'claim_checks':[]}):
            self.assertFalse(variety.reviewed_episode({**review,**override},projection,focus,()))
        self.assertFalse(variety.reviewed_episode(review,projection,focus,(('members','Another wording',keys),)))
        self.assertIsNone(variety.select_focus(projection,'live_performance',(('live_performance','Prior',keys),)))


class StoryVarietyOwnerTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        owner.PublicArtistNarrationTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        owner.PublicArtistNarrationTest.tearDownClass()

    async def asyncSetUp(self):
        self.f=owner.PublicArtistNarrationTest()
        await self.f.asyncSetUp()
        self.initial_fact=self.f.fact
        self.clock=time.monotonic()
        self.f.manager._monotonic_source=lambda:self.clock
        self.f.session.planner.elapsed_time_source=lambda:self.clock
        self.f.session.presence_ledger.clock=lambda:self.clock
        self.old_fetch,self.old_model=self.f.fetch,self.f.model
        self.deny_novelty=False
        self.topic_missing=False
        self.answers=[]
        self.f.fetch=self.fetch
        self.f.model=self.model
        self.paragraphs={
            'live_performance':'Nora Vale 1 performed at the <i>Amber Festival</i> with Ada Reed.',
            'members':'Nora Vale 1 met band member Ada Reed at <i>Paper Hall</i>.',
            'recording':'Nora Vale 1 recorded <i>Paper Lanterns</i> with Ada Reed.',
            'background':'Nora Vale 1 formed the <i>Lantern Club</i> with Ada Reed.',
        }
        self.texts={
            'live_performance':'Op Amber Festival stond Nora Vale 1 samen met Ada Reed op het podium.',
            'members':'Nora Vale 1 ontmoette bandlid Ada Reed in Paper Hall.',
            'recording':'Voor Paper Lanterns nam Nora Vale 1 samen met Ada Reed op.',
            'background':'Nora Vale 1 richtte samen met Ada Reed de Lantern Club op.',
        }

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def fetch(self,fetch,url,**kwargs):
        status,body,final=await self.old_fetch(fetch,url,**kwargs)
        if status==200 and 'query' in json.loads(body):
            data=json.loads(body)
            parts=[] if self.topic_missing else list(self.paragraphs.values())
            data['query']['pages'][0]['extract']='<p>Nora Vale 1 is a music group.</p>'+''.join('<p>'+p+'</p>' for p in parts)
            return status,json.dumps(data),final
        return status,body,final

    async def model(self,hass,data,**kwargs):
        self.f.calls.append(data['text'])
        payload=json.loads(data['text'].split('\nData:\n')[1])
        if 'answer' not in payload:
            evidence=payload['public_music_research']
            topic=evidence['editorial_focus']['topic']
            self.answers.append((topic,self.texts[topic]))
            result=self.texts[topic]
        else:
            evidence=payload['evidence']['public_music_research']
            focus=evidence['editorial_focus']
            span=next(s for source in evidence['sources'] for s in source['evidence_spans'] if s['id'] in focus['episode_span_ids'])
            result=json.dumps({'review_schema':'source_id_review_v1','supported':True,'unsupported_claims':[],
                'language_ok':True,'style_ok':True,'topic_preserved':True,'novel_episode':not self.deny_novelty,
                'temporal_claims':[],'claim_checks':[{'text':payload['answer'],'kind':'relationship','evidence_ids':[span['id']]}]})
        return {'response':{'speech':{'plain':{'speech':result}}}}

    async def next_track(self,index):
        self.clock+=300
        self.f.catalog={**self.f.catalog,'uri':'spotify:track:'+str(index+101).zfill(22)}
        self.f.fact=replace(self.initial_fact,media_identity=self.f.catalog['uri'])
        stamp=(datetime.now(UTC)+timedelta(seconds=index*300)).isoformat()
        with patch.object(self.f.r,'_timestamp',lambda:stamp):
            await self.f.manager.async_update_playback_projection(owner_profile_id='profile-a',
                session_id=self.f.session.session_id,state='playing',media_identity=self.f.catalog['uri'],
                title='Fixture track '+str(index),artist=self.f.catalog['artist'],duration_ms=300000,position_ms=0)
            return await self.f.publish()

    async def test_four_observed_tracks_have_distinct_episodes_and_durable_replayable_flow(self):
        from custom_components.djconnect.public_artist_narration import admitted
        from custom_components.djconnect.session_conversation import query_service
        from custom_components.djconnect.session_speech import moment_projection
        moments=[]
        for index in range(4):
            moment=await self.next_track(index)
            self.assertIsNotNone(moment,self.f.debug)
            self.assertTrue(admitted(moment))
            self.assertTrue(moment_projection(self.f.session.broadcast,moment)['manual_allowed'])
            moments.append(moment)
        self.assertEqual([m.narration_acceptance.accepted.editorial_topic for m in moments],list(variety.TOPICS))
        self.assertEqual(len({k for m in moments for k in m.narration_acceptance.accepted.episode_keys}),4)
        self.assertEqual(len(self.f.calls),8)
        self.assertEqual(len({m.moment_id for m in moments}),4)
        self.assertEqual(self.f.session.presence_ledger.total_published,4)
        page=await query_service(self.f.hass,self.f.history).async_timeline_page('profile-a',self.f.session.session_id)
        stored={e['text'] for e in page['entries'] if e['kind']=='dj_moment'}
        self.assertTrue({m.content for m in moments}<=stored)
        self.assertFalse(any('spotify:track:' in prompt for prompt in self.f.calls))
        self.assertEqual(len(variety.published_context(self.f.session.moment_engine.moments,'Q1')),4)
        # Exhausted source paragraphs cannot buy a fifth paraphrase or another model call.
        self.assertIsNone(await self.next_track(4))
        self.assertEqual(len(self.f.calls),8)
        await self.f.manager.async_end(owner_profile_id='profile-a',session_id=self.f.session.session_id)
        await self.f.fixture.service.async_close()
        await self.f.fixture.service.async_initialize()
        archived=await query_service(self.f.hass,self.f.history).async_timeline_page('profile-a',self.f.session.session_id)
        entries=[e for e in archived['entries'] if e['kind']=='dj_moment']
        self.assertEqual({e['text'] for e in entries},{m.content for m in moments})
        self.assertTrue(all(e['sources'] and e['session_speech']['manual_allowed'] for e in entries))
        self.assertEqual(len(self.f.calls),8)

    async def test_rejected_semantic_repeat_does_not_advance_flow_or_episode_memory(self):
        self.assertIsNotNone(await self.next_track(0))
        before=tuple(self.f.session.planner.output.session_flow.items)
        self.deny_novelty=True
        self.assertIsNone(await self.next_track(1))
        self.assertEqual(self.f.debug['block_reason'],'artist_topic_or_novelty_unverified')
        self.assertEqual(self.f.session.planner.output.session_flow.items,before)
        self.assertEqual(len(variety.published_context(self.f.session.moment_engine.moments,'Q1')),1)
        self.deny_novelty=False
        next_moment=await self.next_track(2)
        self.assertEqual(next_moment.narration_acceptance.accepted.editorial_topic,'members')

    async def test_no_documented_topic_declines_without_raw_credit_or_extra_model_attempt(self):
        self.topic_missing=True
        self.assertIsNone(await self.next_track(0))
        self.assertEqual(self.f.debug['block_reason'],'fresh_artist_episode_unavailable')
        self.assertEqual(self.f.calls,[])
        self.assertEqual(self.f.session.presence_ledger.total_published,0)

    async def test_topic_and_evidence_receipts_cannot_be_forged_after_acceptance(self):
        from custom_components.djconnect import public_artist_narration as narration
        moment=await self.next_track(0)
        accepted=moment.narration_acceptance.accepted
        self.assertTrue(accepted.valid(time.monotonic()))
        for forged in (replace(accepted,editorial_topic='members'),replace(accepted,episode_keys=('a'*64,))):
            self.assertFalse(forged.valid(time.monotonic()))
            changed=replace(moment,narration_acceptance=replace(moment.narration_acceptance,accepted=forged))
            self.assertEqual(variety.published_context((changed,),'Q1'),())
        self.assertEqual(variety.published_context((moment,),'Q2'),())
        with patch.object(narration.time,'monotonic',return_value=accepted.expires_at+1):
            self.assertFalse(narration.admitted(moment))
            self.assertEqual(len(variety.published_context((moment,),'Q1')),1)

    async def test_planner_credit_cooldown_runs_before_ranking_and_never_widens_eligibility(self):
        from custom_components.djconnect.session_facts import recording_facts, ArtistImageIdentity
        catalog={**self.f.catalog,'artist_ids':['A'*22]}
        fact=recording_facts(catalog,{'id':'00000000-0000-0000-0000-000000000001',
            'relations':[{'type':'producer','target-type':'artist','artist':{'name':'Ada Reed'}}]})[0]
        fact=replace(fact,artwork_artist_identity=ArtistImageIdentity('spotify:artist:'+'A'*22,
            'Q1','Nora Vale 1','00000000-0000-0000-0000-000000000001'))
        args=dict(facts=(fact,),media_identity=fact.media_identity,used_keys=set(),locale='nl',allowed_intents=None,
            session_start_strategy=self.f.session.session_start_strategy,session_direction=self.f.session.session_direction.direction,
            selected_mood='energy',persona=self.f.session.dj_persona,remaining_seconds=300)
        memory=self.f.session.performance_memory
        self.assertIsNotNone(self.f.session.planner.select_qualified_current_fact(**args,performance_memory=memory))
        self.assertIsNone(self.f.session.planner.select_qualified_current_fact(**args,
            performance_memory=replace(memory,recent_qualified_topics=(('Q1','credits'),))))
        self.assertIsNotNone(self.f.session.planner.select_qualified_current_fact(**args,
            performance_memory=replace(memory,recent_qualified_topics=(('Q2','credits'),))))
        self.assertIsNone(self.f.session.planner.select_qualified_current_fact(**{**args,'facts':(replace(fact,license='invalid'),)},performance_memory=memory))

    async def test_missing_narration_owner_cannot_publish_raw_researchable_artist_seed(self):
        async def insight():
            return {'_qualified_facts':(self.f.fact,)}
        self.assertFalse(self.f.manager._narration_providers)
        result=await self.f.manager.async_process_track_started(owner_profile_id='profile-a',
            session_id=self.f.session.session_id,media_identity=self.f.catalog['uri'],insight_provider=insight,
            require_current_playback=True,allow_initial_facts=True)
        self.assertIsNone(result)
        self.assertEqual(self.f.session.presence_ledger.total_published,0)

    async def test_ambiguous_title_resolves_exact_qid_sitelink_without_name_guessing(self):
        from urllib.parse import parse_qs,urlsplit
        research=self.f.research
        calls=[]
        async def guard():
            pass
        async def network(fetch,url,**kwargs):
            calls.append(url)
            fetch.requests+=1
            args=parse_qs(urlsplit(url).query)
            if urlsplit(url).hostname=='www.wikidata.org':
                return 200,json.dumps({'entities':{'Q1':{'id':'Q1','sitelinks':{
                    language+'wiki':{'site':language+'wiki','title':'Nora Vale 1 (band)'} for language in ('nl','en')}}}}),url
            correct=args.get('titles')==['Nora Vale 1 (band)']
            return 200,json.dumps({'query':{'pages':[{'title':args['titles'][0],
                'pageprops':{'wikibase_item':'Q1' if correct else 'Q2','wikibase-shortdesc':'music group'},
                'extract':'<p>Nora Vale 1 is a music group.</p><p>Nora Vale 1 performed at a festival.</p>',
                'revisions':[{'revid':123}]}]}}),url
        with patch.object(research.PublicFetch,'request',network):
            async with research.PublicFetch(guard) as fetch:
                for locale in ('nl','en'):
                    result=await research.wikipedia(fetch,'Nora Vale 1','one documented concert',locale,
                        expected_roles=('Group',),expected_entity_id='Q1',original_paragraphs=True)
                    self.assertEqual(result.entity_id,'Q1')
                    self.assertIn('Nora_Vale_1_%28band%29',result.url)
        self.assertEqual(sum(urlsplit(u).hostname=='www.wikidata.org' for u in calls),1)
        self.assertEqual(len(calls),5)
        self.assertFalse(any('gsrsearch' in u for u in calls))

    async def test_wrong_sitelink_entity_cannot_qualify_an_ambiguous_article(self):
        research=self.f.research
        async def guard():
            pass
        async def wrong(fetch,url,**kwargs):
            fetch.requests+=1
            if 'wikidata.org' in url:
                return 200,json.dumps({'entities':{'Q1':{'id':'Q2','sitelinks':{
                    'nlwiki':{'site':'nlwiki','title':'Nora Vale 1 (band)'}}}}}),url
            return 200,json.dumps({'query':{'pages':[{'title':'Nora Vale 1',
                'pageprops':{'wikibase_item':'Q2','wikibase-shortdesc':'music group'},
                'extract':'Nora Vale 1 is a music group.','revisions':[{'revid':1}]}]}}),url
        with patch.object(research.PublicFetch,'request',wrong):
            async with research.PublicFetch(guard) as fetch:
                self.assertIsNone(await research.wikipedia(fetch,'Nora Vale 1','concert','nl',
                    expected_roles=('Group',),expected_entity_id='Q1'))
                self.assertEqual(fetch.requests,3)
