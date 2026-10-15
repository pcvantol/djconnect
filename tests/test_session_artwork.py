"""Subject and bounded resource invariants; real HA acceptance is separate."""
import importlib
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_session_runtime as runtime_tests


class SessionArtworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = runtime_tests._load_runtime_module()
        cls.art = importlib.import_module('custom_components.djconnect.session_artwork')
        cls.proxy = importlib.import_module('custom_components.djconnect.image_proxy')
        cls.facts = importlib.import_module('custom_components.djconnect.session_facts')

    @classmethod
    def tearDownClass(cls):
        import sys
        if cls.previous_const is not None:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const

    def test_receiver_snapshot_and_real_incremental_events_never_carry_owner_media(self):
        import asyncio
        manager=self.runtime.SessionRuntimeManager()
        active=asyncio.run(manager.async_start(owner_profile_id='profile-unit'))
        engine=active.broadcast
        engine.media_projector=lambda:[{'private_resource':'owner-only'}]
        receiver=[]
        _,snapshot=engine.subscribe_with_broadcast_token(engine.broadcast_token,receiver.append)
        self.assertNotIn('session_media',snapshot)
        engine._publish(self.runtime.BroadcastEventType.SESSION_FLOW_UPDATED,
                        {'session_flow':engine.state.session_flow.as_dict()})
        self.assertTrue(receiver)
        self.assertNotIn('session_media',receiver[-1]['payload'])
        self.assertIn('session_media',engine.as_dict())

    def test_album_edition_is_source_identity_and_never_current_title(self):
        fact = SimpleNamespace(intent='album_story', source_url='https://open.spotify.com/album/' + 'A'*22,
                               media_identity='spotify:track:' + 'B'*22)
        self.assertEqual(self.art.subject_for_fact(fact), 'spotify:album:' + 'A'*22)
        fact.source_url = 'https://open.spotify.com/album/not-an-id'
        self.assertIsNone(self.art.subject_for_fact(fact))

    def test_artist_never_borrows_recording_cover_without_cross_reference(self):
        fact = SimpleNamespace(intent='artist_story', media_identity='spotify:track:' + 'B'*22)
        self.assertIsNone(self.art.subject_for_fact(fact))
        fact.artwork_subject_uri = 'spotify:artist:' + 'A'*22
        self.assertEqual(self.art.subject_for_fact(fact), fact.artwork_subject_uri)

    def test_musicbrainz_artist_requires_explicit_provider_link(self):
        catalog = {'uri': 'spotify:track:'+'T'*22, 'artist_ids': ['A'*22]}
        person = {'id': '12345678-1234-1234-1234-123456789abc', 'name': 'Same name',
                  'type': 'Group', 'life-span': {'begin': '1991'}, 'relations': []}
        self.assertEqual(self.facts.artist_facts(catalog, person)[0].artwork_subject_uri, '')
        person['relations'] = [{'type': 'streaming', 'url': {'resource': 'https://open.spotify.com/artist/'+'B'*22}}]
        self.assertEqual(self.facts.artist_facts(catalog, person)[0].artwork_subject_uri, '')
        person['relations'][0]['url']['resource'] = 'https://open.spotify.com/artist/'+'A'*22
        self.assertEqual(self.facts.artist_facts(catalog, person)[0].artwork_subject_uri, 'spotify:artist:'+'A'*22)

    def test_wikidata_unique_non_deprecated_artist_reference(self):
        catalog = {'uri': 'spotify:track:'+'T'*22, 'artist': 'A', 'artist_ids': ['A'*22]}
        entity = {'descriptions': {'en': {'value': 'Band'}}, 'claims': {}}
        self.assertEqual(self.facts.description_fact(catalog, entity, 'Q42').artwork_subject_uri, '')
        entity['claims']['P1902'] = [{'mainsnak': {'datavalue': {'value': 'A'*22}}}]
        self.assertEqual(self.facts.description_fact(catalog, entity, 'Q42').artwork_subject_uri, 'spotify:artist:'+'A'*22)
        entity['claims']['P1902'][0]['rank'] = 'deprecated'
        self.assertEqual(self.facts.description_fact(catalog, entity, 'Q42').artwork_subject_uri, '')

    def asset(self, body=b'x', authority=lambda: True):
        return {'body': body, 'deadline': time.monotonic()+300, 'authority': authority}

    def test_capacity_does_not_evict_usable_targets(self):
        registry = self.proxy.ManagedSessionImages()
        for i in range(64):
            self.assertTrue(registry.commit(i, self.asset()))
        self.assertFalse(registry.commit(64, self.asset()))
        self.assertEqual(len(registry.assets), 64)

    def test_failed_target_metadata_is_bounded_independently_of_negative_cache(self):
        registry=self.proxy.ManagedSessionImages()
        for i in range(200):
            registry.record_state(i,'source_withdrawn')
        self.assertEqual(len(registry.states),64)

    def test_aggregate_byte_bound(self):
        registry = self.proxy.ManagedSessionImages()
        for i in range(16):
            self.assertTrue(registry.commit(i, self.asset(b'x'*(2*1024*1024))))
        self.assertFalse(registry.commit(17, self.asset()))

    def test_expiry_and_authority_withdrawal_remove_bytes_without_read_renewal(self):
        registry = self.proxy.ManagedSessionImages()
        asset = self.asset()
        registry.commit('a', asset)
        deadline = asset['deadline']
        self.assertIs(registry.get('a'), asset)
        self.assertEqual(asset['deadline'], deadline)
        with patch('time.monotonic', lambda: deadline):
            self.assertIsNone(registry.get('a'))
        registry.commit('b', self.asset(authority=lambda: False))
        self.assertIsNone(registry.get('b'))

    def test_temporary_withdrawal_latches_pending_work_and_removes_resident_bytes(self):
        registry = self.proxy.ManagedSessionImages()
        granted, valid = [True], [True]
        def authority():
            return granted[0] and valid[0]
        def invalidate():
            valid[0] = False
        key = ('owner', 'session', (('entry_id', 'entry'),))
        registry.work_guards[key] = (authority, invalidate)
        registry.commit(key, self.asset(authority=authority))
        granted[0] = False
        registry.collect()
        granted[0] = True
        self.assertFalse(authority())
        self.assertNotIn(key, registry.assets)
        self.assertEqual(registry.states[key][1], 'source_withdrawn')

    def test_session_end_invalidates_pending_work_only_for_its_session(self):
        registry = self.proxy.ManagedSessionImages()
        valid = [True, True]
        registry.work_guards[('owner', 'session', ())] = (lambda: True, lambda: valid.__setitem__(0, False))
        registry.work_guards[('owner', 'other', ())] = (lambda: True, lambda: valid.__setitem__(1, False))
        registry.end_session('owner', 'session')
        self.assertEqual(valid, [False, True])

    def test_missing_is_no_display_grant_or_url(self):
        result = self.art.unavailable('s', {'entry_id': 'e'}, 'insufficient_identity')
        self.assertNotIn('url', result['artwork'])
        self.assertFalse(result['artwork']['historical_display_allowed'])

    def test_unchanged_projection_has_identical_initial_and_cached_revision(self):
        artwork={'state':'ready','subject':{'uri':'spotify:track:'+'A'*22},
                 'current_display_allowed':True,'active_flow_display_allowed':True,
                 'historical_display_allowed':False}
        revision=self.art.projection_revision(artwork)
        artwork['media_revision']=revision
        original={'revision':revision,'artwork':artwork}
        projected=self.art.project({'projection':original},current=True,historical=False)
        self.assertEqual(projected,original)
        changed=self.art.project({'projection':original},current=False,historical=False)
        self.assertNotEqual(changed['revision'],revision)
        self.assertEqual(changed['artwork']['media_revision'],revision)

    def test_edition_basis_distinguishes_album_identity_from_artist(self):
        self.assertEqual(self.art.edition_basis('spotify:album:'+'A'*22,''),'original_bound')
        self.assertEqual(self.art.edition_basis('spotify:track:'+'A'*22,''),'provider_resolved_now')
        self.assertEqual(self.art.edition_basis('spotify:track:'+'A'*22,'spotify:album:'+'B'*22),'original_bound')
        self.assertEqual(self.art.edition_basis('spotify:artist:'+'A'*22,''),'not_applicable')

    def test_reprojection_does_not_mutate_original_resource(self):
        original = {'schema_version': 1, 'session_id': 's', 'moment_id': 'm', 'revision': 'one',
                    'artwork': {'current_display_allowed': True, 'active_flow_display_allowed': True,
                                'historical_display_allowed': False, 'expires_at': 'original'}}
        projected = self.art.project({'projection': original}, current=False, historical=True)
        self.assertTrue(original['artwork']['current_display_allowed'])
        self.assertFalse(projected['artwork']['current_display_allowed'])
        self.assertTrue(projected['artwork']['historical_display_allowed'])
        self.assertEqual(projected['artwork']['expires_at'], 'original')
        self.assertNotEqual(projected['revision'], original['revision'])


class ManagedSessionExpiryAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import asyncio
        import sys
        self.runtime, self.previous_const = runtime_tests._load_runtime_module()
        self.art = importlib.import_module('custom_components.djconnect.session_artwork')
        self.proxy = importlib.import_module('custom_components.djconnect.image_proxy')
        self.hass = SimpleNamespace(data={'djconnect':{}}, loop=asyncio.get_running_loop(),
                                    bus=SimpleNamespace(async_listen_once=lambda *a: None),
                                    async_create_task=asyncio.create_task)
        with patch.dict(sys.modules, {'homeassistant.const': SimpleNamespace(EVENT_HOMEASSISTANT_STOP='homeassistant_stop')}):
            self.registry = self.proxy.ManagedSessionImages(self.hass)
        self.hass.data['djconnect']['session_images']=self.registry
        self.key=('profile-unit','session-unit',(('entry_id','entry-unit'),))
        self.context=SimpleNamespace(profile_id='profile-unit')

    async def asyncTearDown(self):
        import sys
        self.registry.close()
        if self.previous_const is not None:
            sys.modules['custom_components.djconnect.const']=self.previous_const

    def asset(self, allowed, *, delay=300, authority=lambda: True):
        return {'asset_id':'asset-unit','deadline':time.monotonic()+delay,'body':b'private pixels',
                'mime':'image/png','authority':authority,'allowed':allowed,'expected_source':{}}

    async def test_idle_expiry_removes_actual_resident_bytes_without_any_read(self):
        import asyncio
        async def allowed():
            return True
        self.registry.commit(self.key,self.asset(allowed,delay=0.02))
        await asyncio.sleep(0.05)
        self.assertEqual(self.registry.assets,{})
        self.assertEqual(self.registry.timers,{})
        self.assertEqual(self.registry.states[self.key][1],'expired')

    async def test_deadline_is_checked_again_after_awaiting_history(self):
        async def allowed():
            asset['deadline']=time.monotonic()-1
            return True
        asset=self.asset(allowed)
        self.registry.commit(self.key,asset)
        with patch.object(self.art,'artist_authority',lambda *a,**k:lambda:True):
            result=await self.art.image(self.hass,self.context,'session-unit','asset-unit',runtime=object())
        self.assertIsNone(result)
        self.assertNotIn(self.key,self.registry.assets)

    async def test_source_withdrawal_during_history_await_never_returns_pixels(self):
        granted=[True]
        async def allowed():
            granted[0]=False
            return True
        self.registry.commit(self.key,self.asset(allowed,authority=lambda:granted[0]))
        with patch.object(self.art,'artist_authority',lambda *a,**k:lambda:True):
            result=await self.art.image(self.hass,self.context,'session-unit','asset-unit',runtime=object())
        self.assertIsNone(result)

    async def test_session_end_clears_only_live_resources(self):
        async def allowed():
            return True
        live=self.asset(allowed)
        live['historical']=False
        historical=self.asset(allowed)
        historical['asset_id']='historical'
        historical['historical']=True
        self.registry.commit(self.key,live)
        old=('profile-unit','old-session',(('entry_id','old-entry'),))
        self.registry.commit(old,historical)
        self.registry.end_session('profile-unit','session-unit')
        self.assertNotIn(self.key,self.registry.assets)
        self.assertIn(old,self.registry.assets)

    async def test_total_deadline_includes_wait_for_semaphore_and_never_fetches(self):
        from unittest.mock import AsyncMock
        import sys
        async def allowed():
            return True
        resolved=('spotify:track:'+'A'*22,
                  dict.fromkeys(('backend_id','music_account_id','provider_entry_id','provider_account_id'),'unit'),
                  allowed,False,True,'','playback_thumbnail',lambda:(False,True))
        storage=SimpleNamespace(household=SimpleNamespace(profiles={'profile-unit':SimpleNamespace()}))
        await self.registry.semaphore.acquire()
        await self.registry.semaphore.acquire()
        fetch=AsyncMock(side_effect=AssertionError('No provider work while queued'))
        try:
            with (patch.object(self.art,'PREPARE_TIMEOUT',0.03),
                  patch.object(self.art,'resolve_target',AsyncMock(return_value=resolved)),
                  patch.object(self.art,'artist_authority',lambda *a,**k:lambda:True),
                  patch.dict(sys.modules, {'custom_components.djconnect.profile_context':
                                           SimpleNamespace(profile_storage=lambda h:storage),
                                           'custom_components.djconnect.spotify_backend':
                                           SimpleNamespace(SpotifyBackend=object)}),
                  patch.object(self.art,'_fetch',fetch)):
                entered=time.monotonic()
                result=await self.art.prepare(self.hass,object(),self.context,session_id='session-unit',target={'entry_id':'entry-unit'})
            self.assertLess(time.monotonic()-entered,0.25)
            self.assertEqual(result['artwork']['state'],'unavailable')
            fetch.assert_not_called()
        finally:
            self.registry.semaphore.release()
            self.registry.semaphore.release()

    async def test_complete_deadline_covers_cached_and_initial_history_admission(self):
        import asyncio
        import sys
        from unittest.mock import AsyncMock
        async def blocked():
            await asyncio.Event().wait()
        uri = 'spotify:track:'+'A'*22
        resolved = (uri, dict.fromkeys(('backend_id','music_account_id','provider_entry_id','provider_account_id'),'unit'),
                    blocked,False,True,'','playback_thumbnail',lambda:(False,True))
        storage=SimpleNamespace(household=SimpleNamespace(profiles={'profile-unit':SimpleNamespace()}))
        for cached in (False, True):
            with self.subTest(cached=cached):
                if cached:
                    asset=self.asset(blocked)
                    asset['subject']=uri
                    self.registry.commit(self.key,asset)
                with (patch.object(self.art,'PREPARE_TIMEOUT',0.03),
                      patch.object(self.art,'resolve_target',AsyncMock(return_value=resolved)),
                      patch.object(self.art,'artist_authority',lambda *a,**k:lambda:True),
                      patch.dict(sys.modules, {'custom_components.djconnect.profile_context':
                                               SimpleNamespace(profile_storage=lambda h:storage)})):
                    result=await asyncio.wait_for(self.art.prepare(self.hass,object(),self.context,
                                session_id='session-unit',target={'entry_id':'entry-unit'}),0.25)
                self.assertEqual(result['artwork']['state'],'unavailable')

    async def test_inflight_wait_has_own_deadline_without_cancelling_shared_work(self):
        import asyncio
        import sys
        from unittest.mock import AsyncMock
        async def allowed():
            return True
        resolved=('spotify:track:'+'A'*22,
                  dict.fromkeys(('backend_id','music_account_id','provider_entry_id','provider_account_id'),'unit'),
                  allowed,False,True,'','playback_thumbnail',lambda:(False,True))
        storage=SimpleNamespace(household=SimpleNamespace(profiles={'profile-unit':SimpleNamespace()}))
        pending=asyncio.create_task(asyncio.Event().wait())
        self.registry.inflight[self.key]=pending
        with (patch.object(self.art,'PREPARE_TIMEOUT',0.03),
              patch.object(self.art,'resolve_target',AsyncMock(return_value=resolved)),
              patch.object(self.art,'artist_authority',lambda *a,**k:lambda:True),
              patch.dict(sys.modules, {'custom_components.djconnect.profile_context':
                                       SimpleNamespace(profile_storage=lambda h:storage)})):
            result=await asyncio.wait_for(self.art.prepare(self.hass,object(),self.context,
                        session_id='session-unit',target={'entry_id':'entry-unit'}),0.25)
        self.assertEqual(result['artwork']['state'],'unavailable')
        self.assertFalse(pending.done())

    async def test_unload_removes_stop_listener_once_even_when_closed_twice(self):
        import sys
        from unittest.mock import Mock
        remove=Mock()
        self.hass.bus.async_listen_once=lambda *args:remove
        with patch.dict(sys.modules, {'homeassistant.const': SimpleNamespace(EVENT_HOMEASSISTANT_STOP='homeassistant_stop')}):
            registry=self.proxy.ManagedSessionImages(self.hass)
        registry.close()
        registry.close()
        remove.assert_called_once_with()

    async def test_cancelled_decode_keeps_permit_until_executor_really_finishes(self):
        import asyncio
        future=asyncio.get_running_loop().create_future()
        self.hass.async_add_executor_job=lambda *args:future
        task=asyncio.create_task(self.registry.decode(lambda body:None,b'pixels'))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(future.cancelled())
        self.assertEqual(self.registry.decode_slots._value,1)
        self.registry.close()
        self.assertEqual(self.registry.decode_slots._value,1)
        future.set_result((64,64))
        await asyncio.sleep(0)
        self.assertEqual(self.registry.decode_slots._value,2)

    async def test_actual_stop_does_not_remove_an_already_removed_one_shot_listener(self):
        from unittest.mock import Mock
        remove=Mock()
        self.registry._unsubscribe=remove
        await self.registry._on_stop(None)
        self.assertTrue(self.registry.closed)
        remove.assert_not_called()

    async def test_external_metadata_cannot_change_subject_edition_or_source(self):
        import copy
        import sys
        from unittest.mock import AsyncMock
        uri='spotify:track:'+'A'*22
        item={'id':'A'*22,'uri':uri,'type':'track','name':'Fixture track',
              'external_urls':{'spotify':'https://open.spotify.com/track/'+'A'*22},
              'album':{'id':'B'*22,'uri':'spotify:album:'+'B'*22,
                       'images':[{'url':'https://i.scdn.co/image/'+'a'*40}]}}
        pixels=(__import__('pathlib').Path(__file__).resolve().parents[1]/
                'examples/client_contracts/session_artwork_v1/assets/cover.png').read_bytes()
        async def chunks(_size):
            yield pixels
        response=SimpleNamespace(status=200,headers={'Content-Type':'image/png'},
                                 content=SimpleNamespace(iter_chunked=chunks))
        class Wire:
            async def __aenter__(self):
                return response
            async def __aexit__(self,*args):
                return None
        network=SimpleNamespace(get=lambda *args,**kwargs:Wire())
        cases=[('id','wrong','subject_mismatch'),('external_urls',{},'subject_mismatch'),
               ('album',None,'missing_edition'),('name','','missing_subject_label')]
        for field,value,reason in cases:
            with self.subTest(field=field):
                candidate=copy.deepcopy(item)
                candidate[field]=value
                with (patch.dict(sys.modules,{'aiohttp':SimpleNamespace(ClientTimeout=lambda **kwargs:None),
                                              'homeassistant.helpers.aiohttp_client':
                                              SimpleNamespace(async_get_clientsession=lambda hass:network)}),
                      patch.object(self.registry,'decode',AsyncMock(return_value=(64,64)))):
                    with self.assertRaisesRegex(ValueError,'^'+reason+'$'):
                        await self.art._fetch(self.hass,SimpleNamespace(_request=AsyncMock(return_value=candidate)),
                                              uri,guard=AsyncMock(),expected_album_uri='spotify:album:'+'B'*22)
        for album,reason in (({'id':'wrong','uri':'spotify:album:'+'B'*22},'missing_edition'),
                             ({'id':'B'*22,'uri':'spotify:album:'+'B'*22,'images':None},'missing_image'),
                             ({'id':'B'*22,'uri':'spotify:album:'+'B'*22,'images':[{'url':'https://evil.invalid/a'}]},'missing_image'),
                             ({'id':'C'*22,'uri':'spotify:album:'+'C'*22},'edition_mismatch')):
            with self.subTest(album=album):
                candidate={**item,'album':album}
                with self.assertRaisesRegex(ValueError,'^'+reason+'$'):
                    await self.art._fetch(self.hass,SimpleNamespace(_request=AsyncMock(return_value=candidate)),
                                          uri,guard=AsyncMock(),expected_album_uri='spotify:album:'+'B'*22)

    async def test_source_withdrawal_after_provider_response_prevents_cdn_request(self):
        from unittest.mock import AsyncMock
        guard=AsyncMock(side_effect=PermissionError('source_withdrawn'))
        with self.assertRaises(PermissionError):
            await self.art._fetch(self.hass,SimpleNamespace(_request=AsyncMock(return_value={})),
                                  'spotify:track:'+'A'*22,guard=guard)
        guard.assert_awaited_once_with()

    async def test_batch_delivery_rechecks_early_ready_asset_after_other_target_wait(self):
        import asyncio
        import sys
        from copy import deepcopy
        for mutation in ('end','source','track','expiry'):
            with self.subTest(mutation=mutation):
                scope=[(True,False)]
                granted=[True]
                ready={'schema_version':1,'session_id':'session-unit','entry_id':'entry-unit','revision':'initial',
                       'artwork':{'state':'ready','url':'/original','expires_at':'original-deadline',
                                  'current_display_allowed':True,'active_flow_display_allowed':True,
                                  'historical_display_allowed':False,'media_revision':'pixels'}}
                async def allowed():
                    return True
                asset=self.asset(allowed,authority=lambda:granted[0])
                asset.update(subject='spotify:track:'+'A'*22,projection=deepcopy(ready),
                             historical=False,delivery_scope=lambda:scope[0])
                self.registry.commit(self.key,asset)
                entered,release=asyncio.Event(),asyncio.Event()
                async def preparing(hass,runtime,context,*,session_id,target):
                    if target['entry_id']=='entry-unit':
                        return deepcopy(ready)
                    entered.set()
                    await release.wait()
                    return self.art.unavailable(session_id,target)
                context=SimpleNamespace(profile_id='profile-unit',privacy_policy=SimpleNamespace(allow_personal_read=True))
                async def auth(*args,**kwargs):
                    return object(),context,None,200
                with (patch.object(self.art,'prepare',preparing),
                      patch.dict(sys.modules,{'custom_components.djconnect.api_handlers':
                                             SimpleNamespace(_error_payload=lambda code:{'error':code},
                                                             _session_profile_context=auth)})):
                    request=asyncio.create_task(self.art.handle_prepare(self.hass,{'contract_version':1,
                        'session_id':'session-unit','targets':[{'entry_id':'entry-unit'},{'entry_id':'blocked'}]}))
                    await entered.wait()
                    if mutation=='end':
                        scope[0]=None
                        self.registry.end_session('profile-unit','session-unit')
                    elif mutation=='source':
                        granted[0]=False
                        self.registry.collect()
                    elif mutation=='track':
                        scope[0]=(False,False)
                    else:
                        asset['deadline']=time.monotonic()-1
                    release.set()
                    response,status=await request
                projected=response['session_media'][0]
                self.assertEqual(status,200)
                if mutation=='track':
                    self.assertEqual(projected['artwork']['state'],'ready')
                    self.assertFalse(projected['artwork']['current_display_allowed'])
                    self.assertTrue(projected['artwork']['active_flow_display_allowed'])
                    self.assertEqual(projected['artwork']['url'],'/original')
                    self.assertEqual(projected['artwork']['expires_at'],'original-deadline')
                else:
                    self.assertNotEqual(projected['artwork']['state'],'ready')
                    self.assertNotIn('url',projected['artwork'])

    async def test_last_authorization_await_cannot_return_ready_after_end(self):
        import sys
        from unittest.mock import AsyncMock
        ready={'artwork':{'state':'ready','url':'/original'}}
        async def allowed():
            return True
        asset=self.asset(allowed)
        asset.update(projection=ready,historical=False,delivery_scope=lambda:(True,False))
        self.registry.commit(self.key,asset)
        context=SimpleNamespace(profile_id='profile-unit',privacy_policy=SimpleNamespace(allow_personal_read=True))
        calls=0
        async def auth(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls==2:
                self.registry.end_session('profile-unit','session-unit')
            return object(),context,None,200
        with (patch.object(self.art,'prepare',AsyncMock(return_value=ready)),
              patch.dict(sys.modules,{'custom_components.djconnect.api_handlers':
                                     SimpleNamespace(_error_payload=lambda code:{'error':code},_session_profile_context=auth)})):
            response,status=await self.art.handle_prepare(self.hass,{'contract_version':1,'session_id':'session-unit',
                'targets':[{'entry_id':'entry-unit'}]})
        self.assertEqual(status,200)
        self.assertEqual(response['session_media'][0]['artwork']['state'],'withdrawn')

    async def test_history_repository_purge_fences_assets_before_storage_await(self):
        import asyncio
        from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
        async def allowed():
            return True
        ready={'artwork':{'state':'ready','url':'/old'}}
        asset=self.asset(allowed)
        asset.update(historical=True,projection=ready,delivery_scope=lambda:(False,True))
        self.registry.commit(self.key,asset)
        valid=[True]
        self.registry.work_guards[self.key]=(lambda:valid[0],lambda:valid.__setitem__(0,False))
        entered,release=asyncio.Event(),asyncio.Event()
        async def transaction(*args,**kwargs):
            entered.set()
            await release.wait()
        service=SimpleNamespace(session_image_owner=self.registry,async_in_transaction=transaction)
        task=asyncio.create_task(HistoricalProjectionRepository(service).async_purge_profile_history('profile-unit'))
        await entered.wait()
        self.assertFalse(valid[0])
        self.assertNotIn(self.key,self.registry.assets)
        result=self.art.delivery_projection(self.hass,'profile-unit','session-unit',{'entry_id':'entry-unit'},ready)
        self.assertEqual(result['artwork']['state'],'withdrawn')
        self.assertNotIn('url',result['artwork'])
        release.set()
        await task

    async def test_retention_fence_preserves_unexpired_other_profile_and_live_moment(self):
        async def allowed():
            return True
        now=time.time()
        def expired_scope():
            return False,True
        expired_scope.history_retained_until=now-1
        expired_scope.history_session_created_at=now-100
        def retained_scope():
            return False,True
        retained_scope.history_retained_until=now+300
        retained_scope.history_session_created_at=now
        old=self.asset(allowed)
        old.update(delivery_scope=expired_scope,historical=True)
        self.registry.commit(self.key,old)
        other=('profile-other','other-session',(('entry_id','other-entry'),))
        kept=self.asset(allowed)
        kept.update(delivery_scope=retained_scope,historical=True)
        self.registry.commit(other,kept)
        live=('profile-unit','session-unit',(('moment_id','live-moment'),))
        self.registry.commit(live,self.asset(allowed))
        self.registry.invalidate_history(expired_before=now,session_cutoff=now-1000)
        self.assertNotIn(self.key,self.registry.assets)
        self.assertIn(other,self.registry.assets)
        self.assertIn(live,self.registry.assets)

    async def test_purge_barrier_blocks_new_grants_until_finally_and_is_bounded(self):
        async def allowed():
            return True
        def scope():
            return False,True
        source={'provider_entry_id':'provider-X'}
        token=self.registry.begin_history_change(owner='profile-unit')
        self.assertTrue(self.registry.history_blocked(self.key,source,scope))
        asset=self.asset(allowed,authority=lambda:not self.registry.history_blocked(self.key,source,scope))
        self.assertFalse(self.registry.commit(self.key,asset))
        self.registry.end_history_change(token,owner='profile-unit')
        self.assertFalse(self.registry.history_blocked(self.key,source,scope))
        self.assertTrue(self.registry.commit(self.key,asset))
        tokens=[self.registry.begin_history_change(owner='profile-unit') for _ in range(10)]
        self.assertEqual(len(self.registry.history_barriers),8)
        self.assertEqual(self.registry.history_overflow,2)
        for token in tokens:
            self.registry.end_history_change(token,owner='profile-unit')
        self.assertEqual(self.registry.history_barriers,{})
        self.assertEqual(self.registry.history_overflow,0)

    async def test_source_X_withdrawal_preserves_unrelated_Y_pending_preparation(self):
        valid={'X':True,'Y':True}
        keys={}
        for provider in valid:
            key=('profile-unit','session-unit',(('entry_id','entry-'+provider),))
            keys[provider]=key
            def invalidate(provider=provider):
                valid[provider]=False
            invalidate.provider_entry_id='provider-'+provider
            invalidate.delivery_scope=lambda:(False,True)
            self.registry.work_guards[key]=(lambda provider=provider:valid[provider],invalidate)
        token=self.registry.begin_history_change(provider_entry_id='provider-X')
        self.assertEqual(valid,{'X':False,'Y':True})
        self.assertFalse(self.registry.history_blocked(keys['Y'],{'provider_entry_id':'provider-Y'},lambda:(False,True)))
        self.registry.end_history_change(token,provider_entry_id='provider-X')
        self.assertTrue(valid['Y'])

    async def test_old_session_header_retention_revokes_even_recent_retained_entry(self):
        async def allowed():
            return True
        now=time.time()
        def scope():
            return False,True
        scope.history_retained_until=now+300
        scope.history_session_created_at=now-1000
        asset=self.asset(allowed)
        asset.update(historical=True,delivery_scope=scope)
        self.registry.commit(self.key,asset)
        token=self.registry.begin_history_change(expired_before=now,session_cutoff=now-100)
        self.assertNotIn(self.key,self.registry.assets)
        self.registry.end_history_change(token,expired_before=now,session_cutoff=now-100)

    async def test_no_oversized_commit_and_closed_owner_rejects_late_commit(self):
        async def allowed():
            return True
        asset=self.asset(allowed)
        asset['body']=b'x'*(2*1024*1024+1)
        self.assertFalse(self.registry.commit(self.key,asset))
        self.registry.close()
        self.assertFalse(self.registry.commit(self.key,self.asset(allowed)))
