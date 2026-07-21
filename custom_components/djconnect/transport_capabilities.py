"""Transport-independent capability declarations for DJ Session Broadcast."""
from __future__ import annotations

from typing import Any

from .const import API_SESSION_BROADCAST


def session_broadcast_transport_capabilities() -> dict[str, Any]:
    """Return the currently implemented Broadcast transport contract.

    This is intentionally declarative: adapters serialize this single source,
    while Runtime and Broadcast behaviour remain independent of discovery.
    """
    return {
        "http_snapshot": {
            "available": True,
            "path": API_SESSION_BROADCAST,
        },
        "websocket_subscription": {
            "available": True,
            "command": "djconnect/session/broadcast/subscribe",
        },
        "websocket_recovery": {
            "available": True,
            "command": "djconnect/session/broadcast/recover",
        },
        "snapshot_recovery": True,
        "replay": True,
        "cursor": True,
        "flow_delta": False,
        "sequence": False,
    }
