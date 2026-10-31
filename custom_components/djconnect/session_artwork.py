"""Subject-bound Session image admission, never semantic publication or history."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import secrets
import time
from dataclasses import dataclass
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
            'historical_resolution': 'exact_subject_original_source_only',
            'supported_contract_versions':[1,2],
            'artist_image_sources_v2':['spotify','wikimedia_commons'],
            'captured_reply_subjects':True}


def subject_for_fact(fact, *, contract_version=1):
    """Source identity, never presentation text or current playback artwork."""
    if fact is None:
        return None
    from .session_facts import ProducerRecommendationFact, ArtistImageIdentity
    if contract_version==2 and getattr(fact,'key','') in {'recording_credits','work_composers'}:
        identity=getattr(fact,'artwork_artist_identity',None)
        return identity.spotify_uri if type(identity) is ArtistImageIdentity and identity.eligible() else None
    if isinstance(fact, ProducerRecommendationFact):
        uri = fact.recommended_media_identity
    elif fact.intent == 'artist_story':
        uri = getattr(fact, 'artwork_subject_uri', '')
    elif getattr(fact, 'key', '') == 'genre_context':
        m = re.fullmatch(r'https://open\.spotify\.com/artist/([A-Za-z0-9]{22})', fact.source_url)
        uri = 'spotify:artist:' + m[1] if m else ''
    elif fact.intent == 'album_story' or getattr(fact, 'key', '') == 'album_continuity':
        m = re.fullmatch(r'https://open\.spotify\.com/album/([A-Za-z0-9]{22})', fact.source_url)
        uri = 'spotify:album:' + m[1] if m else ''
    else:
        uri = fact.media_identity
    return uri if isinstance(uri, str) and URI.fullmatch(uri) else None



class ArtistTarget(tuple):
    """Existing target tuple plus private, qualified performer image identity."""
    def __new__(cls, values, identity):
        value=super().__new__(cls,values)
        value.artist_identity=identity
        return value


def target_key(owner,session_id,target,contract_version=1):
    scope=tuple(sorted(target.items()))
    if contract_version==2:
        scope=(*scope,('media_contract_version','2'))
    return owner,session_id,scope


async def _resolve(hass,runtime,context,session_id,target,version):
    if version==2:
        return await resolve_target(hass,runtime,context,session_id,target,contract_version=2)
    return await resolve_target(hass,runtime,context,session_id,target)


def unavailable(session_id, target, reason='not_prepared', *, contract_version=1):
    state = {'loading': 'loading', 'missing_image': 'missing', 'expired': 'expired',
             'source_withdrawn': 'withdrawn'}.get(reason, 'unavailable')
    return {'schema_version': contract_version, 'session_id': session_id, **target,
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


@dataclass(frozen=True, repr=False)
class _PreparedBytes:
    body: bytes
    mime: str
    width: int
    height: int
    sha256: str


@dataclass(frozen=True, repr=False)
class _FetchedImage:
    values: tuple
    validated_bytes: object

    def __iter__(self):
        return iter(self.values)


def _decode_prepared(body):
    """The existing bounded executor admission, not an on-read decoder."""
    from .direct_rich_frame import complete_image
    width, height = _decoded_size(body)
    mime = "image/png" if body.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg"
    witness = (_PreparedBytes(body, mime, width, height, hashlib.sha256(body).hexdigest())
        if len(body) <= 256000 and complete_image(body, mime) else None)
    return (width, height), witness


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
    dimensions, witness = await session_images(hass).decode(_decode_prepared, body)
    width, height = dimensions
    await guard()
    name = item.get('name')
    if not isinstance(name, str) or not 0 < len(name) <= 320 or any(ord(c) < 32 for c in name):
        raise ValueError('missing_subject_label')
    return _FetchedImage((body, mime, source, album_uri, width, height, name), witness)


async def prepare(hass, runtime, context, *, session_id, target, contract_version=1):
    """Explicit bounded owner action; all identity and scope selected server-side."""
    complete_deadline = asyncio.get_running_loop().time() + PREPARE_TIMEOUT
    try:
        async with asyncio.timeout_at(complete_deadline):
            return await _prepare(hass, runtime, context, session_id=session_id,
                                  target=target, complete_deadline=complete_deadline,contract_version=contract_version)
    except TimeoutError:
        return unavailable(session_id, target, 'source_unavailable',contract_version=contract_version)


async def _prepare(hass, runtime, context, *, session_id, target, complete_deadline,contract_version=1):
    from .persistence.service import PersistenceError

    try:
        async with asyncio.timeout_at(complete_deadline):
            resolved = await _resolve(hass, runtime, context, session_id, target,contract_version)
    except (ValueError, PermissionError, PersistenceError, TimeoutError):
        return unavailable(session_id, target, 'target_unavailable',contract_version=contract_version)
    if resolved is None:
        return unavailable(session_id, target, 'insufficient_identity',contract_version=contract_version)
    uri, expected_source, allowed, current, historical, expected_album, role, delivery_scope = resolved
    identity=getattr(resolved,'artist_identity',None)
    if (not isinstance(expected_source, dict) or not all(expected_source.get(k) for k in
            ('backend_id', 'music_account_id', 'provider_entry_id', 'provider_account_id'))):
        return unavailable(session_id, target, 'source_withdrawn',contract_version=contract_version)
    source_authority = artist_authority(hass, runtime, owner_profile_id=context.profile_id, expected_source=expected_source)

    lifetime_valid = [True]

    def invalidate():
        lifetime_valid[0] = False
    invalidate.delivery_scope = delivery_scope
    invalidate.provider_entry_id = expected_source['provider_entry_id']

    def authority():
        from .profile_context import profile_storage
        from .profile_privacy import resolve_profile_privacy_policy

        profile = profile_storage(hass).household.profiles.get(context.profile_id)
        return bool(lifetime_valid[0] and not registry.history_blocked(key, expected_source, delivery_scope)
                    and source_authority() and profile is not None
                    and resolve_profile_privacy_policy(profile, {}).allow_personal_read)

    async def fresh_scope():
        result = await _resolve(hass, runtime, context, session_id, target,contract_version)
        if (result is None or result[0] != uri or result[1] != expected_source
                or result[4] != historical or result[5] != expected_album
                or getattr(result,'artist_identity',None)!=identity):
            return None
        return result[3]

    async def guard():
        if not authority() or not await allowed() or not authority():
            raise PermissionError('source_withdrawn')

    registry = session_images(hass)
    key = target_key(context.profile_id,session_id,target,contract_version)
    cached = registry.get(key)
    if cached and cached['subject'] == uri and await cached['allowed']():
        fresh_current = await fresh_scope()
        if fresh_current is not None and registry.get(key) is cached and authority():
            return project(cached, current=fresh_current, historical=historical)
    if key in registry.inflight:
        return await asyncio.shield(registry.inflight[key])
    if not authority() or not await allowed():
        return unavailable(session_id, target, 'source_withdrawn',contract_version=contract_version)
    registry.collect()
    if key in registry.negative:
        return unavailable(session_id, target, 'backoff',contract_version=contract_version)
    if len(registry.inflight) >= 8 or len(registry.assets) + len(registry.negative) + len(registry.inflight) >= 64:
        return unavailable(session_id, target, 'capacity',contract_version=contract_version)

    async def run():
        from .spotify_backend import SpotifyBackend
        try:
            async with asyncio.timeout_at(complete_deadline), registry.semaphore:
                if not authority() or not await allowed():
                    return unavailable(session_id, target, 'source_withdrawn',contract_version=contract_version)
                attribution=None
                validated_bytes = None
                try:
                    fetched = await _fetch(
                        hass, SpotifyBackend(hass, runtime), uri, guard=guard, expected_album_uri=expected_album)
                    body, mime, source, album, width, height, name = fetched
                    if type(fetched) is _FetchedImage:
                        validated_bytes = fetched.validated_bytes
                except ValueError as exc:
                    if contract_version!=2 or str(exc)!='missing_image' or identity is None:
                        raise
                    from . import artist_photo
                    async def decode(pixels):
                        return await registry.decode(_decoded_size,pixels)
                    body,mime,photo=await artist_photo.fetch(hass,identity.wikidata_id,guard=guard,decode=decode)
                    attribution=photo.metadata()
                    source,album,width,height,name=attribution['url'],'',photo.width,photo.height,identity.name
                fresh_current = await fresh_scope()
                if fresh_current is None or not authority():
                    return unavailable(session_id, target, 'source_withdrawn',contract_version=contract_version)
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
                           'active_flow_display_allowed': not historical and role != 'captured_reply_subject',
                           'historical_display_allowed': historical, 'cache_policy': 'no-store',
                           'crop_allowed': False, 'requires_device_auth': True,
                           'width': width, 'height': height, 'alt_text': alt_text(name, ':artist:' in uri),
                           'url': PATH.format(session_id=session_id, asset_id=asset_id)}
                if role == 'captured_reply_subject':
                    artwork['reply_display_allowed'] = True
                if contract_version==2 and identity is not None:
                    artwork['subject']['wikidata_id']=identity.wikidata_id
                    artwork['upscale_allowed']=False
                if attribution is not None:
                    artwork['attribution']=attribution
                    artwork['usage_basis']='licensed_artist_image_owner_display'
                    artwork['image_source']={'provider':'wikimedia_commons','selection':'licensed_artist_context'}
                revision = projection_revision(artwork)
                artwork['media_revision'] = revision
                projection = {'schema_version': contract_version, 'session_id': session_id, **target,
                              'revision': revision, 'artwork': artwork}
                asset = {'body': body, 'mime': mime, 'deadline': mono + TTL,
                         '_direct_rich_bytes': validated_bytes,
                         'captured_monotonic': mono, 'authority': authority,
                         'allowed': allowed, 'asset_id': asset_id, 'subject': uri, 'projection': projection,
                         'historical': historical, 'expected_source': dict(expected_source), 'delivery_scope': delivery_scope}
                if not registry.commit(key, asset):
                    return unavailable(session_id, target, 'capacity',contract_version=contract_version)
                if not historical and contract_version==1:
                    attach_live_projection(hass, context.profile_id, session_id)
                return projection
        except asyncio.CancelledError:
            raise
        except PermissionError:
            registry.record_state(key, 'source_withdrawn')
            return unavailable(session_id, target, 'source_withdrawn',contract_version=contract_version)
        except ValueError as exc:
            known = {'missing_image', 'missing_edition', 'edition_mismatch', 'subject_mismatch',
                     'unsafe_image', 'image_too_large', 'source_unavailable', 'missing_subject_label'}
            reason = str(exc) if str(exc) in known else 'source_unavailable'
            registry.negative[key] = time.monotonic()+60
            registry.record_state(key, reason)
            return unavailable(session_id, target, reason,contract_version=contract_version)
        except Exception:  # Optional image failure never invalidates semantic text.
            registry.negative[key] = time.monotonic() + 60
            registry.record_state(key, 'source_unavailable')
            return unavailable(session_id, target, 'source_unavailable',contract_version=contract_version)
        finally:
            registry.inflight.pop(key, None)
            registry.work_guards.pop(key, None)

    registry.work_guards[key] = (authority, invalidate)
    task = hass.async_create_task(run())
    registry.inflight[key] = task
    if not historical and contract_version==1:
        attach_live_projection(hass, context.profile_id, session_id)
    task.add_done_callback(lambda done: registry.inflight.pop(key, None)
                           if registry.inflight.get(key) is done else None)
    return await asyncio.shield(task)


async def resolve_target(hass, runtime, context, session_id, target, *, contract_version=1):
    """Current published contribution or authorized retained entry, never input URI."""
    from .session_runtime import session_runtime_manager

    manager = session_runtime_manager(hass)
    moment_id, entry_id = target.get('moment_id'), target.get('entry_id')
    if bool(moment_id) == bool(entry_id):
        return None
    active = await manager.async_get_active(context.profile_id)
    if moment_id:
        if active is None or active.session_id != session_id or getattr(active.broadcast, 'content_pending', False):
            return None
        moment = next((m for m in active.broadcast.state.dj_moments if m.moment_id == moment_id), None)
        admission = next((a for a in active.broadcast.native_delivery()['admissions'] if a['moment_id'] == moment_id), {})
        fact = getattr(moment, 'source_fact', None)
        uri = subject_for_fact(fact,contract_version=contract_version)
        if not uri or not (admission.get('current_display_allowed') or admission.get('active_flow_display_allowed')):
            return None
        def delivery_scope():
            current = manager._active_by_profile.get(context.profile_id)
            if (current is None or current.broadcast is not active.broadcast
                    or moment_id in current.broadcast.content_pending_moment_ids):
                return None
            a = next((a for a in current.broadcast.native_delivery()['admissions'] if a['moment_id'] == moment_id), {})
            if not (a.get('current_display_allowed') or a.get('active_flow_display_allowed')):
                return None
            return bool(a.get('current_display_allowed')), False
        async def allowed():
            return delivery_scope() is not None
        values=(uri, manager._history_source_contexts.get(session_id, {}), allowed,
                bool(admission.get('current_display_allowed')), False,
                getattr(fact, 'artwork_album_uri', '') if ':track:' in uri else '',
                'contextual_artist' if ':artist:' in uri else 'cover', delivery_scope)
        from .session_facts import ArtistImageIdentity
        identity=getattr(fact,'artwork_artist_identity',None)
        if (contract_version==2 and type(identity) is ArtistImageIdentity
                and identity.eligible() and identity.spotify_uri==uri):
            return ArtistTarget(values,identity)
        return values
    from .session_conversation import query_service

    query = query_service(hass)
    opened = await query.async_open_entry(context.profile_id, session_id, entry_id)
    row = await query._repository.async_entry_record(context.profile_id, session_id, entry_id)
    if not row:
        return None
    body = json.loads(row['body'])
    identity=None
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
        if contract_version==2:
            from .session_facts import ArtistImageIdentity
            artist=body.get('artist_image_reference',{})
            if artist:
                identity=ArtistImageIdentity(artist.get('subject_uri',''),artist.get('wikidata_id',''),
                    artist.get('name',''),artist.get('musicbrainz_id',''))
                if artist.get('version')!=2 or not identity.eligible():
                    return None
                uri,source,album,role=identity.spotify_uri,artist.get('source_context',{}),'','contextual_artist'
            elif body.get('moment_type')=='track':
                return None  # An old cover is not an artist identity.

    elif row['kind'] == 'conversation_dj':
        from .reply_artwork import checked, KEY
        ref = body
        history = query._conversation_history
        if history is None or ref.get('history_scope') != 'profile:' + context.profile_id:
            return None
        messages = await history.async_messages_by_id(ref['history_scope'], {str(ref.get('message_id') or '')})
        message = messages.get(ref.get('message_id'))
        if (not message or message.get('role') != 'assistant'
                or message.get('session_turn', {}).get('turn_id') != ref.get('turn_id')):
            return None
        captured = checked(message.get('session_turn', {}).get(KEY))
        if captured is None:
            return None
        uri, source, album = captured['subject_uri'], captured['source_context'], captured['album_uri']
        from .session_conversation import async_qualify_history_source
        if not await async_qualify_history_source(hass, context.profile_id, {
                'kind':'playback_observed', 'body':json.dumps({'provider':'Spotify','source_context':source})}):
            return None
        role = 'captured_reply_subject'
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
    retained_until = datetime.fromisoformat(row['retained_until']).timestamp() if row.get('retained_until') else None
    def delivery_scope():
        if retained_until is not None and time.time() >= retained_until:
            return None
        latest = manager._active_by_profile.get(context.profile_id)
        same_session = latest is not None and latest.session_id == session_id
        if historical:
            return None if same_session else (False, True)
        if not same_session or latest.broadcast is not active.broadcast:
            return None
        return body.get('item_id') == latest.broadcast.state.playback.item_id, False
    delivery_scope.history_retained_until = retained_until
    header = await query._repository.async_get_session_for_originating_id(session_id) if historical else None
    delivery_scope.history_session_created_at = datetime.fromisoformat(header.created_at).timestamp() if header else None
    values=(uri, source, allowed, is_current, historical, album if ':track:' in uri else '', role, delivery_scope)
    return ArtistTarget(values,identity) if identity is not None else values


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
    reply = artwork.get('role') == 'captured_reply_subject'
    artwork['active_flow_display_allowed'] = not historical and not reply
    if reply:
        artwork['reply_display_allowed'] = True
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
            if (key[:2] != (owner, session_id)
                    or ('media_contract_version','2') in key[2]
                    or ('resource_scope','current_reply') in key[2]):
                # Explicit-response resources never become Session/Flow cards,
                # including their loading, expired or withdrawn state entries.
                continue
            target = {k:v for k,v in key[2] if k in {'moment_id','entry_id'}}
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


def delivery_projection(hass, owner, session_id, target, prepared):
    """Final no-await response fence after every target and authorization await."""
    if prepared.get('artwork', {}).get('state') != 'ready':
        return prepared
    version=prepared.get('schema_version',1)
    registry = hass.data.get('djconnect', {}).get('session_images')
    key = target_key(owner,session_id,target,version)
    asset = registry.get(key) if registry is not None else None
    if asset is None:
        reason = registry.states.get(key, (0, 'source_withdrawn'))[1] if registry else 'source_withdrawn'
        return unavailable(session_id, target, reason,contract_version=version)
    if asset['projection']['artwork']['url'] != prepared['artwork'].get('url'):
        return unavailable(session_id, target, 'source_withdrawn',contract_version=version)
    scope = asset['delivery_scope']()
    if scope is None:
        registry.evict(key, 'source_withdrawn')
        return unavailable(session_id, target, 'source_withdrawn',contract_version=version)
    return project(asset, current=scope[0], historical=scope[1])


async def handle_prepare(hass, data, *, headers=None, user_id=None):
    from .api_handlers import _session_profile_context, _error_payload

    if (not isinstance(data, dict) or type(data.get('contract_version')) is not int
            or data['contract_version'] not in {1,2} or not isinstance(data.get('session_id'), str)
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
            return await prepare(hass, runtime, context, session_id=data['session_id'], target=target,
                                 **({'contract_version':2} if data['contract_version']==2 else {}))
        except (ValueError, PermissionError):
            return unavailable(data['session_id'], target, 'target_unavailable',contract_version=data['contract_version'])
    projections = await asyncio.gather(*(one(t) for t in targets))
    _, current, error, status = await _session_profile_context(
        hass, dict(data), headers=headers, user_id=user_id, source='session_media_complete')
    if error is not None:
        return error, status
    if current.profile_id != context.profile_id or not current.privacy_policy.allow_personal_read:
        return _error_payload('media_not_allowed'), 403
    projections = [delivery_projection(hass, current.profile_id, data['session_id'], target, prepared)
                   for target, prepared in zip(targets, projections, strict=True)]
    return {'success': True, 'contract_version': data['contract_version'], 'session_media': projections}, 200


def project_history_media(hass, owner, row, entry):
    """Pure already-authorized row projection; no IO, renewal or provider work."""
    if row['kind'] not in {'playback_observed', 'dj_moment', 'conversation_dj'}:
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
