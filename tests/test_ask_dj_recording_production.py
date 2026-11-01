"""Recording-purpose regressions; external provider/model/authority replies are synthetic."""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared
from tests.test_ask_dj_semantic_reads import id_review_fixture

URI = 'spotify:track:' + 'A'*22
AID = 'B'*22
PUBLIC = ('Example Band is een band die muziek maakt. '
          'Het nummer "Paper Windows" werd door Example Band in afzonderlijke sessies opgenomen.')
ANSWER = 'Paper Windows werd door Example Band in afzonderlijke sessies opgenomen.'


class RecordingProductionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = shared.SharedDialogueTest()
        await self.f.asyncSetUp()
        self.overrides = ExitStack()
        self.calls, self.prompts = [], []
        self.mode = 'production'
        self.current = {'uri': URI, 'artist': 'PRIVATE DISPLAY ARTIST',
                        'title': 'PRIVATE DISPLAY TITLE', 'is_playing': True}
        self.after_catalog = None
        self.before_interpret = None
        self.interpret_plan = None
        self.catalog = {'uri': URI, 'artist': 'Example Band', 'title': 'Paper Windows', 'artist_id': AID}
        from custom_components.djconnect import reply_artwork
        source = {'backend_id': 'synthetic-backend', 'music_account_id': 'synthetic-account',
                  'provider_entry_id': 'synthetic-entry', 'provider_account_id': 'synthetic-provider'}
        self.overrides.enter_context(patch.object(reply_artwork, 'source_admission', return_value=(source, lambda: True)))
        async def read(hass, runtime, command, value=None, **kwargs):
            self.calls.append((command, value))
            self.assertIn(command, {'status', 'track_metadata'}, 'No effect or other lookup authorized')
            if command == 'status':
                return {'success': True, 'playback': deepcopy(self.current)}
            self.assertEqual(value, URI)
            if self.after_catalog:
                await self.after_catalog()
            return {'success': True, 'track': deepcopy(self.catalog)}
        self.overrides.enter_context(patch.object(self.f.core, 'run_music_command', read))
        async def agent(hass, data, **kwargs):
            p = json.loads(data['text'].split('\nData:\n', 1)[1])
            self.prompts.append(p)
            if 'available' in p:
                if self.before_interpret:
                    await self.before_interpret()
                if self.interpret_plan is not None:
                    return {'response': {'speech': {'plain': {'speech': json.dumps(self.interpret_plan)}}}}
                reply = json.dumps({'read': 'none' if self.mode == 'clarify' else 'production_story',
                    'reference': 'none' if self.mode == 'clarify' else 'current', 'exclude_current': False})
            elif 'evidence' in p:
                reply = json.dumps(id_review_fixture(p))
            else:
                reply = shared._research_generation_fixture(p, ANSWER)
            return {'response': {'speech': {'plain': {'speech': reply}}}}
        self.overrides.enter_context(patch.object(self.f.pipeline, '_call_conversation_process_transport', agent))
        self.overrides.enter_context(self.f.research_http(title='Example Band', text=PUBLIC, entity_id='Q1'))

    async def asyncTearDown(self):
        # Restore our nested transports before the underlying fixture restores
        # its own originals; reversing this order leaks stale fixture methods.
        self.overrides.close()
        await self.f.asyncTearDown()

    async def test_direct_current_production_uses_catalogue_then_public_work_not_private_labels(self):
        result, code = await self.f.request('Vertel eens over deze productie', language='nl')
        self.assertEqual(code, 200, result)
        self.assertIn('Paper Windows', result['text'])
        self.assertFalse(result.get('clarification_required', False), result)
        self.assertIn(('track_metadata', URI), self.calls)
        self.assertNotIn('PRIVATE DISPLAY', json.dumps(self.prompts))
        self.assertNotIn('PRIVATE DISPLAY', json.dumps(self.f.web_calls))
        self.assertEqual(self.f.effects, [])

    async def test_current_actual_ha_receipt_binds_all_products_without_quality_or_native_claim(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root/'examples/client_contracts/ask_dj_recording_production_v1/actual-ha-wire.json').read_text())
        self.assertEqual(len(proof['source_pins']), 302)
        for name, digest in proof['source_pins'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((root/proof['harness']).read_bytes()).hexdigest(), proof['harness_sha256'])
        extension = proof['extension']
        self.assertEqual(extension['native'], 'NOT_RUN')
        self.assertEqual(extension['installed'], 'NOT_RUN')
        self.assertEqual(extension['factual_narrative_quality'], 'NOT_QUALIFIED')
        self.assertEqual(extension['effect_count'], 0)
        self.assertEqual(extension['model_provider_calls'], 0)
        self.assertEqual(len(extension['cases']), 7)
        self.assertEqual(set(extension['cases'].values()), {'PASS'})

    async def test_screenshot_clarification_then_current_keeps_original_purpose(self):
        self.mode = 'clarify'
        first, code = await self.f.request('Vertel eens over deze productie', identifier='production-first', language='nl')
        self.assertEqual(code, 200, first)
        self.assertTrue(first.get('clarification_required'), first)
        frame = self.f.history.dialogue.owners['profile:profile-a']['default']
        pending, revision = frame.pending, frame.pending_revision
        self.assertEqual(pending['type'], 'recording_production')
        self.assertNotIn('question', pending)
        self.mode = 'production'
        result, code = await self.f.request('Huidig nummer', identifier='production-current', language='nl')
        self.assertEqual(code, 200, result)
        self.assertIn('Paper Windows', result['text'])
        self.assertIsNone(frame.pending)
        self.assertEqual(frame.pending_revision, revision+1)
        self.assertEqual(self.f.effects, [])

    async def test_standalone_bare_current_is_a_read_without_model(self):
        result, code = await self.f.request('Huidig nummer', language='nl')
        self.assertEqual(code, 200, result)
        self.assertIn('PRIVATE DISPLAY TITLE', result['text'])
        self.assertEqual(self.prompts, [])
        self.assertNotIn(('track_metadata', URI), self.calls)
        self.assertEqual(self.f.effects, [])

    async def test_freeworded_selection_retains_purpose_in_shared_semantic_execution(self):
        frame = await self._clarify()
        original_hash = frame.pending['request_hash']
        self.interpret_plan = {'read': 'production_story', 'reference': 'current', 'exclude_current': False}
        result, code = await self.f.request('Ik bedoel het liedje dat nu speelt',
                                           identifier='freeworded-selection', language='nl')
        self.assertEqual(code, 200, result)
        self.assertIn('Paper Windows', result['text'])
        interpreted = next(p for p in reversed(self.prompts) if 'available' in p)
        self.assertTrue(interpreted['available']['production_selection_pending'])
        self.assertNotIn(original_hash, json.dumps(interpreted))
        self.assertIn(original_hash, frame.response_dependencies['freeworded-selection'])
        self.assertIsNone(frame.pending)
        self.assertIn(('track_metadata', URI), self.calls)

    async def test_freeworded_selection_rejects_original_expiry_during_interpretation(self):
        clock = [self.f.history.dialogue.clock()]
        with patch.object(self.f.history.dialogue, 'clock', lambda: clock[0]):
            frame = await self._clarify()
            deadline = frame.pending['deadline']
            async def expire():
                clock[0] = deadline
            self.before_interpret = expire
            self.interpret_plan = {'read': 'production_story', 'reference': 'current', 'exclude_current': False}
            result, code = await self.f.request('Ik bedoel het liedje dat nu speelt',
                                               identifier='expired-selection', language='nl')
        self.assertEqual(code, 409, result)
        self.assertFalse(any(c == 'track_metadata' for c, _ in self.calls))
        self.assertFalse(self.f.web_calls)

    async def test_private_or_local_recording_never_exports_work_labels(self):
        self.current['uri'] = 'spotify:local:PRIVATE:PRIVATE:PRIVATE:1'
        result, code = await self.f.request('Vertel eens over deze productie', language='nl')
        self.assertEqual(code, 200, result)
        self.assertEqual(result['knowledge_basis'], 'public_recording_research_unavailable')
        self.assertFalse(self.f.web_calls)
        self.assertFalse(any(c == 'track_metadata' for c, _ in self.calls))
        self.assertEqual(len(self.prompts), 1)

    async def test_pending_replacement_during_catalogue_read_rejects_before_public_lookup(self):
        self.mode = 'clarify'
        first, code = await self.f.request('Vertel eens over deze productie', identifier='race-first', language='nl')
        self.assertTrue(first.get('clarification_required'), first)
        frame = self.f.history.dialogue.owners['profile:profile-a']['default']
        async def replace_slot():
            original = deepcopy(frame.pending)
            frame.set_pending(None)
            frame.set_pending(original)
        self.after_catalog = replace_slot
        result, code = await self.f.request('Huidig nummer', identifier='race-current', language='nl')
        self.assertEqual(code, 409, result)
        self.assertFalse(self.f.web_calls)
        self.assertEqual(self.f.effects, [])

    async def test_catalogue_response_mismatch_does_not_research_private_or_other_work(self):
        self.catalog['uri'] = 'spotify:track:'+'C'*22
        result, code = await self.f.request('Vertel eens over deze productie', language='nl')
        self.assertEqual(code, 200, result)
        self.assertEqual(result['knowledge_basis'], 'public_recording_research_unavailable')
        self.assertFalse(self.f.web_calls)

    async def test_no_public_work_evidence_does_not_replace_production_with_artist_biography(self):
        with self.f.research_http(title='Example Band', text='Example Band is een band die muziek maakt.', entity_id='Q1'):
            result, code = await self.f.request('Vertel eens over deze productie', language='nl')
        self.assertEqual(code, 200, result)
        self.assertEqual(result['knowledge_basis'], 'public_recording_research_unavailable')
        self.assertEqual(len(self.prompts), 1)

    async def test_backend_exact_catalogue_read_closes_ambiguous_and_local_data(self):
        from custom_components.djconnect.spotify_backend import SpotifyBackend, SpotifyBackendError
        backend = object.__new__(SpotifyBackend)
        valid = {'id': 'A'*22, 'uri': URI, 'type': 'track', 'is_local': False, 'name': 'Paper Windows',
                 'artists': [{'id': AID, 'uri': 'spotify:artist:'+AID, 'type': 'artist', 'name': 'Example Band'}]}
        current = valid
        calls = []
        async def request(method, path):
            calls.append((method, path))
            return deepcopy(current)
        backend._request = request
        self.assertEqual(await backend.track_metadata(URI), self.catalog)
        self.assertEqual(calls, [('GET', '/tracks/'+'A'*22)])
        for change in ({'id': 'C'*22}, {'uri': 'spotify:track:'+'C'*22}, {'is_local': True},
                       {'is_local': 0}, {'type': 'episode'}, {'linked_from': {'id': 'D'*22}},
                       {'artists': []}, {'artists': valid['artists']*2}, {'name': None}):
            current = {**valid, **change}
            with self.subTest(change=change), self.assertRaises(SpotifyBackendError):
                await backend.track_metadata(URI)
        count = len(calls)
        for target in ('file:///PRIVATE', 'spotify:local:x:y:z:1', URI+'/other', None):
            with self.assertRaises(SpotifyBackendError):
                await backend.track_metadata(target)
        self.assertEqual(len(calls), count)

    async def _clarify(self, identifier='purpose-original'):
        self.mode = 'clarify'
        result, code = await self.f.request('Vertel eens over deze productie', identifier=identifier, language='nl')
        self.assertEqual(code, 200, result)
        self.assertTrue(result.get('clarification_required'), result)
        return self.f.history.dialogue.owners['profile:profile-a']['default']

    async def _captured_request(self, text, identifier):
        from custom_components.djconnect.transport_delivery import capture_delivery_admissions
        with capture_delivery_admissions() as admissions:
            result, code = await self.f.handlers.async_handle_ask_dj_message_payload(self.f.hass,
                {**self.f.identity, 'client_message_id': identifier, 'text': text,
                 'language': 'nl', 'audio_response': 'never'}, headers=self.f.headers)
        return result, code, tuple(admissions)

    async def test_first_clarification_delivery_cannot_survive_slot_replacement(self):
        self.mode = 'clarify'
        result, code, admissions = await self._captured_request('Vertel eens over deze productie', 'held-clarification')
        self.assertEqual(code, 200, result)
        self.assertTrue(admissions)
        for admit in admissions:
            await admit()
        frame = self.f.history.dialogue.owners['profile:profile-a']['default']
        frame.set_pending(deepcopy(frame.pending))
        from custom_components.djconnect.ask_dj.dialogue import DialogueError
        with self.assertRaises(DialogueError):
            for admit in admissions:
                await admit()

    async def test_own_consume_allows_delivery_but_subsequent_slot_aba_does_not(self):
        frame = await self._clarify()
        original = deepcopy(frame.pending)
        result, code, admissions = await self._captured_request('Huidig nummer', 'held-production')
        self.assertEqual(code, 200, result)
        self.assertIn('Paper Windows', result['text'])
        self.assertIsNone(frame.pending)
        for admit in admissions:
            await admit()
        frame.set_pending(original)
        frame.set_pending(None)
        from custom_components.djconnect.ask_dj.dialogue import DialogueError
        with self.assertRaises(DialogueError):
            for admit in admissions:
                await admit()

    async def test_unrelated_read_ignores_old_purpose_expiry_during_interpretation(self):
        clock = [self.f.history.dialogue.clock()]
        with patch.object(self.f.history.dialogue, 'clock', lambda: clock[0]):
            frame = await self._clarify()
            original_hash = frame.pending['request_hash']
            clock[0] = frame.pending['deadline'] - 0.5
            async def expire_unused():
                clock[0] += 1
            self.before_interpret = expire_unused
            self.interpret_plan = {'read': 'artist', 'reference': 'current', 'exclude_current': False}
            result, code = await self.f.request('hee wie zingdt er eigelijk wat nu opstaat?',
                                               identifier='independent-identity', language='nl')
        self.assertEqual(code, 200, result)
        self.assertIn('PRIVATE DISPLAY ARTIST', result['text'])
        self.assertNotIn(original_hash, frame.response_dependencies['independent-identity'])
        self.assertFalse(any(c == 'track_metadata' for c, _ in self.calls))

    async def test_unrelated_read_cannot_clear_a_newer_pending_slot(self):
        frame = await self._clarify()
        original = deepcopy(frame.pending)
        newer = {**original, 'request_hash': 'f'*64}
        async def replace_unused():
            frame.set_pending(newer)
        self.before_interpret = replace_unused
        self.interpret_plan = {'read': 'artist', 'reference': 'current', 'exclude_current': False}
        result, code = await self.f.request('hee wie zingdt er eigelijk wat nu opstaat?',
                                           identifier='unrelated-replacement', language='nl')
        self.assertEqual(code, 200, result)
        self.assertEqual(frame.pending, newer)
        self.assertNotIn(original['request_hash'], frame.response_dependencies['unrelated-replacement'])

    async def test_purpose_erasure_during_catalogue_read_closes_before_public_work(self):
        await self._clarify()
        async def erase():
            await self.f.history.async_clear('profile:profile-a')
        self.after_catalog = erase
        result, code = await self.f.request('Huidig nummer', identifier='erased-production', language='nl')
        self.assertEqual(code, 409, result)
        self.assertFalse(self.f.web_calls)
        self.assertEqual(self.f.effects, [])

    async def test_missing_selected_never_substitutes_current_playback(self):
        await self._clarify()
        result, code = await self.f.request('Het geselecteerde nummer', identifier='missing-selected', language='nl')
        self.assertEqual(code, 200, result)
        self.assertEqual(result['knowledge_basis'], 'public_recording_research_unavailable')
        self.assertFalse(any(c == 'track_metadata' for c, _ in self.calls))
        self.assertFalse(self.f.web_calls)

    async def test_foreign_current_source_never_exports_labels_or_catalogue_id(self):
        from custom_components.djconnect import reply_artwork
        with patch.object(reply_artwork, 'source_admission', return_value=(None, None)):
            result, code = await self.f.request('Vertel eens over deze productie', language='nl')
        self.assertEqual(code, 200, result)
        self.assertEqual(result['knowledge_basis'], 'public_recording_research_unavailable')
        self.assertFalse(any(c == 'track_metadata' for c, _ in self.calls))
        self.assertFalse(self.f.web_calls)

    async def test_artist_page_mentioning_another_recording_is_not_current_work_evidence(self):
        public = ('Example Band is een band die muziek maakt. '
                  'Het nummer "Paper Windows" werd door Another Band opgenomen.')
        with self.f.research_http(title='Example Band', text=public, entity_id='Q1'):
            result, code = await self.f.request('Vertel eens over deze productie', language='nl')
        self.assertEqual(code, 200, result)
        self.assertEqual(result['knowledge_basis'], 'public_recording_research_unavailable')
        self.assertEqual(len(self.prompts), 1)

    async def test_other_artist_prefix_or_suffix_cannot_supply_recording_provenance(self):
        from custom_components.djconnect.ask_dj import public_research
        for sentence in (
            'Example Band discussed how Another Example Band recorded the song "Paper Windows".',
            'The song "Paper Windows" by Example Band Junior was recorded in separate sessions.',
            'Het nummer "Paper Windows" werd door Example Band Junior in afzonderlijke sessies opgenomen.',
        ):
            with self.subTest(sentence=sentence):
                source = public_research._source('Wikipedia', 'Example Band',
                    'https://en.wikipedia.org/wiki/Example_Band', sentence, 'en', entity_id='Q1')
                self.assertIsNone(public_research.public_recording_names([source], 'Example Band', 'Paper Windows'))
        for sentence in (
            'Example Band recorded the song "Paper Windows".',
            'The song "Paper Windows" by Example Band was recorded in separate sessions.',
            'Het nummer "Paper Windows" werd door Example Band in afzonderlijke sessies opgenomen.',
        ):
            with self.subTest(sentence=sentence):
                source = public_research._source('Wikipedia', 'Example Band',
                    'https://en.wikipedia.org/wiki/Example_Band', sentence, 'en', entity_id='Q1')
                self.assertEqual(public_research.public_recording_names([source], 'Example Band', 'Paper Windows'),
                                 ('Example Band', 'Paper Windows'))

    async def test_cancel_during_catalogue_read_does_not_begin_public_research(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def held():
            entered.set()
            await release.wait()
        self.after_catalog = held
        task = asyncio.create_task(self.f.request('Vertel eens over deze productie', identifier='cancelled-production', language='nl'))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        try:
            with self.assertRaises(asyncio.CancelledError):
                await task
        finally:
            release.set()
        self.assertFalse(self.f.web_calls)
        self.assertEqual(self.f.effects, [])
