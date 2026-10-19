"""Actual paired operation/settings/speech owners; external TTS is a fixture."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_profile_settings_speech as shared
from tests.test_transport_operation_journal import Store, identifier


class PersonaReactionTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = shared.SharedSettingsSpeechTests.__dict__['setUpClass']
    tearDownClass = shared.SharedSettingsSpeechTests.__dict__['tearDownClass']
    choose = shared.SharedSettingsSpeechTests.choose
    provider = shared.SharedSettingsSpeechTests.provider

    async def asyncSetUp(self):
        await shared.SharedSettingsSpeechTests.asyncSetUp(self)
        from custom_components.djconnect import hybrid_service, persona_reactions
        self.hybrid, self.react = hybrid_service, persona_reactions
        self.store = Store()
        self.operations = hybrid_service.HybridOperations(self.hass, self.store)
        self.counter = 0
        self.settings_counter = 0
        self.sent = []
        async def no_speaker(*args, **kwargs):
            self.sent.append((args, kwargs))
        self.hass.services = SimpleNamespace(async_call=no_speaker)

    async def asyncTearDown(self):
        book = self.hass.data.get('djconnect', {}).get('persona_reaction_book')
        if book:
            for state in book.rows.values():
                if state.lease:
                    state.lease.dispose()
        await self.operations.close()
        await shared.SharedSettingsSpeechTests.asyncTearDown(self)

    async def start(self, *, output='client_device', persona='home_dj', mood='groove', language='en'):
        if output in ('ha_speaker', 'both'):
            self.runtime.config['dj_announcement_speaker_entity_id'] = 'media_player.owned_speaker'
            self.hass.states = SimpleNamespace(get=lambda entity: SimpleNamespace(
                state='idle', attributes={'supported_features': 512})
                if entity == 'media_player.owned_speaker' else None)
        self.settings_counter += 1
        await self.choose('cedar', counter=self.settings_counter, extra={'persona': persona, 'mood': mood,
            'presence': 'music_only', 'announcement_output': output})
        return await self.f.fixture.manager.async_start(owner_profile_id='profile-a', locale=language)

    def request(self, *, operation=None, **overrides):
        active = self.f.fixture.manager.current_active('profile-a')
        context = {'session_id': active.session_id, 'generation': active.settings_generation,
                   'revision': active.settings_revision} if active else {'session_id': 'absent', 'generation': 'absent', 'revision': 0}
        self.counter += 1
        return {'contract_version': 1, 'operation_id': identifier(self.now, 100+self.counter),
            'operation_epoch': self.operations.journal.epoch,
            'operation': operation or self.react.OPERATION,
            'payload': {'contract_version': 1, 'session': context, 'language': 'en',
                        'kind': 'check_in', 'processor': 'local_on_device', **overrides}}

    async def execute(self, request=None, *, raw=False, transport='http', authority=None):
        authority = authority or await self.hybrid.PairedAuthority.resolve(self.hass, self.f.identity, self.f.headers)
        result, status = await self.operations.execute(authority, request or self.request(), transport=transport)
        if not raw and hasattr(result, 'admitted_body'):
            result = await result.admitted_body()
        return result, status

    async def cancel(self, reaction_id, *, reason='dismissed', authority=None):
        active = self.f.fixture.manager.current_active('profile-a')
        request = self.request(operation=self.react.CANCEL)
        request['payload'] = {'contract_version': 1, 'session_id': active.session_id,
                              'reaction_id': reaction_id, 'reason': reason}
        return await self.execute(request, authority=authority)

    def clock(self):
        book = self.hass.data['djconnect']['persona_reaction_book']
        value = [book.now()]
        book.now = lambda: value[0]
        return value

    async def observe(self, result, *, authority=None, frames=None):
        authority = authority or await self.hybrid.PairedAuthority.resolve(self.hass, self.f.identity, self.f.headers)
        self.hass.data['djconnect']['hybrid_operation_manager'] = self.operations
        frames = frames if frames is not None else []
        return self.react.observe(self.hass, authority, {
            'contract_version': 1, 'operation_id': result['persona_reaction']['reaction_id'],
            'operation_epoch': self.operations.journal.epoch,
            'session_id': result['persona_reaction']['session']['session_id']}, 31, frames.append)

    async def test_cancel_before_original_execute_is_durable_and_has_zero_source_or_synthesis(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            for processor in ('local_on_device', 'ha_configured'):
                request = self.request(processor=processor)
                cancelled, status = await self.cancel(request['operation_id'])
                self.assertEqual(status, 200, cancelled)
                outcome, status = await self.execute(request)
                self.assertEqual((status, outcome['error']), (409, 'persona_reaction_withdrawn'))
                self.assertEqual(outcome['operation_receipt']['phase'], 'cancelled')
                self.assertNotIn('persona_reaction', outcome)
            self.assertNotIn('persona_reaction_book', self.hass.data['djconnect'])
            self.assertEqual((calls, self.sent), ([], []))
            self.assertTrue(any(r.get('cancelled_before_send') for r in self.store.data['records'].values()))

    async def test_pre_admission_cancellation_cannot_cancel_another_devices_unknown_intent(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            _, _, other = await self.second_device()
            request = self.request()
            await self.cancel(request['operation_id'])
            result, status = await self.execute(request, authority=other)
            self.assertEqual(status, 200, result)
            self.assertTrue(result['persona_reaction']['text'])
            self.assertEqual(calls, [])

    async def test_durable_cancel_survives_journal_restart_and_new_epoch_replay(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            request = self.request()
            await self.cancel(request['operation_id'])
            await self.operations.close()
            self.operations = self.hybrid.HybridOperations(self.hass, self.store)
            request['operation_epoch'] = self.operations.journal.epoch
            with self.assertRaises(self.hybrid.OperationError) as error:
                await self.execute(request)
            self.assertEqual(error.exception.code, 'operation_conflict')
            self.assertEqual(calls, [])
            self.assertNotIn('persona_reaction_book', self.hass.data['djconnect'])

    async def test_delivered_receipt_is_not_admission_and_foreground_withdrawal_is_observable(self):
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.start()
            request = self.request()
            delivered, _ = await self.execute(request)
            frames = []
            observation = await self.observe(delivered, frames=frames)
            try:
                initial = observation.snapshot()
                self.assertEqual(initial['state'], 'valid')
                self.assertEqual(initial['expires_at'], delivered['persona_reaction']['expires_at'])
                self.react.withdraw_for_interaction(self.hass, 'profile-a')
                self.assertEqual(len(frames), 1)
                self.assertEqual(frames[0]['event'], self.react.WITHDRAW_EVENT)
                self.assertEqual(frames[0]['_persona_observation'].snapshot()['state'], 'withdrawn')
                self.assertNotIn('text', observation.snapshot())
                receipt, status = await self.operations.status(
                    await self.hybrid.PairedAuthority.resolve(self.hass, self.f.identity, self.f.headers),
                    {k: request[k] for k in ('contract_version', 'operation_id', 'operation_epoch')})
                self.assertEqual(status, 200)
                self.assertEqual(receipt['operation_receipt']['phase'], 'confirmed')
                self.assertFalse(receipt['result_available'])
            finally:
                observation.close()
                await asyncio.gather(observation.task, return_exceptions=True)

    async def test_provider_withdrawal_after_delivery_is_detected_without_another_byte_read(self):
        stack, entity, _, calls, _ = self.provider()
        with stack:
            await self.start()
            delivered, _ = await self.execute(self.request(processor='ha_configured'))
            frames = []
            observation = await self.observe(delivered, frames=frames)
            try:
                entity.subentry.data['tts_speed'] = 1.1
                await asyncio.wait_for(observation.task, 2)
                self.assertTrue(frames)
                self.assertEqual(observation.snapshot()['state'], 'withdrawn')
                self.assertEqual(len(calls), 1)
            finally:
                observation.close()
                await asyncio.gather(observation.task, return_exceptions=True)

    async def test_observer_is_private_bounded_and_disconnect_withdraws_downloaded_audio(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            _, _, other = await self.second_device()
            delivered, _ = await self.execute(self.request(processor='ha_configured'))
            with self.assertRaises(self.hybrid.OperationError) as error:
                await self.observe(delivered, authority=other)
            self.assertEqual(error.exception.status, 404)
            observation = await self.observe(delivered)
            with self.assertRaises(self.hybrid.OperationError) as error:
                await self.observe(delivered)
            self.assertEqual(error.exception.code, 'persona_reaction_observer_busy')
            observation.close()
            await asyncio.gather(observation.task, return_exceptions=True)
            item, status = await self.speech.async_handle_audio(self.hass, self.asset_request(delivered), headers=self.f.headers)
            self.assertEqual((status, item), (404, None))
            self.assertEqual(len(calls), 1)
            self.assertIsNone(observation.lease.source.timer)
            self.assertEqual(observation.snapshot()['state'], 'withdrawn')

    async def test_observer_original_deadline_has_real_expiry_no_read_renewal(self):
        stack, _, _, calls, _ = self.provider()
        with stack, patch.object(self.react, 'MAX_SECONDS', .15):
            await self.start()
            delivered, _ = await self.execute()
            frames = []
            observation = await self.observe(delivered, frames=frames)
            try:
                deadline = observation.snapshot()['expires_at']
                await asyncio.wait_for(observation.lease.cancelled.wait(), 1)
                self.assertEqual(len(frames), 1)
                self.assertEqual(observation.snapshot()['state'], 'withdrawn')
                self.assertEqual(observation.snapshot()['expires_at'], deadline)
                self.assertEqual(calls, [])
            finally:
                observation.close()
                await asyncio.gather(observation.task, return_exceptions=True)

    def asset_request(self, result):
        return {**self.f.identity, 'contract_version': 1,
                'asset_id': result['persona_reaction']['speech']['audio_reference']['asset_id']}

    async def test_explicit_music_only_reaction_has_no_flow_history_model_source_or_music_effect(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            session = await self.start()
            before = deepcopy(session.as_dict())
            history = await self.f.history.async_history('profile:profile-a')
            result, status = await self.execute()
            self.assertEqual(status, 200, result)
            self.assertTrue(result['result_available'])
            value = result['persona_reaction']
            self.assertEqual(value['content_basis'], 'core_owned_curated_reaction_v1')
            self.assertFalse(value['history_publication'])
            self.assertEqual(value['speech']['audio_state'], 'renderer_pending')
            self.assertEqual(value['speech']['processor'], 'local_on_device')
            self.assertEqual(self.f.fixture.manager.current_active('profile-a').as_dict(), before)
            after = await self.f.history.async_history('profile:profile-a')
            for document in (history, after):
                document.pop('server_time', None)
            self.assertEqual(after, history)
            self.assertEqual(session.presence_ledger.total_published, 0)
            self.assertEqual((calls, self.sent, self.f.prompts, self.f.web_calls, self.f.effects), ([], [], [], [], []))
            self.assertNotIn(value['text'], json.dumps(self.store.data))
            self.assertNotIn('persona_reaction', session.broadcast.as_dict())

    async def test_text_only_zero_synthesis_for_both_processors_and_no_audio_grant(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start(output='text_only')
            for processor in ('local_on_device', 'ha_configured'):
                result, status = await self.execute(self.request(processor=processor))
                self.assertEqual(status, 200, result)
                value = result['persona_reaction']
                self.assertTrue(value['text'])
                self.assertEqual(value['speech']['reason'], 'announcement_text_only')
                self.assertFalse(value['speech']['segments'])
                self.assertNotIn('audio_reference', value['speech'])
                await self.cancel(value['reaction_id'])
                self.clock()[0] += 11
            self.assertEqual((calls, self.sent, self.f.prompts), ([], [], []))
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))

    async def test_configured_ha_speaks_exact_curated_text_current_voice_and_mood(self):
        stack, _, pipeline, calls, _ = self.provider()
        with stack:
            await self.start(persona='festival_dj', mood='party')
            original = deepcopy(pipeline.__dict__)
            result, status = await self.execute(self.request(processor='ha_configured'))
            self.assertEqual(status, 200, result)
            value, speech = result['persona_reaction'], result['persona_reaction']['speech']
            self.assertEqual(speech['audio_state'], 'ready')
            self.assertEqual(speech['effective_voice']['voice_id'], 'cedar')
            self.assertEqual(calls[0][0], value['text'])
            self.assertEqual(calls[0][2]['voice'], 'cedar')
            self.assertEqual((value['persona'], value['mood']), ('festival_dj', 'party'))
            self.assertEqual(''.join(s['text'] for s in speech['segments']), value['text'])
            self.assertEqual(pipeline.__dict__, original)
            item, status = await self.speech.async_handle_audio(self.hass, self.asset_request(result), headers=self.f.headers)
            self.assertEqual(status, 200)
            self.assertEqual(item.delivery_device_id, self.f.identity['device_id'])
            self.assertEqual(result['delivery']['audible'], 'not_proven')

    async def test_local_processor_does_not_require_the_configured_ha_provider(self):
        stack, entity, _, calls, _ = self.provider()
        with stack:
            await self.start()
            entity.available = False
            result, status = await self.execute()
            self.assertEqual(status, 200, result)
            self.assertEqual(result['persona_reaction']['speech']['audio_state'], 'renderer_pending')
            self.assertEqual(calls, [])

    async def test_unqualified_speaker_target_never_dispatches_or_substitutes_client_audio(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start(output='ha_speaker')
            result, status = await self.execute(self.request(processor='ha_configured'))
            self.assertEqual(status, 200, result)
            self.assertTrue(result['persona_reaction']['text'])
            self.assertEqual(result['persona_reaction']['speech']['reason'], 'persona_reaction_speaker_not_qualified')
            self.assertEqual(result['delivery']['ha_speaker'], 'not_qualified')
            self.assertEqual(result['delivery']['local'], 'not_requested')
            self.assertEqual((calls, self.sent), ([], []))

    async def test_both_reports_explicit_partial_qualification_without_a_speaker_call(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start(output='both')
            result, status = await self.execute()
            self.assertEqual(status, 200, result)
            self.assertEqual(result['delivery'], {'local': 'renderer_pending', 'ha_speaker': 'not_qualified', 'audible': 'not_proven'})
            self.assertEqual((calls, self.sent), ([], []))

    async def test_duplicate_returns_only_original_receipt_and_new_request_is_busy(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            request = self.request()
            result, status = await self.execute(request)
            again, status = await self.execute(request)
            self.assertEqual(status, 200, again)
            self.assertFalse(again['result_available'])
            self.assertNotIn('persona_reaction', again)
            busy, status = await self.execute()
            self.assertEqual((status, busy['error']), (409, 'persona_reaction_busy'))
            self.assertEqual(calls, [])
            self.assertTrue(result['persona_reaction']['text'])

    async def test_cancel_does_not_reset_cooldown_rolling_rate_or_content_sequence(self):
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.start()
            first, _ = await self.execute()
            await self.cancel(first['persona_reaction']['reaction_id'])
            clock = self.clock()
            cooldown, status = await self.execute()
            self.assertEqual((status, cooldown['error']), (429, 'persona_reaction_cooldown'))
            texts = [first['persona_reaction']['text']]
            for _ in range(5):
                clock[0] += 11
                result, status = await self.execute()
                self.assertEqual(status, 200, result)
                texts.append(result['persona_reaction']['text'])
                await self.cancel(result['persona_reaction']['reaction_id'])
            self.assertTrue(all(a != b for a, b in zip(texts, texts[1:])))
            clock[0] += 11
            denied, status = await self.execute()
            self.assertEqual((status, denied['error']), (429, 'persona_reaction_rate_limit'))
            clock[0] += 600
            allowed, status = await self.execute()
            self.assertEqual(status, 200, allowed)

    async def test_pending_duplicate_cancel_and_late_provider_completion_never_publish_old_audio(self):
        stack, entity, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        original = entity.async_get_tts_audio
        async def delayed(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        entity.async_get_tts_audio = delayed
        with stack:
            await self.start()
            request = self.request(processor='ha_configured')
            pending = asyncio.create_task(self.execute(request, transport='websocket'))
            await asyncio.wait_for(entered.wait(), 2)
            duplicate, status = await self.execute(request)
            self.assertEqual(status, 202, duplicate)
            busy, status = await self.execute()
            self.assertEqual((status, busy['error']), (409, 'persona_reaction_busy'))
            cancelled, status = await self.cancel(request['operation_id'], reason='background')
            self.assertEqual(status, 200, cancelled)
            result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual((status, result['error']), (409, 'persona_reaction_withdrawn'))
            release.set()
            await asyncio.sleep(0)
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))
            self.assertLessEqual(len(calls), 1)
            self.assertEqual(self.sent, [])

    async def hold_settings(self):
        entered, release = asyncio.Event(), asyncio.Event()
        manager = self.f.fixture.manager
        original = manager.async_read_dj_settings
        async def held(**kwargs):
            entered.set()
            await release.wait()
            return await original(**kwargs)
        manager.async_read_dj_settings = held
        return entered, release

    async def test_foreground_during_settings_read_withdraws_before_any_lease_or_synthesis(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            entered, release = await self.hold_settings()
            pending = asyncio.create_task(self.execute(self.request(processor='ha_configured')))
            await asyncio.wait_for(entered.wait(), 2)
            self.react.withdraw_for_interaction(self.hass, 'profile-a')
            result, status = await asyncio.wait_for(pending, 2)
            release.set()
            self.assertEqual((status, result['error']), (409, 'persona_reaction_withdrawn'))
            self.assertNotIn('persona_reaction', result)
            self.assertEqual(calls, [])
            self.assertTrue(all(not s.accepted and s.lease is None and s.pending is None
                                for s in self.hass.data['djconnect']['persona_reaction_book'].rows.values()))

    async def test_explicit_cancel_and_second_device_busy_cover_pending_settings_read(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            _, _, other = await self.second_device()
            entered, release = await self.hold_settings()
            request = self.request(processor='ha_configured')
            pending = asyncio.create_task(self.execute(request))
            await asyncio.wait_for(entered.wait(), 2)
            denied, status = await self.cancel(request['operation_id'], authority=other)
            self.assertEqual((status, denied['error']), (404, 'persona_reaction_unavailable'))
            busy, status = await self.execute(authority=other)
            self.assertEqual((status, busy['error']), (409, 'persona_reaction_busy'))
            cancelled, status = await self.cancel(request['operation_id'])
            self.assertEqual(status, 200, cancelled)
            result, status = await asyncio.wait_for(pending, 2)
            release.set()
            self.assertEqual((status, result['error']), (409, 'persona_reaction_withdrawn'))
            self.assertEqual(calls, [])

    async def test_settings_wait_consumes_original_deadline_without_renewal(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            entered, release = await self.hold_settings()
            pending = asyncio.create_task(self.execute(self.request(processor='ha_configured')))
            await asyncio.wait_for(entered.wait(), 2)
            self.clock()[0] += 31
            release.set()
            result, status = await asyncio.wait_for(pending, 2)
            self.assertEqual((status, result['error']), (409, 'persona_reaction_withdrawn'))
            self.assertEqual(calls, [])

    async def test_provider_change_during_durable_send_admission_prevents_synthesis(self):
        stack, entity, _, calls, _ = self.provider()
        save = self.store.async_save
        changed = []
        async def switch_after_save(value):
            await save(value)
            if not changed and any(r['phase'] == 'sent_unknown' for r in value['records'].values()):
                changed.append(True)
                entity.subentry.data['tts_speed'] = 1.1
        self.store.async_save = switch_after_save
        with stack:
            await self.start()
            result, status = await self.execute(self.request(processor='ha_configured', language='nl'))
            self.assertEqual((status, result.get('error')), (409, 'speech_configuration_changed'), result)
            self.assertEqual(result['notification']['code'], 'tts_configuration_changed')
            self.assertEqual(result['notification']['locale'], 'nl')
            self.assertEqual(changed, [True])
            self.assertEqual((calls, self.sent), ([], []))
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))

    async def test_socket_loss_keeps_one_operation_then_explicit_cancel_withdraws_it(self):
        stack, entity, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        original = entity.async_get_tts_audio
        async def delayed(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        entity.async_get_tts_audio = delayed
        with stack:
            await self.start()
            request = self.request(processor='ha_configured')
            pending = asyncio.create_task(self.execute(request, transport='websocket'))
            await asyncio.wait_for(entered.wait(), 2)
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            repeated, status = await self.execute(request)
            self.assertEqual(status, 202, repeated)
            await self.cancel(request['operation_id'])
            await asyncio.gather(*tuple(self.operations.tasks.values()))
            release.set()
            await asyncio.sleep(0)
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))
            self.assertLessEqual(len(calls), 1)

    async def test_settings_change_invalidates_held_content_and_old_audio_bytes(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            result, status = await self.execute(self.request(processor='ha_configured'), raw=True)
            self.assertEqual(status, 200)
            read = self.asset_request(result)
            await self.choose('marin', counter=2, extra={'mood': 'party'})
            self.assertFalse((await result.admitted_body())['result_available'])
            item, status = await self.speech.async_handle_audio(self.hass, read, headers=self.f.headers)
            self.assertEqual((status, item), (404, None))
            self.assertEqual(len(calls), 1)

    async def test_end_and_successor_session_cancel_preparation_and_cannot_reuse_old_context(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            session = await self.start()
            request = self.request()
            result, _ = await self.execute(request, raw=True)
            manager = self.f.fixture.manager
            book = self.hass.data['djconnect']['persona_reaction_book']
            lease = next(iter(book.rows.values())).lease
            await manager.async_end(owner_profile_id='profile-a', session_id=session.session_id)
            self.assertTrue(lease.cancelled.is_set())
            self.assertFalse((await result.admitted_body())['result_available'])
            await manager.async_start(owner_profile_id='profile-a', locale='en')
            stale = self.request(session=request['payload']['session'])
            denied, status = await self.execute(stale)
            self.assertEqual((status, denied['error']), (409, 'persona_reaction_context_changed'))
            self.assertEqual(calls, [])

    async def test_ask_dj_foreground_withdraws_reaction_without_fabricating_an_ask_dj_turn(self):
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.start()
            result, _ = await self.execute(raw=True)
            self.assertEqual(self.f.prompts, [])
            answer, status = await self.f.request('What is an ostinato?', identifier='real-user-foreground', speech_contract_version=3)
            self.assertEqual(status, 200, answer)
            self.assertFalse((await result.admitted_body())['result_available'])
            self.assertEqual(len(self.f.prompts), 1)

    async def test_unknown_provider_is_a_text_result_with_functional_feedback_not_false_audio(self):
        stack, entity, _, calls, _ = self.provider()
        with stack:
            await self.start()
            entity.available = False
            result, status = await self.execute(self.request(processor='ha_configured'))
            self.assertEqual(status, 200, result)
            self.assertTrue(result['persona_reaction']['text'])
            self.assertEqual(result['persona_reaction']['speech']['reason'], 'tts_provider_unavailable')
            self.assertIn('notification', result['persona_reaction']['speech'])
            self.assertNotIn('audio_reference', result['persona_reaction']['speech'])
            self.assertEqual(calls, [])

    async def test_closed_schema_rejects_overrides_bad_context_and_unsupported_locale(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            for extra in ({'text': 'caller text'}, {'voice_id': 'marin'}, {'target': 'ha_speaker'},
                          {'language': 'it'}, {'kind': []}, {'processor': 'caller_processor'},
                          {'contract_version': True}, {'session': {'session_id': 'old'}}):
                result, status = await self.execute(self.request(**extra))
                self.assertEqual((status, result['error']), (400, 'invalid_request'), extra)
            request = self.request()
            request['payload']['session']['revision'] += 1
            result, status = await self.execute(request)
            self.assertEqual((status, result['error']), (409, 'persona_reaction_context_changed'))
            self.assertEqual((calls, self.sent), ([], []))

    async def test_missing_session_or_unconfirmed_settings_never_start_a_session(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            denied, status = await self.execute()
            self.assertEqual((status, denied['error']), (409, 'persona_reaction_session_unavailable'))
            self.assertIsNone(self.f.fixture.manager.current_active('profile-a'))
            session = await self.f.fixture.manager.async_start(owner_profile_id='profile-a', selected_mood='groove')
            denied, status = await self.execute()
            self.assertEqual((status, denied['error']), (409, 'settings_migration_choice_required'))
            self.assertEqual(self.f.fixture.manager.current_active('profile-a').session_id, session.session_id)
            self.assertEqual(calls, [])

    async def test_original_deadline_does_not_extend_on_retry_or_wall_clock_rollback(self):
        stack, _, _, _, _ = self.provider()
        with stack:
            await self.start()
            result, _ = await self.execute(raw=True)
            clock = self.clock()
            clock[0] += 31
            with patch.object(self.react.time, 'time', return_value=self.react.time.time()-3600):
                self.assertFalse((await result.admitted_body())['result_available'])
                self.assertNotIn('persona_reaction', await result.admitted_body())

    async def second_device(self):
        from custom_components.djconnect.profile_context import profile_storage
        identity = {'device_id': 'djconnect-ios-ABCDEF654321', 'client_type': 'ios'}
        headers = {'Authorization': 'Bearer synthetic-second-token'}
        storage = profile_storage(self.hass)
        await storage.async_upsert_device(identity['device_id'], 'ios', linked_profile_id='profile-a')
        runtime = SimpleNamespace(**self.runtime.__dict__)
        runtime.config = {**runtime.config, **identity}
        runtime.device_status = dict(identity)
        runtime.device_token = 'synthetic-second-token'
        runtime.authorize_device_request = lambda h, device_id=None, client_type=None: (
            h == headers and device_id == identity['device_id'] and client_type == 'ios')
        runtime.entry = SimpleNamespace(entry_id='second-entry', data={**runtime.config,
            'device_token': runtime.device_token}, options={}, disabled_by=None,
            state=SimpleNamespace(value='loaded'))
        self.hass.data['djconnect']['second-entry'] = runtime
        entries = {self.entry.entry_id: self.entry, runtime.entry.entry_id: runtime.entry}
        self.hass.config_entries.async_get_entry = entries.get
        authority = await self.hybrid.PairedAuthority.resolve(self.hass, identity, headers)
        return identity, headers, authority

    async def test_other_paired_device_cannot_read_or_cancel_but_shares_the_busy_budget(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            identity, headers, authority = await self.second_device()
            result, status = await self.execute(self.request(processor='ha_configured'))
            self.assertEqual(status, 200, result)
            read = {**self.asset_request(result), **identity}
            denied, status = await self.speech.async_handle_audio(self.hass, read, headers=headers)
            self.assertEqual((status, denied), (404, None))
            cancelled, status = await self.cancel(result['persona_reaction']['reaction_id'], authority=authority)
            self.assertEqual((status, cancelled['error']), (404, 'persona_reaction_unavailable'))
            busy, status = await self.execute(authority=authority)
            self.assertEqual((status, busy['error']), (409, 'persona_reaction_busy'))
            original, status = await self.speech.async_handle_audio(self.hass, self.asset_request(result), headers=self.f.headers)
            self.assertEqual(status, 200)
            self.assertIsNotNone(original)
            self.assertEqual(len(calls), 1)

    async def test_cancellation_during_settings_and_provider_work_cannot_leak_a_ready_result(self):
        stack, entity, _, calls, _ = self.provider()
        entered, release = asyncio.Event(), asyncio.Event()
        original = entity.async_get_tts_audio
        async def delayed(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        entity.async_get_tts_audio = delayed
        with stack:
            await self.start()
            request = self.request(processor='ha_configured')
            pending = asyncio.create_task(self.execute(request))
            await asyncio.wait_for(entered.wait(), 2)
            await self.choose('marin', counter=2, extra={'announcement_output': 'text_only'})
            release.set()
            result, status = await pending
            self.assertEqual((status, result['error']), (409, 'persona_reaction_withdrawn'))
            self.assertFalse(self.hass.data['djconnect'].get('tts_audio'))
            self.assertLessEqual(len(calls), 1)

    async def test_real_voice_preview_supersedes_touch_without_reusing_its_text(self):
        stack, _, _, calls, _ = self.provider()
        with stack:
            await self.start()
            result, _ = await self.execute(raw=True)
            preview = self.request(operation='speech/preview')
            preview['payload'] = {'contract_version': 1, 'language': 'en'}
            actual, status = await self.execute(preview)
            self.assertEqual(status, 200, actual)
            self.assertFalse((await result.admitted_body())['result_available'])
            self.assertNotEqual(calls[0][0], result['persona_reaction']['text'])

    async def style_routes(self, language):
        from custom_components.djconnect.persona_reaction_text import PERSONAS, MOODS
        fixture = json.loads((Path(__file__).resolve().parents[1]/'examples/client_contracts/persona_touch_reaction_v1/curated-texts.json').read_text())
        catalog = {(r['language'], r['persona'], r['mood'], r['kind']): r['texts'] for r in fixture['cases']}
        stack, _, pipeline, calls, _ = self.provider()
        with stack:
            for persona in PERSONAS:
                for mood in MOODS:
                    session = await self.start(persona=persona, mood=mood, language=language)
                    result, status = await self.execute(self.request(language=language))
                    self.assertEqual(status, 200, result)
                    value = result['persona_reaction']
                    self.assertIn(value['text'], catalog[language, persona, mood, 'check_in'])
                    self.assertEqual((value['persona'], value['mood'], value['locale']), (persona, mood, language))
                    self.assertEqual(session.presence_ledger.total_published, 0)
                    await self.f.fixture.manager.async_end(owner_profile_id='profile-a', session_id=session.session_id)
            self.assertEqual((calls, self.sent, self.f.prompts, self.f.web_calls), ([], [], [], []))

    async def test_actual_confirmed_style_routes_en(self):
        await self.style_routes('en')

    async def test_actual_confirmed_style_routes_nl(self):
        await self.style_routes('nl')

    async def test_actual_confirmed_style_routes_de(self):
        await self.style_routes('de')

    async def test_actual_confirmed_style_routes_fr(self):
        await self.style_routes('fr')

    async def test_actual_confirmed_style_routes_es(self):
        await self.style_routes('es')

    def test_all_persona_mood_language_kind_cells_are_actual_bounded_varied_texts(self):
        from custom_components.djconnect.persona_reaction_text import PERSONAS, MOODS, LANGUAGES, KINDS, render
        rows = []
        for language in LANGUAGES:
            for persona in PERSONAS:
                for mood in MOODS:
                    for kind in KINDS:
                        values = [render(persona=persona, mood=mood, language=language, kind=kind, sequence=i) for i in range(2)]
                        self.assertNotEqual(*values)
                        self.assertTrue(all(0 < len(text) <= 220 and '{' not in text for text in values))
                        rows.append({'language': language, 'persona': persona, 'mood': mood, 'kind': kind, 'texts': values})
        self.assertEqual(len(rows), 240)
        self.assertEqual(len({text for row in rows for text in row['texts']}), 480)
        # These are the producer's actual literal outputs, available for review;
        # fixture audio does not turn them into native or listening acceptance.
        fixture = Path(__file__).resolve().parents[1]/'examples/client_contracts/persona_touch_reaction_v1/curated-texts.json'
        self.assertEqual(json.loads(fixture.read_text())['cases'], rows)

    def test_capability_is_explicit_local_only_and_keeps_silence_excluded_from_speech(self):
        from custom_components.djconnect.session_persona import capability
        descriptor = capability()['touch_reaction']
        self.assertIn(descriptor['operation'], self.hybrid.ACTION_OPERATIONS)
        self.assertIn(descriptor['cancel_operation'], self.hybrid.ACTION_OPERATIONS)
        self.assertFalse(descriptor['ha_speaker_target'])
        self.assertFalse(descriptor['history_publication'])
        self.assertFalse(descriptor['model_calls'])
        self.assertIn('silence', self.speech.capability()['excluded_moment_types'])
