"""Backend-independent DJConnect Track Insight service."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DEFAULT_MUSIC_BACKEND
from .mood import enrich_payload_with_mood_zone, mood_context_text
from .pipeline import _assist_context, _speech_from_response, call_conversation_process_with_agent_retry
from .use_cases import run_music_command

_LOGGER = logging.getLogger(__name__)

TRACK_INSIGHT_CACHE_TTL_SECONDS = 24 * 60 * 60
TRACK_INSIGHT_RATE_WINDOW_SECONDS = 60
TRACK_INSIGHT_MAX_CALLS_PER_WINDOW = 6
TRACK_INSIGHT_DEBOUNCE_SECONDS = 8
TRACK_INSIGHT_EVENT = "djconnect_track_insight"

_MOTION_STYLES = ("flowing", "pulsing", "sharp", "minimal", "organic", "cinematic")
_SPECTRUM_BIASES = ("low", "mid", "high", "balanced")


class TrackInsightError(Exception):
    """Structured Track Insight failure."""

    def __init__(self, code: str, message: str, *, status: int = 400) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)

    def as_dict(self) -> dict[str, Any]:
        return {"success": False, "error": self.code, "message": self.message}


@dataclass(frozen=True)
class TrackInsightRequest:
    """Normalized Track Insight request."""

    source: str = "auto"
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    entity_id: str | None = None
    player_id: str | None = None
    music_backend: str | None = None
    force_refresh: bool = False
    locale: str | None = None
    mood: int | None = None
    mood_zone: str | None = None
    mood_zone_prompt: str | None = None
    include_visual_profile: bool = True
    include_raw_response: bool = False


class TrackInsightPromptBuilder:
    """Build the strict JSON prompt sent to the configured conversation stack."""

    def build(self, track: dict[str, Any], locale: str, mood_context: str | None = None) -> str:
        title = track.get("title") or "Unknown title"
        artist = track.get("artist") or "Unknown artist"
        album = track.get("album") or "Unknown album"
        mood_line = (
            f"Realtime client mood: {mood_context}. Adapt wording, listening cues, "
            "and visual energy to this mood without inventing track facts.\n"
            if mood_context
            else ""
        )
        return (
            "You are DJConnect Track Insight. Analyze the music track below. "
            "Return JSON only, with no markdown and no surrounding explanation. "
            f"Use locale/language: {locale or 'en'}.\n"
            f"Track title: {title}\n"
            f"Artist: {artist}\n"
            f"Album: {album}\n"
            f"{mood_line}"
            "Return this object shape exactly: "
            "{\"summary\": string, \"full_text\": string, \"genre\": string|null, "
            "\"subgenre\": string|null, \"mood\": string|null, \"vibe\": string|null, "
            "\"texture\": string|null, \"emotional_tone\": string|null, "
            "\"energy\": number 0..1, \"danceability\": number 0..1, "
            "\"intensity\": number 0..1, \"confidence\": number 0..1, "
            "\"production_notes\": string[], \"instrumentation\": string[], "
            "\"arrangement_notes\": string[], \"listening_cues\": string[], "
            "\"similar_tracks\": [{\"title\": string, \"artist\": string, \"reason\": string}]}. "
            "Be concise but musically rich. Include why the track works."
        )


class TrackInsightCache:
    """Runtime-backed TTL cache for Track Insight responses."""

    def __init__(self, runtime: Any, ttl_seconds: int = TRACK_INSIGHT_CACHE_TTL_SECONDS) -> None:
        self.runtime = runtime
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> dict[str, Any] | None:
        cache = self._cache()
        item = cache.get(key)
        if not isinstance(item, dict):
            return None
        created = _float(item.get("_cached_at"))
        if not created or time.time() - created > self.ttl_seconds:
            cache.pop(key, None)
            return None
        value = item.get("response")
        if isinstance(value, dict):
            result = _strip_track_insight_music_dna_match(value)
            result["cache"] = {"hit": True, "key": key}
            return result
        return None

    def set(self, key: str, response: dict[str, Any]) -> None:
        self._cache()[key] = {
            "_cached_at": time.time(),
            "response": _strip_track_insight_music_dna_match(response),
        }

    def _cache(self) -> dict[str, Any]:
        cache = getattr(self.runtime, "track_insight_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            setattr(self.runtime, "track_insight_cache", cache)
        return cache


class TrackInsightAnalyzer:
    """Analyze tracks through HA conversation, with deterministic local fallback."""

    def __init__(self, prompt_builder: TrackInsightPromptBuilder | None = None) -> None:
        self.prompt_builder = prompt_builder or TrackInsightPromptBuilder()

    async def analyze(
        self,
        hass: HomeAssistant,
        runtime: Any,
        track: dict[str, Any],
        request: TrackInsightRequest,
    ) -> tuple[dict[str, Any], str | None]:
        locale = request.locale or _runtime_locale(runtime)
        if _demo_enabled(runtime):
            return _demo_analysis(track, locale), None
        prompt = self.prompt_builder.build(track, locale, _request_mood_context(request))
        raw_response: str | None = None
        try:
            raw_response = await self._ask_conversation(hass, runtime, prompt, request)
            parsed = _parse_json_object(raw_response)
            if parsed:
                return _normalize_analysis(parsed, track, locale), raw_response
            _LOGGER.debug("DJConnect Track Insight conversation returned malformed JSON")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect Track Insight conversation unavailable: %s", exc.__class__.__name__)
        return _fallback_analysis(track, locale), raw_response

    async def _ask_conversation(
        self,
        hass: HomeAssistant,
        runtime: Any,
        prompt: str,
        request: TrackInsightRequest,
    ) -> str:
        services = getattr(hass, "services", None)
        caller = getattr(services, "async_call", None)
        if not callable(caller):
            raise TrackInsightError("ai_provider_unavailable", "Home Assistant conversation service is unavailable.", status=503)
        assist_context = _assist_context(hass, getattr(runtime, "config", {}) or {})
        data: dict[str, Any] = {"text": prompt, "language": request.locale or _runtime_locale(runtime)}
        if assist_context.get("agent_id"):
            data["agent_id"] = assist_context["agent_id"]
        result = await call_conversation_process_with_agent_retry(hass, data)
        message = _speech_from_response((result or {}).get("response") or {})
        if not message:
            raise TrackInsightError("ai_empty_response", "Track Insight did not receive analysis text.", status=502)
        return message


class TrackInsightResponseSerializer:
    """Serialize a Track Insight result into the Apple/client contract."""

    def serialize(
        self,
        *,
        request: TrackInsightRequest,
        track: dict[str, Any],
        analysis: dict[str, Any],
        cache_key: str,
        cache_hit: bool,
        raw_response: str | None = None,
    ) -> dict[str, Any]:
        response = {
            "id": _insight_id(cache_key),
            "created_at": datetime.now(UTC).isoformat(),
            "source": request.source or "auto",
            "language": _language_code(request.locale),
            "mood_context": _request_mood_metadata(request),
            "track": track,
            "analysis": analysis,
            "visual_profile": _visual_profile(track, analysis) if request.include_visual_profile else None,
            "cache": {"hit": cache_hit, "key": cache_key},
        }
        if raw_response and request.include_raw_response:
            response["raw_response"] = raw_response
        return response


class TrackInsightService:
    """Shared Track Insight engine used by Ask DJ, HTTP and HA services."""

    def __init__(
        self,
        *,
        analyzer: TrackInsightAnalyzer | None = None,
        serializer: TrackInsightResponseSerializer | None = None,
    ) -> None:
        self.analyzer = analyzer or TrackInsightAnalyzer()
        self.serializer = serializer or TrackInsightResponseSerializer()

    async def async_analyze(
        self,
        hass: HomeAssistant,
        runtime: Any,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "auto",
    ) -> dict[str, Any]:
        started = time.monotonic()
        request = _request_from_payload(payload or {}, source)
        track = await self._resolve_track(hass, runtime, request)
        cache_key = _cache_key(track, request.locale, _request_mood_context(request))
        cache = TrackInsightCache(runtime)
        cached = None if request.force_refresh else cache.get(cache_key)
        if cached is not None:
            _LOGGER.debug(
                "DJConnect Track Insight cache hit for %s language=%s mood=%s",
                cache_key,
                _language_code(request.locale),
                request.mood_zone or request.mood,
            )
            return cached
        self._check_rate_limit(runtime, track, request)
        analysis, raw_response = await self.analyzer.analyze(hass, runtime, track, request)
        response = self.serializer.serialize(
            request=request,
            track=track,
            analysis=analysis,
            cache_key=cache_key,
            cache_hit=False,
            raw_response=raw_response,
        )
        cache.set(cache_key, response)
        _LOGGER.debug(
            "DJConnect Track Insight analyzed track=%s artist=%s backend=%s language=%s mood=%s latency_ms=%s",
            track.get("title") or "unknown",
            track.get("artist") or "unknown",
            track.get("backend") or "unknown",
            _language_code(request.locale),
            request.mood_zone or request.mood,
            int((time.monotonic() - started) * 1000),
        )
        return response

    async def _resolve_track(
        self,
        hass: HomeAssistant,
        runtime: Any,
        request: TrackInsightRequest,
    ) -> dict[str, Any]:
        explicit_title = str(request.title or "").strip()
        explicit_artist = str(request.artist or "").strip()
        if explicit_title and explicit_artist:
            return _track_contract(
                {
                    "title": explicit_title,
                    "artist": explicit_artist,
                    "album": request.album,
                    "entity_id": request.entity_id,
                    "player_id": request.player_id,
                    "provider": request.music_backend,
                },
                runtime,
                request,
            )
        playback = await _current_playback(hass, runtime, request)
        track = _track_contract(playback, runtime, request)
        if not track.get("title") or not track.get("artist"):
            raise TrackInsightError(
                "no_track_playing",
                "No currently playing track could be resolved.",
                status=404,
            )
        return track

    def _check_rate_limit(self, runtime: Any, track: dict[str, Any], request: TrackInsightRequest) -> None:
        if request.force_refresh:
            return
        now = time.time()
        state = getattr(runtime, "track_insight_rate_limit", None)
        if not isinstance(state, dict):
            state = {"calls": []}
            setattr(runtime, "track_insight_rate_limit", state)
        last_key = str(state.get("last_key") or "")
        last_at = _float(state.get("last_at")) or 0
        key = _cache_key(track, request.locale, _request_mood_context(request))
        if last_key == key and now - last_at < TRACK_INSIGHT_DEBOUNCE_SECONDS:
            raise TrackInsightError("rate_limited", "Track Insight was requested too quickly for the same track.", status=429)
        calls = [
            stamp
            for stamp in state.get("calls", [])
            if isinstance(stamp, (int, float)) and now - float(stamp) < TRACK_INSIGHT_RATE_WINDOW_SECONDS
        ]
        if len(calls) >= TRACK_INSIGHT_MAX_CALLS_PER_WINDOW:
            raise TrackInsightError("rate_limited", "Track Insight rate limit reached. Try again shortly.", status=429)
        calls.append(now)
        state.update({"calls": calls, "last_key": key, "last_at": now})


class TrackInsightCoordinator(TrackInsightService):
    """Compatibility alias for the shared Track Insight service layer."""


class TrackInsightIntentHandler:
    """Ask DJ adapter for Track Insight requests."""

    def __init__(self, service: TrackInsightService | None = None) -> None:
        self.service = service or TrackInsightService()

    async def async_handle(
        self,
        hass: HomeAssistant,
        runtime: Any,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        insight = await self.service.async_analyze(
            hass,
            runtime,
            payload or {},
            source="ask_dj",
        )
        track = insight.get("track") if isinstance(insight.get("track"), dict) else {}
        title = str(track.get("title") or "this track")
        artist = str(track.get("artist") or "").strip()
        speak = f"Here is the Track Insight for {title}{f' by {artist}' if artist else ''}."
        summary = str((insight.get("analysis") or {}).get("summary") or "").strip()
        if summary:
            speak = f"{speak} {summary}"
        return {
            "success": True,
            "type": "track_insight",
            "text": speak,
            "dj_text": speak,
            "message": speak,
            "action": "track_insight",
            "open_screen": "track_insight",
            "track_insight": insight,
            "analysis": insight.get("analysis"),
            "items": [],
            "images": [],
            "links": [],
            "sources": [{"source": "track_insight", "kind": "source", "title": "DJConnect Track Insight"}],
            "playback_actions": [],
            "intent": {"category": "informational", "intent": "track_insight", "action": "track_insight"},
        }


class TrackInsightHassService:
    """Home Assistant developer service adapter."""

    def __init__(self, service: TrackInsightService | None = None) -> None:
        self.service = service or TrackInsightService()

    async def async_handle(self, hass: HomeAssistant, runtime: Any, data: dict[str, Any]) -> dict[str, Any]:
        result = await self.service.async_analyze(hass, runtime, data, source="service")
        bus = getattr(hass, "bus", None)
        fire = getattr(bus, "async_fire", None)
        if callable(fire):
            fire(TRACK_INSIGHT_EVENT, result)
        _LOGGER.info(
            "DJConnect Track Insight generated for %s by %s",
            result.get("track", {}).get("title") if isinstance(result.get("track"), dict) else "unknown",
            result.get("track", {}).get("artist") if isinstance(result.get("track"), dict) else "unknown",
        )
        return result


async def async_track_insight_tool(
    hass: HomeAssistant,
    runtime: Any,
    **parameters: Any,
) -> dict[str, Any]:
    """AI-callable Track Insight tool entry point."""
    return await TrackInsightService().async_analyze(
        hass,
        runtime,
        parameters,
        source="tool",
    )


def is_track_insight_request(text: str) -> bool:
    """Return true when Ask DJ text should route to Track Insight."""
    normalized = _normalize_text(text)
    if "track insight" in normalized:
        return True
    track_terms = (
        "this track",
        "this song",
        "current track",
        "playing track",
        "dit nummer",
        "deze track",
        "deze plaat",
        "huidige nummer",
    )
    insight_terms = (
        "tell me about",
        "analyze",
        "analyseer",
        "analyse",
        "what is special",
        "why does",
        "vibe",
        "emotional",
        "sound emotional",
        "vertel me over",
        "wat is bijzonder",
        "waarom klinkt",
        "sfeer",
    )
    return any(term in normalized for term in track_terms) and any(term in normalized for term in insight_terms)


def track_insight_error_response(exc: TrackInsightError) -> dict[str, Any]:
    """Return a response dict for a Track Insight error."""
    return exc.as_dict()


def _request_from_payload(payload: dict[str, Any], source: str) -> TrackInsightRequest:
    payload = enrich_payload_with_mood_zone(payload)
    track_payload = payload.get("track") if isinstance(payload.get("track"), dict) else {}
    playback_payload = payload.get("playback") if isinstance(payload.get("playback"), dict) else {}
    media_payload = payload.get("media") if isinstance(payload.get("media"), dict) else {}
    explicit = {**playback_payload, **media_payload, **track_payload, **payload}
    return TrackInsightRequest(
        source=str(payload.get("source") or source or "auto"),
        title=_first_text(explicit, "title", "track_name", "media_title", "name", "track"),
        artist=_first_text(explicit, "artist", "artist_name", "media_artist", "artists"),
        album=_first_text(explicit, "album", "album_name", "media_album_name", "media_album"),
        entity_id=_first_text(explicit, "entity_id"),
        player_id=_first_text(explicit, "player_id"),
        music_backend=_first_text(explicit, "music_backend", "backend", "provider"),
        force_refresh=_bool(payload.get("force_refresh")),
        locale=_optional_text(payload.get("locale") or payload.get("language")),
        mood=payload.get("mood") if isinstance(payload.get("mood"), int) else None,
        mood_zone=_optional_text(payload.get("mood_zone")),
        mood_zone_prompt=_optional_text(payload.get("mood_zone_prompt")),
        include_visual_profile=_bool(payload.get("include_visual_profile"), True),
        include_raw_response=_bool(payload.get("include_raw_response")),
    )


async def _current_playback(
    hass: HomeAssistant,
    runtime: Any,
    request: TrackInsightRequest,
) -> dict[str, Any]:
    if request.entity_id:
        state = getattr(getattr(hass, "states", None), "get", lambda _entity_id: None)(request.entity_id)
        attrs = getattr(state, "attributes", {}) or {}
        if attrs:
            return {
                "title": attrs.get("media_title"),
                "artist": attrs.get("media_artist"),
                "album": attrs.get("media_album_name") or attrs.get("media_album"),
                "artwork_url": attrs.get("entity_picture") or attrs.get("media_image_url"),
                "duration_ms": _seconds_to_ms(attrs.get("media_duration")),
                "progress_ms": _seconds_to_ms(attrs.get("media_position")),
                "is_playing": getattr(state, "state", None) == "playing",
                "entity_id": request.entity_id,
                "player_id": request.player_id or request.entity_id,
                "provider": request.music_backend,
            }
    value = {"entity_id": request.entity_id, "player_id": request.player_id}
    try:
        result = await run_music_command(hass, runtime, "status", value)
        playback = result.get("playback") if isinstance(result, dict) else {}
        if isinstance(playback, dict):
            return playback
    except TypeError:
        result = await run_music_command(hass, runtime, "status")
        playback = result.get("playback") if isinstance(result, dict) else {}
        if isinstance(playback, dict):
            return playback
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("DJConnect Track Insight playback resolution failed: %s", exc.__class__.__name__)
    playback = getattr(runtime, "last_playback", None)
    return playback if isinstance(playback, dict) else {}


def _track_contract(playback: dict[str, Any], runtime: Any, request: TrackInsightRequest) -> dict[str, Any]:
    device = playback.get("device") if isinstance(playback.get("device"), dict) else {}
    backend = (
        request.music_backend
        or playback.get("backend")
        or playback.get("provider")
        or playback.get("source")
        or getattr(runtime, "config", {}).get("music_backend")
        or DEFAULT_MUSIC_BACKEND
    )
    return {
        "title": _first_text(playback, "title", "track_name", "name", "track"),
        "artist": _first_text(playback, "artist", "artist_name", "artists"),
        "album": _first_text(playback, "album", "album_name"),
        "artwork_url": _first_text(playback, "artwork_url", "image_url", "entity_picture", "album_image_url"),
        "duration_ms": _int_ms(playback.get("duration_ms") or playback.get("duration")),
        "progress_ms": _int_ms(playback.get("progress_ms") or playback.get("position_ms") or playback.get("progress")),
        "is_playing": bool(playback.get("is_playing") or playback.get("state") == "playing"),
        "player_id": request.player_id or _first_text(playback, "player_id", "device_id") or device.get("id"),
        "entity_id": request.entity_id or _first_text(playback, "entity_id") or device.get("entity_id"),
        "backend": str(backend) if backend else None,
    }


def _normalize_analysis(data: dict[str, Any], track: dict[str, Any], locale: str | None = None) -> dict[str, Any]:
    fallback = _fallback_analysis(track, locale)
    return {
        "summary": _text(data.get("summary")) or fallback["summary"],
        "full_text": _text(data.get("full_text")) or _text(data.get("detailed_analysis")) or fallback["full_text"],
        "genre": _nullable_text(data.get("genre")),
        "subgenre": _nullable_text(data.get("subgenre")),
        "mood": _nullable_text(data.get("mood")),
        "vibe": _nullable_text(data.get("vibe")),
        "texture": _nullable_text(data.get("texture")),
        "emotional_tone": _nullable_text(data.get("emotional_tone")),
        "energy": _normalized_float(data.get("energy"), fallback["energy"]),
        "danceability": _normalized_float(data.get("danceability"), fallback["danceability"]),
        "intensity": _normalized_float(data.get("intensity"), fallback["intensity"]),
        "confidence": _normalized_float(data.get("confidence"), 0.55),
        "production_notes": _string_list(data.get("production_notes")) or fallback["production_notes"],
        "instrumentation": _string_list(data.get("instrumentation")) or fallback["instrumentation"],
        "arrangement_notes": _string_list(data.get("arrangement_notes")) or fallback["arrangement_notes"],
        "listening_cues": _string_list(data.get("listening_cues")) or fallback["listening_cues"],
        "similar_tracks": _similar_tracks(data.get("similar_tracks")),
    }


def _fallback_analysis(track: dict[str, Any], locale: str | None = None) -> dict[str, Any]:
    title = str(track.get("title") or ("dit nummer" if _is_dutch_locale(locale) else "this track"))
    artist = str(track.get("artist") or ("de artiest" if _is_dutch_locale(locale) else "the artist"))
    seed = _seed(track)
    energy = _seed_float(seed, 0)
    danceability = _seed_float(seed, 1)
    intensity = _seed_float(seed, 2)
    if _is_dutch_locale(locale):
        return {
            "summary": f"{title} van {artist} komt naar voren als een gefocust, expressief nummer met een duidelijke muzikale identiteit.",
            "full_text": (
                f"{title} van {artist} balanceert groove, arrangement en textuur. "
                "Luister naar hoe het kernmotief, de ritmesectie en de productieruimte de emotionele lijn ondersteunen."
            ),
            "genre": None,
            "subgenre": None,
            "mood": "reflectief" if intensity < 0.55 else "gedreven",
            "vibe": "meeslepend",
            "texture": "gelaagd",
            "emotional_tone": "expressief",
            "energy": energy,
            "danceability": danceability,
            "intensity": intensity,
            "confidence": 0.45,
            "production_notes": ["Let op de balans tussen de voorgrondmelodie en de ondersteunende textuur."],
            "instrumentation": ["Leidend muzikaal motief", "Ritmische basis", "Gelaagde productie-elementen"],
            "arrangement_notes": ["Het arrangement werkt waarschijnlijk door een herkenbaar idee te herhalen en tegelijk dichtheid en dynamiek te varieren."],
            "listening_cues": ["Let op de eerste grote textuurverandering.", "Luister hoe het ritme de vocal of leadlijn ondersteunt."],
            "similar_tracks": [],
        }
    return {
        "summary": f"{title} by {artist} is presented as a focused, expressive track with a clear musical identity.",
        "full_text": (
            f"{title} by {artist} balances groove, arrangement and texture. "
            "Listen for how the core motif, rhythm section and production space support the emotional arc."
        ),
        "genre": None,
        "subgenre": None,
        "mood": "reflective" if intensity < 0.55 else "driven",
        "vibe": "immersive",
        "texture": "layered",
        "emotional_tone": "expressive",
        "energy": energy,
        "danceability": danceability,
        "intensity": intensity,
        "confidence": 0.45,
        "production_notes": ["Focus on the balance between foreground melody and supporting texture."],
        "instrumentation": ["Lead musical motif", "Rhythmic foundation", "Layered production elements"],
        "arrangement_notes": ["The arrangement likely works by repeating a recognizable idea while varying density and dynamics."],
        "listening_cues": ["Notice the first major texture change.", "Listen for how the rhythm supports the vocal or lead line."],
        "similar_tracks": [],
    }


def _demo_analysis(track: dict[str, Any], locale: str | None = None) -> dict[str, Any]:
    analysis = _fallback_analysis(track, locale)
    if _is_dutch_locale(locale):
        analysis.update(
            {
                "summary": "Demo Track Insight: een gepolijste, filmische groove met warme details en een zelfverzekerde puls.",
                "genre": "electronic",
                "subgenre": "melodic house",
                "mood": "opbeurend",
                "vibe": "filmisch",
                "confidence": 0.8,
            }
        )
        return analysis
    analysis.update(
        {
            "summary": "Demo Track Insight: a polished, cinematic groove with warm detail and a confident pulse.",
            "genre": "electronic",
            "subgenre": "melodic house",
            "mood": "uplifting",
            "vibe": "cinematic",
            "confidence": 0.8,
        }
    )
    return analysis


def _visual_profile(track: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    seed = _seed(track)
    energy = _normalized_float(analysis.get("energy"), 0.5)
    danceability = _normalized_float(analysis.get("danceability"), 0.5)
    intensity = _normalized_float(analysis.get("intensity"), 0.5)
    return {
        "palette": _palette(seed),
        "motion_style": _MOTION_STYLES[int(seed[0:2], 16) % len(_MOTION_STYLES)],
        "pulse_speed": round(0.25 + danceability * 0.75, 3),
        "wave_amplitude": round(0.2 + intensity * 0.8, 3),
        "particle_density": round(0.15 + energy * 0.85, 3),
        "glow_strength": round(0.2 + ((energy + intensity) / 2) * 0.8, 3),
        "spectrum_bias": _SPECTRUM_BIASES[int(seed[2:4], 16) % len(_SPECTRUM_BIASES)],
        "seed": seed,
    }


def _strip_track_insight_music_dna_match(response: dict[str, Any]) -> dict[str, Any]:
    """Return response copy without legacy per-track Music DNA match data."""
    sanitized = dict(response)
    sanitized.pop("music_dna", None)
    return sanitized


def _palette(seed: str) -> list[str]:
    return [f"#{seed[index:index + 6]}" for index in (0, 6, 12)]


def _cache_key(
    track: dict[str, Any],
    locale: str | None = None,
    mood_context: str | None = None,
) -> str:
    identity = "|".join(
        str(track.get(key) or "").strip().lower()
        for key in ("title", "artist", "album", "backend", "duration_ms")
    )
    identity = f"{identity}|{_language_code(locale)}|{str(mood_context or '').strip().lower()}"
    return hashlib.sha256(identity.encode()).hexdigest()[:24]


def _insight_id(cache_key: str) -> str:
    return f"track_insight_{cache_key}"


def _language_code(locale: str | None) -> str:
    value = str(locale or "").strip().lower().replace("_", "-")
    if not value:
        return "en"
    return value.split("-", 1)[0] or "en"


def _request_mood_context(request: TrackInsightRequest) -> str | None:
    if request.mood is None:
        return None
    return mood_context_text(
        {
            "mood": request.mood,
            "mood_zone": request.mood_zone,
            "mood_zone_prompt": request.mood_zone_prompt,
        }
    )


def _request_mood_metadata(request: TrackInsightRequest) -> dict[str, Any] | None:
    if request.mood is None:
        return None
    return {
        "value": request.mood,
        "zone": request.mood_zone,
        "prompt": request.mood_zone_prompt,
        "text": _request_mood_context(request),
    }


def _is_dutch_locale(locale: str | None) -> bool:
    return _language_code(locale) == "nl"


def _seed(track: dict[str, Any]) -> str:
    identity = "|".join(str(track.get(key) or "") for key in ("title", "artist", "album", "duration_ms"))
    return hashlib.sha256(identity.encode()).hexdigest()


def _seed_float(seed: str, offset: int) -> float:
    start = offset * 2
    return round(int(seed[start:start + 2], 16) / 255, 3)


def _parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _first_text(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if str(item or "").strip())
        text = _optional_text(value)
        if text:
            return text
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text or None


def _nullable_text(value: Any) -> str | None:
    return _optional_text(value)


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalized_float(value: Any, default: float = 0.0) -> float:
    number = _float(value)
    if number is None:
        number = default
    if number > 1:
        number = number / 100
    return round(max(0.0, min(1.0, number)), 3)


def _int_ms(value: Any) -> int:
    number = _float(value)
    if number is None:
        return 0
    if number and number < 1000:
        number *= 1000
    return max(0, int(number))


def _seconds_to_ms(value: Any) -> int:
    number = _float(value)
    return 0 if number is None else max(0, int(number * 1000))


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _similar_tracks(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = _text(item.get("title"))
        artist = _text(item.get("artist"))
        if title and artist:
            items.append({"title": title, "artist": artist, "reason": _text(item.get("reason"))})
    return items[:5]


def _runtime_locale(runtime: Any) -> str:
    config = getattr(runtime, "config", {}) or {}
    return str(config.get("device_language") or "en")


def _demo_enabled(runtime: Any) -> bool:
    config = getattr(runtime, "config", {}) or {}
    status = getattr(runtime, "device_status", {}) or {}
    return _bool(config.get("demo_mode")) or _bool(status.get("demo_mode")) or _bool(status.get("track_insight_demo"))


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").casefold().split())
