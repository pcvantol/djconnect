"""Real isolated HA/paired HTTP/Store/SQL; declared synthetic external read boundaries.

This qualifies routing, original pending purpose and withdrawal, not real model
semantics or factual production quality. No provider/model/network/device effect.
"""
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from unittest.mock import patch


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import DJConnectRuntime, ask_dj, pipeline
    from custom_components.djconnect.ask_dj import public_research
    from custom_components.djconnect.domain.music_account import MusicAccountKind

    domain = hass.data['djconnect']
    runtime = domain['owner-entry']
    storage = domain['djconnect_profile_platform']
    source = hass.config_entries.async_get_entry('source-entry')
    hass.config_entries.async_update_entry(source,
        data={**source.data, 'music_backend': 'source-spotify', 'profile_id': 'profile-a'})
    hass.config_entries.async_update_entry(runtime.entry, data={**runtime.entry.data,
        'music_backend': 'source-spotify', 'music_account_id': 'source-account',
        'profile_backend_entry_id': 'source-entry'})
    domain['source-entry'] = DJConnectRuntime(source)
    await storage.async_upsert_music_account('source-account', 'source-spotify',
        kind=MusicAccountKind.PERSONAL, display_name='Synthetic original account',
        linked_profile_ids=frozenset({'profile-a'}), provider_account_id='original-provider')
    await storage.async_update_profile('profile-a', preferences=replace(
        storage.household.profiles['profile-a'].preferences,
        default_backend_id='source-spotify', default_music_account_id='source-account'))
    active = manager.current_active('profile-a')
    if active:
        await manager.async_end(owner_profile_id='profile-a', session_id=active.session_id)
    session = await manager.async_start(owner_profile_id='profile-a', music_backend='spotify_direct', locale='nl',
        history_source_context={'backend_id': 'source-spotify', 'music_account_id': 'source-account',
            'provider_entry_id': 'source-entry', 'provider_account_id': 'original-provider'})
    uri, aid = 'spotify:track:'+'A'*22, 'B'*22
    mode, calls, interpretations, research_calls = ['clarify'], [], [], []
    after_catalog = [None]

    async def backend(hass, runtime, command, value=None, **kwargs):
        calls.append(command)
        assert command in {'status', 'track_metadata'}, command
        if command == 'status':
            return {'success': True, 'playback': {'uri': uri, 'title': 'PRIVATE DISPLAY TITLE',
                'artist': 'PRIVATE DISPLAY ARTIST', 'is_playing': True}}
        assert value == uri
        if after_catalog[0]:
            after_catalog[0]()
        return {'success': True, 'track': {'uri': uri, 'artist': 'Example Band',
            'title': 'Paper Windows', 'artist_id': aid}}

    async def interpretation(hass, data, **kwargs):
        projection = json.loads(data['text'].split('\nData:\n', 1)[1])
        assert 'available' in projection, 'No synthetic narration or assessment allowed'
        assert 'PRIVATE DISPLAY' not in json.dumps(projection)
        interpretations.append(projection)
        plan = {'read': 'none', 'reference': 'none', 'exclude_current': False}
        if mode[0] == 'production':
            assert projection['available']['production_selection_pending'] is True
            plan.update(read='production_story', reference='current')
        return {'response': {'speech': {'plain': {'speech': json.dumps(plan)}}}}

    async def no_public_evidence(subject, question, language, guard, **kwargs):
        await guard()
        assert subject == 'Example Band' and kwargs['lookup_topic'] == 'Paper Windows'
        assert 'PRIVATE DISPLAY' not in question
        research_calls.append('declared_synthetic_empty_public_source')
        return [], {'state': 'unavailable', 'requests': 0}

    async def send(text, identifier):
        return await request('POST', '/api/djconnect/v1/ask_dj/message', {
            'client_message_id': identifier, 'text': text, 'language': 'nl', 'audio_response': 'never',
            'conversation_context': {'session_id': session.session_id}})

    with patch.object(ask_dj, 'run_music_command', backend), patch.object(
            pipeline, '_call_conversation_process_transport', interpretation), patch.object(
            public_research, 'research', no_public_evidence):
        first, code = await send('Vertel eens over deze productie', 'production-original')
        assert code == 200 and first['clarification_required'] is True, first
        frame = history.dialogue.owners['profile:profile-a']['default']
        pending = dict(frame.pending)
        assert pending['type'] == 'recording_production' and 'question' not in pending
        mode[0] = 'production'
        followup, code = await send('Ik bedoel het liedje dat nu speelt', 'production-selection')
        assert code == 200 and followup['knowledge_basis'] == 'public_recording_research_unavailable', followup
        assert frame.pending is None and pending['request_hash'] in frame.response_dependencies['production-selection']
        assert calls.count('track_metadata') == 1 and len(research_calls) == 1
        assert not followup.get('clarification_required') and not followup.get('playback_actions')
        saved = await history.async_saved_exchange('profile:profile-a', 'production-selection')
        assert saved['assistant_message']['text'] == followup['text']
        bare, code = await send('Huidig nummer', 'production-bare-current')
        assert code == 200 and 'PRIVATE DISPLAY TITLE' in bare['text'], bare
        assert calls.count('track_metadata') == 1
        mode[0] = 'clarify'
        again, code = await send('Vertel eens over deze productie', 'production-race-origin')
        assert code == 200 and again['clarification_required'], again
        def replace_original():
            newer = {**frame.pending, 'request_hash': 'f'*64}
            frame.set_pending(newer)
        after_catalog[0] = replace_original
        closed, code = await send('Huidig nummer', 'production-race-selection')
        assert code == 409, closed
        assert len(research_calls) == 1, 'Replaced purpose must close before public lookup'
    return {'qualification': 'ACTUAL_ISOLATED_HA_PAIRED_HTTP_STORE_SQL_DECLARED_SYNTHETIC_EXTERNAL_READS',
        'cases': {name: 'PASS' for name in ('original_production_clarification',
            'freeworded_selection_retains_original_purpose_and_dependency',
            'empty_public_evidence_recording_specific_unavailable_not_subject_loop',
            'ordinary_Store_saved_reply_matches', 'bare_current_still_identifies_without_catalogue',
            'replacement_during_catalogue_closes_before_public_lookup', 'no_private_labels_in_interpreter')},
        'effect_count': 0, 'model_provider_calls': 0, 'native': 'NOT_RUN', 'installed': 'NOT_RUN',
        'factual_narrative_quality': 'NOT_QUALIFIED',
        'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
