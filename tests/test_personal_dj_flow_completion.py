"""Actual qualified production and SQLite reopening, not relabelled Moment seeds."""
import time
import unittest
from unittest.mock import patch

from tests import test_session_conversation_history as fixtures
from tests.context_variation_fixtures import source


class PublishedFlowCompletionTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = fixtures.SessionConversationHistoryTest()
        await self.fixture.asyncSetUp()
        self.hass, _, self.history, _, _ = await self.fixture.transport_fixture()
        self.r = self.fixture.runtime
        self.manager = self.fixture.manager
        self.clock = [time.monotonic()]
        self.manager._monotonic_source = lambda: self.clock[0]

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def test_actual_source_families_and_silence_survive_reopen_and_search_beyond250(self):
        from custom_components.djconnect import session_facts
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.session_conversation import async_metadata_archive_admission, query_service
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        await storage.async_upsert_music_account('source-account', 'source-spotify',
            kind=MusicAccountKind.PERSONAL, display_name='Synthetic source account',
            linked_profile_ids=frozenset({'profile-a'}), provider_account_id='fixture-provider-owner')
        captured = {'backend_id': 'source-spotify', 'music_account_id': 'source-account',
                    'provider_entry_id': 'source-entry', 'provider_account_id': 'fixture-provider-owner'}
        session = await self.manager.async_start(owner_profile_id='profile-a', locale='nl',
            selected_mood='groove', music_backend='spotify_direct', history_source_context=captured)
        async def realize(brief, guard):
            # External expression boundary fixture, not a real-LLM style claim.
            guard()
            return brief.seed
        async def archive(binding):
            return await async_metadata_archive_admission(self.hass, 'profile-a', binding, lambda: None)
        self.manager.connect_narration('profile-a', session.session_id, realize, lambda: None,
                                      archive_admission=archive)
        moments = []
        for number, family in enumerate(('description', 'edition', 'credits', 'genre', 'description')):
            session = await self.manager.async_get_active('profile-a')
            # Exercise existing no-provider CC0 history compatibility here;
            # registered artist stories may no longer publish bare seeds.
            # Their sealed research + image/reopen chain lives in the owning
            # PublicArtistNarrationTest, without weakening either admission.
            if family == 'description':
                self.manager._narration_providers.pop('profile-a', None)
            else:
                self.manager.connect_narration('profile-a', session.session_id, realize, lambda: None,
                                              archive_admission=archive)
            if number == 4:
                # Real silence publication/storage, enough to exercise the
                # scan cursor independently of visible-page size.
                for _ in range(260):
                    silence = session.moment_engine.create_silence(session_id=session.session_id,
                        selected_mood=session.selected_mood, persona=session.dj_persona,
                        locale=session.locale, reason='private_test_reason')
                    self.assertTrue(await self.manager._async_persist_moment(session, silence))
                    session.publish_moment(silence)
            catalog, fact = source(family if family in {'description', 'edition'} else 'birth', number)
            if family == 'credits':
                # This bulk pagination test isolates CC0 metadata retention,
                # not researched-story admission. An absent contributor MBID
                # cannot enter public research; the researched producer test
                # independently exercises sealed acceptance and SQLite replay.
                fact = session_facts.recording_facts(catalog, {
                    'id': '00000000-0000-0000-0000-000000000003', 'title': catalog['title'],
                    'artist-credit': [{'artist': {'name': catalog['artist']}}],
                    'relations': [{'target-type': 'artist', 'type': 'producer',
                        'artist': {'name': 'Actual credit fixture'}}]})[0]
                from custom_components.djconnect.narration_brief import qualify
                from custom_components.djconnect.public_artist_narration import can_research
                brief = qualify(fact, locale='nl', persona='radio_dj', mood='groove', seed='Storage boundary fixture')
                self.assertIsNotNone(brief)
                self.assertFalse(can_research(brief))
            elif family == 'genre':
                fact = session_facts.observed_genre_facts({
                    'source': 'spotify_playback_status', 'backend': 'spotify_direct', 'is_playing': True,
                    'media_identity': catalog['uri'], 'title': catalog['title'], 'artist': catalog['artist'],
                    'artist_ids': ['Z'*22], 'genres': ['ambient'], 'genre_source_expires_at': time.monotonic()+1800},
                    media_identity=catalog['uri'], title=catalog['title'], artist=catalog['artist'])[0]
            self.clock[0] += 300
            await self.manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=session.session_id,
                state='playing', media_identity=catalog['uri'], title=catalog['title'], artist=catalog['artist'],
                album=catalog['album_name'], duration_ms=600000, position_ms=0)
            async def provider():
                return {'_qualified_facts': (fact,)}
            moment = await self.manager.async_process_track_started(owner_profile_id='profile-a', session_id=session.session_id,
                media_identity=catalog['uri'], insight_provider=provider, require_current_playback=True, allow_initial_facts=True)
            self.assertIsNotNone(moment, family)
            self.assertIs(moment.source_fact, fact)
            moments.append(moment)
            self.assertIn(moment.moment_id, {m.moment_id for m in session.broadcast.state.dj_moments})
        self.assertEqual([m.moment_type.value for m in moments], ['artist', 'album', 'track', 'genre', 'artist'])
        await self.manager.async_end(owner_profile_id='profile-a', session_id=session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        query = query_service(self.hass, self.history)
        transaction_counts = []
        original = self.fixture.service.async_in_transaction
        count = [0]
        async def counted(*args, **kwargs):
            count[0] += 1
            return await original(*args, **kwargs)
        before_read = await self.fixture.repo.async_session_record(session.session_id)
        with patch.object(self.fixture.service, 'async_in_transaction', counted):
            for size in (10, 50):
                count[0] = 0
                await query.async_timeline_page('profile-a', session.session_id, limit=size)
                transaction_counts.append(count[0])
        self.assertEqual(transaction_counts[0], transaction_counts[1])
        self.assertLessEqual(max(transaction_counts), 12)
        cursor, entries, pages = '', [], 0
        while True:
            page = await query.async_timeline_page('profile-a', session.session_id, limit=50, cursor=cursor)
            entries.extend(page['entries'])
            pages += 1
            cursor = page['next_cursor']
            if not cursor:
                break
        self.assertGreater(pages, 5)
        # Five genuinely accepted playback observations, five spoken Moments
        # and260silences; no synthetic relabelled contribution types.
        self.assertEqual(len(entries), 270)
        self.assertEqual(len({e['entry_id'] for e in entries}), 270)
        self.assertEqual([e['order'] for e in entries], sorted(e['order'] for e in entries))
        by_id = {e['moment_id']: e for e in entries if e.get('moment_id')}
        for moment in moments:
            retained = by_id[moment.moment_id]
            self.assertEqual(retained['text'], moment.content)
            self.assertTrue(retained['session_speech']['manual_allowed'])
        self.assertTrue(all(e['text'] is None and not e['speech_available']
                            for e in entries if e['kind'] == 'dj_silence'))
        first = await query.async_search_entries('profile-a', session.session_id, 'Nora Vale 5')
        self.assertEqual(first['matches'], [])
        self.assertIsNotNone(first['next_cursor'])
        last = await query.async_search_entries('profile-a', session.session_id, 'Nora Vale 5', cursor=first['next_cursor'])
        self.assertEqual([e['moment_id'] for e in last['matches'] if e.get('moment_id')], [moments[-1].moment_id])
        self.assertEqual(sum(e['kind'] == 'playback_observed' for e in last['matches']), 1)
        self.assertTrue(last['complete'])
        record = await self.fixture.repo.async_session_record(session.session_id)
        self.assertEqual(record['summary']['moments_published']['value'], 5)
        self.assertEqual(record['revision'], before_read['revision'])
        body_bytes = await self.fixture.service.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT SUM(length(body)) FROM djconnect_session_entries WHERE session_id=?', (session.session_id,))[0])
        self.assertLess(body_bytes, 256*1024)
        import os
        import json
        from pathlib import Path
        if capture := os.environ.get('DJC_FLOW_CAPTURE_DIR'):
            (Path(capture)/'qualified-flow-reopen.json').write_text(json.dumps({
                'entries': len(entries), 'spoken_moments': 5, 'silences': 260, 'accepted_playback_observations': 5,
                'page_count': pages, 'query_transactions_page10_and50': transaction_counts,
                'retained_body_bytes': body_bytes, 'read_revision_unchanged': True,
                'source_boundary': 'Synthetic external metadata and expression; actual Planner/Knowledge/Moment/SQLite/query/reopen.'}, indent=2)+'\n')
        self.assertNotIn('private_test_reason', str(entries))
        await self.fixture.repo.async_withdraw_source_entry('source-entry')
        withdrawn = await query.async_open_entry('profile-a', session.session_id, by_id[moments[1].moment_id]['entry_id'])
        self.assertEqual(withdrawn['entry']['order'], by_id[moments[1].moment_id]['order'])
        self.assertIsNone(withdrawn['entry']['text'])
        self.assertFalse(withdrawn['entry']['speech_available'])

    async def test_actual_published_credit_recommendation_survives_reopen_without_fake_play(self):
        from dataclasses import replace
        from custom_components.djconnect import session_facts, session_speech
        from custom_components.djconnect.pipeline import realize_session_narration
        from custom_components.djconnect.narration_brief import qualify
        session = await self.manager.async_start(owner_profile_id='profile-a', locale='nl', selected_mood='groove',
            session_start_strategy=self.r.SessionStartStrategy.DISCOVER)
        calls = []
        async def transport(hass, data, **kwargs):
            import json
            calls.append(data['text'])
            reply = ({'supported':True,'language_ok':True,'style_ok':True} if 'Review this proposed' in data['text']
                else {'text':'Zullen we {previous_track} nog eens opzoeken? {producer} staat daar én bij {current_track} als producer vermeld.'})
            return {'response':{'speech':{'plain':{'speech':json.dumps(reply)}}}}
        async def model(brief, guard):
            return await realize_session_narration(self.hass, fallback_text=brief.seed,
                conf={}, narration=brief, admission=guard)
        session_ids, moments, facts, catalogs = session.session_id, [], [], []
        for number in (0, 1):
            catalog, _ = source('birth', number)
            fact = session_facts.recording_facts(catalog, {
                'id': f'00000000-0000-0000-0000-{number+1:012}', 'title':catalog['title'],
                'artist-credit':[{'artist':{'name':catalog['artist']}}],
                'relations':[{'target-type':'artist','type':'producer','artist':{
                    'name':'Qualified producer','id':'00000000-0000-0000-0000-000000000009'}}]})[0]
            facts.append(fact)
            catalogs.append(catalog)
            self.clock[0] += 300
            await self.manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=session_ids,
                state='playing', media_identity=catalog['uri'], title=catalog['title'], artist=catalog['artist'],
                album=catalog['album_name'], duration_ms=600000, position_ms=0)
            async def provider():
                return {'_qualified_facts':(fact,)}
            if number:
                self.manager.connect_narration('profile-a', session_ids, model, lambda:None)
            with patch('custom_components.djconnect.pipeline._call_conversation_process_transport', transport), patch(
                    'custom_components.djconnect.pipeline._assist_context', return_value={'agent_id':'fixture-agent','language':'nl'}):
                if number:
                    import sqlite3
                    from custom_components.djconnect.persistence.service import PersistenceError
                    await self.fixture.service.async_in_transaction(lambda tx: tx.execute(
                        "CREATE TRIGGER reject_recommendation BEFORE INSERT ON djconnect_session_entries WHEN NEW.kind='dj_moment' AND json_extract(NEW.body,'$.moment_type')='recommendation' BEGIN SELECT RAISE(ABORT,'injected recommendation refusal'); END"))
                    with self.assertRaises((PersistenceError, sqlite3.IntegrityError, RuntimeError)):
                        await self.manager.async_process_track_started(owner_profile_id='profile-a', session_id=session_ids,
                            media_identity=catalog['uri'], insight_provider=provider, require_current_playback=True, allow_initial_facts=True)
                    before_retry=await self.fixture.repo.async_session_record(session_ids)
                    self.assertEqual(before_retry['summary']['moments_published']['value'],1)
                    self.assertEqual(session.published_recording_context.used_relations,set())
                    await self.fixture.service.async_in_transaction(lambda tx: tx.execute('DROP TRIGGER reject_recommendation'))
                moment = await self.manager.async_process_track_started(owner_profile_id='profile-a', session_id=session_ids,
                    media_identity=catalog['uri'], insight_provider=provider, require_current_playback=True, allow_initial_facts=True)
            self.assertIsNotNone(moment)
            moments.append(moment)
        recommendation = moments[1]
        self.assertEqual(recommendation.moment_type.value, 'recommendation')
        proof = recommendation.source_fact
        self.assertIs(type(proof), session_facts.ProducerRecommendationFact)
        self.assertEqual(proof.previous_moment_id, moments[0].moment_id)
        self.assertEqual(proof.recommended_media_identity, catalogs[0]['uri'])
        self.assertEqual(proof.media_identity, catalogs[1]['uri'])
        self.assertEqual(len(calls), 4)
        self.assertEqual(qualify(proof, locale='nl', persona='home_dj', mood='groove', seed=recommendation.content).family(), 'producer_recommendation')
        self.assertEqual(recommendation.actions, ())
        self.assertIsNone(recommendation.artwork_url)
        self.assertTrue(session_speech.moment_projection(session.broadcast, recommendation)['manual_allowed'])
        admission = next(a for a in session.broadcast.native_delivery()['admissions'] if a['moment_id']==recommendation.moment_id)
        self.assertEqual(admission['qualification'], 'qualified')
        for invalid in (replace(proof, previous_moment_id=''), replace(proof, producer_id='00000000-0000-0000-0000-000000000099'),
                        replace(proof, previous_evidence=replace(proof.previous_evidence, observed_at=time.monotonic()-1801))):
            self.assertFalse(invalid.eligible(invalid.media_identity, time.monotonic()))
        # Same normalized relation cannot become a second Track or Recommendation.
        self.assertIsNone(session.published_recording_context.candidate((facts[1],), catalogs[1]['uri'], time.monotonic()))
        unpublished = session_facts.PublishedRecordingContext()
        for catalog in catalogs:
            unpublished.observe(catalog['uri'], time.monotonic())
        unpublished.commit(facts[0], time.monotonic())  # Facts alone have no publication-ID.
        relation = unpublished.candidate((facts[1],), catalogs[1]['uri'], time.monotonic())
        self.assertIsNone(session_facts.producer_recommendation(relation, '', time.monotonic()))
        consumed = session_facts.PublishedRecordingContext()
        consumed.consume(proof, time.monotonic()+1801, semantic_accepted=True)
        self.assertIn(proof.relation_key, consumed.used_relations)
        self.assertEqual(consumed.credits, {})
        self.assertEqual(consumed.published_moment_ids, {})
        await self.manager.async_end(owner_profile_id='profile-a', session_id=session_ids)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        page = await self.fixture.queries.async_timeline_page('profile-a', session_ids)
        retained = next(e for e in page['entries'] if e.get('moment_id')==recommendation.moment_id)
        self.assertEqual(retained['text'], recommendation.content)
        self.assertTrue(retained['session_speech']['manual_allowed'])

    async def test_retained_album_and_artist_artwork_resolve_original_subject_with_current_owner_rights(self):
        import json
        from dataclasses import replace
        from pathlib import Path
        from types import SimpleNamespace
        from custom_components.djconnect import session_artwork
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.profile_context import profile_storage
        from custom_components.djconnect.session_conversation import async_metadata_archive_admission
        self.runtime = self.hass.data['djconnect']['owner-entry']
        storage = profile_storage(self.hass)
        await storage.async_upsert_music_account('source-account', 'source-spotify', kind=MusicAccountKind.PERSONAL,
            display_name='Synthetic source', linked_profile_ids=frozenset({'profile-a'}), provider_account_id='fixture-owner')
        profile = storage.household.profiles['profile-a']
        await storage.async_update_profile('profile-a', preferences=replace(profile.preferences,
            default_backend_id='source-spotify', default_music_account_id='source-account'))
        owner_entry = SimpleNamespace(entry_id='owner-entry', data={**self.runtime.config, 'device_token':self.runtime.device_token, 'profile_backend_entry_id':'source-entry', 'profile_id':'profile-a', 'music_account_id':'source-account'},
            options={}, disabled_by=None, state=SimpleNamespace(value='loaded'))
        self.runtime.entry = owner_entry
        source_entry = self.hass.config_entries.async_entries('djconnect')[0]
        source_entry.disabled_by=None
        source_entry.state=SimpleNamespace(value='loaded')
        source_entry.data.update(profile_id='profile-a', music_backend='source-spotify')
        provider = SimpleNamespace(entry=source_entry, config=dict(source_entry.data))
        self.hass.data['djconnect']['source-entry'] = provider
        self.hass.config_entries.async_get_entry = lambda eid: {'owner-entry':owner_entry,'source-entry':source_entry}.get(eid)
        self.hass.async_create_task = __import__('asyncio').create_task
        import asyncio
        import sys
        from custom_components.djconnect.image_proxy import ManagedSessionImages
        self.hass.loop = asyncio.get_running_loop()
        self.hass.bus = SimpleNamespace(async_listen_once=lambda *args:None)
        with patch.dict(sys.modules, {'homeassistant.const':SimpleNamespace(EVENT_HOMEASSISTANT_STOP='homeassistant_stop')}):
            self.hass.data['djconnect']['session_images'] = ManagedSessionImages(self.hass)

        binding = {'backend_id':'source-spotify','music_account_id':'source-account',
                   'provider_entry_id':'source-entry','provider_account_id':'fixture-owner'}
        session = await self.manager.async_start(owner_profile_id='profile-a', locale='nl', selected_mood='groove',
            history_source_context=binding)
        async def realize(brief, guard):
            guard()
            return brief.seed
        async def archive(captured):
            return await async_metadata_archive_admission(self.hass, 'profile-a', captured, lambda:None)
        self.manager.connect_narration('profile-a', session.session_id, realize, lambda:None, archive_admission=archive)
        moments=[]
        for number, family in enumerate(('edition','description')):
            catalog, fact = source(family, number)
            if family == 'description':
                # This legacy retained-subject test isolates no-provider CC0
                # history compatibility; actual registered artist media is
                # separately covered through sealed research publication.
                self.manager._narration_providers.pop('profile-a', None)
                fact=replace(fact, artwork_subject_uri='spotify:artist:'+'Z'*22)
            self.clock[0]+=300
            await self.manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=session.session_id,
                state='playing',media_identity=catalog['uri'],title=catalog['title'],artist=catalog['artist'],
                duration_ms=600000,position_ms=0)
            async def provider_fact(): return {'_qualified_facts':(fact,)}
            moments.append(await self.manager.async_process_track_started(owner_profile_id='profile-a',session_id=session.session_id,
                media_identity=catalog['uri'],insight_provider=provider_fact,require_current_playback=True,allow_initial_facts=True))
        await self.manager.async_end(owner_profile_id='profile-a',session_id=session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        page=await self.fixture.queries.async_timeline_page('profile-a',session.session_id)
        before=await self.fixture.repo.async_session_record(session.session_id)
        entries=[next(e for e in page['entries'] if e.get('moment_id')==m.moment_id) for m in moments]
        pixels=Path('examples/client_contracts/session_artwork_v1/assets/cover.png').read_bytes()
        fetched=[]
        async def fetch(hass, backend, uri, *,guard,expected_album_uri=''):
            await guard()
            fetched.append(uri)
            return pixels,'image/png','https://open.spotify.com/'+uri.split(':')[1]+'/'+uri.split(':')[2],'',160,160,'Original subject'
        context=SimpleNamespace(profile_id='profile-a')
        with patch.object(session_artwork,'_fetch',fetch):
            for entry in entries:
                ready=await session_artwork.prepare(self.hass,self.runtime,context,
                    session_id=session.session_id,target={'entry_id':entry['entry_id']})
                self.assertEqual(ready['artwork']['state'],'ready',ready)
                self.assertTrue(ready['artwork']['historical_display_allowed'])
                self.assertFalse(ready['artwork']['current_display_allowed'])
                asset=ready['artwork']['url'].rsplit('/',1)[-1]
                self.assertEqual(await session_artwork.image(self.hass,context,session.session_id,asset,runtime=self.runtime),
                    (pixels,'image/png'))
            self.assertEqual(fetched,['spotify:album:'+str(1).zfill(22),'spotify:artist:'+'Z'*22])
        after=await self.fixture.repo.async_session_record(session.session_id)
        self.assertEqual(after['revision'],before['revision'])
        self.assertIsNone(self.manager.current_active('profile-a'))
        for entry in entries:
            row=await self.fixture.queries._repository.async_entry_record('profile-a',session.session_id,entry['entry_id'])
            retained=json.loads(row['body'])
            self.assertNotIn('url',retained['session_media_reference'])
        await self.fixture.repo.async_withdraw_source_entry('source-entry')
        self.assertIsNone(await session_artwork.image(self.hass,context,session.session_id,asset,runtime=self.runtime))

    async def test_current_insight_reuses_unpublished_exact_credit_without_new_lookup_or_audio_claims(self):
        import json
        from types import SimpleNamespace
        from custom_components.djconnect import session_facts, track_insight
        self.runtime = self.hass.data['djconnect']['owner-entry']
        self.hass.services=SimpleNamespace(async_call=lambda *args,**kwargs:None)
        session=await self.manager.async_start(owner_profile_id='profile-a',locale='en',selected_mood='groove',
            session_start_strategy=self.r.SessionStartStrategy.DISCOVER)
        catalog, artist=source('description',0)
        credit=session_facts.recording_facts(catalog, {'id':'00000000-0000-0000-0000-000000000011',
            'title':catalog['title'],'artist-credit':[{'artist':{'name':catalog['artist']}}],
            'relations':[{'target-type':'artist','type':'producer',
                'artist':{'name':'Qualified producer','id':'00000000-0000-0000-0000-000000000009'}}]})[0]
        await self.manager.async_update_playback_projection(owner_profile_id='profile-a',session_id=session.session_id,
            state='playing',media_identity=catalog['uri'],title=catalog['title'],artist=catalog['artist'],duration_ms=600000,position_ms=0)
        async def facts(): return {'_qualified_facts':(artist,credit)}
        published=await self.manager.async_process_track_started(owner_profile_id='profile-a',session_id=session.session_id,
            media_identity=catalog['uri'],insight_provider=facts,require_current_playback=True,allow_initial_facts=True)
        self.assertEqual(published.moment_type.value,'artist')
        calls,lookups=[],[]
        async def status(*args,**kwargs):
            lookups.append(True)
            return {'provider':'spotify_direct','playback':{'uri':catalog['uri'],'title':catalog['title'],
                'artist':catalog['artist'],'genres':['ambient'],'is_playing':True}}
        async def agent(hass,data,**kwargs):
            calls.append(data['text'])
            result=({'supported':True,'language_ok':True,'style_ok':True} if data['text'].startswith('Review every claim') else
                    {'summary':'A person behind this recording.','full_text':'Qualified producer is credited as producer on this recording.', 'listening_cues':[]})
            return {'response':{'speech':{'plain':{'speech':json.dumps(result)}}}}
        with patch.object(track_insight,'run_music_command',status), patch('custom_components.djconnect.pipeline._call_conversation_process_transport',agent), patch.object(
                track_insight,'_assist_context',return_value={'agent_id':'fixture-agent','language':'en'}):
            result=await track_insight.TrackInsightService().async_analyze(self.hass,self.runtime,{'language':'en'},
                source='http',owner_profile_id='profile-a',commit_guard=lambda:None)
        self.assertEqual(len(lookups),1)
        self.assertEqual(len(calls),2)
        self.assertEqual(result['analysis']['source_attribution']['provider'],'MusicBrainz')
        self.assertIn('Qualified producer',result['analysis']['verified_context'])
        self.assertEqual(result['analysis']['full_text'],'Qualified producer is credited as producer on this recording.')
        self.assertFalse(result['analysis']['measured_audio'])
        self.assertIsNone(result['analysis']['energy'])
        self.assertEqual(session.broadcast.state.dj_moments,(published,))
        self.assertNotIn(published.content,calls[0])
        # New source context is never inferred from an old cached presentation.
        self.runtime.track_insight_rate_limit={}
        async def ended(hass,data,**kwargs):
            await self.manager.async_end(owner_profile_id='profile-a',session_id=session.session_id)
            return await agent(hass,data,**kwargs)
        with patch.object(track_insight,'run_music_command',status), patch('custom_components.djconnect.pipeline._call_conversation_process_transport',ended), patch.object(
                track_insight,'_assist_context',return_value={'agent_id':'fixture-agent','language':'en'}):
            from custom_components.djconnect.track_insight_target import TrackInsightError
            with self.assertRaises(TrackInsightError) as denied:
                await track_insight.TrackInsightService().async_analyze(self.hass,self.runtime,{'language':'en','force_refresh':True},
                    source='http',owner_profile_id='profile-a',commit_guard=lambda:None)
        self.assertEqual(len(calls),3)
        self.assertEqual(denied.exception.code, 'track_insight_context_changed')
