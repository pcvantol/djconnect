"""Two independently sourced recordings through the real Runtime ingress."""
import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import sys
import unittest
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module
from tests import test_session_facts as source_tests


class SharedProducerContinuityTest(unittest.TestCase):
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

    def catalog(self, number):
        return {**source_tests.SessionFactsTest.catalog(self), "uri": "spotify:track:" + chr(65+number)*22,
                "title": f"Recording {number}", "artist": f"Artist {number}"}

    def recording(self, number, *, ids=(9, 8), role="producer", attributes=None, names=None):
        return {"id": f"00000000-0000-0000-0000-{number+1:012d}",
                "title": f"Recording {number}",
                "artist-credit": [{"artist": {"name": f"Artist {number}"}}],
                "relations": [{"type": role, "target-type": "artist",
                    "attributes": attributes or [], "artist": {
                        "id": f"00000000-0000-0000-0000-{i:012d}",
                        "name": names[index] if names else f"Producer {i}"}}
                    for index, i in enumerate(ids)]}

    def pool(self, number, **kwargs):
        return tuple(self.facts.recording_facts(self.catalog(number), self.recording(number, **kwargs)))

    def run_pair(self, *, locale="nl", discover=True, second=None, first=None,
                 first_duration=300000, second_duration=300000, restart=False):
        async def scenario():
            now = [100.0]
            manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: now[0])
            async def start():
                return await manager.async_start(owner_profile_id="owner", locale=locale,
                    music_backend="spotify_direct", session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER
                    if discover else self.runtime.SessionStartStrategy.MANUAL)
            session = await start()
            session = replace(session, session_direction=replace(session.session_direction,
                direction=self.runtime.SessionDirectionType.EXPLORING))
            manager._active_by_profile["owner"] = session
            snapshots, moments = [], []
            for number in (0, 1):
                if number and restart:
                    await manager.async_end(owner_profile_id="owner", session_id=session.session_id)
                    session = await start()
                now[0] += 15
                stamp[0] = (base + timedelta(seconds=15*number)).isoformat()
                catalog = self.catalog(number)
                await manager.async_update_playback_projection(owner_profile_id="owner", session_id=session.session_id,
                    state="playing", media_identity=catalog["uri"], title=catalog["title"], artist=catalog["artist"],
                    album=catalog["album_name"], artwork_url="/api/djconnect/v1/image_proxy/software-art",
                    duration_ms=second_duration if number else first_duration, position_ms=0)
                async def source():
                    return {"_qualified_facts": (second if second is not None else self.pool(1)) if number
                            else (first if first is not None else self.pool(0))}
                moment = await manager.async_process_track_started(owner_profile_id="owner", session_id=session.session_id,
                    media_identity=catalog["uri"], insight_provider=source, require_current_playback=True, allow_initial_facts=True)
                moments.append(moment)
                snapshots.append(session.broadcast.as_dict())
            self.last_capture = {"snapshots": snapshots, "receipts": [m.as_dict() if m else None for m in moments]}
            self.manager, self.session = manager, await manager.async_get_active("owner")
            return moments
        base = datetime.now(UTC)
        stamp = [base.isoformat()]
        with patch.object(self.runtime, "_timestamp", lambda: stamp[0]):
            return asyncio.run(scenario())

    def test_two_recordings_publish_new_relation_and_two_sources_in_five_languages(self):
        for locale in self.facts.LANGUAGES:
            a, b = self.run_pair(locale=locale)
            self.assertEqual(b.moment_type.value, "track")
            self.assertIn("Recording 0", b.content)
            self.assertIn("Recording 1", b.content)
            self.assertIn("Producer 8", b.content)
            self.assertIn("url_previous", dict(b.source_attribution))
            self.assertNotEqual(a.content, b.content)

    def test_producer_choice_is_stable_under_source_order(self):
        _, a = self.run_pair(second=self.pool(1, ids=(8, 9)))
        _, b = self.run_pair(second=self.pool(1, ids=(9, 8)))
        self.assertEqual(a.content, b.content)
        self.assertIn("Producer 8", b.content)

    def test_unpublished_previous_and_new_session_never_connect(self):
        for args in ({"first_duration":44000}, {"restart":True}, {"first":()}, {"discover":False}):
            _, b = self.run_pair(**args)
            self.assertNotIn("Recording 0", b.content)

    def test_wrong_ids_roles_attributes_labels_sources_and_same_recording_never_connect(self):
        valid = self.pool(1)[0]
        cases = [self.pool(1, ids=(7,), names=("Producer 8",)), self.pool(1, role="vocal"),
                 self.pool(1, attributes=["executive"]), self.pool(1, names=("Conflict", "Conflict")),
                 (replace(valid, source_url=""),), (replace(valid, observed_at=valid.observed_at-1801),)]
        same = self.facts.recording_facts(self.catalog(1), {**self.recording(1), "id":self.recording(0)["id"]})
        cases.append(tuple(same))
        for second in cases:
            _, b = self.run_pair(second=second)
            self.assertTrue(b is None or "Recording 0" not in b.content)

    def test_expired_previous_conflicting_identity_and_restricted_roles(self):
        first = self.pool(0)[0]
        _, b = self.run_pair(first=(replace(first, observed_at=first.observed_at-1801),))
        self.assertNotIn("Recording 0", b.content)
        for modification in ({"title":"Different mix"}, {"artist-credit":[]},
                             {"id":"invalid"}):
            recording = {**self.recording(1), **modification}
            facts = tuple(self.facts.recording_facts(self.catalog(1), recording))
            _, b = self.run_pair(second=facts)
            self.assertTrue(b is None or "Recording 0" not in b.content)
        for role in ("composer", "instrument", "vocal"):
            _, b = self.run_pair(second=self.pool(1, role=role))
            self.assertTrue(b is None or "Recording 0" not in b.content)
        for attribute in ("executive", "additional", "co", "unknown"):
            _, b = self.run_pair(second=self.pool(1, attributes=[attribute]))
            self.assertTrue(b is None or "Recording 0" not in b.content)
        recording = self.recording(1)
        recording["relations"].append({**recording["relations"][1], "artist": {
            **recording["relations"][1]["artist"], "name":"Conflicting label"}})
        facts = tuple(self.facts.recording_facts(self.catalog(1), recording))
        _, b = self.run_pair(second=facts)
        self.assertIn("Producer 9", b.content)
        self.assertNotIn("Producer 8", b.content)

    def test_restricted_or_ended_producer_not_widened_in_ordinary_copy(self):
        for restriction in ({"attributes":["executive"]}, {"attributes":["additional"]},
                            {"ended":True}, {"attribute-values":{"executive":"yes"}}):
            recording = self.recording(0, ids=(8,))
            recording["relations"][0].update(restriction)
            recording["relations"].append({"type":"vocal", "target-type":"artist", "artist":{"name":"Singer"}})
            fact = self.facts.recording_facts(self.catalog(0), recording)[0]
            for _, body in fact.contents:
                self.assertNotIn("Producer 8", body)
                self.assertIn("Singer", body)
            self.assertIsNone(fact.recording_evidence)

    def test_readfit_gates_commit_and_end_disposes_even_retained_runtime(self):
        _, b = self.run_pair(second_duration=44000)
        self.assertIsNone(b)
        state = self.session.published_recording_context
        self.assertEqual(state.used_relations, set())
        self.assertEqual(set(state.credits), {self.catalog(0)["uri"]})
        async def finish():
            ended = await self.manager.async_end(owner_profile_id="owner", session_id=self.session.session_id)
            self.assertEqual(state.credits, {})
            self.assertEqual(ended.published_recording_context.observed_tracks, [])
            self.assertEqual(state.used_relations, set())
        asyncio.run(finish())

    def test_three_observed_tracks_evict_even_unpublished_and_expire(self):
        state = self.facts.PublishedRecordingContext()
        fact = self.pool(0)[0]
        now = fact.observed_at
        state.observe(fact.media_identity, now)
        state.commit(fact, now)
        for number in (1, 2, 3):
            state.observe(self.catalog(number)["uri"], now)
        self.assertEqual(state.credits, {})
        self.assertEqual(len(state.observed_tracks), 3)
        state.observe(fact.media_identity, now)
        state.commit(fact, now)
        state.observe(self.catalog(1)["uri"], now+1801)
        self.assertIsNone(state.candidate(self.pool(1), self.catalog(1)["uri"], now+1801))

    def test_four_published_tracks_and_end_leave_no_other_knowledge_proof(self):
        self.run_pair(discover=False)
        async def scenario():
            session, manager = self.session, self.manager
            for number in (2, 3):
                catalog = self.catalog(number)
                await manager.async_update_playback_projection(owner_profile_id="owner", session_id=session.session_id,
                    state="playing", media_identity=catalog["uri"], title=catalog["title"], artist=catalog["artist"],
                    duration_ms=300000, position_ms=0)
                async def source():
                    return {"_qualified_facts":self.pool(number)}
                moment = await manager.async_process_track_started(owner_profile_id="owner", session_id=session.session_id,
                    media_identity=catalog["uri"], insight_provider=source, require_current_playback=True)
                self.assertIsNotNone(moment)
            self.assertEqual(len(session.published_recording_context.credits), 3)
            self.assertNotIn(self.catalog(0)["uri"], session.published_recording_context.credits)
            self.assertFalse(any(c.qualified_fact for c in session.knowledge_engine.assembled_contexts))
            ended = await manager.async_end(owner_profile_id="owner", session_id=session.session_id)
            self.assertEqual(ended.published_recording_context.credits, {})
            self.assertFalse(any(c.qualified_fact for c in ended.knowledge_engine.assembled_contexts))
        asyncio.run(scenario())

    def test_reconnect_duplicate_pause_seek_and_late_results_do_not_publish(self):
        self.run_pair()
        async def scenario():
            session, manager = self.session, self.manager
            count = len(session.broadcast.state.dj_moments)
            session.broadcast.as_dict()  # reconnect/readback is a projection only
            async def source():
                return {"_qualified_facts": self.pool(1)}
            duplicate = await manager.async_process_track_started(owner_profile_id="owner", session_id=session.session_id,
                media_identity=self.catalog(1)["uri"], insight_provider=source, require_current_playback=True)
            self.assertIsNone(duplicate)
            for state, position in (("paused",0), ("playing",100000)):
                await manager.async_update_playback_projection(owner_profile_id="owner", session_id=session.session_id,
                    state=state, media_identity=self.catalog(1)["uri"], title="Recording 1", artist="Artist 1",
                    duration_ms=300000, position_ms=position)
                self.assertIsNone(await manager.async_maybe_publish_intra_track_moment(owner_profile_id="owner",
                    session_id=session.session_id, media_identity=self.catalog(1)["uri"]))
            self.assertEqual(len(session.broadcast.state.dj_moments), count)
            self.assertEqual(len(session.published_recording_context.used_relations), 1)
            entered, release = asyncio.Event(), asyncio.Event()
            catalog = self.catalog(2)
            await manager.async_update_playback_projection(owner_profile_id="owner", session_id=session.session_id,
                state="playing", media_identity=catalog["uri"], title=catalog["title"], artist=catalog["artist"],
                duration_ms=300000, position_ms=0)
            async def late():
                entered.set()
                await release.wait()
                return {"_qualified_facts":self.pool(2)}
            task = asyncio.create_task(manager.async_process_track_started(owner_profile_id="owner",
                session_id=session.session_id, media_identity=catalog["uri"], insight_provider=late, require_current_playback=True))
            await entered.wait()
            await manager.async_update_playback_projection(owner_profile_id="owner", session_id=session.session_id,
                state="paused", media_identity=catalog["uri"], title=catalog["title"], artist=catalog["artist"],
                duration_ms=300000, position_ms=0)
            release.set()
            self.assertIsNone(await task)
            self.assertEqual(len(session.broadcast.state.dj_moments), count)
            self.assertNotIn(catalog["uri"], session.published_recording_context.credits)
        asyncio.run(scenario())
