"""Reference-only public topic: actual frame lifecycle, never factual authority."""
import json
import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


class PublicQueryReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        from custom_components.djconnect.ask_dj import dialogue, semantic_reads
        cls.d, cls.s = dialogue, semantic_reads

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def setUp(self):
        self.state = self.d.DialogueState()
        self.frame = self.state.frame('profile:one', 'default', 'generation')

    def turn(self, client, candidate=''):
        async def valid():
            pass
        return self.d.DialogueTurn(self.frame, 'profile:one', 'default', client,
            'digest', self.frame.generation, valid, None,
            public_query_candidate=candidate)

    def complete(self, turn, question):
        self.state.complete(turn, {'success': True, 'text': 'Unqualified response.',
            'text_source': 'core', 'is_generated_text': False,
            'knowledge_basis': 'public_research_unqualified', '_dialogue_question': question})

    def test_failed_named_answer_keeps_only_original_user_name_reference(self):
        self.complete(self.turn('first', 'Example Band'), 'Vertel wat leuks over Example Band')
        reference = self.frame.public_query_reference
        self.assertEqual(reference.subject, 'Example Band')
        self.assertEqual(reference.scope, 'profile:one')
        self.assertEqual(self.frame.subjects, [])
        self.assertTrue(all(m['role'] == 'user' for m in self.frame.messages))
        data = json.loads(self.s.prompt('Gewoon een verrassend feitje', 'nl',
            selected=False, active=False, recent_subject=reference.subject).split('\nData:\n')[1])
        self.assertEqual(data['recent_public_query']['subject'], 'Example Band')
        self.assertNotIn('Unqualified response', json.dumps(data))
        self.assertNotIn('profile:one', json.dumps(data))
        self.assertNotIn('request_hash', data['recent_public_query'])

    def test_model_body_or_unmentioned_name_cannot_publish_public_reference(self):
        self.complete(self.turn('forged', 'Other Band'), 'Vertel wat leuks over Example Band')
        self.assertIsNone(self.frame.public_query_reference)
        self.complete(self.turn('body-only'), 'Gewoon een feitje')
        self.assertIsNone(self.frame.public_query_reference)

    def test_late_earlier_completion_cannot_replace_newer_reference(self):
        earlier, later = self.turn('earlier', 'First Band'), self.turn('later', 'Second Band')
        self.complete(later, 'Vertel wat leuks over Second Band')
        current = self.frame.public_query_reference
        self.complete(earlier, 'Vertel wat leuks over First Band')
        self.assertIs(self.frame.public_query_reference, current)
        self.assertEqual(self.frame.current_client_id, 'later')

    def test_same_name_aba_never_revalidates_original_reference(self):
        self.complete(self.turn('first', 'Example Band'), 'Tell me about Example Band')
        original = self.frame.public_query_reference
        pending = self.turn('pending', 'Another Band')
        self.complete(self.turn('second', 'Second Band'), 'Tell me about Second Band')
        self.complete(self.turn('third', 'Example Band'), 'Tell me about Example Band')
        current = self.frame.public_query_reference
        self.assertIsNot(current, original)
        self.complete(pending, 'Tell me about Another Band')
        self.assertIs(self.frame.public_query_reference, current)

    def test_empty_reference_aba_after_newer_origin_erasure_blocks_late_completion(self):
        earlier, later = self.turn('earlier', 'First Band'), self.turn('later', 'Second Band')
        self.complete(later, 'Tell me about Second Band')
        reference = self.frame.public_query_reference
        self.state.withdraw_content('profile:one', request_hashes={reference.request_hash}, turn_ids=set())
        self.assertIsNone(self.frame.public_query_reference)
        self.assertGreater(self.frame.public_query_revision, earlier.public_reference_revision_at_start)
        self.complete(earlier, 'Tell me about First Band')
        self.assertIsNone(self.frame.public_query_reference)

    def test_origin_erasure_clears_reference_after_a_later_turn_became_current(self):
        self.complete(self.turn('first', 'Example Band'), 'Tell me about Example Band')
        reference = self.frame.public_query_reference
        later = self.turn('later')
        later.source_request_hashes = {reference.request_hash}
        self.complete(later, 'Gewoon een verrassend feitje')
        self.assertEqual(self.frame.current_client_id, 'later')
        self.state.withdraw_content('profile:one', request_hashes={reference.request_hash}, turn_ids=set())
        self.assertIsNone(self.frame.public_query_reference)

    def test_clear_generation_and_owner_boundaries_do_not_restore_reference(self):
        self.complete(self.turn('first', 'Example Band'), 'Tell me about Example Band')
        self.assertIsNone(self.state.frame('profile:two', 'default', 'generation').public_query_reference)
        self.assertIsNone(self.state.frame('profile:one', 'other', 'generation').public_query_reference)
        self.state.invalidate('profile:one')
        self.assertIsNone(self.frame.public_query_reference)

    def test_recent_plan_carries_only_angle_and_cannot_choose_subject_or_effect(self):
        value = {'read': 'research', 'reference': 'recent', 'exclude_current': False, 'angle': 'biography'}
        plan = self.s.parse_plan(json.dumps(value))
        self.assertIsNotNone(plan)
        self.assertEqual(plan.subject, '')
        for change in ({'subject': 'Unrelated Band'}, {'exclude_current': True},
                       {'angle': 'private history'}, {'read': 'play'}, {'uri': 'invented'}):
            self.assertIsNone(self.s.parse_plan(json.dumps({**value, **change})))

    def test_recent_fence_rejects_retarget_after_turn_start_and_same_name_aba(self):
        self.complete(self.turn('first', 'Example Band'), 'Tell me about Example Band')
        waiting = self.turn('waiting')
        original = waiting.public_reference_at_start
        scope = self.s.ReadScope(None, None, original, waiting.public_reference_revision_at_start)
        self.s._validate_recent_reference(waiting, scope)
        self.complete(self.turn('new', 'Second Band'), 'Tell me about Second Band')
        newer_scope = self.s.ReadScope(None, None, self.frame.public_query_reference,
                                      self.frame.public_query_revision)
        for candidate in (scope, newer_scope):
            with self.assertRaises(self.d.DialogueError):
                self.s._validate_recent_reference(waiting, candidate)
        self.complete(self.turn('same-name', 'Example Band'), 'Tell me about Example Band')
        with self.assertRaises(self.d.DialogueError):
            self.s._validate_recent_reference(waiting, scope)


class PublicQueryAwaitTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        from custom_components.djconnect.ask_dj import dialogue, semantic_reads
        cls.d, cls.s = dialogue, semantic_reads

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.state = self.d.DialogueState()
        self.frame = self.state.frame('profile:one', 'default', 'generation')
        self.complete(self.turn('origin', 'First Band'), 'Tell me about First Band')

    def turn(self, client, candidate=''):
        async def valid():
            pass
        turn = self.d.DialogueTurn(self.frame, 'profile:one', 'default', client,
            'digest', self.frame.generation, valid, None,
            public_query_candidate=candidate, style=self.d.style_projection({'language': 'nl'}))
        turn.source_request_hashes = set()
        return turn

    def complete(self, turn, question):
        self.state.complete(turn, {'success': True, 'text': 'Unqualified response.',
            '_dialogue_question': question})

    async def test_common_recent_execution_keeps_original_fence_over_lookup_and_delivery(self):
        from custom_components.djconnect import session_runtime
        from custom_components.djconnect.ask_dj import exploration
        turn = self.turn('followup')
        original = turn.public_reference_at_start
        scope = self.s.ReadScope(None, None, original, turn.public_reference_revision_at_start)
        plan = self.s.ReadPlan('research', 'recent', False, angle='biography')
        async def lookup(*args, **kwargs):
            self.assertIs(kwargs['recent_reference'], original)
            self.assertIn(original.request_hash, turn.source_request_hashes)
            await asyncio.sleep(0)
            await turn.guard()
            return {'success': True}
        token = self.d.current_turn.set(turn)
        try:
            with patch.object(session_runtime, 'session_runtime_manager', return_value=SimpleNamespace()), patch.object(
                    exploration, 'research_response', lookup):
                self.assertEqual(await self.s.execute_plan(None, None, 'Gewoon een feitje', plan, scope), {'success': True})
            self.assertTrue(turn.delivery_validators)
            for validate in turn.delivery_validators:
                validate()
            self.state.withdraw_content('profile:one', request_hashes={original.request_hash}, turn_ids=set())
            with self.assertRaises(self.d.DialogueError):
                turn.delivery_validators[-1]()
        finally:
            self.d.current_turn.reset(token)

    async def test_common_recent_execution_rejects_reference_replacement_during_lookup(self):
        from custom_components.djconnect import session_runtime
        from custom_components.djconnect.ask_dj import exploration
        turn = self.turn('followup')
        scope = self.s.ReadScope(None, None, turn.public_reference_at_start,
                                 turn.public_reference_revision_at_start)
        plan = self.s.ReadPlan('research', 'recent', False, angle='biography')
        async def lookup(*args, **kwargs):
            await asyncio.sleep(0)
            self.complete(self.turn('newer', 'Second Band'), 'Tell me about Second Band')
            await turn.guard()
            self.fail('Replaced original reference survived lookup await')
        token = self.d.current_turn.set(turn)
        try:
            with patch.object(session_runtime, 'session_runtime_manager', return_value=SimpleNamespace()), patch.object(
                    exploration, 'research_response', lookup):
                with self.assertRaises(self.d.DialogueError):
                    await self.s.execute_plan(None, None, 'Gewoon een feitje', plan, scope)
        finally:
            self.d.current_turn.reset(token)

    async def test_initial_guard_await_cannot_adopt_a_newer_public_reference(self):
        from custom_components.djconnect import session_runtime, ask_dj
        turn = self.turn('waiting')
        async def guard():
            await asyncio.sleep(0)
            self.complete(self.turn('newer', 'Second Band'), 'Tell me about Second Band')
        turn.validate = guard
        async def forbidden(*args, **kwargs):
            self.fail('Model interpretation started after original reference changed')
        manager = SimpleNamespace(current_active=lambda _: None)
        token = self.d.current_turn.set(turn)
        try:
            with patch.object(session_runtime, 'session_runtime_manager', return_value=manager), patch.object(
                    ask_dj, '_call_dialogue_agent', forbidden):
                with self.assertRaises(self.d.DialogueError):
                    await self.s.read_response(None, SimpleNamespace(config={}), 'Gewoon een feitje', {})
        finally:
            self.d.current_turn.reset(token)

    async def test_unused_recent_reference_does_not_fence_a_new_named_completion(self):
        from custom_components.djconnect import session_runtime, ask_dj
        from custom_components.djconnect.ask_dj import exploration
        turn = self.turn('new-named')
        async def agent(*args, **kwargs):
            return {'response': {'speech': {'plain': {'speech': json.dumps({
                'read': 'research', 'reference': 'named', 'exclude_current': False,
                'subject': 'Second Band', 'angle': 'biography'})}}}}
        async def lookup(*args, **kwargs):
            turn.public_query_candidate = 'Second Band'
            turn.reset_topic = True
            return {'success': True}
        token = self.d.current_turn.set(turn)
        try:
            with patch.object(session_runtime, 'session_runtime_manager', return_value=SimpleNamespace(current_active=lambda _: None)), patch.object(
                    ask_dj, '_assist_context', return_value={}), patch.object(
                    ask_dj, '_call_dialogue_agent', agent), patch.object(exploration, 'research_response', lookup):
                await self.s.read_response(None, SimpleNamespace(config={}), 'Tell me about Second Band', {})
            self.complete(turn, 'Tell me about Second Band')
            self.assertEqual(self.frame.public_query_reference.subject, 'Second Band')
            self.assertEqual(turn.delivery_validators, [])
            await turn.guard()
        finally:
            self.d.current_turn.reset(token)
