"""Ask DJ response and media helpers."""
from __future__ import annotations

import secrets

from homeassistant.core import HomeAssistant

from ..const import API_IMAGE_PROXY_BASE, DOMAIN

IMAGE_PROXY_KEY = "image_proxy"


def register_image_proxy_url(hass: HomeAssistant, external_url: str) -> str:
    """Register an external image URL and return a Home Assistant proxy URL."""
    url = str(external_url or "").strip()
    if not url or url.startswith(API_IMAGE_PROXY_BASE) or not url.startswith(("http://", "https://")):
        return url
    token = secrets.token_urlsafe(18)
    hass.data.setdefault(DOMAIN, {}).setdefault(IMAGE_PROXY_KEY, {})[token] = url
    return f"{API_IMAGE_PROXY_BASE}/{token}"


def image_proxy_target(hass: HomeAssistant, token: str) -> str | None:
    """Return registered image proxy target URL."""
    return (
        hass.data.get(DOMAIN, {})
        .get(IMAGE_PROXY_KEY, {})
        .get(str(token or "").strip())
    )
