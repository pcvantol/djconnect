"""DJConnect use-case layer over music backend adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from homeassistant.core import HomeAssistant

from .const import (
    CONF_MUSIC_ASSISTANT_PLAYER,
    CONF_MUSIC_BACKEND,
    CONF_MUSIC_BACKEND_REVISION,
    CONF_SPOTIFY_REFRESH_TOKEN,
    DEFAULT_MUSIC_BACKEND,
    MUSIC_BACKEND_MUSIC_ASSISTANT,
    MUSIC_BACKEND_NAMES,
    MUSIC_BACKEND_SPOTIFY_DIRECT,
)
from .spotify_backend import (
    SpotifyBackendError,
    handle_spotify_command as _handle_spotify_command,
)


class MusicCommand(StrEnum):
    """Known DJConnect music backend commands."""

    DEVICES = "devices"
    SET_OUTPUT = "set_output"
    QUEUE = "queue"
    PLAYLISTS = "playlists"
    SEARCH_PLAYLISTS = "search_playlists"
    SEARCH_TRACKS = "search_tracks"
    SEARCH_ALBUMS = "search_albums"
    SEARCH_MEDIA = "search_media"
    STATUS = "status"
    PLAY = "play"
    PLAY_URIS = "play_uris"
    PAUSE = "pause"
    NEXT = "next"
    PREVIOUS = "previous"
    SET_VOLUME = "set_volume"
    SAVE_CURRENT_TRACK = "save_current_track"
    SET_CURRENT_TRACK_FAVORITE = "set_current_track_favorite"
    TOGGLE_CURRENT_TRACK_FAVORITE = "toggle_current_track_favorite"
    RECENTLY_PLAYED = "recently_played"
    ARTIST_RECOMMENDATIONS = "artist_recommendations"
    LISTENING_PROFILE = "listening_profile"
    SET_SHUFFLE = "set_shuffle"
    SET_REPEAT = "set_repeat"
    SEEK_RELATIVE = "seek_relative"


@dataclass(frozen=True)
class BackendActionValue:
    """Backend-specific value payload for a client playback action."""

    item_id: str = ""
    uri: str = ""
    provider: str = ""
    media_type: str = ""
    title: str = ""
    subtitle: str = ""
    image_url: str = ""
    target_player_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "item_id": self.item_id,
                "uri": self.uri,
                "provider": self.provider,
                "media_type": self.media_type,
                "title": self.title,
                "subtitle": self.subtitle,
                "image_url": self.image_url,
                "target_player_id": self.target_player_id,
            }.items()
            if value not in ("", None)
        }


@dataclass(frozen=True)
class PlaybackAction:
    """Client-visible playback action with typed backend metadata."""

    id: str
    kind: str
    label: str = "Play Now"
    button_label: str = "Play Now"
    action_style: str = "play_now"
    title: str = ""
    subtitle: str = ""
    image_url: str = ""
    reason: str = ""
    backend: str = DEFAULT_MUSIC_BACKEND
    provider: str = "spotify"
    music_backend_revision: int = 0
    value: BackendActionValue = field(default_factory=BackendActionValue)

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "id": self.id,
                "kind": self.kind,
                "label": self.label,
                "button_label": self.button_label,
                "action_style": self.action_style,
                "title": self.title,
                "subtitle": self.subtitle,
                "image_url": self.image_url,
                "reason": self.reason,
                "backend": self.backend,
                "provider": self.provider,
                "music_backend_revision": self.music_backend_revision,
                "value": self.value.to_dict(),
            }.items()
            if value not in ("", None, {})
        }


@dataclass(frozen=True)
class MusicBackendResult:
    """Normalized result from a music backend command."""

    success: bool = True
    provider: str = ""
    source: str = ""
    backend_available: bool | None = None
    playback: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        result: dict[str, Any] | None,
        *,
        provider: str,
    ) -> "MusicBackendResult":
        payload = dict(result or {})
        success = bool(payload.pop("success", True))
        result_provider = str(payload.pop("provider", provider) or provider)
        source = str(payload.pop("source", result_provider) or result_provider)
        backend_available = payload.pop("backend_available", None)
        playback = payload.pop("playback", {})
        return cls(
            success=success,
            provider=result_provider,
            source=source,
            backend_available=backend_available,
            playback=playback if isinstance(playback, dict) else {},
            data=payload,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.data)
        payload.update(
            {
                "success": self.success,
                "provider": self.provider,
                "source": self.source or self.provider,
            }
        )
        if self.backend_available is not None:
            payload["backend_available"] = self.backend_available
        if self.playback:
            payload["playback"] = self.playback
        return payload


@dataclass(frozen=True)
class MusicBackendCapabilities:
    """Small capability map for DJConnect music use-cases."""

    supports_search: bool = False
    supports_playlists: bool = False
    supports_queue: bool = False
    supports_outputs: bool = False
    supports_volume: bool = False
    supports_favorites: bool = False
    supports_recently_played: bool = False
    supports_top_items: bool = False
    supports_recommendations: bool = False
    supports_library_profile: bool = False
    supports_shuffle: bool = False
    supports_repeat: bool = False
    supports_seek: bool = False
    supports_transfer_or_output_selection: bool = False


@dataclass(frozen=True)
class MusicBackendObservationCapabilities:
    """Bounded Playback Observation Boundary capability report."""

    supports_current_playback_status: bool = False
    supports_media_change_observation: bool = False
    observation_mode_event: bool = False
    observation_mode_polling: bool = False
    supports_playback_instance_identity: bool = False
    supports_continue_stage2: bool = False


class MusicBackend(Protocol):
    """Protocol implemented by DJConnect music backend adapters."""

    provider: str
    capabilities: MusicBackendCapabilities
    observation_capabilities: MusicBackendObservationCapabilities

    async def handle_command(
        self,
        command: MusicCommand | str,
        value: Any = None,
        *,
        play: bool | None = None,
    ) -> dict[str, Any]:
        """Run a backend command and return the DJConnect-compatible shape."""


class MusicBackendCapabilityError(SpotifyBackendError):
    """Raised when the selected backend cannot serve a use-case."""

    def __init__(
        self,
        command: str,
        capability: str | None = None,
        backend: str | None = None,
    ) -> None:
        self.command = command
        self.capability = capability or _CAPABILITY_BY_COMMAND.get(command) or "unknown"
        self.backend = backend or "unknown"
        super().__init__(unsupported_capability_message(self.capability, self.backend))


class SpotifyDirectBackend:
    """Adapter that keeps Spotify Direct behind the use-case/backend boundary."""

    provider = "spotify_direct"
    capabilities = MusicBackendCapabilities(
        supports_search=True,
        supports_playlists=True,
        supports_queue=True,
        supports_outputs=True,
        supports_volume=True,
        supports_favorites=True,
        supports_recently_played=True,
        supports_top_items=True,
        supports_recommendations=True,
        supports_library_profile=True,
        supports_shuffle=True,
        supports_repeat=True,
        supports_seek=True,
        supports_transfer_or_output_selection=True,
    )
    observation_capabilities = MusicBackendObservationCapabilities(
        supports_current_playback_status=True,
        supports_media_change_observation=True,
        observation_mode_polling=True,
    )

    def __init__(self, hass: HomeAssistant, runtime: Any) -> None:
        self.hass = hass
        self.runtime = runtime

    async def handle_command(
        self,
        command: MusicCommand | str,
        value: Any = None,
        *,
        play: bool | None = None,
    ) -> dict[str, Any]:
        """Delegate to the existing Spotify Direct backend implementation."""
        command_value = normalize_music_command(command)
        return await _handle_spotify_command(
            self.hass,
            self.runtime,
            command_value,
            value,
            play=play,
        )


class MusicAssistantBackend:
    """Music Assistant adapter using Home Assistant media_player services."""

    provider = MUSIC_BACKEND_MUSIC_ASSISTANT
    capabilities = MusicBackendCapabilities(
        supports_search=False,
        supports_playlists=False,
        supports_queue=False,
        supports_outputs=True,
        supports_volume=True,
        supports_favorites=False,
        supports_recently_played=False,
        supports_top_items=False,
        supports_recommendations=False,
        supports_library_profile=False,
        supports_shuffle=False,
        supports_repeat=False,
        supports_seek=False,
        supports_transfer_or_output_selection=False,
    )
    observation_capabilities = MusicBackendObservationCapabilities()

    def __init__(self, hass: HomeAssistant, runtime: Any) -> None:
        self.hass = hass
        self.runtime = runtime

    @property
    def player_entity_id(self) -> str:
        return str(self.runtime.config.get(CONF_MUSIC_ASSISTANT_PLAYER) or "").strip()

    async def handle_command(
        self,
        command: MusicCommand | str,
        value: Any = None,
        *,
        play: bool | None = None,
    ) -> dict[str, Any]:
        """Handle DJConnect commands through a configured Music Assistant player."""
        player = self.player_entity_id
        if not player:
            raise SpotifyBackendError("Music Assistant player is not configured")
        normalized = normalize_music_command(command)
        if normalized == "status":
            return {"success": True, "playback": self._playback_state(player)}
        if normalized == "devices":
            return {
                "success": True,
                "devices": [self._output_item(player)],
                "outputs": [self._output_item(player)],
            }
        if normalized == "play":
            if value:
                await self._call_media_player(
                    "play_media",
                    player,
                    media_content_id=_media_content_id(value),
                    media_content_type=_media_content_type(value),
                )
            else:
                await self._call_media_player("media_play", player)
            return {"success": True, "playback": self._playback_state(player)}
        if normalized == "pause":
            await self._call_media_player("media_pause", player)
            return {"success": True, "playback": self._playback_state(player)}
        if normalized == "next":
            await self._call_media_player("media_next_track", player)
            return {"success": True, "playback": self._playback_state(player)}
        if normalized == "previous":
            await self._call_media_player("media_previous_track", player)
            return {"success": True, "playback": self._playback_state(player)}
        if normalized == "set_volume":
            await self._call_media_player(
                "volume_set",
                player,
                volume_level=_volume_level(value),
            )
            return {"success": True, "playback": self._playback_state(player)}
        if normalized == "set_output":
            return {"success": True, "playback": self._playback_state(player)}
        raise MusicBackendCapabilityError(
            normalized,
            _CAPABILITY_BY_COMMAND.get(normalized),
            self.provider,
        )

    async def _call_media_player(self, service: str, entity_id: str, **data: Any) -> None:
        services = getattr(self.hass, "services", None)
        caller = getattr(services, "async_call", None)
        if not callable(caller):
            raise SpotifyBackendError("Home Assistant media_player services are unavailable")
        await caller(
            "media_player",
            service,
            {"entity_id": entity_id, **data},
            blocking=True,
        )

    def _playback_state(self, entity_id: str) -> dict[str, Any]:
        state = _state_for_entity(self.hass, entity_id)
        attrs = getattr(state, "attributes", {}) or {}
        status = str(getattr(state, "state", "") or "")
        title = attrs.get("media_title")
        artist = attrs.get("media_artist")
        album = attrs.get("media_album_name")
        image_url = attrs.get("entity_picture") or attrs.get("media_image_url")
        volume = attrs.get("volume_level")
        volume_percent = None
        try:
            volume_percent = int(round(float(volume) * 100))
        except (TypeError, ValueError):
            pass
        return {
            "has_playback": bool(title or artist or status in {"playing", "paused"}),
            "is_playing": status == "playing",
            "state": status,
            "provider": self.provider,
            "source": self.provider,
            "device": self._output_item(entity_id),
            "title": title,
            "track_name": title,
            "artist": artist,
            "album": album,
            "album_name": album,
            "image_url": image_url,
            "entity_picture": image_url,
            "volume": volume_percent,
            "volume_percent": volume_percent,
            "media_type": attrs.get("media_content_type"),
            "uri": attrs.get("media_content_id"),
        }

    def _output_item(self, entity_id: str) -> dict[str, Any]:
        state = _state_for_entity(self.hass, entity_id)
        attrs = getattr(state, "attributes", {}) or {}
        return {
            "id": entity_id,
            "entity_id": entity_id,
            "name": attrs.get("friendly_name") or entity_id,
            "provider": self.provider,
            "source": self.provider,
            "is_active": str(getattr(state, "state", "") or "") == "playing",
            "can_play": True,
        }


class DJConnectUseCases:
    """Typed DJConnect music use-cases backed by the selected adapter."""

    def __init__(
        self,
        hass: HomeAssistant,
        runtime: Any,
        *,
        backend: MusicBackend | None = None,
    ) -> None:
        self.hass = hass
        self.runtime = runtime
        self.backend = backend or _selected_backend(hass, runtime)

    async def command(
        self,
        command: MusicCommand | str,
        value: Any = None,
        *,
        play: bool | None = None,
    ) -> dict[str, Any]:
        """Run a normalized DJConnect music command through the backend."""
        normalized = normalize_music_command(command)
        self._ensure_capability(normalized)
        result = await self.backend.handle_command(normalized, value, play=play)
        return self._normalize_result(result)

    async def play_music(self, value: Any = None) -> dict[str, Any]:
        return await self.command("play", value)

    async def get_current_track(self) -> dict[str, Any]:
        return await self.command("status")

    async def get_queue(self) -> dict[str, Any]:
        return await self.command("queue")

    async def get_playlists(self, value: Any = None) -> dict[str, Any]:
        return await self.command("playlists", value)

    async def pause_music(self) -> dict[str, Any]:
        return await self.command("pause")

    async def resume_music(self) -> dict[str, Any]:
        return await self.command("play")

    async def next_track(self) -> dict[str, Any]:
        return await self.command("next")

    async def previous_track(self) -> dict[str, Any]:
        return await self.command("previous")

    async def set_volume(self, value: Any) -> dict[str, Any]:
        return await self.command("set_volume", value)

    async def set_output(self, value: Any, *, play: bool | None = None) -> dict[str, Any]:
        return await self.command("set_output", value, play=play)

    async def set_shuffle(self, value: Any) -> dict[str, Any]:
        return await self.command("set_shuffle", value)

    async def set_repeat(self, value: Any) -> dict[str, Any]:
        return await self.command("set_repeat", value)

    async def favorite_current_track(self, value: Any = True) -> dict[str, Any]:
        return await self.command("set_current_track_favorite", value)

    async def recommend_music(self, value: Any) -> dict[str, Any]:
        return await self.command("artist_recommendations", value)

    def _ensure_capability(self, command: str) -> None:
        capability = _CAPABILITY_BY_COMMAND.get(command)
        if capability and not getattr(self.backend.capabilities, capability, False):
            raise MusicBackendCapabilityError(
                command,
                capability,
                getattr(self.backend, "provider", None),
            )

    def _normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        backend_result = MusicBackendResult.from_mapping(
            result,
            provider=self.backend.provider,
        )
        if backend_result.success and backend_result.backend_available is None:
            backend_result = MusicBackendResult(
                success=backend_result.success,
                provider=backend_result.provider,
                source=backend_result.source,
                backend_available=True,
                playback=backend_result.playback,
                data=backend_result.data,
            )
        return backend_result.to_dict()


_CAPABILITY_BY_COMMAND = {
    MusicCommand.DEVICES.value: "supports_outputs",
    MusicCommand.SET_OUTPUT.value: "supports_outputs",
    MusicCommand.QUEUE.value: "supports_queue",
    MusicCommand.PLAYLISTS.value: "supports_playlists",
    MusicCommand.SEARCH_PLAYLISTS.value: "supports_playlists",
    MusicCommand.SEARCH_TRACKS.value: "supports_search",
    MusicCommand.SEARCH_ALBUMS.value: "supports_search",
    MusicCommand.SEARCH_MEDIA.value: "supports_search",
    MusicCommand.SET_VOLUME.value: "supports_volume",
    MusicCommand.SAVE_CURRENT_TRACK.value: "supports_favorites",
    MusicCommand.SET_CURRENT_TRACK_FAVORITE.value: "supports_favorites",
    MusicCommand.TOGGLE_CURRENT_TRACK_FAVORITE.value: "supports_favorites",
    MusicCommand.RECENTLY_PLAYED.value: "supports_recently_played",
    MusicCommand.ARTIST_RECOMMENDATIONS.value: "supports_recommendations",
    MusicCommand.LISTENING_PROFILE.value: "supports_library_profile",
    MusicCommand.SET_SHUFFLE.value: "supports_shuffle",
    MusicCommand.SET_REPEAT.value: "supports_repeat",
    MusicCommand.SEEK_RELATIVE.value: "supports_seek",
}


def normalize_music_command(command: MusicCommand | str) -> str:
    """Return the canonical backend command string."""
    if isinstance(command, MusicCommand):
        return command.value
    return str(command or "").strip().lower()


def _selected_backend(hass: HomeAssistant, runtime: Any) -> MusicBackend:
    backend = str(
        getattr(runtime, "profile_context_backend_id", "")
        or getattr(runtime, "config", {}).get(CONF_MUSIC_BACKEND)
        or DEFAULT_MUSIC_BACKEND
    ).strip()
    if backend == MUSIC_BACKEND_MUSIC_ASSISTANT:
        return MusicAssistantBackend(hass, runtime)
    return SpotifyDirectBackend(hass, runtime)


def music_backend_metadata(hass: HomeAssistant, runtime: Any) -> dict[str, Any]:
    """Return the client-visible selected music backend contract."""
    backend = str(
        getattr(runtime, "profile_context_backend_id", "")
        or getattr(runtime, "config", {}).get(CONF_MUSIC_BACKEND)
        or DEFAULT_MUSIC_BACKEND
    ).strip()
    if backend not in MUSIC_BACKEND_NAMES:
        backend = DEFAULT_MUSIC_BACKEND
    adapter = _selected_backend(hass, runtime)
    target_player = {}
    if backend == MUSIC_BACKEND_MUSIC_ASSISTANT:
        player_id = str(
            getattr(runtime, "config", {}).get(CONF_MUSIC_ASSISTANT_PLAYER) or ""
        ).strip()
        if player_id:
            state = _state_for_entity(hass, player_id)
            attrs = getattr(state, "attributes", {}) or {}
            target_player = {
                "id": player_id,
                "name": attrs.get("friendly_name") or player_id,
            }
    available = True
    error = None
    if (
        backend == MUSIC_BACKEND_SPOTIFY_DIRECT
        and not str(getattr(runtime, "config", {}).get(CONF_SPOTIFY_REFRESH_TOKEN) or "").strip()
    ):
        available = False
        error = {
            "code": "spotify_oauth_required",
            "message": "Spotify OAuth is required before Spotify Direct can play music.",
        }
    if backend == MUSIC_BACKEND_MUSIC_ASSISTANT and not target_player:
        available = False
        error = {
            "code": "music_assistant_player_not_found",
            "message": "The selected Music Assistant player is not configured.",
        }
    return {
        "music_backend": backend,
        "music_backend_name": MUSIC_BACKEND_NAMES[backend],
        "music_backend_available": available,
        "music_backend_revision": _int_revision(
            getattr(runtime, "config", {}).get(CONF_MUSIC_BACKEND_REVISION)
        ),
        "music_backend_capabilities": dict(adapter.capabilities.__dict__),
        "music_backend_observation_capabilities": dict(adapter.observation_capabilities.__dict__),
        "music_target_player": target_player,
        "music_backend_error": error,
    }


def music_backend_action_fields(
    runtime: Any,
    kind: str,
    item_id: str,
    image_url: str = "",
    title: str = "",
    subtitle: str = "",
) -> dict[str, Any]:
    """Return backend-aware playback action metadata for client contracts."""
    config = getattr(runtime, "config", {}) if runtime is not None else {}
    backend = str(config.get(CONF_MUSIC_BACKEND) or DEFAULT_MUSIC_BACKEND).strip()
    if backend not in MUSIC_BACKEND_NAMES:
        backend = DEFAULT_MUSIC_BACKEND
    revision = _int_revision(config.get(CONF_MUSIC_BACKEND_REVISION))
    provider = (
        MUSIC_BACKEND_MUSIC_ASSISTANT if backend == MUSIC_BACKEND_MUSIC_ASSISTANT else "spotify"
    )
    clean_kind = str(kind or "music").strip().lower() or "music"
    if backend == MUSIC_BACKEND_MUSIC_ASSISTANT:
        value = BackendActionValue(
            item_id=item_id,
            provider=provider,
            media_type=clean_kind,
            title=title,
            subtitle=subtitle,
            image_url=image_url,
            target_player_id=str(config.get(CONF_MUSIC_ASSISTANT_PLAYER) or ""),
        )
    else:
        value = BackendActionValue(
            uri=item_id,
            title=title,
            subtitle=subtitle,
            image_url=image_url,
        )
    return {
        "backend": backend,
        "provider": provider,
        "music_backend_revision": revision,
        "value": value.to_dict(),
    }


def build_playback_action(
    runtime: Any,
    item: dict[str, Any],
    kind: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Build a backend-aware client playback action from an intent item."""
    if not isinstance(item, dict):
        return {}
    item_id = _playback_item_id(item)
    clean_kind = str(kind or _playback_item_kind(item, item_id)).strip().lower() or "music"
    title, subtitle, image_url = _playback_action_text(item, item_id)
    action = PlaybackAction(
        id=item_id or str(item.get("id") or "").strip(),
        title=title,
        subtitle=subtitle,
        kind=clean_kind,
        image_url=image_url,
        reason=reason,
        **_playback_action_backend_fields(runtime, clean_kind, item_id, image_url, title, subtitle),
    ).to_dict()
    if item_id and item_id.startswith("spotify:"):
        action["uri"] = item_id
    context_uri = str(item.get("context_uri") or "").strip()
    if context_uri:
        action["context_uri"] = context_uri
        if clean_kind == "track":
            action["offset_uri"] = item_id
    if image_url:
        action["thumbnail_url"] = image_url
    return {key: value for key, value in action.items() if value not in ("", None, [], {})}


def _playback_action_text(item: dict[str, Any], item_id: str) -> tuple[str, str, str]:
    """Extract the display fields shared by all client playback actions."""
    title = _first_item_text(item, "title", "track_name", "name") or item_id
    subtitle = _first_item_text(item, "subtitle", "artist", "artist_name", "album_name", "owner")
    image_url = _first_item_text(
        item,
        "image_url",
        "thumbnail_url",
        "album_image_url",
        "artist_image_url",
        "album_art_url",
        "media_image_url",
        "entity_picture",
    )
    return title, subtitle, image_url


def _first_item_text(item: dict[str, Any], *keys: str) -> str:
    """Return the first non-empty display property from an intent item."""
    return str(next((item.get(key) for key in keys if item.get(key)), "") or "").strip()


def unsupported_capability_message(capability: str, backend: str) -> str:
    """Return a safe user-facing unsupported capability message."""
    labels = {
        "supports_top_items": "top artists or tracks",
        "supports_recently_played": "recent listening history",
        "supports_favorites": "favorites or liked tracks",
        "supports_queue": "queue browsing",
        "supports_outputs": "output selection",
        "supports_volume": "volume control",
        "supports_shuffle": "shuffle control",
        "supports_repeat": "repeat control",
        "supports_recommendations": "recommendations",
        "supports_library_profile": "music profile analysis",
        "supports_search": "music search",
    }
    feature = labels.get(capability, "this music feature")
    return f"The selected music backend does not provide {feature}."


def _int_revision(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _state_for_entity(hass: HomeAssistant, entity_id: str) -> Any:
    states = getattr(hass, "states", None)
    getter = getattr(states, "get", None)
    return getter(entity_id) if callable(getter) else None


def _media_content_id(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("uri", "id", "media_content_id", "item_id"):
            candidate = str(value.get(key) or "").strip()
            if candidate:
                return candidate
    return str(value or "").strip()


def _media_content_type(value: Any) -> str:
    if isinstance(value, dict):
        return str(
            value.get("media_type")
            or value.get("type")
            or value.get("media_content_type")
            or "music"
        )
    return "music"


def _volume_level(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))


def _playback_action_backend_fields(
    runtime: Any,
    kind: str,
    item_id: str,
    image_url: str,
    title: str,
    subtitle: str,
) -> dict[str, Any]:
    fields = music_backend_action_fields(runtime, kind, item_id, image_url, title, subtitle)
    return {
        "backend": fields["backend"],
        "provider": fields["provider"],
        "music_backend_revision": fields["music_backend_revision"],
        "value": BackendActionValue(**fields["value"]),
    }


def _playback_item_id(item: dict[str, Any]) -> str:
    for key in (
        "uri",
        "current_uri",
        "context_uri",
        "playlist_uri",
        "album_uri",
        "artist_uri",
        "item_id",
        "media_content_id",
        "id",
    ):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def _playback_item_kind(item: dict[str, Any], item_id: str) -> str:
    spotify_kind = _spotify_uri_kind(item_id)
    if spotify_kind:
        return spotify_kind
    kind = (
        str(item.get("media_type") or item.get("type") or item.get("kind") or "music")
        .strip()
        .lower()
    )
    return kind if kind in {"track", "album", "artist", "playlist"} else "music"


def _spotify_uri_kind(uri: str) -> str:
    parts = str(uri or "").split(":")
    if (
        len(parts) >= 3
        and parts[0] == "spotify"
        and parts[1] in {"track", "album", "artist", "playlist"}
    ):
        return parts[1]
    return ""


async def run_music_command(
    hass: HomeAssistant,
    runtime: Any,
    command: MusicCommand | str,
    value: Any = None,
    *,
    play: bool | None = None,
) -> dict[str, Any]:
    """Run a DJConnect music command through the use-case layer."""
    return await DJConnectUseCases(hass, runtime).command(command, value, play=play)


async def run_text_command(
    hass: HomeAssistant,
    runtime: Any,
    text: str,
    *,
    play: bool = True,
    correct_stt: bool = False,
    user_id: str | None = None,
    memory_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a natural-language DJConnect command through the use-case boundary."""
    from .processor import process_text_command
    from .profile_context import ProfilePlatformNotConfigured, async_apply_profile_context

    payload = dict(memory_payload or {})
    if payload:
        try:
            await async_apply_profile_context(
                hass,
                runtime,
                payload,
                user_id=user_id,
                request_source=str(payload.get("request_source") or "voice_endpoint"),
            )
        except ProfilePlatformNotConfigured:
            pass
    try:
        return await process_text_command(
            hass,
            runtime,
            text,
            play=play,
            correct_stt=correct_stt,
            memory_payload=payload or memory_payload,
            user_id=user_id,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        kwargs: dict[str, Any] = {
            "play": play,
            "correct_stt": correct_stt,
        }
        if user_id is not None and "user_id" not in str(exc):
            kwargs["user_id"] = user_id
        if (payload or memory_payload) and "memory_payload" not in str(exc):
            kwargs["memory_payload"] = payload or memory_payload
        return await process_text_command(hass, runtime, text, **kwargs)
