"""Shared Home Assistant device info helpers for DJConnect entities."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CLIENT_TYPE_CONVERSATION_AGENT,
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_RASPBERRY_PI,
    CLIENT_TYPE_WATCHOS,
    CLIENT_TYPE_WINDOWS,
    CONF_CLIENT_TYPE,
    CONF_DEVICE_NAME,
    DEFAULT_CLIENT_TYPE,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
)

DEFAULT_DEVICE_NAMES = {
    CLIENT_TYPE_ESP32: "DJConnect ESP32",
    CLIENT_TYPE_RASPBERRY_PI: "DJConnect Pi",
    CLIENT_TYPE_IOS: "DJConnect iPhone",
    CLIENT_TYPE_MACOS: "DJConnect macOS",
    CLIENT_TYPE_WATCHOS: "DJConnect Watch",
    CLIENT_TYPE_WINDOWS: "DJConnect Windows",
    CLIENT_TYPE_CONVERSATION_AGENT: "DJConnect DJ",
}


def djconnect_device_info(runtime: Any) -> DeviceInfo:
    """Return the shared Home Assistant device info for a runtime."""
    return DeviceInfo(
        identifiers={(DOMAIN, runtime.entry.entry_id)},
        name=djconnect_device_name(runtime),
        manufacturer="DJConnect",
        model="DJConnect device",
    )


def djconnect_device_name(runtime: Any) -> str:
    """Resolve the display name used for the single HA device."""
    status = getattr(runtime, "device_status", {}) or {}
    config = getattr(runtime, "config", {}) or {}
    client_type = _runtime_client_type(runtime, status, config)
    for source in (status, config):
        if isinstance(source, dict):
            name = str(source.get(CONF_DEVICE_NAME) or "").strip()
            if name:
                if name == DEFAULT_DEVICE_NAME:
                    return DEFAULT_DEVICE_NAMES.get(client_type, DEFAULT_DEVICE_NAME)
                return name
    return DEFAULT_DEVICE_NAMES.get(client_type, DEFAULT_DEVICE_NAME)


def _runtime_client_type(runtime: Any, status: dict[str, Any], config: dict[str, Any]) -> str:
    getter = getattr(runtime, "client_type", None)
    if callable(getter):
        client_type = str(getter() or "").strip()
        if client_type:
            return client_type
    return str(
        status.get(CONF_CLIENT_TYPE)
        or config.get(CONF_CLIENT_TYPE)
        or DEFAULT_CLIENT_TYPE
    )
