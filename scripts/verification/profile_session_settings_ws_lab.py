"""Actual TLS paired sockets and existing HA event infrastructure, no native claim."""

import asyncio
from contextlib import AsyncExitStack
import json
import os
import resource
import ssl
import time
from uuid import UUID

from aiohttp import web


async def run(hass, runtime, client, identity, output, peers):
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(output/'server.pem', output/'server-key.pem')
    site = web.TCPSite(client.server.runner, '127.0.0.1', 18239, ssl_context=tls)
    await site.start()
    participants = [(runtime.entry, identity)]
    for entry_id in peers:
        entry = hass.config_entries.async_get_entry(entry_id)
        peer = {'device_id': entry.data['device_id'], 'client_type': entry.data['client_type']}
        # The configured-slot API pairs the active setup slot; the HA config-
        # flow UI is outside this test. Select that explicit real Runtime as in
        # entry bootstrap, then exercise the unmodified pair/auth acceptance.
        domain = hass.data['djconnect']
        previous_primary = domain['runtime']
        domain['runtime'] = domain[entry_id]
        try:
            response = await client.post('/api/djconnect/v1/pair', json={**peer, 'pair_code': entry.data['pair_code']})
            paired = await response.json()
        finally:
            domain['runtime'] = previous_primary
        assert response.status == 200, (peer['client_type'], response.status, paired.get('error'))
        assert paired['device_token'] == entry.data['device_token']
        participants.append((entry, peer))
    requests = [0]*len(participants)
    collected = []
    try:
        async with AsyncExitStack() as stack:
            sockets = []
            async def connect(entry, peer):
                ws = await stack.enter_async_context(client.session.ws_connect(
                    'https://127.0.0.1:18239/api/djconnect/v1/actions/paired', ssl=False))
                required = await ws.receive_json(timeout=3)
                assert required['type'] == 'auth_required'
                await ws.send_json({'type': 'auth', 'protocol_version': 1,
                    'audience': 'paired_owner_actions', **peer, 'device_token': entry.data['device_token']})
                accepted = await ws.receive_json(timeout=3)
                assert accepted['type'] == 'auth_ok', accepted
                return ws
            for entry, peer in participants:
                sockets.append(await connect(entry, peer))

            async def command(index, kind, **fields):
                requests[index] += 1
                rid = requests[index]
                await sockets[index].send_json({'id': rid, 'type': kind, **fields})
                while True:
                    item = await sockets[index].receive_json(timeout=3)
                    if item.get('type') == 'event':
                        collected.append((index, item))
                        continue
                    assert item['id'] == rid and item['status'] == 200, item
                    return item['result']

            for index in range(len(sockets)):
                await command(index, 'djconnect/profile/settings/subscribe', contract_version=2, enabled=True)
            expected = None
            changes = ({'persona': 'festival_dj'}, {'mood': 'energy'}, {'presence': 'balanced'},
                       {'voice': {'kind': 'provider_default'}}, {'gender': 'female'})
            matrix = []
            for counter, patch in enumerate(changes, 1):
                before = await command(0, 'djconnect/read', operation='profile/settings', payload={'contract_version': 2})
                assert before['snapshot']['session'] is None
                now = int(time.time()*1000)
                op = str(UUID(int=(now << 80) | (7 << 76) | (2 << 62) | (100+counter)))
                updated = await command(0, 'djconnect/profile/settings/update', payload={
                    'contract_version': 2, 'binding': before['binding'], 'operation_id': op, 'patch': patch,
                    'expected_defaults_revision': before['snapshot']['defaults_revision'], 'expected_session': None})
                expected = updated['snapshot']['defaults']
                for index in (1, 2):
                    event = await sockets[index].receive_json(timeout=3)
                    assert event.get('event') == 'profile/settings/changed', event
                    assert not any(key in json.dumps(event) for key in ('profile_id', 'defaults', 'voice_id', 'gender'))
                    state = await command(index, 'djconnect/read', operation='profile/settings', payload={'contract_version': 2})
                    assert state['snapshot']['defaults'] == expected
                    assert state['snapshot']['defaults_revision'] == updated['snapshot']['defaults_revision']
                matrix.append({'patch': patch, 'confirmed_revision': updated['snapshot']['defaults_revision'],
                               'surfaces': ['paired_ios', 'paired_macos', 'paired_second_ios']})
            try:
                unsolicited = await sockets[3].receive_json(timeout=.25)
            except asyncio.TimeoutError:
                pass
            else:
                raise AssertionError(('other Profile received private invalidation', unsolicited))
            other = await command(3, 'djconnect/read', operation='profile/settings', payload={'contract_version': 2})
            assert other['snapshot']['defaults_revision'] == 0
            assert other['snapshot']['defaults'] != expected
            # Actually close/re-authenticate the TLS connection. Reusing a
            # socket for another read alone would not prove reconnect semantics.
            await sockets[1].close()
            sockets[1] = await connect(*participants[1])
            final = await command(1, 'djconnect/read', operation='profile/settings', payload={'contract_version': 2})
            assert final['snapshot']['defaults'] == expected
            assert final['snapshot']['defaults_revision'] == updated['snapshot']['defaults_revision']
            seconds = min(120, max(0, int(os.environ.get('DJC_SETTINGS_SOAK_SECONDS', '0'))))
            soak = {'state': 'NOT_RUN', 'requested_seconds': seconds}
            if seconds:
                from custom_components.djconnect.session_runtime import session_runtime_manager
                manager = session_runtime_manager(hass)
                persistence = manager._settings_repository._persistence
                def counts(tx):
                    return {name: tx.fetchone('SELECT COUNT(*) FROM '+name)[0] for name in (
                        'djconnect_profile_dj_settings', 'djconnect_session_dj_settings',
                        'djconnect_settings_operations', 'djconnect_settings_clock')}
                before_counts = await persistence.async_in_transaction(counts)
                started, reads, reconnects = time.monotonic(), 0, 1
                while time.monotonic() - started < seconds:
                    for index in (0, 1, 2):
                        state = await command(index, 'djconnect/read', operation='profile/settings',
                                              payload={'contract_version': 2})
                        assert state['snapshot']['defaults'] == expected
                        assert state['snapshot']['defaults_revision'] == final['snapshot']['defaults_revision']
                        assert state['snapshot']['session'] is None
                        reads += 1
                    isolated = await command(3, 'djconnect/read', operation='profile/settings',
                                             payload={'contract_version': 2})
                    assert isolated['snapshot']['defaults_revision'] == 0
                    assert isolated['snapshot']['session'] is None
                    if reconnects == 1 and time.monotonic()-started >= seconds/2:
                        await sockets[2].close()
                        sockets[2] = await connect(*participants[2])
                        reconnects += 1
                    await asyncio.sleep(1)
                after_counts = await persistence.async_in_transaction(counts)
                assert before_counts == after_counts, (before_counts, after_counts)
                soak = {'state': 'PASS_CORE_READS_RECONNECT_NO_MUTATION',
                        'seconds': round(time.monotonic()-started, 3), 'owner_reads': reads,
                        'actual_tls_reconnects': reconnects, 'row_counts_before': before_counts,
                        'row_counts_after': after_counts,
                        'process_max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
            return {'case': 'tls_websocket_all_five_no_session_cross_device_invalidation',
                    'matrix': matrix, 'final_revision': final['snapshot']['defaults_revision'],
                    'other_profile_events': 0, 'native': 'NOT_RUN', 'bounded_soak': soak,
                    'reconnect': 'ACTUAL_TLS_CLOSE_PAIR_AUTH_READ_SAME_REVISION',
                    'pairing_scope': 'actual_HTTP_configured_slot_acceptance; explicit_HA_bootstrap_slot_selection; config_flow_UI_NOT_RUN'}
    finally:
        await site.stop()
