"""One HA-owned technical collector/builder lifecycle, never a publisher."""
from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import timedelta
import time

from .bulletin_builder import BulletinBuilder
from .bulletin_intake import FeedCollector, POLL_SECONDS
from .bulletin_runtime import capture_work


class BulletinService:
    def __init__(self, manager, store, http, *, create_task, subscribe,
                 wall=time.time, monotonic=time.monotonic):
        self.manager, self.http = manager, http
        self.create_task, self.subscribe = create_task, subscribe
        self.wall, self.monotonic = wall, monotonic
        self.collector = FeedCollector(http, monotonic=monotonic)
        self.builder = BulletinBuilder(store, self._generate, wall=wall, monotonic=monotonic)
        self.closed = False
        self._task = None
        self._unsubscribe = None
        self._work = None

    async def start(self):
        await self.builder.initialize()
        if self.closed:
            return
        self._unsubscribe = self.subscribe(self.tick)
        if self.closed:
            self._unsubscribe()
            self._unsubscribe = None
            return
        self.manager._bulletin_service = self
        self.tick()

    def tick(self, *args):
        """HA technical callback: at most one owned cancellable task, no catch-up."""
        if not self.closed and (self._task is None or self._task.done()):
            self._task = self.create_task(self.poll())

    async def _generate(self, prompt, session, guard):
        work = self._work
        if self.closed or work is None or work.session != session:
            raise PermissionError("bulletin_owner_unavailable")
        work.guard()
        guard()
        result = await work.generate(prompt, session, guard)
        guard()
        work.guard()
        return result

    async def poll(self):
        """Collect public metadata; prepare for an original owner, NEVER publish."""
        try:
            items = await self.collector.collect(now=self.wall())
            if self.closed:
                return
            if self._work is not None:
                try:
                    self._work.guard()
                    candidate = self.builder._candidate
                    if candidate is not None and candidate.eligible(session=self._work.session,
                            now=self.wall(), monotonic=self.monotonic()):
                        return
                except PermissionError:
                    self._work = None
                self.builder._candidate = None
                self._work = None
            for owner in tuple(self.manager._active_by_profile):
                if self.closed:
                    return
                try:
                    work = capture_work(self.manager, owner)
                    if work is None:
                        continue
                    self._work = work
                    candidate = await self.builder.prepare(items, session=work.session, guard=work.guard)
                    if candidate is not None:
                        return
                except (PermissionError, ValueError):
                    self._work = None
                self._work = None
        except Exception:  # noqa: BLE001 - technical failure is silence; never log source bodies.
            self.builder._candidate = None
            self._work = None

    def ready(self, owner, session_id):
        candidate, work = self.builder._candidate, self._work
        if (self.closed or self.builder._failed or candidate is None or work is None
                or work.owner != owner or work.session.session_id != session_id):
            return None
        try:
            work.guard()
            if not candidate.eligible(session=work.session, now=self.wall(), monotonic=self.monotonic()):
                return None
        except PermissionError:
            return None
        return self.builder, candidate, work

    async def close(self):
        self.closed = True
        if self.manager._bulletin_service is self:
            self.manager._bulletin_service = None
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        task = self._task
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self.builder._candidate = None
        self._work = None
        await self.http.close()


async def async_start_bulletin_service(hass):
    """Loaded-entry ownership; no additional user setting or network credentials."""
    from .const import DOMAIN
    from .session_runtime import session_runtime_manager
    data = hass.data[DOMAIN]
    if "bulletin_service" in data:
        return
    # Require the real HA background owner; do not create orphan task fallbacks.
    if not callable(getattr(hass, "async_create_background_task", None)):
        return
    from aiohttp import ClientSession, ClientTimeout, DummyCookieJar
    from homeassistant.helpers.event import async_track_time_interval
    from .bulletin_reservations import BulletinReservationStore
    from .persistence.bootstrap import persistence_service
    store = BulletinReservationStore(persistence_service(hass))
    def subscribe(action):
        # Coroutine jobs stay on HA's event loop; an undecorated sync method
        # would otherwise be scheduled as executor work by HassJob.
        async def scheduled(now):
            action(now)
        return async_track_time_interval(hass, scheduled, timedelta(seconds=POLL_SECONDS))
    http = ClientSession(cookie_jar=DummyCookieJar(), trust_env=False,
        timeout=ClientTimeout(total=8), headers={"User-Agent": "DJConnect-Bulletin/1"})
    service = BulletinService(session_runtime_manager(hass),
        store, http,
        create_task=lambda coro: hass.async_create_background_task(coro, "djconnect-bulletin-intake"),
        subscribe=subscribe)
    data["bulletin_service"] = service  # Before first await: parallel entry setup cannot duplicate owners.
    try:
        await service.start()
    except asyncio.CancelledError:
        await service.close()
        raise
    except Exception:  # noqa: BLE001 - quarantine corrupt/unavailable storage; no automatic repair.
        await service.close()


async def async_close_bulletin_service(hass):
    from .const import DOMAIN
    service = hass.data.get(DOMAIN, {}).pop("bulletin_service", None)
    if service is not None:
        await service.close()
