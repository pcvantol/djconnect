"""Server-side Music DNA for Ask DJ context."""
from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import logging
import re
import uuid
from typing import Any, Callable

from .const import CONF_CLIENT_TYPE, CONF_DEVICE_ID, CONF_DEVICE_NAME
from .mood import mood_zone_for_value

_LOGGER = logging.getLogger(__name__)

STORE_KEY = "djconnect_music_dna"
STORE_VERSION = 1
MAX_SESSION_TURNS = 20
MAX_RECENT_TRACKS = 20
MAX_CHAT_FACTS = 20
MAX_PROFILE_SNAPSHOTS = 12
MAX_TEXT_LENGTH = 500
LISTENING_PROFILE_TTL_SECONDS = 6 * 60 * 60
PENDING_FOLLOWUP_TTL_SECONDS = 10 * 60
SECRET_KEY_FRAGMENTS = ("token", "password", "secret", "authorization")


class MusicDNAManager:
    """Manage compact server-side Music DNA for Ask DJ."""

    def __init__(self, hass: Any | None = None, store: Any | None = None) -> None:
        self.hass = hass
        self._store = store if store is not None else self._create_store(hass)
        self._loaded = False
        self._data: dict[str, Any] = {"version": STORE_VERSION, "memories": {}}
        self._session: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=MAX_SESSION_TURNS)
        )

    @property
    def data(self) -> dict[str, Any]:
        """Return the in-memory persistent data cache."""
        return self._data

    async def async_load(self) -> dict[str, Any]:
        """Load persistent Music DNA from Home Assistant Store."""
        if self._loaded:
            return self._data
        loaded: dict[str, Any] | None = None
        if self._store is not None:
            loaded = await self._store.async_load()
        self._data = _normalize_store_data(loaded)
        self._loaded = True
        return self._data

    async def async_save(self) -> None:
        """Persist compact Music DNA."""
        await self.async_load()
        if self._store is not None:
            await self._store.async_save(_compact_store_data(self._data))

    async def async_clear(self, music_dna_key: str | None = None) -> None:
        """Clear all memory or one resolved memory key."""
        await self.async_load()
        if music_dna_key:
            key = _safe_music_dna_key(music_dna_key)
            memory = self._memory_for_key(key)
            generation = int(memory.get("generation") or 0) + 1
            enabled = bool(memory.get("enabled"))
            self._data["memories"][key] = {
                "enabled": enabled,
                "generation": generation,
                "clear_requested_at": _now(),
                "updated_at": _now(),
            }
            self._session.pop(key, None)
        else:
            self._data = {"version": STORE_VERSION, "memories": {}}
            self._session.clear()
        await self.async_save()

    async def async_mark_clear_required(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Clear server-side history and mark clients to clear local chat cache."""
        await self.async_load()
        key = resolve_music_dna_key(runtime, payload, user_id=user_id)
        await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        generation = int(memory.get("generation") or 0) + 1
        preserved = {
            "user_id": memory.get("user_id"),
            "device_id": memory.get("device_id"),
            "client_type": memory.get("client_type"),
            "device_name": memory.get("device_name"),
            "generation": generation,
            "clear_requested_at": _now(),
            "last_seen": _now(),
            "updated_at": _now(),
        }
        self._data["memories"][key] = {
            name: value
            for name, value in preserved.items()
            if value not in (None, "", [], {})
        }
        self._session.pop(key, None)
        await self.async_save()
        return {
            "music_dna_key": key,
            "ask_dj_clear_required": True,
            "generation": generation,
            "clear_requested_at": self._data["memories"][key].get("clear_requested_at"),
        }

    async def async_history_state(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
        client_generation: int | None = None,
    ) -> dict[str, Any]:
        """Return whether a client should clear local Ask DJ chat history."""
        await self.async_load()
        key = await self.async_update_client_metadata(
            runtime,
            payload,
            user_id=user_id,
        )
        memory = self._memory_for_key(key)
        generation = int(memory.get("generation") or 0)
        clear_required = bool(
            memory.get("clear_requested_at")
            and (client_generation is None or int(client_generation) < generation)
        )
        return {
            "music_dna_key": key,
            "ask_dj_clear_required": clear_required,
            "generation": generation,
            "clear_requested_at": memory.get("clear_requested_at"),
        }

    async def async_update_client_metadata(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> str:
        """Resolve memory key and update client metadata."""
        await self.async_load()
        payload = payload or {}
        key = resolve_music_dna_key(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        now = _now()
        device_id = _first_text(
            payload.get(CONF_DEVICE_ID),
            getattr(runtime, "device_status", {}).get(CONF_DEVICE_ID),
            getattr(runtime, "pairing_device_id", None),
            getattr(runtime, "config", {}).get(CONF_DEVICE_ID),
        )
        client_type = _first_text(
            payload.get(CONF_CLIENT_TYPE),
            getattr(runtime, "device_status", {}).get(CONF_CLIENT_TYPE),
            _call_or_none(getattr(runtime, "client_type", None)),
            getattr(runtime, "config", {}).get(CONF_CLIENT_TYPE),
        )
        device_name = _first_text(
            payload.get(CONF_DEVICE_NAME),
            payload.get("name"),
            getattr(runtime, "device_status", {}).get(CONF_DEVICE_NAME),
            getattr(runtime, "config", {}).get(CONF_DEVICE_NAME),
        )
        memory.update(
            {
                "enabled": bool(memory.get("enabled")),
                "user_id": _clean_text(user_id or payload.get("user_id")),
                "device_id": device_id,
                "client_type": client_type,
                "device_name": device_name,
                "last_seen": now,
                "updated_at": now,
            }
        )
        if not self._memory_enabled(memory):
            await self.async_save()
            return key
        mood = _clean_mood(payload.get("mood"))
        if mood is not None:
            _record_mood_signal(memory, mood)
        dj_style = _clean_text(payload.get("dj_style"))
        if dj_style:
            memory["dj_style"] = dj_style
        preferred_device_id = _clean_text(payload.get("preferred_device_id"))
        if preferred_device_id:
            memory["preferred_device_id"] = preferred_device_id
        _update_time_context(memory)
        await self.async_save()
        return key

    async def async_set_enabled(
        self,
        runtime: Any,
        enabled: bool,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Persist the user's Music DNA opt-in state."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        previous = bool(memory.get("enabled"))
        memory["enabled"] = bool(enabled)
        memory["consent_updated_at"] = _now()
        memory["updated_at"] = _now()
        if previous and not enabled:
            self._clear_knowledge(memory)
            memory["clear_requested_at"] = _now()
            memory["generation"] = int(memory.get("generation") or 0) + 1
            self._session.pop(key, None)
        elif enabled:
            payload = payload or {}
            mood = _clean_mood(payload.get("mood"))
            if mood is not None:
                _record_mood_signal(memory, mood)
            dj_style = _clean_text(payload.get("dj_style"))
            if dj_style:
                memory["dj_style"] = dj_style
            _update_time_context(memory)
        await self.async_save()
        return {
            "success": True,
            "music_dna_key": key,
            "enabled": bool(memory.get("enabled")),
            "generation": int(memory.get("generation") or 0),
            "clear_requested_at": memory.get("clear_requested_at"),
            "consent_updated_at": memory.get("consent_updated_at"),
        }

    async def async_profile(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Return a client-facing structured Music DNA profile."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        enabled = self._memory_enabled(memory)
        profile = _profile_payload(memory) if enabled else {}
        return {
            "success": True,
            "music_dna_key": key,
            "enabled": enabled,
            "generation": int(memory.get("generation") or 0),
            "clear_requested_at": memory.get("clear_requested_at"),
            "updated_at": memory.get("updated_at"),
            "profile": profile,
            "sources": [{"source": "djconnect_music_dna", "kind": "source", "title": "Music DNA"}],
        }

    async def async_import_profile(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Overwrite server-side Music DNA with an imported client profile."""
        payload = payload or {}
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        if not self._memory_enabled(memory):
            return {
                "success": False,
                "error": "music_dna_not_enabled",
                "message": "Music DNA must be enabled before import.",
            }, 409
        imported = _import_profile_payload(payload)
        if imported is None:
            return {
                "success": False,
                "error": "invalid_music_dna_profile",
                "message": "Music DNA import requires a valid profile response.",
            }, 400
        metadata = {
            "user_id": memory.get("user_id"),
            "device_id": memory.get("device_id"),
            "client_type": memory.get("client_type"),
            "device_name": memory.get("device_name"),
            "enabled": True,
            "generation": int(memory.get("generation") or 0) + 1,
            "consent_updated_at": memory.get("consent_updated_at"),
            "imported_at": _now(),
            "updated_at": _now(),
        }
        self._data.setdefault("memories", {})[key] = _memory_from_profile_payload(
            imported,
            metadata,
        )
        self._session.pop(key, None)
        await self.async_save()
        return await self.async_profile(runtime, payload, user_id=user_id), 200

    async def async_export_profile(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Return a stable Music DNA export envelope for client downloads."""
        profile = await self.async_profile(runtime, payload, user_id=user_id)
        payload = payload or {}
        return {
            "success": True,
            "format": "djconnect.music_dna.export",
            "schema_version": 1,
            "exported_at": _now(),
            "exported_by_client_type": _clean_text(
                payload.get(CONF_CLIENT_TYPE)
                or getattr(runtime, "device_status", {}).get(CONF_CLIENT_TYPE)
                or _call_or_none(getattr(runtime, "client_type", None))
            ),
            "app_version": _clean_text(payload.get("app_version") or payload.get("version")),
            "profile": profile,
        }

    async def async_append_runtime_message(
        self,
        runtime: Any,
        role: str,
        text: str,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> str:
        """Append a bounded runtime-only session message."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        message = {
            "role": _clean_text(role) or "user",
            "text": _clean_text(text),
            "created_at": _now(),
        }
        if message["text"]:
            self._session[key].append(message)
        return key

    async def async_update_last_ask_dj(
        self,
        runtime: Any,
        *,
        input_text: str,
        result: dict[str, Any],
        payload: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> str:
        """Update persistent Ask DJ context and runtime session history."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        if not self._memory_enabled(memory):
            return key
        intent = result.get("intent") if isinstance(result, dict) else {}
        playback = result.get("playback") if isinstance(result, dict) else {}
        response_text = _clean_text(
            result.get("dj_text") or result.get("text") if isinstance(result, dict) else None
        )
        action = _clean_text(_intent_value(intent, "action") or _intent_value(intent, "intent"))
        track = _track_from_context(playback, intent, result)
        speaker = _speaker_from_playback(playback)
        now = _now()
        last_ask = {
            "input": _clean_text(input_text),
            "intent": _clean_text(_intent_value(intent, "intent") or _intent_value(intent, "type")),
            "response_text": response_text,
            "action": action,
            "track": track,
            "speaker": speaker,
            "playback_actions": _sanitize_value(result.get("playback_actions") if isinstance(result, dict) else []),
            "created_at": now,
        }
        memory["last_ask_dj"] = _compact_dict(last_ask)
        memory["updated_at"] = now
        self._session[key].append(
            {
                "role": "user",
                "text": _clean_text(input_text),
                "created_at": now,
            }
        )
        if response_text:
            self._session[key].append(
                {
                    "role": "assistant",
                    "text": response_text,
                    "created_at": now,
                }
            )
        if track:
            self.update_recent_tracks(key, track)
        await self.async_save()
        _LOGGER.debug(
            "DJConnect Music DNA updated key=%s client_type=%s has_track=%s has_response=%s",
            key,
            memory.get("client_type") or "unknown",
            bool(track),
            bool(response_text),
        )
        return key

    async def async_record_blocked_music_preference(
        self,
        runtime: Any,
        item: dict[str, Any],
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> str:
        """Persist a compact negative music preference for future Ask DJ choices."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        if not self._memory_enabled(memory):
            return key
        kind = _clean_text(item.get("kind") or "artist") or "artist"
        name = _clean_text(item.get("name") or item.get("title") or item.get("artist"))
        if not name:
            return key
        record = {
            "kind": kind,
            "name": name,
            "reason": _clean_text(item.get("reason") or "user_dislike"),
            "created_at": _now(),
        }
        key_name = "blocked_artists" if kind == "artist" else "blocked_items"
        existing = memory.get(key_name)
        if not isinstance(existing, list):
            existing = []
        deduped = [
            value
            for value in existing
            if not (
                isinstance(value, dict)
                and str(value.get("kind") or "").lower() == kind.lower()
                and str(value.get("name") or "").lower() == name.lower()
            )
        ]
        memory[key_name] = [record, *deduped][:MAX_CHAT_FACTS]
        memory["updated_at"] = _now()
        await self.async_save()
        return key

    def update_recent_tracks(self, music_dna_key: str, track: dict[str, Any]) -> None:
        """Update bounded recent track context."""
        key = _safe_music_dna_key(music_dna_key)
        memory = self._memory_for_key(key)
        if not self._memory_enabled(memory):
            return
        recent = memory.get("recent_tracks")
        if not isinstance(recent, list):
            recent = []
        compact_track = _compact_track(track)
        if not compact_track:
            return
        identity = _track_identity(compact_track)
        last_identity = _clean_text(memory.get("last_playback_track_identity"))
        is_new_play_signal = bool(identity and identity != last_identity)
        deduped = [
            item
            for item in recent
            if _track_identity(item if isinstance(item, dict) else {}) != identity
        ]
        memory["recent_tracks"] = [compact_track, *deduped][:MAX_RECENT_TRACKS]
        if identity:
            memory["last_playback_track_identity"] = identity
        artists = _track_artists(compact_track)
        if artists and is_new_play_signal:
            counts = memory.get("artist_play_counts")
            if not isinstance(counts, dict):
                counts = {}
            for artist in artists:
                counts[artist] = int(counts.get(artist) or 0) + 1
            memory["artist_play_counts"] = dict(
                sorted(
                    counts.items(),
                    key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
                )[:50]
            )
            memory["favorite_artists"] = _favorite_artists_from_counts(
                memory["artist_play_counts"],
                memory.get("favorite_artists"),
            )
            duration_seconds = _track_duration_seconds(compact_track)
            if duration_seconds > 0:
                memory["total_play_seconds"] = int(memory.get("total_play_seconds") or 0) + duration_seconds
                artist_seconds = memory.get("artist_play_seconds")
                if not isinstance(artist_seconds, dict):
                    artist_seconds = {}
                for artist in artists:
                    artist_seconds[artist] = int(artist_seconds.get(artist) or 0) + duration_seconds
                memory["artist_play_seconds"] = dict(
                    sorted(
                        artist_seconds.items(),
                        key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
                    )[:50]
                )
                album = _track_album(compact_track)
                if album:
                    album_seconds = memory.get("album_play_seconds")
                    if not isinstance(album_seconds, dict):
                        album_seconds = {}
                    album_seconds[album] = int(album_seconds.get(album) or 0) + duration_seconds
                    memory["album_play_seconds"] = dict(
                        sorted(
                            album_seconds.items(),
                            key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
                        )[:50]
                    )
        genres = compact_track.get("genres")
        if isinstance(genres, list) and genres:
            memory["favorite_genres"] = _unique_texts(
                [*genres, *(memory.get("favorite_genres") or [])]
            )[:20]
        memory["updated_at"] = _now()

    def update_track_insight_energy(
        self,
        music_dna_key: str,
        track: dict[str, Any],
        analysis: dict[str, Any],
    ) -> None:
        """Store compact Track Insight energy signals for the Music DNA profile."""
        key = _safe_music_dna_key(music_dna_key)
        memory = self._memory_for_key(key)
        if not self._memory_enabled(memory):
            return
        compact_track = _compact_track(track)
        if not compact_track:
            return
        energy = _normalized_ratio(analysis.get("energy"))
        danceability = _normalized_ratio(analysis.get("danceability"))
        intensity = _normalized_ratio(analysis.get("intensity"))
        if energy is None and danceability is None and intensity is None:
            return
        signal = {
            **compact_track,
            **({"energy": energy} if energy is not None else {}),
            **({"danceability": danceability} if danceability is not None else {}),
            **({"intensity": intensity} if intensity is not None else {}),
            **({"confidence": _normalized_ratio(analysis.get("confidence"))} if _normalized_ratio(analysis.get("confidence")) is not None else {}),
            **({"genre": _clean_text(analysis.get("genre"))} if _clean_text(analysis.get("genre")) else {}),
            **({"mood": _clean_text(analysis.get("mood"))} if _clean_text(analysis.get("mood")) else {}),
            **({"vibe": _clean_text(analysis.get("vibe"))} if _clean_text(analysis.get("vibe")) else {}),
            "created_at": _now(),
        }
        signals = memory.get("track_insight_energy_signals")
        if not isinstance(signals, list):
            signals = []
        memory["track_insight_energy_signals"] = [signal, *[item for item in signals if isinstance(item, dict)]][:50]
        memory["updated_at"] = _now()

    async def async_update_listening_profile(
        self,
        runtime: Any,
        profile: dict[str, Any],
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> str:
        """Persist a compact backend listening profile snapshot."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        if not self._memory_enabled(memory):
            return key
        compact = _compact_listening_profile(profile)
        if compact:
            memory["listening_profile"] = compact
            memory["listening_profile_snapshots"] = _updated_listening_profile_snapshots(
                memory.get("listening_profile_snapshots"),
                compact,
            )
            memory["last_profile_refresh"] = compact.get("last_profile_refresh") or _now()
            memory["updated_at"] = _now()
            for track in compact.get("recent_tracks") or []:
                if isinstance(track, dict):
                    self.update_recent_tracks(key, track)
            genres = compact.get("inferred_genres")
            if isinstance(genres, list) and genres:
                memory["favorite_genres"] = _unique_texts(
                    [*genres, *(memory.get("favorite_genres") or [])]
                )[:20]
        await self.async_save()
        return key

    async def async_listening_profile(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the stored compact listening profile for the resolved key."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        profile = memory.get("listening_profile")
        return deepcopy(profile) if isinstance(profile, dict) else {}

    async def async_listening_profile_is_fresh(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
        ttl_seconds: int = LISTENING_PROFILE_TTL_SECONDS,
    ) -> bool:
        """Return whether the stored listening profile is still fresh."""
        profile = await self.async_listening_profile(runtime, payload, user_id=user_id)
        refreshed_at = _parse_timestamp(profile.get("last_profile_refresh"))
        if refreshed_at is None:
            return False
        age = (datetime.now(timezone.utc) - refreshed_at).total_seconds()
        return age < max(60, int(ttl_seconds))

    async def async_record_recommendation_play(
        self,
        runtime: Any,
        recommendation: dict[str, Any],
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> str:
        """Record that the user explicitly played an Ask DJ recommendation."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        plays = memory.get("recommendation_plays")
        if not isinstance(plays, list):
            plays = []
        record = _compact_dict(
            {
                "uri": recommendation.get("uri") or recommendation.get("context_uri"),
                "uris": _sanitize_value(recommendation.get("uris")),
                "title": recommendation.get("title"),
                "subtitle": recommendation.get("subtitle"),
                "kind": recommendation.get("kind"),
                "reason": recommendation.get("reason"),
                "source_intent": "personal_music_recommendations",
                "created_at": _now(),
            }
        )
        if record:
            memory["recommendation_plays"] = [record, *plays][:MAX_CHAT_FACTS]
            memory["last_played_recommendation"] = record
            memory["updated_at"] = _now()
            await self.async_save()
        return key

    async def async_record_current_track_favorite(
        self,
        runtime: Any,
        track: dict[str, Any],
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> str:
        """Record a compact positive signal when the user favorites the current track."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        if not self._memory_enabled(memory):
            return key
        compact_track = _compact_track(track)
        if not compact_track:
            return key
        record = {
            **compact_track,
            "source": "ask_dj_current_track_favorite",
            "created_at": _now(),
        }
        favorites = memory.get("recent_favorite_tracks")
        if not isinstance(favorites, list):
            favorites = []
        identity = _track_identity(compact_track)
        deduped = [
            item
            for item in favorites
            if _track_identity(item if isinstance(item, dict) else {}) != identity
        ]
        memory["recent_favorite_tracks"] = [record, *deduped][:MAX_CHAT_FACTS]
        memory["updated_at"] = _now()
        self.update_recent_tracks(key, compact_track)
        await self.async_save()
        return key

    async def async_record_discovery_play(
        self,
        runtime: Any,
        item: dict[str, Any],
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> str:
        """Record that the user played a Music Discovery recommendation."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        if not self._memory_enabled(memory):
            return key
        plays = memory.get("discovery_plays")
        if not isinstance(plays, list):
            plays = []
        record = _compact_dict(
            {
                "discovery_item_id": item.get("id"),
                "section_id": (payload or {}).get("section_id"),
                "kind": item.get("kind"),
                "uri": item.get("uri"),
                "title": item.get("title"),
                "subtitle": item.get("subtitle"),
                "reason": item.get("reason"),
                "reason_sources": _sanitize_value(item.get("reason_sources")),
                "quality_score": item.get("quality_score"),
                "quality_band": item.get("quality_band"),
                "quality_factors": _sanitize_value(item.get("quality_factors")),
                "source": "music_discovery_play",
                "created_at": _now(),
            }
        )
        if record:
            memory["discovery_plays"] = [record, *plays][:MAX_CHAT_FACTS]
            memory["updated_at"] = _now()
            await self.async_save()
        return key

    async def async_store_pending_followup(
        self,
        runtime: Any,
        followup: dict[str, Any],
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Store the latest pending Ask DJ follow-up confirmation."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        now = _now()
        pending = _compact_dict(
            {
                "id": followup.get("id") or f"followup-{uuid.uuid4()}",
                "type": followup.get("type") or "playback_confirmation",
                "question": followup.get("question"),
                "proposed_intent": followup.get("proposed_intent"),
                "proposed_action": followup.get("proposed_action"),
                "proposed_payload": _sanitize_value(followup.get("proposed_payload")),
                "client_id": (payload or {}).get("client_id"),
                "client_type": (payload or {}).get(CONF_CLIENT_TYPE),
                "created_at": now,
                "expires_at": _timestamp_after(PENDING_FOLLOWUP_TTL_SECONDS),
                "handled": False,
            }
        )
        memory["pending_followup"] = pending
        memory["updated_at"] = now
        await self.async_save()
        return deepcopy(pending)

    async def async_pending_followup(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the current pending Ask DJ follow-up, if still open."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        pending = memory.get("pending_followup")
        if not isinstance(pending, dict) or pending.get("handled"):
            return {}
        if _parse_timestamp(pending.get("expires_at")) is not None and _parse_timestamp(pending.get("expires_at")) < datetime.now(timezone.utc):
            pending["handled"] = True
            pending["expired_at"] = _now()
            memory["updated_at"] = _now()
            await self.async_save()
            return {"expired": True, **deepcopy(pending)}
        return deepcopy(pending)

    async def async_consume_pending_followup(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Mark the latest pending Ask DJ follow-up as handled and return it."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = self._memory_for_key(key)
        pending = memory.get("pending_followup")
        if not isinstance(pending, dict) or pending.get("handled"):
            return {}
        now = _now()
        pending["handled"] = True
        pending["handled_at"] = now
        memory["updated_at"] = now
        await self.async_save()
        return deepcopy(pending)

    async def async_context_for_runtime(
        self,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Return compact memory context for prompt enrichment and response metadata."""
        key = await self.async_update_client_metadata(runtime, payload, user_id=user_id)
        memory = deepcopy(self._memory_for_key(key))
        if not self._memory_enabled(memory):
            return {
                "music_dna_key": key,
                "memory": {"enabled": False, "generation": int(memory.get("generation") or 0)},
                "session": [],
            }
        return {
            "music_dna_key": key,
            "memory": _prompt_safe_memory(memory),
            "session": list(self._session.get(key, ())),
        }

    def _memory_for_key(self, key: str) -> dict[str, Any]:
        memories = self._data.setdefault("memories", {})
        safe_key = _safe_music_dna_key(key)
        memory = memories.setdefault(
            safe_key,
            {
                "user_id": None,
                "device_id": None,
                "client_type": None,
                "device_name": None,
                "generation": 0,
                "favorite_artists": [],
                "artist_play_counts": {},
                "favorite_genres": [],
                "track_insight_energy_signals": [],
                "mood_signals": {},
                "blocked_artists": [],
                "blocked_items": [],
                "recent_tracks": [],
                "chat_facts": [],
                "updated_at": _now(),
            },
        )
        return memory

    @staticmethod
    def _memory_enabled(memory: dict[str, Any]) -> bool:
        return bool(memory.get("enabled"))

    @staticmethod
    def _clear_knowledge(memory: dict[str, Any]) -> None:
        for key in (
            "favorite_artists",
            "artist_play_counts",
            "artist_play_seconds",
            "album_play_seconds",
            "total_play_seconds",
            "favorite_genres",
            "track_insight_energy_signals",
            "mood_signals",
            "blocked_artists",
            "blocked_items",
            "recent_tracks",
            "chat_facts",
            "last_ask_dj",
            "listening_profile",
            "listening_time_context",
            "listening_time_signals",
            "listening_time_patterns",
            "last_profile_refresh",
            "recommendation_plays",
            "discovery_plays",
            "last_played_recommendation",
            "last_playback_track_identity",
            "pending_followup",
            "mood",
            "mood_zone",
            "mood_zone_prompt",
            "dj_style",
        ):
            memory.pop(key, None)

    @staticmethod
    def _create_store(hass: Any | None) -> Any | None:
        if hass is None:
            return None
        try:
            from homeassistant.helpers.storage import Store
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Home Assistant Store unavailable for Music DNA", exc_info=True)
            return None
        return Store(hass, STORE_VERSION, STORE_KEY)


def resolve_music_dna_key(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
) -> str:
    """Resolve canonical memory key, preferring HA user identity."""
    payload = payload or {}
    explicit = _clean_text(payload.get("music_dna_key"))
    user = _clean_text(user_id or payload.get("user_id"))
    if user:
        return _safe_music_dna_key(f"user:{user}")
    if explicit:
        return _safe_music_dna_key(explicit)
    device_id = _first_text(
        payload.get(CONF_DEVICE_ID),
        getattr(runtime, "device_status", {}).get(CONF_DEVICE_ID),
        getattr(runtime, "pairing_device_id", None),
        getattr(runtime, "config", {}).get(CONF_DEVICE_ID),
    )
    if device_id:
        return _safe_music_dna_key(device_id)
    entry = getattr(runtime, "entry", None)
    entry_id = _clean_text(getattr(entry, "entry_id", None))
    return _safe_music_dna_key(f"entry:{entry_id or 'default'}")


def prompt_context_text(context: dict[str, Any]) -> str:
    """Return compact prompt context without secrets or raw payloads."""
    memory = context.get("memory") if isinstance(context, dict) else {}
    session = context.get("session") if isinstance(context, dict) else []
    server_history = context.get("server_history") if isinstance(context, dict) else []
    if not isinstance(memory, dict):
        memory = {}
    lines = _memory_prompt_lines(memory)
    lines.extend(_discovery_feedback_prompt_lines(memory))
    time_context_line = _listening_time_context_prompt_line(memory)
    if time_context_line:
        lines.append(time_context_line)
    recent_tracks_line = _recent_tracks_prompt_line(memory)
    if recent_tracks_line:
        lines.append(recent_tracks_line)
    lines.extend(_history_prompt_lines(session, "Recente Ask DJ beurt(en)", 6))
    lines.extend(_history_prompt_lines(server_history, "Server Ask DJ history", 8))
    return "\n".join(line for line in lines if line and not line.endswith(": None"))


def _memory_prompt_lines(memory: dict[str, Any]) -> list[str]:
    """Build the stable Music DNA prompt lines from persisted memory."""
    lines: list[str] = []
    last = memory.get("last_ask_dj") if isinstance(memory.get("last_ask_dj"), dict) else {}
    if last:
        lines.append(f"Laatste Ask DJ vraag: {last.get('input')}")
        lines.append(f"Laatste DJ antwoord: {last.get('response_text')}")
        if last.get("intent"):
            lines.append(f"Laatste intent: {last.get('intent')}")
        track = last.get("track") if isinstance(last.get("track"), dict) else {}
        if track:
            lines.append(
                "Laatste track: "
                + " - ".join(
                    str(value)
                    for value in (track.get("artist"), track.get("title") or track.get("name"))
                    if value
                )
            )
    if memory.get("mood") is not None:
        zone = mood_zone_for_value(memory.get("mood"))
        if zone is not None:
            lines.append(f"Mood/energy: {memory.get('mood')}/100 ({zone.name}: {zone.prompt_hint})")
        else:
            lines.append(f"Mood/energy: {memory.get('mood')}/100")
    if memory.get("dj_style"):
        lines.append(f"DJ stijl: {memory.get('dj_style')}")
    lines.extend(_blocked_music_prompt_lines(memory))
    return lines


def _blocked_music_prompt_lines(memory: dict[str, Any]) -> list[str]:
    """Render explicit artist and item exclusions without raw payload data."""
    lines: list[str] = []
    for key, prefix in (
        ("blocked_artists", "Niet meer draaien volgens gebruiker: "),
        ("blocked_items", "Vermijd deze muziekitems: "),
    ):
        blocked = memory.get(key)
        if not isinstance(blocked, list) or not blocked:
            continue
        names = [
            str(item.get("name") or "").strip()
            for item in blocked[:8]
            if isinstance(item, dict) and item.get("name")
        ]
        if names:
            lines.append(prefix + "; ".join(names))
    return lines


def _discovery_feedback_prompt_lines(memory: dict[str, Any]) -> list[str]:
    """Render eligible Discover feedback in the compact prompt format."""
    lines: list[str] = []
    discovery_feedback = _profile_discovery_feedback(memory)
    if not discovery_feedback.get("eligible"):
        return lines
    accepted_lines = _accepted_discovery_feedback_lines(discovery_feedback)
    if accepted_lines:
        lines.append("Discover gekozen door gebruiker: " + "; ".join(accepted_lines[:5]))
    avoid_lines = _blocked_discovery_feedback_lines(discovery_feedback)
    if avoid_lines:
        lines.append("Discover negatieve feedback: " + "; ".join(avoid_lines[:8]))
    return lines


def _accepted_discovery_feedback_lines(feedback: dict[str, Any]) -> list[str]:
    """Return concise labels for accepted Discover items."""
    lines: list[str] = []
    for item in feedback.get("accepted_items") or []:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        if not title:
            continue
        subtitle = _clean_text(item.get("subtitle"))
        score = item.get("quality_score")
        reason = _clean_text(item.get("reason"))
        lines.append(
            title
            + (f" - {subtitle}" if subtitle else "")
            + (f", kwaliteit {score}" if score is not None else "")
            + (f", reden: {reason}" if reason else "")
        )
    return lines


def _blocked_discovery_feedback_lines(feedback: dict[str, Any]) -> list[str]:
    """Return concise labels for rejected Discover items."""
    artists = [
        f"artiest {item.get('name')}"
        for item in feedback.get("blocked_artists") or []
        if isinstance(item, dict) and item.get("name")
    ]
    items = [
        str(item.get("name"))
        for item in feedback.get("blocked_items") or []
        if isinstance(item, dict) and item.get("name")
    ]
    return artists + items


def _listening_time_context_prompt_line(memory: dict[str, Any]) -> str:
    """Format listening-time context when it is available."""
    time_context = memory.get("listening_time_context")
    if not isinstance(time_context, dict):
        return ""
    day = time_context.get("weekday_name")
    daypart = time_context.get("daypart")
    weekend = "weekend" if time_context.get("is_weekend") else "weekdag"
    hour = time_context.get("hour")
    return "Luistertijdcontext: " + ", ".join(
        str(value)
        for value in (day, daypart, weekend, f"{hour}:00" if hour is not None else "")
        if value
    )


def _recent_tracks_prompt_line(memory: dict[str, Any]) -> str:
    """Format recently played tracks for prompt context."""
    recent = memory.get("recent_tracks")
    if not isinstance(recent, list) or not recent:
        return ""
    names = [
        " - ".join(
            str(value)
            for value in (track.get("artist"), track.get("title") or track.get("name"))
            if value
        )
        for track in recent[:5]
        if isinstance(track, dict)
    ]
    return "Recente tracks: " + "; ".join(name for name in names if name) if names else ""


def _history_prompt_lines(history: Any, label: str, limit: int) -> list[str]:
    """Format a bounded conversational history section."""
    if not isinstance(history, list) or not history:
        return []
    turns = [
        f"{item.get('role')}: {item.get('text')}"
        for item in history[-limit:]
        if isinstance(item, dict) and item.get("text")
    ]
    return [f"{label}: " + " | ".join(turns)] if turns else []


def enrich_user_text_with_memory(user_text: str, context: dict[str, Any]) -> str:
    """Append compact Music DNA context for Assist while preserving user input."""
    memory_text = prompt_context_text(context)
    text = str(user_text or "").strip()
    if not memory_text:
        return text
    return (
        f"{text}\n\n"
        "DJConnect Ask DJ context voor follow-up interpretatie. "
        "Gebruik deze context alleen om voornaamwoorden, sfeer en vervolgvragen te begrijpen; "
        "voer geen andere Home Assistant acties uit op basis van deze context.\n"
        f"{memory_text}"
    )


def _normalize_store_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"version": STORE_VERSION, "memories": {}}
    memories = data.get("memories")
    if not isinstance(memories, dict):
        memories = {}
    return {"version": STORE_VERSION, "memories": deepcopy(memories)}


def _compact_store_data(data: dict[str, Any]) -> dict[str, Any]:
    memories = data.get("memories") if isinstance(data, dict) else {}
    compact: dict[str, Any] = {}
    if isinstance(memories, dict):
        for key, memory in memories.items():
            if isinstance(memory, dict):
                compact[_safe_music_dna_key(key)] = _prompt_safe_memory(memory)
    return {"version": STORE_VERSION, "memories": compact}


def _prompt_safe_memory(memory: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "enabled",
        "consent_updated_at",
        "user_id",
        "device_id",
        "client_type",
        "device_name",
        "preferred_device_id",
        "mood",
        "dj_style",
        "favorite_artists",
        "artist_play_counts",
        "artist_play_seconds",
        "album_play_seconds",
        "total_play_seconds",
        "favorite_genres",
        "track_insight_energy_signals",
        "mood_signals",
        "blocked_artists",
        "blocked_items",
        "recent_tracks",
        "chat_facts",
        "last_ask_dj",
        "listening_profile",
        "listening_profile_snapshots",
        "listening_time_context",
        "listening_time_signals",
        "listening_time_patterns",
        "last_profile_refresh",
        "recommendation_plays",
        "discovery_plays",
        "recent_favorite_tracks",
        "pending_followup",
        "last_seen",
        "updated_at",
        "generation",
        "clear_requested_at",
    }
    result = {
        key: _sanitize_value(value)
        for key, value in memory.items()
        if key in allowed and value not in (None, "", [], {})
    }
    if isinstance(result.get("recent_tracks"), list):
        result["recent_tracks"] = result["recent_tracks"][:MAX_RECENT_TRACKS]
    if isinstance(result.get("track_insight_energy_signals"), list):
        result["track_insight_energy_signals"] = result["track_insight_energy_signals"][:50]
    if isinstance(result.get("chat_facts"), list):
        result["chat_facts"] = result["chat_facts"][:MAX_CHAT_FACTS]
    if isinstance(result.get("blocked_artists"), list):
        result["blocked_artists"] = result["blocked_artists"][:MAX_CHAT_FACTS]
    if isinstance(result.get("blocked_items"), list):
        result["blocked_items"] = result["blocked_items"][:MAX_CHAT_FACTS]
    if isinstance(result.get("recent_favorite_tracks"), list):
        result["recent_favorite_tracks"] = result["recent_favorite_tracks"][:MAX_CHAT_FACTS]
    if isinstance(result.get("discovery_plays"), list):
        result["discovery_plays"] = result["discovery_plays"][:MAX_CHAT_FACTS]
    if isinstance(result.get("artist_play_seconds"), dict):
        result["artist_play_seconds"] = dict(
            sorted(
                result["artist_play_seconds"].items(),
                key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
            )[:50]
        )
    if isinstance(result.get("album_play_seconds"), dict):
        result["album_play_seconds"] = dict(
            sorted(
                result["album_play_seconds"].items(),
                key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
            )[:50]
        )
    if isinstance(result.get("listening_profile"), dict):
        result["listening_profile"] = _compact_listening_profile(result["listening_profile"])
    if isinstance(result.get("listening_profile_snapshots"), list):
        result["listening_profile_snapshots"] = [
            snapshot
            for snapshot in (
                _compact_listening_profile_snapshot(snapshot)
                for snapshot in result["listening_profile_snapshots"][:MAX_PROFILE_SNAPSHOTS]
                if isinstance(snapshot, dict)
            )
            if snapshot
        ]
    if isinstance(result.get("listening_time_patterns"), list):
        result["listening_time_patterns"] = result["listening_time_patterns"][:MAX_CHAT_FACTS]
    return result


def _profile_payload(memory: dict[str, Any]) -> dict[str, Any]:
    listening = memory.get("listening_profile") if isinstance(memory.get("listening_profile"), dict) else {}
    recent_tracks = memory.get("recent_tracks") if isinstance(memory.get("recent_tracks"), list) else []
    favorite_genres = _unique_texts(
        [
            *(memory.get("favorite_genres") or []),
            *(listening.get("inferred_genres") or []),
        ]
    )[:20]
    artist_items = _profile_artist_items(memory, listening)
    artists = [item["name"] for item in artist_items]
    mood = memory.get("mood")
    zone = mood_zone_for_value(mood) if mood is not None else None
    mood_profile = _profile_mood(memory, mood, zone)
    energy_profile = _profile_energy_profile(memory)
    playtime = _profile_playtime(memory)
    listening_rhythm = _profile_listening_rhythm(memory)
    mood_mix = _profile_mood_mix(memory)
    repeat_magnets = _profile_repeat_magnets(memory)
    explicit_positives = _profile_explicit_positives(memory)
    taste_anchors = _profile_taste_anchors(memory, favorite_genres)
    discovery_feedback = _profile_discovery_feedback(memory)
    profile = {
        "summary": _profile_summary(memory, favorite_genres, artists, recent_tracks, playtime),
        "favorite_genres": [{"name": value} for value in favorite_genres],
        "favorite_artists": artist_items,
        "energy_profile": energy_profile,
        "playtime": playtime,
        "listening_rhythm": listening_rhythm,
        "mood_mix": mood_mix,
        "repeat_magnets": repeat_magnets,
        "explicit_positives": explicit_positives,
        "taste_anchors": taste_anchors,
        "recent_tracks": [_compact_track(track) for track in recent_tracks[:MAX_RECENT_TRACKS] if isinstance(track, dict)],
        "recent_favorite_tracks": [
            _compact_track(track)
            for track in (memory.get("recent_favorite_tracks") or [])[:MAX_CHAT_FACTS]
            if isinstance(track, dict)
        ],
        "top_tracks_by_range": listening.get("top_tracks_by_range") or {},
        "top_artists_by_range": listening.get("top_artists_by_range") or {},
        "snapshot_history": memory.get("listening_profile_snapshots") or [],
        "mood": mood_profile,
        "time_patterns": memory.get("listening_time_patterns") or [],
        "recommendation_signals": memory.get("recommendation_plays") or [],
        "blocked_artists": memory.get("blocked_artists") or [],
        "blocked_items": memory.get("blocked_items") or [],
        "discovery_feedback": discovery_feedback,
        "privacy_dashboard": _profile_privacy_dashboard(memory, listening),
        "last_profile_refresh": listening.get("last_profile_refresh") or memory.get("last_profile_refresh"),
        "consent_updated_at": memory.get("consent_updated_at"),
    }
    return _hide_empty_profile_blocks(profile)


def _profile_summary(
    memory: dict[str, Any],
    genres: list[str],
    artists: list[str],
    recent_tracks: list[Any],
    playtime: dict[str, Any] | None = None,
) -> str:
    has_playtime = isinstance(playtime, dict) and int(playtime.get("total_seconds") or 0) > 0
    if not (genres or artists or recent_tracks or memory.get("mood") is not None or has_playtime):
        return "Music DNA is ingeschakeld, maar er is nog weinig profieldata opgebouwd."
    parts: list[str] = []
    if has_playtime:
        parts.append(f"{playtime.get('formatted_total')} luistertijd")
    if recent_tracks:
        parts.append(f"{len(recent_tracks)} recente track(s)")
    if artists:
        parts.append(f"{len(artists)} artiest(en)")
    if genres:
        parts.append("genres zoals " + ", ".join(genres[:3]))
    if memory.get("mood") is not None:
        zone = mood_zone_for_value(memory.get("mood"))
        parts.append(f"een {zone.name if zone is not None else 'bekende'} mood")
    return "Je Music DNA bevat nu " + "; ".join(parts) + "."


def _profile_privacy_dashboard(memory: dict[str, Any], listening: dict[str, Any]) -> dict[str, Any]:
    """Return compact transparency metadata for the Music DNA dashboard."""
    sources: list[dict[str, Any]] = []

    def add_source(source_id: str, label: str, *, enabled: bool, count: int = 0, last_updated: str = "") -> None:
        sources.append(
            {
                "id": source_id,
                "label": label,
                "enabled": bool(enabled),
                **({"count": max(0, int(count))} if count else {}),
                **({"last_updated": last_updated} if last_updated else {}),
            }
        )

    recent_tracks = memory.get("recent_tracks") if isinstance(memory.get("recent_tracks"), list) else []
    favorite_tracks = memory.get("recent_favorite_tracks") if isinstance(memory.get("recent_favorite_tracks"), list) else []
    recommendation_plays = memory.get("recommendation_plays") if isinstance(memory.get("recommendation_plays"), list) else []
    discovery_plays = memory.get("discovery_plays") if isinstance(memory.get("discovery_plays"), list) else []
    blocked_items = memory.get("blocked_items") if isinstance(memory.get("blocked_items"), list) else []
    blocked_artists = memory.get("blocked_artists") if isinstance(memory.get("blocked_artists"), list) else []
    snapshots = memory.get("listening_profile_snapshots") if isinstance(memory.get("listening_profile_snapshots"), list) else []
    energy_signals = memory.get("track_insight_energy_signals") if isinstance(memory.get("track_insight_energy_signals"), list) else []
    mood_signals = memory.get("mood_signals") if isinstance(memory.get("mood_signals"), list) else []

    add_source("ask_dj", "Ask DJ playback context", enabled=bool(memory.get("last_ask_dj")), count=1 if memory.get("last_ask_dj") else 0)
    add_source("recent_tracks", "Recent DJConnect tracks", enabled=bool(recent_tracks), count=len(recent_tracks))
    add_source("spotify_listening_profile", "Spotify recent/top profile snapshots", enabled=bool(listening or snapshots), count=len(snapshots), last_updated=_clean_text(listening.get("last_profile_refresh") or memory.get("last_profile_refresh")))
    add_source("recommendation_feedback", "Recommendation feedback", enabled=bool(recommendation_plays or discovery_plays), count=len(recommendation_plays) + len(discovery_plays))
    add_source("negative_feedback", "Blocked artists/items", enabled=bool(blocked_items or blocked_artists), count=len(blocked_items) + len(blocked_artists))
    add_source("favorites", "Explicit favorite signals", enabled=bool(favorite_tracks), count=len(favorite_tracks))
    add_source("track_insight", "Track Insight energy signals", enabled=bool(energy_signals), count=len(energy_signals))
    add_source("mood", "Client mood samples", enabled=bool(mood_signals or memory.get("mood") is not None), count=len(mood_signals))

    active_count = sum(1 for source in sources if source.get("enabled"))
    return {
        "enabled": bool(memory.get("enabled")),
        "scope": "ha_user_or_client",
        "stores_raw_audio": False,
        "stores_oauth_tokens": False,
        "stores_full_prompts": False,
        "data_sources": sources,
        "active_source_count": active_count,
        "retention": {
            "recent_tracks_max": MAX_RECENT_TRACKS,
            "chat_facts_max": MAX_CHAT_FACTS,
            "snapshot_history_max": MAX_PROFILE_SNAPSHOTS,
        },
        "controls": {
            "clear_supported": True,
            "export_supported": True,
            "import_supported": True,
            "opt_out_preserves_clear": True,
        },
    }


def _hide_empty_profile_blocks(profile: dict[str, Any]) -> dict[str, Any]:
    """Omit empty optional dashboard sections so clients can stay compact."""
    cleaned = dict(profile)
    for key in (
        "favorite_genres",
        "favorite_artists",
        "recent_tracks",
        "recent_favorite_tracks",
        "recommendation_signals",
        "blocked_artists",
        "blocked_items",
    ):
        if cleaned.get(key) in (None, [], {}):
            cleaned.pop(key, None)
    discovery_feedback = cleaned.get("discovery_feedback")
    if not isinstance(discovery_feedback, dict) or not discovery_feedback.get("eligible"):
        cleaned.pop("discovery_feedback", None)
    if not isinstance(cleaned.get("time_patterns"), list) or len(cleaned.get("time_patterns") or []) < 3:
        cleaned.pop("time_patterns", None)
    for key in ("top_tracks_by_range", "top_artists_by_range", "snapshot_history", "privacy_dashboard", "mood", "energy_profile"):
        if cleaned.get(key) in (None, {}, []):
            cleaned.pop(key, None)
    playtime = cleaned.get("playtime")
    if not isinstance(playtime, dict) or int(playtime.get("total_seconds") or 0) <= 0:
        cleaned.pop("playtime", None)
    rhythm = cleaned.get("listening_rhythm")
    if not isinstance(rhythm, dict) or int(rhythm.get("sample_count") or 0) < 3:
        cleaned.pop("listening_rhythm", None)
    mood_mix = cleaned.get("mood_mix")
    if not isinstance(mood_mix, dict) or int(mood_mix.get("sample_count") or 0) <= 0:
        cleaned.pop("mood_mix", None)
    for key in ("last_profile_refresh", "consent_updated_at"):
        if cleaned.get(key) in (None, "", [], {}):
            cleaned.pop(key, None)
    return cleaned


def _profile_artist_items(memory: dict[str, Any], listening: dict[str, Any]) -> list[dict[str, Any]]:
    counts = memory.get("artist_play_counts")
    count_items: list[dict[str, Any]] = []
    if isinstance(counts, dict):
        for name, count in counts.items():
            artist = _clean_text(name)
            if artist:
                count_items.append({"name": artist, "play_count": max(1, int(count or 0))})
    count_items.sort(key=lambda item: (-int(item.get("play_count") or 0), item["name"].lower()))
    seen = {item["name"].lower() for item in count_items}
    extras = _unique_texts(
        [
            *_artist_name_values(memory.get("favorite_artists")),
            *(listening.get("recent_artists") or []),
            *[
                artist.get("name") or artist.get("artist") or artist.get("artist_name")
                for group in (listening.get("top_artists_by_range") or {}).values()
                if isinstance(group, list)
                for artist in group
                if isinstance(artist, dict)
            ],
        ]
    )
    for artist in extras:
        if artist.lower() in seen:
            continue
        count_items.append({"name": artist})
        seen.add(artist.lower())
    return count_items[:20]


def _profile_playtime(memory: dict[str, Any]) -> dict[str, Any]:
    total_seconds = max(0, int(memory.get("total_play_seconds") or 0))
    top_artists = _top_duration_items(memory.get("artist_play_seconds"), limit=3)
    top_albums = _top_duration_items(memory.get("album_play_seconds"), limit=3)
    return {
        "total_seconds": total_seconds,
        "total_hours": round(total_seconds / 3600, 2),
        "formatted_total": _format_duration(total_seconds),
        "top_artists": top_artists,
        "top_albums": top_albums,
    }


def _profile_listening_rhythm(memory: dict[str, Any]) -> dict[str, Any]:
    signals = memory.get("listening_time_signals")
    if not isinstance(signals, dict):
        signals = {}
    dayparts = _count_items(signals.get("dayparts"))
    weekdays = _count_items(signals.get("weekdays"))
    total = max(0, int(signals.get("count") or sum(dayparts.values()) or sum(weekdays.values())))
    return {
        "sample_count": total,
        "dayparts": _top_count_items(dayparts, key_name="daypart"),
        "weekdays": _top_count_items(weekdays, key_name="weekday"),
        "top_daypart": _top_key(dayparts),
        "top_weekday": _top_key(weekdays),
    }


def _profile_mood_mix(memory: dict[str, Any]) -> dict[str, Any]:
    signals = memory.get("mood_signals")
    if not isinstance(signals, dict):
        return {"sample_count": 0, "zones": [], "top_zone": None}
    zones = _count_items(signals.get("zones"))
    total = max(0, int(signals.get("count") or sum(zones.values())))
    zone_items: list[dict[str, Any]] = []
    for zone, count in sorted(zones.items(), key=lambda item: (-item[1], item[0])):
        percent = round((count / total) * 100, 1) if total else 0
        zone_items.append({"zone": zone, "count": count, "percent": percent})
    return {
        "sample_count": total,
        "average": int(signals.get("average") or 0) if total else None,
        "top_zone": _top_key(zones),
        "zones": zone_items,
    }


def _profile_repeat_magnets(memory: dict[str, Any]) -> dict[str, Any]:
    artists = [
        {"kind": "artist", "name": item["name"], "count": item["play_count"]}
        for item in _profile_artist_items(memory, {})
        if int(item.get("play_count") or 0) >= 2
    ][:3]
    albums = [
        {"kind": "album", "name": item["name"], "seconds": item["seconds"], "formatted": item["formatted"]}
        for item in _top_duration_items(memory.get("album_play_seconds"), limit=3)
        if int(item.get("seconds") or 0) >= 20 * 60
    ]
    items = [*artists, *albums][:3]
    if len(items) < 2:
        return {"eligible": False, "items": [], "reason": "insufficient_repeat_signals"}
    return {"eligible": True, "items": items}


def _profile_explicit_positives(memory: dict[str, Any]) -> dict[str, Any]:
    favorites = [
        {
            "kind": "favorite_track",
            "title": track.get("title") or track.get("track_name") or track.get("name"),
            "artist": track.get("artist") or track.get("artist_name"),
            "uri": track.get("uri"),
        }
        for track in (memory.get("recent_favorite_tracks") or [])
        if isinstance(track, dict) and (track.get("title") or track.get("track_name") or track.get("name"))
    ][:3]
    recommendations = [
        {
            "kind": "accepted_recommendation",
            "title": item.get("title"),
            "subtitle": item.get("subtitle"),
            "uri": item.get("uri"),
            "reason": item.get("reason"),
        }
        for item in (memory.get("recommendation_plays") or [])
        if isinstance(item, dict) and (item.get("title") or item.get("uri"))
    ][:3]
    total = len(favorites) + len(recommendations)
    if total <= 0:
        return {
            "eligible": False,
            "favorite_tracks": [],
            "accepted_recommendations": [],
            "reason": "no_explicit_positive_signals",
        }
    return {
        "eligible": True,
        "favorite_tracks": favorites,
        "accepted_recommendations": recommendations,
        "signal_count": total,
    }


def _profile_discovery_feedback(memory: dict[str, Any]) -> dict[str, Any]:
    """Return compact Discover feedback that Ask DJ may use as taste context."""
    recommendation_plays = memory.get("recommendation_plays")
    discovery_plays = memory.get("discovery_plays")
    blocked_artists = memory.get("blocked_artists")
    blocked_items = memory.get("blocked_items")
    if not isinstance(recommendation_plays, list):
        recommendation_plays = []
    if not isinstance(discovery_plays, list):
        discovery_plays = []
    if not isinstance(blocked_artists, list):
        blocked_artists = []
    if not isinstance(blocked_items, list):
        blocked_items = []

    accepted_items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in [*discovery_plays, *recommendation_plays]:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        uri = _clean_text(item.get("uri") or item.get("context_uri"))
        if not title and not uri:
            continue
        identity = (uri.lower(), title.lower())
        if identity in seen:
            continue
        seen.add(identity)
        accepted_items.append(
            _compact_dict(
                {
                    "kind": item.get("kind") or "track",
                    "title": title,
                    "subtitle": item.get("subtitle"),
                    "uri": uri,
                    "reason": item.get("reason"),
                    "source": item.get("source") or item.get("source_intent") or "ask_dj_recommendation_play",
                    "section_id": item.get("section_id"),
                    "quality_score": item.get("quality_score"),
                    "quality_band": item.get("quality_band"),
                    "created_at": item.get("created_at"),
                }
            )
        )

    blocked_artist_items = [
        _compact_dict(
            {
                "kind": "artist",
                "name": item.get("name"),
                "reason": item.get("reason"),
                "created_at": item.get("created_at"),
            }
        )
        for item in blocked_artists
        if isinstance(item, dict) and item.get("name")
    ][:8]
    blocked_music_items = [
        _compact_dict(
            {
                "kind": item.get("kind") or "track",
                "name": item.get("name"),
                "reason": item.get("reason"),
                "created_at": item.get("created_at"),
            }
        )
        for item in blocked_items
        if isinstance(item, dict) and item.get("name")
    ][:8]
    accepted_count = len(accepted_items)
    negative_count = len(blocked_artist_items) + len(blocked_music_items)
    if accepted_count + negative_count <= 0:
        return {
            "eligible": False,
            "accepted_items": [],
            "blocked_artists": [],
            "blocked_items": [],
            "reason": "no_discovery_feedback_signals",
        }
    return {
        "eligible": True,
        "accepted_items": accepted_items[:8],
        "blocked_artists": blocked_artist_items,
        "blocked_items": blocked_music_items,
        "accepted_count": accepted_count,
        "negative_count": negative_count,
    }


def _profile_taste_anchors(memory: dict[str, Any], favorite_genres: list[str]) -> dict[str, Any]:
    artist_counts = memory.get("artist_play_counts")
    artist_seconds = memory.get("artist_play_seconds")
    anchors: list[dict[str, Any]] = []
    if isinstance(artist_counts, dict):
        for name, count in sorted(
            artist_counts.items(),
            key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
        ):
            artist = _clean_text(name)
            play_count = int(count or 0)
            seconds = int(artist_seconds.get(artist) or 0) if isinstance(artist_seconds, dict) and artist else 0
            if artist and (play_count >= 2 or seconds >= 30 * 60):
                anchors.append(
                    {
                        "kind": "artist",
                        "name": artist,
                        "play_count": play_count,
                        "seconds": seconds,
                        "formatted": _format_duration(seconds) if seconds > 0 else None,
                    }
                )
            if len(anchors) >= 3:
                break
    genre_anchors = [{"kind": "genre", "name": genre} for genre in favorite_genres[:3]]
    if len(anchors) + len(genre_anchors) < 2:
        return {"eligible": False, "items": [], "reason": "insufficient_anchor_signals"}
    return {"eligible": True, "items": [*anchors, *genre_anchors][:5]}


def _top_duration_items(values: Any, *, limit: int) -> list[dict[str, Any]]:
    if not isinstance(values, dict):
        return []
    items: list[dict[str, Any]] = []
    for name, seconds in sorted(
        values.items(),
        key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
    )[:limit]:
        label = _clean_text(name)
        value = max(0, int(seconds or 0))
        if label and value > 0:
            items.append(
                {
                    "name": label,
                    "seconds": value,
                    "hours": round(value / 3600, 2),
                    "formatted": _format_duration(value),
                }
            )
    return items


def _profile_mood(memory: dict[str, Any], mood: Any, zone: Any) -> dict[str, Any]:
    profile: dict[str, Any] = {}
    if mood is not None:
        profile.update(
            {
                "value": mood,
                "zone": zone.name if zone is not None else None,
                "prompt_hint": zone.prompt_hint if zone is not None else None,
            }
        )
    signals = memory.get("mood_signals")
    if not isinstance(signals, dict):
        return profile
    count = int(signals.get("count") or 0)
    total = int(signals.get("total") or 0)
    if count <= 0:
        return profile
    average = int(round(total / count))
    average_zone = mood_zone_for_value(average)
    zone_counts = signals.get("zones")
    profile.update(
        {
            "sample_count": count,
            "average": average,
            "average_zone": average_zone.name if average_zone is not None else None,
            "average_prompt_hint": average_zone.prompt_hint if average_zone is not None else None,
            "zone_counts": dict(zone_counts) if isinstance(zone_counts, dict) else {},
        }
    )
    return profile


def _profile_energy_profile(memory: dict[str, Any]) -> dict[str, Any]:
    signals = memory.get("track_insight_energy_signals")
    if not isinstance(signals, list):
        return {}
    items = [item for item in signals if isinstance(item, dict)]
    if not items:
        return {}
    energy_values = [_normalized_ratio(item.get("energy")) for item in items]
    dance_values = [_normalized_ratio(item.get("danceability")) for item in items]
    intensity_values = [_normalized_ratio(item.get("intensity")) for item in items]
    energy = _average_ratio(energy_values)
    danceability = _average_ratio(dance_values)
    intensity = _average_ratio(intensity_values)
    profile: dict[str, Any] = {
        "sample_count": len(items),
        "recent_signals": items[:10],
    }
    if energy is not None:
        percent = int(round(energy * 100))
        zone = mood_zone_for_value(percent)
        profile.update(
            {
                "energy": energy,
                "energy_percent": percent,
                "zone": zone.name if zone is not None else None,
                "prompt_hint": zone.prompt_hint if zone is not None else None,
            }
        )
    if danceability is not None:
        profile["danceability"] = danceability
        profile["danceability_percent"] = int(round(danceability * 100))
    if intensity is not None:
        profile["intensity"] = intensity
        profile["intensity_percent"] = int(round(intensity * 100))
    return profile


def _record_mood_signal(memory: dict[str, Any], mood: int) -> None:
    memory["mood"] = mood
    zone = mood_zone_for_value(mood)
    if zone is not None:
        memory["mood_zone"] = zone.name
        memory["mood_zone_prompt"] = zone.prompt_hint
    signals = memory.get("mood_signals")
    if not isinstance(signals, dict):
        signals = {}
    zones = signals.get("zones")
    if not isinstance(zones, dict):
        zones = {}
    previous = _clean_mood(signals.get("last_value"))
    if previous == mood and int(signals.get("count") or 0) > 0:
        signals.update(
            {
                "last_value": mood,
                "last_seen": _now(),
                "zones": zones,
            }
        )
        memory["mood_signals"] = signals
        return
    if zone is not None:
        zones[zone.name] = int(zones.get(zone.name) or 0) + 1
    count = int(signals.get("count") or 0) + 1
    total = int(signals.get("total") or 0) + mood
    signals.update(
        {
            "count": count,
            "total": total,
            "average": int(round(total / count)),
            "last_value": mood,
            "last_seen": _now(),
            "zones": zones,
        }
    )
    memory["mood_signals"] = signals


def _favorite_artists_from_counts(
    counts: dict[str, Any],
    existing: Any,
) -> list[str]:
    names = [
        str(name)
        for name, _count in sorted(
            counts.items(),
            key=lambda item: (-int(item[1] or 0), str(item[0]).lower()),
        )
        if _clean_text(name)
    ]
    return _unique_texts([*names, *_artist_name_values(existing)])[:20]


def _artist_name_values(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        text
        for text in (
            _clean_text(item.get("name") or item.get("artist") or item.get("artist_name"))
            if isinstance(item, dict)
            else _clean_text(item)
            for item in value
        )
        if text
    ]


def _track_artists(track: dict[str, Any]) -> list[str]:
    raw_artists = track.get("artists")
    if isinstance(raw_artists, list):
        names = _unique_texts(
            [
                item.get("name") if isinstance(item, dict) else item
                for item in raw_artists
            ]
        )
        if names:
            return names
    value = _clean_text(track.get("artist") or track.get("artist_name"))
    if not value:
        return []
    parts = re.split(r"\s*,\s*|\s+feat\.?\s+|\s+ft\.?\s+|\s+&\s+", value, flags=re.IGNORECASE)
    return _unique_texts([part for part in parts if _clean_text(part)])[:10]


def _track_album(track: dict[str, Any]) -> str | None:
    return _clean_text(track.get("album") or track.get("album_name"))


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _compact_dict(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value[:MAX_RECENT_TRACKS]]
    if isinstance(value, str):
        return _clean_text(value)
    return value


def _compact_dict(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        normalized = str(key).lower()
        if any(secret in normalized for secret in SECRET_KEY_FRAGMENTS):
            continue
        cleaned = _sanitize_value(item)
        if cleaned not in (None, "", [], {}):
            result[str(key)] = cleaned
    return result


def _track_from_context(*sources: Any) -> dict[str, Any]:
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ("track", "current_track", "resolved_media", "media"):
            value = source.get(key)
            if isinstance(value, dict):
                compact = _compact_track(value)
                if compact:
                    return compact
        compact = _compact_track(source)
        if compact:
            return compact
    return {}


def _compact_track(track: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id",
        "uri",
        "title",
        "name",
        "track_name",
        "artist",
        "artist_name",
        "album",
        "album_name",
        "genres",
        "duration_ms",
    )
    result: dict[str, Any] = {}
    for key in keys:
        value = track.get(key)
        if key == "genres" and isinstance(value, list):
            genres = _unique_texts(value)[:10]
            if genres:
                result[key] = genres
            continue
        cleaned = _clean_text(value)
        if cleaned:
            result[key] = cleaned
    duration_ms = _duration_ms(track)
    if duration_ms > 0:
        result["duration_ms"] = duration_ms
    return result


def _update_time_context(memory: dict[str, Any]) -> None:
    context = _current_time_context()
    memory["listening_time_context"] = context
    signals = memory.get("listening_time_signals")
    if not isinstance(signals, dict):
        signals = {}
    dayparts = _count_items(signals.get("dayparts"))
    weekdays = _count_items(signals.get("weekdays"))
    daypart = _clean_text(context.get("daypart"))
    weekday_name = _clean_text(context.get("weekday_name"))
    if daypart:
        dayparts[daypart] = int(dayparts.get(daypart) or 0) + 1
    if weekday_name:
        weekdays[weekday_name] = int(weekdays.get(weekday_name) or 0) + 1
    signals.update(
        {
            "count": int(signals.get("count") or 0) + 1,
            "dayparts": dayparts,
            "weekdays": weekdays,
            "last_seen": context.get("observed_at"),
        }
    )
    memory["listening_time_signals"] = signals
    patterns = memory.get("listening_time_patterns")
    if not isinstance(patterns, list):
        patterns = []
    key = (
        context.get("weekday"),
        context.get("is_weekend"),
        context.get("daypart"),
    )
    deduped = [
        item
        for item in patterns
        if not (
            isinstance(item, dict)
            and (
                item.get("weekday"),
                item.get("is_weekend"),
                item.get("daypart"),
            )
            == key
        )
    ]
    memory["listening_time_patterns"] = [context, *deduped][:MAX_CHAT_FACTS]


def _current_time_context() -> dict[str, Any]:
    now = _local_now()
    hour = int(now.hour)
    weekday = int(now.weekday())
    weekday_name = (
        "maandag",
        "dinsdag",
        "woensdag",
        "donderdag",
        "vrijdag",
        "zaterdag",
        "zondag",
    )[weekday]
    return {
        "hour": hour,
        "weekday": weekday,
        "weekday_name": weekday_name,
        "is_weekend": weekday >= 5,
        "daypart": _daypart(hour),
        "observed_at": now.isoformat(),
    }


def _local_now() -> datetime:
    try:
        from homeassistant.util import dt as dt_util

        value = dt_util.now()
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


def _daypart(hour: int) -> str:
    if hour < 6:
        return "nacht"
    if hour < 12:
        return "ochtend"
    if hour < 18:
        return "middag"
    return "avond"


def _compact_profile_artist(artist: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "uri", "name", "artist", "artist_name", "genres")
    result: dict[str, Any] = {}
    for key in keys:
        value = artist.get(key)
        if key == "genres" and isinstance(value, list):
            genres = _unique_texts(value)[:10]
            if genres:
                result[key] = genres
            continue
        cleaned = _clean_text(value)
        if cleaned:
            result[key] = cleaned
    return result


def _compact_listening_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {}
    recent_tracks = [
        compact
        for compact in (
            _compact_track(track)
            for track in (profile.get("recent_tracks") or [])[:50]
            if isinstance(track, dict)
        )
        if compact
    ]
    top_tracks_by_range = _compact_profile_ranges(
        profile.get("top_tracks_by_range"), _compact_track
    )
    top_artists_by_range = _compact_profile_ranges(
        profile.get("top_artists_by_range"), _compact_profile_artist
    )
    result = {
        "source": "spotify",
        "recent_track_ids": _unique_texts(profile.get("recent_track_ids") or [])[:50],
        "recent_artists": _unique_texts(profile.get("recent_artists") or [])[:25],
        "recent_tracks": recent_tracks,
        "top_artists_by_range": top_artists_by_range,
        "top_tracks_by_range": top_tracks_by_range,
        "inferred_genres": _unique_texts(profile.get("inferred_genres") or [])[:20],
        "mood_energy_summary": _clean_text(profile.get("mood_energy_summary")),
        "last_profile_refresh": _clean_text(profile.get("last_profile_refresh")) or _now(),
        "sources": _unique_texts(profile.get("sources") or [])[:12],
    }
    return {
        key: value
        for key, value in result.items()
        if value not in (None, "", [], {})
    }


def _compact_profile_ranges(
    ranges: Any, compact_item: Callable[[dict[str, Any]], dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Compact supported Spotify time ranges without retaining provider payloads."""
    if not isinstance(ranges, dict):
        return {}
    supported = {"short_term", "medium_term", "long_term"}
    return {
        time_range: [
            compact
            for compact in (
                compact_item(item) for item in items[:50] if isinstance(item, dict)
            )
            if compact
        ]
        for time_range, items in ranges.items()
        if time_range in supported and isinstance(items, list)
    }


def _updated_listening_profile_snapshots(existing: Any, profile: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = _compact_listening_profile_snapshot(profile)
    snapshots = [
        compact
        for compact in (
            _compact_listening_profile_snapshot(item)
            for item in (existing if isinstance(existing, list) else [])
            if isinstance(item, dict)
        )
        if compact
    ]
    if not snapshot:
        return snapshots[:MAX_PROFILE_SNAPSHOTS]
    snapshot_key = snapshot.get("captured_at")
    deduped = [
        item
        for item in snapshots
        if item.get("captured_at") != snapshot_key
    ]
    return [snapshot, *deduped][:MAX_PROFILE_SNAPSHOTS]


def _compact_listening_profile_snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    captured_at = _clean_text(profile.get("captured_at") or profile.get("last_profile_refresh")) or _now()
    top_tracks = _snapshot_top_tracks(profile.get("top_tracks_by_range"))
    top_artists = _snapshot_top_artists(profile.get("top_artists_by_range"))
    recent_artists = _unique_texts(profile.get("recent_artists") or [])[:5]
    inferred_genres = _unique_texts(profile.get("inferred_genres") or [])[:8]
    result = {
        "captured_at": captured_at,
        "source": _clean_text(profile.get("source") or "spotify"),
        "sources": _unique_texts(profile.get("sources") or [])[:8],
        "recent_artists": recent_artists,
        "top_artists": top_artists,
        "top_tracks": top_tracks,
        "inferred_genres": inferred_genres,
        "recent_track_count": len(profile.get("recent_tracks") or []),
    }
    return {
        key: value
        for key, value in result.items()
        if value not in (None, "", [], {})
    }


def _snapshot_top_tracks(value: Any) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    for track in _range_items(value):
        compact = _compact_track(track)
        if not compact:
            continue
        item = _compact_dict(
            {
                "title": compact.get("title") or compact.get("track_name") or compact.get("name"),
                "artist": compact.get("artist"),
                "uri": compact.get("uri"),
            }
        )
        if item:
            tracks.append(item)
        if len(tracks) >= 5:
            break
    return tracks


def _snapshot_top_artists(value: Any) -> list[dict[str, Any]]:
    artists: list[dict[str, Any]] = []
    for artist in _range_items(value):
        compact = _compact_profile_artist(artist)
        if not compact:
            continue
        item = _compact_dict(
            {
                "name": compact.get("name"),
                "uri": compact.get("uri"),
                "genres": compact.get("genres"),
            }
        )
        if item:
            artists.append(item)
        if len(artists) >= 5:
            break
    return artists


def _range_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    items: list[dict[str, Any]] = []
    for range_name in ("short_term", "medium_term", "long_term"):
        values = value.get(range_name)
        if isinstance(values, list):
            items.extend(item for item in values if isinstance(item, dict))
    return items


def _unique_texts(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    if not isinstance(values, list):
        return result
    for value in values:
        text = _clean_text(value)
        normalized = str(text or "").lower()
        if text and normalized not in seen:
            seen.add(normalized)
            result.append(text)
    return result


def _speaker_from_playback(playback: Any) -> dict[str, Any]:
    if not isinstance(playback, dict):
        return {}
    for key in ("device", "speaker", "output_device"):
        value = playback.get(key)
        if isinstance(value, dict):
            return _compact_dict(
                {
                    "id": value.get("id"),
                    "name": value.get("name"),
                    "type": value.get("type"),
                }
            )
    return {}


def _track_identity(track: dict[str, Any]) -> str:
    return str(
        track.get("uri")
        or track.get("id")
        or track.get("title")
        or track.get("track_name")
        or track.get("name")
        or ""
    ).lower()


def _intent_value(intent: Any, key: str) -> Any:
    return intent.get(key) if isinstance(intent, dict) else None


def _safe_music_dna_key(value: Any) -> str:
    text = _clean_text(value) or "default"
    return re.sub(r"[^A-Za-z0-9_.:@-]", "_", text)[:160] or "default"


def _import_profile_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    value = payload
    if payload.get("format") != "djconnect.music_dna.export":
        value = payload.get("profile")
    if not isinstance(value, dict):
        return None
    if value.get("format") == "djconnect.music_dna.export":
        value = value.get("profile")
    if not isinstance(value, dict) or value.get("success") is not True:
        return None
    if "enabled" not in value or not isinstance(value.get("profile"), dict):
        return None
    return deepcopy(value["profile"])


def _memory_from_profile_payload(profile: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    memory = {
        key: value
        for key, value in metadata.items()
        if value not in (None, "", [], {})
    }
    for key, value in profile.items():
        if key in {"mood", "time_context"}:
            continue
        memory[key] = _sanitize_value(value)
    mood = profile.get("mood")
    if isinstance(mood, dict):
        mood_value = _clean_mood(mood.get("value"))
        if mood_value is not None:
            zone_name = _clean_text(mood.get("zone")) or mood_zone_for_value(mood_value).name
            memory["mood"] = mood_value
            memory["mood_signals"] = {
                "count": 1,
                "total": mood_value,
                "zones": {zone_name: 1},
                "last": {
                    "value": mood_value,
                    "zone": zone_name,
                    "updated_at": _clean_text(mood.get("updated_at")) or memory.get("updated_at"),
                },
            }
    time_context = profile.get("time_context")
    if isinstance(time_context, dict):
        memory["time_context"] = _sanitize_value(time_context)
    return _compact_dict(memory)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:MAX_TEXT_LENGTH]


def _clean_mood(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return None


def _duration_ms(track: dict[str, Any]) -> int:
    for key in ("duration_ms", "durationMs", "track_duration_ms"):
        value = track.get(key)
        if value not in (None, ""):
            try:
                return max(0, min(3 * 60 * 60 * 1000, int(value)))
            except (TypeError, ValueError):
                return 0
    for key in ("duration_seconds", "duration", "track_duration_seconds"):
        value = track.get(key)
        if value not in (None, ""):
            try:
                return max(0, min(3 * 60 * 60 * 1000, int(float(value) * 1000)))
            except (TypeError, ValueError):
                return 0
    return 0


def _track_duration_seconds(track: dict[str, Any]) -> int:
    return int(round(_duration_ms(track) / 1000))


def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}u {minutes}m"
    if hours:
        return f"{hours}u"
    if minutes:
        return f"{minutes}m"
    return "0m"


def _count_items(values: Any) -> dict[str, int]:
    if not isinstance(values, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in values.items():
        label = _clean_text(key)
        if not label:
            continue
        try:
            count = int(value or 0)
        except (TypeError, ValueError):
            count = 0
        if count > 0:
            result[label] = count
    return result


def _top_count_items(values: dict[str, int], *, key_name: str) -> list[dict[str, Any]]:
    total = sum(max(0, int(value or 0)) for value in values.values())
    items: list[dict[str, Any]] = []
    for key, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))[:7]:
        items.append(
            {
                key_name: key,
                "count": count,
                "percent": round((count / total) * 100, 1) if total else 0,
            }
        )
    return items


def _top_key(values: dict[str, int]) -> str | None:
    if not values:
        return None
    return sorted(values.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _normalized_ratio(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, round(number, 4)))


def _average_ratio(values: list[float | None]) -> float | None:
    numbers = [value for value in values if isinstance(value, (int, float))]
    if not numbers:
        return None
    return round(sum(float(value) for value in numbers) / len(numbers), 4)


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return None


def _call_or_none(value: Any) -> Any:
    return value() if callable(value) else value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_after(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(1, int(seconds)))).isoformat()


def _parse_timestamp(value: Any) -> datetime | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
