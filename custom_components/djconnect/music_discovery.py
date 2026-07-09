"""Music Discovery feed support for DJConnect clients."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import logging
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
DISCOVERY_RECENTLY_PLAYED_REFRESH_SECONDS = 60 * 60
DISCOVERY_ITEM_KINDS = {"track", "album", "artist", "playlist"}

_LOGGER = logging.getLogger(__name__)


async def async_handle_music_discovery_feed_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
    force_refresh: bool = False,
) -> tuple[dict[str, Any], int]:
    """Return the Music Discovery feed for the resolved Music DNA context."""
    _LOGGER.debug(
        "DJConnect Music Discovery feed request received client_type=%s device_id=%s force_refresh=%s",
        _request_client_type(data, headers),
        _request_device_id(data, headers),
        force_refresh,
    )
    runtime, payload, error = await _authorized_payload(hass, data, headers)
    if error:
        _log_error_response("feed", error)
        return error
    context = await _music_dna_context(runtime, payload, user_id=user_id)
    if not _music_dna_enabled(context):
        response = _disabled("music_dna_disabled", context)
        _LOGGER.debug(
            "DJConnect Music Discovery feed disabled reason=music_dna_disabled client_type=%s device_id=%s music_dna_key_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            payload.get(CONF_DEVICE_ID),
            bool(context.get("music_dna_key")),
        )
        return response, 200
    refreshed_recently_played = await _refresh_recently_played_if_stale(
        hass,
        runtime,
        payload,
        user_id=user_id,
    )
    if refreshed_recently_played:
        context = await _music_dna_context(runtime, payload, user_id=user_id)
    cache_key = _cache_key(context)
    cached = _cache(runtime).get(cache_key)
    now = _now()
    if not force_refresh and not refreshed_recently_played and _cache_valid(cached, now):
        response = dict(cached["response"])
        response["cache"] = {"hit": True}
        _LOGGER.debug(
            "DJConnect Music Discovery feed cache hit client_type=%s device_id=%s sections=%s items=%s revision=%s",
            payload.get(CONF_CLIENT_TYPE),
            payload.get(CONF_DEVICE_ID),
            len(response.get("sections") or []),
            _section_item_count(response.get("sections")),
            response.get("revision"),
        )
        return response, 200
    response = await _build_feed(hass, runtime, context, payload)
    _cache(runtime)[cache_key] = {
        "generated_at": now,
        "response": response,
    }
    _LOGGER.debug(
        "DJConnect Music Discovery feed built client_type=%s device_id=%s sections=%s items=%s revision=%s cache_hit=False",
        payload.get(CONF_CLIENT_TYPE),
        payload.get(CONF_DEVICE_ID),
        len(response.get("sections") or []),
        _section_item_count(response.get("sections")),
        response.get("revision"),
    )
    return response, 200


async def async_music_discovery_feed_tool(
    runtime: Any,
    params: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Return the Music Discovery feed for an already-authorized AI tool context."""
    payload = dict(params or {})
    context = await _music_dna_context(runtime, payload, user_id=user_id)
    if not _music_dna_enabled(context):
        return _disabled("music_dna_disabled", context)
    cache_key = _cache_key(context)
    cached = _cache(runtime).get(cache_key)
    now = _now()
    if _cache_valid(cached, now):
        response = dict(cached["response"])
        response["cache"] = {"hit": True}
    else:
        response = await _build_feed(None, runtime, context, payload)
        _cache(runtime)[cache_key] = {
            "generated_at": now,
            "response": response,
        }
    limit = _tool_limit(payload)
    if limit:
        response = _limit_feed_items(response, limit)
    return response


async def async_handle_music_discovery_refresh_payload(
    hass: Any,
    data: dict[str, Any],
    *,
    headers: Any | None = None,
    user_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Force-refresh the Music Discovery feed with a small server-side rate limit."""
    _LOGGER.debug(
        "DJConnect Music Discovery refresh request received client_type=%s device_id=%s",
        _request_client_type(data, headers),
        _request_device_id(data, headers),
    )
    runtime, payload, error = await _authorized_payload(hass, data, headers)
    if error:
        _log_error_response("refresh", error)
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
            _LOGGER.debug(
                "DJConnect Music Discovery refresh rate-limited client_type=%s device_id=%s sections=%s items=%s revision=%s",
                payload.get(CONF_CLIENT_TYPE),
                payload.get(CONF_DEVICE_ID),
                len(response.get("sections") or []),
                _section_item_count(response.get("sections")),
                response.get("revision"),
            )
            return response, 200
    setattr(runtime, "music_discovery_last_refresh", now_monotonic)
    _LOGGER.debug(
        "DJConnect Music Discovery refresh accepted client_type=%s device_id=%s",
        payload.get(CONF_CLIENT_TYPE),
        payload.get(CONF_DEVICE_ID),
    )
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
    _LOGGER.debug(
        "DJConnect Music Discovery play request received client_type=%s device_id=%s item_id_present=%s section_id_present=%s",
        _request_client_type(data, headers),
        _request_device_id(data, headers),
        bool(str((data or {}).get("discovery_item_id") or (data or {}).get("item_id") or "").strip()),
        bool(str((data or {}).get("section_id") or "").strip()),
    )
    runtime, payload, error = await _authorized_payload(hass, data, headers)
    if error:
        _log_error_response("play", error)
        return error
    context = await _music_dna_context(runtime, payload, user_id=user_id)
    if not _music_dna_enabled(context):
        response = _disabled("music_dna_disabled", context)
        _LOGGER.debug(
            "DJConnect Music Discovery play disabled reason=music_dna_disabled client_type=%s device_id=%s",
            payload.get(CONF_CLIENT_TYPE),
            payload.get(CONF_DEVICE_ID),
        )
        return response, 200
    item_id = str(payload.get("discovery_item_id") or payload.get("item_id") or "").strip()
    section_id = str(payload.get("section_id") or "").strip()
    item = _find_cached_item(runtime, context, item_id, section_id)
    if not item:
        _LOGGER.debug(
            "DJConnect Music Discovery play failed reason=discovery_item_not_found client_type=%s device_id=%s section_id_present=%s item_id_present=%s",
            payload.get(CONF_CLIENT_TYPE),
            payload.get(CONF_DEVICE_ID),
            bool(section_id),
            bool(item_id),
        )
        return {"success": False, "error": "discovery_item_not_found", "message": "Discovery item is no longer available."}, 404
    uri = str(item.get("uri") or "").strip()
    if not uri:
        _LOGGER.debug(
            "DJConnect Music Discovery play failed reason=discovery_item_not_playable client_type=%s device_id=%s item_kind=%s",
            payload.get(CONF_CLIENT_TYPE),
            payload.get(CONF_DEVICE_ID),
            item.get("kind"),
        )
        return {"success": False, "error": "discovery_item_not_playable", "message": "Discovery item cannot be played."}, 400
    kind = str(item.get("kind") or "").strip()
    command = "play_uris" if kind == "track" else "play_context_at"
    value: Any = {"uris": [uri]} if kind == "track" else {"context_uri": uri}
    playback = await run_music_command(hass, runtime, command, value, play=True)
    recorded = await _record_discovery_play(runtime, item, payload, user_id=user_id)
    _LOGGER.debug(
        "DJConnect Music Discovery play completed client_type=%s device_id=%s item_kind=%s playback_success=%s feedback_recorded=%s",
        payload.get(CONF_CLIENT_TYPE),
        payload.get(CONF_DEVICE_ID),
        kind,
        bool(playback.get("success", True)) if isinstance(playback, dict) else True,
        recorded,
    )
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
    payload = _metadata_payload(data or {}, headers)
    identity = identity_payload(payload)
    runtime = resolve_runtime(
        hass,
        identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID) or headers.get("X-DJConnect-Device-ID"),
        headers,
    )
    if runtime is None:
        _LOGGER.debug(
            "DJConnect Music Discovery auth failed reason=not_configured client_type=%s device_id=%s",
            identity.get(CONF_CLIENT_TYPE) or payload.get(CONF_CLIENT_TYPE),
            identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID),
        )
        return None, payload, ({"success": False, "enabled": False, "reason": "not_configured", "sections": []}, 503)
    client_type = validate_required_client_type(identity or payload)
    if client_type is None:
        _LOGGER.debug(
            "DJConnect Music Discovery auth failed reason=invalid_client_type device_id=%s",
            identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID),
        )
        return runtime, payload, ({"success": False, "enabled": False, "reason": "invalid_client_type", "sections": []}, 400)
    expected = str(runtime_client_type(runtime) or "").strip()
    if expected and expected != client_type:
        _LOGGER.debug(
            "DJConnect Music Discovery auth failed reason=client_type_mismatch expected=%s actual=%s device_id=%s",
            expected,
            client_type,
            identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID),
        )
        return runtime, payload, ({"success": False, "enabled": False, "reason": "client_type_mismatch", "sections": []}, 400)
    if not authorize_runtime_device_request(
        runtime,
        headers,
        identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID),
        client_type,
    ):
        _LOGGER.debug(
            "DJConnect Music Discovery auth failed reason=unauthorized client_type=%s device_id=%s authorization_present=%s",
            client_type,
            identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID),
            bool(headers.get("Authorization") if hasattr(headers, "get") else None),
        )
        return runtime, payload, ({"success": False, "enabled": False, "reason": "unauthorized", "sections": []}, 401)
    payload.setdefault(CONF_CLIENT_TYPE, client_type)
    payload.setdefault(CONF_DEVICE_ID, identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID))
    return runtime, payload, None


def _request_client_type(data: dict[str, Any] | None, headers: Any | None) -> str:
    payload = data or {}
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    header_value = headers.get("X-DJConnect-Client-Type") if hasattr(headers, "get") else ""
    return str(identity.get(CONF_CLIENT_TYPE) or payload.get(CONF_CLIENT_TYPE) or header_value or "").strip()


def _request_device_id(data: dict[str, Any] | None, headers: Any | None) -> str:
    payload = data or {}
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    header_value = headers.get("X-DJConnect-Device-ID") if hasattr(headers, "get") else ""
    return str(identity.get(CONF_DEVICE_ID) or payload.get(CONF_DEVICE_ID) or header_value or "").strip()


def _log_error_response(route: str, error: tuple[dict[str, Any], int]) -> None:
    body, status = error
    _LOGGER.debug(
        "DJConnect Music Discovery %s rejected status=%s reason=%s",
        route,
        status,
        body.get("reason") or body.get("error"),
    )


def _section_item_count(sections: Any) -> int:
    if not isinstance(sections, list):
        return 0
    return sum(len(section.get("items") or []) for section in sections if isinstance(section, dict))


def _tool_limit(payload: dict[str, Any]) -> int:
    try:
        return max(0, min(int(payload.get("limit") or 0), 24))
    except (TypeError, ValueError):
        return 0


def _limit_feed_items(response: dict[str, Any], limit: int) -> dict[str, Any]:
    if limit <= 0:
        return response
    result = dict(response)
    remaining = limit
    sections: list[dict[str, Any]] = []
    for section in response.get("sections") or []:
        if not isinstance(section, dict) or remaining <= 0:
            continue
        items = section.get("items") if isinstance(section.get("items"), list) else []
        selected = items[:remaining]
        if selected:
            sections.append({**section, "items": selected})
            remaining -= len(selected)
    result["sections"] = sections
    return result


def _metadata_payload(data: dict[str, Any], headers: Any) -> dict[str, Any]:
    """Merge request payload with DJConnect client identity headers."""
    payload = dict(data)
    for header_name, payload_key in (
        ("X-DJConnect-Device-ID", CONF_DEVICE_ID),
        ("X-DJConnect-Client-Type", CONF_CLIENT_TYPE),
        ("X-DJConnect-Client-ID", "client_id"),
        ("X-DJConnect-Device-Name", "device_name"),
        ("X-DJConnect-App-Version", "app_version"),
        ("X-DJConnect-App-Build", "app_build"),
        ("X-DJConnect-Language", "language"),
        ("X-DJConnect-Locale", "locale"),
        ("Accept-Language", "locale"),
        ("X-DJConnect-Timezone", "timezone"),
    ):
        value = headers.get(header_name) if hasattr(headers, "get") else None
        if value and not payload.get(payload_key):
            payload[payload_key] = str(value).split(",", 1)[0].strip()
    return payload


async def _music_dna_context(runtime: Any, payload: dict[str, Any], *, user_id: str | None) -> dict[str, Any]:
    memory = getattr(runtime, "memory", None)
    if memory is None:
        return {"music_dna_key": payload.get("music_dna_key"), "memory": {"enabled": False}}
    return await memory.async_context_for_runtime(runtime, payload, user_id=user_id)


def _music_dna_enabled(context: dict[str, Any]) -> bool:
    memory = context.get("memory") if isinstance(context, dict) else {}
    return bool(isinstance(memory, dict) and memory.get("enabled"))


async def _refresh_recently_played_if_stale(
    hass: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_id: str | None,
) -> bool:
    """Refresh Music DNA from backend recent history without mutating playback."""
    memory = getattr(runtime, "memory", None)
    freshness = getattr(memory, "async_listening_profile_is_fresh", None)
    updater = getattr(memory, "async_update_listening_profile", None)
    if not callable(freshness) or not callable(updater):
        return False
    try:
        if await freshness(
            runtime,
            payload,
            user_id=user_id,
            ttl_seconds=DISCOVERY_RECENTLY_PLAYED_REFRESH_SECONDS,
        ):
            return False
        result = await run_music_command(
            hass,
            runtime,
            "recently_played",
            {"limit": 50},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug(
            "DJConnect Music Discovery recently played refresh skipped: %s",
            exc.__class__.__name__,
        )
        return False
    tracks = result.get("tracks") if isinstance(result, dict) else []
    if not isinstance(tracks, list) or not tracks:
        return False
    await updater(
        runtime,
        {
            "source": "spotify",
            "recent_tracks": tracks[:50],
            "recent_track_ids": [
                str(track.get("id") or "").strip()
                for track in tracks
                if isinstance(track, dict) and str(track.get("id") or "").strip()
            ][:50],
            "recent_artists": _unique_text_values(
                track.get("artist")
                for track in tracks
                if isinstance(track, dict)
            )[:25],
            "sources": ["spotify_recently_played"],
            "last_profile_refresh": _now().isoformat(),
        },
        payload,
        user_id=user_id,
    )
    _LOGGER.debug(
        "DJConnect Music Discovery refreshed recently played profile tracks=%s client_type=%s device_id=%s",
        len(tracks[:50]),
        payload.get(CONF_CLIENT_TYPE),
        payload.get(CONF_DEVICE_ID),
    )
    return True


def _disabled(reason: str, context: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "enabled": False,
        "reason": reason,
        "music_dna_key": context.get("music_dna_key"),
        "sections": [],
    }


async def _build_feed(hass: Any, runtime: Any, context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    memory = context.get("memory") if isinstance(context.get("memory"), dict) else {}
    profile = _profile_from_memory(memory)
    sections = [
        section
        for section in [
            await _new_music_section(hass, runtime, profile),
            *_sections_from_profile(profile),
        ]
        if section.get("items")
    ]
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
    listening = memory.get("listening_profile") if isinstance(memory.get("listening_profile"), dict) else {}
    return {
        "favorite_genres": _texts(memory.get("favorite_genres")),
        "favorite_artists": _artist_names(memory.get("favorite_artists")),
        "recent_tracks": [item for item in memory.get("recent_tracks") or [] if isinstance(item, dict)],
        "recent_favorite_tracks": [item for item in memory.get("recent_favorite_tracks") or [] if isinstance(item, dict)],
        "recommendation_plays": [item for item in memory.get("recommendation_plays") or [] if isinstance(item, dict)],
        "top_tracks_by_range": listening.get("top_tracks_by_range") if isinstance(listening.get("top_tracks_by_range"), dict) else {},
        "top_artists_by_range": listening.get("top_artists_by_range") if isinstance(listening.get("top_artists_by_range"), dict) else {},
        "taste_anchors": _texts(memory.get("favorite_genres"))[:3] + _artist_names(memory.get("favorite_artists"))[:3],
    }


def _sections_from_profile(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "accepted_recommendations",
            "title": "Meer zoals je eerdere keuzes",
            "items": _items_from_recommendations(profile.get("recommendation_plays") or [], limit=6),
        },
    ]


async def _new_music_section(hass: Any, runtime: Any, profile: dict[str, Any]) -> dict[str, Any]:
    if hass is None:
        return {"id": "new_for_you", "title": "Nieuw voor jou", "items": []}
    seeds = _recommendation_seeds(profile)
    if not any(seeds.values()):
        return {"id": "new_for_you", "title": "Nieuw voor jou", "items": []}
    try:
        result = await run_music_command(
            hass,
            runtime,
            "artist_recommendations",
            {**seeds, "limit": 12},
        )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Music Discovery recommendations unavailable: %s", exc.__class__.__name__)
        return {"id": "new_for_you", "title": "Nieuw voor jou", "items": []}
    tracks = result.get("recommended_tracks") or result.get("tracks") if isinstance(result, dict) else []
    items = _items_from_recommended_tracks(
        tracks if isinstance(tracks, list) else [],
        excluded_uris=_known_track_uris(profile),
        limit=6,
    )
    return {
        "id": "new_for_you",
        "title": "Nieuw voor jou",
        "items": items,
    }


def _recommendation_seeds(profile: dict[str, Any]) -> dict[str, list[str]]:
    tracks: list[str] = []
    for source in (
        profile.get("recent_favorite_tracks") or [],
        profile.get("recommendation_plays") or [],
        _range_items(profile.get("top_tracks_by_range")),
        profile.get("recent_tracks") or [],
    ):
        for item in source if isinstance(source, list) else []:
            if not isinstance(item, dict):
                continue
            uri = _first_text(item, "uri", "context_uri")
            title = _first_text(item, "title", "track_name", "name")
            artist = _first_text(item, "artist", "artist_name", "subtitle")
            value = uri if uri.startswith("spotify:track:") else " ".join(part for part in (title, artist) if part)
            if value and value not in tracks:
                tracks.append(value)
            if len(tracks) >= 3:
                break
        if len(tracks) >= 3:
            break
    artists = _unique_text_values(
        [
            *profile.get("favorite_artists", []),
            *[
                _first_text(item, "name", "artist", "artist_name")
                for item in _range_items(profile.get("top_artists_by_range"))
                if isinstance(item, dict)
            ],
        ]
    )[:2]
    genres = _unique_text_values(profile.get("favorite_genres") or [])[:2]
    return {"tracks": tracks[:3], "artists": artists, "genres": genres}


def _range_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    items: list[dict[str, Any]] = []
    for range_name in ("short_term", "medium_term", "long_term"):
        values = value.get(range_name)
        if isinstance(values, list):
            items.extend(item for item in values if isinstance(item, dict))
    return items


def _known_track_uris(profile: dict[str, Any]) -> set[str]:
    uris: set[str] = set()
    for source in (
        profile.get("recent_tracks") or [],
        profile.get("recent_favorite_tracks") or [],
        profile.get("recommendation_plays") or [],
        _range_items(profile.get("top_tracks_by_range")),
    ):
        for item in source if isinstance(source, list) else []:
            if isinstance(item, dict):
                uri = _first_text(item, "uri", "context_uri").lower()
                if uri:
                    uris.add(uri)
    return uris


def _items_from_recommended_tracks(
    tracks: list[dict[str, Any]],
    *,
    excluded_uris: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for track in tracks:
        uri = _first_text(track, "uri", "context_uri")
        if not uri or uri.lower() in excluded_uris or uri.lower() in seen:
            continue
        title = _first_text(track, "title", "track_name", "name")
        artist = _first_text(track, "artist", "artist_name", "subtitle")
        if not title:
            continue
        seen.add(uri.lower())
        items.append(
            _item(
                "track",
                title,
                artist,
                uri,
                "Nieuwe aanbeveling op basis van je Music DNA en Spotify luisterprofiel.",
                ["spotify_recommendations", "djconnect_music_dna"],
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
    item_id = (
        "disc-"
        + hashlib.sha1(
            "|".join((kind, uri, title)).encode(), usedforsecurity=False
        ).hexdigest()[:16]
    )
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


def _unique_text_values(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _artist_names(values: Any) -> list[str]:
    return _texts(values)
