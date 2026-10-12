"""Real paired HA Forecast chain; external Spotify/CDN are explicit fixtures."""
from __future__ import annotations
import asyncio
import struct
import zlib
import copy
import json
import os
import time
from dataclasses import replace
from unittest.mock import patch

from narrative_album_runtime_acceptance import AlbumLab
from custom_components.djconnect.session_runtime import DJPersona
from homeassistant.helpers import aiohttp_client

def png_chunk(kind, data):
    return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))


# Valid explicit one-pixel external-image fixture; not real provider/hardware evidence.
PNG = (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB',1,1,8,2,0,0,0))
       + png_chunk(b'IDAT', zlib.compress(b'\x00\x60\x70\x80')) + png_chunk(b'IEND', b''))

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

    async def invalid_forecast_requests(self):
        """Actual loaded HA handler validates closed identity before any product work."""
        from custom_components.djconnect.session_forecast_transport import async_handle_forecast
        active = await self.manager.async_get_active('profile-a')
        valid = {**self.owner['identity'], 'contract_version':1, 'session_id':active.session_id}
        cases = [('not_object',None,400), ('extra_owner',{**valid,'owner_profile_id':'profile-a'},400),
                 ('missing_identity',{k:v for k,v in valid.items() if k != 'device_id'},400),
                 ('boolean_version',{**valid,'contract_version':True},400),
                 ('string_version',{**valid,'contract_version':'1'},400),
                 ('unknown_version',{**valid,'contract_version':2},400),
                 ('empty_session',{**valid,'session_id':''},400),
                 ('retired_windows',{**valid,'client_type':'windows'},400),
                 ('unknown_client',{**valid,'client_type':'untrusted'},400),
                 ('unknown_device',{**valid,'device_id':'djconnect-ios-UNKNOWN00000'},401)]
        before = (self.calls,self.cdn_calls,active.broadcast.delivery_sequence,
                  active.planner.as_dict(),copy.deepcopy({k:v for k,v in active.presence_ledger.__dict__.items() if k != 'clock'}))
        results = []
        for name,data,expected in cases:
            result,status = await async_handle_forecast(self.hass,data,headers=self.owner['headers'])
            assert status == expected and result['success'] is False,(name,status)
            results.append({'case':name,'status':status})
        for name,headers in [('missing_bearer',{}),
                             ('mismatched_header',{**self.owner['headers'],'X-DJConnect-Device-ID':'other'})]:
            result,status = await async_handle_forecast(self.hass,valid,headers=headers)
            assert status == 401 and not result['success'],(name,status)
            results.append({'case':name,'status':status})
        assert before == (self.calls,self.cdn_calls,active.broadcast.delivery_sequence,
                          active.planner.as_dict(),{k:v for k,v in active.presence_ledger.__dict__.items() if k != 'clock'})
        return results

    async def authority_cases(self, client):
        """Real ordinary paired peer retains no lease across provider withdrawal."""
        from homeassistant.config_entries import ConfigEntryState
        from custom_components.djconnect.domain.backend.models import MusicBackendState
        from custom_components.djconnect.profile_context import profile_storage
        storage = profile_storage(self.hass)
        peer_identity = {'device_id':'djconnect-macos-ABCDEF123457', 'client_type':'macos'}
        # The legacy pair endpoint uses the currently selected config-flow slot.
        # Select only this owned test slot; the ordinary handler still mints/persists auth.
        self.hass.data['djconnect']['runtime'] = self.hass.data['djconnect']['second-owner']
        try:
            response = await client.post('/api/djconnect/v1/pair', json={**peer_identity, 'pair_code':'234567'})
            paired = await response.json()
        finally:
            self.hass.data['djconnect']['runtime'] = self.integration
        assert response.status == 200 and paired['success']
        peer_headers = {'Authorization':'Bearer '+paired['device_token'],
                        'X-DJConnect-Device-ID':peer_identity['device_id']}
        results = []
        for case in ('backend_disabled', 'account_backend_changed', 'membership_removed',
                     'provider_unloaded', 'provider_replaced', 'provider_generation', 'device_token_rotated', 'manager_generation', 'storage_replaced'):
            await self.start()
            await self.step(1)
            await self.settle_art()
            status, snapshot = await self.forecast(headers=peer_headers, identity=peer_identity)
            assert status == 200, (case, status)
            url = snapshot['forecast']['imagery'][0]['url']
            backend = storage.household.music_backends['spotify_direct']
            account = storage.household.music_accounts['fixture-account']
            entry = self.integration.entry
            generation = getattr(self.integration, '_receiver_end_generation', 0)
            original_entry_data = dict(entry.data)
            manager_generation = self.manager.receiver_entry_generation(entry.entry_id)
            if case == 'backend_disabled':
                storage.household.music_backends['spotify_direct'] = replace(backend, state=MusicBackendState.DISABLED)
            elif case == 'account_backend_changed':
                storage.household.music_accounts['fixture-account'] = replace(account, backend_id='other-backend')
            elif case == 'membership_removed':
                storage.household.music_accounts['fixture-account'] = replace(account, linked_profile_ids=frozenset())
            elif case == 'provider_unloaded':
                entry._async_set_state(self.hass, ConfigEntryState.NOT_LOADED, None)
            elif case == 'provider_replaced':
                self.hass.data['djconnect']['owner-entry'] = object()
            elif case == 'provider_generation':
                self.integration._receiver_end_generation = generation + 1
            elif case == 'storage_replaced':
                from custom_components.djconnect.domain.storage import ProfilePlatformStorage
                self.hass.data['djconnect']['djconnect_profile_platform'] = ProfilePlatformStorage(self.hass)
            elif case == 'manager_generation':
                await self.manager.async_revoke_receiver_end_grants_for_entry(entry.entry_id)
            else:
                self.hass.config_entries.async_update_entry(entry, data={**original_entry_data, 'device_token':'fixture-device-rotated'})
            try:
                denied_status, denied_payload = await self.forecast(headers=peer_headers, identity=peer_identity)
                withdrawn = denied_status == 200 and denied_payload.get('forecast', {}).get('state') == 'withdrawn'
                assert denied_status in (401, 403, 409, 503) or withdrawn or (denied_status == 400 and denied_payload.get('error') == 'profile_backend_account_mismatch'), (case, denied_status, denied_payload.get('error'))
                if withdrawn:
                    assert denied_payload['forecast']['sections'] == [] and denied_payload['forecast']['imagery'] == []
                assert (await client.get(url)).status == 404, case
            finally:
                self.hass.data['djconnect']['djconnect_profile_platform'] = storage
                storage.household.music_backends['spotify_direct'] = backend
                storage.household.music_accounts['fixture-account'] = account
                self.hass.data['djconnect']['owner-entry'] = self.integration
                entry._async_set_state(self.hass, ConfigEntryState.LOADED, None)
                self.integration._receiver_end_generation = generation
                self.manager._receiver_entry_generations[entry.entry_id] = manager_generation
                self.hass.config_entries.async_update_entry(entry, data=original_entry_data)
            results.append({'case':case, 'peer_content_withdrawn':True, 'status':denied_status, 'old_image_denied':True})
        # A normal OAuth refresh-token rotation keeps the exact provider owner.
        await self.start()
        await self.step(1)
        await self.settle_art()
        url = (await self.forecast())[1]['forecast']['imagery'][0]['url']
        entry = self.integration.entry
        previous = dict(entry.data)
        self.hass.config_entries.async_update_entry(entry, data={**previous, 'spotify_refresh_token':'fixture-rotated'})
        try:
            assert (await self.forecast())[0] == 200
            assert (await client.get(url)).status == 200
        finally:
            self.hass.config_entries.async_update_entry(entry, data=previous)
        results.append({'case':'oauth_rotation', 'authority_preserved':True})
        # Canonical source withdrawal during the external metadata await.
        for case in ('backend_disabled', 'device_token_rotated', 'provider_unloaded', 'provider_replaced'):
            await self.start()
            self.delayed_artist = asyncio.Event()
            await self.step(1)
            await asyncio.sleep(0)
            backend = storage.household.music_backends['spotify_direct']
            entry = self.integration.entry
            previous = dict(entry.data)
            if case == 'backend_disabled':
                storage.household.music_backends['spotify_direct'] = replace(backend, state=MusicBackendState.DISABLED)
            elif case == 'device_token_rotated':
                self.hass.config_entries.async_update_entry(entry, data={**previous, 'device_token':'fixture-device-rotated'})
            elif case == 'provider_unloaded':
                entry._async_set_state(self.hass, ConfigEntryState.NOT_LOADED, None)
            else:
                self.hass.data['djconnect']['owner-entry'] = object()
            self.delayed_artist.set()
            try:
                await self.settle_art()
                active = await self.manager.async_get_active('profile-a')
                assert active.broadcast.forecast_artwork.assets == (), case
            finally:
                self.delayed_artist = None
                storage.household.music_backends['spotify_direct'] = backend
                self.hass.data['djconnect']['owner-entry'] = self.integration
                entry._async_set_state(self.hass, ConfigEntryState.LOADED, None)
                self.hass.config_entries.async_update_entry(entry, data=previous)
            results.append({'case':'inflight_'+case, 'no_asset_committed':True})
        return results

    async def duration_case(self):
        """Real wall-clock source expiry, independent of modeled input spacing."""
        seconds = int(os.environ.get('DJC_FORECAST_DURATION', '0'))
        if not seconds:
            return {'state':'NOT_RUN'}
        assert 121 <= seconds <= 180
        await self.start()
        await self.presence('music_only')
        await self.step(1)
        await self.settle_art()
        before = (await self.forecast())[1]['forecast']
        active = await self.manager.async_get_active('profile-a')
        ledger = {k:v for k,v in active.presence_ledger.__dict__.items() if k != 'clock'}
        moments = active.broadcast.state.dj_moments
        calls = (self.calls, self.cdn_calls)
        start, reads = time.monotonic(), 0
        while time.monotonic() - start < seconds:
            await asyncio.sleep(1)
            status, value = await self.forecast()
            assert status == 200
            assert value['forecast']['valid_until'] == before['valid_until']
            reads += 1
        expired = (await self.forecast())[1]['forecast']
        assert expired['state'] == 'expired' and expired['imagery'] == [] and expired['sections'] == []
        for mood in ('energy', 'party', 'chill', 'groove'):
            active = await self.manager.async_update_mood(owner_profile_id='profile-a',session_id=active.session_id, selected_mood=mood)
            assert (await self.forecast())[1]['forecast']['state'] == 'expired'
        assert active.broadcast.state.dj_moments == moments
        assert {k:v for k,v in active.presence_ledger.__dict__.items() if k != 'clock'} == ledger
        assert (self.calls, self.cdn_calls) == calls
        await self.step(1)
        await self.settle_art()
        assert (await self.forecast())[1]['forecast']['state'] == 'ready'
        return {'state':'PASS', 'real_elapsed_seconds':round(time.monotonic()-start,3),
                'reads':reads,'zero_read_or_settings_source_renewal':True,
                'off_zero_new_moments':True,'fresh_observation_recovers':True}

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
        invalid_requests = await self.invalid_forecast_requests()
        authority_cases = await self.authority_cases(client)
        duration = await self.duration_case()
        result = {'invalid_requests':invalid_requests,'authority_cases':authority_cases,'duration':duration,'qualification':'ISOLATED_REAL_HA_FORECAST_PASS','twenty_chains':rows,
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
