"""Owned ordinary-pairing HA Session image qualification.

Core registration/storage/projection/auth/image code is real. Only external
Spotify, knowledge-source and CDN responses are fixtures. No installed/native
or hardware claim follows this lab. Bounds: one networkless 1GiB/2CPU container.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import secrets
import sys
import socket
import time
import hashlib
import struct
import zlib
from aiohttp import web
from urllib.parse import urlsplit
from dataclasses import replace
from aiohttp import ClientSession
from homeassistant.helpers import aiohttp_client

from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/verification"))
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.music_dna import MusicDNAManager  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.persistence import (  # noqa: E402
    async_initialize_persistence,
    async_shutdown_persistence,
)
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402


async def main():
    directory = Path(os.environ.get("DJC_LAB_ROOT", "/lab"))
    config = Path(os.environ['DJC_MEDIA_REOPEN_CONFIG']) if os.environ.get('DJC_MEDIA_REOPEN_CONFIG') else directory / ("paired-config-" + secrets.token_hex(4))
    config.mkdir(parents=True,exist_ok=True)
    hass = HomeAssistant(str(config))
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.state = CoreState.running
    hass.config.language = "nl"
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(
        cors_origins=[],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    identity = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"}
    slot = entry(
        "owner-entry",
        {
            **identity,
            "pair_code": "123456",
            "music_backend": "spotify_direct",
            "profile_id": "profile-a",
            "music_account_id": "fixture-account",
            "spotify_client_id": "fixture-client",
            "spotify_refresh_token": "fixture-provider-only",
        },
    )
    # A configured slot, not a paired token. The real HTTP pair handler mints it.
    second_identity = {"device_id": "djconnect-macos-ABCDEF123457", "client_type": "macos"}
    second_slot = entry(
        "second-owner",
        {
            **second_identity,
            "profile_backend_entry_id": "owner-entry",
            "pair_code": "234567",
            "music_backend": "spotify_direct",
            "profile_id": "profile-a",
            "music_account_id": "fixture-account",
            "spotify_client_id": "fixture-client",
            "spotify_refresh_token": "fixture-provider-only",
        },
    )
    store = ConfigEntryStore(hass)
    await store.async_save({"entries": [slot.as_storage_fragment, second_slot.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    slot = hass.config_entries.async_get_entry("owner-entry")
    slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    second_slot = hass.config_entries.async_get_entry("second-owner")
    second_slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    second_runtime = DJConnectRuntime(second_slot)
    runtime = DJConnectRuntime(slot)
    runtime.memory = MusicDNAManager(hass)
    await runtime.memory.async_load()
    hass.data["djconnect"] = {
        "owner-entry": runtime,
        "second-owner": second_runtime,
        "runtime": runtime,
    }
    storage = ProfilePlatformStorage(hass)
    hass.data["djconnect"]["djconnect_profile_platform"] = storage
    await storage.async_upsert_music_backend(
        "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Fixture Spotify"
    )
    existing = await storage.async_load()
    for profile in ("profile-a", "profile-other"):
        if profile in existing.profiles:
            continue
        await storage.async_create_profile(
            profile, profile_id=profile, default_backend_id="spotify_direct"
        )
    await storage.async_upsert_music_account(
        "fixture-account",
        "spotify_direct",
        kind=MusicAccountKind.PERSONAL,
        display_name="Fixture provider account",
        linked_profile_ids=frozenset({"profile-a"}),
        provider_account_id="fixture-client",
    )
    profile = storage.household.profiles["profile-a"]
    await storage.async_update_profile(
        "profile-a",
        preferences=replace(profile.preferences, default_music_account_id="fixture-account"),
    )
    await storage.async_upsert_device(identity["device_id"], "ios", linked_profile_id="profile-a")
    await storage.async_upsert_device(
        second_identity["device_id"], "macos", linked_profile_id="profile-a"
    )
    service = await async_initialize_persistence(hass)
    manager = SessionRuntimeManager(
        PersistentSessionRepository(service),
        HistoricalProjectionRepository(service),
    )
    hass.data["djconnect"]["session_runtime_manager"] = manager
    provider_session = ClientSession()
    cache_key = aiohttp_client._make_key(
        True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT
    )
    hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})[cache_key] = provider_session
    register_http_views(hass)
    await websocket_api.async_setup(hass, {})
    from custom_components.djconnect.spotify_backend import SpotifyBackend
    from custom_components.djconnect.session_facts import SessionFactsResolver
    from custom_components.djconnect.playback_observation import playback_observation_manager

    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (ROOT/'custom_components/djconnect').rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts}
    calls = []
    selected = ['A']
    image_mode = ['ok']
    provider_mode = ['ok']
    began = time.monotonic()
    album_id, artist_id = 'B'*22, 'C'*22
    mbid, rid = '12345678-1234-1234-1234-123456789abc', '22345678-1234-1234-1234-123456789abc'
    images = [{'url': 'https://i.scdn.co/image/'+'a'*40, 'width': 64, 'height': 64}]

    def subject(kind, identifier):
        item = {'id': identifier, 'uri': 'spotify:'+kind+':'+identifier, 'type': kind,
                'name': 'Fixture '+kind, 'external_urls': {'spotify': 'https://open.spotify.com/'+kind+'/'+identifier}}
        if kind == 'track':
            other = identifier == 'D'*22
            item.update(duration_ms=240000, artists=[{'id': 'Z'*22 if other else artist_id,
                                                      'name': 'Southline' if other else 'Northline'}],
                        external_ids={'isrc': 'USAAA0100002' if other else 'USAAA0100001'},
                        album={**subject('album', 'E'*22 if other else album_id),
                               'release_date': '2001-04-02', 'release_date_precision': 'day'})
        else:
            item['images'] = ([{**images[0], 'url': 'https://i.scdn.co/image/'+'c'*40}]
                              if kind == 'artist' else images)
        return item

    async def provider(self, method, path, **kwargs):
        calls.append({'boundary': 'external_spotify_fixture', 'path': path})
        if path == '/me/player':
            return {'is_playing': True, 'progress_ms': 20000+int((time.monotonic()-began)*1000),
                    'item': subject('track', selected[0]*22), 'device': {'name': 'Fixture output', 'id': 'fixture-output'}}
        if path == '/me/player/queue':
            return {'queue': []}
        if path.startswith('/me/tracks/contains'):
            return [False]
        for kind in ('track', 'album', 'artist'):
            if path.startswith('/'+kind+'s/'):
                value=subject(kind,path.rsplit('/',1)[1])
                if kind=='track' and provider_mode[0]=='edition_mismatch':
                    value['album']=subject('album','Z'*22)
                return value
        if path.startswith('/artists'):
            return {'artists': [subject('artist', artist_id)]}
        raise AssertionError('Undeclared provider boundary '+path)

    async def source_get(self, path, params=None, *, wikidata=False):
        calls.append({'boundary': 'external_knowledge_fixture', 'path': path})
        credit = [{'artist': {'id': mbid, 'name': 'Northline'}}]
        if path.startswith('isrc/'):
            return {'recordings': [{'id': rid, 'title': 'Fixture track', 'artist-credit': credit}]}
        if path.startswith('recording/'):
            return {'id': rid, 'title': 'Fixture track', 'artist-credit': credit, 'relations': []}
        if path.startswith('artist/'):
            return {'id': mbid, 'name': 'Northline', 'type': 'Group', 'life-span': {'begin': '1991'},
                    'relations': [{'type': 'streaming', 'url': {'resource': 'https://open.spotify.com/artist/'+artist_id}}]}
        return {}

    def png(color):
        def chunk(kind, data):
            return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
        return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',64,64,8,2,0,0,0))
                +chunk(b'IDAT',zlib.compress(b''.join(b'\0'+bytes(color)*64 for _ in range(64))))+chunk(b'IEND',b''))
    pixels = {'a'*40: png((30,100,160)), 'c'*40: png((160,80,30))}
    image_app = web.Application()
    image_entered, image_release = asyncio.Event(), asyncio.Event()
    async def image_wire(request):
        assert 'Authorization' not in request.headers and 'Cookie' not in request.headers
        calls.append({'boundary': 'external_cdn_fixture', 'path': request.path})
        mode=image_mode[0]
        if mode=='blocked':
            image_entered.set()
            await image_release.wait()
        if mode=='429':
            return web.Response(status=429,headers={'Retry-After':'60'})
        if mode=='redirect':
            return web.Response(status=302,headers={'Location':'http://127.0.0.1/private'})
        if mode=='oversize':
            return web.Response(body=b'\x89PNG\r\n\x1a\n'+b'x'*(2*1024*1024),content_type='image/png')
        if mode=='invalid_decode':
            return web.Response(body=b'\x89PNG\r\n\x1a\n'+b'not an image',content_type='image/png')
        return web.Response(body=pixels[request.match_info['asset']], content_type='image/png')
    image_app.router.add_get('/image/{asset}', image_wire)
    image_client = TestClient(TestServer(image_app))
    await image_client.start_server()
    class Network:
        def get(self, url, **kwargs):
            u = urlsplit(url)
            assert u.scheme == 'https' and u.hostname == 'i.scdn.co' and kwargs.get('allow_redirects') is False
            return image_client.get(u.path, **kwargs)
    hass.data[aiohttp_client.DATA_CLIENTSESSION][cache_key] = Network()
    SpotifyBackend._request = provider
    SessionFactsResolver._get = source_get
    cases = {}
    async with TestClient(TestServer(hass.http.app)) as client:
        pair = await client.post('/api/djconnect/v1/pair', json={**identity, 'pair_code': '123456'})
        paired = await pair.json()
        assert pair.status == 200 and paired['success']
        headers = {'Authorization': 'Bearer '+paired['device_token'], 'X-DJConnect-Device-ID': identity['device_id']}
        async def post(path, payload):
            response = await client.post('/api/djconnect/v1'+path, json=payload, headers=headers)
            body = await response.json()
            assert response.status in (200,201), (response.status,body)
            return body
        async def get(path, *, auth=True):
            r = await client.get('/api/djconnect/v1'+path, params=identity, headers=headers if auth else {})
            return r, await r.json()
        if os.environ.get('DJC_MEDIA_REOPEN_CONFIG'):
            _, listing=await get('/session/history')
            old_session=listing['sessions'][0]['session_id']
            _, old_page=await get('/session/history/'+old_session)
            old_entry=next(e for e in old_page['entries'] if e['kind']=='playback_observed')
            stored=await HistoricalProjectionRepository(service).async_entry_record('profile-a',old_session,old_entry['entry_id'])
            raw_body=json.loads(stored['body'])
            assert not raw_body.get('album_uri') and 'session_media_reference' not in raw_body
            reply=await post('/session/media/prepare',{**identity,'contract_version':1,'session_id':old_session,
                             'targets':[{'entry_id':old_entry['entry_id']}]})
            art=reply['session_media'][0]['artwork']
            assert art['state']=='ready' and art['resolution_basis']=='resolved_now'
            assert art['edition_basis']=='provider_resolved_now'
            r=await client.get(art['url'],params=identity,headers=headers)
            assert r.status==200 and await r.read()==pixels['a'*40]
            (directory/'legacy-reopened.json').write_text(json.dumps({'ordinary_pairing':True,
                'actual_predecessor_sqlite_store':True,'no_runtime_restored':not manager._active_by_profile,
                'old_stored_body':raw_body,'response':reply,'source_hashes':source_hashes},indent=2)+'\n')
            print('LEGACY_REOPEN_PASS',flush=True)
            hass.data[aiohttp_client.DATA_CLIENTSESSION][cache_key]=provider_session
            await image_client.close()
            await provider_session.close()
            await async_shutdown_persistence(hass)
            await hass.async_stop()
            return
        start_clock=time.monotonic()
        started = await post('/session/start', {**identity,'mood':'groove','locale':'nl'})
        sid = started['session']['session_id']
        start_latency=time.monotonic()-start_clock
        print('STARTED',flush=True)
        _, first_timeline = await get('/session/history/'+sid)
        playback = next(e for e in first_timeline['entries'] if e['kind']=='playback_observed')
        image_clock=time.monotonic()
        early = await post('/session/media/prepare', {**identity,'contract_version':1,'session_id':sid,
                           'targets':[{'entry_id':playback['entry_id']}]})
        cover = early['session_media'][0]
        assert cover['artwork']['state']=='ready', cover
        r = await client.get(cover['artwork']['url'],params=identity,headers=headers)
        assert r.status==200 and await r.read()==pixels['a'*40]
        first_image_latency=time.monotonic()-image_clock
        cases['playback_cover']={'projection':cover,'bytes_sha256':hashlib.sha256(pixels['a'*40]).hexdigest()}
        for _ in range(24):
            active = await manager.async_get_active('profile-a')
            moments = [m for m in active.broadcast.state.dj_moments if getattr(m,'source_fact',None)]
            for candidate in moments:
                if candidate.source_fact.intent=='album_story' and 'album_story' not in cases:
                    art = await post('/session/media/prepare',{**identity,'contract_version':1,'session_id':sid,
                                     'targets':[{'moment_id':candidate.moment_id}]})
                    media = art['session_media'][0]
                    if media['artwork']['state']=='ready':
                        assert media['artwork']['subject']['uri']=='spotify:album:'+album_id
                        cases['album_story']={'projection':media}
            if any(m.source_fact.intent == 'artist_story' for m in moments) and 'album_story' in cases:
                break
            await asyncio.sleep(4)
            observed = playback_observation_manager(hass)._spotify_sessions['profile-a']
            await playback_observation_manager(hass)._async_poll_spotify(observed)
        assert 'album_story' in cases
        assert any(m.source_fact.intent == 'artist_story' for m in moments), [m.moment_type.value for m in moments]
        # Keep the already published artist A while ordinary observation moves to B.
        await post('/session/presence', {**identity,'contract_version':1,'session_id':sid,
                   'selected_presence':'music_only','expected_presence_revision':0})
        selected[0]='D'
        observed = playback_observation_manager(hass)._spotify_sessions['profile-a']
        await playback_observation_manager(hass)._async_poll_spotify(observed)
        before_ids = [m.moment_id for m in active.broadcast.state.dj_moments]
        for moment in [m for m in moments if m.source_fact.intent=='artist_story']:
            ready = await post('/session/media/prepare', {**identity,'contract_version':1,'session_id':sid,
                               'targets':[{'moment_id': moment.moment_id}]})
            media = ready['session_media'][0]
            assert media['artwork']['state'] == 'ready', media
            url = media['artwork']['url']
            r = await client.get(url, params=identity, headers=headers)
            assert r.status == 200 and r.headers['Cache-Control'] == 'no-store'
            data = await r.read()
            expected = 'c'*40 if ':artist:' in media['artwork']['subject']['uri'] else 'a'*40
            assert data == pixels[expected]
            denied = await client.get(url, params=identity)
            assert denied.status in (401,403)
            assert media['artwork']['subject']['uri']=='spotify:artist:'+artist_id
            cases[moment.source_fact.intent] = {'current_recording': 'spotify:track:'+'D'*22, 'current_artist': 'spotify:artist:'+'Z'*22,'projection':media,'bytes_sha256':hashlib.sha256(data).hexdigest(),'denied_status':denied.status}
        assert before_ids == [m.moment_id for m in active.broadcast.state.dj_moments]
        for identifier in ('F','G','H','I'):
            selected[0]=identifier
            await playback_observation_manager(hass)._async_poll_spotify(observed)
        _, all_entries=await get('/session/history/'+sid)
        negative_entries=[e for e in all_entries['entries'] if e['kind']=='playback_observed'
                          and e['entry_id']!=playback['entry_id']]
        await post('/session/end', {**identity,'session_id':sid})
        # Old stored exact identity, original source authority, real owner query.
        ready = await post('/session/media/prepare', {**identity,'contract_version':1,'session_id':sid,
                           'targets':[{'entry_id': playback['entry_id']}]})
        historical = ready['session_media'][0]
        assert historical['artwork']['state']=='ready' and historical['artwork']['historical_display_allowed'], historical
        r = await client.get(historical['artwork']['url'], params=identity, headers=headers)
        assert r.status == 200 and await r.read()==pixels['a'*40]
        before_calls=len(calls)
        for _ in range(3):
            _, stored = await get('/session/history/'+sid)
            assert any(e.get('session_media') for e in stored['entries'])
        assert len(calls)==before_calls
        cases['older_entry_refresh']={'projection':historical,'pure_reads_provider_calls':0}

        history_before=await HistoricalProjectionRepository(service).async_session_record(sid)
        stored_before=await service.async_in_transaction(lambda tx:tx.fetchall("SELECT * FROM djconnect_session_summaries WHERE session_id=?",(sid,)))
        await asyncio.gather(*(post('/session/media/prepare',{**identity,'contract_version':1,'session_id':sid,
                               'targets':[{'entry_id':playback['entry_id']}]}) for _ in range(5)))
        history_after=await HistoricalProjectionRepository(service).async_session_record(sid)
        assert history_before['revision']==history_after['revision']
        stored_after=await service.async_in_transaction(lambda tx:tx.fetchall("SELECT * FROM djconnect_session_summaries WHERE session_id=?",(sid,)))
        assert stored_before==stored_after
        def stable(value):
            if isinstance(value,dict):
                return {k:stable(v) for k,v in value.items() if k!='as_of'}
            return value
        assert stable(history_before['summary'])==stable(history_after['summary'])
        assert len(calls)==before_calls
        cases['duplicate_prepare_reads_no_semantic_mutation']={'provider_calls':0,'history_revision_equal':True,'summary_equal':True}
        assert len(negative_entries)>=5
        for row,mode in zip(negative_entries,('429','redirect','oversize','invalid_decode','edition_mismatch')):
            provider_mode[0]='edition_mismatch' if mode=='edition_mismatch' else 'ok'
            image_mode[0]='ok' if mode=='edition_mismatch' else mode
            result=await post('/session/media/prepare',{**identity,'contract_version':1,'session_id':sid,
                              'targets':[{'entry_id':row['entry_id']}]})
            assert result['session_media'][0]['artwork']['state']=='unavailable',result
            previous=len(calls)
            repeated=await post('/session/media/prepare',{**identity,'contract_version':1,'session_id':sid,
                                'targets':[{'entry_id':row['entry_id']}]})
            assert repeated['session_media'][0]['artwork']['reason']=='backoff' and len(calls)==previous
            cases[mode]={'state':'unavailable','retry':'backoff','retry_provider_calls':0}
        image_mode[0]='ok'
        provider_mode[0]='ok'
        denied=await client.post('/api/djconnect/v1/session/media/prepare',headers=headers,
                                json={**identity,'contract_version':1,'session_id':sid,
                                      'targets':[{'entry_id':playback['entry_id'],'subject':'injected'}]})
        assert denied.status==400
        cases['untrusted_subject_rejected']={'status':denied.status}
        # Select the second configured slot; the real pairing handler still
        # validates its code/client type and mints the ordinary device token.
        hass.data['djconnect']['runtime']=second_runtime
        try:
            second_pair=await client.post('/api/djconnect/v1/pair',json={**second_identity,'pair_code':'234567'})
        finally:
            hass.data['djconnect']['runtime']=runtime
        second_paired=await second_pair.json()
        assert second_pair.status==200, (second_pair.status, second_paired.get("error"))
        second_headers={'Authorization':'Bearer '+second_paired['device_token'],
                        'X-DJConnect-Device-ID':second_identity['device_id']}
        await storage.async_upsert_device(second_identity['device_id'],'macos',linked_profile_id='profile-other')
        denied=await client.get(historical['artwork']['url'],params=second_identity,headers=second_headers)
        assert denied.status in (401,403,404,409)
        cases['other_profile_denied']={'status':denied.status}
        # Ordinary Profile commits revoke bytes immediately and latch an already
        # running external request, even when binding returns before it completes.
        await storage.async_upsert_device(identity['device_id'],'ios',linked_profile_id='profile-other')
        await storage.async_upsert_device(identity['device_id'],'ios',linked_profile_id='profile-a')
        image_mode[0]='blocked'
        pending=asyncio.create_task(post('/session/media/prepare',{**identity,'contract_version':1,'session_id':sid,
                                   'targets':[{'entry_id':playback['entry_id']}]}))
        await asyncio.wait_for(image_entered.wait(),10)
        await storage.async_upsert_device(identity['device_id'],'ios',linked_profile_id='profile-other')
        await storage.async_upsert_device(identity['device_id'],'ios',linked_profile_id='profile-a')
        image_release.set()
        race=await pending
        assert race['session_media'][0]['artwork']['state']=='withdrawn',race
        assert 'url' not in race['session_media'][0]['artwork']
        image_mode[0]='ok'
        restored=await post('/session/media/prepare',{**identity,'contract_version':1,'session_id':sid,
                            'targets':[{'entry_id':playback['entry_id']}]})
        historical=restored['session_media'][0]
        assert historical['artwork']['state']=='ready'
        cases['binding_away_and_back_inflight']={'state':'withdrawn','old_url':False,'fresh_explicit_prepare':'ready'}
        if os.environ.get('DJC_MEDIA_REAL_EXPIRY')=='1':
            captured=time.monotonic()
            await asyncio.sleep(301)
            registry=hass.data['djconnect']['session_images']
            asset_id=historical['artwork']['url'].rsplit('/',1)[-1]
            assert not any(a['asset_id']==asset_id for a in registry.assets.values())
            expired=await client.get(historical['artwork']['url'],params=identity,headers=headers)
            assert expired.status==404
            cases['expiry']={'image_status':expired.status,'real_elapsed_seconds':time.monotonic()-captured,'idle_bytes_removed_before_read':True}
        else:
            cases['expiry']={'state':'NOT_RUN_REAL_TIME','unit_clock_tests_separate':True}
        fresh=await post('/session/media/prepare',{**identity,'contract_version':1,'session_id':sid,
                         'targets':[{'entry_id':playback['entry_id']}]})
        historical=fresh['session_media'][0]
        assert historical['artwork']['state']=='ready'
        await storage.async_upsert_music_account('fixture-account','spotify_direct',kind=MusicAccountKind.PERSONAL,
            display_name='Fixture provider account',linked_profile_ids=frozenset(),provider_account_id='fixture-client')
        withdrawn=await client.get(historical['artwork']['url'],params=identity,headers=headers)
        assert withdrawn.status in (401,403,404,409)
        cases['source_withdrawal']={'status':withdrawn.status}
        assert source_hashes=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (ROOT/'custom_components/djconnect').rglob('*')
                              if p.is_file() and '__pycache__' not in p.parts}
        (directory/'session-artwork.json').write_text(json.dumps({'ordinary_pairing':True,'broad_ha_credentials':False,
            'source_hashes':source_hashes,'cases':cases,'external_fixture_calls':calls,
            'session_start_seconds':start_latency,'first_image_seconds':first_image_latency,
            'elapsed_seconds':time.monotonic()-began,
            'native_acceptance':'OPEN','installed_acceptance':'NOT_RUN','hardware_acceptance':'NOT_CLAIMED'},indent=2)+'\n')
        print(json.dumps({'cases':list(cases),'source_files':len(source_hashes)}),flush=True)
    hass.data[aiohttp_client.DATA_CLIENTSESSION][cache_key]=provider_session
    await image_client.close()
    await provider_session.close()
    await async_shutdown_persistence(hass)
    await hass.async_stop()


asyncio.run(main())
