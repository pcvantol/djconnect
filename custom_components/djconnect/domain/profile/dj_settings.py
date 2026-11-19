"""Typed shared DJ choices; never provider configuration or device autoplay."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from ...presence_policy import DEFAULT as DEFAULT_PRESENCE, canonical_presence


SETTINGS_VERSION = 3
FIELDS = frozenset({'persona', 'voice', 'gender', 'mood', 'presence', 'announcement_output'})
ANNOUNCEMENT_OUTPUTS = frozenset({'client_device', 'both', 'ha_speaker', 'text_only'})
PERSONAS = frozenset({'home_dj', 'radio_dj', 'club_dj', 'festival_dj'})
MOODS = frozenset({'chill', 'groove', 'energy', 'party'})


class SettingsValidationError(ValueError):
    """A closed machine code, with no raw caller/provider material."""


class GenderPreference(StrEnum):
    DEFAULT = 'default'
    FEMALE = 'female'
    MALE = 'male'


def _identifier(value):
    if (type(value) is not str or not 0 < len(value) <= 128
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise SettingsValidationError('invalid_voice_identity')
    return value


@dataclass(frozen=True)
class VoiceSelection:
    """A semantic choice, not a transient audio processor/grant/revision."""

    kind: str = 'provider_default'
    provider_id: str = ''
    voice_id: str = ''

    def __post_init__(self):
        if self.kind == 'provider_default':
            if self.provider_id or self.voice_id:
                raise SettingsValidationError('invalid_default_voice')
        elif self.kind == 'provider_voice':
            _identifier(self.provider_id)
            _identifier(self.voice_id)
        else:
            raise SettingsValidationError('invalid_voice_kind')

    def as_dict(self):
        if self.kind == 'provider_default':
            return {'kind': self.kind}
        return {'kind': self.kind, 'provider_id': self.provider_id, 'voice_id': self.voice_id}

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict:
            raise SettingsValidationError('invalid_voice')
        kind = value.get('kind')
        fields = {'kind'} if kind == 'provider_default' else {'kind', 'provider_id', 'voice_id'}
        if set(value) != fields:
            raise SettingsValidationError('invalid_voice_fields')
        return cls(**value)


@dataclass(frozen=True)
class DJSettings:
    """The six orthogonal values shared by defaults and an effective Session."""

    persona: str = 'home_dj'
    voice: VoiceSelection = VoiceSelection()
    gender: GenderPreference = GenderPreference.DEFAULT
    mood: str = 'groove'
    presence: str = DEFAULT_PRESENCE
    announcement_output: str = 'client_device'

    def __post_init__(self):
        if type(self.persona) is not str or self.persona not in PERSONAS:
            raise SettingsValidationError('invalid_persona')
        if type(self.mood) is not str or self.mood not in MOODS:
            raise SettingsValidationError('invalid_mood')
        try:
            object.__setattr__(self, 'presence', canonical_presence(self.presence))
        except ValueError:
            raise SettingsValidationError('invalid_presence') from None
        if type(self.announcement_output) is not str or self.announcement_output not in ANNOUNCEMENT_OUTPUTS:
            raise SettingsValidationError('invalid_announcement_output')
        if not isinstance(self.voice, VoiceSelection):
            raise SettingsValidationError('invalid_voice')
        if not isinstance(self.gender, GenderPreference):
            raise SettingsValidationError('invalid_gender')

    def as_dict(self):
        return {'persona': self.persona, 'voice': self.voice.as_dict(),
                'gender': self.gender.value, 'mood': self.mood, 'presence': self.presence,
                'announcement_output': self.announcement_output}

    def patched(self, patch):
        if type(patch) is not dict or not patch or set(patch) - FIELDS:
            raise SettingsValidationError('invalid_settings_patch')
        values = dict(patch)
        if 'voice' in values:
            values['voice'] = VoiceSelection.from_dict(values['voice'])
        if 'gender' in values:
            if type(values['gender']) is not str:
                raise SettingsValidationError('invalid_gender')
            try:
                values['gender'] = GenderPreference(values['gender'])
            except ValueError:
                raise SettingsValidationError('invalid_gender') from None
        return replace(self, **values)

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or set(value) != FIELDS:
            raise SettingsValidationError('invalid_settings_fields')
        return cls().patched(value)


def validate_voice_combination(settings, *, provider_id, voice_genders, supported_genders):
    """Qualify an explicit update using the existing producer's exact inventory.

    This pure validator neither discovers metadata nor substitutes a voice.
    Availability reads retain the stored choice; only explicit updates call it.
    """
    voice, gender = settings.voice, settings.gender.value
    if voice.kind == 'provider_voice':
        if voice.provider_id != provider_id or voice.voice_id not in voice_genders:
            raise SettingsValidationError('selected_voice_unavailable')
        if gender != 'default' and voice_genders[voice.voice_id] != gender:
            raise SettingsValidationError('voice_gender_conflict')
    if gender != 'default' and gender not in supported_genders:
        raise SettingsValidationError('voice_gender_unavailable')
