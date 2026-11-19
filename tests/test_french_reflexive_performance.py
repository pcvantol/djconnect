"""French reflexive stage performances must not become production credits."""
import importlib
import json
from pathlib import Path
import unittest

from tests import test_ask_dj_contextual_dialogue as shared


class FrenchReflexivePerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.research = importlib.import_module('custom_components.djconnect.ask_dj.public_research')
        cls.original = json.loads((Path(__file__).parent / 'fixtures/french_reflexive/'
                                   'consumed_4765_original.json').read_text())

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def test_original_first_draft_is_a_performance_but_second_role_expansion_stays_denied(self):
        self.assertEqual(self.original['run'], 40195148203)
        context = {'public_music_research': self.original['original_public_music_research']}
        first, second = self.original['drafts']
        self.assertIs(first['original_accepted'], False)
        self.assertIs(second['original_accepted'], False)
        for row in (first, second):
            self.assertTrue(self.research.temporal_evidence_ok(
                row['answer'], row['original_resolved_review'], context))
        self.assertTrue(self.research.claim_evidence_ok(
            first['answer'], first['original_resolved_review'], context))
        self.assertFalse(self.research.claim_evidence_ok(
            second['answer'], second['original_resolved_review'], context))

    def test_only_match_local_reflexive_stage_wording_with_original_performance_evidence(self):
        quote = self.original['drafts'][0]['original_resolved_review']['claim_checks'][0]['quote']
        for text in ("Volbeat s'est produit au Download Festival.",
                     'Volbeat s’est produit au Download Festival.',
                     'La formation S’EST PRODUITE sur cette scène.'):
            with self.subTest(text=text):
                self.assertTrue(self.research._assertions_fit(text, quote))
        for text in ('They produced the album.', 'Zij produceerden het album.',
                     'Sie produzierten das Album.', 'Ils ont produit cet album.',
                     'Ellos produjeron el álbum.',
                     'Volbeat s’est produit au festival et a produit cet album.',
                     'Volbeat a produit le festival.', 'Volbeat s’est produit un album.'):
            with self.subTest(text=text):
                self.assertFalse(self.research._assertions_fit(text, quote))
        text = 'Volbeat s’est produit au Download Festival.'
        for insufficient in ('Volbeat attended Download Festival.',
                             'Download Festival is a music festival.',
                             'Volbeat recorded guest solos.', 'Volbeat performed with another band.',
                             'Volbeat never performed at Download Festival.',
                             "Volbeat hasn't played at Download Festival.",
                             'Volbeat performed at no festivals.',
                             'Volbeat played at neither Download Festival nor Pinkpop.',
                             'It is false that Volbeat performed at Download Festival.',
                             'It is untrue that Volbeat performed at Download Festival.',
                             'Volbeat played on this album.'):
            with self.subTest(quote=insufficient):
                self.assertFalse(self.research._assertions_fit(text, insufficient))


if __name__ == '__main__':
    unittest.main()
