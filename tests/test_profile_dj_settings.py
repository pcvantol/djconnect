"""Shared choices reject scope leakage, unsupported identity and axis coupling."""

import unittest

from tests.test_persistence_platform import PersistenceService  # noqa: F401
from custom_components.djconnect.domain.profile.dj_settings import (
    DJSettings, GenderPreference, SettingsValidationError, VoiceSelection,
    validate_voice_combination,
)


class ProfileDJSettingsModelTests(unittest.TestCase):
    def test_roundtrip_preserves_provider_bound_choice_and_all_five_axes(self):
        value = {'persona': 'festival_dj', 'voice': {'kind': 'provider_voice',
                 'provider_id': 'qualified-provider', 'voice_id': 'voice-7'},
                 'gender': 'female', 'mood': 'chill', 'presence': 'music_only'}
        choice = DJSettings.from_dict(value)
        self.assertEqual(choice.as_dict(), value)
        restored = DJSettings.from_dict(choice.as_dict())
        validate_voice_combination(restored, provider_id='qualified-provider',
            voice_genders={'voice-7': 'female'}, supported_genders={'female'})
        self.assertEqual(restored.persona, 'festival_dj')
        self.assertEqual(restored.mood, 'chill')

    def test_partial_change_never_changes_other_axes_or_input(self):
        initial = DJSettings().patched({'gender': 'female', 'persona': 'club_dj'})
        patch = {'mood': 'party'}
        changed = initial.patched(patch)
        self.assertEqual(changed.gender, GenderPreference.FEMALE)
        self.assertEqual(changed.persona, 'club_dj')
        self.assertEqual(changed.voice, initial.voice)
        self.assertEqual(changed.presence, initial.presence)
        self.assertEqual(initial.mood, 'groove')
        self.assertEqual(patch, {'mood': 'party'})

    def test_mass_assignment_wrong_types_and_numeric_legacy_mood_are_rejected(self):
        for patch in ({}, {'autoplay': True}, {'profile_id': 'other'},
                      {'device_token': 'secret'}, {'mood': 90}, {'mood': True},
                      {'persona': 'classic_radio'}, {'gender': None},
                      {'gender': True}, {'presence': False}):
            with self.subTest(patch=patch), self.assertRaises(SettingsValidationError):
                DJSettings().patched(patch)

    def test_no_partial_unknown_or_credential_bearing_stored_object(self):
        complete = DJSettings().as_dict()
        for value in ({}, {**complete, 'prompt': 'private'},
                      {k: v for k, v in complete.items() if k != 'voice'}):
            with self.assertRaises(SettingsValidationError):
                DJSettings.from_dict(value)
        for voice in ({'kind': 'provider_default', 'voice_id': 'hidden'},
                      {'kind': 'provider_voice', 'provider_id': 'p'},
                      {'kind': 'provider_voice', 'provider_id': 'p', 'voice_id': 'v', 'token': 'hidden'},
                      {'kind': 'provider_voice', 'provider_id': 'p', 'voice_id': 'v\nheader'},
                      {'kind': 'provider_voice', 'provider_id': 'p', 'voice_id': 'v'*129}):
            with self.assertRaises(SettingsValidationError):
                VoiceSelection.from_dict(voice)

    def test_withdrawal_and_conflict_do_not_rewrite_stored_preference(self):
        selected = DJSettings().patched({'voice': {'kind': 'provider_voice',
            'provider_id': 'p', 'voice_id': 'v'}, 'gender': 'female'})
        original = selected.as_dict()
        for provider, voices, genders in [('changed', {'v': 'female'}, {'female'}),
                ('p', {}, {'female'}), ('p', {'v': 'male'}, {'male'}),
                ('p', {'v': None}, set())]:
            with self.assertRaises(SettingsValidationError):
                validate_voice_combination(selected, provider_id=provider,
                    voice_genders=voices, supported_genders=genders)
            self.assertEqual(selected.as_dict(), original)

    def test_no_gender_provider_retains_concrete_voice_and_explicit_default(self):
        selected = DJSettings().patched({'voice': {'kind': 'provider_voice',
            'provider_id': 'p', 'voice_id': 'v'}})
        validate_voice_combination(selected, provider_id='p',
            voice_genders={'v': None}, supported_genders=set())
        default = selected.patched({'voice': {'kind': 'provider_default'}, 'gender': 'default'})
        validate_voice_combination(default, provider_id='other',
            voice_genders={}, supported_genders=set())
        self.assertEqual(default.voice, VoiceSelection())
