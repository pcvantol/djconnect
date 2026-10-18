"""Exact live/retained DJMoment replay through existing operation and byte owners."""
from contextvars import ContextVar
import hashlib
from uuid import UUID
from datetime import datetime

from .announcement_policy import output_policy
from .announcements import configured_announcement_speaker
from .dj_response import grant_speaker_media, get_private_tts_audio, _async_ha_base_url
from .hybrid_service import guard_transport_effect, validate_transport_effect_now
from .session_speech import async_handle_prepare

_automatic_publication = ContextVar('djconnect_automatic_speech_publication', default=None)


def connect_automatic(hass, runtime, session, identity, headers):
    """Attach to this Session's publication owner, never replay a snapshot/join."""
    from .session_runtime import session_runtime_manager
    manager = session_runtime_manager(hass)
    identity = {key:identity.get(key) for key in ('device_id', 'client_type')}
    # Preserve HTTP case-insensitivity while retaining only owner-auth headers.
    headers = {name:value for name in ('Authorization', 'X-DJConnect-Device-ID')
               if (value := headers.get(name)) is not None}

    def publication(moment):
        current = manager.current_active(session.owner_profile_id)
        if (current is None or current.session_id != session.session_id
                or current.selected_announcement_output not in {'ha_speaker', 'both'}):
            return
        captured = manager.dj_settings_fence_token(session.owner_profile_id)
        target = output_policy(hass, runtime)
        if not target.speaker_available:
            return
        reference = {'session_id': session.session_id, 'moment_id': moment.moment_id}
        def admission():
            live = manager.current_active(session.owner_profile_id)
            if (live is None or live.session_id != session.session_id
                    or manager.dj_settings_fence_token(session.owner_profile_id) != captured
                    or output_policy(hass, runtime).revision != target.revision):
                raise PermissionError('speech_publication_changed')
        async def deliver():
            from .hybrid_service import PairedAuthority, operations
            marker = _automatic_publication.set((reference, admission))
            try:
                admission()
                authority = await PairedAuthority.resolve(hass, identity, headers)
                admission()
                owner = operations(hass)
                created = int(datetime.fromisoformat(moment.created_at).timestamp()*1000)
                # One UUIDv7 per original publication, independent of client reads.
                suffix = int.from_bytes(hashlib.sha256(
                    (session.session_id + '/' + moment.moment_id).encode()).digest()[:8], 'big') & ((1 << 62)-1)
                identifier = str(UUID(int=(created << 80) | (7 << 76) | (2 << 62) | suffix))
                await owner.execute(authority, {'contract_version':1, 'operation_id':identifier,
                    'operation_epoch':owner.journal.epoch, 'operation':'session/speech/play',
                    'payload': {'contract_version':3, 'processor':'ha_configured', 'intent':'automatic',
                                'target':'ha_speaker', 'reference':reference}}, transport='http')
            except Exception:
                # No retry/catch-up queue and no claim of audible playback.
                pass
            finally:
                _automatic_publication.reset(marker)
        hass.async_create_task(deliver(), 'DJConnect accepted Moment speaker delivery')
    session.broadcast.owner_moment_speech_delivery = publication


async def async_play(hass, authority, payload):
    # No arbitrary text, entity, URL or retained/private conversation playback.
    # Historical DJMoments use an exact owner entry, and only a deliberate replay.
    reference = payload.get('reference') if type(payload) is dict else None
    if (type(reference) is not dict or set(reference) not in (
            {'session_id', 'moment_id'}, {'session_id', 'entry_id'})
            or ('entry_id' in reference and payload.get('intent') != 'manual')
            or type(payload.get('target')) is not str or payload['target'] not in {'ha_speaker', 'both'}
            or payload.get('processor') != 'ha_configured'
            or payload.get('contract_version') != 3):
        return {'success': False, 'error': 'invalid_request'}, 400
    automatic = _automatic_publication.get()
    if payload.get('intent') == 'automatic':
        if automatic is None or automatic[0] != reference:
            return {'success': False, 'error': 'automatic_speech_requires_publication'}, 409
        automatic[1]()
    runtime = authority.runtime
    original = output_policy(hass, runtime)
    if not original.speaker_available and payload['target'] != 'both':
        return {'success': False, 'error': 'announcement_speaker_unavailable'}, 409
    result, status = await async_handle_prepare(hass, payload, headers=authority.headers,
                                               _speaker_operation=True)
    descriptor = result.get('session_speech', {})
    if status != 200 or descriptor.get('audio_state') != 'ready':
        return result, status
    def guard():
        if payload.get('intent') == 'automatic':
            automatic[1]()
        authority.validate_now()
        if output_policy(hass, runtime).revision != original.revision:
            raise PermissionError('announcement_target_changed')
    return await deliver_prepared(hass, authority, descriptor, target=payload['target'],
                                  original=original, source_guard=guard)


async def deliver_prepared(hass, authority, descriptor, *, target, original,
                           source_guard, result_key='session_speech'):
    """One existing bounded media owner for Moment replay and literal previews."""
    runtime = authority.runtime
    owner = authority.context.profile_id
    speaker = configured_announcement_speaker(runtime)
    asset_id = descriptor['audio_reference']['asset_id']
    asset = get_private_tts_audio(hass, asset_id, owner)
    def guard():
        source_guard()
        asset.admission()
        if output_policy(hass, runtime).revision != original.revision:
            raise PermissionError('announcement_target_changed')
    guard()
    if not original.speaker_available:
        return {'success': True, result_key: descriptor,
                'delivery': {'ha_speaker':'unavailable', 'speaker_reason':original.reason,
                             'local':'ready', 'audible':'not_proven'}}, 200
    base_url = await _async_ha_base_url(hass, runtime.config)
    if not base_url:
        guard()
        if target == 'both':
            return {'success': True, result_key: descriptor,
                    'delivery': {'ha_speaker': 'unavailable',
                                 'speaker_reason': 'speech_media_url_unavailable',
                                 'local': 'ready', 'audible': 'not_proven'}}, 200
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
            failed = {'success': False, 'error': 'speaker_delivery_unknown',
                    'delivery': {'ha_speaker': 'unknown', 'local':'ready' if target=='both'
                                 else 'not_requested', 'audible': 'not_proven'}}
            if target == 'both':
                failed[result_key] = descriptor
            return failed, 503
    projected = dict(descriptor)
    if target != 'both':
        projected.pop('audio_reference', None)
    return {'success': True, result_key: projected,
            'delivery': {'ha_speaker': 'queued', 'local': 'ready' if target == 'both'
                         else 'not_requested', 'audible': 'not_proven'}}, 200
