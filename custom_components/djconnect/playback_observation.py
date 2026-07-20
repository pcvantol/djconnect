"""Active-session Live Playback Observation Stage 1 orchestration."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Awaitable, Callable

try:
    from homeassistant.helpers.event import async_track_time_interval
except ImportError:  # pragma: no cover - Home Assistant supplies this at runtime
    async_track_time_interval = None

from .const import DOMAIN, MUSIC_BACKEND_SPOTIFY_DIRECT
from .session_runtime import DJSessionRuntime, session_runtime_manager
from .spotify_backend import SpotifyBackend, SpotifyBackendError

_LOGGER = logging.getLogger(__name__)
SPOTIFY_OBSERVATION_INTERVAL = timedelta(seconds=15)

InsightProvider = Callable[[], Awaitable[dict[str, Any]]]


@dataclass
class _SpotifyObservationSession:
    """Ephemeral scheduler state for one active Spotify Session."""

    integration_runtime: Any
    owner_profile_id: str
    session_id: str
    insight_provider: InsightProvider
    remove_listener: Callable[[], None] | None = None
    poll_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    unavailable: bool = False


class PlaybackObservationManager:
    """Coordinates active-session Stage 1 observation without provider leakage."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass
        self._spotify_sessions: dict[str, _SpotifyObservationSession] = {}

    async def async_start_spotify(
        self,
        *,
        integration_runtime: Any,
        session: DJSessionRuntime,
        insight_provider: InsightProvider,
    ) -> None:
        """Attach one bounded Spotify observer after an eligible Session starts."""
        if session.music_backend != MUSIC_BACKEND_SPOTIFY_DIRECT:
            return
        await self.async_stop(session.owner_profile_id)
        observed = _SpotifyObservationSession(
            integration_runtime=integration_runtime,
            owner_profile_id=session.owner_profile_id,
            session_id=session.session_id,
            insight_provider=insight_provider,
        )
        self._spotify_sessions[session.owner_profile_id] = observed

        async def poll(_now: Any = None) -> None:
            await self._async_poll_spotify(observed)

        # The first successful state is a Runtime baseline, never a second
        # Session-start contribution. The Runtime owns this identity-only rule.
        await poll()
        if self._spotify_sessions.get(session.owner_profile_id) is not observed:
            return
        if async_track_time_interval is not None:
            observed.remove_listener = async_track_time_interval(
                self._hass, poll, SPOTIFY_OBSERVATION_INTERVAL
            )

    async def async_stop(self, owner_profile_id: str, session_id: str = "") -> None:
        """Stop future polling and make any late result inert."""
        observed = self._spotify_sessions.get(owner_profile_id)
        if observed is None or (session_id and observed.session_id != session_id):
            return
        self._spotify_sessions.pop(owner_profile_id, None)
        if observed.remove_listener is not None:
            observed.remove_listener()
            observed.remove_listener = None

    async def async_stop_runtime(self, integration_runtime: Any) -> None:
        """Release observers owned by an unloading integration Runtime."""
        for observed in tuple(self._spotify_sessions.values()):
            if observed.integration_runtime is integration_runtime:
                await self.async_stop(observed.owner_profile_id, observed.session_id)

    async def _async_poll_spotify(self, observed: _SpotifyObservationSession) -> None:
        """Poll one observer without overlap or provider details in Runtime."""
        if self._spotify_sessions.get(observed.owner_profile_id) is not observed:
            return
        if observed.poll_lock.locked():
            return
        async with observed.poll_lock:
            if self._spotify_sessions.get(observed.owner_profile_id) is not observed:
                return
            active = await session_runtime_manager(self._hass).async_get_active(
                observed.owner_profile_id
            )
            if active is None or active.session_id != observed.session_id:
                await self.async_stop(observed.owner_profile_id, observed.session_id)
                return
            try:
                result = await SpotifyBackend(
                    self._hass, observed.integration_runtime
                ).async_observe_current_playback()
            except SpotifyBackendError as exc:
                if not observed.unavailable:
                    _LOGGER.debug(
                        "DJConnect Spotify playback observation unavailable: %s",
                        exc.__class__.__name__,
                    )
                observed.unavailable = True
                return
            except Exception as exc:  # noqa: BLE001
                if not observed.unavailable:
                    _LOGGER.debug(
                        "DJConnect Spotify playback observation failed: %s",
                        exc.__class__.__name__,
                    )
                observed.unavailable = True
                return
            observed.unavailable = False
            if self._spotify_sessions.get(observed.owner_profile_id) is not observed:
                return
            if not result.is_playing or not result.media_identity:
                return
            await session_runtime_manager(self._hass).async_process_track_started(
                owner_profile_id=observed.owner_profile_id,
                session_id=observed.session_id,
                insight_provider=observed.insight_provider,
                media_identity=result.media_identity,
            )


def playback_observation_manager(hass: Any) -> PlaybackObservationManager:
    """Return the integration-wide ephemeral observation coordinator."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get("playback_observation_manager")
    if manager is None:
        manager = PlaybackObservationManager(hass)
        domain_data["playback_observation_manager"] = manager
    return manager
