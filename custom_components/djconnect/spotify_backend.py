from __future__ import annotations

import asyncio
import time
import logging
import re
from urllib.parse import urlencode
from typing import Any

from aiohttp import ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .ambient_ask_dj import async_maybe_append_ambient_fact
from .const import (
    CONF_LIKED_PROXY,
    CONF_SPOTIFY_CLIENT_ID,
    CONF_SPOTIFY_REFRESH_TOKEN,
    CONF_SPOTIFY_SOURCE,
    DOMAIN,
    DEFAULT_SPOTIFY_MARKET,
)
from .spotify_oauth import SpotifyTokenRefreshError, refresh_access_token

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
CACHE_TTL_SECONDS = 30
LISTENING_PROFILE_CACHE_TTL_SECONDS = 6 * 60 * 60
ACCESS_TOKEN_EXPIRY_SAFETY_SECONDS = 60
MAX_QUEUE_ITEMS = 100
MAX_PLAYLIST_ITEMS = 100
SPOTIFY_PLAYLIST_PAGE_LIMIT = 50
DEFAULT_PLAYLIST_LIMIT = 100
ESP_DEFAULT_PLAYLIST_LIMIT = 20
ARTIST_QUERY_ALIASES = {
    "paul van dijk": "Paul van Dyk",
    "paul van dyke": "Paul van Dyk",
}
_LOGGER = logging.getLogger(__name__)


class SpotifyBackendError(RuntimeError):
    """Raised when the configured Spotify backend cannot serve a command."""


class SpotifyReauthRequiredError(SpotifyBackendError):
    """Raised when Spotify revoked the stored OAuth refresh token."""


async def handle_spotify_command(
    hass: HomeAssistant,
    runtime: Any,
    command: str,
    value: Any = None,
    *,
    play: bool | None = None,
) -> dict[str, Any]:
    """Handle a generic DJConnect playback command using HA-stored credentials."""
    backend = SpotifyBackend(hass, runtime)
    normalized = str(command or "").strip().lower()
    _LOGGER.debug("DJConnect Spotify backend handling command: %s", normalized)
    if normalized == "status":
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "devices":
        return {"success": True, "devices": await backend.devices()}
    if normalized == "queue":
        return {"success": True, **await backend.queue()}
    if normalized == "playlists":
        limit = _playlist_limit(value)
        playlists = await backend.playlists(limit=limit)
        _LOGGER.debug(
            "DJConnect Spotify playlists resolved client_type=%s limit=%s count=%s",
            _playlist_client_type(value) or "unknown",
            limit,
            len(playlists),
        )
        return {
            "success": True,
            "backend_available": True,
            "playlists": playlists,
            "items": playlists,
            "data": {"playlists": playlists, "items": playlists},
            "result": {"playlists": playlists, "items": playlists},
            "count": len(playlists),
        }
    if normalized == "search_playlists":
        playlists = await backend.search_playlists(
            _search_query(value),
            limit=_search_limit(value, default=5, maximum=10),
        )
        return {
            "success": True,
            "backend_available": True,
            "playlists": playlists,
            "items": playlists,
            "data": {"playlists": playlists, "items": playlists},
            "result": {"playlists": playlists, "items": playlists},
            "count": len(playlists),
        }
    if normalized == "search_tracks":
        tracks = await backend.search_tracks(
            _search_query(value),
            limit=_search_limit(value, default=10, maximum=10),
        )
        return {
            "success": True,
            "backend_available": True,
            "tracks": tracks,
            "items": tracks,
            "data": {"tracks": tracks, "items": tracks},
            "result": {"tracks": tracks, "items": tracks},
            "count": len(tracks),
        }
    if normalized == "search_albums":
        albums = await backend.search_albums(
            _search_query(value),
            limit=_search_limit(value, default=10, maximum=10),
        )
        return {
            "success": True,
            "backend_available": True,
            "albums": albums,
            "items": albums,
            "data": {"albums": albums, "items": albums},
            "result": {"albums": albums, "items": albums},
            "count": len(albums),
        }
    if normalized == "search_media":
        item = await backend.search_media(
            _search_query(value),
            str(value.get("type") or "track") if isinstance(value, dict) else "track",
        )
        return {"success": True, "item": item, "media": item}
    if normalized == "listening_profile":
        return {"success": True, "profile": await backend.listening_profile()}
    if normalized == "recently_played":
        limit = _search_limit(value, default=50, maximum=50)
        return {
            "success": True,
            "tracks": await backend.recently_played(limit=limit),
            "source": "spotify_recently_played",
        }
    if normalized == "technical_track_analysis":
        return {
            "success": True,
            "analysis": await backend.technical_track_analysis(value),
        }
    if normalized == "artist_recommendations":
        return {
            "success": True,
            **await backend.seed_recommendations(value),
        }
    if normalized == "create_playlist":
        return {
            "success": True,
            "playlist": await backend.create_playlist_from_tracks(value),
        }
    if normalized == "artist_albums":
        return {
            "success": True,
            **await backend.artist_albums(_artist_album_query(value)),
        }
    if normalized == "related_artists":
        return {
            "success": True,
            **await backend.related_artists(_artist_album_query(value)),
        }
    if normalized == "artist_profile":
        return {
            "success": True,
            "artist": await backend.artist_profile(_artist_album_query(value)),
        }
    if normalized == "pause":
        await backend.pause()
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "play":
        await backend.play(value)
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "play_context_at":
        await backend.play_context_at(value)
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "next":
        await backend.next()
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "previous":
        await backend.previous()
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "seek_relative":
        await backend.seek_relative(value)
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "start_liked_proxy":
        await backend.start_liked_proxy()
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "start_playlist":
        await backend.start_playlist(str(value or ""))
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "play_artist_top_tracks":
        await backend.play_artist_top_tracks(_search_query(value))
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "play_uris":
        await backend.play_uris(_track_uris(value))
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "set_shuffle":
        await backend.set_shuffle(value)
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "set_repeat":
        await backend.set_repeat(str(value or ""))
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "set_output":
        await backend.set_output(str(value or ""), play=bool(play))
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "set_volume":
        await backend.set_volume(value)
        return {"success": True, "playback": await backend.playback_state()}
    if normalized == "save_current_track":
        playback = await backend.set_current_track_favorite(True)
        return {"success": True, "playback": playback}
    if normalized in {"set_current_track_favorite", "toggle_current_track_favorite"}:
        playback = await backend.set_current_track_favorite(value)
        return {"success": True, "playback": playback}
    raise ValueError(f"Unsupported DJConnect command: {command}")


class SpotifyBackend:
    """Small Spotify Web API backend using credentials stored in Home Assistant."""

    def __init__(self, hass: HomeAssistant, runtime: Any) -> None:
        self.hass = hass
        self.runtime = runtime
        self.session = async_get_clientsession(hass)

    @property
    def conf(self) -> dict[str, Any]:
        return self.runtime.config

    async def _access_token(self, *, force_refresh: bool = False) -> str:
        client_id = str(self.conf.get(CONF_SPOTIFY_CLIENT_ID) or "").strip()
        refresh_token = _current_refresh_token(self.runtime, self.conf)
        if not client_id or not refresh_token:
            raise SpotifyBackendError("Spotify OAuth is not configured in Home Assistant")
        cached_token = getattr(self.runtime, "spotify_access_token", None)
        cached_expires_at = float(getattr(self.runtime, "spotify_access_token_expires_at", 0) or 0)
        now = time.time()
        seconds_left = int(cached_expires_at - now)
        if (
            not force_refresh
            and cached_token
            and cached_expires_at - ACCESS_TOKEN_EXPIRY_SAFETY_SECONDS > now
        ):
            _LOGGER.debug(
                "DJConnect Spotify using cached access token seconds_left=%s",
                seconds_left,
            )
            return str(cached_token)
        _LOGGER.debug(
            "DJConnect Spotify access token refresh needed force_refresh=%s "
            "cached=%s seconds_left=%s refresh_sources=%s",
            force_refresh,
            bool(cached_token),
            seconds_left if cached_token else None,
            _refresh_token_source_names(self.runtime, self.conf),
        )
        lock = _token_refresh_lock(self.runtime)
        async with lock:
            cached_token = getattr(self.runtime, "spotify_access_token", None)
            cached_expires_at = float(
                getattr(self.runtime, "spotify_access_token_expires_at", 0) or 0
            )
            now = time.time()
            seconds_left = int(cached_expires_at - now)
            if (
                not force_refresh
                and cached_token
                and cached_expires_at - ACCESS_TOKEN_EXPIRY_SAFETY_SECONDS > now
            ):
                _LOGGER.debug(
                    "DJConnect Spotify reused access token after refresh lock seconds_left=%s",
                    seconds_left,
                )
                return str(cached_token)
            refresh_token = _current_refresh_token(self.runtime, self.conf)
            if not refresh_token:
                raise SpotifyBackendError("Spotify OAuth is not configured in Home Assistant")
            return await self._refresh_access_token_locked(
                client_id=client_id,
                refresh_token=refresh_token,
            )

    async def _refresh_access_token_locked(
        self,
        *,
        client_id: str,
        refresh_token: str,
        attempted_refresh_tokens: set[str] | None = None,
    ) -> str:
        attempted_refresh_tokens = set(attempted_refresh_tokens or set())
        attempted_refresh_tokens.add(refresh_token)
        _LOGGER.debug(
            "DJConnect Spotify refresh attempt source_count=%s attempted=%s",
            len(_refresh_token_candidates(self.runtime, self.conf)),
            len(attempted_refresh_tokens),
        )
        try:
            token = await refresh_access_token(
                self.hass,
                client_id=client_id,
                refresh_token=refresh_token,
            )
        except SpotifyTokenRefreshError as exc:
            if exc.error == "invalid_grant":
                for source, latest_refresh_token in _refresh_token_candidates(
                    self.runtime,
                    self.conf,
                ):
                    if latest_refresh_token in attempted_refresh_tokens:
                        continue
                    _LOGGER.debug(
                        "DJConnect Spotify refresh_token rejected; retrying alternate stored token source=%s",
                        source,
                    )
                    return await self._refresh_access_token_locked(
                        client_id=client_id,
                        refresh_token=latest_refresh_token,
                        attempted_refresh_tokens=attempted_refresh_tokens,
                    )
                _LOGGER.warning(
                    "DJConnect Spotify refresh token rejected by Spotify; user reauthorization required"
                )
                _create_spotify_reauth_issue(
                    self.hass,
                    getattr(self.runtime, "entry", None),
                )
                message = (
                    "Spotify authorization has expired or was revoked. "
                    "Reauthorize DJConnect from the integration options or run "
                    "djconnect.start_spotify_oauth, then try again."
                )
                self.runtime.update(last_error=message)
                raise SpotifyReauthRequiredError(message) from exc
            raise SpotifyBackendError(
                f"Spotify OAuth refresh failed HTTP {exc.status}: {exc.error or 'unknown'}"
            ) from exc
        rotated = str(token.get("refresh_token") or "").strip()
        if rotated:
            updater = getattr(self.runtime, "update_spotify_refresh_token", None)
            if callable(updater) and updater(rotated):
                entry = getattr(self.runtime, "entry", None)
                if entry is not None:
                    new_data = dict(entry.data)
                    new_data[CONF_SPOTIFY_REFRESH_TOKEN] = rotated
                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                _LOGGER.debug(
                    "DJConnect Spotify refresh_token=rotated/persisted source=token_endpoint"
                )
        access_token = str(token.get("access_token") or "").strip()
        if not access_token:
            raise SpotifyBackendError("Spotify OAuth refresh did not return an access token")
        expires_in = int(token.get("expires_in") or 3600)
        self.runtime.spotify_access_token = access_token
        self.runtime.spotify_access_token_expires_at = time.time() + max(60, expires_in)
        _LOGGER.debug(
            "DJConnect Spotify access token refreshed expires_in=%s rotated_refresh_token=%s",
            expires_in,
            bool(rotated),
        )
        return access_token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        expected_empty: bool = False,
    ) -> Any:
        return await self._request_with_token(
            method,
            path,
            json=json,
            expected_empty=expected_empty,
            force_refresh=False,
            retry_on_unauthorized=True,
        )

    async def _request_with_token(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None,
        expected_empty: bool,
        force_refresh: bool,
        retry_on_unauthorized: bool,
    ) -> Any:
        token = await self._access_token(force_refresh=force_refresh)
        async with self.session.request(
            method,
            SPOTIFY_API_BASE + path,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
            timeout=ClientTimeout(total=12),
        ) as resp:
            if resp.status == 401 and retry_on_unauthorized:
                await _consume_spotify_response(resp)
                self.runtime.spotify_access_token = None
                self.runtime.spotify_access_token_expires_at = 0
                _LOGGER.debug("DJConnect Spotify access token expired; refreshing once")
                return await self._request_with_token(
                    method,
                    path,
                    json=json,
                    expected_empty=expected_empty,
                    force_refresh=True,
                    retry_on_unauthorized=False,
                )
            if resp.status == 204 or expected_empty:
                if resp.status < 200 or resp.status >= 300:
                    text = await resp.text()
                    raise SpotifyBackendError(
                        f"Spotify API failed HTTP {resp.status}: {_spotify_error_message(text)}"
                    )
                return {}
            try:
                body = await resp.json(content_type=None)
            except Exception:  # noqa: BLE001
                body = {"message": await resp.text()}
            if resp.status < 200 or resp.status >= 300:
                raise SpotifyBackendError(
                    f"Spotify API failed HTTP {resp.status}: {_spotify_error_message(body)}"
                )
            return body or {}

    async def _cached(self, key: str, loader, *, ttl: int = CACHE_TTL_SECONDS) -> Any:
        cache = getattr(self.runtime, "backend_cache", None)
        if cache is None:
            self.runtime.backend_cache = {}
            cache = self.runtime.backend_cache
        now = time.monotonic()
        cached = cache.get(key)
        if cached and now - cached[0] < ttl:
            return cached[1]
        value = await loader()
        cache[key] = (now, value)
        return value

    async def playback_state(self) -> dict[str, Any]:
        data = await self._request("GET", "/me/player")
        playback = _normalize_playback(data)
        await self._enrich_current_track_favorite_status(playback)
        _merge_playback_status(
            self.runtime.device_status,
            {
                "spotify_status": "playing" if playback.get("is_playing") else "idle",
                "volume": playback.get("volume_percent"),
                "last_track": playback.get("track_name"),
                "current_track_is_liked": playback.get("is_liked"),
                "sound_output": (playback.get("device") or {}).get("name"),
                "shuffle": playback.get("shuffle"),
                "repeat_state": playback.get("repeat_state"),
            },
        )
        self.runtime.update(last_playback=playback, last_error=None)
        await async_maybe_append_ambient_fact(self.hass, self.runtime, playback)
        return playback

    async def _enrich_current_track_favorite_status(self, playback: dict[str, Any]) -> None:
        uri = str(playback.get("uri") or playback.get("current_uri") or "").strip()
        track_id = _spotify_id_from_uri(uri)
        if not _looks_like_spotify_id(track_id):
            return
        try:
            data = await self._request("GET", f"/me/tracks/contains?ids={track_id}")
        except SpotifyBackendError as exc:
            _LOGGER.debug("DJConnect could not read current track favorite status: %s", exc)
            return
        if isinstance(data, list) and data:
            playback["is_liked"] = bool(data[0])
            playback["favorite_status"] = bool(data[0])

    async def devices(self) -> list[dict[str, Any]]:
        async def load():
            data = await self._request("GET", "/me/player/devices")
            return [_normalize_device(device) for device in data.get("devices", [])]

        devices = await self._cached("devices", load)
        self.runtime.device_status["available_outputs"] = devices
        self.runtime.update()
        return devices

    async def queue(self) -> dict[str, Any]:
        data = await self._request("GET", "/me/player/queue")
        queue = data.get("queue") or []
        normalized = [_normalize_queue_item(item) for item in queue[:MAX_QUEUE_ITEMS]]
        playback = self.runtime.last_playback or {}
        context_uri = str(playback.get("context_uri") or playback.get("queue_context") or "").strip()
        if context_uri:
            for item in normalized:
                item["context_uri"] = context_uri
                item["contextUri"] = context_uri
        self.runtime.device_status["queue"] = {
            "items": normalized,
            "context_uri": context_uri,
            "contextUri": context_uri,
        }
        self.runtime.update()
        return {
            "queue": normalized,
            "context_uri": context_uri,
            "contextUri": context_uri,
        }

    async def playlists(self, *, limit: int | None = DEFAULT_PLAYLIST_LIMIT) -> list[dict[str, str]]:
        limit = DEFAULT_PLAYLIST_LIMIT if limit is None else int(limit)
        limit = max(0, min(MAX_PLAYLIST_ITEMS, limit))
        if limit <= 0:
            self.runtime.device_status["playlists"] = []
            self.runtime.update()
            return []

        async def load():
            playlists: list[dict[str, str]] = []
            offset = 0
            while len(playlists) < limit:
                page_limit = min(SPOTIFY_PLAYLIST_PAGE_LIMIT, limit - len(playlists))
                data = await self._request(
                    "GET",
                    f"/me/playlists?limit={page_limit}&offset={offset}",
                )
                items = data.get("items") or []
                if not isinstance(items, list) or not items:
                    break
                playlists.extend(_normalize_playlist(item) for item in items if isinstance(item, dict))
                if len(items) < page_limit:
                    break
                offset += len(items)
            return playlists[:limit]

        playlists = await self._cached(f"playlists:{limit}", load)
        self.runtime.device_status["playlists"] = playlists
        self.runtime.update()
        return playlists

    async def search_playlists(self, query: str, *, limit: int = 5) -> list[dict[str, str]]:
        """Search Spotify playlists and return normalized playable items."""
        query = str(query or "").strip()
        if not query:
            return []
        limit = max(0, min(10, int(limit)))
        if limit <= 0:
            return []
        market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
        params = urlencode({"q": query, "type": "playlist", "limit": limit, "market": market})
        data = await self._request("GET", f"/search?{params}")
        section = data.get("playlists") or {}
        items = section.get("items") or []
        if not isinstance(items, list):
            items = []
        playlists = [
            _normalize_playlist(item)
            for item in items
            if isinstance(item, dict)
        ][:limit]
        self.runtime.last_spotify_search = _spotify_search_debug(
            query=query,
            spotify_type="playlist",
            data=data,
            selected=playlists[0] if playlists else {},
        )
        return playlists

    async def search_tracks(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Search Spotify tracks and return normalized playable items."""
        query = str(query or "").strip()
        if not query:
            return []
        limit = max(0, min(10, int(limit)))
        if limit <= 0:
            return []
        market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
        params = urlencode({"q": query, "type": "track", "limit": limit, "market": market})
        data = await self._request("GET", f"/search?{params}")
        section = data.get("tracks") or {}
        items = section.get("items") or []
        if not isinstance(items, list):
            items = []
        tracks = [
            _normalize_search_item(item, "track", query)
            for item in items
            if isinstance(item, dict)
        ][:limit]
        self.runtime.last_spotify_search = _spotify_search_debug(
            query=query,
            spotify_type="track",
            data=data,
            selected=tracks[0] if tracks else {},
        )
        return tracks

    async def search_albums(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Search Spotify albums and return normalized playable items."""
        query = str(query or "").strip()
        if not query:
            return []
        limit = max(0, min(10, int(limit)))
        if limit <= 0:
            return []
        market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
        params = urlencode({"q": query, "type": "album", "limit": limit, "market": market})
        data = await self._request("GET", f"/search?{params}")
        section = data.get("albums") or {}
        items = section.get("items") or []
        if not isinstance(items, list):
            items = []
        albums = [
            album
            for album in (_normalize_album_item(item) for item in items if isinstance(item, dict))
            if album
        ][:limit]
        self.runtime.last_spotify_search = _spotify_search_debug(
            query=query,
            spotify_type="album",
            data=data,
            selected=albums[0] if albums else {},
        )
        return albums

    async def search_media(self, query: str, media_type: str = "track") -> dict[str, Any]:
        """Search a single Spotify media item without changing playback."""
        query = str(query or "").strip()
        if not query:
            raise SpotifyBackendError("Provide a Spotify search query")
        spotify_type = _spotify_search_type(media_type)
        market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
        params = urlencode({"q": query, "type": spotify_type, "limit": 1, "market": market})
        data = await self._request("GET", f"/search?{params}")
        item = _first_search_item(data, spotify_type)
        if not item:
            raise SpotifyBackendError(f"Spotify search found no {spotify_type} for: {query}")
        resolved = _normalize_search_item(item, spotify_type, query)
        self.runtime.last_spotify_search = _spotify_search_debug(
            query=query,
            spotify_type=spotify_type,
            data=data,
            selected=resolved,
        )
        return resolved

    async def seed_recommendations(self, value: Any) -> dict[str, Any]:
        """Build a Spotify recommendations track list from artist, track or genre seeds."""
        artist_names = _artist_names(value)
        track_names = _track_names(value)
        genre_names = _genre_names(value)
        limit = _search_limit(value, default=25, maximum=50)
        artists: list[dict[str, Any]] = []
        seed_tracks: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for name in artist_names:
            try:
                artist = await self._search_artist(name)
            except SpotifyBackendError:
                continue
            artist_id = str(artist.get("id") or _spotify_id_from_uri(artist.get("uri"))).strip()
            if not artist_id or artist_id in seen_ids:
                continue
            seen_ids.add(artist_id)
            artists.append(_normalize_related_artist(artist))
            if len(artists) >= 5:
                break
        seen_track_ids: set[str] = set()
        for name in track_names:
            uri = str(name or "").strip() if str(name or "").strip().startswith("spotify:track:") else ""
            if not uri:
                try:
                    uri = await self._search_uri(name, "track")
                except SpotifyBackendError:
                    continue
            track_id = _spotify_id_from_uri(uri)
            if not track_id or track_id in seen_track_ids:
                continue
            seen_track_ids.add(track_id)
            selected = getattr(self.runtime, "last_resolved_media", None)
            seed_tracks.append(selected if isinstance(selected, dict) else {"uri": uri, "title": name})
            if len(artists) + len(seed_tracks) >= 5:
                break
        genres = []
        seen_genres: set[str] = set()
        for genre in genre_names:
            normalized_genre = str(genre or "").strip().lower()
            if normalized_genre and normalized_genre not in seen_genres:
                seen_genres.add(normalized_genre)
                genres.append(normalized_genre)
            if len(artists) + len(seed_tracks) + len(genres) >= 5:
                break
        if not (artists or seed_tracks or genres):
            raise SpotifyBackendError("Spotify found no usable seeds for this mix request")
        market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
        params_payload = {"limit": limit, "market": market}
        if artists:
            params_payload["seed_artists"] = ",".join(_spotify_id_from_uri(artist.get("uri")) for artist in artists)
        if seed_tracks:
            params_payload["seed_tracks"] = ",".join(_spotify_id_from_uri(track.get("uri")) for track in seed_tracks)
        if genres:
            params_payload["seed_genres"] = ",".join(genres)
        params = urlencode(params_payload)
        data = await self._request("GET", f"/recommendations?{params}")
        items = data.get("tracks") if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = []
        tracks = [
            track
            for track in (_normalize_profile_track(item) for item in items if isinstance(item, dict))
            if track.get("uri")
        ][:limit]
        return {
            "artists": artists,
            "seed_tracks": seed_tracks,
            "seed_genres": genres,
            "tracks": tracks,
            "recommended_tracks": tracks,
            "seed_count": len(artists) + len(seed_tracks) + len(genres),
            "requested_artists": artist_names,
            "requested_tracks": track_names,
            "requested_genres": genre_names,
            "source": "spotify_recommendations",
        }

    async def listening_profile(self) -> dict[str, Any]:
        """Fetch compact Spotify listening profile data for Ask DJ."""
        async def load():
            recently_played = await self._recently_played(limit=50)
            top_artists = {
                time_range: await self._top_items("artists", time_range=time_range, limit=50)
                for time_range in ("short_term", "medium_term", "long_term")
            }
            top_tracks = {
                time_range: await self._top_items("tracks", time_range=time_range, limit=50)
                for time_range in ("short_term", "medium_term", "long_term")
            }
            profile = {
                "source": "spotify",
                "recent_tracks": recently_played,
                "recent_track_ids": [
                    track.get("id") for track in recently_played if track.get("id")
                ][:50],
                "recent_artists": _unique_values(
                    track.get("artist") for track in recently_played
                )[:25],
                "top_artists_by_range": top_artists,
                "top_tracks_by_range": top_tracks,
                "inferred_genres": _infer_genres_from_top_artists(top_artists),
                "sources": [
                    "spotify_recently_played",
                    "spotify_top_tracks_short_term",
                    "spotify_top_tracks_medium_term",
                    "spotify_top_tracks_long_term",
                    "spotify_top_artists_short_term",
                    "spotify_top_artists_medium_term",
                    "spotify_top_artists_long_term",
                ],
                "fetched_at": int(time.time()),
                "ttl_seconds": LISTENING_PROFILE_CACHE_TTL_SECONDS,
            }
            status = getattr(self.runtime, "device_status", None)
            if isinstance(status, dict):
                status["spotify_listening_profile"] = {
                    "last_profile_refresh": profile["fetched_at"],
                    "recent_track_count": len(recently_played),
                    "top_artist_count": sum(len(items) for items in top_artists.values()),
                    "top_track_count": sum(len(items) for items in top_tracks.values()),
                }
            self.runtime.update()
            return profile

        return await self._cached(
            "listening_profile:v1",
            load,
            ttl=LISTENING_PROFILE_CACHE_TTL_SECONDS,
        )

    async def recently_played(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch recent Spotify playback history without top-item profile calls."""
        return await self._recently_played(limit=limit)

    async def technical_track_analysis(self, value: Any = None) -> dict[str, Any]:
        """Fetch live Spotify audio analysis data for the current or supplied track."""
        playback = value.get("playback") if isinstance(value, dict) else {}
        if not isinstance(playback, dict) or not playback.get("uri"):
            try:
                playback = await self.playback_state()
            except SpotifyBackendError:
                playback = {}
        track = _track_from_playback_for_analysis(playback)
        track_id = _spotify_id_from_uri(track.get("uri")) or str(track.get("id") or "").strip()
        analysis: dict[str, Any] = {
            "track": track,
            "source": "spotify",
        }
        if not track_id:
            analysis["unavailable_reason"] = "missing_spotify_track_id"
            return analysis
        features = await self._optional_spotify_track_data(f"/audio-features/{track_id}")
        audio_analysis = await self._optional_spotify_track_data(f"/audio-analysis/{track_id}")
        if features:
            analysis["audio_features"] = features
        if audio_analysis:
            analysis["audio_analysis"] = {
                "sections": audio_analysis.get("sections") or [],
                "segments_count": len(audio_analysis.get("segments") or []),
                "bars_count": len(audio_analysis.get("bars") or []),
                "beats_count": len(audio_analysis.get("beats") or []),
                "tatums_count": len(audio_analysis.get("tatums") or []),
            }
        if not features and not audio_analysis:
            analysis["unavailable_reason"] = "spotify_audio_analysis_unavailable"
        return analysis

    async def artist_albums(self, query: str) -> dict[str, Any]:
        """Fetch album discography for the best Spotify artist search result."""
        query = str(query or "").strip()
        if not query:
            raise ValueError("Provide an artist name")

        async def load():
            artist = await self._search_artist(query)
            artist_id = str(artist.get("id") or _spotify_id_from_uri(artist.get("uri"))).strip()
            if not artist_id:
                raise SpotifyBackendError(f"Spotify search found no artist for: {query}")
            albums: list[dict[str, Any]] = []
            offset = 0
            market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
            while len(albums) < 100:
                params = urlencode(
                    {
                        "include_groups": "album",
                        "limit": 50,
                        "market": market,
                        "offset": offset,
                    }
                )
                data = await self._request("GET", f"/artists/{artist_id}/albums?{params}")
                items = data.get("items") if isinstance(data, dict) else []
                if not isinstance(items, list) or not items:
                    break
                albums.extend(
                    album
                    for album in (_normalize_album_item(item) for item in items)
                    if album
                )
                if len(items) < 50:
                    break
                offset += len(items)
            return {
                "artist": str(artist.get("name") or query),
                "artist_uri": str(artist.get("uri") or ""),
                "artist_id": artist_id,
                "albums": _dedupe_albums(albums),
                "source": "spotify_artist_albums",
            }

        return await self._cached(f"artist_albums:{query.lower()}", load, ttl=LISTENING_PROFILE_CACHE_TTL_SECONDS)

    async def related_artists(self, query: str) -> dict[str, Any]:
        """Fetch Spotify related artists for the best artist search result."""
        query = str(query or "").strip()
        if not query:
            raise ValueError("Provide an artist name")

        async def load():
            artist = await self._search_artist(query)
            artist_id = str(artist.get("id") or _spotify_id_from_uri(artist.get("uri"))).strip()
            if not artist_id:
                raise SpotifyBackendError(f"Spotify search found no artist for: {query}")
            data = await self._request("GET", f"/artists/{artist_id}/related-artists")
            items = data.get("artists") if isinstance(data, dict) else []
            if not isinstance(items, list):
                items = []
            return {
                "artist": str(artist.get("name") or query),
                "artist_uri": str(artist.get("uri") or ""),
                "artist_id": artist_id,
                "artists": [
                    related
                    for related in (_normalize_related_artist(item) for item in items[:20])
                    if related
                ],
                "source": "spotify_related_artists",
            }

        return await self._cached(f"related_artists:{query.lower()}", load, ttl=LISTENING_PROFILE_CACHE_TTL_SECONDS)

    async def artist_profile(self, query: str) -> dict[str, Any]:
        """Fetch compact Spotify artist profile metadata for Ask DJ style questions."""
        query = str(query or "").strip()
        if not query:
            raise ValueError("Provide an artist name")

        async def load():
            return _normalize_profile_artist(await self._search_artist(query))

        return await self._cached(f"artist_profile:{query.lower()}", load, ttl=LISTENING_PROFILE_CACHE_TTL_SECONDS)

    async def _search_artist(self, query: str) -> dict[str, Any]:
        market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
        for candidate in _artist_search_queries(query):
            params = urlencode({"q": candidate, "type": "artist", "limit": 1, "market": market})
            data = await self._request("GET", f"/search?{params}")
            artist = _first_search_item(data, "artist")
            if artist:
                return artist
        raise SpotifyBackendError(f"Spotify search found no artist for: {query}")

    async def _recently_played(self, *, limit: int = 50) -> list[dict[str, Any]]:
        limit = min(50, max(1, int(limit)))
        data = await self._request("GET", f"/me/player/recently-played?limit={limit}")
        items = data.get("items") if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []
        tracks = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            track_data = item.get("track") if isinstance(item.get("track"), dict) else item
            track = _normalize_profile_track(track_data)
            if not track:
                continue
            played_at = str(item.get("played_at") or "").strip()
            if played_at:
                track["played_at"] = played_at
            context = item.get("context") if isinstance(item.get("context"), dict) else {}
            context_uri = str(context.get("uri") or "").strip()
            if context_uri:
                track["context_uri"] = context_uri
                track["context_type"] = str(context.get("type") or "").strip()
            tracks.append(track)
        return tracks

    async def _optional_spotify_track_data(self, path: str) -> dict[str, Any]:
        try:
            data = await self._request("GET", path)
        except SpotifyBackendError as exc:
            _LOGGER.debug("DJConnect optional Spotify track analysis unavailable for %s: %s", path, exc)
            return {}
        return data if isinstance(data, dict) else {}

    async def _top_items(
        self,
        item_type: str,
        *,
        time_range: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if item_type not in {"artists", "tracks"}:
            raise ValueError("Spotify top item type must be artists or tracks")
        if time_range not in {"short_term", "medium_term", "long_term"}:
            raise ValueError("Spotify top time_range is invalid")
        limit = min(50, max(1, int(limit)))
        params = urlencode({"time_range": time_range, "limit": limit})
        data = await self._request("GET", f"/me/top/{item_type}?{params}")
        items = data.get("items") if isinstance(data, dict) else []
        if not isinstance(items, list):
            return []
        if item_type == "artists":
            return [
                artist
                for artist in (_normalize_profile_artist(item) for item in items[:limit] if isinstance(item, dict))
                if artist
            ]
        return [
            track
            for track in (_normalize_profile_track(item) for item in items[:limit] if isinstance(item, dict))
            if track
        ]

    async def pause(self) -> None:
        await self._request("PUT", "/me/player/pause", expected_empty=True)

    async def play(self, value: Any = None) -> None:
        body = None
        if value:
            value = await self._playable_value(value)
            body = {"uris": [str(value)]} if str(value).startswith("spotify:track:") else {"context_uri": str(value)}
        try:
            await self._request("PUT", "/me/player/play", json=body, expected_empty=True)
        except SpotifyBackendError as exc:
            if not _looks_like_no_active_device(exc):
                raise
            await self._ensure_playback_device(play=False)
            await self._request("PUT", "/me/player/play", json=body, expected_empty=True)

    async def play_context_at(self, value: Any) -> None:
        if not isinstance(value, dict):
            raise ValueError("Provide context_uri and offset_uri")
        context_uri = str(value.get("context_uri") or "").strip()
        offset_uri = str(value.get("offset_uri") or value.get("uri") or "").strip()
        if not offset_uri:
            raise ValueError("Provide offset_uri")
        if not context_uri:
            playback = self.runtime.last_playback or {}
            context_uri = str(playback.get("context_uri") or "").strip()
        if not context_uri:
            await self._request(
                "PUT",
                "/me/player/play",
                json={"uris": [offset_uri]},
                expected_empty=True,
            )
            return
        if context_uri.startswith("spotify:artist:") and offset_uri.startswith("spotify:track:"):
            await self._request(
                "PUT",
                "/me/player/play",
                json={"uris": [offset_uri]},
                expected_empty=True,
            )
            return
        await self._request(
            "PUT",
            "/me/player/play",
            json={"context_uri": context_uri, "offset": {"uri": offset_uri}},
            expected_empty=True,
        )

    async def next(self) -> None:
        await self._request("POST", "/me/player/next", expected_empty=True)

    async def previous(self) -> None:
        await self._request("POST", "/me/player/previous", expected_empty=True)

    async def seek_relative(self, value: Any) -> None:
        """Seek relative to the current Spotify playback position."""
        try:
            offset_ms = int(float(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("seek_relative value must be an integer millisecond offset") from exc
        playback = await self.playback_state()
        if not playback.get("has_playback"):
            raise SpotifyBackendError("Cannot seek because Spotify playback is not active")
        current_ms = _int_or_none(playback.get("progress_ms")) or 0
        duration_ms = _int_or_none(playback.get("duration_ms"))
        position_ms = max(0, current_ms + offset_ms)
        if duration_ms is not None:
            position_ms = min(position_ms, max(0, duration_ms))
        await self._request(
            "PUT",
            f"/me/player/seek?position_ms={position_ms}",
            expected_empty=True,
        )

    async def start_liked_proxy(self) -> None:
        playlist = str(self.conf.get(CONF_LIKED_PROXY) or "").strip()
        if not playlist:
            raise SpotifyBackendError("DJConnect Liked Proxy playlist URI is not configured")
        await self.start_playlist(playlist)

    async def start_playlist(self, playlist_uri: str) -> None:
        uri = playlist_uri.strip()
        if not uri:
            raise ValueError("Provide a playlist URI")
        if not uri.startswith("spotify:playlist:"):
            uri = await self._search_uri(uri, "playlist")
        body = {"context_uri": uri}
        try:
            await self._request("PUT", "/me/player/play", json=body, expected_empty=True)
        except SpotifyBackendError as exc:
            if not _looks_like_no_active_device(exc):
                raise
            await self._ensure_playback_device(play=False)
            await self._request("PUT", "/me/player/play", json=body, expected_empty=True)

    async def play_artist_top_tracks(self, query: str, *, limit: int = 10) -> None:
        """Resolve an artist and start playback with that artist's popular tracks."""
        artist = await self._search_artist(query)
        artist_id = str(artist.get("id") or _spotify_id_from_uri(artist.get("uri"))).strip()
        if not artist_id:
            raise SpotifyBackendError(f"Spotify search found no artist for: {query}")
        market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
        params = urlencode({"market": market})
        data = await self._request("GET", f"/artists/{artist_id}/top-tracks?{params}")
        tracks = data.get("tracks") if isinstance(data, dict) else []
        if not isinstance(tracks, list):
            tracks = []
        uris = [
            str(track.get("uri") or "").strip()
            for track in tracks[: max(1, min(20, int(limit)))]
            if isinstance(track, dict) and str(track.get("uri") or "").startswith("spotify:track:")
        ]
        if not uris:
            raise SpotifyBackendError(f"Spotify found no top tracks for artist: {query}")
        selected = _normalize_related_artist(artist)
        self.runtime.last_resolved_media = selected
        self.runtime.last_spotify_search = _spotify_search_debug(
            query=query,
            spotify_type="artist",
            data={"artists": {"total": 1, "items": [artist]}},
            selected=selected,
        )
        try:
            await self._request(
                "PUT",
                "/me/player/play",
                json={"uris": uris},
                expected_empty=True,
            )
        except SpotifyBackendError as exc:
            if not _looks_like_no_active_device(exc):
                raise
            await self._ensure_playback_device(play=False)
            await self._request(
                "PUT",
                "/me/player/play",
                json={"uris": uris},
                expected_empty=True,
            )

    async def play_uris(self, uris: list[str]) -> None:
        """Start playback with explicit Spotify track URIs."""
        track_uris = [
            str(uri).strip()
            for uri in uris
            if str(uri).strip().startswith("spotify:track:")
        ][:100]
        if not track_uris:
            raise SpotifyBackendError("No playable Spotify track URIs were provided")
        body = {"uris": track_uris}
        try:
            await self._request("PUT", "/me/player/play", json=body, expected_empty=True)
        except SpotifyBackendError as exc:
            if not _looks_like_no_active_device(exc):
                raise
            await self._ensure_playback_device(play=False)
            await self._request("PUT", "/me/player/play", json=body, expected_empty=True)

    async def create_playlist_from_tracks(self, value: Any) -> dict[str, Any]:
        """Create a private Spotify playlist and add track URIs."""
        if not isinstance(value, dict):
            raise ValueError("Provide playlist name and track URIs")
        name = str(value.get("name") or "DJConnect mix").strip()[:100]
        description = str(value.get("description") or "Samengesteld door DJConnect Ask DJ.").strip()[:300]
        uris = _track_uris(value)
        if not uris:
            raise SpotifyBackendError("No Spotify track URIs available to save")
        profile = await self._request("GET", "/me")
        user_id = str(profile.get("id") or "").strip()
        if not user_id:
            raise SpotifyBackendError("Spotify user profile is unavailable")
        playlist = await self._request(
            "POST",
            f"/users/{user_id}/playlists",
            json={"name": name, "public": False, "description": description},
        )
        playlist_id = str(playlist.get("id") or _spotify_id_from_uri(playlist.get("uri"))).strip()
        if not playlist_id:
            raise SpotifyBackendError("Spotify did not return a playlist id")
        await self._request(
            "POST",
            f"/playlists/{playlist_id}/tracks",
            json={"uris": uris[:100]},
        )
        return _normalize_playlist(playlist)

    async def _playable_value(self, value: Any) -> str:
        if isinstance(value, dict):
            query = str(value.get("query") or value.get("value") or "").strip()
            media_type = str(value.get("type") or "artist").strip().lower()
            if not query:
                raise ValueError("Provide a Spotify URI or search query")
            if query.startswith("spotify:"):
                return query
            return await self._search_uri(query, media_type)
        text = str(value or "").strip()
        if not text:
            raise ValueError("Provide a Spotify URI or search query")
        if text.startswith("spotify:"):
            return text
        return await self._search_uri(text, "artist")

    async def _search_uri(self, query: str, media_type: str) -> str:
        spotify_type = _spotify_search_type(media_type)
        market = str(self.conf.get("spotify_market") or DEFAULT_SPOTIFY_MARKET)
        params = urlencode({"q": query, "type": spotify_type, "limit": 1, "market": market})
        data = await self._request("GET", f"/search?{params}")
        item = _first_search_item(data, spotify_type)
        uri = str(item.get("uri") or "").strip()
        if not uri:
            self.runtime.last_spotify_search = _spotify_search_debug(
                query=query,
                spotify_type=spotify_type,
                data=data,
                selected={},
            )
            raise SpotifyBackendError(f"Spotify search found no {spotify_type} for: {query}")
        resolved = _normalize_search_item(item, spotify_type, query)
        self.runtime.last_resolved_media = resolved
        self.runtime.last_spotify_search = _spotify_search_debug(
            query=query,
            spotify_type=spotify_type,
            data=data,
            selected=resolved,
        )
        _LOGGER.debug(
            "DJConnect Spotify search resolved type=%s query=%s uri=%s",
            spotify_type,
            query,
            uri,
        )
        return uri

    async def _ensure_playback_device(self, *, play: bool) -> str:
        devices = await self.devices()
        configured = str(self.conf.get(CONF_SPOTIFY_SOURCE) or "").strip()
        selected = _select_spotify_device(devices, configured)
        device_id = str(selected.get("id") or "").strip()
        if not device_id:
            raise SpotifyBackendError(
                "No Spotify playback device is available. Open Spotify on a phone, "
                "desktop or speaker, or set Spotify source in DJConnect options."
            )
        await self._transfer_playback(device_id, play=play)
        return device_id

    async def set_shuffle(self, value: Any) -> None:
        """Set Spotify shuffle state from the canonical DJConnect command."""
        enabled = _bool_value(value)
        await self._request(
            "PUT",
            f"/me/player/shuffle?state={str(enabled).lower()}",
            expected_empty=True,
        )

    async def set_repeat(self, value: str) -> None:
        """Set Spotify repeat state from the canonical DJConnect command."""
        repeat = value.strip().lower()
        if repeat not in {"off", "track", "context"}:
            raise ValueError("set_repeat value must be off, track or context")
        await self._request(
            "PUT",
            f"/me/player/repeat?state={repeat}",
            expected_empty=True,
        )

    async def set_output(self, device_id: str, *, play: bool = False) -> None:
        if not device_id:
            raise ValueError("Provide an output device id")
        devices = await self.devices()
        selected = _select_spotify_device(devices, device_id)
        device_id = str(selected.get("id") or device_id).strip()
        if not device_id:
            raise ValueError("Provide an output device id")
        await self._transfer_playback(device_id, play=play)

    async def _transfer_playback(self, device_id: str, *, play: bool = False) -> None:
        await self._request(
            "PUT",
            "/me/player",
            json={"device_ids": [device_id], "play": play},
            expected_empty=True,
        )

    async def set_volume(self, value: Any) -> None:
        try:
            volume = max(0, min(100, int(float(value))))
        except (TypeError, ValueError) as exc:
            raise ValueError("set_volume value must be 0-100") from exc
        await self._request(
            "PUT",
            f"/me/player/volume?volume_percent={volume}",
            expected_empty=True,
        )

    async def save_current_track(self) -> dict[str, Any]:
        return await self.set_current_track_favorite(True)

    async def set_current_track_favorite(self, value: Any = True) -> dict[str, Any]:
        target = _favorite_target(value)
        playback = await self.playback_state()
        uri = str(playback.get("uri") or playback.get("current_uri") or "").strip()
        track_id = _spotify_id_from_uri(uri)
        if not _looks_like_spotify_id(track_id):
            raise SpotifyBackendError("No current Spotify track is available to update favorites")
        await self._request(
            "PUT" if target else "DELETE",
            f"/me/tracks?ids={track_id}",
            expected_empty=True,
        )
        playback["is_liked"] = target
        playback["favorite_status"] = target
        return playback


def _normalize_playback(data: dict[str, Any]) -> dict[str, Any]:
    item = data.get("item") or {}
    context = data.get("context") or {}
    context_uri = context.get("uri") or ""
    artists = item.get("artists") or []
    album = item.get("album") or {}
    album_uri = str(album.get("uri") or "").strip()
    images = album.get("images") or item.get("images") or []
    album_image_url = _best_image_url(images)
    return {
        "has_playback": bool(data),
        "is_playing": bool(data.get("is_playing")),
        "title": item.get("name") or "",
        "track_name": item.get("name") or "",
        "uri": item.get("uri") or "",
        "current_uri": item.get("uri") or "",
        "context": _normalize_context(context),
        "context_uri": context_uri,
        "queue_context": context_uri,
        "artist": ", ".join(artist.get("name", "") for artist in artists if artist.get("name")),
        "artist_name": ", ".join(artist.get("name", "") for artist in artists if artist.get("name")),
        "album_name": album.get("name") or "",
        "album_image_url": album_image_url,
        "media_image_url": album_image_url,
        "progress_ms": data.get("progress_ms"),
        "duration_ms": item.get("duration_ms"),
        "volume_percent": (data.get("device") or {}).get("volume_percent"),
        "shuffle": bool(data.get("shuffle_state")),
        "repeat_state": data.get("repeat_state") or "off",
        "device": _normalize_device(data.get("device") or {}),
    }


def _spotify_search_type(media_type: str) -> str:
    normalized = str(media_type or "").strip().lower()
    if normalized == "playlist":
        return "playlist"
    if normalized == "track":
        return "track"
    if normalized == "album":
        return "album"
    return "artist"


def _favorite_target(value: Any) -> bool:
    if isinstance(value, dict):
        for key in ("favorite", "is_liked", "liked", "target", "value"):
            if key in value:
                return _favorite_target(value.get(key))
        return True
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"false", "0", "no", "nee", "off", "remove", "unlike", "unsave"}:
            return False
        if normalized in {"true", "1", "yes", "ja", "on", "add", "like", "save"}:
            return True
    return bool(value)


def _looks_like_spotify_id(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{8,64}", str(value or "").strip()))


def _artist_album_query(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("artist") or value.get("query") or value.get("value") or "").strip()
    return str(value or "").strip()


def _playlist_limit(value: Any) -> int:
    """Return client-aware playlist limit for Spotify browsing commands."""
    raw_limit = None
    client_type = _playlist_client_type(value)
    if isinstance(value, dict):
        raw_limit = value.get("limit")
    else:
        raw_limit = value
    default = ESP_DEFAULT_PLAYLIST_LIMIT if client_type == "esp32" else DEFAULT_PLAYLIST_LIMIT
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = default
    maximum = ESP_DEFAULT_PLAYLIST_LIMIT if client_type == "esp32" else MAX_PLAYLIST_ITEMS
    return max(0, min(maximum, limit))


def _playlist_client_type(value: Any) -> str:
    """Return normalized client_type from a playlist command payload."""
    if isinstance(value, dict):
        return str(value.get("client_type") or "").strip().lower()
    return ""


def _search_query(value: Any) -> str:
    """Return a normalized Spotify search query from command payload variants."""
    if isinstance(value, dict):
        return str(value.get("query") or value.get("search") or value.get("value") or "").strip()
    return str(value or "").strip()


def _artist_search_queries(query: str) -> list[str]:
    """Return canonical Spotify artist search variants for common spoken/typed variants."""
    raw = str(query or "").strip()
    if not raw:
        return []
    canonical = ARTIST_QUERY_ALIASES.get(_normalize_artist_alias_key(raw))
    variants = [candidate for candidate in (canonical, raw) if candidate]
    return list(dict.fromkeys(variants))


def _normalize_artist_alias_key(query: str) -> str:
    normalized = str(query or "").strip().lower()
    normalized = re.sub(r"[^\w\s&]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _search_limit(value: Any, *, default: int, maximum: int) -> int:
    """Return bounded search result count from command payload variants."""
    raw = value.get("limit") if isinstance(value, dict) else None
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        limit = default
    return max(0, min(maximum, limit))


def _artist_names(value: Any) -> list[str]:
    """Return ordered unique artist names from a command payload."""
    raw: Any
    if isinstance(value, dict):
        raw = value.get("artists") or value.get("artist_names") or value.get("query") or value.get("value")
    else:
        raw = value
    if isinstance(raw, list):
        candidates = [str(item or "").strip() for item in raw]
    else:
        text = str(raw or "").strip()
        candidates = [
            item.strip()
            for item in _split_seed_list(text)
        ]
    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = " ".join(candidate.strip(" ?.!'\"").split())
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _track_names(value: Any) -> list[str]:
    """Return ordered unique track search strings from a command payload."""
    raw: Any
    if isinstance(value, dict):
        raw = value.get("tracks") or value.get("track_names")
    else:
        raw = None
    return _clean_seed_values(raw)


def _genre_names(value: Any) -> list[str]:
    """Return ordered unique genre seed strings from a command payload."""
    raw: Any
    if isinstance(value, dict):
        raw = value.get("genres") or value.get("genre_names")
    else:
        raw = None
    return _clean_seed_values(raw)


def _clean_seed_values(raw: Any) -> list[str]:
    if isinstance(raw, list):
        candidates = [str(item or "").strip() for item in raw]
    else:
        candidates = _split_seed_list(str(raw or ""))
    result: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = " ".join(candidate.strip(" ?.!'\"").split())
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _split_seed_list(text: str) -> list[str]:
    """Split a user-supplied seed list."""
    return re.split(r"\s*(?:,|;|\+|/|\ben\b|\band\b)\s*", text)


def _track_uris(value: Any) -> list[str]:
    """Return bounded Spotify track URIs from command payload variants."""
    raw: Any
    if isinstance(value, dict):
        raw = value.get("uris") or value.get("track_uris") or value.get("tracks") or value.get("uri")
    else:
        raw = value
    if isinstance(raw, str):
        values = [item.strip() for item in raw.split(",")]
    elif isinstance(raw, list):
        values = [
            str(item.get("uri") if isinstance(item, dict) else item).strip()
            for item in raw
        ]
    else:
        values = []
    result: list[str] = []
    seen: set[str] = set()
    for uri in values:
        if uri.startswith("spotify:track:") and uri not in seen:
            seen.add(uri)
            result.append(uri)
        if len(result) >= 100:
            break
    return result


def _first_search_item(data: dict[str, Any], spotify_type: str) -> dict[str, Any]:
    section = data.get(f"{spotify_type}s") or {}
    items = section.get("items") or []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict):
            return item
    return {}


def _normalize_search_item(item: dict[str, Any], spotify_type: str, query: str) -> dict[str, Any]:
    artists = item.get("artists") or []
    owner = item.get("owner") or {}
    album = item.get("album") or {}
    images = album.get("images") or item.get("images") or []
    image_url = _best_image_url(images)
    name = item.get("name") or ""
    artist_name = (
        name
        if spotify_type == "artist"
        else ", ".join(artist.get("name", "") for artist in artists if artist.get("name"))
    )
    return {
        "id": item.get("id") or "",
        "type": spotify_type,
        "query": query,
        "uri": item.get("uri") or "",
        "title": "" if spotify_type == "artist" else name,
        "track_name": "" if spotify_type == "artist" else name,
        "artist": artist_name,
        "artist_name": artist_name,
        "album_name": album.get("name") or "",
        "context_uri": album.get("uri") or "",
        "image_url": image_url,
        "album_image_url": image_url,
        "thumbnail_url": image_url,
        "owner": owner.get("display_name") or owner.get("id") or "",
    }


def _normalize_album_item(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    name = str(item.get("name") or "").strip()
    uri = str(item.get("uri") or "").strip()
    if not (name or uri):
        return {}
    images = item.get("images") or []
    artists = item.get("artists") or []
    return {
        "id": str(item.get("id") or "").strip(),
        "name": name,
        "title": name,
        "uri": uri,
        "release_date": str(item.get("release_date") or "").strip(),
        "album_type": str(item.get("album_type") or "").strip(),
        "total_tracks": item.get("total_tracks"),
        "artist": ", ".join(
            str(artist.get("name") or "").strip()
            for artist in artists
            if isinstance(artist, dict) and artist.get("name")
        ),
        "image_url": _best_image_url(images),
        "album_image_url": _best_image_url(images),
    }


def _normalize_related_artist(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    name = str(item.get("name") or "").strip()
    uri = str(item.get("uri") or "").strip()
    if not (name or uri):
        return {}
    images = item.get("images") or []
    genres = item.get("genres") or []
    return {
        "id": str(item.get("id") or "").strip(),
        "name": name,
        "title": name,
        "uri": uri,
        "genres": [str(genre) for genre in genres if genre],
        "popularity": item.get("popularity"),
        "image_url": _best_image_url(images),
        "artist_image_url": _best_image_url(images),
    }


def _dedupe_albums(albums: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for album in albums:
        name = str(album.get("name") or album.get("title") or "").strip()
        year = str(album.get("release_date") or "")[:4]
        key = " ".join(name.lower().split())
        if year:
            key = f"{key}:{year}"
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(album)
    return sorted(
        result,
        key=lambda item: str(item.get("release_date") or "9999"),
    )


def _spotify_id_from_uri(uri: Any) -> str:
    text = str(uri or "").strip()
    if not text.startswith("spotify:"):
        return ""
    return text.rsplit(":", 1)[-1].strip()


def _spotify_search_debug(
    *,
    query: str,
    spotify_type: str,
    data: dict[str, Any],
    selected: dict[str, Any],
) -> dict[str, Any]:
    section = data.get(f"{spotify_type}s") or {}
    items = section.get("items") or []
    if not isinstance(items, list):
        items = []
    return {
        "query": query,
        "type": spotify_type,
        "total": section.get("total"),
        "returned": len(items),
        "selected": selected,
        "candidates": [
            _normalize_search_item(item, spotify_type, query)
            for item in items[:5]
            if isinstance(item, dict)
        ],
    }


def _select_spotify_device(devices: list[dict[str, Any]], configured: str) -> dict[str, Any]:
    configured = str(configured or "").strip()
    if configured:
        for device in devices:
            if str(device.get("id") or "").strip() == configured:
                return device
        for device in devices:
            if str(device.get("name") or "").strip().lower() == configured.lower():
                return device
    for device in devices:
        if device.get("active") and device.get("id"):
            return device
    for device in devices:
        if device.get("id"):
            return device
    return {}


def _looks_like_no_active_device(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "no active device" in message
        or "device not found" in message
        or "player command failed" in message
    )


def _merge_playback_status(device_status: dict[str, Any], update: dict[str, Any]) -> None:
    """Merge backend playback status without erasing cached device sensor values."""
    for key, value in update.items():
        if value in (None, "", [], {}) and key in device_status:
            continue
        device_status[key] = value


def _normalize_context(context: dict[str, Any]) -> dict[str, str]:
    return {
        "type": context.get("type") or "",
        "uri": context.get("uri") or "",
        "href": context.get("href") or "",
    }


def _best_image_url(images: Any) -> str:
    if not isinstance(images, list):
        return ""
    valid = [image for image in images if isinstance(image, dict) and image.get("url")]
    if not valid:
        return ""
    sorted_images = sorted(
        valid,
        key=lambda image: int(image.get("width") or 0) * int(image.get("height") or 0),
        reverse=True,
    )
    return str(sorted_images[0]["url"])


def _normalize_device(device: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": device.get("id") or "",
        "name": device.get("name") or "",
        "type": device.get("type") or "",
        "active": bool(device.get("is_active")),
        "supports_volume": not bool(device.get("is_restricted")),
        "volume_percent": device.get("volume_percent"),
    }


def _normalize_queue_item(item: dict[str, Any]) -> dict[str, str]:
    artists = item.get("artists") or []
    images = (item.get("album") or {}).get("images") or item.get("images") or []
    album_image_url = _best_image_url(images)
    return {
        "title": item.get("name") or "",
        "subtitle": ", ".join(artist.get("name", "") for artist in artists if artist.get("name")),
        "uri": item.get("uri") or "",
        "album_image_url": album_image_url,
        "albumImageUrl": album_image_url,
        "image_url": album_image_url,
        "imageUrl": album_image_url,
        "thumbnail_url": album_image_url,
    }


def _normalize_playlist(item: dict[str, Any]) -> dict[str, str]:
    owner = item.get("owner") or {}
    image_url = _best_image_url(item.get("images") or [])
    name = item.get("name") or ""
    uri = item.get("uri") or ""
    owner_name = owner.get("display_name") or owner.get("id") or ""
    return {
        "id": uri or item.get("id") or "",
        "name": name,
        "title": name,
        "display_title": name,
        "owner": owner_name,
        "subtitle": owner_name,
        "uri": uri,
        "value": uri,
        "playlist_uri": uri,
        "image_url": image_url,
        "imageUrl": image_url,
        "album_image_url": image_url,
        "albumImageUrl": image_url,
        "album_art_url": image_url,
        "media_image_url": image_url,
        "entity_picture": image_url,
        "thumbnail_url": image_url,
    }


def _normalize_profile_track(item: dict[str, Any]) -> dict[str, Any]:
    artists = item.get("artists") or []
    album = item.get("album") or {}
    album_uri = str(album.get("uri") or "").strip()
    image_url = _best_image_url(album.get("images") or item.get("images") or [])
    artist_names = [
        str(artist.get("name") or "").strip()
        for artist in artists
        if isinstance(artist, dict) and artist.get("name")
    ]
    name = str(item.get("name") or "").strip()
    uri = str(item.get("uri") or "").strip()
    track_id = str(item.get("id") or "").strip()
    if not (name or uri or track_id):
        return {}
    return {
        key: value
        for key, value in {
            "id": track_id,
            "uri": uri,
            "title": name,
            "track_name": name,
            "artist": ", ".join(artist_names),
            "artist_name": ", ".join(artist_names),
            "artists": artist_names[:5],
            "album": album.get("name") or "",
            "album_name": album.get("name") or "",
            "album_uri": album_uri,
            "context_uri": album_uri,
            "album_image_url": image_url,
            "image_url": image_url,
            "duration_ms": item.get("duration_ms"),
            "popularity": item.get("popularity"),
        }.items()
        if value not in (None, "", [], {})
    }


def _track_from_playback_for_analysis(playback: Any) -> dict[str, Any]:
    if not isinstance(playback, dict):
        return {}
    track = playback.get("track") if isinstance(playback.get("track"), dict) else playback
    result = {
        key: value
        for key, value in {
            "id": track.get("id"),
            "uri": track.get("uri"),
            "title": track.get("title") or track.get("track_name") or track.get("name"),
            "track_name": track.get("track_name") or track.get("title") or track.get("name"),
            "artist": track.get("artist") or track.get("artist_name"),
            "artist_name": track.get("artist_name") or track.get("artist"),
            "album": track.get("album") or track.get("album_name"),
            "album_name": track.get("album_name") or track.get("album"),
            "duration_ms": track.get("duration_ms"),
        }.items()
        if value not in (None, "", [], {})
    }
    return result


def _normalize_profile_artist(item: dict[str, Any]) -> dict[str, Any]:
    image_url = _best_image_url(item.get("images") or [])
    name = str(item.get("name") or "").strip()
    artist_id = str(item.get("id") or "").strip()
    uri = str(item.get("uri") or "").strip()
    genres = [str(genre) for genre in (item.get("genres") or []) if genre]
    if not (name or artist_id or uri):
        return {}
    return {
        key: value
        for key, value in {
            "id": artist_id,
            "uri": uri,
            "name": name,
            "artist": name,
            "artist_name": name,
            "genres": genres[:10],
            "image_url": image_url,
            "popularity": item.get("popularity"),
        }.items()
        if value not in (None, "", [], {})
    }


def _unique_values(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        normalized = text.lower()
        if not text or normalized in seen:
            continue
        seen.add(normalized)
        result.append(text)
    return result


def _infer_genres_from_top_artists(top_artists: dict[str, list[dict[str, Any]]]) -> list[str]:
    counts: dict[str, int] = {}
    for artists in top_artists.values():
        if not isinstance(artists, list):
            continue
        for artist in artists:
            if not isinstance(artist, dict):
                continue
            for genre in artist.get("genres") or []:
                text = str(genre or "").strip()
                if text:
                    counts[text] = counts.get(text, 0) + 1
    return [
        genre
        for genre, _count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )[:20]
    ]


def _bool_value(value: Any) -> bool:
    """Parse a canonical boolean command value."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("set_shuffle value must be true or false")


def _int_or_none(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _current_refresh_token(runtime: Any, conf: dict[str, Any]) -> str:
    candidates = _refresh_token_candidates(runtime, conf)
    return candidates[0][1] if candidates else ""


def _refresh_token_candidates(runtime: Any, conf: dict[str, Any]) -> list[tuple[str, str]]:
    """Return known Spotify refresh tokens without exposing token values in logs."""
    entry = getattr(runtime, "entry", None)
    entry_data = getattr(entry, "data", {}) if entry is not None else {}
    raw_candidates = (
        ("runtime", getattr(runtime, "latest_spotify_refresh_token", None)),
        ("entry", entry_data.get(CONF_SPOTIFY_REFRESH_TOKEN)),
        ("config", conf.get(CONF_SPOTIFY_REFRESH_TOKEN)),
    )
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for source, value in raw_candidates:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        result.append((source, token))
    return result


def _refresh_token_source_names(runtime: Any, conf: dict[str, Any]) -> list[str]:
    """Return source names only; never return token values."""
    return [source for source, _token in _refresh_token_candidates(runtime, conf)]


def _token_refresh_lock(runtime: Any) -> asyncio.Lock:
    lock = getattr(runtime, "spotify_token_refresh_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        runtime.spotify_token_refresh_lock = lock
    return lock


def _spotify_error_message(body: Any) -> str:
    """Return a concise Spotify error message without logging full payloads."""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("reason") or "Spotify API error")
        if isinstance(error, str):
            return error
        return str(body.get("message") or "Spotify API error")
    text = str(body or "").strip()
    return text[:240] if text else "Spotify API error"


async def _consume_spotify_response(resp: Any) -> None:
    """Read an error response before retrying so aiohttp can reuse the connection."""
    try:
        await resp.text()
    except Exception:  # noqa: BLE001
        pass


def _create_spotify_reauth_issue(hass: HomeAssistant, entry: Any) -> None:
    """Create a repair hint when Spotify revoked the stored refresh token."""
    if entry is None:
        return
    try:
        from homeassistant.helpers import issue_registry as ir

        ir.async_create_issue(
            hass,
            DOMAIN,
            "spotify_refresh_token_revoked",
            data={"entry_id": entry.entry_id},
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="spotify_refresh_token_revoked",
        )
    except Exception:  # noqa: BLE001
        _LOGGER.debug(
            "DJConnect could not create Spotify reauthorization repair issue",
            exc_info=True,
        )
