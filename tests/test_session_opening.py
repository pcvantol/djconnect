"""Opening through real settings, Runtime, SQLite, Flow and speech owners.

Expression outputs are fixtures; these tests do not qualify generated prose or
native/audible playback.
"""
import asyncio
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
import importlib
import sqlite3
import unittest

from tests import test_session_conversation_history as history_fixtures
from tests.test_profile_dj_settings_persistence import operation


class SessionOpeningTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        history_fixtures.SessionConversationHistoryTest.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        history_fixtures.SessionConversationHistoryTest.tearDownClass.__func__(cls)

    async def asyncSetUp(self):
        await history_fixtures.SessionConversationHistoryTest.asyncSetUp(self)
        from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
        self.settings = ProfileDJSettingsRepository(self.service)
        self.manager._settings_repository = self.settings
        self.counter = 0

    async def asyncTearDown(self):
        await history_fixtures.SessionConversationHistoryTest.asyncTearDown(self)

    async def start(self, *, mood='energy', persona='home_dj', presence='balanced', locale='nl', history=True):
        from custom_components.djconnect.domain.profile.dj_settings import DJSettings
        self.counter += 1
        owner = 'opening-owner-'+str(self.counter)
        now = int(datetime.now(UTC).timestamp()*1000)
        await self.settings.async_accept_user_choice(owner,
            operation_id=operation(now, self.counter), binding='a'*64,
            patch=DJSettings(mood=mood, persona=persona, presence=presence).as_dict(),
            expected_defaults_revision=0, now_ms=now, authorize=lambda: True)
        return await self.manager.async_start(owner_profile_id=owner, locale=locale,
            history_enabled=history, inherit_settings=True)

    async def open(self, session):
        return await self.manager.async_open_session(owner_profile_id=session.owner_profile_id,
                                                     session_id=session.session_id)

    async def test_all_start_choices_are_confirmed_localized_retained_and_reopened_once(self):
        from custom_components.djconnect.session_opening import COPY, MOODS, PERSONAS, PRESENCES
        for locale in COPY:
            if locale != next(iter(COPY)):
                # Each language is a fresh household fixture: do not bypass the
                # real global limit on unexpired settings-operation receipts.
                await self.asyncTearDown()
                await self.asyncSetUp()
            for mood in MOODS:
                for persona in PERSONAS:
                    for presence in PRESENCES:
                        with self.subTest(locale=locale, mood=mood, persona=persona, presence=presence):
                            session = await self.start(mood=mood, persona=persona, presence=presence, locale=locale)
                            moment = await self.open(session)
                            self.assertIsNotNone(moment)
                            self.assertIs(await self.open(session), moment)
                            self.assertEqual(len(session.broadcast.state.dj_moments), 1)
                            self.assertEqual(session.broadcast.state.dj_moments[0].moment_id, moment.moment_id)
                            values = session.opening_context.values()
                            for key in ('mood', 'persona', 'presence', 'mood_meaning', 'persona_meaning', 'presence_meaning'):
                                self.assertIn(values[key], moment.content)
                            self.assertEqual(moment.as_dict()['type'], 'session')
                            self.assertEqual(moment.as_dict()['generation_metadata']['start_presence'], presence)
                            self.assertEqual(moment.actions, ())
                            native = session.broadcast.native_delivery()['admissions']
                            self.assertEqual(native[0]['qualification'], 'qualified')
                            self.assertTrue(native[0]['active_flow_display_allowed'])
                            await self.manager.async_end(owner_profile_id=session.owner_profile_id,
                                                         session_id=session.session_id)
                            page = await self.queries.async_timeline_page(session.owner_profile_id, session.session_id)
                            retained = [e for e in page['entries'] if e['kind'] == 'dj_moment']
                            self.assertEqual(len(retained), 1)
                            self.assertEqual(retained[0]['text'], moment.content)
                            self.assertEqual(retained[0]['generation_metadata']['start_mood'], mood)
        await self.service.async_close()
        await self.service.async_initialize()
        page = await self.queries.async_timeline_page(session.owner_profile_id, session.session_id)
        self.assertEqual(next(e['text'] for e in page['entries'] if e['kind'] == 'dj_moment'), moment.content)

    async def test_concurrent_start_and_retries_use_one_expression_outside_lock(self):
        session = await self.start()
        briefs = importlib.import_module('custom_components.djconnect.narration_brief')
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def provider(brief, guard):
            self.assertFalse(self.manager._lock.locked())
            self.assertFalse(session.allows_proactive())
            guard()
            calls.append(brief)
            entered.set()
            await release.wait()
            frame = ('Welkom! Als {persona} ben ik je warme gezelschap. Met {mood} vertel ik vlot en levendig. '
                     'Bij {presence} wissel ik bijdragen af met ruimte voor de muziek. Veel luisterplezier!')
            return briefs.NarratedText(brief.render(frame), frame)
        self.manager.connect_narration(session.owner_profile_id, session.session_id, provider, lambda: None)
        tasks = [asyncio.create_task(self.open(session)) for _ in range(12)]
        await asyncio.wait_for(entered.wait(), 2)
        with self.assertRaises(self.runtime.ActiveSessionExistsError):
            await self.manager.async_start(owner_profile_id=session.owner_profile_id)
        tasks[0].cancel()
        with self.assertRaises(asyncio.CancelledError):
            await tasks[0]
        release.set()
        moments = await asyncio.gather(*tasks[1:])
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(m is moments[0] for m in moments))
        self.assertEqual(moments[0].content, briefs.qualify_runtime_moment(moments[0], locale='nl').render(moments[0].narration_acceptance.frame))
        self.assertNotIn(session.owner_profile_id, calls[0].prompt())
        self.assertNotIn(session.session_id, calls[0].prompt())
        self.assertIn('all three confirmed start choices', calls[0].prompt())
        self.assertEqual(len(session.broadcast.state.dj_moments), 1)
        page = await self.queries.async_timeline_page(session.owner_profile_id, session.session_id)
        self.assertEqual(sum(e['kind'] == 'dj_moment' for e in page['entries']), 1)

    async def test_inflight_setting_change_keeps_start_snapshot_and_disallows_automatic_speech(self):
        session = await self.start(presence='presenter')
        entered, release = asyncio.Event(), asyncio.Event()
        async def provider(brief, guard):
            entered.set()
            await release.wait()
            return brief.seed
        self.manager.connect_narration(session.owner_profile_id, session.session_id, provider, lambda: None)
        task = asyncio.create_task(self.open(session))
        await asyncio.wait_for(entered.wait(), 2)
        await self.manager.async_update_mood(owner_profile_id=session.owner_profile_id,
            session_id=session.session_id, selected_mood='chill')
        await self.manager.async_update_presence(owner_profile_id=session.owner_profile_id,
            session_id=session.session_id, selected_presence='music_only')
        release.set()
        moment = await task
        self.assertEqual(moment.content, session.opening_context.seed())
        self.assertEqual(moment.presentation_intent.source_session_mood, 'energy')
        self.assertEqual(dict(moment.generation_metadata)['start_presence'], 'presenter')
        current = self.manager.current_active(session.owner_profile_id)
        from custom_components.djconnect.session_speech import moment_projection
        self.assertFalse(moment_projection(current.broadcast, moment, autoplay=True)['autoplay_eligible'])
        await self.manager.async_end(owner_profile_id=session.owner_profile_id, session_id=session.session_id)
        page = await self.queries.async_timeline_page(session.owner_profile_id, session.session_id)
        self.assertEqual(next(e['text'] for e in page['entries'] if e['kind'] == 'dj_moment'), moment.content)

    async def test_music_only_has_manual_replay_but_no_automatic_client_or_speaker_work(self):
        from unittest.mock import patch
        from custom_components.djconnect import speaker_delivery
        from custom_components.djconnect.session_speech import moment_projection
        session = await self.start(presence='music_only')
        moment = await self.open(session)
        descriptor = moment_projection(session.broadcast, moment, autoplay=True)
        self.assertTrue(descriptor['manual_allowed'])
        self.assertFalse(descriptor['autoplay_eligible'])
        from types import SimpleNamespace
        hass = SimpleNamespace(async_create_task=lambda *args: self.fail('Music-only scheduled speech'))
        with (patch.object(speaker_delivery, 'output_policy', side_effect=AssertionError('Music-only accessed speaker')),
                patch.object(self.runtime, 'session_runtime_manager', return_value=self.manager)):
            speaker_delivery.connect_automatic(hass, None, session, {}, {})
            session.broadcast.owner_moment_speech_delivery(moment)

    async def test_end_and_owner_revocation_during_generation_never_publish(self):
        for change in ('end', 'owner'):
            session = await self.start()
            entered, release = asyncio.Event(), asyncio.Event()
            valid = [True]
            def authorize():
                if not valid[0]:
                    raise PermissionError('withdrawn')
            async def provider(brief, guard):
                entered.set()
                await release.wait()
                return brief.seed
            self.manager.connect_narration(session.owner_profile_id, session.session_id, provider, authorize)
            task = asyncio.create_task(self.open(session))
            await asyncio.wait_for(entered.wait(), 2)
            if change == 'end':
                await self.manager.async_end(owner_profile_id=session.owner_profile_id, session_id=session.session_id)
            else:
                valid[0] = False
            release.set()
            self.assertIsNone(await task)
            page = await self.queries.async_timeline_page(session.owner_profile_id, session.session_id)
            self.assertFalse(any(e['kind'] == 'dj_moment' for e in page['entries']))

    async def test_real_sql_failure_cannot_leave_a_live_only_welcome(self):
        from custom_components.djconnect.persistence.service import PersistenceError
        session = await self.start()
        calls = []
        async def provider(brief, guard):
            calls.append(brief)
            return brief.seed
        self.manager.connect_narration(session.owner_profile_id, session.session_id, provider, lambda: None)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER reject_opening BEFORE INSERT ON djconnect_session_entries "
                       "WHEN NEW.kind='dj_moment' BEGIN SELECT RAISE(ABORT,'synthetic opening failure'); END")
        with self.assertRaises(PersistenceError):
            await self.open(session)
        self.assertEqual(session.broadcast.state.dj_moments, ())
        self.assertEqual(session.moment_engine.moments, ())
        record = await self.repo.async_session_record(session.session_id)
        self.assertEqual(record['summary']['moments_published']['value'], 0)
        page = await self.queries.async_timeline_page(session.owner_profile_id, session.session_id)
        self.assertFalse(any(e['kind'] == 'dj_moment' for e in page['entries']))
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('DROP TRIGGER reject_opening')
        accepted = await self.open(session)
        self.assertIsNotNone(accepted)
        self.assertIs(await self.open(session), accepted)
        self.assertEqual(len(calls), 1)
        page = await self.queries.async_timeline_page(session.owner_profile_id, session.session_id)
        self.assertEqual(sum(e['kind'] == 'dj_moment' for e in page['entries']), 1)

    async def test_settings_changed_before_opening_cannot_replace_original_persona(self):
        session = await self.start()
        await self.manager.async_update_persona(owner_profile_id=session.owner_profile_id,
            session_id=session.session_id, dj_persona=self.runtime.DJPersona.RADIO_DJ)
        await self.manager.async_update_mood(owner_profile_id=session.owner_profile_id,
            session_id=session.session_id, selected_mood='party')
        moment = await self.open(session)
        self.assertIsNotNone(moment)
        self.assertIn('Home DJ', moment.content)
        self.assertEqual(moment.presentation_intent.dj_persona, self.runtime.DJPersona.HOME_DJ)
        self.assertEqual(moment.presentation_intent.source_session_mood, 'energy')

    async def test_history_opt_out_does_not_store_welcome_and_tampering_is_denied(self):
        session = await self.start(history=False)
        moment = await self.open(session)
        self.assertIsNotNone(moment)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM djconnect_session_entries WHERE session_id=?',
                                       (session.session_id,)).fetchone()[0], 0)
        forged = replace(moment, content='I have started your favourite recording.')
        self.assertFalse(await self.manager._async_persist_moment(session, forged))
        from custom_components.djconnect.session_opening import admitted_opening
        self.assertFalse(admitted_opening(forged))
        self.assertFalse(admitted_opening(replace(moment, session_opening=replace(moment.session_opening, mood='party'))))
