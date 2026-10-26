"""Request-owned Help metadata must not invent agent readiness or call it."""
import importlib
import asyncio
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from tests.test_http_voice_helpers import install_http_stubs


class HelpAgentAvailabilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_http_stubs()
        cls.catalogue = importlib.import_module(
            'custom_components.djconnect.ask_dj.example_catalogue')
        cls.use_cases = importlib.import_module('custom_components.djconnect.use_cases')
        cls.turn = importlib.import_module(
            'custom_components.djconnect.ask_dj.dialogue').current_turn
        cls.store_key = importlib.import_module(
            'custom_components.djconnect.domain.storage').STORE_KEY

    def context(self, agent, *, loaded=True, matching_owner=True):
        # Real committed storage/owner fixture; pipeline/Task metadata is an
        # explicit unit boundary, not actual HA/provider qualification.
        from tests.test_ask_dj_help_live_observation import HelpObservationTests
        from custom_components.djconnect.ask_dj.help_configuration import QUALIFIED_AGENT_PROMPT
        from custom_components.djconnect import structured_playback
        case = HelpObservationTests('test_global_read_is_detached_and_does_not_borrow_an_active_session')
        hass, storage, runtime, _ = asyncio.run(case.fixture())
        storage._loaded = loaded
        runtime.entry.data = {**runtime.entry.data, 'assist_pipeline_id': 'synthetic-pipeline',
                              'assist_structured_task_id': 'ai_task.synthetic'}
        pipeline = ModuleType('homeassistant.components.assist_pipeline.pipeline')
        pipeline.KEY_ASSIST_PIPELINE = 'synthetic-loaded-pipeline'
        hass.data[pipeline.KEY_ASSIST_PIPELINE] = object()
        hass.services = SimpleNamespace(has_service=lambda *_: True)
        resolutions = []
        # Preserve pipeline identity across final metadata rechecks.
        selected = SimpleNamespace(id='synthetic-pipeline', conversation_engine='conversation.synthetic')
        def get_pipelines(_hass):
            resolutions.append('pipeline')
            return {'synthetic-pipeline': selected}
        pipeline.async_get_pipelines = get_pipelines
        options = dict(chat_model='gpt-6-luna', max_tokens=3000, reasoning_effort='medium',
            store_responses=False, web_search=False, code_interpreter=False, service_tier='auto')
        if agent is not None:
            agent.subentry = SimpleNamespace(data={**options, 'llm_hass_api': [], 'prompt': QUALIFIED_AGENT_PROMPT})
        binding = SimpleNamespace(agent=agent, entity=object(), entry=object(),
            subentry=SimpleNamespace(data=options), fingerprint='synthetic-original-public-revision')
        def get_task(*_args, **_kwargs):
            resolutions.append('agent')
            return binding
        token = self.turn.set(SimpleNamespace(scope='profile:' + ('owner' if matching_owner else 'foreign'), session_id=''))
        try:
            with patch.dict(sys.modules, {pipeline.__name__: pipeline}), patch.object(
                    structured_playback, 'capture_task', get_task), patch.object(
                    self.use_cases, 'music_backend_metadata', side_effect=AssertionError('no creating metadata accessor')):
                result = self.catalogue.help_context(hass, runtime)
        finally:
            self.turn.reset(token)
        return result, resolutions

    @staticmethod
    async def never_process(*_args, **_kwargs):
        raise AssertionError('Help readiness must not call an agent or provider')

    def test_missing_readiness_does_not_advertise_an_agent_route(self):
        fixture = self.catalogue.catalogue()
        fixture['status'] = 'qualified_v1'
        cooking = next(e for e in fixture['entries'] if e['id'] == 'play.cooking')
        cooking['publication'] = 'qualified_v1'
        cooking['qualification']['nl'] = {
            'state': 'qualified_owner_route', 'route': cooking['route']}
        with patch.object(self.catalogue, '_CATALOGUE', fixture):
            context, resolutions = self.context(SimpleNamespace(async_process=self.never_process))
            self.assertEqual(resolutions, ['pipeline', 'agent'])
            self.assertIs(context.get('agent_available'), False)
            self.assertNotIn('play.cooking', [e['id'] for e in
                self.catalogue.eligible(context, 'ask_dj', 'nl')])
            self.assertNotIn('play.cooking', [e['id'] for e in
                self.catalogue.eligible(context, 'ask_dj', 'nl', for_help=True)])

    def test_only_explicit_boolean_readiness_with_callable_process_is_known(self):
        for value in (True, False, None, 1, 0, 'true'):
            with self.subTest(value=value):
                context, _ = self.context(SimpleNamespace(
                    available=value, async_process=self.never_process))
                self.assertIs(context.get('agent_available'), value is True)
        for agent in (None, SimpleNamespace(available=True),
                      SimpleNamespace(available=True, async_process=None)):
            with self.subTest(agent=agent):
                context, _ = self.context(agent)
                self.assertIs(context.get('agent_available'), False)

    def test_readiness_property_failure_stays_unknown_without_a_call(self):
        class Broken:
            @property
            def available(self):
                raise RuntimeError('synthetic unavailable metadata')
        context, _ = self.context(Broken())
        self.assertIs(context.get('agent_available'), False)

    def test_unloaded_or_other_owner_never_resolves_an_agent(self):
        for options in ({'loaded': False}, {'matching_owner': False}):
            context, resolutions = self.context(SimpleNamespace(
                available=True, async_process=self.never_process), **options)
            self.assertEqual(resolutions, [])
            self.assertNotIn('agent_available', context)
