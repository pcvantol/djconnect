"""Pairing defaults and validation helpers for DJConnect config flow."""
from __future__ import annotations

import re
from typing import Any

from .const import DEFAULT_DEVICE_NAME

PAIR_CODE_PATTERN = re.compile(r"^\d{6}$")


def clean(value: Any, default: Any = "") -> Any:
    """Normalize empty form values."""
    if value is None:
        return default
    if isinstance(value, str) and value.strip() == "":
        return default
    return value


def default_local_url(pair_code: str | None) -> str:
    """Do not derive local URLs from pairing codes."""
    return ""


def valid_pair_code(pair_code: str) -> bool:
    """Accept only the displayed 6-digit pairing code."""
    return bool(PAIR_CODE_PATTERN.fullmatch(str(pair_code or "").strip()))


def device_name_for_client_type(
    client_type: Any,
    base_name: Any = DEFAULT_DEVICE_NAME,
    *,
    suffixes: dict[str, str],
) -> str:
    """Return the suggested HA device name with a client-type suffix."""
    name = str(base_name or DEFAULT_DEVICE_NAME).strip() or DEFAULT_DEVICE_NAME
    suffix = suffixes.get(str(client_type or "").strip())
    if not suffix:
        return name
    normalized_name = " ".join(name.lower().split())
    normalized_suffix = suffix.lower()
    if normalized_name.endswith(f" {normalized_suffix}") or normalized_name.endswith(
        f" ({normalized_suffix})"
    ):
        return name
    return f"{name} {suffix}"
