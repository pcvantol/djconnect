"""Proactive Golden matrix through existing Runtime/Planner/Knowledge/Flow.

Provider boundaries are synthetic; no LLM or native/installed claim.
"""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_expressive_dj_persona as persona_tests
from tests import test_expressive_context_variation as context_tests

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'docs/verification/fixtures/dj_moment_persona_mood_golden_v1.json'


class DJMomentGoldenMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        persona_tests.ExpressiveDJPersonaTest.setUpClass()
        cls.runtime = persona_tests.ExpressiveDJPersonaTest.runtime
        context_tests.ExpressiveContextVariationTest.runtime = cls.runtime
        context_tests.ExpressiveContextVariationTest.facts = persona_tests.ExpressiveDJPersonaTest.facts

    @classmethod
    def tearDownClass(cls):
        persona_tests.ExpressiveDJPersonaTest.tearDownClass()

    def cells(self):
        rows=json.loads(MANIFEST.read_text())['cells']
        expected={(p.value,m,l) for p in self.runtime.DJPersona
                  for m in ('chill','groove','energy','party') for l in ('en','nl','de','fr','es')}
        self.assertEqual({(r['persona'],r['mood'],r['language']) for r in rows},expected)
        self.assertEqual(len(rows),80)
        self.assertEqual(len({r['id'] for r in rows}),80)
        return rows

    def assert_publication(self, fixture, rows, cell):
        self.assertTrue(rows)
        self.assertEqual(fixture.session.selected_mood,cell['mood'])
        self.assertEqual(fixture.session.dj_persona.value,cell['persona'])
        ids=[r['moment_id'] for r in rows]
        self.assertEqual(len(ids),len(set(ids)))
        broadcast={m.moment_id for m in fixture.session.broadcast.state.dj_moments}
        flow={i.moment_id for i in fixture.session.planner.output.session_flow.items if i.moment_id}
        self.assertTrue(set(ids)<=broadcast)
        self.assertTrue(set(ids)<=flow)
        self.assertEqual(sum(m.moment_type.value!='silence' for m in fixture.session.broadcast.state.dj_moments),
                         fixture.session.presence_ledger.total_published)
        for row in rows:
            self.assertEqual(row['presentation_intent']['source_session_mood'],cell['mood'])
            self.assertEqual(row['presentation_intent']['dj_persona'],cell['persona'])
            self.assertEqual(row['session_id'],fixture.session.session_id)
            self.assertTrue(row['source_attribution']['url'].startswith('https://'))
            self.assertTrue(row['source_attribution']['license'])
            self.assertTrue(row['content'].strip())
            self.assertNotIn('{',row['content'])
            self.assertNotIn('untrusted malformed model text',row['content'])
            self.assertLessEqual(len(row['summary'])+len(row['content']),1260)

    def test_track_credits_continuity_persona_mood_five_languages(self):
        first_forms={}
        for cell in self.cells():
            with self.subTest(case=cell['id']+'-track'):
                fixture=persona_tests.ExpressiveDJPersonaTest()
                moments=fixture.run_sequence(self.runtime.DJPersona(cell['persona']),cell['language'],mood=cell['mood'])
                rows=[m.as_dict() for m in moments if m]
                self.assertEqual(len(rows),4)
                self.assert_publication(fixture,rows,cell)
                for i,row in enumerate(rows):
                    self.assertEqual(row['type'],'track')
                    self.assertIn('Nora Vale',row['content'])
                    if i%2==0:
                        self.assertIn('Sam Reed',row['content'])
                    else:
                        self.assertIn(fixture.source_pair(i)[0]['title'],row['content'])
                        self.assertIn(fixture.source_pair(i-1)[0]['title'],row['content'])
                        self.assertTrue(row['source_attribution']['url_previous'])
                first_forms.setdefault((cell['mood'],cell['language']),[]).append(rows[0]['content'])
        self.assertTrue(all(len(set(forms))==4 for forms in first_forms.values()))

    def test_artist_album_genre_persona_mood_five_languages(self):
        dates={'en':'4 March 1960','nl':'4 maart 1960','de':'4. März 1960','fr':'4 mars 1960','es':'4 de marzo de 1960'}
        original=self.runtime.SessionRuntimeManager.async_start
        for cell in self.cells():
            async def start(manager,**kwargs):
                return await original(manager,**{**kwargs,'selected_mood':cell['mood']})
            for family in ('birth','formation','description','edition','genre'):
                with self.subTest(case=cell['id']+'-'+family),patch.object(self.runtime.SessionRuntimeManager,'async_start',start):
                    fixture=context_tests.ExpressiveContextVariationTest()
                    receipts=fixture.run_sequence(family,self.runtime.DJPersona(cell['persona']),cell['language'])
                    kind='genre' if family=='genre' else 'album' if family=='edition' else 'artist'
                    rows=[r for r in receipts if r and r['type']==kind]
                    self.assertEqual(len(rows),2)
                    self.assert_publication(fixture,rows,cell)
                    for i,row in enumerate(rows):
                        if family in ('birth','formation','edition'):
                            self.assertIn(dates[cell['language']],row['content'])
                        elif family=='description':
                            fact=fixture.source(family,i)[1]
                            self.assertIn(fact.copy_for(cell['language'])[1],row['content'])
                        if family!='genre':
                            self.assertEqual(row['source_attribution']['url'],fixture.source(family,i)[1].source_url)

    def test_music_only_suppresses_every_persona_mood_language(self):
        original=self.runtime.SessionRuntimeManager.async_start
        for cell in self.cells():
            async def start(manager,**kwargs):
                session=await original(manager,**kwargs)
                await manager.async_update_presence(owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id,selected_presence='music_only')
                return await manager.async_get_active(session.owner_profile_id)
            with self.subTest(case=cell['id']+'-music-only'),patch.object(self.runtime.SessionRuntimeManager,'async_start',start):
                fixture=persona_tests.ExpressiveDJPersonaTest()
                receipts=fixture.run_sequence(self.runtime.DJPersona(cell['persona']),cell['language'],mood=cell['mood'])
                self.assertFalse(any(receipts))
                self.assertEqual(fixture.session.presence_ledger.total_published,0)
                self.assertEqual(fixture.session.broadcast.state.dj_moments,())
                self.assertEqual(fixture.session.moment_engine._expression_forms,())
