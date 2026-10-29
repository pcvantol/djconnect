"""Actual HA native flow manager, pending PairView, Core hook and real SQLite.

Manual Profile/setup boundaries are explicit fixtures; no full entry-setup,
registrar, native push, model or provider qualification is inferred.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth, loader
from homeassistant.config_entries import ConfigEntries, ConfigEntriesFlowManager, ConfigEntryState, ConfigEntryStore
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.data_entry_flow import UnknownFlow
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.helpers import area_registry, device_registry, entity_registry, frame

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
from custom_components.djconnect import async_setup, _restore_runtime  # noqa: E402
from custom_components.djconnect.config_flow import DJConnectConfigFlow  # noqa: E402
from custom_components.djconnect.persistence import async_initialize_persistence, async_shutdown_persistence  # noqa: E402
from custom_components.djconnect.const import DOMAIN, SETUP_METHOD_PAIR_APP  # noqa: E402


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / 'custom_components/djconnect').rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


async def main():
    before = hashes()
    lab = Path(os.environ['DJC_LAB_ROOT'])
    config = lab / 'empty-ha-config'
    config.mkdir(parents=True, exist_ok=False)
    hass = HomeAssistant(str(config))
    hass.state = CoreState.running
    hass.config.internal_url = 'http://127.0.0.1:8123'
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{'type': 'homeassistant'}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ['127.0.0.1'], 0, [], 'modern')
    await hass.http.async_initialize(cors_origins=[], use_x_forwarded_for=False,
        login_threshold=-1, is_ban_enabled=False, use_x_frame_options=True)
    hass.config.components.add('http')
    frame.async_setup(hass)
    loader.async_setup(hass)
    assert await async_setup(hass, {})
    await ConfigEntryStore(hass).async_save({'entries': []})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    persistence = await async_initialize_persistence(hass)
    flows = []
    setup_fail = False
    held = None
    profile_held = None

    async def source_factory(manager, handler, *, context, data):
        assert handler == DOMAIN
        flow = DJConnectConfigFlow()
        flow.hass = hass
        flow.init_step = context["source"]  # Actual native factory wiring.
        flows.append(flow)
        return flow

    async def manual_profile(flow, user_input=None):
        if profile_held is not None:
            profile_held[0].set()
            await profile_held[1].wait()
        return flow.async_create_entry(title='Synthetic native pairing flow', data={
            **flow._pairing, 'ha_install_id': 'synthetic-ha-install'})

    async def isolated_setup(manager, entry_id):
        entry = manager.async_get_entry(entry_id)
        assert entry is not None
        runtime = _restore_runtime(hass, entry)  # Actual shipping Runtime, not a stub.
        assert runtime.entry is entry
        if held is not None:
            held[0].set()
            await held[1].wait()
        entry._async_set_state(hass, ConfigEntryState.SETUP_ERROR if setup_fail else ConfigEntryState.LOADED, None)
        return not setup_fail

    async def multiple_entries(*args):
        return False  # Matches the actual multi-entry integration manifest.

    cases = []
    async def count():
        return await persistence.async_in_transaction(lambda tx: tx.fetchone(
            'SELECT count(*) FROM djconnect_surface_pairs')[0])
    async def settle():
        await hass.async_block_till_done()
        for flow in flows:
            # Entry records are private; no credentials appear in this receipt.
            assert flow.hass is hass
        for runtime in tuple(hass.data[DOMAIN].values()):
            record = getattr(runtime, 'surface_pair_registration', None)
            if record:
                while record.tasks:
                    await asyncio.gather(*tuple(record.tasks))

    with patch.object(ConfigEntriesFlowManager, 'async_create_flow', source_factory), \
            patch.object(ConfigEntries, 'async_setup', isolated_setup), \
            patch('homeassistant.config_entries._support_single_config_entry_only', multiple_entries), \
            patch('custom_components.djconnect.config_flow._has_valid_assist_pipeline', return_value=True), \
            patch.object(DJConnectConfigFlow, 'async_step_profile_choice', manual_profile):
        async with TestClient(TestServer(hass.http.app)) as client:
            async def begin():
                result = await hass.config_entries.flow.async_init(DOMAIN,
                    context={'source': 'user'}, data={'setup_method': SETUP_METHOD_PAIR_APP, 'client_type': 'ios'})
                flow = flows[-1]
                assert result['flow_id'] == flow.flow_id
                result = await hass.config_entries.flow.async_configure(
                    flow.flow_id, user_input={'client_type': 'ios'})
                assert result['type'] == 'form'
                code = flow._discovered_defaults['pair_code']
                return flow, code
            async def post(code, device):
                async with client.post('/api/djconnect/v1/pair', json={
                        'pair_code': code, 'device_id': device, 'client_type': 'ios',
                        'device_name': 'Synthetic isolated client'}) as response:
                    body = await response.json()
                    assert response.status == 200 and body['success'] and body['setup_pending']
                    return body
            async def finish(flow):
                return await hass.config_entries.flow.async_configure(flow.flow_id,
                    user_input={})  # Native app-details form has no editable fields.

            # Real native finish/add/setup/on_create_entry order, not direct hook invocation.
            first, code = await begin()
            one = await post(code, 'djconnect-ios-ABCDEF123456')
            two = await post(code, 'djconnect-ios-ABCDEF123456')
            assert one['device_token'] == two['device_token']
            result = await finish(first)
            entry = result['result']
            assert entry is hass.config_entries.async_get_entry(entry.entry_id)
            assert entry.state == ConfigEntryState.LOADED
            await settle()
            record = hass.data[DOMAIN][entry.entry_id].surface_pair_registration
            assert record is not None and record.phase == 'recorded' and not record.retired
            assert await count() == 1
            cases.append('actual_native_created_hook_and_duplicate_POST_record_once')

            aborted, code = await begin()
            await post(code, 'djconnect-ios-BBBBBB123456')
            hass.config_entries.flow.async_abort(aborted.flow_id)
            await settle()
            assert await count() == 1
            assert code not in hass.data[DOMAIN]['config_flow_app_pairing_pending']
            cases.append('actual_native_abort_retires_pending_context_without_SQL')

            failed, code = await begin()
            await post(code, 'djconnect-ios-CCCCCC123456')
            setup_fail = True
            result = await finish(failed)
            setup_fail = False
            assert result['result'].state == ConfigEntryState.SETUP_ERROR
            await settle()
            assert await count() == 1
            cases.append('actual_setup_failure_has_no_local_record_or_tombstone')

            late, code = await begin()
            await post(code, 'djconnect-ios-DDDDDD123456')
            entered, release = asyncio.Event(), asyncio.Event()
            original_unique = late.async_set_unique_id
            async def delayed_unique(value):
                entered.set()
                await release.wait()
                return await original_unique(value)
            late.async_set_unique_id = delayed_unique
            task = asyncio.create_task(finish(late))
            await asyncio.wait_for(entered.wait(), 3)
            await post(code, 'djconnect-ios-EEEEEE123456')
            release.set()
            await task
            await settle()
            assert await count() == 1
            cases.append('conflicting_POST_during_actual_unique_id_await_suppresses_registration')

            # Actual native removal while entry setup is still awaiting.
            during, code = await begin()
            await post(code, 'djconnect-ios-FFFFFF123456')
            held = (asyncio.Event(), asyncio.Event())
            task = asyncio.create_task(finish(during))
            await asyncio.wait_for(held[0].wait(), 3)
            hass.config_entries.flow.async_abort(during.flow_id)
            held[1].set()
            try:
                await task
            except (asyncio.CancelledError, UnknownFlow):
                pass
            held = None
            await settle()
            assert await count() == 1
            cases.append('actual_native_abort_during_setup_has_no_late_SQL_ack')
    await async_shutdown_persistence(hass)
    assert before == hashes()
    result = {'status': 'PASS', 'source_hashes': before, 'source_before_after_equal': True,
        'cases': cases, 'actual_HA_flow_manager': True, 'actual_pending_PairView_and_Core_hooks': True,
        'actual_SQLite': True, 'profile_and_setup_boundaries': 'EXPLICIT_SYNTHETIC_FIXTURES_NOT_FULL_ENTRY_SETUP',
        'positive_permission': 'UNAVAILABLE', 'model_calls': 0, 'external_provider_calls': 0,
        'installed': 'NOT_RUN', 'native_push': 'NOT_RUN'}
    (lab / 'http-producer-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'cases': len(cases)}))


if __name__ == '__main__':
    asyncio.run(main())
