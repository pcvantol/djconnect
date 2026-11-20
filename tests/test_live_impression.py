"""Actual Runtime/SQLite/native/media/Ask/speech flow with synthetic source/model input.

These fixtures prove software boundaries; they are not real-public-source or
live-model/editorial/native-device acceptance.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_personal_dj_narration_public_artist as base_tests


def accepted_text(fact, *, locale='nl',persona='home_dj',mood='energy'):
    from PIL import Image
    from custom_components.djconnect import live_impression as li
    pixels=io.BytesIO()
    Image.new('RGB',(1024,768),(30,65,120)).save(pixels,format='PNG')
    pixels=pixels.getvalue()
    revision=hashlib.sha256(pixels).hexdigest()
    photo={'photo_id':'photo-fixture','revision':revision,'caption':'Nora Vale 1 performed at Fixture Hall, Fixture City, 2020-06-02.',
        'alt_text':{language:'Nora Vale 1 — Fixture Hall' for language in li.LANGUAGES},'width':1024,'height':768,
        'source_url':'https://commons.wikimedia.org/wiki/File:Nora_Vale_concert_fixture.png',
        'author':'Fixture Photographer','credit':'Fixture Photographer · CC BY-SA 4.0',
        'license':'CC-BY-SA-4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/'}
    payload={'schema_version':1,'event':{'event_id':'event-fixture','artist':'Nora Vale 1','date':'2020-06-02',
        'date_precision':'day','venue':'Fixture Hall','city':'Fixture City','relationship':'same_artist'},'photos':[photo]}
    title='Een avond in Fixture Hall'
    lead='Nora Vale 1 speelde in Fixture Hall. De foto bewaart die avond.'
    text=lead+' In Fixture City stond de artiest op 2 juni 2020 op het podium. Dit opgeslagen verhaal en deze foto gaan over dat optreden, ook wanneer er een ander nummer speelt.'
    sources=[{'provider':'Wikimedia Commons','title':'Original concert fixture','url':photo['source_url'],'license':photo['license']}]
    reference={'photo_id':photo['photo_id'],'revision':revision,'source_url':photo['source_url'],
        'url':'https://upload.wikimedia.org/wikipedia/commons/a/ab/fixture.png',
        'original_url':'https://upload.wikimedia.org/wikipedia/commons/a/ab/fixture.png',
        'license':photo['license'],'license_url':photo['license_url'],'commons_revision':'a'*40}
    values=(fact,title,lead,text,li._json(payload),li._json(sources),li._json(reference),locale,persona,mood)
    proof=li.Acceptance(*values,li._seal(*values))
    return li.LiveImpressionText(proof,pixels,'image/png')


class LiveImpressionTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # The shared harness replaces Runtime for its disposable HA stubs.
        # Restore both module identities so later HTTP fixtures catch the same
        # revision exception classes their manager actually raises.
        import sys
        cls._prior_runtime=sys.modules.get('custom_components.djconnect.session_runtime')
        base_tests.PublicArtistNarrationTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        import sys
        import custom_components.djconnect as package
        base_tests.PublicArtistNarrationTest.tearDownClass()
        if cls._prior_runtime is None:
            sys.modules.pop('custom_components.djconnect.session_runtime',None)
        else:
            sys.modules['custom_components.djconnect.session_runtime']=cls._prior_runtime
        if cls._prior_runtime is None:
            package.__dict__.pop('session_runtime',None)
        else:
            package.session_runtime=cls._prior_runtime
    asyncSetUp=base_tests.PublicArtistNarrationTest.asyncSetUp
    asyncTearDown=base_tests.PublicArtistNarrationTest.asyncTearDown

    async def publish_live(self, *, mutate=None):
        async def provider(brief,guard):
            guard()
            text=accepted_text(brief.fact,locale=brief.locale,persona=brief.persona,mood=brief.mood)
            if mutate is not None:
                text=mutate(text)
            return text
        self.manager.connect_narration('profile-a',self.session.session_id,provider,lambda:None)
        self.manager._hass=self.hass
        from custom_components.djconnect.image_proxy import ManagedSessionImages
        registry=ManagedSessionImages()
        self.hass.data['djconnect']['session_images']=registry
        self.addCleanup(registry.close)
        self.hass.async_create_task=asyncio.create_task
        async def insight():
            return {'_qualified_facts':(self.fact,)}
        return await self.manager.async_process_track_started(owner_profile_id='profile-a',
            session_id=self.session.session_id,media_identity=self.catalog['uri'],insight_provider=insight,
            require_current_playback=True,allow_initial_facts=True)

    async def test_actual_commit_native_image_original_ask_and_restart_replay(self):
        from custom_components.djconnect import live_impression as li, session_artwork as art,session_speech
        from custom_components.djconnect.ask_dj.service import _live_reference
        from custom_components.djconnect.ask_dj.dialogue import model_source
        from custom_components.djconnect.session_conversation import query_service
        moment=await self.publish_live()
        self.assertIsNotNone(moment)
        self.assertTrue(li.admitted(moment))
        wire=next(m for m in self.session.broadcast.as_dict()['dj_moments'] if m['moment_id']==moment.moment_id)
        self.assertEqual(wire['type'],'live_impression')
        self.assertEqual(wire['knowledge_intent']['type'],'live_impression')
        self.assertFalse(hasattr(moment.live_impression,'pixels'))
        self.assertNotIn('original_url',json.dumps(wire))
        self.assertNotIn('commons_revision',json.dumps(wire))
        a=next(a for a in self.session.broadcast.native_delivery()['admissions'] if a['moment_id']==moment.moment_id)
        self.assertEqual(a['qualification'],'qualified')
        self.assertIsNone(a['source_expires_at'])
        self.assertFalse(a['requires_spotify_attribution'])
        # New private source/media rights never become a passive or receiver grant.
        _,receiver=self.session.broadcast.subscribe_with_broadcast_token(self.session.broadcast.broadcast_token,lambda event:None)
        self.assertNotIn('live_impression',json.dumps(receiver))
        from custom_components.djconnect.passive_contribution import contribution
        import time
        passive,_=contribution(self.session.broadcast,time.monotonic(),projection_version=3)
        self.assertNotEqual(passive.get('moment_id') if passive else None,moment.moment_id)
        context=SimpleNamespace(profile_id='profile-a')
        photo=wire['live_impression']['photos'][0]
        media=await art.prepare(self.hass,self.runtime,context,session_id=self.session.session_id,
            target={'moment_id':moment.moment_id,'photo_id':photo['photo_id']},contract_version=3)
        self.assertEqual(media['artwork']['state'],'ready',media)
        result,status=await art.handle_prepare(self.hass,{**self.identity,'contract_version':3,
            'session_id':self.session.session_id,'targets':[{'moment_id':moment.moment_id,'photo_id':photo['photo_id']}]},headers=self.headers)
        self.assertEqual(status,200,result)
        self.assertEqual(result['session_media'][0]['schema_version'],3)
        self.assertEqual(result['session_media'][0]['artwork']['state'],'ready',result)
        self.assertEqual(media['artwork']['media_revision'],photo['revision'])
        asset_id=media['artwork']['url'].rsplit('/',1)[-1]
        body=await art.image(self.hass,context,self.session.session_id,asset_id,runtime=self.runtime)
        self.assertEqual(hashlib.sha256(body[0]).hexdigest(),photo['revision'])
        other=await art.image(self.hass,SimpleNamespace(profile_id='profile-b'),self.session.session_id,asset_id,runtime=self.runtime)
        self.assertIsNone(other)
        query=query_service(self.hass,self.history)
        page=await query.async_timeline_page('profile-a',self.session.session_id)
        entries=[e for e in page['entries'] if e.get('moment_id')==moment.moment_id]
        self.assertEqual(len(entries),1)
        entry=entries[0]
        self.assertEqual(entry['archive_basis'],li.BASIS)
        self.assertEqual(entry['live_impression'],wire['live_impression'])
        self.assertNotIn('live_impression_reference',entry)
        self.assertEqual(entry['title'],moment.title)
        self.session.broadcast.owner_speech_output=lambda:'text_only'
        speech=session_speech.moment_projection(self.session.broadcast,moment,autoplay=True)
        self.assertTrue(speech['manual_allowed'],speech)
        self.assertFalse(speech['autoplay_eligible'])
        self.assertEqual(speech['moment_type'],'live_impression')
        await self.manager.async_update_playback_projection(owner_profile_id='profile-a',session_id=self.session.session_id,
            state='playing',media_identity='spotify:track:'+'B'*22,title='Other track',artist='Other artist',duration_ms=300000,position_ms=0)
        original=await _live_reference(self.manager,'profile-a',{'session_id':self.session.session_id,'moment_id':moment.moment_id})
        self.assertEqual(original['live_impression']['event']['event_id'],'event-fixture')
        self.assertEqual(model_source(original)['event']['artist'],'Nora Vale 1')
        from custom_components.djconnect.ask_dj.public_research import subject_for_question
        selected=SimpleNamespace(source_context=model_source(original),frame=SimpleNamespace(subjects=[]),reset_topic=False)
        self.assertEqual(subject_for_question('Vertel meer over die artiest',selected)[0],'Nora Vale 1')
        await self.manager.async_end(owner_profile_id='profile-a',session_id=self.session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        query=query_service(self.hass,self.history)
        reopened=await query.async_timeline_page('profile-a',self.session.session_id)
        retained=next(e for e in reopened['entries'] if e.get('moment_id')==moment.moment_id)
        self.assertEqual(retained['text'],moment.content)
        self.assertEqual(retained['live_impression'],wire['live_impression'])
        self.assertTrue(retained['session_speech']['manual_allowed'],retained['session_speech'])
        descriptor,guard=await session_speech.resolve_retained(self.hass,self.history,'profile-a',
            {'session_id':self.session.session_id,'entry_id':retained['entry_id']})
        self.assertEqual(guard.processor_basis,'qualified_dialogue_v1')
        self.assertEqual(''.join(s['text'] for s in descriptor['segments']),moment.content)
        destination=os.getenv('DJCONNECT_LIVE_FIXTURE_OUTPUT')
        if destination:
            Path(destination).write_text(json.dumps({'moment':wire,'history':retained,'media':media,'speech':speech},indent=2))
        registry=self.hass.data['djconnect'].get('session_images')
        if registry:
            registry.close()

    async def test_forged_payload_cannot_publish_or_change_original_photo(self):
        from custom_components.djconnect import live_impression as li
        good=accepted_text(self.fact)
        changed=replace(good.accepted,payload_json=good.accepted.payload_json.replace('event-fixture','event-other'))
        self.assertFalse(changed.valid())
        moment=await self.publish_live(mutate=lambda _:li.LiveImpressionText(changed,good.pixels,good.mime))
        self.assertIsNone(moment)

    async def test_schema_rejects_unknown_rights_future_event_wrong_hash_and_duplicates(self):
        from custom_components.djconnect import live_impression as li
        live=json.loads(accepted_text(self.fact).accepted.payload_json)
        self.assertIsNotNone(li.checked(live))
        value=deepcopy(live)
        value['schema_version']=True
        self.assertIsNone(li.checked(value))
        for mutate in (lambda v:v['event'].update(date='2999-01-01'),
                       lambda v:v['photos'][0].update(license='unknown'),
                       lambda v:v['photos'][0].update(revision='not-a-digest'),
                       lambda v:v['photos'].append(deepcopy(v['photos'][0])),
                       lambda v:v['photos'][0].update(width=99999)):
            value=deepcopy(live)
            mutate(value)
            self.assertIsNone(li.checked(value))

    async def test_original_refetch_rejects_other_bytes_without_changing_text(self):
        from custom_components.djconnect import live_impression_media as media
        text=accepted_text(self.fact)
        reference=json.loads(text.accepted.reference_json)
        async def guard():
            pass
        photo=media.artist_photo.Candidate('File:Nora Vale concert fixture.png',reference['url'],1024,768,
            'Fixture Photographer','Original photo','Fixture Photographer · CC BY-SA 4.0',
            reference['license'],reference['license_url'],reference['commons_revision'],True,reference['original_url'])
        caption='Nora Vale 1 performed at Fixture Hall, Fixture City, 2020-06-02.'
        reference['source_metadata_revision']=media.metadata_revision(photo,caption,'2020-06-02')
        data={'query':{'pages':[{'title':photo.title,'imageinfo':[{'extmetadata':{
            'ImageDescription':{'value':caption},'DateTimeOriginal':{'value':'2020-06-02'}}}]}]}}
        async def request(*args,**kwargs):
            return 200,json.dumps(data),'https://commons.wikimedia.org/'
        async def image(*args,**kwargs):
            return b'changed','image/png'
        with patch.object(media.EventPublicFetch,'request',request),patch.object(media.EventPublicFetch,'image',image),\
             patch.object(media.artist_photo,'candidates',return_value=[photo]):
            with self.assertRaisesRegex(ValueError,'bytes_changed'):
                await media.refetch(reference,guard)
        self.assertTrue(text.accepted.valid())

    async def test_current_speech_requires_original_retained_row_and_guard(self):
        from custom_components.djconnect import session_speech
        moment=await self.publish_live()
        reference={'session_id':self.session.session_id,'moment_id':moment.moment_id}
        descriptor,guard=await session_speech.resolve_moment(self.hass,'profile-a',reference,history=self.history)
        self.assertTrue(descriptor['manual_allowed'])
        self.assertEqual(guard.processor_basis,'qualified_dialogue_v1')
        from unittest.mock import AsyncMock
        with patch.object(self.manager._historical_projections,'async_entry_record',AsyncMock(return_value=None)):
            with self.assertRaises(PermissionError):
                await session_speech.resolve_moment(self.hass,'profile-a',reference,history=self.history)
        self.fixture.service.history_retention_epoch=getattr(self.fixture.service,'history_retention_epoch',0)+1
        with self.assertRaises(PermissionError):
            guard()

    async def test_discovery_checks_original_metadata_and_does_not_use_upload_date(self):
        from custom_components.djconnect import live_impression_research as research
        from custom_components.djconnect import artist_photo
        from unittest.mock import AsyncMock
        title='File:Nora concert fixture.jpg'
        info={'url':'https://upload.wikimedia.org/wikipedia/commons/a/ab/Nora.jpg',
            'descriptionurl':artist_photo.file_url(title),'width':1600,'height':1200,
            'mime':'image/jpeg','mediatype':'BITMAP','sha1':'a'*40,
            'extmetadata':{k:{'value':v} for k,v in {'Artist':'Fixture creator','Credit':'Original photograph',
                'LicenseShortName':'CC BY 4.0','LicenseUrl':'https://creativecommons.org/licenses/by/4.0/',
                'ImageDescription':'Nora Vale 1 Live at Fixture Hall, Fixture City.',
                'DateTime':'2026-11-19'}.items()}}
        data={'query':{'pages':[{'title':title,'ns':6,'imageinfo':[info]}]}}
        fetch=SimpleNamespace(request=AsyncMock(return_value=(200,json.dumps(data),'https://commons.wikimedia.org/w/api.php')))
        candidates=await research.discover(fetch,'Nora Vale 1')
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0][2],'')  # Upload metadata never dates the event.
        self.assertIn('generator=search',fetch.request.call_args.args[0])
        for field,value in [('LicenseShortName','unknown'),('ImageDescription','Other Artist Live at Fixture Hall'),
            ('ImageDescription','Nora Vale 1 at the meet and greet of her concert at Fixture Hall'),
            ('ImageDescription','Nora Vale 1 backstage at Fixture Hall concert'),
            ('ImageDescription','Nora Vale 1 concert soundcheck at Fixture Hall')]:
            bad=deepcopy(data)
            bad['query']['pages'][0]['imageinfo'][0]['extmetadata'][field]['value']=value
            fetch.request.return_value=(200,json.dumps(bad),'https://commons.wikimedia.org/w/api.php')
            self.assertEqual(await research.discover(fetch,'Nora Vale 1'),[])

    async def test_event_identity_accepts_only_original_date_and_fetched_location(self):
        from custom_components.djconnect import live_impression_research as research
        sample=accepted_text(self.fact)
        payload=json.loads(sample.accepted.payload_json)
        data={'date':'2020-06-02','date_precision':'day','venue':'Fixture Hall','city':'Fixture City',
            'title':sample.accepted.title,'lead':sample.accepted.lead,'text':str(sample),
            'alt_text':payload['photos'][0]['alt_text']}
        event=research.event_candidate(data,subject='Nora Vale 1',caption='Nora Vale 1 at Fixture Hall.',
            captured_date='2020-06-02',evidence='Nora Vale 1 performed in Fixture City at Fixture Hall.')
        self.assertEqual(event['date'],'2020-06-02')
        data['date']='2026-11-19'
        self.assertIsNone(research.event_candidate(data,subject='Nora Vale 1',caption='Nora Vale 1 at Fixture Hall.',
            captured_date='2020-06-02',evidence='Nora Vale 1 in Fixture City at Fixture Hall.'))

    async def test_failed_live_model_cannot_buy_another_writer_reviewer_pair(self):
        from custom_components.djconnect.narration_brief import qualify
        from custom_components.djconnect import public_artist_narration as artist
        from custom_components.djconnect import live_impression_research as live
        from unittest.mock import AsyncMock
        brief=qualify(self.fact,locale='nl',persona='home_dj',mood='energy',seed='Een bestaande brongebonden bijdrage.')
        calls=[]
        async def ha_model(*args,**kwargs):
            calls.append(args)
            return {'response':{'speech':{'plain':{'speech':'draft'}}}}
        async def failed(brief,*,ask,admission,debug=None,fetch=None):
            await ask('one bounded draft')
            return None
        fallback=AsyncMock(return_value='must never be called')
        with patch.object(live,'realize',failed),patch.object(artist,'realize',fallback),\
             patch.object(self.pipeline,'_assist_context',return_value={'agent_id':'fixture-agent'}),\
             patch.object(self.pipeline,'call_conversation_process_with_agent_retry',ha_model):
            result=await self.pipeline.realize_session_narration(self.hass,narration=brief,admission=lambda:None,
                fallback_text=brief.seed,conf=self.runtime.config)
        self.assertEqual(result,brief.seed)
        self.assertEqual(len(calls),1)
        fallback.assert_not_called()


    async def test_same_pixels_changed_source_metadata_withdraws_only_image(self):
        from custom_components.djconnect import live_impression_media as media
        from unittest.mock import AsyncMock
        sample=accepted_text(self.fact)
        reference=json.loads(sample.accepted.reference_json)
        photo=media.artist_photo.Candidate('File:Nora Vale concert fixture.png',reference['url'],1024,768,
            'Fixture Photographer','Original photo','Fixture Photographer · CC BY-SA 4.0',
            reference['license'],reference['license_url'],reference['commons_revision'],True,reference['original_url'])
        caption=json.loads(sample.accepted.payload_json)['photos'][0]['caption']
        reference['source_metadata_revision']=media.metadata_revision(photo,caption,'2020-06-02')
        data={'query':{'pages':[{'title':photo.title,'imageinfo':[{'extmetadata':{
            'ImageDescription':{'value':caption},'DateTimeOriginal':{'value':'2020-06-02'}}}]}]}}
        async def guard():
            pass
        image=AsyncMock(return_value=(sample.pixels,sample.mime))
        with patch.object(media.EventPublicFetch,'request',AsyncMock(return_value=(200,json.dumps(data),'https://commons.wikimedia.org/'))), \
             patch.object(media.EventPublicFetch,'image',image), \
             patch.object(media.artist_photo,'candidates',return_value=[photo]):
            self.assertEqual(await media.refetch(reference,guard),(sample.pixels,sample.mime))
        for field,value in [('ImageDescription','Corrected: a different concert'),('DateTimeOriginal','2021-06-02')]:
            changed=deepcopy(data)
            changed['query']['pages'][0]['imageinfo'][0]['extmetadata'][field]['value']=value
            image.reset_mock()
            with patch.object(media.EventPublicFetch,'request',AsyncMock(return_value=(200,json.dumps(changed),'https://commons.wikimedia.org/'))), \
                 patch.object(media.EventPublicFetch,'image',image), \
                 patch.object(media.artist_photo,'candidates',return_value=[photo]):
                with self.assertRaisesRegex(PermissionError,'metadata_withdrawn'):
                    await media.refetch(reference,guard)
                image.assert_not_awaited()
            self.assertTrue(sample.accepted.valid())
            self.assertEqual(str(sample),sample.accepted.text)


    async def test_future_exact_original_date_cannot_be_coarsened_to_current_year(self):
        from datetime import UTC, datetime, date
        from custom_components.djconnect import live_impression_research as research
        sample=accepted_text(self.fact)
        data={'date':'2026','date_precision':'year','venue':'Fixture Hall','city':'Fixture City',
            'title':sample.accepted.title,'lead':sample.accepted.lead,'text':str(sample),
            'alt_text':json.loads(sample.accepted.payload_json)['photos'][0]['alt_text']}
        clock=SimpleNamespace(now=lambda tz:datetime(2026,6,1,tzinfo=UTC))
        caption='Nora Vale 1 Live at Fixture Hall, Fixture City.'
        with patch.object(research,'datetime',clock):
            self.assertIsNone(research.event_candidate(data,subject='Nora Vale 1',caption=caption,
                captured_date='2026-06-02 18:00'))
            self.assertIsNone(research.event_candidate(data,subject='Nora Vale 1',caption=caption+' 2026-06-02',
                captured_date=''))
            self.assertIsNotNone(research.event_candidate(data,subject='Nora Vale 1',caption=caption,
                captured_date='2026-05-31 18:00'))
        self.assertFalse(research.original_date_not_future('2026-06-02',today=date(2026,6,1)))
        self.assertTrue(research.original_date_not_future('2026-05-31',today=date(2026,6,1)))

    def test_tracked_actual_ha_http_receipt_binds_final_source_and_declared_fixture_scope(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        proof=json.loads((root/'examples/client_contracts/live_impression_v1/actual-ha-wire.json').read_text())
        self.assertTrue(proof['source_before_after_equal'])
        self.assertEqual(len(proof['source_pins']),318)
        for path,digest in proof['source_pins'].items():
            self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(),digest,path)
        self.assertEqual(hashlib.sha256((root/proof['harness']).read_bytes()).hexdigest(),proof['harness_sha256'])
        raw=proof['receipt']
        self.assertTrue(raw['source_unchanged'])
        self.assertEqual(len(raw['source_files_sha256']),proof['raw_selected_product_count'])
        extension=raw['extension']
        self.assertEqual(extension['state'],'PASS')
        self.assertEqual(extension['declared_synthetic_source_and_narration_calls'],1)
        self.assertEqual((extension['real_model_calls'],extension['real_public_source_calls']),(0,0))
        self.assertTrue(extension['ordinary_paired_media_prepare3'])
        self.assertTrue(extension['ordinary_paired_local_speech_prepare3'])
        self.assertTrue(extension['original_story_photo_event_survive_restart'])
        self.assertEqual(extension['native_or_installed_acceptance'],'NOT_RUN')
