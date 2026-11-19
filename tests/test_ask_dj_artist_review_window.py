"""Real public-task coroutine: review timeout, cancellation and binding fences."""
import asyncio
from contextvars import ContextVar
import hashlib
import importlib
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


class ArtistReviewWindowTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()
        cls.transport = importlib.import_module('custom_components.djconnect.structured_playback')
        cls.artist = importlib.import_module('custom_components.djconnect.structured_artist')

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def scenario(self, operation, *, cancel=False, changed=False):
        prompt = 'Synthetic public-task timeout probe'
        owner = SimpleNamespace(conversation_id='owned', cleaned=False)
        owner.async_cleanup = lambda: setattr(owner, 'cleaned', True)
        sessions = ModuleType('homeassistant.helpers.chat_session')
        sessions.current_session = ContextVar('window_test_session', default=None)
        sessions.DATA_CHAT_SESSION = 'window_test_sessions'
        tasks = ModuleType('homeassistant.components.ai_task')
        class Result:
            def __init__(self):
                self.data = {'value': 'original'}
                self.conversation_id = 'owned'
        tasks.GenDataTaskResult = Result
        hass = SimpleNamespace(data={sessions.DATA_CHAT_SESSION: {}},
                               services=SimpleNamespace(has_service=lambda *args: True))
        calls = []
        entered = asyncio.Event()
        async def generate(*args, **kwargs):
            calls.append(kwargs)
            hass.data[sessions.DATA_CHAT_SESSION]['owned'] = owner
            sessions.current_session.set(owner)
            entered.set()
            await asyncio.sleep(.31)
            return Result()
        tasks.async_generate_data = generate
        binding = SimpleNamespace(agent=object(), entity=object(), entry=object(),
                                  subentry=object(), fingerprint='original')
        captures = []
        def capture(*args):
            captures.append(True)
            if changed and len(captures) > 1:
                return SimpleNamespace(**{**vars(binding), 'fingerprint': 'changed'})
            return binding
        original_timeout = asyncio.timeout
        seconds_seen = []
        def scaled(seconds):
            seconds_seen.append(seconds)
            return original_timeout(seconds / 100)
        artist = (None if operation is None else self.artist.ArtistTask(
            operation, hashlib.sha256(prompt.encode()).hexdigest()))
        components = importlib.import_module('homeassistant.components')
        helpers = importlib.import_module('homeassistant.helpers')
        with patch.dict(sys.modules, {'homeassistant.components.ai_task': tasks,
                                      'homeassistant.helpers.chat_session': sessions}), \
             patch.object(components, 'ai_task', tasks, create=True), \
             patch.object(helpers, 'chat_session', sessions, create=True), \
             patch.object(self.transport, 'capture_task', capture), \
             patch.object(self.transport, 'role_schema', return_value=lambda v: v), \
             patch.object(self.artist, 'schema', return_value=lambda v: v), \
             patch.object(self.transport.asyncio, 'timeout', scaled):
            pending = asyncio.create_task(self.transport.generate(hass, agent_id='agent',
                task_id='task', prompt=prompt, artist=artist,
                brief=SimpleNamespace(literal_gap_slots=lambda: ()) if artist is None else None,
                admission=lambda: None))
            await asyncio.wait_for(entered.wait(), 2)
            if cancel:
                pending.cancel()
            try:
                result = await pending
            finally:
                self.assertTrue(owner.cleaned)
                self.assertEqual(len(calls), 1)
                self.assertEqual(seconds_seen, [60 if operation == 'artist_word_review_v1' else 30])
        return result

    async def test_review_can_finish_after_generation_limit_without_retry(self):
        self.assertEqual(await self.scenario('artist_word_review_v1'), '{"value": "original"}')

    async def test_generation_and_playback_keep_original_short_limit(self):
        for operation in ('artist_generation_v1', None):
            with self.subTest(operation=operation), self.assertRaises(TimeoutError):
                await self.scenario(operation)

    async def test_external_cancellation_cleans_owned_session_and_never_retries(self):
        with self.assertRaises(asyncio.CancelledError):
            await self.scenario('artist_word_review_v1', cancel=True)

    async def test_task_revision_change_closes_completed_review(self):
        with self.assertRaisesRegex(Exception, 'structured_playback_task_changed'):
            await self.scenario('artist_word_review_v1', changed=True)
