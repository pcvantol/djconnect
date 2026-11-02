"""Artist context does not inherit the recording identity gate or its claims."""
import asyncio
from copy import deepcopy
import sys
import unittest
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module


class IndependentArtistIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.previous_const = _load_runtime_module()
        from custom_components.djconnect import session_facts
        cls.facts = session_facts

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if cls.previous_const is not None:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const

    def scenario(self):
        catalog = {'uri': 'spotify:track:'+'A'*22, 'title': 'Test song - Live edition',
                   'artist': 'Test group', 'artist_ids': ['Z'*22], 'isrc': 'USABC0100001'}
        mbid = '00000000-0000-0000-0000-000000000002'
        url = 'https://open.spotify.com/artist/'+'Z'*22
        person = {'id': mbid, 'name': 'Test group', 'type': 'Group',
                  'life-span': {'begin': '1964'}, 'relations': [
                      {'type': 'free streaming', 'url': {'resource': url}},
                      {'type': 'wikidata', 'url': {'resource': 'https://www.wikidata.org/wiki/Q1'}}]}
        entity = {'id': 'Q1', 'descriptions': {lang: {'value': 'Test group description '+lang}
                                             for lang in self.facts.LANGUAGES},
                  'claims': {'P434': [{'rank': 'normal', 'mainsnak': {'datavalue': {'value': mbid}}}]}}
        responses = {'isrc/USABC0100001': {'recordings': []},
                     'url': {'resource': url, 'relations': [
                         {'target-type': 'artist', 'artist': {'id': mbid}}]},
                     'artist/'+mbid: person, '': {'entities': {'Q1': entity}}}
        class Resolver(self.facts.SessionFactsResolver):
            async def _get(inner, path, params=None, **kwargs):
                inner.calls.append((path, deepcopy(params)))
                return deepcopy(responses.get(path, {}))
        resolver = Resolver(object())
        resolver.calls = []
        return catalog, resolver, responses

    def test_missing_or_ambiguous_recording_still_has_independent_artist_story(self):
        for recording in (None, [], [{}, {}], [{'id': 'wrong', 'title': 'Other recording'}]):
            with self.subTest(recording=recording):
                catalog, resolver, responses = self.scenario()
                if recording is None:
                    catalog.pop('isrc')
                else:
                    responses['isrc/USABC0100001'] = {'recordings': recording}
                facts = asyncio.run(resolver.resolve(catalog))
                self.assertEqual({f.key for f in facts}, {'artist_begin', 'artist_description'})
                self.assertEqual({f.public_artist_qid for f in facts}, {'Q1'})
                self.assertTrue(all(f.eligible(catalog['uri'], f.observed_at) for f in facts))
                self.assertTrue(all(f.artwork_artist_identity is not None for f in facts))
                self.assertFalse(any(p.startswith('recording/') for p, _ in resolver.calls))
                self.assertEqual(sum(p == 'url' for p, _ in resolver.calls), 1)

    def test_independent_artist_never_supplies_recording_work_or_album_proof(self):
        catalog, resolver, _ = self.scenario()
        facts = asyncio.run(resolver.resolve(catalog))
        self.assertEqual({f.key for f in facts}, {'artist_begin', 'artist_description'})
        self.assertTrue(all(f.provider in {'MusicBrainz', 'Wikidata'} for f in facts))
        self.assertTrue(all(f.artwork_album_uri == '' for f in facts))
        self.assertTrue(all(f.recording_evidence is None for f in facts))

    def test_credit_only_does_not_start_artist_resolution(self):
        catalog, resolver, _ = self.scenario()
        self.assertEqual(asyncio.run(resolver.resolve(catalog, credits_only=True)), ())
        self.assertEqual([p for p, _ in resolver.calls], ['isrc/USABC0100001'])

    def test_artist_resolution_requires_single_original_id_and_reciprocal_identity(self):
        mutations = ('multiple_ids', 'missing_ids', 'malformed_id', 'wrong_url', 'multiple_actors',
                     'wrong_name', 'wrong_type', 'missing_backlink', 'wrong_qid', 'wrong_reciprocal',
                     'deprecated_reciprocal', 'conflicting_spotify_id')
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                catalog, resolver, responses = self.scenario()
                person = responses[next(p for p in responses if p.startswith('artist/'))]
                entity = responses['']['entities']['Q1']
                if mutation == 'multiple_ids':
                    catalog['artist_ids'].append('Y'*22)
                if mutation == 'missing_ids':
                    catalog.pop('artist_ids')
                if mutation == 'malformed_id':
                    catalog['artist_ids'] = ['bad']
                if mutation == 'wrong_url':
                    responses['url']['resource'] += 'other'
                if mutation == 'multiple_actors':
                    responses['url']['relations'].append({'target-type': 'artist', 'artist': {'id': '0'*36}})
                if mutation == 'wrong_name':
                    person['name'] = 'Other group'
                if mutation == 'wrong_type':
                    person['type'] = 'Other'
                if mutation == 'missing_backlink':
                    person['relations'].pop(0)
                if mutation == 'wrong_qid':
                    person['relations'][1]['url']['resource'] += '2'
                if mutation == 'wrong_reciprocal':
                    entity['claims']['P434'][0]['mainsnak']['datavalue']['value'] = 'other'
                if mutation == 'deprecated_reciprocal':
                    entity['claims']['P434'][0]['rank'] = 'deprecated'
                if mutation == 'conflicting_spotify_id':
                    entity['claims']['P1902'] = [{'rank': 'normal', 'mainsnak': {'datavalue': {'value': 'Y'*22}}}]
                self.assertEqual(asyncio.run(resolver.resolve(catalog)), ())

    def test_withdrawal_after_lookup_cannot_deliver_artist_facts(self):
        catalog, resolver, _ = self.scenario()
        def authorize():
            if any(path == 'url' for path, _ in resolver.calls):
                raise PermissionError('original_owner_withdrawn')
        with self.assertRaises(PermissionError):
            asyncio.run(resolver.resolve(catalog, authorize=authorize))
        self.assertEqual([p for p, _ in resolver.calls], ['isrc/USABC0100001', 'url'])

    def test_original_deadline_and_cancellation_do_not_reopen_an_artist_budget(self):
        async def scenario(cancel):
            catalog, resolver, _ = self.scenario()
            original = resolver._get
            real_timeout = asyncio.timeout
            budgets = []
            def bounded(seconds):
                budgets.append(seconds)
                return real_timeout(0)
            async def pending(path, params=None, **kwargs):
                result = await original(path, params, **kwargs)
                if cancel:
                    raise asyncio.CancelledError
                await asyncio.sleep(0)
                return result
            resolver._get = pending
            with patch.object(self.facts.asyncio, 'timeout', bounded):
                with self.assertRaises(asyncio.CancelledError if cancel else TimeoutError):
                    await resolver.resolve(catalog)
            self.assertEqual(budgets, [35])
            self.assertEqual([p for p, _ in resolver.calls], ['isrc/USABC0100001'])
        for cancel in (False, True):
            asyncio.run(scenario(cancel))

    def test_catalog_mutation_during_recording_lookup_cannot_rebind_artist(self):
        catalog, resolver, _ = self.scenario()
        original = resolver._get
        async def changed(path, params=None, **kwargs):
            result = await original(path, params, **kwargs)
            if path.startswith('isrc/'):
                catalog['artist_ids'][0] = 'Y'*22
                catalog['artist'] = 'Replacement group'
            return result
        resolver._get = changed
        facts = asyncio.run(resolver.resolve(catalog))
        self.assertEqual({f.display_core.subject if f.display_core else dict(f.summaries)['nl'] for f in facts},
                         {'Test group'})
        self.assertEqual({f.artwork_artist_identity.spotify_uri for f in facts}, {'spotify:artist:'+'Z'*22})
        self.assertEqual(next(params['resource'] for path, params in resolver.calls if path == 'url'),
                         'https://open.spotify.com/artist/'+'Z'*22)

    def test_identity_without_actual_artist_facts_does_not_manufacture_a_story_seed(self):
        catalog, resolver, responses = self.scenario()
        responses[next(p for p in responses if p.startswith('artist/'))].pop('life-span')
        responses['']['entities']['Q1']['descriptions'] = {}
        self.assertEqual(asyncio.run(resolver.resolve(catalog)), ())
