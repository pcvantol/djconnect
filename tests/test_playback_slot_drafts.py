"""Closed model tokens become Core slots before the unchanged whole-text review."""
from copy import deepcopy
from dataclasses import replace
import importlib
import hashlib
import json
from pathlib import Path
import re
import time
import unittest

from tests import test_ask_dj_contextual_dialogue as shared


class PlaybackSlotDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.p = importlib.import_module('custom_components.djconnect.playback_request')
        cls.n = importlib.import_module('custom_components.djconnect.narration_brief')

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def brief(self):
        return self.p.PlaybackRequestBrief(
            self.p.PlaybackAcceptance('private-id', time.monotonic() + 20),
            'en', 'home_dj', 'groove', 'Fallback.', ('{title}', '{artist}', '{status}'),
            'One actual accepted request.', 'Only dispatch is proven.',
            (('{title}', 'PRIVATE_TITLE'), ('{artist}', 'PRIVATE_ARTIST'), ('{status}', 'Requested.')),
            selection_kind='artist_tracks', playback_state='dispatched')

    def wire(self):
        return {'schema': 'playback_slot_drafts_v1', 'drafts': [{'parts': [
            {'literal': 'I am handing “'}, {'slot': 'title'}, {'literal': '” by '},
            {'slot': 'artist'}, {'literal': ' over to you. '}, {'slot': 'status'}]}]}

    def decode(self, value, brief=None):
        brief = brief or self.brief()
        return brief.decode_drafts(json.dumps(value, ensure_ascii=False),
            lambda text: self.n.candidate(brief, json.dumps({'text': text})))

    def example(self, brief):
        instructions = brief.prompt(verified_drafts=True).split('\nData:\n', 1)[0]
        match = re.search(r'\{"schema"\s*:\s*"playback_literal_gaps_v2"', instructions)
        self.assertIsNotNone(match)
        return json.JSONDecoder().raw_decode(instructions[match.start():])[0]

    def collection_brief(self, kind='playlist', locale='en', *, observed=False, rich=False):
        media = {'uri': 'PRIVATE_URI_CANARY', 'title': 'PRIVATE_TITLE_CANARY'}
        if rich:
            media.update(artist='PRIVATE_ARTIST_CANARY', album_name='PRIVATE_ALBUM_CANARY')
        receipt = {'selection': {'kind': kind, 'media': media},
                   'state': 'observed' if observed else 'dispatched', 'observed_match': observed}
        bindings, fallback = self.p._copy(receipt, locale)
        if kind == 'artist_tracks':
            bindings.pop('{media_kind}')
            bindings.pop('{album}', None)
        return replace(self.brief(), locale=locale, selection_kind=kind,
                       playback_state='observed' if observed else 'dispatched', seed=fallback,
                       anchors=tuple(bindings), bindings=tuple(bindings.items()))

    def test_actual_core_inventories_are_complete_in_each_illustrated_draft_in_five_locales(self):
        for locale in ('en', 'nl', 'de', 'fr', 'es'):
            for kind in ('track', 'artist_tracks', 'album', 'playlist'):
                for observed in (False, True):
                    for rich in (False, True):
                        brief = self.collection_brief(kind, locale, observed=observed, rich=rich)
                        prompt = brief.prompt(verified_drafts=True)
                        data = json.loads(prompt.split('\nData:\n', 1)[1])
                        example = self.example(brief)
                        with self.subTest(locale=locale, kind=kind, observed=observed, rich=rich):
                            self.assertNotIn('PRIVATE_', prompt)
                            self.assertEqual(set(data['required_slots']),
                                             {anchor[1:-1] for anchor in brief.anchors})
                            self.assertEqual(len(example['drafts']), 2)
                            for draft in example['drafts']:
                                self.assertEqual(len(draft['gaps']), len(data['core_slot_order']))
                                self.assertEqual(set(data['core_slot_order']), set(data['required_slots']))
                                self.assertEqual(data['core_slot_order'][-1], 'status')
                                self.assertRegex(draft['gaps'][-1], r'[.!?] $')
                            compiled = self.decode(example, brief)
                            self.assertEqual(len(compiled.texts), 2)
                            for text in compiled.texts:
                                self.assertTrue(text.endswith('. {status}'))
                                self.assertTrue(all(text.count(anchor) == 1 for anchor in brief.anchors))
                            legacy = brief.prompt()
                            self.assertIn('Return only {"text":"your reply"}', legacy)
                            self.assertNotIn('playback_slot_drafts_v1', legacy)
                            self.assertNotIn('PRIVATE_', legacy)

    def test_seven_consumed_missing_kind_wires_and_bad_second_drafts_still_reject_before_normalization(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/playback_slot_example/'
                              'consumed_0d115_missing_kind.json').read_text())
        self.assertEqual(fixture['run'], 40188270227)
        self.assertEqual(len(fixture['cases']), 7)
        brief = self.collection_brief()
        complete = {'parts': [{'slot': name} for name in brief.literal_gap_slots()]}
        for row in fixture['cases']:
            raw = row['original_generated_text']
            self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), row['original_generated_sha256'])
            self.assertCountEqual(row['required_slots'], [a[1:-1] for a in brief.anchors])
            bad = json.loads(raw)
            for draft in bad['drafts']:
                self.assertNotIn('media_kind', [p.get('slot') for p in draft['parts']])
            for value in (bad, {'schema': bad['schema'], 'drafts': [complete, bad['drafts'][0]]}):
                calls = []
                with self.subTest(case=row['case_id']), self.assertRaisesRegex(
                        ValueError, 'incomplete_playback_slot_draft'):
                    brief.decode_drafts(json.dumps(value), lambda text: calls.append(text) or text)
                self.assertEqual(calls, [])

    def test_original_misquoted_placeholder_is_rejected_but_core_compiles_valid_slot_names(self):
        brief = self.brief()
        old = {'drafts': ['I am handing “{title}” by {artist”} over to you. {status}']}
        with self.assertRaises(ValueError):
            self.decode(old)
        with self.assertRaises(ValueError):
            self.n.verified_drafts(json.dumps(self.wire()), str.strip)
        pool = self.decode(self.wire())
        self.assertEqual(pool.texts, ('I am handing “{title}” by {artist} over to you. {status}',))
        self.assertNotIn('PRIVATE_', pool.texts[0])
        for locale in ('en', 'nl', 'de', 'fr', 'es'):
            prompt = replace(brief, locale=locale).prompt(verified_drafts=True)
            self.assertNotIn('PRIVATE_', prompt)
            self.assertEqual(json.loads(prompt.split('\nData:\n', 1)[1])['required_slots'],
                             ['title', 'artist', 'status'])

    def test_gap_wire_binds_every_original_role_without_adding_any_model_prose(self):
        brief = self.brief()
        value = {'schema': 'playback_literal_gaps_v2', 'drafts': [
            {'gaps': ['I hand “', '” by ', ' over to you. ']}]}
        self.assertEqual(self.decode(value).texts,
                         ('I hand “{title}” by {artist} over to you. {status}',))
        # A grammatical defect or factual assertion is not corrected here:
        # the unchanged whole-answer assessor still owns their acceptance.
        value['drafts'][0]['gaps'][0] = 'The best music ever: '
        self.assertIn('The best music ever:', self.decode(value).texts[0])
        self.assertIn('Reject new music facts', brief.assessment_prompt(self.decode(value).texts[0]))

    def test_new_gap_wire_malformed_second_draft_rejects_entire_batch_before_normalization(self):
        base = {'schema': 'playback_literal_gaps_v2', 'drafts': [
            {'gaps': ['I hand ', ' by ', ' to you. ']}]}
        bad_gaps = [[], ['x'], ['a', 'b'], ['a', 'b', '. ', 'extra'],
                    ['a', 1, '. '], ['a', True, '. '], ['a', None, '. '],
                    ['{title}', ' by ', '. '], ['a', '\x00', '. '],
                    ['a', '\n', '. '], ['a', '\x7f', '. '],
                    ['a', '\ud800', '. '], ['a', 'b', 'no separator'],
                    ['x' * 701, 'b', '. ']]
        variants = [{'gaps': gaps} for gaps in bad_gaps]
        variants += [{'gaps': base['drafts'][0]['gaps'], 'slot': 'title'},
                     {'parts': [{'slot': 'title'}]}, None]
        for bad in variants:
            value = deepcopy(base)
            value['drafts'].append(bad)
            calls = []
            with self.subTest(bad=repr(bad)), self.assertRaises(ValueError):
                self.brief().decode_drafts(json.dumps(value), lambda text: calls.append(text) or text)
            self.assertEqual(calls, [])
        for anchors in (('{title}', '{status}', '{status}'), ('{title}',),
                        ('{unknown}', '{title}', '{status}')):
            with self.subTest(anchors=anchors), self.assertRaises(ValueError):
                self.decode(base, replace(self.brief(), anchors=anchors))
        for value in ({**base, 'extra': True}, {**base, 'drafts': []},
                      {**base, 'drafts': base['drafts'] * 3}):
            with self.assertRaises(ValueError):
                self.decode(value)

    def test_every_part_and_every_draft_must_be_valid_before_any_normalization(self):
        base = self.wire()
        invalid = []
        for part in ({'slot': 'artist”'}, {'slot': True}, {'slot': 'unknown'},
                     {'literal': '{artist}'}, {'literal': ''}, {'literal': None},
                     {'slot': 'title', 'literal': 'ignored'}, ['not-an-object']):
            row = deepcopy(base)
            row['drafts'][0]['parts'][3] = part
            invalid.append(row)
        for parts in (base['drafts'][0]['parts'][:-1], base['drafts'][0]['parts'] + [{'literal': '.'}],
                      base['drafts'][0]['parts'][:3] + [{'slot': 'title'}, {'slot': 'status'}]):
            row = deepcopy(base)
            row['drafts'][0]['parts'] = parts
            invalid.append(row)
        for row in invalid:
            # A valid first draft cannot salvage a malformed second one.
            both = {'schema': base['schema'], 'drafts': base['drafts'] + row['drafts']}
            normalized = []
            with self.subTest(row=row), self.assertRaises((ValueError, TypeError)):
                self.brief().decode_drafts(json.dumps(both), lambda text: normalized.append(text) or text)
            self.assertEqual(normalized, [])

    def test_closed_json_bounds_duplicates_and_legacy_text_contract_stay_closed(self):
        for raw in ('{"schema":"playback_slot_drafts_v1","drafts":[],"drafts":[]}',
                    '{"schema":"playback_slot_drafts_v1","drafts":[NaN]}',
                    json.dumps({'schema': 'playback_slot_drafts_v1', 'drafts': [], 'extra': True}),
                    'x' * 8193):
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                self.brief().decode_drafts(raw, str.strip)
        legacy = {'drafts': ['I hand {title} by {artist} to you. {status}']}
        self.assertEqual(len(self.decode(legacy).texts), 1)
        for failed in ('supported', 'language_ok', 'style_ok'):
            review = {k: k != failed for k in ('supported', 'language_ok', 'style_ok')}
            self.assertFalse(self.n.assessed(json.dumps(review)))
