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

    def test_missing_is_no_display_grant_or_url(self):
        result = self.art.unavailable('s', {'entry_id': 'e'}, 'insufficient_identity')
        self.assertNotIn('url', result['artwork'])
        self.assertFalse(result['artwork']['historical_display_allowed'])

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
