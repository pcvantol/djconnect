"""Music Discovery feed support for DJConnect clients."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any

from .const import CONF_CLIENT_TYPE, CONF_DEVICE_ID
from .request_auth import (
    authorize_runtime_device_request,
    identity_payload,
    resolve_runtime,
    runtime_client_type,
    validate_required_client_type,
)
from .use_cases import run_music_command

DISCOVERY_TTL_SECONDS = 24 * 60 * 60
DISCOVERY_REFRESH_MIN_SECONDS = 5 * 60
DISCOVERY_ITEM_KINDS = {"track", "album", "artist", "playlist"}


async def async_handle_music_discovery_feed_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
    force_refresh: bool = False,
) -> tuple[dict[str, Any], int]:
    """Return the Music Discovery feed for the resolved Music DNA context."""
    runtime, payload, error = await _authorized_payload(hass, data, headers)
    if error:
        return error
    context = await _music_dna_context(runtime, payload, user_id=user_id)
    if not _music_dna_enabled(context):
        return _disabled("music_dna_disabled", context), 200
    cache_key = _cache_key(context)
    cached = _cache(runtime).get(cache_key)
    now = _now()
    if not force_refresh and _cache_valid(cached, now):
        response = dict(cached["response"])
        response["cache"] = {"hit": True}
        return response, 200
    response = _build_feed(runtime, context, payload)
    _cache(runtime)[cache_key] = {
        "generated_at": now,
        "response": response,
    }
    return response, 200


async def async_handle_music_discovery_refresh_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Force-refresh the Music Discovery feed with a small server-side rate limit."""
    runtime, payload, error = await _authorized_payload(hass, data, headers)
    if error:
        return error
    last_refresh = float(getattr(runtime, "music_discovery_last_refresh", 0) or 0)
    now_monotonic = __import__("time").monotonic()
    if now_monotonic - last_refresh < DISCOVERY_REFRESH_MIN_SECONDS:
        context = await _music_dna_context(runtime, payload, user_id=user_id)
        cached = _cache(runtime).get(_cache_key(context))
        if isinstance(cached, dict) and isinstance(cached.get("response"), dict):
            response = dict(cached["response"])
            response["rate_limited"] = True
            response["cache"] = {"hit": True}
            return response, 200
    setattr(runtime, "music_discovery_last_refresh", now_monotonic)
    return await async_handle_music_discovery_feed_payload(
        hass,
        payload,
        headers=headers,
        user_id=user_id,
        force_refresh=True,
    )


async def async_handle_music_discovery_play_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Play one discovery item and record the click as positive Music DNA feedback."""
    runtime, payload, error = await _authorized_payload(hass, data, headers)
    if error:
        return error
    context = await _music_dna_context(runtime, payload, user_id=user_id)
    if not _music_dna_enabled(context):
        return _disabled("music_dna_disabled", context), 200
    item_id = str(payload.get("discovery_item_id") or payload.get("item_id") or "").strip()
    section_id = str(payload.get("section_id") or "").strip()
    item = _find_cached_item(runtime, context, item_id, section_id)
    if not item:
        return {"success": False, "error": "discovery_item_not_found", "message": "Discovery item is no longer available."}, 404
    uri = str(item.get("uri") or "").strip()
    if not uri:
        return {"success": False, "error": "discovery_item_not_playable", "message": "Discovery item cannot be played."}, 400
    kind = str(item.get("kind") or "").strip()
    command = "play_uris" if kind == "track" else "play_context_at"
    value: Any = {"uris": [uri]} if kind == "track" else {"context_uri": uri}
    playback = await run_music_command(hass, runtime, command, value, play=True)
    recorded = await _record_discovery_play(runtime, item, payload, user_id=user_id)
    return {
        "success": bool(playback.get("success", True)) if isinstance(playback, dict) else True,
        "played": True,
        "playback": playback.get("playback") if isinstance(playback, dict) else {},
        "item": item,
        "music_dna_feedback_recorded": recorded,
    }, 200


async def _authorized_payload(
    hass: Any,
    data: dict[str, Any],
    headers: Any | None,
) -> tuple[Any | None, dict[str, Any], tuple[dict[str, Any], int] | None]:
    headers = headers or {}
    payload = dict(data or {})
    identity = identity_payload(payload)
    runtime = resolve_runtime(
        hass,
        identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID) or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        return None, payload, ({"success": False, "enabled": False, "reason": "not_configured", "sections": []}, 503)
    client_type = validate_required_client_type(identity or payload)
    if client_type is None:
        return runtime, payload, ({"success": False, "enabled": False, "reason": "invalid_client_type", "sections": []}, 400)
    expected = str(runtime_client_type(runtime) or "").strip()
    if expected and expected != client_type:
        return runtime, payload, ({"success": False, "enabled": False, "reason": "client_type_mismatch", "sections": []}, 400)
    if not authorize_runtime_device_request(
        runtime,
        headers,
        identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID),
        client_type,
    ):
        return runtime, payload, ({"success": False, "enabled": False, "reason": "unauthorized", "sections": []}, 401)
    payload.setdefault(CONF_CLIENT_TYPE, client_type)
    payload.setdefault(CONF_DEVICE_ID, identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID))
    return runtime, payload, None


async def _music_dna_context(runtime: Any, payload: dict[str, Any], *, user_id: str | None) -> dict[str, Any]:
    memory = getattr(runtime, "memory", None)
    if memory is None:
        return {"music_dna_key": payload.get("music_dna_key"), "memory": {"enabled": False}}
    return await memory.async_context_for_runtime(runtime, payload, user_id=user_id)


def _music_dna_enabled(context: dict[str, Any]) -> bool:
    memory = context.get("memory") if isinstance(context, dict) else {}
    return bool(isinstance(memory, dict) and memory.get("enabled"))


def _disabled(reason: str, context: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "enabled": False,
        "reason": reason,
        "music_dna_key": context.get("music_dna_key"),
        "sections": [],
    }


def _build_feed(runtime: Any, context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    memory = context.get("memory") if isinstance(context.get("memory"), dict) else {}
    profile = _profile_from_memory(memory)
    sections = [section for section in _sections_from_profile(profile) if section.get("items")]
    revision = int(getattr(runtime, "music_discovery_revision", 0) or 0) + 1
    setattr(runtime, "music_discovery_revision", revision)
    generated_at = _now().isoformat()
    return {
        "success": True,
        "enabled": True,
        "revision": revision,
        "generated_at": generated_at,
        "ttl_seconds": DISCOVERY_TTL_SECONDS,
        "source": "music_dna",
        "music_dna_key": context.get("music_dna_key"),
        "sections": sections,
        "cache": {"hit": False},
    }


def _profile_from_memory(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "favorite_genres": _texts(memory.get("favorite_genres")),
        "favorite_artists": _artist_names(memory.get("favorite_artists")),
        "recent_tracks": [item for item in memory.get("recent_tracks") or [] if isinstance(item, dict)],
        "recent_favorite_tracks": [item for item in memory.get("recent_favorite_tracks") or [] if isinstance(item, dict)],
        "recommendation_plays": [item for item in memory.get("recommendation_plays") or [] if isinstance(item, dict)],
        "taste_anchors": _texts(memory.get("favorite_genres"))[:3] + _artist_names(memory.get("favorite_artists"))[:3],
    }


def _sections_from_profile(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "because_you_like",
            "title": "Omdat dit bij je smaak past",
            "items": _items_from_tracks(
                profile.get("recent_tracks") or [],
                reason="Past bij je Music DNA smaakankers.",
                reason_sources=["taste_anchors", "recent_tracks"],
                limit=6,
            ),
        },
        {
            "id": "recent_vibe",
            "title": "Verder in je recente vibe",
            "items": _items_from_tracks(
                profile.get("recent_favorite_tracks") or [],
                reason="Gebaseerd op muziek die je recent aan favorieten toevoegde.",
                reason_sources=["explicit_positives", "recent_favorite_tracks"],
                limit=6,
            ),
        },
        {
            "id": "accepted_recommendations",
            "title": "Meer zoals je eerdere keuzes",
            "items": _items_from_recommendations(profile.get("recommendation_plays") or [], limit=6),
        },
    ]


def _items_from_tracks(
    tracks: list[dict[str, Any]],
    *,
    reason: str,
    reason_sources: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for track in tracks:
        title = _first_text(track, "title", "track_name", "name")
        artist = _first_text(track, "artist", "artist_name", "subtitle")
        uri = _first_text(track, "uri", "context_uri")
        if not (title and uri):
            continue
        items.append(
            _item(
                "track",
                title,
                artist,
                uri,
                reason,
                reason_sources,
                image_url=_first_text(track, "image_url", "album_image_url", "thumbnail_url"),
            )
        )
        if len(items) >= limit:
            break
    return items


def _items_from_recommendations(recommendations: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for value in recommendations:
        title = _first_text(value, "title", "name")
        subtitle = _first_text(value, "subtitle", "artist", "artist_name")
        uri = _first_text(value, "uri", "context_uri")
        kind = _kind_from_uri(uri) or str(value.get("kind") or "track").strip()
        reason = _first_text(value, "reason") or "Gebaseerd op eerdere Ontdek- en Ask DJ-keuzes."
        if not (title and uri and kind in DISCOVERY_ITEM_KINDS):
            continue
        items.append(
            _item(
                kind,
                title,
                subtitle,
                uri,
                reason,
                ["explicit_positives", "accepted_recommendations"],
                image_url=_first_text(value, "image_url", "album_image_url", "thumbnail_url"),
            )
        )
        if len(items) >= limit:
            break
    return items


def _item(
    kind: str,
    title: str,
    subtitle: str,
    uri: str,
    reason: str,
    reason_sources: list[str],
    *,
    image_url: str = "",
) -> dict[str, Any]:
    item_id = "disc-" + hashlib.sha1("|".join((kind, uri, title)).encode()).hexdigest()[:16]
    return {
        "id": item_id,
        "kind": kind,
        "title": title,
        "subtitle": subtitle,
        "uri": uri,
        **({"image_url": image_url} if image_url else {}),
        "reason": reason,
        "reason_sources": reason_sources,
        "confidence": "medium",
    }


def _find_cached_item(runtime: Any, context: dict[str, Any], item_id: str, section_id: str) -> dict[str, Any]:
    cached = _cache(runtime).get(_cache_key(context))
    response = cached.get("response") if isinstance(cached, dict) else {}
    for section in response.get("sections") or []:
        if section_id and section.get("id") != section_id:
            continue
        for item in section.get("items") or []:
            if item.get("id") == item_id:
                return dict(item)
    return {}


async def _record_discovery_play(
    runtime: Any,
    item: dict[str, Any],
    payload: dict[str, Any],
    *,
    user_id: str | None,
) -> bool:
    memory = getattr(runtime, "memory", None)
    recorder = getattr(memory, "async_record_discovery_play", None)
    if not callable(recorder):
        return False
    await recorder(runtime, item, payload, user_id=user_id)
    return True


def _cache(runtime: Any) -> dict[str, Any]:
    cache = getattr(runtime, "music_discovery_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(runtime, "music_discovery_cache", cache)
    return cache


def _cache_key(context: dict[str, Any]) -> str:
    return str(context.get("music_dna_key") or "default")


def _cache_valid(cached: Any, now: datetime) -> bool:
    if not isinstance(cached, dict) or not isinstance(cached.get("response"), dict):
        return False
    generated_at = cached.get("generated_at")
    return isinstance(generated_at, datetime) and now - generated_at < timedelta(seconds=DISCOVERY_TTL_SECONDS)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _kind_from_uri(uri: str) -> str:
    if uri.startswith("spotify:"):
        parts = uri.split(":")
        if len(parts) >= 3 and parts[1] in DISCOVERY_ITEM_KINDS:
            return parts[1]
    return ""


def _first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _texts(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value.get("name") if isinstance(value, dict) else value).strip() for value in values if value]


def _artist_names(values: Any) -> list[str]:
    return _texts(values)
