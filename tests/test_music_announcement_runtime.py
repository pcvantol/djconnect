"""Actual Runtime/Planner and SQLite acceptance, with fixture expression only.

No claim about a real model, speech synthesis, provider playback or Apple UI.
"""
import importlib
import json
import time
from types import SimpleNamespace
import unittest

from tests import test_session_conversation_history as history_fixtures


class AnnouncementRuntimeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        history_fixtures.SessionConversationHistoryTest.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        history_fixtures.SessionConversationHistoryTest.tearDownClass.__func__(cls)

    async def asyncSetUp(self):
        await history_fixtures.SessionConversationHistoryTest.asyncSetUp(self)
        self.module = importlib.import_module('custom_components.djconnect.track_start_announcement')
        self.briefs = importlib.import_module('custom_components.djconnect.narration_brief')
        self.source = dict(backend_id='source', music_account_id='account',
                           provider_entry_id='entry', provider_account_id='provider-owner')
        self.active = await self.manager.async_start(owner_profile_id='profile-a', locale='nl',
            selected_mood='energy', history_source_context=self.source)
        await self.manager.async_update_presence(owner_profile_id='profile-a',
            session_id=self.active.session_id, selected_presence='music_only')
        self.active = self.manager.current_active('profile-a')
        self.calls = []
        self.valid = True
        async def archive(captured):
            self.assertEqual(captured, self.source)
            return lambda: self.authorize()
        async def model(brief, guard):
            guard()
            self.assertFalse(self.manager._lock.locked())
            self.calls.append(brief)
            frame = '{artist} — {track}. Geef dit moment even alle ruimte.'
            return self.briefs.NarratedText(brief.render(frame), frame)
        self.manager.connect_narration('profile-a', self.active.session_id,
            model, self.authorize, archive_admission=archive)

    def authorize(self):
        if not self.valid:
            raise PermissionError('fixture-source-withdrawn')

    async def asyncTearDown(self):
        await history_fixtures.SessionConversationHistoryTest.asyncTearDown(self)

    async def sample(self, character='A', title='Original {artist}', artist='Original artist'):
        observed = SimpleNamespace(state='playing', media_identity='spotify:track:'+character*22,
            title=title, artist=artist, position_ms=0, duration_ms=180000,
            catalog={'album_uri':'spotify:album:'+'Z'*22}, target_id='output')
        await self.manager.async_update_playback_projection(owner_profile_id='profile-a',
            session_id=self.active.session_id, state='playing', media_identity=observed.media_identity,
            title=title, artist=artist, position_ms=0, duration_ms=180000)
        occurrence = self.module.capture(self.manager, owner_profile_id='profile-a',
            session_id=self.active.session_id, observed=observed, authorize=lambda: self.valid)
        return occurrence

    async def publish(self, occurrence):
        return await self.module.publish(self.manager, owner_profile_id='profile-a',
            session_id=self.active.session_id, occurrence=occurrence, authorize=lambda: self.valid)

    async def test_music_only_has_one_typed_durable_original_with_manual_replay(self):
        from custom_components.djconnect.session_speech import moment_projection, retained_projection
        occurrence = await self.sample()
        moment = await self.publish(occurrence)
        self.assertIsNotNone(moment)
        self.assertEqual(moment.moment_type.value, 'music_announcement')
        self.assertEqual(moment.title, 'Muziek aankondiging')
        self.assertIn('Original {artist}', moment.content)
        self.assertTrue(self.module.accepted(moment))
        self.assertTrue(self.module.retained(moment))
        self.assertIsNone(await self.publish(occurrence))
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn('Original artist', self.calls[0].prompt())
        active = self.manager.current_active('profile-a')
        active.broadcast.owner_speech_output = lambda: 'text_only'
        speech = moment_projection(active.broadcast, moment, autoplay=True)
        self.assertTrue(speech['manual_allowed'])
        self.assertFalse(speech['autoplay_eligible'])
        self.assertEqual(speech['moment_type'], 'music_announcement')
        self.assertEqual(active.presence_ledger.announcements_published, 1)
        await self.manager.async_end(owner_profile_id='profile-a', session_id=active.session_id)
        await self.service.async_close()
        await self.service.async_initialize()
        page = await self.queries.async_timeline_page('profile-a', active.session_id)
        entry = next(e for e in page['entries'] if e.get('moment_id') == moment.moment_id)
        self.assertEqual(entry['text'], moment.content)
        self.assertEqual(entry['music_announcement']['occurrence_id'], occurrence.occurrence_id)
        raw = await self.repo.async_entry_record('profile-a', active.session_id, '', moment_id=moment.moment_id)
        self.assertEqual(json.loads(raw['body'])['session_media_reference']['album_uri'], 'spotify:album:'+'Z'*22)
        self.assertTrue(retained_projection(entry)['manual_allowed'])
        self.assertEqual(retained_projection(entry)['moment_type'], 'music_announcement')

    async def test_source_withdrawal_during_expression_never_publishes(self):
        occurrence = await self.sample()
        async def withdrawn(brief, guard):
            self.valid = False
            guard()
        self.manager.connect_narration('profile-a', self.active.session_id,
            withdrawn, self.authorize)
        self.assertIsNone(await self.publish(occurrence))
        self.assertEqual(self.manager.current_active('profile-a').broadcast.state.dj_moments, ())

    async def test_generation_timeout_uses_one_honest_degraded_text(self):
        occurrence = await self.sample()
        async def unavailable(brief, guard):
            raise TimeoutError
        self.manager.connect_narration('profile-a', self.active.session_id,
            unavailable, self.authorize)
        moment = await self.publish(occurrence)
        self.assertIsNotNone(moment)
        self.assertEqual(moment.content, 'Original {artist} — Original artist.')
        self.assertEqual(moment.as_dict()['music_announcement']['realization'], 'degraded')
        self.assertIsNone(await self.publish(occurrence))

    async def test_twenty_starts_use_separate_budget_with_last_eight_published_frames(self):
        frames = []
        async def model(brief, guard):
            guard()
            self.assertEqual(brief.recent_frames, tuple(frames[-8:]))
            # Distinct fixture frames stand in for independently reviewed output.
            frame = '{artist} — {track}. Geef dit moment ruimte' + '!' * (len(frames)+1)
            frames.append(frame)
            return self.briefs.NarratedText(brief.render(frame), frame)
        registration = self.manager._narration_providers['profile-a']
        self.manager.connect_narration('profile-a', self.active.session_id, model, self.authorize,
            archive_admission=registration[4])
        for index in range(20):
            occurrence = await self.sample(chr(65+index))
            self.assertIsNotNone(await self.publish(occurrence))
        active = self.manager.current_active('profile-a')
        self.assertEqual(active.presence_ledger.announcements_published, 20)
        # Presence-change confirmation already used its explicit settings route;
        # no intro consumed the auxiliary per-track/rolling quotas.
        self.assertEqual(active.presence_ledger.total_published, 0)
        self.assertEqual(active.broadcast.track_announcements.recent_frames, tuple(frames[-8:]))
        entries = await self.repo.async_entry_records('profile-a', active.session_id)
        self.assertEqual(sum(json.loads(e['body']).get('moment_type') == 'music_announcement' for e in entries), 20)

    async def test_private_queue_hint_is_reused_only_when_actually_started(self):
        await self.sample()
        before = self.manager.current_active('profile-a').broadcast.state.dj_moments
        observed = SimpleNamespace(state='playing', position_ms=165000, duration_ms=180000)
        preview = {'_announcement_candidates': [{'uri':'spotify:track:'+'B'*22}],
                   'deadline':time.monotonic()+30}
        for _ in range(3):
            await self.module.prepare_next(self.manager, owner_profile_id='profile-a',
                session_id=self.active.session_id, observed=observed, preview=preview,
                authorize=lambda: self.valid)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(before, self.manager.current_active('profile-a').broadcast.state.dj_moments)
        self.assertEqual(self.manager.current_active('profile-a').presence_ledger.announcements_published, 0)
        occurrence = await self.sample('B')
        moment = await self.publish(occurrence)
        self.assertIsNotNone(moment)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(moment.as_dict()['music_announcement']['realization'], 'generated')

    async def test_queued_hint_cannot_survive_reorder_or_source_withdrawal(self):
        await self.sample()
        observed = SimpleNamespace(state='playing', position_ms=165000, duration_ms=180000)
        preview = {'_announcement_candidates': [{'uri':'spotify:track:'+'B'*22}],
                   'deadline':time.monotonic()+30}
        await self.module.prepare_next(self.manager, owner_profile_id='profile-a',
            session_id=self.active.session_id, observed=observed, preview=preview,
            authorize=lambda: self.valid)
        preview['_announcement_candidates'] = [{'uri':'spotify:track:'+'C'*22}]
        observed.position_ms = 1000  # Clearing is independent of preparation window.
        await self.module.prepare_next(self.manager, owner_profile_id='profile-a',
            session_id=self.active.session_id, observed=observed, preview=preview,
            authorize=lambda: self.valid)
        state = self.manager.current_active('profile-a').broadcast.track_announcements
        self.assertEqual(state.preparations, ())

    async def test_expired_start_does_not_expire_manual_text_or_original_art_reference(self):
        from unittest.mock import patch
        from custom_components.djconnect.session_speech import moment_projection
        occurrence = await self.sample()
        moment = await self.publish(occurrence)
        active = self.manager.current_active('profile-a')
        with patch('custom_components.djconnect.session_runtime.time.monotonic', return_value=occurrence.deadline+1):
            speech = moment_projection(active.broadcast, moment, autoplay=True)
        self.assertTrue(speech['manual_allowed'])
        self.assertFalse(speech['autoplay_eligible'])

    async def test_original_identity_and_retention_are_sealed_not_just_text(self):
        from dataclasses import replace
        occurrence = await self.sample()
        moment = await self.publish(occurrence)
        for changed in (replace(moment, session_id='other-session'), replace(moment, moment_id='other-moment'),
                        replace(moment, track_announcement=replace(moment.track_announcement, retained_until='9999-01-01T00:00:00+00:00'))):
            self.assertFalse(self.module.accepted(changed))

    async def test_live_manual_replay_cannot_survive_actual_retained_row_deletion(self):
        from unittest.mock import patch
        from custom_components.djconnect.session_speech import resolve_moment
        occurrence = await self.sample()
        moment = await self.publish(occurrence)
        self.assertTrue(self.module.retained(moment))
        await self.service.async_in_transaction(lambda tx: tx.execute(
            'DELETE FROM djconnect_session_entries WHERE owner_profile_id=? AND session_id=? AND reference_id=?',
            ('profile-a', self.active.session_id, moment.moment_id)))
        # Deliberately retain the old live immutable object: its RAM seal alone
        # cannot replace the actual row or its normal private-history admission.
        with patch.object(self.runtime, 'session_runtime_manager', return_value=self.manager):
            with self.assertRaises(PermissionError):
                await resolve_moment(SimpleNamespace(data={}), 'profile-a',
                    {'session_id':self.active.session_id, 'moment_id':moment.moment_id}, history=object())

    async def test_short_tracks_and_long_original_names_keep_text_without_automatic_speech(self):
        from dataclasses import replace
        from custom_components.djconnect.session_speech import moment_projection
        for index, title in enumerate(('Original '+('long title '*25), 'Short track')):
            occurrence = await self.sample(chr(65+index), title=title)
            if index:
                state = self.manager.current_active('profile-a').broadcast.track_announcements
                occurrence = replace(occurrence, duration_ms=2000)
                state.current_occurrence = occurrence
            moment = await self.publish(occurrence)
            self.assertIsNotNone(moment)
            active = self.manager.current_active('profile-a')
            speech = moment_projection(active.broadcast, moment, autoplay=True)
            self.assertTrue(speech['manual_allowed'])
            self.assertFalse(speech['autoplay_eligible'])
            self.assertIn(title, moment.content)
