"""Passive projection invariants over real Runtime/Planner/source-shaped facts."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_expressive_dj_persona as sources
from custom_components.djconnect import passive_session as passive


class PassiveProjectionTests(unittest.TestCase):
    setUpClass = sources.ExpressiveDJPersonaTest.__dict__['setUpClass']
    tearDownClass = sources.ExpressiveDJPersonaTest.__dict__['tearDownClass']
    source_pair = sources.ExpressiveDJPersonaTest.source_pair
    run_sequence = sources.ExpressiveDJPersonaTest.run_sequence

    def frame(self, now=101, **kwargs):
        with patch('time.monotonic', return_value=now):
            return passive.projection(self.session, self.grant, **kwargs)

    def prepare(self, count=1):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=count)
        self.grant = passive.SurfaceGrant('grant', 'binding', 'generation', 'entry', 'widget', False, lambda: True)
        b = self.session.broadcast
        b.passive_state_observed = (100, time.time())
        b.passive_observation = (100, time.time(), b.state.playback)
        return moments

    def test_real_published_cc0_exact_text_and_all_sources_no_private_payload(self):
        moments = self.prepare()
        frame = self.frame()
        c = frame['contribution']
        self.assertEqual(c['text'], moments[-1].content)
        self.assertEqual(c['source_attribution'], dict(moments[-1].source_attribution))
        for forbidden in ('owner_profile_id', 'device_id', 'grant_id', 'session_flow', 'history', 'audience', 'planner'):
            self.assertNotIn(forbidden, frame)
        self.assertNotIn('bearer', json.dumps(frame).lower())

    def test_repeated_read_keeps_semantics_sequence_revision_deadline_and_no_write(self):
        self.prepare()
        before = deepcopy(self.session.broadcast.state)
        sequence = self.session.broadcast.delivery_sequence
        first, second = self.frame(), self.frame(110)
        self.assertEqual(first['revision'], second['revision'])
        self.assertEqual(first['contribution']['expires_at'], second['contribution']['expires_at'])
        self.assertEqual(first['delivery_sequence'], sequence)
        self.assertEqual(before, self.session.broadcast.state)
        self.assertEqual(sequence, self.session.broadcast.delivery_sequence)

    def test_expiry_is_not_read_repaint_or_reconnect_renewed(self):
        self.prepare()
        self.assertIsNotNone(self.frame()['contribution'])
        expired = self.frame(300)
        self.assertEqual(expired['state'], 'stale')
        self.assertIsNone(expired['contribution'])
        self.assertIsNone(expired['now_playing'])
        self.assertEqual(expired['artwork'], [])

    def test_music_only_suppresses_old_contribution_without_new_publication(self):
        self.prepare()
        b = self.session.broadcast
        b.state = replace(b.state, selected_presence='music_only')
        seq = b.delivery_sequence
        self.assertIsNone(self.frame()['contribution'])
        self.assertEqual(b.delivery_sequence, seq)

    def test_private_owner_contribution_and_unknown_source_are_omitted(self):
        moments = self.prepare()
        b = self.session.broadcast
        original = moments[-1]
        for m in (replace(original, source_fact=None), replace(original,
                  presentation_intent=replace(original.presentation_intent,
                      visibility=self.runtime.DJMomentVisibility.OWNER_ONLY))):
            b.state = replace(b.state, dj_moments=(m,))
            self.assertIsNone(self.frame()['contribution'])

    def test_overlong_copy_is_not_cut_or_rewritten(self):
        moments = self.prepare()
        b = self.session.broadcast
        b.state = replace(b.state, dj_moments=(replace(moments[-1], content='X' * 641),))
        self.assertIsNone(self.frame()['contribution'])

    def test_silence_never_resurrects_an_older_passive_contribution(self):
        self.prepare()
        with patch('time.monotonic', return_value=110):
            silence = self.session.moment_engine.create_silence(
                session_id=self.session.session_id, selected_mood=self.session.selected_mood,
                persona=self.session.dj_persona, locale='nl', reason='planned_silence')
            self.session.publish_moment(silence)
        self.assertIsNone(self.frame(111)['contribution'])
        self.assertIsNone(self.frame(210)['contribution'])

    def test_denied_grant_never_reveals_text_music_or_art(self):
        self.prepare()
        self.grant = replace(self.grant, authority=lambda: False)
        result = self.frame()
        self.assertEqual(result['state'], 'withdrawn')
        self.assertNotIn('contribution', result)
        self.assertNotIn('now_playing', result)
        self.assertEqual(result['artwork'], [])

    def test_pause_remains_active_and_end_withdraws(self):
        self.prepare()
        b = self.session.broadcast
        b.state = replace(b.state, playback=replace(b.state.playback, state='paused'))
        self.assertEqual(self.frame()['state'], 'active')
        self.assertEqual(self.frame()['playback_state'], 'paused')
        asyncio.run(self.manager.async_end(owner_profile_id='owner'))
        self.assertEqual(self.frame()['state'], 'withdrawn')
        self.assertFalse(b.passive_grants)

    def test_metadata_requires_exact_observed_spotify_identity(self):
        self.prepare()
        b = self.session.broadcast
        observed = self.runtime.RendererSafePlaybackProjection.from_observation(
            state='playing', media_identity='spotify:track:'+'A'*22, title='Observed track', artist='Observed artist')
        b.state = replace(b.state, playback=observed)
        b.passive_observation = (100, time.time(), observed)
        frame = self.frame()
        self.assertEqual(frame['now_playing']['subject_uri'], 'spotify:track:'+'A'*22)
        self.assertEqual(frame['now_playing']['track'], observed.title)
        b.state = replace(b.state, playback=replace(b.state.playback, item_id='other'))
        self.assertIsNone(self.frame()['now_playing'])

    def test_v2_independent_empty_playback_artwork_and_freshness_reasons(self):
        self.prepare()
        self.grant = replace(self.grant, projection_version=2)
        b = self.session.broadcast
        b.passive_observation = None
        frame = self.frame()
        self.assertEqual(frame['contribution_status'], {'state': 'available', 'reason': 'qualified'})
        self.assertEqual(frame['now_playing_status']['reason'], 'no_observation')
        self.assertEqual(frame['artwork_status']['reason'], 'not_prepared')
        observed = self.runtime.RendererSafePlaybackProjection.from_observation(
            state='playing', media_identity='spotify:track:'+'A'*22, title='Observed track', artist='Observed artist')
        b.state = replace(b.state, playback=observed)
        b.passive_observation = (100, time.time(), observed)
        self.assertEqual(self.frame()['now_playing_status'], {'state': 'available', 'reason': 'qualified'})
        b.state = replace(b.state, playback=replace(observed, item_id='different'))
        self.assertEqual(self.frame()['now_playing_status']['reason'], 'subject_changed')
        b.state = replace(b.state, playback=replace(observed, state='idle'))
        self.assertEqual(self.frame()['now_playing_status']['reason'], 'playback_inactive')
        b.passive_observation = (0, time.time(), observed)
        self.assertEqual(self.frame(121)['now_playing_status']['reason'], 'original_deadline_expired')
        b.passive_observation = (100, time.time(), replace(observed, source_url='https://example.invalid/'))
        self.assertEqual(self.frame()['now_playing_status']['reason'], 'source_not_qualified')
        for name in ('contribution_status', 'now_playing_status', 'artwork_status'):
            self.assertEqual(self.frame(221)[name], {'state': 'stale', 'reason': 'original_snapshot_expired'})
        self.grant = replace(self.grant, authority=lambda: False)
        for name in ('contribution_status', 'now_playing_status', 'artwork_status'):
            self.assertEqual(self.frame()[name], {'state': 'withdrawn', 'reason': 'authority_withdrawn'})
        self.grant = replace(self.grant, projection_version=1, authority=lambda: True)
        self.assertFalse(any(name.endswith('_status') for name in self.frame() if name != 'playback_state'))
        b.passive_observation = (100, time.time(), replace(observed, source_url='https://example.invalid/track'))
        self.assertIsNone(self.frame()['now_playing'])

    def test_new_media_does_not_make_new_moment_or_publication(self):
        moments = self.prepare()
        now = time.time()
        art = {'state': 'ready', 'subject': {'type': 'album', 'uri': 'spotify:album:'+'B'*22},
               'role': 'cover', 'usage_basis': 'spotify_temporary_owner_display',
               'source_url': 'https://open.spotify.com/album/'+'B'*22,
               'attribution': {'provider': 'Spotify', 'mark': 'spotify', 'url': 'https://open.spotify.com/album/'+'B'*22},
               'expires_at': passive.stamp(now+300), 'captured_at': passive.stamp(now),
               'media_revision': 'r1', 'alt_text': {'en': 'Cover'}, 'width': 64, 'height': 64}
        asset = {'historical': False, 'deadline': 500, 'captured_monotonic': 100, 'authority': lambda: True,
                 'delivery_scope': lambda: (True, False), 'asset_id': 'asset',
                 'projection': {'artwork': art}}
        registry = SimpleNamespace(closed=False, assets={('owner', self.session.session_id,
            (('moment_id', moments[-1].moment_id),)): asset})
        first = self.frame(registry=registry, owner='owner')
        self.assertEqual(len(first['artwork']), 1)
        art['media_revision'] = 'r2'
        second = self.frame(registry=registry, owner='owner')
        self.assertEqual(first['contribution'], second['contribution'])
        self.assertEqual(first['delivery_sequence'], second['delivery_sequence'])
        self.assertNotEqual(first['revision'], second['revision'])
        self.assertNotIn('/session/media/', json.dumps(second))
        art['subject']['type'] = 'artist'
        self.assertEqual(self.frame(registry=registry, owner='owner')['artwork'], [])
        art['subject']['type'] = 'album'
        # Fresh same-item observation + a backwards UTC clock must never renew
        # the existing cover's120monotonic seconds or its image admission.
        b = self.session.broadcast
        observed = self.runtime.RendererSafePlaybackProjection.from_observation(
            state='playing', media_identity='spotify:track:'+'A'*22, title='Observed track', artist='Observed artist')
        b.state = replace(b.state, playback=observed)
        b.passive_observation = (221, now-180, observed)
        b.passive_state_observed = (221, now-180)
        art['subject'].update(type='track', uri='spotify:track:'+'A'*22)
        art['source_url'] = observed.source_url
        art['attribution']['url'] = observed.source_url
        registry.assets = {('owner', self.session.session_id, (('entry_id', 'entry'),)): asset}
        with patch('time.time', return_value=now-180):
            rolled = self.frame(221, registry=registry, owner='owner')
            self.assertIsNotNone(rolled['now_playing'])
            self.assertEqual(rolled['artwork'], [])
        asset.pop('captured_monotonic')
        self.assertEqual(self.frame(registry=registry, owner='owner')['artwork'], [])

    def test_shared_receiver_gets_no_passive_hint_or_private_grant(self):
        self.prepare()
        with patch('time.monotonic', return_value=101):
            owner = self.session.broadcast.as_dict()
            shared = self.session.broadcast.as_dict(include_owner_only=False)
        self.assertTrue(owner['passive_surface']['invalidation_only'])
        self.assertNotIn('passive_surface', shared)

    def test_existing_progress_does_not_refresh_backend_observation_clock(self):
        self.prepare()
        b = self.session.broadcast
        original = b.passive_observation
        with patch('time.monotonic', return_value=150):
            b.update_playback_progress(replace(b.state.playback, position_ms=1234))
        self.assertIs(b.passive_observation, original)

    def test_four_personas_five_languages_preserve_exact_published_copy_and_sources(self):
        for persona in self.runtime.DJPersona:
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                with self.subTest(persona=persona, locale=locale):
                    moments = self.run_sequence(persona, locale=locale, count=1)
                    self.grant = passive.SurfaceGrant('grant', 'binding', 'generation', 'entry',
                        'widget', False, lambda: True)
                    self.session.broadcast.passive_state_observed = (100, time.time())
                    copy = self.frame()['contribution']
                    self.assertIsNotNone(copy)
                    self.assertEqual(copy['text'], moments[-1].content)
                    self.assertEqual(copy['persona'], persona.value)
                    self.assertEqual(copy['source_attribution'], dict(moments[-1].source_attribution))

    def test_exact_observed_uri_hash_is_required_for_passive_metadata(self):
        self.prepare()
        b = self.session.broadcast
        wrong = replace(b.state.playback, source_url='https://open.spotify.com/track/'+'Z'*22)
        b.passive_observation = (100, time.time(), wrong)
        self.assertIsNone(self.frame()['now_playing'])


class PassiveRequestValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_purpose_or_fields_or_no_bearer_rejected_before_resolution(self):
        from tests.test_http_voice_helpers import install_http_stubs
        install_http_stubs()
        data = {'contract_version': 1, 'device_id': 'djconnect-ios-ABCDEF123456',
                'client_type': 'ios', 'session_id': 'session', 'surface': 'widget', 'grant_id': 'grant'}
        for invalid in ({**data, 'surface': 'watch'}, {**data, 'profile_id': 'injected'},
                        {**data, 'contract_version': True}, {**data, 'grant_id': ''}):
            _, status = await passive.handle(SimpleNamespace(), invalid)
            self.assertEqual(status, 400)
        _, status = await passive.handle(SimpleNamespace(), data)
        self.assertEqual(status, 401)


class PassiveEvidenceIdentityTests(unittest.TestCase):
    def test_ha_report_rejects_changed_product_and_executing_harness_bytes(self):
        from scripts.verification.passive_public_v2_lab import verify_source_identity
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product = root/'custom_components/djconnect/fixture.py'
            harness = root/'scripts/verification/fixture.py'
            for path in (product, harness):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('original')
            original = hashlib.sha256(b'original').hexdigest()
            sources = {str(product.relative_to(root)): original}
            scripts = {str(harness.relative_to(root)): original}
            verify_source_identity(root, sources, scripts)
            product.write_text('changed')
            with self.assertRaisesRegex(AssertionError, 'product_source_changed'):
                verify_source_identity(root, sources, scripts)
            product.write_text('original')
            harness.write_text('changed')
            with self.assertRaisesRegex(AssertionError, 'qualification_harness_changed'):
                verify_source_identity(root, sources, scripts)


class PassiveOwnerGrantTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        from tests import test_session_conversation_history as fixtures
        cls.fixtures = fixtures
        fixtures.SessionConversationHistoryTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.SessionConversationHistoryTest.tearDownClass()

    async def test_surface_isolation_and_stale_snapshot_do_not_renew_or_remove_grants(self):
        fixture = self.fixtures.SessionConversationHistoryTest()
        await fixture.asyncSetUp()
        try:
            hass, runtime, _history, identity, headers = await fixture.transport_fixture()
            runtime.entry = SimpleNamespace(entry_id='owner-entry', data=runtime.config, options={})
            session = await fixture.manager.async_start(owner_profile_id='profile-a', locale='nl')
            base = {**identity, 'contract_version': 1, 'session_id': session.session_id}
            # Public source qualification is an explicit external boundary fixture;
            # actual pairing/Profile/Session/privacy and grant handling execute.
            with patch('custom_components.djconnect.forecast_imagery.artist_authority',
                       return_value=lambda: True):
                widget, status = await passive.handle(hass, {**base, 'surface': 'widget',
                    'enabled': True, 'os_snapshot_cache': True, 'locked_display': True},
                    headers=headers, authorize=True)
                self.assertEqual(status, 200, widget)
                live, status = await passive.handle(hass, {**base, 'surface': 'live_activity',
                    'enabled': True, 'os_snapshot_cache': True, 'locked_display': True},
                    headers=headers, authorize=True)
                self.assertEqual(status, 200, live)
                self.assertNotEqual(widget['grant_id'], live['grant_id'])
                await passive.handle(hass, {**base, 'surface': 'live_activity',
                    'enabled': False, 'os_snapshot_cache': True, 'locked_display': True},
                    headers=headers, authorize=True)
                read = {**base, 'surface': 'widget', 'grant_id': widget['grant_id']}
                before = session.broadcast.passive_state_observed
                with patch('time.monotonic', return_value=before[0] + 121), \
                        patch('time.time', return_value=before[1] + 121):
                    stale, status = await passive.handle(hass, read, headers=headers)
                self.assertEqual(status, 200, stale)
                self.assertEqual(stale['passive_session']['state'], 'stale')
                self.assertEqual(stale['passive_session']['expires_at'], widget['passive_session']['expires_at'])
                self.assertEqual(session.broadcast.passive_state_observed, before)
                self.assertIsNone(stale['passive_session']['now_playing'])
                self.assertIsNone(stale['passive_session']['contribution'])
                self.assertEqual(stale['passive_session']['artwork'], [])
                # Only a new accepted playback observation admits fresh metadata.
                await fixture.manager.async_update_playback_projection(owner_profile_id='profile-a',
                    session_id=session.session_id, state='playing', media_identity='spotify:track:'+'B'*22,
                    title='New observed recording', artist='Synthetic performer',
                    duration_ms=120000, position_ms=0)
                fresh, status = await passive.handle(hass, read, headers=headers)
                self.assertEqual(status, 200, fresh)
                self.assertEqual(fresh['grant_id'], widget['grant_id'])
                self.assertEqual(fresh['passive_session']['binding_id'], widget['passive_session']['binding_id'])
                self.assertEqual(fresh['passive_session']['now_playing']['track'], 'New observed recording')
                denied, status = await passive.handle(hass, {**base, 'surface': 'live_activity',
                    'grant_id': live['grant_id']}, headers=headers)
                self.assertEqual(status, 403, denied)
                self.assertEqual(denied['error'], 'surface_grant_invalid')
        finally:
            await fixture.asyncTearDown()

    async def test_projection_version_is_explicit_grant_bound_and_widget_needs_no_lock_consent(self):
        fixture = self.fixtures.SessionConversationHistoryTest()
        await fixture.asyncSetUp()
        try:
            hass, runtime, _, identity, headers = await fixture.transport_fixture()
            runtime.entry = SimpleNamespace(entry_id='owner-entry', data=runtime.config, options={})
            session = await fixture.manager.async_start(owner_profile_id='profile-a', locale='nl')
            base = {**identity, 'contract_version': 1, 'session_id': session.session_id, 'surface': 'widget'}
            consent = {**base, 'enabled': True, 'os_snapshot_cache': True, 'locked_display': False}
            with patch('custom_components.djconnect.forecast_imagery.artist_authority', return_value=lambda: True):
                legacy, code = await passive.handle(hass, consent, headers=headers, authorize=True)
                self.assertEqual(code, 200)
                self.assertEqual(legacy['passive_session']['schema_version'], 1)
                modern, code = await passive.handle(hass, {**consent, 'projection_version': 2},
                                                    headers=headers, authorize=True)
                self.assertEqual(code, 200)
                self.assertEqual(modern['passive_session']['schema_version'], 2)
                self.assertNotEqual(modern['passive_session']['generation'], legacy['passive_session']['generation'])
                read = {**base, 'grant_id': modern['grant_id']}
                for version in (None, 1):
                    request = read if version is None else {**read, 'projection_version': version}
                    denied, code = await passive.handle(hass, request, headers=headers)
                    self.assertEqual((code, denied['error']), (403, 'surface_grant_invalid'))
                valid, code = await passive.handle(hass, {**read, 'projection_version': 2}, headers=headers)
                self.assertEqual(code, 200)
                self.assertEqual(valid['passive_session']['cache_policy']['locked_display'], False)
                for version in (True, '2', 0, 3):
                    _, code = await passive.handle(hass, {**read, 'projection_version': version}, headers=headers)
                    self.assertEqual(code, 400)
                _, code = await passive.handle(hass, {**consent, 'surface': 'live_activity',
                    'projection_version': 2}, headers=headers, authorize=True)
                self.assertEqual(code, 403)
        finally:
            await fixture.asyncTearDown()


class ResearchedPassiveProjectionTests(unittest.IsolatedAsyncioTestCase):
    """Actual Runtime/public-source acceptance; external research/model fixtures."""
    @classmethod
    def setUpClass(cls):
        from tests.test_personal_dj_narration_public_artist import PublicArtistNarrationTest
        cls.story_type = PublicArtistNarrationTest
        cls.story_type.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.story_type.tearDownClass()

    async def asyncSetUp(self):
        self.story = self.story_type()
        await self.story.asyncSetUp()

    async def asyncTearDown(self):
        await self.story.asyncTearDown()

    def frame(self, version=2):
        grant = passive.SurfaceGrant('grant', 'binding', 'generation', 'entry',
            'widget', False, lambda: self.story.authorized, version)
        return passive.projection(self.story.session, grant)

    async def test_v1_never_emits_new_basis_while_v2_preserves_complete_sources_and_pure_reads(self):
        moment = await self.story.publish()
        self.assertIsNotNone(moment, self.story.debug)
        legacy = self.frame(1)
        self.assertIsNone(legacy['contribution'])
        self.assertEqual(legacy['schema_version'], 1)
        self.assertNotIn('contribution_status', legacy)
        before = (len(self.story.calls), len(self.story.urls), self.story.session.presence_ledger.total_published,
                  self.story.session.broadcast.delivery_sequence)
        modern = self.frame()
        self.assertEqual(modern['contribution_status'], {'state': 'available', 'reason': 'qualified'})
        copy = modern['contribution']
        self.assertEqual(copy['text'], moment.content)
        self.assertEqual(copy['usage_basis'], 'public_artist_narration_v1')
        self.assertEqual(copy['sources'], moment.as_dict()['sources'])
        self.assertEqual(copy['expression_license']['id'], 'CC-BY-SA-4.0')
        self.assertTrue(copy['expression_license']['attribution_required'])
        self.assertFalse(copy['rights']['external_relay'])
        for _ in range(20):
            again = self.frame()
            self.assertEqual(again['contribution'], copy)
            self.assertEqual(again['revision'], modern['revision'])
        after = (len(self.story.calls), len(self.story.urls), self.story.session.presence_ledger.total_published,
                 self.story.session.broadcast.delivery_sequence)
        self.assertEqual(before, after)
        for forbidden in ('untrusted_excerpt', 'claim_checks', 'owner_profile_id', 'device_token', 'grant_id'):
            self.assertNotIn(forbidden, json.dumps(modern))

    async def test_forged_public_copy_and_withdrawn_authority_never_enter_passive_cache(self):
        moment = await self.story.publish()
        broadcast = self.story.session.broadcast
        broadcast.state = replace(broadcast.state, dj_moments=(replace(moment, content=moment.content+' Invented.'),))
        result = self.frame()
        self.assertIsNone(result['contribution'])
        self.assertEqual(result['contribution_status']['reason'], 'source_not_qualified')
        self.story.authorized = False
        denied = self.frame()
        self.assertEqual(denied['state'], 'withdrawn')
        self.assertNotIn('contribution', denied)
        self.assertEqual(denied['contribution_status']['reason'], 'authority_withdrawn')

    async def test_each_source_needs_its_own_passive_purpose_and_complete_attribution(self):
        from custom_components.djconnect.passive_contribution import researched_sources
        moment = await self.story.publish()
        sources = moment.as_dict()['sources']
        self.assertEqual(researched_sources(moment, time.monotonic()), sources)
        # Policy-unit negatives over source metadata; original publication and
        # its cryptographic acceptance are independently exercised above.
        for index, field, value in (
                (0, 'license', 'public_page_short_reference'),
                (0, 'revision_url', ''),
                (0, 'revision_url', 'https://evil.example/w/index.php?oldid=1234'),
                (0, 'revision_url', 'https://nl.wikipedia.org/w/index.php?oldid=0'),
                (0, 'revision_url', 'https://nl.wikipedia.org/w/index.php?oldid=1234&title=Another'),
                (0, 'url', 'https://nl.wikipedia.org/wiki/Another'),
                (0, 'language', ''),
                (0, 'untrusted_excerpt', 'Never cache provider prose'),
                (0, 'expires_at', '2000-01-01T00:00:00+00:00'),
                (0, 'expires_at', '2099-01-01T00:00:00'),
                (2, 'provider', 'Public Web'),
                (2, 'license', 'Unknown'),
                (2, 'url', 'https://musicbrainz.org/artist/'+'-'*36)):
            with self.subTest(field=field, value=value):
                altered = deepcopy(sources)
                altered[index][field] = value
                with patch('custom_components.djconnect.public_artist_narration.sources_for', return_value=altered):
                    self.assertIsNone(researched_sources(moment, time.monotonic()))

    async def test_oversized_copy_has_typed_omission_without_rewriting_the_publication(self):
        self.story.answer = self.story.answer.split('. ', 1)[0]+'. Zo kijk ik graag '+('heel rustig, '*44)+'nog even mee.'
        moment = await self.story.publish()
        self.assertIsNotNone(moment)
        self.assertGreater(len(moment.content), 640)
        result = self.frame()
        self.assertIsNone(result['contribution'])
        self.assertEqual(result['contribution_status']['reason'], 'copy_too_long')
        self.assertEqual(self.story.session.broadcast.state.dj_moments[-1].content, moment.content)

    async def test_original_deadline_and_music_only_have_explicit_nonrenewing_omission(self):
        moment = await self.story.publish()
        original = self.frame()['contribution']
        self.assertIsNotNone(original)
        b = self.story.session.broadcast
        boundary = b._moment_delivery_boundaries[moment.moment_id]
        with patch('time.monotonic', return_value=boundary.published_monotonic+100), \
                patch('time.time', return_value=time.time()+100):
            expired = self.frame()
        self.assertIsNone(expired['contribution'])
        self.assertEqual(expired['contribution_status']['reason'], 'original_deadline_expired')
        b.state = replace(b.state, selected_presence='music_only')
        quiet = self.frame()
        self.assertIsNone(quiet['contribution'])
        self.assertEqual(quiet['contribution_status']['reason'], 'presence_music_only')
