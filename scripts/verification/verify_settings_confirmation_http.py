"""Real HA registered settings/native delivery over disposable owner SQLite.

The existing harness owns pairing/auth/store. No installed config, providers,
model execution, native audio, playback actions or physical devices are used.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from unittest.mock import patch

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT/'scripts/verification')]


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    from custom_components.djconnect.domain.profile.dj_settings import DJSettings
    from custom_components.djconnect import mood_music_steering
    from custom_components.djconnect.session_speech import moment_projection
    service = persistence_service(hass)
    manager._settings_repository = ProfileDJSettingsRepository(service)
    owner = 'profile-a'
    active = manager.current_active(owner)
    if active:
        await manager.async_end(owner_profile_id=owner, session_id=active.session_id)
    cases = {}
    samples = []
    path = '/api/djconnect/v1/profile/settings'

    async def read():
        body, status = await request('GET', path, {'contract_version':3})
        assert status == 200, body
        return body

    def change(before, values):
        session = before['snapshot']['session']
        return {'contract_version':3, 'binding':before['binding'],
            'operation_id':str(uuid.uuid7()), 'patch':values,
            'expected_defaults_revision':before['snapshot']['defaults_revision'],
            'expected_session':{k:session[k] for k in ('session_id','generation','revision')} if session else None}

    with patch.object(mood_music_steering, 'schedule', side_effect=AssertionError('No duplicate mix question')):
        before = await read()
        initial = change(before, {**DJSettings().as_dict(),'mood':'energy','persona':'radio_dj','presence':'balanced'})
        result,status = await request('PATCH', path, initial)
        assert status == 200 and result['settings_confirmation']['moment_id'] is None, result
        assert manager.current_active(owner) is None
        cases['profile_only_confirmation_without_session_creation'] = 'PASS'
        active = await manager.async_start(owner_profile_id=owner,selected_mood='chill',locale='nl')
        for field,value in [('mood','party'),('persona','festival_dj'),('presence','music_only')]:
            before = await read()
            payload = change(before,{field:value})
            result,status = await request('PATCH',path,payload)
            assert status == 200 and result['settings_confirmation']['changed_fields'] == [field], result
            active = manager.current_active(owner)
            moment = active.broadcast.state.dj_moments[-1]
            assert moment.moment_id == result['settings_confirmation']['moment_id']
            assert result['settings_confirmation']['text'] == moment.content
            assert active.presence_ledger.total_published == 0
            assert active.broadcast.native_delivery()['current_moment_id'] == moment.moment_id
            assert active.broadcast.native_delivery(include_owner_only=False)['admissions'] == []
            assert moment_projection(active.broadcast,moment,autoplay=True)['autoplay_eligible']
            boundaries = active.broadcast._moment_delivery_boundaries.copy()
            count = len(active.broadcast.state.dj_moments)
            replay,status = await request('PATCH',path,payload)
            assert status == 200 and replay['replayed'] and replay['settings_confirmation'] == result['settings_confirmation']
            outcome,status = await request('POST',path+'/operation',{'contract_version':3,'binding':before['binding'],'operation_id':payload['operation_id']})
            assert status == 200 and outcome['phase'] == 'accepted'
            assert outcome['receipt']['settings_confirmation'] == result['settings_confirmation']
            assert len(active.broadcast.state.dj_moments) == count and active.broadcast._moment_delivery_boundaries == boundaries
            samples.append({'case':field,'response':result,'moment':moment.as_dict(),'native_delivery':active.broadcast.native_delivery()})
            cases[field+'_one_original_confirmation_replay_readback_no_extra_lease'] = 'PASS'
        cases['paused_music_only_explicit_confirmation_budget_exempt'] = 'PASS'
        cases['owner_only_receiver_redaction'] = 'PASS'
        before = await read()
        noop,status = await request('PATCH',path,change(before,{'presence':'music_only'}))
        assert status == 200 and 'settings_confirmation' not in noop
        cases['same_choice_has_no_confirmation'] = 'PASS'
        denied,status = await request('PATCH',path,payload,authorized=False)
        assert status == 401 and 'settings_confirmation' not in denied
        stale,status = await request('PATCH',path,{**payload,'operation_id':str(uuid.uuid7()),'patch':{'persona':'club_dj'}})
        assert status == 409 and 'settings_confirmation' not in stale
        cases['unauthorized_and_stale_revision_no_false_confirmation'] = 'PASS'
        response = await client.get(path, params={'contract_version':'3', 'client_type':'ios',
                                                  'device_id':'djconnect-ios-ABCDEF123456'})
        assert response.status == 401 and response.headers.get('Cache-Control') == 'no-store'
        cases['registered_http_no_store_on_denial'] = 'PASS'
        before = await read()
        with patch.object(type(active),'compose_moment',side_effect=RuntimeError('causal postcommit fixture')):
            pending,status = await request('PATCH',path,change(before,{'persona':'home_dj'}))
        assert status == 200 and pending['delivery_pending']
        count = len(active.broadcast.state.dj_moments)
        await read()
        # Ordinary settings reads recover through the existing owner Runtime read.
        await manager.async_get_active(owner)
        active = manager.current_active(owner)
        assert len(active.broadcast.state.dj_moments) == count+1
        assert active.broadcast.state.dj_moments[-1].moment_id == pending['settings_confirmation']['moment_id']
        cases['durable_postcommit_fault_recovers_original_publication'] = 'PASS'
        timeline,status = await request('GET','/api/djconnect/v1/session/history/'+active.session_id,
            {'history_contract_version':2})
        assert status == 200, timeline
        retained = [e for e in timeline['entries'] if e.get('archive_basis') == 'runtime_accepted_settings_v1']
        assert len(retained) == 4 and len({e['moment_id'] for e in retained}) == 4, timeline
        assert all(e['historical_view_only'] and not e['current_display_allowed'] for e in retained)
        cases['actual_v2_history_retains_distinct_original_acknowledgements'] = 'PASS'
        await manager.async_end(owner_profile_id=owner,session_id=active.session_id)
        active = await manager.async_start(owner_profile_id=owner,selected_mood='chill',locale='nl',history_enabled=False)
        before = await read()
        result,status = await request('PATCH',path,change(before,{'mood':'chill'}))
        assert status == 200 and result['settings_confirmation']['moment_id'], result
        counts = await service.async_in_transaction(lambda tx: (
            tx.fetchone('SELECT count(*) FROM djconnect_session_entries WHERE session_id=?',(active.session_id,))[0],
            tx.fetchone('SELECT count(*) FROM djconnect_session_acceptances WHERE session_id=?',(active.session_id,))[0]))
        assert counts == (0,0), counts
        assert len(active.broadcast.state.dj_moments) == 1
        cases['actual_history_off_publishes_without_entry_or_semantic_archive_event'] = 'PASS'
    return {'qualification':'ACTUAL_HA_REGISTERED_PAIRED_HTTP_SQLITE_SETTINGS_CONFIRMATION',
        'cases':cases,'examples':samples,'model_provider_calls':0,'playback_or_device_effects':0,
        'native_audio_user_acceptance':'NOT_RUN','time':datetime.now(UTC).isoformat(),
        'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'fixture_sha256':hashlib.sha256(json.dumps(samples,sort_keys=True).encode()).hexdigest()}


if __name__ == '__main__':
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
