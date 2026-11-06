"""Synthetic Spotify wires: exact artist-to-playlist resolution, no live playback."""
import asyncio
from copy import deepcopy
import importlib
from types import SimpleNamespace
import unittest
from urllib.parse import urlsplit,parse_qs
from tests.test_http_voice_helpers import install_http_stubs


class DiscoveryArtistResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_http_stubs()
        cls.module=importlib.import_module('custom_components.djconnect.spotify_backend')

    def setUp(self):
        self.artist='A'*22
        self.playlist='B'*22
        self.item={'id':self.playlist,'uri':'spotify:playlist:'+self.playlist,
            'type':'playlist','name':'This Is Fixture Artist','owner':{'id':'spotify'}}
        self.artist_data={'id':self.artist,'uri':'spotify:artist:'+self.artist,'type':'artist','name':'Fixture Artist'}
        self.details={**deepcopy(self.item),'tracks':{'items':[{'track':{'id':'C'*22,'uri':'spotify:track:'+'C'*22,
            'type':'track','artists':[{'id':self.artist,'uri':'spotify:artist:'+self.artist}]}}]}}
        self.results=[self.item]
        self.calls=[]
        self.backend=object.__new__(self.module.SpotifyBackend)
        self.backend.runtime=SimpleNamespace(config={})
        async def request(method,path,**kwargs):
            self.calls.append((method,path,kwargs))
            route=urlsplit(path).path
            if route=='/artists/'+self.artist:return deepcopy(self.artist_data)
            if route=='/search':
                q=parse_qs(urlsplit(path).query)
                self.assertEqual(q['type'],['playlist'])
                self.assertLessEqual(int(q['limit'][0]),10)
                return {'playlists':{'items':deepcopy(self.results)}}
            if route=='/playlists/'+self.playlist:return deepcopy(self.details)
            raise self.module.SpotifyBackendError('synthetic denied',http_status=403)
        self.backend._request=request

    def resolve(self):
        return asyncio.run(self.backend.resolve_discovery_artist('spotify:artist:'+self.artist))

    def test_real_exact_artist_and_official_this_is_identity_without_mutation(self):
        selected=self.resolve()
        self.assertEqual(selected['uri'],'spotify:playlist:'+self.playlist)
        self.assertEqual(selected['artist_uri'],'spotify:artist:'+self.artist)
        self.assertEqual([m for m,_,_ in self.calls],['GET']*len(self.calls))

    def test_new_item_envelope_qualifies_exact_credited_artist(self):
        self.details['items']={'items':[{'item':self.details.pop('tracks')['items'][0]['track']}]}
        self.assertEqual(self.resolve()['uri'],'spotify:playlist:'+self.playlist)

    def test_fan_playlist_and_guessed_title_are_not_an_official_resolution(self):
        for changed in [{'owner':{'id':'fan'}},{'name':'Best of Fixture Artist'},{'uri':'spotify:playlist:'+'D'*22}]:
            with self.subTest(changed=changed):
                self.results=[{**self.item,**changed}]
                with self.assertRaises(self.module.SpotifyBackendError):self.resolve()

    def test_wrong_artist_id_even_same_display_name_is_rejected(self):
        self.details['tracks']['items'][0]['track']['artists']=[{'id':'E'*22,'name':'Fixture Artist'}]
        with self.assertRaises(self.module.SpotifyBackendError):self.resolve()

    def test_missing_or_restricted_item_evidence_never_becomes_a_guess(self):
        self.details.pop('tracks')
        with self.assertRaises(self.module.SpotifyBackendError):self.resolve()
        self.assertTrue(all(method=='GET' for method,_,_ in self.calls))

    def test_wrong_artist_endpoint_identity_and_empty_playlist_fail_closed(self):
        self.artist_data['id']='F'*22
        with self.assertRaises(self.module.SpotifyBackendError):self.resolve()
        self.artist_data['id']=self.artist
        self.details['tracks']['items']=[]
        with self.assertRaises(self.module.SpotifyBackendError):self.resolve()

    def test_null_search_candidates_are_not_executed(self):
        self.results=[None,self.item]
        self.assertEqual(self.resolve()['uri'],'spotify:playlist:'+self.playlist)

    def test_context_only_payload_cannot_use_the_old_offset_command(self):
        with self.assertRaises(ValueError):
            asyncio.run(self.backend.play_context_at({'context_uri':'spotify:playlist:'+self.playlist}))
        self.assertEqual(self.calls,[])
