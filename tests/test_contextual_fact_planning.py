"""Policy acceptance through current playback → Runtime → Flow/Broadcast."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import itertools
import sys
import unittest
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module
from tests import test_session_facts as source_tests


class ContextualFactPlanningTest(unittest.TestCase):
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

    def pool(self, long=False):
        catalog = source_tests.SessionFactsTest.catalog(self)
        album = self.facts.catalog_facts(catalog)[0]
        recording = self.facts.recording_facts(catalog, {
            "id": "00000000-0000-0000-0000-000000000001",
            "relations": [{"type": "producer", "target-type": "artist",
                           "artist": {"name": ("Producer " + "x" * 145) if long else "Test producer"}}],
        })[0]
        # Long legitimate multi-role recording copy, following producer schema.
        if long:
            recording = self.facts.recording_facts(catalog, {
                "id": "00000000-0000-0000-0000-000000000001",
                "relations": [{"type": role, "target-type": "artist", "artist": {"name": "Producer " + str(index) + "x" * 95}}
                              for role in ("producer", "instrument", "vocal") for index in range(2)],
            })[0]
        artist = self.facts.artist_facts(catalog, {
            "id": "00000000-0000-0000-0000-000000000002", "name": catalog["artist"],
            "type": "Person", "life-span": {"begin": "1960-01-02"},
        })[0]
        return album, recording, artist

    def run_session(self, facts, *, discover=False, mood="neutral", positions=(0,), duration=300000,
                    persona=None, allowed=None, direction=None, durations=None, locale="nl"):
        async def scenario():
            now = [100.0]
            manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: now[0])
            args = {"owner_profile_id": "owner", "locale": locale, "selected_mood": mood,
                    "music_backend": "spotify_direct", "session_start_strategy":
                        self.runtime.SessionStartStrategy.DISCOVER if discover else self.runtime.SessionStartStrategy.MANUAL}
            if persona is not None:
                args["dj_persona"] = persona
            args["allowed_capability_intents"] = allowed
            session = await manager.async_start(**args)
            if direction is not None:
                session = replace(session, session_direction=replace(session.session_direction, direction=direction))
                manager._active_by_profile["owner"] = session
            catalog = source_tests.SessionFactsTest.catalog(self)
            receipts = []
            snapshots = []
            async def insight():
                return {"_qualified_facts": facts}
            for index, position in enumerate(positions):
                now[0] = 100 + position / 1000
                stamp[0] = (start + timedelta(milliseconds=position)).isoformat()
                await manager.async_update_playback_projection(
                    owner_profile_id="owner", session_id=session.session_id, state="playing",
                    media_identity=catalog["uri"], title=catalog["title"], artist=catalog["artist"],
                    album=catalog["album_name"], duration_ms=durations[index] if durations else duration, position_ms=position,
                )
                if index == 0:
                    moment = await manager.async_process_track_started(
                        owner_profile_id="owner", session_id=session.session_id, media_identity=catalog["uri"],
                        insight_provider=insight, require_current_playback=True, allow_initial_facts=True,
                    )
                else:
                    moment = await manager.async_maybe_publish_intra_track_moment(
                        owner_profile_id="owner", session_id=session.session_id, media_identity=catalog["uri"],
                    )
                if moment:
                    receipts.append({"position_ms": position, "type": moment.moment_type.value,
                                     "content": moment.content, "reason": session.planner.last_decision.reason,
                                     "source_url":dict(moment.source_attribution).get("url")})
                    snapshots.append(session.broadcast.as_dict())
            flow = [i.moment_id for i in session.planner.output.session_flow.items if i.moment_id]
            broadcast = [m.moment_id for m in session.broadcast.state.dj_moments]
            self.assertEqual(flow, broadcast)
            self.assertEqual(len(receipts), len(flow))
            self.last_capture = {"simulator": True, "source": "Existing producer schemas → real Core Runtime → Flow → Broadcast",
                                 "receipts": receipts, "snapshots": snapshots, "after": session.broadcast.as_dict()}
            return receipts, await manager.async_get_active("owner")
        start = datetime.now(UTC)
        stamp = [start.isoformat()]
        with patch.object(self.runtime, "_timestamp", lambda: stamp[0]):
            return asyncio.run(scenario())

    def test_source_order_is_irrelevant_and_context_changes_real_moment_sequence(self):
        pool = self.pool()
        choices = [self.run_session(tuple(p))[0][0]["content"] for p in itertools.permutations(pool)]
        self.assertEqual(len(set(choices)), 1)
        manual, _ = self.run_session(pool, positions=(0, 15000, 30000, 45000, 60000, 75000, 90000))
        self.assertEqual([m["type"] for m in manual], ["track", "album", "artist"])
        discover, _ = self.run_session(pool, discover=True, positions=(0, 15000, 30000, 45000, 60000, 75000, 90000))
        self.assertEqual([m["type"] for m in discover], ["artist", "album", "track"])
        # The new selected persona slice may realize the same immutable fact
        # differently by actual published position; selection/source stays equal.
        self.assertEqual({m["source_url"] for m in manual}, {m["source_url"] for m in discover})
        self.assertTrue(all(m["reason"].startswith("contextual_fact:") for m in discover))

    def test_long_candidate_does_not_block_short_fact_or_consume_rejected_angle(self):
        album, recording, artist = self.pool(long=True)
        receipts, session = self.run_session((recording, album, artist), positions=(0,), duration=50000)
        self.assertEqual(len(receipts), 1)
        self.assertNotEqual(receipts[0]["type"], "track")
        self.assertNotIn(f"{recording.source_url}|fact:{recording.key}", session.moment_engine._track_keys)
        receipts, _ = self.run_session((recording, album, artist), duration=44000)
        self.assertEqual(receipts, [])

    def test_calm_and_club_context_bound_spacing_preserves_qualified_anchors(self):
        pool = self.pool()
        neutral, _ = self.run_session(pool, positions=(0, 15000, 30000, 45000, 50000))
        calm, _ = self.run_session(pool, mood="chill", positions=(0, 15000, 30000, 45000, 50000))
        club, _ = self.run_session(pool, persona=self.runtime.DJPersona.CLUB_DJ,
                                   positions=(0, 15000, 30000, 45000, 50000))
        self.assertEqual(neutral[1]["position_ms"], 45000)
        self.assertEqual(calm[1]["position_ms"], 50000)
        self.assertEqual(club[1]["position_ms"], 50000)
        anchors={"track":("Test producer",), "album":("Test edition","2001-03-04"),
                 "artist":("Test artist","1960-01-02")}
        for moment in neutral+calm+club:
            self.assertTrue(all(anchor in moment["content"] for anchor in anchors[moment["type"]]))

    def test_eligibility_precedes_discover_relevance(self):
        album, _, artist = self.pool()
        invalid = (replace(artist, license="Spotify metadata display"),
                   replace(artist, observed_at=artist.observed_at - 1801),
                   replace(artist, media_identity="spotify:track:" + "Z" * 22),
                   replace(artist, contents=(("en", "English only"),)),
                   replace(artist, source_url="https://unqualified.example/artist"),
                   replace(artist, intent="unknown"))
        for fact in invalid:
            with self.subTest(fact=fact):
                receipts, _ = self.run_session((fact, album), discover=True)
                self.assertEqual(receipts[0]["type"], "album")
        receipts, _ = self.run_session((artist, album), discover=True, allowed=frozenset({"album_story"}))
        self.assertEqual(receipts[0]["type"], "album")

    def test_recent_delivered_type_demotes_another_unused_angle(self):
        album, recording, artist = self.pool()
        catalog = source_tests.SessionFactsTest.catalog(self)
        work = self.facts.work_facts(catalog, {"relations": [{"type": "performance", "target-type": "work", "work": {
            "id": "00000000-0000-0000-0000-000000000003",
            "relations": [{"type": "composer", "target-type": "artist", "artist": {"name": "Test composer"}}],
        }}]})[0]
        receipts, session = self.run_session((work, recording, artist, album),
                                             positions=(0, 15000, 30000, 45000, 60000, 75000, 90000, 105000, 120000, 135000))
        self.assertEqual([r["type"] for r in receipts], ["track", "album", "track", "artist"])
        self.assertEqual(len(session.performance_memory.recent_moment_ids), 4)
        # Without recent committed type demotion, both track angles outrank album.
        with patch.object(self.runtime, "_recent_factual_moment_type", lambda memory: None):
            without_memory, _ = self.run_session((work, recording, artist, album),
                                                 positions=(0, 15000, 30000, 45000))
        self.assertEqual([r["type"] for r in without_memory], ["track", "track"])
        # Rejected readability choices enter neither used state nor Flow memory.
        empty, rejected = self.run_session((recording,), duration=44000)
        self.assertEqual(empty, [])
        self.assertEqual(rejected.performance_memory.recent_moment_ids, ())
        self.assertEqual(rejected.moment_engine._track_keys, set())

    def test_direction_only_changes_choice_and_all_five_locale_anchors_stay_exact(self):
        pool = self.pool()
        manual, _ = self.run_session(pool)
        exploring, _ = self.run_session(pool, direction=self.runtime.SessionDirectionType.EXPLORING)
        self.assertEqual(manual[0]["type"], "track")
        self.assertEqual(exploring[0]["type"], "artist")
        for locale in self.facts.LANGUAGES:
            receipts, _ = self.run_session(pool, discover=True, locale=locale)
            self.assertIn("Test artist",receipts[0]["content"])
            self.assertIn("1960-01-02",receipts[0]["content"])
            self.assertEqual(receipts[0]["source_url"],pool[2].source_url)
