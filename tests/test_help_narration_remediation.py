"""Causal source/presentation regressions; no paid model or provider effects."""
import importlib
import json
from types import SimpleNamespace
import unittest

from tests import test_ask_dj_contextual_dialogue as dialogue_tests


class HelpNarrationRemediationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dialogue_tests.SharedDialogueTest.setUpClass()
        cls.core = dialogue_tests.SharedDialogueTest.core
        cls.http = importlib.import_module('custom_components.djconnect.http')
        cls.dialogue = importlib.import_module('custom_components.djconnect.ask_dj.dialogue')

    @classmethod
    def tearDownClass(cls):
        dialogue_tests.SharedDialogueTest.tearDownClass()

    def test_current_owner_language_localizes_both_speaker_offers_without_changing_authority(self):
        labels = {'en': 'Play here', 'nl': 'Speel hier', 'de': 'Hier abspielen',
            'fr': 'Lire ici', 'es': 'Reproducir aquí'}
        selection = {'kind': 'artist_tracks', 'uris': ['spotify:track:' + 'A' * 22]}
        for locale, expected in labels.items():
            token = self.dialogue.current_turn.set(SimpleNamespace(style={'language': locale}))
            try:
                offered = self.core._output_device_play_request_actions(
                    [{'id': 'owned-output', 'name': 'Owned speaker'}], 'original request', {}, selection=selection)[0]
                recommendation = self.http._output_actions_for_recommendation(
                    [{'id': 'owned-output', 'name': 'Owned speaker'}], selection)[0]
                for row in (offered, recommendation):
                    self.assertEqual((row['label'], row['button_label']), (expected, expected), locale)
                self.assertEqual(offered['command'], 'ask_dj_play_request_on_output')
                self.assertEqual(offered['value']['request']['_frozen_playback_selection'], selection)
                self.assertEqual(recommendation['value']['recommendation'], selection)
            finally:
                self.dialogue.current_turn.reset(token)

    def test_actual_catalogue_action_factories_keep_uris_and_localize_play_labels(self):
        labels = {'en': 'Play', 'nl': 'Afspelen', 'de': 'Abspielen', 'fr': 'Lire', 'es': 'Reproducir'}
        hass = SimpleNamespace(data={'djconnect': []})
        for locale, expected in labels.items():
            token = self.dialogue.current_turn.set(SimpleNamespace(style={'language': locale}))
            try:
                album = self.core._artist_album_playback_action(hass, 'Source artist',
                    {'uri': 'spotify:album:' + 'B' * 22, 'name': 'Source album'})
                track = self.core._play_now_action_from_spotify_item(hass,
                    {'uri': 'spotify:track:' + 'A' * 22, 'name': 'Source track'})
                playlists = self.core._playlist_search_playback_actions(hass,
                    [{'uri': 'spotify:playlist:' + 'C' * 22, 'name': 'Source playlist'}])
                for row in (album, track, *playlists):
                    self.assertEqual((row['label'], row['button_label']), (expected, expected), locale)
                    self.assertEqual(row['action_style'], 'play_now')
                self.assertEqual(album['context_uri'], 'spotify:album:' + 'B' * 22)
                self.assertEqual(track['uri'], 'spotify:track:' + 'A' * 22)
            finally:
                self.dialogue.current_turn.reset(token)

    def test_old_prose_only_success_does_not_hide_dutch_or_english_foreign_cta(self):
        from scripts.verification.askdj_example_catalogue_golden import check_action_copy
        case = {'language': 'de', 'entry_id': 'play.artist'}
        body = {'text': 'Wähle einen Lautsprecher.', 'playback_actions': [{
            'kind': 'output', 'command': 'ask_dj_play_request_on_output',
            'label': 'Speel hier', 'button_label': 'Speel hier'}]}
        self.assertEqual(check_action_copy(case, body), ['action_label_locale_unproved'])
        body['playback_actions'][0].update(label='Hier abspielen', button_label='Hier abspielen')
        self.assertEqual(check_action_copy(case, body), [])
        body['playback_actions'][0].update(kind='track', command='', action_style='play_now',
            label='Play Now', button_label='Play Now')
        self.assertEqual(check_action_copy(case, body), ['action_label_locale_unproved'])

    def test_negative_semantic_or_language_assessment_cannot_be_promoted_by_prompt_changes(self):
        from custom_components.djconnect.narration_brief import assessed
        for failed in ('supported', 'language_ok', 'style_ok'):
            review = {key: key != failed for key in ('supported', 'language_ok', 'style_ok')}
            self.assertFalse(assessed(json.dumps(review)), failed)
        self.assertTrue(assessed(json.dumps(dict(supported=True, language_ok=True, style_ok=True))))

    def test_public_evidence_is_an_original_snapshot_for_both_acceptance_outcomes(self):
        from scripts.verification.askdj_example_catalogue_golden import append_public_support_observation
        for accepted in (True, False):
            outer = {'private_household': 'PRIVATE_OUTER_CANARY',
                'public_music_research': {'schema_version': 3, 'sources': [{'quote': 'Public fact.'}]}}
            review = {'supported': accepted}
            rows = []
            snapshot = append_public_support_observation(rows, case_id='original-request',
                accepted=accepted, answer='Public answer.', review=review,
                research=outer['public_music_research'])
            before = json.dumps(snapshot)
            outer['public_music_research']['sources'][0]['quote'] = 'LATE_CANARY' * 20000
            review['supported'] = not accepted
            self.assertEqual(json.dumps(rows[0]), before)
            self.assertNotIn('PRIVATE_OUTER_CANARY', before)
            self.assertEqual(snapshot['accepted'], accepted)
            self.assertEqual(snapshot['case_id'], 'original-request')

    def test_public_evidence_count_utf8_and_nonfinite_bounds_fail_without_partial_append(self):
        from scripts.verification.askdj_example_catalogue_golden import append_public_support_observation
        args = dict(case_id='original', accepted=True, answer='Public answer', review='{}', research={})
        for changed in ({'answer': 'é' * 65537}, {'research': {'nonfinite': float('nan')}}):
            rows = []
            with self.assertRaises((AssertionError, ValueError)):
                append_public_support_observation(rows, **(args | changed))
            self.assertEqual(rows, [])
        rows = []
        for _ in range(20):
            append_public_support_observation(rows, **args)
        with self.assertRaises(AssertionError):
            append_public_support_observation(rows, **args)
        self.assertEqual(len(rows), 20)
