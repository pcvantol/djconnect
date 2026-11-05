"""Actual isolated HA paired HTTP/SQLite; fixture provider/model responses only."""
from __future__ import annotations
import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT/'scripts/verification')]


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import DJConnectRuntime, pipeline, track_start_announcement as intro
    from custom_components.djconnect.profile_context import profile_storage
    from custom_components.djconnect.domain.music_account import MusicAccountKind
    from custom_components.djconnect.forecast_imagery import artist_authority
    from custom_components.djconnect import api_handlers
    storage = profile_storage(hass)
    await storage.async_upsert_music_account('source-account', 'source-spotify',
        kind=MusicAccountKind.PERSONAL, display_name='Synthetic announcement account',
        linked_profile_ids=frozenset({'profile-a'}), provider_account_id='synthetic-announcement-owner')
    profile = storage.household.profiles['profile-a']
    await storage.async_update_profile('profile-a', preferences=replace(profile.preferences,
        default_backend_id='source-spotify', default_music_account_id='source-account'))
    source_entry = hass.config_entries.async_get_entry('source-entry')
    hass.config_entries.async_update_entry(source_entry, data={**source_entry.data,
        'profile_id':'profile-a', 'music_backend':'source-spotify', 'spotify_client_id':'fixture'})
    hass.data['djconnect']['source-entry'] = DJConnectRuntime(source_entry, device_token='')
    owner_entry = hass.config_entries.async_get_entry('owner-entry')
    hass.config_entries.async_update_entry(owner_entry, data={**owner_entry.data,
        'profile_backend_entry_id':'source-entry', 'music_backend':'source-spotify',
        'music_account_id':'source-account'})
    source = dict(backend_id='source-spotify', music_account_id='source-account',
                  provider_entry_id='source-entry', provider_account_id='synthetic-announcement-owner')
    runtime = hass.data['djconnect']['owner-entry']
    valid = artist_authority(hass, runtime, owner_profile_id='profile-a', expected_source=source)
    assert valid(), 'actual loaded owner/source qualification required'
    active = manager.current_active('profile-a')
    if active:
        await manager.async_end(owner_profile_id='profile-a', session_id=active.session_id)
    cases, examples, calls = {}, [], []
    async def wire(hass, data, **kwargs):
        assert data.get('agent_id') == 'history-fixture-agent'
        assert kwargs.get('allow_agent_fallback') is False
        text = data['text']
        assert 'Synthetic recording' not in text and 'Synthetic performer' not in text
        review = text.startswith('Review this proposed')
        calls.append('review' if review else 'realize')
        answer = json.dumps({'supported':True, 'language_ok':True, 'style_ok':True}) if review else json.dumps(
            {'text':'{artist} — {track}. Geef dit moment even alle ruimte.'})
        return {'response':{'speech':{'plain':{'speech':answer}}}}
    # Connect through the actual paired Session start, not a fabricated
    # registration or direct archive-guard override. No observer/provider effects.
    async def no_background(*args, **kwargs):
        return None
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    with (patch.object(pipeline, '_call_conversation_process_transport', wire),
          patch.object(PlaybackObservationManager, 'async_start_spotify', no_background),
          patch.object(api_handlers, '_async_generate_initial_session_moment', no_background)):
        body, status = await request('POST', '/api/djconnect/v1/session/start', {'mood':'energy', 'language':'nl'})
        assert status == 201, status
        active = manager.current_active('profile-a')
        active = await manager.async_update_presence(owner_profile_id='profile-a',
            session_id=active.session_id, selected_presence='music_only')
        assert 'profile-a' in manager._narration_providers
        for index in range(20):
            observed = SimpleNamespace(state='playing', media_identity='spotify:track:'+chr(65+index)*22,
                title='Synthetic recording', artist='Synthetic performer', position_ms=0,
                duration_ms=180000, catalog={'album_uri':'spotify:album:'+'Z'*22}, target_id='fixture-output')
            await manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=active.session_id,
                state='playing', media_identity=observed.media_identity, title=observed.title, artist=observed.artist,
                position_ms=0, duration_ms=180000)
            occurrence = intro.capture(manager, owner_profile_id='profile-a', session_id=active.session_id,
                observed=observed, authorize=valid)
            moment = await intro.publish(manager, owner_profile_id='profile-a', session_id=active.session_id,
                occurrence=occurrence, authorize=valid)
            assert moment is not None and intro.retained(moment), index
            assert moment.as_dict()['type'] == 'music_announcement'
            assert moment.as_dict()['music_announcement']['realization'] == 'generated'
            body, status = await request('GET', '/api/djconnect/v1/session/active')
            assert status == 200 and body['session']['broadcast']['dj_moments'][-1]['moment_id'] == moment.moment_id, body.keys()
            examples.append({'moment':moment.as_dict(), 'native_delivery':active.broadcast.native_delivery()})
        assert len(calls) == 40 and calls == ['realize','review']*20, calls
        assert active.presence_ledger.announcements_published == 20
        assert active.presence_ledger.total_published == 0
        cases['twenty_music_only_starts_one_original_text_and_independent_review_each'] = 'PASS'
        cases['placeholder_only_generation_no_music_or_audio_effect'] = 'PASS'
        cases['separate_baseline_and_auxiliary_story_budgets'] = 'PASS'
        await manager.async_end(owner_profile_id='profile-a', session_id=active.session_id)
        body, status = await request('GET', '/api/djconnect/v1/session/history/'+active.session_id,
                                     {'history_contract_version':2, 'limit':50})
        assert status == 200, body
        entries = [entry for entry in body['entries'] if entry.get('moment_type') == 'music_announcement']
        assert len(entries) == 20, len(entries)
        assert all(entry['text'] and entry['session_speech']['manual_allowed'] for entry in entries)
        cases['paired_archived_history_contains_all_original_text_and_manual_references'] = 'PASS'
        from custom_components.djconnect.persistence import persistence_service
        from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
        manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
        before, status = await request('GET', '/api/djconnect/v1/profile/settings', {'contract_version':3})
        assert status == 200, before
        from custom_components.djconnect.domain.profile.dj_settings import DJSettings
        choice = {'contract_version':3, 'binding':before['binding'], 'operation_id':str(uuid.uuid7()),
            'patch':{**DJSettings().as_dict(), 'announcement_output':'text_only'},
            'expected_defaults_revision':before['snapshot']['defaults_revision'], 'expected_session':None}
        changed, status = await request('PATCH', '/api/djconnect/v1/profile/settings', choice)
        assert status == 200, changed
        reference = {key:entries[-1][key] for key in ('session_id', 'entry_id')}
        manual, status = await request('POST', '/api/djconnect/v1/speech/prepare',
            {'contract_version':3, 'intent':'manual', 'target':'local', 'processor':'local_on_device',
             'reference':reference})
        assert status == 200 and manual['session_speech']['manual_allowed'], manual
        assert manual['session_speech']['audio_state'] == 'renderer_pending', manual
        automatic, status = await request('POST', '/api/djconnect/v1/speech/prepare',
            {'contract_version':3, 'intent':'automatic', 'target':'local', 'processor':'local_on_device',
             'reference':reference})
        assert status == 200 and not automatic['session_speech']['manual_allowed'], automatic
        assert manager.current_active('profile-a') is None and len(calls) == 40
        cases['actual_text_only_local_manual_archive_replay_without_generation_or_session_restart'] = 'PASS'
        cases['actual_text_only_automatic_archive_speech_denied'] = 'PASS'
        _, status = await request('GET', '/api/djconnect/v1/session/history/'+active.session_id,
                                  {'history_contract_version':2}, authorized=False)
        assert status == 401
        cases['unpaired_history_denied'] = 'PASS'
    return {'qualification':'ACTUAL_ISOLATED_HA_PAIRED_HTTP_SQLITE_MUSIC_ANNOUNCEMENT',
        'cases':cases, 'examples':examples, 'synthetic_model_response_calls':len(calls),
        'real_model_provider_calls':0, 'real_spotify_calls':0, 'music_or_audio_effects':0,
        'native_installed_audible_acceptance':'NOT_RUN',
        'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
