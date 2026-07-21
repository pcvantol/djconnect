from __future__ import annotations

import asyncio
import importlib.util
import inspect
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

    def test_runtime_owns_one_internal_planning_runtime_coordinator(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-coordinator"))

        self.assertIsInstance(
            created.planning_coordinator, self.runtime.PlanningRuntimeCoordinator
        )
        self.assertIsNot(created.planning_coordinator, created.planner)
        self.assertIsNot(created.planning_coordinator, created.knowledge_engine)
        self.assertIsNot(created.planning_coordinator, created.moment_engine)
        self.assertNotIn("planning_coordinator", created.as_dict())

    def test_planning_runtime_coordinator_uses_planned_silence_and_existing_publication(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(owner_profile_id="profile-coordinated", selected_mood="groove")
        )

        async def insight() -> dict:
            return {
                "track": {"title": "Track", "artist": "Artist", "producer": "Producer"},
                "analysis": {"summary": "Safe summary.", "full_text": "Safe content."},
            }

        moment = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id="profile-coordinated",
                session_id=created.session_id,
                insight_provider=insight,
                upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                    (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),),
                    confidence=0.8,
                ),
            )
        )

        assert moment is not None
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.SILENCE)
        self.assertEqual(dict(moment.generation_metadata)["reason"], "planned_silence")
        self.assertEqual(created.planning_coordinator.last_planning_generation, 0)
        self.assertEqual(created.planning_coordinator.last_lifecycle_state, "completed")
        self.assertEqual(created.planning_coordinator.last_approval_source, "planned_intent")
        self.assertIn(
            ("silence", 0, 60), created.planner.horizon.consumed_slot_keys
        )
        self.assertIsNone(created.planner.last_decision)
        self.assertEqual(created.planner.output.session_flow.items[-1].moment_id, moment.moment_id)
        self.assertEqual(created.broadcast.state.dj_moments[-1], moment)

    def test_planning_runtime_coordinator_primary_path_consumes_prepared_knowledge(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(owner_profile_id="profile-primary-planning", selected_mood="groove")
        )
        assert created.planner.horizon is not None
        created.planner.horizon._candidate_slots = lambda coverage: (
            self.runtime.CandidatePlanningSlot("artist_story", 0, coverage),
        )

        async def insight() -> dict:
            return {
                "track": {
                    "title": "Track",
                    "artist": "Prepared Artist",
                    "producer": "Producer",
                },
                "analysis": {"summary": "Safe summary.", "full_text": "Safe content."},
            }

        moment = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id="profile-primary-planning",
                session_id=created.session_id,
                insight_provider=insight,
                upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                    (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),),
                    confidence=0.8,
                ),
            )
        )

        assert moment is not None
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.ARTIST)
        self.assertEqual(created.planning_coordinator.last_lifecycle_state, "completed")
        self.assertEqual(created.planning_coordinator.last_approval_source, "planned_intent")
        self.assertEqual(created.planner.horizon.consumed_slot_keys, (("artist_story", 0, 60),))
        self.assertEqual(created.knowledge_engine.assembled_contexts[-1].sources, ("prepared_knowledge",))
        self.assertIsNone(created.planner.last_decision)
        self.assertEqual(created.planner.output.session_flow.items[-1].moment_id, moment.moment_id)
        self.assertEqual(created.broadcast.state.dj_moments[-1], moment)

    def test_planning_runtime_coordinator_falls_back_to_existing_track_started_path(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(owner_profile_id="profile-coordinator-fallback", selected_mood="groove")
        )

        async def insight() -> dict:
            return {
                "track": {"title": "Track", "artist": "Artist", "producer": "Producer"},
                "analysis": {"summary": "Safe summary.", "full_text": "Safe content."},
            }

        moment = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id="profile-coordinator-fallback",
                session_id=created.session_id,
                insight_provider=insight,
                upcoming_playback=self.runtime.UpcomingPlaybackProjection(),
            )
        )

        assert moment is not None
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.ARTIST)
        self.assertEqual(moment.source_references, ("track_insight",))
        self.assertEqual(created.planner.horizon.planning_window.planned_intents, ())
        self.assertEqual(created.planning_coordinator.last_lifecycle_state, "fallback")
        self.assertEqual(created.planning_coordinator.last_fallback_reason, "no_ready_planned_intent")

    def test_runtime_disposal_releases_planning_runtime_coordinator(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-coordinator-disposal"))
        coordinator = created.planning_coordinator
        coordinator.last_planning_generation = 3

        asyncio.run(
            manager.async_end(
                owner_profile_id="profile-coordinator-disposal", session_id=created.session_id
            )
        )

        self.assertTrue(coordinator.disposed)
        self.assertIsNone(coordinator.last_planning_generation)
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-coordinator-disposal")))

    def test_planning_horizon_with_no_observable_playback_has_no_planned_intents(self) -> None:
        horizon = self.runtime.RollingSessionHorizon(window_minutes=15, created_at="now")

        window = horizon.build_planning_window()

        self.assertEqual(window.planned_intents, ())
        self.assertIsNone(window.approve_earliest_planned_intent())

    def test_planning_horizon_creates_bounded_multiple_planned_intents(self) -> None:
        horizon = self.runtime.RollingSessionHorizon(
            window_minutes=2,
            created_at="now",
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (
                    self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-b", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-c", duration_seconds=60),
                ),
                confidence=0.8,
            ),
        )

        window = horizon.build_planning_window()

        self.assertEqual(window.planning_coverage_seconds, 120)
        self.assertEqual(
            [(intent.slot.starts_at_seconds, intent.slot.ends_at_seconds) for intent in window.planned_intents],
            [(0, 60), (60, 120)],
        )
        self.assertTrue(
            all(intent.status is self.runtime.PlannedIntentStatus.PLANNED for intent in window.planned_intents)
        )
        self.assertTrue(all(intent.confidence == 0.8 for intent in window.planned_intents))

    def test_planned_intents_have_deterministic_slot_order(self) -> None:
        window = self.runtime.PlanningWindow(
            starts_at="now",
            ends_at="later",
            planning_coverage_seconds=180,
            generation=4,
            confidence=1.0,
            candidate_slots=(
                self.runtime.CandidatePlanningSlot("recommendation", 120, 180),
                self.runtime.CandidatePlanningSlot("artist_story", 0, 60),
                self.runtime.CandidatePlanningSlot("genre_story", 60, 120),
                self.runtime.CandidatePlanningSlot("lyrics_story", 30, 45),
            ),
        )

        planned = window.plan_intents()

        self.assertEqual(
            [intent.category for intent in planned],
            ["artist_story", "genre_story", "recommendation"],
        )
        self.assertEqual([intent.generation for intent in planned], [4, 4, 4])

    def test_only_earliest_planned_intent_becomes_approved(self) -> None:
        window = self.runtime.PlanningWindow(
            starts_at="now",
            ends_at="later",
            planning_coverage_seconds=120,
            candidate_slots=(
                self.runtime.CandidatePlanningSlot("artist_story", 0, 60),
                self.runtime.CandidatePlanningSlot("genre_story", 60, 120),
            ),
        )
        window.evaluate_readiness()

        first = window.select_intent()
        second = window.select_intent()

        self.assertEqual(first, self.runtime.PlannerIntent("artist_story", 0))
        self.assertEqual(second, first)
        self.assertEqual(
            [intent.status for intent in window.planned_intents],
            [
                self.runtime.PlannedIntentStatus.APPROVED,
                self.runtime.PlannedIntentStatus.PLANNED,
            ],
        )

    def test_planned_intents_remain_runtime_internal_and_are_disposed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-planning"))
        assert created.planner.horizon is not None
        created.planner.horizon.upcoming_playback = self.runtime.UpcomingPlaybackProjection.from_entries(
            (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),)
        )
        window = created.planner.horizon.build_planning_window()

        self.assertNotIn("horizon", created.planner.as_dict())
        self.assertNotIn("planned_intents", created.as_dict())
        self.assertTrue(window.planned_intents)

        asyncio.run(
            manager.async_end(owner_profile_id="profile-planning", session_id=created.session_id)
        )

        self.assertIsNone(asyncio.run(manager.async_get_active("profile-planning")))

    def test_planner_influence_normalizes_mood_direction_and_performance_memory(self) -> None:
        memory = self.runtime.PerformanceMemory("flow-a", recent_artists=("Artist",))

        influence = self.runtime.PlannerInfluence.normalize(
            mood=" Chill ",
            direction=self.runtime.SessionDirectionType.EXPLORING,
            performance_memory=memory,
            generation=-2,
            confidence=2.0,
            freshness=-1.0,
        )

        self.assertEqual(influence.effective_mood, "chill")
        self.assertEqual(influence.effective_direction, self.runtime.SessionDirectionType.EXPLORING)
        self.assertIs(influence.performance_memory, memory)
        self.assertEqual((influence.generation, influence.confidence, influence.freshness), (0, 1.0, 0.0))
        self.assertTrue(influence.is_valid)

    def test_planner_influence_and_selector_are_deterministic(self) -> None:
        window = self.runtime.PlanningWindow(
            starts_at="now",
            ends_at="later",
            candidate_slots=(
                self.runtime.CandidatePlanningSlot("silence", 0, 60),
                self.runtime.CandidatePlanningSlot("recommendation", 60, 120),
            ),
        )
        influence = self.runtime.PlannerInfluence.normalize(
            mood="chill", direction=self.runtime.SessionDirectionType.EXPLORING
        )

        first = self.runtime.PlannerIntentSelector.select(window, influence=influence)
        second = self.runtime.PlannerIntentSelector.select(window, influence=influence)

        self.assertEqual(first, self.runtime.PlannerIntent("silence", 0))
        self.assertEqual(first, second)

    def test_selector_consumes_only_planner_influence_model(self) -> None:
        window = self.runtime.PlanningWindow(
            starts_at="now",
            ends_at="later",
            candidate_slots=(
                self.runtime.CandidatePlanningSlot("artist_story", 0, 60),
                self.runtime.CandidatePlanningSlot("genre_story", 60, 120),
            ),
        )
        influence = self.runtime.PlannerInfluence.normalize(
            performance_memory=self.runtime.PerformanceMemory("flow-a", recent_artists=("Artist",))
        )
        parameters = inspect.signature(self.runtime.PlannerIntentSelector.select).parameters

        selected = self.runtime.PlannerIntentSelector.select(window, influence=influence)

        self.assertEqual(selected, self.runtime.PlannerIntent("genre_story", 0))
        self.assertIn("influence", parameters)
        self.assertNotIn("mood", parameters)
        self.assertNotIn("direction", parameters)
        self.assertNotIn("performance_memory", parameters)

    def test_changed_influence_participates_in_horizon_invalidation(self) -> None:
        horizon = self.runtime.RollingSessionHorizon(
            window_minutes=15,
            created_at="now",
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),)
            ),
        )
        horizon.build_planning_window()
        influence = self.runtime.PlannerInfluence.normalize(
            mood="chill", generation=1, confidence=0.7, freshness=0.9
        )

        replanned = horizon.replan(influence=influence)
        repeated = horizon.replan(influence=influence)

        self.assertEqual(replanned.generation, 1)
        self.assertIs(repeated, replanned)
        self.assertEqual(horizon.influence, influence)

    def test_planner_influence_is_runtime_internal_and_disposed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-influence"))
        assert created.planner.horizon is not None
        created.planner.horizon.replan(
            influence=self.runtime.PlannerInfluence.normalize(mood="chill", generation=1)
        )

        self.assertNotIn("influence", created.planner.as_dict())
        self.assertNotIn("influence", created.as_dict())

        asyncio.run(
            manager.async_end(owner_profile_id="profile-influence", session_id=created.session_id)
        )

        self.assertIsNone(asyncio.run(manager.async_get_active("profile-influence")))

    def test_knowledge_prefetch_is_created_for_a_planned_knowledge_intent(self) -> None:
        window = self.runtime.PlanningWindow(
            starts_at="now",
            ends_at="later",
            planning_coverage_seconds=120,
            generation=3,
            confidence=0.8,
            influence=self.runtime.PlannerInfluence.normalize(confidence=0.6, freshness=0.9),
            candidate_slots=(
                self.runtime.CandidatePlanningSlot("artist_story", 0, 60),
                self.runtime.CandidatePlanningSlot("silence", 60, 120),
            ),
        )
        window.plan_intents()

        prefetches = window.plan_knowledge_prefetches(invalidation_generation=4)

        self.assertEqual(len(prefetches), 1)
        prefetch = prefetches[0]
        self.assertEqual(prefetch.target_intent, window.planned_intents[0])
        self.assertEqual(prefetch.knowledge_category, "artist")
        self.assertEqual(prefetch.planning_generation, 3)
        self.assertEqual(prefetch.status, self.runtime.KnowledgePrefetchStatus.PLANNED)
        self.assertEqual((prefetch.knowledge_confidence, prefetch.freshness), (0.6, 0.9))
        self.assertEqual(prefetch.invalidation_generation, 4)

    def test_obsolete_planned_intent_invalidates_associated_prefetch(self) -> None:
        original = self.runtime.PlanningWindow(
            starts_at="now",
            ends_at="later",
            planning_coverage_seconds=60,
            generation=0,
            candidate_slots=(self.runtime.CandidatePlanningSlot("artist_story", 0, 60),),
        )
        original.plan_intents()
        original.plan_knowledge_prefetches(invalidation_generation=0)
        replacement = self.runtime.PlanningWindow(
            starts_at="now",
            ends_at="later",
            planning_coverage_seconds=60,
            generation=1,
            candidate_slots=(self.runtime.CandidatePlanningSlot("album_story", 0, 60),),
        )
        replacement.plan_intents()

        prefetches = replacement.plan_knowledge_prefetches(
            invalidation_generation=1,
            previous_prefetches=original.knowledge_prefetches,
        )

        self.assertEqual(
            [prefetch.status for prefetch in prefetches],
            [
                self.runtime.KnowledgePrefetchStatus.PLANNED,
                self.runtime.KnowledgePrefetchStatus.INVALIDATED,
            ],
        )
        self.assertEqual(prefetches[1].target_intent, original.planned_intents[0])
        self.assertEqual(prefetches[1].invalidation_generation, 1)

    def test_knowledge_prefetch_generation_is_deterministic(self) -> None:
        def build_prefetches():
            window = self.runtime.PlanningWindow(
                starts_at="now",
                ends_at="later",
                planning_coverage_seconds=60,
                generation=5,
                candidate_slots=(self.runtime.CandidatePlanningSlot("genre_story", 0, 60),),
            )
            window.plan_intents()
            return window.plan_knowledge_prefetches(invalidation_generation=7)

        first = build_prefetches()
        second = build_prefetches()

        self.assertEqual(first, second)
        self.assertEqual((first[0].planning_generation, first[0].invalidation_generation), (5, 7))

    def test_knowledge_prefetch_is_runtime_internal_and_disposed_with_runtime(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-prefetch"))
        assert created.planner.horizon is not None
        window = created.planner.horizon.build_planning_window()

        self.assertEqual(window.knowledge_prefetches, ())
        self.assertNotIn("knowledge_prefetches", created.planner.as_dict())
        self.assertNotIn("knowledge_prefetches", created.as_dict())
        self.assertNotIn("readiness_evaluations", created.planner.as_dict())
        self.assertNotIn("readiness_evaluations", created.as_dict())

        asyncio.run(
            manager.async_end(owner_profile_id="profile-prefetch", session_id=created.session_id)
        )

        self.assertIsNone(asyncio.run(manager.async_get_active("profile-prefetch")))

    def test_prefetch_execution_request_is_immutable_and_bounded(self) -> None:
        window = self._artist_prefetch_window()
        prefetch = window.knowledge_prefetches[0]

        request = self.runtime.KnowledgePrefetchRequest.from_prefetch(
            prefetch,
            subject_projection=(
                ("artist", "Artist"),
                ("ignored", "must not cross the boundary"),
            ),
        )

        self.assertEqual(request.target_category, "artist_story")
        self.assertEqual(request.planning_slot, ("artist_story", 0, 60))
        self.assertEqual(request.planning_generation, 2)
        self.assertEqual(request.knowledge_category, "artist")
        self.assertEqual(request.subject_projection, (("artist", "Artist"),))
        self.assertEqual(request.invalidation_generation, 4)

    def test_prefetch_execution_boundary_prepares_valid_available_knowledge(self) -> None:
        window = self._artist_prefetch_window()
        boundary = self.runtime.KnowledgePrefetchExecutionBoundary()

        prepared = boundary.submit(
            prefetch=window.knowledge_prefetches[0],
            subject_projection=(("artist", "Artist"),),
            window=window,
            invalidation_generation=4,
            knowledge_engine=self.runtime.DJKnowledgeEngine(),
        )

        self.assertEqual(prepared.status, self.runtime.PreparedKnowledgeStatus.PREPARED)
        self.assertEqual(prepared.projection, (("artist", "Artist"),))
        self.assertTrue(prepared.is_valid)
        self.assertEqual(prepared.planning_generation, 2)

    def test_prefetch_execution_rejects_superseded_or_unavailable_requirements(self) -> None:
        window = self._artist_prefetch_window()
        boundary = self.runtime.KnowledgePrefetchExecutionBoundary()
        engine = self.runtime.DJKnowledgeEngine()

        superseded = boundary.submit(
            prefetch=window.knowledge_prefetches[0],
            subject_projection=(("artist", "Artist"),),
            window=window,
            invalidation_generation=5,
            knowledge_engine=engine,
        )
        unavailable = boundary.submit(
            prefetch=window.knowledge_prefetches[0],
            subject_projection=(),
            window=window,
            invalidation_generation=4,
            knowledge_engine=engine,
        )

        self.assertEqual(superseded.status, self.runtime.PreparedKnowledgeStatus.SUPERSEDED)
        self.assertEqual(unavailable.status, self.runtime.PreparedKnowledgeStatus.UNAVAILABLE)
        self.assertEqual(engine.assembled_contexts, ())

    def test_readiness_evaluation_marks_valid_prepared_knowledge_ready(self) -> None:
        window = self._artist_prefetch_window()
        prepared = self.runtime.KnowledgePrefetchExecutionBoundary().submit(
            prefetch=window.knowledge_prefetches[0],
            subject_projection=(("artist", "Artist"),),
            window=window,
            invalidation_generation=4,
            knowledge_engine=self.runtime.DJKnowledgeEngine(),
        )

        evaluations = window.evaluate_readiness((prepared,), invalidation_generation=4)

        self.assertEqual(len(evaluations), 1)
        self.assertEqual(evaluations[0].status, self.runtime.ReadinessStatus.READY)
        self.assertTrue(evaluations[0].prepared_knowledge_available)
        self.assertTrue(evaluations[0].prepared_knowledge_valid)
        self.assertEqual(window.approve_earliest_planned_intent(), self.runtime.PlannerIntent("artist_story", 2))

    def test_readiness_evaluation_waits_for_required_prepared_knowledge(self) -> None:
        window = self._artist_prefetch_window()

        evaluation = window.evaluate_readiness(invalidation_generation=4)[0]

        self.assertEqual(evaluation.status, self.runtime.ReadinessStatus.WAITING)
        self.assertFalse(evaluation.prepared_knowledge_available)
        self.assertIsNone(window.approve_earliest_planned_intent())

    def test_readiness_evaluation_blocks_unavailable_prepared_knowledge(self) -> None:
        window = self._artist_prefetch_window()
        unavailable = self.runtime.PreparedKnowledge(
            "prefetch-artist-2-0-60",
            2,
            "artist",
            self.runtime.PreparedKnowledgeStatus.UNAVAILABLE,
        )

        evaluation = window.evaluate_readiness((unavailable,), invalidation_generation=4)[0]

        self.assertEqual(evaluation.status, self.runtime.ReadinessStatus.BLOCKED)
        self.assertEqual(evaluation.execution_status, self.runtime.PreparedKnowledgeStatus.UNAVAILABLE)

    def test_readiness_evaluation_distinguishes_unsupported_and_expired(self) -> None:
        window = self._artist_prefetch_window()
        unsupported = self.runtime.PreparedKnowledge(
            "prefetch-artist-2-0-60",
            2,
            "artist",
            self.runtime.PreparedKnowledgeStatus.UNSUPPORTED,
        )
        stale = self.runtime.PreparedKnowledge(
            "prefetch-artist-2-0-60",
            2,
            "artist",
            self.runtime.PreparedKnowledgeStatus.STALE,
        )

        self.assertEqual(
            window.evaluate_readiness((unsupported,), invalidation_generation=4)[0].status,
            self.runtime.ReadinessStatus.UNSUPPORTED,
        )
        self.assertEqual(
            window.evaluate_readiness((stale,), invalidation_generation=4)[0].status,
            self.runtime.ReadinessStatus.EXPIRED,
        )

    def test_readiness_evaluation_invalidates_superseded_intent_deterministically(self) -> None:
        window = self._artist_prefetch_window()
        planned = window.planned_intents[0]
        window.planned_intents = (
            self.runtime.PlannedIntent(
                planned.category,
                planned.slot,
                planned.generation,
                planned.confidence,
                self.runtime.PlannedIntentStatus.SUPERSEDED,
            ),
        )

        first = window.evaluate_readiness(invalidation_generation=4)
        second = window.evaluate_readiness(invalidation_generation=4)

        self.assertEqual(first, second)
        self.assertEqual(first[0].status, self.runtime.ReadinessStatus.INVALID)
        self.assertTrue(first[0].is_invalidated)

    def test_readiness_evaluation_invalidates_mismatched_planning_generation(self) -> None:
        window = self._artist_prefetch_window()
        mismatched = self.runtime.PreparedKnowledge(
            "prefetch-artist-2-0-60",
            1,
            "artist",
            self.runtime.PreparedKnowledgeStatus.PREPARED,
            projection=(("artist", "Artist"),),
            confidence=0.7,
            freshness=0.9,
            is_valid=True,
        )

        evaluation = window.evaluate_readiness((mismatched,), invalidation_generation=4)[0]

        self.assertEqual(evaluation.status, self.runtime.ReadinessStatus.INVALID)
        self.assertTrue(evaluation.is_invalidated)

    def test_readiness_is_runtime_internal_and_approval_accepts_only_evaluations(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-readiness"))
        parameters = inspect.signature(self.runtime.PlanningWindow.approve_earliest_planned_intent).parameters

        self.assertNotIn("readiness_evaluations", created.planner.as_dict())
        self.assertNotIn("readiness_evaluations", created.as_dict())
        self.assertNotIn("prepared_knowledge", parameters)

        asyncio.run(
            manager.async_end(owner_profile_id="profile-readiness", session_id=created.session_id)
        )

        self.assertIsNone(asyncio.run(manager.async_get_active("profile-readiness")))

    def _artist_prefetch_window(self):
        window = self.runtime.PlanningWindow(
            starts_at="now",
            ends_at="later",
            planning_coverage_seconds=60,
            generation=2,
            confidence=0.8,
            influence=self.runtime.PlannerInfluence.normalize(confidence=0.7, freshness=0.9),
            candidate_slots=(self.runtime.CandidatePlanningSlot("artist_story", 0, 60),),
        )
        window.plan_intents()
        window.plan_knowledge_prefetches(invalidation_generation=4)
        return window

    def test_horizon_replanning_is_a_no_op_for_unchanged_inputs(self) -> None:
        horizon = self.runtime.RollingSessionHorizon(
            window_minutes=15,
            created_at="now",
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),)
            ),
        )
        original = horizon.build_planning_window()

        replanned = horizon.replan()

        self.assertIs(replanned, original)
        self.assertEqual(replanned.generation, 0)

    def test_changed_upcoming_playback_creates_a_new_planning_generation(self) -> None:
        horizon = self.runtime.RollingSessionHorizon(
            window_minutes=15,
            created_at="now",
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),)
            ),
        )
        horizon.build_planning_window()

        replanned = horizon.replan(
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (
                    self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-b", duration_seconds=60),
                )
            )
        )

        self.assertEqual(replanned.generation, 1)
        self.assertEqual(len(replanned.planned_intents), 2)

    def test_replanning_supersedes_obsolete_provisional_intents_and_retains_valid_ones(self) -> None:
        horizon = self.runtime.RollingSessionHorizon(
            window_minutes=15,
            created_at="now",
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (
                    self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-b", duration_seconds=60),
                )
            ),
        )
        original = horizon.build_planning_window()

        extended = horizon.replan(
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (
                    self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-b", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-c", duration_seconds=60),
                )
            )
        )
        shortened = horizon.replan(
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=30),)
            )
        )

        self.assertIs(extended.planned_intents[0], original.planned_intents[0])
        self.assertTrue(
            any(
                intent.status is self.runtime.PlannedIntentStatus.SUPERSEDED
                for intent in shortened.planned_intents
            )
        )

    def test_replanning_preserves_approved_intent_and_does_not_recreate_consumed_slot(self) -> None:
        horizon = self.runtime.RollingSessionHorizon(
            window_minutes=15,
            created_at="now",
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (
                    self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-b", duration_seconds=60),
                )
            ),
        )
        original = horizon.build_planning_window()
        original.evaluate_readiness()
        approved = original.select_intent()
        assert approved is not None
        approved_planned = original.planned_intents[0]
        horizon.mark_planned_intent_consumed(original.planned_intents[1])

        replanned = horizon.replan(
            upcoming_playback=self.runtime.UpcomingPlaybackProjection.from_entries(
                (
                    self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-b", duration_seconds=60),
                    self.runtime.UpcomingPlaybackEntry("track-c", duration_seconds=60),
                )
            )
        )

        self.assertIn(approved_planned, replanned.planned_intents)
        self.assertEqual(replanned.approved_intent, approved)
        self.assertNotIn(
            ("silence", 60, 120),
            [(intent.category, intent.slot.starts_at_seconds, intent.slot.ends_at_seconds) for intent in replanned.planned_intents],
        )

    def test_replanning_is_deterministic_and_equivalent_replans_do_not_churn(self) -> None:
        projection = self.runtime.UpcomingPlaybackProjection.from_entries(
            (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=90),)
        )
        first = self.runtime.RollingSessionHorizon(window_minutes=15, created_at="now")
        second = self.runtime.RollingSessionHorizon(window_minutes=15, created_at="now")
        first.build_planning_window()
        second.build_planning_window()

        influence = self.runtime.PlannerInfluence.normalize(mood="chill")
        first_replan = first.replan(upcoming_playback=projection, influence=influence)
        second_replan = second.replan(upcoming_playback=projection, influence=influence)
        repeated = first.replan(upcoming_playback=projection, influence=influence)

        self.assertEqual(first_replan, second_replan)
        self.assertIs(repeated, first_replan)

    def test_empty_replan_keeps_session_flow_and_public_runtime_state_unchanged(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-replanning"))
        assert created.planner.horizon is not None
        horizon = created.planner.horizon
        horizon.upcoming_playback = self.runtime.UpcomingPlaybackProjection.from_entries(
            (self.runtime.UpcomingPlaybackEntry("track-a", duration_seconds=60),)
        )
        horizon.build_planning_window()
        flow_before = created.planner.output.session_flow
        public_before = created.planner.as_dict()

        replanned = horizon.replan(upcoming_playback=self.runtime.UpcomingPlaybackProjection())

        self.assertEqual(replanned.planning_coverage_seconds, 0)
        self.assertEqual(created.planner.output.session_flow, flow_before)
        self.assertEqual(created.planner.as_dict(), public_before)
        self.assertNotIn("horizon", created.as_dict()["planner"])

    def test_session_start_strategies_initialize_runtime_owned_direction(self) -> None:
        expected = {
            self.runtime.SessionStartStrategy.CONTINUE: "maintaining_energy",
            self.runtime.SessionStartStrategy.DISCOVER: "exploring",
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
            self.assertEqual(created.session_start_strategy, strategy)

    def test_start_strategies_initialize_deterministic_planner_configuration(self) -> None:
        expected = {
            self.runtime.SessionStartStrategy.CONTINUE: ("balanced", 60.0, "continuity"),
            self.runtime.SessionStartStrategy.DISCOVER: ("prefer", 60.0, "curious"),
            self.runtime.SessionStartStrategy.MANUAL: ("balanced", 60.0, "balanced"),
        }
        for strategy, (recommendations, minimum_interval, profile) in expected.items():
            manager = self.runtime.SessionRuntimeManager()
            created = asyncio.run(
                manager.async_start(
                    owner_profile_id=f"profile-{strategy.value}",
                    session_start_strategy=strategy,
                )
            )
            self.assertEqual(
                created.planner.configuration.recommendation_preference,
                recommendations,
            )
            self.assertEqual(
                created.planner.configuration.minimum_time_between_moments_seconds,
                minimum_interval,
            )
            self.assertEqual(created.interaction_profile, profile)

    def test_initial_session_mood_is_independent_from_strategy_and_persona(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                selected_mood="focus",
                dj_persona=self.runtime.DJPersona.FESTIVAL_DJ,
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )

        self.assertEqual(created.session_start_strategy, self.runtime.SessionStartStrategy.DISCOVER)
        self.assertEqual(created.initial_session_mood, "focus")
        self.assertEqual(created.selected_mood, "focus")
        self.assertEqual(created.dj_persona, self.runtime.DJPersona.FESTIVAL_DJ)
        self.assertEqual(created.session_direction.direction, self.runtime.SessionDirectionType.EXPLORING)
        self.assertEqual(created.as_dict()["initial_session_mood"], "focus")

        updated = asyncio.run(
            manager.async_update_mood(
                owner_profile_id="profile-a",
                session_id=created.session_id,
                selected_mood="party",
            )
        )
        assert updated is not None
        self.assertEqual(updated.initial_session_mood, "focus")
        self.assertEqual(updated.selected_mood, "party")

    def test_continue_strategy_is_explicit_and_uses_ephemeral_fallback(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        asyncio.run(manager.async_end(owner_profile_id="profile-a", session_id=first.session_id))
        continued = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                session_start_strategy=self.runtime.SessionStartStrategy.CONTINUE,
            )
        )

        self.assertEqual(
            continued.session_start_strategy, self.runtime.SessionStartStrategy.CONTINUE
        )
        self.assertEqual(
            continued.session_direction.direction,
            self.runtime.SessionDirectionType.MAINTAINING_ENERGY,
        )
        self.assertEqual(continued.performance_memory.recent_moment_ids, ())

    def test_session_start_strategy_is_immutable_runtime_state(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                selected_mood="ambient",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )

        with self.assertRaises(FrozenInstanceError):
            created.session_start_strategy = self.runtime.SessionStartStrategy.MANUAL  # type: ignore[misc]

    def test_discover_strategy_prefers_recommendation_over_manual_track_context(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        discover = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-discover",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
        manual = asyncio.run(manager.async_start(owner_profile_id="profile-manual"))
        hints = {
            "related_tracks": "Angel",
            "artist": "Massive Attack",
            "producer": "Neil Davidge",
            "genre": "trip-hop",
        }

        discover_decision = discover.planner.evaluate_track_started(
            session_start_strategy=discover.session_start_strategy,
            session_direction=discover.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=discover.performance_memory,
            discover_context=discover.discover_context,
        )
        manual_decision = manual.planner.evaluate_track_started(
            session_direction=manual.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=manual.performance_memory,
            discover_context=manual.discover_context,
        )

        self.assertEqual(
            discover_decision.decision_type,
            self.runtime.PlannerDecisionType.CREATE_RECOMMENDATION,
        )
        self.assertEqual(discover_decision.reason, "discover_knowledge_hint:related_tracks")
        self.assertEqual(
            manual_decision.decision_type,
            self.runtime.PlannerDecisionType.CREATE_ARTIST_STORY,
        )

    def test_planner_spaces_an_immediately_previous_recommendation_when_context_allows(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-discover",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
        hints = {
            "related_tracks": "Sour Times",
            "artist": "Portishead",
            "producer": "Geoff Barrow",
            "genre": "trip-hop",
        }
        memory = self.runtime.PerformanceMemory(
            "flow-test", recent_moment_types=(self.runtime.DJMomentType.RECOMMENDATION,)
        )

        first = created.planner.evaluate_track_started(
            session_start_strategy=created.session_start_strategy,
            session_direction=created.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=memory,
            discover_context=created.discover_context,
        )
        second = created.planner.evaluate_track_started(
            session_start_strategy=created.session_start_strategy,
            session_direction=created.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=memory,
            discover_context=created.discover_context,
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first.decision_type, self.runtime.PlannerDecisionType.CREATE_ARTIST_STORY
        )
        self.assertEqual(first.reason, "discover_knowledge_hint:producer")

    def test_planner_retains_recommendation_when_spacing_has_no_valid_alternative(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-discover",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
        decision = created.planner.evaluate_track_started(
            session_start_strategy=created.session_start_strategy,
            session_direction=created.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints={"related_tracks": "Sour Times"},
            performance_memory=self.runtime.PerformanceMemory(
                "flow-test",
                recent_moment_types=(self.runtime.DJMomentType.RECOMMENDATION,),
            ),
            discover_context=created.discover_context,
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_RECOMMENDATION
        )
        self.assertNotEqual(decision.decision_type, self.runtime.PlannerDecisionType.SILENCE)

    def test_personal_discover_context_avoids_familiar_artist(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        context = self.runtime.DiscoverContext(
            personal_context_authorized=True,
            familiar_artists=("Massive Attack",),
        )
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
                discover_context=context,
            )
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
            performance_memory=created.performance_memory,
            discover_context=created.discover_context,
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_GENRE_STORY
        )
        self.assertTrue(created.discover_context.personal_context_authorized)

    def test_community_discover_session_uses_no_personal_context(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )

        decision = created.planner.evaluate_track_started(
            session_direction=created.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints={"related_tracks": "Angel", "artist": "Massive Attack"},
            performance_memory=created.performance_memory,
            discover_context=created.discover_context,
        )

        self.assertFalse(created.discover_context.personal_context_authorized)
        self.assertEqual(
            decision.decision_type,
            self.runtime.PlannerDecisionType.CREATE_RECOMMENDATION,
        )

    def test_discover_combines_performance_memory_with_recommendation_diversity(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
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
                "producer": "Neil Davidge",
                "genre": "trip-hop",
            },
            performance_memory=memory,
            discover_context=created.discover_context,
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_ARTIST_STORY
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

    def test_planner_recovers_direction_after_two_consecutive_silences(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))

        decision = created.planner.evaluate_track_started(
            session_direction=created.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            performance_memory=self.runtime.PerformanceMemory(
                "flow-test",
                recent_moment_types=(
                    self.runtime.DJMomentType.SILENCE,
                    self.runtime.DJMomentType.SILENCE,
                ),
            ),
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_SESSION_UPDATE
        )
        self.assertEqual(decision.reason, "recent_silence_recovery")
        self.assertEqual(
            decision.proposed_session_direction, self.runtime.SessionDirectionType.RESETTING
        )

    def test_planner_returns_after_the_immediately_preceding_resetting_update(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-a"))
        resetting = self.runtime.SessionDirection(
            self.runtime.SessionDirectionType.RESETTING,
            "then",
            "now",
            self.runtime.SessionStartStrategy.MANUAL,
        )

        decision = created.planner.evaluate_track_started(
            session_direction=resetting,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            performance_memory=self.runtime.PerformanceMemory(
                "flow-test",
                recent_moment_types=(self.runtime.DJMomentType.SESSION,),
                recent_session_directions=(self.runtime.SessionDirectionType.RESETTING,),
            ),
        )

        self.assertEqual(
            decision.decision_type, self.runtime.PlannerDecisionType.CREATE_SESSION_UPDATE
        )
        self.assertEqual(decision.reason, "resetting_session_return")
        self.assertEqual(
            decision.proposed_session_direction, self.runtime.SessionDirectionType.RETURNING
        )

    def test_planner_combines_all_orthogonal_runtime_dimensions(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        manual = asyncio.run(manager.async_start(owner_profile_id="profile-manual"))
        discover = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-discover",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
        hints = {
            "related_tracks": "Angel",
            "artist": "Massive Attack",
            "producer": "Neil Davidge",
            "album": "Mezzanine",
            "release_year": "1998",
            "genre": "trip-hop",
        }
        deepening = self.runtime.SessionDirection(
            self.runtime.SessionDirectionType.DEEPENING,
            "now",
            "now",
            self.runtime.SessionStartStrategy.MANUAL,
        )
        building = self.runtime.SessionDirection(
            self.runtime.SessionDirectionType.BUILDING_ENERGY,
            "now",
            "now",
            self.runtime.SessionStartStrategy.MANUAL,
        )

        manual_decision = manual.planner.evaluate_track_started(
            session_start_strategy=manual.session_start_strategy,
            session_direction=manual.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=manual.performance_memory,
        )
        discover_decision = discover.planner.evaluate_track_started(
            session_start_strategy=discover.session_start_strategy,
            session_direction=discover.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=discover.performance_memory,
        )
        direction_decision = manual.planner.evaluate_track_started(
            session_start_strategy=manual.session_start_strategy,
            session_direction=deepening,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=manual.performance_memory,
        )
        persona_decision = manual.planner.evaluate_track_started(
            session_start_strategy=manual.session_start_strategy,
            session_direction=manual.session_direction,
            selected_mood="groove",
            persona=self.runtime.DJPersona.RADIO_DJ,
            knowledge_hints=hints,
            performance_memory=manual.performance_memory,
        )
        festival_decision = manual.planner.evaluate_track_started(
            session_start_strategy=manual.session_start_strategy,
            session_direction=building,
            selected_mood="groove",
            persona=self.runtime.DJPersona.FESTIVAL_DJ,
            knowledge_hints=hints,
            performance_memory=manual.performance_memory,
        )
        mood_decision = manual.planner.evaluate_track_started(
            session_start_strategy=manual.session_start_strategy,
            session_direction=building,
            selected_mood="party",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=manual.performance_memory,
        )
        deep_mood_decision = manual.planner.evaluate_track_started(
            session_start_strategy=manual.session_start_strategy,
            session_direction=deepening,
            selected_mood="deep",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=self.runtime.PerformanceMemory(
                "flow-test", recent_silence_count=2
            ),
        )
        memory_decision = manual.planner.evaluate_track_started(
            session_start_strategy=manual.session_start_strategy,
            session_direction=deepening,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            knowledge_hints=hints,
            performance_memory=self.runtime.PerformanceMemory(
                "flow-test", recent_albums=("Mezzanine",)
            ),
        )

        self.assertEqual(manual_decision.decision_type, self.runtime.PlannerDecisionType.CREATE_ARTIST_STORY)
        self.assertEqual(discover_decision.decision_type, self.runtime.PlannerDecisionType.CREATE_RECOMMENDATION)
        self.assertEqual(direction_decision.decision_type, self.runtime.PlannerDecisionType.CREATE_ALBUM_STORY)
        self.assertEqual(persona_decision.decision_type, self.runtime.PlannerDecisionType.CREATE_ALBUM_STORY)
        self.assertEqual(festival_decision.decision_type, self.runtime.PlannerDecisionType.CREATE_RECOMMENDATION)
        self.assertEqual(mood_decision.decision_type, self.runtime.PlannerDecisionType.CREATE_RECOMMENDATION)
        self.assertEqual(deep_mood_decision.decision_type, self.runtime.PlannerDecisionType.CREATE_ALBUM_STORY)
        self.assertEqual(memory_decision.decision_type, self.runtime.PlannerDecisionType.CREATE_ARTIST_STORY)

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
        self.assertEqual(state["broadcast"]["snapshot_watermark"], 2)
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

    def test_flow_revision_and_journal_record_only_semantic_flow_changes(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        planner = created.planner

        self.assertEqual(planner.output.session_flow.flow_revision, 0)
        self.assertEqual(
            [(entry.revision, entry.change_type.value) for entry in planner.flow_change_journal],
            [(0, "initialized")],
        )
        with self.assertRaises(FrozenInstanceError):
            planner.output.session_flow.flow_revision = 1  # type: ignore[misc]

        created.submit_audience_signal(self.runtime.AudienceSignalType.MORE_ENERGY)
        self.assertEqual(planner.output.session_flow.flow_revision, 0)
        self.assertEqual(len(planner.flow_change_journal), 1)

        republished = created.republish_session_flow()
        moment = created.moment_engine.create_silence(
            session_id=created.session_id,
            selected_mood=created.selected_mood,
            persona=created.dj_persona,
            locale=created.locale,
            reason="flow_revision_test",
        )
        created.publish_moment(moment)

        self.assertEqual(republished.flow_revision, 1)
        self.assertEqual(planner.output.session_flow.flow_revision, 2)
        self.assertEqual(
            [(entry.revision, entry.change_type.value) for entry in planner.flow_change_journal],
            [(0, "initialized"), (1, "republished"), (2, "moment_appended")],
        )
        self.assertEqual(
            [entry.flow.flow_revision for entry in planner.flow_change_journal], [0, 1, 2]
        )

    def test_flow_journal_is_runtime_scoped_and_broadcast_never_mutates_it(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        first = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        first.republish_session_flow()
        planner = first.planner
        flow = planner.output.session_flow
        journal = planner.flow_change_journal

        first.broadcast.publish_session_flow(flow)
        self.assertEqual(planner.output.session_flow.flow_revision, 1)
        self.assertEqual(planner.flow_change_journal, journal)
        self.assertEqual(first.broadcast.as_dict()["session_flow"]["flow_revision"], 1)

        ended = asyncio.run(manager.async_end(owner_profile_id="profile-peter", session_id=first.session_id))
        assert ended is not None
        self.assertEqual(ended.planner.flow_change_journal, ())
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-peter")))

        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        self.assertNotEqual(second.session_id, first.session_id)
        self.assertEqual(second.planner.output.session_flow.flow_revision, 0)
        self.assertEqual(
            [entry.revision for entry in second.planner.flow_change_journal], [0]
        )

    def test_broadcast_delivery_identity_is_independent_and_runtime_scoped(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        broadcast = created.broadcast

        self.assertEqual(broadcast.delivery_sequence, 2)
        self.assertEqual(
            [entry.delivery_sequence for entry in broadcast.replay_log], [1, 2]
        )
        self.assertEqual(broadcast.as_dict()["broadcast"]["snapshot_watermark"], 2)
        cursor = broadcast.recovery_cursor
        assert cursor is not None
        self.assertEqual(
            (
                cursor.session_id,
                cursor.delivery_sequence,
                cursor.snapshot_watermark,
                cursor.authorization_scope,
            ),
            (
                created.session_id,
                2,
                2,
                self.runtime.BroadcastAuthorizationScope.OWNER,
            ),
        )
        self.assertIn(cursor.delivery_sequence, [entry.delivery_sequence for entry in broadcast.replay_log])
        self.assertGreaterEqual(len(cursor.opaque_value), 32)
        self.assertNotIn(cursor.opaque_value, broadcast.as_dict())
        with self.assertRaises(FrozenInstanceError):
            cursor.delivery_sequence = 3  # type: ignore[misc]

        created.planner.republish_session_flow()
        self.assertEqual(created.planner.output.session_flow.flow_revision, 1)
        self.assertEqual(broadcast.delivery_sequence, 2)
        self.assertIs(broadcast.recovery_cursor, cursor)

        broadcast.as_dict()
        broadcast.as_dict()
        broadcast.subscribe(lambda _event: None)
        self.assertEqual(broadcast.delivery_sequence, 2)

        created.republish_session_flow()
        self.assertEqual(created.planner.output.session_flow.flow_revision, 2)
        self.assertEqual(broadcast.delivery_sequence, 4)
        assert broadcast.recovery_cursor is not None
        self.assertEqual(broadcast.recovery_cursor.delivery_sequence, 4)
        self.assertEqual(broadcast.recovery_cursor.snapshot_watermark, 4)
        self.assertEqual(
            [entry.delivery_sequence for entry in broadcast.replay_log], [1, 2, 3, 4]
        )
        self.assertEqual(broadcast.as_dict()["broadcast"]["snapshot_watermark"], 4)

        ended = asyncio.run(
            manager.async_end(owner_profile_id="profile-peter", session_id=created.session_id)
        )
        assert ended is not None
        self.assertEqual(ended.broadcast.delivery_sequence, 0)
        self.assertEqual(ended.broadcast.replay_log, ())
        self.assertIsNone(ended.broadcast.recovery_cursor)
        self.assertEqual(ended.broadcast.as_dict()["broadcast"]["snapshot_watermark"], 0)

        second = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        assert second.broadcast.recovery_cursor is not None
        self.assertNotEqual(second.broadcast.recovery_cursor.session_id, cursor.session_id)

    def test_broadcast_replay_log_is_bounded_and_entries_are_immutable(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        broadcast = self.runtime.DJSessionBroadcastEngine(
            state=created.broadcast.state, replay_log_limit=2
        )

        self.assertEqual(broadcast.delivery_sequence, 0)
        self.assertEqual(broadcast.as_dict()["broadcast"]["snapshot_watermark"], 0)
        broadcast._publish(self.runtime.BroadcastEventType.PLANNER_UPDATED, {"planner": {"value": 1}})
        broadcast._publish(self.runtime.BroadcastEventType.AUDIENCE_UPDATED, {"audience": {"value": 2}})
        broadcast._publish(self.runtime.BroadcastEventType.MOOD_CHANGED, {"session": {"value": 3}})

        self.assertEqual(broadcast.delivery_sequence, 3)
        self.assertEqual(
            [entry.delivery_sequence for entry in broadcast.replay_log], [2, 3]
        )
        assert broadcast.recovery_cursor is not None
        self.assertEqual(broadcast.recovery_cursor.delivery_sequence, 3)
        self.assertIn(
            broadcast.recovery_cursor.delivery_sequence,
            [entry.delivery_sequence for entry in broadcast.replay_log],
        )
        with self.assertRaises(FrozenInstanceError):
            broadcast.replay_log[0].delivery_sequence = 9  # type: ignore[misc]

    def test_broadcast_owner_recovery_replays_only_the_bounded_runtime_log(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        broadcast = created.broadcast
        cursor = broadcast.owner_recovery_cursor()
        assert cursor is not None

        created.republish_session_flow()
        recovery = broadcast.recover_owner(cursor)
        assert recovery is not None
        self.assertEqual(recovery["recovery"], "replayed")
        self.assertEqual(
            [event["event_type"] for event in recovery["events"]],
            ["planner_updated", "session_flow_updated"],
        )
        self.assertEqual(recovery["snapshot_watermark"], broadcast.delivery_sequence)
        self.assertNotIn("delivery_sequence", recovery)
        self.assertNotIn("replay_log", recovery)
        self.assertNotEqual(recovery["recovery_cursor"], cursor)
        self.assertIsNone(broadcast.recover_owner("invalid"))

        other = asyncio.run(manager.async_start(owner_profile_id="profile-other"))
        cross_session = other.broadcast.recover_owner(cursor)
        assert cross_session is not None
        self.assertEqual(cross_session["recovery"], "snapshot_required")
        self.assertEqual(cross_session["snapshot"]["session"]["session_id"], other.session_id)

    def test_broadcast_owner_recovery_falls_back_after_replay_log_eviction(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        broadcast = self.runtime.DJSessionBroadcastEngine(
            state=created.broadcast.state, replay_log_limit=2
        )
        broadcast._publish(self.runtime.BroadcastEventType.PLANNER_UPDATED, {"planner": {"value": 1}})
        expired_cursor = broadcast.owner_recovery_cursor()
        assert expired_cursor is not None
        broadcast._publish(self.runtime.BroadcastEventType.AUDIENCE_UPDATED, {"audience": {"value": 2}})
        broadcast._publish(self.runtime.BroadcastEventType.MOOD_CHANGED, {"session": {"value": 3}})

        recovery = broadcast.recover_owner(expired_cursor)
        assert recovery is not None
        self.assertEqual(recovery["recovery"], "snapshot_required")
        self.assertEqual(recovery["snapshot"]["broadcast"]["snapshot_watermark"], 3)

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

    def test_broadcast_registration_without_snapshot_preserves_live_delivery_and_cleanup(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        received: list[dict] = []
        snapshot = created.broadcast.as_dict

        def fail_if_snapshot_is_constructed():
            raise AssertionError("snapshot construction is not part of registration")

        created.broadcast.as_dict = fail_if_snapshot_is_constructed
        subscription_id = asyncio.run(
            manager.async_register_subscription(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=received.append,
            )
        )
        self.assertIsNotNone(subscription_id)
        self.assertEqual(created.broadcast.subscriber_count, 1)

        created.broadcast.as_dict = snapshot
        created.republish_session_flow()
        self.assertEqual(
            [event["event_type"] for event in received],
            ["planner_updated", "session_flow_updated"],
        )
        asyncio.run(
            manager.async_unsubscribe(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                subscription_id=subscription_id,
            )
        )
        self.assertEqual(created.broadcast.subscriber_count, 0)

    def test_pending_broadcast_subscriptions_buffer_events_until_each_snapshot_is_sent(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-peter"))
        first_events: list[dict] = []
        second_events: list[dict] = []
        first = asyncio.run(
            manager.async_register_pending_subscription(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=first_events.append,
            )
        )
        second = asyncio.run(
            manager.async_register_pending_subscription(
                owner_profile_id="profile-peter",
                session_id=created.session_id,
                callback=second_events.append,
            )
        )
        assert first is not None and second is not None

        created.republish_session_flow()
        self.assertEqual(first_events, [])
        self.assertEqual(second_events, [])

        asyncio.run(
            manager.async_activate_subscription(
                owner_profile_id="profile-peter", session_id=created.session_id, subscription_id=first
            )
        )
        self.assertEqual(
            [event["event_type"] for event in first_events],
            ["planner_updated", "session_flow_updated"],
        )
        self.assertEqual(second_events, [])
        asyncio.run(
            manager.async_activate_subscription(
                owner_profile_id="profile-peter", session_id=created.session_id, subscription_id=second
            )
        )
        self.assertEqual(
            [event["event_type"] for event in second_events],
            ["planner_updated", "session_flow_updated"],
        )

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

    def test_runtime_uses_one_insight_for_contextual_planner_intents(self) -> None:
        cases = (
            ("artist", self.runtime.SessionStartStrategy.MANUAL, {"producer": "Producer"}, self.runtime.DJMomentType.ARTIST, "track", "producer"),
            ("album", self.runtime.SessionStartStrategy.MANUAL, {"release_year": "1998"}, self.runtime.DJMomentType.ALBUM, "track", "release_year"),
            ("genre", self.runtime.SessionStartStrategy.MANUAL, {}, self.runtime.DJMomentType.GENRE, "analysis", "genre"),
            ("recommendation", self.runtime.SessionStartStrategy.DISCOVER, {"related_tracks": "Angel"}, self.runtime.DJMomentType.RECOMMENDATION, "track", "related_tracks"),
        )
        for name, strategy, metadata, expected_type, evidence_source, evidence_key in cases:
            with self.subTest(name=name):
                manager = self.runtime.SessionRuntimeManager()
                created = asyncio.run(
                    manager.async_start(
                        owner_profile_id=f"profile-{name}",
                        session_start_strategy=strategy,
                    )
                )
                calls = 0

                async def insight() -> dict:
                    nonlocal calls
                    calls += 1
                    return {
                        "track": {
                            "title": "Teardrop",
                            "artist": "Massive Attack",
                            "album": "Mezzanine",
                            "genres": ["trip-hop"],
                            **metadata,
                        },
                        "analysis": {
                            "summary": "A spacious trip-hop landmark.",
                            "full_text": "The suspended beat leaves room for the bass.",
                            "genre": "trip-hop",
                        },
                    }

                moment = asyncio.run(
                    manager.async_process_track_started(
                        owner_profile_id=created.owner_profile_id,
                        session_id=created.session_id,
                        insight_provider=insight,
                    )
                )

                assert moment is not None
                self.assertEqual(calls, 1)
                self.assertEqual(moment.moment_type, expected_type)
                context = created.knowledge_engine.assembled_contexts[-1].as_insight()
                self.assertIn(evidence_key, context[evidence_source])
                self.assertEqual(
                    moment.knowledge_intent.intent_type.value,
                    expected_type.value + "_story" if expected_type is not self.runtime.DJMomentType.RECOMMENDATION else "recommendation",
                )
                self.assertIn(
                    moment.moment_id,
                    [item.moment_id for item in created.planner.output.session_flow.items],
                )
                self.assertEqual(
                    created.broadcast.as_dict()["dj_moments"][-1]["moment_id"], moment.moment_id
                )

    def test_runtime_performance_memory_prevents_repeated_discover_recommendation(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-discover",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )

        insight_calls = 0

        async def insight() -> dict:
            nonlocal insight_calls
            insight_calls += 1
            return {
                "track": {
                    "title": "Teardrop" if insight_calls == 1 else "Angel",
                    "artist": "Massive Attack",
                    "genres": ["trip-hop"],
                    "related_tracks": "Angel",
                },
                "analysis": {
                    "summary": "A spacious trip-hop landmark.",
                    "full_text": "The suspended beat leaves room for the bass.",
                    "genre": "trip-hop",
                },
            }

        first = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )
        created.planner.last_spoken_moment_at = 0.0
        second = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )

        assert first is not None and second is not None
        self.assertEqual(first.moment_type, self.runtime.DJMomentType.RECOMMENDATION)
        self.assertEqual(second.moment_type, self.runtime.DJMomentType.GENRE)

    def test_runtime_spaces_discover_recommendations_without_changing_delivery_owners(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-spacing",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
        insight_calls = 0

        async def insight() -> dict:
            nonlocal insight_calls
            insight_calls += 1
            if insight_calls == 1:
                return {
                    "track": {
                        "title": "Teardrop",
                        "artist": "Massive Attack",
                        "related_tracks": "Angel",
                    },
                    "analysis": {"summary": "A recommendation.", "full_text": "Safe context."},
                }
            return {
                "track": {
                    "title": "Roads",
                    "artist": "Portishead",
                    "producer": "Geoff Barrow",
                    "related_tracks": "Sour Times",
                },
                "analysis": {"summary": "Artist context.", "full_text": "Safe context."},
            }

        first = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )
        active = asyncio.run(manager.async_get_active(created.owner_profile_id))
        assert active is not None
        active.planner.last_spoken_moment_at = 0.0
        second = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )
        active = asyncio.run(manager.async_get_active(created.owner_profile_id))

        assert first is not None and second is not None and active is not None
        self.assertEqual(insight_calls, 2)
        self.assertEqual(first.moment_type, self.runtime.DJMomentType.RECOMMENDATION)
        self.assertEqual(second.moment_type, self.runtime.DJMomentType.ARTIST)
        self.assertEqual(active.performance_memory.recent_moment_types[-2:], (first.moment_type, second.moment_type))
        self.assertEqual(
            [item.moment_id for item in active.planner.output.session_flow.items if item.moment_id][-2:],
            [first.moment_id, second.moment_id],
        )
        self.assertEqual(active.broadcast.as_dict()["dj_moments"][-1]["moment_id"], second.moment_id)
        self.assertEqual(len(active.knowledge_engine.assembled_contexts), 2)
        self.assertEqual(len(active.moment_engine.moments), 2)

    def test_track_started_publishes_one_planner_approved_transition(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-transition",
                selected_mood="groove",
                dj_persona=self.runtime.DJPersona.RADIO_DJ,
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
        events: list[dict] = []
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                callback=events.append,
            )
        )
        calls = 0

        async def insight() -> dict:
            nonlocal calls
            calls += 1
            if calls == 1:
                return {
                    "track": {"title": "Teardrop", "artist": "Massive Attack", "producer": "Neil Davidge"},
                    "analysis": {"summary": "A landmark.", "full_text": "A detailed artist context."},
                }
            return {
                "track": {"title": "Roads", "artist": "Portishead", "related_tracks": "Sour Times"},
                "analysis": {"summary": "A related discovery.", "full_text": "A detailed recommendation context."},
            }

        first = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )
        created.planner.last_spoken_moment_at = 0.0
        second = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )

        assert first is not None and second is not None
        transition = created.moment_engine.moments[-1]
        self.assertEqual(calls, 2)
        self.assertEqual(first.moment_type, self.runtime.DJMomentType.ARTIST)
        self.assertEqual(second.moment_type, self.runtime.DJMomentType.RECOMMENDATION)
        self.assertEqual(transition.moment_type, self.runtime.DJMomentType.TRANSITION)
        self.assertEqual(
            created.planner.last_decision.decision_type,
            self.runtime.PlannerDecisionType.CREATE_TRANSITION,
        )
        self.assertEqual(transition.presentation_intent.source_session_mood, "groove")
        self.assertEqual(transition.presentation_intent.dj_persona, self.runtime.DJPersona.RADIO_DJ)
        self.assertEqual(
            dict(transition.generation_metadata)["transition_from_moment_id"], first.moment_id
        )
        self.assertEqual(
            dict(transition.generation_metadata)["transition_to_moment_id"], second.moment_id
        )
        flow_moments = [
            item for item in created.planner.output.session_flow.items
            if item.item_type is self.runtime.SessionFlowItemType.DJ_MOMENT
        ]
        self.assertEqual([item.moment_id for item in flow_moments[-2:]], [second.moment_id, transition.moment_id])
        self.assertEqual(flow_moments[-1].position, self.runtime.SessionFlowPosition.NEXT)
        self.assertEqual(created.broadcast.as_dict()["dj_moments"][-1]["moment_id"], transition.moment_id)
        self.assertEqual(
            [
                event["event_type"]
                for event in events
                if event["event_type"] in {"session_flow_updated", "dj_moment_published"}
            ][-4:],
            ["session_flow_updated", "dj_moment_published", "session_flow_updated", "dj_moment_published"],
        )
        with self.assertRaises(FrozenInstanceError):
            transition.title = "Mutated"

    def test_transition_no_approval_is_silent_and_repetition_is_prevented(self) -> None:
        engine = self.runtime.DJMomentEngine()
        rejected = engine.create_transition(
            session_id="session-transition",
            approval=None,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="en",
        )
        self.assertEqual(rejected.moment_type, self.runtime.DJMomentType.SILENCE)
        invalid = engine.create_transition(
            session_id="session-transition",
            approval=self.runtime.PlannerDecision(
                self.runtime.PlannerDecisionType.CREATE_TRANSITION,
                "invalid",
                self.runtime.KnowledgeIntent(
                    self.runtime.KnowledgeIntentType.TRANSITION, "Invalid approval."
                ),
                transition_moment_ids=("missing-one", "missing-two"),
                transition_placement="next",
            ),
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="en",
        )
        self.assertEqual(invalid.moment_type, self.runtime.DJMomentType.SILENCE)

        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-transition-repeat",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
        responses = iter(
            (
                {
                    "track": {"title": "First", "artist": "Artist One", "producer": "Producer"},
                    "analysis": {"summary": "Artist context.", "full_text": "Artist full context."},
                },
                {
                    "track": {"title": "Second", "artist": "Artist Two", "related_tracks": "Related"},
                    "analysis": {"summary": "Recommendation.", "full_text": "Recommendation full context."},
                },
                {
                    "track": {"title": "Third", "artist": "Artist Three", "related_tracks": "Related"},
                    "analysis": {"summary": "Recommendation.", "full_text": "Recommendation full context."},
                },
            )
        )

        async def insight() -> dict:
            return next(responses)

        for _ in range(2):
            asyncio.run(
                manager.async_process_track_started(
                    owner_profile_id=created.owner_profile_id,
                    session_id=created.session_id,
                    insight_provider=insight,
                )
            )
            created.planner.last_spoken_moment_at = 0.0
        moments_before = len(created.moment_engine.moments)
        third = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )

        assert third is not None
        self.assertEqual(third.moment_type, self.runtime.DJMomentType.RECOMMENDATION)
        self.assertEqual(len(created.moment_engine.moments), moments_before + 1)
        self.assertEqual(created.planner.last_decision.decision_type, self.runtime.PlannerDecisionType.NO_TRANSITION)
        self.assertEqual(created.moment_engine.moments[-1].moment_type, self.runtime.DJMomentType.RECOMMENDATION)

    def test_track_context_can_precede_an_exploring_recommendation_transition(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-track-transition",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
            )
        )
        calls = 0

        async def insight() -> dict:
            nonlocal calls
            calls += 1
            if calls == 1:
                return {
                    "track": {"title": "First Track", "artist": "First Artist"},
                    "analysis": {"summary": "Track context.", "full_text": "Track context detail."},
                }
            return {
                "track": {"title": "Second Track", "artist": "Second Artist", "related_tracks": "Related"},
                "analysis": {"summary": "Recommendation.", "full_text": "Recommendation detail."},
            }

        first = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )
        created.planner.last_spoken_moment_at = 0.0
        second = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )

        assert first is not None and second is not None
        transition = created.moment_engine.moments[-1]
        self.assertEqual(calls, 2)
        self.assertEqual(first.moment_type, self.runtime.DJMomentType.TRACK)
        self.assertEqual(second.moment_type, self.runtime.DJMomentType.RECOMMENDATION)
        self.assertEqual(transition.moment_type, self.runtime.DJMomentType.TRANSITION)
        self.assertEqual(
            dict(transition.generation_metadata)["transition_from_moment_id"], first.moment_id
        )
        self.assertEqual(
            dict(transition.generation_metadata)["transition_to_moment_id"], second.moment_id
        )
        flow_moments = [
            item
            for item in created.planner.output.session_flow.items
            if item.item_type is self.runtime.SessionFlowItemType.DJ_MOMENT
        ]
        self.assertEqual(
            [item.moment_id for item in flow_moments[-2:]],
            [second.moment_id, transition.moment_id],
        )
        self.assertEqual(created.broadcast.as_dict()["dj_moments"][-1]["moment_id"], transition.moment_id)
        with self.assertRaises(FrozenInstanceError):
            transition.content = "Mutated"

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
        self.assertNotIn("release_year", dict(context.track))
        self.assertNotIn("instrumentation", dict(context.analysis))
        self.assertFalse(context.personal_context_used)
        self.assertNotIn("music_dna", context.as_insight())
        self.assertEqual(
            context.as_insight()["performance_memory"]["source_flow_id"],
            f"flow-{created.session_id}",
        )
        self.assertEqual(context.as_insight()["session_start_strategy"], "manual")
        self.assertNotIn("session_mood", context.as_insight())
        self.assertEqual(moment.source_references, ("track_insight",))

    def test_knowledge_engine_consumes_matching_prepared_knowledge(self) -> None:
        planned, prefetch, prepared = self._approved_artist_prefetch()
        engine = self.runtime.DJKnowledgeEngine()

        context = asyncio.run(
            engine.async_resolve_approved_planned_intent(
                approved_intent=planned.as_planner_intent(),
                planned_intent=planned,
                knowledge_intent=self.runtime.KnowledgeIntent(
                    self.runtime.KnowledgeIntentType.ARTIST_STORY, "Share artist context."
                ),
                prefetch=prefetch,
                prepared_knowledge=(prepared,),
                invalidation_generation=4,
                raw_insight={"track": {"producer": "Fallback producer"}},
            )
        )

        self.assertEqual(context.sources, ("prepared_knowledge",))
        self.assertEqual(context.track, (("artist", "Prepared Artist"),))
        self.assertEqual(prepared.projection, (("artist", "Prepared Artist"),))

    def test_knowledge_engine_falls_back_when_prepared_knowledge_is_not_usable(self) -> None:
        unusable_statuses = (
            self.runtime.PreparedKnowledgeStatus.UNAVAILABLE,
            self.runtime.PreparedKnowledgeStatus.INVALID,
            self.runtime.PreparedKnowledgeStatus.STALE,
            self.runtime.PreparedKnowledgeStatus.UNSUPPORTED,
            self.runtime.PreparedKnowledgeStatus.CANCELLED,
            self.runtime.PreparedKnowledgeStatus.SUPERSEDED,
        )
        for status in unusable_statuses:
            with self.subTest(status=status):
                planned, prefetch, prepared = self._approved_artist_prefetch(status=status)
                context = asyncio.run(
                    self.runtime.DJKnowledgeEngine().async_resolve_approved_planned_intent(
                        approved_intent=planned.as_planner_intent(),
                        planned_intent=planned,
                        knowledge_intent=self.runtime.KnowledgeIntent(
                            self.runtime.KnowledgeIntentType.ARTIST_STORY,
                            "Share artist context.",
                        ),
                        prefetch=prefetch,
                        prepared_knowledge=(prepared,),
                        invalidation_generation=4,
                        raw_insight={"track": {"producer": "Fallback producer"}},
                    )
                )

                self.assertEqual(context.sources, ("track_insight",))
                self.assertEqual(dict(context.track)["producer"], "Fallback producer")

    def test_knowledge_engine_rejects_stale_and_superseded_prepared_knowledge(self) -> None:
        planned, prefetch, stale = self._approved_artist_prefetch(
            status=self.runtime.PreparedKnowledgeStatus.STALE
        )
        _, _, superseded_generation = self._approved_artist_prefetch(planning_generation=1)
        engine = self.runtime.DJKnowledgeEngine()
        arguments = dict(
            approved_intent=planned.as_planner_intent(),
            planned_intent=planned,
            knowledge_intent=self.runtime.KnowledgeIntent(
                self.runtime.KnowledgeIntentType.ARTIST_STORY, "Share artist context."
            ),
            prefetch=prefetch,
            invalidation_generation=4,
            raw_insight={"track": {"producer": "Fallback producer"}},
        )

        stale_context = asyncio.run(
            engine.async_resolve_approved_planned_intent(
                **arguments, prepared_knowledge=(stale,)
            )
        )
        superseded_context = asyncio.run(
            engine.async_resolve_approved_planned_intent(
                **arguments, prepared_knowledge=(superseded_generation,)
            )
        )

        self.assertEqual(stale_context.sources, ("track_insight",))
        self.assertEqual(superseded_context.sources, ("track_insight",))

    def test_knowledge_engine_rejects_invalid_prepared_subject_deterministically(self) -> None:
        planned, prefetch, prepared = self._approved_artist_prefetch()
        invalid_subject = self.runtime.PreparedKnowledge(
            prepared.request_id,
            prepared.planning_generation,
            prepared.knowledge_category,
            self.runtime.PreparedKnowledgeStatus.PREPARED,
            projection=(("album", "Wrong subject"),),
            confidence=prepared.confidence,
            freshness=prepared.freshness,
            is_valid=True,
        )
        engine = self.runtime.DJKnowledgeEngine()
        arguments = dict(
            approved_intent=planned.as_planner_intent(),
            planned_intent=planned,
            knowledge_intent=self.runtime.KnowledgeIntent(
                self.runtime.KnowledgeIntentType.ARTIST_STORY, "Share artist context."
            ),
            prefetch=prefetch,
            prepared_knowledge=(invalid_subject,),
            invalidation_generation=4,
            raw_insight={"track": {"producer": "Fallback producer"}},
        )

        first = asyncio.run(engine.async_resolve_approved_planned_intent(**arguments))
        second = asyncio.run(engine.async_resolve_approved_planned_intent(**arguments))

        self.assertEqual(first, second)
        self.assertEqual(first.sources, ("track_insight",))

    def test_prepared_knowledge_consumption_is_runtime_scoped(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-prepared-consumption"))
        planned, prefetch, prepared = self._approved_artist_prefetch()
        asyncio.run(
            created.knowledge_engine.async_resolve_approved_planned_intent(
                approved_intent=planned.as_planner_intent(),
                planned_intent=planned,
                knowledge_intent=self.runtime.KnowledgeIntent(
                    self.runtime.KnowledgeIntentType.ARTIST_STORY, "Share artist context."
                ),
                prefetch=prefetch,
                prepared_knowledge=(prepared,),
                invalidation_generation=4,
                raw_insight={},
            )
        )

        self.assertNotIn("prepared_knowledge", created.as_dict())
        asyncio.run(
            manager.async_end(
                owner_profile_id="profile-prepared-consumption", session_id=created.session_id
            )
        )
        self.assertIsNone(asyncio.run(manager.async_get_active("profile-prepared-consumption")))

    def _approved_artist_prefetch(self, *, status=None, planning_generation: int = 2):
        status = status or self.runtime.PreparedKnowledgeStatus.PREPARED
        slot = self.runtime.CandidatePlanningSlot("artist_story", 0, 60)
        planned = self.runtime.PlannedIntent(
            "artist_story",
            slot,
            2,
            0.8,
            self.runtime.PlannedIntentStatus.APPROVED,
        )
        prefetch = self.runtime.KnowledgePrefetch(
            self.runtime.PlannedIntent("artist_story", slot, 2, 0.8),
            "artist",
            2,
            self.runtime.KnowledgePrefetchStatus.PLANNED,
            0.7,
            0.9,
            4,
        )
        request_id = self.runtime.KnowledgePrefetchRequest.from_prefetch(
            prefetch, subject_projection=()
        ).request_id
        prepared = self.runtime.PreparedKnowledge(
            request_id,
            planning_generation,
            "artist",
            status,
            projection=(("artist", "Prepared Artist"),),
            confidence=0.7,
            freshness=0.9,
            is_valid=status is self.runtime.PreparedKnowledgeStatus.PREPARED,
        )
        return planned, prefetch, prepared

    def test_knowledge_engine_selects_metadata_by_planner_intent(self) -> None:
        engine = self.runtime.DJKnowledgeEngine()
        raw_insight = {
            "track": {
                "title": "Teardrop",
                "artist": "Massive Attack",
                "album": "Mezzanine",
                "genres": ["trip-hop"],
                "producer": "Neil Davidge",
                "composer": "Massive Attack",
                "release_year": "1998",
                "recording_context": "Recorded in London.",
                "related_artists": "Portishead",
                "related_tracks": "Angel",
            },
            "analysis": {
                "summary": "A spacious trip-hop landmark.",
                "full_text": "The suspended beat leaves room for the bass.",
                "genre": "trip-hop",
                "subgenre": "downtempo",
                "production_notes": "Layered drums.",
                "similar_tracks": "Glory Box",
            },
        }
        cases = (
            (self.runtime.KnowledgeIntentType.ARTIST_STORY, "track", "producer", "Neil Davidge", "composer"),
            (self.runtime.KnowledgeIntentType.ALBUM_STORY, "track", "release_year", "1998", "release_date"),
            (self.runtime.KnowledgeIntentType.GENRE_STORY, "analysis", "genre", "trip-hop", "subgenre"),
            (self.runtime.KnowledgeIntentType.RECOMMENDATION, "track", "related_tracks", "Angel", "related_artists"),
        )

        for intent_type, selected_source, selected_key, selected_value, excluded_key in cases:
            with self.subTest(intent_type=intent_type):
                context = asyncio.run(
                    engine.async_assemble_track_context(
                        intent=self.runtime.KnowledgeIntent(intent_type, "test"),
                        raw_insight=raw_insight,
                    )
                )
                selected = context.as_insight()[selected_source]
                self.assertEqual(selected[selected_key], selected_value)
                self.assertNotIn(excluded_key, selected)
                evidence = {
                    key: value
                    for source in ("track", "analysis")
                    for key, value in context.as_insight()[source].items()
                    if key not in {"title", "artist", "album", "artwork_url", "backend", "summary", "full_text"}
                }
                self.assertEqual(evidence, {selected_key: selected_value})

    def test_knowledge_engine_uses_next_safe_primary_evidence_deterministically(self) -> None:
        engine = self.runtime.DJKnowledgeEngine()
        intent = self.runtime.KnowledgeIntent(
            self.runtime.KnowledgeIntentType.ARTIST_STORY, "Share artist context."
        )
        raw_insight = {
            "track": {
                "title": "Teardrop",
                "artist": "Massive Attack",
                "producer": {"unsafe": "payload"},
                "composer": "Massive Attack",
                "recording_context": "Recorded in London.",
            },
            "analysis": {"summary": "Safe.", "full_text": "Safe context."},
        }

        first = asyncio.run(engine.async_assemble_track_context(intent=intent, raw_insight=raw_insight))
        second = asyncio.run(engine.async_assemble_track_context(intent=intent, raw_insight=raw_insight))

        self.assertEqual(first, second)
        self.assertEqual(dict(first.track)["composer"], "Massive Attack")
        self.assertNotIn("producer", dict(first.track))
        self.assertNotIn("recording_context", dict(first.track))

    def test_knowledge_engine_missing_intent_metadata_preserves_safe_silence(self) -> None:
        engine = self.runtime.DJKnowledgeEngine()
        intent = self.runtime.KnowledgeIntent(
            self.runtime.KnowledgeIntentType.ARTIST_STORY, "Share artist context."
        )
        context = asyncio.run(
            engine.async_assemble_track_context(
                intent=intent,
                raw_insight={
                    "track": {"title": "Teardrop", "artist": "Massive Attack"},
                    "analysis": {"summary": "Safe.", "full_text": "Safe context."},
                },
            )
        )
        moment = self.runtime.DJMomentEngine().create_track_context(
            session_id="session-test",
            knowledge_intent=intent,
            selected_mood="groove",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="en",
            insight=context.as_insight(),
        )

        self.assertEqual(context.as_insight()["track"], {})
        self.assertEqual(context.as_insight()["analysis"], {})
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.SILENCE)

    def test_moment_engine_realizes_stage_two_knowledge_contexts_immutably(self) -> None:
        engine = self.runtime.DJMomentEngine()
        runtime = self.runtime.SessionRuntimeManager()
        contexts = (
            (
                self.runtime.KnowledgeIntentType.ARTIST_STORY,
                self.runtime.DJMomentType.ARTIST,
                "Artist One",
                {"composer": "Composer One"},
                {},
            ),
            (
                self.runtime.KnowledgeIntentType.ALBUM_STORY,
                self.runtime.DJMomentType.ALBUM,
                "Album Two",
                {"album": "Album Two", "release_year": "1998"},
                {},
            ),
            (
                self.runtime.KnowledgeIntentType.GENRE_STORY,
                self.runtime.DJMomentType.GENRE,
                "trip-hop",
                {"genres": "trip-hop"},
                {"genre": "trip-hop"},
            ),
            (
                self.runtime.KnowledgeIntentType.RECOMMENDATION,
                self.runtime.DJMomentType.RECOMMENDATION,
                "Explore beyond Artist Four",
                {"related_artists": "Portishead"},
                {},
            ),
        )

        for index, (intent_type, expected_type, expected_title, track_context, analysis_context) in enumerate(contexts, start=1):
            with self.subTest(intent_type=intent_type):
                context = self.runtime.KnowledgeContext(
                    track=tuple(
                        {
                            "title": f"Track {index}",
                            "artist": f"Artist {['One', 'Two', 'Three', 'Four'][index - 1]}",
                            **track_context,
                        }.items()
                    ),
                    analysis=tuple(
                        {
                            "summary": "A safe selected summary.",
                            "full_text": "A safe selected full context.",
                            **analysis_context,
                        }.items()
                    ),
                    sources=("track_insight",),
                )
                before_runtime = tuple(runtime._active_by_profile.items())
                moment = engine.create_track_context(
                    session_id="session-stage-two",
                    knowledge_intent=self.runtime.KnowledgeIntent(intent_type, "Selected by Planner."),
                    selected_mood="deep",
                    persona=self.runtime.DJPersona.RADIO_DJ,
                    locale="en",
                    insight=context.as_insight(),
                )

                self.assertEqual(moment.moment_type, expected_type)
                self.assertEqual(moment.title, expected_title)
                self.assertEqual(moment.presentation_intent.source_session_mood, "deep")
                self.assertEqual(moment.presentation_intent.dj_persona, self.runtime.DJPersona.RADIO_DJ)
                self.assertEqual(moment.source_references, ("track_insight",))
                self.assertEqual(tuple(runtime._active_by_profile.items()), before_runtime)
                with self.assertRaises(FrozenInstanceError):
                    moment.title = "Mutated"

        recommendation = engine.moments[-1]
        self.assertEqual(
            tuple(action.action_type for action in recommendation.actions),
            ("play_recommendation", "save_recommendation"),
        )

    def test_moment_engine_is_deterministic_and_silences_invalid_selected_context(self) -> None:
        intent = self.runtime.KnowledgeIntent(
            self.runtime.KnowledgeIntentType.ARTIST_STORY, "Selected by Planner."
        )
        valid_insight = {
            "track": {"title": "Track", "artist": "Artist", "composer": "Composer"},
            "analysis": {"summary": "Safe summary.", "full_text": "Safe full context."},
        }
        first = self.runtime.DJMomentEngine().create_track_context(
            session_id="session-stage-two",
            knowledge_intent=intent,
            selected_mood="focus",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="en",
            insight=valid_insight,
        )
        second = self.runtime.DJMomentEngine().create_track_context(
            session_id="session-stage-two",
            knowledge_intent=intent,
            selected_mood="focus",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="en",
            insight=valid_insight,
        )
        self.assertEqual(
            (first.moment_type, first.title, first.summary, first.content, first.actions, first.presentation_intent),
            (second.moment_type, second.title, second.summary, second.content, second.actions, second.presentation_intent),
        )

        silence = self.runtime.DJMomentEngine().create_track_context(
            session_id="session-stage-two",
            knowledge_intent=intent,
            selected_mood="focus",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="en",
            insight={
                "track": {"title": "Track", "artist": "Artist"},
                "analysis": {"summary": "Safe summary.", "full_text": "Safe full context."},
            },
        )
        self.assertEqual(silence.moment_type, self.runtime.DJMomentType.SILENCE)
        self.assertEqual(silence.presentation_intent, first.presentation_intent)

    def test_discover_knowledge_context_includes_only_safe_personal_projection(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                selected_mood="ambient",
                session_start_strategy=self.runtime.SessionStartStrategy.DISCOVER,
                discover_context=self.runtime.DiscoverContext(
                    personal_context_authorized=True,
                    familiar_artists=("Massive Attack",),
                    familiar_genres=("trip-hop",),
                ),
            )
        )

        async def insight() -> dict:
            return {
                "track": {"title": "Roads", "artist": "Portishead"},
                "analysis": {"summary": "A quiet classic.", "full_text": "Sparse and intimate."},
            }

        asyncio.run(
            manager.async_process_track_started(
                owner_profile_id="profile-a",
                session_id=created.session_id,
                insight_provider=insight,
            )
        )
        context = created.knowledge_engine.assembled_contexts[-1]

        self.assertEqual(context.as_insight()["session_start_strategy"], "discover")
        self.assertEqual(context.as_insight()["session_mood"], "ambient")
        self.assertEqual(
            context.as_insight()["discover_context"],
            {
                "personal_context_authorized": True,
                "familiar_artists": ["Massive Attack"],
                "familiar_genres": ["trip-hop"],
            },
        )
        self.assertNotIn("music_dna", context.as_insight())

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
        self.assertEqual(dict(moment.generation_metadata)["context_source"], "session_direction")
        self.assertEqual(
            dict(moment.generation_metadata)["start_strategy"],
            active.session_start_strategy.value,
        )
        self.assertEqual(
            active.planner.output.session_flow.items[-1].moment_id, moment.moment_id
        )
        self.assertEqual(active.broadcast.as_dict()["dj_moments"][-1]["moment_id"], moment.moment_id)
        self.assertEqual(
            [
                event["event_type"]
                for event in events
                if event["event_type"] in {"session_flow_updated", "dj_moment_published"}
            ][-2:],
            ["session_flow_updated", "dj_moment_published"],
        )
        with self.assertRaises(FrozenInstanceError):
            moment.summary = "Mutated"

    def test_session_update_requires_safe_knowledge_context(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        engine = self.runtime.DJMomentEngine()
        direction = self.runtime.SessionDirection(
            self.runtime.SessionDirectionType.BUILDING_ENERGY,
            "now",
            "now",
            self.runtime.SessionStartStrategy.MANUAL,
        )
        before_runtime = tuple(manager._active_by_profile.items())
        moment = engine.create_session_update(
            session_id="session-test",
            selected_mood="energy",
            persona=self.runtime.DJPersona.HOME_DJ,
            locale="en",
            session_direction=direction,
            knowledge_context=None,
        )

        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.SILENCE)
        self.assertEqual(tuple(manager._active_by_profile.items()), before_runtime)

    def test_no_direction_change_emits_no_session_update(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-no-update"))
        calls = 0

        async def insight() -> dict:
            nonlocal calls
            calls += 1
            return {
                "track": {"title": "Track", "artist": "Artist"},
                "analysis": {"summary": "Safe summary.", "full_text": "Safe full context."},
            }

        moment = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=insight,
            )
        )

        assert moment is not None
        self.assertEqual(calls, 1)
        self.assertNotEqual(moment.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertNotIn(
            self.runtime.DJMomentType.SESSION,
            tuple(item.moment_type for item in created.planner.output.session_flow.items if item.moment_id),
        )

    def test_two_consecutive_silences_trigger_one_resetting_session_update(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-resetting"))
        calls = 0

        async def invalid_insight() -> dict:
            return {}

        for _ in range(2):
            silence = asyncio.run(
                manager.async_process_track_started(
                    owner_profile_id=created.owner_profile_id,
                    session_id=created.session_id,
                    insight_provider=invalid_insight,
                )
            )
            assert silence is not None
            self.assertEqual(silence.moment_type, self.runtime.DJMomentType.SILENCE)

        events: list[dict] = []
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                callback=events.append,
            )
        )

        async def provider() -> dict:
            nonlocal calls
            calls += 1
            return {}

        update = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=provider,
            )
        )

        assert update is not None
        self.assertEqual(calls, 0)
        self.assertEqual(update.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(
            update.generation_metadata[0], ("direction", self.runtime.SessionDirectionType.RESETTING.value)
        )
        self.assertEqual(
            created.planner.last_decision.reason, "recent_silence_recovery"
        )
        self.assertEqual(created.planner.output.session_flow.items[-1].moment_id, update.moment_id)
        self.assertEqual(created.broadcast.as_dict()["dj_moments"][-1]["moment_id"], update.moment_id)
        self.assertEqual(
            [
                event["event_type"]
                for event in events
                if event["event_type"] in {"session_flow_updated", "dj_moment_published"}
            ],
            ["session_flow_updated", "dj_moment_published"],
        )

    def test_resetting_update_is_followed_once_by_a_returning_update(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(manager.async_start(owner_profile_id="profile-returning"))

        async def invalid_insight() -> dict:
            return {}

        for _ in range(2):
            silence = asyncio.run(
                manager.async_process_track_started(
                    owner_profile_id=created.owner_profile_id,
                    session_id=created.session_id,
                    insight_provider=invalid_insight,
                )
            )
            assert silence is not None
            self.assertEqual(silence.moment_type, self.runtime.DJMomentType.SILENCE)

        resetting = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=invalid_insight,
            )
        )
        assert resetting is not None
        self.assertEqual(
            dict(resetting.generation_metadata)["direction"],
            self.runtime.SessionDirectionType.RESETTING.value,
        )
        events: list[dict] = []
        asyncio.run(
            manager.async_subscribe(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                callback=events.append,
            )
        )
        created.planner.last_spoken_moment_at = 0
        calls = 0

        async def provider() -> dict:
            nonlocal calls
            calls += 1
            return {}

        returning = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=provider,
            )
        )
        active = asyncio.run(manager.async_get_active(created.owner_profile_id))

        assert returning is not None and active is not None
        self.assertEqual(calls, 0)
        self.assertEqual(returning.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(
            dict(returning.generation_metadata)["direction"],
            self.runtime.SessionDirectionType.RETURNING.value,
        )
        self.assertEqual(created.planner.last_decision.reason, "resetting_session_return")
        self.assertEqual(active.session_direction.direction, self.runtime.SessionDirectionType.RETURNING)
        self.assertEqual(active.planner.output.session_flow.items[-1].moment_id, returning.moment_id)
        self.assertEqual(active.broadcast.as_dict()["dj_moments"][-1]["moment_id"], returning.moment_id)
        self.assertEqual(
            [
                event["event_type"]
                for event in events
                if event["event_type"] in {"session_flow_updated", "dj_moment_published"}
            ],
            ["session_flow_updated", "dj_moment_published"],
        )
        with self.assertRaises(FrozenInstanceError):
            returning.title = "Mutated"

        created.planner.last_spoken_moment_at = 0
        next_moment = asyncio.run(
            manager.async_process_track_started(
                owner_profile_id=created.owner_profile_id,
                session_id=created.session_id,
                insight_provider=provider,
            )
        )
        assert next_moment is not None
        self.assertNotEqual(next_moment.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertEqual(calls, 1)

    def test_later_mood_and_persona_changes_do_not_mutate_existing_moment(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                selected_mood="deep",
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

    def test_planner_updates_direction_before_knowledge_for_deep_session(self) -> None:
        manager = self.runtime.SessionRuntimeManager()
        created = asyncio.run(
            manager.async_start(
                owner_profile_id="profile-a",
                selected_mood="deep",
            )
        )
        invoked = False

        async def insight() -> dict:
            nonlocal invoked
            invoked = True
            return {}

        moment = asyncio.run(manager.async_process_track_started(owner_profile_id="profile-a", session_id=created.session_id, insight_provider=insight))
        assert moment is not None
        self.assertEqual(moment.moment_type, self.runtime.DJMomentType.SESSION)
        self.assertFalse(invoked)
        self.assertEqual(
            created.planner.last_decision.decision_type,
            self.runtime.PlannerDecisionType.CREATE_SESSION_UPDATE,
        )

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
