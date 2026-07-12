"""Verification Runtime version and capability metadata."""

from __future__ import annotations

RUNTIME_NAME = "djconnect-verification-platform"
RUNTIME_PRODUCT = "Verification Runtime"
RUNTIME_VERSION = "1.1.0"
RUNTIME_SCHEMA_VERSION = 1
RUNTIME_REPOSITORY = "pcvantol/djconnect"
RUNTIME_DOCKER_REPOSITORY = "pcvantol/djconnect-verification-platform"
RUNTIME_CAPABILITIES = (
    "planner",
    "execution",
    "evidence",
    "investigator",
    "qualification",
    "reporting",
    "coverage",
)


def runtime_metadata() -> dict[str, str | int]:
    return {
        "name": RUNTIME_NAME,
        "product": RUNTIME_PRODUCT,
        "version": RUNTIME_VERSION,
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "repository": RUNTIME_REPOSITORY,
        "docker_repository": RUNTIME_DOCKER_REPOSITORY,
        "compatibility": "capability-driven",
        "capabilities": list(RUNTIME_CAPABILITIES),
    }
