"""Client identity helpers shared by config-flow orchestration."""
from __future__ import annotations

from typing import Any

from .const import (
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_RASPBERRY_PI,
    CLIENT_TYPE_WATCHOS,
    CLIENT_TYPE_WINDOWS,
    CLIENT_TYPES,
    SETUP_METHOD_PAIR_APP,
    SETUP_METHOD_PAIR_LOCAL_DEVICE,
)


def default_pair_client_type(setup_method: Any) -> str:
    """Return the default client type for a setup method."""
    if str(setup_method or "") == SETUP_METHOD_PAIR_LOCAL_DEVICE:
        return CLIENT_TYPE_ESP32
    return CLIENT_TYPE_IOS


def pair_client_type_options(setup_method: Any) -> list[str]:
    """Return allowed client types for a setup method."""
    if str(setup_method or "") == SETUP_METHOD_PAIR_LOCAL_DEVICE:
        return [CLIENT_TYPE_ESP32, CLIENT_TYPE_RASPBERRY_PI]
    if str(setup_method or "") == SETUP_METHOD_PAIR_APP:
        return [CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS, CLIENT_TYPE_WINDOWS]
    return list(CLIENT_TYPES)


def client_type_uses_local_device_api(client_type: Any) -> bool:
    """Return whether a client type uses the local DJConnect device API."""
    return str(client_type or "").strip() in {
        CLIENT_TYPE_ESP32,
        CLIENT_TYPE_RASPBERRY_PI,
    }
