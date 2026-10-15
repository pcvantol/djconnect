"""Client identity helpers shared by config-flow orchestration."""
from __future__ import annotations

from typing import Any
import re

from .const import (
    CLIENT_TYPE_ESP32,
    CLIENT_TYPE_IOS,
    CLIENT_TYPE_MACOS,
    CLIENT_TYPE_RASPBERRY_PI,
    CLIENT_TYPE_WATCHOS,
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
        return [CLIENT_TYPE_IOS, CLIENT_TYPE_MACOS, CLIENT_TYPE_WATCHOS]
    return list(CLIENT_TYPES)


def client_type_uses_local_device_api(client_type: Any) -> bool:
    """Return whether a client type uses the local DJConnect device API."""
    return str(client_type or "").strip() in {
        CLIENT_TYPE_ESP32,
        CLIENT_TYPE_RASPBERRY_PI,
    }


def device_id_matches_client_type(device_id: Any, client_type: Any) -> bool:
    """Match only currently supported canonical IDs, including ESP setup slots."""
    device = str(device_id or "").strip()
    client = str(client_type or "").strip()
    if client == CLIENT_TYPE_ESP32:
        return bool(re.fullmatch(r"djconnect-\d{6}|djconnect-(?:lilygo-t-embed-s3|esp32-s3-box-3|lilygo)-[0-9A-Fa-f]{12}", device))
    if client not in CLIENT_TYPES:
        return False
    prefix = "raspberry-pi" if client == CLIENT_TYPE_RASPBERRY_PI else client
    return bool(re.fullmatch(r"djconnect-" + re.escape(prefix) + r"-[A-Za-z0-9]{12}", device))
