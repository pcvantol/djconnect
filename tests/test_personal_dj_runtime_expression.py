"""Real ordinary producers through the common two-call expression owner."""
import asyncio
from contextlib import contextmanager
from dataclasses import replace
import json
import math
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_session_conversation_history as fixtures


@contextmanager
def _business_clock(clock):
    """Simulate application time without freezing asyncio's timeout clock."""
    real_monotonic = time.monotonic  # Capture the callable, not loop.time's wrapper.
    loop = asyncio.get_running_loop()
    with patch.object(loop, 'time', real_monotonic), patch('time.monotonic', lambda: clock[0]):
        yield


async def _wait_for_model_entry(producer, entered):
    """A failed/finished producer must not leave an entered-only wait hanging."""
    waiter = asyncio.create_task(entered.wait())
    try:
        done, _ = await asyncio.wait({producer, waiter}, timeout=2,
            return_when=asyncio.FIRST_COMPLETED)
        if producer in done:
            producer.result()  # Preserve the original exception, if any.
            raise AssertionError('Genre producer finished before the held model entry')
        if waiter not in done or not entered.is_set():
            raise AssertionError('Genre producer did not reach the model within two real seconds')
    finally:
        waiter.cancel()
        await asyncio.gather(waiter, return_exceptions=True)


class RuntimeExpressionTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = fixtures.SessionConversationHistoryTest()
        await self.fixture.asyncSetUp()
        self.hass, self.runtime, _, _, _ = await self.fixture.transport_fixture()
        self.r, self.manager = self.fixture.runtime, self.fixture.manager

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def history_authority(self):
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.session_conversation import async_metadata_archive_admission
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        await storage.async_upsert_music_account('source-account','source-spotify', kind=MusicAccountKind.PERSONAL,
            display_name='Synthetic source', linked_profile_ids=frozenset({'profile-a'}),provider_account_id='fixture-owner')
        binding={'backend_id':'source-spotify','music_account_id':'source-account',
                 'provider_entry_id':'source-entry','provider_account_id':'fixture-owner'}
        async def archive(captured):
            return await async_metadata_archive_admission(self.hass,'profile-a',captured,lambda:None)
        return binding, archive

    async def produce(self, persona, *, hold=None, retained=False):
        from custom_components.djconnect import pipeline
        binding, archive = await self.history_authority() if retained else ({},None)
        session = await self.manager.async_start(owner_profile_id='profile-a', locale='nl',
            selected_mood='groove', dj_persona=persona, music_backend='spotify_direct', history_source_context=binding)
        calls, briefs = [], []
        async def transport(domain, service, data, **kwargs):
            calls.append(data['text'])
            if hold is not None and len(calls) == 1:
                hold[0].set()
                await hold[1].wait()
            text = (json.dumps({'text': '{track} van {artist} speelt nu. Ik schuif even aan.'})
                    if len(calls) == 1 and briefs[-1].kind == 'observed_playback' else
                    json.dumps({'text': 'Ik houd het hier in beweging, lekker met je mee.'})
                    if len(calls) == 1 else
                    json.dumps({'supported': True, 'language_ok': True, 'style_ok': True}))
            return {'response': {'speech': {'plain': {'speech': text}}}}
        self.hass.services = SimpleNamespace(async_call=transport)
        async def realize(brief, guard):
            briefs.append(brief)
            return await pipeline.realize_session_narration(self.hass, narration=brief,
                admission=guard, fallback_text=brief.seed, conf=self.runtime.config)
        self.manager.connect_narration('profile-a', session.session_id, realize, lambda: None, archive_admission=archive)
        async def knowledge():
            return {'track': {'title': 'Local exact title', 'artist': 'Local exact artist'},
                'analysis': {'summary': 'Unmeasured', 'full_text': 'No qualified audio analysis.',
                             'basis': 'unmeasured_metadata_only_v1'}}
        with patch.object(pipeline, '_assist_context', return_value={'agent_id': 'fixture-agent', 'language': 'nl'}):
            for marker in ('A', 'B'):
                session = await self.manager.async_get_active('profile-a')
                media = 'spotify:track:'+marker*22
                await self.manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=session.session_id,
                    state='playing', media_identity=media, title='Local exact title', artist='Local exact artist',
                    duration_ms=600000, position_ms=0)
                result = await self.manager.async_process_track_started(owner_profile_id='profile-a', session_id=session.session_id,
                    media_identity=media, insight_provider=knowledge, require_current_playback=True)
        return session, result, calls, briefs

    async def test_actual_playback_and_direction_get_assessed_text_without_catalog_model_input(self):
        from custom_components.djconnect import session_speech
        from custom_components.djconnect.narration_brief import admitted_runtime_text
        for persona, kind in ((self.r.DJPersona.HOME_DJ, 'observed_playback'),
                              (self.r.DJPersona.FESTIVAL_DJ, 'session_direction')):
            with self.subTest(kind=kind):
                session, moment, calls, briefs = await self.produce(persona, retained=True)
                self.assertIsNotNone(moment)
                self.assertEqual(len(calls), 2)
                self.assertEqual([b.kind for b in briefs], [kind])
                self.assertTrue(admitted_runtime_text(moment))
                self.assertNotIn('Local exact title', '\n'.join(calls))
                self.assertNotIn('Local exact artist', '\n'.join(calls))
                self.assertEqual(dict(moment.generation_metadata)['realization'], 'qualified_runtime_narration_v1')
                self.assertEqual(session.broadcast.state.dj_moments[-1].content, moment.content)
                self.assertEqual(''.join(s['text'] for s in session_speech.moment_projection(session.broadcast, moment)['segments']), moment.content)
                self.assertNotIn('narration_acceptance', moment.as_dict())
                self.assertFalse(admitted_runtime_text(replace(moment, content=moment.content+' Invented extra.')))
                if kind == 'observed_playback':
                    self.assertIn('Local exact title', moment.content)
                    admission = next(a for a in session.broadcast.native_delivery()['admissions'] if a['moment_id'] == moment.moment_id)
                    self.assertEqual(admission['qualification'], 'qualified')
                    # A metadata flag alone never qualifies a replacement body.
                    tampered = replace(moment, narration_acceptance=None)
                    from custom_components.djconnect.native_moment_delivery import admission as admit
                    self.assertEqual(admit(tampered, session.broadcast._moment_delivery_boundaries[moment.moment_id],
                        session_id=session.session_id, active=True,
                        flow_ids={i.moment_id for i in session.planner.output.session_flow.items},
                        playback_item_id=session.broadcast.state.playback.item_id, playing=True,
                        now=__import__('time').monotonic())['qualification'], 'unqualified')
                await self.manager.async_end(owner_profile_id='profile-a', session_id=session.session_id)
                await self.fixture.service.async_close()
                await self.fixture.service.async_initialize()
                page=await self.fixture.queries.async_timeline_page('profile-a',session.session_id)
                entry=next(e for e in page['entries'] if e.get('moment_id')==moment.moment_id)
                self.assertEqual(entry['text'],moment.content)
                self.assertTrue(entry['session_speech']['manual_allowed'])


    async def test_end_during_runtime_generation_does_not_block_end_or_publish(self):
        hold = asyncio.Event(), asyncio.Event()
        task = asyncio.create_task(self.produce(self.r.DJPersona.HOME_DJ, hold=hold))
        await asyncio.wait_for(hold[0].wait(), 2)
        active = await self.manager.async_get_active('profile-a')
        await asyncio.wait_for(self.manager.async_end(owner_profile_id='profile-a', session_id=active.session_id), 2)
        hold[1].set()
        _, moment, calls, _ = await task
        self.assertIsNone(moment)
        self.assertEqual(len(calls), 1)
        self.assertEqual(active.broadcast.state.dj_moments, ())
        row = await self.fixture.repo.async_session_record(active.session_id)
        self.assertEqual(row['summary']['moments_published']['value'], 0)

    async def test_actual_pending_genre_transition_keeps_one_published_expression_frame(self):
        from custom_components.djconnect.narration_brief import NarratedText, admitted_runtime_text, recent_frames
        binding, archive = await self.history_authority()
        # Exact binary fixture ticks: a real uptime near an exponent boundary
        # can round (start+225)-(start+180) to just below the real 45s policy.
        clock = [100.0]
        self.manager._monotonic_source = lambda: clock[0]
        with _business_clock(clock):
            active = await self.manager.async_start(owner_profile_id='profile-a', selected_mood='groove', locale='nl',
                session_start_strategy=self.r.SessionStartStrategy.DISCOVER, elapsed_time_source=lambda: clock[0], history_source_context=binding)
            active = await self.manager.async_update_presence(owner_profile_id='profile-a',
                session_id=active.session_id, selected_presence='presenter')
            async def fallback(brief,guard):
                guard()
                return brief.seed
            self.manager.connect_narration('profile-a', active.session_id, fallback, lambda:None, archive_admission=archive)
            for number, title in ((1, 'Baseline'), (2, 'Earlier title'), (3, 'Current title')):
                active = await self.manager.async_get_active('profile-a')
                media = 'spotify:track:'+str(number).zfill(22)
                await self.manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=active.session_id,
                    state='playing', media_identity=media, title=title, artist='Local artist', duration_ms=600000, position_ms=0)
                async def status():
                    return {'track': {'title': title, 'artist': 'Local artist', 'genres': ['ambient'], 'backend': 'spotify_direct'},
                        'analysis': {'summary': 'Unmeasured', 'full_text': 'No measured audio.', 'basis': 'unmeasured_metadata_only_v1'},
                        '_session_narrative_evidence': {'source': 'spotify_playback_status', 'backend': 'spotify_direct',
                            'media_identity': media, 'title': title, 'artist': 'Local artist', 'artist_ids': ['Z'*22],
                            'genres': ['ambient'], 'is_playing': True, 'genre_source_expires_at': clock[0]+1800}}
                await self.manager.async_process_track_started(owner_profile_id='profile-a', session_id=active.session_id,
                    media_identity=media, insight_provider=status, require_current_playback=True)
                if number < 3:
                    clock[0] += 90
            active = await self.manager.async_get_active('profile-a')
            self.assertIsNotNone(self.manager._intra_track_opportunities['profile-a'].pending_transition)
            before = active.moment_engine._expression_moment_ids
            frame = '{source_track} bracht {artist} al langs {genre}; nu speelt {target_track}.'
            entered, release = asyncio.Event(), asyncio.Event()
            async def model(brief, guard):
                self.assertEqual(brief.kind, 'genre_transition')
                self.assertNotIn('Current title', brief.prompt())
                entered.set()
                await release.wait()
                guard()
                return NarratedText(brief.render(frame), frame)
            self.manager.connect_narration('profile-a', active.session_id, model, lambda: None, archive_admission=archive)
            clock[0] += 45
            await self.manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=active.session_id,
                state='playing', media_identity=media, title='Current title', artist='Local artist', duration_ms=600000, position_ms=45000)
            task = asyncio.create_task(self.manager.async_maybe_publish_intra_track_moment(owner_profile_id='profile-a',
                session_id=active.session_id, media_identity=media))
            try:
                await _wait_for_model_entry(task, entered)
                self.assertIsNone(await self.manager.async_maybe_publish_intra_track_moment(owner_profile_id='profile-a',
                    session_id=active.session_id, media_identity=media))
                self.assertEqual(active.moment_engine._expression_moment_ids, before)
                release.set()
                moment = await task
                self.assertIsNotNone(moment)
                self.assertEqual(moment.moment_type.value, 'transition')
                self.assertTrue(admitted_runtime_text(moment))
                current = await self.manager.async_get_active('profile-a')
                self.assertEqual(current.moment_engine._expression_moment_ids, (*before, moment.moment_id)[-6:])
                self.assertEqual(recent_frames(current.moment_engine._expression_forms)[-1], frame)
                self.assertEqual(sum(m.moment_id == moment.moment_id for m in current.broadcast.state.dj_moments), 1)
                self.assertIsNone(await self.manager.async_maybe_publish_intra_track_moment(owner_profile_id='profile-a',
                    session_id=active.session_id, media_identity=media))
                self.assertEqual(current.moment_engine._expression_moment_ids.count(moment.moment_id), 1)
                await self.manager.async_end(owner_profile_id='profile-a',session_id=active.session_id)
                await self.fixture.service.async_close()
                await self.fixture.service.async_initialize()
                page=await self.fixture.queries.async_timeline_page('profile-a',active.session_id)
                entry=next(e for e in page['entries'] if e.get('moment_id')==moment.moment_id)
                self.assertEqual(entry['text'],moment.content)
                self.assertTrue(entry['session_speech']['manual_allowed'])
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_presence_clock_keeps_the_exact_policy_boundary_without_an_epsilon(self):
        from custom_components.djconnect.presence_policy import PresenceLedger
        for base, expected in ((math.nextafter(824.0, math.inf), False), (100.0, True)):
            with self.subTest(base=base.hex()):
                clock = [base]
                clock[0] += 90
                clock[0] += 90
                ledger = PresenceLedger(clock=lambda: clock[0])
                ledger.commit('previous-observed-item', 15)
                clock[0] += 45
                interval = clock[0] - ledger.last_at
                self.assertEqual(ledger.admits('presenter', 'current-observed-item'), expected)
                if expected:
                    self.assertEqual(interval, 45.0)
                    self.assertEqual(ledger.suppression_reason, '')
                else:
                    self.assertLess(interval, 45.0)
                    self.assertEqual(ledger.suppression_reason, 'presence_readable_interval')

    async def test_simulated_business_clock_keeps_a_real_timeout_and_restores_both_clocks(self):
        real_clock = time.monotonic
        loop = asyncio.get_running_loop()
        original_loop_time = loop.time
        clock = [real_clock() + 225]
        with _business_clock(clock):
            self.assertEqual(time.monotonic(), clock[0])
            waiter = asyncio.create_task(asyncio.wait_for(asyncio.Event().wait(), .02))
            guard = threading.Timer(2, lambda: loop.call_soon_threadsafe(waiter.cancel))
            guard.daemon = True
            guard.start()
            try:
                with self.assertRaises(asyncio.TimeoutError):
                    await waiter
                self.assertEqual(time.monotonic(), clock[0])
            finally:
                guard.cancel()
                guard.join(2)
        self.assertIs(time.monotonic, real_clock)
        self.assertEqual(loop.time, original_loop_time)

    async def test_model_entry_wait_surfaces_early_producer_failure_or_empty_result(self):
        async def failed():
            raise RuntimeError('synthetic producer failure')
        async def empty():
            return None
        with _business_clock([time.monotonic()]):
            for operation, exception in ((failed, RuntimeError), (empty, AssertionError)):
                task = asyncio.create_task(operation())
                with self.subTest(operation=operation.__name__):
                    with self.assertRaises(exception):
                        await _wait_for_model_entry(task, asyncio.Event())
                await asyncio.gather(task, return_exceptions=True)



    async def test_sql_rollback_keeps_every_track_started_commit_route_retryable(self):
        from contextlib import ExitStack
        from custom_components.djconnect.persistence.service import PersistenceError
        async def knowledge():
            return {'track': {'title': 'Exact title', 'artist': 'Exact artist'},
                'analysis': {'summary': 'Unmeasured', 'full_text': 'No measured audio.',
                             'basis': 'unmeasured_metadata_only_v1'}}
        async def no_legacy(owner, active, **kwargs):
            return active, None
        for route in ('coordinator', 'legacy_silence', 'fallback_silence', 'fallback_track'):
            with self.subTest(route=route):
                active = await self.manager.async_start(owner_profile_id='profile-a',
                    locale='nl', selected_mood='groove',music_backend='spotify_direct')
                sid = active.session_id
                async def fallback_expression(brief, guard):
                    guard()
                    return brief.seed
                self.manager.connect_narration('profile-a',sid,fallback_expression,lambda:None)
                for marker in ('A', 'B'):
                    uri = 'spotify:track:'+marker*22
                    await self.manager.async_update_playback_projection(owner_profile_id='profile-a',
                        session_id=sid, state='playing', media_identity=uri, title='Exact title',
                        artist='Exact artist', duration_ms=600000, position_ms=0)
                    if marker == 'A':
                        await self.manager.async_process_track_started(owner_profile_id='profile-a',session_id=sid,
                            media_identity=uri,insight_provider=knowledge,require_current_playback=True)
                with ExitStack() as stack:
                    if route != 'coordinator':
                        stack.enter_context(patch.object(self.r.PlanningRuntimeCoordinator,
                            'async_coordinate_track_started', return_value=None))
                    if route.startswith('fallback_'):
                        stack.enter_context(patch.object(self.manager,'_apply_legacy_initial_track_started_decision',no_legacy))
                    if route.endswith('silence'):
                        stack.enter_context(patch.object(self.r.DJSessionPlanner,'evaluate_track_started',
                            return_value=self.r.PlannerDecision(self.r.PlannerDecisionType.SILENCE,'fixture silence')))
                    await self.fixture.service.async_in_transaction(lambda tx:tx.execute(
                        "CREATE TRIGGER reject_started BEFORE INSERT ON djconnect_session_entries WHEN NEW.kind IN ('dj_moment','dj_silence','dj_publication') BEGIN SELECT RAISE(ABORT,'injected source refusal'); END"))
                    with self.assertRaises(PersistenceError):
                        await self.manager.async_process_track_started(owner_profile_id='profile-a',session_id=sid,
                            media_identity=uri,insight_provider=knowledge,require_current_playback=True)
                    current = self.manager.current_active('profile-a')
                    self.assertEqual(current.last_accepted_media_identity,'spotify:track:'+'A'*22)
                    self.assertEqual(current.broadcast.state.dj_moments,())
                    row=await self.fixture.repo.async_session_record(sid)
                    self.assertEqual(row['summary']['moments_published']['value'],0)
                    await self.fixture.service.async_in_transaction(lambda tx:tx.execute('DROP TRIGGER reject_started'))
                    retried=await self.manager.async_process_track_started(owner_profile_id='profile-a',session_id=sid,
                        media_identity=uri,insight_provider=knowledge,require_current_playback=True)
                    self.assertIsNotNone(retried)
                    self.assertEqual(retried.moment_type.value,'silence' if route.endswith('silence') else 'track')
                    self.assertIsNone(await self.manager.async_process_track_started(owner_profile_id='profile-a',session_id=sid,
                        media_identity=uri,insight_provider=knowledge,require_current_playback=True))
                    self.assertEqual(len(self.manager.current_active('profile-a').broadcast.state.dj_moments),1)
                await self.manager.async_end(owner_profile_id='profile-a',session_id=sid)
