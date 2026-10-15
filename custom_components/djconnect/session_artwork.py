"""Subject-bound Session image admission, never semantic publication or history."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import secrets
import time
from datetime import UTC, datetime

from .discovery_artwork import provider_asset_id
from .forecast_imagery import artist_authority, image_format
from .image_proxy import session_images

URI = re.compile(r'spotify:(track|album|artist):([A-Za-z0-9]{22})\Z')
TTL = 300
MAX_BYTES = 2 * 1024 * 1024
PATH = '/api/djconnect/v1/session/media/image/{session_id}/{asset_id}'


def capability():
    return {'contract_version': 1, 'owner_only': True, 'explicit_prepare': True,
            'max_targets': 8, 'image_requires_device_auth': True,
            'historical_resolution': 'exact_subject_original_source_only'}


def subject_for_fact(fact):
    """Source identity, never presentation text or current playback artwork."""
    if fact is None:
        return None
    if fact.intent == 'artist_story':
        uri = getattr(fact, 'artwork_subject_uri', '')
    elif fact.intent == 'album_story':
        m = re.fullmatch(r'https://open\.spotify\.com/album/([A-Za-z0-9]{22})', fact.source_url)
        uri = 'spotify:album:' + m[1] if m else ''
    else:
        uri = fact.media_identity
    return uri if isinstance(uri, str) and URI.fullmatch(uri) else None


def unavailable(session_id, target, reason='not_prepared'):
    return {'schema_version': 1, 'session_id': session_id, **target,
            'revision': reason, 'artwork': {'state': 'unavailable', 'reason': reason,
                                         'current_display_allowed': False,
                                         'active_flow_display_allowed': False,
                                         'historical_display_allowed': False}}


def _decoded_size(body):
    from PIL import Image

    with Image.open(io.BytesIO(body)) as image:
        width, height = image.size
        if (image.format not in {'JPEG', 'PNG', 'WEBP'} or getattr(image, 'n_frames', 1) != 1
                or not 0 < width <= 4096 or not 0 < height <= 4096 or width * height > 16_000_000):
            raise ValueError('unsafe_image')
        image.verify()
    with Image.open(io.BytesIO(body)) as image:
        image.load()
    return width, height


async def _fetch(hass, backend, uri):
    """Exact existing provider/CDN adapters; no search, redirects or cookies."""
    match = URI.fullmatch(uri)
    kind, identifier = match.groups()
    item = await asyncio.wait_for(backend._request('GET', '/' + kind + 's/' + identifier), 8)
    if not isinstance(item, dict) or item.get('id') != identifier or item.get('uri') != uri or item.get('type') != kind:
        raise ValueError('subject_mismatch')
    source = 'https://open.spotify.com/' + kind + '/' + identifier
    if (item.get('external_urls') or {}).get('spotify') != source:
        raise ValueError('subject_mismatch')
    media = item.get('album') if kind == 'track' else item
    if not isinstance(media, dict):
        raise ValueError('missing_edition')
    album_uri = ''
    if kind == 'track':
        album_uri = media.get('uri', '')
        if (not re.fullmatch(r'spotify:album:[A-Za-z0-9]{22}', str(album_uri))
                or media.get('id') != album_uri.rsplit(':', 1)[-1]):
            raise ValueError('missing_edition')
    images = media.get('images')
    if not isinstance(images, list):
        raise ValueError('missing_image')
    image = next((v for v in images[:3] if isinstance(v, dict) and provider_asset_id(v.get('url'))), None)
    if not image:
        raise ValueError('missing_image')
    from aiohttp import ClientTimeout
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    async with async_get_clientsession(hass).get(image['url'], allow_redirects=False,
                                                timeout=ClientTimeout(total=8)) as response:
        if response.status != 200:
            raise ValueError('source_unavailable')
        mime = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
        body = bytearray()
        async for chunk in response.content.iter_chunked(65536):
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise ValueError('image_too_large')
    body = bytes(body)
    if not image_format(body, mime):
        raise ValueError('unsafe_image')
    width, height = await hass.async_add_executor_job(_decoded_size, body)
    return body, mime, source, album_uri, width, height


async def prepare(hass, runtime, context, *, session_id, target):
    """Explicit bounded owner action; all identity and scope selected server-side."""
    resolved = await resolve_target(hass, runtime, context, session_id, target)
    if resolved is None:
        return unavailable(session_id, target, 'insufficient_identity')
    uri, expected_source, allowed, current, historical = resolved
    if (not isinstance(expected_source, dict) or not all(expected_source.get(k) for k in
            ('backend_id', 'music_account_id', 'provider_entry_id', 'provider_account_id'))):
        return unavailable(session_id, target, 'source_withdrawn')
    source_authority = artist_authority(hass, runtime, owner_profile_id=context.profile_id, expected_source=expected_source)

    def authority():
        from .profile_context import profile_storage
        from .profile_privacy import resolve_profile_privacy_policy

        profile = profile_storage(hass).household.profiles.get(context.profile_id)
        return bool(source_authority() and profile is not None
                    and resolve_profile_privacy_policy(profile, {}).allow_personal_read)

    registry = session_images(hass)
    key = (context.profile_id, session_id, tuple(sorted(target.items())))
    cached = registry.get(key)
    if cached and cached['subject'] == uri and await cached['allowed']():
        return project(cached, current=current, historical=historical)
    if key in registry.inflight:
        return await asyncio.shield(registry.inflight[key])
    if not authority() or not await allowed():
        return unavailable(session_id, target, 'source_withdrawn')
    registry.collect()
    if key in registry.negative:
        return unavailable(session_id, target, 'backoff')
    if len(registry.inflight) >= 8 or len(registry.assets) + len(registry.negative) + len(registry.inflight) >= 64:
        return unavailable(session_id, target, 'capacity')

    async def run():
        from .spotify_backend import SpotifyBackend
        try:
            async with registry.semaphore, asyncio.timeout(20):
                if not authority() or not await allowed():
                    return unavailable(session_id, target, 'source_withdrawn')
                body, mime, source, album, width, height = await _fetch(hass, SpotifyBackend(hass, runtime), uri)
                if not authority() or not await allowed():
                    return unavailable(session_id, target, 'source_withdrawn')
                wall, mono = time.time(), time.monotonic()
                asset_id = secrets.token_urlsafe(24)
                artwork = {'state': 'ready', 'subject': {'provider': 'spotify', 'uri': uri,
                           'type': URI.fullmatch(uri)[1], **({'album_uri': album} if album else {})},
                           'role': 'playback_thumbnail' if target.get('entry_id') and current else
                                   'contextual_artist' if ':artist:' in uri else 'cover',
                           'resolution_basis': 'resolved_now' if historical else 'observed',
                           'source_url': source, 'attribution': {'provider': 'Spotify', 'mark': 'spotify', 'url': source},
                           'usage_basis': 'spotify_temporary_owner_display',
                           'captured_at': datetime.fromtimestamp(wall, UTC).isoformat(),
                           'expires_at': datetime.fromtimestamp(wall + TTL, UTC).isoformat(),
                           'current_display_allowed': current and not historical,
                           'active_flow_display_allowed': not historical,
                           'historical_display_allowed': historical, 'cache_policy': 'no-store',
                           'crop_allowed': False, 'requires_device_auth': True,
                           'width': width, 'height': height,
                           'url': PATH.format(session_id=session_id, asset_id=asset_id)}
                revision = hashlib.sha256(json.dumps(artwork, sort_keys=True).encode()).hexdigest()[:24]
                artwork['media_revision'] = revision
                projection = {'schema_version': 1, 'session_id': session_id, **target,
                              'revision': revision, 'artwork': artwork}
                asset = {'body': body, 'mime': mime, 'deadline': mono + TTL, 'authority': authority,
                         'allowed': allowed, 'asset_id': asset_id, 'subject': uri, 'projection': projection,
                         'historical': historical}
                if not registry.commit(key, asset):
                    return unavailable(session_id, target, 'capacity')
                if not historical:
                    attach_live_projection(hass, context.profile_id, session_id)
                return projection
        except asyncio.CancelledError:
            raise
        except Exception:  # Optional image failure never invalidates semantic text.
            registry.negative[key] = time.monotonic() + 60
            return unavailable(session_id, target, 'source_unavailable')
        finally:
            registry.inflight.pop(key, None)

    task = hass.async_create_task(run())
    registry.inflight[key] = task
    task.add_done_callback(lambda done: registry.inflight.pop(key, None)
                           if registry.inflight.get(key) is done else None)
    return await asyncio.shield(task)


async def resolve_target(hass, runtime, context, session_id, target):
    """Current published contribution or authorized retained entry, never input URI."""
    from .session_runtime import session_runtime_manager

    manager = session_runtime_manager(hass)
    moment_id, entry_id = target.get('moment_id'), target.get('entry_id')
    if bool(moment_id) == bool(entry_id):
        return None
    active = await manager.async_get_active(context.profile_id)
    if moment_id:
        if active is None or active.session_id != session_id:
            return None
        moment = next((m for m in active.broadcast.state.dj_moments if m.moment_id == moment_id), None)
        admission = next((a for a in active.broadcast.native_delivery()['admissions'] if a['moment_id'] == moment_id), {})
        fact = getattr(moment, 'source_fact', None)
        uri = subject_for_fact(fact)
        if not uri or not (admission.get('current_display_allowed') or admission.get('active_flow_display_allowed')):
            return None
        async def allowed():
            current = await manager.async_get_active(context.profile_id)
            if current is not active:
                return False
            a = next((a for a in current.broadcast.native_delivery()['admissions'] if a['moment_id'] == moment_id), {})
            return bool(a.get('current_display_allowed') or a.get('active_flow_display_allowed'))
        return uri, manager._history_source_contexts.get(session_id, {}), allowed, bool(admission.get('current_display_allowed')), False
    from .session_conversation import query_service

    query = query_service(hass)
    opened = await query.async_open_entry(context.profile_id, session_id, entry_id)
    row = await query._repository.async_entry_record(context.profile_id, session_id, entry_id)
    if not row:
        return None
    body = json.loads(row['body'])
    if row['kind'] == 'playback_observed':
        match = re.fullmatch(r'https://open\.spotify\.com/track/([A-Za-z0-9]{22})', str(body.get('source_url', '')))
        uri = 'spotify:track:' + match[1] if match else None
        source = body.get('source_context', {})
    elif row['kind'] == 'dj_moment':
        ref = body.get('session_media_reference', {})
        uri = ref.get('subject_uri')
        source = ref.get('source_context', {})
    else:
        return None
    if not isinstance(uri, str) or not URI.fullmatch(uri) or not source:
        return None
    historical = opened['read_only']
    async def allowed():
        try:
            opened_now = await query.async_open_entry(context.profile_id, session_id, entry_id)
            return bool(opened_now and opened_now['read_only'] == historical)
        except (PermissionError, ValueError):
            return False
    historical = opened['read_only']
    is_current = bool(not historical and active is not None and active.session_id == session_id
                      and body.get('item_id') == active.broadcast.state.playback.item_id)
    return uri, source, allowed, is_current, historical


async def image(hass, context, session_id, asset_id):
    registry = session_images(hass)
    registry.collect()
    for key, value in list(registry.assets.items()):
        if key[:2] == (context.profile_id, session_id) and value['asset_id'] == asset_id:
            if await value['allowed']() and value['authority']():
                return value['body'], value['mime']
            registry.assets.pop(key, None)
    return None


def project(asset, *, current, historical):
    from copy import deepcopy

    value = deepcopy(asset['projection'])
    artwork = value['artwork']
    artwork['current_display_allowed'] = bool(current and not historical)
    artwork['active_flow_display_allowed'] = not historical
    artwork['historical_display_allowed'] = historical
    value['revision'] = hashlib.sha256(json.dumps(artwork, sort_keys=True).encode()).hexdigest()[:24]
    return value


def attach_live_projection(hass, owner, session_id):
    from .session_runtime import session_runtime_manager, BroadcastEventType

    manager = session_runtime_manager(hass)
    active = manager._active_by_profile.get(owner)
    if active is None or active.session_id != session_id:
        return
    registry = session_images(hass)

    def projected():
        if manager._active_by_profile.get(owner) is not active:
            return []
        admissions = {a['moment_id']: a for a in active.broadcast.native_delivery()['admissions']}
        result = []
        registry.collect()
        for key, asset in list(registry.assets.items()):
            if key[:2] != (owner, session_id):
                continue
            target = dict(key[2])
            if 'moment_id' not in target:
                continue
            a = admissions.get(target['moment_id'], {})
            if not (a.get('current_display_allowed') or a.get('active_flow_display_allowed')):
                continue
            result.append(project(asset, current=a.get('current_display_allowed'), historical=False))
        return result

    active.broadcast.media_projector = projected
    active.broadcast._publish(BroadcastEventType.SESSION_FLOW_UPDATED,
                              {'session_flow': active.broadcast.state.session_flow.as_dict()})


async def handle_prepare(hass, data, *, headers=None, user_id=None):
    from .api_handlers import _session_profile_context, _error_payload

    if (not isinstance(data, dict) or type(data.get('contract_version')) is not int
            or data['contract_version'] != 1 or not isinstance(data.get('session_id'), str)
            or not isinstance(data.get('targets'), list) or not 1 <= len(data['targets']) <= 8):
        return _error_payload('invalid_request'), 400
    targets = data['targets']
    if any(not isinstance(t, dict) or len(t) != 1 or not set(t).issubset({'moment_id', 'entry_id'})
           or any(not isinstance(v, str) or not 0 < len(v) <= 128 for v in t.values()) for t in targets):
        return _error_payload('invalid_request'), 400
    runtime, context, error, status = await _session_profile_context(
        hass, dict(data), headers=headers, user_id=user_id, source='session_media_prepare')
    if error is not None:
        return error, status
    if not context.privacy_policy.allow_personal_read:
        return _error_payload('media_not_allowed'), 403
    async def one(target):
        try:
            return await prepare(hass, runtime, context, session_id=data['session_id'], target=target)
        except (ValueError, PermissionError):
            return unavailable(data['session_id'], target, 'target_unavailable')
    projections = await asyncio.gather(*(one(t) for t in targets))
    _, current, error, status = await _session_profile_context(
        hass, dict(data), headers=headers, user_id=user_id, source='session_media_complete')
    if error is not None:
        return error, status
    if current.profile_id != context.profile_id or not current.privacy_policy.allow_personal_read:
        return _error_payload('media_not_allowed'), 403
    return {'success': True, 'contract_version': 1, 'session_media': projections}, 200


def project_history_media(hass, owner, row, entry):
    """Pure already-authorized row projection; no IO, renewal or provider work."""
    registry = session_images(hass)
    key = (owner, row['session_id'], (('entry_id', row['entry_id']),))
    asset = registry.get(key)
    if asset:
        if not asset['historical']:
            from .session_runtime import session_runtime_manager

            active = session_runtime_manager(hass)._active_by_profile.get(owner)
            if active is None or active.session_id != row['session_id']:
                return entry
        entry['session_media'] = project(asset, current=False, historical=asset['historical'])
    return entry


async def prepare_visible(hass, runtime, owner, session_id):
    """Reuse existing observation enrichment work, never create another scheduler."""
    from types import SimpleNamespace
    from .session_runtime import session_runtime_manager
    from .profile_context import profile_storage
    from .profile_privacy import resolve_profile_privacy_policy

    profile = profile_storage(hass).resolver().resolve_bound_device(
        str(({**runtime.entry.data, **runtime.entry.options}).get('device_id') or ''))
    if profile.profile_id != owner or not resolve_profile_privacy_policy(profile, {}).allow_personal_read:
        return
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(owner)
    if active is None or active.session_id != session_id:
        return
    admitted = active.broadcast.native_delivery()
    moment_ids = [a['moment_id'] for a in admitted['admissions']
                  if a['current_display_allowed'] or a['active_flow_display_allowed']][-4:]
    context = SimpleNamespace(profile_id=owner)
    for identifier in moment_ids:
        await prepare(hass, runtime, context, session_id=session_id, target={'moment_id': identifier})
    if manager._historical_projections is not None:
        entry_id = await manager._historical_projections.async_current_playback_entry(
            owner, session_id, active.broadcast.state.playback.item_id)
        if entry_id:
            await prepare(hass, runtime, context, session_id=session_id, target={'entry_id': entry_id})
