"""Purpose-qualified passive Session delivery, never a second content producer.

Only original accepted evidence and already prepared cover bytes are projected.
Reads do not renew clocks, fetch content, mutate grants or publish events.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import re
import secrets
import time
from typing import Callable

VERSION = 1
MAX_GRANTS = 32
SURFACES = {'widget', 'live_activity'}
TRACK = re.compile(r'https://open\.spotify\.com/track/([A-Za-z0-9]{22})\Z')
BASE = '/api/djconnect/v1/session/surface'


def stamp(value):
    return datetime.fromtimestamp(value, UTC).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:32]


def capability():
    return {'version': VERSION, 'owner_only': True, 'authentication': 'paired_device_bearer',
            'authorize_path': BASE + '/authorize', 'read_path': BASE + '/read',
            'surfaces': sorted(SURFACES), 'explicit_consent_required': True,
            'max_cache_seconds': 120, 'read_side_effects': False,
            'live_invalidation': 'existing_owner_broadcast_events',
            'background_delivery': False, 'watch_replication': False}


@dataclass(frozen=True)
class SurfaceGrant:
    grant_id: str
    binding_id: str
    generation: str
    entry_id: str
    surface: str
    locked_display: bool
    authority: Callable[[], bool]


def _text(broadcast, now):
    """Exact complete accepted copy; no inference or client-side shortening."""
    if broadcast.state.selected_presence == 'music_only':
        return None
    admissions = {a['moment_id']: a for a in broadcast.native_delivery()['admissions']}
    for moment in reversed(broadcast.state.dj_moments):
        a = admissions.get(moment.moment_id, {})
        boundary = broadcast._moment_delivery_boundaries.get(moment.moment_id)
        if (not boundary or a.get('qualification') != 'qualified'
                or not (a.get('current_display_allowed') or a.get('active_flow_display_allowed'))
                or moment.presentation_intent.visibility.value == 'owner_only'
                or moment.moment_type.value == 'silence' or not moment.content
                or len(moment.content) > 640):
            continue
        fact = moment.source_fact
        cc0 = fact is not None and fact.provider in {'MusicBrainz', 'Wikidata'} and fact.license == 'CC0-1.0'
        authored = fact is None and moment.source_references == ('session_direction',)
        if not (cc0 or authored):
            continue
        # Native qualification is one input, not the passive purpose licence.
        deadline = datetime.fromisoformat(a['display_expires_at']).timestamp()
        if not boundary.published_monotonic <= now < boundary.published_monotonic + min(
                120, moment.presentation_intent.maximum_duration_seconds):
            continue
        return {'moment_id': moment.moment_id, 'published_at': boundary.published_at,
                'text': moment.content, 'persona': moment.presentation_intent.dj_persona.value,
                'source_attribution': dict(moment.source_attribution),
                'usage_basis': 'cc0_facts_authored_expression' if cc0 else 'runtime_authored_direction',
                'expires_at': stamp(deadline)}
    return None


def _music(broadcast, now):
    observed = broadcast.passive_observation
    if not observed or not 0 <= now - observed[0] < 120:
        return None
    _, wall, original = observed
    current = broadcast.state.playback
    match = TRACK.fullmatch(original.source_url)
    if (not match or current.item_id != original.item_id
            or current.state not in {'playing', 'paused'} or not original.title):
        return None
    return {'item_id': original.item_id, 'subject_uri': 'spotify:track:' + match[1],
            'track': original.title, 'artist': original.artist, 'album': original.album,
            'observed_at': stamp(wall), 'expires_at': stamp(wall + 120),
            'source_url': original.source_url,
            'attribution': {'provider': 'Spotify', 'mark': 'spotify', 'url': original.source_url},
            'usage_basis': 'spotify_temporary_passive_metadata'}


def _covers(registry, owner, session_id, contribution, music, now):
    """Independent cover-only qualification; no private URL/grant reuse."""
    if registry is None or registry.closed:
        return []
    slots = []
    for key, asset in registry.assets.items():
        if (key[:2] != (owner, session_id) or asset['historical']
                or asset['deadline'] <= now or not asset['authority']()):
            continue
        scope = asset['delivery_scope']()
        art = asset['projection']['artwork']
        target = dict(key[2])
        subject = art.get('subject', {})
        if (scope is None or art.get('state') != 'ready' or subject.get('type') not in {'track', 'album'}
                or art.get('role') not in {'cover', 'playback_thumbnail'}
                or art.get('usage_basis') != 'spotify_temporary_owner_display'
                or art.get('attribution') != {'provider': 'Spotify', 'mark': 'spotify', 'url': art.get('source_url')}
                or not re.fullmatch(r'https://open\.spotify\.com/(track|album)/[A-Za-z0-9]{22}', art.get('source_url', ''))):
            continue
        slot, expires = None, None
        if contribution and target.get('moment_id') == contribution['moment_id']:
            slot, expires = 'contribution', contribution['expires_at']
        elif music and scope[0] and subject.get('uri') == music['subject_uri']:
            slot, expires = 'now_playing', music['expires_at']
        if slot is None or any(v['slot'] == slot for v in slots):
            continue
        expiry = min(datetime.fromisoformat(expires).timestamp(),
                     datetime.fromisoformat(art['expires_at']).timestamp(),
                     datetime.fromisoformat(art['captured_at']).timestamp() + 120)
        # Monotonic and UTC must both permit; clock uncertainty fails closed.
        if time.time() >= expiry:
            continue
        slots.append({'slot': slot, 'asset_id': asset['asset_id'], 'subject': dict(subject),
                      'role': 'contextual_cover' if slot == 'contribution' else 'current_cover',
                      'media_revision': art['media_revision'], 'captured_at': art['captured_at'],
                      'expires_at': stamp(expiry), 'source_url': art['source_url'],
                      'attribution': dict(art['attribution']), 'alt_text': dict(art['alt_text']),
                      'width': art['width'], 'height': art['height'], 'crop_allowed': False,
                      'usage_basis': 'spotify_temporary_passive_cover',
                      'image_path': BASE + '/image/' + session_id + '/' + asset['asset_id'],
                      'rights': {'passive_cache': True, 'os_snapshot': True,
                                 'external_relay': False, 'watch_replication': False}})
    return slots


def projection(active, grant, *, registry=None, owner=''):
    """Pure projection over accepted state; grant authority is checked by caller."""
    broadcast = active.broadcast
    now, wall = time.monotonic(), time.time()
    result = {'schema_version': VERSION, 'surface': grant.surface,
              'binding_id': grant.binding_id, 'generation': grant.generation,
              'session_id': active.session_id, 'delivery_sequence': broadcast.delivery_sequence,
              'as_of': stamp(wall), 'observed_at': stamp(broadcast.passive_state_observed[1]),
              'expires_at': stamp(broadcast.passive_state_observed[1] + 120),
              'state': 'active', 'playback_state': broadcast.state.playback.state,
              'cache_policy': {'scope': 'current_surface_only', 'maximum_seconds': 120,
                               'renew_on_read': False, 'locked_display': grant.locked_display,
                               'os_pixel_erasure': 'best_effort_when_learned'},
              'mood': {'value': active.selected_mood if active.selected_mood in
                       {'chill', 'groove', 'energy', 'party'} else None, 'revision': active.mood_revision},
              'presence': active.selected_presence, 'persona': active.dj_persona.value,
              'navigation': {'kind': 'open_session', 'session_id': active.session_id}}
    if (not grant.authority() or active.runtime_state.value != 'active'
            or broadcast.state.runtime_state.value != 'active'):
        return {'schema_version': VERSION, 'state': 'withdrawn', 'surface': grant.surface,
                'binding_id': grant.binding_id, 'generation': grant.generation,
                'session_id': active.session_id, 'delivery_sequence': broadcast.delivery_sequence,
                'as_of': stamp(wall), 'expires_at': stamp(wall), 'artwork': []}
    contribution, music = _text(broadcast, now), _music(broadcast, now)
    result['contribution'], result['now_playing'] = contribution, music
    result['artwork'] = _covers(registry, owner, active.session_id, contribution, music, now)
    if now - broadcast.passive_state_observed[0] >= 120:
        result['state'] = 'stale'
        result['contribution'], result['now_playing'], result['artwork'] = None, None, []
    result['revision'] = digest({k: v for k, v in result.items() if k != 'as_of'})
    return result


async def handle(hass, payload, *, headers=None, authorize=False):
    """Ordinary pairing + exact owner/entry/generation/source fences."""
    from .api_handlers import _async_owner_broadcast_session_context
    from .profile_context import profile_storage
    from .profile_privacy import resolve_profile_privacy_policy
    from .forecast_imagery import artist_authority
    from .request_auth import resolve_runtime, authorize_runtime_device_request

    def error(code, status):
        return {'success': False, 'error': code}, status

    fields = {'contract_version', 'device_id', 'client_type', 'session_id', 'surface'}
    fields |= {'enabled', 'os_snapshot_cache', 'locked_display'} if authorize else {'grant_id'}
    if (not isinstance(payload, dict) or set(payload) != fields
            or type(payload.get('contract_version')) is not int or payload['contract_version'] != VERSION
            or any(type(payload[k]) is not str or not 0 < len(payload[k]) <= 128
                   for k in fields - {'contract_version', 'enabled', 'os_snapshot_cache', 'locked_display'})
            or payload['surface'] not in SURFACES or payload['client_type'] not in {'ios', 'macos'}):
        return error('invalid_request', 400)
    if authorize and any(type(payload[k]) is not bool for k in ('enabled', 'os_snapshot_cache', 'locked_display')):
        return error('invalid_request', 400)
    headers = headers or {}
    if not str(headers.get('Authorization', '')).startswith('Bearer '):
        return error('unauthorized', 401)
    runtime = resolve_runtime(hass, payload['device_id'], headers)
    if runtime is None or not authorize_runtime_device_request(runtime, headers, payload['device_id'], payload['client_type']):
        return error('unauthorized', 401)
    context, status, manager, owner = await _async_owner_broadcast_session_context(
        hass, dict(payload), headers=headers, source='passive_session')
    if manager is None:
        return context, status
    storage = profile_storage(hass)
    revision = storage.authority_revision
    entry = runtime.entry
    device_id, client_type = payload['device_id'], payload['client_type']
    entry_generation = getattr(runtime, '_receiver_end_generation', 0)
    source_authority = artist_authority(hass, runtime, owner_profile_id=owner,
        expected_source=manager._history_source_contexts.get(payload['session_id'], {}))
    active = manager._active_by_profile.get(owner)
    if active is None or active.session_id != payload['session_id']:
        return error('active_session_not_found', 404)

    def current():
        try:
            profile = storage.resolver().resolve_bound_device(device_id)
            latest = manager._active_by_profile.get(owner)
            conf = {**entry.data, **entry.options}
            return (profile_storage(hass) is storage and storage.authority_revision == revision
                    and latest is not None and latest.broadcast is active.broadcast
                    and latest.runtime_state.value == 'active' and source_authority()
                    and manager.receiver_entry_generation(entry.entry_id) == entry_generation
                    and profile.profile_id == owner and profile.privacy_mode.value == 'normal'
                    and resolve_profile_privacy_policy(profile, {}).allow_personal_read
                    and conf.get('device_id') == device_id and conf.get('client_type') == client_type)
        except Exception:
            return False

    if not current():
        return error('surface_not_allowed', 403)
    grants = active.broadcast.passive_grants
    key = (entry.entry_id, payload['surface'])
    if authorize:
        if not payload['enabled']:
            grants.pop(key, None)
            return {'success': True, 'contract_version': VERSION, 'state': 'disabled'}, 200
        if not payload['os_snapshot_cache'] or (payload['surface'] == 'live_activity' and not payload['locked_display']):
            return error('surface_consent_required', 403)
        if key not in grants and len(grants) >= MAX_GRANTS:
            return error('surface_capacity', 409)
        grant = SurfaceGrant(secrets.token_urlsafe(24), secrets.token_hex(16), secrets.token_hex(16),
                             entry.entry_id, payload['surface'], payload['locked_display'], current)
        grants[key] = grant
    else:
        grant = grants.get(key)
        if not grant or not secrets.compare_digest(grant.grant_id, payload['grant_id']) or not grant.authority():
            return error('surface_grant_invalid', 403)
    resource = projection(active, grant, registry=hass.data.get('djconnect', {}).get('session_images'), owner=owner)
    return {'success': True, 'contract_version': VERSION, 'grant_id': grant.grant_id,
            'passive_session': resource}, 200
