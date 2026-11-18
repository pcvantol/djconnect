"""Causal ephemeral Visual Director cases; synthetic data, no HA/provider/model."""

from __future__ import annotations
import asyncio
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import uuid


def load():
    name = "djc_visual_director_test_subject"
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).parents[1] / "custom_components/djconnect/visual_director.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class VisualDirectorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.m = load()
        self.clock = 100.0
        self.valid = True
        self.actor = object()
        self.source = object()
        self.visit = str(uuid.uuid4())
        self.engine = self.m.VisualDirector(
            clock=lambda: self.clock, epoch=lambda: 1792623600 + self.clock, call_later=None
        )
        self.request = {
            "schema_version": 1,
            "client_type": "ios",
            "device_id": "djconnect-ios-SYNTHETIC001",
            "session_id": "SYNTHETIC-SESSION",
            "visit_id": self.visit,
        }
        self.scene = {
            "palette": [0.3, 0.85, 0.6],
            "motion": 0.3,
            "depth": 0.5,
            "roughness": 0.1,
            "deformation": 0.4,
        }
        self.observe()

    def observe(self, media="spotify:track:" + "a" * 22, target="synthetic-output", position=None):
        return self.engine.observe(
            self.source,
            media=media,
            target=target,
            position_ms=10000 + (self.clock - 100) * 1000 if position is None else position,
            state="playing",
            music={"title": "Synthetic recording", "artist": "Synthetic artist", "mood": "groove"},
            authorized=lambda: self.valid,
        )

    async def context(self):
        return await self.engine.context(
            self.actor, self.source, self.request, authorized=lambda: self.valid
        )

    def turn(self, context, text="Maak het wat rustiger en vloeibaarder", **extra):
        return {
            **self.request,
            "client_turn_id": str(uuid.uuid4()),
            "base_scene_revision": 1,
            "context_lease_id": context["context_lease_id"],
            "observed_occurrence_id": context["observed_occurrence_id"],
            "text": text,
            "active_scene": copy.deepcopy(self.scene),
            "dynamics_bias": 0.5,
            "scope": "current_track",
            **extra,
        }

    async def interpret(self, body):
        return await self.engine.interpret(
            self.actor, self.source, body, authorized=lambda: self.valid
        )

    async def failure(self, awaitable, code):
        with self.assertRaises(self.m.VisualDirectorError) as e:
            await awaitable
        self.assertEqual(e.exception.code, code)

    async def test_context_is_small_unmeasured_and_original_lease_coherent(self):
        c = await self.context()
        self.assertGreater(c["lease_duration_ms"], 0)
        self.assertLessEqual(c["lease_duration_ms"], 15000)
        self.assertEqual(c["music_context"]["genres"], [])
        self.assertIsNone(c["music_context"]["audio_features"])
        self.assertEqual(c["music_context"]["symbolic_session_mood"], "groove")
        self.assertNotIn("spotify:", json.dumps(c))

    async def test_progress_poll_keeps_epoch_but_A_B_A_output_and_seek_fence_old(self):
        a = await self.context()
        self.clock += 2
        self.observe()
        b = await self.context()
        self.assertEqual(a["observed_occurrence_id"], b["observed_occurrence_id"])
        self.observe("spotify:track:" + "b" * 22)
        self.observe()
        c = await self.context()
        self.assertNotEqual(a["observed_occurrence_id"], c["observed_occurrence_id"])
        await self.failure(self.interpret(self.turn(a)), "visual_context_changed")
        self.observe(target="different-output")
        d = await self.context()
        self.assertNotEqual(c["observed_occurrence_id"], d["observed_occurrence_id"])
        self.observe(target="different-output", position=0)
        e = await self.context()
        self.assertNotEqual(d["observed_occurrence_id"], e["observed_occurrence_id"])

    async def test_new_context_poll_cannot_renew_original_turn(self):
        a = await self.context()
        self.clock += 10
        self.observe()
        b = await self.context()
        self.clock += 6
        await self.failure(self.interpret(self.turn(a)), "visual_context_expired")
        self.assertTrue((await self.interpret(self.turn(b)))["success"])

    async def test_revoke_is_idempotent_tombstone_and_context_cannot_rearm(self):
        c = await self.context()
        self.engine.revoke(self.actor, self.source, self.request)
        self.engine.revoke(self.actor, self.source, self.request)
        await self.failure(self.context(), "visual_context_expired")
        await self.failure(self.interpret(self.turn(c)), "visual_context_expired")

    async def test_late_context_completion_after_revoke_cannot_get_or_create(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def yield_once():
            entered.set()
            await release.wait()

        self.engine.yield_once = yield_once
        pending = asyncio.create_task(self.context())
        await entered.wait()
        self.engine.revoke(self.actor, self.source, self.request)
        release.set()
        await self.failure(pending, "visual_context_expired")
        await self.failure(self.context(), "visual_context_expired")

    async def test_late_interpret_after_exit_owner_or_source_change_has_no_result(self):
        for withdrawal in ("revoke", "owner", "source"):
            with self.subTest(withdrawal=withdrawal):
                await self.asyncSetUp()
                c = await self.context()
                entered, release = asyncio.Event(), asyncio.Event()

                async def yield_once():
                    entered.set()
                    await release.wait()

                self.engine.yield_once = yield_once
                pending = asyncio.create_task(self.interpret(self.turn(c)))
                await entered.wait()
                if withdrawal == "revoke":
                    self.engine.revoke(self.actor, self.source, self.request)
                elif withdrawal == "owner":
                    self.valid = False
                else:
                    self.engine.withdraw(self.source)
                release.set()
                with self.assertRaises(self.m.VisualDirectorError):
                    await pending

    async def test_current_scene_corrections_are_patches_and_hold_undo_reset_variant_exclusive(
        self,
    ):
        c = await self.context()
        a = await self.interpret(self.turn(c))
        self.assertLess(a["directive"]["patch"]["motion"], 0.3)
        self.assertNotIn("palette", a["directive"]["patch"])
        self.assertEqual(a["status"], "interpreted")
        self.assertNotIn("applied", a)
        b = await self.interpret(self.turn(c, "En iets meer goud", base_scene_revision=2))
        self.assertEqual(set(b["directive"]["patch"]), {"palette"})
        d = await self.interpret(
            self.turn(c, "Nee, iets minder goud. Wel meer diepte.", base_scene_revision=3)
        )
        self.assertEqual(set(d["directive"]["patch"]), {"palette", "depth"})
        for text, kind in [
            ("Hou deze stijl aan, maar blijf variëren per nummer", "hold"),
            ("Ga terug naar hoe het net was", "undo"),
            ("Terug naar de DJ", "reset"),
            ("Maak een variant", "variant"),
        ]:
            result = await self.interpret(self.turn(c, text, base_scene_revision=4))
            self.assertEqual(result["directive"]["kind"], kind)
            if kind == "hold":
                self.assertEqual(result["directive"]["scope"], "while_in_vibescape")

    async def test_explicit_speech_scope_wins_over_hint_without_whole_baseline(self):
        c = await self.context()
        r = await self.interpret(
            self.turn(c, "Meer diepte, alleen dit nummer", scope="while_in_vibescape")
        )
        self.assertEqual(r["directive"]["scope"], "current_track")
        r = await self.interpret(self.turn(c, "Meer diepte, hele verblijf"))
        self.assertEqual(r["directive"]["scope"], "while_in_vibescape")

    async def test_five_language_visual_phrases(self):
        c = await self.context()
        for text in [
            "Make it calmer and more fluid",
            "Maak het rustiger en vloeibaarder",
            "Mach es ruhiger und flüssiger",
            "Plus calme et plus fluide",
            "Más tranquilo y más fluido",
        ]:
            r = await self.interpret(self.turn(c, text))
            self.assertEqual(r["directive"]["kind"], "patch")
            self.assertLess(r["directive"]["patch"]["motion"], 0.3)

    async def test_general_music_ha_and_mixed_commands_fail_closed(self):
        c = await self.context()
        for text in [
            "Speel Pink Floyd",
            "Speel Pink Floyd en maak het goud",
            "Turn on the kitchen light",
            "Who wrote this song?",
            "Open https://example.com/shader",
            "import os; run code",
        ]:
            await self.failure(self.interpret(self.turn(c, text)), "visual_only_unsupported")
        await self.failure(
            self.interpret(self.turn(c, "Doe dat maar anders")), "visual_direction_ambiguous"
        )

    async def test_duplicate_turn_old_revision_and_wrong_actor_are_rejected(self):
        c = await self.context()
        t = self.turn(c)
        await self.interpret(t)
        await self.failure(self.interpret(t), "visual_context_changed")
        await self.failure(
            self.interpret(self.turn(c, base_scene_revision=0)), "visual_context_changed"
        )
        await self.failure(
            self.engine.interpret(object(), self.source, self.turn(c), authorized=lambda: True),
            "visual_context_changed",
        )

    async def test_attempt_budget_survives_track_change_context_renewal_and_rejections(self):
        c = await self.context()
        for n in range(32):
            await self.failure(
                self.interpret(self.turn(c, "Speel Pink Floyd", base_scene_revision=n)),
                "visual_only_unsupported",
            )
        self.observe("spotify:track:" + "b" * 22)
        d = await self.context()
        await self.failure(
            self.interpret(self.turn(d, base_scene_revision=33)), "visual_turn_limit_reached"
        )

    async def test_original_visit_lifetime_and_rollback_fail_closed(self):
        await self.context()
        # Real fresh observations maintain source availability, never the
        # original visit deadline. A thirty-minute source gap is withdrawal.
        for _ in range(119):
            self.clock += 15
            self.observe()
        self.clock += 14
        self.observe()
        await self.context()
        self.clock += 2
        self.observe()
        await self.failure(self.context(), "visual_context_expired")
        await self.asyncSetUp()
        c = await self.context()
        self.clock -= 1
        await self.failure(self.interpret(self.turn(c)), "visual_context_expired")

    async def test_capacity_does_not_evict_live_tombstone_to_rearm(self):
        self.engine.maximum_visits = 1
        await self.context()
        self.engine.revoke(self.actor, self.source, self.request)
        other = {**self.request, "visit_id": str(uuid.uuid4())}
        await self.failure(
            self.engine.context(self.actor, self.source, other, authorized=lambda: True),
            "visual_rate_limited",
        )
        await self.failure(self.context(), "visual_context_expired")

    async def test_strict_utf8_nonfinite_duplicate_nested_unknown_and_total_size(self):
        c = await self.context()
        for raw in [b'{"x":1,"x":1}', b'{"x":NaN}', b'{"x":Infinity}', b"\xff", b" " * 8193]:
            with self.assertRaises(self.m.VisualDirectorError):
                self.m.parse_body(raw)
        for mutate in [
            lambda t: t.update(text="🎵" * 257),
            lambda t: t.update(observed_occurrence_id="🎵" * 65),
            lambda t: t["active_scene"].update(shader="code"),
            lambda t: t["active_scene"].update(depth=True),
            lambda t: t.update(schema_version=True),
        ]:
            t = self.turn(c)
            mutate(t)
            await self.failure(self.interpret(t), "invalid_request")

    async def test_no_text_scene_or_results_retained_after_interpret_and_revoke(self):
        c = await self.context()
        marker = "En iets meer goud"
        await self.interpret(self.turn(c, marker))
        self.engine.revoke(self.actor, self.source, self.request)
        retained = repr(vars(self.engine))
        self.assertNotIn(marker, retained)
        self.assertNotIn("Synthetic recording", retained)
        self.assertNotIn("active_scene", retained)

    async def test_uuid_case_variants_cannot_rearm_visit_or_replay_turn(self):
        c = await self.context()
        turn = self.turn(c)
        await self.interpret(turn)
        await self.failure(
            self.interpret({**turn, "client_turn_id": turn["client_turn_id"].upper()}),
            "visual_context_changed",
        )
        self.engine.revoke(
            self.actor, self.source, {**self.request, "visit_id": self.visit.upper()}
        )
        await self.failure(self.context(), "visual_context_expired")

    async def test_same_visit_id_cannot_rearm_against_a_replacement_source(self):
        await self.context()
        new_source = object()
        await self.failure(
            self.engine.context(self.actor, new_source, self.request, authorized=lambda: True),
            "visual_context_changed",
        )
        self.assertEqual(len(self.engine.visits), 1)

    async def test_comparative_negation_and_unsupported_scripts_cannot_reverse_visual_intent(self):
        for text in (
            "less fluid",
            "less calm",
            "no faster",
            "less a bit fluid",
            "weniger flussiger",
            "moins fluide",
            "menos fluido",
            "more depth 播放音乐",
            "meer diepte включи музыку",
        ):
            with self.subTest(text=text), self.assertRaises(self.m.VisualDirectorError):
                self.m.interpret_visual(text, self.scene, "current_track")
        answer = self.m.interpret_visual(
            "Nee, iets minder goud. Wel meer diepte.", self.scene, "current_track"
        )
        self.assertGreater(answer["patch"]["depth"], self.scene["depth"])
        self.assertEqual(set(answer["patch"]), {"palette", "depth"})

    async def test_every_localized_help_example_has_its_promised_effect_and_scope(self):
        spec = importlib.util.spec_from_file_location(
            "vibe_help_subject",
            Path(__file__).parents[1] / "custom_components/djconnect/visual_director_catalogue.py",
        )
        catalogue = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(catalogue)
        metadata = catalogue.capability()
        self.assertEqual(set(metadata["help"]), {"en", "nl", "de", "fr", "es"})
        for locale, help_content in metadata["help"].items():
            for example in help_content["examples"]:
                with self.subTest(locale=locale, example=example["id"]):
                    effect = self.m.interpret_visual(example["text"], self.scene, "current_track")
                    key = example["id"]
                    if key in ("variant", "hold", "undo", "reset"):
                        self.assertEqual(effect["kind"], key)
                    else:
                        self.assertEqual(effect["kind"], "patch")
                        fields = effect["patch"]
                        if key == "calmer_fluid":
                            self.assertLess(fields["motion"], self.scene["motion"])
                            self.assertLess(fields["roughness"], self.scene["roughness"])
                            self.assertGreater(fields["deformation"], self.scene["deformation"])
                            self.assertEqual(set(fields), {"motion", "roughness", "deformation"})
                        elif key == "faster":
                            self.assertGreater(fields["motion"], self.scene["motion"])
                            self.assertEqual(set(fields), {"motion"})
                        elif key == "more_depth":
                            self.assertGreater(fields["depth"], self.scene["depth"])
                            self.assertEqual(set(fields), {"depth"})
                        else:
                            self.assertEqual(set(fields), {"palette"})
                            self.assertGreater(fields["palette"][0], self.scene["palette"][0])
                    if key in ("calmer_fluid", "faster", "more_depth", "more_gold"):
                        for scope in help_content["scopes"]:
                            scoped = self.m.interpret_visual(
                                example["text"] + " " + scope["text"], self.scene, "current_track"
                            )
                            self.assertEqual(scoped["scope"], scope["id"])
        metadata["help"]["nl"]["examples"].clear()
        self.assertEqual(len(catalogue.capability()["help"]["nl"]["examples"]), 8)
