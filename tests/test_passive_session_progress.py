"""Original observation progress only; no provider/model or native authority."""
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

import importlib
import time
from tests import test_expressive_dj_persona as sources


class PassiveProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources.ExpressiveDJPersonaTest.setUpClass.__func__(cls)
        cls.passive = importlib.import_module('custom_components.djconnect.passive_session')

    tearDownClass = sources.ExpressiveDJPersonaTest.__dict__['tearDownClass']
    source_pair = sources.ExpressiveDJPersonaTest.source_pair
    run_sequence = sources.ExpressiveDJPersonaTest.run_sequence

    def prepare(self):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        self.grant = self.passive.SurfaceGrant('grant', 'binding', 'generation', 'entry',
                                              'widget', False, lambda: True)
        b = self.session.broadcast
        b.passive_state_observed = (100, time.time())
        b.passive_observation = (100, time.time(), b.state.playback)
        return moments

    def sample(self, *, state='playing', position=12000, duration=180000):
        self.prepare()
        self.grant = replace(self.grant, projection_version=3)
        b = self.session.broadcast
        original = self.runtime.RendererSafePlaybackProjection.from_observation(
            state=state, media_identity='spotify:track:'+'A'*22, title='Original track',
            artist='Original artist', album='Original album', duration_ms=duration, position_ms=position)
        b.state = replace(b.state, playback=original)
        self.wall = b.passive_state_observed[1]
        b.passive_observation = (100, self.wall, original)
        return b, original

    def frame(self, *, elapsed=1, monotonic=None, wall=None, version=3):
        with patch('time.monotonic', return_value=100+elapsed if monotonic is None else monotonic), \
                patch('time.time', return_value=self.wall+elapsed if wall is None else wall):
            return self.passive.projection(self.session, replace(self.grant, projection_version=version))

    def test_exact_sample_survives_ticks_and_repeated_reads_without_renewal_or_mutation(self):
        b, original = self.sample()
        b.state = replace(b.state, playback=replace(original, position_ms=90000))
        state, sample, sequence = deepcopy(b.state), b.passive_observation, b.delivery_sequence
        first, later = self.frame(), self.frame(elapsed=8)
        progress = first['now_playing']['progress']
        self.assertEqual(progress['position_ms'], 12000)
        self.assertEqual(progress['duration_ms'], 180000)
        self.assertEqual(progress['playback_state'], 'playing')
        self.assertEqual(progress['schema_version'], 1)
        self.assertEqual(progress['observed_at'], self.passive.stamp(self.wall))
        self.assertEqual(progress['expires_at'], self.passive.stamp(self.wall+120))
        self.assertEqual(progress, later['now_playing']['progress'])
        self.assertEqual(first['revision'], later['revision'])
        self.assertEqual(b.state, state)
        self.assertIs(b.passive_observation, sample)
        self.assertEqual(b.delivery_sequence, sequence)

    def test_paused_original_is_frozen_and_state_mismatch_cannot_continue_old_progress(self):
        b, original = self.sample(state='paused', position=0)
        self.assertEqual(self.frame()['now_playing']['progress']['position_ms'], 0)
        self.assertEqual(self.frame()['now_playing']['progress']['playback_state'], 'paused')
        b.state = replace(b.state, playback=replace(original, state='playing'))
        self.assertNotIn('progress', self.frame()['now_playing'])

    def test_track_switch_and_stop_cannot_keep_old_progress_or_relabel_metadata(self):
        b, original = self.sample()
        for playback in (replace(original, item_id='another-item'), replace(original, state='stopped')):
            b.state = replace(b.state, playback=playback)
            self.assertIsNone(self.frame()['now_playing'])

    def test_invalid_original_numbers_are_absent_without_hiding_qualified_music(self):
        b, original = self.sample()
        for position, duration in [(None, 180000), (True, 180000), (0, False), (0, 0),
                                   (-1, 180000), (180001, 180000), (1.0, 180000),
                                   (0, 9007199254740992), (0, None)]:
            with self.subTest(position=position, duration=duration):
                bad = replace(original, position_ms=position, duration_ms=duration)
                b.passive_observation = (100, self.wall, bad)
                self.assertEqual(self.frame()['now_playing']['track'], 'Original track')
                self.assertNotIn('progress', self.frame()['now_playing'])

    def test_dual_clock_expiry_and_future_clock_never_authorize_progress(self):
        self.sample()
        for elapsed, mono, wall in [(121, None, None), (1, 99, None), (1, None, self.wall-1),
                                    (1, 105, self.wall+121)]:
            with self.subTest(elapsed=elapsed, mono=mono, wall=wall):
                frame = self.frame(elapsed=elapsed, monotonic=mono, wall=wall)
                self.assertNotIn('progress', frame.get('now_playing') or {})

    def test_shorter_outer_snapshot_deadline_caps_progress_without_arrival_reset(self):
        b, _ = self.sample()
        b.passive_state_observed = (90, self.wall-10)
        self.assertEqual(self.frame()['now_playing']['progress']['expires_at'], self.passive.stamp(self.wall+110))

    def test_genuine_new_observation_can_reset_seek_sample_but_read_cannot(self):
        b, original = self.sample()
        before = self.frame()['now_playing']['progress']
        b.passive_observation = (110, self.wall+10, replace(original, position_ms=2000))
        b.passive_state_observed = (110, self.wall+10)
        after = self.frame(elapsed=11)['now_playing']['progress']
        self.assertEqual(after['position_ms'], 2000)
        self.assertNotEqual(after['observed_at'], before['observed_at'])
        self.assertEqual(after['expires_at'], self.passive.stamp(self.wall+130))

    def test_v1_v2_and_direct_music_default_remain_progress_free(self):
        b, _ = self.sample()
        for version in (1, 2):
            self.assertNotIn('progress', self.frame(version=version)['now_playing'])
        with patch('time.time', return_value=self.wall+1):
            music, _ = self.passive._music(b, 101)
        self.assertNotIn('progress', music)
        self.assertEqual(self.passive.capability()['projection_versions'], [1, 2, 3, 4])
        self.assertEqual(self.passive.capability()['default_projection_version'], 1)

    def test_v3_retains_v2_original_contribution_rights_and_private_grant_withdrawal(self):
        self.sample()
        modern = self.frame()
        legacy_v2 = self.frame(version=2)
        self.assertEqual(modern['contribution'], legacy_v2['contribution'])
        self.assertIs(modern['contribution']['rights']['passive_cache'], True)
        self.grant = replace(self.grant, authority=lambda: False)
        withdrawn = self.frame()
        self.assertEqual(withdrawn['state'], 'withdrawn')
        self.assertNotIn('now_playing', withdrawn)
        self.assertEqual(withdrawn['now_playing_status']['reason'], 'authority_withdrawn')

    def test_confirmed_mood_changes_only_confirmed_color_not_original_playback_clock(self):
        import asyncio
        b, _ = self.sample()
        before = self.frame()
        original = b.passive_observation
        with patch('time.monotonic', return_value=101), patch('time.time', return_value=self.wall+1):
            self.session = asyncio.run(self.manager.async_update_mood(owner_profile_id='owner',
                session_id=self.session.session_id, selected_mood='energy',
                expected_revision=self.session.mood_revision))
        after = self.frame(elapsed=2)
        self.assertEqual(after['mood']['value'], 'energy')
        self.assertGreater(after['mood']['revision'], before['mood']['revision'])
        self.assertIs(b.passive_observation, original)
        self.assertEqual(before['now_playing']['progress'], after['now_playing']['progress'])
        self.assertEqual(before['contribution'], after['contribution'])
