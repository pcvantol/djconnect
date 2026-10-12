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
            before = projection.as_dict()
            now[0] = 221.0
            expired = projection.as_dict()
            self.assertEqual(expired['revision'], before['revision'])
            self.assertEqual(expired['valid_until'], before['valid_until'])
            self.assertEqual(expired['sections'], [])
            self.assertEqual(expired['state'], 'expired')
            self.assertTrue(projection.tick())
            self.assertFalse(projection.tick())
            active.broadcast.update_forecast(active)
            fresh = projection.as_dict()
            self.assertGreater(fresh['revision'], expired['revision'])
            self.assertEqual(fresh['state'], 'ready')
            self.assertEqual(projection.deadline, 341.0)
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
