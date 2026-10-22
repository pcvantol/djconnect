"""Bounded Spotify artwork references, never provider payloads or portable grants."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import math
import re
import time
from typing import Any
from urllib.parse import urlsplit

ARTWORK_TTL_SECONDS = 6 * 60 * 60
ARTWORK_LEASE_SECONDS = 15 * 60
ARTWORK_MAX_BYTES = 2 * 1024 * 1024
ARTWORK_MAX_GRANTS = 512
_URI = re.compile(r"spotify:(track|album|artist):([A-Za-z0-9]{22})\Z")
_ASSET = re.compile(r"[a-f0-9]{40,64}\Z")
_IMAGE_KEYS = frozenset(
    {
        "artwork",
        "_artwork",
        "image_url",
        "album_image_url",
        "artist_image_url",
        "thumbnail_url",
        "artwork_url",
        "artwork_reference_version",
        "artwork_recent_reference_version",
        "reply_media_reference",
        "images",
        "album_art_url",
        "media_image_url",
        "entity_picture",
        "image_expires_at",
        "image_attribution",
        "image_subject_uri",
        "image_captured_at",
        "image_reference_expires_at",
    }
)


def provider_asset_id(url: Any) -> str:
    """Only the exact existing Spotify CDN image route, no user-controlled fetch."""
    if not isinstance(url, str) or len(url) > 256 or "\\" in url or any(c.isspace() for c in url):
        return ""
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "i.scdn.co"
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            return ""
    except ValueError:
        return ""
    prefix = "/image/"
    asset = parsed.path[len(prefix) :] if parsed.path.startswith(prefix) else ""
    return asset if _ASSET.fullmatch(asset) else ""


def capture_artwork(
    url: Any, subject_uri: Any, media_uri: Any, *, now: float | None = None
) -> dict[str, Any]:
    """Called only at authoritative provider normalization; preserve original clock."""
    asset = provider_asset_id(url)
    if not asset or not isinstance(subject_uri, str) or not isinstance(media_uri, str):
        return {}
    subject, media = _URI.fullmatch(subject_uri), _URI.fullmatch(media_uri)
    if not subject or not media or media[1] != ("album" if subject[1] == "track" else subject[1]):
        return {}
    if subject[1] != "track" and subject_uri != media_uri:
        return {}
    captured = time.time() if now is None else now
    return {
        "version": 1,
        "provider": "spotify",
        "subject_uri": subject_uri,
        "media_uri": media_uri,
        "asset_id": asset,
        "captured_at": captured,
        "expires_at": captured + ARTWORK_TTL_SECONDS,
    }


def compact_artwork(item: dict[str, Any], *, now: float | None = None) -> dict[str, Any]:
    """Validate a current bounded reference against this exact item's identity."""
    ref = item.get("artwork")
    if (
        not isinstance(ref, dict)
        or type(ref.get("version")) is not int
        or ref.get("version") != 1
        or ref.get("provider") != "spotify"
    ):
        return {}
    uri = item.get("uri")
    if ref.get("subject_uri") != uri or not isinstance(uri, str) or not _URI.fullmatch(uri):
        return {}
    if item.get("id") and item["id"] != uri.rsplit(":", 1)[-1]:
        return {}
    media = ref.get("media_uri")
    if uri.startswith("spotify:track:") and item.get("album_uri") != media:
        return {}
    asset = ref.get("asset_id")
    if not isinstance(asset, str) or not _ASSET.fullmatch(asset):
        return {}
    captured, expiry = ref.get("captured_at"), ref.get("expires_at")
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in (captured, expiry)
    ):
        return {}
    current = time.time() if now is None else now
    if (
        not 0 < captured <= current
        or not captured < expiry <= captured + ARTWORK_TTL_SECONDS
        or expiry <= current
    ):
        return {}
    valid = capture_artwork("https://i.scdn.co/image/" + asset, uri, media, now=captured)
    if not valid:
        return {}
    owner = ref.get("owner")
    if (
        isinstance(owner, dict)
        and set(owner) == {"profile_id", "backend_id", "account_id", "revision"}
        and all(isinstance(v, str) and len(v) <= 128 for v in owner.values())
    ):
        valid["owner"] = dict(owner)
    valid["expires_at"] = expiry
    return valid


def artwork_url(item: dict[str, Any]) -> str:
    ref = compact_artwork(item)
    return "https://i.scdn.co/image/" + ref["asset_id"] if ref else ""


def strip_artwork(value: Any) -> Any:
    """Temporary provider references cannot become import/export/archive grants."""
    if isinstance(value, dict):
        return {
            k: strip_artwork(v)
            for k, v in value.items()
            if k.lower().replace("_", "") not in {key.replace("_", "") for key in _IMAGE_KEYS}
        }
    if isinstance(value, list):
        return [strip_artwork(v) for v in value]
    return deepcopy(value)


def artwork_owner(runtime: Any) -> dict[str, str]:
    """Compact non-secret source ownership, preserved only with current references."""
    return {
        "profile_id": str(getattr(runtime, "profile_context_profile_id", "")),
        "backend_id": str(getattr(runtime, "profile_context_backend_id", "")),
        "account_id": str(getattr(runtime, "profile_context_music_account_id", "")),
        "revision": str((getattr(runtime, "config", {}) or {}).get("music_backend_revision", 0)),
    }


def authority_valid(runtime: Any) -> bool:
    """Use current HA and canonical provider ownership, not retained runtime hints."""
    from .profile_backend import profile_backend_entry_id, profile_backend_runtime
    from .client_retirement import is_retired_entry

    manager = getattr(runtime, "memory", None)
    hass = getattr(manager, "hass", None)
    if hass is None:
        return True  # Lightweight unit contexts; production uses the HA manager.
    entry = getattr(runtime, "entry", None)
    entries = getattr(hass, "config_entries", None)
    if (
        entry is None
        or entries is None
        or entries.async_get_entry(entry.entry_id) is not entry
        or is_retired_entry(entry)
        or entry.disabled_by is not None
        or getattr(entry.state, "value", entry.state) != "loaded"
        or hass.data.get("djconnect", {}).get(entry.entry_id) is not runtime
    ):
        return False
    conf = {**entry.data, **entry.options}
    if conf.get("device_token") != getattr(runtime, "device_token", None):
        return False
    platform = hass.data.get("djconnect", {}).get("djconnect_profile_platform")
    pid = getattr(runtime, "profile_context_profile_id", "")
    if not pid:
        return True  # Existing non-Profile contexts retain their paired entry fence.
    if platform is None:
        return False
    household = platform.household
    profile = household.profiles.get(pid)
    backend_id = getattr(runtime, "profile_context_backend_id", "")
    account_id = getattr(runtime, "profile_context_music_account_id", "")
    account = household.music_accounts.get(account_id)
    backend = household.music_backends.get(backend_id)
    if (
        profile is None
        or str(profile.state) != "active"
        or account is None
        or str(account.state) != "active"
        or backend is None
        or str(backend.state) != "active"
        or account.backend_id != backend_id
        or pid not in account.linked_profile_ids
        or profile.preferences.default_backend_id != backend_id
        or profile.preferences.default_music_account_id != account_id
    ):
        return False
    try:
        provider = profile_backend_runtime(hass, runtime, provider_only=True)
        return profile_backend_entry_id(hass, pid) == provider.entry.entry_id
    except Exception:
        return False


def privacy_scope(runtime: Any) -> tuple[Any, ...]:
    policy = getattr(runtime, "profile_context_privacy_policy", None)
    return (
        str(getattr(policy, "mode", "normal")),
        bool(getattr(policy, "private_session", False)),
        bool(getattr(policy, "allow_personal_read", True)),
        bool(getattr(policy, "allow_music_dna_persistence", True)),
    )


def provider_identity(runtime: Any) -> tuple[Any, ...]:
    """Capture the current canonical provider instance, never rotating token material."""
    hass = getattr(getattr(runtime, "memory", None), "hass", None)
    provider = runtime
    if hass is not None:
        from .profile_backend import profile_backend_runtime

        try:
            provider = profile_backend_runtime(hass, runtime, provider_only=True)
        except Exception:
            return (None, None, None, "")
    entry = getattr(provider, "entry", None)
    registered = (
        getattr(hass, "data", {}).get("djconnect", {}).get(getattr(entry, "entry_id", None))
        if hass is not None
        else provider
    )
    return (
        id(provider),
        id(entry),
        id(registered),
        str((getattr(provider, "config", {}) or {}).get("spotify_client_id") or ""),
    )


def credential_cache_scope(runtime: Any) -> str:
    """Effective HA-only credentials fence cache reuse; rotation is not revocation."""
    getter = getattr(runtime, "get_current_spotify_credentials", None)
    credentials = getter() if callable(getter) else (getattr(runtime, "config", {}) or {})
    material = "|".join(
        str(credentials.get(k) or "") for k in ("spotify_client_id", "spotify_refresh_token")
    )
    return hashlib.sha256(material.encode()).hexdigest()


def runtime_scope(runtime: Any) -> tuple[Any, ...]:
    """Transient owner fence; never serialize credentials or this scope."""
    config = getattr(runtime, "config", {}) or {}
    memory = getattr(runtime, "memory", None)
    data = getattr(memory, "data", {}) or {}
    profile = getattr(runtime, "profile_context_profile_id", "")
    key = "profile:" + profile if profile else str(config.get("device_id") or "")
    record = data.get("memories", {}).get(key)
    hass = getattr(memory, "hass", None)
    platform = getattr(hass, "data", {}).get("djconnect", {}).get("djconnect_profile_platform")
    return (
        profile,
        privacy_scope(runtime),
        getattr(runtime, "profile_context_backend_id", ""),
        getattr(runtime, "profile_context_music_account_id", ""),
        config.get("music_backend_revision"),
        config.get("device_id"),
        id(getattr(runtime, "entry", None)),
        str(getattr(getattr(runtime, "entry", None), "state", "")),
        getattr(runtime, "device_token", None),
        id(memory),
        id(record),
        (record or {}).get("generation", 0),
        id(getattr(platform, "household", None)),
        provider_identity(runtime),
    )


@dataclass(frozen=True, repr=False)
class RefreshGuard:
    """Fence provider awaits against clear, consent ABA and owner changes."""

    runtime: Any
    manager: Any
    key: str
    record: dict[str, Any]
    generation: int
    enabled: bool
    scope: tuple[Any, ...]

    @property
    def persistence_allowed(self) -> bool:
        return bool(
            self.enabled
            and getattr(
                getattr(self.runtime, "profile_context_privacy_policy", None),
                "allow_music_dna_persistence",
                True,
            )
        )

    def valid(self) -> bool:
        current = self.manager.data.get("memories", {}).get(self.key)
        hass = getattr(self.manager, "hass", None)
        entry = getattr(self.runtime, "entry", None)
        entry_id = getattr(entry, "entry_id", None)
        if (
            hass is not None
            and entry_id
            and getattr(hass, "data", {}).get("djconnect", {}).get(entry_id) is not self.runtime
        ):
            return False
        return (
            (
                not self.key.startswith("profile:")
                or self.key == "profile:" + getattr(self.runtime, "profile_context_profile_id", "")
            )
            and getattr(self.runtime, "memory", None) is self.manager
            and current is self.record
            and bool(current.get("enabled")) == self.enabled
            and current.get("generation", 0) == self.generation
            and runtime_scope(self.runtime) == self.scope
            and authority_valid(self.runtime)
            and getattr(
                getattr(self.runtime, "profile_context_privacy_policy", None),
                "allow_personal_read",
                True,
            )
        )


async def capture_refresh_guard(
    runtime: Any, payload: dict[str, Any], *, user_id: str | None = None
) -> RefreshGuard | None:
    """Capture before network I/O, using the manager's canonical resolved key."""
    from .music_dna import resolve_music_dna_key

    manager = getattr(runtime, "memory", None)
    if manager is None or not hasattr(manager, "data") or not hasattr(manager, "async_load"):
        return None
    await manager.async_load()
    key = resolve_music_dna_key(runtime, payload, user_id=user_id)
    record = manager.data.get("memories", {}).get(key)
    if record is None:
        record = manager._memory_for_key(key) if authority_valid(runtime) else {}
    if not isinstance(record, dict):
        return None
    return RefreshGuard(
        runtime,
        manager,
        key,
        record,
        record.get("generation", 0),
        bool(record.get("enabled")),
        runtime_scope(runtime),
    )


_GRANTS = "discovery_image_grants"


def register_discovery_image(
    hass: Any, guard: RefreshGuard, ref: dict[str, Any]
) -> tuple[str, float]:
    """Issue a bounded headerless capability to the already authorized owner."""
    import secrets
    from .const import API_IMAGE_PROXY_BASE, DOMAIN

    now = time.time()
    if (
        not guard.enabled
        or not guard.valid()
        or ref.get("owner") != artwork_owner(guard.runtime)
        or ref.get("expires_at", 0) <= now
    ):
        return "", 0
    grants = hass.data.setdefault(DOMAIN, {}).setdefault(_GRANTS, {})
    for token, grant in list(grants.items()):
        if grant["expires_at"] <= now or not grant["guard"].valid():
            grants.pop(token)
    expiry = min(ref["expires_at"], now + ARTWORK_LEASE_SECONDS)
    while len(grants) >= ARTWORK_MAX_GRANTS:
        grants.pop(next(iter(grants)))
    token = "disc-" + secrets.token_urlsafe(24)
    grants[token] = {"guard": guard, "ref": dict(ref), "expires_at": expiry}
    return f"{API_IMAGE_PROXY_BASE}/{token}", expiry


async def discovery_image_response(hass: Any, request: Any, token: str) -> Any:
    """Bounded credential-free CDN delivery; legacy image tokens use their old path."""
    import asyncio
    from aiohttp import ClientError, ClientTimeout, web
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from .const import DOMAIN
    from .request_auth import authorize_runtime_device_request

    def current() -> bool:
        return bool(
            grant
            and grant["expires_at"] > time.time()
            and grant["guard"].valid()
            and grant["ref"]["expires_at"] > time.time()
        )

    grant = hass.data.get(DOMAIN, {}).get(_GRANTS, {}).get(token)
    if not current():
        return web.Response(status=404)
    guard = grant["guard"]
    headers = request.headers
    if any(
        headers.get(k)
        for k in ("Authorization", "X-DJConnect-Device-ID", "X-DJConnect-Client-Type")
    ):
        if not authorize_runtime_device_request(
            guard.runtime,
            headers,
            headers.get("X-DJConnect-Device-ID"),
            headers.get("X-DJConnect-Client-Type"),
        ):
            return web.Response(status=401)
    url = "https://i.scdn.co/image/" + grant["ref"]["asset_id"]
    if not provider_asset_id(url):
        return web.Response(status=404)
    try:
        async with async_get_clientsession(hass).get(
            url,
            allow_redirects=False,
            timeout=ClientTimeout(total=12),
            headers={"Accept": "image/png,image/jpeg,image/webp"},
        ) as response:
            mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if response.status != 200 or mime not in {"image/png", "image/jpeg", "image/webp"}:
                return web.Response(status=502)
            if response.content_length is not None and response.content_length > ARTWORK_MAX_BYTES:
                return web.Response(status=502)
            chunks = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                chunks.extend(chunk)
                if len(chunks) > ARTWORK_MAX_BYTES:
                    return web.Response(status=502)
            body = bytes(chunks)
            signatures = {
                "image/png": body.startswith(b"\x89PNG\r\n\x1a\n"),
                "image/jpeg": body.startswith(b"\xff\xd8\xff"),
                "image/webp": body.startswith(b"RIFF") and body[8:12] == b"WEBP",
            }
            if not signatures[mime]:
                return web.Response(status=502)
    except (ClientError, asyncio.TimeoutError):
        return web.Response(status=502)
    if not current():
        return web.Response(status=404)
    return web.Response(
        body=body,
        content_type=mime,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


async def project_discovery_images(
    hass: Any,
    runtime: Any,
    response: dict[str, Any],
    payload: dict[str, Any],
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Project private reference cache into fresh scoped delivery URLs, never grants in Store."""
    result = deepcopy(response)
    guard = await capture_refresh_guard(runtime, payload, user_id=user_id)
    for section in result.get("sections", []):
        for item in section.get("items", []):
            ref = item.pop("_artwork", {})
            item.pop("image_url", None)
            if ref and guard is not None and hass is not None:
                valid = compact_artwork(
                    {"uri": item.get("uri"), "album_uri": ref.get("media_uri"), "artwork": ref}
                )
                url, expiry = register_discovery_image(hass, guard, valid) if valid else ("", 0)
                if url:
                    item.update(
                        image_url=url,
                        image_expires_at=expiry,
                        image_attribution={
                            "provider": "spotify",
                            "media_uri": ref["media_uri"],
                            "source_url": "https://open.spotify.com/"
                            + ref["media_uri"].replace("spotify:", "").replace(":", "/"),
                        },
                    )
    return result


def project_music_dna_images(
    hass: Any,
    runtime: Any,
    response: dict[str, Any],
    guard: RefreshGuard | None,
) -> dict[str, Any]:
    """Only current exact media proof becomes a transient owner-scoped image lease."""
    from .music_dna import _accepted_artwork_reference

    result = strip_artwork(response)
    if (
        not result.get("enabled")
        or guard is None
        or guard.runtime is not runtime
        or result.get("music_dna_key") != guard.key
        or not guard.enabled
        or not guard.valid()
        or not isinstance(getattr(hass, "data", None), dict)
    ):
        return result
    profile = result.get("profile")
    if not isinstance(profile, dict):
        return result
    # Deliberately exclude historical snapshots, blocked data and label-only joins.
    groups = [profile.get(k) for k in (
        "recent_tracks", "recent_favorite_tracks", "favorite_artists", "recommendation_signals"
    )]
    for family in ("top_tracks_by_range", "top_artists_by_range"):
        ranges = profile.get(family)
        if isinstance(ranges, dict):
            groups.extend(ranges.values())
    positives = profile.get("explicit_positives")
    if isinstance(positives, dict):
        groups.extend(positives.get(k) for k in ("favorite_tracks", "accepted_recommendations"))
    issued: dict[str, tuple[str, dict[str, Any]]] = {}
    scanned = 0
    owner = artwork_owner(runtime)
    for group in groups:
        if not isinstance(group, list):
            continue
        for item in group:
            scanned += 1
            if scanned > 1000:
                return result
            if not isinstance(item, dict):
                continue
            uri = item.get("uri")
            if not isinstance(uri, str) or not _URI.fullmatch(uri):
                continue
            if item.get("id") and item["id"] != uri.rsplit(":", 1)[-1]:
                continue
            if uri in issued:
                media_uri, projection = issued[uri]
                if not item.get("album_uri") or item["album_uri"] == media_uri:
                    item.update(projection)
                continue
            if len(issued) >= 128:
                continue
            ref = _accepted_artwork_reference(guard.record, uri, owner)
            if not ref or (item.get("album_uri") and item["album_uri"] != ref["media_uri"]):
                continue
            url, expiry = register_discovery_image(hass, guard, ref)
            if not url:
                continue
            projection = {
                "image_url": url,
                "image_subject_uri": uri,
                "image_captured_at": ref["captured_at"],
                "image_reference_expires_at": ref["expires_at"],
                "image_expires_at": expiry,
                "image_attribution": {
                    "provider": "spotify",
                    "media_uri": ref["media_uri"],
                    "source_url": "https://open.spotify.com/"
                    + ref["media_uri"].replace("spotify:", "").replace(":", "/"),
                },
            }
            issued[uri] = (ref["media_uri"], projection)
            item.update(projection)
    return result
