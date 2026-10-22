"""Conversational named questions use public research, never an older selection."""
import unittest

from tests import test_ask_dj_contextual_dialogue as shared


class NamedArtistIntroductionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = shared.SharedDialogueTest()
        await self.f.asyncSetUp()

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    def test_named_conversational_introductions_keep_only_the_public_name(self):
        from custom_components.djconnect.ask_dj.public_research import explicit_public_subject
        for question in (
            'Vertel eens wat over Metallica', 'Vertel me iets over Metallica.',
            'Tell me a bit about Metallica', 'Erzähl mir mal etwas über Metallica',
            'Parle-moi un peu de Metallica', 'Háblame un poco de Metallica',
        ):
            with self.subTest(question=question):
                self.assertEqual(explicit_public_subject(question),'Metallica')
        for question in ('Vertel eens wat over deze artiest', 'Tell me a bit about this artist',
                         'Erzähl mir mal etwas über diese Band', 'Parle-moi un peu de cet artiste',
                         'Háblame un poco de este artista'):
            with self.subTest(question=question):
                self.assertIsNone(explicit_public_subject(question))

    async def test_reported_question_ignores_expired_old_selection_and_researches_named_band(self):
        f=self.f
        f.reply='Metallica is een Amerikaanse metalband.'
        with f.research_http(title='Metallica',text='Metallica is een Amerikaanse metalband.'):
            result,status=await f.request('Vertel eens wat over Metallica',language='nl',
                context={'selected_entry':{'session_id':'expired','entry_id':'missing'}})
        self.assertEqual(status,200,result)
        self.assertEqual(result['text'],f.reply)
        self.assertEqual(result['knowledge_basis'],'fetched_public_music_research_v1')
        self.assertEqual(result['conversation']['metrics']['agent_calls'],2)
        self.assertNotIn('selected_entry',result['conversation']['context'])
        self.assertEqual(result.get('playback_actions',[]),[])
        self.assertEqual(f.effects,[])
        self.assertTrue(f.web_calls)
        self.assertEqual(f.prompts[0]['public_music_research']['resolved_public_subject'],'Metallica')

    async def test_named_question_does_not_bypass_an_explicit_stale_session(self):
        result,status=await self.f.request('Vertel eens wat over Metallica',language='nl',
            context={'session_id':'expired'})
        self.assertEqual(status,409,result)
        self.assertEqual(result['error'],'session_context_changed')
        self.assertEqual(self.f.web_calls,[])
        self.assertEqual(self.f.prompts,[])
        self.assertEqual(self.f.effects,[])
