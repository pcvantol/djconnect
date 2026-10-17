"""Actual qualified production and SQLite reopening, not relabelled Moment seeds."""
import time
import unittest
from unittest.mock import patch

from tests import test_session_conversation_history as fixtures
from tests.context_variation_fixtures import source


class PublishedFlowCompletionTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SessionConversationHistoryTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.SessionConversationHistoryTest.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = fixtures.SessionConversationHistoryTest()
        await self.fixture.asyncSetUp()
        self.hass, _, self.history, _, _ = await self.fixture.transport_fixture()
        self.r = self.fixture.runtime
        self.manager = self.fixture.manager
        self.clock = [time.monotonic()]
        self.manager._monotonic_source = lambda: self.clock[0]

    async def asyncTearDown(self):
        await self.fixture.asyncTearDown()

    async def test_actual_source_families_and_silence_survive_reopen_and_search_beyond250(self):
        from custom_components.djconnect import session_facts
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.session_conversation import async_metadata_archive_admission, query_service
        storage = self.hass.data['djconnect']['djconnect_profile_platform']
        await storage.async_upsert_music_account('source-account', 'source-spotify',
            kind=MusicAccountKind.PERSONAL, display_name='Synthetic source account',
            linked_profile_ids=frozenset({'profile-a'}), provider_account_id='fixture-provider-owner')
        captured = {'backend_id': 'source-spotify', 'music_account_id': 'source-account',
                    'provider_entry_id': 'source-entry', 'provider_account_id': 'fixture-provider-owner'}
        session = await self.manager.async_start(owner_profile_id='profile-a', locale='nl',
            selected_mood='groove', music_backend='spotify_direct', history_source_context=captured)
        async def realize(brief, guard):
            # External expression boundary fixture, not a real-LLM style claim.
            guard()
            return brief.seed
        async def archive(binding):
            return await async_metadata_archive_admission(self.hass, 'profile-a', binding, lambda: None)
        self.manager.connect_narration('profile-a', session.session_id, realize, lambda: None,
                                      archive_admission=archive)
        moments = []
        for number, family in enumerate(('description', 'edition', 'credits', 'genre', 'description')):
            session = await self.manager.async_get_active('profile-a')
            if number == 4:
                # Real silence publication/storage, enough to exercise the
                # scan cursor independently of visible-page size.
                for _ in range(260):
                    silence = session.moment_engine.create_silence(session_id=session.session_id,
                        selected_mood=session.selected_mood, persona=session.dj_persona,
                        locale=session.locale, reason='private_test_reason')
                    self.assertTrue(await self.manager._async_persist_moment(session, silence))
                    session.publish_moment(silence)
            catalog, fact = source(family if family in {'description', 'edition'} else 'birth', number)
            if family == 'credits':
                fact = session_facts.recording_facts(catalog, {
                    'id': '00000000-0000-0000-0000-000000000003', 'title': catalog['title'],
                    'artist-credit': [{'artist': {'name': catalog['artist']}}],
                    'relations': [{'target-type': 'artist', 'type': 'producer',
                        'artist': {'name': 'Actual credit fixture', 'id': '00000000-0000-0000-0000-000000000009'}}]})[0]
            elif family == 'genre':
                fact = session_facts.observed_genre_facts({
                    'source': 'spotify_playback_status', 'backend': 'spotify_direct', 'is_playing': True,
                    'media_identity': catalog['uri'], 'title': catalog['title'], 'artist': catalog['artist'],
                    'artist_ids': ['Z'*22], 'genres': ['ambient'], 'genre_source_expires_at': time.monotonic()+1800},
                    media_identity=catalog['uri'], title=catalog['title'], artist=catalog['artist'])[0]
            self.clock[0] += 300
            await self.manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=session.session_id,
                state='playing', media_identity=catalog['uri'], title=catalog['title'], artist=catalog['artist'],
                album=catalog['album_name'], duration_ms=600000, position_ms=0)
            async def provider():
                return {'_qualified_facts': (fact,)}
            moment = await self.manager.async_process_track_started(owner_profile_id='profile-a', session_id=session.session_id,
                media_identity=catalog['uri'], insight_provider=provider, require_current_playback=True, allow_initial_facts=True)
            self.assertIsNotNone(moment, family)
            self.assertIs(moment.source_fact, fact)
            moments.append(moment)
            self.assertIn(moment.moment_id, {m.moment_id for m in session.broadcast.state.dj_moments})
        self.assertEqual([m.moment_type.value for m in moments], ['artist', 'album', 'track', 'genre', 'artist'])
        await self.manager.async_end(owner_profile_id='profile-a', session_id=session.session_id)
        await self.fixture.service.async_close()
        await self.fixture.service.async_initialize()
        query = query_service(self.hass, self.history)
        transaction_counts = []
        original = self.fixture.service.async_in_transaction
        count = [0]
        async def counted(*args, **kwargs):
            count[0] += 1
            return await original(*args, **kwargs)
        before_read = await self.fixture.repo.async_session_record(session.session_id)
        with patch.object(self.fixture.service, 'async_in_transaction', counted):
            for size in (10, 50):
                count[0] = 0
                await query.async_timeline_page('profile-a', session.session_id, limit=size)
                transaction_counts.append(count[0])
        self.assertEqual(transaction_counts[0], transaction_counts[1])
        self.assertLessEqual(max(transaction_counts), 12)
        cursor, entries, pages = '', [], 0
        while True:
            page = await query.async_timeline_page('profile-a', session.session_id, limit=50, cursor=cursor)
            entries.extend(page['entries'])
            pages += 1
            cursor = page['next_cursor']
            if not cursor:
                break
        self.assertGreater(pages, 5)
        # Five genuinely accepted playback observations, five spoken Moments
        # and260silences; no synthetic relabelled contribution types.
        self.assertEqual(len(entries), 270)
        self.assertEqual(len({e['entry_id'] for e in entries}), 270)
        self.assertEqual([e['order'] for e in entries], sorted(e['order'] for e in entries))
        by_id = {e['moment_id']: e for e in entries if e.get('moment_id')}
        for moment in moments:
            retained = by_id[moment.moment_id]
            self.assertEqual(retained['text'], moment.content)
            self.assertTrue(retained['session_speech']['manual_allowed'])
        self.assertTrue(all(e['text'] is None and not e['speech_available']
                            for e in entries if e['kind'] == 'dj_silence'))
        first = await query.async_search_entries('profile-a', session.session_id, 'Nora Vale 5')
        self.assertEqual(first['matches'], [])
        self.assertIsNotNone(first['next_cursor'])
        last = await query.async_search_entries('profile-a', session.session_id, 'Nora Vale 5', cursor=first['next_cursor'])
        self.assertEqual([e['moment_id'] for e in last['matches'] if e.get('moment_id')], [moments[-1].moment_id])
        self.assertEqual(sum(e['kind'] == 'playback_observed' for e in last['matches']), 1)
        self.assertTrue(last['complete'])
        record = await self.fixture.repo.async_session_record(session.session_id)
        self.assertEqual(record['summary']['moments_published']['value'], 5)
        self.assertEqual(record['revision'], before_read['revision'])
        body_bytes = await self.fixture.service.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT SUM(length(body)) FROM djconnect_session_entries WHERE session_id=?', (session.session_id,))[0])
        self.assertLess(body_bytes, 256*1024)
        import os
        import json
        from pathlib import Path
        if capture := os.environ.get('DJC_FLOW_CAPTURE_DIR'):
            (Path(capture)/'qualified-flow-reopen.json').write_text(json.dumps({
                'entries': len(entries), 'spoken_moments': 5, 'silences': 260, 'accepted_playback_observations': 5,
                'page_count': pages, 'query_transactions_page10_and50': transaction_counts,
                'retained_body_bytes': body_bytes, 'read_revision_unchanged': True,
                'source_boundary': 'Synthetic external metadata and expression; actual Planner/Knowledge/Moment/SQLite/query/reopen.'}, indent=2)+'\n')
        self.assertNotIn('private_test_reason', str(entries))
        await self.fixture.repo.async_withdraw_source_entry('source-entry')
        withdrawn = await query.async_open_entry('profile-a', session.session_id, by_id[moments[1].moment_id]['entry_id'])
        self.assertEqual(withdrawn['entry']['order'], by_id[moments[1].moment_id]['order'])
        self.assertIsNone(withdrawn['entry']['text'])
        self.assertFalse(withdrawn['entry']['speech_available'])
