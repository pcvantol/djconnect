"""Independent whole-draft selection on the original two-call owner path."""
import asyncio
import hashlib
from dataclasses import replace
import importlib
import json
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


class VerifiedNarrationDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.n = importlib.import_module('custom_components.djconnect.narration_brief')
        cls.p = importlib.import_module('custom_components.djconnect.playback_request')
        cls.pipeline = importlib.import_module('custom_components.djconnect.pipeline')

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def brief(self):
        return self.p.PlaybackRequestBrief(
            self.p.PlaybackAcceptance('private-recording', time.monotonic() + 30),
            'en', 'home_dj', 'groove', 'Local fallback.', ('{title}', '{status}'),
            'Actual accepted choice.', 'Actual observed playback.',
            (('{title}', 'Private title'), ('{status}', 'Playback is confirmed.')),
            selection_kind='playlist', playback_state='observed')

    def pool(self):
        return self.n.verified_drafts(json.dumps({'drafts': [
            'I have made room for {title}. {status}',
            'I am handing you {title} now. {status}']}),
            lambda value: self.n.candidate(self.brief(), json.dumps({'text': value})))

    def reviews(self, pool, positives):
        return json.dumps({'draft_reviews': [
            {**{key: value for key, value in row.items() if key != 'text'},
             'review': {'supported': positive, 'language_ok': True, 'style_ok': True}}
            for row, positive in zip(pool.records(), positives, strict=True)]})

    def test_malformed_batch_never_drops_or_reindexes_a_draft_or_falls_back_to_prose(self):
        valid = self.pool().texts[0]
        for value in [
            {'drafts': [valid, 'Missing the required original slots.']},
            {'drafts': [valid, None]}, {'drafts': [valid, valid]},
            {'drafts': [valid] * 3}, {'drafts': []}, {'drafts': [valid], 'text': valid},
            [valid], {'drafts': [valid, {'text': valid}]}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.n.verified_drafts(json.dumps(value),
                    lambda text: self.n.candidate(self.brief(), json.dumps({'text': text})))
        for raw in ['{"drafts":', '{"drafts":[],"drafts":[]}',
                    '{"drafts":[NaN]}', '{"drafts":["escaped\\u0000control"]}',
                    '{"drafts":["lone\\ud800surrogate"]}', '[' * 1000, 'x' * 8193]:
            with self.subTest(raw=raw[:60]), self.assertRaises((ValueError, RecursionError)):
                self.n.verified_drafts(raw, lambda text: text)

    def test_entire_review_envelope_must_bind_exact_original_indices_and_texts(self):
        pool = self.pool()
        good = json.loads(self.reviews(pool, [True, True]))
        rows = good['draft_reviews']
        invalid = [rows[::-1], rows[:1], rows + rows[:1],
            [{**rows[0], 'index': True}, rows[1]],
            [{**rows[0], 'sha256': rows[1]['sha256']}, rows[1]],
            [rows[0], {**rows[1], 'review': {'supported': True}}],
            [rows[0], {**rows[1], 'review': {**rows[1]['review'], 'supported': 1}}]]
        for altered in invalid:
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                self.n.bound_draft_reviews(json.dumps({'draft_reviews': altered}), pool)
        with self.assertRaises(ValueError):
            self.n.bound_draft_reviews(json.dumps(rows[0]['review']), pool)

    def test_one_generation_one_assessment_selects_only_first_fully_accepted_whole_draft(self):
        for positives, selected in [([False, True], 1), ([True, True], 0), ([False, False], None)]:
            with self.subTest(positives=positives):
                result, calls = asyncio.run(self.realize(positives))
                expected = 'Local fallback.' if selected is None else self.brief().render(self.pool().texts[selected])
                self.assertEqual(result, expected)
                self.assertEqual(len(calls), 2)
                self.assertNotIn('private-recording', json.dumps(calls))
                self.assertNotIn('Private title', json.dumps(calls))
                data = json.loads(calls[1]['text'].split('\nData:\n')[1])
                self.assertEqual(data['drafts'], self.pool().records())
                self.assertEqual(data['playback_state'], 'observed')
                self.assertEqual(json.loads(calls[0]['text'].split('\nData:\n')[1])['playback_state'], 'observed')

    async def realize(self, positives, *, withdraw=False, cancel=False, legacy=False):
        brief, calls = self.brief(), []
        active = True
        pool = self.pool()
        class Services:
            async def async_call(inner, domain, service, data, **kwargs):
                nonlocal active
                calls.append(data)
                if len(calls) == 1:
                    reply = json.dumps({'text': pool.texts[0]}) if legacy else json.dumps({'drafts': list(pool.texts)})
                else:
                    if cancel:
                        raise asyncio.CancelledError
                    active = not withdraw
                    reply = json.dumps({'supported': True, 'language_ok': True, 'style_ok': True}) if legacy else self.reviews(pool, positives)
                return {'response': {'speech': {'plain': {'speech': reply}}}}
        def admission():
            if not active:
                raise PermissionError('original_owner_withdrawn')
        with patch.object(self.pipeline, '_assist_context', return_value={'agent_id': 'same-qualified-agent'}):
            result = await self.pipeline.realize_session_narration(SimpleNamespace(services=Services()),
                narration=brief, admission=admission, fallback_text=brief.seed, conf={})
        return result, calls

    def test_original_owner_withdrawal_and_cancellation_close_all_alternatives(self):
        result, calls = asyncio.run(self.realize([True, True], withdraw=True))
        self.assertEqual(result, 'Local fallback.')
        self.assertEqual(len(calls), 2)
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(self.realize([True, True], cancel=True))

    def test_legacy_single_reply_keeps_existing_single_review_contract(self):
        result, calls = asyncio.run(self.realize([True, True], legacy=True))
        self.assertEqual(result, self.brief().render(self.pool().texts[0]))
        self.assertNotIn('drafts', json.loads(calls[1]['text'].split('\nData:\n')[1]))
        self.assertEqual(replace(self.brief(), playback_state='dispatched').playback_state, 'dispatched')

    def test_actual_receipt_state_owns_both_prompts_and_local_confirmation_in_all_locales(self):
        async def scenario():
            from custom_components.djconnect.ask_dj.dialogue import current_turn
            async def guard():
                pass
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                for state, matched, expected in [('observed', True, 'observed'),
                        ('observed', False, 'dispatched'), ('dispatched', True, 'dispatched'),
                        ('unknown', True, 'dispatched'), ('observed', 1, 'dispatched')]:
                    turn = SimpleNamespace(style={'language': locale, 'persona': 'home_dj', 'mood': 'groove'},
                        effect_started=True, accepted_playback_narration=False, agent_calls=0,
                        generation=1, frame=SimpleNamespace(generation=1), effect_validators=[], guard=guard)
                    receipt = {'schema_version': 1, 'state': state, 'observed_match': matched,
                        'selection': {'kind': 'playlist', 'media': {'uri': 'local-only', 'name': 'Private title'}}}
                    seen = []
                    async def realize(hass, *, narration, **kwargs):
                        seen.append(narration)
                        return narration.seed
                    token = current_turn.set(turn)
                    try:
                        with patch.object(self.pipeline, 'realize_session_narration', realize):
                            await self.p.response(SimpleNamespace(data={}), SimpleNamespace(config={}), receipt)
                    finally:
                        current_turn.reset(token)
                    brief = seen[0]
                    for prompt in (brief.prompt(verified_drafts=True), brief.assessment_prompt(self.pool().texts[0])):
                        projection = json.loads(prompt.split('\nData:\n')[1])
                        self.assertEqual(projection['playback_state'], expected)
                        self.assertEqual('observed and confirmed' in projection['reference'], expected == 'observed')
                    status = dict(brief.bindings)['{status}']
                    self.assertEqual(';' not in status and ' ; ' not in status, expected == 'observed')
        asyncio.run(scenario())


class VerifiedArtistDraftTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def test_artist_generation_separates_wire_contract_from_natural_story_in_all_locales(self):
        from tests.test_ask_dj_semantic_reads import id_review_fixture
        f = shared.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            catalogue = json.loads((Path(__file__).resolve().parents[1] /
                'custom_components/djconnect/ask_dj/examples_v1.json').read_text())
            questions = next(row['templates'] for row in catalogue['entries'] if row['id'] == 'listen.artist')
            for locale, question in questions.items():
                await f.history.async_clear('profile:profile-a')
                calls = []
                async def agent(hass, data, **kwargs):
                    instructions, body = data['text'].split('\nData:\n', 1)
                    projection = json.loads(body)
                    calls.append(projection)
                    if set(projection) == {'question', 'language', 'available'}:
                        reply = {'read': 'artist_story', 'reference': 'current', 'exclude_current': False}
                    elif 'evidence' not in projection:
                        self.assertTrue(instructions.startswith('DJConnect output contract: '))
                        self.assertIn('JSON envelope', instructions.split('\n', 1)[0])
                        self.assertEqual(projection['answer_form'], 'Natural prose inside each draft text; the outer response follows the Core-owned artist_evidence_drafts_v1 JSON output contract.')
                        self.assertIn('Choose a documented musical activity/work', instructions)
                        self.assertNotIn('Only natural prose, no JSON', instructions)
                        self.assertNotIn('No JSON', instructions)
                        reply = json.loads(shared._research_generation_fixture(projection, 'Volbeat is a Danish band.'))
                    else:
                        reply = id_review_fixture(projection)
                    return {'response': {'speech': {'plain': {'speech': json.dumps(reply) if isinstance(reply, dict) else reply}}}}
                async def status(*args, **kwargs):
                    return {'success': True, 'playback': {'uri': 'spotify:track:' + 'N' * 22,
                        'artist': 'Volbeat', 'title': 'Private current recording'}}
                with f.research_http(title='Volbeat', text='Volbeat is a Danish band.'), patch.object(
                        f.pipeline, '_call_conversation_process_transport', agent), patch.object(f.core, 'run_music_command', status):
                    await f.request(question, identifier='artist-envelope-' + locale, language=locale)
                self.assertEqual(len(calls), 3)
                self.assertEqual(f.effects, [])
        finally:
            await f.asyncTearDown()

    async def test_actual_paired_route_selects_whole_second_answer_without_extra_call_or_unused_history(self):
        from tests.test_ask_dj_semantic_reads import id_review_fixture
        f = shared.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            bad, good = 'Volbeat invented every instrument.', 'Volbeat is a Danish band.'
            for mode in ('second', 'all_false', 'swapped', 'malformed_last', 'first_bad_claim', 'first_bad_temporal', 'control'):
                await f.history.async_clear('profile:profile-a')
                calls = []
                async def agent(hass, data, **kwargs):
                    projection = json.loads(data['text'].split('\nData:\n', 1)[1])
                    calls.append(projection)
                    if set(projection) == {'question', 'language', 'available'}:
                        reply = {'read': 'artist_story', 'reference': 'current', 'exclude_current': False}
                    elif 'evidence' not in projection:
                        texts = ([good + '\x00', bad] if mode == 'control' else
                                 [good, bad] if mode.startswith('first_') else [bad, good])
                        reply = {'schema': 'artist_evidence_drafts_v1', 'drafts': [
                            {'anchors': [anchor['id']], 'text': text} for anchor, text in
                            zip(projection['literal_anchors'][:2], texts, strict=True)]}
                    else:
                        rows = []
                        for row in projection['drafts']:
                            review = id_review_fixture({**projection, 'answer': row['text']})
                            positive = row['index'] == (0 if mode.startswith('first_') else 1) and mode != 'all_false'
                            review.update(supported=positive, unsupported_claims=[] if positive else [row['text']])
                            if not positive:
                                review.update(claim_checks=[], temporal_claims=[])
                            rows.append({'index': row['index'], 'sha256': row['sha256'], 'review': review})
                        if mode == 'swapped':
                            rows.reverse()
                        if mode == 'malformed_last':
                            rows[-1]['review'].pop('style_ok')
                        if mode == 'first_bad_claim':
                            rows[-1]['review']['claim_checks'] = [{'unexpected_nested_field': 'invalid'}]
                        if mode == 'first_bad_temporal':
                            rows[-1]['review']['temporal_claims'] = {'not': 'a list'}
                        reply = {'draft_reviews': rows}
                    return {'response': {'speech': {'plain': {'speech': json.dumps(reply)}}}}
                async def status(hass, runtime, command, *args, **kwargs):
                    self.assertEqual(command, 'status')
                    return {'success': True, 'playback': {'uri': 'spotify:track:' + 'N' * 22,
                        'artist': 'Volbeat', 'title': 'Private current recording'}}
                with f.research_http(title='Volbeat', text=good + ' Volbeat performed a concert.'), patch.object(
                        f.pipeline, '_call_conversation_process_transport', agent), patch.object(
                        f.core, 'run_music_command', status):
                    answer, code = await f.request('tell me about this artist', identifier='draft-' + mode)
                if mode == 'control':
                    self.assertEqual(code, 502, answer)
                    self.assertEqual(len(calls), 2)
                    continue
                self.assertEqual(code, 200, answer)
                self.assertEqual(len(calls), 3)
                self.assertEqual(answer['conversation']['metrics']['agent_calls'], 3)
                self.assertEqual(answer['is_generated_text'], mode == 'second', answer)
                if mode == 'second':
                    self.assertEqual(answer['text'], good)
                    self.assertEqual(answer['knowledge_basis'], 'fetched_public_music_research_v1')
                else:
                    self.assertEqual(answer['knowledge_basis'], 'public_research_unqualified')
                self.assertNotIn(bad, json.dumps((await f.history.async_history('profile:profile-a'))['messages']))
                self.assertNotIn('Private current recording', json.dumps(calls))
                self.assertEqual(f.effects, [])
        finally:
            await f.asyncTearDown()


class ArtistGenerationWireMetadataTests(unittest.TestCase):
    def test_metadata_binds_only_user_generation_instructions_and_never_exports_data(self):
        from scripts.verification.askdj_example_catalogue_golden import artist_generation_wire as extract
        instructions = 'DJConnect output contract: JSON envelope. Return ONLY {"drafts": ["text"]}'
        private_data = {'style': {'language': 'en'}, 'public_music_research': {'schema_version': 3, 'sources': ['private-never-export']}}
        prompt = instructions + '\nData:\n' + json.dumps(private_data)
        result = extract([{'role': 'user', 'content': [{'type': 'input_text', 'text': prompt}]}])
        self.assertEqual(result, {'research_schema': 3, 'language': 'en', 'drafts_requested': True, 'wire_contract_first': True,
            'trusted_instructions_sha256': hashlib.sha256(instructions.encode()).hexdigest()})
        self.assertNotIn('private-never-export', json.dumps(result))
        self.assertIsNone(extract([{'role': 'assistant', 'content': prompt}]))
        self.assertIsNone(extract([{'role': 'user', 'content': 'Invalid\nData:\n['}]))
        self.assertIsNone(extract([{'role': 'user', 'content': 'Assessment\nData:\n' + json.dumps({'evidence': private_data})}]))
        untrusted = {'style': {'language': 'en'}, 'public_music_research': {'schema_version': 3}, 'source_excerpt': instructions}
        result = extract([{'role': 'user', 'content': 'Legacy prose\nData:\n' + json.dumps(untrusted)}])
        self.assertFalse(result['drafts_requested'])
        self.assertFalse(result['wire_contract_first'])


if __name__ == '__main__':
    unittest.main()
