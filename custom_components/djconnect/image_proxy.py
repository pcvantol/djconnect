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
        self.history_barriers = {}
        self.history_overflow = 0
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
        if self.hass is not None:
            service = self.hass.data.get(DOMAIN, {}).get("persistence_service")
            if getattr(service, "session_image_owner", None) is self:
                service.session_image_owner = None
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
        self.history_barriers.clear()
        self.history_overflow = 0

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

    @staticmethod
    def _history_matches(key, source, delivery_scope, scope):
        target = dict(key[2])
        if 'entry_id' not in target or (scope.get('owner') is not None and key[0] != scope['owner']):
            return False
        ids = scope.get('identifiers')
        if ids is not None and target['entry_id'] not in ids:
            return False
        provider = scope.get('provider_entry_id')
        if provider is not None and source.get('provider_entry_id') != provider:
            return False
        if scope.get('expired_before') is not None:
            retained = getattr(delivery_scope, 'history_retained_until', None)
            header = getattr(delivery_scope, 'history_session_created_at', None)
            cutoff = scope.get('session_cutoff')
            if (retained is not None and retained > scope['expired_before']
                    and (header is None or cutoff is None or header > cutoff)):
                return False
        return True

    def history_blocked(self, key, source, delivery_scope):
        if 'entry_id' not in dict(key[2]):
            return False
        return self.history_overflow > 0 or any(
            self._history_matches(key, source, delivery_scope, scope)
            for scope in self.history_barriers.values())

    def invalidate_history(self, **scope):
        """Bounded synchronous link from the existing destructive history owner."""
        for key in set(self.assets) | set(self.inflight) | set(self.work_guards):
            asset = self.assets.get(key)
            guard = self.work_guards.get(key)
            source = (asset.get('expected_source', {}) if asset is not None else
                      {'provider_entry_id': getattr(guard[1], 'provider_entry_id', None)} if guard else {})
            delivery_scope = (asset.get('delivery_scope') if asset is not None else
                              getattr(guard[1], 'delivery_scope', None) if guard else None)
            if not self._history_matches(key, source, delivery_scope, scope):
                continue
            if guard is not None:
                guard[1]()
            self.evict(key, 'source_withdrawn')

    def begin_history_change(self, **scope):
        token = object()
        if len(self.history_barriers) >= 8:
            self.history_overflow += 1
            self.invalidate_history()
            return None
        if scope.get('identifiers') is not None:
            scope['identifiers'] = frozenset(scope['identifiers'])
        self.history_barriers[token] = scope
        self.invalidate_history(**scope)
        return token

    def end_history_change(self, token, **scope):
        if self.closed:
            return
        self.invalidate_history(**scope)
        if token is None:
            self.history_overflow = max(0, self.history_overflow - 1)
        else:
            self.history_barriers.pop(token, None)

    def end_session(self, owner, session_id):
        for key, (_, invalidate) in list(self.work_guards.items()):
            if key[:2] == (owner, session_id):
                invalidate()
        for key, asset in list(self.assets.items()):
            if key[:2] == (owner, session_id) and not asset.get('historical'):
                self.evict(key, 'source_withdrawn')

    def withdraw_content(self, owner, *, entries=frozenset(), moments=frozenset()):
        """Withdraw exact target grants; never purge shared provider images."""
        for key in set(self.assets) | set(self.inflight) | set(self.work_guards):
            if key[0] != owner:
                continue
            target = dict(key[2])
            if ((key[1], target.get('entry_id')) not in entries
                    and (key[1], target.get('moment_id')) not in moments):
                continue
            guard = self.work_guards.get(key)
            if guard is not None:
                guard[1]()
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
        if self.closed or not asset['authority']():
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
    service = owner.get('persistence_service')
    if service is not None:
        service.session_image_owner = owner['session_images']
    return owner['session_images']
