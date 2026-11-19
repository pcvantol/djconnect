"""Published Album -> exact current edition through canonical Runtime."""
import asyncio
from dataclasses import replace
import sys
import time
import unittest
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module


class NarrativeAlbumContinuityTest(unittest.TestCase):
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

    def catalog(self, number=0, **changes):
        return {"uri": "spotify:track:" + chr(65 + number) * 22,
                "title": f"Current track {number}", "artist": "Catalog artist",
                "album_name": "Exact edition", "album_uri": "spotify:album:" + "Z" * 22,
                "release_date": "2001-03-04", "release_date_precision": "day", **changes}

    def pool(self, number=0, **changes):
        return tuple(self.facts.catalog_facts(self.catalog(number, **changes)))

    async def start(self, *, mode="balanced", locale="nl", persona=None, discover=True):
        self.clock = [100.0]
        self.manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: self.clock[0])
        session = await self.manager.async_start(owner_profile_id="owner", locale=locale,
            music_backend="spotify_direct", dj_persona=persona or self.runtime.DJPersona.HOME_DJ,
            session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER
                if discover else self.runtime.SessionStartStrategy.MANUAL)
        session = replace(session, session_direction=replace(session.session_direction,
            direction=self.runtime.SessionDirectionType.EXPLORING), selected_presence=mode)
        session.broadcast.state = replace(session.broadcast.state, selected_presence=mode)
        self.manager._active_by_profile["owner"] = session
        self.session = session
        return session

    async def track(self, number, facts=None, *, duration=300000, position=0):
        self.clock[0] += 200
        session = await self.manager.async_get_active("owner")
        catalog = self.catalog(number)
        await self.manager.async_update_playback_projection(owner_profile_id="owner",
            session_id=session.session_id, state="playing", media_identity=catalog["uri"],
            title=catalog["title"], artist=catalog["artist"], album=catalog["album_name"],
            duration_ms=duration, position_ms=position)
        async def provider():
            return {"_qualified_facts": self.pool(number) if facts is None else facts}
        return await self.manager.async_process_track_started(owner_profile_id="owner",
            session_id=session.session_id, media_identity=catalog["uri"], insight_provider=provider,
            require_current_playback=True, allow_initial_facts=True)

    def test_published_album_then_exact_edition_track_for_four_personas_five_languages(self):
        async def scenario():
            for locale in self.facts.LANGUAGES:
                copies = []
                for persona in self.runtime.DJPersona:
                    await self.start(locale=locale, persona=persona)
                    a = await self.track(0)
                    self.assertEqual(a.moment_type.value, "album")
                    frozen = a.as_dict()
                    from custom_components.djconnect import session_speech
                    from tests.speech_capture import capture
                    first_speech = session_speech.moment_projection(self.session.broadcast, a)
                    self.assertTrue(first_speech['manual_allowed'])
                    b = await self.track(1)
                    self.assertEqual(b.moment_type.value, "track")
                    self.assertIsInstance(b.source_fact, self.facts.AlbumContinuityFact)
                    self.assertEqual(b.source_fact.current_album.contents, self.pool(1)[0].contents)
                    dates = {"en": "4 March 2001", "nl": "4 maart 2001", "de": "4. März 2001",
                             "fr": "4 mars 2001", "es": "4 de marzo de 2001"}
                    self.assertIn("Exact edition", b.content)
                    self.assertIn(dates[locale], b.content)
                    self.assertIn("Spotify", b.content)
                    self.assertEqual(dict(b.source_attribution)["url"], self.pool(1)[0].source_url)
                    self.assertEqual(a.as_dict(), frozen)
                    self.assertEqual(len(self.session.published_album_context.used_relations), 1)
                    self.assertIn(b.moment_id, [i.moment_id for i in self.session.planner.output.session_flow.items])
                    native = self.session.broadcast.native_delivery()
                    delivery = next(x for x in native["admissions"] if x["moment_id"] == b.moment_id)
                    self.assertTrue(delivery["current_display_allowed"])
                    self.assertFalse(delivery["active_flow_display_allowed"])
                    self.assertTrue(delivery["requires_spotify_attribution"])
                    speech = session_speech.moment_projection(self.session.broadcast, b)
                    self.assertTrue(speech['manual_allowed'], speech)
                    self.assertEqual(''.join(p['text'] for p in speech['segments']), b.content)
                    self.assertEqual(speech['attribution'], [dict(b.source_attribution)])
                    capture('album-continuity-speech', {'locale': locale, 'persona': persona.value,
                        'sequence': [a.as_dict(), b.as_dict()], 'speech': [first_speech, speech],
                        'scope': 'Actual published Runtime/Planner album relation, elapsed fixture; same private speech descriptor; no native synthesis claim.'})
                    copies.append(b.content)
                self.assertEqual(len(set(copies)), 4)
        asyncio.run(scenario())

    def test_exact_identity_expiry_and_unpublished_predecessor_fail_closed(self):
        async def scenario():
            for changes in ({"album_uri": "spotify:album:" + "Y"*22},
                            {"album_uri": ""}, {"release_date": "2002-03-04"},
                            {"release_date_precision": "year", "release_date": "2001"},
                            {"album_name": "Conflicting name"}):
                await self.start()
                await self.track(0)
                b = await self.track(1, self.pool(1, **changes))
                self.assertFalse(b and isinstance(b.source_fact, self.facts.AlbumContinuityFact))
            for first in ((), (replace(self.pool(0)[0], observed_at=time.monotonic()-1801),)):
                await self.start()
                await self.track(0, first)
                b = await self.track(1)
                self.assertFalse(b and isinstance(b.source_fact, self.facts.AlbumContinuityFact))
            await self.start()
            await self.track(0, duration=44000)
            self.assertFalse(self.session.published_album_context.albums)
            b = await self.track(1)
            self.assertFalse(b and isinstance(b.source_fact, self.facts.AlbumContinuityFact))
            await self.start()
            await self.track(0)
            self.session.published_album_context.albums[self.catalog(0)["uri"]] = replace(
                self.pool(0)[0], observed_at=time.monotonic()-1801)
            b = await self.track(1)
            self.assertFalse(b and isinstance(b.source_fact, self.facts.AlbumContinuityFact))
        asyncio.run(scenario())

    def test_off_noop_reconnect_and_session_end_do_not_reset_relation_guards(self):
        async def scenario():
            await self.start()
            await self.track(0)
            await self.track(1)
            used = self.session.published_album_context.used_relations.copy()
            budget = self.session.presence_ledger.total_published
            for mode in ("balanced", "music_only", "presenter"):
                self.session = await self.manager.async_update_presence(owner_profile_id="owner",
                    session_id=self.session.session_id, selected_presence=mode)
            self.assertEqual(self.session.published_album_context.used_relations, used)
            self.assertEqual(self.session.presence_ledger.total_published, budget)
            self.assertFalse(self.session.published_album_context.albums)
            self.session.broadcast.as_dict()
            self.session.broadcast.native_delivery()
            b = await self.track(0)
            self.assertFalse(b and isinstance(b.source_fact, self.facts.AlbumContinuityFact))
            await self.manager.async_end(owner_profile_id="owner", session_id=self.session.session_id)
            self.assertFalse(self.session.published_album_context.used_relations)
            await self.start(mode="music_only")
            self.assertIsNone(await self.track(0))
            self.assertIsNone(await self.track(1))
            self.assertEqual(self.session.presence_ledger.total_published, 0)
            self.assertFalse(self.session.published_album_context.albums)
        asyncio.run(scenario())

    def test_failed_publication_leaves_relation_and_engine_unconsumed(self):
        async def scenario():
            await self.start()
            await self.track(0)
            engine_keys = self.session.moment_engine._track_keys.copy()
            with patch.object(self.runtime.DJSessionRuntime, "publish_moment", side_effect=RuntimeError("failure")):
                with self.assertRaisesRegex(RuntimeError, "failure"):
                    await self.track(1)
            self.assertFalse(self.session.published_album_context.used_relations)
            self.assertEqual(self.session.moment_engine._track_keys, engine_keys)
            catalog = self.catalog(1)
            b = await self.manager.async_maybe_publish_intra_track_moment(owner_profile_id="owner",
                session_id=self.session.session_id, media_identity=catalog["uri"])
            self.assertIsInstance(b.source_fact, self.facts.AlbumContinuityFact)
            self.assertEqual(len(self.session.published_album_context.used_relations), 1)
        asyncio.run(scenario())

    def test_closed_derived_fact_and_memory_saturation(self):
        state = self.facts.PublishedAlbumContext()
        previous = self.pool(0)[0]
        current = self.pool(1)[0]
        now = time.monotonic()
        state.observe(previous.media_identity, now)
        state.commit(previous, now)
        state.observe(current.media_identity, now)
        fact = state.candidate((current,), current.media_identity, now)
        self.assertTrue(fact.eligible(current.media_identity, now))
        for changes in ({"key": "album_release"}, {"provider": "MusicBrainz"},
                        {"observed_at": now-1801}, {"contents": current.contents},
                        {"previous_album": current}, {"source_url": "https://example.com"}):
            self.assertFalse(replace(fact, **changes).eligible(current.media_identity, now))
        self.assertIsNone(state.candidate((current, replace(current, observed_at=now-1)),
                                         current.media_identity, now))
        from custom_components.djconnect.native_moment_delivery import source_deadline
        earlier = replace(previous, observed_at=now-1790)
        old = replace(fact, previous_album=earlier)
        self.assertEqual(source_deadline(old), earlier.observed_at+1800)
        self.assertFalse(old.eligible(current.media_identity, now+11))
        state.commit(fact, now)
        self.assertIsNone(state.candidate((current,), current.media_identity, now))
        state.used_relations.update((str(i), str(i+1), previous.source_url) for i in range(5))
        self.assertEqual(len(state.used_relations), 6)
        for number in range(2, 12):
            state.observe(self.catalog(number)["uri"], now)
            state.commit(self.pool(number)[0], time.monotonic())
            self.assertIsNone(state.candidate(self.pool(number), self.catalog(number)["uri"], now))
        self.assertLessEqual(len(state.observed_tracks), 3)
        self.assertLessEqual(len(state.albums), 3)
        self.assertEqual(len(state.used_relations), 6)


    def test_failed_album_publication_cannot_open_line(self):
        async def scenario():
            await self.start()
            with patch.object(self.runtime.DJSessionRuntime, "publish_moment", side_effect=RuntimeError("failure")):
                with self.assertRaisesRegex(RuntimeError, "failure"):
                    await self.track(0)
            self.assertFalse(self.session.published_album_context.albums)
            b=await self.track(1)
            self.assertFalse(b and isinstance(b.source_fact,self.facts.AlbumContinuityFact))
        asyncio.run(scenario())

    def test_real_planner_closure_survives_return_scope_before_fact_selection(self):
        async def scenario():
            await self.start()
            await self.track(0)
            self.assertTrue(self.session.published_album_context.albums)
            active=await self.manager.async_update_mood(owner_profile_id="owner",
                session_id=self.session.session_id,selected_mood="deep")
            await self.manager._apply_legacy_initial_track_started_decision("owner",active)
            current=await self.manager.async_get_active("owner")
            self.assertIs(current.session_direction.direction,self.runtime.SessionDirectionType.DEEPENING)
            self.assertFalse(current.published_album_context.albums)
            # Controlled return-scope fixture: the real Planner's recent-session
            # dosing deliberately prevents an immediate second direction card.
            current=replace(current,session_direction=replace(current.session_direction,
                direction=self.runtime.SessionDirectionType.EXPLORING))
            self.manager._active_by_profile["owner"]=current
            b=await self.track(1)
            self.assertFalse(b and isinstance(b.source_fact,self.facts.AlbumContinuityFact))
        asyncio.run(scenario())

    def test_future_mood_persona_preserve_old_fact_and_budget(self):
        async def scenario():
            await self.start()
            a=await self.track(0)
            frozen=a.as_dict()
            budget=self.session.presence_ledger.total_published
            await self.manager.async_update_mood(owner_profile_id="owner",
                session_id=self.session.session_id,selected_mood="chill")
            await self.manager.async_update_persona(owner_profile_id="owner",
                session_id=self.session.session_id,dj_persona=self.runtime.DJPersona.CLUB_DJ)
            self.assertEqual(self.session.presence_ledger.total_published,budget)
            b=await self.track(1)
            self.assertIsInstance(b.source_fact,self.facts.AlbumContinuityFact)
            self.assertTrue(b.content.startswith("Dezelfde uitgave, een ander nummer."))
            self.assertEqual(a.as_dict(),frozen)
        asyncio.run(scenario())


    def test_album_outside_exploring_cannot_seed_future_return(self):
        async def scenario():
            await self.start()
            current=replace(self.session, session_direction=replace(self.session.session_direction,
                direction=self.runtime.SessionDirectionType.BUILDING_ENERGY))
            self.manager._active_by_profile["owner"]=current
            a=await self.track(0)
            self.assertEqual(a.moment_type.value,"album")
            self.assertFalse(current.published_album_context.albums)
            active=await self.manager.async_get_active("owner")
            # Controlled scope-return input; the first actual publication used
            # the normal Runtime/Planner/Knowledge/Moment/Flow/Broadcast chain.
            self.manager._active_by_profile["owner"]=replace(active,
                session_direction=replace(active.session_direction,
                    direction=self.runtime.SessionDirectionType.EXPLORING))
            b=await self.track(1)
            self.assertFalse(b and isinstance(b.source_fact,self.facts.AlbumContinuityFact))
        asyncio.run(scenario())
