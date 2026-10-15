"""Active mood ordering and the existing asynchronous candidate decision boundary."""

from __future__ import annotations

import asyncio
import copy
import sys
import unittest
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module
from tests import test_vibecast_multimoment as multimoment


class ActiveSessionMoodRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("custom_components.djconnect.session_runtime", None)
        if cls.previous_const is None:
            sys.modules.pop("custom_components.djconnect.const", None)
        else:
            sys.modules["custom_components.djconnect.const"] = cls.previous_const

    def test_cas_noop_two_clients_and_immutable_session(self):
        async def scenario():
            manager = self.runtime.SessionRuntimeManager()
            session = await manager.async_start(owner_profile_id="owner", selected_mood="groove")
            events = []
            await manager.async_subscribe(
                owner_profile_id="owner", session_id=session.session_id, callback=events.append
            )
            same = await manager.async_update_mood(
                owner_profile_id="owner",
                session_id=session.session_id,
                selected_mood="groove",
                expected_revision=0,
            )
            self.assertEqual(same.mood_revision, 0)
            self.assertEqual(events, [])
            results = await asyncio.gather(
                *[
                    manager.async_update_mood(
                        owner_profile_id="owner",
                        session_id=session.session_id,
                        selected_mood=mood,
                        expected_revision=0,
                    )
                    for mood in ("energy", "party")
                ],
                return_exceptions=True,
            )
            self.assertEqual(
                sum(isinstance(r, self.runtime.MoodRevisionConflictError) for r in results), 1
            )
            current = await manager.async_get_active("owner")
            self.assertEqual(current.mood_revision, 1)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["payload"]["session"]["mood_revision"], 1)
            self.assertEqual(current.session_id, session.session_id)
            self.assertEqual(current.started_at, session.started_at)
            self.assertEqual(current.initial_session_mood, "groove")
            self.assertEqual(current.broadcast.state.dj_moments, ())
            with self.assertRaises(self.runtime.MoodRevisionConflictError):
                await manager.async_update_mood(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    selected_mood=current.selected_mood,
                    expected_revision=0,
                )

        asyncio.run(scenario())

    def test_final_authority_check_after_lock_wait(self):
        async def scenario():
            manager = self.runtime.SessionRuntimeManager()
            session = await manager.async_start(owner_profile_id="owner", selected_mood="groove")
            valid = [True]
            await manager._lock.acquire()
            pending = asyncio.create_task(
                manager.async_update_mood(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    selected_mood="energy",
                    expected_revision=0,
                    authorize=lambda: valid[0],
                )
            )
            await asyncio.sleep(0)
            valid[0] = False
            manager._lock.release()
            with self.assertRaises(PermissionError):
                await pending
            current = await manager.async_get_active("owner")
            self.assertEqual((current.selected_mood, current.mood_revision), ("groove", 0))

        asyncio.run(scenario())

    async def _unpublished_current_track(self):
        manager = self.runtime.SessionRuntimeManager()
        session = await manager.async_start(owner_profile_id="owner", selected_mood="groove")
        previous = "spotify:track:" + "A" * 22
        current = "spotify:track:" + "B" * 22

        async def insight():
            return {
                "track": {"title": "Current", "artist": "Artist", "album": "Album"},
                "analysis": {
                    "summary": "A bounded synthetic summary.",
                    "full_text": "A synthetic source-shaped musical context.",
                },
            }

        await manager.async_update_playback_projection(
            owner_profile_id="owner",
            session_id=session.session_id,
            state="playing",
            media_identity=previous,
            title="Previous",
            artist="Artist",
            duration_ms=300000,
            position_ms=0,
        )
        await manager.async_process_track_started(
            owner_profile_id="owner",
            session_id=session.session_id,
            media_identity=previous,
            require_current_playback=True,
            insight_provider=insight,
        )
        await manager.async_update_playback_projection(
            owner_profile_id="owner",
            session_id=session.session_id,
            state="playing",
            media_identity=current,
            title="Current",
            artist="Artist",
            album="Album",
            duration_ms=300000,
            position_ms=0,
        )
        return manager, session, previous, current, insight

    revision_field = "mood_revision"

    async def _aba(self, manager, session):
        for mood in ("energy", "groove"):
            await manager.async_update_mood(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                selected_mood=mood,
            )

    def test_coordinator_aba_drops_copy_and_retries_same_observed_track(self):
        async def scenario():
            manager, session, previous, current, insight = await self._unpublished_current_track()
            entered = asyncio.Event()
            release = asyncio.Event()
            original = self.runtime.PlanningRuntimeCoordinator.async_coordinate_track_started

            async def delayed(coordinator, **kwargs):
                entered.set()
                await release.wait()
                return await original(coordinator, **kwargs)

            baseline = session.planner.as_dict()
            with patch.object(
                self.runtime.PlanningRuntimeCoordinator, "async_coordinate_track_started", delayed
            ):
                pending = asyncio.create_task(
                    manager.async_process_track_started(
                        owner_profile_id="owner",
                        session_id=session.session_id,
                        media_identity=current,
                        require_current_playback=True,
                        insight_provider=insight,
                    )
                )
                await asyncio.wait_for(entered.wait(), 2)
                await self._aba(manager, session)
                release.set()
                self.assertIsNone(await pending)
            active = await manager.async_get_active("owner")
            self.assertEqual(active.last_accepted_media_identity, previous)
            self.assertEqual(active.planner.as_dict(), baseline)
            self.assertEqual(active.broadcast.state.dj_moments, ())
            self.assertEqual(active.moment_engine._expression_forms, ())
            retry = await manager.async_process_track_started(
                owner_profile_id="owner",
                session_id=session.session_id,
                media_identity=current,
                require_current_playback=True,
                insight_provider=insight,
            )
            self.assertIsNotNone(retry)
            self.assertEqual(retry.presentation_intent.source_session_mood, "groove")
            self.assertEqual(getattr(await manager.async_get_active("owner"), self.revision_field), 2)

        asyncio.run(scenario())

    def test_fallback_aba_has_no_candidate_consumption_and_same_track_retry(self):
        async def scenario():
            manager, session, previous, current, insight = await self._unpublished_current_track()
            entered = asyncio.Event()
            release = asyncio.Event()
            original = self.runtime.DJKnowledgeEngine.async_assemble_track_context

            async def delayed(engine, **kwargs):
                entered.set()
                await release.wait()
                return await original(engine, **kwargs)

            with patch.object(
                self.runtime.PlanningRuntimeCoordinator,
                "async_coordinate_track_started",
                side_effect=RuntimeError("synthetic coordinator failure"),
            ):
                with patch.object(
                    self.runtime.DJKnowledgeEngine, "async_assemble_track_context", delayed
                ):
                    pending = asyncio.create_task(
                        manager.async_process_track_started(
                            owner_profile_id="owner",
                            session_id=session.session_id,
                            media_identity=current,
                            require_current_playback=True,
                            insight_provider=insight,
                        )
                    )
                    await asyncio.wait_for(entered.wait(), 2)
                    active = await manager.async_get_active("owner")
                    baseline = copy.deepcopy(active.planner.as_dict())
                    knowledge = copy.deepcopy(active.knowledge_engine.__dict__)
                    await self._aba(manager, session)
                    release.set()
                    self.assertIsNone(await pending)
                active = await manager.async_get_active("owner")
                self.assertEqual(active.last_accepted_media_identity, previous)
                self.assertEqual(active.planner.as_dict(), baseline)
                self.assertEqual(active.knowledge_engine.__dict__, knowledge)
                self.assertEqual(active.moment_engine._expression_forms, ())
                retry = await manager.async_process_track_started(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    media_identity=current,
                    require_current_playback=True,
                    insight_provider=insight,
                )
                self.assertIsNotNone(retry)
                self.assertEqual(retry.presentation_intent.source_session_mood, "groove")

        asyncio.run(scenario())

    def test_intra_track_aba_releases_pending_without_spending_opportunity(self):
        async def scenario():
            helper = multimoment.VibeCastMultiMomentTest()
            helper.runtime = self.runtime
            manager, session, first, media_id, now = await helper._ready()
            await helper._observe(manager, session, media_id, now, seconds=45, position_ms=45000)
            entered = asyncio.Event()
            release = asyncio.Event()
            original = self.runtime.DJKnowledgeEngine.async_assemble_track_context

            async def delayed(engine, **kwargs):
                entered.set()
                await release.wait()
                return await original(engine, **kwargs)

            with patch.object(
                self.runtime.DJKnowledgeEngine, "async_assemble_track_context", delayed
            ):
                pending = asyncio.create_task(helper._later(manager, session, media_id))
                await asyncio.wait_for(entered.wait(), 2)
                await self._aba(manager, session)
                release.set()
                self.assertIsNone(await pending)
            opportunity = manager._intra_track_opportunities[session.owner_profile_id]
            self.assertFalse(opportunity.pending)
            self.assertFalse(opportunity.spent)
            self.assertEqual(session.broadcast.state.dj_moments, (first,))
            retry = await helper._later(manager, session, media_id)
            self.assertIsNotNone(retry)
            self.assertEqual(retry.presentation_intent.source_session_mood, "groove")

        asyncio.run(scenario())
