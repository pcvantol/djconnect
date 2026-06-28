"""Discovery selection helpers for DJConnect config flow."""
from __future__ import annotations

from typing import Any

from .const import (
    CONF_CLIENT_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_LOCAL_URL,
    CONF_PAIR_CODE,
    DEFAULT_CLIENT_TYPE,
    DEFAULT_DEVICE_NAME,
    CLIENT_TYPES,
)
from .discovery import DiscoveredClient


def discovered_client_key(client: DiscoveredClient) -> str:
    """Return the stable form key for a discovered client."""
    return client.device_id or client.local_url


def discovered_client_options(clients: list[DiscoveredClient]) -> dict[str, str]:
    """Return mDNS discovery choices for the pairing form."""
    return {discovered_client_key(client): client.label for client in clients}


def selected_discovered_client(
    clients: list[DiscoveredClient],
    selected_key: str,
) -> DiscoveredClient | None:
    """Return the selected mDNS client, if the user picked one."""
    if not selected_key:
        return None
    for client in clients:
        if discovered_client_key(client) == selected_key:
            return client
    return None


def discovered_client_defaults(client: DiscoveredClient) -> dict[str, Any]:
    """Return authoritative pairing defaults from a discovered client."""
    client_type = (
        client.client_type
        if client.client_type in CLIENT_TYPES
        else DEFAULT_CLIENT_TYPE
    )
    return {
        CONF_DEVICE_ID: client.device_id,
        CONF_DEVICE_NAME: str(client.device_name or DEFAULT_DEVICE_NAME).strip()
        or DEFAULT_DEVICE_NAME,
        CONF_CLIENT_TYPE: client_type,
        CONF_LOCAL_URL: client.local_url,
        CONF_PAIR_CODE: client.pair_code,
    }
