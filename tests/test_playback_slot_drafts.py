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

    def test_public_task_schema_contains_exact_original_roles_without_catalogue_values(self):
        module = importlib.import_module('custom_components.djconnect.structured_playback')
        for locale in ('en', 'nl', 'de', 'fr', 'es'):
            for kind in ('track', 'artist_tracks', 'album', 'playlist'):
                brief = self.collection_brief(kind, locale, rich=True)
                structure = module.role_structure(brief)
                self.assertNotIn('PRIVATE_', json.dumps(structure))
                fields = structure['drafts']['selector']['object']['fields']
                roles = fields['gaps']['selector']['object']['fields']
                self.assertEqual(set(roles), set(brief.literal_gap_slots()))
                self.assertTrue(all(row == {'required': True, 'selector': {'text': {}}}
                                    for row in roles.values()))
        with self.assertRaises(ValueError):
            module.role_structure(object())
        with self.assertRaises(ValueError):
            module.role_structure(replace(self.brief(), anchors=('{title}', '{title}', '{status}')))

    def test_typed_task_result_uses_unchanged_whole_map_and_character_guards(self):
        module = importlib.import_module('custom_components.djconnect.structured_playback')
        wire = {'schema': 'playback_role_gaps_v3', 'drafts': [{'gaps': {
            'title': 'I am handing you ', 'artist': ' by ', 'status': '. '}}]}
        normalized = []
        self.brief().decode_drafts(module.freeze_typed_reply(wire),
            lambda text: normalized.append(text) or text)
        self.assertEqual(normalized, ['I am handing you {title} by {artist}. {status}'])
        for changed in (
            {'title': 'I am handing you ', 'artist': ' by ', '. ': ''},
            {'title': 'I am handing you ', 'artist': ' by ', 'status': ''},
            {'title': '{title}', 'artist': ' by ', 'status': '. '},
            {'title': 'x\x00', 'artist': ' by ', 'status': '. '},
        ):
            invalid = deepcopy(wire)
            invalid['drafts'].append({'gaps': changed})
            normalized.clear()
            with self.assertRaises(ValueError):
                self.brief().decode_drafts(module.freeze_typed_reply(invalid),
                    lambda text: normalized.append(text) or text)
            self.assertEqual(normalized, [])
        for invalid in (None, [], {'x': float('nan')}, {'x': 'x' * 8192}):
            with self.assertRaises(ValueError):
                module.freeze_typed_reply(invalid)

    def example(self, brief):
        instructions = brief.prompt(verified_drafts=True).split('\nData:\n', 1)[0]
        match = re.search(r'\{"schema"\s*:\s*"playback_role_gaps_v3"', instructions)
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
                            self.assertEqual(len(example['drafts']), 1)
                            for draft in example['drafts']:
                                self.assertIs(type(draft['gaps']), dict)
                                self.assertEqual(set(draft['gaps']), set(data['core_slot_order']))
                                self.assertEqual(set(data['core_slot_order']), set(data['required_slots']))
                                self.assertEqual(data['core_slot_order'][-1], 'status')
                                self.assertRegex(draft['gaps']['status'], r'[.!?] $')
                            compiled = self.decode(example, brief)
                            self.assertEqual(len(compiled.texts), 1)
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

    def test_role_map_orders_complete_named_gaps_without_adding_prose(self):
        value = {'schema': 'playback_role_gaps_v3', 'drafts': [{'gaps': {
            'status': ' to you. ', 'artist': ' by ', 'title': 'I hand '}}]}
        self.assertEqual(self.decode(value).texts,
            ('I hand {title} by {artist} to you. {status}',))

    def test_role_map_rejects_bad_second_map_before_any_normalization(self):
        good = {'title': 'I hand ', 'artist': ' by ', 'status': ' to you. '}
        bad = [{k: v for k, v in good.items() if k != 'artist'},
               {**good, 'genre': 'wrong '}, {'title': 'I hand ', 'artist': ' by ', 'status': ''},
               {**good, 'status': 'no separator'}, {**good, 'title': '{title}'},
               {**good, 'artist': True}, {**good, 'artist': None}, {**good, 'artist': [' by ']},
               {**good, 'artist': '\x00'}, {**good, 'artist': '\x7f'},
               {**good, 'artist': '\ud800'}, {**good, 'title': 'x' * 701},
               list(good.values()), None]
        for gaps in bad:
            value = {'schema': 'playback_role_gaps_v3',
                     'drafts': [{'gaps': good}, {'gaps': gaps}]}
            calls = []
            with self.subTest(gaps=repr(gaps)), self.assertRaises(ValueError):
                self.brief().decode_drafts(json.dumps(value), lambda text: calls.append(text) or text)
            self.assertEqual(calls, [])
        raw = ('{"schema":"playback_role_gaps_v3","drafts":[{"gaps":'
               '{"title":"I hand ","artist":" by ","status":". ","status":". "}}]}')
        with self.assertRaises(ValueError):
            self.brief().decode_drafts(raw, str.strip)

    def test_original_18b6_two_gap_failures_stay_denied_without_repair(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/playback_role_gaps/'
                              'consumed_18b6_original.json').read_text())
        self.assertEqual(fixture['run'], 40206158531)
        self.assertEqual(len(fixture['rows']), 4)
        for row in fixture['rows']:
            raw = row['original_wire']
            self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), row['original_wire_sha256'])
            self.assertEqual(len(json.loads(raw)['drafts'][0]['gaps']), 2)
            brief = self.collection_brief(kind=row['selection_kind'], locale=row['locale'])
            self.assertEqual(brief.literal_gap_slots(), row['required_roles'])
            calls = []
            with self.subTest(case=row['case_id']), self.assertRaises(ValueError):
                brief.decode_drafts(raw, lambda text: calls.append(text) or text)
            self.assertEqual(calls, [])

    def test_role_map_envelope_and_original_scope_are_closed(self):
        good = {'schema': 'playback_role_gaps_v3', 'drafts': [{'gaps': {
            'title': 'I hand ', 'artist': ' by ', 'status': ' to you. '}}]}
        invalid = [{**good, 'extra': True}, {**good, 'drafts': []},
                   {**good, 'drafts': True}, {**good, 'drafts': good['drafts'] * 3},
                   {**good, 'drafts': [{'gaps': good['drafts'][0]['gaps'], 'extra': True}]},
                   {**good, 'drafts': [None]}, {**good, 'drafts': [{'gaps': {}}]}]
        for value in invalid:
            calls = []
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.brief().decode_drafts(json.dumps(value), lambda text: calls.append(text) or text)
            self.assertEqual(calls, [])
        for anchors in (('{title}', '{status}', '{status}'), ('{title}',),
                        ('{unknown}', '{title}', '{status}')):
            brief = replace(self.brief(), anchors=anchors)
            value = {'schema': 'playback_role_gaps_v3', 'drafts': [{'gaps': {
                name: '. ' for name in brief.literal_gap_slots()}}]}
            with self.subTest(anchors=anchors), self.assertRaises(ValueError):
                self.decode(value, brief)
