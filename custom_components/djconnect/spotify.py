from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import CONF_LIKED_PROXY, CONF_SPOTIFY_SOURCE
from .music_intent import clean_music_query, extract_artist_query, parse_spoken_music_request
from .spotify_backend import handle_spotify_command

MEDIA_CONTENT_TYPES = {
    "artist": "artist",
    "album": "album",
    "track": "track",
    "search": "artist",
    "music": "artist",
    "playlist": "playlist",
}


async def play_from_intent(
    hass: HomeAssistant,
    runtime: Any,
    intent: dict[str, Any],
    conf: dict[str, Any],
) -> dict[str, Any]:
    source = (conf.get(CONF_SPOTIFY_SOURCE) or "").strip()
    if source:
        await handle_spotify_command(hass, runtime, "set_output", source, play=False)

    media_content_id, media_content_type = _media_from_intent(intent, conf)

    if not media_content_id:
        raise RuntimeError("Could not determine a Spotify search query")

    command = "start_playlist" if media_content_type == "playlist" else "play"
    if media_content_type == "artist":
        command = "play_artist_top_tracks"
    value: Any = media_content_id
    if command == "play" and not media_content_id.startswith("spotify:"):
        value = {"query": media_content_id, "type": media_content_type}
    if command == "play_artist_top_tracks":
        value = {"query": media_content_id}
    response = await handle_spotify_command(
        hass,
        runtime,
        command,
        value,
    )
    resolved_media = _fresh_resolved_media(runtime, media_content_id)

    return {
        "played": True,
        "source": source,
        "media_content_id": media_content_id,
        "media_content_type": media_content_type,
        "resolved_media": resolved_media,
        "device_response": response,
    }


def _fresh_resolved_media(
    runtime: Any,
    query: str,
) -> dict[str, Any] | None:
    """Return media resolved by the command that just ran, not stale playback."""
    search = getattr(runtime, "last_spotify_search", None)
    if isinstance(search, dict) and str(search.get("query") or "").strip() == str(query).strip():
        selected = search.get("selected")
        if isinstance(selected, dict) and selected:
            return selected
    return None


def _media_from_intent(
    intent: dict[str, Any],
    conf: dict[str, Any],
) -> tuple[str, str]:
    media_type = (intent.get("type") or "search").lower()
    media_content_id = (
        intent.get("spotify_search_query") or intent.get("query") or ""
    ).strip()

    if media_type == "liked":
        return _liked_proxy_media(conf)
    if media_type == "playlist":
        return (intent.get("playlist") or media_content_id).strip(), "playlist"
    if media_type == "track":
        return _track_media(intent, media_content_id)
    if media_type == "album":
        return _album_media(intent, media_content_id)
    if media_type == "latest_album":
        return _artist_media(intent, media_content_id)
    if media_type in {"search", "music"}:
        if intent.get("artist"):
            return _artist_media(intent, media_content_id)
        if intent.get("playlist"):
            return str(intent.get("playlist") or "").strip(), "playlist"
        if intent.get("title") or intent.get("track"):
            return _track_media(intent, media_content_id)
        if intent.get("album"):
            return _album_media(intent, media_content_id)
        parsed = parse_spoken_music_request(media_content_id)
        parsed_type = str(parsed.get("type") or "artist")
        if parsed_type == "liked":
            return _liked_proxy_media(conf)
        if parsed_type == "playlist":
            return str(parsed.get("query") or "").strip(), "playlist"
        if parsed_type == "track":
            return str(parsed.get("query") or "").strip(), "track"
        if parsed_type == "album":
            return str(parsed.get("query") or "").strip(), "album"
        return str(parsed.get("query") or "").strip(), "artist"
    if media_type == "artist":
        return _artist_media(intent, media_content_id)
    return media_content_id, MEDIA_CONTENT_TYPES.get(media_type, "music")


def _liked_proxy_media(conf: dict[str, Any]) -> tuple[str, str]:
    proxy = (conf.get(CONF_LIKED_PROXY) or "").strip()
    if not proxy:
        raise RuntimeError("Liked songs require a default playlist URI")
    return proxy, "playlist"


def _artist_media(
    intent: dict[str, Any],
    fallback_query: str,
) -> tuple[str, str]:
    artist = (intent.get("artist") or "").strip()
    query = artist if artist else extract_artist_query(fallback_query)
    return query, "artist"


def _track_media(
    intent: dict[str, Any],
    fallback_query: str,
) -> tuple[str, str]:
    title = clean_music_query(intent.get("title") or intent.get("track") or "")
    artist = clean_music_query(intent.get("artist") or "")
    query = _query_with_artist(title, artist) if title else clean_music_query(fallback_query)
    return query, "track"


def _album_media(
    intent: dict[str, Any],
    fallback_query: str,
) -> tuple[str, str]:
    album = clean_music_query(intent.get("album") or intent.get("title") or "")
    artist = clean_music_query(intent.get("artist") or "")
    query = _query_with_artist(album, artist) if album else clean_music_query(fallback_query)
    return query, "album"


def _query_with_artist(title: str, artist: str) -> str:
    return f"{title} {artist}".strip() if artist else title
