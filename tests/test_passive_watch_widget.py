"""Minimal independently consented Watch view; never phone grant replication."""
from dataclasses import replace
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from tests import test_passive_session_progress as progress


class WatchWidgetProjectionTests(unittest.TestCase):
    setUpClass = progress.PassiveProgressTests.__dict__['setUpClass']
    tearDownClass = progress.PassiveProgressTests.__dict__['tearDownClass']
    source_pair = progress.PassiveProgressTests.source_pair
    run_sequence = progress.PassiveProgressTests.run_sequence
    prepare = progress.PassiveProgressTests.prepare
    sample = progress.PassiveProgressTests.sample

    def watch_frame(self, elapsed=1):
        grant = replace(self.grant, surface='watch_widget', projection_version=1, locked_display=True)
        with patch('time.monotonic', return_value=100+elapsed), patch('time.time', return_value=self.wall+elapsed):
            return self.passive.projection(self.session, grant)

    def test_watch_contains_only_selected_track_mood_and_original_source_bindings(self):
        self.sample()
        frame = self.watch_frame()
        self.assertEqual(frame['scope'], 'paired_watch_widget_v1')
        self.assertEqual(frame['surface'], 'watch_widget')
        self.assertEqual(frame['schema_version'], 1)
        self.assertEqual(frame['now_playing']['track'], 'Original track')
        self.assertEqual(set(frame['now_playing']), {'item_id','subject_uri','track','observed_at',
            'expires_at','source_url','attribution','usage_basis'})
        for key in ('contribution','contribution_status','persona','presence','navigation','playback_state'):
            self.assertNotIn(key, frame)
        self.assertNotIn('progress', frame['now_playing'])
        self.assertEqual(frame['cache_policy']['scope'], 'current_watch_widget_only')
        self.assertIs(frame['cache_policy']['locked_display'], True)

    def test_watch_minimal_envelope_is_closed(self):
        self.sample()
        frame = self.watch_frame()
        self.assertEqual(set(frame), {'schema_version','scope','surface','binding_id','generation',
            'session_id','delivery_sequence','as_of','observed_at','expires_at','state',
            'cache_policy','mood','now_playing','artwork','now_playing_status','artwork_status','revision'})

    def test_watch_read_does_not_refresh_sample_or_original_expiry(self):
        b, _ = self.sample()
        original = b.passive_observation
        first, second = self.watch_frame(), self.watch_frame(8)
        self.assertEqual(first['now_playing'], second['now_playing'])
        self.assertEqual(first['revision'], second['revision'])
        self.assertIs(b.passive_observation, original)
        self.assertIsNone(self.watch_frame(121)['now_playing'])

    def test_watch_authority_withdrawal_has_no_phone_or_contribution_fallback(self):
        self.sample()
        self.grant = replace(self.grant, authority=lambda: False)
        frame = self.watch_frame()
        self.assertEqual(frame['state'], 'withdrawn')
        self.assertIsNone(frame.get('now_playing'))
        self.assertEqual(frame['artwork'], [])
        self.assertNotIn('contribution', frame)


class WatchWidgetRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_cross_scope_and_missing_locked_consent_fail_before_live_owner_lookup(self):
        from tests.test_http_voice_helpers import install_http_stubs
        install_http_stubs()
        from custom_components.djconnect import passive_session
        base = {'contract_version':1,'device_id':'djconnect-watchos-ABCDEF123456',
                'client_type':'watchos','session_id':'original-session','surface':'watch_widget',
                'projection_version':1,'grant_id':'synthetic-not-live'}
        for changed in [{'client_type':'ios'},{'client_type':'macos'}, {'surface':'widget'},
                        {'surface':'live_activity'}, {'projection_version':3}]:
            _, code = await passive_session.handle(SimpleNamespace(), {**base,**changed})
            self.assertEqual(code, 400)
        capability = passive_session.capability()
        self.assertEqual(capability['watch_widget']['scope'], 'paired_watch_widget_v1')
        self.assertEqual(capability['watch_widget']['client_type'], 'watchos')
        self.assertIs(capability['watch_replication'], False)
