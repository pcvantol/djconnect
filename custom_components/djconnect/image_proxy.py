"""Shared Home Assistant image-proxy registration for renderer-safe media."""
from __future__ import annotations

import secrets
from typing import Any

from .const import API_IMAGE_PROXY_BASE, DOMAIN

IMAGE_PROXY_KEY = "image_proxy"


def register_image_proxy_url(hass: Any, external_url: str) -> str:
    """Register an external image URL once and return its HA proxy URL."""
    url = str(external_url or "").strip()
    if not url or url.startswith(API_IMAGE_PROXY_BASE) or not url.startswith(("http://", "https://")):
        return url
    targets = hass.data.setdefault(DOMAIN, {}).setdefault(IMAGE_PROXY_KEY, {})
    for token, target in targets.items():
        if target == url:
            return f"{API_IMAGE_PROXY_BASE}/{token}"
    token = secrets.token_urlsafe(18)
    targets[token] = url
    return f"{API_IMAGE_PROXY_BASE}/{token}"


def image_proxy_target(hass: Any, token: str) -> str | None:
    """Return the external target registered for an HA proxy token."""
    return (
        hass.data.get(DOMAIN, {})
        .get(IMAGE_PROXY_KEY, {})
        .get(str(token or "").strip())
    )
