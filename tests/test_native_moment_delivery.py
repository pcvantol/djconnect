"""Native admission through real resolver → Runtime → Flow/Broadcast."""
import asyncio
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from tests import test_expressive_dj_persona as source_tests


class NativeMomentDeliveryTest(unittest.TestCase):
    # Reuse only the source-shaped fixture; existing regression tests run separately.
    setUpClass = source_tests.ExpressiveDJPersonaTest.__dict__["setUpClass"]
    tearDownClass = source_tests.ExpressiveDJPersonaTest.__dict__["tearDownClass"]
    source_pair = source_tests.ExpressiveDJPersonaTest.source_pair
    run_sequence = source_tests.ExpressiveDJPersonaTest.run_sequence
    def test_native_current_and_flow_admission_preserve_two_sources(self):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=2)
        with patch('time.monotonic', lambda: 400.0):
            snapshot = self.session.broadcast.as_dict()
        native = snapshot['native_delivery']
        self.assertEqual(native['schema_version'], 1)
        self.assertEqual(native['current_moment_id'], moments[1].moment_id)
        self.assertEqual(native['active_flow_moment_ids'], [m.moment_id for m in moments])
        second = next(m for m in snapshot['dj_moments'] if m['moment_id'] == moments[1].moment_id)
        self.assertEqual(second['content'], moments[1].content)
        self.assertEqual(second['source_attribution'], dict(moments[1].source_attribution))
        self.assertIn('url_previous', second['source_attribution'])
        self.assertEqual(native['admissions'][1]['executable_actions'], [])

    def test_expiry_never_restores_text_flow_label_presentation_or_replay(self):
        moments = self.run_sequence(self.runtime.DJPersona.RADIO_DJ, count=2)
        broadcast = self.session.broadcast
        cursor = broadcast.replay_log[0].recovery_cursor
        with patch('time.monotonic', lambda: 1901.0):
            snapshot = broadcast.as_dict()
            recovery = broadcast.recover_owner(cursor)
        encoded = json.dumps(snapshot) + json.dumps(recovery)
        self.assertNotIn(moments[0].content, encoded)
        self.assertNotIn(moments[1].content, encoded)  # shortest source is A
        self.assertEqual(snapshot['native_delivery']['active_flow_moment_ids'], [])
        self.assertNotIn(moments[0].title, encoded)
        self.assertEqual(snapshot['presentations'], [])
        self.assertEqual(recovery['recovery'], 'snapshot_required')

    def test_pause_end_and_unknown_qualification_fail_closed(self):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        broadcast = self.session.broadcast
        with patch('time.monotonic', lambda: 101.0):
            broadcast.update_playback(replace(broadcast.state.playback, state='paused'))
            self.assertIsNone(broadcast.as_dict()['native_delivery']['current_moment_id'])
            broadcast.state = replace(broadcast.state, dj_moments=(replace(moments[0], source_fact=None),))
            self.assertEqual(broadcast.as_dict()['native_delivery']['active_flow_moment_ids'], [])
            asyncio.run(self.manager.async_end(owner_profile_id='owner'))
            self.assertEqual(broadcast.as_dict()['native_delivery']['active_flow_moment_ids'], [])

    def test_deadlines_are_stable_across_reconnect_and_card_duration_is_distinct(self):
        moments = self.run_sequence(self.runtime.DJPersona.CLUB_DJ, count=1)
        with patch('time.monotonic', lambda: 101.0):
            first = self.session.broadcast.as_dict()['native_delivery']
        with patch('time.monotonic', lambda: 150.0):
            second = self.session.broadcast.as_dict()['native_delivery']
        self.assertEqual(first['admissions'][0]['source_expires_at'], second['admissions'][0]['source_expires_at'])
        self.assertIsNone(second['current_moment_id'])
        self.assertEqual(second['active_flow_moment_ids'], [moments[0].moment_id])

    def test_shortest_source_deadline_and_invalidation_on_existing_paused_tick(self):
        moments = self.run_sequence(self.runtime.DJPersona.RADIO_DJ, count=2)
        broadcast = self.session.broadcast
        received = []
        broadcast.register_subscription(received.append)
        with patch('time.monotonic', lambda: 401.0):
            broadcast.update_playback(replace(broadcast.state.playback, state='paused'))
            before = broadcast.as_dict()['native_delivery']
        self.assertEqual(before['admissions'][0]['source_expires_at'], before['admissions'][1]['source_expires_at'])
        with patch('time.monotonic', lambda: 1900.0):
            asyncio.run(self.manager.async_advance_playback_progress(owner_profile_id='owner', session_id=self.session.session_id))
        self.assertEqual(received[-1]['event_type'], 'session_flow_updated')
        self.assertEqual(received[-1]['payload']['native_delivery']['active_flow_moment_ids'], [])
        self.assertNotIn(moments[0].title, json.dumps(received[-1]))

    def test_pending_delivery_rechecks_expiry_and_foreign_session_publication(self):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        broadcast = self.session.broadcast
        received = []
        token = broadcast.register_pending_subscription(received.append)
        with patch('time.monotonic', lambda: 110.0):
            broadcast.publish_session_flow(broadcast.state.session_flow)
        with patch('time.monotonic', lambda: 1901.0):
            broadcast.activate_subscription(token)
        self.assertNotIn(moments[0].title, json.dumps(received))
        self.assertEqual(received[-1]['payload']['native_delivery']['active_flow_moment_ids'], [])
        count = len(broadcast.state.dj_moments)
        broadcast.publish_moment(replace(moments[0], session_id='another-session', moment_id='foreign'))
        self.assertEqual(len(broadcast.state.dj_moments), count)

    def test_immutable_semantics_and_original_identity_survive_repeated_projection(self):
        moments = self.run_sequence(self.runtime.DJPersona.FESTIVAL_DJ, count=2)
        original = [m.as_dict() for m in moments]
        with patch('time.monotonic', lambda: 401.0):
            snapshot = self.session.broadcast.as_dict()
            source = moments[0].source_fact
            self.assertNotEqual(source.media_identity, moments[1].source_fact.media_identity)
            self.assertEqual(snapshot['dj_moments'][0]['playback_item_id'], self.session.broadcast._moment_playback_item_ids[moments[0].moment_id])
            self.assertNotEqual(snapshot['dj_moments'][0]['playback_item_id'], snapshot['playback']['item_id'])
        with patch('time.monotonic', lambda: 9999.0):
            self.session.broadcast.as_dict()
        self.assertEqual([m.as_dict() for m in moments], original)

    def test_malformed_source_wrong_attribution_and_flow_removal_fail_closed(self):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        broadcast = self.session.broadcast
        fact = moments[0].source_fact
        for source, attrs in ((replace(fact, license='invented'), moments[0].source_attribution),
                              (replace(fact, observed_at=float('nan')), moments[0].source_attribution),
                              (fact, (("provider", 'MusicBrainz'),))):
            broadcast.state = replace(broadcast.state, dj_moments=(replace(moments[0], source_fact=source, source_attribution=attrs),))
            with patch('time.monotonic', lambda: 101.0):
                projection = broadcast.as_dict()
            self.assertEqual(projection['native_delivery']['active_flow_moment_ids'], [])
            self.assertEqual(projection['dj_moments'], [])
        broadcast.state = replace(broadcast.state, dj_moments=tuple(moments),
            session_flow=replace(broadcast.state.session_flow, items=()))
        with patch('time.monotonic', lambda: 101.0):
            self.assertEqual(broadcast.as_dict()['native_delivery']['active_flow_moment_ids'], [])

    def test_receiver_events_never_reveal_owner_only_admission_or_flow_label(self):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        broadcast = self.session.broadcast
        received = []
        broadcast.subscribe_with_broadcast_token(broadcast.broadcast_token, received.append)
        owner = replace(moments[0], moment_id='owner-only-card', title='private source label',
            presentation_intent=replace(moments[0].presentation_intent, visibility=self.runtime.DJMomentVisibility.OWNER_ONLY))
        with patch('time.monotonic', lambda: 101.0):
            self.session.publish_moment(owner)
            broadcast.update_playback(replace(broadcast.state.playback, position_ms=1000))
            snapshot = broadcast.as_dict(include_owner_only=False)
        self.assertNotIn('owner-only-card', json.dumps(received) + json.dumps(snapshot))
        self.assertNotIn('private source label', json.dumps(received) + json.dumps(snapshot))
        for event in received:
            self.assertNotIn(owner.moment_id, event['payload']['native_delivery']['active_flow_moment_ids'])

    def test_pause_resume_seek_and_track_return_never_reactivate_old_current(self):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        broadcast = self.session.broadcast
        original = broadcast.state.playback
        with patch('time.monotonic', lambda: 101.0):
            broadcast.update_playback(replace(original, state='paused'))
            broadcast.update_playback(original)
            self.assertIsNone(broadcast.as_dict()['native_delivery']['current_moment_id'])
            self.assertEqual(broadcast.as_dict()['native_delivery']['active_flow_moment_ids'], [moments[0].moment_id])
        # Fresh card, then a real Runtime seek invalidates current authority.
        self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        async def seek():
            await self.manager.async_update_playback_projection(owner_profile_id='owner', session_id=self.session.session_id,
                state='playing', media_identity=self.source_pair(0)[0]['uri'], title='Amber Lines', artist='Artist 0',
                album='Test edition', duration_ms=300000, position_ms=150000)
        with patch('time.monotonic', lambda: 101.0):
            asyncio.run(seek())
            self.assertIsNone(self.session.broadcast.as_dict()['native_delivery']['current_moment_id'])

    def test_terminal_delivery_removes_all_admissions_and_original_authority(self):
        self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        broadcast = self.session.broadcast
        events=[]
        broadcast.register_subscription(events.append)
        asyncio.run(self.manager.async_end(owner_profile_id='owner'))
        for projection in [broadcast.as_dict(), broadcast.as_dict(include_owner_only=False), *[e['payload'] for e in events]]:
            native=projection['native_delivery']
            self.assertEqual(native['admissions'], [])
            self.assertEqual(native['active_flow_moment_ids'], [])
            self.assertIsNone(native['current_moment_id'])
        self.assertEqual(broadcast._moment_delivery_boundaries, {})
        self.assertIsNone(asyncio.run(self.manager.async_get_active('owner')))

    def test_internal_session_context_recovery_reprojects_card_expiry(self):
        moments = self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        broadcast=self.session.broadcast
        internal=replace(moments[0], moment_id='internal-update', source_fact=None, source_attribution=(),
                         source_references=('session_direction',))
        broadcast.state=replace(broadcast.state, dj_moments=(), presentations=())
        with patch('time.monotonic', lambda: 101.0):
            cursor=broadcast.owner_recovery_cursor()
            self.session.publish_moment(internal)
        with patch('time.monotonic', lambda: 200.0):
            recovered=broadcast.recover_owner(cursor)
            snapshot=broadcast.as_dict()
        self.assertEqual(recovered['recovery'], 'replayed')
        for event in recovered['events']:
            self.assertIsNone(event['payload']['native_delivery']['current_moment_id'])
            self.assertGreater(event['delivery_sequence'], 0)
        self.assertIsNone(snapshot['native_delivery']['current_moment_id'])

    def test_active_runtime_projection_has_no_alternate_expired_planner_label(self):
        moments=self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=2)
        with patch('time.monotonic', lambda: 1901.0):
            active=self.session.as_dict()
        for moment in moments:
            self.assertNotIn(moment.title, json.dumps(active))
            self.assertNotIn(moment.content, json.dumps(active))
        self.assertEqual(active['planner']['output']['session_flow'], active['broadcast']['session_flow'])

    def test_native_source_policy_covers_existing_fields_without_history_for_spotify(self):
        from tests.test_session_facts import SessionFactsTest
        fixture=SessionFactsTest()
        self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        catalog=fixture.catalog()
        clock=100.0
        with patch('time.monotonic', lambda: clock):
            spotify=self.facts.catalog_facts(catalog)[0]
            manager=self.runtime.SessionRuntimeManager()
            session=asyncio.run(manager.async_start(owner_profile_id='another-owner'))
            asyncio.run(manager.async_update_playback_projection(owner_profile_id='another-owner', session_id=session.session_id,
                state='playing', media_identity=catalog['uri']))
            engine=session.moment_engine
            moment=engine.create_qualified_fact(session_id=session.session_id,
                intent=self.runtime.KnowledgeIntent(self.runtime.KnowledgeIntentType.ALBUM_STORY, 'display current album'),
                fact=spotify, selected_mood='neutral', persona=self.runtime.DJPersona.HOME_DJ, locale='en')
            session.publish_moment(moment)
            native=session.broadcast.as_dict()['native_delivery']
        self.assertEqual(native['current_moment_id'], moment.moment_id)
        self.assertEqual(native['active_flow_moment_ids'], [])
        self.assertTrue(native['admissions'][0]['requires_spotify_attribution'])
        self.assertEqual(native['admissions'][0]['executable_actions'], [])

    def test_runtime_publication_is_idempotent_and_rejects_other_session(self):
        moments=self.run_sequence(self.runtime.DJPersona.HOME_DJ, count=1)
        before=self.session.planner.output.session_flow
        sequence=self.session.broadcast.delivery_sequence
        self.session.publish_moment(moments[0])
        self.session.publish_moment(replace(moments[0], session_id='other-session', moment_id='foreign'))
        self.assertEqual(self.session.planner.output.session_flow, before)
        self.assertEqual(self.session.broadcast.delivery_sequence, sequence)
