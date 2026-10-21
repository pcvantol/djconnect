"""Synthetic archive deletion through actual HA paired HTTP, Store and SQLite.

Reuses ordinary pairing and real DJConnectRuntime authority from the existing
isolated lab. No live config, external network, paid provider or personal data.
Run in the pinned HA image with readonly /candidate and disposable /lab.
"""
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


def operation(sequence):
    ms = int(datetime.now(UTC).timestamp() * 1000)
    return str(UUID(int=(ms << 80) | (7 << 76) | (2 << 62) | sequence))


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
    from custom_components.djconnect.history_deletion import deletion_coordinator
    from custom_components.djconnect.session_conversation import query_service
    service = persistence_service(hass)
    repo = HistoricalProjectionRepository(service)
    cases = []
    examples = {}
    before = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    async def seed(owner, name, *, terminal=True):
        session = await manager.async_start(owner_profile_id=owner, selected_mood='chill', locale='en')
        exchange = await history.async_append_exchange(
            'profile:' + owner, {'client_message_id': name, 'text': 'Synthetic question ' + name},
            {'success': True, 'text': 'Synthetic answer ' + name},
            session_turn={'turn_id': name, 'context': {'session_id': session.session_id}})
        await repo.async_append_entries(owner, session.session_id, [
            {'kind': 'conversation_user' if m['role'] == 'user' else 'conversation_dj',
             'reference_id': name + '-' + m['role'], 'body': {'history_scope': 'profile:' + owner,
                'turn_id': name, 'message_id': m['id']}} for m in exchange['messages']])
        if terminal:
            await manager.async_end(owner_profile_id=owner, session_id=session.session_id)
        return session.session_id

    old = await seed('profile-a', 'archive-delete-old')
    foreign = await seed('profile-other', 'archive-delete-foreign')
    detail, status = await request('GET', '/api/djconnect/v1/session/history/' + old,
                                   {'history_contract_version': '2'})
    assert status == 200 and len(detail['entries']) == 2, detail
    delete = {'session_id': old, 'expected_revision': detail['session']['revision'],
              'operation_id': operation(1), 'confirmed': True, 'history_contract_version': 2}
    forbidden, status = await request('POST', '/api/djconnect/v1/session/history/delete',
                                      {**delete, 'session_id': foreign})
    assert status == 404 and forbidden['error'] == 'history_unavailable', forbidden
    examples['single_request'] = delete
    cases.append('actual_paired_foreign_target_hidden')
    # The actual Store writes bytes, then deliberately loses its acknowledgement.
    save = history._store.async_save
    async def lost_ack(data):
        await save(data)
        raise OSError('synthetic lost acknowledgement after actual HA Store save')
    with patch.object(history._store, 'async_save', lost_ack):
        unknown, status = await request('POST', '/api/djconnect/v1/session/history/delete', delete)
    assert status == 503 and unknown['error'] == 'history_delete_outcome_unknown', unknown
    raw, raw_status = await request('GET', '/api/djconnect/v1/ask_dj/history')
    assert raw_status == 503 and raw['error'] == 'history_delete_outcome_unknown', raw
    examples['pending_response'] = unknown
    hidden, status = await request('GET', '/api/djconnect/v1/session/history/' + old)
    assert status in {404, 503} and 'entries' not in hidden, hidden
    try:
        await history.async_history('profile:profile-a')
    except RuntimeError as error:
        assert str(error) == 'history_delete_outcome_unknown'
    else:
        raise AssertionError('pending erasure must close Store reads')
    cases.append('actual_store_save_lost_ack_no_success_or_reread')

    # A separate Python process reopens the actual SQLite and HA Store, with no
    # original RAM, request lifetime or paired context. It must finish the intent.
    await service.async_close()
    process = await asyncio.create_subprocess_exec(
        sys.executable, str(Path(__file__)), '--recover', hass.config.config_dir,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(process.communicate(), 45)
    assert process.returncode == 0, stderr.decode()[-3000:]
    recovered = json.loads(stdout.decode().strip().splitlines()[-1])
    assert recovered == {'recovered': 1, 'pending': 0}, recovered
    await service.async_initialize()
    # Drop the previous process-local read cache/barriers, exactly as a new HA
    # request owner would do after startup recovery.
    domain = hass.data['djconnect']
    domain.pop('history_deletion_coordinator', None)
    domain.pop('session_history_query', None)
    service.history_retention_writes = 0
    service.history_retention_epoch += 1
    restored = AskDJHistoryManager(hass)
    domain['ask_dj_history_manager'] = restored
    domain['owner-entry'].ask_dj_history = restored
    query_service(hass, restored)
    assert await repo.async_session_record(old) is None
    assert await repo.async_session_record(foreign) is not None
    assert 'archive-delete-old' not in str((await restored.async_history('profile:profile-a'))['messages'])
    cases.append('separate_process_durable_sqlite_store_recovery')
    completed, status = await request('POST', '/api/djconnect/v1/session/history/delete', delete)
    assert status == 200 and completed['deleted_session_id'] == old, completed
    examples['single_response'] = completed
    cases.append('exact_completed_receipt_after_process_recovery')

    # Bulk uses all retained server records, not a displayed page. A Session
    # ending after snapshot preparation is deliberately kept.
    history = restored
    first = await seed('profile-a', 'archive-bulk-first')
    second = await seed('profile-a', 'archive-bulk-second')
    captured, status = await request('GET', '/api/djconnect/v1/session/history/delete_snapshot')
    assert status == 200 and captured['target_count'] >= 2, captured
    examples['snapshot_response'] = captured
    newer = await seed('profile-a', 'archive-bulk-newer')
    live = await seed('profile-a', 'archive-bulk-live', terminal=False)
    playback_before = manager.current_active('profile-a').broadcast.state.playback
    # The existing paired-owner WebSocket remains bound to its original live
    # Session across archive erasure; no native HA credential is minted.
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
            async def active_read(identifier):
                await ws.send_json({'id': identifier, 'type': 'djconnect/read',
                                    'operation': 'session/active', 'payload': {}})
                frame = await asyncio.wait_for(ws.receive_json(), 10)
                assert frame['success'] and frame['id'] == identifier, frame
                assert frame['connection_id'] == ready['connection_id']
                assert frame['result']['session']['session_id'] == live, frame
            await active_read(1)
            bulk_request = {'snapshot_id': captured['snapshot_id'], 'operation_id': operation(2), 'confirmed': True}
            result, status = await request('POST', '/api/djconnect/v1/session/history/delete_all', bulk_request)
            examples['bulk_request'] = bulk_request
            examples['bulk_response'] = result
            assert status == 200 and result['deleted_session_count'] == captured['target_count'], result
            for target in (first, second):
                assert await repo.async_session_record(target) is None
            for preserved in (newer, live, foreign):
                assert await repo.async_session_record(preserved) is not None
            assert manager.current_active('profile-a').session_id == live
            assert manager.current_active('profile-a').broadcast.state.playback == playback_before
            assert 'archive-bulk-newer' in str((await history.async_history('profile:profile-a'))['messages'])
            assert 'archive-bulk-live' in str((await history.async_history('profile:profile-a'))['messages'])
            assert 'archive-bulk-first' not in str((await history.async_history('profile:profile-a'))['messages'])
            assert not await deletion_coordinator(hass).journal.async_pending()
            cases.append('actual_bulk_snapshot_new_completion_active_foreign_playback_preserved')
            await active_read(2)
            cases.append('actual_paired_websocket_keeps_original_active_session_across_bulk_erasure')
    finally:
        await secure_site.stop()
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == before
    return {'scenario': 'archive_deletion_actual_ha', 'cases': cases, 'model_calls': 0, 'examples': examples,
            'harness_sha256': before, 'qualification': 'paired HTTP/WebSocket/HA Store/SQLite plus separate-process recovery; synthetic data only; no native/installed acceptance'}


async def recover(config):
    from homeassistant.core import HomeAssistant
    from custom_components.djconnect.persistence import async_initialize_persistence, async_shutdown_persistence
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
    from custom_components.djconnect.persistence.history_deletion import HistoryDeletionRepository
    hass = HomeAssistant(config)
    # Bootstrap performs the production recovery before reconciliation/maintenance.
    service = await async_initialize_persistence(hass)
    assert not await HistoryDeletionRepository(service).async_pending()
    history = AskDJHistoryManager(hass)
    assert 'archive-delete-old' not in str((await history.async_history('profile:profile-a'))['messages'])
    await async_shutdown_persistence(hass)
    print(json.dumps({'recovered': 1, 'pending': 0}))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--recover':
        asyncio.run(recover(sys.argv[2]))
    else:
        from verify_session_conversation_history_http import main
        asyncio.run(main(qualification_extension=qualify))
