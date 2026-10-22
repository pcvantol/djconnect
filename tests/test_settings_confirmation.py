"""Causal accepted-choice/SQLite/native/speech regressions, no model or devices."""
from dataclasses import replace
import sqlite3
from contextlib import closing
import unittest
from unittest.mock import patch

from tests import test_profile_dj_settings_runtime as fixture
from tests.test_profile_dj_settings_persistence import operation


class SettingsConfirmationTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixture.ProfileSettingsRuntimeTests.asyncSetUp
    asyncTearDown = fixture.ProfileSettingsRuntimeTests.asyncTearDown
    expected = fixture.ProfileSettingsRuntimeTests.expected
    choose = fixture.ProfileSettingsRuntimeTests.choose

    async def counts(self):
        return await self.service.async_in_transaction(lambda tx: (
            tx.fetchone("SELECT count(*) FROM djconnect_session_entries WHERE kind='dj_moment'")[0],
            tx.fetchone("SELECT count(*) FROM djconnect_session_acceptances WHERE kind='dj_moment'")[0]))

    async def test_three_axes_one_combined_confirmation_paused_music_only_budget_exempt(self):
        self.active.presence_ledger.total_published = 7
        result = await self.choose({'mood':'energy','persona':'festival_dj','presence':'music_only'})
        a = self.manager.current_active('owner')
        self.assertEqual(len(a.broadcast.state.dj_moments), 1)
        m = a.broadcast.state.dj_moments[0]
        self.assertEqual(result['settings_confirmation']['changed_fields'], ['mood','persona','presence'])
        self.assertEqual(result['settings_confirmation']['text'], m.content)
        self.assertEqual(m.presentation_intent.dj_persona.value, 'festival_dj')
        self.assertEqual(a.presence_ledger.total_published, 7)
        self.assertEqual(await self.counts(), (1,1))
        native = a.broadcast.native_delivery()
        self.assertEqual(native['current_moment_id'], m.moment_id)
        from custom_components.djconnect.session_speech import moment_projection
        speech = moment_projection(a.broadcast, m, autoplay=True)
        self.assertTrue(speech['autoplay_eligible'], speech)
        a.broadcast.owner_speech_output = lambda:'text_only'
        self.assertFalse(moment_projection(a.broadcast,m,autoplay=True)['manual_allowed'])

    async def test_noop_and_voice_change_and_replay_do_not_duplicate(self):
        first = await self.choose({'mood':'energy'})
        boundary = self.manager.current_active('owner').broadcast._moment_delivery_boundaries.copy()
        replay = await self.choose({'mood':'energy'})
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['settings_confirmation'], replay['settings_confirmation'])
        a = self.manager.current_active('owner')
        noop = await self.choose({'mood':'energy'},expected_defaults=1,expected_session=self.expected(a),counter=2)
        self.assertNotIn('settings_confirmation', noop)
        a = self.manager.current_active('owner')
        await self.choose({'announcement_output':'text_only'},expected_defaults=1,
                          expected_session=self.expected(a),counter=3)
        self.assertEqual(await self.counts(), (1,1))
        self.assertEqual(a.broadcast._moment_delivery_boundaries, boundary)

    async def test_failed_history_staging_rolls_back_settings_and_receipt(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER reject_confirmation BEFORE INSERT ON djconnect_session_entries WHEN NEW.kind='dj_moment' BEGIN SELECT RAISE(ABORT,'injected confirmation failure'); END")
        with self.assertRaises(RuntimeError):
            await self.choose({'persona':'radio_dj'})
        self.assertIs(self.manager.current_active('owner'), self.active)
        self.assertEqual((await self.repo.async_read('owner',authorize=lambda:True))['defaults_revision'],0)
        self.assertEqual(await self.counts(),(0,0))
        status = await self.manager.async_dj_settings_operation_result(owner_profile_id='owner',
            operation_id=operation(self.now,1),binding='b'*64,now_ms=self.now,authorize=lambda:True)
        self.assertNotEqual(status['phase'], 'accepted')

    async def recover_after_fault(self, history_enabled, readback):
        if not history_enabled:
            await self.manager.async_end(owner_profile_id='owner',session_id=self.active.session_id)
            self.active = await self.manager.async_start(owner_profile_id='owner',selected_mood='chill',history_enabled=False)
        with patch.object(type(self.active), 'compose_moment', side_effect=RuntimeError('postcommit failure')):
            first = await self.choose({'mood':'energy'})
        self.assertTrue(first['accepted'])
        self.assertTrue(first['delivery_pending'])
        a = self.manager.current_active('owner')
        self.assertFalse(a.broadcast.state.dj_moments)
        boundaries = a.broadcast._moment_delivery_boundaries.copy()
        counts = await self.counts()
        if readback:
            result = await self.manager.async_dj_settings_operation_result(owner_profile_id='owner',
                operation_id=operation(self.now,1),binding='b'*64,now_ms=self.now,authorize=lambda:True)
            self.assertEqual(result['phase'],'accepted')
        else:
            self.assertTrue((await self.choose({'mood':'energy'}))['replayed'])
        self.assertEqual(len(a.broadcast.state.dj_moments),1)
        self.assertEqual(a.broadcast.state.dj_moments[0].moment_id, first['settings_confirmation']['moment_id'])
        self.assertEqual(a.broadcast._moment_delivery_boundaries,boundaries)
        self.assertEqual(await self.counts(),counts)
        self.assertEqual(counts,(1,1) if history_enabled else (0,0))
        self.assertEqual(a.presence_ledger.total_published,0)
        await self.choose({'mood':'energy'})
        self.assertEqual(len(a.broadcast.state.dj_moments),1)

    async def test_postcommit_fault_replay_repairs_original_once(self):
        await self.recover_after_fault(True,False)

    async def test_postcommit_fault_readback_repairs_original_history_off(self):
        await self.recover_after_fault(False,True)

    async def test_superseded_pending_and_aba_never_revive(self):
        with patch.object(type(self.active),'compose_moment',side_effect=RuntimeError('postcommit failure')):
            first = await self.choose({'mood':'energy'})
        a = self.manager.current_active('owner')
        await self.choose({'mood':'party'},expected_defaults=1,expected_session=self.expected(a),counter=2)
        a = self.manager.current_active('owner')
        await self.choose({'mood':'energy'},expected_defaults=2,expected_session=self.expected(a),counter=3)
        await self.choose({'mood':'energy'})
        a = self.manager.current_active('owner')
        self.assertNotIn(first['settings_confirmation']['moment_id'],[m.moment_id for m in a.broadcast.state.dj_moments])
        self.assertEqual(len(a.broadcast.state.dj_moments),2)

    async def test_recovery_expiry_does_not_renew(self):
        with patch.object(type(self.active),'compose_moment',side_effect=RuntimeError('postcommit failure')):
            first = await self.choose({'presence':'presenter'})
        a = self.manager.current_active('owner')
        mid = first['settings_confirmation']['moment_id']
        original = a.broadcast._moment_delivery_boundaries[mid]
        a.broadcast._moment_delivery_boundaries[mid] = replace(original,published_monotonic=original.published_monotonic-100)
        await self.choose({'presence':'presenter'})
        self.assertEqual(a.broadcast.state.dj_moments,())
        self.assertEqual(a.broadcast._moment_delivery_boundaries[mid].published_monotonic,original.published_monotonic-100)

    async def test_no_session_ack_in_requested_locale_never_starts_session(self):
        self.manager._active_by_profile.clear()
        result = await self.manager.async_accept_dj_settings(owner_profile_id='owner',operation_id=operation(self.now,1),
            binding='b'*64,patch={'mood':'energy'},expected_defaults_revision=0,expected_session=None,
            now_ms=self.now,authorize=lambda:True,validate_voice=lambda _:None,confirmation_locale='nl-NL')
        self.assertIsNone(result['settings_confirmation']['moment_id'])
        self.assertIn('Energy',result['settings_confirmation']['text'])
        self.assertEqual(result['settings_confirmation']['locale'],'nl')
        self.assertIsNone(self.manager.current_active('owner'))

    async def test_automatic_mood_withdraws_confirmation_without_new_moment(self):
        await self.choose({'mood':'energy'})
        a = self.manager.current_active('owner')
        await self.manager.async_update_mood(owner_profile_id='owner',session_id=a.session_id,selected_mood='party')
        self.assertIsNone(a.broadcast.native_delivery()['current_moment_id'])
        self.assertEqual(len(a.broadcast.state.dj_moments),1)

    async def test_tampered_text_or_unsealed_proof_never_admitted(self):
        await self.choose({'presence':'music_only'})
        a = self.manager.current_active('owner')
        m = a.broadcast.state.dj_moments[0]
        from custom_components.djconnect.settings_confirmation import context, render
        self.assertIsNone(context(replace(m,content='injected claim')))
        self.assertIsNone(context(replace(m,settings_confirmation=None)))
        self.assertFalse(a.allows_moment(replace(m,content='injected claim')))
        d=m.settings_confirmation.data()
        texts=set()
        for language in ('en','nl','de','fr','es'):
            for persona in ('home_dj','radio_dj','club_dj','festival_dj'):
                for mood in ('chill','groove','energy','party'):
                    title,text=render({**d,'locale':language,'settings':{**d['settings'],'persona':persona,'mood':mood},'changed_fields':['mood','persona','presence']})
                    self.assertTrue(title and len(text)<700)
                    self.assertNotIn('{',text)
                    texts.add(text)
        self.assertEqual(len(texts),80)

    async def test_legacy_explicit_three_axes_confirm_but_system_change_does_not(self):
        from custom_components.djconnect.persistence.sessions import PersistentSessionRepository
        from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
        manager = self.r.SessionRuntimeManager(PersistentSessionRepository(self.service),HistoricalProjectionRepository(self.service))
        a = await manager.async_start(owner_profile_id='legacy',selected_mood='chill',locale='nl')
        a = await manager.async_update_mood(owner_profile_id='legacy',session_id=a.session_id,selected_mood='energy',expected_revision=0,legacy_user_choice=True,authorize=lambda:True)
        a = await manager.async_update_persona(owner_profile_id='legacy',session_id=a.session_id,dj_persona=self.r.DJPersona.RADIO_DJ,expected_revision=0,legacy_user_choice=True,authorize=lambda:True)
        a = await manager.async_update_presence(owner_profile_id='legacy',session_id=a.session_id,selected_presence='music_only',expected_revision=0,legacy_user_choice=True,authorize=lambda:True)
        self.assertEqual(len(a.broadcast.state.dj_moments),3)
        self.assertEqual(a.presence_ledger.total_published,0)
        self.assertEqual(a.broadcast.native_delivery()['current_moment_id'],a.broadcast.state.dj_moments[-1].moment_id)
        await manager.async_update_presence(owner_profile_id='legacy',session_id=a.session_id,selected_presence='music_only',expected_revision=1,legacy_user_choice=True,authorize=lambda:True)
        self.assertEqual(len(a.broadcast.state.dj_moments),3)
        await manager.async_update_mood(owner_profile_id='legacy',session_id=a.session_id,selected_mood='party')
        self.assertEqual(len(a.broadcast.state.dj_moments),3)
        self.assertIsNone(a.broadcast.native_delivery()['current_moment_id'])

    async def test_owner_only_settings_not_in_shared_receiver_and_no_reread_lease(self):
        await self.choose({'persona':'radio_dj'})
        a=self.manager.current_active('owner')
        b=a.broadcast
        native=b.native_delivery()
        self.assertEqual(b.native_delivery(include_owner_only=False)['admissions'],[])
        self.assertEqual(native,b.native_delivery())
        moment=b.state.dj_moments[0]
        self.assertIsNone(moment.source_fact)
        self.assertEqual(moment.actions,())
        self.assertIsNone(moment.artwork_url)

    async def test_actual_ha_fixture_pins_source_and_declares_native_install_boundary(self):
        import json
        import hashlib
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        d=json.loads((root/'examples/client_contracts/settings_confirmation_v1/actual-ha-wire.json').read_text())
        self.assertEqual(d['ha_sdk_version'],'2026.10.0')
        self.assertEqual(len(d['cases']),12)
        self.assertEqual(set(d['cases'].values()),{'PASS'})
        self.assertEqual(d['model_provider_calls'],0)
        self.assertEqual(d['playback_or_device_effects'],0)
        for key in ('installed','native','audible'):
            self.assertEqual(d[key],'NOT_RUN')
        self.assertEqual(hashlib.sha256((root/'scripts/verification/verify_settings_confirmation_http.py').read_bytes()).hexdigest(),d['harness_sha256'])
        for relative,digest in d['source_pins'].items():
            self.assertEqual(hashlib.sha256((root/relative).read_bytes()).hexdigest(),digest,relative)
        for example in d['examples']:
            self.assertEqual(example['moment']['source_references'],['accepted_settings'])
            self.assertEqual(example['response']['settings_confirmation']['moment_id'],example['moment']['moment_id'])

    async def test_automatic_axis_aba_cannot_recover_old_pending_confirmation(self):
        with patch.object(type(self.active),'compose_moment',side_effect=RuntimeError('original publication failed')):
            result = await self.choose({'mood':'energy'})
        active = self.manager.current_active('owner')
        revision = active.settings_revision
        original = self.manager._pending_settings_confirmations['owner']
        await self.manager.async_update_persona(owner_profile_id='owner',session_id=active.session_id,dj_persona=self.r.DJPersona.RADIO_DJ)
        await self.manager.async_update_persona(owner_profile_id='owner',session_id=active.session_id,dj_persona=self.r.DJPersona.HOME_DJ)
        active = self.manager.current_active('owner')
        self.assertEqual(active.settings_revision,revision)
        self.assertEqual(active.dj_persona.value,result['settings_confirmation']['settings']['persona'])
        self.assertFalse(active.allows_moment(original))
        await self.manager.async_get_active('owner')
        self.assertFalse(active.broadcast.state.dj_moments)
        self.assertNotIn('owner',self.manager._pending_settings_confirmations)
        self.assertFalse(any(i.moment_id==original.moment_id for i in active.planner.output.session_flow.items))
