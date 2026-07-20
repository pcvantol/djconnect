from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from dataclasses import FrozenInstanceError


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.djconnect"


def _load_runtime_module():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault(PACKAGE, package)
    const = types.ModuleType(f"{PACKAGE}.const")
    const.DOMAIN = "djconnect"
    previous_const = sys.modules.get(f"{PACKAGE}.const")
    sys.modules[f"{PACKAGE}.const"] = const
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.session_runtime",
        ROOT / "custom_components" / "djconnect" / "session_runtime.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, previous_const


class SessionRuntimeManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls) -> None:
        sys.modules.pop(f"{PACKAGE}.session_runtime", None)
        if cls.previous_const is None:
            sys.modules.pop(f"{PACKAGE}.const", None)
        else:
            sys.modules[f"{PACKAGE}.const"] = cls.previous_const

    def test_creates_and_looks_up_active_runtime_for_profile(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-peter",
                room="living-room",
                selected_mood="groove",
                music_backend="spotify_direct",
            )
        )
        reconnected = asyncio.run(manager.async_get_active("profile-peter"))

        self.assertEqual(created, reconnected)
        self.assertIs(created.planner, reconnected.planner)
        self.assertIs(created.broadcast, reconnected.broadcast)
        self.assertEqual(created.runtime_state, self.runtime.SessionRuntimeState.ACTIVE)
        self.assertEqual(created.owner_profile_id, "profile-peter")
        self.assertTrue(created.started_at)

    def test_runtime_creates_one_ephemeral_planner_with_foundation_defaults(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        planner = created.planner
        self.assertEqual(planner.planner_state, self.runtime.PlannerState.READY)
        self.assertEqual(planner.planning_horizon_minutes, 15)
        self.assertEqual(
            created.session_direction.direction,
            self.runtime.SessionDirectionType.MAINTAINING_ENERGY,
        )
        self.assertEqual(
            created.session_direction.start_strategy,
            self.runtime.SessionStartStrategy.MANUAL,
        )
        self.assertEqual(planner.pending_events, ())
        self.assertEqual(planner.output.session_flow.planning_horizon_minutes, 15)
        public_planner = created.as_dict()["planner"]
        self.assertEqual(public_planner["planning_horizon_minutes"], 15)
        self.assertEqual(
            created.as_dict()["session_direction"]["direction"], "maintaining_energy"
        )
        self.assertEqual(
            public_planner["output"]["session_flow"]["flow_id"],
            f"flow-{created.session_id}",
        )

    def test_session_start_strategies_initialize_runtime_owned_direction(self) -> None:
        expected = {
            self.runtime.SessionStartStrategy.DISCOVER: "exploring",
            self.runtime.SessionStartStrategy.PARTY: "building_energy",
            self.runtime.SessionStartStrategy.FOCUS: "deepening",
            self.runtime.SessionStartStrategy.CHILL: "cooling_down",
            self.runtime.SessionStartStrategy.MANUAL: "maintaining_energy",
        }
        for strategy, direction in expected.items():
            manager = self.runtime.SessionRuntimeManager()
            created = asyncio.run(
                manager.async_start(
                    owner_profile_id=f"profile-{strategy.value}",
                    session_start_strategy=strategy,
                )
            )
            self.assertEqual(created.session_direction.direction.value, direction)
            self.assertEqual(created.session_direction.start_strategy, strategy)
            self.assertTrue(created.session_direction.initialized_at)
            self.assertEqual(
                created.session_direction.initialized_at,
                created.session_direction.updated_at,
            )

    def test_planner_proposes_direction_change_without_owning_runtime_state(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))

        decision = created.planner.evaluate_track_started(
            session_direction=created.session_direction,
            selected_mood="energy",
            persona=self.runtime.DJPersona.HOME_DJ,
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_SESSION_UPDATE
        )
        self.assertEqual(
            decision.proposed_session_direction,
            self.runtime.SessionDirectionType.BUILDING_ENERGY,
        )
        self.assertEqual(
            created.session_direction.direction,
            self.runtime.SessionDirectionType.MAINTAINING_ENERGY,
        )

    def test_performance_memory_is_runtime_scoped_and_starts_empty(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))

        memory = created.performance_memory
        self.assertEqual(memory.source_flow_id, f"flow-{created.session_id}")
        self.assertEqual(memory.recent_moment_ids, ())
        self.assertEqual(memory.recent_moment_types, ())
        self.assertEqual(memory.recent_silence_count, 0)
        self.assertNotIn("profile", memory.as_dict())

    def test_planner_uses_performance_memory_to_prevent_duplicate_artist_story(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        memory = self.runtime.PerformanceMemory(
            "flow-test", recent_artists=("Daft Punk",)
        )

        decision = created.planner.evaluate_track_started(
            session_direction=created.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints={
                "producer": "Daft Punk",
                "artist": "Daft Punk",
                "genre": "electronic",
            },
            performance_memory=memory,
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_GENRE_STORY
        )

    def test_planner_uses_performance_memory_to_prevent_duplicate_recommendation(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        memory = self.runtime.PerformanceMemory(
            "flow-test", recent_recommendations=("Massive Attack",)
        )

        decision = created.planner.evaluate_track_started(
            session_direction=created.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints={
                "related_tracks": "Angel",
                "artist": "Massive Attack",
                "genre": "trip-hop",
            },
            performance_memory=memory,
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_GENRE_STORY
        )

    def test_planner_prefers_an_unused_moment_type_when_genre_repeats(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        memory = self.runtime.PerformanceMemory("flow-test", recent_genres=("house",))

        decision = created.planner.evaluate_track_started(
            session_direction=created.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints={"genre": "house", "producer": "Nile Rodgers", "artist": "Chic"},
            performance_memory=memory,
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_ARTIST_STORY
        )

    def test_planner_is_not_shared_between_runtimes_and_is_disposed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=first.session_id)
        )
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))
        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        self.assertIsNot(first.planner, second.planner)

    def test_runtime_creates_one_broadcast_engine_with_canonical_state(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(owner_profile_id="profile-peter", selected_mood="groove")
        )

        state = created.broadcast.as_dict()
        self.assertEqual(
            state["session"],
            {
                "session_id": created.session_id,
                "runtime_state": "active",
                "selected_mood": "groove",
            },
        )
        self.assertEqual(
            state["playback"],
            {
                "current_track": None,
                "playback_progress": None,
            },
        )
        self.assertEqual(state["planner"]["planning_horizon_minutes"], 15)
        self.assertEqual(state["planner"]["current_direction"], "maintaining_energy")
        self.assertEqual(
            state["planner"]["session_direction"]["start_strategy"], "manual"
        )
        self.assertEqual(
            state["session_flow"],
            created.planner.output.session_flow.as_dict(),
        )
        self.assertEqual(state["audience"], {"signal_totals": {}, "recent_activity": []})
        self.assertTrue(state["broadcast"]["started_at"])
        self.assertEqual(created.as_dict()["broadcast"], state)

    def test_planner_creates_and_republishes_its_canonical_session_flow(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        flow = created.planner.output.session_flow
        self.assertEqual(flow.flow_id, f"flow-{created.session_id}")
        self.assertEqual(flow.planning_horizon_minutes, 15)
        self.assertEqual(
            [(item.position.value, item.item_type.value) for item in flow.items],
            [
                ("now", "current_track"),
                ("next", "planning_horizon"),
                ("next", "maintain_direction"),
                ("later", "future_direction"),
                ("later", "future_placeholder"),
            ],
        )

        republished = created.republish_session_flow()

        self.assertIs(created.planner.output.session_flow, republished)
        self.assertEqual(created.broadcast.as_dict()["session_flow"], republished.as_dict())
        self.assertTrue(created.planner.last_replan_at)

    def test_session_flow_is_not_shared_and_is_removed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        ended = asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=first.session_id)
        )
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))

        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        self.assertIsNot(
            first.planner.output.session_flow,
            second.planner.output.session_flow,
        )
        self.assertEqual(
            ended.broadcast.as_dict()["session_flow"]["flow_id"],
            first.planner.output.session_flow.flow_id,
        )

    def test_broadcast_engine_is_not_shared_and_is_removed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        ended = asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=first.session_id)
        )

        self.assertEqual(ended.broadcast.as_dict()["session"]["runtime_state"], "ended")
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))
        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        self.assertIsNot(first.broadcast, second.broadcast)

    def test_broadcast_subscription_receives_snapshot_incremental_events_and_cleanup(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        received: list[dict] = []

        subscribed = asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=received.append,
            )
        )

        self.assertIsNotNone(subscribed)
        subscription_id, snapshot = subscribed
        self.assertEqual(snapshot, created.broadcast.as_dict())
        self.assertEqual(created.broadcast.subscriber_count, 1)

        created.republish_session_flow()
        self.assertEqual(
            [event["event_type"] for event in received],
            ["planner_updated", "session_flow_updated"],
        )
        self.assertEqual(received[-1]["payload"]["session_flow"], created.broadcast.as_dict()["session_flow"])

        asyncio.run(
            manager.async_unsubscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                subscription_id=subscription_id,
            )
        )
        self.assertEqual(created.broadcast.subscriber_count, 0)

    def test_broadcast_runtime_termination_notifies_and_releases_subscriptions(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        received: list[dict] = []
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=received.append,
            )
        )

        asyncio.run(manager.async_end(owner_profile_id="profile-peter", session_id=created.session_id))

        self.assertEqual(
            [event["event_type"] for event in received],
            ["runtime_ended", "broadcast_stopped"],
        )
        self.assertEqual(created.broadcast.subscriber_count, 0)

    def test_profile_owned_runtime_terminates_every_bound_device_subscription(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        first_events: list[dict] = []
        second_events: list[dict] = []
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=first_events.append,
            )
        )
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=second_events.append,
            )
        )

        asyncio.run(manager.async_end(owner_profile_id="profile-peter", session_id=created.session_id))

        self.assertEqual(created.broadcast.subscriber_count, 0)
        self.assertEqual(
            [event["event_type"] for event in first_events],
            ["runtime_ended", "broadcast_stopped"],
        )
        self.assertEqual(
            [event["event_type"] for event in second_events],
            ["runtime_ended", "broadcast_stopped"],
        )

    def test_subscription_is_rejected_when_requested_runtime_belongs_to_another_profile(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-owner"))

        subscribed = asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-other",
                session_id=created.session_id,
                callback=lambda event: None,
            )
        )

        self.assertIsNone(subscribed)

    def test_broadcast_token_is_read_only_runtime_scoped_and_invalid_after_end(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        second = asyncio.run(manager.async_start(owner_profile_id="profile-b"))
        contract = asyncio.run(
            manager.async_broadcast_token_for_owner(
                owner_profile_id="profile-a", session_id=first.session_id
            )
        )
        assert contract is not None
        token = contract["broadcast_token"]
        self.assertEqual(
            contract["capabilities"],
            {"view_broadcast": True, "like": False, "audience_signals": True, "ask_dj": False, "owner_controls": False},
        )
        self.assertNotIn("profile", contract)

        received: list[dict] = []
        self.assertIsNotNone(
            asyncio.run(
                manager.async_subscribe_with_broadcast_token(
                    session_id=first.session_id, broadcast_token=token, callback=received.append
                )
            )
        )
        self.assertIsNone(
            asyncio.run(
                manager.async_subscribe_with_broadcast_token(
                    session_id=second.session_id, broadcast_token=token, callback=received.append
                )
            )
        )
        self.assertIsNone(
            asyncio.run(
                manager.async_subscribe_with_broadcast_token(
                    session_id=first.session_id, broadcast_token=f"{token}changed", callback=received.append
                )
            )
        )
        asyncio.run(manager.async_end(owner_profile_id="profile-a", session_id=first.session_id))
        self.assertIsNone(
            asyncio.run(
                manager.async_subscribe_with_broadcast_token(
                    session_id=first.session_id, broadcast_token=token, callback=received.append
                )
            )
        )

    def test_audience_signals_aggregate_in_planner_and_republish_broadcast_state(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        token = asyncio.run(manager.async_broadcast_token_for_owner(owner_profile_id="profile-a", session_id=created.session_id))["broadcast_token"]
        events: list[dict] = []
        asyncio.run(manager.async_subscribe(owner_profile_id="profile-a", session_id=created.session_id, callback=events.append))

        for _ in range(2):
            audience = asyncio.run(manager.async_submit_audience_signal_with_broadcast_token(session_id=created.session_id, broadcast_token=token, signal="more_energy"))
        audience = asyncio.run(manager.async_submit_audience_signal_with_broadcast_token(session_id=created.session_id, broadcast_token=token, signal="genre_suggestion", value="techno"))

        self.assertEqual(audience["signal_totals"], {"more_energy": 2, "genre_suggestion:techno": 1})
        self.assertEqual([event["event_type"] for event in events], ["audience_updated", "audience_updated", "audience_updated"])
        self.assertIsNone(asyncio.run(manager.async_submit_audience_signal_with_broadcast_token(session_id=created.session_id, broadcast_token="invalid", signal="more_energy")))

    def test_broadcast_event_vocabulary_is_stable(self) -> None:
        self.assertEqual(
            [event.value for event in self.runtime.BroadcastEventType],
            [
                "runtime_created",
                "runtime_ended",
                "playback_changed",
                "playback_progress",
                "planner_updated",
                "mood_changed",
                "track_changed",
                "session_flow_updated",
                "audience_updated",
                "broadcast_started",
                "broadcast_stopped",
                "dj_moment_published",
            ],
        )

    def test_track_context_moment_is_frozen_placed_and_broadcast(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                selected_mood="groove",
                dj_persona=self.runtime.DJPersona.RADIO_DJ,
            )
        )
        events: list[dict] = []
        asyncio.run(manager.async_subscribe(owner_profile_id="profile-a", session_id=created.session_id, callback=events.append))

        async def insight() -> dict:
            return {
                "track": {"title": "Teardrop", "artist": "Massive Attack", "album": "Mezzanine"},
                "analysis": {"summary": "A spacious trip-hop landmark.", "full_text": "The suspended beat and vocal leave room for the bass to breathe."},
            }

        moment = asyncio.run(manager.async_generate_track_context(owner_profile_id="profile-a", session_id=created.session_id, insight_provider=insight))

        assert moment is not None
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.TRACK)
        self.assertEqual(moment.presentation_intent.source_session_mood, "groove")
        self.assertEqual(moment.presentation_intent.dj_persona, self.runtime.DJPersona.RADIO_DJ)
        self.assertEqual(created.broadcast.as_dict()["dj_moments"][0]["moment_id"], moment.moment_id)
        self.assertIn(moment.moment_id, [item.moment_id for item in created.planner.output.session_flow.items])
        self.assertEqual(events[-1]["event_type"], "dj_moment_published")
        with self.assertRaises(FrozenInstanceError):
            moment.summary = "mutated"  # type: ignore[misc]

    def test_runtime_owns_knowledge_engine_and_assembles_safe_context(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        self.assertIsInstance(created.knowledge_engine, self.runtime.DJKnowledgeEngine)

        async def insight() -> dict:
            return {
                "track": {"title": "Track", "artist": "Artist", "album": "Album", "genres": ["electronic"], "producer": "Producer", "release_year": 1998},
                "analysis": {"summary": "Safe summary.", "full_text": "Safe full context.", "instrumentation": ["bass", "drums"]},
                "music_dna": {"private": "never included"},
            }

        moment = asyncio.run(manager.async_process_track_started(owner_profile_id="profile-a", session_id=created.session_id, insight_provider=insight))
        assert moment is not None
        context = created.knowledge_engine.assembled_contexts[0]
        self.assertEqual(dict(context.track)["title"], "Track")
        self.assertEqual(dict(context.track)["producer"], "Producer")
        self.assertEqual(dict(context.track)["release_year"], "1998")
        self.assertIn("instrumentation", dict(context.analysis))
        self.assertFalse(context.personal_context_used)
        self.assertNotIn("music_dna", context.as_insight())
        self.assertEqual(
            context.as_insight()["performance_memory"]["source_flow_id"],
            f"flow-{created.session_id}",
        )
        self.assertEqual(moment.source_references, ("track_insight",))

    def test_performance_memory_projects_recent_runtime_moments_from_session_flow(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))

        async def insight() -> dict:
            return {
                "track": {
                    "title": "Teardrop",
                    "artist": "Massive Attack",
                    "album": "Mezzanine",
                    "genres": ["trip-hop"],
                },
                "analysis": {
                    "summary": "A spacious trip-hop landmark.",
                    "full_text": "The suspended beat leaves room for the bass.",
                    "genre": "trip-hop",
                },
            }

        moment = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id="profile-a",
                session_id=created.session_id,
                insight_provider=insight,
            )
        )
        active = asyncio.run(manager.async_get_active("profile-a"))

        assert moment is not None and active is not None
        memory = active.performance_memory
        self.assertEqual(memory.recent_moment_ids, (moment.moment_id,))
        self.assertEqual(memory.recent_moment_types, (self.runtime.DJMomentType.GENRE,))
        self.assertEqual(memory.recent_artists, ("Massive Attack",))
        self.assertEqual(memory.recent_albums, ("Mezzanine",))
        self.assertEqual(memory.recent_genres, ("trip-hop",))
        self.assertEqual(
            memory.source_flow_id, active.planner.output.session_flow.flow_id
        )

    def test_performance_memory_is_disposed_with_ended_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        ended = asyncio.run(
            manager.async_end(owner_profile_id="profile-a", session_id=first.session_id)
        )
        second = asyncio.run(manager.async_start(owner_profile_id="profile-a"))

        assert ended is not None
        self.assertEqual(ended.performance_memory.recent_moment_ids, ())
        self.assertNotEqual(
            first.performance_memory.source_flow_id,
            second.performance_memory.source_flow_id,
        )
        self.assertEqual(second.performance_memory.recent_moment_ids, ())

    def test_direction_change_is_runtime_owned_and_generates_session_update(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(owner_profile_id="profile-a", selected_mood="energy")
        )
        events: list[dict] = []
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id="profile-a",
                session_id=created.session_id,
                callback=events.append,
            )
        )
        provider_called = False

        async def insight() -> dict:
            nonlocal provider_called
            provider_called = True
            return {}

        moment = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id="profile-a",
                session_id=created.session_id,
                insight_provider=insight,
            )
        )
        active = asyncio.run(manager.async_get_active("profile-a"))

        assert moment is not None and active is not None
        self.assertFalse(provider_called)
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(
            moment.knowledge_intent.intent_type,
            self.runtime.KnowledgeIntentType.SESSION_DIRECTION,
        )
        self.assertEqual(
            active.session_direction.direction,
            self.runtime.SessionDirectionType.BUILDING_ENERGY,
        )
        self.assertNotEqual(
            active.session_direction.updated_at, active.session_direction.initialized_at
        )
        self.assertEqual(
            active.broadcast.as_dict()["planner"]["session_direction"]["direction"],
            "building_energy",
        )
        self.assertIn("planner_updated", [event["event_type"] for event in events])
        self.assertEqual(
            active.knowledge_engine.assembled_contexts[-1].session_direction,
            active.session_direction,
        )
        self.assertEqual(moment.source_references, ("session_direction",))

    def test_later_mood_and_persona_changes_do_not_mutate_existing_moment(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                selected_mood="deep",
                session_start_strategy=self.runtime.SessionStartStrategy.FOCUS,
            )
        )

        async def first() -> dict:
            return {"track": {"title": "A", "artist": "B"}, "analysis": {"summary": "One.", "full_text": "One full context."}}

        first_moment = asyncio.run(manager.async_generate_track_context(owner_profile_id="profile-a", session_id=created.session_id, insight_provider=first))
        asyncio.run(manager.async_update_mood(owner_profile_id="profile-a", session_id=created.session_id, selected_mood="energy"))
        asyncio.run(manager.async_update_persona(owner_profile_id="profile-a", session_id=created.session_id, dj_persona=self.runtime.DJPersona.CLUB_DJ))

        async def second() -> dict:
            return {"track": {"title": "C", "artist": "D"}, "analysis": {"summary": "Two.", "full_text": "Two full context."}}

        second_moment = asyncio.run(manager.async_generate_track_context(owner_profile_id="profile-a", session_id=created.session_id, insight_provider=second))
        assert first_moment is not None and second_moment is not None
        self.assertEqual(first_moment.presentation_intent.source_session_mood, "deep")
        self.assertEqual(second_moment.presentation_intent.source_session_mood, "energy")
        self.assertEqual(first_moment.presentation_intent.dj_persona, self.runtime.DJPersona.HOME_DJ)
        self.assertEqual(second_moment.presentation_intent.dj_persona, self.runtime.DJPersona.CLUB_DJ)

    def test_invalid_or_duplicate_generation_becomes_intentional_silence(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))

        async def invalid() -> dict:
            return {"track": {}, "analysis": {}}

        silence = asyncio.run(manager.async_generate_track_context(owner_profile_id="profile-a", session_id=created.session_id, insight_provider=invalid))
        assert silence is not None
        self.assertEqual(silence.moment_type, self.runtime.DJMomentType.SILENCE)
        self.assertEqual(created.broadcast.as_dict()["dj_moments"], [silence.as_dict()])

    def test_ai_provider_failure_preserves_active_runtime_with_silence(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))

        async def unavailable() -> dict:
            raise TimeoutError("provider timeout")

        moment = asyncio.run(manager.async_generate_track_context(owner_profile_id="profile-a", session_id=created.session_id, insight_provider=unavailable))
        assert moment is not None
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.SILENCE)
        self.assertEqual(asyncio.run(manager.async_get_active("profile-a")).runtime_state, self.runtime.SessionRuntimeState.ACTIVE)

    def test_planner_decides_silence_before_knowledge_for_deep_or_club_session(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                selected_mood="deep",
                session_start_strategy=self.runtime.SessionStartStrategy.FOCUS,
            )
        )
        invoked = False

        async def insight() -> dict:
            nonlocal invoked
            invoked = True
            return {}

        moment = asyncio.run(manager.async_process_track_started(owner_profile_id="profile-a", session_id=created.session_id, insight_provider=insight))
        assert moment is not None
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.SILENCE)
        self.assertFalse(invoked)
        self.assertEqual(created.planner.last_decision.decision_type, self.runtime.PlannerDecisionType.SILENCE)

    def test_owner_only_moment_never_reaches_broadcast_token_viewer(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        token = asyncio.run(manager.async_broadcast_token_for_owner(owner_profile_id="profile-a", session_id=created.session_id))["broadcast_token"]
        receiver_events: list[dict] = []
        subscription = asyncio.run(manager.async_subscribe_with_broadcast_token(session_id=created.session_id, broadcast_token=token, callback=receiver_events.append))
        assert subscription is not None
        private = self.runtime.DJMoment(
            moment_id="private-moment", session_id=created.session_id, created_at="now", moment_type=self.runtime.DJMomentType.TRACK,
            knowledge_intent=self.runtime.KnowledgeIntent(self.runtime.KnowledgeIntentType.TRACK_CONTEXT, "private"),
            presentation_intent=self.runtime.PresentationIntent("deep", self.runtime.DJPersona.HOME_DJ, "warm", "deep", "short", "guided", "music", "normal", 20, (self.runtime.DeliveryChannel.OWNER,), self.runtime.DJMomentVisibility.OWNER_ONLY),
            title="Private", summary="Private", content="Private", artwork_url=None, actions=(), source_references=(), generation_metadata=(),
        )
        created.broadcast.publish_moment(private)
        self.assertEqual(receiver_events, [])
        self.assertEqual(subscription[1]["dj_moments"], [])

    def test_generated_moments_remain_isolated_between_profile_runtimes(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        second = asyncio.run(manager.async_start(owner_profile_id="profile-b"))

        async def insight() -> dict:
            return {
                "track": {"title": "Private Track", "artist": "Artist"},
                "analysis": {"summary": "Safe context.", "full_text": "Safe generated context."},
                "music_dna": {"private": "must never project"},
            }

        moment = asyncio.run(manager.async_generate_track_context(owner_profile_id="profile-a", session_id=first.session_id, insight_provider=insight))
        assert moment is not None
        self.assertEqual(len(first.broadcast.as_dict()["dj_moments"]), 1)
        self.assertEqual(second.broadcast.as_dict()["dj_moments"], [])
        self.assertNotIn("music_dna", moment.as_dict())

    def test_rejects_second_active_runtime_for_same_profile(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

        with self.assertRaises(self.runtime.ActiveSessionExistsError):
            asyncio.run(manager.async_start(owner_profile_id="profile-peter"))

    def test_ends_and_disposes_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        ended = asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=created.session_id)
        )

        self.assertEqual(ended.runtime_state, self.runtime.SessionRuntimeState.ENDED)
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))


if __name__ == "__main__":
    unittest.main()
