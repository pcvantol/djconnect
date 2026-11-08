"""Prepare and release current album bytes for separately admitted displays."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
from typing import Callable

from .forecast_imagery import safe_cdn_url
from .image_proxy import image_proxy_target

MAX_BYTES = 256000
LIFETIME = 120


@dataclass(frozen=True, repr=False)
class DisplayArtwork:
    nonce: str
    item_id: str
    source_url: str
    body: bytes
    mime: str
    deadline: float
    expires_at: str
    source_current: Callable[[], bool]

    def current(self, active, now):
        playback = active.broadcast.state.playback
        return (now < self.deadline and playback.state in {"playing", "paused"}
                and playback.item_id == self.item_id and playback.source_url == self.source_url
                and self.source_current())


def qualified(active, display, state):
    """Return the exact display-purpose reference and live authority, if any."""
    if active is None or active.session_id != display.owner.session_id:
        return None
    now = state._clock()
    share = state._shares.get(display.share_id)
    asset = getattr(active.broadcast, "display_artwork", None)
    if (asset is None or share is None or state._displays.get(display.display_id) is not display
            or now >= min(share.deadline, display.lease_deadline)
            or active.broadcast.state.runtime_state != "active"
            or not display.owner.valid() or not share.owner.valid() or not asset.current(active, now)):
        return None
    binding = (state.issuer_epoch, display.display_id, share.share_id,
               str(share.generation), active.session_id, asset.item_id, asset.nonce)
    reference = hashlib.sha256(":".join(binding).encode()).hexdigest()
    return reference, asset


def descriptor(active, display, state):
    found = qualified(active, display, state)
    if found is None:
        return None
    reference, asset = found
    return {"reference": reference, "item_id": asset.item_id,
            "expires_at": asset.expires_at}


def schedule(hass, manager, observed, result, source_sample):
    """Start bounded preparation from a normal observation, never a display read."""
    state = manager._display_admission
    active = manager.current_active(observed.owner_profile_id)

    def has_viewer():
        now = state._clock()
        for display in state._displays.values():
            share = state._shares.get(display.share_id)
            if (display.owner.session_id == observed.session_id and share is not None
                    and now < min(display.lease_deadline, share.deadline)
                    and display.owner.valid() and share.owner.valid()):
                return True
        return False

    if active is None or active.session_id != observed.session_id:
        return
    if not has_viewer():
        active.broadcast.display_artwork = None
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
    if existing is not None and existing.current(active, now) and existing.deadline > now + 25:
        return
    observed.display_artwork_task = hass.async_create_task(
        _prepare(hass, state, broadcast, item_id, source_url, url, still_current, has_viewer,
                 source_sample.observed_monotonic + LIFETIME))


async def _prepare(hass, state, broadcast, item_id, source_url, url, current, has_viewer, deadline):
    from aiohttp import ClientTimeout
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from .image_proxy import session_images
    from .session_artwork import _decode_prepared

    try:
        if not current() or not has_viewer():
            return
        async with asyncio.timeout(10):
            async with async_get_clientsession(hass).get(
                url, allow_redirects=False, timeout=ClientTimeout(total=8)
            ) as response:
                if response.status != 200 or not current():
                    return
                body = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    if len(body) + len(chunk) > MAX_BYTES or not current():
                        return
                    body.extend(chunk)
            _, witness = await session_images(hass).decode(_decode_prepared, bytes(body))
            if witness is not None and current() and has_viewer() and state._clock() < deadline:
                broadcast.display_artwork = DisplayArtwork(
                    secrets.token_hex(16), item_id, source_url, witness.body, witness.mime, deadline,
                    (datetime.now(timezone.utc) + timedelta(seconds=deadline-state._clock())).isoformat(),
                    current)
    except Exception:
        # Optional media failure leaves the authorized track labels available.
        return
