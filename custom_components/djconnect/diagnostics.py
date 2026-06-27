from __future__ import annotations

from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_MUSIC_BACKEND,
    CONF_ASSIST_PIPELINE_ID,
    CONF_SPOTIFY_SCOPES,
    DEFAULT_MUSIC_BACKEND,
    DOMAIN,
    MUSIC_BACKEND_MUSIC_ASSISTANT,
    SPOTIFY_SCOPES,
)
from .assist_stt import detect_stt_support
from .spotify_oauth import missing_spotify_scopes, normalize_spotify_scopes
from .tts import detect_tts_support
from .use_cases import MusicAssistantBackend, SpotifyDirectBackend

_REDACT_KEY_PARTS = (
    "token",
    "password",
    "secret",
    "proof",
    "authorization",
    "prompt",
    "history",
    "memory",
    "raw_audio",
    "tts_voice",
)
LEGAL_DIAGNOSTICS = {
    "copyright": "Copyright (c) 2026 Peter van Tol. All rights reserved.",
    "spotify_trademark": "Spotify is a trademark of Spotify AB.",
    "affiliation": (
        "DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB."
    ),
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("REDACTED" if _is_sensitive_key(key) else _redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key).lower()
    return any(part in normalized for part in _REDACT_KEY_PARTS)


def _assist_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    config = {**dict(entry.data), **dict(entry.options)}
    stt = _safe_support_probe(detect_stt_support, hass, config)
    tts = _safe_support_probe(detect_tts_support, hass, config)
    return {
        "configured_pipeline_id": config.get(CONF_ASSIST_PIPELINE_ID) or None,
        "stt": stt,
        "tts": tts,
        "ready": bool(stt.get("configured") and tts.get("configured")),
    }


def _safe_support_probe(probe, hass: HomeAssistant, config: dict[str, Any]) -> dict[str, Any]:
    try:
        return _redact(probe(hass, config))
    except Exception as exc:  # noqa: BLE001
        return {
            "configured": False,
            "error": type(exc).__name__,
            "message": str(exc)[:160],
        }


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    backend = str(
        entry.options.get(CONF_MUSIC_BACKEND)
        or entry.data.get(CONF_MUSIC_BACKEND)
        or DEFAULT_MUSIC_BACKEND
    )
    configured_scopes = entry.data.get(CONF_SPOTIFY_SCOPES)
    missing_scopes = missing_spotify_scopes(configured_scopes)
    capabilities = (
        MusicAssistantBackend.capabilities
        if backend == MUSIC_BACKEND_MUSIC_ASSISTANT
        else SpotifyDirectBackend.capabilities
    )
    spotify_oauth = {
        "configured_scopes": normalize_spotify_scopes(configured_scopes),
        "required_scopes": SPOTIFY_SCOPES,
        "missing_scopes": missing_scopes,
        "reauthorization_required": bool(missing_scopes),
    }
    if backend == MUSIC_BACKEND_MUSIC_ASSISTANT:
        spotify_oauth = {
            "required": False,
            "reauthorization_required": False,
        }
    return {
        "legal": LEGAL_DIAGNOSTICS,
        "music_backend": {
            "selected": backend,
            "capabilities": dict(capabilities.__dict__),
        },
        "assist": _assist_diagnostics(hass, entry),
        "spotify_oauth": spotify_oauth,
        "entry": {
            "title": entry.title,
            "data": _redact(dict(entry.data)),
            "options": _redact(dict(entry.options)),
        },
        "runtime": _redact({
            "last_text": getattr(runtime, "last_text", None),
            "last_stt_text": getattr(runtime, "last_stt_text", None),
            "last_corrected_text": getattr(runtime, "last_corrected_text", None),
            "last_intent": getattr(runtime, "last_intent", None),
            "last_dj_text": getattr(runtime, "last_dj_text", None),
            "last_dj_spoken": getattr(runtime, "last_dj_spoken", None),
            "last_dj_displayed": getattr(runtime, "last_dj_displayed", None),
            "last_dj_response_at": getattr(runtime, "last_dj_response_at", None),
            "last_error": getattr(runtime, "last_error", None),
            "device_status": getattr(runtime, "device_status", {}),
            "ota_in_progress": getattr(runtime, "ota_in_progress", False),
            "ota_last_error": getattr(runtime, "ota_last_error", None),
        }) if runtime else {},
    }
