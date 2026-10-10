"""Pure metadata for the paired owner live transport."""

from typing import Any

PAIRED_LIVE_PATH = "/api/djconnect/v1/session/broadcast/paired"
PAIRED_LIVE_VERSION = 1
AUTH_TIMEOUT_SECONDS = 5
LEASE_SECONDS = 300
RECHECK_SECONDS = 1
COMMANDS = (
    "djconnect/session/broadcast/subscribe",
    "djconnect/session/broadcast/recover",
)


def paired_live_capability() -> dict[str, Any]:
    return {
        "available": True,
        "path": PAIRED_LIVE_PATH,
        "version": PAIRED_LIVE_VERSION,
        "auth": "paired_device_first_frame",
        "audience": "active_owner_broadcast",
        "client_types": ["ios", "macos", "watchos"],
        "commands": list(COMMANDS),
        "lease_seconds": LEASE_SECONDS,
        "auth_timeout_seconds": AUTH_TIMEOUT_SECONDS,
        "revocation_check_seconds": RECHECK_SECONDS,
        "ha_credentials_issued": False,
    }
