"""Confirmed settings fences through the actual existing visual owner adapter."""
import asyncio
import importlib
from dataclasses import replace
import sqlite3
import unittest
from unittest.mock import patch
import uuid

from tests import test_visual_director_runtime as fixtures


class VisualSettingsFenceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.VisualRuntimeTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.VisualRuntimeTests.tearDownClass()

    async def asyncSetUp(self):
        self.f = fixtures.VisualRuntimeTests()
        await self.f.asyncSetUp()

    async def asyncTearDown(self):
        await self.f.asyncTearDown()

    async def persona(self, value):
        from custom_components.djconnect.session_runtime import DJPersona
        return await self.f.manager.async_update_persona(
            owner_profile_id="profile-a", session_id=self.f.session.session_id,
            dj_persona=DJPersona(value))

    async def mood(self, value):
        return await self.f.manager.async_update_mood(
            owner_profile_id="profile-a", session_id=self.f.session.session_id,
            selected_mood=value)

    async def denied(self, context):
        answer, status = await self.f.request("interpret", self.f.turn(context))
        self.assertIn(status, (409, 410, 503), answer)
        self.assertNotIn("directive", answer)

    async def test_confirmed_persona_switch_invalidates_original_lease(self):
        context = await self.f.ready()
        await self.persona("radio_dj")
        await self.denied(context)

    async def test_actual_persona_A_B_A_cannot_revive_original_lease(self):
        context = await self.f.ready()
        original = self.f.manager.current_active("profile-a")
        await self.persona("radio_dj")
        current = await self.persona(original.dj_persona.value)
        self.assertGreater(current.persona_revision, original.persona_revision)
        await self.denied(context)

    async def test_actual_mood_A_B_A_cannot_revive_original_lease(self):
        context = await self.f.ready()
        await self.mood("chill")
        current = await self.mood("energy")
        self.assertEqual(current.mood_revision, 2)
        await self.denied(context)

    async def test_settings_change_during_provider_wait_rejects_original_sample(self):
        context = await self.f.ready()
        admission = self.f.module.capture_observer(self.f.hass, self.f.observed)
        await self.persona("club_dj")
        self.assertFalse(self.f.module.accept_observation(
            self.f.hass, self.f.observed, self.f.result, admission))
        await self.denied(context)

    async def test_settings_change_during_context_or_interpret_await_is_rejected(self):
        for kind in ("context", "interpret"):
            with self.subTest(kind=kind):
                context = await self.f.ready() if self.f.engine is None else (await self.f.request())[0]
                entered, release = asyncio.Event(), asyncio.Event()
                async def wait():
                    entered.set()
                    await release.wait()
                self.f.engine.yield_once = wait
                pending = asyncio.create_task(self.f.request(kind,
                    self.f.turn(context) if kind == "interpret" else self.f.body))
                await entered.wait()
                current = self.f.manager.current_active("profile-a")
                await self.persona("radio_dj" if current.dj_persona.value != "radio_dj" else "home_dj")
                release.set()
                answer, status = await pending
                self.assertIn(status, (409, 410, 503), answer)
                self.assertNotIn("directive", answer)
                self.assertNotIn("music_context", answer)
                async def ready():
                    return None
                self.f.engine.yield_once = ready
                await self.f.observe()

    async def test_seen_equal_revision_conflict_latches_old_lease_after_restore_and_poll(self):
        from custom_components.djconnect.session_runtime import DJPersona
        context = await self.f.ready()
        original = self.f.manager.current_active("profile-a")
        conflict = replace(original, dj_persona=DJPersona.RADIO_DJ)
        self.f.manager._active_by_profile["profile-a"] = conflict
        await self.denied(context)
        self.f.manager._active_by_profile["profile-a"] = original
        await self.f.observe()
        await self.denied(context)

    async def test_fresh_settings_context_keeps_original_visit_deadline_and_turn_count(self):
        context = await self.f.ready()
        answer, status = await self.f.request("interpret", self.f.turn(context))
        self.assertEqual(status, 200, answer)
        visit = next(iter(self.f.engine.visits.values()))
        deadline, count = visit.deadline, len(visit.turns)
        await self.persona("festival_dj")
        await self.f.observe()
        fresh, status = await self.f.request()
        self.assertEqual(status, 200, fresh)
        answer, status = await self.f.request("interpret", self.f.turn(fresh, base_scene_revision=2))
        self.assertEqual(status, 200, answer)
        self.assertIs(next(iter(self.f.engine.visits.values())), visit)
        self.assertEqual(visit.deadline, deadline)
        self.assertEqual(len(visit.turns), count + 1)
        await self.denied(context)

    async def test_invalid_original_settings_metadata_never_admits_observation(self):
        await self.f.ready()
        original = self.f.manager.current_active("profile-a")
        for changes in ({"persona_revision": True}, {"persona_revision": -1},
                        {"mood_revision": True}, {"mood_revision": -1}):
            with self.subTest(changes=changes):
                self.f.manager._active_by_profile["profile-a"] = replace(original, **changes)
                self.assertIsNone(self.f.module.capture_observer(self.f.hass, self.f.observed))
                self.f.manager._active_by_profile["profile-a"] = original

    async def test_failed_setting_authorization_keeps_original_confirmed_persona(self):
        from custom_components.djconnect.session_runtime import DJPersona
        context = await self.f.ready()
        original = self.f.manager.current_active("profile-a")
        with self.assertRaises(PermissionError):
            await self.f.manager.async_update_persona(
                owner_profile_id="profile-a", session_id=original.session_id,
                dj_persona=DJPersona.RADIO_DJ, authorize=lambda: False)
        self.assertIs(self.f.manager.current_active("profile-a"), original)
        answer, status = await self.f.request("interpret", self.f.turn(context))
        self.assertEqual(status, 200, answer)

    async def test_explicit_dynamics_phrases_patch_only_same_effective_slider_in_five_locales(self):
        director = importlib.import_module("custom_components.djconnect.visual_director")
        for phrases, expected in ((
                ("Meer dynamiek", "More dynamics", "Mehr Dynamik", "Plus de dynamisme", "Más dinamismo"), 0.65), (
                ("Minder dynamiek", "Less dynamics", "Weniger Dynamik", "Moins de dynamisme", "Menos dinamismo"), 0.35)):
            for phrase in phrases:
                with self.subTest(phrase=phrase):
                    directive = director.interpret_visual(phrase,
                        {**self.f.scene, "motion": 0.5}, "current_track")
                    self.assertEqual(directive, {"kind": "patch", "scope": "current_track", "patch": {"motion": expected}})
        with self.assertRaises(director.VisualDirectorError):
            director.interpret_visual("Meer dynamiek en speel Pink Floyd", self.f.scene, "current_track")

    async def test_48_logical_context_states_have_no_numeric_dependency_or_visual_writes(self):
        await self.f.ready()
        def dump():
            connection = sqlite3.connect(f"file:{self.f.f.path}?mode=ro", uri=True)
            try:
                return tuple(connection.iterdump())
            finally:
                connection.close()
        cases = 0
        for persona in ("home_dj", "radio_dj", "club_dj", "festival_dj"):
            for mood in ("chill", "groove", "energy", "party"):
                # Deliberate normal settings updates are outside the visual
                # read-only measurement; each triplet is a separate visit.
                await self.persona(persona)
                await self.mood(mood)
                self.assertTrue(await self.f.observe())
                self.f.body["visit_id"] = str(uuid.uuid4())
                before, household = dump(), self.f.storage.household
                with (patch.object(self.f.storage, "async_save", side_effect=AssertionError("visual Profile write")),
                      patch.object(self.f.history, "async_append_exchange", side_effect=AssertionError("visual history write"))):
                    context, status = await self.f.request()
                    self.assertEqual(status, 200, context)
                    self.assertIsNone(context["music_context"]["audio_features"])
                    for index, bias in enumerate((0.0, 0.5, 1.0)):
                        answer, status = await self.f.request("interpret", self.f.turn(context,
                            base_scene_revision=index + 1, dynamics_bias=bias,
                            active_scene={**self.f.scene, "motion": bias}, text="Meer diepte"))
                        self.assertEqual(status, 200, answer)
                        self.assertEqual(set(answer["directive"]["patch"]), {"depth"})
                        self.assertEqual(answer["base_scene_revision"], index + 1)
                        self.assertNotIn("applied", answer)
                        cases += 1
                self.assertIs(self.f.storage.household, household)
                self.assertEqual(dump(), before)
        self.assertEqual(cases, 48)

