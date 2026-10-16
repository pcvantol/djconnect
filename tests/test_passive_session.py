"""Passive projection invariants over real Runtime/Planner/source-shaped facts."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
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
