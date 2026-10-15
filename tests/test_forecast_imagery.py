"""Bounded artist imagery admission, lease, scope and failure contracts."""
import asyncio
import importlib
import unittest
import sys
from tests.test_session_runtime import _load_runtime_module


class ForecastImageryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()
        cls.imagery = importlib.import_module('custom_components.djconnect.forecast_imagery')

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if cls.previous_const is None:
            sys.modules.pop('custom_components.djconnect.const', None)
        else:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const

    def test_closed_public_url_boundary(self):
        good = 'https://i.scdn.co/image/'+'a'*40
        self.assertTrue(self.imagery.safe_cdn_url(good))
        for bad in ('http'+good[5:], good+'?token=x', good+'#x',
                    good.replace('i.scdn.co','localhost'), good.replace('i.scdn.co','i.scdn.co.evil.test'),
                    good.replace('i.scdn.co','user@i.scdn.co'), good.replace('i.scdn.co','i.scdn.co:8123'),
                    'https://i.scdn.co/other/'+'a'*40, None):
            self.assertFalse(self.imagery.safe_cdn_url(bad), bad)

    def test_fail_closed_media_body(self):
        for body,mime in ((b'<svg/>','image/svg+xml'), (b'<html/>','image/png'),
                          (b'\xff\xd8\xff','text/html'), (b'','image/jpeg'),
                          (b'\x89PNG\r\n\x1a\n'+bytes(self.imagery.MAX_BYTES),'image/png')):
            self.assertFalse(self.imagery.image_format(body,mime))

    def test_scope_expiry_revocation_and_bounded_store(self):
        allowed = [True]
        store = self.imagery.ForecastArtwork()
        for i in range(3):
            asset = self.imagery.ForecastAsset(str(i),'artist','current',{'url':str(i)},b'png','image/png',100,lambda:allowed[0])
            store.commit(asset)
        self.assertEqual(len(store.assets),2)
        self.assertTrue(asset.allowed(99,'current'))
        self.assertFalse(asset.allowed(100,'current'))
        self.assertFalse(asset.allowed(99,'different-track'))
        allowed[0] = False
        self.assertFalse(asset.allowed(99,'current'))
        store.attempts = 7
        store.last_attempt['artist']=1
        store.clear()
        self.assertEqual(store.assets,())
        self.assertEqual(store.attempts,7)
        self.assertEqual(store.last_attempt,{'artist':1})

    def test_exact_artist_rebinding_preserves_original_lease_and_budget(self):
        async def scenario():
            import time
            store = self.imagery.ForecastArtwork()
            until = time.monotonic()+100
            asset = self.imagery.ForecastAsset('old','A'*22,'track-a',
                {'url':'old','expires_at':'original-deadline','source_url':'original-source'},
                b'png','image/png',until,lambda:True)
            store.commit(asset)
            store.attempts = 12
            store.last_attempt['A'*22] = time.monotonic()
            rebound = await store.prepare(hass=None,backend=None,session_id='session',item_id='track-b',
                artist_id='A'*22,authority=lambda:True,candidate_current=lambda:True)
            self.assertEqual(rebound.item_id,'track-b')
            self.assertNotEqual(rebound.asset_id,asset.asset_id)
            self.assertEqual(rebound.deadline,until)
            self.assertEqual(rebound.metadata['expires_at'],'original-deadline')
            self.assertEqual(rebound.metadata['source_url'],'original-source')
            self.assertEqual(store.attempts,12)
            self.assertFalse(asset.allowed(time.monotonic(),'track-b'))
            self.assertTrue(rebound.allowed(time.monotonic(),'track-b'))
            self.assertFalse(await store.prepare(hass=None,backend=None,session_id='session',item_id='track-b',
                artist_id='B'*22,authority=lambda:True,candidate_current=lambda:True))
        asyncio.run(scenario())

    def test_metadata_failure_budget_and_no_fetch_on_ineligible_input(self):
        async def scenario():
            class Backend:
                calls=0
                async def _request(self,*args):
                    self.calls+=1
                    return {'id':'wrong-subject','type':'artist'}
            store=self.imagery.ForecastArtwork()
            backend=Backend()
            common={'hass':None,'backend':backend,'session_id':'session','item_id':'track',
                    'authority':lambda:True,'candidate_current':lambda:True}
            self.assertFalse(await store.prepare(**common,artist_id='name-only'))
            self.assertFalse(await store.prepare(**{**common,'authority':lambda:False},artist_id='A'*22))
            self.assertEqual(backend.calls,0)
            for i in range(20):
                self.assertFalse(await store.prepare(**common,artist_id=f'{i:022d}'))
            self.assertEqual(backend.calls,12)
            self.assertEqual(store.attempts,12)
            self.assertEqual(len(store.last_attempt),12)
            self.assertEqual(store.assets,())
        asyncio.run(scenario())

    def test_negative_cache_has_no_read_reset(self):
        async def scenario():
            class Backend:
                calls=0
                async def _request(self,*args):
                    self.calls+=1
                    return None
            backend=Backend()
            store=self.imagery.ForecastArtwork()
            common={'hass':None,'backend':backend,'session_id':'session','item_id':'track','artist_id':'A'*22,
                    'authority':lambda:True,'candidate_current':lambda:True}
            await store.prepare(**common)
            for _ in range(20):
                self.assertEqual(store.public('track'),())
                await store.prepare(**common)
            self.assertEqual(backend.calls,1)
            self.assertEqual(store.attempts,1)
        asyncio.run(scenario())

    def test_malformed_metadata_and_remote_failure_do_not_admit_art(self):
        async def scenario():
            from unittest.mock import patch
            import types
            artist = 'A'*22
            url = 'https://i.scdn.co/image/'+'a'*40
            metadata = {'id':artist,'type':'artist','uri':'spotify:artist:'+artist,'name':'Verified artist',
                'external_urls':{'spotify':'https://open.spotify.com/artist/'+artist},
                'images':[{'url':url,'width':100,'height':100}]}
            class Backend:
                async def _request(self,*args):
                    return self.metadata
            backend = Backend()
            common = {'hass':None,'backend':backend,'session_id':'session','item_id':'track',
                'artist_id':artist,'authority':lambda:True,'candidate_current':lambda:True}
            for change in ({'external_urls':{'spotify':'https://evil.test'}}, {'images':None},
                           {'images':[{'url':url,'width':0,'height':100}]}, {'name':''}):
                backend.metadata = {**metadata,**change}
                store = self.imagery.ForecastArtwork()
                self.assertFalse(await store.prepare(**common))
                self.assertEqual(store.assets,())
                self.assertEqual(store.attempts,1)
            backend.metadata = metadata
            class Response:
                status = 200
                headers = {'Content-Type':'image/png'}
                def __init__(self,body):
                    self.body = body
                    self.content = self
                async def __aenter__(self):
                    return self
                async def __aexit__(self,*args):
                    return False
                async def iter_chunked(self,size):
                    yield self.body
            response = Response(b'not-an-image')
            class Session:
                def get(self,*args,**kwargs):
                    return response
            module = types.ModuleType('homeassistant.helpers.aiohttp_client')
            module.async_get_clientsession = lambda hass:Session()
            with patch.dict(sys.modules,{'homeassistant.helpers.aiohttp_client':module}):
                for status,body in ((503,b''),(200,b'not-an-image'),
                                    (200,b'x'*(self.imagery.MAX_BYTES+1))):
                    response.status = status
                    response.body = body
                    store = self.imagery.ForecastArtwork()
                    self.assertFalse(await store.prepare(**common))
                    self.assertEqual(store.assets,())
                    self.assertEqual(store.attempts,1)
            class FailingBackend:
                async def _request(self,*args):
                    raise TimeoutError('bounded external failure')
            self.assertFalse(await self.imagery.ForecastArtwork().prepare(**{**common,'backend':FailingBackend()}))
            class CancelledBackend:
                async def _request(self,*args):
                    raise asyncio.CancelledError()
            with self.assertRaises(asyncio.CancelledError):
                await self.imagery.ForecastArtwork().prepare(**{**common,'backend':CancelledBackend()})
        asyncio.run(scenario())
