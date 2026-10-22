"""Synthetic actual dialogue/Session owners; no live Spotify/model/playback calls."""
import asyncio
import json
import unittest
from unittest.mock import patch

from tests import test_mood_music_steering as shared


class MoodMixCorrectionTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(lambda cls: shared.MoodMusicSteeringTests.setUpClass())
    tearDownClass = classmethod(lambda cls: shared.MoodMusicSteeringTests.tearDownClass())
    asyncSetUp = shared.MoodMusicSteeringTests.asyncSetUp
    asyncTearDown = shared.MoodMusicSteeringTests.asyncTearDown
    agent = shared.MoodMusicSteeringTests.agent
    request = shared.MoodMusicSteeringTests.request
    async def mix_agent(self, hass, data, **kwargs):
        projection = json.loads(data['text'].split('\nData:\n', 1)[1])
        if 'allowed' not in projection:
            return await self.agent(hass, data, **kwargs)
        self.models.append(projection)
        genre = 'techno' if projection['question'] == 'Techno' else 'house'
        reply = {'decision': 'selected', 'genre': genre, 'request_kind': 'mix'}
        return {'response': {'speech': {'plain': {'speech': json.dumps(reply)}}}}

    async def test_house_mix_then_unoffered_techno_preserves_mix_and_original_deadline(self):
        f = self.f
        queries = []
        async def backend(hass, runtime, command, value=None, **kwargs):
            self.assertIn(command, {'queue', 'playlists', 'artist_recommendations'})
            if command != 'artist_recommendations':
                return {'success': True, 'queue': [], 'playlists': []}
            queries.append(value)
            if value['genres'] == ['house']:
                return {'success': True, 'tracks': []}
            return {'success': True, 'tracks': [
                {'uri': 'spotify:track:' + letter * 22, 'name': 'Private exact ' + letter,
                 'artist': 'Private provider performer'} for letter in 'AB']}
        with patch('custom_components.djconnect.use_cases.run_music_command', backend), patch.object(
                f.pipeline, '_call_conversation_process_transport', self.mix_agent), patch.object(
                f.core, '_spotify_track_search', side_effect=AssertionError('mix is not three tracks')):
            question, status = await self.request('original-mood-question', language='nl')
            self.assertEqual(status, 200, question)
            frame = f.history.dialogue.owners['profile:profile-a']['default']
            deadline = frame.pending['deadline']
            result, status = await f.request('Maak een house mix', identifier='house-mix',
                language='nl', context={'session_id': self.session.session_id})
            self.assertEqual(status, 200, result)
            self.assertTrue(result['clarification_required'])
            self.assertEqual(frame.pending['deadline'], deadline)
            self.assertEqual(frame.pending['request_text'], 'Maak een house mix')
            result, status = await f.request('Techno', identifier='techno-mix', language='nl',
                context={'session_id': self.session.session_id})
        self.assertEqual(status, 200, result)
        self.assertFalse(result['clarification_required'])
        self.assertEqual(queries, [{'genres': ['house'], 'limit': 25},
                                   {'genres': ['techno'], 'limit': 25}])
        self.assertEqual(len(result['playback_actions']), 1)
        action = result['playback_actions'][0]
        self.assertEqual(action['kind'], 'track_mix')
        self.assertEqual(action['uris'], ['spotify:track:' + letter * 22 for letter in 'AB'])
        self.assertTrue(action['result_set_id'])
        self.assertTrue(action['action_id'])
        self.assertEqual(action['label'], self.steering.COPY['nl']['now'])
        self.assertEqual(result['conversation']['metrics']['agent_calls'], 3)
        self.assertEqual(self.models[-3]['original_request'], 'Maak een house mix')
        self.assertEqual(self.models[-3]['original_request_kind'], 'mix')
        self.assertIn('clarification_question', self.models[-3])
        self.assertNotIn('Private exact', json.dumps(self.models))
        self.assertEqual(f.effects, [])

    async def test_unoffered_supported_correction_keeps_track_request(self):
        f = self.f
        async def backend(*args, **kwargs):
            return {'success': True, 'queue': [], 'playlists': []}
        async def agent(hass, data, **kwargs):
            projection = json.loads(data['text'].split('\nData:\n', 1)[1])
            if 'allowed' in projection:
                return {'response': {'speech': {'plain': {'speech': json.dumps(
                    {'decision': 'selected', 'genre': 'electronic', 'request_kind': 'tracks'})}}}}
            return await self.agent(hass, data, **kwargs)
        async def search(hass, runtime, query, **kwargs):
            self.assertEqual(query, 'genre:electronic')
            return {'success': True, 'tracks': [
                {'uri': 'spotify:track:' + 'E' * 22, 'name': 'Exact correction'}]}
        with patch('custom_components.djconnect.use_cases.run_music_command', backend), patch.object(
                f.pipeline, '_call_conversation_process_transport', agent), patch.object(
                f.core, '_spotify_track_search', search):
            result, status = await self.request('unoffered-question')
            self.assertEqual(status, 200, result)
            frame = f.history.dialogue.owners['profile:profile-a']['default']
            frame.pending['genres'] = ['soul', 'jazz', 'ambient']
            result, status = await f.request('nee elektronische dance', identifier='unoffered-reply',
                context={'session_id': self.session.session_id})
        self.assertEqual(status, 200, result)
        self.assertEqual(result['playback_actions'][0]['kind'], 'track')
        self.assertEqual(f.effects, [])

    async def test_expiry_during_mix_lookup_withdraws_all_results(self):
        f = self.f
        entered, release = asyncio.Event(), asyncio.Event()
        clock = [f.history.dialogue.clock()]
        f.history.dialogue.clock = lambda: clock[0]
        async def backend(hass, runtime, command, value=None, **kwargs):
            if command == 'artist_recommendations':
                entered.set()
                await release.wait()
                return {'success': True, 'tracks': [
                    {'uri': 'spotify:track:' + letter * 22, 'name': 'Withdrawn ' + letter}
                    for letter in 'AB']}
            return {'success': True, 'queue': [], 'playlists': []}
        with patch('custom_components.djconnect.use_cases.run_music_command', backend), patch.object(
                f.pipeline, '_call_conversation_process_transport', self.mix_agent):
            result, status = await self.request('expiry-question')
            self.assertEqual(status, 200, result)
            frame = f.history.dialogue.owners['profile:profile-a']['default']
            task = asyncio.create_task(f.request('Maak een house mix', identifier='expiry-mix',
                context={'session_id': self.session.session_id}))
            await asyncio.wait_for(entered.wait(), 2)
            clock[0] = frame.pending['deadline'] + 1
            release.set()
            result, status = await asyncio.wait_for(task, 2)
        self.assertEqual((status, result.get('error')), (409, 'choice_expired'))
        self.assertFalse(result.get('playback_actions'))
        self.assertNotIn('Withdrawn', json.dumps(result))
        self.assertEqual(f.effects, [])

    async def test_mix_offer_filters_invalid_duplicates_and_unplayable_records(self):
        f = self.f
        good = {'uri': 'spotify:track:' + 'A' * 22, 'name': 'One actual record'}
        async def backend(hass, runtime, command, value=None, **kwargs):
            if command == 'artist_recommendations':
                return {'success': True, 'tracks': [good, good, None,
                    {'uri': 'spotify:playlist:' + 'P' * 22},
                    {'uri': 'spotify:track:' + 'B' * 22, 'is_playable': False}]}
            return {'success': True, 'queue': [], 'playlists': []}
        with patch('custom_components.djconnect.use_cases.run_music_command', backend), patch.object(
                f.pipeline, '_call_conversation_process_transport', self.mix_agent):
            result, status = await self.request('invalid-records-question', language='nl')
            self.assertEqual(status, 200, result)
            frame = f.history.dialogue.owners['profile:profile-a']['default']
            deadline = frame.pending['deadline']
            result, status = await f.request('Maak een house mix', identifier='invalid-records-mix',
                language='nl', context={'session_id': self.session.session_id})
        self.assertEqual(status, 200, result)
        self.assertEqual(result['playback_actions'], [])
        self.assertEqual(result['text'], self.steering.MIX_UNAVAILABLE['nl'].format(genre='house'))
        self.assertFalse(result['is_generated_text'])
        self.assertEqual(result['conversation']['metrics']['agent_calls'], 1)
        self.assertEqual(frame.pending['deadline'], deadline)
        self.assertEqual(f.effects, [])

    async def test_explicit_mix_play_serializes_exact_order_once_after_offer(self):
        from custom_components.djconnect import http
        from custom_components.djconnect.spotify_backend import SpotifyBackend
        from custom_components.djconnect.domain.backend import BackendProvider
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.domain.profile import ProfilePreferences
        f = self.f
        storage = f.handlers.profile_storage(f.hass)
        await storage.async_upsert_music_backend('spotify_direct', BackendProvider.SPOTIFY_DIRECT,
            display_name='Synthetic provider')
        await storage.async_upsert_music_account('playback-account', 'spotify_direct',
            kind=MusicAccountKind.PERSONAL, display_name='Synthetic account',
            linked_profile_ids=frozenset({'profile-a'}))
        await storage.async_update_profile('profile-a', preferences=ProfilePreferences(
            default_backend_id='spotify_direct', default_music_account_id='playback-account'))
        f.hass.config_entries.async_entries('djconnect')[0].data.update(music_account_id='playback-account')
        await f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=self.session.session_id)
        self.session = await f.fixture.manager.async_start(owner_profile_id='profile-a', locale='en',
            selected_mood='groove', music_backend='spotify_direct', history_source_context={
                'backend_id':'spotify_direct', 'music_account_id':'playback-account',
                'provider_entry_id':'source-entry'})
        f.runtime.config['spotify_refresh_token'] = 'synthetic-never-sent-fixture-grant'
        def update(**values):
            for key, value in values.items():
                setattr(f.runtime, key, value)
        f.runtime.update = update
        uris = ['spotify:track:' + letter * 22 for letter in 'AB']
        async def readonly(hass, runtime, command, value=None, **kwargs):
            self.assertIn(command, {'queue', 'playlists', 'artist_recommendations'})
            if command == 'artist_recommendations':
                return {'success':True, 'tracks':[{'uri':uri, 'name':'Exact mix track'} for uri in uris]}
            return {'success':True, 'queue':[], 'playlists':[]}
        backend = object.__new__(SpotifyBackend)
        backend.hass, backend.runtime = f.hass, f.runtime
        async def token(**kwargs):
            return 'SYNTHETIC_FIXTURE_TOKEN'
        backend._access_token = token
        sent = []
        class Response:
            status = 204
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
        class Transport:
            def request(self, method, url, **kwargs):
                sent.append((method, url, kwargs.get('json')))
                return Response()
        backend.session = Transport()
        async def playback(hass, runtime, command, value=None, **kwargs):
            if command == 'status':
                return {'playback':{'uri':uris[0], 'is_playing':True}}
            self.assertEqual((command, value), ('play_uris', uris))
            async def dispatch():
                await backend.play_uris(value)
            return await f.external_effect_probe(command, value, dispatch)
        with patch('custom_components.djconnect.use_cases.run_music_command', readonly), patch.object(
                f.pipeline, '_call_conversation_process_transport', self.mix_agent), patch.object(
                http, 'run_music_command', playback):
            result, status = await self.request('play-mix-question')
            self.assertEqual(status, 200, result)
            result, status = await f.request('Maak een house mix', identifier='offer-mix',
                context={'session_id':self.session.session_id})
            self.assertEqual(status, 200, result)
            self.assertEqual(sent, [])
            action = result['playback_actions'][0]
            choice = {key:action[key] for key in ('result_set_id', 'action_id')}
            args = {'identifier':'play-exact-mix', 'context':{'session_id':self.session.session_id},
                    'choice_action':{**choice, 'operation':'play'}}
            result, status = await f.request('Play now', **args)
            self.assertEqual(status, 200, result)
            self.assertTrue(result['success'], result)
            self.assertEqual(result['selected_action_id'], action['action_id'])
            duplicate, status = await f.request('Play now', **args)
            self.assertEqual(status, 200, duplicate)
            self.assertTrue(duplicate['deduplicated'])
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][0], 'PUT')
        self.assertIn('/me/player/play', sent[0][1])
        self.assertEqual(sent[0][2], {'uris':uris})

    async def test_selected_without_explicit_kind_never_downgrades_new_mix_to_tracks(self):
        f = self.f
        async def backend(hass, runtime, command, value=None, **kwargs):
            self.assertIn(command, {'queue', 'playlists'})
            return {'success':True, 'queue':[], 'playlists':[]}
        async def legacy(hass, data, **kwargs):
            projection = json.loads(data['text'].split('\nData:\n', 1)[1])
            if 'allowed' in projection:
                return {'response':{'speech':{'plain':{'speech':json.dumps(
                    {'decision':'selected', 'genre':'house'})}}}}
            return await self.agent(hass, data, **kwargs)
        with patch('custom_components.djconnect.use_cases.run_music_command', backend), patch.object(
                f.pipeline, '_call_conversation_process_transport', legacy), patch.object(
                f.core, '_spotify_track_search', side_effect=AssertionError('no inferred track request')):
            result, status = await self.request('no-kind-question')
            self.assertEqual(status, 200, result)
            result, status = await f.request('Maak een house mix', identifier='missing-kind-mix',
                context={'session_id':self.session.session_id})
        self.assertEqual((status, result.get('error')), (502, 'music_direction_interpretation_invalid'))
        self.assertFalse(result.get('playback_actions'))
        self.assertEqual(f.effects, [])

    async def test_mix_card_labels_use_each_original_turn_language(self):
        f = self.f
        async def backend(hass, runtime, command, value=None, **kwargs):
            if command == 'artist_recommendations':
                return {'success':True, 'tracks':[{'uri':'spotify:track:' + letter * 22,
                    'name':'Private provider name'} for letter in 'AB']}
            return {'success':True, 'queue':[], 'playlists':[]}
        with patch('custom_components.djconnect.use_cases.run_music_command', backend), patch.object(
                f.pipeline, '_call_conversation_process_transport', self.mix_agent):
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                with self.subTest(locale=locale):
                    result, status = await self.request('locale-question-' + locale, language=locale)
                    self.assertEqual(status, 200, result)
                    result, status = await f.request('Techno', identifier='locale-mix-' + locale,
                        language=locale, context={'session_id':self.session.session_id})
                    self.assertEqual(status, 200, result)
                    action = result['playback_actions'][0]
                    title, subtitle = self.steering.MIX_PRESENTATION[locale]
                    self.assertEqual(action['title'], title.format(genre='techno'))
                    self.assertEqual(action['subtitle'], subtitle.format(count=2))
                    self.assertEqual(action['label'], self.steering.COPY[locale]['now'])
        self.assertEqual(f.effects, [])

    async def test_real_recommendation_adapter_filters_raw_unavailable_tracks(self):
        """Run the actual raw-response normalizer, not a pre-normalized command stub."""
        from custom_components.djconnect.spotify_backend import SpotifyBackend
        from types import SimpleNamespace
        backend = object.__new__(SpotifyBackend)
        backend.runtime = SimpleNamespace(config={'spotify_market':'NL'})
        async def no_artists(names):
            self.assertEqual(names, [])
            return []
        async def no_tracks(names, count):
            self.assertEqual((names, count), ([], 0))
            return []
        backend._recommendation_artists = no_artists
        backend._recommendation_tracks = no_tracks
        async def request(method, path):
            self.assertEqual(method, 'GET')
            self.assertIn('/recommendations?', path)
            self.assertIn('seed_genres=techno', path)
            return {'tracks':[
                {'uri':'spotify:track:' + 'A' * 22, 'name':'Playable', 'is_playable':True},
                {'uri':'spotify:track:' + 'B' * 22, 'name':'Unavailable', 'is_playable':False},
                {'uri':'spotify:track:' + 'C' * 22, 'name':'Restricted',
                 'restrictions':{'reason':'market'}},
                {'uri':'spotify:track:' + 'D' * 22, 'name':'Local', 'is_local':True}]}
        backend._request = request
        result = await backend.seed_recommendations({'genres':['techno'], 'limit':25})
        self.assertEqual([track['uri'] for track in result['tracks']], ['spotify:track:' + 'A' * 22])
