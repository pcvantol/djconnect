"""Version3 closed wire shape and generic provider metadata adaptation."""

import copy
import unittest

from tests import test_persistence_platform  # noqa: F401
from custom_components.djconnect.domain.profile.dj_settings import DJSettings, SettingsValidationError
from custom_components.djconnect.profile_settings import (
    VoicePolicy, allowed_values, binding_digest, validate_request,
)


class SharedSettingsContractTests(unittest.TestCase):
    def identity(self):
        return {'contract_version': 3, 'device_id': 'djconnect-ios-84B1B418D81E', 'client_type': 'ios'}

    def policy(self):
        return VoicePolicy.from_options({'revision': 'r1', 'state': 'available',
            'provider_voice': {'engine': 'tts.configured', 'pipeline_id': 'private_pipeline'},
            'voices': [{'voice_id': 'v1', 'gender': 'female'}, {'voice_id': 'v2', 'gender': 'male'}],
            'gender_selection': {'values': ['female', 'male']}})

    def test_closed_identity_and_write_schema(self):
        validate_request(self.identity())
        request = {**self.identity(), 'binding': 'b'*64, 'operation_id': 'uuidv7',
                   'patch': {'mood': 'chill'}, 'expected_defaults_revision': 0, 'expected_session': None}
        validate_request(request, write=True)
        for key, value in (('profile_id', 'other'), ('save_as_default', True), ('autoplay', True)):
            with self.subTest(key=key), self.assertRaises(SettingsValidationError):
                validate_request({**request, key: value}, write=True)
        with self.assertRaises(SettingsValidationError):
            validate_request({**request, 'expected_defaults_revision': True}, write=True)

    def test_provider_gender_and_concrete_voice_coherent_without_local_scope(self):
        policy = self.policy()
        settings = DJSettings().patched({'voice': {'kind': 'provider_voice',
                    'provider_id': 'tts.configured', 'voice_id': 'v1'}, 'gender': 'female'})
        policy.validate(settings)
        with self.assertRaises(SettingsValidationError):
            policy.validate(settings.patched({'gender': 'male'}))
        values = allowed_values(policy)
        self.assertEqual(values['gender'], ['default', 'female', 'male'])
        self.assertNotIn('pipeline_id', str(values))
        self.assertNotIn('device_local', str(values))

    def test_no_gender_provider_still_supports_concrete_voice(self):
        policy = VoicePolicy('tts.generic', 'r2', (('voice', None),), (), True, None)
        settings = DJSettings().patched({'voice': {'kind': 'provider_voice',
                    'provider_id': 'tts.generic', 'voice_id': 'voice'}})
        policy.validate(settings)
        with self.assertRaises(SettingsValidationError):
            policy.validate(settings.patched({'gender': 'female'}))

    def test_missing_or_withdrawn_provider_preserves_selection_and_allows_explicit_reset(self):
        settings = DJSettings().patched({'voice': {'kind': 'provider_voice',
                    'provider_id': 'tts.configured', 'voice_id': 'v1'}, 'gender': 'female'})
        before = copy.deepcopy(settings.as_dict())
        policy = VoicePolicy('', 'gone', (), (), False, 'tts_provider_unavailable')
        self.assertEqual(policy.selection_state(settings),
                         {'available': False, 'reason': 'selected_voice_unavailable'})
        self.assertEqual(settings.as_dict(), before)
        policy.validate(DJSettings())
        self.assertFalse(policy.selection_state(DJSettings())['available'])

    def test_binding_changes_with_original_authority_and_hides_token(self):
        kwargs = dict(entry_id='entry', device_id='device', profile_id='profile',
                      generation='epoch1', token='test-only-bearer')
        original = binding_digest(**kwargs)
        self.assertEqual(len(original), 64)
        self.assertEqual(original, binding_digest(**kwargs))
        for key in kwargs:
            changed = {**kwargs, key: kwargs[key] + 'other'}
            self.assertNotEqual(original, binding_digest(**changed))

    def test_speech_discovery_separates_legacy_local_and_shared_prepare_semantics(self):
        from custom_components.djconnect.session_speech import capability
        discovered = capability()
        self.assertEqual(discovered['version'], 1)
        self.assertEqual(discovered['legacy_voice_option_prepare_versions'], [1])
        versions = discovered['prepare_contracts']
        self.assertEqual(versions['1']['voice_preference_context']['storage_owner'], 'client')
        shared = versions['2']
        self.assertEqual(shared['processors'], ['ha_configured'])
        self.assertFalse(shared['caller_voice_override'])
        self.assertEqual(shared['voice_preference_context']['storage_owner'], 'core')
        self.assertEqual(shared['voice_preference_context']['session_end'], 'retain_profile_defaults')
        self.assertEqual(shared['settings_contract_version'], 2)
