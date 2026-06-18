from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_ASSIST_PIPELINE_ID,
)
from .wav_util import simple_tone_wav

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TtsAudio:
    """Playable HA TTS audio for DJConnect devices."""

    data: bytes
    extension: str
    content_type: str


class UnsupportedTtsAudioError(RuntimeError):
    """Raised when HA TTS works but returns audio the ESP cannot play."""


async def create_tts_audio(hass: HomeAssistant, text: str, conf: dict) -> TtsAudio:
    """Generate backend TTS audio and return WAV or MP3 bytes for the ESP."""
    try:
        from homeassistant.components import tts
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Home Assistant TTS is unavailable") from exc

    media_source_id = await _async_generate_tts_media_source_id(tts, hass, text, conf)
    if not media_source_id:
        raise RuntimeError("Home Assistant TTS did not return a media source")

    media_source_audio = getattr(tts, "async_get_media_source_audio", None)
    if media_source_audio is None:
        raise RuntimeError("Home Assistant TTS audio fetch helper is unavailable")

    mime_type, audio = await media_source_audio(hass, media_source_id)
    audio_type = _audio_type(mime_type, audio)
    if audio_type == "wav":
        return TtsAudio(audio, "wav", "audio/wav")
    if audio_type == "mp3":
        return TtsAudio(audio, "mp3", "audio/mpeg")
    raise UnsupportedTtsAudioError(
        f"Home Assistant TTS returned unsupported audio type {mime_type}"
    )


async def create_tts_wav(hass: HomeAssistant, text: str, conf: dict) -> bytes:
    """Generate backend TTS audio and return it only when HA provides WAV bytes."""
    audio = await create_tts_audio(hass, text, conf)
    if audio.extension != "wav":
        raise UnsupportedTtsAudioError(
            f"Home Assistant TTS returned unsupported audio type {audio.content_type}"
        )
    return audio.data


async def create_error_wav(hass: HomeAssistant, message: str, conf: dict) -> bytes:
    return simple_tone_wav()


def _audio_type(mime_type: Any, audio: bytes) -> str | None:
    normalized = str(mime_type or "").lower()
    if "wav" in normalized or (audio.startswith(b"RIFF") and audio[8:12] == b"WAVE"):
        return "wav"
    if (
        "mpeg" in normalized
        or "mp3" in normalized
        or audio.startswith(b"ID3")
        or (len(audio) >= 2 and audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0)
    ):
        return "mp3"
    return None


async def _async_generate_tts_media_source_id(
    tts_module: Any,
    hass: HomeAssistant,
    text: str,
    conf: dict,
) -> str | None:
    """Call the HA TTS media-source generator across supported HA versions."""
    generators = (
        getattr(tts_module, "async_generate_media_source_id", None),
        getattr(tts_module, "generate_media_source_id", None),
    )
    for generator in generators:
        if generator is None:
            continue
        for kwargs in _tts_media_source_kwargs(hass, text=text, conf=conf):
            try:
                value = generator(hass, **kwargs)
                if hasattr(value, "__await__"):
                    value = await value
                if value:
                    return str(value)
            except TypeError:
                continue
            except Exception as exc:  # noqa: BLE001
                if _is_invalid_tts_provider_error(exc):
                    attempted_engine = kwargs.get("engine") or "Home Assistant default"
                    _LOGGER.debug(
                        "DJConnect TTS provider %s is invalid; trying next TTS fallback",
                        attempted_engine,
                    )
                    continue
                _LOGGER.debug("DJConnect TTS media-source generation failed", exc_info=True)
                continue
    return None


def _tts_media_source_kwargs(
    hass: HomeAssistant,
    *,
    text: str,
    conf: dict,
) -> tuple[dict[str, Any], ...]:
    values: list[dict[str, Any]] = []
    for pipeline in _tts_pipeline_candidates(hass, conf):
        values.extend(_tts_kwargs_for_pipeline(text, pipeline))
    values.append({"message": text})
    return tuple(values)


def _tts_kwargs_for_pipeline(text: str, pipeline: Any) -> list[dict[str, Any]]:
    engine = str(_first_attr(pipeline, "tts_engine", "tts_engine_id") or "").strip()
    language = str(_first_attr(pipeline, "tts_language", "language") or "").strip()
    voice = str(_first_attr(pipeline, "tts_voice", "voice") or "").strip()
    if not engine:
        return []
    base: dict[str, Any] = {"message": text, "engine": engine}
    if language:
        base["language"] = language
    values = []
    if voice:
        with_voice = dict(base)
        with_voice["options"] = {"voice": voice}
        values.append(with_voice)
    values.append(base)
    return values


def _tts_pipeline_candidates(hass: HomeAssistant, conf: dict) -> tuple[Any, ...]:
    try:
        from homeassistant.components.assist_pipeline.pipeline import async_get_pipelines

        pipelines = async_get_pipelines(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("DJConnect could not resolve Assist pipelines for TTS", exc_info=True)
        return ()

    available = _pipeline_list(pipelines)
    candidates: list[Any] = []
    pipeline_id = str(conf.get(CONF_ASSIST_PIPELINE_ID) or "").strip()
    if pipeline_id:
        pipeline = _find_pipeline(pipelines, available, pipeline_id)
        if pipeline is not None:
            candidates.append(pipeline)

    preferred_getter = getattr(pipelines, "async_get_preferred_pipeline", None)
    if callable(preferred_getter):
        try:
            preferred = preferred_getter()
            if preferred is not None:
                candidates.append(preferred)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("DJConnect preferred Assist pipeline TTS lookup failed")

    preferred = _first_attr(pipelines, "preferred_pipeline", "current_pipeline")
    if preferred is not None:
        candidates.append(preferred)
    candidates.extend(pipeline for pipeline in available if _pipeline_has_tts(pipeline))
    return tuple(_dedupe_pipelines(candidates))


def _pipeline_list(pipelines: Any) -> list[Any]:
    if isinstance(pipelines, dict):
        return list(pipelines.values())
    mapping = getattr(pipelines, "pipelines", None)
    if isinstance(mapping, dict):
        return list(mapping.values())
    if isinstance(mapping, list | tuple):
        return list(mapping)
    try:
        return list(pipelines)
    except TypeError:
        return []


def _find_pipeline(pipelines: Any, available: list[Any], pipeline_id: str) -> Any | None:
    getter = getattr(pipelines, "async_get_pipeline", None)
    if callable(getter):
        try:
            pipeline = getter(pipeline_id)
            if pipeline is not None:
                return pipeline
        except Exception:  # noqa: BLE001
            _LOGGER.debug("DJConnect Assist pipeline TTS lookup failed")
    for pipeline in available:
        if str(getattr(pipeline, "id", "") or "") == pipeline_id:
            return pipeline
    return None


def _pipeline_has_tts(pipeline: Any) -> bool:
    return bool(_first_attr(pipeline, "tts_engine", "tts_engine_id"))


def _dedupe_pipelines(pipelines: list[Any]) -> list[Any]:
    seen: set[int | str] = set()
    result = []
    for pipeline in pipelines:
        key: int | str = str(getattr(pipeline, "id", "") or "") or id(pipeline)
        if key in seen:
            continue
        seen.add(key)
        result.append(pipeline)
    return result


def _first_attr(obj: Any, *names: str) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, ""):
            return value
    return None


def _is_invalid_tts_provider_error(exc: Exception) -> bool:
    return "invalid tts provider selected" in str(exc).lower()
