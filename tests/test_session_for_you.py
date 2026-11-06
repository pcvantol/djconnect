"""Owner-selected For-you behavior reuses the original dialogue/effect owner."""
from copy import deepcopy
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from tests import test_session_first_play as fixtures


class ForYouTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixtures.FirstPlayTests.asyncSetUp(self)
        # Other module fixtures reload Session authority. Bind the preparation
        # service to this test's current real dialogue/authority modules too.
        import importlib
        importlib.reload(importlib.import_module('custom_components.djconnect.ask_dj.service'))
    new_session = fixtures.FirstPlayTests.new_session
    new_turn = fixtures.FirstPlayTests.new_turn
    offer = fixtures.FirstPlayTests.offer
    choose = fixtures.FirstPlayTests.choose

    async def test_offer_independent_of_playback_queue_and_speaker(self):
        for state in ('playing', 'paused', 'stopped', 'idle'):
            with self.subTest(state=state):
                await self.new_session()
                self.new_turn('prepare-' + state)
                self.observed = SimpleNamespace(state=state)
                self.devices = []
                await self.manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
                    session_id=self.active.session_id, state=state, media_identity='spotify:track:'+'A'*22)
                reply = await self.offer()
                self.assertEqual(reply['first_play']['state'], 'genres')
                self.assertEqual(len(reply['result_set']['items']), 3)
                self.assertEqual(self.effects, [])
                self.assertEqual(self.reservations, [])
                self.assertEqual(self.active.broadcast.first_play_state, 'ready')

    async def test_genre_then_output_finishes_same_mix(self):
        self.devices[0]['is_active'] = False
        genres = await self.offer()
        exact = genres['result_set']['items'][1]['uris']
        admission = self.turn.first_play_admission
        deadline = admission.deadline
        output = await self.choose(1)
        self.assertEqual(output['first_play']['state'], 'output')
        self.assertEqual(self.effects, [])
        result = await self.choose(0, 'speaker-completes-original-request')
        self.assertTrue(result['action_outcome']['readback_confirmed'])
        self.assertEqual(self.effects, [('set_output', 'synthetic-output', False), ('play_uris', exact, True)])
        self.assertEqual(admission.deadline, deadline)
        self.assertEqual(self.active.broadcast.first_play_state, 'confirmed')

    async def test_confirmation_closes_whole_card_for_original_session(self):
        await self.offer()
        result = await self.choose()
        self.assertTrue(result['action_outcome']['readback_confirmed'])
        for state in ('paused', 'stopped', 'idle', 'playing'):
            await self.manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
                session_id=self.active.session_id, state=state, media_identity='spotify:track:'+'B'*22)
            projected = self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active)
            self.assertFalse(projected['visible'])
            self.assertEqual(projected['options'], [])
        await self.new_session()
        self.assertTrue(self.steering._first_play_empty(self.active))

    async def test_uncertain_ack_keeps_card_and_never_reissues_play(self):
        await self.offer()
        original = self.use_cases.run_music_command
        async def uncertain(*args, **kwargs):
            result = await original(*args, **kwargs)
            result['playback'] = {}
            return result
        with patch.object(self.use_cases, 'run_music_command', uncertain):
            result = await self.choose()
        self.assertFalse(result['action_outcome']['readback_confirmed'])
        self.assertEqual(result['first_play']['state'], 'uncertain')
        self.assertTrue(self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active)['visible'])
        with self.assertRaises(self.dialogue.DialogueError):
            await self.choose(0, 'no-second-start')
        self.assertEqual(len(self.effects), 1)

    async def test_start_prepares_once_without_chat_and_polls_do_not_regenerate(self):
        from tests.test_music_dna import FakeStore
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
        from custom_components.djconnect.domain.storage import STORE_KEY
        history = AskDJHistoryManager(store=FakeStore())
        storage = self.hass.data['djconnect'][STORE_KEY]
        context = SimpleNamespace(profile_id='synthetic-owner', profile=storage.household.profiles['synthetic-owner'])
        def current():
            if not self.allowed:
                raise PermissionError('owner-withdrawn')
        source = patch('custom_components.djconnect.reply_artwork.source_admission', return_value=(self.source, lambda: self.allowed))
        source.start()
        self.addCleanup(source.stop)
        await self.steering.prepare_for_you_once(self.hass, self.runtime, context, self.active, history, current)
        offer = self.steering.for_you_projection(self.hass, self.runtime, context.profile_id, self.active)
        self.assertEqual(offer['state'], 'available', offer)
        self.assertEqual(len(offer['options']), 3)
        def stable(value):
            value = deepcopy(value)
            value.pop('expires_in', None)
            if value.get('result_set'):
                value['result_set'].pop('expires_in', None)
            return value
        original = stable(offer)
        for _ in range(4):
            await self.steering.prepare_for_you_once(self.hass, self.runtime, context, self.active, history, current)
            self.assertEqual(stable(self.steering.for_you_projection(self.hass, self.runtime, context.profile_id, self.active)), original)
        self.assertEqual(len([p for p in self.reads if p.startswith('/search')]), 3)
        frame = history.dialogue.owners['profile:synthetic-owner'][offer['conversation_context']['thread_id']]
        self.assertEqual(frame.messages, [])
        self.assertEqual(frame.local_turns, [])
        self.assertFalse(history.data.get('users'))
        self.assertEqual(self.effects, [])
        self.assertEqual(len({o['visual_recipe']['artistic_direction'] for o in offer['options']}), 3)
        self.assertEqual(len({o['visual_recipe']['variation_id'] for o in offer['options']}), 3)
        for option in offer['options']:
            self.assertTrue(option['visual_recipe']['illustrative_not_audio_analysis'])
            for forbidden in ('action_id', 'uris', 'images', 'artwork_url'):
                self.assertNotIn(forbidden, option['visual_recipe'])

    async def test_confirmation_memory_is_deduped_and_clear_removes_it(self):
        memory = self.runtime.memory
        self.assertTrue(await memory.async_record_for_you_choice('synthetic-owner', 'original-action', 'neo soul', authorize=lambda: True))
        self.assertFalse(await memory.async_record_for_you_choice('synthetic-owner', 'original-action', 'neo soul', authorize=lambda: True))
        self.assertEqual(memory.loaded_for_you_choices('synthetic-owner'), (('original-action', 'neo soul'),))
        await memory.async_clear('profile:synthetic-owner')
        self.assertEqual(memory.loaded_for_you_choices('synthetic-owner'), ())

    async def prepared(self):
        from tests.test_music_dna import FakeStore
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
        from custom_components.djconnect.domain.storage import STORE_KEY
        history = AskDJHistoryManager(store=FakeStore())
        storage = self.hass.data['djconnect'][STORE_KEY]
        context = SimpleNamespace(profile_id='synthetic-owner', profile=storage.household.profiles['synthetic-owner'])
        source = patch('custom_components.djconnect.reply_artwork.source_admission', return_value=(self.source, lambda: self.allowed))
        source.start()
        self.addCleanup(source.stop)
        await self.steering.prepare_for_you_once(self.hass, self.runtime, context, self.active, history, lambda: None)
        return history, self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active)

    async def test_dismissal_is_client_scoped_revokes_old_click_and_is_not_a_taste_vote(self):
        history, offer = await self.prepared()
        before = deepcopy(self.runtime.memory.data)
        choice = {'operation': 'dismiss', 'result_set_id': offer['offer_id'], 'action_id': ''}
        closed = self.steering.dismiss_for_you(self.hass, 'synthetic-owner', 'phone', offer['conversation_context'], choice, history)
        self.assertFalse(closed['for_you']['visible'])
        self.assertFalse(self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active, client_device_id='phone')['visible'])
        self.assertTrue(self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active, client_device_id='ipad')['visible'])
        self.frame = history.dialogue.owners['profile:synthetic-owner'][offer['conversation_context']['thread_id']]
        admission = self.frame.result_set['first_play_admission']
        self.new_turn('stale-phone-click')
        self.turn.client_device_id = 'phone'
        with self.assertRaises(self.dialogue.DialogueError):
            admission.bind(self.turn)
        self.assertFalse(admission.withdrawn)
        self.new_turn('independent-ipad')
        self.turn.client_device_id = 'ipad'
        admission.bind(self.turn)
        self.assertEqual(self.runtime.memory.data, before)
        self.assertEqual(self.effects, [])

    async def test_old_session_dismissal_never_changes_replacement_session(self):
        history, offer = await self.prepared()
        await self.new_session()
        with self.assertRaises(self.dialogue.DialogueError):
            self.steering.dismiss_for_you(self.hass, 'synthetic-owner', 'phone', offer['conversation_context'],
                {'operation': 'dismiss', 'result_set_id': offer['offer_id'], 'action_id': ''}, history)
        self.assertEqual(self.active.broadcast.first_play_dismissed_devices, set())

    async def test_expired_actions_do_not_remove_card_or_renew_on_poll(self):
        _, offer = await self.prepared()
        cached = self.active.broadcast.first_play_offer
        cached['_action_wall_deadline'] = 0
        cached['_action_monotonic_deadline'] = 0
        reads = list(self.reads)
        projected = self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active)
        self.assertTrue(projected['visible'])
        self.assertFalse(projected['actions_available'])
        self.assertEqual(projected['options'], offer['options'])
        self.assertFalse(projected['refresh_request']['automatic'])
        self.assertEqual(self.reads, reads)

    async def test_late_exact_playback_can_reconcile_unknown_result(self):
        await self.offer()
        original = self.use_cases.run_music_command
        async def uncertain(*args, **kwargs):
            result = await original(*args, **kwargs)
            result['playback'] = {}
            return result
        with patch.object(self.use_cases, 'run_music_command', uncertain):
            result = await self.choose()
        self.assertFalse(result['action_outcome']['readback_confirmed'])
        pending = self.active.broadcast.first_play_pending
        await self.manager.async_update_playback_projection(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, state='playing', media_identity=pending.selected_media[0],
            original_status=SimpleNamespace(target_id=pending.output_id))
        self.assertEqual(self.active.broadcast.first_play_state, 'confirmed')
        self.assertEqual(len(self.effects), 1)

    async def test_generated_intro_requires_independent_review_and_excludes_grants(self):
        import json
        core = __import__('custom_components.djconnect.ask_dj', fromlist=['x'])
        await self.offer()
        admission = self.turn.first_play_admission
        calls = []
        async def narrator(hass, data):
            calls.append(data['text'])
            body = {'intro': 'I picked three mixes for your taste. Which shall we play?'} if len(calls) == 1 else {'approved': True}
            return {'response': {'speech': {'plain': {'speech': json.dumps(body)}}}}
        with patch.object(core, '_assist_context', return_value={'agent_id': 'synthetic-agent'}), patch.object(core, '_call_dialogue_agent', narrator):
            intro, generated = await self.original_for_you_intro(self.hass, self.runtime, admission, self.owned_genres)
        self.assertTrue(generated)
        self.assertEqual(len(calls), 2)
        self.assertTrue(intro.endswith('?'))
        for prompt in calls:
            for private in ('spotify:track:', 'action_id', 'result_set_id', 'original-generation'):
                self.assertNotIn(private, prompt)
        calls.clear()
        async def rejected(hass, data):
            calls.append(data['text'])
            body = {'intro': 'I remember your favourite live show. Which mix?'} if len(calls) == 1 else {'approved': False}
            return {'response': {'speech': {'plain': {'speech': json.dumps(body)}}}}
        with patch.object(core, '_assist_context', return_value={'agent_id': 'synthetic-agent'}), patch.object(core, '_call_dialogue_agent', rejected):
            intro, generated = await self.original_for_you_intro(self.hass, self.runtime, admission, self.owned_genres)
        self.assertFalse(generated)
        self.assertEqual(intro, self.steering.FOR_YOU_INTRO['en'])

    async def test_settings_change_disables_old_choices_without_regeneration(self):
        from dataclasses import replace
        _, offer = await self.prepared()
        changed = replace(self.active, selected_mood='party')
        projected = self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', changed)
        self.assertTrue(projected['visible'])
        self.assertFalse(projected['actions_available'])
        self.assertEqual(projected['reason'], 'session_settings_changed')
        self.assertEqual(projected['options'], offer['options'])
        self.assertEqual(len([p for p in self.reads if p.startswith('/search')]), 3)

    async def test_confirmed_operation_ids_never_enter_generic_model_memory(self):
        from custom_components.djconnect.music_dna import _compact_store_data, _prompt_safe_memory
        await self.runtime.memory.async_record_for_you_choice('synthetic-owner', 'private-operation-id', 'neo soul', authorize=lambda: True)
        row = self.runtime.memory.data['memories']['profile:synthetic-owner']
        self.assertNotIn('for_you_choices', _prompt_safe_memory(row))
        stored = _compact_store_data(self.runtime.memory.data)
        self.assertEqual(stored['memories']['profile:synthetic-owner']['for_you_choices'], [{'operation_id': 'private-operation-id', 'genre': 'neo soul'}])

    async def test_explicit_mix_replaces_current_playback_and_queue(self):
        self.observed = SimpleNamespace(state='playing', media_identity='spotify:track:'+'A'*22)
        self.queue = {'queue': [{'uri': 'spotify:track:'+'B'*22}], 'currently_playing': {'uri': 'spotify:track:'+'A'*22}}
        offer = await self.offer()
        chosen = offer['result_set']['items'][0]['uris']
        self.assertFalse(self.effects)
        result = await self.choose(0, 'replace-on-genre-click')
        self.assertTrue(result['action_outcome']['readback_confirmed'])
        self.assertEqual(self.effects, [('play_uris', chosen, True)])

    async def test_revoked_dna_removes_cached_grants_and_intro(self):
        _, offer = await self.prepared()
        self.runtime.memory.data['memories']['profile:synthetic-owner']['enabled'] = False
        current = self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active)
        self.assertTrue(current['visible'])
        self.assertEqual(current['options'], [])
        self.assertNotIn('result_set', current)
        self.assertEqual(current['intro'], '')
        self.assertFalse(current['actions_available'])

    async def test_dismiss_during_reservation_prevents_late_provider_dispatch(self):
        import asyncio
        history, offer = await self.prepared()
        self.history = history
        self.frame = history.dialogue.owners['profile:synthetic-owner'][offer['conversation_context']['thread_id']]
        admission = self.frame.result_set['first_play_admission']
        action = self.frame.result_set['items'][0]
        entered, release = asyncio.Event(), asyncio.Event()
        async def reserve(*args, **kwargs):
            entered.set()
            await release.wait()
        history.async_reserve_dialogue_effect = reserve
        self.new_turn('pending-phone-click')
        self.turn.thread_id = offer['conversation_context']['thread_id']
        self.turn.client_device_id = 'phone'
        task = asyncio.create_task(self.steering.first_play_choose(self.hass, self.runtime, action, self.frame.result_set, self.turn))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            self.steering.dismiss_for_you(self.hass, 'synthetic-owner', 'phone', offer['conversation_context'],
                {'operation': 'dismiss', 'result_set_id': offer['offer_id'], 'action_id': ''}, history)
            self.assertTrue(admission.withdrawn)
        finally:
            release.set()
        with self.assertRaises(self.dialogue.DialogueError):
            await task
        self.assertEqual(self.effects, [])

    async def prepare_current(self, *, locale='nl'):
        from tests.test_music_dna import FakeStore
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
        from custom_components.djconnect.domain.storage import STORE_KEY
        self.preparation_history = AskDJHistoryManager(store=FakeStore())
        storage = self.hass.data['djconnect'][STORE_KEY]
        self.preparation_context = SimpleNamespace(profile_id='synthetic-owner',
            profile=storage.household.profiles['synthetic-owner'], client_type='ios', device_id='phone')
        source = patch('custom_components.djconnect.reply_artwork.source_admission',
                      return_value=(self.source, lambda: self.allowed))
        source.start()
        self.addCleanup(source.stop)
        await self.new_session(locale=locale)
        await self.steering.prepare_for_you_once(self.hass, self.runtime, self.preparation_context,
            self.active, self.preparation_history, self.preparation_guard)
        return self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active)

    def preparation_guard(self):
        if not self.allowed:
            raise PermissionError('synthetic-owner-withdrawn')

    async def refresh_mood(self, mood):
        previous = self.manager.current_active('synthetic-owner')
        self.active = await self.manager.async_update_mood(owner_profile_id='synthetic-owner',
            session_id=previous.session_id, selected_mood=mood, expected_revision=previous.mood_revision)
        status = self.steering.schedule_for_you_refresh(self.hass, self.runtime, self.preparation_context,
            previous, self.preparation_history, self.preparation_guard)
        return previous, status

    async def wait_refresh(self, status):
        import asyncio
        async with asyncio.timeout(2):
            while status['state'] == 'pending':
                await asyncio.sleep(.001)

    async def test_session_locale_drives_intro_despite_default_english_profile(self):
        offer = await self.prepare_current(locale='nl')
        self.assertEqual(offer['intro'], self.steering.FOR_YOU_INTRO['nl'])
        self.assertEqual(offer['language'], 'nl')
        self.assertEqual([o['label'] for o in offer['options'] if o['genre']=='indie rock'], ['indierock'])
        self.assertEqual(set(o['genre'] for o in offer['options']), set(self.owned_genres))
        self.assertEqual(self.effects, [])

    async def test_locale_projection_never_regenerates_renews_or_changes_mix_ids(self):
        english = await self.prepare_current(locale='en')
        reads = list(self.reads)
        dutch = self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', self.active, locale='nl')
        self.assertEqual(dutch['intro'], self.steering.FOR_YOU_INTRO['nl'])
        self.assertEqual([o['option_id'] for o in english['options']], [o['option_id'] for o in dutch['options']])
        self.assertLessEqual(dutch['expires_in'], english['expires_in'])
        self.assertEqual(self.active.locale, 'en')
        self.assertEqual(self.reads, reads)
        self.assertEqual(self.effects, [])

    async def test_one_preparation_per_confirmed_revision_and_poll_never_retries(self):
        original = await self.prepare_current()
        previous, status = await self.refresh_mood('party')
        same = self.steering.schedule_for_you_refresh(self.hass, self.runtime, self.preparation_context,
            previous, self.preparation_history, self.preparation_guard)
        self.assertIs(same, status)
        await self.wait_refresh(status)
        self.assertEqual(status['state'], 'available')
        current = self.manager.current_active('synthetic-owner')
        offer = self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', current)
        self.assertNotEqual(original['offer_id'], offer['offer_id'])
        self.assertEqual(offer['refresh_policy']['mood_revision'], current.mood_revision)
        self.assertTrue(all(o['visual_recipe']['mood']=='party' for o in offer['options']))
        reads = list(self.reads)
        for _ in range(3):
            self.steering.for_you_projection(self.hass, self.runtime, 'synthetic-owner', current)
            self.steering.schedule_for_you_refresh(self.hass, self.runtime, self.preparation_context,
                previous, self.preparation_history, self.preparation_guard)
        self.assertEqual(self.reads, reads)
        self.assertEqual(self.effects, [])

    async def test_late_mood_result_cannot_replace_newer_offer(self):
        import asyncio
        await self.prepare_current()
        entered, release = asyncio.Event(), asyncio.Event()
        async def delayed(hass, runtime, admission, directions):
            if admission.active.selected_mood == 'chill':
                entered.set()
                await release.wait()
            return self.steering.FOR_YOU_INTRO[admission.locale], False
        with patch.object(self.steering, '_for_you_intro', delayed):
            _, old = await self.refresh_mood('chill')
            await asyncio.wait_for(entered.wait(), 2)
            _, latest = await self.refresh_mood('energy')
            await self.wait_refresh(latest)
            winner = self.active.broadcast.first_play_offer
            release.set()
            await self.wait_refresh(old)
        self.assertIs(self.active.broadcast.first_play_offer, winner)
        self.assertEqual(latest['state'], 'available')
        self.assertEqual(self.effects, [])

    async def test_failed_refresh_is_not_restarted_by_same_revision(self):
        await self.prepare_current()
        async def unavailable(*args):
            raise TimeoutError
        with patch.object(self.steering, '_for_you_intro', unavailable):
            previous, status = await self.refresh_mood('chill')
            await self.wait_refresh(status)
        self.assertEqual(status['state'], 'unavailable')
        reads = list(self.reads)
        self.assertIs(self.steering.schedule_for_you_refresh(self.hass, self.runtime,
            self.preparation_context, previous, self.preparation_history, self.preparation_guard), status)
        self.assertEqual(self.reads, reads)
        self.assertEqual(self.effects, [])
