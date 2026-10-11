"""Publication accounting, owner ordering and async presence fences."""
import asyncio
import copy
import json
import sys
import unittest
from dataclasses import replace

from tests.test_session_runtime import _load_runtime_module
from tests import test_contextual_fact_planning as contextual
from tests import test_session_facts as source_tests


class SessionPresenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if cls.previous_const is not None:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const
        else:
            sys.modules.pop('custom_components.djconnect.const',None)

    async def rich_trace(self, mode):
        now = [100.0]
        manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: now[0])
        session = await manager.async_start(owner_profile_id='owner', selected_mood='groove', locale='nl')
        await manager.async_update_presence(owner_profile_id='owner', session_id=session.session_id,
                                          selected_presence=mode, expected_revision=0)
        fixture = contextual.ContextualFactPlanningTest()
        fixture.runtime = self.runtime
        from custom_components.djconnect import session_facts
        fixture.facts = session_facts
        pool = fixture.pool()
        catalog = source_tests.SessionFactsTest.catalog(fixture)
        work = fixture.facts.work_facts(catalog, {"relations": [{"type": "performance", "target-type": "work", "work": {
            "id": "00000000-0000-0000-0000-000000000003",
            "relations": [{"type": "composer", "target-type": "artist", "artist": {"name": "Fixture composer"}}],
        }}]})[0]
        receipts = []
        for track in range(4):
            media = 'spotify:track:' + chr(ord('A') + track) * 22
            facts = tuple(replace(f, media_identity=media, source_url=f.source_url.replace('00000000-0000-0000-0000',f'0000000{track}-0000-0000-0000')) for f in (*pool, work))
            async def insight():
                return {'_qualified_facts': facts}
            for pos in range(0, 151000, 15000):
                now[0] = 100 + track * 180 + pos / 1000
                await manager.async_update_playback_projection(owner_profile_id='owner', session_id=session.session_id,
                    state='playing',media_identity=media,title=catalog['title'],artist=catalog['artist'],
                    album=catalog['album_name'],duration_ms=180000,position_ms=pos)
                if pos == 0:
                    moment = await manager.async_process_track_started(owner_profile_id='owner',session_id=session.session_id,
                        insight_provider=insight,media_identity=media,require_current_playback=True,allow_initial_facts=True)
                else:
                    moment = await manager.async_maybe_publish_intra_track_moment(owner_profile_id='owner',session_id=session.session_id,media_identity=media)
                if moment:
                    receipts.append((track * 180 + pos / 1000,moment.moment_type.value))
        active = await manager.async_get_active('owner')
        return receipts, active, manager

    def test_same_rich_trace_five_actual_publication_counts(self):
        async def scenario():
            from custom_components.djconnect.presence_policy import POLICIES
            rows = {}
            for mode in POLICIES:
                receipts, active, _ = await self.rich_trace(mode)
                rows[mode] = receipts
                self.assertEqual(len(receipts), active.presence_ledger.total_published)
                self.assertEqual(len(receipts), len(active.broadcast.state.dj_moments))
                self.assertTrue(all(len(active.presence_ledger.publications) <= 16 for _ in [0]))
            self.assertEqual([len(v) for v in rows.values()], [0, 2, 6, 10, 13], rows)
        asyncio.run(scenario())

    def test_cas_noop_and_no_budget_reset_or_old_content_change(self):
        async def scenario():
            _, active, manager = await self.rich_trace('balanced')
            frozen = json.dumps(active.broadcast.as_dict()['dj_moments'],sort_keys=True)
            ledger = copy.deepcopy(active.presence_ledger.__dict__)
            old = (active.session_id,active.started_at,active.selected_mood,active.dj_persona,active.broadcast.state.playback)
            for mode in ('presenter','music_only','balanced','balanced'):
                active = await manager.async_update_presence(owner_profile_id='owner',session_id=active.session_id,
                    selected_presence=mode,expected_revision=active.presence_revision)
            self.assertEqual(active.presence_revision, 3)
            self.assertEqual(active.presence_ledger.__dict__,ledger)
            self.assertEqual(json.dumps(active.broadcast.as_dict()['dj_moments'],sort_keys=True),frozen)
            self.assertEqual((active.session_id,active.started_at,active.selected_mood,active.dj_persona,active.broadcast.state.playback),old)
            with self.assertRaises(self.runtime.PresenceRevisionConflictError):
                await manager.async_update_presence(owner_profile_id='owner',session_id=active.session_id,selected_presence='balanced',expected_revision=0)
        asyncio.run(scenario())

    def test_insight_inflight_off_on_aba_no_late_publication(self):
        async def scenario():
            manager = self.runtime.SessionRuntimeManager()
            session = await manager.async_start(owner_profile_id='owner', selected_mood='groove')
            entered, release = asyncio.Event(), asyncio.Event()
            async def insight():
                entered.set()
                await release.wait()
                return {'track':{'title':'Synthetic','artist':'Artist'},'analysis':{'summary':'Synthetic context','full_text':'Bounded fixture context'}}
            task = asyncio.create_task(manager.async_process_track_started(owner_profile_id='owner',session_id=session.session_id,media_identity='',insight_provider=insight))
            await asyncio.wait_for(entered.wait(),2)
            for mode in ('music_only','presenter'):
                await manager.async_update_presence(owner_profile_id='owner',session_id=session.session_id,selected_presence=mode)
            release.set()
            self.assertIsNone(await task)
            self.assertEqual(session.broadcast.state.dj_moments,())
            self.assertEqual(session.presence_ledger.total_published,0)
        asyncio.run(scenario())

    def test_rejected_final_authority_and_off_skips_producer(self):
        async def scenario():
            manager = self.runtime.SessionRuntimeManager()
            session = await manager.async_start(owner_profile_id='owner')
            with self.assertRaises(PermissionError):
                await manager.async_update_presence(owner_profile_id='owner',session_id=session.session_id,selected_presence='music_only',authorize=lambda:False)
            self.assertEqual(session.presence_revision,0)
            await manager.async_update_presence(owner_profile_id='owner',session_id=session.session_id,selected_presence='music_only')
            async def forbidden():
                self.fail('music-only invoked proactive provider')
            self.assertIsNone(await manager.async_process_track_started(owner_profile_id='owner',session_id=session.session_id,insight_provider=forbidden))
        asyncio.run(scenario())

    def test_retained_runtime_cannot_publish_after_off_aba_mood_persona_or_end(self):
        async def scenario(change):
            manager=self.runtime.SessionRuntimeManager()
            retained=await manager.async_start(owner_profile_id="owner",selected_mood="groove")
            moment=retained.moment_engine.create_silence(session_id=retained.session_id,
                selected_mood="groove",persona=retained.dj_persona,locale="nl",reason="fixture")
            moment=replace(moment,moment_type=self.runtime.DJMomentType.SESSION,content="Fixture direction")
            if change in ("off","presence_aba"):
                await manager.async_update_presence(owner_profile_id="owner",session_id=retained.session_id,selected_presence="music_only")
                if change=="presence_aba":
                    await manager.async_update_presence(owner_profile_id="owner",session_id=retained.session_id,selected_presence="balanced")
            elif change=="mood":
                await manager.async_update_mood(owner_profile_id="owner",session_id=retained.session_id,selected_mood="energy")
            elif change=="persona_aba":
                for persona in (self.runtime.DJPersona.RADIO_DJ,self.runtime.DJPersona.HOME_DJ):
                    await manager.async_update_persona(owner_profile_id="owner",session_id=retained.session_id,dj_persona=persona)
            else:
                await manager.async_end(owner_profile_id="owner",session_id=retained.session_id)
            sequence=retained.broadcast.delivery_sequence
            retained.publish_moment(moment)
            self.assertFalse(retained.publication_context_is_current())
            self.assertEqual(retained.broadcast.state.dj_moments,())
            self.assertEqual(retained.broadcast.delivery_sequence,sequence)
            self.assertEqual(retained.presence_ledger.total_published,0)
        for change in ("off","presence_aba","mood","persona_aba","end"):
            with self.subTest(change=change):
                asyncio.run(scenario(change))


from tests import test_active_session_mood as mood_tests  # noqa: E402


class PresenceCandidateRaceTest(mood_tests.ActiveSessionMoodRuntimeTest):
    """Keep the original Mood suite, repeat its production paths for presence."""
    revision_field = "presence_revision"

    async def _aba(self, manager, session):
        for mode in ('music_only', 'balanced'):
            await manager.async_update_presence(owner_profile_id=session.owner_profile_id,
                session_id=session.session_id, selected_presence=mode)

    def test_fallback_reacquisition_rejects_before_legacy_direction_mutation(self):
        async def scenario():
            manager, session, previous, current, insight = await self._unpublished_current_track()
            entered, release = asyncio.Event(), asyncio.Event()
            underlying = manager._lock
            class Gate:
                count = 0
                async def __aenter__(gate):
                    gate.count += 1
                    if gate.count == 4:
                        entered.set()
                        await release.wait()
                    await underlying.acquire()
                async def __aexit__(gate, *args):
                    underlying.release()
            manager._lock = Gate()
            from unittest.mock import patch
            async def fallback(coordinator, **kwargs):
                return None
            with patch.object(self.runtime.PlanningRuntimeCoordinator, 'async_coordinate_track_started', fallback):
                pending = asyncio.create_task(manager.async_process_track_started(owner_profile_id='owner',
                    session_id=session.session_id,media_identity=current,require_current_playback=True,insight_provider=insight))
                await asyncio.wait_for(entered.wait(),2)
                active = manager._active_by_profile['owner']
                before = (copy.deepcopy(active.planner.as_dict()),active.session_direction,active.presence_ledger.total_published)
                await self._aba(manager, session)
                release.set()
                self.assertIsNone(await pending)
                active = manager._active_by_profile['owner']
                self.assertEqual((active.planner.as_dict(),active.session_direction,active.presence_ledger.total_published),before)
                self.assertEqual(active.last_accepted_media_identity,previous)
        asyncio.run(scenario())

    def test_cancelled_coordinator_and_fallback_restore_unspent_current_candidate(self):
        async def scenario(path):
            manager,session,previous,current,insight=await self._unpublished_current_track()
            entered=asyncio.Event()
            from unittest.mock import patch
            async def delayed(*args,**kwargs):
                entered.set()
                await asyncio.Event().wait()
            async def fallback(*args,**kwargs):
                return None
            target=self.runtime.PlanningRuntimeCoordinator if path=="coordinator" else self.runtime.DJKnowledgeEngine
            method="async_coordinate_track_started" if path=="coordinator" else "async_assemble_track_context"
            from contextlib import ExitStack
            with ExitStack() as stack:
                if path=="fallback":
                    stack.enter_context(patch.object(self.runtime.PlanningRuntimeCoordinator,"async_coordinate_track_started",fallback))
                stack.enter_context(patch.object(target,method,delayed))
                task=asyncio.create_task(manager.async_process_track_started(owner_profile_id="owner",session_id=session.session_id,
                    media_identity=current,require_current_playback=True,insight_provider=insight))
                await asyncio.wait_for(entered.wait(),2)
                before=(session.presence_ledger.total_published,session.broadcast.state.dj_moments)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            active=await manager.async_get_active("owner")
            self.assertEqual(active.last_accepted_media_identity,previous)
            self.assertEqual((active.presence_ledger.total_published,active.broadcast.state.dj_moments),before)
            retry=await manager.async_process_track_started(owner_profile_id="owner",session_id=session.session_id,
                media_identity=current,require_current_playback=True,insight_provider=insight)
            self.assertIsNotNone(retry)
        for path in ("coordinator","fallback"):
            with self.subTest(path=path):
                asyncio.run(scenario(path))

    def test_cancelled_intratrack_releases_pending_without_spending(self):
        async def scenario():
            from tests import test_vibecast_multimoment as multi
            from unittest.mock import patch
            helper=multi.VibeCastMultiMomentTest()
            helper.runtime=self.runtime
            manager,session,first,media,now=await helper._ready()
            await helper._observe(manager,session,media,now,seconds=45,position_ms=45000)
            entered=asyncio.Event()
            async def delayed(*args,**kwargs):
                entered.set()
                await asyncio.Event().wait()
            with patch.object(self.runtime.DJKnowledgeEngine,"async_assemble_track_context",delayed):
                task=asyncio.create_task(helper._later(manager,session,media))
                await asyncio.wait_for(entered.wait(),2)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            opportunity=manager._intra_track_opportunities[session.owner_profile_id]
            self.assertFalse(opportunity.pending)
            self.assertFalse(opportunity.spent)
            self.assertEqual(session.broadcast.state.dj_moments,(first,))
            self.assertEqual(session.presence_ledger.total_published,1)
            self.assertIsNotNone(await helper._later(manager,session,media))
        asyncio.run(scenario())


class PresenceLedgerRetentionTest(unittest.TestCase):
    def test_old_track_budget_survives_240_distinct_tracks_and_quiet_time(self):
        from custom_components.djconnect.presence_policy import PresenceLedger
        now = [0.0]
        ledger = PresenceLedger(clock=lambda:now[0])
        for _ in range(6):
            self.assertTrue(ledger.admits('presenter','old-track'))
            ledger.commit('old-track',40)
            now[0] += 60
        for index in range(240):
            now[0] += 600
            if ledger.admits('presenter',f'track-{index}'):
                ledger.commit(f'track-{index}',40)
        now[0] += 600
        self.assertFalse(ledger.admits('presenter','old-track'))
        self.assertEqual(ledger.suppression_reason,'presence_track_budget')
        self.assertEqual(len(ledger.track_counts),65536)
