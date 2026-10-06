"""Active-session Live Playback Observation Stage 1 orchestration."""
from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Awaitable, Callable

try:
    from homeassistant.helpers.event import async_track_time_interval
except ImportError:  # pragma: no cover - Home Assistant supplies this at runtime
    async_track_time_interval = None

from .const import DOMAIN, MUSIC_BACKEND_SPOTIFY_DIRECT
from .image_proxy import register_image_proxy_url
from .session_runtime import DJSessionRuntime, session_runtime_manager
from .spotify_backend import SpotifyBackend, SpotifyBackendError

_LOGGER = logging.getLogger(__name__)
SPOTIFY_OBSERVATION_INTERVAL = timedelta(seconds=15)
PLAYBACK_PROGRESS_INTERVAL = timedelta(seconds=1)

InsightProvider = Callable[[], Awaitable[dict[str, Any]]]
InsightProviderFactory = Callable[[Any, DJSessionRuntime], InsightProvider]


@dataclass(frozen=True)
class SpotifyObservationResumeKey:
    """Identity needed to resume one observer after its Runtime reloads."""

    owner_profile_id: str
    session_id: str


@dataclass
class _SpotifyObservationSession:
    """Ephemeral scheduler state for one active Spotify Session."""

    integration_runtime: Any
    owner_profile_id: str
    session_id: str
    insight_provider: InsightProvider
    remove_listener: Callable[[], None] | None = None
    remove_progress_listener: Callable[[], None] | None = None
    poll_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    enrichment_task: asyncio.Task[Any] | None = None
    enrichment_media_identity: str = ""
    unavailable: bool = False


class PlaybackObservationManager:
    """Coordinates active-session Stage 1 observation without provider leakage."""

    def __init__(self, hass: Any) -> None:
        self._hass = hass
        self._spotify_sessions: dict[str, _SpotifyObservationSession] = {}
        self._reloading_entry_ids: set[str] = set()
        self._pending_reload_sessions: dict[
            str, dict[str, SpotifyObservationResumeKey]
        ] = {}

    async def async_start_spotify(
        self,
        *,
        integration_runtime: Any,
        session: DJSessionRuntime,
        insight_provider: InsightProvider | None = None,
        insight_provider_factory: InsightProviderFactory | None = None,
    ) -> None:
        """Attach one bounded Spotify observer after an eligible Session starts."""
        if session.music_backend != MUSIC_BACKEND_SPOTIFY_DIRECT:
            return
        entry_id = self._runtime_entry_id(integration_runtime)
        if entry_id and entry_id in self._reloading_entry_ids:
            self._pending_reload_sessions.setdefault(entry_id, {})[
                session.owner_profile_id
            ] = SpotifyObservationResumeKey(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
            )
            return
        if entry_id:
            current_runtime = self._hass.data.get(DOMAIN, {}).get(entry_id)
            if current_runtime is not None and current_runtime is not integration_runtime:
                integration_runtime = current_runtime
        if insight_provider_factory is not None:
            insight_provider = insight_provider_factory(integration_runtime, session)
        if insight_provider is None:
            raise ValueError("Spotify playback observation requires an insight provider")
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

        async def advance_progress(_now: Any = None) -> None:
            if self._spotify_sessions.get(observed.owner_profile_id) is not observed:
                return
            await session_runtime_manager(self._hass).async_advance_playback_progress(
                owner_profile_id=observed.owner_profile_id,
                session_id=observed.session_id,
            )

        if async_track_time_interval is not None:
            observed.remove_listener = async_track_time_interval(
                self._hass, poll, SPOTIFY_OBSERVATION_INTERVAL
            )
            observed.remove_progress_listener = async_track_time_interval(
                self._hass, advance_progress, PLAYBACK_PROGRESS_INTERVAL
            )
        # Register recurring observation before the initial poll. Track Insight
        # can take longer than one observation interval and must never prevent
        # a newer Spotify projection from reaching the active Runtime.
        await poll()

    async def async_stop(self, owner_profile_id: str, session_id: str = "") -> None:
        """Stop future polling and make any late result inert."""
        observed = self._spotify_sessions.get(owner_profile_id)
        if observed is None or (session_id and observed.session_id != session_id):
            return
        self._spotify_sessions.pop(owner_profile_id, None)
        await session_runtime_manager(self._hass).async_revoke_receiver_end_grants(
            owner_profile_id=owner_profile_id, session_id=observed.session_id
        )
        await session_runtime_manager(self._hass).async_invalidate_intra_track_opportunity(
            owner_profile_id=owner_profile_id, session_id=observed.session_id
        )
        if observed.remove_listener is not None:
            observed.remove_listener()
            observed.remove_listener = None
        if observed.remove_progress_listener is not None:
            observed.remove_progress_listener()
            observed.remove_progress_listener = None
        current_task = asyncio.current_task()
        if observed.enrichment_task is not None and observed.enrichment_task is not current_task:
            if not observed.enrichment_task.done():
                observed.enrichment_task.cancel()
            with suppress(asyncio.CancelledError):
                await observed.enrichment_task
        observed.enrichment_task = None
        observed.enrichment_media_identity = ""

    async def async_stop_runtime(self, integration_runtime: Any) -> None:
        """Release observers owned by an unloading integration Runtime."""
        for observed in tuple(self._spotify_sessions.values()):
            if observed.integration_runtime is integration_runtime:
                await self.async_stop(observed.owner_profile_id, observed.session_id)

    def resume_keys_for_runtime(
        self, integration_runtime: Any
    ) -> tuple[SpotifyObservationResumeKey, ...]:
        """Capture only active observer identities before a Runtime reload."""
        return tuple(
            SpotifyObservationResumeKey(
                owner_profile_id=observed.owner_profile_id,
                session_id=observed.session_id,
            )
            for observed in self._spotify_sessions.values()
            if observed.integration_runtime is integration_runtime
        )

    def begin_runtime_reload(
        self, integration_runtime: Any
    ) -> tuple[SpotifyObservationResumeKey, ...]:
        """Quiesce new observer starts and capture the current Runtime set."""
        entry_id = self._runtime_entry_id(integration_runtime)
        if entry_id:
            self._reloading_entry_ids.add(entry_id)
        return self.resume_keys_for_runtime(integration_runtime)

    def finish_runtime_reload(
        self,
        integration_runtime: Any,
        resume_keys: tuple[SpotifyObservationResumeKey, ...],
    ) -> tuple[SpotifyObservationResumeKey, ...]:
        """Include Sessions started during reload and reopen observer starts."""
        entry_id = self._runtime_entry_id(integration_runtime)
        pending = self._pending_reload_sessions.pop(entry_id, {}) if entry_id else {}
        if entry_id:
            self._reloading_entry_ids.discard(entry_id)
        combined = {
            (resume_key.owner_profile_id, resume_key.session_id): resume_key
            for resume_key in (*resume_keys, *pending.values())
        }
        return tuple(combined.values())

    def abort_runtime_reload(
        self,
        integration_runtime: Any,
        resume_keys: tuple[SpotifyObservationResumeKey, ...] = (),
    ) -> tuple[SpotifyObservationResumeKey, ...]:
        """Release reload bookkeeping and return Sessions needing rollback."""
        entry_id = self._runtime_entry_id(integration_runtime)
        if not entry_id:
            return resume_keys
        self._reloading_entry_ids.discard(entry_id)
        pending = self._pending_reload_sessions.pop(entry_id, {})
        combined = {
            (resume_key.owner_profile_id, resume_key.session_id): resume_key
            for resume_key in (*resume_keys, *pending.values())
        }
        return tuple(combined.values())

    async def async_resume_spotify(
        self,
        *,
        integration_runtime: Any,
        resume_keys: tuple[SpotifyObservationResumeKey, ...],
        insight_provider_factory: InsightProviderFactory,
    ) -> None:
        """Resume eligible Spotify observers against a replacement Runtime."""
        runtime_manager = session_runtime_manager(self._hass)
        for resume_key in resume_keys:
            active = await runtime_manager.async_get_active(
                resume_key.owner_profile_id
            )
            if (
                active is None
                or active.session_id != resume_key.session_id
                or active.music_backend != MUSIC_BACKEND_SPOTIFY_DIRECT
            ):
                continue
            observed = self._spotify_sessions.get(active.owner_profile_id)
            if (
                observed is not None
                and observed.integration_runtime is integration_runtime
                and observed.session_id == active.session_id
            ):
                continue
            await self.async_start_spotify(
                integration_runtime=integration_runtime,
                session=active,
                insight_provider_factory=insight_provider_factory,
            )

    @staticmethod
    def _runtime_entry_id(integration_runtime: Any) -> str:
        """Return the stable config-entry identity for one Runtime."""
        return str(
            getattr(getattr(integration_runtime, "entry", None), "entry_id", "") or ""
        ).strip()

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
            previous_media_identity = active.last_accepted_media_identity
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
            await session_runtime_manager(self._hass).async_update_playback_projection(
                owner_profile_id=observed.owner_profile_id,
                session_id=observed.session_id,
                state=getattr(result, "state", "playing" if result.is_playing else "idle"),
                media_identity=getattr(result, "media_identity", ""),
                title=getattr(result, "title", ""),
                artist=getattr(result, "artist", ""),
                album=getattr(result, "album", ""),
                artwork_url=register_image_proxy_url(
                    self._hass, getattr(result, "artwork_url", "")
                ),
                target_name=getattr(result, "target_name", ""),
                duration_ms=getattr(result, "duration_ms", None),
                position_ms=getattr(result, "position_ms", None),
            )
            # Optional queue lookup must not delay or invalidate current playback.
            next_item = {}
            if result.is_playing and result.media_identity:
                try:
                    next_item = await asyncio.wait_for(SpotifyBackend(self._hass, observed.integration_runtime).async_observe_next_item(result.media_identity), timeout=3)
                except Exception:  # Best-effort queue absence is not playback failure.
                    next_item = {}
                if next_item:
                    next_item["artwork_url"] = register_image_proxy_url(self._hass, next_item.get("artwork_url", ""))
            if self._spotify_sessions.get(observed.owner_profile_id) is not observed:
                return
            await session_runtime_manager(self._hass).async_update_next_item_projection(
                owner_profile_id=observed.owner_profile_id, session_id=observed.session_id,
                media_identity=result.media_identity, target_name=getattr(result, "target_name", ""), up_next=next_item,
            )
        if not result.is_playing or not result.media_identity:
            previous = observed.enrichment_task
            if previous is not None and previous is not asyncio.current_task() and not previous.done():
                previous.cancel()
                with suppress(asyncio.CancelledError):
                    await previous
            observed.enrichment_task = None
            observed.enrichment_media_identity = ""
            return

        if (
            previous_media_identity == result.media_identity
            and (observed.enrichment_task is None or observed.enrichment_task.done())
        ):
            await session_runtime_manager(self._hass).async_maybe_publish_intra_track_moment(
                owner_profile_id=observed.owner_profile_id,
                session_id=observed.session_id,
                media_identity=result.media_identity,
            )
            return

        current_task = asyncio.current_task()
        previous = observed.enrichment_task
        if previous is not None and not previous.done():
            if observed.enrichment_media_identity == result.media_identity:
                return
            if previous is not current_task:
                previous.cancel()
                with suppress(asyncio.CancelledError):
                    await previous
                if self._spotify_sessions.get(observed.owner_profile_id) is not observed:
                    return
        observed.enrichment_task = current_task
        observed.enrichment_media_identity = result.media_identity
        try:
            async def qualified_insight() -> dict[str, Any]:
                from .session_facts import session_facts_resolver, catalog_facts
                catalog = getattr(result, "catalog", {})
                async def facts() -> tuple[Any, ...]:
                    try:
                        return await session_facts_resolver(self._hass).resolve(catalog)
                    except Exception:  # Provider absence never creates invented facts.
                        return tuple(catalog_facts(catalog))
                evidence = await facts()
                if evidence:
                    return {"_qualified_facts": evidence}
                return {**await observed.insight_provider(), "_qualified_facts": ()}

            await session_runtime_manager(self._hass).async_process_track_started(
                owner_profile_id=observed.owner_profile_id,
                session_id=observed.session_id,
                insight_provider=qualified_insight,
                media_identity=result.media_identity,
                require_current_playback=True,
                allow_initial_facts=bool(getattr(result, "catalog", {})),
            )
        except asyncio.CancelledError:
            await session_runtime_manager(self._hass).async_restore_track_started_media(
                owner_profile_id=observed.owner_profile_id,
                session_id=observed.session_id,
                media_identity=result.media_identity,
                previous_media_identity=previous_media_identity,
            )
            return
        finally:
            if observed.enrichment_task is current_task:
                observed.enrichment_task = None
                observed.enrichment_media_identity = ""


def playback_observation_manager(hass: Any) -> PlaybackObservationManager:
    """Return the integration-wide ephemeral observation coordinator."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get("playback_observation_manager")
    if manager is None:
        manager = PlaybackObservationManager(hass)
        domain_data["playback_observation_manager"] = manager
    return manager
