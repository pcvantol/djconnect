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

    def __init__(self, hass=None):
        import asyncio

        self.assets = {}
        self.inflight = {}
        self.negative = {}
        self.semaphore = asyncio.Semaphore(2)
        self.decode_slots = (hass.data.setdefault(DOMAIN, {}).setdefault(
            "session_image_decode_slots", asyncio.Semaphore(2)) if hass is not None
            else asyncio.Semaphore(2))
        self.hass = hass
        self.closed = False
        self.timers = {}
        self.states = {}
        self.work_guards = {}
        self._unsubscribe = None
        if hass is not None:
            from homeassistant.const import EVENT_HOMEASSISTANT_STOP
            self._unsubscribe = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._on_stop)

    async def _on_stop(self, _event):
        # HA removes one-shot listeners before invoking them.
        self._unsubscribe = None
        self.close()

    async def decode(self, callback, body):
        """Keep the shared decode permit until the actual executor job finishes.

        Cancelling an awaiting request cannot stop a running decoder thread.
        The permit survives request timeout and registry unload/reload.
        """
        import asyncio

        await self.decode_slots.acquire()
        if self.closed:
            self.decode_slots.release()
            raise PermissionError('source_withdrawn')
        try:
            future = self.hass.async_add_executor_job(callback, body)
        except BaseException:
            self.decode_slots.release()
            raise
        future.add_done_callback(lambda _: self.decode_slots.release())
        return await asyncio.shield(future)

    def close(self):
        self.closed = True
        unsubscribe, self._unsubscribe = self._unsubscribe, None
        if unsubscribe is not None:
            unsubscribe()
        for handle in self.timers.values():
            handle.cancel()
        for task in self.inflight.values():
            task.cancel()
        self.timers.clear()
        self.assets.clear()
        self.inflight.clear()
        self.negative.clear()
        self.states.clear()
        for _, invalidate in self.work_guards.values():
            invalidate()
        self.work_guards.clear()

    def evict(self, key, reason):
        self.assets.pop(key, None)
        timer = self.timers.pop(key, None)
        if timer:
            timer.cancel()
        self.record_state(key, reason)

    def record_state(self, key, reason):
        import time

        if len(self.states) < 64 or key in self.states:
            self.states[key] = (time.monotonic() + 60, reason)

    def expire(self, key, asset_id):
        asset = self.assets.get(key)
        if asset is not None and asset.get('asset_id') == asset_id:
            self.evict(key, 'expired')

    def end_session(self, owner, session_id):
        for key, (_, invalidate) in list(self.work_guards.items()):
            if key[:2] == (owner, session_id):
                invalidate()
        for key, asset in list(self.assets.items()):
            if key[:2] == (owner, session_id) and not asset.get('historical'):
                self.evict(key, 'source_withdrawn')

    def collect(self):
        import time

        now = time.monotonic()
        for key, (authority, invalidate) in list(self.work_guards.items()):
            if not authority():
                invalidate()
                self.evict(key, 'source_withdrawn')
        for key, asset in list(self.assets.items()):
            if asset['deadline'] <= now:
                self.evict(key, 'expired')
            elif not asset['authority']():
                self.evict(key, 'source_withdrawn')
        self.states = {k: v for k, v in self.states.items() if v[0] > now}
        self.negative = {k: v for k, v in self.negative.items() if v > now}

    def get(self, key):
        self.collect()
        return self.assets.get(key)

    def commit(self, key, asset):
        self.collect()
        if self.closed:
            return False
        total = sum(len(v['body']) for k, v in self.assets.items() if k != key)
        if len(asset['body']) > 2 * 1024 * 1024:
            return False
        if (key not in self.assets and len(self.assets) >= 64) or total + len(asset['body']) > 32 * 1024 * 1024:
            return False
        old = self.timers.pop(key, None)
        if old:
            old.cancel()
        self.assets[key] = asset
        self.states.pop(key, None)
        if self.hass is not None:
            import time
            self.timers[key] = self.hass.loop.call_later(
                max(0, asset['deadline'] - time.monotonic()), self.expire, key, asset.get('asset_id'))
        return True


def session_images(hass):
    """One RAM registry under the existing shared image-proxy owner."""
    owner = hass.data.setdefault(DOMAIN, {})
    if 'session_images' not in owner:
        owner['session_images'] = ManagedSessionImages(hass)
    return owner['session_images']
