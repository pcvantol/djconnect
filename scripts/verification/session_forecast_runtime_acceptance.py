"""Real paired HA Forecast chain; external Spotify/CDN are explicit fixtures."""
from __future__ import annotations
import asyncio
import base64
import copy
import json
from unittest.mock import patch

from narrative_album_runtime_acceptance import AlbumLab
from custom_components.djconnect.session_runtime import DJPersona
from homeassistant.helpers import aiohttp_client

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6rVQAAAAASUVORK5CYII=')
ARTIST = 'X'*22


class RemoteImage:
    status = 200
    headers = {'Content-Type': 'image/png'}
    content = None

    def __init__(self):
        self.content = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def iter_chunked(self, size):
        yield PNG


class ForecastLab(AlbumLab):
    def __init__(self, *args):
        super().__init__(*args)
        self.cdn_calls = 0
        self.cdn_patch = None
        self.delayed_artist = None

    async def provider(self, backend, method, path, **kwargs):
        if path == '/artists/'+ARTIST:
            self.calls += 1
            if self.delayed_artist is not None:
                await self.delayed_artist.wait()
            return {'id': ARTIST, 'uri': 'spotify:artist:'+ARTIST, 'type': 'artist',
                    'name': 'Catalog artist', 'external_urls': {'spotify': 'https://open.spotify.com/artist/'+ARTIST},
                    'images': [{'url': 'https://i.scdn.co/image/'+'a'*40, 'width': 1, 'height': 1}]}
        return await super().provider(backend, method, path, **kwargs)

    def begin(self):
        super().begin()
        if self.cdn_patch is None:
            original = aiohttp_client.async_get_clientsession
            lab = self
            class RemoteSession:
                def get(self, url, **kwargs):
                    assert url == 'https://i.scdn.co/image/'+'a'*40
                    assert kwargs.get('allow_redirects') is False
                    lab.cdn_calls += 1
                    return RemoteImage()
            def external_session(hass, *args, **kwargs):
                if hass is lab.hass:
                    return RemoteSession()
                return original(hass, *args, **kwargs)
            self.cdn_patch = patch.object(aiohttp_client, 'async_get_clientsession', external_session)
            self.cdn_patch.start()

    async def forecast(self, *, headers=None, identity=None, session_id=None):
        active = await self.manager.async_get_active('profile-a')
        session_id = session_id or active.session_id
        response = await self.owner['client'].get('/api/djconnect/v1/session/forecast/'+session_id,
            headers=headers if headers is not None else self.owner['headers'],
            params={**(identity or self.owner['identity']), 'contract_version': '1'})
        return response.status, await response.json()

    async def settle_art(self):
        observed = self.observer._spotify_sessions.get('profile-a')
        if observed and observed.enrichment_task:
            await observed.enrichment_task
        if observed and observed.forecast_art_task:
            await observed.forecast_art_task
        if observed and observed.remove_listener:
            observed.remove_listener()
            observed.remove_listener = None
        if observed and observed.remove_progress_listener:
            observed.remove_progress_listener()
            observed.remove_progress_listener = None

    async def qualify(self, client, identity, headers):
        self.owner = {'client': client, 'identity': identity, 'headers': headers}
        rows, fixtures = [], []
        for locale in ('en','nl','de','fr','es'):
            for persona in DJPersona:
                active = await self.start(locale=locale, persona=persona, direct_persona=True)
                status, before = await self.forecast()
                assert status == 200 and before['forecast']['sections'] == []
                ws, initial = await self.live()
                await self.step(1)
                await self.settle_art()
                status, after = await self.forecast()
                forecast = after['forecast']
                assert status == 200 and forecast['state'] == 'ready', after
                assert len(forecast['sections']) == 3 and len(forecast['imagery']) == 1, forecast
                image = forecast['imagery'][0]
                assert image['subject']['type'] == 'artist' and image['role'] == 'current'
                image_response = await client.get(image['url'])
                assert image_response.status == 200 and await image_response.read() == PNG
                assert image_response.headers['Cache-Control'] == 'no-store'
                provider_before, cdn_before = self.calls, self.cdn_calls
                immutable = copy.deepcopy((active.planner.as_dict(), {k:v for k,v in active.presence_ledger.__dict__.items() if k != 'clock'},
                                           [m.as_dict() for m in active.broadcast.state.dj_moments]))
                for _ in range(10):
                    assert (await self.forecast())[1] == after
                    r = await client.get(image['url'])
                    assert await r.read() == PNG
                assert (self.calls, self.cdn_calls) == (provider_before, cdn_before)
                assert immutable == (active.planner.as_dict(), {k:v for k,v in active.presence_ledger.__dict__.items() if k != 'clock'},
                                     [m.as_dict() for m in active.broadcast.state.dj_moments])
                envelopes = []
                while True:
                    event = await asyncio.wait_for(ws.receive_json(), 5)
                    envelopes.append(event)
                    if event.get('data',{}).get('payload',{}).get('session_forecast',{}).get('imagery'):
                        break
                await ws.close()
                recovered_ws, recovery = await self.live()
                await recovered_ws.close()
                assert (await self.forecast())[1]['forecast']['valid_until'] == forecast['valid_until']
                public = active.broadcast.as_dict(include_owner_only=False)['session_forecast']
                assert public == forecast
                for private in ('owner_profile_id','planned_intents','confidence','task_id','music_dna','conversation'):
                    assert private not in json.dumps(forecast)
                rows.append({'language': locale, 'persona': persona.value, 'state':'ready',
                             'current_artist_art':True,'zero_read_product_or_provider_effects':True,
                             'reconnect_deadline_unchanged':True})
                fixtures.append({'language':locale,'persona':persona.value,'initial_snapshot':initial,
                                 'owner_read':after,'live_events':envelopes,'reconnect':recovery})
        active = await self.start()
        await self.step(1)
        await self.settle_art()
        moods = []
        for mood in ('chill','groove','energy','party'):
            a = await self.manager.async_get_active('profile-a')
            r = await client.post('/api/djconnect/v1/session/mood',headers=headers,json={**identity,
                'contract_version':1,'session_id':a.session_id,'selected_mood':mood,'expected_mood_revision':a.mood_revision})
            assert r.status == 200
            moods.append((await self.forecast())[1]['forecast']['sections'][-1]['text'])
        assert len(set(moods)) == 4
        for mode in ('music_only','occasional','balanced','talkative','presenter'):
            await self.presence(mode)
            assert (await self.forecast())[1]['forecast']['state']=='ready'
        assert (await self.forecast(headers={**headers,'Authorization':'Bearer wrong'}))[0] == 401
        assert (await self.forecast(session_id='other-session'))[0] == 404
        original = await self.owner_snapshot()
        ended_id = active.session_id
        await self.start()
        assert (await self.forecast(session_id=ended_id))[0] == 404
        art = original['session_forecast']['imagery'][0]['url']
        assert (await client.get(art)).status == 404
        result = {'qualification':'ISOLATED_REAL_HA_FORECAST_PASS','twenty_chains':rows,
                  'transport_fixtures':fixtures,'four_mood_texts_distinct':True,
                  'all_presence_readable':True,'wrong_authority_and_session_denied':True,
                  'ended_art_denied':True,'provider_calls':self.calls,'cdn_calls':self.cdn_calls,
                  'fixture_boundaries':['SpotifyBackend._request','external CDN aiohttp response'],
                  'native':'NOT_RUN','installed':'NOT_RUN','hardware':'NOT_RUN','joint':'OPEN'}
        return result

    async def stop(self):
        await super().stop()
        if self.cdn_patch:
            self.cdn_patch.stop()
            self.cdn_patch = None
