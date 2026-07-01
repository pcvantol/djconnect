from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
try:
    from homeassistant.helpers import entity_registry as er
except ImportError:  # pragma: no cover - older HA/test stubs
    er = None

from .const import CLIENT_TYPE_ESP32, DOMAIN
from .entity_ids import entry_unique_id
from .use_cases import run_music_command

_LOGGER = logging.getLogger(__name__)
REMOVED_BACKEND_SWITCH_KEYS = ("shuffle",)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    _remove_legacy_entities(hass, runtime, "switch", REMOVED_BACKEND_SWITCH_KEYS)
    entities: list[SwitchEntity] = []
    if _runtime_client_type(runtime) == CLIENT_TYPE_ESP32:
        entities.append(DJConnectWakeWordSwitch(runtime, hass))
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


class DJConnectShuffleSwitch(SwitchEntity):
    """Home Assistant switch for backend playback shuffle."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "shuffle"
    _attr_unique_id = "djconnect_shuffle"

    def __init__(self, runtime: Any, hass: HomeAssistant) -> None:
        self.runtime = runtime
        self.hass = hass
        self._last_is_on: bool | None = None
        self._attr_unique_id = entry_unique_id(runtime, "shuffle")
        runtime.listeners.append(self._handle_runtime_update)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.runtime.entry.entry_id)},
            name="DJConnect",
            manufacturer="DJConnect",
            model="DJConnect device",
        )

    @property
    def is_on(self) -> bool | None:
        value: bool | None = None
        playback = _playback_mapping(self.runtime)
        if "shuffle" in playback:
            value = _as_bool(playback.get("shuffle"))
        else:
            status_playback = self.runtime.device_status.get("playback")
            if isinstance(status_playback, dict) and "shuffle" in status_playback:
                value = _as_bool(status_playback.get("shuffle"))
            elif "shuffle" in self.runtime.device_status:
                value = _as_bool(self.runtime.device_status.get("shuffle"))
        if value is not None:
            self._last_is_on = value
            return value
        return self._last_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_shuffle(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_shuffle(False)

    async def _set_shuffle(self, enabled: bool) -> None:
        await run_music_command(self.hass, self.runtime, "set_shuffle", enabled)
        self.runtime.device_status["shuffle"] = enabled
        self.runtime.update()
        await self._refresh_device_display()

    async def async_update(self) -> None:
        try:
            await run_music_command(self.hass, self.runtime, "status")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect shuffle refresh failed: %s", exc)

    async def _refresh_device_display(self) -> None:
        try:
            await self.runtime.async_device_command(self.hass, "status")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("DJConnect device display refresh failed: %s", exc)

    @callback
    def _handle_runtime_update(self) -> None:
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._handle_runtime_update in self.runtime.listeners:
            self.runtime.listeners.remove(self._handle_runtime_update)


class DJConnectWakeWordSwitch(SwitchEntity):
    """Home Assistant switch for ESP wake word detection."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "wake_word"

    def __init__(self, runtime: Any, hass: HomeAssistant) -> None:
        self.runtime = runtime
        self.hass = hass
        self._attr_unique_id = entry_unique_id(runtime, "wake_word")
        runtime.listeners.append(self._handle_runtime_update)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.runtime.entry.entry_id)},
            name="DJConnect",
            manufacturer="DJConnect",
            model="DJConnect device",
        )

    @property
    def is_on(self) -> bool | None:
        return _wake_word_enabled(self.runtime.device_status)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_wake_word(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_wake_word(False)

    async def _set_wake_word(self, enabled: bool) -> None:
        await self.runtime.async_device_command(
            self.hass,
            "wake_word",
            value=enabled,
        )
        self.runtime.device_status["wake_word_enabled"] = enabled
        self.runtime.device_status["wake_word"] = enabled
        self.runtime.update()

    @callback
    def _handle_runtime_update(self) -> None:
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._handle_runtime_update in self.runtime.listeners:
            self.runtime.listeners.remove(self._handle_runtime_update)


def _wake_word_enabled(status: dict[str, Any]) -> bool | None:
    settings = status.get("settings")
    if isinstance(settings, dict):
        for key in ("wake_word_enabled", "wake_word"):
            if settings.get(key) is not None:
                return _as_bool(settings[key])
    for key in ("wake_word_enabled", "wake_word"):
        if status.get(key) is not None:
            return _as_bool(status[key])
    return False


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return bool(value)


def _playback_mapping(runtime: Any) -> dict[str, Any]:
    playback = getattr(runtime, "last_playback", None)
    if isinstance(playback, dict) and playback:
        return playback
    status = getattr(runtime, "device_status", {}) or {}
    playback = status.get("playback")
    if isinstance(playback, dict):
        return playback
    return {}


def _runtime_client_type(runtime: Any) -> str:
    getter = getattr(runtime, "client_type", None)
    if callable(getter):
        return str(getter() or CLIENT_TYPE_ESP32)
    status = getattr(runtime, "device_status", {}) or {}
    config = getattr(runtime, "config", {}) or {}
    return str(status.get("client_type") or config.get("client_type") or CLIENT_TYPE_ESP32)
