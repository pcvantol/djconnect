"""Explicit non-interruption events through existing Flow/Broadcast ownership."""
import asyncio
import json
from dataclasses import replace
import unittest
from unittest.mock import patch
from tests import test_expressive_dj_persona as fixtures


class SilenceLiveDeliveryTest(unittest.TestCase):
    setUpClass=fixtures.ExpressiveDJPersonaTest.__dict__['setUpClass']
    tearDownClass=fixtures.ExpressiveDJPersonaTest.__dict__['tearDownClass']
    source_pair=fixtures.ExpressiveDJPersonaTest.source_pair
    run_sequence=fixtures.ExpressiveDJPersonaTest.run_sequence

    def start(self):
        self.run_sequence(self.runtime.DJPersona.HOME_DJ,count=1)
        self.broadcast=self.session.broadcast
        self.received=[]
        self.broadcast.register_subscription(self.received.append)
        self.spoken=[]
        self.broadcast.owner_moment_speech_delivery=self.spoken.append
        self.before=self.session.presence_ledger.total_published

    def publish(self):
        moment=self.session.moment_engine.create_silence(session_id=self.session.session_id,
            selected_mood=self.session.selected_mood,persona=self.session.dj_persona,
            locale='nl',reason='planned_silence')
        self.session.publish_moment(moment)
        return moment

    def test_live_signal_is_immutable_deduplicated_in_flow_without_speech_or_budget(self):
        self.start()
        with patch('time.monotonic',lambda:110.0):
            silence=self.publish()
            self.session.publish_moment(silence)
            snapshot=self.broadcast.as_dict()
        events=[e for e in self.received if e['event_type']=='dj_moment_published']
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['payload']['dj_moment']['type'],'silence')
        self.assertEqual(events[0]['payload']['dj_moment']['content'],'')
        self.assertEqual(snapshot['native_delivery']['current_silence_moment_id'],silence.moment_id)
        self.assertIsNone(snapshot['native_delivery']['current_moment_id'])
        self.assertEqual(sum(i.moment_id==silence.moment_id for i in self.session.planner.output.session_flow.items),1)
        admission=next(a for a in snapshot['native_delivery']['admissions'] if a['moment_id']==silence.moment_id)
        self.assertEqual(admission['qualification'],'intentional_silence')
        self.assertFalse(admission['current_display_allowed'])
        self.assertEqual(admission['executable_actions'],[])
        self.assertEqual(self.spoken,[])
        self.assertEqual(self.session.presence_ledger.total_published,self.before)
        self.assertNotIn(silence.moment_id,json.dumps(snapshot['session_speech']))

    def test_reconnect_uses_original_deadline_and_expiry_does_not_revive_older_card(self):
        self.start()
        with patch('time.monotonic',lambda:110.0):
            silence=self.publish()
            initial=self.broadcast.as_dict()['native_delivery']
            cursor=self.broadcast.replay_log[-2].recovery_cursor
        with patch('time.monotonic',lambda:115.0):
            resumed=self.broadcast.as_dict()['native_delivery']
            self.broadcast.recover_owner(cursor)
        original=next(a for a in initial['admissions'] if a['moment_id']==silence.moment_id)
        replayed=next(a for a in resumed['admissions'] if a['moment_id']==silence.moment_id)
        self.assertEqual(original['display_expires_at'],replayed['display_expires_at'])
        with patch('time.monotonic',lambda:210.0):
            expired=self.broadcast.as_dict()['native_delivery']
        self.assertIsNone(expired['current_silence_moment_id'])
        self.assertIsNone(expired['current_moment_id'])
        self.assertEqual(self.spoken,[])

    def test_pause_resume_track_change_and_end_clear_current_silence(self):
        for change in ('pause','track','end'):
            with self.subTest(change=change):
                self.start()
                with patch('time.monotonic',lambda:110.0):
                    self.publish()
                    if change=='end':
                        asyncio.run(self.manager.async_end(owner_profile_id='owner'))
                    elif change=='track':
                        self.broadcast.update_playback(replace(self.broadcast.state.playback,item_id='another-item'))
                    else:
                        self.broadcast.update_playback(replace(self.broadcast.state.playback,state='paused'))
                        self.broadcast.update_playback(replace(self.broadcast.state.playback,state='playing'))
                    self.assertIsNone(self.broadcast.as_dict()['native_delivery']['current_silence_moment_id'])

    def test_next_content_moment_replaces_current_silence_without_rewriting_it(self):
        self.start()
        self.runtime_clock[0]=410.0
        with patch('time.monotonic',lambda:410.0):
            silence=self.publish()
            frozen=silence.as_dict()
            original=self.broadcast.state.dj_moments[0]
            newer=replace(original,moment_id='next-qualified-content')
            self.session.publish_moment(newer)
            snapshot=self.broadcast.as_dict()
        self.assertIsNone(snapshot['native_delivery']['current_silence_moment_id'])
        self.assertEqual(snapshot['native_delivery']['current_moment_id'],newer.moment_id)
        self.assertEqual(silence.as_dict(),frozen)
        self.assertEqual(self.spoken,[newer])
