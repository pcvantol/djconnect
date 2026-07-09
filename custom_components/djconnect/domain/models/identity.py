"""Identity helpers for core domain models."""

from __future__ import annotations

from typing import Any


def clean_identifier(value: Any) -> str:
    """Return a normalized non-empty identifier or an empty string."""
    return str(value or "").strip()
