"""Closed model tokens become Core slots before the unchanged whole-text review."""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
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
