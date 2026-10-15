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


class ManagedSessionImages:
    """Bounded private Session resources within the existing image owner.

    This cache is RAM-only. Callers own subject/retention admission; delivery
    must additionally authenticate the current owner, never just an asset ID.
    """

    def __init__(self):
        import asyncio

        self.assets = {}
        self.inflight = {}
        self.negative = {}
        self.semaphore = asyncio.Semaphore(2)

    def collect(self):
        import time

        now = time.monotonic()
        self.assets = {k: v for k, v in self.assets.items() if v['deadline'] > now and v['authority']()}
        self.negative = {k: v for k, v in self.negative.items() if v > now}

    def get(self, key):
        self.collect()
        return self.assets.get(key)

    def commit(self, key, asset):
        self.collect()
        total = sum(len(v['body']) for k, v in self.assets.items() if k != key)
        if (key not in self.assets and len(self.assets) >= 64) or total + len(asset['body']) > 32 * 1024 * 1024:
            return False
        self.assets[key] = asset
        return True


def session_images(hass):
    """One RAM registry under the existing shared image-proxy owner."""
    return hass.data.setdefault(DOMAIN, {}).setdefault('session_images', ManagedSessionImages())
