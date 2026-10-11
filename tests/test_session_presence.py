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
