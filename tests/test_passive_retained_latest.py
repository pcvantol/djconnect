"""Original retained publication lease, independently bounded snapshots; no I/O."""
from dataclasses import replace
from datetime import datetime
import unittest
from unittest.mock import patch
from tests import test_passive_session_progress as original


class RetainedLatestTests(unittest.TestCase):
    setUpClass = original.PassiveProgressTests.__dict__['setUpClass']
    tearDownClass = original.PassiveProgressTests.__dict__['tearDownClass']
    source_pair = original.PassiveProgressTests.source_pair
    run_sequence = original.PassiveProgressTests.run_sequence
    prepare = original.PassiveProgressTests.prepare
    sample = original.PassiveProgressTests.sample

    def frame(self, elapsed=100, version=4):
        with patch('time.monotonic', return_value=100+elapsed), patch('time.time', return_value=self.wall+elapsed):
            return self.passive.projection(self.session, replace(self.grant, projection_version=version))

    def test_original_publication_survives_prominence_but_not_original_retained_deadline(self):
        b, _ = self.sample()
        first = self.frame()
        self.assertIsNone(first['contribution'])
        retained = first['latest_contribution']
        self.assertEqual(retained['purpose'], 'retained_latest')
        self.assertTrue(retained['text'])
        self.assertIsNotNone(first['now_playing'])
        later = self.frame(110)['latest_contribution']
        self.assertEqual(retained['retained_expires_at'], later['retained_expires_at'])
        self.assertEqual(retained['expires_at'], later['expires_at'])
        self.assertLessEqual(datetime.fromisoformat(retained['retained_expires_at']).timestamp(),
                             datetime.fromisoformat(retained['published_at']).timestamp()+1800)
        self.assertIsNone(self.frame(1801)['latest_contribution'])

    def test_snapshot_expiry_removes_latest_without_renewing_publication(self):
        self.sample()
        first = self.frame()['latest_contribution']
        self.assertIsNotNone(first)
        self.assertIsNone(self.frame(121)['latest_contribution'])

    def test_genuine_fresh_snapshot_does_not_restart_original_retained_lease(self):
        b, _ = self.sample()
        first = self.frame()['latest_contribution']
        b.passive_state_observed = (250, self.wall+150)
        second = self.frame(160)['latest_contribution']
        self.assertEqual(first['retained_expires_at'], second['retained_expires_at'])
        self.assertEqual(first['published_at'], second['published_at'])
        self.assertEqual(first['moment_id'], second['moment_id'])
        self.assertNotEqual(first['expires_at'], second['expires_at'])

    def test_no_newest_private_or_overlong_to_older_fallback(self):
        b, _ = self.sample()
        newest = b.state.dj_moments[-1]
        for modified in [replace(newest, content='x'*641), replace(newest,
            presentation_intent=replace(newest.presentation_intent,
                visibility=self.runtime.DJMomentVisibility.OWNER_ONLY))]:
            b.state = replace(b.state, dj_moments=(*b.state.dj_moments[:-1], modified))
            self.assertIsNone(self.frame()['latest_contribution'])

    def test_music_only_pending_withdrawal_and_silence_are_barriers(self):
        b, _ = self.sample()
        for name in ('content_pending', 'content_current_withdrawn'):
            setattr(b,name,True)
            self.assertIsNone(self.frame()['latest_contribution'])
            setattr(b,name,False)
        b.state = replace(b.state, selected_presence='music_only')
        self.assertIsNone(self.frame()['latest_contribution'])

    def test_old_projection_versions_and_live_activity_do_not_gain_retained_copy(self):
        self.sample()
        for version in (1,2,3):
            self.assertNotIn('latest_contribution', self.frame(version=version))

    def test_mood_and_repeat_reads_cannot_republish_or_renew(self):
        b, _ = self.sample()
        sequence = b.delivery_sequence
        first = self.frame()['latest_contribution']
        self.session = replace(self.session, selected_mood='party', mood_revision=self.session.mood_revision+1)
        self.assertEqual(first,self.frame(110)['latest_contribution'])
        self.assertEqual(sequence,b.delivery_sequence)

    def test_original_source_deadline_shortens_retained_lease(self):
        b, _ = self.sample()
        native = b.native_delivery
        def shorter():
            data = native()
            for row in data['admissions']:
                row['source_expires_at'] = self.passive.stamp(self.wall+105)
            return data
        with patch.object(b, 'native_delivery', side_effect=shorter):
            body = self.frame()['latest_contribution']
            self.assertEqual(body['retained_expires_at'], self.passive.stamp(self.wall+105))
            self.assertIsNone(self.frame(110)['latest_contribution'])

    def test_clock_rollback_cannot_display_original_publication(self):
        self.sample()
        with patch('time.monotonic',return_value=99), patch('time.time',return_value=self.wall-1):
            frame = self.passive.projection(self.session,replace(self.grant,projection_version=4))
        self.assertIsNone(frame['latest_contribution'])

    def test_withdrawal_clears_latest_and_keeps_typed_reason(self):
        self.sample()
        self.grant = replace(self.grant,authority=lambda:False)
        frame = self.frame()
        self.assertIsNone(frame['latest_contribution'])
        self.assertEqual(frame['latest_contribution_status']['reason'],'authority_withdrawn')

    def test_silence_never_resurrects_prior_copy(self):
        self.sample()
        with patch('time.monotonic',return_value=150):
            silence=self.session.moment_engine.create_silence(session_id=self.session.session_id,
                persona=self.session.dj_persona,selected_mood=self.session.selected_mood,locale='nl',reason='planned_silence')
            self.session.publish_moment(silence)
        self.assertIsNone(self.frame()['latest_contribution'])
        self.assertEqual(self.frame()['latest_contribution_status']['reason'],'intentional_silence')
