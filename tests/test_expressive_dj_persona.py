"""Editorial behaviour through existing resolver → Runtime → Flow/Broadcast."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import sys
import unittest
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module
from tests import test_shared_producer_continuity as shared_source


class ExpressiveDJPersonaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()
        from custom_components.djconnect import session_facts

        cls.facts = session_facts

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("custom_components.djconnect.session_runtime", None)
        if cls.previous_const is not None:
            sys.modules["custom_components.djconnect.const"] = cls.previous_const
        else:
            sys.modules.pop("custom_components.djconnect.const", None)

    def source_pair(self, number):
        fixture = shared_source.SharedProducerContinuityTest()
        fixture.facts = self.facts
        titles = ("Amber Lines", "Slow Lanterns", "Paper Windows", "Quiet Current")
        catalog = {
            **fixture.catalog(number),
            "title": titles[number % 4] + (f" {number}" if number >= 4 else ""),
            "release_date": "",
            "isrc": f"USABC010000{number + 1}",
        }
        recording = fixture.recording(
            number, ids=(8, 9) if number < 2 else (6, 7), names=("Nora Vale", "Sam Reed")
        )
        recording["title"] = catalog["title"]
        recording["artist-credit"][0]["artist"]["id"] = (
            f"00000000-0000-0000-0000-{100 + number:012d}"
        )
        return catalog, recording

    def run_sequence(self, persona, locale="nl", *, mood="neutral", durations=None, count=4):
        async def scenario():
            now = [100.0]
            manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: now[0])
            session = await manager.async_start(
                owner_profile_id="owner",
                locale=locale,
                selected_mood=mood,
                dj_persona=persona,
                music_backend="spotify_direct",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
            session = replace(
                session,
                session_direction=replace(
                    session.session_direction, direction=self.runtime.SessionDirectionType.EXPLORING
                ),
            )
            manager._active_by_profile["owner"] = session
            receipts, snapshots, originals = [], [], []
            for number in range(count):
                catalog, recording = self.source_pair(number)
                now[0] = 100.0 + 300 * number
                stamp[0] = (base + timedelta(seconds=300 * number)).isoformat()

                class Resolver(self.facts.SessionFactsResolver):
                    async def _get(inner, path, params=None, **kwargs):
                        if path.startswith("isrc/"):
                            return {"recordings": [recording]}
                        if path.startswith("recording/"):
                            return recording
                        return {}

                facts = await Resolver(object()).resolve(catalog)
                originals.append(facts)
                await manager.async_update_playback_projection(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    state="playing",
                    media_identity=catalog["uri"],
                    title=catalog["title"],
                    artist=catalog["artist"],
                    album=catalog["album_name"],
                    artwork_url="/api/djconnect/v1/image_proxy/software-art",
                    duration_ms=durations[number] if durations else 300000,
                    position_ms=0,
                )

                async def source():
                    return {
                        "_qualified_facts": facts,
                        "raw_provider_payload": {"private": "never model input"},
                        "analysis": {"summary": "untrusted malformed model text"},
                    }

                moment = await manager.async_process_track_started(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    media_identity=catalog["uri"],
                    insight_provider=source,
                    require_current_playback=True,
                    allow_initial_facts=True,
                )
                receipts.append(moment)
                snapshots.append(session.broadcast.as_dict())
            self.manager, self.session = manager, await manager.async_get_active("owner")
            self.originals = originals
            self.last_capture = {
                "receipts": [m.as_dict() if m else None for m in receipts],
                "snapshots": snapshots,
            }
            return receipts

        base = datetime.now(UTC)
        stamp = [base.isoformat()]
        # All normalized source age / observed-event time use the same fake clock;
        # provider responses remain source-shaped fixtures, not live MusicBrainz.
        clock = [100.0]
        original_pair = self.source_pair

        def pair(number):
            clock[0] = 100.0 + 300 * number
            return original_pair(number)

        with (
            patch.object(self.runtime, "_timestamp", lambda: stamp[0]),
            patch("time.monotonic", lambda: clock[0]),
            patch.object(self, "source_pair", pair),
        ):
            return asyncio.run(scenario())

    def test_four_personas_realize_same_facts_differently_in_all_five_languages(self):
        for locale in self.facts.LANGUAGES:
            series = [self.run_sequence(persona, locale) for persona in self.runtime.DJPersona]
            self.assertEqual(len({moments[0].content for moments in series}), 4)
            self.assertEqual(len({moments[1].content for moments in series}), 4)
            for moments in series:
                self.assertEqual([m.moment_type.value for m in moments], ["track"] * 4)
                for index, moment in enumerate(moments):
                    self.assertIn("Nora Vale", moment.content)
                    if index in (0, 2):
                        self.assertIn("Sam Reed", moment.content)
                        self.assertNotIn("url_previous", dict(moment.source_attribution))
                    else:
                        self.assertIn(self.source_pair(index)[0]["title"], moment.content)
                        self.assertIn(self.source_pair(index - 1)[0]["title"], moment.content)
                        self.assertIn("url_previous", dict(moment.source_attribution))

    def test_identical_ordinary_credit_core_varies_only_after_published_moments(self):
        for persona in self.runtime.DJPersona:
            moments = self.run_sequence(persona)
            self.assertEqual(
                self.originals[0][0].copy_for("nl"), self.originals[2][0].copy_for("nl")
            )
            self.assertNotEqual(moments[0].content, moments[2].content)
            for moment in moments:
                self.assertNotIn("Wist je dat", moment.content)
                self.assertNotIn("private", moment.content)

    def test_source_realization_never_enters_speech_projection(self):
        self.run_sequence(self.runtime.DJPersona.HOME_DJ)
        for snapshot in self.last_capture["snapshots"]:
            self.assertTrue(snapshot.get("presentations"))
            for presentation in snapshot["presentations"]:
                self.assertNotIn("speech", presentation)

    def fact(self, *, long=False):
        from tests import test_contextual_fact_planning as contextual

        fixture = contextual.ContextualFactPlanningTest()
        fixture.runtime, fixture.facts = self.runtime, self.facts
        return fixture.pool(long=long)[1]

    def test_preview_is_pure_missing_language_and_bad_core_keep_exact_fallback(self):
        engine = self.runtime.DJMomentEngine()
        fact = self.fact()
        args = dict(
            selected_mood="neutral",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="nl",
            remaining_seconds=300,
        )
        first = engine.preview_qualified_fact(fact=fact, **args)
        self.assertEqual(first, engine.preview_qualified_fact(fact=fact, **args))
        self.assertEqual(engine._expression_forms, ())
        for core in (None, replace(fact.display_core, roles=(("producer", ("Invented name",)),))):
            fallback = engine.preview_qualified_fact(fact=replace(fact, display_core=core), **args)
            self.assertEqual((fallback.summary, fallback.content), fact.copy_for("nl"))
            self.assertEqual(fallback.expression_form, "")
        self.assertIsNone(engine.preview_qualified_fact(fact=fact, **{**args, "locale": "it"}))
        self.assertIsNone(engine.preview_qualified_fact(fact=replace(fact, source_url=""), **args))

    def test_final_text_fit_uses_faithful_short_fallback_through_runtime(self):
        from tests import test_contextual_fact_planning as contextual

        fixture = contextual.ContextualFactPlanningTest()
        fixture.runtime, fixture.facts = self.runtime, self.facts
        fact = self.fact(long=True)
        engine = self.runtime.DJMomentEngine()
        args = dict(selected_mood="neutral", persona=self.runtime.DJPersona.RADIO_DJ, locale="nl")
        full = engine.preview_qualified_fact(fact=fact, remaining_seconds=300, **args)
        original = fact.copy_for("nl")
        short_duration = self.runtime._presentation_intent(
            "neutral",
            args["persona"],
            reading_characters=sum(map(len, original)),
            minimum_duration_seconds=40,
        ).maximum_duration_seconds
        full_duration = self.runtime._presentation_intent(
            "neutral",
            args["persona"],
            reading_characters=len(full.summary) + len(full.content),
            minimum_duration_seconds=40,
        ).maximum_duration_seconds
        self.assertGreater(full_duration, short_duration)
        receipts, session = fixture.run_session(
            (fact,), duration=(short_duration + 5) * 1000, persona=args["persona"]
        )
        self.assertEqual(receipts[0]["content"], original[1])
        self.assertEqual(session.moment_engine._expression_forms, ())
        self.assertEqual(
            session.broadcast.state.dj_moments[0].presentation_intent.maximum_duration_seconds,
            short_duration,
        )
        receipts, session = fixture.run_session(
            (fact,), duration=(short_duration + 4) * 1000, persona=args["persona"]
        )
        self.assertEqual(receipts, [])
        self.assertEqual(session.moment_engine._expression_forms, ())

    def test_engine_rejects_forged_realization_and_does_not_expose_style_memory(self):
        fact = self.fact()
        engine = self.runtime.DJMomentEngine()
        args = dict(selected_mood="neutral", persona=self.runtime.DJPersona.HOME_DJ, locale="nl")
        preview = engine.preview_qualified_fact(fact=fact, remaining_seconds=300, **args)
        moment = engine.create_qualified_fact(
            session_id="session",
            intent=self.runtime.KnowledgeIntent(
                self.runtime.KnowledgeIntentType.TRACK_CONTEXT, "Qualified credit"
            ),
            fact=fact,
            realization=replace(preview, content="Invented collaboration"),
            **args,
        )
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.SILENCE)
        self.assertEqual(engine._expression_forms, ())
        self.assertNotIn("expression_form", moment.as_dict())
        self.assertNotIn("visual_only", moment.as_dict())

    def test_style_memory_commits_only_flow_publication_and_clears_at_end(self):
        self.run_sequence(self.runtime.DJPersona.FESTIVAL_DJ)
        engine = self.session.moment_engine
        self.assertEqual(len(engine._expression_forms), 4)
        flow = self.session.planner.output.session_flow
        moment = engine.moments[-1]
        before = engine._expression_forms
        engine.commit_expression(replace(moment, moment_id="unpublished"), flow)
        self.assertEqual(engine._expression_forms, before)
        engine.commit_expression(moment, flow)
        self.assertEqual(engine._expression_forms, before)
        self.run_sequence(self.runtime.DJPersona.FESTIVAL_DJ, count=8)
        engine = self.session.moment_engine
        self.assertEqual(len(engine._expression_forms), 6)
        self.assertEqual(len(engine._expression_moment_ids), 6)
        asyncio.run(
            self.manager.async_end(owner_profile_id="owner", session_id=self.session.session_id)
        )
        self.assertEqual(engine._expression_forms, ())

    def test_single_name_and_nonproducer_roles_remain_exact_in_every_authored_form(self):
        from custom_components.djconnect.moment_expression import realize

        catalog, _ = self.source_pair(0)
        fact = self.facts.recording_facts(
            catalog,
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "relations": [
                    {"type": role, "target-type": "artist", "artist": {"name": name}}
                    for role, name in (
                        ("producer", "Nora Vale"),
                        ("instrument", "Instrument Person"),
                        ("vocal", "Vocal Person"),
                    )
                ],
            },
        )[0]
        for locale in self.facts.LANGUAGES:
            for persona in self.runtime.DJPersona:
                for form in range(4):
                    summary, content = realize(
                        fact, locale=locale, persona=persona.value, form=form, mood="neutral"
                    )
                    for name in ("Nora Vale", "Instrument Person", "Vocal Person"):
                        self.assertEqual(content.count(name), 1)
                    self.assertNotIn("Nora Vale staan", content)
                    self.assertNotIn("stehen Nora Vale", content)
                    self.assertNotIn("aparecen Nora Vale", content)
                    self.assertNotIn("those names", content)
                    self.assertNotIn("die namen", content)

    def test_edition_date_precision_and_person_group_identity_remain_qualified(self):
        from custom_components.djconnect.moment_expression import realize

        catalog, _ = self.source_pair(0)
        for date, precision in (("2007", "year"), ("2007-05", "month"), ("2007-05-12", "day")):
            edition = self.facts.catalog_facts(
                {**catalog, "release_date": date, "release_date_precision": precision}
            )[0]
            for entity_type in ("Person", "Group"):
                begin = self.facts.artist_facts(
                    catalog,
                    {
                        "id": "00000000-0000-0000-0000-000000000009",
                        "name": "Source Artist",
                        "type": entity_type,
                        "life-span": {"begin": date},
                    },
                )[0]
                for locale in self.facts.LANGUAGES:
                    for persona in self.runtime.DJPersona:
                        for fact in (edition, begin):
                            copy = realize(
                                fact, locale=locale, persona=persona.value, form=0, mood="neutral"
                            )
                            self.assertIn(date, copy[1])
                            self.assertIn(fact.display_core.subject, copy[1])
                            self.assertTrue(fact.display_core.validates(fact))
                        self.assertIn(
                            "Spotify",
                            realize(
                                edition,
                                locale=locale,
                                persona=persona.value,
                                form=0,
                                mood="neutral",
                            )[1],
                        )

    def test_late_seek_pause_change_end_and_reconnect_do_not_advance_expression(self):
        for interrupt in ("paused", "seek", "change", "end"):
            self.run_sequence(self.runtime.DJPersona.HOME_DJ)

            async def scenario():
                manager, session = self.manager, self.session
                engine = session.moment_engine
                before = engine._expression_forms
                count = len(session.broadcast.state.dj_moments)
                session.broadcast.as_dict()
                self.assertEqual(engine._expression_forms, before)
                entered, release = asyncio.Event(), asyncio.Event()
                catalog, recording = self.source_pair(0)
                catalog = {**catalog, "uri": "spotify:track:" + "Z" * 22}
                facts = tuple(self.facts.recording_facts(catalog, recording))

                async def late():
                    entered.set()
                    await release.wait()
                    return {"_qualified_facts": facts}

                async def playback(state="playing", identity=None, position=0):
                    await manager.async_update_playback_projection(
                        owner_profile_id="owner",
                        session_id=session.session_id,
                        state=state,
                        media_identity=identity or catalog["uri"],
                        title=catalog["title"],
                        artist=catalog["artist"],
                        duration_ms=300000,
                        position_ms=position,
                    )

                await playback()
                task = asyncio.create_task(
                    manager.async_process_track_started(
                        owner_profile_id="owner",
                        session_id=session.session_id,
                        media_identity=catalog["uri"],
                        insight_provider=late,
                        require_current_playback=True,
                    )
                )
                await entered.wait()
                if interrupt == "end":
                    await manager.async_end(owner_profile_id="owner", session_id=session.session_id)
                else:
                    await playback(
                        state="paused" if interrupt == "paused" else "playing",
                        identity="spotify:track:" + "Y" * 22 if interrupt == "change" else None,
                        position=100000 if interrupt == "seek" else 0,
                    )
                release.set()
                self.assertIsNone(await task)
                self.assertEqual(engine._expression_forms, () if interrupt == "end" else before)
                self.assertEqual(len(session.broadcast.state.dj_moments), count)

            asyncio.run(scenario())
