"""Source-shaped fixtures through the real context Runtime/Flow/Broadcast."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import sys
import unittest
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module


FAMILIES = ("birth", "formation", "description", "edition", "genre")


class ExpressiveContextVariationTest(unittest.TestCase):
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

    def source(self, family, index, **kwargs):
        from tests.context_variation_fixtures import source

        return source(family, index, **kwargs)

    def run_sequence(self, family, persona, locale, *, count=2):
        async def scenario():
            manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: clock[0])
            session = await manager.async_start(
                owner_profile_id="context-owner",
                locale=locale,
                dj_persona=persona,
                selected_mood="neutral",
                music_backend="spotify_direct",
                elapsed_time_source=lambda: clock[0],
                session_start_strategy=self.runtime.SessionStartStrategy.MANUAL,
                allowed_capability_intents=None
                if family == "genre"
                else frozenset({"album_story" if family == "edition" else "artist_story"}),
            )
            snapshots, receipts, originals, memory = [], [], [], []
            for index in range(12 if family == "genre" else count):
                clock[0] = 100.0 + 300 * index
                stamp[0] = (base + timedelta(seconds=300 * index)).isoformat()
                catalog, source = self.source(family, index)
                originals.append(source if isinstance(source, dict) else source.copy_for(locale))
                await manager.async_update_playback_projection(
                    owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id,
                    state="playing",
                    media_identity=catalog["uri"],
                    title=catalog["title"],
                    artist=catalog["artist"],
                    album=catalog["album_name"],
                    duration_ms=300000,
                    position_ms=0,
                    artwork_url="/api/djconnect/v1/image_proxy/context-fixture",
                )

                async def provide():
                    return source if isinstance(source, dict) else {"_qualified_facts": (source,)}

                moment = await manager.async_process_track_started(
                    owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id,
                    media_identity=catalog["uri"],
                    insight_provider=provide,
                    require_current_playback=True,
                    allow_initial_facts=family != "genre",
                )
                receipts.append(moment.as_dict() if moment else None)
                snapshots.append(session.broadcast.as_dict())
                memory.append(list(session.moment_engine._expression_forms))
                if (
                    family == "genre"
                    and sum(bool(m and m["type"] == "genre") for m in receipts) >= count
                ):
                    break
            self.manager, self.session = (
                manager,
                await manager.async_get_active(session.owner_profile_id),
            )
            self.last_capture = {
                "simulator": True,
                "receipts": receipts,
                "snapshots": snapshots,
                "originals": originals,
                "memory": memory,
            }
            return receipts

        base = datetime.now(UTC)
        stamp, clock = [base.isoformat()], [100.0]
        with (
            patch.object(self.runtime, "_timestamp", lambda: stamp[0]),
            patch("time.monotonic", lambda: clock[0]),
        ):
            return asyncio.run(scenario())

    def test_whole_runtime_matrix_publishes_two_forms_without_extra_moments(self):
        for family in FAMILIES:
            for locale in self.facts.LANGUAGES:
                first_forms = []
                for persona in self.runtime.DJPersona:
                    with self.subTest(family=family, locale=locale, persona=persona):
                        receipts = self.run_sequence(family, persona, locale)
                        if family == "genre":
                            receipts = [m for m in receipts if m and m["type"] == "genre"]
                        self.assertTrue(all(receipts), receipts)
                        expected = (
                            "genre"
                            if family == "genre"
                            else "album"
                            if family == "edition"
                            else "artist"
                        )
                        self.assertEqual([m["type"] for m in receipts], [expected, expected])
                        self.assertEqual(
                            [key.rsplit(":", 1)[-1] for key in self.last_capture["memory"][-1]],
                            ["0", "1"],
                        )
                        published = [m for m in self.last_capture["receipts"] if m]
                        self.assertEqual(
                            len(
                                [
                                    item
                                    for item in self.session.planner.output.session_flow.items
                                    if item.moment_id
                                ]
                            ),
                            len(published),
                        )
                        self.assertEqual(
                            len(self.session.broadcast.state.dj_moments), len(published)
                        )
                        first_forms.append(receipts[0]["content"])
                        for index, moment in enumerate(receipts):
                            source = self.source(family, index)[1]
                            if family != "genre":
                                self.assertEqual(
                                    moment["source_attribution"]["url"], source.source_url
                                )
                                if family == "description":
                                    self.assertIn(source.copy_for(locale)[1], moment["content"])
                                else:
                                    self.assertIn(source.display_core.date, moment["content"])
                            self.assertLessEqual(
                                len(moment["summary"]) + len(moment["content"]), 1260
                            )
                self.assertEqual(len(set(first_forms)), 4)

    def test_preview_is_pure_exact_fallback_precision_and_missing_language(self):
        engine = self.runtime.DJMomentEngine()
        args = {
            "persona": self.runtime.DJPersona.HOME_DJ,
            "selected_mood": "neutral",
            "locale": "nl",
            "remaining_seconds": 300,
        }
        for family in FAMILIES[:-1]:
            for date, precision in (("1960", "year"), ("1960-03", "month"), ("1960-03-04", "day")):
                fact = self.source(family, 0, date=date, precision=precision)[1]
                first = engine.preview_qualified_fact(fact=fact, **args)
                self.assertEqual(first, engine.preview_qualified_fact(fact=fact, **args))
                self.assertEqual(engine._expression_forms, ())
                self.assertIsNone(
                    engine.preview_qualified_fact(fact=fact, **{**args, "locale": "it"})
                )
                self.assertIsNone(
                    engine.preview_qualified_fact(fact=fact, **{**args, "remaining_seconds": 10})
                )
                if family != "description":
                    for core in (None, replace(fact.display_core, date="invented")):
                        fallback = engine.preview_qualified_fact(
                            fact=replace(fact, display_core=core), **args
                        )
                        self.assertEqual((fallback.summary, fallback.content), fact.copy_for("nl"))
                        self.assertEqual(fallback.expression_form, "")

    def test_bounded_memory_only_publication_and_end_clears(self):
        self.run_sequence("edition", self.runtime.DJPersona.HOME_DJ, "nl", count=8)
        engine = self.session.moment_engine
        self.assertEqual(len(engine._expression_forms), 6)
        moment = engine.moments[-1]
        before = engine._expression_forms
        engine.commit_expression(moment, self.session.planner.output.session_flow)
        self.assertEqual(engine._expression_forms, before)
        engine.commit_expression(
            replace(moment, moment_id="never-published"), self.session.planner.output.session_flow
        )
        self.assertEqual(engine._expression_forms, before)
        asyncio.run(
            self.manager.async_end(
                owner_profile_id=self.session.owner_profile_id, session_id=self.session.session_id
            )
        )
        self.assertEqual(engine._expression_forms, ())

    def test_later_genre_exact_short_fallback_publishes_at_remaining_boundary(self):
        async def scenario():
            clock = [100.0]
            manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: clock[0])
            session = await manager.async_start(
                owner_profile_id="genre-boundary",
                locale="en",
                dj_persona=self.runtime.DJPersona.HOME_DJ,
                selected_mood="neutral",
                elapsed_time_source=lambda: clock[0],
            )
            title, artist, genre = "T" * 160, "A" * 160, "G" * 160

            async def provide():
                return {
                    "track": {
                        "title": title,
                        "artist": artist,
                        "album": "Edition",
                        "producer": "Named producer",
                        "genres": [genre],
                    },
                    "analysis": {
                        "summary": "Qualified existing context.",
                        "full_text": "Existing narrative context.",
                        "genre": genre,
                    },
                }

            for identity in ("spotify:track:" + "0" * 22, "spotify:track:" + "1" * 22):
                clock[0] += 300
                await manager.async_update_playback_projection(
                    owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id,
                    state="playing",
                    media_identity=identity,
                    title=title,
                    artist=artist,
                    duration_ms=300000,
                    position_ms=0,
                )
                first = await manager.async_process_track_started(
                    owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id,
                    media_identity=identity,
                    insight_provider=provide,
                    require_current_playback=True,
                )
            self.assertEqual(first.moment_type, self.runtime.DJMomentType.ARTIST)
            clock[0] += 246
            await manager.async_update_playback_projection(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                state="playing",
                media_identity=identity,
                title=title,
                artist=artist,
                duration_ms=300000,
                position_ms=246000,
            )
            later = await manager.async_maybe_publish_intra_track_moment(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                media_identity=identity,
            )
            self.assertIsNotNone(later)
            self.assertEqual(later.moment_type, self.runtime.DJMomentType.GENRE)
            original = self.runtime._genre_moment_copy("en", genre, title, artist)
            self.assertEqual((later.summary, later.content), original)
            self.assertEqual(later.presentation_intent.maximum_duration_seconds, 49)
            self.assertEqual(later.expression_form, "")
            self.assertEqual(session.moment_engine._expression_forms, ())
            self.assertIn(
                later.moment_id, [m.moment_id for m in session.broadcast.state.dj_moments]
            )

        asyncio.run(scenario())

    def test_missing_descriptor_translation_and_persona_family_interleaving(self):
        engine = self.runtime.DJMomentEngine()
        _, fact = self.source("description", 0)
        missing = replace(
            fact, contents=tuple((lang, text) for lang, text in fact.contents if lang != "nl")
        )
        args = dict(
            selected_mood="neutral",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="nl",
            remaining_seconds=300,
        )
        self.assertIsNone(engine.preview_qualified_fact(fact=missing, **args))
        self.run_sequence("birth", self.runtime.DJPersona.HOME_DJ, "nl")
        engine = self.session.moment_engine
        self.assertEqual(
            engine.next_expression_form(self.runtime.DJPersona.HOME_DJ, "artist_begin"), 0
        )
        self.assertEqual(
            engine.next_expression_form(self.runtime.DJPersona.RADIO_DJ, "artist_begin"), 0
        )
        self.assertEqual(
            engine.next_expression_form(self.runtime.DJPersona.HOME_DJ, "album_release"), 0
        )
        self.assertEqual(
            engine._expression_forms, ("home_dj:artist_begin:0", "home_dj:artist_begin:1")
        )

    def test_failed_fact_publication_keeps_candidate_and_style_unconsumed(self):
        async def scenario():
            manager = self.runtime.SessionRuntimeManager()
            session = await manager.async_start(owner_profile_id="publication-failure", locale="nl")
            catalog, fact = self.source("edition", 0)
            await manager.async_update_playback_projection(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                state="playing",
                media_identity=catalog["uri"],
                title=catalog["title"],
                artist=catalog["artist"],
                duration_ms=300000,
                position_ms=0,
            )

            async def provide():
                return {"_qualified_facts": (fact,)}

            with patch.object(
                self.runtime.PresentationComposer,
                "compose_with_diagnostics",
                side_effect=RuntimeError("synthetic publication failure"),
            ):
                with self.assertRaises(RuntimeError):
                    await manager.async_process_track_started(
                        owner_profile_id=session.owner_profile_id,
                        session_id=session.session_id,
                        media_identity=catalog["uri"],
                        insight_provider=provide,
                        require_current_playback=True,
                        allow_initial_facts=True,
                    )
            self.assertEqual(session.moment_engine._track_keys, set())
            self.assertEqual(session.moment_engine._expression_forms, ())
            self.assertEqual(session.broadcast.state.dj_moments, ())
            self.assertEqual(session.moment_engine.moments, ())
            recovered = await manager.async_maybe_publish_intra_track_moment(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                media_identity=catalog["uri"],
            )
            self.assertIsNotNone(recovered)
            self.assertEqual(recovered.moment_type, self.runtime.DJMomentType.ALBUM)
            self.assertEqual(len(session.moment_engine._expression_forms), 1)

        asyncio.run(scenario())
