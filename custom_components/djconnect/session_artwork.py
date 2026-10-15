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
PREPARE_TIMEOUT = 20
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
    state = {'loading': 'loading', 'missing_image': 'missing', 'expired': 'expired',
             'source_withdrawn': 'withdrawn'}.get(reason, 'unavailable')
    return {'schema_version': 1, 'session_id': session_id, **target,
            'revision': reason, 'artwork': {'state': state, 'reason': reason,
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


async def _fetch(hass, backend, uri, *, guard, expected_album_uri=""):
    """Exact existing provider/CDN adapters; no search, redirects or cookies."""
    match = URI.fullmatch(uri)
    kind, identifier = match.groups()
    item = await asyncio.wait_for(backend._request('GET', '/' + kind + 's/' + identifier), 8)
    await guard()
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
        if expected_album_uri and album_uri != expected_album_uri:
            raise ValueError('edition_mismatch')
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
        await guard()
        if response.status != 200:
            raise ValueError('source_unavailable')
        mime = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
        body = bytearray()
        async for chunk in response.content.iter_chunked(65536):
            await guard()
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise ValueError('image_too_large')
    body = bytes(body)
    if not image_format(body, mime):
        raise ValueError('unsafe_image')
    width, height = await session_images(hass).decode(_decoded_size, body)
    await guard()
    name = item.get('name')
    if not isinstance(name, str) or not 0 < len(name) <= 320 or any(ord(c) < 32 for c in name):
        raise ValueError('missing_subject_label')
    return body, mime, source, album_uri, width, height, name


async def prepare(hass, runtime, context, *, session_id, target):
    """Explicit bounded owner action; all identity and scope selected server-side."""
    complete_deadline = asyncio.get_running_loop().time() + PREPARE_TIMEOUT
    try:
        async with asyncio.timeout_at(complete_deadline):
            return await _prepare(hass, runtime, context, session_id=session_id,
                                  target=target, complete_deadline=complete_deadline)
    except TimeoutError:
        return unavailable(session_id, target, 'source_unavailable')


async def _prepare(hass, runtime, context, *, session_id, target, complete_deadline):
    from .persistence.service import PersistenceError

    try:
        async with asyncio.timeout_at(complete_deadline):
            resolved = await resolve_target(hass, runtime, context, session_id, target)
    except (ValueError, PermissionError, PersistenceError, TimeoutError):
        return unavailable(session_id, target, 'target_unavailable')
    if resolved is None:
        return unavailable(session_id, target, 'insufficient_identity')
    uri, expected_source, allowed, current, historical, expected_album, role = resolved
    if (not isinstance(expected_source, dict) or not all(expected_source.get(k) for k in
            ('backend_id', 'music_account_id', 'provider_entry_id', 'provider_account_id'))):
        return unavailable(session_id, target, 'source_withdrawn')
    source_authority = artist_authority(hass, runtime, owner_profile_id=context.profile_id, expected_source=expected_source)

    lifetime_valid = [True]

    def invalidate():
        lifetime_valid[0] = False

    def authority():
        from .profile_context import profile_storage
        from .profile_privacy import resolve_profile_privacy_policy

        profile = profile_storage(hass).household.profiles.get(context.profile_id)
        return bool(lifetime_valid[0] and source_authority() and profile is not None
                    and resolve_profile_privacy_policy(profile, {}).allow_personal_read)

    async def fresh_scope():
        result = await resolve_target(hass, runtime, context, session_id, target)
        if (result is None or result[0] != uri or result[1] != expected_source
                or result[4] != historical or result[5] != expected_album):
            return None
        return result[3]

    async def guard():
        if not authority() or not await allowed() or not authority():
            raise PermissionError('source_withdrawn')

    registry = session_images(hass)
    key = (context.profile_id, session_id, tuple(sorted(target.items())))
    cached = registry.get(key)
    if cached and cached['subject'] == uri and await cached['allowed']():
        fresh_current = await fresh_scope()
        if fresh_current is not None and registry.get(key) is cached and authority():
            return project(cached, current=fresh_current, historical=historical)
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
            async with asyncio.timeout_at(complete_deadline), registry.semaphore:
                if not authority() or not await allowed():
                    return unavailable(session_id, target, 'source_withdrawn')
                body, mime, source, album, width, height, name = await _fetch(
                    hass, SpotifyBackend(hass, runtime), uri, guard=guard, expected_album_uri=expected_album)
                fresh_current = await fresh_scope()
                if fresh_current is None or not authority():
                    return unavailable(session_id, target, 'source_withdrawn')
                wall, mono = time.time(), time.monotonic()
                asset_id = secrets.token_urlsafe(24)
                artwork = {'state': 'ready', 'subject': {'provider': 'spotify', 'uri': uri,
                           'type': URI.fullmatch(uri)[1], **({'album_uri': album} if album else {})},
                           'role': role, 'resolution_basis': 'resolved_now',
                           'edition_basis': edition_basis(uri, expected_album),
                           'source_url': source, 'attribution': {'provider': 'Spotify', 'mark': 'spotify', 'url': source},
                           'usage_basis': 'spotify_temporary_owner_display',
                           'captured_at': datetime.fromtimestamp(wall, UTC).isoformat(),
                           'expires_at': datetime.fromtimestamp(wall + TTL, UTC).isoformat(),
                           'current_display_allowed': fresh_current and not historical,
                           'active_flow_display_allowed': not historical,
                           'historical_display_allowed': historical, 'cache_policy': 'no-store',
                           'crop_allowed': False, 'requires_device_auth': True,
                           'width': width, 'height': height, 'alt_text': alt_text(name, ':artist:' in uri),
                           'url': PATH.format(session_id=session_id, asset_id=asset_id)}
                revision = projection_revision(artwork)
                artwork['media_revision'] = revision
                projection = {'schema_version': 1, 'session_id': session_id, **target,
                              'revision': revision, 'artwork': artwork}
                asset = {'body': body, 'mime': mime, 'deadline': mono + TTL, 'authority': authority,
                         'allowed': allowed, 'asset_id': asset_id, 'subject': uri, 'projection': projection,
                         'historical': historical, 'expected_source': dict(expected_source)}
                if not registry.commit(key, asset):
                    return unavailable(session_id, target, 'capacity')
                if not historical:
                    attach_live_projection(hass, context.profile_id, session_id)
                return projection
        except asyncio.CancelledError:
            raise
        except PermissionError:
            registry.record_state(key, 'source_withdrawn')
            return unavailable(session_id, target, 'source_withdrawn')
        except ValueError as exc:
            known = {'missing_image', 'missing_edition', 'edition_mismatch', 'subject_mismatch',
                     'unsafe_image', 'image_too_large', 'source_unavailable', 'missing_subject_label'}
            reason = str(exc) if str(exc) in known else 'source_unavailable'
            registry.negative[key] = time.monotonic()+60
            registry.record_state(key, reason)
            return unavailable(session_id, target, reason)
        except Exception:  # Optional image failure never invalidates semantic text.
            registry.negative[key] = time.monotonic() + 60
            registry.record_state(key, 'source_unavailable')
            return unavailable(session_id, target, 'source_unavailable')
        finally:
            registry.inflight.pop(key, None)
            registry.work_guards.pop(key, None)

    registry.work_guards[key] = (authority, invalidate)
    task = hass.async_create_task(run())
    registry.inflight[key] = task
    if not historical:
        attach_live_projection(hass, context.profile_id, session_id)
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
            if current is None or current.broadcast is not active.broadcast:
                return False
            a = next((a for a in current.broadcast.native_delivery()['admissions'] if a['moment_id'] == moment_id), {})
            return bool(a.get('current_display_allowed') or a.get('active_flow_display_allowed'))
        return (uri, manager._history_source_contexts.get(session_id, {}), allowed,
                bool(admission.get('current_display_allowed')), False,
                getattr(fact, 'artwork_album_uri', '') if ':track:' in uri else '',
                'contextual_artist' if ':artist:' in uri else 'cover')
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
        album = body.get('album_uri', '')
        role = 'playback_thumbnail'
    elif row['kind'] == 'dj_moment':
        ref = body.get('session_media_reference', {})
        uri = ref.get('subject_uri')
        source = ref.get('source_context', {})
        album = ref.get('album_uri', '')
        role = 'contextual_artist' if ':artist:' in str(uri) else 'cover'
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
    is_current = bool(not historical and active is not None and active.session_id == session_id
                      and body.get('item_id') == active.broadcast.state.playback.item_id)
    if album and not re.fullmatch(r'spotify:album:[A-Za-z0-9]{22}', str(album)):
        return None
    return uri, source, allowed, is_current, historical, album if ':track:' in uri else '', role


async def image(hass, context, session_id, asset_id, *, runtime):
    registry = hass.data.get('djconnect', {}).get('session_images')
    if registry is None:
        return None
    registry.collect()
    for key, value in list(registry.assets.items()):
        if key[:2] == (context.profile_id, session_id) and value['asset_id'] == asset_id:
            requester = artist_authority(hass, runtime, owner_profile_id=context.profile_id,
                                         expected_source=value['expected_source'])
            if not value['authority']() or not requester():
                return None
            try:
                allowed = await value['allowed']()
            except Exception:  # Closed/deleted history is unavailable media.
                allowed = False
            if allowed and registry.get(key) is value and value['authority']() and requester():
                return value['body'], value['mime']
            registry.evict(key, 'source_withdrawn')
    return None


def edition_basis(uri, original_album):
    """An album subject itself binds its edition; artist imagery has no edition."""
    if ':artist:' in uri:
        return 'not_applicable'
    return 'original_bound' if original_album or ':album:' in uri else 'provider_resolved_now'


def projection_revision(artwork):
    """One equality hash for initial response and later unchanged projections."""
    value = {key: item for key, item in artwork.items() if key != 'media_revision'}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:24]


def project(asset, *, current, historical):
    from copy import deepcopy

    value = deepcopy(asset['projection'])
    artwork = value['artwork']
    artwork['current_display_allowed'] = bool(current and not historical)
    artwork['active_flow_display_allowed'] = not historical
    artwork['historical_display_allowed'] = historical
    value['revision'] = projection_revision(artwork)
    return value


def attach_live_projection(hass, owner, session_id):
    from .session_runtime import session_runtime_manager, BroadcastEventType

    manager = session_runtime_manager(hass)
    active = manager._active_by_profile.get(owner)
    if active is None or active.session_id != session_id:
        return
    registry = session_images(hass)

    def projected():
        current = manager._active_by_profile.get(owner)
        if (current is None or current.broadcast is not active.broadcast
                or current.broadcast.state.runtime_state.value != 'active'):
            return []
        admissions = {a['moment_id']: a for a in active.broadcast.native_delivery()['admissions']}
        result = []
        registry.collect()
        for key in set(registry.assets) | set(registry.states) | set(registry.inflight):
            if key[:2] != (owner, session_id):
                continue
            target = dict(key[2])
            a = admissions.get(target.get('moment_id'), {})
            if 'moment_id' in target and not (a.get('current_display_allowed') or a.get('active_flow_display_allowed')):
                continue
            asset = registry.assets.get(key)
            if asset:
                if not asset['historical']:
                    result.append(project(asset, current=a.get('current_display_allowed', False), historical=False))
            else:
                reason = 'loading' if key in registry.inflight else registry.states.get(key, (0,'not_prepared'))[1]
                result.append(unavailable(session_id, target, reason))
        return sorted(result, key=lambda item: str(item.get('moment_id') or item.get('entry_id')))

    active.broadcast.media_projector = projected
    active.broadcast.media_cleanup = lambda: registry.end_session(owner, session_id)
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
    if row['kind'] not in {'playback_observed', 'dj_moment'}:
        return entry
    registry = hass.data.get('djconnect', {}).get('session_images')
    key = (owner, row['session_id'], (('entry_id', row['entry_id']),))
    asset = registry.get(key) if registry else None
    if asset:
        if not asset['historical']:
            from .session_runtime import session_runtime_manager

            active = session_runtime_manager(hass)._active_by_profile.get(owner)
            if active is None or active.session_id != row['session_id']:
                entry['session_media'] = unavailable(row['session_id'], {'entry_id':row['entry_id']}, 'source_withdrawn')
                return entry
        entry['session_media'] = project(asset, current=False, historical=asset['historical'])
    else:
        reason = ('loading' if registry and key in registry.inflight else
                  registry.states.get(key, (0,'not_prepared'))[1] if registry else 'not_prepared')
        entry['session_media'] = unavailable(row['session_id'], {'entry_id':row['entry_id']}, reason)
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


def alt_text(name, artist):
    labels = ({'en': 'Artist image for', 'nl': 'Artiestbeeld van', 'de': 'Künstlerbild von',
               'fr': 'Image de l’artiste', 'es': 'Imagen del artista'}
              if artist else {'en': 'Artwork for', 'nl': 'Hoes van', 'de': 'Cover von',
                              'fr': 'Pochette de', 'es': 'Portada de'})
    return {lang: text + ' ' + name for lang, text in labels.items()}
