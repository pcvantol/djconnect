"""Current-artist display assets; bounded preparation and pure scoped reads."""
from __future__ import annotations

import asyncio
import hashlib
import re
import secrets
import time
from dataclasses import dataclass, replace
from typing import Any, Callable
from urllib.parse import urlparse

from .session_forecast import timestamp

MAX_ATTEMPTS = 12
MAX_BYTES = 2 * 1024 * 1024
ASSET_LIFETIME = 300
NEGATIVE_BACKOFF = 60
IMAGE_PATH = '/api/djconnect/v1/session/forecast/art/{session_id}/{asset_id}'


def safe_cdn_url(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        p = urlparse(value)
        return (p.scheme == 'https' and p.hostname == 'i.scdn.co' and p.port in (None, 443)
                and not p.username and not p.password and not p.query and not p.fragment
                and re.fullmatch(r'/image/[A-Za-z0-9]{20,128}', p.path) is not None)
    except ValueError:
        return False


def image_format(body: bytes, mime: str) -> bool:
    return (0 < len(body) <= MAX_BYTES and
            ((mime == 'image/png' and body.startswith(b'\x89PNG\r\n\x1a\n'))
             or (mime == 'image/jpeg' and body.startswith(b'\xff\xd8\xff'))
             or (mime == 'image/webp' and body[:4] == b'RIFF' and body[8:12] == b'WEBP')))


@dataclass(frozen=True)
class ForecastAsset:
    asset_id: str
    subject_id: str
    item_id: str
    metadata: dict
    body: bytes
    mime: str
    deadline: float
    authority: Callable[[], bool]

    def allowed(self, now: float, item_id: str) -> bool:
        return now < self.deadline and item_id == self.item_id and self.authority()


class ForecastArtwork:
    """One bounded store belongs to one Forecast, not persisted/global cache."""

    def __init__(self):
        self.assets: tuple[ForecastAsset, ...] = ()
        self.attempts = 0
        self.last_attempt: dict[str, float] = {}
        self.lock = asyncio.Lock()

    def public(self, item_id: str) -> tuple[dict, ...]:
        return tuple(a.metadata for a in self.assets if a.allowed(time.monotonic(), item_id))

    def commit(self, asset):
        self.assets = (*self.assets[-1:], asset)

    def clear(self):
        self.assets = ()
        # Counters survive settings/reconnect; only Runtime disposal ends them.

    async def prepare(self, *, hass, backend, session_id: str, item_id: str,
                      artist_id: str, authority, candidate_current) -> ForecastAsset | bool:
        if not re.fullmatch(r'[A-Za-z0-9]{22}', artist_id) or self.lock.locked():
            return False
        now = time.monotonic()
        observed_wall = time.time()
        if not authority() or not candidate_current():
            return False
        # Rebind already-qualified pixels only to an observed track with this
        # exact artist identity. Preserve original provenance/deadlines/budget.
        for cached in self.assets:
            if cached.subject_id == artist_id and now < cached.deadline and cached.authority():
                if cached.item_id == item_id:
                    return False
                asset_id = secrets.token_urlsafe(24)
                metadata = {**cached.metadata,
                            'url': IMAGE_PATH.format(session_id=session_id, asset_id=asset_id)}
                return replace(cached, asset_id=asset_id, item_id=item_id, metadata=metadata,
                               authority=authority)
        if (self.attempts >= MAX_ATTEMPTS
                or now - self.last_attempt.get(artist_id, -1e9) < NEGATIVE_BACKOFF):
            return False
        async with self.lock:
            self.attempts += 1
            self.last_attempt[artist_id] = now
            try:
                metadata = await asyncio.wait_for(backend._request('GET', '/artists/'+artist_id), timeout=4)
                if not authority() or not candidate_current():
                    return False
                if (not isinstance(metadata, dict) or metadata.get('id') != artist_id
                        or metadata.get('type') != 'artist' or metadata.get('uri') != 'spotify:artist:'+artist_id):
                    return False
                source = 'https://open.spotify.com/artist/'+artist_id
                if (metadata.get('external_urls') or {}).get('spotify') != source:
                    return False
                images = metadata.get('images')
                if not isinstance(images, list):
                    return False
                image = next((i for i in images[:3] if isinstance(i, dict) and safe_cdn_url(i.get('url'))
                              and type(i.get('width')) is int and type(i.get('height')) is int
                              and 0 < i['width'] <= 4096 and 0 < i['height'] <= 4096), None)
                if image is None or type(metadata.get('name')) is not str or not metadata['name'].strip():
                    return False
                from homeassistant.helpers.aiohttp_client import async_get_clientsession
                from aiohttp import ClientTimeout
                async with async_get_clientsession(hass).get(image['url'], allow_redirects=False,
                                                            timeout=ClientTimeout(total=4)) as response:
                    if response.status != 200:
                        return False
                    mime = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            return False
                    body = bytes(body)
                if not image_format(body, mime) or not authority() or not candidate_current():
                    return False
                asset_id = secrets.token_urlsafe(24)
                public = {'subject': {'type': 'artist', 'id': 'spotify:artist:'+artist_id,
                                      'name': metadata['name'].strip()[:256]},
                          'role': 'current', 'source_url': source, 'image_source_url': image['url'],
                          'attribution': {'provider': 'Spotify', 'mark': 'spotify', 'url': source},
                          'usage_basis': 'spotify_display_current_only',
                          'expires_at': timestamp(observed_wall+ASSET_LIFETIME),
                          'url': IMAGE_PATH.format(session_id=session_id, asset_id=asset_id),
                          'cache_policy': 'active_session_no_store'}
                asset = ForecastAsset(asset_id, artist_id, item_id, public, body, mime,
                                      now+ASSET_LIFETIME, authority)
                return asset
            except asyncio.CancelledError:
                raise
            except Exception:
                # Public-art failure adds no provider fallback, log payload or Moment.
                return False


def artist_authority(hass, runtime, *, owner_profile_id: str, expected_source=None):
    """Capture source/account/pairing authority without storing credentials."""
    from .const import DOMAIN
    from .profile_context import profile_storage
    from .profile_backend import profile_backend_runtime
    entry = getattr(runtime, 'entry', None)
    entry_id = str(getattr(entry, 'entry_id', ''))
    generation = getattr(runtime, '_receiver_end_generation', 0)
    conf = {**getattr(entry, 'data', {}), **getattr(entry, 'options', {})}
    device_id = str(conf.get('device_id') or '')
    token_present = bool(conf.get('device_token'))
    token_digest = hashlib.sha256(str(conf.get('device_token') or '').encode()).digest()
    expected_source = expected_source or {}
    manager = hass.data.get(DOMAIN, {}).get('session_runtime_manager')
    try:
        provider = profile_backend_runtime(hass, runtime, provider_only=True)
        provider_entry = provider.entry
        provider_generation = getattr(provider, "_receiver_end_generation", 0)
        storage = profile_storage(hass)
        profile = storage.resolver().resolve_bound_device(device_id)
        prefs = profile.preferences
        account = storage.household.music_accounts.get(prefs.default_music_account_id)
        backend = storage.household.music_backends.get(prefs.default_backend_id)
    except Exception:
        return lambda: False

    def allowed():
        if (entry is None or account is None or backend is None or not token_present
                or manager is None
                or hass.data.get(DOMAIN, {}).get('session_runtime_manager') is not manager
                or manager.receiver_entry_generation(entry_id) != generation
                or hass.data.get(DOMAIN, {}).get(entry_id) is not runtime
                or hass.config_entries.async_get_entry(entry_id) is not entry
                or entry.disabled_by is not None
                or getattr(getattr(entry, 'state', None), 'value', None) != 'loaded'
                or getattr(runtime, '_receiver_end_generation', 0) != generation):
            return False
        current_conf = {**entry.data, **entry.options}
        if (current_conf.get('device_id') != device_id
                or hashlib.sha256(str(current_conf.get('device_token') or '').encode()).digest() != token_digest):
            return False
        try:
            if profile_storage(hass) is not storage:
                return False
            current_provider = profile_backend_runtime(hass, runtime, provider_only=True)
            if (current_provider is not provider
                    or manager.receiver_entry_generation(provider_entry.entry_id) != provider_generation
                    or getattr(provider, "_receiver_end_generation", 0) != provider_generation
                    or expected_source.get("provider_entry_id", provider_entry.entry_id) != provider_entry.entry_id
                    or hass.data.get(DOMAIN, {}).get(provider_entry.entry_id) is not provider
                    or hass.config_entries.async_get_entry(provider_entry.entry_id) is not provider_entry
                    or provider_entry.disabled_by is not None
                    or getattr(provider_entry.state, 'value', provider_entry.state) != 'loaded'):
                return False
            current = storage.resolver().resolve_bound_device(device_id)
            return (current.profile_id == owner_profile_id and current.state.value == 'active'
                    and account.state.value == 'active' and backend.state.value == 'active'
                    and account.backend_id == backend.backend_id
                    and owner_profile_id in account.linked_profile_ids
                    and expected_source.get('music_account_id', prefs.default_music_account_id) == prefs.default_music_account_id
                    and expected_source.get('backend_id', prefs.default_backend_id) == prefs.default_backend_id
                    and expected_source.get('provider_account_id', account.provider_account_id) == account.provider_account_id
                    and current.preferences.default_music_account_id == prefs.default_music_account_id
                    and current.preferences.default_backend_id == prefs.default_backend_id
                    and storage.household.music_accounts.get(prefs.default_music_account_id) is account
                    and storage.household.music_backends.get(prefs.default_backend_id) is backend)
        except Exception:
            return False
    return allowed
