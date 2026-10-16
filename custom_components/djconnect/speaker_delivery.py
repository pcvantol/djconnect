"""One exact live Moment replay through existing operation and private byte owners."""
from .announcement_policy import output_policy
from .announcements import configured_announcement_speaker
from .dj_response import grant_speaker_media, get_private_tts_audio, _async_ha_base_url
from .hybrid_service import guard_transport_effect, validate_transport_effect_now
from .session_speech import async_handle_prepare


async def async_play(hass, authority, payload):
    # No arbitrary text, entity, URL or retained/private conversation playback.
    reference = payload.get('reference') if type(payload) is dict else None
    if (type(reference) is not dict or set(reference) != {'session_id', 'moment_id'}
            or type(payload.get('target')) is not str or payload['target'] not in {'ha_speaker', 'both'}
            or payload.get('contract_version') != 3):
        return {'success': False, 'error': 'invalid_request'}, 400
    runtime = authority.runtime
    original = output_policy(hass, runtime)
    if not original.speaker_available:
        return {'success': False, 'error': 'announcement_speaker_unavailable'}, 409
    speaker = configured_announcement_speaker(runtime)
    result, status = await async_handle_prepare(hass, payload, headers=authority.headers,
                                               _speaker_operation=True)
    descriptor = result.get('session_speech', {})
    if status != 200 or descriptor.get('audio_state') != 'ready':
        return result, status
    owner = authority.context.profile_id
    asset_id = descriptor['audio_reference']['asset_id']
    asset = get_private_tts_audio(hass, asset_id, owner)

    def guard():
        authority.validate_now()
        asset.admission()
        if output_policy(hass, runtime).revision != original.revision:
            raise PermissionError('announcement_target_changed')
    guard()
    base_url = await _async_ha_base_url(hass, runtime.config)
    if not base_url:
        return {'success': False, 'error': 'speech_media_url_unavailable'}, 503
    from .session_runtime import session_runtime_manager
    manager = session_runtime_manager(hass)
    # The existing settings/Session owner orders dispatch acceptance and switches.
    async with manager._lock:
        guard()
        await guard_transport_effect()
        guard()
        validate_transport_effect_now()
        grant = grant_speaker_media(hass, asset_id, owner, guard)
        url = f'{base_url.rstrip("/")}/api/djconnect/v1/speech/media/{asset_id}/{grant}'
        try:
            await hass.services.async_call('media_player', 'play_media', {
                'entity_id': speaker, 'media_content_id': url,
                'media_content_type': asset.content_type}, blocking=False)
        except Exception:
            # Delivery may already have happened. The operation journal prevents
            # retries from dispatching again; never report failed as safe-to-retry.
            asset.speaker_grants.pop(grant, None)
            return {'success': False, 'error': 'speaker_delivery_unknown',
                    'delivery': {'ha_speaker': 'unknown', 'audible': 'not_proven'}}, 503
    projected = dict(descriptor)
    if payload['target'] != 'both':
        projected.pop('audio_reference', None)
    return {'success': True, 'session_speech': projected,
            'delivery': {'ha_speaker': 'queued', 'local': 'ready' if payload['target'] == 'both'
                         else 'not_requested', 'audible': 'not_proven'}}, 200
