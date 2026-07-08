from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
try:
    from homeassistant.helpers import entity_registry as er
except ImportError:  # pragma: no cover - older HA/test stubs
    er = None

from . import DEFAULT_TEST_TTS_TEXT, async_speak_dj_test
from .const import (
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_RASPBERRY_PI,
    CLIENT_TYPE_WATCHOS,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    DOMAIN,
)
from .device_info import djconnect_device_info
from .entity_ids import entry_unique_id
from .push import EVENT_ASK_DJ_CONFIRM, async_send_event as async_send_push_event
from .spotify_backend import SpotifyBackendError
from .use_cases import run_music_command

_LOGGER = logging.getLogger(__name__)
APPLE_PUSH_CLIENT_TYPES = {CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS}
REMOVED_BACKEND_BUTTON_KEYS = (
    "next_track",
    "previous_track",
    "play_pause",
    "refresh_device_info",
    "refresh_up_next",
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    _remove_legacy_entities(hass, runtime, "button", REMOVED_BACKEND_BUTTON_KEYS)
    entities = []
    if runtime.client_type() == CLIENT_TYPE_ESP32:
        entities.extend(
            [
                DJConnectTestVoiceButton(runtime, hass),
                DJConnectRebootButton(runtime, hass),
            ]
        )
    if runtime.client_type() == CLIENT_TYPE_RASPBERRY_PI:
        entities.extend(
            [
                DJConnectPiRestartButton(runtime, hass),
                DJConnectPiShutdownButton(runtime, hass),
            ]
        )
    if runtime.client_type() in APPLE_PUSH_CLIENT_TYPES:
        entities.append(DJConnectTestPushButton(runtime, hass))
    async_add_entities(entities)


def _remove_legacy_entities(
    hass: HomeAssistant,
    runtime: Any,
    platform: str,
    keys: tuple[str, ...],
) -> None:
    if er is None:
        return
    registry = er.async_get(hass)
    if registry is None:
        return
    get_entity_id = getattr(registry, "async_get_entity_id", None)
    remove_entity = getattr(registry, "async_remove", None)
    if not callable(get_entity_id) or not callable(remove_entity):
        return
    for key in keys:
        entity_id = get_entity_id(platform, DOMAIN, entry_unique_id(runtime, key))
        if entity_id:
            remove_entity(entity_id)

class DJConnectTestVoiceButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "test_dj_response"
    _attr_unique_id = "djconnect_test_dj_voice"

    def __init__(self, runtime, hass: HomeAssistant) -> None:
        self.runtime = runtime
        self.hass = hass
        self._attr_unique_id = entry_unique_id(runtime, "test_dj_voice")

    @property
    def device_info(self):
        return djconnect_device_info(self.runtime)

    async def async_press(self) -> None:
        await async_speak_dj_test(self.hass, self.runtime, DEFAULT_TEST_TTS_TEXT)
        _LOGGER.debug("DJConnect test button sent DJ response to device")


class DJConnectBaseButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, runtime, hass: HomeAssistant, translation_key: str) -> None:
        self.runtime = runtime
        self.hass = hass
        self._attr_translation_key = translation_key
        self._attr_unique_id = entry_unique_id(runtime, translation_key)

    @property
    def device_info(self):
        return djconnect_device_info(self.runtime)


class DJConnectCommandButton(DJConnectBaseButton):
    def __init__(
        self,
        runtime,
        hass: HomeAssistant,
        command: str,
        translation_key: str,
    ) -> None:
        super().__init__(runtime, hass, translation_key)
        self.command = command

    async def async_press(self) -> None:
        try:
            if self.command in {"next", "previous"}:
                await self.runtime.async_device_command(self.hass, self.command)
            elif self.command == "play_pause":
                playback = await self._current_playback_for_toggle()
                backend_command = "pause" if playback.get("is_playing") else "play"
                await run_music_command(self.hass, self.runtime, backend_command)
            else:
                await self.runtime.async_device_command(self.hass, self.command)
        except SpotifyBackendError as exc:
            self.runtime.update(last_error=str(exc))
            _LOGGER.warning("DJConnect button command unavailable: %s", exc)
            return
        _LOGGER.debug("DJConnect button sent command %s", self.command)

    async def _current_playback_for_toggle(self) -> dict[str, Any]:
        try:
            result = await run_music_command(self.hass, self.runtime, "status")
            playback = result.get("playback") if isinstance(result, dict) else None
            if isinstance(playback, dict):
                return playback
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect button playback status refresh failed: %s", exc)
        return self.runtime.last_playback or {}


class DJConnectRefreshUpNextButton(DJConnectBaseButton):
    def __init__(self, runtime, hass: HomeAssistant) -> None:
        super().__init__(runtime, hass, "refresh_up_next")

    async def async_press(self) -> None:
        try:
            await run_music_command(self.hass, self.runtime, "queue")
        except SpotifyBackendError as exc:
            self.runtime.update(last_error=str(exc))
            _LOGGER.warning("DJConnect up next refresh unavailable: %s", exc)


class DJConnectTestPushButton(DJConnectBaseButton):
    def __init__(self, runtime, hass: HomeAssistant) -> None:
        super().__init__(runtime, hass, "test_push_message")

    async def async_press(self) -> None:
        result = await async_send_push_event(
            self.hass,
            self.runtime,
            user_id=None,
            event_type=EVENT_ASK_DJ_CONFIRM,
            source_device_id=_runtime_device_id(self.runtime),
            client_type=_runtime_client_type(self.runtime),
            explicit_user_request=True,
        )
        if not result.get("sent"):
            reason = (
                result.get("error")
                or result.get("last_push_error")
                or result.get("suppressed")
                or ("disabled" if result.get("disabled") else None)
                or ("relay_error" if result.get("errors") else None)
                or "not_sent"
            )
            update = getattr(self.runtime, "update", None)
            if callable(update):
                update(last_error=f"DJConnect test push was not sent: {reason}")
            _LOGGER.warning("DJConnect test push was not sent: %s", reason)
            return
        _LOGGER.debug("DJConnect test push message sent")


class DJConnectRebootButton(DJConnectBaseButton):
    def __init__(self, runtime, hass: HomeAssistant) -> None:
        super().__init__(runtime, hass, "reboot_device")

    async def async_press(self) -> None:
        await self.runtime.async_device_post(self.hass, "/api/device/reboot")


class DJConnectPiRestartButton(DJConnectBaseButton):
    def __init__(self, runtime, hass: HomeAssistant) -> None:
        super().__init__(runtime, hass, "restart_device")

    async def async_press(self) -> None:
        await self.runtime.async_device_post(self.hass, "/api/device/restart")


class DJConnectPiShutdownButton(DJConnectBaseButton):
    def __init__(self, runtime, hass: HomeAssistant) -> None:
        super().__init__(runtime, hass, "shutdown_device")

    async def async_press(self) -> None:
        await self.runtime.async_device_post(self.hass, "/api/device/shutdown")


def _runtime_client_type(runtime: Any) -> str:
    getter = getattr(runtime, "client_type", None)
    if callable(getter):
        return str(getter() or "").strip().lower()
    status = getattr(runtime, "device_status", {}) or {}
    config = getattr(runtime, "config", {}) or {}
    return str(status.get(CONF_CLIENT_TYPE) or config.get(CONF_CLIENT_TYPE) or "").strip().lower()


def _runtime_device_id(runtime: Any) -> str | None:
    status = getattr(runtime, "device_status", {}) or {}
    config = getattr(runtime, "config", {}) or {}
    device_id = status.get(CONF_DEVICE_ID) or config.get(CONF_DEVICE_ID)
    return str(device_id).strip() if device_id else None
