"""One deliberate neutral HA voice sample; never a dialogue or published Moment."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import hashlib
import time

TEXT = {
    'en': 'This is a short example of your selected DJ voice.',
    'nl': 'Dit is een kort voorbeeld van je gekozen DJ-stem.',
    'de': 'Dies ist ein kurzes Beispiel deiner gewählten DJ-Stimme.',
    'fr': 'Voici un court exemple de la voix DJ que tu as choisie.',
    'es': 'Este es un breve ejemplo de la voz de DJ que has elegido.',
}
MAX_SECONDS = 120


def capability():
    return {'available': True, 'version': 1, 'operation': 'speech/preview',
            'path': '/api/djconnect/v1/transport/operation', 'method': 'POST',
            'language_families': list(TEXT), 'processor': 'ha_configured',
            'settings_contract_version': 3, 'requires_confirmed_settings': True,
            'caller_text_or_voice_override': False, 'maximum_seconds': MAX_SECONDS,
            'session_required': False, 'history_publication': False,
            'output_authority': 'confirmed_profile_or_active_session',
            'duplicate': 'original_operation_receipt_no_new_audio_or_dispatch',
            'cache_policy': 'private,no-store'}


class _Lease:
    """RAM-only expiry/disposal, bounded by the existing operation and audio owners."""
    def __init__(self, guard, expires_at):
        self.authorize = guard
        self.expires_at = expires_at
        self.deadline = time.monotonic() + max(0, expires_at-time.time())
        self.withdrawn = False
        self.disposals = []
        self.handle = asyncio.get_running_loop().call_later(
            max(0, self.deadline-time.monotonic()), self.dispose)

    def __call__(self):
        if self.withdrawn or time.time() >= self.expires_at or time.monotonic() >= self.deadline:
            raise PermissionError('voice_preview_withdrawn')
        self.authorize()

    def on_withdraw(self, callback):
        self()
        self.disposals.append(callback)
        def remove():
            if callback in self.disposals:
                self.disposals.remove(callback)
        return remove

    def dispose(self):
        self.withdrawn = True
        self.handle.cancel()
        callbacks, self.disposals = self.disposals, []
        self.authorize = lambda: None
        for callback in callbacks:
            callback()


async def async_preview(hass, authority, payload):
    from .announcement_policy import output_policy
    from .domain.profile.dj_settings import DJSettings
    from .hybrid_service import current_operation_identity, guard_transport_effect
    from .persistence.dj_settings import SettingsCommitError
    from .profile_context import profile_storage
    from .profile_settings import VoicePolicy
    from .session_runtime import session_runtime_manager
    from .session_speech import prepare_ha, exact_segments
    from .settings_migration import assessment
    from .speech_processor import voice_options
    from .speech_feedback import notification
    from .transport_delivery import register_delivery_admission

    def failed(reason, status=409, **extra):
        result = {'success': False, 'error': reason, **extra}
        notice = notification(reason, payload.get('language'))
        if notice:
            result['notification'] = notice
        return result, status

    if (type(payload) is not dict
            or set(payload) != {'contract_version', 'language', 'device_id', 'client_type'}
            or type(payload['contract_version']) is not int or payload['contract_version'] != 1
            or type(payload['language']) is not str or payload['language'] not in TEXT):
        return {'success': False, 'error': 'invalid_request'}, 400
    identifier, operation_expiry_ms = current_operation_identity(authority)
    # Safe typed denials need only current paired owner authority. Rich accepted
    # samples additionally register their immutable lease/provider below.
    register_delivery_admission(authority.owner_final_guard)
    manager = session_runtime_manager(hass)
    profile = authority.context.profile_id
    active = manager.current_active(profile)
    # The normal settings reader can migrate old Presence. A preview must not
    # perform that lifecycle mutation or silently choose unconfirmed settings.
    if active is not None and active.selected_presence == 'talkative':
        return failed('settings_migration_choice_required')
    lease = None
    try:
        def owner_current():
            authority.owner_final_guard()
            if (session_runtime_manager(hass) is not manager
                    or manager.current_active(profile) is not active):
                raise PermissionError('voice_preview_withdrawn')
        def read_authority():
            owner_current()
            return True
        snapshot = await manager.async_read_dj_settings(owner_profile_id=profile,
                                                       authorize=read_authority)
        owner_current()
        acceptance = {key: snapshot[key] for key in ('activated', 'accepted_contract_version')}
        storage = profile_storage(hass)
        if (not snapshot['activated'] or assessment(hass, storage.household,
                authority.context.profile, **acceptance)['requires_review']
                or (snapshot['session'] or {}).get('selection_required')):
            return failed('settings_migration_choice_required')
        token = manager.dj_settings_fence_token(profile)
        selected = DJSettings.from_dict((snapshot['session'] or {}).get('settings') or snapshot['defaults'])
        if selected.announcement_output == 'text_only':
            return failed('announcement_text_only')
        policy = VoicePolicy.from_options(voice_options(hass, authority.runtime.config))
        availability = policy.selection_state(selected)
        if not availability['available']:
            reason = availability['reason']
            if reason == 'selected_voice_unavailable':
                reason = policy.reason or 'no_matching_voice'
            return failed(reason)
        original = output_policy(hass, authority.runtime)
        target = {'client_device': 'local', 'ha_speaker': 'ha_speaker', 'both': 'both'}[selected.announcement_output]
        if target == 'ha_speaker' and not original.speaker_available:
            return failed('announcement_speaker_unavailable')
        def guard():
            owner_current()
            if (manager.dj_settings_fence_token(profile) != token
                    or output_policy(hass, authority.runtime).revision != original.revision
                    or assessment(hass, storage.household, storage.household.profiles[profile],
                                  **acceptance)['requires_review']):
                raise PermissionError('voice_preview_withdrawn')
        lease = _Lease(guard, min(time.time()+MAX_SECONDS, operation_expiry_ms/1000))
        lease.processor_basis = 'core_owned_voice_preview_v1'
        lease()
        text = TEXT[payload['language']]
        revision = hashlib.sha256(text.encode()).hexdigest()[:24]
        descriptor = {'schema_version': 1, 'preview_id': identifier, 'text': text,
            'locale': payload['language'], 'source_id': 'voice_preview:'+authority.device,
            'text_revision': revision, 'presentation_revision': revision,
            'segments': exact_segments(text), 'state': 'available', 'manual_allowed': True,
            'settings_contract_version': 3, 'settings_revision': token,
            'expires_at': datetime.fromtimestamp(lease.expires_at, UTC).isoformat(),
            'cache_policy': 'private,no-store'}
        data = {'reference': {'preview_id': identifier}, 'voice_preference': selected.gender.value}
        if selected.voice.kind == 'provider_voice':
            data['voice_id'] = selected.voice.voice_id
        await guard_transport_effect()
        lease()
        prepared = await prepare_ha(hass, authority.runtime, profile, data, descriptor, lease,
            expected_provider=selected.voice.provider_id if selected.voice.kind == 'provider_voice' else None)
        lease()
        if prepared.get('audio_state') != 'ready':
            lease.dispose()
            return failed(prepared['reason'], voice_preview={
                'schema_version': 1, 'preview_id': identifier, 'state': 'unavailable',
                'reason': prepared['reason'], 'locale': payload['language']})
        from .dj_response import get_private_tts_audio
        asset = get_private_tts_audio(hass, prepared['audio_reference']['asset_id'], profile)
        register_delivery_admission(lease)
        register_delivery_admission(asset.admission)
        # This dedicated result never pretends to be a Session contribution.
        for key in ('source_id', 'text_revision', 'presentation_revision', 'segments',
                    'manual_allowed', 'autoplay_eligible', 'mood_prosody'):
            prepared.pop(key, None)
        if target == 'local':
            return {'success': True, 'voice_preview': prepared,
                    'delivery': {'local': 'ready', 'ha_speaker': 'not_requested',
                                 'audible': 'not_proven'}}, 200
        from .speaker_delivery import deliver_prepared
        return await deliver_prepared(hass, authority, prepared, target=target,
            original=original, source_guard=lease, result_key='voice_preview')
    except SettingsCommitError:
        if lease is not None:
            lease.dispose()
        return failed('settings_unavailable', 503)
    except PermissionError:
        if lease is not None:
            lease.dispose()
        return failed('voice_preview_withdrawn')
    except BaseException:
        if lease is not None:
            lease.dispose()
        raise
