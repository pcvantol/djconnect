"""Contract2 owner settings boundary; one five-axis Runtime/Store acceptance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json

from .domain.profile.dj_settings import (
    DJSettings, FIELDS, MOODS, PERSONAS, SettingsValidationError, validate_voice_combination,
)
from .presence_policy import POLICIES
from .persistence.dj_settings import SettingsCommitError, SettingsRevisionConflict

PATH = '/api/djconnect/v1/profile/settings'
IDENTITY_FIELDS = frozenset({'contract_version', 'device_id', 'client_type'})
WRITE_FIELDS = IDENTITY_FIELDS | {'binding', 'operation_id', 'patch',
                                 'expected_defaults_revision', 'expected_session'}


def validate_request(data, *, write=False):
    """Closed schema; an arbitrary Profile ID or legacy init is not authority."""
    if type(data) is not dict or set(data) != (WRITE_FIELDS if write else IDENTITY_FIELDS):
        raise SettingsValidationError('invalid_settings_request')
    if type(data['contract_version']) is not int or data['contract_version'] != 2:
        raise SettingsValidationError('unsupported_contract_version')
    if data['client_type'] not in {'ios', 'macos', 'watchos', 'raspberry_pi', 'esp32'}:
        raise SettingsValidationError('unsupported_settings_client')
    from .client_identity import device_id_matches_client_type
    if type(data['device_id']) is not str or not device_id_matches_client_type(
            data['device_id'], data['client_type']):
        raise SettingsValidationError('invalid_settings_identity')
    if write:
        DJSettings().patched(data['patch'])
        revision = data['expected_defaults_revision']
        if type(revision) is not int or revision < 0:
            raise SettingsValidationError('invalid_settings_revision')
        context = data['expected_session']
        if context is not None and (
                type(context) is not dict or set(context) != {'session_id', 'generation', 'revision'}
                or type(context['revision']) is not int or context['revision'] < 0
                or any(type(context[k]) is not str or not 0 < len(context[k]) <= 128
                       for k in ('session_id', 'generation'))):
            raise SettingsValidationError('invalid_settings_session')


@dataclass(frozen=True)
class VoicePolicy:
    """Pure immutable capture of the existing provider's qualified metadata."""

    provider_id: str
    revision: str
    voices: tuple[tuple[str, str | None], ...]
    genders: tuple[str, ...]
    available: bool
    reason: str | None

    @classmethod
    def from_options(cls, options):
        voice = options.get('provider_voice') or {}
        available = options.get('state') == 'available'
        return cls(str(voice.get('engine') or ''), str(options['revision']),
                   tuple((v['voice_id'], v.get('gender')) for v in options.get('voices', [])),
                   tuple(options.get('gender_selection', {}).get('values', [])),
                   available, options.get('reason'))

    def validate(self, settings):
        # Explicit provider-default/no-preference is always a valid reset. Its
        # availability remains separately visible; no fallback is synthesized.
        if settings.voice.kind == 'provider_default' and settings.gender.value == 'default':
            return
        if not self.available:
            raise SettingsValidationError('selected_voice_unavailable')
        validate_voice_combination(settings, provider_id=self.provider_id,
                                   voice_genders=dict(self.voices), supported_genders=self.genders)

    def selection_state(self, settings):
        try:
            self.validate(settings)
        except SettingsValidationError as exc:
            return {'available': False, 'reason': str(exc)}
        return {'available': self.available, 'reason': None if self.available else self.reason}


def binding_digest(*, entry_id, device_id, profile_id, generation, token):
    """Opaque equality token, not a bearer credential or global Profile key."""
    return hashlib.sha256(json.dumps([entry_id, device_id, profile_id, generation,
        hashlib.sha256(token.encode()).hexdigest()], separators=(',', ':')).encode()).hexdigest()


def allowed_values(policy):
    return {'persona': sorted(PERSONAS), 'mood': sorted(MOODS), 'presence': list(POLICIES),
            'voice': {'kinds': ['provider_default', 'provider_voice'],
                      'provider_id': policy.provider_id,
                      'voices': [{'voice_id': voice, 'gender': gender} for voice, gender in policy.voices]},
            'gender': ['default', *policy.genders]}


async def async_handle_settings(hass, data, *, headers=None, write=False):
    """Ordinary paired device only, including when there is no active Session."""
    from .api_handlers import _session_profile_context, _conversation_profile_fence
    from .profile_context import profile_storage
    from .request_auth import request_token
    from .session_runtime import session_runtime_manager
    from .speech_processor import voice_options
    from .transport_delivery import register_delivery_admission

    def error(code, status, **extra):
        return {'success': False, 'error': code, **extra}, status

    try:
        validate_request(data, write=write)
    except (ValueError, TypeError):
        return error('invalid_settings_request', 400)
    headers = headers or {}
    if not str(headers.get('Authorization', '')).startswith('Bearer '):
        return error('unauthorized', 401)
    identity = {key: data[key] for key in IDENTITY_FIELDS}
    runtime, context, failure, status = await _session_profile_context(
        hass, dict(identity), headers=headers, user_id=None, source='profile_settings_v2')
    if failure is not None:
        return failure, status
    if context.profile.profile_type.value in {'guest', 'room', 'party'}:
        return error('owner_settings_not_allowed', 403)
    storage = profile_storage(hass)
    device = storage.household.devices.get(data['device_id'])
    entry = getattr(runtime, 'entry', None)
    generation = getattr(device, 'binding_generation', '')
    if entry is None or not generation:
        return error('settings_binding_unavailable', 503)
    binding = binding_digest(entry_id=entry.entry_id, device_id=data['device_id'],
                             profile_id=context.profile_id, generation=generation,
                             token=request_token(headers))
    manager = session_runtime_manager(hass)
    options = voice_options(hass, runtime.config)
    policy = VoicePolicy.from_options(options)

    def authority():
        try:
            _conversation_profile_fence(hass, runtime, identity, headers, context)
            current = storage.household.devices.get(data['device_id'])
            return (current is not None and current.binding_generation == generation
                    and hass.data.get('djconnect', {}).get('session_runtime_manager') is manager)
        except Exception:
            return False

    def commit_authority():
        return authority() and (not write or not ({'voice', 'gender'} & data['patch'].keys())
                                or voice_options(hass, runtime.config)['revision'] == policy.revision)

    try:
        if write:
            if data['binding'] != binding:
                return error('settings_binding_changed', 409)
            result = await manager.async_accept_dj_settings(
                owner_profile_id=context.profile_id, operation_id=data['operation_id'], binding=binding,
                patch=data['patch'], expected_defaults_revision=data['expected_defaults_revision'],
                expected_session=data['expected_session'], now_ms=int(datetime.now(UTC).timestamp()*1000),
                authorize=commit_authority, validate_voice=policy.validate)
            snapshot = result['snapshot']
        else:
            snapshot = await manager.async_read_dj_settings(owner_profile_id=context.profile_id,
                                                            authorize=authority)
            result = {'snapshot': snapshot}
        if not authority():
            return error('unauthorized', 401)
        register_delivery_admission(lambda: _require_authority(authority))
        return {'success': True, **result, 'contract_version': 2, 'binding': binding,
                'scope': 'profile_and_active_session', 'allowed_values': allowed_values(policy),
                'writable_fields': sorted(FIELDS), 'voice_revision': policy.revision,
                'voice_availability': policy.selection_state(DJSettings.from_dict(
                    snapshot['session']['settings'] if snapshot['session'] else snapshot['defaults'])),
                'as_of': datetime.now(UTC).isoformat(), 'cache_policy': 'private,no-store'}, 200
    except SettingsRevisionConflict as exc:
        return error('settings_revision_conflict', 409, current=exc.current)
    except PermissionError:
        return error('unauthorized', 401)
    except (SettingsValidationError, SettingsCommitError) as exc:
        return error(str(exc), 409)
    except RuntimeError:
        return error('settings_unavailable', 503)


def _require_authority(authority):
    if not authority():
        raise PermissionError('unauthorized')
