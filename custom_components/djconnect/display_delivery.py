"""Bounded B transport accounting and prepared display media delivery."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
import time
from typing import Callable

from .display_admission import DisplayAdmissionError
from .display_projection import MAX_FRAME_BYTES
from .forecast_imagery import safe_cdn_url
from .image_proxy import image_proxy_target


MAX_DISPLAY_ARTWORK_BYTES = 256000
DISPLAY_ARTWORK_LIFETIME = 120
MAX_FLOW_ARTWORK = 12
FLOW_ARTWORK_LIFETIME = 30 * 60


class DisplayLiveHub:
    """Runtime-owned transport accounting; transitions still use its sole lock."""
    def __init__(self, manager):
        self.manager = manager
        self.preauth = 0
        self.sources = {}
        self.connections = {}
        self.reserved_bytes = 0
        self.projections = 0
        self.projecting = {}
        self.artwork_reads = {}
        self.peak_reserved_bytes = 0
        self.peak_projections = 0
        self.peak_preauth = 0
        self._observation_revision = 0

    def live_displays(self, profile_id, session_id):
        return tuple(sorted(
            (connection.display.display_id, connection.display.share_id, connection.generation)
            for connection in self.connections.values()
            if connection.display.owner.profile_id == profile_id
            and connection.active.session_id == session_id
            and connection.current()
        ))

    def next_observation_revision(self):
        self._observation_revision = max(
            self._observation_revision + 1, time.monotonic_ns() // 1000,
        )
        return self._observation_revision

    def reserve_projection(self, display_id):
        size = 2 * MAX_FRAME_BYTES
        if (display_id in self.projecting or self.projections >= 8
                or self.reserved_bytes + size > 4 * 1024 * 1024):
            raise DisplayAdmissionError("display_capacity", 429)
        marker = object()
        self.projecting[display_id] = marker
        self.projections += 1
        self.reserved_bytes += size
        self.peak_reserved_bytes = max(self.peak_reserved_bytes, self.reserved_bytes)
        self.peak_projections = max(self.peak_projections, self.projections)
        def release():
            if self.projecting.get(display_id) is marker:
                del self.projecting[display_id]
                self.projections -= 1
                self.reserved_bytes -= size
        return release

    def reserve_artwork(self, display_id):
        """Keep optional media reads out of the live projection allowance."""
        size = MAX_DISPLAY_ARTWORK_BYTES
        if (display_id in self.artwork_reads or len(self.artwork_reads) >= 8
                or self.reserved_bytes + size > 4 * 1024 * 1024):
            raise DisplayAdmissionError("display_capacity", 429)
        marker = object()
        self.artwork_reads[display_id] = marker
        self.reserved_bytes += size
        self.peak_reserved_bytes = max(self.peak_reserved_bytes, self.reserved_bytes)

        def release():
            if self.artwork_reads.get(display_id) is marker:
                del self.artwork_reads[display_id]
                self.reserved_bytes -= size

        return release

    def reserve_preauth(self, source):
        if self.preauth >= 16 or self.sources.get(source, 0) >= 2:
            raise DisplayAdmissionError("display_capacity", 429)
        self.preauth += 1
        self.peak_preauth = max(self.peak_preauth, self.preauth)
        self.sources[source] = self.sources.get(source, 0) + 1

    def release_preauth(self, source):
        self.preauth -= 1
        count = self.sources[source] - 1
        if count:
            self.sources[source] = count
        else:
            del self.sources[source]


def display_live_hub(manager):
    hub = getattr(manager, "_display_live_hub", None)
    if hub is None:
        hub = manager._display_live_hub = DisplayLiveHub(manager)
    return hub


@dataclass(frozen=True, repr=False)
class DisplayArtwork:
    nonce: str
    item_id: str
    source_url: str
    body: bytes
    mime: str
    deadline: float
    expires_at: str
    flow_deadline: float
    flow_expires_at: str
    source_current: Callable[[], bool]
    shares: frozenset[tuple[str, int]]
    playback_current: Callable[[], bool]

    def current(self, active, now):
        playback = active.broadcast.state.playback
        return (now < self.deadline and playback.state in {"playing", "paused"}
                and playback.item_id == self.item_id and playback.source_url == self.source_url
                and self.playback_current())


def qualified_artwork(active, display, state, *, flow_item_id=None):
    """Resolve prepared media within the current display and source authority."""
    if active is None or active.session_id != display.owner.session_id:
        return None
    now = state._clock()
    share = state._shares.get(display.share_id)
    if (share is None or state._displays.get(display.display_id) is not display
            or now >= min(share.deadline, display.lease_deadline)
            or active.broadcast.state.runtime_state != "active"
            or not display.owner.valid() or not share.owner.valid()):
        return None
    if flow_item_id is None:
        asset = getattr(active.broadcast, "display_artwork", None)
        if asset is None or not asset.current(active, now):
            return None
    else:
        asset = getattr(active.broadcast, "display_flow_artwork", {}).get(flow_item_id)
        if (asset is None or now >= asset.flow_deadline or not asset.source_current()
                or (share.share_id, share.generation) not in asset.shares):
            return None
    binding = (state.issuer_epoch, display.display_id, share.share_id,
               str(share.generation), active.session_id, asset.item_id, asset.nonce)
    if flow_item_id is not None:
        binding += ("flow",)
    reference = hashlib.sha256(":".join(binding).encode()).hexdigest()
    return reference, asset


def artwork_descriptor(active, display, state, *, flow_item_id=None):
    found = qualified_artwork(active, display, state, flow_item_id=flow_item_id)
    if found is None:
        return None
    reference, asset = found
    result = {"reference": reference, "item_id": asset.item_id, "expires_at": asset.expires_at}
    if flow_item_id is not None:
        result.update(source_url=asset.source_url, expires_at=asset.flow_expires_at)
    return result


def schedule_artwork(hass, manager, observed, result, source_sample):
    """Start bounded preparation from a normal observation, never a display read."""
    state = manager._display_admission
    active = manager.current_active(observed.owner_profile_id)

    def admitted_shares():
        now = state._clock()
        shares = set()
        for display in state._displays.values():
            share = state._shares.get(display.share_id)
            if (display.owner.session_id == observed.session_id and share is not None
                    and now < min(display.lease_deadline, share.deadline)
                    and display.owner.valid() and share.owner.valid()):
                shares.add((share.share_id, share.generation))
        return shares

    if active is None or active.session_id != observed.session_id:
        return
    shares = admitted_shares()
    if not shares:
        active.broadcast.display_artwork = None
        getattr(active.broadcast, "display_flow_artwork", {}).clear()
        return
    if source_sample is None or not source_sample.current():
        return
    track = getattr(result, "media_identity", "")
    url = getattr(result, "artwork_url", "")
    if not re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", track) or not safe_cdn_url(url):
        return
    item_id = hashlib.sha256(track.encode()).hexdigest()[:24]
    source_url = "https://open.spotify.com/track/" + track.rsplit(":", 1)[-1]
    broadcast = active.broadcast
    recording_serial = observed.forecast_recording_serial
    key = (item_id, url, recording_serial)
    now = state._clock()
    task = observed.display_artwork_task
    if ((task is not None and not task.done())
            or (observed.display_artwork_attempt == key and now < observed.display_artwork_retry)):
        return
    observed.display_artwork_attempt = key
    observed.display_artwork_retry = now + 20

    def still_current():
        current = manager.current_active(observed.owner_profile_id)
        return (current is not None and current.broadcast is broadcast and not observed.unavailable
                and observed.forecast_recording_serial == recording_serial
                and source_sample.current() and broadcast.state.playback.item_id == item_id
                and broadcast.state.playback.source_url == source_url
                and image_proxy_target(hass, broadcast.state.playback.artwork_url.rsplit("/", 1)[-1]) == url
                and broadcast.state.playback.state in {"playing", "paused"})

    existing = getattr(broadcast, "display_artwork", None)
    if (existing is not None and existing.current(active, now)
            and existing.deadline > now + 25 and shares <= existing.shares):
        return
    def historical_source_current():
        # A later playback command changes the current track proof. It does
        # not change the provider/account that supplied the original cover.
        return not observed.unavailable and source_sample.witness.current(historical=True)

    observed.display_artwork_task = hass.async_create_task(
        _prepare_artwork(hass, state, broadcast, item_id, source_url, url, still_current,
                         historical_source_current, lambda: shares & admitted_shares(),
                         source_sample.observed_monotonic))


async def _prepare_artwork(hass, state, broadcast, item_id, source_url, url, current,
                           source_current, admitted_shares, observed_at):
    from aiohttp import ClientTimeout
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from .image_proxy import session_images
    from .session_artwork import _decode_prepared

    deadline = observed_at + DISPLAY_ARTWORK_LIFETIME
    flow_deadline = observed_at + FLOW_ARTWORK_LIFETIME
    try:
        if not current() or not admitted_shares():
            return
        async with asyncio.timeout(10):
            async with async_get_clientsession(hass).get(
                url, allow_redirects=False, timeout=ClientTimeout(total=8)
            ) as response:
                if response.status != 200 or not current():
                    return
                body = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    if len(body) + len(chunk) > MAX_DISPLAY_ARTWORK_BYTES or not current():
                        return
                    body.extend(chunk)
            _, witness = await session_images(hass).decode(_decode_prepared, bytes(body))
            shares = admitted_shares()
            now = state._clock()
            if witness is not None and current() and shares and now < deadline:
                wall = datetime.now(timezone.utc)
                asset = DisplayArtwork(
                    secrets.token_hex(16), item_id, source_url, witness.body, witness.mime, deadline,
                    (wall + timedelta(seconds=deadline-now)).isoformat(), flow_deadline,
                    (wall + timedelta(seconds=flow_deadline-now)).isoformat(),
                    source_current, frozenset(shares), current)
                broadcast.display_artwork = asset
                retained = getattr(broadcast, "display_flow_artwork", {})
                retained = {key: value for key, value in retained.items()
                            if key != item_id and value.flow_deadline > now and value.source_current()}
                retained[item_id] = asset
                broadcast.display_flow_artwork = dict(list(retained.items())[-MAX_FLOW_ARTWORK:])
    except Exception:
        # Optional media failure leaves the authorized track labels available.
        return
