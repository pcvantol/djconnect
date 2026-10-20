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

    def test_reference_label_is_not_an_episode_focus_even_with_recording_keywords(self):
        from custom_components.djconnect.ask_dj import public_research as research
        stamp=datetime.now(UTC).isoformat()
        label='Music archive – Guides to studio sessions output and live concerts'
        for language,text in (('en','The band recorded “Paper Lanterns.”'),
                ('nl','De band maakte studio-opnamen.'),('de','Die Band machte Studioaufnahmen.'),
                ('fr','Le groupe a enregistré en studio.'),('es','La banda grabó en el estudio.')):
            original=label+'\n'+text
            source=research.PublicSource('Wikipedia','Band','https://en.wikipedia.org/wiki/Band',
                original,language,stamp,stamp,'CC-BY-SA-4.0',entity_id='Q1',
                original_text=original,paragraph_ranges=((0,len(label)),(len(label)+1,len(original))))
            projection=research.research_projection('Band',[source],{'state':'available'})
            focus=variety.select_focus(projection,'recording',())
            spans=research.evidence_spans(projection['sources'][0])
            self.assertIsNotNone(focus,(language,projection))
            self.assertEqual(focus['episode_span_ids'],[spans[1]['id']])
            used=(('recording','Synthetic prior',(variety.span_key(text),)),)
            self.assertIsNone(variety.select_focus(projection,'recording',used))
            self.assertIn(label,projection['sources'][0]['untrusted_excerpt'])


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

    async def test_used_episodes_then_link_label_choose_another_topic_without_publishing_label(self):
        self.paragraphs['recording']='Music archive – Guides to studio sessions output and live concerts'
        first=await self.next_track(0)
        second=await self.next_track(1)
        third=await self.next_track(2)
        self.assertTrue(all(m is not None for m in (first,second,third)),self.f.debug)
        self.assertEqual([m.narration_acceptance.accepted.editorial_topic for m in (first,second,third)],
            ['live_performance','members','background'])
        self.assertEqual(len(self.f.calls),6)
        self.assertEqual(self.f.session.presence_ledger.total_published,3)
        self.assertEqual(third.content,self.texts['background'])
        self.assertNotIn('Music archive',third.content)

    async def test_exact_artist_website_episode_uses_shared_fetch_and_persists_in_reopened_flow(self):
        from urllib.parse import urlsplit
        from custom_components.djconnect.session_conversation import query_service
        self.topic_missing=True
        original=self.f.fetch
        async def transport(fetch,url,**kwargs):
            if urlsplit(url).hostname not in {'www.wikidata.org','artist.example'}:
                return await original(fetch,url,**kwargs)
            await fetch.guard()
            self.assertLess(fetch.requests,fetch.maximum_requests)
            fetch.requests+=1
            self.f.fetch_owners.append(fetch)
            self.f.urls.append(url)
            if urlsplit(url).hostname=='www.wikidata.org':
                return 200,json.dumps({'entities':{'Q1':{'id':'Q1','lastrevid':123,
                    'claims':{'P856':[{'id':'Q1$'+'a'*36,'rank':'normal',
                        'mainsnak':{'property':'P856','datatype':'url','snaktype':'value',
                            'datavalue':{'value':'https://artist.example/'}}}]}}}}),url
            if url.endswith('/robots.txt'):
                return 200,'User-agent: *\nAllow: /',url
            return 200,('<html lang="en"><p>Nora Vale 1 recorded the album <i>Paper Lanterns</i> '
                        'in a studio with Ada Reed.</p></html>'),url
        self.f.fetch=transport
        moment=await self.next_track(0)
        self.assertIsNotNone(moment,self.f.debug)
        self.assertEqual(moment.content,self.texts['recording'])
        self.assertEqual(moment.narration_acceptance.accepted.editorial_topic,'recording')
        self.assertEqual(len(self.f.calls),2)
        self.assertLessEqual(len(self.f.urls),8)
        self.assertTrue(all(f is self.f.fetch_owners[0] for f in self.f.fetch_owners))
        source=next(s for s in moment.as_dict()['sources'] if s['provider']=='Artist website')
        self.assertEqual(source['official_site_reference'],{'basis':'wikidata_p856_v1',
            'entity_id':'Q1','claim_id':'Q1$'+'a'*36,'revision':123})
        self.assertEqual(source['usage_basis'],'public_page_short_reference')
        # Actual shared allowlist -> actual generated renderer's citation
        # validator, not a separately reconstructed citation fixture.
        import secrets
        import shutil
        import subprocess
        from pathlib import Path
        from custom_components.djconnect.display_admission import DisplayAdmissionState, DisplayOwnerBinding
        from custom_components.djconnect.display_projection import shared_snapshot
        state=DisplayAdmissionState(time.monotonic)
        owner_binding=DisplayOwnerBinding('profile-a',self.f.session.session_id,'entry','stamp',lambda:True)
        nonce=secrets.token_urlsafe(32)
        claim=state.create_claim(source='unit',browser_nonce=nonce)
        state.approve(owner=owner_binding,**{k:claim[k] for k in (
            'issuer_epoch','claim_id','browser_generation','code')},share={'mode':'create','consent':True})
        collected=state.collect(**{k:claim[k] for k in (
            'issuer_epoch','claim_id','browser_generation','claim_secret')},browser_nonce=nonce)
        snapshot=shared_snapshot(self.f.session,state._displays[collected['display_id']],state)
        card=next(m for m in snapshot['dj_moments'] if m['moment_id']==moment.moment_id)
        self.assertEqual(card['content'],moment.content)
        self.assertEqual(len(card['sources']),3)
        projected=next(s for s in card['sources'] if s['provider']=='Artist website')
        self.assertEqual(projected['official_site_reference'],source['official_site_reference'])
        for private in ('untrusted_excerpt','literal_passages','original_document_hash','content_hash','fetched_at'):
            self.assertNotIn(private,json.dumps(snapshot))
        node=shutil.which('node')
        self.assertIsNotNone(node)
        page=Path(__file__).resolve().parents[1]/'custom_components/djconnect/vibecast.html'
        script="""const fs=require('node:fs'),assert=require('node:assert/strict');
const page=fs.readFileSync(process.argv[1],'utf8');
const functions=page.match(/  function qualifiedCitations[\\s\\S]*?(?=  function cardFor)/)[0];
const validate=new Function('sources',functions+';return qualifiedCitations(sources)');
const sources=JSON.parse(fs.readFileSync(0,'utf8'));
assert.equal(validate(sources).length,3);
const bad=sources.map(s=>s.provider==='Artist website'?{...s,official_site_reference:undefined}:s);
assert.equal(validate(bad),null);"""
        import asyncio
        checked=await asyncio.to_thread(subprocess.run,[node,'-e',script,str(page)],input=json.dumps(card['sources']),
            capture_output=True,text=True)
        self.assertEqual(checked.returncode,0,checked.stderr)
        before=(len(self.f.calls),len(self.f.urls))
        await self.f.manager.async_end(owner_profile_id='profile-a',session_id=self.f.session.session_id)
        await self.f.fixture.service.async_close()
        await self.f.fixture.service.async_initialize()
        page=await query_service(self.f.hass,self.f.history).async_timeline_page('profile-a',self.f.session.session_id)
        entry=next(e for e in page['entries'] if e.get('moment_id')==moment.moment_id)
        self.assertEqual(entry['text'],moment.content)
        self.assertIn(source,entry['sources'])
        self.assertEqual((len(self.f.calls),len(self.f.urls)),before)

    async def test_website_identity_robots_redirect_scope_and_budget_fail_closed(self):
        from copy import deepcopy
        from custom_components.djconnect.official_artist_research import website_reference
        identity=('artist','https://www.wikidata.org/wiki/Q1','Nora Vale 1','Group','Q1')
        claim={'id':'Q1$'+'a'*36,'rank':'normal','mainsnak':{'property':'P856',
            'datatype':'url','snaktype':'value','datavalue':{'value':'https://artist.example/'}}}
        fixture={'id':'Q1','lastrevid':123,'claims':{'P856':[claim]}}
        class Fetch:
            maximum_requests=8
            def __init__(self,entity,*,start=0,robots=True,redirect=False,text=None):
                self.requests=start
                self.entity,self.allowed,self.redirect=entity,robots,redirect
                self.text=text or '<p>Nora Vale 1 recorded music in a studio.</p>'
                self.visited=[]
            async def request(self,url,**kwargs):
                self.requests+=1
                self.visited.append(url)
                if 'www.wikidata.org' in url:
                    return 200,json.dumps({'entities':{'Q1':self.entity}}),url
                return 200,self.text,('https://other.example/' if self.redirect else url)
            async def robots(self,url):
                self.requests+=1
                return self.allowed
        invalid=[]
        for change in ({'id':'Q2'},{'lastrevid':0},{'lastrevid':True},{'lastrevid':2**53}):
            invalid.append({**deepcopy(fixture),**change})
        for change in ({'rank':'deprecated'},{'qualifiers':{'P582':[]}},
                {'mainsnak':{**claim['mainsnak'],'snaktype':'somevalue'}},
                {'mainsnak':{**claim['mainsnak'],'datavalue':{'value':'https://127.0.0.1/'}}},
                {'id':'Q2$'+'a'*36}):
            invalid.append({**deepcopy(fixture),'claims':{'P856':[{**deepcopy(claim),**change}]}})
        second={**deepcopy(claim),'mainsnak':{**claim['mainsnak'],
            'datavalue':{'value':'https://another.example/'}}}
        invalid.append({**deepcopy(fixture),'claims':{'P856':[claim,second]}})
        for entity in invalid:
            fetch=Fetch(entity)
            self.assertIsNone(await website_reference(fetch,identity,'recording'),entity)
            self.assertEqual(fetch.requests,1)
        for options in ({'start':6},{'robots':False},{'redirect':True},
                {'text':'<p>Different artist recorded music in a studio.</p>'},
                {'text':'<p>Nora Vale 1 studio music guide</p>'},
                {'text':'<p>Nora Vale 1 recorded music '+('x'*600)+'.</p>'}):
            fetch=Fetch(fixture,**options)
            self.assertIsNone(await website_reference(fetch,identity,'recording'),options)
            self.assertLessEqual(fetch.requests,8)
        self.assertEqual(self.f.calls,[])

    async def test_optional_website_failure_keeps_wiki_but_never_hides_owner_withdrawal(self):
        from custom_components.djconnect import official_artist_research as official
        identity=('artist','https://www.wikidata.org/wiki/Q1','Nora Vale 1','Group','Q1')
        async def guard():
            return None
        async def network(fetch,url,**kwargs):
            return await self.f.fetch(fetch,url,**kwargs)
        with patch.object(self.f.research.PublicFetch,'request',network):
            for failure in (TimeoutError(),self.f.research.ResearchUnavailable('public_research_budget')):
                with patch.object(official,'website_reference',side_effect=failure):
                    sources=await official.artist_references('Nora Vale 1','One recording episode',
                        'nl',guard,identity=identity,roles=('Group',),topic='recording')
                self.assertEqual([s.provider for s in sources],['Wikipedia','Wikipedia'])
                self.assertTrue(all(s.entity_id=='Q1' for s in sources))
            with patch.object(official,'website_reference',side_effect=PermissionError('owner_withdrawn')):
                with self.assertRaises(PermissionError):
                    await official.artist_references('Nora Vale 1','One recording episode',
                        'nl',guard,identity=identity,roles=('Group',),topic='recording')
            with patch.object(official,'website_reference',side_effect=AssertionError('unqualified site lookup')):
                sources=await official.artist_references('Nora Vale 1','One recording episode',
                    'nl',guard,identity=(*identity[:4],'Q999'),roles=('Group',),topic='recording')
                self.assertEqual(sources,[])
        self.assertEqual(self.f.calls,[])

    async def test_actual_wikidata_info_request_and_language_only_qualifier_keep_website_identity(self):
        from copy import deepcopy
        from urllib.parse import parse_qs,urlsplit
        from custom_components.djconnect.official_artist_research import website_reference,language_qualifiers_only
        identity=('artist','https://www.wikidata.org/wiki/Q1','Nora Vale 1','Group','Q1')
        language={'property':'P407','snaktype':'value','datatype':'wikibase-item',
            'datavalue':{'type':'wikibase-entityid','value':{'entity-type':'item','id':'Q1860','numeric-id':1860}}}
        claim={'id':'Q1$'+'a'*36,'rank':'normal','qualifiers':{'P407':[language]},
            'mainsnak':{'property':'P856','snaktype':'value','datatype':'url',
                       'datavalue':{'type':'string','value':'https://artist.example/'}}}
        class Fetch:
            maximum_requests=8
            requests=0
            async def request(self,url,**kwargs):
                self.requests+=1
                if urlsplit(url).hostname=='www.wikidata.org':
                    props=parse_qs(urlsplit(url).query)['props'][0].split('|')
                    entity={'id':'Q1','claims':{'P856':[claim]}}
                    # The actual API omits revision metadata unless info was
                    # requested; do not make the fixture invent it for claims.
                    if 'info' in props:
                        entity['lastrevid']=123
                    return 200,json.dumps({'entities':{'Q1':entity}}),url
                return 200,'<p>Nora Vale 1 recorded an album in the studio.</p>',url
            async def robots(self,url):
                self.requests+=1
                return True
        fetch=Fetch()
        source=await website_reference(fetch,identity,'recording')
        self.assertIsNotNone(source)
        self.assertEqual(source.artist_identity,identity)
        self.assertEqual(source.entity_revision,123)
        self.assertEqual(fetch.requests,3)
        self.assertTrue(language_qualifiers_only(claim))
        for qualifiers in ({'P580':[]},{'P407':[]},{'P407':[{'snaktype':'somevalue'}]},
                {'P407':[None]},{'P407':[{**language,'datavalue':None}]},
                {'P407':[language],'P582':[]},
                {'P407':[{**language,'datavalue':{'type':'wikibase-entityid',
                    'value':{'entity-type':'item','id':'Q1860','numeric-id':1}}}]}):
            self.assertFalse(language_qualifiers_only({**deepcopy(claim),'qualifiers':qualifiers}),qualifiers)
        self.assertEqual(self.f.calls,[])

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
        self.assertEqual(len(calls),4)
        self.assertFalse(any(urlsplit(u).hostname=='en.wikipedia.org'
            and parse_qs(urlsplit(u).query).get('titles')==['Nora Vale 1'] for u in calls))
        self.assertFalse(any('gsrsearch' in u for u in calls))

    async def test_cached_exact_qid_titles_leave_room_for_web_page_within_shared_budget(self):
        """Real research/robots/budget; only HTTP replies are external fixtures."""
        from urllib.parse import parse_qs,urlsplit
        research=self.f.research
        calls=[]
        async def guard():
            pass
        async def network(fetch,url,**kwargs):
            await fetch.guard()
            if fetch.requests>=fetch.maximum_requests:
                raise research.ResearchUnavailable('public_research_budget')
            fetch.requests+=1
            calls.append(url)
            parsed=urlsplit(url)
            args=parse_qs(parsed.query)
            if parsed.path=='/robots.txt':
                return 200,'User-agent: *\nAllow: /',url
            if parsed.hostname=='www.wikidata.org':
                return 200,json.dumps({'entities':{'Q1':{'id':'Q1','sitelinks':{
                    language+'wiki':{'site':language+'wiki','title':'Nora Vale 1 (band)'}
                    for language in ('nl','en')}}}}),url
            if parsed.hostname in {'nl.wikipedia.org','en.wikipedia.org'}:
                correct=args.get('titles')==['Nora Vale 1 (band)']
                return 200,json.dumps({'query':{'pages':[{'title':args['titles'][0],
                    'pageprops':{'wikibase_item':'Q1' if correct else 'Q2',
                                 'wikibase-shortdesc':'music group'},
                    'extract':'<p>Nora Vale 1 is a music group.</p>',
                    'revisions':[{'revid':123}]}]}}),url
            if parsed.hostname=='html.duckduckgo.com' and parsed.path=='/html/':
                return 200,'<a href="https://artist.example.org/about">Discovery text is not evidence</a>',url
            if parsed.hostname=='artist.example.org' and parsed.path=='/about':
                return 200,('<html lang="en"><p>Nora Vale 1 is a music group. '
                    'Nora Vale 1 recorded Paper Lanterns with Ada Reed.</p></html>'),url
            raise AssertionError('Unexpected external fixture destination')
        with patch.object(research.PublicFetch,'request',network):
            sources,state=await research.research('Nora Vale 1','Band history','nl',guard,
                qualified_music=True,expected_roles=('Group',),expected_entity_id='Q1',
                allow_web=True,original_paragraphs=True)
        self.assertEqual({s.provider for s in sources},{'Wikipedia','Public web'})
        self.assertEqual(len(sources),3)
        web=next(s for s in sources if s.provider=='Public web')
        self.assertIn('recorded Paper Lanterns',web.text)
        self.assertNotIn('Discovery text',web.text)
        self.assertIn('https://artist.example.org/robots.txt',calls)
        self.assertEqual(calls[-1],'https://artist.example.org/about')
        self.assertEqual(state['requests'],8)
        self.assertEqual(len(calls),8)

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
