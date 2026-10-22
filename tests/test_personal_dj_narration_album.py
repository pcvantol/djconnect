"""Album regression through the real Moment/Flow/SQLite owner.

Public HTTP and HA model replies are explicit fixtures, never actual literary
quality, installation or audible acceptance.
"""
from dataclasses import replace
import json
import time
import unittest
from urllib.parse import parse_qs, urlsplit

from tests import test_personal_dj_narration_public_artist as fixtures
from scripts.verification.source_fixture_urls import wikipedia_api_fixture


class AlbumNarrationTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.PublicArtistNarrationTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.PublicArtistNarrationTest.tearDownClass()

    async def asyncSetUp(self):
        self.base = fixtures.PublicArtistNarrationTest()
        await self.base.asyncSetUp()
        from custom_components.djconnect.session_facts import catalog_facts
        self.artist_id = 'A'*22
        self.mbid = '00000000-0000-0000-0000-000000000001'
        self.group_id = '00000000-0000-0000-0000-000000000002'
        self.resource = 'https://open.spotify.com/artist/'+self.artist_id
        self.base.fact = catalog_facts({**self.base.catalog, 'artist_ids':[self.artist_id]})[0]
        self.base.answer = ('Voor Paper Windows 1 nam Nora Vale 1 zes stukken op met een orkest. '
                            'Daar schuif ik graag even bij aan.')
        self.mode = ''
        self.urls, self.owners, self.calls = [], [], []
        self.base.fetch, self.base.model = self.fetch, self.model
        self.after_draft = None
        await self.base.manager.async_update_allowed_capability_intents(owner_profile_id='profile-a',
            session_id=self.base.session.session_id, allowed_capability_intents=frozenset({'album_story'}))
        self.base.session = await self.base.manager.async_get_active('profile-a')

    async def asyncTearDown(self):
        await self.base.asyncTearDown()

    async def fetch(self, fetch, url, **kwargs):
        await fetch.guard()
        if fetch.requests >= self.base.research.MAX_REQUESTS:
            raise self.base.research.ResearchUnavailable('public_research_budget')
        fetch.requests += 1
        self.urls.append(url)
        self.owners.append(fetch)
        location = urlsplit(url)
        if location.hostname == 'musicbrainz.org':
            if location.path == '/ws/2/url':
                data = {'resource':self.resource, 'relations':[{'target-type':'artist',
                        'artist':{'id':self.mbid,'name':'Nora Vale 1'}}]}
                if self.mode == 'wrong-resource':
                    data['resource'] += 'wrong'
            elif location.path == '/ws/2/artist/'+self.mbid:
                data = {'id':self.mbid,'name':'Nora Vale 1','type':'Group','relations':[
                    {'type':'streaming','url':{'resource':self.resource}},
                    {'type':'wikidata','url':{'resource':'https://www.wikidata.org/wiki/Q1'}}]}
                if self.mode == 'wrong-artist':
                    data['name'] = 'Same Title Tribute'
                if self.mode == 'wrong-spotify-id':
                    data['relations'][0]['url']['resource'] += 'wrong'
            elif location.path == '/ws/2/release-group':
                self.assertEqual(parse_qs(location.query)['query'],
                    ['releasegroup:"Paper Windows 1" AND arid:'+self.mbid])
                group = {'id':self.group_id,'title':'Paper Windows 1','primary-type':'Album',
                    'artist-credit':[{'artist':{'id':self.mbid,'name':'Nora Vale 1'}}]}
                if self.mode == 'sequel':
                    group['title'] += ' II'
                if self.mode == 'other-performer':
                    group['artist-credit'][0]['artist']['id'] = self.group_id
                data = {'count':1, 'offset':0, 'release-groups':[group]}
                if self.mode == 'ambiguous':
                    data['release-groups'].append({**group, 'id':self.mbid})
                    data['count'] = 2
                if self.mode == 'truncated':
                    data['count'] = 6
            else:
                return 404, '', url
        elif location.hostname == 'www.wikidata.org':
            data = {'entities':{'Q1':{'id':'Q1','claims':{'P434':[{
                'mainsnak':{'datavalue':{'value':self.group_id if self.mode == 'wrong-reciprocal' else self.mbid}}}]}}}}
        elif wikipedia_api_fixture(url):
            paragraph = ('<p>Nora Vale 1 is a music group.</p><p>For <i>Paper Windows 1</i>, '
                         'Nora Vale 1 recorded six pieces with an orchestra.</p>')
            if self.mode == 'biography-only':
                paragraph = '<p>Nora Vale 1 is a music group.</p><p>The band played with an orchestra.</p>'
            if self.mode == 'sequel-passage':
                paragraph = paragraph.replace('Paper Windows 1','Paper Windows 1 II')
            if self.mode in {'pronoun-paragraph','other-album-pronoun'}:
                paragraph = ('<p>Nora Vale 1 is a music group.</p><p>Nora Vale 1 announced '
                    '<i>Paper Windows 1</i> on its website. '
                    + ('The album' if self.mode == 'pronoun-paragraph' else '<i>Other Album</i>')
                    + ' consists of six pieces recorded with an orchestra.</p>')
            if self.mode == 'competing-antecedent':
                paragraph = ('<p>Nora Vale 1 is a music group.</p><p>Nora Vale 1 followed '
                    '<i>Paper Windows 1</i> with <i>Other Album</i>. '
                    'The album consists of six pieces recorded with an orchestra.</p>')
            data = {'query':{'pages':[{'title':'Nora Vale 1', 'extract':paragraph,
                'pageprops':{'wikibase_item':'Q2' if self.mode == 'wrong-wiki' else 'Q1',
                             'wikibase-shortdesc':'music group'}, 'revisions':[{'revid':1234}]}]}}
        elif location.hostname == 'html.duckduckgo.com':
            return 404, '', url
        else:
            raise AssertionError('unexpected destination')
        return 200, json.dumps(data), url

    async def model(self, hass, data, **kwargs):
        self.calls.append(data['text'])
        if len(self.calls) % 2:
            if self.after_draft:
                await self.after_draft()
            value = self.base.answer
        else:
            assessment = json.loads(data['text'].split('\nData:\n')[1])
            sources = assessment['evidence']['public_music_research']['sources']
            span = next(s for source in sources if source['provider'] == 'Wikipedia'
                        for s in source['evidence_spans'] if 'six pieces' in s['text'])
            first, second = self.base.answer.split('. ', 1)
            appreciation = self.mode in {'named-appreciation','named-unsupported-modifier'}
            prefix, clause = first.split(': ',1) if appreciation else ('',first)
            primary = ([{'text':'Voor Paper Windows 1','kind':'relationship','evidence_ids':[span['id']]},
                        {'text':clause.removeprefix('Voor Paper Windows 1 ')+'.','kind':'fact','evidence_ids':[span['id']]}]
                       if self.mode == 'competing-antecedent' else
                       [{'text':clause+'.', 'kind':'fact' if self.mode == 'fact-label' else 'relationship', 'evidence_ids':[span['id']]}])
            value = json.dumps({'supported':True, 'unsupported_claims':[], 'temporal_claims':[],
                'language_ok':True, 'style_ok':self.mode != 'dry-review',
                'album_focus_preserved':self.mode != 'no-album-focus',
                'review_schema':'source_id_review_v1', 'claim_checks':[
                    *([{'text':prefix+':','kind':'dj_appreciation','evidence_ids':[]}] if appreciation else []),
                    *primary,
                    {'text':second, 'kind':'dj_appreciation', 'evidence_ids':[]}]})
        return {'response':{'speech':{'plain':{'speech':value}}}}

    async def test_album_story_actual_publication_reopen_context_and_replay_keep_public_scope(self):
        from custom_components.djconnect.public_artist_narration import admitted
        from custom_components.djconnect.ask_dj.service import _live_reference
        from custom_components.djconnect.ask_dj.dialogue import model_source
        from custom_components.djconnect.session_conversation import query_service
        from custom_components.djconnect.session_speech import moment_projection, resolve_retained
        moment = await self.base.publish()
        self.assertIsNotNone(moment, self.base.debug)
        self.assertEqual(moment.content, self.base.answer)
        self.assertEqual(moment.moment_type.value, 'album')
        self.assertTrue(admitted(moment))
        self.assertEqual(len(self.calls), 2)
        self.assertLessEqual(len(self.urls), 8)
        self.assertTrue(all(owner is self.owners[0] for owner in self.owners))
        self.assertEqual({s['provider'] for s in moment.as_dict()['sources']}, {'Wikipedia','MusicBrainz'})
        for prompt in self.calls:
            for private in ('spotify:', self.artist_id, self.base.catalog['release_date'], 'Spotify dates'):
                self.assertNotIn(private, prompt)
        selected = await _live_reference(self.base.manager, 'profile-a',
            {'session_id':moment.session_id, 'moment_id':moment.moment_id})
        context = model_source(selected)
        self.assertEqual(context['attribution']['provider'], 'MusicBrainz')
        self.assertIn('/release-group/', context['attribution']['url'])
        self.assertNotIn(self.base.catalog['release_date'], context['qualified_excerpt'])
        self.assertNotIn('orchestra', context['qualified_excerpt'])
        self.assertTrue(moment_projection(self.base.session.broadcast, moment)['manual_allowed'])
        await self.base.manager.async_end(owner_profile_id='profile-a', session_id=moment.session_id)
        await self.base.fixture.service.async_close()
        await self.base.fixture.service.async_initialize()
        page = await query_service(self.base.hass, self.base.history).async_timeline_page('profile-a', moment.session_id)
        entry = next(e for e in page['entries'] if e.get('moment_id') == moment.moment_id)
        self.assertEqual(entry['text'], self.base.answer)
        descriptor, _ = await resolve_retained(self.base.hass, self.base.history, 'profile-a',
            {'session_id':moment.session_id,'entry_id':entry['entry_id']})
        self.assertTrue(descriptor['manual_allowed'])
        self.assertEqual({s['provider'] for s in descriptor['attribution']}, {'Wikipedia','MusicBrainz'})

    async def test_ambiguous_wrong_subject_and_sequel_decline_before_any_model_call(self):
        for mode in ('wrong-resource','wrong-artist','wrong-spotify-id','wrong-reciprocal',
                     'sequel','other-performer','ambiguous','truncated','wrong-wiki','biography-only','sequel-passage'):
            with self.subTest(mode=mode):
                self.mode = mode
                # Test the same production expression without consuming new opportunities.
                from custom_components.djconnect.narration_brief import qualify
                brief = qualify(self.base.fact, locale='nl',persona='home_dj',mood='chill',
                                seed=self.base.fact.copy_for('nl')[1])
                from unittest.mock import patch
                async def network(fetch, url, **kwargs):
                    return await self.fetch(fetch, url, **kwargs)
                async def ask(prompt):
                    raise AssertionError('unqualified identity reached model')
                from custom_components.djconnect.public_artist_narration import realize
                with patch.object(self.base.research.PublicFetch,'request',network):
                    self.assertIsNone(await realize(brief, ask=ask, admission=lambda:None))
        self.assertEqual(self.calls, [])

    async def test_rejected_album_story_never_publishes_date_fallback_or_retries_tick(self):
        self.mode = 'dry-review'
        self.assertIsNone(await self.base.publish())
        self.assertEqual(self.base.session.broadcast.state.dj_moments, ())
        self.assertEqual(self.base.session.presence_ledger.total_published, 0)
        self.assertEqual(len(self.calls), 2)
        self.assertIsNone(await self.base.publish())
        self.assertEqual(len(self.calls), 2)
        opportunity = self.base.manager._intra_track_opportunities['profile-a']
        self.assertIn('album_release', opportunity.used_fact_keys)
        self.assertFalse(opportunity.pending)

    async def test_missing_album_focus_is_not_repaired_with_more_model_calls(self):
        self.mode = 'no-album-focus'
        self.assertIsNone(await self.base.publish())
        self.assertEqual(len(self.calls), 2)

    async def test_rejected_album_does_not_starve_independently_qualified_current_genre(self):
        from custom_components.djconnect.session_facts import observed_genre_facts
        from custom_components.djconnect.session_conversation import query_service
        owner, sid = 'profile-a', self.base.session.session_id
        await self.base.manager.async_update_allowed_capability_intents(owner_profile_id=owner,
            session_id=sid,allowed_capability_intents=frozenset({'album_story','genre_story'}))
        await self.base.manager.async_update_presence(owner_profile_id=owner,session_id=sid,
            selected_presence='presenter')
        catalog = self.base.catalog
        genres = observed_genre_facts({'source':'spotify_playback_status','backend':'spotify_direct',
            'is_playing':True,'media_identity':catalog['uri'],'title':catalog['title'],
            'artist':catalog['artist'],'artist_ids':[self.artist_id], 'genres':['synth-pop'],
            'genre_source_expires_at':time.monotonic()+600},media_identity=catalog['uri'],
            title=catalog['title'],artist=catalog['artist'])
        self.assertEqual(len(genres),1)
        callbacks = []
        async def expression(brief, guard):
            guard()
            callbacks.append(brief.fact.key)
            # Explicit synthetic research rejection; no network or model call.
            return brief.seed
        self.base.manager.connect_narration(owner,sid,expression,lambda:None)
        async def insight():
            return {'_qualified_facts':(self.base.fact,*genres)}
        first = await self.base.manager.async_process_track_started(owner_profile_id=owner,
            session_id=sid,media_identity=catalog['uri'],insight_provider=insight,
            require_current_playback=True,allow_initial_facts=True)
        self.assertIsNone(first)
        await self.base.manager.async_update_playback_projection(owner_profile_id=owner,session_id=sid,
            state='playing',media_identity=catalog['uri'],title=catalog['title'],artist=catalog['artist'],
            duration_ms=300000,position_ms=15000)
        moment = await self.base.manager.async_maybe_publish_intra_track_moment(owner_profile_id=owner,
            session_id=sid,media_identity=catalog['uri'])
        self.assertIsNotNone(moment)
        self.assertEqual(moment.moment_type.value,'genre')
        self.assertIn('synth-pop',moment.content)
        self.assertEqual(callbacks,['album_release','genre_context'])
        for _ in range(3):
            self.assertIsNone(await self.base.manager.async_maybe_publish_intra_track_moment(
                owner_profile_id=owner,session_id=sid,media_identity=catalog['uri']))
        self.assertEqual(callbacks,['album_release','genre_context'])
        self.assertEqual(self.base.manager.current_active(owner).presence_ledger.total_published,1)
        await self.base.manager.async_end(owner_profile_id=owner,session_id=sid)
        await self.base.fixture.service.async_close()
        await self.base.fixture.service.async_initialize()
        page = await query_service(self.base.hass,self.base.history).async_timeline_page(owner,sid)
        published = [e for e in page['entries'] if e.get('moment_id')]
        self.assertEqual([e['moment_id'] for e in published],[moment.moment_id])
        # Live genre proof is not a durable archive grant. This fixture did not
        # connect archive admission, so SQLite retains only its causal receipt.
        self.assertIsNone(published[0]['text'])
        self.assertEqual(published[0]['content_state'],'unavailable')
        self.assertFalse(published[0]['speech_available'])

    async def test_real_observer_collects_genre_once_and_discards_changed_source_or_full_pool(self):
        import asyncio
        import importlib
        from unittest.mock import AsyncMock, patch
        from custom_components.djconnect.spotify_backend import SpotifyBackend, SpotifyPlaybackObservation
        from custom_components.djconnect.profile_context import profile_storage
        # Other owning test loaders deliberately replace sys.modules entries.
        # Use their current module owners, not stale package attributes or a
        # backend class captured by a previously imported observer fixture.
        forecast_imagery = importlib.import_module('custom_components.djconnect.forecast_imagery')
        playback_observation = importlib.import_module('custom_components.djconnect.playback_observation')
        session_facts = importlib.import_module('custom_components.djconnect.session_facts')
        self.base.hass.async_create_task = asyncio.create_task
        catalog = {**self.base.catalog,'artist_ids':[self.artist_id]}
        result = SpotifyPlaybackObservation(is_playing=True,state='playing',media_identity=catalog['uri'],
            title=catalog['title'],artist=catalog['artist'],album=catalog['album_name'],
            duration_ms=300000,position_ms=0,catalog=catalog)
        for mode in ('available','command','authority','track','full-pool','short'):
            with self.subTest(mode=mode):
                prior = self.base.manager.current_active('profile-a')
                if prior is not None:
                    await self.base.manager.async_end(owner_profile_id='profile-a',session_id=prior.session_id)
                active = await self.base.manager.async_start(owner_profile_id='profile-a',locale='nl',
                    selected_mood='party',music_backend='spotify_direct',
                    allowed_capability_intents=frozenset({'album_story','genre_story'}))
                active = await self.base.manager.async_update_presence(owner_profile_id='profile-a',
                    session_id=active.session_id,selected_presence='presenter')
                observer = playback_observation.PlaybackObservationManager(self.base.hass)
                requests, expressions = [], []
                async def expression(brief,guard):
                    guard()
                    expressions.append(brief.fact.key)
                    return brief.seed
                self.base.manager.connect_narration('profile-a',active.session_id,expression,lambda:None)
                async def no_other_insight():
                    raise AssertionError('catalogue evidence must not trigger TrackInsight/model fallback')
                async def request(backend,method,path,**kwargs):
                    requests.append((method,path))
                    if mode == 'command':
                        observer._spotify_sessions['profile-a'].command_revision += 1
                    elif mode == 'authority':
                        profile_storage(self.base.hass).authority_revision += 1
                    elif mode == 'track':
                        await self.base.manager.async_update_playback_projection(owner_profile_id='profile-a',
                            session_id=active.session_id,state='playing',media_identity='spotify:track:'+'Z'*22,
                            title='Other recording',artist='Other artist',duration_ms=300000,position_ms=0)
                    return {'artists':[{'id':self.artist_id,'genres':['synth-pop']}]}
                pool = (self.base.fact,)*6 if mode == 'full-pool' else (self.base.fact,)
                resolver = type('Resolver',(),{'resolve':AsyncMock(return_value=pool)})()
                current_result = replace(result,duration_ms=10000) if mode == 'short' else result
                # Separate ordinary per-track source lookup from an unrelated
                # cached success in a previous synthetic Session.
                self.base.runtime.backend_cache = {}
                with patch.object(SpotifyBackend,'async_observe_current_playback',AsyncMock(return_value=current_result)), \
                        patch.object(SpotifyBackend,'async_observe_next_item',AsyncMock(return_value={})), \
                        patch.object(SpotifyBackend,'async_observe_forecast_queue',AsyncMock(return_value={})), \
                        patch.object(SpotifyBackend,'_request',request), \
                        patch.object(forecast_imagery,'artist_authority',return_value=lambda:True), \
                        patch.object(session_facts,'session_facts_resolver',return_value=resolver), \
                        patch.object(playback_observation,'SpotifyBackend',SpotifyBackend), \
                        patch.object(playback_observation,'async_track_time_interval',None), \
                        patch.object(self.base.manager,'async_prepare_forecast_art',AsyncMock()):
                    await observer.async_start_spotify(integration_runtime=self.base.runtime,
                        session=active,insight_provider=no_other_insight)
                    if mode == 'available':
                        observed = observer._spotify_sessions['profile-a']
                        for _ in range(3):
                            await observer._async_poll_spotify(observed)
                        published = self.base.manager.current_active('profile-a').broadcast.state.dj_moments
                        self.assertEqual([m.moment_type.value for m in published],['genre'])
                        self.assertEqual(expressions,['album_release','genre_context'])
                        self.assertEqual(requests,[('GET','/artists?ids='+self.artist_id)])
                    else:
                        self.assertEqual(self.base.manager.current_active('profile-a').broadcast.state.dj_moments,())
                        self.assertEqual(len(requests),0 if mode == 'full-pool' else 1)
                    await observer.async_stop('profile-a',active.session_id)

    async def test_track_change_during_generation_cannot_publish_album_or_seed(self):
        async def change():
            await self.base.manager.async_update_playback_projection(owner_profile_id='profile-a',
                session_id=self.base.session.session_id, state='playing',media_identity='spotify:track:'+'Z'*22,
                title='Other recording',artist='Other performer',duration_ms=300000,position_ms=0)
        self.after_draft = change
        self.assertIsNone(await self.base.publish())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.base.session.broadcast.state.dj_moments, ())

    async def test_mutated_album_receipts_and_source_bindings_fail_closed(self):
        from custom_components.djconnect.public_artist_narration import admitted
        moment = await self.base.publish()
        self.assertTrue(admitted(moment))
        for changed in (replace(moment, content=moment.content+' Invented.'),
                replace(moment, source_fact=replace(self.base.fact, album_artist_id='Z'*22)),
                replace(moment, source_fact=replace(self.base.fact, album_artist='Someone else')),
                replace(moment, source_attribution=(('provider','Spotify'),)),
                replace(moment, moment_type=self.base.r.DJMomentType.ARTIST)):
            self.assertFalse(admitted(changed))
        self.assertFalse(admitted(moment, moment.narration_acceptance.accepted.expires_at))

    async def test_catalogue_binding_does_not_admit_missing_multiartist_or_private_query(self):
        from custom_components.djconnect.album_narration import lookup_subject
        self.assertIsNotNone(lookup_subject(self.base.fact))
        for changed in (replace(self.base.fact, album_artist_id=''),
                        replace(self.base.fact, album_artist='my neighbour Alice'),
                        replace(self.base.fact, observed_at=time.monotonic()-1801)):
            self.assertIsNone(lookup_subject(changed))
        from custom_components.djconnect.session_facts import catalog_facts
        for ids in ([], [self.artist_id,'B'*22]):
            self.assertIsNone(lookup_subject(catalog_facts({**self.base.catalog,'artist_ids':ids})[0]))

    async def test_factual_review_label_does_not_reject_exact_album_evidence(self):
        self.mode = 'fact-label'
        moment = await self.base.publish()
        self.assertIsNotNone(moment, self.base.debug)
        self.assertEqual(moment.content, self.base.answer)

    async def test_original_album_antecedent_is_bound_without_exporting_a_scope_flag(self):
        self.mode = 'pronoun-paragraph'
        moment = await self.base.publish()
        self.assertIsNotNone(moment, self.base.debug)
        self.assertEqual(moment.content, self.base.answer)
        self.assertNotIn('AlbumResearchContext', self.calls[1])

    async def test_other_album_activity_is_not_borrowed_from_the_same_paragraph(self):
        self.mode = 'other-album-pronoun'
        self.assertIsNone(await self.base.publish())
        self.assertEqual(self.base.debug['block_reason'], 'research_claim_coverage_unverified')

    async def test_competing_work_in_original_antecedent_blocks_even_split_claims(self):
        self.mode = 'competing-antecedent'
        self.assertIsNone(await self.base.publish())
        self.assertEqual(self.base.debug['block_reason'],'research_claim_coverage_unverified')
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.base.session.broadcast.state.dj_moments,())
        self.assertEqual(self.base.session.presence_ledger.total_published,0)

    async def test_present_interest_can_name_album_but_does_not_exempt_sonic_modifier(self):
        self.mode = 'named-appreciation'
        self.base.answer = ('Wat ik mooi vind aan Paper Windows 1 van Nora Vale 1: '
            'zes stukken zijn opgenomen met een orkest. Daar schuif ik graag even bij aan.')
        moment = await self.base.publish()
        self.assertIsNotNone(moment,self.base.debug)
        # A new track opportunity is unnecessary for this direct qualification
        # check: typed context cannot exempt an unsupported album modifier.
        from custom_components.djconnect.album_narration import AlbumResearchContext
        from custom_components.djconnect.ask_dj.public_research import claim_evidence_ok
        source = self.base.research.PublicSource('Wikipedia','Nora Vale 1','https://en.wikipedia.org/wiki/Nora_Vale',
            'For Paper Windows 1, Nora Vale 1 recorded six pieces with an orchestra.','en','','','CC-BY-SA-4.0',
            source_anchors=('Paper Windows 1',))
        projection = self.base.research.research_projection('Paper Windows 1',[source],{})
        span = source.model_data()['evidence_spans'][0]
        text = 'Wat ik mooi vind aan het experimentele Paper Windows 1: zes stukken zijn opgenomen met een orkest.'
        checks = {'claim_checks':[
            {'text':'Wat ik mooi vind aan het experimentele Paper Windows 1:', 'kind':'dj_appreciation','evidence_ids':[],'quote':''},
            {'text':'zes stukken zijn opgenomen met een orkest.', 'kind':'fact','evidence_ids':[span['id']],'quote':span['text']}]}
        typed = AlbumResearchContext({'public_music_research':projection},fact=self.base.fact,
            identity=moment.narration_acceptance.accepted.subject_identity,album_spans=(span['id'],))
        self.assertFalse(claim_evidence_ok(text,checks,typed))
        clean = self.base.answer.split('. ',1)[0]+'.'
        checks['claim_checks'][0]['text'] = 'Wat ik mooi vind aan Paper Windows 1 van Nora Vale 1:'
        # A plain copied wire dict does not acquire typed album scope.
        self.assertFalse(claim_evidence_ok(clean,checks,dict(typed)))

    async def test_original_compositions_never_become_new_material_in_five_languages(self):
        from custom_components.djconnect.ask_dj.public_research import claim_evidence_ok
        for text in ('It brings new compositions together.',
                     'Het brengt nieuwe composities samen.',
                     'Es vereint neue Kompositionen.',
                     'Il réunit de nouvelles compositions.',
                     'Reúne nuevas composiciones.'):
            with self.subTest(text=text):
                def context_for(quote):
                    source = self.base.research.PublicSource('Wikipedia','Synthetic artist',
                        'https://en.wikipedia.org/wiki/Example',quote,'en','','','CC-BY-SA-4.0')
                    return {'public_music_research':self.base.research.research_projection(
                        'Synthetic artist',[source],{})}, source.model_data()['evidence_spans'][0]
                context, span = context_for('The album consists of original compositions.')
                checks = {'claim_checks':[{'text':text,'kind':'fact',
                    'evidence_ids':[span['id']],'quote':span['text']}]}
                self.assertFalse(claim_evidence_ok(text,checks,context))
                # Freshness is permissible when actually stated by this source;
                # the guard is not a blanket prohibition on new music.
                context, span = context_for('The album consists of new compositions.')
                checks['claim_checks'][0].update(evidence_ids=[span['id']],quote=span['text'])
                self.assertTrue(claim_evidence_ok(text,checks,context))

    async def test_new_material_summary_cannot_hide_as_present_appreciation(self):
        # Actual trial6's independently accepted second sentence made this leap.
        # No album name in that second sentence: work-name checks alone miss it.
        self.base.answer = ('Voor Paper Windows 1 nam Nora Vale 1 zes stukken op met een orkest. '
            'Zo brengt het livealbum bestaand materiaal en nieuwe composities samen in één orkestproject.')
        moment = await self.base.publish()
        self.assertIsNone(moment)
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.base.session.broadcast.state.dj_moments,())
        self.assertEqual(self.base.session.presence_ledger.total_published,0)

    async def test_split_novelty_checks_cannot_evade_complete_sentence_evidence(self):
        from custom_components.djconnect.ask_dj.public_research import claim_evidence_ok
        for first, second in (('It brings new','compositions together.'),
                              ('Het brengt nieuwe','composities samen.'),
                              ('Es vereint neue','Kompositionen.'),
                              ('Il réunit de nouvelles','compositions.'),
                              ('Reúne nuevas','composiciones.')):
            text=first+' '+second
            for original in (True,False):
                with self.subTest(text=text,original=original):
                    source=self.base.research.PublicSource('Wikipedia','Synthetic artist',
                        'https://en.wikipedia.org/wiki/Example',
                        'The album consists of '+('original' if original else 'new')+' compositions.',
                        'en','','','CC-BY-SA-4.0')
                    context={'public_music_research':self.base.research.research_projection(
                        'Synthetic artist',[source],{})}
                    span=source.model_data()['evidence_spans'][0]
                    checks={'claim_checks':[{'text':part,'kind':'fact',
                        'evidence_ids':[span['id']],'quote':span['text']} for part in (first,second)]}
                    self.assertEqual(claim_evidence_ok(text,checks,context),not original)
                    checks['claim_checks'][0].update(kind='dj_appreciation',evidence_ids=[],quote='')
                    self.assertEqual(claim_evidence_ok(text,checks,context),not original)

    async def test_novelty_of_another_work_in_same_paragraph_never_transfers(self):
        from custom_components.djconnect.ask_dj.public_research import claim_evidence_ok
        for target_new in (False,True):
            paragraph=('Paper Windows 1 consists of '+('new' if target_new else 'original')+
                ' compositions. Other Album consists of '+('original' if target_new else 'new')+' compositions.')
            source=self.base.research.PublicSource('Wikipedia','Synthetic artist',
                'https://en.wikipedia.org/wiki/Example',paragraph,'en','','','CC-BY-SA-4.0',
                source_anchors=('Paper Windows 1','Other Album'),original_text=paragraph,
                paragraph_ranges=((0,len(paragraph)),))
            context={'public_music_research':self.base.research.research_projection(
                'Paper Windows 1',[source],{})}
            span=source.model_data()['evidence_spans'][0]
            text='Paper Windows 1 consists of new compositions.'
            for parts in ([text],['Paper Windows 1 consists of new','compositions.']):
                with self.subTest(target_new=target_new,parts=parts):
                    checks={'claim_checks':[{'text':part,'kind':'fact',
                        'evidence_ids':[span['id']],'quote':span['text']} for part in parts]}
                    self.assertEqual(claim_evidence_ok(text,checks,context),target_new)

    async def test_pronoun_only_novelty_recap_keeps_selected_album_scope(self):
        from custom_components.djconnect.album_narration import AlbumResearchContext
        from custom_components.djconnect.ask_dj.public_research import claim_evidence_ok
        moment=await self.base.publish()
        self.assertIsNotNone(moment,self.base.debug)
        for target_new in (False,True):
            paragraph=('Paper Windows 1 consists of '+('new' if target_new else 'original')+
                ' compositions. Other Album consists of '+('original' if target_new else 'new')+' compositions.')
            source=self.base.research.PublicSource('Wikipedia','Synthetic artist',
                'https://en.wikipedia.org/wiki/Example',paragraph,'en','','','CC-BY-SA-4.0',
                source_anchors=('Paper Windows 1','Other Album'),original_text=paragraph,
                paragraph_ranges=((0,len(paragraph)),))
            projection=self.base.research.research_projection('Paper Windows 1',[source],{})
            span=source.model_data()['evidence_spans'][0]
            context=AlbumResearchContext({'public_music_research':projection},fact=self.base.fact,
                identity=moment.narration_acceptance.accepted.subject_identity,album_spans=(span['id'],))
            for parts in (['It contains new compositions.'],['It contains new','compositions.']):
                text=' '.join(parts)
                checks={'claim_checks':[{'text':part,'kind':'fact',
                    'evidence_ids':[span['id']],'quote':span['text']} for part in parts]}
                self.assertEqual(claim_evidence_ok(text,checks,context),target_new)
