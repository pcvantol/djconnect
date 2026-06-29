"""Server-side Music DNA for Ask DJ context."""
from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import logging
import re
import uuid
from typing import Any

from .const import CONF_CLIENT_TYPE, CONF_DEVICE_ID, CONF_DEVICE_NAME
from .mood import mood_zone_for_value

_LOGGER = logging.getLogger(__name__)

STORE_KEY = "djconnect_music_dna"
STORE_VERSION = 1
MAX_SESSION_TURNS = 20
MAX_RECENT_TRACKS = 20
MAX_CHAT_FACTS = 20
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
            memory["mood"] = mood
            zone = mood_zone_for_value(mood)
            if zone is not None:
                memory["mood_zone"] = zone.name
                memory["mood_zone_prompt"] = zone.prompt_hint
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
                memory["mood"] = mood
                zone = mood_zone_for_value(mood)
                if zone is not None:
                    memory["mood_zone"] = zone.name
                    memory["mood_zone_prompt"] = zone.prompt_hint
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
        deduped = [
            item
            for item in recent
            if _track_identity(item if isinstance(item, dict) else {}) != identity
        ]
        memory["recent_tracks"] = [compact_track, *deduped][:MAX_RECENT_TRACKS]
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
                "favorite_genres": [],
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
            "favorite_genres",
            "blocked_artists",
            "blocked_items",
            "recent_tracks",
            "chat_facts",
            "last_ask_dj",
            "listening_profile",
            "listening_time_context",
            "listening_time_patterns",
            "last_profile_refresh",
            "recommendation_plays",
            "last_played_recommendation",
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
    blocked_artists = memory.get("blocked_artists")
    if isinstance(blocked_artists, list) and blocked_artists:
        names = [
            str(item.get("name") or "").strip()
            for item in blocked_artists[:8]
            if isinstance(item, dict) and item.get("name")
        ]
        if names:
            lines.append("Niet meer draaien volgens gebruiker: " + "; ".join(names))
    blocked_items = memory.get("blocked_items")
    if isinstance(blocked_items, list) and blocked_items:
        names = [
            str(item.get("name") or "").strip()
            for item in blocked_items[:8]
            if isinstance(item, dict) and item.get("name")
        ]
        if names:
            lines.append("Vermijd deze muziekitems: " + "; ".join(names))
    time_context = memory.get("listening_time_context")
    if isinstance(time_context, dict):
        day = time_context.get("weekday_name")
        daypart = time_context.get("daypart")
        weekend = "weekend" if time_context.get("is_weekend") else "weekdag"
        hour = time_context.get("hour")
        lines.append(
            "Luistertijdcontext: "
            + ", ".join(str(value) for value in (day, daypart, weekend, f"{hour}:00" if hour is not None else "") if value)
        )
    recent = memory.get("recent_tracks")
    if isinstance(recent, list) and recent:
        names = []
        for track in recent[:5]:
            if isinstance(track, dict):
                label = " - ".join(
                    str(value)
                    for value in (track.get("artist"), track.get("title") or track.get("name"))
                    if value
                )
                if label:
                    names.append(label)
        if names:
            lines.append("Recente tracks: " + "; ".join(names))
    if isinstance(session, list) and session:
        turns = [
            f"{item.get('role')}: {item.get('text')}"
            for item in session[-6:]
            if isinstance(item, dict) and item.get("text")
        ]
        if turns:
            lines.append("Recente Ask DJ beurt(en): " + " | ".join(turns))
    if isinstance(server_history, list) and server_history:
        turns = [
            f"{item.get('role')}: {item.get('text')}"
            for item in server_history[-8:]
            if isinstance(item, dict) and item.get("text")
        ]
        if turns:
            lines.append("Server Ask DJ history: " + " | ".join(turns))
    return "\n".join(line for line in lines if line and not line.endswith(": None"))


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
        "favorite_genres",
        "blocked_artists",
        "blocked_items",
        "recent_tracks",
        "chat_facts",
        "last_ask_dj",
        "listening_profile",
        "listening_time_context",
        "listening_time_patterns",
        "last_profile_refresh",
        "recommendation_plays",
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
    if isinstance(result.get("chat_facts"), list):
        result["chat_facts"] = result["chat_facts"][:MAX_CHAT_FACTS]
    if isinstance(result.get("blocked_artists"), list):
        result["blocked_artists"] = result["blocked_artists"][:MAX_CHAT_FACTS]
    if isinstance(result.get("blocked_items"), list):
        result["blocked_items"] = result["blocked_items"][:MAX_CHAT_FACTS]
    if isinstance(result.get("listening_profile"), dict):
        result["listening_profile"] = _compact_listening_profile(result["listening_profile"])
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
    artists = _unique_texts(
        [
            *(memory.get("favorite_artists") or []),
            *(listening.get("recent_artists") or []),
            *[
                artist.get("name") or artist.get("artist") or artist.get("artist_name")
                for group in (listening.get("top_artists_by_range") or {}).values()
                if isinstance(group, list)
                for artist in group
                if isinstance(artist, dict)
            ],
        ]
    )[:20]
    mood = memory.get("mood")
    zone = mood_zone_for_value(mood) if mood is not None else None
    return {
        "summary": _profile_summary(memory, favorite_genres, artists, recent_tracks),
        "favorite_genres": [{"name": value} for value in favorite_genres],
        "favorite_artists": [{"name": value} for value in artists],
        "recent_tracks": [_compact_track(track) for track in recent_tracks[:MAX_RECENT_TRACKS] if isinstance(track, dict)],
        "top_tracks_by_range": listening.get("top_tracks_by_range") or {},
        "top_artists_by_range": listening.get("top_artists_by_range") or {},
        "mood": (
            {
                "value": mood,
                "zone": zone.name if zone is not None else None,
                "prompt_hint": zone.prompt_hint if zone is not None else None,
            }
            if mood is not None
            else {}
        ),
        "time_patterns": memory.get("listening_time_patterns") or [],
        "recommendation_signals": memory.get("recommendation_plays") or [],
        "blocked_artists": memory.get("blocked_artists") or [],
        "blocked_items": memory.get("blocked_items") or [],
        "last_profile_refresh": listening.get("last_profile_refresh") or memory.get("last_profile_refresh"),
        "consent_updated_at": memory.get("consent_updated_at"),
    }


def _profile_summary(
    memory: dict[str, Any],
    genres: list[str],
    artists: list[str],
    recent_tracks: list[Any],
) -> str:
    if not (genres or artists or recent_tracks or memory.get("mood") is not None):
        return "Music DNA is ingeschakeld, maar er is nog weinig profieldata opgebouwd."
    parts: list[str] = []
    if genres:
        parts.append("genres zoals " + ", ".join(genres[:3]))
    if artists:
        parts.append("artiesten zoals " + ", ".join(artists[:3]))
    if memory.get("mood") is not None:
        zone = mood_zone_for_value(memory.get("mood"))
        parts.append(f"een {zone.name if zone is not None else 'bekende'} mood")
    if not parts:
        parts.append(f"{len(recent_tracks)} recente track(s)")
    return "Je Music DNA bevat nu " + "; ".join(parts) + "."


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
    )
    return {
        key: _clean_text(track.get(key))
        for key in keys
        if _clean_text(track.get(key))
    }


def _update_time_context(memory: dict[str, Any]) -> None:
    context = _current_time_context()
    memory["listening_time_context"] = context
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
    top_tracks_by_range: dict[str, list[dict[str, Any]]] = {}
    for time_range, tracks in (profile.get("top_tracks_by_range") or {}).items():
        if time_range not in {"short_term", "medium_term", "long_term"} or not isinstance(tracks, list):
            continue
        top_tracks_by_range[time_range] = [
            compact
            for compact in (
                _compact_track(track)
                for track in tracks[:50]
                if isinstance(track, dict)
            )
            if compact
        ]
    top_artists_by_range: dict[str, list[dict[str, Any]]] = {}
    for time_range, artists in (profile.get("top_artists_by_range") or {}).items():
        if time_range not in {"short_term", "medium_term", "long_term"} or not isinstance(artists, list):
            continue
        top_artists_by_range[time_range] = [
            compact
            for compact in (
                _compact_profile_artist(artist)
                for artist in artists[:50]
                if isinstance(artist, dict)
            )
            if compact
        ]
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
