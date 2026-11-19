"""Closed shared output policy; physical HA targets never become preferences."""
from dataclasses import dataclass
import hashlib
import json

from .domain.profile.dj_settings import ANNOUNCEMENT_OUTPUTS, SettingsValidationError


@dataclass(frozen=True)
class OutputPolicy:
    """An immutable admission snapshot; SQL validation reads no HA state."""
    speaker_available: bool
    reason: str | None
    revision: str

    def validate(self, settings):
        if settings.announcement_output in {'both', 'ha_speaker'} and not self.speaker_available:
            raise SettingsValidationError('announcement_speaker_unavailable')

    def projection(self, selected):
        return {'selected': selected, 'speaker_available': self.speaker_available,
                'speaker_reason': self.reason,
                'outputs': [{'value': value, 'available': self.speaker_available
                            if value in {'both', 'ha_speaker'} else True}
                           for value in sorted(ANNOUNCEMENT_OUTPUTS)],
                'voice_applicability': 'not_applicable_text_only'
                    if selected == 'text_only' else 'applicable',
                'autoplay_scope': 'device_local_default_off'}


def output_policy(hass, runtime):
    """Resolve HA-owned target health on-loop; expose no entity ID or config."""
    from .announcements import configured_announcement_speaker, validate_announcement_speaker
    speaker = configured_announcement_speaker(runtime)
    reason = validate_announcement_speaker(hass, speaker) if speaker else 'announcement_speaker_not_configured'
    available = reason is None
    # Entity changes are authority changes even if both targets are healthy.
    token = hashlib.sha256(json.dumps([speaker, available, reason], separators=(',', ':')).encode()).hexdigest()
    return OutputPolicy(available, reason, token)


@dataclass(frozen=True)
class AnnouncementAdmission:
    """One in-flight view of canonical state, never another preference store."""
    settings: object
    locale: str
    guard: object


async def capture_announcement_admission(hass, runtime):
    """Fence legacy generation/URLs through the same existing settings owner.

    Published installations without this new owner retain their legacy route.
    Once connected, failure to resolve/read authority must never permit TTS.
    """
    domain = hass.data.get('djconnect', {})
    manager = domain.get('session_runtime_manager')
    if manager is None or manager._settings_repository is None:
        return None
    from .profile_context import async_resolve_request_context, profile_storage
    from .domain.profile.dj_settings import DJSettings
    context = await async_resolve_request_context(hass, runtime, {}, request_source='announcement_policy')
    storage = profile_storage(hass)
    device = storage.household.devices.get(context.device_id)
    fallback = storage.household.fallback
    entry = getattr(runtime, 'entry', None)
    receiver_generation = getattr(runtime, '_receiver_end_generation', 0)
    pairing_token = getattr(runtime, 'device_token', None)
    token = None
    migration_acceptance = None

    def migration_current():
        if migration_acceptance is None:
            return True  # The first authorized read supplies this acceptance.
        from .settings_migration import assessment
        return not assessment(hass, storage.household, context.profile,
                              **migration_acceptance)['requires_review']

    def current():
        entries = getattr(hass, 'config_entries', None)
        return (entry is not None and entries is not None
                and entries.async_get_entry(entry.entry_id) is entry
                and entry.disabled_by is None
                and getattr(entry.state, 'value', entry.state) == 'loaded'
                and hass.data.get('djconnect', {}).get(entry.entry_id) is runtime
                and getattr(runtime, '_receiver_end_generation', 0) == receiver_generation
                and getattr(runtime, 'device_token', None) == pairing_token
                and entry.data.get('device_token') == pairing_token
                and hass.data.get('djconnect', {}).get('session_runtime_manager') is manager
                and storage.household.profiles.get(context.profile_id) == context.profile
                and storage.household.devices.get(context.device_id) == device
                and (device is not None or storage.household.fallback == fallback)
                and (token is None or manager.dj_settings_fence_token(context.profile_id) == token)
                and migration_current())

    snapshot = await manager.async_read_dj_settings(owner_profile_id=context.profile_id, authorize=current)
    from .settings_migration import assessment
    if assessment(hass, storage.household, context.profile, activated=snapshot['activated'],
                  accepted_contract_version=snapshot['accepted_contract_version'])['requires_review']:
        raise PermissionError('settings_migration_choice_required')
    migration_acceptance = {key: snapshot[key] for key in ('activated', 'accepted_contract_version')}
    token = manager.dj_settings_fence_token(context.profile_id)
    selected = DJSettings.from_dict((snapshot['session'] or {}).get('settings') or snapshot['defaults'])
    def guard():
        if not current():
            raise PermissionError('announcement_settings_changed')
    guard()
    # This legacy call has no accepted-reference language. Preserve the actual
    # HA pipeline's qualified locale rather than inventing one from UI language.
    from .speech_processor import voice_options
    locale = (voice_options(hass, runtime.config).get('provider_voice') or {}).get('locale', '')
    return AnnouncementAdmission(selected, locale.replace('_', '-').split('-', 1)[0], guard)
