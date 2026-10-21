"""Individual erasure over real HA paired HTTP/TLSWS/Store/SQLite; synthetic only."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
from uuid import UUID

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', '/candidate'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts/verification'))
PREFIX = '/api/djconnect/v1/session/content/delete'


def operation(sequence):
    ms = int(datetime.now(UTC).timestamp() * 1000)
    return str(UUID(int=(ms << 80) | (7 << 76) | (2 << 62) | sequence))


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
    from custom_components.djconnect.content_deletion import content_deletion_coordinator
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager, _request_hash
    service = persistence_service(hass)
    repo = HistoricalProjectionRepository(service)
    examples, cases = {}, []

    async def exchange(name, sid='', dependencies=()):
        saved = await history.async_append_exchange('profile:profile-a',
            {'client_message_id': name, 'text': 'Synthetic question ' + name},
            {'success': True, 'text': 'Synthetic answer ' + name},
            session_turn={'turn_id': name, 'context': {'session_id': sid},
                'dependency_request_hashes': [_request_hash('profile:profile-a', n) for n in dependencies]})
        if sid:
            saved['entry_ids'] = await repo.async_append_entries('profile-a', sid, [
                {'kind': 'conversation_user' if m['role'] == 'user' else 'conversation_dj',
                 'reference_id': name + '-' + m['role'],
                 'body': {'history_scope': 'profile:profile-a', 'turn_id': name, 'message_id': m['id']}}
                for m in saved['messages']])
        return saved

    async def prepare(kind, sid, target):
        body = {'contract_version': 1, 'target': {'kind': kind, 'session_id': sid, 'target_id': target}}
        result, status = await request('POST', PREFIX + '/prepare', body)
        assert status == 200, result
        return body, result

    def command(preview, seq):
        return {'contract_version': 1, 'confirmation_id': preview['confirmation_id'],
                'operation_id': operation(seq), 'confirmed': True}

    async def status(command):
        return await request('GET', PREFIX + '/status',
            {k: str(v) for k, v in command.items() if k != 'confirmed'})

    live = await manager.async_start(owner_profile_id='profile-a', selected_mood='chill', locale='en')
    selected = await exchange('individual-selected', live.session_id)
    dependent = await exchange('individual-dependent', live.session_id, ('individual-selected',))
    independent = await exchange('individual-independent', live.session_id)
    playback_before = live.broadcast.state.playback
    body, preview = await prepare('message', live.session_id, selected['user_message']['id'])
    _, other = await prepare('message', live.session_id, selected['assistant_message']['id'])
    assert preview['unit'] == other['unit'] and preview['removed_message_ids'] == other['removed_message_ids']
    assert len(preview['removed_message_ids']) == len(preview['unavailable_message_ids']) == 2
    examples.update(prepare_request=body, prepare_response=preview)
    foreign = await manager.async_start(owner_profile_id='profile-other', selected_mood='chill', locale='en')
    wrong, code = await request('POST', PREFIX + '/prepare', {'contract_version': 1,
        'target': {**body['target'], 'session_id': foreign.session_id}})
    assert code == 404 and wrong['error'] == 'content_unavailable', wrong
    examples['foreign_response'] = wrong
    wrong, code = await request('POST', PREFIX + '/prepare', {**body, 'profile_id': 'profile-other'})
    assert code == 400 and wrong['error'] == 'invalid_content_delete_request', wrong
    # Changed SQL scope must not silently change the confirmed operation.
    await repo.async_append_entries('profile-a', live.session_id, [{'kind': 'playback_observed',
        'reference_id': 'synthetic-preserved-observation', 'body': {'item_id': 'synthetic-observed'}}])
    stale, code = await request('POST', PREFIX, command(preview, 98))
    assert code == 409 and stale['error'] == 'content_delete_scope_conflict', stale
    assert len((await history.async_history('profile:profile-a'))['messages']) == 6
    body, preview = await prepare('message', live.session_id, selected['user_message']['id'])
    examples.update(prepare_request=body, prepare_response=preview, wrong_profile_hint_response=wrong, stale_scope_response=stale)
    cases.append('actual_other_owner_wrong_session_extra_profile_and_stale_scope_refused_without_erase')
    cmd = command(preview, 1)
    rejected, code = await request('POST', PREFIX, {**cmd, 'confirmed': False})
    assert code == 400 and rejected['error'] == 'invalid_content_delete_request', rejected
    assert len((await history.async_history('profile:profile-a'))['messages']) == 6
    cases.append('actual_prepare_either_role_same_server_exchange_exact_cascade_explicit_consent')
    # Original paired TLS WebSocket keeps the active Session across this content operation.
    from aiohttp import ClientSession, TCPConnector, web
    from verify_hybrid_transport_http import tls
    server_ssl, client_ssl = tls(Path(hass.config.config_dir))
    secure_site = web.TCPSite(client.server.runner, '127.0.0.1', 0, ssl_context=server_ssl)
    await secure_site.start()
    secure = 'https://127.0.0.1:' + str(secure_site._server.sockets[0].getsockname()[1])
    try:
        async with ClientSession(connector=TCPConnector(ssl=client_ssl)) as secure_client, secure_client.ws_connect(
                secure + '/api/djconnect/v1/actions/paired') as ws:
            assert (await ws.receive_json())['type'] == 'auth_required'
            await ws.send_json({'type': 'auth', 'protocol_version': 1, 'audience': 'paired_owner_actions',
                'device_id': 'djconnect-ios-ABCDEF123456', 'client_type': 'ios',
                'device_token': hass.data['djconnect']['owner-entry'].device_token})
            ready = await ws.receive_json()
            assert ready['type'] == 'auth_ok', ready
            async def read(identifier):
                await ws.send_json({'id': identifier, 'type': 'djconnect/read', 'operation': 'session/active', 'payload': {}})
                frame = await asyncio.wait_for(ws.receive_json(), 10)
                assert frame['success'] and frame['connection_id'] == ready['connection_id'], frame
                assert frame['result']['session']['session_id'] == live.session_id, frame
            await read(1)
            result, code = await request('POST', PREFIX, cmd)
            assert code == 200 and result['state'] == 'completed', result
            assert not result['music_playback_undone']
            assert manager.current_active('profile-a').session_id == live.session_id
            assert manager.current_active('profile-a').broadcast.state.playback == playback_before
            await read(2)
    finally:
        await secure_site.stop()
    rows = (await history.async_history('profile:profile-a'))['messages']
    assert not any(m['id'] in preview['removed_message_ids'] for m in rows)
    assert all(m['content_state'] == 'source_withdrawn' for m in rows if m['id'] in preview['unavailable_message_ids'])
    assert all(any(m['id'] == original['id'] for m in rows) for original in independent['messages'])
    for eid in selected['entry_ids']:
        assert await repo.async_entry_record('profile-a', live.session_id, eid) is None
    for eid in dependent['entry_ids'] + independent['entry_ids']:
        assert await repo.async_entry_record('profile-a', live.session_id, eid) is not None
    examples.update(delete_request=cmd, delete_response=result)
    found, code = await status(cmd)
    assert code == 200 and found['state'] == 'completed', found
    examples['completed_status_response'] = found
    cases.append('actual_active_session_playback_independent_exchange_and_original_tlsws_preserved')

    # Standalone Profile contributions have no invented Session/context binding.
    standalone = await exchange('standalone-selected')
    _, standalone_preview = await prepare('message', '', standalone['assistant_message']['id'])
    standalone_result, code = await request('POST', PREFIX, command(standalone_preview, 2))
    assert code == 200 and standalone_result['unit']['session_id'] == '', standalone_result
    examples['standalone_response'] = standalone_result
    cases.append('actual_standalone_profile_either_bubble_erases_server_pair')
    _, cancelled = await prepare('request', '', 'original-uncertain-not-arrived')
    cancelled_cmd = command(cancelled, 3)
    answer, code = await request('POST', PREFIX, cancelled_cmd)
    assert code == 200 and answer['unit']['kind'] == 'attempt', answer
    late, code = await request('POST', '/api/djconnect/v1/ask_dj/message',
        {'client_message_id': 'original-uncertain-not-arrived', 'text': 'What is an ostinato?'})
    assert code != 200 and not late.get('success'), late
    examples.update(attempt_prepare_response=cancelled, attempt_response=answer, late_attempt_response=late)
    cases.append('actual_original_pre_admission_cancel_prevents_provider_and_store_replay')

    # Accepted active Moment is withdrawn through the normal Runtime-owned chain.
    await manager.async_end(owner_profile_id='profile-a', session_id=live.session_id)
    moment_session = await manager.async_start(owner_profile_id='profile-a', selected_mood='groove', locale='en',
        music_backend='spotify_direct', history_source_context={'backend_id': 'source-spotify',
            'music_account_id': 'source-account', 'provider_entry_id': 'source-entry'})
    from custom_components.djconnect import session_facts
    fact = session_facts._fact('recording_credits', {'uri': 'spotify:track:0123456789abcdefghijkL'}, 'track_context',
        ['Synthetic Composer'] * 5,
        [f"{session_facts.CREDIT_ROLES['producer'][i]}: Synthetic Composer" for i in range(5)], 'MusicBrainz',
        'https://musicbrainz.org/recording/11111111-1111-1111-1111-111111111111',
        session_facts.DisplayFactCore('recording_credits', roles=(('producer', ('Synthetic Composer',)),)))
    await manager.async_update_playback_projection(owner_profile_id='profile-a', session_id=moment_session.session_id,
        state='playing', media_identity=fact.media_identity, title='Synthetic work', artist='Synthetic performer',
        duration_ms=300000, position_ms=1000)
    async def provider():
        return {'_qualified_facts': (fact,)}
    moment = await manager.async_process_track_started(owner_profile_id='profile-a', session_id=moment_session.session_id,
        media_identity=fact.media_identity, insight_provider=provider, require_current_playback=True, allow_initial_facts=True)
    assert moment is not None, {'last_decision': str(manager.current_active('profile-a').planner.last_decision),
        'fact_count': manager._intra_track_opportunities['profile-a'].fact_count}
    from dataclasses import replace
    from custom_components.djconnect import session_runtime as core
    current = manager.current_active('profile-a')
    target = replace(moment, moment_id='independent-transition-target', moment_type=core.DJMomentType.RECOMMENDATION)
    current.moment_engine.moments = (*current.moment_engine.moments, target)
    # Use the actual ordinary transition engine, with no genre-only proof.
    decision = core.PlannerDecision(core.PlannerDecisionType.CREATE_TRANSITION, 'synthetic_relation',
        core.KnowledgeIntent(core.KnowledgeIntentType.TRANSITION, 'Synthetic relation'),
        transition_moment_ids=(moment.moment_id, target.moment_id), transition_placement='next')
    transition = current.moment_engine.create_transition(session_id=current.session_id, approval=decision,
        selected_mood='groove', persona=core.DJPersona.HOME_DJ, locale='en')
    assert transition.moment_type is core.DJMomentType.TRANSITION and transition.genre_transition is None
    current.presence_ledger.clock = lambda: current.presence_ledger.last_at + 91
    assert await manager._async_persist_moment(current, transition)
    row = next(r for r in await repo.async_entry_records('profile-a', current.session_id)
        if r['reference_id'] == transition.moment_id)
    assert set(json.loads(row['body'])['dependency_moment_ids']) == {moment.moment_id, target.moment_id}
    current.broadcast.publish_moment(transition)
    _, moment_preview = await prepare('moment', moment_session.session_id, moment.moment_id)
    answer, code = await request('POST', PREFIX, command(moment_preview, 4))
    assert code == 200, answer
    current = manager.current_active('profile-a')
    assert current.session_id == moment_session.session_id and not current.broadcast.content_pending
    assert moment.moment_id not in {m.moment_id for m in current.moment_engine.moments}
    assert moment.moment_id not in {i.moment_id for i in current.planner.output.session_flow.items}
    assert not current.allows_moment(moment)
    assert transition.moment_id not in {m.moment_id for m in current.broadcast.state.dj_moments}
    assert not current.allows_moment(transition)
    assert target.moment_id in {m.moment_id for m in current.moment_engine.moments}
    cases.append('ordinary_transition_explicit_ids_durably_captured_and_live_dependency_withdrawn')
    examples.update(moment_prepare_response=moment_preview, moment_response=answer)
    cases.append('actual_active_moment_flow_engine_native_admission_withdrawn_without_session_end')

    # Durable intent before a real HA Store save with a deliberately lost ack.
    recover_pair = await exchange('individual-recover')
    _, pending = await prepare('message', '', recover_pair['user_message']['id'])
    pending_cmd = command(pending, 5)
    save = history._store.async_save
    async def lost_ack(data):
        await save(data)
        raise OSError('synthetic lost actual Store acknowledgement')
    with patch.object(history._store, 'async_save', lost_ack):
        unknown, code = await request('POST', PREFIX, pending_cmd)
    assert code == 503 and unknown['error'] == 'content_delete_outcome_unknown', unknown
    before_clock = await service.async_in_transaction(lambda tx: tx.fetchall('SELECT * FROM djconnect_history_deletion_clock'))
    found, code = await status(pending_cmd)
    assert code == 200 and found['state'] == 'pending', found
    assert before_clock == await service.async_in_transaction(lambda tx: tx.fetchall('SELECT * FROM djconnect_history_deletion_clock'))
    assert len(await content_deletion_coordinator(hass).journal.async_pending_content()) == 1
    examples.update(pending_request=pending_cmd, pending_response=unknown, pending_status_response=found)
    cases.append('actual_status_is_read_only_no_recovery_clock_renewal_or_optimistic_success')
    await service.async_close()
    process = await asyncio.create_subprocess_exec(sys.executable, str(Path(__file__)), '--recover', hass.config.config_dir,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(process.communicate(), 45)
    assert process.returncode == 0, stderr.decode()[-3000:]
    assert json.loads(stdout.decode().strip().splitlines()[-1]) == {'recovered': 1, 'pending': 0}
    await service.async_initialize()
    domain = hass.data['djconnect']
    for key in ('content_deletion_coordinator', 'history_deletion_coordinator', 'session_history_query', 'content_confirmations'):
        domain.pop(key, None)
    service.history_retention_writes = 0
    service.history_retention_epoch += 1
    history = AskDJHistoryManager(hass)
    domain['ask_dj_history_manager'] = history
    domain['owner-entry'].ask_dj_history = history
    result, code = await request('POST', PREFIX, pending_cmd)
    assert code == 200 and result['state'] == 'completed', result
    assert not any(m.get('client_message_id') == 'individual-recover' for m in
        (await history.async_history('profile:profile-a'))['messages'])
    examples['recovered_response'] = result
    cases.append('separate_process_sqlite_actual_store_recovery_and_same_original_receipt_without_preview')
    return {'scenario': 'individual_content_deletion_actual_ha', 'cases': cases, 'examples': examples,
            'model_provider_calls': 0, 'harness_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'installed': 'NOT_RUN', 'native_audio_user_acceptance': 'NOT_RUN'}


async def recover(config):
    from homeassistant.core import HomeAssistant
    from custom_components.djconnect.persistence import async_initialize_persistence, async_shutdown_persistence
    from custom_components.djconnect.persistence.content_deletion import ContentDeletionRepository
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
    hass = HomeAssistant(config)
    service = await async_initialize_persistence(hass)
    assert not await ContentDeletionRepository(service).async_pending_content()
    history = AskDJHistoryManager(hass)
    assert not any(m.get('client_message_id') == 'individual-recover' for m in
        (await history.async_history('profile:profile-a'))['messages'])
    await async_shutdown_persistence(hass)
    print(json.dumps({'recovered': 1, 'pending': 0}))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--recover':
        asyncio.run(recover(sys.argv[2]))
    else:
        from verify_session_conversation_history_http import main
        asyncio.run(main(qualification_extension=qualify))
