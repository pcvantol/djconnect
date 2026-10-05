"""Session-level decisions for bounded DJ narrative continuity."""

from __future__ import annotations

import asyncio
import importlib.util
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "si_continuity_test_package"


def _load_runtime_module():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules[PACKAGE] = package
    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN = "djconnect"
    const.API_IMAGE_PROXY_BASE = "/api/djconnect/v1/image_proxy"
    sys.modules[const.__name__] = const
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.session_runtime",
        ROOT / "custom_components" / "djconnect" / "session_runtime.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SessionContinuityBehaviorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = _load_runtime_module()

    @classmethod
    def tearDownClass(cls) -> None:
        for name in tuple(sys.modules):
            if name == PACKAGE or name.startswith(f"{PACKAGE}."):
                del sys.modules[name]

    def _track(self, manager, session, clock: list[float], insight: dict):
        async def provide_insight() -> dict:
            return insight

        moment = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                insight_provider=provide_insight,
            )
        )
        clock[0] += 75.0
        assert moment is not None
        return moment

    def test_successive_tracks_change_angle_and_choose_silence_when_context_is_spent(self) -> None:
        clock = [100.0]
        manager = self.runtime.SessionRuntimeManager()
        session = asyncio.run(
            manager.async_start(
                owner_profile_id="continuity",
                selected_mood="groove",
                elapsed_time_source=lambda: clock[0],
            )
        )
        flow_id = session.planner.output.session_flow.flow_id
        moments = []
        for number in range(1, 6):
            familiar = number <= 4
            artist = "Artist One" if familiar else "Artist Two"
            album = "Album One" if familiar else "Album Two"
            detail_number = min(number, 3) if familiar else number
            moments.append(
                self._track(
                    manager,
                    session,
                    clock,
                    {
                        "track": {
                            "title": f"Track {number}",
                            "artist": artist,
                            "album": album,
                            "producer": "Producer One" if familiar else "Producer Two",
                            "release_year": "2001" if familiar else "2002",
                        },
                        "analysis": {
                            "summary": f"Safe introduction {detail_number}.",
                            "full_text": f"Safe background detail {detail_number}.",
                            "genre": "downtempo" if familiar else "jazz",
                        },
                        "music_dna": {"private": "never-in-broadcast"},
                    },
                )
            )

        self.assertEqual(
            [moment.moment_type for moment in moments],
            [
                self.runtime.DJMomentType.ARTIST,
                self.runtime.DJMomentType.ALBUM,
                self.runtime.DJMomentType.GENRE,
                self.runtime.DJMomentType.SILENCE,
                self.runtime.DJMomentType.ARTIST,
            ],
        )
        self.assertEqual(dict(moments[3].generation_metadata)["reason"], "planned_silence")
        self.assertEqual(len({moment.content for moment in moments[:3]}), 3)
        active = asyncio.run(manager.async_get_active(session.owner_profile_id))
        assert active is not None
        self.assertEqual(active.planner.output.session_flow.flow_id, flow_id)
        self.assertEqual(
            [item.moment_id for item in active.planner.output.session_flow.items if item.moment_id],
            [moment.moment_id for moment in moments],
        )
        self.assertEqual(active.broadcast.as_dict()["dj_moments"][-1]["moment_id"], moments[-1].moment_id)
        self.assertNotIn("never-in-broadcast", str(active.broadcast.as_dict()))
        self.assertNotIn("recent_topics", str(active.broadcast.as_dict()))
        horizon = active.planner.horizon
        assert horizon is not None and horizon.planning_window is not None
        self.assertEqual(horizon.upcoming_playback.entries, ())
        self.assertTrue(all(slot.is_current_track for slot in horizon.planning_window.candidate_slots))
        self.assertGreater(horizon.invalidation_generation, 0)
        with self.assertRaises(FrozenInstanceError):
            moments[0].content = "changed"

    def test_same_spoken_fact_is_not_repeated_as_a_different_moment_type(self) -> None:
        clock = [100.0]
        manager = self.runtime.SessionRuntimeManager()
        session = asyncio.run(
            manager.async_start(
                owner_profile_id="same-fact",
                selected_mood="groove",
                elapsed_time_source=lambda: clock[0],
            )
        )
        shared_analysis = {"summary": "The shared fact.", "full_text": "The same safe fact."}
        first = self._track(
            manager,
            session,
            clock,
            {
                "track": {
                    "title": "First",
                    "artist": "Artist One",
                    "album": "Album One",
                    "producer": "Producer One",
                    "release_year": "2001",
                },
                "analysis": shared_analysis,
            },
        )
        second = self._track(
            manager,
            session,
            clock,
            {
                "track": {
                    "title": "Second",
                    "artist": "Artist One",
                    "album": "Album Two",
                    "producer": "Producer Two",
                    "release_year": "2002",
                },
                "analysis": shared_analysis,
            },
        )
        self.assertEqual(first.moment_type, self.runtime.DJMomentType.ARTIST)
        self.assertEqual(second.moment_type, self.runtime.DJMomentType.SILENCE)

    def test_session_update_waits_through_one_silence_after_a_recent_update(self) -> None:
        clock = [100.0]
        manager = self.runtime.SessionRuntimeManager()
        session = asyncio.run(
            manager.async_start(
                owner_profile_id="direction-pacing",
                selected_mood="energy",
                elapsed_time_source=lambda: clock[0],
            )
        )
        empty_insight: dict = {}
        first = self._track(manager, session, clock, empty_insight)
        self.assertEqual(first.moment_type, self.runtime.DJMomentType.SESSION)
        horizon = session.planner.horizon
        assert horizon is not None
        generation_before_mood_change = horizon.invalidation_generation
        asyncio.run(
            manager.async_update_mood(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                selected_mood="chill",
            )
        )
        second = self._track(manager, session, clock, empty_insight)
        third = self._track(manager, session, clock, empty_insight)
        self.assertEqual(
            [second.moment_type, third.moment_type],
            [self.runtime.DJMomentType.SILENCE, self.runtime.DJMomentType.SILENCE],
        )
        active = asyncio.run(manager.async_get_active(session.owner_profile_id))
        assert active is not None
        self.assertEqual(active.session_direction.direction, self.runtime.SessionDirectionType.BUILDING_ENERGY)
        self.assertEqual(
            sum(moment.moment_type is self.runtime.DJMomentType.SESSION for moment in active.moment_engine.moments),
            1,
        )
        cooled = self._track(manager, session, clock, empty_insight)
        self.assertEqual(cooled.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(dict(cooled.generation_metadata)["direction"], "cooling_down")
        assert horizon.planning_window is not None
        self.assertGreater(horizon.invalidation_generation, generation_before_mood_change)
        self.assertEqual(horizon.planning_window.influence.effective_mood, "chill")
        self.assertEqual(horizon.upcoming_playback.entries, ())

    def test_distinct_safe_angle_spaces_the_previous_moment_type(self) -> None:
        clock = [100.0]
        manager = self.runtime.SessionRuntimeManager()
        session = asyncio.run(
            manager.async_start(
                owner_profile_id="type-spacing",
                selected_mood="groove",
                elapsed_time_source=lambda: clock[0],
            )
        )
        selected = []
        for artist, album in (("Artist One", "Album One"), ("Artist Two", "Album Two")):
            selected.append(
                self._track(
                    manager,
                    session,
                    clock,
                    {
                        "track": {
                            "title": f"Track by {artist}",
                            "artist": artist,
                            "album": album,
                            "producer": f"Producer for {artist}",
                            "release_year": "2001",
                        },
                        "analysis": {
                            "summary": f"Safe summary for {artist}.",
                            "full_text": f"Safe detail for {artist}.",
                        },
                    },
                )
            )
        self.assertEqual(
            [moment.moment_type for moment in selected],
            [self.runtime.DJMomentType.ARTIST, self.runtime.DJMomentType.ALBUM],
        )

    def test_type_spacing_keeps_valid_angle_when_alternative_lacks_context(self) -> None:
        clock = [100.0]
        manager = self.runtime.SessionRuntimeManager()
        session = asyncio.run(
            manager.async_start(
                owner_profile_id="incomplete-alternative",
                selected_mood="groove",
                elapsed_time_source=lambda: clock[0],
            )
        )
        first = self._track(
            manager,
            session,
            clock,
            {
                "track": {"title": "First", "artist": "Artist One", "producer": "Producer One"},
                "analysis": {"summary": "First summary.", "full_text": "First detail."},
            },
        )
        second = self._track(
            manager,
            session,
            clock,
            {
                "track": {
                    "title": "Second",
                    "artist": "Artist Two",
                    "producer": "Producer Two",
                    "release_year": "2002",
                },
                "analysis": {"summary": "Second summary.", "full_text": "Second detail."},
            },
        )
        self.assertEqual(first.moment_type, self.runtime.DJMomentType.ARTIST)
        self.assertEqual(second.moment_type, self.runtime.DJMomentType.ARTIST)
        third = self._track(
            manager,
            session,
            clock,
            {
                "track": {
                    "title": "Third",
                    "artist": "Artist Three",
                    "producer": "Producer Three",
                    "release_year": "2003",
                },
                "analysis": {
                    "summary": "Third summary.",
                    "full_text": "Third detail.",
                    "genre": "jazz",
                },
            },
        )
        self.assertEqual(third.moment_type, self.runtime.DJMomentType.GENRE)

    def test_transition_is_bounded_across_a_multi_track_exploration(self) -> None:
        clock = [100.0]
        manager = self.runtime.SessionRuntimeManager()
        session = asyncio.run(
            manager.async_start(
                owner_profile_id="transition-pacing",
                selected_mood="groove",
                dj_persona=self.runtime.DJPersona.RADIO_DJ,
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
                elapsed_time_source=lambda: clock[0],
            )
        )
        track_inputs = (
            {"track": {"title": "First", "artist": "Artist One", "producer": "Producer One"}, "analysis": {"summary": "First context.", "full_text": "First safe detail."}},
            {"track": {"title": "Second", "artist": "Artist Two", "related_tracks": "Related Two"}, "analysis": {"summary": "Second context.", "full_text": "Second safe detail."}},
            {"track": {"title": "Third", "artist": "Artist Three", "producer": "Producer Three", "related_tracks": "Related Three"}, "analysis": {"summary": "Third context.", "full_text": "Third safe detail."}},
            {"track": {"title": "Fourth", "artist": "Artist Four", "related_tracks": "Related Four"}, "analysis": {"summary": "Fourth context.", "full_text": "Fourth safe detail."}},
        )
        selected = [self._track(manager, session, clock, insight) for insight in track_inputs]
        self.assertEqual(
            [moment.moment_type for moment in selected],
            [
                self.runtime.DJMomentType.ARTIST,
                self.runtime.DJMomentType.RECOMMENDATION,
                self.runtime.DJMomentType.ARTIST,
                self.runtime.DJMomentType.RECOMMENDATION,
            ],
        )
        transitions = tuple(
            moment for moment in session.moment_engine.moments
            if moment.moment_type is self.runtime.DJMomentType.TRANSITION
        )
        self.assertEqual(len(transitions), 1)
        self.assertNotIn("relation", dict(transitions[0].generation_metadata))
        self.assertEqual(
            dict(transitions[0].generation_metadata)["transition_to_moment_id"],
            selected[1].moment_id,
        )
        self.assertIn("The session moves from", transitions[0].content)
        self.assertEqual(session.planner.last_decision.decision_type, self.runtime.PlannerDecisionType.NO_TRANSITION)

    def test_resetting_returns_after_interval_silence_without_getting_stuck(self) -> None:
        clock = [100.0]
        manager = self.runtime.SessionRuntimeManager()
        session = asyncio.run(
            manager.async_start(
                owner_profile_id="reset-return",
                elapsed_time_source=lambda: clock[0],
            )
        )
        self.assertEqual(self._track(manager, session, clock, {}).moment_type, self.runtime.DJMomentType.SILENCE)
        self.assertEqual(self._track(manager, session, clock, {}).moment_type, self.runtime.DJMomentType.SILENCE)
        resetting = self._track(manager, session, clock, {})
        self.assertEqual(resetting.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(dict(resetting.generation_metadata)["direction"], "resetting")

        clock[0] -= 74.0
        pause = self._track(manager, session, clock, {})
        self.assertEqual(pause.moment_type, self.runtime.DJMomentType.SILENCE)
        returning = self._track(manager, session, clock, {})
        self.assertEqual(returning.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(dict(returning.generation_metadata)["direction"], "returning")

        clock[0] -= 74.0
        for _ in range(3):
            self.assertEqual(
                self._track(manager, session, clock, {}).moment_type,
                self.runtime.DJMomentType.SILENCE,
            )
        resetting_again = self._track(manager, session, clock, {})
        self.assertEqual(resetting_again.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(dict(resetting_again.generation_metadata)["direction"], "resetting")
        returning_again = self._track(manager, session, clock, {})
        self.assertEqual(returning_again.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(dict(returning_again.generation_metadata)["direction"], "returning")

    def test_persona_changes_the_first_safe_session_angle(self) -> None:
        insight = {
            "track": {
                "title": "Track",
                "artist": "Artist",
                "album": "Album",
                "producer": "Producer",
                "release_year": "2001",
            },
            "analysis": {"summary": "Safe summary.", "full_text": "Safe detail."},
        }
        selected = []
        for persona in (self.runtime.DJPersona.HOME_DJ, self.runtime.DJPersona.RADIO_DJ):
            clock = [100.0]
            manager = self.runtime.SessionRuntimeManager()
            session = asyncio.run(
                manager.async_start(
                    owner_profile_id=f"persona-{persona.value}",
                    selected_mood="groove",
                    dj_persona=persona,
                    elapsed_time_source=lambda: clock[0],
                )
            )
            selected.append(self._track(manager, session, clock, insight).moment_type)
        self.assertEqual(
            selected, [self.runtime.DJMomentType.ARTIST, self.runtime.DJMomentType.ALBUM]
        )


if __name__ == "__main__":
    unittest.main()
