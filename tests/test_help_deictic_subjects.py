"""Canonical five-language Help references retain qualified current authority."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from tests import test_ask_dj_contextual_dialogue as shared


class HelpDeicticSubjectTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def questions(self):
        data = json.loads((Path(__file__).resolve().parents[1] /
            'custom_components/djconnect/ask_dj/examples_v1.json').read_text())
        return next(row['templates'] for row in data['entries'] if row['id'] == 'listen.artist')

    def turn(self, current=(), older=(), reset=False):
        return SimpleNamespace(source_context={'subjects':list(current)}, reset_topic=reset,
            frame=SimpleNamespace(subjects=list(older)))

    def test_every_actual_catalogue_artist_reference_keeps_qualified_current_subject(self):
        from custom_components.djconnect.ask_dj import dialogue, public_research as research
        turn = self.turn(current=[{'name':'Volbeat','role':'artist'}])
        for locale, question in self.questions().items():
            with self.subTest(locale=locale, question=question):
                self.assertIsNone(dialogue.explicit_subject(question))
                self.assertIsNone(research.explicit_public_subject(question))
                self.assertTrue(dialogue.references_topic(question))
                self.assertEqual(research.subject_for_question(question, turn), ('Volbeat', True, False))

    def test_missing_ambiguous_and_reset_context_cannot_invent_or_restore_a_subject(self):
        from custom_components.djconnect.ask_dj import public_research as research
        for locale, question in self.questions().items():
            with self.subTest(locale=locale):
                self.assertEqual(research.subject_for_question(question,self.turn()), ('',False,False))
                self.assertEqual(research.subject_for_question(question,self.turn(
                    current=[{'name':'Volbeat'},{'name':'Metallica'}])), ('',False,True))
                self.assertEqual(research.subject_for_question(question,self.turn(
                    older=[{'name':'Volbeat'}],reset=True)), ('',False,False))

    def test_secondary_public_extraction_never_turns_a_pronoun_into_a_name(self):
        from custom_components.djconnect.ask_dj import public_research as research
        for question in ('Parle-moi de cet artiste', 'Háblame de este artista',
            'Tell me fun facts about this artist', 'Vertel leuke weetjes over deze artiest',
            'Erzähl etwas über diesem Künstler', 'Erzähl etwas über dieser Band'):
            with self.subTest(question=question):
                self.assertIsNone(research.explicit_public_subject(question))

    def test_explicit_band_names_still_override_an_older_qualified_subject(self):
        from custom_components.djconnect.ask_dj import public_research as research
        for question, name in [('Tell me about The Beatles','The Beatles'),
            ('Erzähl etwas über Die Ärzte','Die Ärzte'), ('Parle-moi de La Femme','La Femme'),
            ('Háblame de Metallica','Metallica')]:
            with self.subTest(question=question):
                self.assertEqual(research.explicit_public_subject(question),name)
                self.assertEqual(research.subject_for_question(question,self.turn(
                    older=[{'name':'Volbeat'}])),(name,False,False))
