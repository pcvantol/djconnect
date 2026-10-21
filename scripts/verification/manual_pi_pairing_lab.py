"""Real HA ConfigFlow and loopback device boundary, never physical pairing."""
from __future__ import annotations

import copy
import asyncio
import hashlib
import json
import time
from uuid import uuid4

from aiohttp import web
from aiohttp.test_utils import TestServer
from homeassistant.data_entry_flow import AbortFlow


async def run(hass, runtime, storage):
    from homeassistant import loader
    from homeassistant.components.assist_pipeline.pipeline import KEY_ASSIST_PIPELINE
    from homeassistant.components.conversation.const import HOME_ASSISTANT_AGENT
    from homeassistant.setup import async_setup_component
    from custom_components.djconnect.config_flow import (
        DJConnectConfigFlow, DJConnectOptionsFlow, PROFILE_PLATFORM_ACTION_FIELD,
        _async_pair_before_create, _has_valid_assist_pipeline,
    )
    from custom_components.djconnect.domain.storage import ProfilePlatformStorage
    from verify_session_conversation_history_http import entry

    # Existing transport probes did not exercise ConfigFlow's real setup gate.
    # Register HA's local built-in agent; do not mock or relax that admission.
    loader.async_setup(hass)
    assert await async_setup_component(hass, 'homeassistant', {})
    assert await async_setup_component(hass, 'conversation', {})
    pipeline = await hass.data[KEY_ASSIST_PIPELINE].pipeline_store.async_create_item({
        'name': 'Owned local conversation setup admission', 'language': 'en',
        'conversation_engine': HOME_ASSISTANT_AGENT, 'conversation_language': 'en',
        'stt_engine': None, 'stt_language': None, 'tts_engine': None,
        'tts_language': None, 'tts_voice': None, 'wake_word_entity': None, 'wake_word_id': None})
    assert _has_valid_assist_pipeline(hass, pipeline.id)

    identity = 'djconnect-raspberry-pi-A1B2C3D4E5F6'
    original = {'device_id': identity, 'client_type': 'raspberry_pi', 'pair_code': '654321',
                'local_url': 'http://unrelated-advertisement.invalid:18080'}
    state = {'mode': 'normal', 'info': original.copy(), 'gets': 0, 'redirect_targets': 0, 'posts': []}

    async def info(request):
        state['gets'] += 1
        if state['mode'] == 'redirect':
            raise web.HTTPFound('/redirect-target')
        if state['mode'] == 'slow_body':
            response = web.StreamResponse(headers={'Content-Type': 'application/json'})
            await response.prepare(request)
            await asyncio.sleep(3.2)
            try:
                await response.write(json.dumps(state['info']).encode())
                await response.write_eof()
            except ConnectionResetError:
                pass  # The production whole-probe deadline already closed it.
            return response
        body = json.dumps({**state['info'], **({'padding': 'x' * 17000}
                                             if state['mode'] == 'oversize' else {})}).encode()
        if state['mode'] == 'chunked_suffix':
            response = web.StreamResponse(headers={'Content-Type': 'application/json'})
            await response.prepare(request)
            await response.write(json.dumps(state['info']).encode())
            # A valid JSON prefix alone is not a complete bounded response.
            await asyncio.sleep(.02)
            await response.write(b' ' * 17000)
            await response.write_eof()
            return response
        return web.Response(body=body, content_type='application/json')

    async def redirect_target(request):
        state['redirect_targets'] += 1
        return web.json_response(state['info'])

    async def pair(request):
        body = await request.json()
        assert body['device_id'] == identity and body['client_type'] == 'raspberry_pi'
        assert body['pair_code'] == original['pair_code'] and body['ha_local_url']
        assert body['device_token'] and not any(k in body for k in (
            'spotify_refresh_token', 'spotify_client_id', 'refresh_token'))
        state['posts'].append({'device_id': body['device_id'], 'client_type': body['client_type'],
            'token_sha256': hashlib.sha256(body['device_token'].encode()).hexdigest()})
        return web.json_response({'success': True, 'device_id': identity,
                                 'client_type': 'raspberry_pi', 'paired': True})

    app = web.Application()
    app.router.add_get('/api/device/pairing-info', info)
    app.router.add_get('/redirect-target', redirect_target)
    app.router.add_post('/api/device/pair', pair)
    server = TestServer(app)
    await server.start_server()
    endpoint = str(server.make_url('/')).rstrip('/')
    saved_internal = hass.config.internal_url
    hass.config.internal_url = 'http://127.0.0.1:8123'
    profiles_before = copy.deepcopy(storage.household.profiles)
    cases = []

    def flow():
        value = DJConnectConfigFlow()
        value.hass = hass
        value.context = {'source': 'user'}
        value.handler = 'djconnect'
        value.flow_id = uuid4().hex
        value._discovered_defaults = {'assist_pipeline_id': pipeline.id}
        # This probe deliberately models no mDNS result, not a device identity.
        value._discovery_checked = True
        return value

    async def submit(value):
        selected = await value.async_step_pair_local_device_type({'client_type': 'raspberry_pi'})
        assert selected['type'] == 'form' and selected['step_id'] == 'pair_local_device_details'
        return await value.async_step_pair_local_device_details({
            'pair_code': original['pair_code'], 'device_name': 'Synthetic manual Pi',
            'local_url': endpoint})

    try:
        # A historical code-derived row must never masquerade as this configured
        # Pi merely because both display names happen to be the same.
        await storage.async_upsert_device('djconnect-030549', 'raspberry_pi',
            display_name='Synthetic configured Pi', linked_profile_id='profile-b')
        legacy_entry = entry('manual-pi-options', {'device_id': identity,
            'client_type': 'raspberry_pi', 'device_name': 'Synthetic configured Pi'})
        options = DJConnectOptionsFlow(legacy_entry)
        options.hass = hass
        options.context = {'source': 'user'}
        options.handler = legacy_entry.entry_id
        options.flow_id = uuid4().hex
        before_options = storage.household
        form = await options.async_step_profile_platform()
        assert storage.household == before_options and identity not in storage.household.devices
        schema = form['data_schema'].schema
        device_key = next(k for k in schema if k.schema == 'device_id')
        profile_key = next(k for k in schema if k.schema == 'profile_id')
        assert profile_key.default() == ''  # No inferred Profile selection.
        labels = schema[device_key].container
        assert identity in labels[identity] and 'djconnect-030549' in labels['djconnect-030549']
        chosen = form['data_schema']({PROFILE_PLATFORM_ACTION_FIELD: 'link_device', 'profile_id': 'profile-a'})
        assert chosen['device_id'] == identity and chosen['client_type'] == 'raspberry_pi'
        linked = await options.async_step_profile_platform(chosen)
        assert linked['type'] == 'create_entry'
        stored = await ProfilePlatformStorage(hass).async_load()
        assert stored.devices[identity].linked_profile_id == 'profile-a'
        assert stored.devices['djconnect-030549'].linked_profile_id == 'profile-b'
        assert stored.profiles == profiles_before and not state['posts']
        cases.append({'case': 'actual_HA_configured_identity_options_and_explicit_profile_choice',
                      'render_mapping_writes': 0, 'exact_ids_visible': True,
                      'implicit_profile_choice': False, 'durable_explicit_device_link': True,
                      'legacy_row_untouched': True, 'pair_posts': 0})
        for mode, changes in (
            ('normal', {'device_id': 'djconnect-654321'}),
            ('normal', {'client_type': 'windows'}),
            ('normal', {'pair_code': '111111'}),
            ('oversize', {}), ('chunked_suffix', {}), ('redirect', {}), ('slow_body', {}),
        ):
            state.update(mode=mode, info={**original, **changes})
            candidate = flow()
            began = time.monotonic()
            rejected = await submit(candidate)
            elapsed = time.monotonic() - began
            if mode == 'slow_body':
                assert elapsed < 6, 'Manual endpoint body escaped the whole-probe deadline'
            assert rejected['type'] == 'form'
            assert rejected['errors']['base'] == 'pairing_info_unavailable', rejected
            assert not candidate._pairing and not state['posts']
            cases.append({'case': 'preflight_rejected', 'mode': mode,
                          'changed_fields': sorted(changes), 'pair_posts': 0,
                          'elapsed_seconds': elapsed})
        assert state['redirect_targets'] == 0
        state.update(mode='normal', info=original.copy())
        existing_unique_id = runtime.entry.unique_id
        hass.config_entries.async_update_entry(runtime.entry, unique_id=identity)
        try:
            try:
                await submit(flow())
            except AbortFlow as exc:
                assert exc.reason == 'already_configured'
            else:
                raise AssertionError('Manual endpoint bypassed real HA duplicate identity check')
        finally:
            hass.config_entries.async_update_entry(runtime.entry, unique_id=existing_unique_id)
        assert not state['posts']
        cases.append({'case': 'actual_HA_duplicate_identity_rejected', 'pair_posts': 0})

        candidate = flow()
        accepted = await submit(candidate)
        assert accepted['type'] == 'form' and accepted['step_id'] == 'profile_choice'
        assert candidate.unique_id == identity
        assert candidate._pairing['device_id'] == identity
        assert candidate._pairing['client_type'] == 'raspberry_pi'
        assert candidate._pairing['local_url'] == endpoint
        assert storage.household.profiles == profiles_before
        # The same ordinary pre-create owner must recheck identity before POST.
        for changed in ({'device_id': 'djconnect-raspberry-pi-111111111111'},
                        {'client_type': 'macos'}, {'pair_code': ''}):
            state['info'] = {**original, **changed}
            try:
                await _async_pair_before_create(hass, dict(candidate._pairing))
            except RuntimeError:
                pass
            else:
                raise AssertionError('Endpoint identity/code changed after preflight')
            assert not state['posts']
            cases.append({'case': 'last_pair_owner_rejected_changed_endpoint',
                          'changed_fields': sorted(changed), 'pair_posts': 0})
        state['info'] = original.copy()
        pairing = dict(candidate._pairing)
        pairing['assist_pipeline_id'] = pipeline.id
        started = time.monotonic()
        await _async_pair_before_create(hass, pairing)
        assert len(state['posts']) == 1
        assert pairing['device_id'] == identity and pairing['local_url'] == endpoint
        assert storage.household.profiles == profiles_before
        cases.append({'case': 'actual_HA_manual_type_details_profile_choice_and_normal_pair_owner',
                      'pair_posts': 1, 'client_type': 'raspberry_pi',
                      'stable_identity_preserved': True, 'submitted_endpoint_preserved': True,
                      'existing_profiles_unchanged': True, 'elapsed_seconds': time.monotonic() - started})
        return {'case': 'manual_pi_pairing_without_mdns', 'result': 'PASS_REAL_HA_FLOW_LOOPBACK_DEVICE',
                'cases': cases, 'pairing_info_gets': state['gets'], 'pair_posts': len(state['posts']),
                'redirect_targets': state['redirect_targets'],
                'boundaries': {'device_server': 'synthetic loopback boundary',
                    'HA_ConfigFlow_unique_id_and_Profile_choice': 'production real HA',
                    'HA_device_pair_owner': 'production real HA', 'native_UI': 'NOT_RUN',
                    'physical_pairing': 'NOT_RUN', 'installed': 'NOT_RUN', 'paid_model_attempts': 0}}
    finally:
        hass.config.internal_url = saved_internal
        await server.close()
