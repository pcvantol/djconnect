"""Causal occurrence and private queue preparation tests; no provider/model I/O."""
import importlib.util
from pathlib import Path
import sys
import unittest

name = 'djc_track_start_announcement_test'
spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] /
    'custom_components/djconnect/track_start_announcement.py')
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)


class OccurrenceTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.state = module.AnnouncementState(lambda: self.now)

    def sample(self, uri='A', **updates):
        data = dict(state='playing', media_uri='spotify:track:'+uri*22,
                    title='Original title', artist='Original artist', position_ms=0,
                    duration_ms=180000, source_context=('original-owner', 'source'), authorize=lambda: True)
        data.update(updates)
        return self.state.observe(**data)

    def test_twenty_starts_each_have_one_occurrence_and_one_attempt(self):
        ids = set()
        for i in range(20):
            occurrence = self.sample(chr(65+i))
            self.assertTrue(self.state.begin(occurrence))
            self.assertFalse(self.state.begin(occurrence))
            self.assertIsNone(self.sample(chr(65+i)))
            ids.add(occurrence.occurrence_id)
            self.state.committed(occurrence, frame='{artist}: {track}. A different angle '+str(i), generated=True)
            self.now += 20
        self.assertEqual(len(ids), 20)
        self.assertEqual(self.state.generated, 20)
        self.assertEqual(len(self.state.recent_frames), 8)

    def test_pause_resume_seek_and_reconnect_do_not_restart(self):
        original = self.sample()
        self.now += 3
        self.sample(position_ms=50000)
        self.sample(state='paused', position_ms=50000)
        self.now += 50
        self.assertIsNone(self.sample(position_ms=50000))
        self.assertIsNone(self.sample(position_ms=0))
        self.assertIs(self.state.current_occurrence, original)

    def test_observed_natural_repeat_is_new_but_tail_seek_is_not(self):
        original = self.sample()
        self.now += 177
        self.sample(position_ms=177000)
        self.now += 1
        self.assertIsNone(self.sample(position_ms=0))  # Did not cross the end.
        self.sample(position_ms=178000)
        self.now += 3
        repeated = self.sample(position_ms=1000)
        self.assertIsNotNone(repeated)
        self.assertNotEqual(original.occurrence_id, repeated.occurrence_id)

    def test_late_observation_has_no_catchup_and_deadline_never_renews(self):
        self.assertIsNone(self.sample(position_ms=20000))
        self.assertIsNone(self.sample(position_ms=21000))
        occurrence = self.sample('B', position_ms=2000)
        self.assertEqual(occurrence.deadline, self.now+10)
        self.now += 11
        self.assertFalse(self.state.begin(occurrence))
        self.assertIsNone(self.sample('B', position_ms=0))

    def test_queue_preparation_never_mints_an_occurrence_or_reuses_old_context(self):
        candidate = module.PreparedIntro('spotify:track:'+'A'*22, 0, 'queue1', ('mood',),
            ('original-owner','source'), '{artist} — {track}. A thought.', self.now, self.now+90, lambda: True)
        self.state.accept_preparations('queue1', [candidate])
        self.assertIsNone(self.state.current_occurrence)
        occurrence = self.sample()
        self.assertIsNone(self.state.take_prepared(occurrence, ('changed-mood',)))
        # A new actual source capture invalidates the original queue authority.
        self.assertEqual(self.state.preparations, ())

    def test_no_occurrence_without_original_source_authority(self):
        self.assertIsNone(self.sample(authorize=lambda: False))
        self.assertIsNone(self.state.current_occurrence)
