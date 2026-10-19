"""Contract3 owner settings boundary; one six-axis Runtime/Store acceptance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json

from .domain.profile.dj_settings import (
    ANNOUNCEMENT_OUTPUTS, DJSettings, FIELDS, MOODS, PERSONAS, SETTINGS_VERSION,
    SettingsValidationError, validate_voice_combination,
)
from .presence_policy import POLICIES
from .persistence.dj_settings import SettingsCommitError, SettingsRevisionConflict

PATH = '/api/djconnect/v1/profile/settings'
CHANGE_EVENT = 'djconnect_profile_dj_settings_changed'
IDENTITY_FIELDS = frozenset({'contract_version', 'device_id', 'client_type'})
WRITE_FIELDS = IDENTITY_FIELDS | {'binding', 'operation_id', 'patch',
                                 'expected_defaults_revision', 'expected_session'}
OPERATION_FIELDS = IDENTITY_FIELDS | {'binding', 'operation_id'}


def validate_request(data, *, write=False, operation=False):
    """Closed schema; an arbitrary Profile ID or legacy init is not authority."""
    fields = WRITE_FIELDS if write else OPERATION_FIELDS if operation else IDENTITY_FIELDS
    if type(data) is not dict or set(data) != fields:
        raise SettingsValidationError('invalid_settings_request')
    if type(data['contract_version']) is not int or data['contract_version'] != SETTINGS_VERSION:
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
    labels: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_options(cls, options):
        voice = options.get('provider_voice') or {}
        available = options.get('state') == 'available'
        return cls(str(voice.get('engine') or ''), str(options['revision']),
                   tuple((v['voice_id'], v.get('gender')) for v in options.get('voices', [])),
                   tuple(options.get('gender_selection', {}).get('values', [])),
                   available, options.get('reason'),
                   tuple((v['voice_id'], v.get('name') or v['voice_id']) for v in options.get('voices', [])))

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
            'announcement_output': sorted(ANNOUNCEMENT_OUTPUTS),
            'voice': {'kinds': ['provider_default', 'provider_voice'],
                      'provider_id': policy.provider_id,
                      'voices': [{'voice_id': voice, 'name': dict(policy.labels).get(voice, voice),
                                  'gender': gender} for voice, gender in policy.voices]},
            'gender': ['default', *policy.genders]}


async def async_handle_settings(hass, data, *, headers=None, write=False, operation=False,
                                validate_ingress=None):
    """Ordinary paired device only, including when there is no active Session."""
    from .api_handlers import _session_profile_context, _conversation_profile_fence
    from .profile_context import profile_storage
    from .request_auth import request_token, resolve_runtime, runtime_matches_device, authorize_runtime_device_request
    from .session_runtime import session_runtime_manager
    from .speech_processor import voice_options
    from .settings_migration import assessment
    from .announcement_policy import output_policy
    from .transport_delivery import register_delivery_admission

    def error(code, status, **extra):
        return {'success': False, 'error': code, **extra}, status

    try:
        validate_request(data, write=write, operation=operation)
    except SettingsValidationError as exc:
        if str(exc) == 'unsupported_contract_version':
            return error('settings_contract_upgrade_required', 426, settings_contract_version=SETTINGS_VERSION)
        return error('invalid_settings_request', 400)
    except (ValueError, TypeError):
        return error('invalid_settings_request', 400)
    headers = headers or {}
    if not str(headers.get('Authorization', '')).startswith('Bearer '):
        return error('unauthorized', 401)
    original = resolve_runtime(hass, data['device_id'], headers)
    entry = getattr(original, 'entry', None)
    entry_generation = getattr(original, '_receiver_end_generation', 0)

    def paired():
        if (entry is None or hass.data.get('djconnect', {}).get(entry.entry_id) is not original
                or hass.config_entries.async_get_entry(entry.entry_id) is not entry
                or entry.disabled_by is not None
                or getattr(entry.state, 'value', entry.state) != 'loaded'):
            return False
        conf = {**entry.data, **entry.options}
        known = (getattr(original, 'device_status', {}).get('device_id')
                 or getattr(original, 'pairing_device_id', '') or conf.get('device_id'))
        return (conf.get('device_token') == request_token(headers)
                and conf.get('device_id') == known == data['device_id']
                and conf.get('client_type') == data['client_type']
                and headers.get('X-DJConnect-Device-ID', data['device_id']) == data['device_id']
                and getattr(original, '_receiver_end_generation', 0) == entry_generation
                and runtime_matches_device(original, data['device_id'])
                and authorize_runtime_device_request(original, headers, data['device_id'], data['client_type']))

    if not paired():
        return error('unauthorized', 401)
    identity = {key: data[key] for key in IDENTITY_FIELDS}
    runtime, context, failure, status = await _session_profile_context(
        hass, dict(identity), headers=headers, user_id=None, source='profile_settings_v3')
    if failure is not None:
        return failure, status
    if runtime is not original:
        return error('unauthorized', 401)
    if context.profile.profile_type.value in {'guest', 'room', 'party'}:
        return error('owner_settings_not_allowed', 403)
    storage = profile_storage(hass)
    device = storage.household.devices.get(data['device_id'])
    generation = getattr(device, 'binding_generation', '')
    if entry is None or not generation:
        return error('settings_binding_unavailable', 503)
    binding = binding_digest(entry_id=entry.entry_id, device_id=data['device_id'],
                             profile_id=context.profile_id, generation=generation,
                             token=request_token(headers))
    manager = session_runtime_manager(hass)
    options = voice_options(hass, runtime.config)
    policy = VoicePolicy.from_options(options)
    delivery_policy = output_policy(hass, runtime)

    def authority():
        try:
            if validate_ingress is not None:
                validate_ingress()
            _conversation_profile_fence(hass, runtime, identity, headers, context)
            current = storage.household.devices.get(data['device_id'])
            return (paired() and current is not None and current.binding_generation == generation
                    and current.pairing_state.value == 'paired'
                    and hass.data.get('djconnect', {}).get('session_runtime_manager') is manager)
        except Exception:
            return False

    def commit_authority():
        if not authority():
            return False
        if write and (
                ({'voice', 'gender'} & data['patch'].keys()
                 and voice_options(hass, runtime.config)['revision'] != policy.revision)
                or ('announcement_output' in data['patch']
                    and output_policy(hass, runtime).revision != delivery_policy.revision)):
            raise SettingsCommitError('settings_configuration_changed')
        return True

    def validate_selection(settings):
        if {'voice', 'gender'} & data['patch'].keys():
            policy.validate(settings)
        if 'announcement_output' in data['patch']:
            delivery_policy.validate(settings)

    def migration_state(*, activated=False, accepted_contract_version=None):
        state = assessment(hass, storage.household,
                           storage.household.profiles[context.profile_id],
                           activated=activated, accepted_contract_version=accepted_contract_version)
        active = manager.current_active(context.profile_id)
        if active is not None and active.settings_contract_version == 1 and not active.selected_mood:
            state.update(state='choice_required', requires_review=True,
                         complete_selection_fields=sorted(FIELDS), selection_basis='legacy_mood_unknown')
        return state

    try:
        if operation:
            if data['binding'] != binding:
                return error('settings_binding_changed', 409)
            result = await manager.async_dj_settings_operation_result(
                owner_profile_id=context.profile_id, operation_id=data['operation_id'], binding=binding,
                now_ms=int(datetime.now(UTC).timestamp()*1000), authorize=authority)
            _require_authority(authority)
            register_delivery_admission(lambda: _require_authority(authority))
            return {'success': True, 'contract_version': SETTINGS_VERSION, **result,
                    'as_of': datetime.now(UTC).isoformat(), 'cache_policy': 'private,no-store'}, 200
        if write:
            if data['binding'] != binding:
                return error('settings_binding_changed', 409)
            def migration_requires_review():
                return migration_state()['requires_review']
            previous_mood_session = manager.current_active(context.profile_id)
            result = await manager.async_accept_dj_settings(
                owner_profile_id=context.profile_id, operation_id=data['operation_id'], binding=binding,
                patch=data['patch'], expected_defaults_revision=data['expected_defaults_revision'],
                expected_session=data['expected_session'], now_ms=int(datetime.now(UTC).timestamp()*1000),
                authorize=commit_authority, validate_voice=validate_selection,
                migration_requires_review=migration_requires_review)
            snapshot = result['snapshot']
            if not result['replayed']:
                if 'mood' in data['patch']:
                    from .mood_music_steering import schedule
                    feedback = schedule(hass, runtime, manager, context.profile_id,
                        previous_mood_session, identity=identity, headers=headers, authorize=authority)
                    if feedback is not None:
                        result = {**result, 'mood_music_feedback': feedback}
                bus = getattr(hass, 'bus', None)
                if bus is not None:
                    try:
                        bus.async_fire(CHANGE_EVENT, {'owner': hashlib.sha256(context.profile_id.encode()).hexdigest()})
                    except Exception:
                        result = {**result, 'delivery_pending': True}
        else:
            snapshot = await manager.async_read_dj_settings(owner_profile_id=context.profile_id,
                                                            authorize=authority)
            result = {'snapshot': snapshot}
        if not authority():
            return error('unauthorized', 401)
        # Reads and non-voice patches may have waited through a provider change.
        # Project current availability without replacing the retained choice.
        policy = VoicePolicy.from_options(voice_options(hass, runtime.config))
        projected_choices = (snapshot['session'] or {}).get('settings') or snapshot['defaults']
        register_delivery_admission(lambda: _require_authority(authority))
        from .mood_music_steering import feedback_status
        feedback = feedback_status(manager, context.profile_id)
        return {'success': True, **result, **({'mood_music_feedback':feedback} if feedback is not None else {}), 'contract_version': SETTINGS_VERSION, 'binding': binding,
                'scope': 'profile_and_active_session',
                'migration': migration_state(activated=snapshot['activated'],
                                            accepted_contract_version=snapshot['accepted_contract_version']),
                'announcement_output': output_policy(hass, runtime).projection(
                    projected_choices['announcement_output']),
                'allowed_values': allowed_values(policy),
                'writable_fields': sorted(FIELDS), 'voice_revision': policy.revision,
                'voice_availability': policy.selection_state(DJSettings.from_dict(
                    projected_choices)),
                'as_of': datetime.now(UTC).isoformat(), 'cache_policy': 'private,no-store'}, 200
    except SettingsRevisionConflict as exc:
        if not authority():
            return error('unauthorized', 401)
        register_delivery_admission(lambda: _require_authority(authority))
        return error('settings_revision_conflict', 409, current=exc.current)
    except PermissionError:
        return error('unauthorized', 401)
    except (SettingsValidationError, SettingsCommitError) as exc:
        if str(exc) == 'settings_migration_choice_required':
            if not authority():
                return error('unauthorized', 401)
            register_delivery_admission(lambda: _require_authority(authority))
            return error(str(exc), 409, migration=migration_state())
        return error(str(exc), 409)
    except RuntimeError:
        return error('settings_unavailable', 503)


def _require_authority(authority):
    if not authority():
        raise PermissionError('unauthorized')
