"""Transport-independent capability declarations for DJ Session Broadcast."""
from __future__ import annotations

from typing import Any

from .const import API_SESSION_BROADCAST
from .paired_live_contract import paired_live_capability


def session_broadcast_transport_capabilities() -> dict[str, Any]:
    """Return the currently implemented Broadcast transport contract.

    This is intentionally declarative: adapters serialize this single source,
    while Runtime and Broadcast behaviour remain independent of discovery.
    """
    return {
        "paired_owner_websocket": paired_live_capability(),
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
        "native_moment_delivery": {
            "schema_version": 1, "projection": "native_delivery",
            "retention": "active_session_only", "executable_actions": [],
        },
        "snapshot_recovery": True,
        "replay": True,
        "cursor": True,
        "flow_delta": False,
        "sequence": False,
    }
