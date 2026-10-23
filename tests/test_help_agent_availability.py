"""Request-owned Help metadata must not invent agent readiness or call it."""
import importlib
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
        owner = 'synthetic-help-owner'
        storage = SimpleNamespace(_loaded=loaded, household=SimpleNamespace(
            profiles={owner: SimpleNamespace(state='active')}))
        hass = SimpleNamespace(data={'djconnect': {self.store_key: storage}})
        runtime = SimpleNamespace(config={}, profile_context_profile_id=(
            owner if matching_owner else 'different-synthetic-owner'))
        pipeline = ModuleType('homeassistant.components.assist_pipeline.pipeline')
        conversation = ModuleType('homeassistant.components.conversation')
        resolutions = []

        def get_pipeline(*_args):
            resolutions.append('pipeline')
            return SimpleNamespace(conversation_engine='synthetic-agent')

        def get_agent(*_args):
            resolutions.append('agent')
            return agent

        pipeline.async_get_pipeline = get_pipeline
        conversation.async_get_agent = get_agent
        modules = {pipeline.__name__: pipeline, conversation.__name__: conversation}
        metadata = {'music_backend_available': True, 'music_backend': 'spotify_direct',
                    'music_backend_capabilities': {'supports_search': True}}
        token = self.turn.set(SimpleNamespace(scope='profile:' + owner))
        try:
            with patch.dict(sys.modules, modules), patch.object(
                    self.use_cases, 'music_backend_metadata', return_value=metadata):
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
            self.assertEqual(self.catalogue.help_sections('nl', context), [])

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
