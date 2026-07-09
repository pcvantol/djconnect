"""DJ announcement output routing."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

try:
    from homeassistant.const import ATTR_ENTITY_ID
except ImportError:  # pragma: no cover - lightweight unit-test stubs.
    ATTR_ENTITY_ID = "entity_id"

from .const import (
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_RASPBERRY_PI,
    CONF_CLIENT_TYPE,
    CONF_DJ_ANNOUNCEMENT_OUTPUT,
    CONF_DJ_ANNOUNCEMENT_SPEAKER,
    DJ_ANNOUNCEMENT_BOTH,
    DJ_ANNOUNCEMENT_CLIENT_DEVICE,
    DJ_ANNOUNCEMENT_HA_SPEAKER,
    DJ_ANNOUNCEMENT_TEXT_ONLY,
)
from .dj_response import async_create_dj_audio_url

_LOGGER = logging.getLogger(__name__)


def announcement_speaker_options(hass: Any) -> dict[str, str]:
    """Return media_player entities that can likely play DJ announcement TTS."""
    options: dict[str, str] = {"": "None"}
    states = getattr(hass, "states", None)
    if not states or not hasattr(states, "async_entity_ids"):
        return options
    try:
        entity_ids = list(states.async_entity_ids("media_player"))
    except Exception:  # noqa: BLE001
        return options
    for entity_id in sorted(entity_ids):
        state = states.get(entity_id) if hasattr(states, "get") else None
        if state is None:
            continue
        if str(getattr(state, "state", "") or "").lower() in {"unknown", "unavailable"}:
            continue
        attrs = getattr(state, "attributes", {}) or {}
        if _supports_play_media(attrs):
            options[entity_id] = str(attrs.get("friendly_name") or entity_id)
    return options


def validate_announcement_speaker(hass: Any, entity_id: Any) -> str | None:
    """Return a config-flow field error for invalid announcement speakers."""
    speaker = str(entity_id or "").strip()
    if not speaker:
        return None
    if "." not in speaker:
        return "announcement_speaker_invalid"
    domain, _, object_id = speaker.partition(".")
    if domain != "media_player" or not object_id:
        return "announcement_speaker_invalid"
    states = getattr(hass, "states", None)
    state = states.get(speaker) if states and hasattr(states, "get") else None
    if state is None:
        return "announcement_speaker_not_found"
    if str(getattr(state, "state", "") or "").lower() in {"unknown", "unavailable"}:
        return "announcement_speaker_unavailable"
    if not _supports_play_media(getattr(state, "attributes", {}) or {}):
        return "announcement_speaker_no_play_media"
    return None


def announcement_capabilities(
    runtime: Any,
    *,
    client_type: str | None = None,
) -> dict[str, Any]:
    """Return client-facing DJ announcement capabilities."""
    effective_client_type = str(
        client_type
        or getattr(runtime, "device_status", {}).get(CONF_CLIENT_TYPE)
        or getattr(runtime, "config", {}).get(CONF_CLIENT_TYPE)
        or ""
    )
    speaker = configured_announcement_speaker(runtime)
    speaker_configured = bool(speaker)
    if effective_client_type == CLIENT_TYPE_RASPBERRY_PI:
        supported = (
            [DJ_ANNOUNCEMENT_TEXT_ONLY, DJ_ANNOUNCEMENT_HA_SPEAKER]
            if speaker_configured
            else [DJ_ANNOUNCEMENT_TEXT_ONLY]
        )
    elif effective_client_type == CLIENT_TYPE_ESP32:
        supported = []
    else:
        supported = [
            DJ_ANNOUNCEMENT_CLIENT_DEVICE,
            DJ_ANNOUNCEMENT_TEXT_ONLY,
        ]
        if speaker_configured:
            supported[1:1] = [DJ_ANNOUNCEMENT_BOTH, DJ_ANNOUNCEMENT_HA_SPEAKER]
    locked = [
        mode
        for mode in (
            DJ_ANNOUNCEMENT_CLIENT_DEVICE,
            DJ_ANNOUNCEMENT_BOTH,
            DJ_ANNOUNCEMENT_HA_SPEAKER,
            DJ_ANNOUNCEMENT_TEXT_ONLY,
        )
        if mode not in supported
    ]
    return {
        "speaker_configured": speaker_configured,
        "speaker_entity_id": speaker or None,
        "supported_outputs": supported,
        "locked_outputs": locked,
        "default_output": default_announcement_output(runtime, client_type=effective_client_type),
        "output": normalize_announcement_output(
            getattr(runtime, "config", {}).get(CONF_DJ_ANNOUNCEMENT_OUTPUT),
            runtime,
            client_type=effective_client_type,
        ),
    }


def configured_announcement_speaker(runtime: Any) -> str:
    """Return the configured HA media_player announcement speaker."""
    return str(getattr(runtime, "config", {}).get(CONF_DJ_ANNOUNCEMENT_SPEAKER) or "").strip()


def default_announcement_output(runtime: Any, *, client_type: str | None = None) -> str:
    """Return the default output for a runtime/client type."""
    effective_client_type = str(client_type or getattr(runtime, "config", {}).get(CONF_CLIENT_TYPE) or "")
    speaker_configured = bool(configured_announcement_speaker(runtime))
    if effective_client_type == CLIENT_TYPE_RASPBERRY_PI:
        return DJ_ANNOUNCEMENT_HA_SPEAKER if speaker_configured else DJ_ANNOUNCEMENT_TEXT_ONLY
    if effective_client_type == CLIENT_TYPE_ESP32:
        return DJ_ANNOUNCEMENT_CLIENT_DEVICE
    return DJ_ANNOUNCEMENT_BOTH if speaker_configured else DJ_ANNOUNCEMENT_CLIENT_DEVICE


def normalize_announcement_output(
    value: Any,
    runtime: Any,
    *,
    client_type: str | None = None,
) -> str:
    """Normalize output to a supported mode for the client/runtime."""
    requested = str(value or "").strip().lower()
    effective_client_type = str(client_type or getattr(runtime, "config", {}).get(CONF_CLIENT_TYPE) or "")
    speaker_configured = bool(configured_announcement_speaker(runtime))
    if effective_client_type == CLIENT_TYPE_RASPBERRY_PI:
        supported = (
            {DJ_ANNOUNCEMENT_TEXT_ONLY, DJ_ANNOUNCEMENT_HA_SPEAKER}
            if speaker_configured
            else {DJ_ANNOUNCEMENT_TEXT_ONLY}
        )
    elif effective_client_type == CLIENT_TYPE_ESP32:
        supported = {DJ_ANNOUNCEMENT_CLIENT_DEVICE}
    else:
        supported = {DJ_ANNOUNCEMENT_CLIENT_DEVICE, DJ_ANNOUNCEMENT_TEXT_ONLY}
        if speaker_configured:
            supported.update({DJ_ANNOUNCEMENT_BOTH, DJ_ANNOUNCEMENT_HA_SPEAKER})
    if requested in supported:
        return requested
    return default_announcement_output(runtime, client_type=client_type)


async def async_apply_announcement_output(
    hass: HomeAssistant,
    runtime: Any,
    response: dict[str, Any],
    *,
    payload: dict[str, Any],
    generate_audio: bool,
    audio_url_factory: Any | None = None,
) -> dict[str, Any]:
    """Attach and/or deliver DJ announcement audio for app-client Ask DJ responses."""
    text = str(response.get("dj_text") or response.get("text") or "").strip()
    client_type = str(payload.get(CONF_CLIENT_TYPE) or getattr(runtime, "config", {}).get(CONF_CLIENT_TYPE) or "")
    output = normalize_announcement_output(
        payload.get(CONF_DJ_ANNOUNCEMENT_OUTPUT)
        or getattr(runtime, "config", {}).get(CONF_DJ_ANNOUNCEMENT_OUTPUT),
        runtime,
        client_type=client_type,
    )
    speaker = configured_announcement_speaker(runtime)
    announcement = {
        "output": output,
        "delivery": output,
        "audio_response_effective": "never" if output == DJ_ANNOUNCEMENT_TEXT_ONLY else "unavailable",
        "audio_url": None,
        "audio_type": None,
        "target": _target_payload(hass, speaker) if output in {DJ_ANNOUNCEMENT_BOTH, DJ_ANNOUNCEMENT_HA_SPEAKER} else None,
        "warnings": [],
    }
    if not text or not generate_audio or output == DJ_ANNOUNCEMENT_TEXT_ONLY:
        response["announcement"] = announcement
        _sync_assistant_announcement(response, announcement)
        return response
    if callable(audio_url_factory):
        audio_result = await audio_url_factory(hass, runtime, text)
        audio_url = (
            audio_result.get("audio_url_value")
            if isinstance(audio_result, dict)
            else audio_result
        )
    else:
        audio_url = await async_create_dj_audio_url(hass, runtime, text)
    if audio_url:
        announcement["audio_url"] = audio_url if output in {DJ_ANNOUNCEMENT_CLIENT_DEVICE, DJ_ANNOUNCEMENT_BOTH} else None
        announcement["audio_type"] = _audio_type_from_url(audio_url)
        announcement["audio_response_effective"] = (
            "server_only" if output == DJ_ANNOUNCEMENT_HA_SPEAKER else "always"
        )
    if output in {DJ_ANNOUNCEMENT_BOTH, DJ_ANNOUNCEMENT_HA_SPEAKER}:
        if audio_url and speaker:
            try:
                await hass.services.async_call(
                    "media_player",
                    "play_media",
                    {
                        ATTR_ENTITY_ID: speaker,
                        "media_content_id": audio_url,
                        "media_content_type": "music",
                    },
                    blocking=False,
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("DJConnect HA speaker announcement failed: %s", exc)
                announcement["warnings"].append("ha_speaker_playback_failed")
        else:
            announcement["warnings"].append("ha_speaker_audio_unavailable")
    if announcement["audio_url"]:
        response["audio_url"] = announcement["audio_url"]
        if announcement["audio_type"]:
            response["audio_type"] = announcement["audio_type"]
    else:
        response.pop("audio_url", None)
        response.pop("audio_type", None)
    response["announcement"] = announcement
    _sync_assistant_announcement(response, announcement)
    return response


def _supports_play_media(attrs: dict[str, Any]) -> bool:
    features = attrs.get("supported_features")
    try:
        return bool(int(features or 0) & 512)
    except (TypeError, ValueError):
        return False


def _target_payload(hass: HomeAssistant, entity_id: str) -> dict[str, Any] | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id) if getattr(hass, "states", None) else None
    attrs = getattr(state, "attributes", {}) or {}
    return {
        "kind": "ha_media_player",
        "entity_id": entity_id,
        "name": attrs.get("friendly_name") or entity_id,
    }


def _audio_type_from_url(audio_url: str | None) -> str | None:
    if not audio_url:
        return None
    lowered = str(audio_url).lower().split("?", 1)[0]
    if lowered.endswith(".wav"):
        return "wav"
    if lowered.endswith(".mp3"):
        return "mp3"
    return None


def _sync_assistant_announcement(response: dict[str, Any], announcement: dict[str, Any]) -> None:
    assistant = response.get("assistant_message")
    if isinstance(assistant, dict):
        assistant["announcement"] = dict(announcement)
        if announcement.get("audio_url"):
            assistant["audio_url"] = announcement["audio_url"]
            if announcement.get("audio_type"):
                assistant["audio_type"] = announcement["audio_type"]
        else:
            assistant.pop("audio_url", None)
            assistant.pop("audio_type", None)
