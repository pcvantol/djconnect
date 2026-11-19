"""Synthetic provider vocabulary matches ordinary multilingual search input."""
import unittest

from scripts.verification.askdj_catalogue_provider_fixture import handle


class CatalogueProviderLexicalFidelityTests(unittest.TestCase):
    def search(self, text, kind='playlist'):
        state = {}
        handled, result = handle('GET', '/search', {'q': [text], 'type': [kind]},
                                 None, state, [{'artists': [{'name': 'Synthetic artist'}]}])
        self.assertTrue(handled)
        return state, result

    def test_cooking_stems_cover_original_german_compound_and_five_languages(self):
        for query in ('cooking music', 'muziek om te koken', 'Musik zum Kochen',
                      'Kochmusik', 'musique pour cuisiner', 'música para cocinar'):
            with self.subTest(query=query):
                state, result = self.search(query)
                self.assertEqual(state['collection'], 'cooking')
                self.assertEqual(len(result['playlists']['items']), 1)
                self.assertEqual(result['playlists']['items'][0]['name'], 'Cooking collection')

    def test_unrelated_and_other_types_do_not_gain_a_playlist_match(self):
        for query in ('unrelated lunar lecture', 'Volbeat', 'anything random'):
            state, result = self.search(query)
            self.assertNotIn('collection', state)
            self.assertEqual(result['playlists']['items'], [])
        _, result = self.search('Kochmusik', 'track')
        self.assertEqual(result['playlists']['items'], [])


if __name__ == '__main__':
    unittest.main()
