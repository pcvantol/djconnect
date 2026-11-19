"""Actual HA source-status sampling; only remote Spotify/CDN are fixtures.

Sample identities are private source DATA, never native presentation/widget IDs.
"""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import verify_session_forecast_http as harness
import session_forecast_runtime_acceptance as forecast_lab


class OriginalStatusLab(forecast_lab.ForecastLab):
    def __init__(self, hass, manager, clock, runtime):
        # Use the actual shipping persistence-backed manager factory. The old
        # Forecast harness manually constructs a manager without optional stores.
        from custom_components.djconnect.session_runtime import session_runtime_manager
        assert hass.data["djconnect"].pop("session_runtime_manager") is manager
        manager = session_runtime_manager(hass)
        manager._monotonic_source = clock.monotonic  # Existing explicit lab clock.
        super().__init__(hass, manager, clock, runtime)

    async def qualify(self, client, identity, headers):
        from custom_components.djconnect.ask_dj.dialogue import current_turn
        from custom_components.djconnect.surface_registration import retire_runtime
        self.owner = {"client": client, "identity": identity, "headers": headers}
        cases = []
        await self.start()
        before = int(time.time() * 1000)
        await self.step(1)
        active = self.manager.current_active("profile-a")
        sample = getattr(active.broadcast, "original_status_sample", None)
        assert sample is not None, "Actual accepted backend observation has no original status sample"
        from custom_components.djconnect import surface_status_samples as status
        assert before <= sample.observed_ms <= int(time.time() * 1000)
        assert sample.state == "playing" and not sample.ended
        cases.append("actual_backend_observer_and_shipping_manager_factory_record_original_sample")
        await self.step(1, playing=False)
        paused = active.broadcast.original_status_sample
        assert paused.state == "paused" and paused.ordinal > sample.ordinal
        self.raw = {}
        observed = self.observer._spotify_sessions["profile-a"]
        await self.observer._async_poll_spotify(observed)
        assert active.broadcast.original_status_sample.state == "unknown"
        cases.append("actual_provider_paused_and_empty_idle_maps_to_unknown_not_playing")

        async def fresh():
            await self.start()
            await self.step(1)
            return self.manager.current_active("profile-a"), self.observer._spotify_sessions["profile-a"]

        async def hold_manager(observed):
            entered, release = asyncio.Event(), asyncio.Event()
            original = self.manager.async_update_playback_projection
            captured = []
            async def blocked(**kwargs):
                await self.manager._lock.acquire()
                task = asyncio.create_task(original(**kwargs))
                captured.append(kwargs["original_status"])
                entered.set()
                try:
                    await release.wait()
                finally:
                    self.manager._lock.release()
                return await task
            patcher = patch.object(self.manager, "async_update_playback_projection", blocked)
            patcher.start()
            task = asyncio.create_task(self.observer._async_poll_spotify(observed))
            await asyncio.wait_for(entered.wait(), 5)
            return release, task, captured[0], patcher

        active, observed = await fresh()
        release, task, original_sample, patcher = await hold_manager(observed)
        try:
            await asyncio.sleep(0.03)
            assert original_sample.observed_ms < int(time.time() * 1000)
            release.set()
            await asyncio.wait_for(task, 5)
        finally:
            release.set()
            patcher.stop()
        assert active.broadcast.original_status_sample.observed_ms == original_sample.observed_ms
        cases.append("actual_manager_lock_delay_does_not_move_original_observation_time")

        active, observed = await fresh()
        release, task, candidate, patcher = await hold_manager(observed)
        service = self.manager._status_samples.persistence
        async def row(scope):
            return await service.async_in_transaction(lambda tx: tx.fetchone(
                "SELECT sample_id,ordinal,observed_ms,playback_state,ended FROM djconnect_status_samples WHERE scope_hash=?", (scope,)))
        prior = await row(candidate.witness.scope)
        try:
            from custom_components.djconnect.domain.storage import STORE_KEY
            self.hass.data["djconnect"][STORE_KEY].authority_revision += 1
            release.set()
            await asyncio.wait_for(task, 5)
        finally:
            release.set()
            patcher.stop()
        assert active.broadcast.original_status_sample is None
        assert await row(candidate.witness.scope) == prior
        cases.append("original_source_revision_change_while_lock_held_suppresses_SQL_and_RAM")

        active, observed = await fresh()
        original_apply = self.manager.async_update_playback_projection
        captured_settings = []
        async def change_settings_before_apply(**kwargs):
            candidate = kwargs["original_status"]
            captured_settings.append(candidate)
            await self.presence("occasional")  # Actual paired owner HTTP/settings commit.
            return await original_apply(**kwargs)
        with patch.object(self.manager, "async_update_playback_projection", change_settings_before_apply):
            await self.observer._async_poll_spotify(observed)
        assert captured_settings and not captured_settings[0].current()
        assert active.broadcast.original_status_sample is None
        cases.append("actual_paired_settings_commit_between_sample_and_apply_fences_original_source")

        active, observed = await fresh()
        from custom_components.djconnect.spotify_backend import SpotifyBackend
        async def readback():
            backend = SpotifyBackend(self.hass, self.integration)
            with patch.object(backend, "_enrich_current_track_favorite_status", AsyncMock()), \
                 patch.object(backend, "_enrich_playback_artist_genres", AsyncMock()), \
                 patch.object(backend, "_record_playback_in_music_dna", AsyncMock()):
                return await backend.playback_state()

        async def no_guard():
            pass
        token = current_turn.set(SimpleNamespace(scope="profile:profile-a", effect_started=True, guard=no_guard))
        entered, release = asyncio.Event(), asyncio.Event()
        backend = SpotifyBackend(self.hass, self.integration)
        stamp = (int(time.time() * 1000), time.monotonic())
        async def held_enrichment(_playback):
            entered.set()
            await release.wait()
        try:
            with patch.object(backend, "_enrich_current_track_favorite_status", held_enrichment), \
                 patch.object(backend, "_enrich_playback_artist_genres", AsyncMock()), \
                 patch.object(backend, "_record_playback_in_music_dna", AsyncMock()), \
                 patch.object(status, "_stamp", return_value=stamp):
                task = asyncio.create_task(backend.playback_state())
                await asyncio.wait_for(entered.wait(), 5)
                await asyncio.sleep(0.03)
                release.set()
                original_readback = await asyncio.wait_for(task, 5)
            assert original_readback.original_status.observed_ms == stamp[0]
            assert original_readback.original_status.observed_monotonic == stamp[1]
            assert "original_status" not in original_readback
            assert type(self.integration.last_playback) is dict
            await self.observer.async_accept_command_readback(self.integration, original_readback)
        finally:
            release.set()
            current_turn.reset(token)
        assert active.broadcast.original_status_sample.observed_ms == stamp[0]
        cases.append("actual_backend_GET_original_time_precedes_held_enrichment_and_is_not_JSON_data")

        active, observed = await fresh()
        revision = observed.command_revision
        entered, release = asyncio.Event(), asyncio.Event()
        calls = 0
        async def turn_guard():
            nonlocal calls
            calls += 1
            if calls == 1:
                entered.set()
                await release.wait()
        token = current_turn.set(SimpleNamespace(scope="profile:profile-a", effect_started=True, guard=turn_guard))
        captured_stamp = (int(time.time() * 1000), time.monotonic())
        try:
            with patch.object(status, "_stamp", return_value=captured_stamp):
                self.raw["is_playing"] = False
                playback = await readback()
                task = asyncio.create_task(self.observer.async_accept_command_readback(self.integration, playback))
                await asyncio.wait_for(entered.wait(), 5)
                await asyncio.sleep(0.03)
                release.set()
                result = await asyncio.wait_for(task, 5)
        finally:
            release.set()
            current_turn.reset(token)
        assert result is not None and observed.command_revision == revision + 1
        assert active.broadcast.original_status_sample.observed_ms == captured_stamp[0]
        assert active.broadcast.original_status_sample.state == "paused"
        cases.append("guarded_readback_original_GET_time_survives_guard_await_and_own_N_to_N1")

        active, observed = await fresh()
        prior = active.broadcast.original_status_sample
        entered, release = asyncio.Event(), asyncio.Event()
        guards = 0
        async def competing_guard():
            nonlocal guards
            guards += 1
            if guards == 1:
                entered.set()
                await release.wait()
        token = current_turn.set(SimpleNamespace(scope="profile:profile-a", effect_started=True, guard=competing_guard))
        try:
            playback = await readback()
            task = asyncio.create_task(self.observer.async_accept_command_readback(self.integration, playback))
            await asyncio.wait_for(entered.wait(), 5)
            observed.command_revision += 1  # Explicit competing command fence, no device effect.
            release.set()
            await asyncio.wait_for(task, 5)
        finally:
            release.set()
            current_turn.reset(token)
        assert active.broadcast.original_status_sample.sample_id == prior.sample_id
        assert not active.broadcast._original_status_capture.current()
        cases.append("competing_command_during_readback_guard_cannot_publish_new_status_sample")

        active, observed = await fresh()
        prior = active.broadcast.original_status_sample
        token = current_turn.set(SimpleNamespace(scope="profile:profile-a", effect_started=True, guard=no_guard))
        try:
            await self.observer.async_accept_command_readback(self.integration,
                {"uri": "spotify:track:" + "1" * 22, "is_playing": False})
        finally:
            current_turn.reset(token)
        assert active.broadcast.original_status_sample.sample_id == prior.sample_id
        cases.append("plain_dictionary_without_original_GET_witness_cannot_mint_status_time")

        active, observed = await fresh()
        pending_scope = active.broadcast.original_status_sample.scope
        before_row = await row(pending_scope)
        active.broadcast.original_status_sample = None
        active.broadcast._original_status_capture = None
        from custom_components.djconnect.spotify_backend import SpotifyBackend
        original_read = SpotifyBackend.async_observe_current_playback
        entered, release = asyncio.Event(), asyncio.Event()
        async def pending_read(backend):
            result = await original_read(backend)
            entered.set()
            await release.wait()
            return result
        with patch.object(SpotifyBackend, "async_observe_current_playback", pending_read):
            task = asyncio.create_task(self.observer._async_poll_spotify(observed))
            await asyncio.wait_for(entered.wait(), 5)
            retire_runtime(self.integration)
            release.set()
            await asyncio.wait_for(task, 5)
        assert active.broadcast.original_status_sample is None
        assert await row(pending_scope) == before_row
        cases.append("runtime_retirement_revokes_pending_source_witness_without_previous_RAM_cache")

        active, observed = await fresh()
        captured_stamp = (int(time.time() * 1000), time.monotonic())
        await self.manager._lock.acquire()
        try:
            with patch.object(status, "_stamp", return_value=captured_stamp):
                task = asyncio.create_task(self.manager.async_end(owner_profile_id="profile-a", session_id=active.session_id))
                await asyncio.sleep(0.03)
                assert not task.done()
                self.manager._lock.release()
                await asyncio.wait_for(task, 5)
        finally:
            if self.manager._lock.locked():
                self.manager._lock.release()
        assert active.broadcast.original_status_sample.ended
        assert active.broadcast.original_status_sample.observed_ms == captured_stamp[0]
        cases.append("original_end_time_precedes_actual_manager_lock_wait")

        active, observed = await fresh()
        assert active.broadcast._original_status_capture is not None
        retire_runtime(self.integration)
        assert active.broadcast.original_status_sample is None
        assert active.broadcast._original_status_capture is None
        cases.append("synchronous_runtime_retirement_drops_status_and_retired_source_snapshots")

        active, observed = await fresh()
        original_backend = __import__("custom_components.djconnect.spotify_backend", fromlist=["SpotifyBackend"]).SpotifyBackend
        original_read = original_backend.async_observe_current_playback
        entered, release = asyncio.Event(), asyncio.Event()
        async def late_read(backend):
            result = await original_read(backend)
            entered.set()
            await release.wait()
            return result
        original_scope = active.broadcast.original_status_sample.scope
        capture = active.broadcast._original_status_capture
        assert capture is not None and capture.current(), {
            "pre_end_current": bool(capture and capture.current()),
            "revoked": bool(capture and capture.witness._revoked[0]),
            "storage_revision_equal": bool(capture and capture.witness.storage.authority_revision == capture.witness.revision),
            "base_source_current": bool(capture and capture.witness.allowed()),
        }
        # No visual listener: the new status end fence must still be unconditional.
        self.manager._visual_withdrawals.pop(("profile-a", active.session_id), None)
        with patch.object(original_backend, "async_observe_current_playback", late_read):
            task = asyncio.create_task(self.observer._async_poll_spotify(observed))
            await asyncio.wait_for(entered.wait(), 5)
            ended = await self.manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
            assert ended is not None
            assert active.broadcast.original_status_sample is not None, {
                "end_marker_type": type(active.broadcast._status_end_pending).__name__,
                "old_source_revoked": capture.witness._revoked[0],
                "storage_revision_equal": capture.witness.storage.authority_revision == capture.witness.revision,
                "base_source_current": capture.witness.allowed(),
            }
            assert active.broadcast.original_status_sample.ended
            assert active.broadcast.original_status_sample.state is None
            assert active.broadcast._original_status_capture is None
            assert not isinstance(active.broadcast._status_end_pending, status.OriginalSample)
            terminal = await row(original_scope)
            release.set()
            await asyncio.wait_for(task, 5)
        assert (await row(original_scope)) == terminal and terminal[-1] == 1
        assert self.manager.current_active("profile-a") is None
        cases.append("actual_end_without_visual_listener_commits_terminal_source_and_rejects_late_provider")

        active, observed = await fresh()
        from custom_components.djconnect.persistence import PersistenceError
        async def failed_end(*args, **kwargs):
            raise PersistenceError("synthetic_end_transition_failure")
        with patch.object(self.manager._persistent_sessions, "async_transition", failed_end):
            try:
                await self.manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
            except PersistenceError:
                pass
            else:
                raise AssertionError("Expected explicit failed end transition")
        assert active.broadcast.original_status_sample is None
        assert active.broadcast._original_status_capture is None
        assert not isinstance(active.broadcast._status_end_pending, status.OriginalSample), "Failed end retained original credential/source witness"
        assert active.broadcast._status_end_pending is not None  # No rearm after unknown/failure.
        cases.append("failed_end_transition_keeps_negative_fence_but_drops_original_source_references")

        active, observed = await fresh()
        original_end = self.manager._persistent_sessions.async_transition
        async def lost_end_ack(*args, **kwargs):
            await original_end(*args, **kwargs)
            raise PersistenceError("synthetic_lost_end_ACK_after_actual_commit")
        with patch.object(self.manager._persistent_sessions, "async_transition", lost_end_ack):
            try:
                await self.manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
            except PersistenceError:
                pass
            else:
                raise AssertionError("Expected explicit lost end ACK")
        actual = await service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT lifecycle_status FROM djconnect_persistent_sessions WHERE session_id=?", (active.session_id,)))
        from custom_components.djconnect.persistence.sessions import ENDED
        assert actual == (ENDED,)
        assert active.broadcast.original_status_sample is None
        assert active.broadcast._original_status_capture is None
        assert not isinstance(active.broadcast._status_end_pending, status.OriginalSample)
        assert active.broadcast._status_end_pending is not None
        cases.append("lost_real_end_commit_ACK_preserves_SQL_truth_and_negative_no_reference_fence")
        return {"state": "PASS", "original_source_sample": True,
                "cases": cases, "sample_ended_source_DATA_not_native_lifecycle": True,
                "command_execution_boundary": "EXPLICIT_SYNTHETIC_TURN_GUARD_NO_ACTUAL_EFFECT",
                "source_DATA_only": True, "native_provider_installed": "NOT_RUN",
                "external_boundary": "Synthetic Spotify/CDN; actual HA/backend/observer/manager/SQLite"}


if __name__ == "__main__":
    forecast_lab.ForecastLab = OriginalStatusLab
    asyncio.run(harness.main())
