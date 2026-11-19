"""Actual paired HA/Settings3 For-you refresh; synthetic provider wires, no playback."""
from __future__ import annotations
import asyncio
import hashlib
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT/'scripts/verification')]
from verify_session_for_you_http import qualify as base_qualify  # noqa: E402


async def qualify(hass, manager, history, request, client):
    examples = []
    async def after(hass, manager, history, request, state):
        from custom_components.djconnect import mood_music_steering as steering
        from custom_components.djconnect.persistence import persistence_service
        from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
        from custom_components.djconnect.domain.profile.dj_settings import DJSettings
        manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
        cases = {}
        path = '/api/djconnect/v1/profile/settings'
        async def change(values):
            before, status = await request('GET', path, {'contract_version':3})
            assert status == 200, before
            session = before['snapshot']['session']
            payload = {'contract_version':3, 'binding':before['binding'],
                'operation_id':str(uuid.uuid7()), 'patch':values,
                'expected_defaults_revision':before['snapshot']['defaults_revision'],
                'expected_session':{k:session[k] for k in ('session_id','generation','revision')} if session else None}
            result, status = await request('PATCH', path, payload)
            assert status == 200, result
            return payload, result
        for locale in ('en', 'nl'):
            active = manager.current_active('profile-a')
            if active:
                await manager.async_end(owner_profile_id='profile-a', session_id=active.session_id)
            state.update(active=True, playing=False, track=None, effects=[], reads=[], tracks={})
            # Current Settings3 defaults are the canonical Session-start source.
            await change({**DJSettings().as_dict(), 'mood':'energy'})
            started, status = await request('POST', '/api/djconnect/v1/session/start', {'mood':'chill','language':locale})
            assert status == 201, started
            assert started['session']['selected_mood'] == 'chill'
            assert started['for_you']['intro'] == steering.FOR_YOU_INTRO[locale], started['for_you']
            assert started['for_you']['language'] == locale
            defaults_after, status = await request('GET', path, {'contract_version':3})
            assert status == 200 and defaults_after['snapshot']['defaults']['mood']=='energy'
            assert defaults_after['snapshot']['session']['settings']['mood']=='chill'
            cases[locale+'_explicit_welcome_mood_session_only_not_stored_default'] = 'PASS'
            payload, result = await change({'mood':'party'})
            async with asyncio.timeout(5):
                while True:
                    projected, status = await request('GET', '/api/djconnect/v1/session/active', {'language':locale})
                    assert status == 200
                    if projected['for_you']['refresh_policy']['state'] != 'pending':
                        break
                    await asyncio.sleep(.005)
            offer = projected['for_you']
            assert offer['refresh_policy']['state'] == 'available', offer
            assert offer['refresh_policy']['mood_revision'] == projected['session']['mood_revision']
            assert offer['intro'] == steering.FOR_YOU_INTRO[locale]
            assert all(o['visual_recipe']['mood']=='party' for o in offer['options'])
            reads = list(state['reads'])
            replay, status = await request('PATCH', path, payload)
            assert status == 200 and replay['replayed'], replay
            again, status = await request('GET', '/api/djconnect/v1/session/active', {'language':locale})
            assert again['for_you']['offer_id'] == offer['offer_id'] and state['reads'] == reads
            assert not state['effects']
            cases[locale+'_confirmed_settings3_mood_one_offer_no_playback_or_retry'] = 'PASS'
            examples.append({'language':locale, 'stage':'refreshed_offer', 'body':projected})
            state['active'] = False
            item = offer['result_set']['items'][0]
            selected, status = await request('POST', '/api/djconnect/v1/ask_dj/message', {
                'client_message_id':'refresh-choice-'+locale, 'text':item['title'], 'language':locale,
                'audio_response':'never', 'conversation_context':offer['conversation_context'],
                'choice_action':{'operation':'select', 'result_set_id':offer['offer_id'], 'action_id':item['action_id']}})
            assert status == 200 and selected['first_play']['state']=='output', selected
            continuation = selected['for_you']['continuation']
            assert continuation['result_set']['items'] == selected['result_set']['items']
            assert continuation['result_set']['result_set_id'] == selected['result_set']['result_set_id']
            assert 0 < continuation['result_set']['expires_in'] <= continuation['expires_in']
            assert not state['effects']
            poll, status = await request('GET', '/api/djconnect/v1/session/active', {'language':locale})
            assert poll['for_you']['continuation']['result_set']['result_set_id'] == selected['result_set']['result_set_id']
            assert poll['for_you']['continuation']['expires_in'] <= continuation['expires_in']
            examples.append({'language':locale, 'stage':'original_speaker_continuation', 'body':selected})
            cases[locale+'_speaker_continuation_original_ids_and_original_lease'] = 'PASS'
            output = continuation['result_set']['items'][0]
            command = {'client_message_id':'refresh-output-'+locale, 'text':output['title'],
                'language':locale, 'audio_response':'never',
                'conversation_context':continuation['conversation_context'],
                'choice_action':{'operation':'select',
                    'result_set_id':continuation['result_set']['result_set_id'], 'action_id':output['action_id']}}
            played, status = await request('POST', '/api/djconnect/v1/ask_dj/message', command)
            assert status == 200 and played['action_outcome']['readback_confirmed'], played
            assert state['effects'] == [{'kind':'output','play':False},
                {'kind':'play','uris':item['uris'],'output':'synthetic-first-play-output'}]
            repeated, status = await request('POST', '/api/djconnect/v1/ask_dj/message', command)
            assert status == 200 and repeated['assistant_message']['id']==played['assistant_message']['id']
            assert len(state['effects']) == 2
            assert played['for_you']['state']=='confirmed' and not played['for_you']['visible']
            examples.append({'language':locale, 'stage':'exact_mix_confirmed_once', 'body':played})
            cases[locale+'_original_speaker_then_exact_mix_once_and_duplicate_no_second_effect'] = 'PASS' 
        return cases
    result = await base_qualify(hass, manager, history, request, client, after=after)
    result.update(qualification='ACTUAL_ISOLATED_HA_SETTINGS3_FOR_YOU_REFRESH',
                  refresh_examples=examples, harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return result


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
