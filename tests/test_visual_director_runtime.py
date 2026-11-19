"""Actual owner/storage/Session fences with disposable SQLite and no providers."""

from __future__ import annotations

import asyncio
import gc
import weakref
from dataclasses import replace
import importlib
import json
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch, AsyncMock
import uuid

from tests import test_session_conversation_history as fixtures


class VisualRuntimeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()
        cls.module = importlib.import_module("custom_components.djconnect.visual_director_runtime")

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = fixtures.SessionConversationHistoryTest()
        await self.f.asyncSetUp()
        (
            self.hass,
            self.runtime,
            self.history,
            identity,
            self.headers,
        ) = await self.f.transport_fixture()
        self.manager = self.f.manager
        self.storage = self.hass.data["djconnect"]["djconnect_profile_platform"]
        self.storage.hass = self.hass
        from custom_components.djconnect.domain.music_account import MusicAccountKind

        await self.storage.async_upsert_music_account(
            "source-account",
            "source-spotify",
            kind=MusicAccountKind.PERSONAL,
            display_name="Synthetic account",
            linked_profile_ids=frozenset({"profile-a"}),
            provider_account_id="synthetic-provider",
        )
        p = self.storage.household.profiles["profile-a"]
        await self.storage.async_update_profile(
            "profile-a",
            preferences=replace(
                p.preferences,
                default_backend_id="source-spotify",
                default_music_account_id="source-account",
            ),
        )
        entry = SimpleNamespace(
            entry_id="owner-entry",
            data={
                **identity,
                "device_token": "synthetic-fixture-token",
                "music_backend": "source-spotify",
                "music_account_id": "source-account",
                "profile_id": "profile-a",
            },
            options={},
            disabled_by=None,
            state=SimpleNamespace(value="loaded"),
        )
        self.runtime.entry = entry
        self.runtime._receiver_end_generation = 0
        self.hass.config_entries = SimpleNamespace(
            async_get_entry=lambda key: entry if key == "owner-entry" else None,
            async_entries=lambda domain: [entry],
        )
        self.session = await self.manager.async_start(
            owner_profile_id="profile-a",
            locale="nl",
            selected_mood="energy",
            music_backend="spotify_direct",
            history_source_context={
                "backend_id": "source-spotify",
                "music_account_id": "source-account",
                "provider_entry_id": "owner-entry",
                "provider_account_id": "synthetic-provider",
            },
        )
        from custom_components.djconnect.playback_observation import (
            PlaybackObservationManager,
            _SpotifyObservationSession,
        )

        self.observers = PlaybackObservationManager(self.hass)

        async def no_insight():
            raise AssertionError("Vibe must not request Track Insight")

        self.observed = _SpotifyObservationSession(
            self.runtime, "profile-a", self.session.session_id, no_insight
        )
        self.observers._spotify_sessions["profile-a"] = self.observed
        self.hass.data["djconnect"]["playback_observation_manager"] = self.observers
        self.body = {
            "schema_version": 1,
            **identity,
            "session_id": self.session.session_id,
            "visit_id": str(uuid.uuid4()),
        }
        self.result = SimpleNamespace(
            media_identity="spotify:track:" + "a" * 22,
            state="playing",
            is_playing=True,
            title="Synthetic recording",
            artist="Synthetic artist",
            target_name="Synthetic output",
            target_id="synthetic-output-a",
            position_ms=1000,
        )
        self.scene = {
            "palette": [0.3, 0.8, 0.6],
            "motion": 0.4,
            "depth": 0.5,
            "roughness": 0.3,
            "deformation": 0.2,
        }
        self.engine = None

    async def asyncTearDown(self):
        if self.engine:
            self.engine.invalidate_all()
        await self.f.asyncTearDown()

    async def request(self, kind="context", body=None, headers=None):
        return await self.module.handle(
            self.hass,
            kind,
            self.body if body is None else body,
            headers=self.headers if headers is None else headers,
        )

    async def observe(self, *, after=None):
        admission = self.module.capture_observer(self.hass, self.observed)
        if after:
            await after()
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            state=self.result.state,
            media_identity=self.result.media_identity,
            title=self.result.title,
            artist=self.result.artist,
            target_name=self.result.target_name,
            duration_ms=180000,
            position_ms=self.result.position_ms,
        )
        return self.module.accept_observation(self.hass, self.observed, self.result, admission)

    async def ready(self):
        first, status = await self.request()
        self.assertEqual(status, 503, first)
        self.engine = self.hass.data["djconnect"]["vibescape_visual_director"]
        self.assertTrue(await self.observe())
        result, status = await self.request()
        self.assertEqual(status, 200, result)
        return result

    def turn(self, context, **kwargs):
        return {
            **self.body,
            "client_turn_id": str(uuid.uuid4()),
            "base_scene_revision": 1,
            "context_lease_id": context["context_lease_id"],
            "observed_occurrence_id": context["observed_occurrence_id"],
            "text": "Maak het rustiger en vloeibaarder",
            "active_scene": self.scene,
            "dynamics_bias": 0.5,
            "scope": "current_track",
            **kwargs,
        }

    async def test_first_context_waits_for_actual_observation_and_interpret_has_no_persistence(
        self,
    ):
        context = await self.ready()

        def durable():
            connection = sqlite3.connect(f"file:{self.f.path}?mode=ro", uri=True)
            try:
                return tuple(connection.iterdump())
            finally:
                connection.close()

        before = durable()
        profile = self.storage.household
        with (
            patch.object(self.storage, "async_save", side_effect=AssertionError("Profile write")),
            patch.object(
                self.history, "async_append_exchange", side_effect=AssertionError("history write")
            ),
        ):
            answer, status = await self.request("interpret", self.turn(context))
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["status"], "interpreted")
        self.assertNotIn("applied", answer)
        self.assertIs(self.storage.household, profile)
        self.assertEqual(durable(), before)
        self.assertNotIn("text", answer)
        self.assertNotIn("Maak het rustiger", json.dumps(answer))
        self.assertIsNone(answer.get("audio_url"))

    async def test_unauthorized_cross_device_session_and_headers_never_allocate_engine(self):
        for body, headers in [
            ({**self.body, "device_id": "djconnect-ios-ZZZZZZZZZZZZ"}, self.headers),
            ({**self.body, "client_type": "watchos"}, self.headers),
            ({**self.body, "session_id": "other-session"}, self.headers),
            (self.body, {"Authorization": "Bearer wrong"}),
            (self.body, {**self.headers, "X-DJConnect-Device-ID": "different"}),
        ]:
            with self.subTest(body=body):
                answer, status = await self.request(body=body, headers=headers)
                self.assertIn(status, (400, 401, 409))
                self.assertNotIn("vibescape_visual_director", self.hass.data["djconnect"])

    async def test_missing_storage_or_original_source_never_lazy_creates_or_falls_back(self):
        domain = self.hass.data["djconnect"]
        storage = domain.pop("djconnect_profile_platform")
        answer, status = await self.request()
        self.assertEqual(status, 503, answer)
        self.assertNotIn("djconnect_profile_platform", domain)
        domain["djconnect_profile_platform"] = storage
        for field in tuple(self.manager._history_source_contexts[self.session.session_id]):
            original = self.manager._history_source_contexts[self.session.session_id].pop(field)
            answer, status = await self.request()
            self.assertEqual(status, 503, answer)
            self.manager._history_source_contexts[self.session.session_id][field] = original

    async def test_profile_revision_A_B_A_and_entry_generation_block_late_context(self):
        await self.ready()
        entered, release = asyncio.Event(), asyncio.Event()

        async def yield_once():
            entered.set()
            await release.wait()

        self.engine.yield_once = yield_once
        pending = asyncio.create_task(self.request())
        await entered.wait()
        self.storage._invalidate_session_images()
        release.set()
        answer, status = await pending
        self.assertIn(status, (409, 410), answer)
        self.assertNotIn("music_context", answer)
        self.assertNotIn("Synthetic recording", repr(vars(self.engine)))

    async def test_actual_progress_preserves_occurrence_but_track_and_output_changes_fence_old_turn(
        self,
    ):
        first = await self.ready()
        self.result.position_ms += 1000
        await self.observe()
        second, status = await self.request()
        self.assertEqual(status, 200)
        self.assertEqual(first["observed_occurrence_id"], second["observed_occurrence_id"])
        old = self.result.media_identity
        self.result.media_identity = "spotify:track:" + "b" * 22
        await self.observe()
        self.result.media_identity = old
        await self.observe()
        third, status = await self.request()
        self.assertEqual(status, 200)
        self.assertNotEqual(third["observed_occurrence_id"], first["observed_occurrence_id"])
        answer, status = await self.request("interpret", self.turn(first))
        self.assertEqual(status, 409, answer)

    async def test_source_change_while_provider_awaits_never_admits_late_metadata(self):
        await self.ready()

        async def change():
            self.runtime._receiver_end_generation += 1

        self.assertFalse(await self.observe(after=change))
        self.assertNotIn("Synthetic recording", repr(vars(self.engine)))

    async def test_revoke_and_session_end_withdraw_before_persistent_await(self):
        context = await self.ready()
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.f.sessions.async_transition

        async def blocked(*args, **kwargs):
            entered.set()
            await release.wait()
            return await original(*args, **kwargs)

        with patch.object(self.f.sessions, "async_transition", blocked):
            pending = asyncio.create_task(
                self.manager.async_end(
                    owner_profile_id="profile-a", session_id=self.session.session_id
                )
            )
            await entered.wait()
            self.assertNotIn("Synthetic recording", repr(vars(self.engine)))
            answer, status = await self.request("interpret", self.turn(context))
            self.assertIn(status, (409, 410), answer)
            release.set()
            await pending
        answer, status = await self.request()
        self.assertEqual(status, 409, answer)

    async def test_guest_shared_and_missing_known_profile_fail_closed(self):
        from custom_components.djconnect.domain import ProfilePrivacyMode

        for privacy in (ProfilePrivacyMode.SHARED, ProfilePrivacyMode.GUEST_SAFE):
            await self.storage.async_update_profile("profile-a", privacy_mode=privacy)
            answer, status = await self.request()
            self.assertEqual(status, 401, answer)
            self.assertNotIn("music_context", answer)

    async def test_real_stage1_poll_feeds_only_actual_accepted_observation_without_extra_provider_calls(
        self,
    ):
        first, status = await self.request()
        self.assertEqual(status, 503, first)
        self.engine = self.hass.data["djconnect"]["vibescape_visual_director"]
        observation_module = importlib.import_module(
            "custom_components.djconnect.playback_observation"
        )
        calls = []
        result = self.result

        class Backend:
            def __init__(self, *args):
                pass

            async def async_observe_current_playback(self):
                calls.append("current")
                return result

            async def async_observe_next_item(self, identity):
                calls.append("existing_queue")
                return {}

        with (
            patch.object(observation_module, "SpotifyBackend", Backend),
            patch.object(self.manager, "async_process_track_started", AsyncMock(return_value=None)),
        ):
            await self.observers._async_poll_spotify(self.observed)
        answer, status = await self.request()
        self.assertEqual(status, 200, answer)
        self.assertEqual(
            answer["music_context"]["recording"],
            {"title": "Synthetic recording", "artist": "Synthetic artist"},
        )
        self.assertEqual(calls, ["current", "existing_queue"])

    async def test_temporary_sample_absence_preserves_original_visit_budget_without_music(self):
        old = await self.ready()
        deadline = next(iter(self.engine.visits.values())).deadline
        self.engine.invalidate_observation(self.observed.visual_source)
        answer, status = await self.request()
        self.assertEqual(status, 503, answer)
        self.assertNotIn("Synthetic recording", repr(vars(self.engine)))
        await self.observe()
        answer, status = await self.request()
        self.assertEqual(status, 200, answer)
        self.assertEqual(next(iter(self.engine.visits.values())).deadline, deadline)
        self.assertNotEqual(old["observed_occurrence_id"], answer["observed_occurrence_id"])

    async def test_profile_value_replacement_never_creates_a_new_actor_to_rearm_same_visit(self):
        await self.ready()
        await self.storage.async_update_profile("profile-a", display_name="Same owner renamed")
        answer, status = await self.request()
        self.assertEqual(status, 410, answer)
        self.assertEqual(len(self.engine.visits), 1)

    async def _assert_provider_failure_drops_metadata(self, error_type):
        module = importlib.import_module("custom_components.djconnect.playback_observation")
        context = await self.ready()
        deadline = next(iter(self.engine.visits.values())).deadline

        class Backend:
            def __init__(self, *args):
                pass

            async def async_observe_current_playback(self):
                raise error_type("Synthetic provider failure")

        with patch.object(module, "SpotifyBackend", Backend):
            await self.observers._async_poll_spotify(self.observed)
        answer, status = await self.request()
        self.assertEqual(status, 503, answer)
        self.assertNotIn("Synthetic recording", repr(vars(self.engine)))
        self.assertEqual(next(iter(self.engine.visits.values())).deadline, deadline)
        self.result.position_ms += 1000
        self.assertTrue(await self.observe())
        recovered, status = await self.request()
        self.assertEqual(status, 200, recovered)
        self.assertNotEqual(recovered["observed_occurrence_id"], context["observed_occurrence_id"])
        self.assertEqual(next(iter(self.engine.visits.values())).deadline, deadline)

    async def test_backend_failure_drops_old_metadata_without_renewing_visit(self):
        module = importlib.import_module("custom_components.djconnect.playback_observation")
        await self._assert_provider_failure_drops_metadata(module.SpotifyBackendError)

    async def test_generic_provider_failure_drops_old_metadata_without_renewing_visit(self):
        await self._assert_provider_failure_drops_metadata(RuntimeError)

    async def test_same_name_different_output_id_invalidates_old_lease_but_stable_id_progress_does_not(
        self,
    ):
        first = await self.ready()
        self.result.position_ms += 1000
        self.assertTrue(await self.observe())
        progressed, status = await self.request()
        self.assertEqual(status, 200)
        self.assertEqual(progressed["observed_occurrence_id"], first["observed_occurrence_id"])
        self.result.target_id = "synthetic-output-b"
        self.result.position_ms += 1000
        self.assertTrue(await self.observe())
        changed, status = await self.request()
        self.assertEqual(status, 200)
        self.assertNotEqual(changed["observed_occurrence_id"], first["observed_occurrence_id"])
        answer, status = await self.request("interpret", self.turn(first))
        self.assertEqual(status, 409, answer)
        self.assertNotIn("synthetic-output-", json.dumps(changed))

    async def test_missing_output_id_cannot_use_display_name_as_an_occurrence_fallback(self):
        await self.ready()
        self.result.target_id = ""
        self.result.position_ms += 1000
        self.assertFalse(await self.observe())
        answer, status = await self.request()
        self.assertEqual(status, 503, answer)
        self.assertNotIn("Synthetic recording", repr(vars(self.engine)))

    async def _assert_visual_marker_does_not_retain_expired_projection(self, reason):
        await self.ready()
        old_admission = self.module.capture_observer(self.hass, self.observed)
        old_projection = weakref.ref(self.session.broadcast.passive_observation[2])
        if reason == "revoke":
            await self.request("revoke")
        else:
            expired_clock = self.engine.last_clock + 1801
            self.engine.clock = lambda: expired_clock
            self.engine.sweep()
        self.result.media_identity = "spotify:track:" + "b" * 22
        self.result.title = "Synthetic next recording"
        self.result.position_ms += 1000
        self.assertFalse(await self.observe())
        gc.collect()
        self.assertIsNone(
            old_projection(), "Visual observer/admission retained the old accepted projection"
        )
        self.assertNotIn("Synthetic recording", repr(vars(self.engine)))
        self.assertIsInstance(old_admission.previous_sample_serial, int)
        self.assertIsInstance(self.observed.visual_sample_serial, int)

    async def test_revoke_then_non_vibe_observation_releases_old_projection(self):
        await self._assert_visual_marker_does_not_retain_expired_projection("revoke")

    async def test_visit_expiry_then_non_vibe_observation_releases_old_projection(self):
        await self._assert_visual_marker_does_not_retain_expired_projection("expiry")
