"""Presentation masks qualify actual route classes, not a generic agent flag."""
from copy import deepcopy
import importlib
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()
from custom_components.djconnect.ask_dj import help_configuration as configuration  # noqa: E402
from custom_components.djconnect.ask_dj import example_catalogue as catalogue  # noqa: E402


class HelpConfigurationTests(unittest.TestCase):
    def test_published_en_nl_leaves_join_original_content_questions_and_preserve_other_locales(self):
        import hashlib
        import json
        from pathlib import Path
        from scripts.verification.askdj_example_catalogue_golden import cases
        root = Path(__file__).resolve().parents[1]
        receipt = json.loads((root / 'docs/verification/fixtures/help_en_nl_text_qualification_v2.json').read_text())
        source = catalogue.catalogue()
        self.assertEqual(source['revision'], 2)
        self.assertEqual((receipt['qualified_entry_locales'], receipt['pending_entry_locales']), (28, 42))
        self.assertEqual(receipt['catalogue_sha256'], catalogue.capability()['sha256'])
        original = {row['id']: row for row in receipt['original_40_cases']}
        self.assertEqual(len(original), 40)
        self.assertTrue(all(row['status'] == 'PASS' for row in original.values()))
        for row in cases():
            if row['language'] in {'en', 'nl'}:
                self.assertEqual(hashlib.sha256(row['question'].encode()).hexdigest(),
                                 original[row['id']]['question_sha256'])
        for entry in source['entries']:
            for language, leaf in entry['qualification'].items():
                self.assertEqual(leaf['state'] == 'qualified_owner_route', language in {'en', 'nl'})
        self.assertEqual(receipt['original_sdk_reserved'], 70)
        self.assertEqual(receipt['original_sdk_completed'], 70)
        self.assertEqual(receipt['installed'], 'NOT_RUN')
        self.assertEqual(receipt['original_source'], '608bc7d15aab813649edb0095476ceb4cfb42a7e')

    def test_new_publication_preserves_original_case_words_and_cannot_reopen_consumed_runner(self):
        from pathlib import Path
        from tests.help_catalogue_history import original_catalogue_v1
        from scripts.verification import askdj_example_catalogue_golden as golden
        from tools.verification import help_content_probe
        import importlib.util
        root = Path(__file__).resolve().parents[1]
        current = golden.cases() + golden.chain_cases()
        current_manifest = golden.manifest_digest()
        self.assertNotEqual(current_manifest, help_content_probe.MANIFEST)
        with original_catalogue_v1():
            self.assertEqual(golden.cases() + golden.chain_cases(), current)
            self.assertEqual(golden.manifest_digest(), help_content_probe.MANIFEST)
        # Tests of old budget/decoder rules do not rebind a consumed runner to V2.
        for file in ('run_help100_artist_envelope_20261025.py',
                     'run_help100_artist_evidence_first_20261025.py',
                     'run_help100_public_source_witness_20261025.py',
                     'run_help100_request_bound_alternatives_20261025.py',
                     'run_help100_verified_drafts_20261025.py'):
            spec = importlib.util.spec_from_file_location('historical_closed_help_profile',
                root / 'tools/verification' / file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with self.subTest(file=file), self.assertRaisesRegex(ValueError, 'PROFILE_INVALID'):
                module.profile(root)

    def options(self):
        return dict(chat_model='gpt-6-luna', max_tokens=3000, reasoning_effort='medium',
                    store_responses=False, web_search=False, code_interpreter=False,
                    service_tier='auto')

    def test_all14_dependencies_are_explicit_without_language_judge_dependency(self):
        identifiers = {e['id'] for e in catalogue.catalogue()['entries']}
        self.assertEqual(identifiers, configuration.MODEL_ENTRY_IDS | configuration.DIRECT_ENTRY_IDS)
        self.assertFalse(configuration.MODEL_ENTRY_IDS & configuration.DIRECT_ENTRY_IDS)
        self.assertEqual(configuration.MODEL_ENTRY_IDS,
                         {'play.artist', 'play.cooking', 'play.quiet', 'listen.artist'})
        rows = {e['id']: e for e in catalogue.catalogue()['entries']}
        self.assertNotIn('agent_available', rows['play.artist']['requires'])
        self.assertNotIn('agent_available', rows['play.quiet']['requires'])

    def test_exact_winning_options_unknown_bool_low_legacy_and_partial_are_closed(self):
        good = self.options()
        self.assertTrue(configuration.qualified_task_options(good))
        for key in good:
            broken = {k: v for k, v in good.items() if k != key}
            self.assertFalse(configuration.qualified_task_options(broken), key)
        for key, value in [('max_tokens', True), ('max_tokens', 2999),
                           ('reasoning_effort', 'low'), ('chat_model', 'other'),
                           ('store_responses', 0), ('web_search', None),
                           ('code_interpreter', True), ('service_tier', 'priority')]:
            self.assertFalse(configuration.qualified_task_options({**good, key: value}))
        # The original official conversation profile omits service_tier; its
        # pinned provider default is auto. The explicit AI Task does not omit it.
        without_tier = {k: v for k, v in good.items() if k != 'service_tier'}
        self.assertTrue(configuration.qualified_task_options(without_tier, agent=True))

    def test_missing_loaded_pipeline_never_calls_a_creating_accessor(self):
        module = ModuleType('homeassistant.components.assist_pipeline.pipeline')
        module.KEY_ASSIST_PIPELINE = 'already-loaded-pipelines'
        module.async_get_pipelines = lambda _: self.fail('cold accessor called')
        with patch.dict(sys.modules, {module.__name__: module}):
            self.assertFalse(configuration.loaded_model_configuration(SimpleNamespace(data={}), {}))

    def test_loaded_pipeline_requires_selected_matching_task_and_static_original_prompt(self):
        module = ModuleType('homeassistant.components.assist_pipeline.pipeline')
        module.KEY_ASSIST_PIPELINE = 'already-loaded-pipelines'
        module.async_get_pipelines = lambda _: {
            'selected': SimpleNamespace(id='selected', conversation_engine='conversation.selected')}
        options = {**self.options(), 'llm_hass_api': [],
                   'prompt': configuration.QUALIFIED_AGENT_PROMPT}
        agent = SimpleNamespace(available=True, subentry=SimpleNamespace(data=options),
                                async_process=lambda: None)
        binding = SimpleNamespace(agent=agent, subentry=SimpleNamespace(data=self.options()))
        hass = SimpleNamespace(data={module.KEY_ASSIST_PIPELINE: object()},
            services=SimpleNamespace(has_service=lambda *args: True))
        task = importlib.import_module('custom_components.djconnect.structured_playback')
        config = {'assist_pipeline_id': 'selected', 'assist_structured_task_id': 'ai_task.selected'}
        with patch.dict(sys.modules, {module.__name__: module}), patch.object(
                task, 'capture_task', return_value=binding) as capture:
            self.assertTrue(configuration.loaded_model_configuration(hass, config))
            capture.assert_called_once_with(hass, 'conversation.selected', 'ai_task.selected', loaded_only=True)
            agent.available = None
            self.assertFalse(configuration.loaded_model_configuration(hass, config))
            agent.available = True
            options['prompt'] += ' extra unqualified instruction'
            self.assertFalse(configuration.loaded_model_configuration(hass, config))
            options['prompt'] = configuration.QUALIFIED_AGENT_PROMPT
            options['llm_hass_api'] = ['assist']
            self.assertFalse(configuration.loaded_model_configuration(hass, config))
            options['llm_hass_api'] = []
            self.assertFalse(configuration.loaded_model_configuration(hass, {**config, 'assist_pipeline_id': 'missing'}))

    def test_same_per_entry_mask_applies_to_help_and_chips_and_unknown_is_false(self):
        data = catalogue.catalogue()
        data['status'] = 'qualified_v1'
        for row in data['entries']:
            row['publication'] = 'qualified_v1'
            row['qualification']['en']['state'] = 'qualified_owner_route'
        context = {'catalogue': {**catalogue.capability(), 'qualified': True},
                   'contracts': {'session_forecast': 1}, 'slots': {'artist': 'Synthetic artist'}}
        context.update({key: True for row in data['entries'] for key in row['requires']})
        with patch.object(catalogue, '_CATALOGUE', data), patch.object(
                configuration, 'loaded_model_configuration', return_value=False):
            context['entry_configuration'] = configuration.entry_configuration_mask(None, {})
            help_ids = {e['id'] for e in catalogue.eligible(context, 'ask_dj', 'en', for_help=True)}
            chip_ids = {e['id'] for e in catalogue.eligible(context, 'ask_dj', 'en')}
            self.assertEqual(help_ids, configuration.DIRECT_ENTRY_IDS)
            self.assertEqual(chip_ids, help_ids)
            # agent_available alone cannot restore either undeclared handover.
            self.assertNotIn('play.artist', help_ids)
            self.assertNotIn('play.quiet', help_ids)
            broken = deepcopy(context)
            broken.pop('entry_configuration')
            self.assertEqual(catalogue.eligible(broken, 'ask_dj', 'en', for_help=True), [])
            broken['entry_configuration'] = dict.fromkeys(help_ids, 1)
            self.assertEqual(catalogue.eligible(broken, 'ask_dj', 'en', for_help=True), [])
            context['entry_configuration']['play.artist'] = True
            context['slots'] = {}
            self.assertIn('play.artist', {e['id'] for e in catalogue.eligible(context, 'ask_dj', 'en', for_help=True)})
            self.assertNotIn('play.artist', {e['id'] for e in catalogue.eligible(context, 'ask_dj', 'en')})

    def test_original_model_binding_revision_survives_no_aba_restore(self):
        agent, entity, entry, subentry, pipeline = (object() for _ in range(5))
        first = SimpleNamespace(agent=agent, entity=entity, entry=entry,
                                subentry=subentry, fingerprint='original-public-revision')
        restored = SimpleNamespace(agent=agent, entity=entity, entry=entry,
                                   subentry=subentry, fingerprint='changed-and-restored-public-revision')
        with patch.object(configuration, '_capture_model_configuration',
                side_effect=[(pipeline, first), (pipeline, first), (pipeline, restored)]):
            mask = configuration.entry_configuration_mask(None, {})
            self.assertTrue(mask['play.artist'])
            self.assertTrue(mask.current())
            self.assertFalse(mask.current())
