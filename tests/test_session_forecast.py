"""Runtime/Planner/Broadcast lifecycle and pure Forecast projection contracts."""
import asyncio
import copy
import sys
import unittest

from tests.test_session_runtime import _load_runtime_module


class SessionForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('custom_components.djconnect.session_runtime', None)
        if cls.previous_const is None:
            sys.modules.pop('custom_components.djconnect.const', None)
        else:
            sys.modules['custom_components.djconnect.const'] = cls.previous_const

    async def start(self, locale='nl', persona=None):
        r = self.runtime
        manager = r.SessionRuntimeManager()
        active = await manager.async_start(owner_profile_id='owner', selected_mood='groove',
            locale=locale, dj_persona=persona or r.DJPersona.HOME_DJ,
            session_start_strategy=r.SessionStartStrategy.DISCOVER)
        await manager.async_update_playback_projection(owner_profile_id='owner', session_id=active.session_id,
            state='playing', media_identity='spotify:track:'+'A'*22, title='Confirmed track',
            artist='Confirmed artist', album='Confirmed edition', duration_ms=300000, position_ms=0)
        return manager, active

    def test_twenty_persona_locale_semantics_and_no_private_horizon(self):
        async def scenario():
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                versions = []
                for persona in self.runtime.DJPersona:
                    manager, active = await self.start(locale, persona)
                    projection = await manager.async_forecast_snapshot(owner_profile_id='owner', session_id=active.session_id)
                    self.assertEqual(projection['state'], 'ready')
                    self.assertEqual([s['claim_type'] for s in projection['sections']],
                                     ['current', 'intention', 'conditional_target'])
                    self.assertIn('Confirmed artist', projection['sections'][1]['text'])
                    self.assertEqual(projection['nominal_window_seconds'], 900)
                    self.assertEqual(projection['supported_window_seconds'], 900)
                    self.assertEqual(projection['imagery'], [])
                    versions.append(projection['sections'][1]['text'])
                    for private in ('planned_intents', 'generation', 'slots', 'owner_profile_id', 'conversation', 'music_dna'):
                        self.assertNotIn(private, repr(projection))
                self.assertEqual(len(set(versions)), 4)
        asyncio.run(scenario())

    def test_all_authored_intentions_have_four_forms_without_changing_facts(self):
        from custom_components.djconnect.forecast_expression import INTENT_FORMS, PERSONAS, realize
        for locale, directions in INTENT_FORMS.items():
            for direction in directions:
                versions = []
                for persona in PERSONAS:
                    summary, sections = realize({'has_current':True,'title':'Actual title','artist':'Actual artist',
                        'album':'Actual edition','source_url':'https://open.spotify.com/track/exact',
                        'guidance':direction,'aim':'groove'},locale,persona)
                    versions.append(summary)
                    self.assertEqual(sections[0]['source_url'],'https://open.spotify.com/track/exact')
                    self.assertEqual(sections[1]['claim_type'],'intention')
                    self.assertEqual(sections[2]['claim_type'],'conditional_target')
                self.assertEqual(len(set(versions)),4,(locale,direction))

    def test_owner_read_purity_repeat_reconnect_and_no_budget_or_planner_changes(self):
        async def scenario():
            manager, active = await self.start()
            before = copy.deepcopy((active.planner.__dict__, active.presence_ledger.__dict__,
                                    active.moment_engine.moments, active.broadcast.delivery_sequence))
            expected = await manager.async_forecast_snapshot(owner_profile_id='owner', session_id=active.session_id)
            for _ in range(50):
                self.assertEqual(await manager.async_forecast_snapshot(owner_profile_id='owner', session_id=active.session_id), expected)
                self.assertEqual(active.broadcast.as_dict()['session_forecast'], expected)
            after = (active.planner.__dict__, active.presence_ledger.__dict__, active.moment_engine.moments,
                     active.broadcast.delivery_sequence)
            self.assertEqual(before, after)
            self.assertIsNone(await manager.async_forecast_snapshot(owner_profile_id='other', session_id=active.session_id))
            with self.assertRaises(PermissionError):
                await manager.async_forecast_snapshot(owner_profile_id='owner',session_id=active.session_id,authorize=lambda:False)
        asyncio.run(scenario())

    def test_localized_reads_preserve_original_deadlines_and_cannot_revive_expired_or_withdrawn_context(self):
        from unittest.mock import patch
        async def scenario():
            manager, active = await self.start('en')
            projection = active.broadcast.forecast
            before = copy.deepcopy((projection.__dict__, active.planner.__dict__,
                                    active.presence_ledger.__dict__, active.broadcast.delivery_sequence))
            with patch.object(active.planner, 'forecast_semantics', side_effect=AssertionError('read replanned')):
                for locale in ('nl','de','fr','es','en'):
                    localized = await manager.async_forecast_snapshot(
                        owner_profile_id='owner', session_id=active.session_id, locale=locale)
                    self.assertEqual(localized['state'], 'ready')
                    self.assertEqual(localized['revision'], projection.revision)
                    self.assertEqual(localized['valid_until'], projection.value['valid_until'])
            self.assertEqual(before, (projection.__dict__, active.planner.__dict__,
                active.presence_ledger.__dict__, active.broadcast.delivery_sequence))
            projection.clock = lambda: projection.deadline
            expired = await manager.async_forecast_snapshot(
                owner_profile_id='owner',session_id=active.session_id,locale='fr')
            self.assertEqual((expired['state'],expired['summary'],expired['sections']),('expired','',[]))
            self.assertEqual(expired['revision'],projection.revision)
            projection.withdraw()
            withdrawn = await manager.async_forecast_snapshot(
                owner_profile_id='owner',session_id=active.session_id,locale='nl')
            self.assertEqual((withdrawn['state'],withdrawn['summary'],withdrawn['sections']),('withdrawn','',[]))
            self.assertEqual(projection._semantic,{})
        asyncio.run(scenario())

    def test_direction_moment_uses_four_authored_personas_without_forecast_media_anchors(self):
        r = self.runtime
        for locale in ('en', 'nl', 'de', 'fr', 'es'):
            for direction_type in r.SessionDirectionType:
                versions = []
                for persona in r.DJPersona:
                    direction = r.SessionDirection(direction=direction_type, initialized_at='fixed',
                        updated_at='fixed', start_strategy=r.SessionStartStrategy.DISCOVER)
                    knowledge = r.DJKnowledgeEngine().assemble_session_direction_context(
                        direction, r.SessionStartStrategy.DISCOVER, 'groove', r.PerformanceMemory(source_flow_id='direction-only'))
                    engine = r.DJMomentEngine()
                    moment = engine.create_session_update(session_id='direction-only',
                        selected_mood='groove', persona=persona, locale=locale,
                        session_direction=direction, knowledge_context=knowledge)
                    self.assertEqual(moment.moment_type, r.DJMomentType.SESSION)
                    self.assertEqual(moment.source_references, ('session_direction',))
                    self.assertEqual(dict(moment.generation_metadata)['direction'], direction_type.value)
                    self.assertEqual(moment.presentation_intent.dj_persona, persona)
                    self.assertNotIn('{', moment.content)
                    from tests.speech_capture import capture
                    capture('direction-knowledge-previews', {'locale': locale, 'persona': persona.value,
                        'direction': direction_type.value, 'moment': moment.as_dict(),
                        'scope': 'Actual Knowledge/Moment realization preview, not independent Runtime publication.'})
                    self.assertNotIn('None', moment.content)
                    versions.append(moment.content)
                self.assertEqual(len(set(versions)), 4, (locale, direction_type))

    def test_direction_persona_is_published_by_existing_runtime_and_immutable_on_live_switch(self):
        async def scenario():
            r = self.runtime
            for locale in ('en', 'nl', 'de', 'fr', 'es'):
                versions = []
                for persona in r.DJPersona:
                    manager = r.SessionRuntimeManager()
                    active = await manager.async_start(owner_profile_id='owner', selected_mood='energy',
                        locale=locale, dj_persona=persona)
                    events = []
                    await manager.async_subscribe(owner_profile_id='owner', session_id=active.session_id,
                        callback=events.append)
                    async def existing_insight():
                        return {}
                    moment = await manager.async_process_track_started(owner_profile_id='owner',
                        session_id=active.session_id, insight_provider=existing_insight)
                    self.assertEqual(moment.moment_type, r.DJMomentType.SESSION)
                    self.assertIn(moment, active.broadcast.state.dj_moments)
                    self.assertIn('dj_moment_published', [e['event_type'] for e in events])
                    from tests.speech_capture import capture
                    capture('direction-runtime-publications', {'locale': locale, 'persona': persona.value,
                        'moment': moment.as_dict(), 'scope': 'Actual Runtime/Planner/Knowledge/Moment/Flow/Broadcast publication.'})
                    versions.append(moment.content)
                    before = moment.as_dict()
                    await manager.async_update_persona(owner_profile_id='owner', session_id=active.session_id,
                        dj_persona=r.DJPersona.FESTIVAL_DJ)
                    self.assertEqual(moment.as_dict(), before)
                    self.assertEqual(len(active.broadcast.state.dj_moments), 1)
                    await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
                self.assertEqual(len(set(versions)), 4, locale)
        asyncio.run(scenario())

    def test_independent_mood_presence_noop_off_and_end(self):
        async def scenario():
            manager, active = await self.start()
            flow = active.planner.output.session_flow
            for mood in ('chill', 'groove', 'energy', 'party'):
                active = await manager.async_update_mood(owner_profile_id='owner', session_id=active.session_id, selected_mood=mood)
                self.assertEqual(active.selected_presence, 'balanced')
                old = active.broadcast.forecast.as_dict()
                same = await manager.async_update_mood(owner_profile_id='owner', session_id=active.session_id, selected_mood=mood)
                self.assertEqual(old, same.broadcast.forecast.as_dict())
            old_ledger = copy.deepcopy(active.presence_ledger.__dict__)
            for presence in ('music_only', 'occasional', 'balanced', 'talkative', 'presenter', 'music_only'):
                active = await manager.async_update_presence(owner_profile_id='owner', session_id=active.session_id, selected_presence=presence)
                forecast = active.broadcast.forecast.as_dict()
                self.assertEqual(active.selected_mood, 'party')
                self.assertEqual(forecast['state'], 'ready')
                if presence == 'music_only':
                    self.assertIn('stil',forecast['sections'][1]['text'])
                self.assertEqual(active.planner.output.session_flow, flow)
                self.assertEqual(active.presence_ledger.__dict__, old_ledger)
                self.assertEqual(active.broadcast.state.dj_moments, ())
            ended = await manager.async_end(owner_profile_id='owner', session_id=active.session_id)
            self.assertIsNotNone(ended)
            self.assertIsNone(await manager.async_forecast_snapshot(owner_profile_id='owner', session_id=active.session_id))
            self.assertEqual(active.broadcast.forecast.as_dict()['sections'], [])
        asyncio.run(scenario())

    def test_original_expiry_read_tick_revision_and_fresh_input(self):
        async def scenario():
            manager, active = await self.start()
            projection = active.broadcast.forecast
            now = [100.0]
            projection.clock = lambda: now[0]
            projection.refreshed_at = now[0]
            projection.deadline = 220.0
            projection.observation_deadline = 220.0
            before = projection.as_dict()
            now[0] = 221.0
            expired = projection.as_dict()
            self.assertEqual(expired['revision'], before['revision'])
            self.assertEqual(expired['valid_until'], before['valid_until'])
            self.assertEqual(expired['sections'], [])
            self.assertEqual(expired['state'], 'expired')
            self.assertTrue(projection.tick())
            self.assertFalse(projection.tick())
            for mood in ('chill', 'groove', 'energy', 'party'):
                active = await manager.async_update_mood(owner_profile_id='owner', session_id=active.session_id, selected_mood=mood)
                self.assertEqual(projection.as_dict()['state'], 'expired')
                self.assertEqual(projection.deadline, 220.0)
            for presence in ('music_only', 'balanced', 'presenter'):
                active = await manager.async_update_presence(owner_profile_id='owner', session_id=active.session_id, selected_presence=presence)
                self.assertEqual(projection.as_dict()['sections'], [])
            for persona in self.runtime.DJPersona:
                active = await manager.async_update_persona(owner_profile_id='owner', session_id=active.session_id, dj_persona=persona)
                self.assertEqual(projection.as_dict()['state'], 'expired')
            await manager.async_update_allowed_capability_intents(owner_profile_id='owner',session_id=active.session_id,allowed_capability_intents=frozenset())
            self.assertEqual(projection.as_dict()['state'], 'expired')
            await manager.async_update_playback_projection(owner_profile_id='owner', session_id=active.session_id,
                state='playing', media_identity='spotify:track:'+'A'*22, title='Confirmed track', artist='Confirmed artist')
            fresh = projection.as_dict()
            self.assertGreater(fresh['revision'], expired['revision'])
            self.assertEqual(fresh['state'], 'ready')
            self.assertEqual(projection.deadline, 341.0)
        asyncio.run(scenario())

    def test_fresh_observation_recovers_withdrawn_projection_without_throttle_delay(self):
        async def scenario():
            manager, active = await self.start()
            projection = active.broadcast.forecast
            self.assertTrue(projection.withdraw())
            self.assertEqual(projection.as_dict()['state'],'withdrawn')
            await manager.async_update_playback_projection(owner_profile_id='owner',session_id=active.session_id,
                state='playing',media_identity='spotify:track:'+'A'*22,title='Confirmed track',artist='Confirmed artist',
                album='Confirmed edition',forecast_authority=lambda:True)
            self.assertEqual(projection.as_dict()['state'],'ready')
        asyncio.run(scenario())

    def test_live_track_and_pause_frames_never_carry_previous_current_claim(self):
        async def scenario():
            manager, active = await self.start()
            events = []
            await manager.async_subscribe(owner_profile_id='owner',session_id=active.session_id,callback=events.append)
            await manager.async_update_playback_projection(owner_profile_id='owner',session_id=active.session_id,
                state='playing',media_identity='spotify:track:'+'B'*22,title='New title',artist='New artist')
            playback_event = next(e for e in events if e['event_type']=='playback_changed')
            self.assertNotIn('session_forecast',playback_event['payload'])
            fresh = active.broadcast.as_dict()
            self.assertEqual(fresh['session_forecast']['current_anchor']['item_id'], fresh['playback']['item_id'])
            self.assertIn('New title',fresh['session_forecast']['sections'][0]['text'])
            events.clear()
            await manager.async_update_playback_projection(owner_profile_id='owner',session_id=active.session_id,
                state='paused',media_identity='spotify:track:'+'B'*22,title='New title',artist='New artist')
            self.assertNotIn('session_forecast',events[0]['payload'])
            # A historical playback frame cannot acquire the live current anchor.
            old = {'playback':{'state':'playing','item_id':'past-track'}}
            self.assertNotIn('session_forecast',active.broadcast._safe_delivery_payload(old, historical=True))
        asyncio.run(scenario())

    def test_missing_paused_changed_context_and_withdrawal(self):
        async def scenario():
            manager = self.runtime.SessionRuntimeManager()
            active = await manager.async_start(owner_profile_id='owner', selected_mood='chill')
            self.assertEqual(active.broadcast.forecast.as_dict()['sections'], [])
            manager, active = await self.start()
            await manager.async_update_playback_projection(owner_profile_id='owner',session_id=active.session_id,
                state='paused',media_identity='spotify:track:'+'A'*22,title='Confirmed track',artist='Confirmed artist')
            self.assertEqual(active.broadcast.forecast.as_dict()['sections'], [])
            withdrawal = active.broadcast.subscription_withdrawal_payload()['session_forecast']
            self.assertEqual(withdrawal['state'], 'withdrawn')
            self.assertEqual(withdrawal['sections'], [])
        asyncio.run(scenario())

    def test_replay_uses_current_snapshot_without_same_revision_poisoning(self):
        async def scenario():
            manager, active = await self.start()
            broadcast = active.broadcast
            cursor = broadcast.owner_recovery_cursor()
            previous = broadcast.as_dict()['session_forecast']
            await manager.async_update_playback_projection(owner_profile_id='owner',session_id=active.session_id,
                state='playing',media_identity='spotify:track:'+'B'*22,title='New title',artist='New artist')
            recovery = broadcast.recover_owner(cursor)
            self.assertEqual(recovery['recovery'],'snapshot_required')
            # A normal monotone consumer can reject <= revisions and still receive B.
            last_revision = previous['revision']
            recovered = recovery['snapshot']['session_forecast']
            self.assertGreater(recovered['revision'],last_revision)
            self.assertEqual(recovered['state'],'ready')
            self.assertIn('New title',recovered['sections'][0]['text'])
            self.assertEqual(recovered,broadcast.as_dict()['session_forecast'])
            cursor = broadcast.owner_recovery_cursor()
            broadcast._publish(self.runtime.BroadcastEventType.SESSION_FLOW_UPDATED,
                {'session_flow':broadcast.state.session_flow.as_dict()})
            recovery = broadcast.recover_owner(cursor)
            self.assertEqual(recovery['recovery'],'replayed')
            for event in recovery['events']:
                self.assertNotIn('session_forecast',event['payload'])
        asyncio.run(scenario())

    def test_projection_imagery_invalidation_preserves_lease_and_fails_closed(self):
        from custom_components.djconnect.session_forecast import ForecastProjection, _valid_wall_deadline
        from datetime import UTC, datetime
        projection = ForecastProjection('session', clock=lambda:10.0,wall_clock=lambda:100.0)
        self.assertFalse(projection.invalidate_imagery(set()))
        projection.accept_observation()
        projection.update({'has_current':True,'title':'Observed','artist':'Actual','guidance':'quiet','source_url':'https://open.spotify.com/track/exact'},
            locale='en',persona='home_dj',current_item_id='track',imagery=({'url':'art',
                'expires_at':datetime.fromtimestamp(200,UTC).isoformat()},))
        deadline = projection.deadline
        original = projection.as_dict()
        self.assertTrue(projection.invalidate_imagery(set()))
        self.assertEqual(projection.deadline,deadline)
        self.assertEqual(projection.as_dict()['revision'],original['revision']+1)
        self.assertFalse(projection.invalidate_imagery(set()))
        projection.authority = lambda:False
        self.assertFalse(projection.update({},locale='en',persona='home_dj'))
        self.assertTrue(projection.tick())
        self.assertFalse(projection.withdraw())
        self.assertEqual(projection.as_dict()['state'],'withdrawn')
        for invalid in (None,'not-a-date',1,'2026-99-99'):
            self.assertFalse(_valid_wall_deadline(invalid,100))
