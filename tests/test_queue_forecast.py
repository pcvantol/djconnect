"""Observed queue prefix, original expiry, source fences and five-locale narrative."""
import asyncio
import copy
import json
from pathlib import Path
import time
from datetime import datetime
import types
import unittest
from unittest.mock import patch

from tests import test_spotify_backend as backend_fixtures
from tests import test_session_forecast as forecast_fixtures


class QueueBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        backend_fixtures.SpotifyBackendTest.setUpClass.__func__(cls)

    def setUp(self):
        backend_fixtures.SpotifyBackendTest.setUp(self)
    def test_queue_exact_contiguous_prefix_and_cached_deadline(self):
        async def scenario():
            runtime = types.SimpleNamespace(config={}, backend_cache={})
            backend = self.backend.SpotifyBackend(object(), runtime)
            current = 'spotify:track:' + 'A'*22
            artist = 'Z'*22
            queue = [{'type':'track','uri':'spotify:track:'+chr(66+i)*22,
                      'name':f'Actual {i}', 'artists':[{'id':artist,'name':'Actual artist'}],
                      'duration_ms':200000} for i in range(7)]
            calls = []
            async def request(method, path):
                self.assertEqual(method, 'GET')
                calls.append(path)
                if path == '/me/player/queue':
                    return {'currently_playing':{'uri':current},'queue':queue}
                return {'artists':[{'id':artist,'genres':['ambient']},
                                   {'id':'Y'*22,'genres':['unrelated genre']}]}
            backend._request = request
            first = await backend.async_observe_forecast_queue(current)
            self.assertEqual(len(first['items']), 5)
            self.assertEqual(first['items'][0]['genres'], ['ambient'])
            self.assertNotIn('unrelated genre', repr(first))
            self.assertEqual(first['up_next']['title'], 'Actual 0')
            second = await backend.async_observe_forecast_queue(current)
            self.assertEqual(second['deadline'], first['deadline'])
            self.assertEqual(second['wall_deadline'], first['wall_deadline'])
            self.assertEqual(len(calls), 2)
            self.assertEqual(await backend.async_observe_forecast_queue('spotify:track:wrong'), {})
            queue[0]['name'] = 'Post-command queue'
            changed = await backend.async_observe_forecast_queue(current, observation_key='session:command2:output')
            self.assertEqual(changed['items'][0]['title'], 'Post-command queue')
            self.assertEqual(len(calls), 4)  # Wrong recording and new command each fetch a fresh queue.
            runtime.backend_cache.clear()
            queue[0]['name'] = 'L'*200
            long_title = await backend.async_observe_forecast_queue(current)
            self.assertEqual(long_title['up_next']['title'], 'L'*200)
            self.assertEqual(long_title['items'], [])
            runtime.backend_cache.clear()
            queue[0]['name'] = 'Actual 0'
            queue[2] = {'type':'episode','name':'Unrelated episode'}
            partial = await backend.async_observe_forecast_queue(current)
            self.assertEqual(len(partial['items']), 2)
            self.assertNotIn('Actual 3', repr(partial))
        asyncio.run(scenario())

    def test_queue_artist_failure_keeps_real_tracks_without_genre_invention(self):
        async def scenario():
            runtime = types.SimpleNamespace(config={}, backend_cache={})
            backend = self.backend.SpotifyBackend(object(), runtime)
            uri = 'spotify:track:'+'A'*22
            async def request(method, path):
                if path.startswith('/artists'):
                    raise self.backend.SpotifyBackendError('not available')
                return {'currently_playing':{'uri':uri},'queue':[
                    {'type':'track','uri':'spotify:track:'+'B'*22,'name':'Real title',
                     'artists':[{'name':'Real artist','id':'Z'*22}]}]}
            backend._request = request
            result = await backend.async_observe_forecast_queue(uri)
            self.assertEqual(result['items'], [{'title':'Real title','artist':'Real artist','genres':[]}])
        asyncio.run(scenario())


class QueueProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        forecast_fixtures.SessionForecastTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        forecast_fixtures.SessionForecastTests.tearDownClass.__func__(cls)

    async def start(self, locale='nl', persona=None):
        return await forecast_fixtures.SessionForecastTests.start(self, locale, persona)

    def test_queue_all_personas_locales_original_expiry_and_no_effects(self):
        async def scenario():
            for locale in ('en','nl','de','fr','es'):
                texts = []
                for persona in self.runtime.DJPersona:
                    manager, active = await self.start(locale, persona)
                    forecast = active.broadcast.forecast
                    now = forecast.clock()
                    data = {'deadline':now+20,'wall_deadline':time.time()+20,'items':[
                        {'title':f'Real {i}','artist':f'Artist {i}','genres':['ambient']} for i in range(3)]}
                    budget = copy.deepcopy(active.presence_ledger.__dict__)
                    moments = active.moment_engine.moments
                    self.assertTrue(await manager.async_update_forecast_queue(
                        owner_profile_id='owner',session_id=active.session_id,
                        media_identity='spotify:track:'+'A'*22,target_name='',preview=data,authority=lambda:True))
                    actual = forecast.as_dict()
                    self.assertIn('Real 0', actual['summary'])
                    self.assertIn('Real 2', actual['summary'])
                    self.assertIn('ambient', actual['summary'])
                    public = active.broadcast.as_dict(include_owner_only=False)['session_forecast']
                    self.assertNotIn('Real 0',public['summary'])
                    self.assertEqual(public['valid_until'],actual['valid_until'])
                    self.assertNotIn('deadline', repr(actual))
                    self.assertLessEqual(forecast.deadline, data['deadline'])
                    self.assertLessEqual(datetime.fromisoformat(actual['valid_until']).timestamp(), data['wall_deadline']+0.000001)
                    for lang in ('en','nl','de','fr','es'):
                        self.assertEqual(forecast.as_dict(locale=lang)['valid_until'],actual['valid_until'])
                    texts.append(actual['summary'])
                    before = (forecast.revision, forecast.deadline, active.broadcast.delivery_sequence)
                    for _ in range(5):
                        self.assertEqual(forecast.as_dict(), actual)
                    self.assertEqual(before, (forecast.revision,forecast.deadline,active.broadcast.delivery_sequence))
                    self.assertEqual(budget, active.presence_ledger.__dict__)
                    self.assertEqual(moments, active.moment_engine.moments)
                    with patch.object(forecast, 'clock', return_value=now+21):
                        self.assertEqual(forecast.as_dict()['state'], 'expired')
                        self.assertEqual(forecast.as_dict()['summary'], '')
                self.assertEqual(len(set(texts)), 4)
        asyncio.run(scenario())

    def test_actual_ha_receipt_pins_current_source_and_declares_visible_acceptance_open(self):
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root/'examples/client_contracts/session_forecast_v1/observed-queue-bulletin-actual-ha.json').read_text())
        import hashlib
        self.assertEqual(fixture['state'], 'PASS')
        self.assertEqual(len(fixture['cases']), 20)
        self.assertEqual({r['locale'] for r in fixture['cases']}, {'en','nl','de','fr','es'})
        self.assertTrue(all(r['late_queue_discarded'] for r in fixture['stale_results']))
        self.assertEqual(fixture['installed'], 'NOT_RUN')
        self.assertEqual(fixture['native'], 'NOT_RUN')
        for path, sha in fixture['source_sha256'].items():
            self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(), sha, path)

    def test_up_next_rechecks_original_authority_after_lock_wait(self):
        async def scenario():
            manager, active = await self.start()
            allowed = [True]
            await manager._lock.acquire()
            task = asyncio.create_task(manager.async_update_next_item_projection(
                owner_profile_id='owner', session_id=active.session_id,
                media_identity='spotify:track:'+'A'*22, target_name='',
                up_next={'title':'Late stale track','artist':'Artist'}, authority=lambda:allowed[0]))
            await asyncio.sleep(0)
            allowed[0] = False
            manager._lock.release()
            self.assertFalse(await task)
            self.assertEqual(active.broadcast.state.playback.up_next, ())
        asyncio.run(scenario())

    def test_wrong_owner_item_output_and_late_revocation_cannot_publish(self):
        async def scenario():
            manager, active = await self.start()
            f = active.broadcast.forecast
            preview = {'deadline':f.clock()+20,'wall_deadline':time.time()+20,'items':[{'title':'Do not leak','artist':'Artist','genres':[]}]}
            args = dict(owner_profile_id='owner',session_id=active.session_id,
                        media_identity='spotify:track:'+'A'*22,target_name='',preview=preview,authority=lambda:True)
            for changes in ({'owner_profile_id':'other'}, {'session_id':'old'},
                            {'media_identity':'spotify:track:'+'B'*22}, {'target_name':'other'},
                            {'authority':lambda:False}):
                self.assertFalse(await manager.async_update_forecast_queue(**(args|changes)))
            allowed = [True]
            await manager.async_update_forecast_queue(**(args|{'authority':lambda:allowed[0]}))
            allowed[0] = False
            self.assertEqual(f.as_dict()['summary'], '')
            self.assertTrue(f.tick())
            self.assertTrue(f.withdrawn)
            self.assertEqual(f._queue, {})
        asyncio.run(scenario())

