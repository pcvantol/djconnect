"""Recognize retired clients from persisted ownership, never request identity."""

from __future__ import annotations

from typing import Any

from .const import CLIENT_TYPE_WINDOWS, CONF_CLIENT_TYPE, CONF_DEVICE_ID


def is_retired_entry(entry: Any) -> bool:
    """Recognize legacy Windows even when one persisted identity field disagrees.

    Both stored layers matter: an options override must not reclassify an old
    Windows device as Apple. Observed status and request payloads are excluded.
    """
    if entry is None:
        return False
    for source in (getattr(entry, "data", {}), getattr(entry, "options", {})):
        if not isinstance(source, dict) and not hasattr(source, "get"):
            continue
        if str(source.get(CONF_CLIENT_TYPE) or "").strip().lower() == CLIENT_TYPE_WINDOWS:
            return True
        if str(source.get(CONF_DEVICE_ID) or "").strip().lower().startswith("djconnect-windows-"):
            return True
    return False


def is_retired_runtime(runtime: Any) -> bool:
    """Test only the server-owned ConfigEntry identity."""
    return is_retired_entry(getattr(runtime, "entry", None))
