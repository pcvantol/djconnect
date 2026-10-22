"""Captured reply subject identity; original pixels and image leases never persist."""

from __future__ import annotations

from copy import deepcopy
import re

SOURCE_FIELDS = ("backend_id", "music_account_id", "provider_entry_id", "provider_account_id")
_URI = re.compile(r"spotify:(track|album|artist):[A-Za-z0-9]{22}\Z")
KEY = "reply_media_reference"


def checked(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "subject_uri", "album_uri", "source_context"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or not isinstance(value["subject_uri"], str)
        or not _URI.fullmatch(value["subject_uri"])
        or not isinstance(value["album_uri"], str)
        or (
            value["album_uri"]
            and not re.fullmatch(r"spotify:album:[A-Za-z0-9]{22}", value["album_uri"])
        )
        or not isinstance(value["source_context"], dict)
        or set(value["source_context"]) != set(SOURCE_FIELDS)
        or any(
            not isinstance(v, str) or not 0 < len(v) <= 256
            for v in value["source_context"].values()
        )
    ):
        return None
    if value["subject_uri"].startswith("spotify:track:") and not value["album_uri"]:
        return None
    if (
        value["subject_uri"].startswith("spotify:album:")
        and value["album_uri"] != value["subject_uri"]
    ):
        return None
    if value["subject_uri"].startswith("spotify:artist:") and value["album_uri"]:
        return None
    return deepcopy(value)


def public(value):
    """A stored original source binding is internal, including nested duplicate receipts."""
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if k != KEY}
    if isinstance(value, list):
        return [public(v) for v in value]
    return value


def source_admission(hass, runtime, owner):
    """Capture the existing loaded source, never pick a substitute account on read."""
    from .profile_backend import profile_backend_runtime
    from .profile_context import profile_storage
    from .forecast_imagery import artist_authority

    try:
        storage = profile_storage(hass)
        profile = storage.household.profiles[owner]
        account = storage.household.music_accounts[profile.preferences.default_music_account_id]
        backend = storage.household.music_backends[profile.preferences.default_backend_id]
        provider = profile_backend_runtime(hass, runtime, provider_only=True)
        if str(backend.provider) != "spotify_direct":
            return None, None
        source = {
            "backend_id": backend.backend_id,
            "music_account_id": account.account_id,
            "provider_entry_id": provider.entry.entry_id,
            "provider_account_id": str(account.provider_account_id),
        }
        if any(not isinstance(source[k], str) or not source[k] for k in SOURCE_FIELDS):
            return None, None
        authority = artist_authority(hass, runtime, owner_profile_id=owner, expected_source=source)
        return (source, authority) if authority() else (None, None)
    except (AttributeError, KeyError, ValueError, PermissionError):
        return None, None


def subject(source, source_context):
    """Only this provider-normalized image's explicit subject and edition qualify."""
    from .discovery_artwork import provider_asset_id

    if not isinstance(source, dict):
        return None
    url = next(
        (
            source.get(k)
            for k in ("album_image_url", "media_image_url", "image_url", "thumbnail_url")
            if source.get(k)
        ),
        None,
    )
    if not provider_asset_id(url):
        return None
    uri = next((source.get(k) for k in ("uri", "track_uri", "current_uri") if source.get(k)), None)
    if not isinstance(uri, str) or not _URI.fullmatch(uri):
        return None
    album = source.get("album_uri")
    if not album and isinstance(source.get("album"), dict):
        album = source["album"].get("uri")
    album = album or (uri if uri.startswith("spotify:album:") else "")
    return checked(
        {
            "schema_version": 1,
            "subject_uri": uri,
            "album_uri": album,
            "source_context": source_context,
        }
    )


def remember_image(source, image):
    from .ask_dj.dialogue import current_turn

    turn = current_turn.get()
    if (
        turn is None
        or getattr(turn, "reply_source_authority", None) is None
        or not turn.reply_source_authority()
    ):
        return
    value = subject(source, turn.reply_source_context)
    if value is not None:
        turn.reply_media_candidate = (value, image["url"])


def accepted(turn, result):
    candidate = turn.reply_media_candidate
    if (
        not candidate
        or getattr(turn, "reply_source_authority", None) is None
        or not turn.reply_source_authority()
        or result.get("success") is False
    ):
        return None
    urls = {i.get("url") for i in result.get("images", []) if isinstance(i, dict)}
    return checked(candidate[0]) if candidate[1] in urls else None


async def _download_observed_cover(hass, url, guard, registry):
    """Only the already observed CDN asset; no new Spotify metadata/model call."""
    from aiohttp import ClientTimeout
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from .session_artwork import MAX_BYTES, _decoded_size
    from .forecast_imagery import image_format

    async with async_get_clientsession(hass).get(
        url, allow_redirects=False, timeout=ClientTimeout(total=4)
    ) as response:
        await guard()
        if response.status != 200:
            raise ValueError('source_unavailable')
        mime=response.headers.get('Content-Type','').split(';')[0].strip().lower()
        body=bytearray()
        async for chunk in response.content.iter_chunked(65536):
            await guard()
            body.extend(chunk)
            if len(body)>MAX_BYTES:
                raise ValueError('image_too_large')
    pixels=bytes(body)
    if not image_format(pixels,mime):
        raise ValueError('unsafe_image')
    await registry.decode(_decoded_size,pixels)
    await guard()
    return pixels,mime


async def observed_current_image(hass, turn, admission, sample):
    """Bounded current-reply pixels under the existing authenticated RAM owner.

    An originally general Profile turn uses no Session identity and never
    creates a Session to obtain images.
    """
    import asyncio
    import secrets
    import time
    from datetime import UTC, datetime
    from .image_proxy import session_images
    from .session_artwork import PATH

    if admission is None or turn.reply_source_authority is None:
        return None
    manager,session_id,item_id=admission
    owner=turn.scope.removeprefix('profile:')
    remaining=(turn.speech_deadline or 0)-turn.history.dialogue.clock()
    if remaining<=0:
        return None
    deadline=time.monotonic()+min(remaining,60)
    registry=session_images(hass)
    def authority():
        from .profile_context import profile_storage
        from .profile_privacy import resolve_profile_privacy_policy
        active=manager.current_active(owner)
        profile=profile_storage(hass).household.profiles.get(owner)
        same_scope=(active is None if not session_id else active is not None
                    and active.session_id==session_id and active.broadcast.state.playback.item_id==item_id)
        return bool(not registry.closed and time.monotonic()<deadline
            and hass.data.get('djconnect',{}).get('session_runtime_manager') is manager
            and profile is not None and resolve_profile_privacy_policy(profile,{}).allow_personal_read
            and turn.reply_source_authority() and same_scope)
    async def allowed():
        if not authority():
            return False
        try:
            await turn.guard()
        except Exception:
            return False
        return authority()
    async def guard():
        if not await allowed():
            raise PermissionError('source_withdrawn')
    registry.collect()
    if not authority() or len(registry.assets)+len(registry.inflight)>=64:
        return None
    try:
        async with asyncio.timeout(4),registry.semaphore:
            await guard()
            body,mime=await _download_observed_cover(hass,sample['album_image_url'],guard,registry)
            await guard()
    except asyncio.CancelledError:
        raise
    except Exception:
        # Optional pixels do not invent another image, metadata source or retry.
        return None
    asset_id=secrets.token_urlsafe(24)
    key=(owner,session_id,(('resource_scope','current_reply'),('reply_id',turn.digest)))
    asset={'body':body,'mime':mime,'deadline':deadline,'authority':authority,'allowed':allowed,
           'asset_id':asset_id,'subject':sample['uri'],'historical':False,
           'expected_source':dict(turn.reply_source_context)}
    if not registry.commit(key,asset):
        return None
    url=(PATH.format(session_id=session_id,asset_id=asset_id) if session_id else
         '/api/djconnect/v1/ask_dj/reply/image/'+asset_id)
    return {'url':url,'thumbnail_url':url,'title':sample['title'],'subtitle':sample['artist'],
            'kind':'album_art','source':'spotify','requires_device_auth':True,
            'expires_at':datetime.fromtimestamp(time.time()+max(0,deadline-time.monotonic()),UTC).isoformat(),
            'cache_policy':'no-store'}
