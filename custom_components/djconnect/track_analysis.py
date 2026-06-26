"""Provider-neutral Ask DJ technical track analysis."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode

from aiohttp import ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DEVICE_LANGUAGE,
    CONF_TRACK_ANALYSIS_ENABLED,
    CONF_TRACK_ANALYSIS_USE_HA_CONVERSATION,
    DEFAULT_DEVICE_LANGUAGE,
    DEFAULT_TRACK_ANALYSIS_ENABLED,
    DEFAULT_TRACK_ANALYSIS_USE_HA_CONVERSATION,
    DEFAULT_TTS_LANGUAGE,
    VERSION,
)
from .pipeline import _assist_context, _speech_from_response
from .use_cases import run_music_command as handle_spotify_command

_LOGGER = logging.getLogger(__name__)

METABRAINZ_CACHE_TTL_SECONDS = 24 * 60 * 60
METABRAINZ_MIN_REQUEST_INTERVAL_SECONDS = 1.0
METABRAINZ_USER_AGENT = f"DJConnect/{VERSION} (https://github.com/pcvantol/djconnect)"
MUSICBRAINZ_RECORDING_SEARCH_URL = "https://musicbrainz.org/ws/2/recording"
LISTENBRAINZ_METADATA_LOOKUP_URL = "https://api.listenbrainz.org/1/metadata/lookup/"


@dataclass(frozen=True)
class TrackAnalysisProviderResult:
    """Result returned by a track-analysis provider."""

    provider_id: str
    display_name: str
    status: str
    data: dict[str, Any] | None = None
    reason: str | None = None


class TrackAnalysisProvider(Protocol):
    """Provider contract for self-hosted Ask DJ technical track analysis."""

    provider_id: str
    display_name: str
    requires_config: bool

    async def async_available(self, runtime: Any) -> bool:
        """Return whether this provider should be attempted for this runtime."""

    async def async_analyze(
        self,
        hass: HomeAssistant,
        runtime: Any,
        playback_context: dict[str, Any],
        context: dict[str, Any],
    ) -> TrackAnalysisProviderResult:
        """Analyze the current track and return provider-scoped data."""


class SpotifyMeasuredAnalysisProvider:
    """Measured analysis provider backed by the user's own Spotify backend."""

    provider_id = "spotify_measured"
    display_name = "Spotify measured analysis"
    requires_config = True

    async def async_available(self, runtime: Any) -> bool:
        return True

    async def async_analyze(
        self,
        hass: HomeAssistant,
        runtime: Any,
        playback_context: dict[str, Any],
        context: dict[str, Any],
    ) -> TrackAnalysisProviderResult:
        try:
            result = await handle_spotify_command(
                hass,
                runtime,
                "technical_track_analysis",
                {"playback": playback_context},
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect technical track analysis unavailable: %s", exc)
            return TrackAnalysisProviderResult(
                self.provider_id,
                self.display_name,
                "error",
                reason=exc.__class__.__name__,
            )
        analysis = result.get("analysis") if isinstance(result, dict) else {}
        if not isinstance(analysis, dict):
            analysis = {}
        has_data = bool(analysis.get("audio_features") or analysis.get("audio_analysis") or analysis.get("track"))
        return TrackAnalysisProviderResult(
            self.provider_id,
            self.display_name,
            "used" if has_data else "unavailable",
            data=analysis,
            reason=str(analysis.get("unavailable_reason") or "") or None,
        )


class HAConversationAnalysisProvider:
    """Inference provider using the user's configured Home Assistant conversation stack."""

    provider_id = "ha_conversation"
    display_name = "Home Assistant conversation"
    requires_config = False

    async def async_available(self, runtime: Any) -> bool:
        conf = getattr(runtime, "config", {}) or {}
        return _bool(
            conf.get(CONF_TRACK_ANALYSIS_USE_HA_CONVERSATION),
            DEFAULT_TRACK_ANALYSIS_USE_HA_CONVERSATION,
        )

    async def async_analyze(
        self,
        hass: HomeAssistant,
        runtime: Any,
        playback_context: dict[str, Any],
        context: dict[str, Any],
    ) -> TrackAnalysisProviderResult:
        title = str(context.get("title") or "de huidige track")
        artist = str(context.get("artist") or "")
        features = context.get("features") if isinstance(context.get("features"), dict) else {}
        sections = context.get("sections") if isinstance(context.get("sections"), list) else []
        prompt = (
            _analysis_prompt_instruction(_analysis_language(runtime))
            +
            f"Track: {artist + ' - ' if artist else ''}{title}\n"
            f"Gemeten features: {_safe_inline_context(features)}\n"
            f"Gemeten secties: {len(sections)}"
        )
        try:
            assist_context = _assist_context(hass, getattr(runtime, "config", {}) or {})
            language = _analysis_language(runtime)
            data = {"text": prompt, "language": language}
            if assist_context.get("agent_id"):
                data["agent_id"] = assist_context["agent_id"]
            result = await hass.services.async_call(
                "conversation",
                "process",
                data,
                blocking=True,
                return_response=True,
            )
            message = _speech_from_response((result or {}).get("response") or {})
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect technical track HA conversation inference unavailable: %s", exc)
            return TrackAnalysisProviderResult(
                self.provider_id,
                self.display_name,
                "error",
                reason=exc.__class__.__name__,
            )
        if not message:
            return TrackAnalysisProviderResult(self.provider_id, self.display_name, "unavailable", reason="empty_response")
        return TrackAnalysisProviderResult(
            self.provider_id,
            self.display_name,
            "used",
            data={"provider": self.provider_id, "structure": message},
        )


class MetaBrainzMetadataProvider:
    """Free online metadata/context provider using MusicBrainz and ListenBrainz."""

    provider_id = "metabrainz_metadata"
    display_name = "MusicBrainz + ListenBrainz metadata"
    requires_config = False

    async def async_available(self, runtime: Any) -> bool:
        return True

    async def async_analyze(
        self,
        hass: HomeAssistant,
        runtime: Any,
        playback_context: dict[str, Any],
        context: dict[str, Any],
    ) -> TrackAnalysisProviderResult:
        title = str(context.get("title") or "").strip()
        artist = str(context.get("artist") or "").strip()
        if not title or not artist:
            return TrackAnalysisProviderResult(self.provider_id, self.display_name, "skipped", reason="missing_track_metadata")
        cache_key = f"track_analysis:metabrainz:{artist.lower()}:{title.lower()}"
        cached = _runtime_cache_get(runtime, cache_key, METABRAINZ_CACHE_TTL_SECONDS)
        if isinstance(cached, dict):
            return TrackAnalysisProviderResult(
                self.provider_id,
                self.display_name,
                "used" if cached.get("metadata") else "unavailable",
                data=cached,
                reason=str(cached.get("reason") or "") or None,
            )
        if not _runtime_rate_limit_ok(runtime, "metabrainz_metadata"):
            return TrackAnalysisProviderResult(self.provider_id, self.display_name, "skipped", reason="rate_limited")
        try:
            session = async_get_clientsession(hass)
            if session is None:
                raise RuntimeError("missing_http_session")
            musicbrainz = await _musicbrainz_recording_lookup(session, artist, title)
            listenbrainz = await _listenbrainz_metadata_lookup(session, artist, title)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect MetaBrainz track metadata unavailable: %s", exc)
            return TrackAnalysisProviderResult(self.provider_id, self.display_name, "error", reason=exc.__class__.__name__)
        metadata = _metabrainz_metadata(artist, title, musicbrainz, listenbrainz)
        data = {
            "provider": self.provider_id,
            "structure": _metabrainz_structure(metadata),
            "metadata": metadata,
            "limitations": _metabrainz_limitations(metadata),
        }
        _runtime_cache_set(runtime, cache_key, data)
        return TrackAnalysisProviderResult(
            self.provider_id,
            self.display_name,
            "used" if metadata else "unavailable",
            data=data,
            reason=None if metadata else "no_metadata_match",
        )


class LocalFallbackAnalysisProvider:
    """Always-available local fallback provider with no external service calls."""

    provider_id = "local_fallback"
    display_name = "Local fallback"
    requires_config = False

    async def async_available(self, runtime: Any) -> bool:
        return True

    async def async_analyze(
        self,
        hass: HomeAssistant,
        runtime: Any,
        playback_context: dict[str, Any],
        context: dict[str, Any],
    ) -> TrackAnalysisProviderResult:
        title = str(context.get("title") or "de huidige track")
        artist = str(context.get("artist") or "")
        features = context.get("features") if isinstance(context.get("features"), dict) else {}
        sections = context.get("sections") if isinstance(context.get("sections"), list) else []
        return TrackAnalysisProviderResult(
            self.provider_id,
            self.display_name,
            "used",
            data={"provider": self.provider_id, "structure": _local_inference(title, artist, features, sections)},
        )


TRACK_ANALYSIS_PROVIDERS: tuple[TrackAnalysisProvider, ...] = (
    SpotifyMeasuredAnalysisProvider(),
    MetaBrainzMetadataProvider(),
    HAConversationAnalysisProvider(),
    LocalFallbackAnalysisProvider(),
)


async def async_analyze_current_track(
    hass: HomeAssistant,
    runtime: Any,
    playback_context: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate measured and inferred analysis for the current track."""
    conf = getattr(runtime, "config", {}) or {}
    if not _bool(conf.get(CONF_TRACK_ANALYSIS_ENABLED), DEFAULT_TRACK_ANALYSIS_ENABLED):
        message = _disabled_text(runtime)
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "track_analysis",
            "analysis": {
                "contract_version": 2,
                "mode": "unavailable",
                "confidence": "low",
                "measured": {},
                "inferred": {},
                "sections": [],
                "timeline": [],
                "dj_tips": [],
                "providers": [
                    _provider_status(
                        "spotify_measured",
                        "Spotify measured analysis",
                        "skipped",
                        True,
                        "track_analysis_disabled",
                    ),
                    _provider_status(
                        "metabrainz_metadata",
                        "MusicBrainz + ListenBrainz metadata",
                        "skipped",
                        False,
                        "track_analysis_disabled",
                    ),
                    _provider_status(
                        "ha_conversation",
                        "Home Assistant conversation",
                        "skipped",
                        False,
                        "track_analysis_disabled",
                    ),
                    _provider_status("local_fallback", "Local fallback", "skipped", False, "track_analysis_disabled"),
                ],
                "limitations": ["Track analysis is disabled in DJConnect options."],
            },
            "items": [],
            "images": [],
            "links": [],
            "sources": [],
            "playback_actions": [],
        }
    provider_results = await _run_provider_chain(hass, runtime, playback_context)
    analysis = _provider_data(provider_results, "spotify_measured")
    track = analysis.get("track") if isinstance(analysis.get("track"), dict) else playback_context
    if not playback_context and not track:
        message = "Ik kan nu niet betrouwbaar zien welke track er speelt, dus ik kan nog geen technische trackanalyse geven."
        return {
            "success": True,
            "text": message,
            "dj_text": message,
            "action": "track_analysis",
            "analysis": {
                "contract_version": 2,
                "mode": "unavailable",
                "confidence": "low",
                "measured": {},
                "inferred": {},
                "sections": [],
                "timeline": [],
                "dj_tips": [],
                "providers": _providers_contract(provider_results),
                "limitations": ["No current playback context was available for track analysis."],
            },
            "items": [],
            "images": [],
            "links": [],
            "sources": [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}],
            "playback_actions": [],
        }
    title = _track_title_from_context(track) or "de huidige track"
    artist = _artist_from_playback_context(track) or _artist_from_playback_context(playback_context)
    features = analysis.get("audio_features") if isinstance(analysis.get("audio_features"), dict) else {}
    audio_analysis = analysis.get("audio_analysis") if isinstance(analysis.get("audio_analysis"), dict) else {}
    sections = audio_analysis.get("sections") if isinstance(audio_analysis.get("sections"), list) else []
    inference_results = await _run_inference_providers(
        hass,
        runtime,
        playback_context,
        title,
        artist,
        features,
        sections,
    )
    provider_results.extend(inference_results)
    inferred = _inferred_from_results(inference_results, title, artist, features, sections)
    metadata = _metadata_from_results(inference_results)
    measured = _measured_context(features, sections)
    limitations = _limitations(features, sections, inferred)
    limitations.extend(_metadata_limitations(inference_results))
    analysis.update(
        {
            "contract_version": 2,
            "mode": _analysis_mode(measured, inferred),
            "confidence": _confidence(measured, inferred),
            "measured": measured,
            "inferred": inferred,
            "metadata": metadata,
            "sections": _client_sections(features, sections, inferred, limitations, metadata),
            "timeline": _client_timeline(sections),
            "dj_tips": _dj_tips(features, sections),
            "providers": _providers_contract(provider_results),
            "limitations": limitations,
        }
    )
    sources = [{"source": "spotify_playback_context", "title": "Spotify playback context", "kind": "source"}]
    if features:
        sources.append({"source": "spotify_audio_features", "title": "Spotify audio features", "kind": "source"})
    if sections:
        sources.append({"source": "spotify_audio_analysis", "title": "Spotify audio analysis", "kind": "source"})
    if metadata:
        sources.append({"source": "metabrainz_metadata", "title": "MusicBrainz + ListenBrainz metadata", "kind": "source"})
    if inferred.get("provider") == "ha_conversation":
        sources.append({"source": "ha_conversation", "title": "Home Assistant conversation", "kind": "source"})
    message = _analysis_text(title, artist, features, sections, analysis)
    return {
        "success": True,
        "text": message,
        "dj_text": message,
        "action": "track_analysis",
        "analysis": analysis,
        "items": _analysis_items(features, sections),
        "images": [],
        "links": [],
        "sources": sources,
        "playback_actions": [],
    }


async def _run_provider_chain(
    hass: HomeAssistant,
    runtime: Any,
    playback_context: dict[str, Any],
) -> list[TrackAnalysisProviderResult]:
    results: list[TrackAnalysisProviderResult] = []
    provider = TRACK_ANALYSIS_PROVIDERS[0]
    if not await provider.async_available(runtime):
        return [TrackAnalysisProviderResult(provider.provider_id, provider.display_name, "skipped", reason="not_available")]
    results.append(await provider.async_analyze(hass, runtime, playback_context, {}))
    return results


async def _run_inference_providers(
    hass: HomeAssistant,
    runtime: Any,
    playback_context: dict[str, Any],
    title: str,
    artist: str,
    features: dict[str, Any],
    sections: list[Any],
) -> list[TrackAnalysisProviderResult]:
    results: list[TrackAnalysisProviderResult] = []
    context = {"title": title, "artist": artist, "features": features, "sections": sections}
    for provider in TRACK_ANALYSIS_PROVIDERS[1:]:
        if not await provider.async_available(runtime):
            results.append(
                TrackAnalysisProviderResult(
                    provider.provider_id,
                    provider.display_name,
                    "skipped",
                    reason="disabled_by_options",
                )
            )
            continue
        result = await provider.async_analyze(hass, runtime, playback_context, context)
        results.append(result)
        if result.status == "used" and provider.provider_id == "ha_conversation":
            break
    return results


def _inferred_from_results(
    results: list[TrackAnalysisProviderResult],
    title: str,
    artist: str,
    features: dict[str, Any],
    sections: list[Any],
) -> dict[str, Any]:
    for preferred_provider in ("ha_conversation", "metabrainz_metadata", "local_fallback"):
        for result in results:
            data = result.data if isinstance(result.data, dict) else {}
            if result.provider_id == preferred_provider and result.status == "used" and data.get("structure"):
                return {"provider": result.provider_id, "structure": str(data["structure"])}
    for result in results:
        data = result.data if isinstance(result.data, dict) else {}
        if result.status == "used" and data.get("structure"):
            return {"provider": result.provider_id, "structure": str(data["structure"])}
    return {"provider": "local_fallback", "structure": _local_inference(title, artist, features, sections)}


def _metadata_from_results(results: list[TrackAnalysisProviderResult]) -> dict[str, Any]:
    for result in results:
        if result.provider_id != "metabrainz_metadata" or not isinstance(result.data, dict):
            continue
        metadata = result.data.get("metadata")
        return metadata if isinstance(metadata, dict) else {}
    return {}


def _metadata_limitations(results: list[TrackAnalysisProviderResult]) -> list[str]:
    for result in results:
        if result.provider_id != "metabrainz_metadata" or not isinstance(result.data, dict):
            continue
        limitations = result.data.get("limitations")
        if isinstance(limitations, list):
            return [str(item) for item in limitations if str(item or "").strip()]
    return []


def _provider_data(results: list[TrackAnalysisProviderResult], provider_id: str) -> dict[str, Any]:
    for result in results:
        if result.provider_id == provider_id and isinstance(result.data, dict):
            return dict(result.data)
    return {}


def _providers_contract(results: list[TrackAnalysisProviderResult]) -> list[dict[str, Any]]:
    return [
        _provider_status(
            result.provider_id,
            result.display_name,
            result.status,
            _provider_requires_config(result.provider_id),
            result.reason,
        )
        for result in results
    ]


def _provider_status(
    provider_id: str,
    display_name: str,
    status: str,
    requires_config: bool,
    reason: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "provider_id": provider_id,
        "display_name": display_name,
        "status": status,
        "requires_config": requires_config,
    }
    if reason:
        item["reason"] = reason
    return item


def _provider_requires_config(provider_id: str) -> bool:
    for provider in TRACK_ANALYSIS_PROVIDERS:
        if provider.provider_id == provider_id:
            return provider.requires_config
    return False


async def _musicbrainz_recording_lookup(session: Any, artist: str, title: str) -> dict[str, Any]:
    query = f'recording:"{title}" AND artist:"{artist}"'
    params = {
        "query": query,
        "limit": "1",
        "fmt": "json",
        "inc": "artist-credits+releases+tags+genres",
    }
    url = f"{MUSICBRAINZ_RECORDING_SEARCH_URL}?{urlencode(params)}"
    body = await _json_get(session, url, service="musicbrainz")
    recordings = body.get("recordings") if isinstance(body, dict) else []
    if not isinstance(recordings, list) or not recordings:
        return {}
    recording = recordings[0]
    return recording if isinstance(recording, dict) else {}


async def _listenbrainz_metadata_lookup(session: Any, artist: str, title: str) -> dict[str, Any]:
    params = {"artist_name": artist, "recording_name": title}
    url = f"{LISTENBRAINZ_METADATA_LOOKUP_URL}?{urlencode(params)}"
    body = await _json_get(session, url, service="listenbrainz")
    return body if isinstance(body, dict) else {}


async def _json_get(session: Any, url: str, *, service: str) -> dict[str, Any]:
    headers = {"Accept": "application/json", "User-Agent": METABRAINZ_USER_AGENT}
    async with session.get(url, headers=headers, timeout=ClientTimeout(total=6)) as response:
        status = int(getattr(response, "status", 0) or 0)
        if status == 404:
            return {}
        if status == 429:
            raise RuntimeError(f"{service}_rate_limited")
        if status < 200 or status >= 300:
            raise RuntimeError(f"{service}_http_{status}")
        data = await response.json(content_type=None)
    return data if isinstance(data, dict) else {}


def _metabrainz_metadata(
    artist: str,
    title: str,
    musicbrainz: dict[str, Any],
    listenbrainz: dict[str, Any],
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if musicbrainz:
        metadata["musicbrainz_recording_id"] = str(musicbrainz.get("id") or "").strip()
        metadata["match_score"] = _int_value(musicbrainz.get("score"))
        metadata["recording_title"] = str(musicbrainz.get("title") or title).strip()
        metadata["artist"] = _musicbrainz_artist_credit(musicbrainz) or artist
        first_release_date = str(musicbrainz.get("first-release-date") or "").strip()
        if first_release_date:
            metadata["first_release_date"] = first_release_date
        releases = musicbrainz.get("releases") if isinstance(musicbrainz.get("releases"), list) else []
        release = next((item for item in releases if isinstance(item, dict)), {})
        if release:
            metadata["release"] = {
                key: value
                for key, value in {
                    "title": str(release.get("title") or "").strip(),
                    "date": str(release.get("date") or "").strip(),
                    "country": str(release.get("country") or "").strip(),
                    "status": str(release.get("status") or "").strip(),
                }.items()
                if value
            }
        genres = _tag_names(musicbrainz.get("genres"))
        tags = _tag_names(musicbrainz.get("tags"))
        if genres:
            metadata["genres"] = genres[:6]
        if tags:
            metadata["tags"] = tags[:8]
    listen_metadata = listenbrainz.get("metadata") if isinstance(listenbrainz.get("metadata"), dict) else listenbrainz
    if isinstance(listen_metadata, dict):
        total_listen_count = _int_value(
            listen_metadata.get("total_listen_count")
            or listen_metadata.get("recording_listen_count")
            or listen_metadata.get("listen_count")
        )
        if total_listen_count is not None:
            metadata["listenbrainz_listen_count"] = total_listen_count
        artist_mbids = listen_metadata.get("artist_mbids")
        if isinstance(artist_mbids, list):
            metadata["listenbrainz_artist_mbids"] = [str(item) for item in artist_mbids[:4] if str(item or "").strip()]
        recording_mbid = str(listen_metadata.get("recording_mbid") or "").strip()
        if recording_mbid and not metadata.get("musicbrainz_recording_id"):
            metadata["musicbrainz_recording_id"] = recording_mbid
    return {key: value for key, value in metadata.items() if value not in ("", None, [], {})}


def _metabrainz_structure(metadata: dict[str, Any]) -> str:
    if not metadata:
        return ""
    parts = []
    genres = metadata.get("genres") or metadata.get("tags") or []
    if genres:
        parts.append("open metadata wijst op " + ", ".join(str(item) for item in genres[:3]))
    release = metadata.get("release") if isinstance(metadata.get("release"), dict) else {}
    release_title = release.get("title") if release else ""
    release_date = metadata.get("first_release_date") or (release.get("date") if release else "")
    if release_title:
        detail = str(release_title)
        if release_date:
            detail += f" ({release_date})"
        parts.append(f"gekoppeld aan release {detail}")
    elif release_date:
        parts.append(f"eerste release rond {release_date}")
    listen_count = metadata.get("listenbrainz_listen_count")
    if listen_count is not None:
        parts.append(f"ListenBrainz-context telt {listen_count} publieke listens")
    if not parts:
        return "MusicBrainz/ListenBrainz leveren wel een match, maar weinig bruikbare technische context."
    return "MetaBrainz-context: " + "; ".join(parts) + "."


def _metabrainz_limitations(metadata: dict[str, Any]) -> list[str]:
    if not metadata:
        return ["MusicBrainz/ListenBrainz did not return a reliable metadata match for this track."]
    return [
        "MusicBrainz/ListenBrainz metadata is contextual and does not measure BPM, key, waveform, stems or exact arrangement sections."
    ]


def _metadata_items(metadata: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if metadata.get("musicbrainz_recording_id"):
        items.append({"label": "MusicBrainz recording", "value": str(metadata["musicbrainz_recording_id"]), "source": "metabrainz_metadata"})
    if metadata.get("first_release_date"):
        items.append({"label": "First release", "value": str(metadata["first_release_date"]), "source": "metabrainz_metadata"})
    release = metadata.get("release") if isinstance(metadata.get("release"), dict) else {}
    if release.get("title"):
        items.append({"label": "Release", "value": str(release["title"]), "source": "metabrainz_metadata"})
    genres = metadata.get("genres") or metadata.get("tags") or []
    if genres:
        items.append({"label": "Genres/tags", "value": ", ".join(str(item) for item in genres[:5]), "source": "metabrainz_metadata"})
    if metadata.get("listenbrainz_listen_count") is not None:
        items.append({"label": "ListenBrainz listens", "value": str(metadata["listenbrainz_listen_count"]), "source": "metabrainz_metadata"})
    return items


def _metadata_summary(metadata: dict[str, Any]) -> str:
    return _metabrainz_structure(metadata).removeprefix("MetaBrainz-context: ").rstrip(".")


def _musicbrainz_artist_credit(recording: dict[str, Any]) -> str:
    credits = recording.get("artist-credit") if isinstance(recording.get("artist-credit"), list) else []
    names = []
    for credit in credits:
        if not isinstance(credit, dict):
            continue
        artist = credit.get("artist") if isinstance(credit.get("artist"), dict) else {}
        name = str(artist.get("name") or credit.get("name") or "").strip()
        if name:
            names.append(name)
    return ", ".join(names[:3])


def _tag_names(value: Any) -> list[str]:
    tags = value if isinstance(value, list) else []
    names = []
    for item in tags:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name and name.lower() not in {existing.lower() for existing in names}:
            names.append(name)
    return names


def _runtime_cache_get(runtime: Any, key: str, ttl: int) -> Any:
    cache = getattr(runtime, "backend_cache", None)
    if not isinstance(cache, dict):
        return None
    cached = cache.get(key)
    if not cached or not isinstance(cached, tuple) or len(cached) != 2:
        return None
    timestamp, value = cached
    try:
        age = time.monotonic() - float(timestamp)
    except (TypeError, ValueError):
        return None
    return value if age < ttl else None


def _runtime_cache_set(runtime: Any, key: str, value: Any) -> None:
    cache = getattr(runtime, "backend_cache", None)
    if not isinstance(cache, dict):
        runtime.backend_cache = {}
        cache = runtime.backend_cache
    cache[key] = (time.monotonic(), value)


def _runtime_rate_limit_ok(runtime: Any, provider_id: str) -> bool:
    cache = getattr(runtime, "backend_cache", None)
    if not isinstance(cache, dict):
        runtime.backend_cache = {}
        cache = runtime.backend_cache
    key = f"track_analysis:last_request:{provider_id}"
    now = time.monotonic()
    last = cache.get(key)
    try:
        if last is not None and now - float(last) < METABRAINZ_MIN_REQUEST_INTERVAL_SECONDS:
            return False
    except (TypeError, ValueError):
        pass
    cache[key] = now
    return True


def _analysis_prompt_instruction(language: str) -> str:
    if str(language or "").lower().startswith("en"):
        return (
            "Give at most two short English sentences with a technical DJ-style "
            "interpretation of this track. Mention exact BPM, key, timestamps or "
            "section labels only when they are explicitly present in the supplied "
            "data. Keep uncertainty compact.\n"
        )
    return (
        "Geef in maximaal twee korte Nederlandse zinnen een technische DJ-duiding "
        "van deze track. Noem alleen exacte BPM, key, timestamps of sectielabels "
        "als die expliciet in de meegegeven data staan. Markeer onzekerheid niet "
        "uitgebreid; wees compact.\n"
    )


def _analysis_language(runtime: Any) -> str:
    language = ""
    getter = getattr(runtime, "device_language", None)
    if callable(getter):
        try:
            language = str(getter() or "").strip()
        except Exception:  # noqa: BLE001
            language = ""
    conf = getattr(runtime, "config", {}) or {}
    language = language or str(conf.get(CONF_DEVICE_LANGUAGE) or "").strip()
    if language.lower().startswith("en"):
        return "en-US"
    if language.lower().startswith("nl"):
        return "nl-NL"
    return DEFAULT_TTS_LANGUAGE or DEFAULT_DEVICE_LANGUAGE


def _disabled_text(runtime: Any) -> str:
    if _analysis_language(runtime).lower().startswith("en"):
        return "Track analysis is disabled in DJConnect options."
    return "Trackanalyse staat uit in de DJConnect opties."


def _bool(value: Any, default: bool) -> bool:
    return default if value is None else bool(value)


def _analysis_text(
    title: str,
    artist: str,
    features: dict[str, Any],
    sections: list[Any],
    analysis: dict[str, Any],
) -> str:
    heading = f"Technische trackanalyse voor {artist} - {title}" if artist else f"Technische trackanalyse voor {title}"
    lines = [heading + "."]
    tempo = _rounded_number(features.get("tempo"))
    key = _musical_key_label(features.get("key"), features.get("mode"))
    if tempo or key:
        details = []
        if tempo:
            details.append(f"{tempo} BPM")
        if key:
            details.append(key)
        lines.append("- Basis: " + ", ".join(details) + ".")
    groove = _groove_line(features)
    if groove:
        lines.append("- Groove: " + groove)
    if sections:
        lines.append("- Opbouw: " + _sections_summary(sections) + ".")
    else:
        lines.append("- Opbouw: diepe sectie-analyse is nu niet beschikbaar; ik baseer dit niet op verzonnen intro/couplet/refrein-labels.")
    inferred = analysis.get("inferred") if isinstance(analysis.get("inferred"), dict) else {}
    structure = str(inferred.get("structure") or "").strip()
    if structure:
        lines.append("- Muzikale duiding: " + structure)
    instrument_hint = _instrument_hint(features)
    if instrument_hint:
        lines.append("- Instrumentatie/klank: " + instrument_hint)
    if not features and not sections:
        reason = str(analysis.get("unavailable_reason") or "").strip()
        suffix = f" ({reason})" if reason else ""
        lines.append(
            "- Live audiofeatures zijn nu niet beschikbaar"
            + suffix
            + "; ik kan daardoor geen betrouwbare BPM, key of arrangementdetails geven."
        )
    return "\n".join(lines)


def _analysis_items(features: dict[str, Any], sections: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    tempo = _rounded_number(features.get("tempo"))
    if tempo:
        items.append({"kind": "technical_metric", "title": "BPM", "value": tempo})
    key = _musical_key_label(features.get("key"), features.get("mode"))
    if key:
        items.append({"kind": "technical_metric", "title": "Key", "value": key})
    for field, label in (("danceability", "Danceability"), ("energy", "Energy"), ("valence", "Valence"), ("acousticness", "Acousticness")):
        value = _percentage(features.get(field))
        if value:
            items.append({"kind": "technical_metric", "title": label, "value": value})
    if sections:
        items.append({"kind": "arrangement", "title": "Sections", "value": str(len(sections))})
    return items


def _client_sections(
    features: dict[str, Any],
    sections: list[Any],
    inferred: dict[str, Any],
    limitations: list[str],
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    metadata = metadata or {}
    tempo = _rounded_number(features.get("tempo"))
    key = _musical_key_label(features.get("key"), features.get("mode"))
    basis_items = []
    if tempo:
        basis_items.append({"label": "BPM", "value": tempo, "source": "measured"})
    if key:
        basis_items.append({"label": "Key", "value": key, "source": "measured"})
    signature = features.get("time_signature")
    if signature:
        basis_items.append({"label": "Time signature", "value": str(signature), "source": "measured"})
    if basis_items:
        result.append(
            {
                "id": "rhythm_bpm",
                "title": "Rhythm & BPM",
                "kind": "technical_metrics",
                "confidence": "high" if tempo else "medium",
                "source": "measured",
                "items": basis_items,
            }
        )

    groove_items = []
    for field, label in (
        ("danceability", "Danceability"),
        ("energy", "Energy"),
        ("valence", "Valence"),
        ("acousticness", "Acousticness"),
        ("instrumentalness", "Instrumentalness"),
    ):
        value = _percentage(features.get(field))
        if value:
            groove_items.append({"label": label, "value": value, "source": "measured"})
    if groove_items:
        result.append(
            {
                "id": "energy_curve",
                "title": "Energy Curve",
                "kind": "audio_features",
                "confidence": "medium",
                "source": "measured",
                "items": groove_items,
            }
        )

    if sections:
        result.append(
            {
                "id": "buildup",
                "title": "Build-up",
                "kind": "arrangement",
                "confidence": "medium",
                "source": "measured",
                "summary": _sections_summary(sections),
                "items": [{"label": "Detected sections", "value": str(len(_measured_sections(sections))), "source": "measured"}],
            }
        )
    else:
        result.append(
            {
                "id": "buildup",
                "title": "Build-up",
                "kind": "arrangement",
                "confidence": "low",
                "source": "unavailable",
                "summary": "Exact intro, verse, chorus, drop or outro timestamps were not measured.",
                "items": [],
            }
        )

    instrument_hint = _instrument_hint(features)
    if instrument_hint:
        result.append(
            {
                "id": "instrumentation",
                "title": "Instrumentation",
                "kind": "timbre_hint",
                "confidence": "low",
                "source": "inferred",
                "summary": instrument_hint.rstrip("."),
                "items": [],
            }
        )

    metadata_items = _metadata_items(metadata)
    if metadata_items:
        result.append(
            {
                "id": "metadata_context",
                "title": "Metadata Context",
                "kind": "metadata_context",
                "confidence": "medium",
                "source": "metabrainz_metadata",
                "summary": _metadata_summary(metadata),
                "items": metadata_items,
            }
        )

    structure = str(inferred.get("structure") or "").strip()
    if structure:
        result.append(
            {
                "id": "melody_harmony",
                "title": "Melody & Harmony",
                "kind": "musical_interpretation",
                "confidence": "low" if inferred.get("provider") == "local_fallback" else "medium",
                "source": inferred.get("provider") or "inferred",
                "summary": structure,
                "items": [],
            }
        )

    result.append(
        {
            "id": "limitations",
            "title": "Limitations",
            "kind": "limitations",
            "confidence": "high",
            "source": "system",
            "items": [{"label": "Note", "value": item, "source": "system"} for item in limitations],
        }
    )
    return result


def _client_timeline(sections: list[Any]) -> list[dict[str, Any]]:
    timeline = []
    for item in _measured_sections(sections):
        entry = {
            "label": f"Section {item['index']}",
            "kind": "section",
            "source": "measured",
            "confidence": item.get("confidence"),
        }
        if "start_ms" in item:
            entry["start_ms"] = item["start_ms"]
        if "duration_ms" in item:
            entry["duration_ms"] = item["duration_ms"]
            if "start_ms" in item:
                entry["end_ms"] = item["start_ms"] + item["duration_ms"]
        timeline.append(entry)
    return timeline


def _dj_tips(features: dict[str, Any], sections: list[Any]) -> list[dict[str, Any]]:
    tips: list[dict[str, Any]] = []
    tempo = _rounded_number(features.get("tempo"))
    if tempo:
        tips.append(
            {
                "kind": "mixing",
                "title": "Tempo match",
                "text": f"Use {tempo} BPM as the beatmatch anchor.",
                "confidence": "high",
                "source": "measured",
            }
        )
    energy = _float_value(features.get("energy"))
    danceability = _float_value(features.get("danceability"))
    if energy is not None:
        if energy >= 0.75:
            text = "Best placed when the set can handle a higher-energy lift."
        elif energy <= 0.35:
            text = "Best placed as a reset, warm-up or late-night breather."
        else:
            text = "Flexible energy: useful as a bridge between warm-up and peak material."
        tips.append({"kind": "set_placement", "title": "Energy placement", "text": text, "confidence": "medium", "source": "measured"})
    if danceability is not None and danceability < 0.45:
        tips.append(
            {
                "kind": "watch_out",
                "title": "Groove caution",
                "text": "Danceability is modest, so check the transition by ear before relying on it as a floor lock.",
                "confidence": "medium",
                "source": "measured",
            }
        )
    if sections:
        first = next((section for section in sections if isinstance(section, dict)), {})
        duration = _float_value(first.get("duration")) if isinstance(first, dict) else None
        if duration is not None and duration >= 16:
            tips.append(
                {
                    "kind": "mixing",
                    "title": "Intro room",
                    "text": f"The first measured section lasts about {_rounded_number(duration)} seconds, which may give room for a clean mix-in.",
                    "confidence": "medium",
                    "source": "measured",
                }
            )
    if not tips:
        tips.append(
            {
                "kind": "limitation",
                "title": "DJ use",
                "text": "Not enough measured audio data is available for reliable mix-in, mix-out or set-placement advice.",
                "confidence": "low",
                "source": "system",
            }
        )
    return tips


def _measured_context(features: dict[str, Any], sections: list[Any]) -> dict[str, Any]:
    measured: dict[str, Any] = {"features": {}}
    tempo = _float_value(features.get("tempo"))
    if tempo is not None:
        measured["bpm"] = round(tempo, 1)
    key = _musical_key_label(features.get("key"), features.get("mode"))
    if key:
        measured["key"] = key
    if features.get("time_signature"):
        measured["time_signature"] = features.get("time_signature")
    for field in ("energy", "danceability", "acousticness", "instrumentalness", "valence", "speechiness"):
        value = _float_value(features.get(field))
        if value is not None:
            measured["features"][field] = value
    measured["sections"] = _measured_sections(sections)
    if not measured["features"]:
        measured.pop("features", None)
    return measured


def _measured_sections(sections: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        start = _float_value(section.get("start"))
        duration = _float_value(section.get("duration"))
        confidence = _float_value(section.get("confidence"))
        item: dict[str, Any] = {"label": "section", "index": index}
        if start is not None:
            item["start_ms"] = int(start * 1000)
        if duration is not None:
            item["duration_ms"] = int(duration * 1000)
        if confidence is not None:
            item["confidence"] = confidence
        result.append(item)
    return result


def _analysis_mode(measured: dict[str, Any], inferred: dict[str, Any]) -> str:
    has_measured = any(measured.get(key) for key in ("bpm", "key", "time_signature", "sections", "features"))
    has_inferred = bool(inferred.get("structure"))
    if has_measured and has_inferred:
        return "measured_plus_knowledge"
    if has_measured:
        return "measured"
    if has_inferred:
        return "knowledge_plus_metadata"
    return "unavailable"


def _confidence(measured: dict[str, Any], inferred: dict[str, Any]) -> str:
    if measured.get("bpm") and measured.get("key") and measured.get("sections"):
        return "high"
    if measured.get("bpm") or measured.get("key") or inferred.get("provider") == "ha_conversation":
        return "medium"
    return "low"


def _limitations(features: dict[str, Any], sections: list[Any], inferred: dict[str, Any]) -> list[str]:
    limitations = []
    if not features:
        limitations.append("BPM, key and audio feature values were not available from a measured provider.")
    if not sections:
        limitations.append("Exact intro, verse, chorus, drop or outro timestamps were not measured.")
    if inferred.get("provider") == "local_fallback":
        limitations.append("Musical interpretation is based on local metadata/fallback rules, not a deep model.")
    return limitations


def _local_inference(title: str, artist: str, features: dict[str, Any], sections: list[Any]) -> str:
    if features or sections:
        parts = []
        energy = _float_value(features.get("energy"))
        danceability = _float_value(features.get("danceability"))
        if energy is not None:
            parts.append("hoog energetisch" if energy >= 0.7 else "rustiger energetisch" if energy <= 0.35 else "matig energetisch")
        if danceability is not None:
            parts.append("duidelijk groovegericht" if danceability >= 0.65 else "minder rechttoe-rechtaan dansbaar")
        if sections:
            parts.append(f"met {len(sections)} gedetecteerde sectiewissels")
        if parts:
            return "Op basis van de beschikbare brondata klinkt dit " + ", ".join(parts) + "."
    label = f"{artist} - {title}" if artist else title
    return (
        f"Voor {label} heb ik nu vooral playbackmetadata; ik kan de muzikale rol duiden, "
        "maar geen gemeten BPM, key of exacte songstructuur claimen."
    )


def _groove_line(features: dict[str, Any]) -> str:
    parts = []
    danceability = _percentage(features.get("danceability"))
    energy = _percentage(features.get("energy"))
    valence = _percentage(features.get("valence"))
    if danceability:
        parts.append(f"danceability {danceability}")
    if energy:
        parts.append(f"energie {energy}")
    if valence:
        parts.append(f"valence {valence}")
    return ", ".join(parts) + "." if parts else ""


def _instrument_hint(features: dict[str, Any]) -> str:
    hints = []
    acousticness = _float_value(features.get("acousticness"))
    instrumentalness = _float_value(features.get("instrumentalness"))
    speechiness = _float_value(features.get("speechiness"))
    if acousticness is not None and acousticness >= 0.55:
        hints.append("relatief akoestisch")
    if instrumentalness is not None and instrumentalness >= 0.45:
        hints.append("sterk instrumentaal")
    if speechiness is not None and speechiness >= 0.33:
        hints.append("spraak/rap-achtig aandeel valt op")
    return ", ".join(hints) + "." if hints else ""


def _sections_summary(sections: list[Any]) -> str:
    clean_sections = [section for section in sections if isinstance(section, dict)]
    if not clean_sections:
        return "geen bruikbare secties gevonden"
    first = clean_sections[0]
    last = clean_sections[-1]
    duration = _rounded_number((float(last.get("start") or 0) + float(last.get("duration") or 0)) if last else None)
    confidence_values = [
        _float_value(section.get("confidence"))
        for section in clean_sections
        if _float_value(section.get("confidence")) is not None
    ]
    confidence = sum(confidence_values) / len(confidence_values) if confidence_values else None
    detail = f"{len(clean_sections)} muzikale secties"
    if duration:
        detail += f" over ongeveer {duration} seconden"
    if confidence is not None:
        detail += f", gemiddelde sectiezekerheid {_percentage(confidence)}"
    first_tempo = _rounded_number(first.get("tempo"))
    last_tempo = _rounded_number(last.get("tempo"))
    if first_tempo and last_tempo and first_tempo != last_tempo:
        detail += f", tempo beweegt van {first_tempo} naar {last_tempo} BPM"
    return detail


def _track_title_from_context(context: dict[str, Any]) -> str:
    for key in ("track_name", "title", "name"):
        value = str(context.get(key) or "").strip()
        if value:
            return value
    track = context.get("track")
    if isinstance(track, dict):
        return _track_title_from_context(track)
    return ""


def _artist_from_playback_context(playback_context: dict[str, Any]) -> str:
    for key in ("artist", "artist_name"):
        value = str(playback_context.get(key) or "").strip()
        if value:
            return value
    track = playback_context.get("track")
    if isinstance(track, dict):
        for key in ("artist", "artist_name"):
            value = str(track.get(key) or "").strip()
            if value:
                return value
    return ""


def _musical_key_label(key: Any, mode: Any) -> str:
    try:
        key_index = int(key)
    except (TypeError, ValueError):
        return ""
    if key_index < 0 or key_index > 11:
        return ""
    names = ("C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B")
    mode_label = "major" if str(mode) == "1" else "minor" if str(mode) == "0" else ""
    return f"{names[key_index]} {mode_label}".strip()


def _rounded_number(value: Any) -> str:
    numeric = _float_value(value)
    if numeric is None:
        return ""
    if abs(numeric - round(numeric)) < 0.05:
        return str(int(round(numeric)))
    return f"{numeric:.1f}"


def _percentage(value: Any) -> str:
    numeric = _float_value(value)
    if numeric is None:
        return ""
    return f"{max(0, min(100, round(numeric * 100)))}%"


def _float_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_inline_context(value: Any) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return text[:1200]
