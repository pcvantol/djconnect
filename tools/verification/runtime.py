"""Verification platform runtime version metadata."""

from __future__ import annotations

RUNTIME_NAME = "djconnect-verification-platform"
RUNTIME_VERSION = "1.0.0"
RUNTIME_SCHEMA_VERSION = 1


def runtime_metadata() -> dict[str, str | int]:
    return {
        "name": RUNTIME_NAME,
        "version": RUNTIME_VERSION,
        "schema_version": RUNTIME_SCHEMA_VERSION,
    }
