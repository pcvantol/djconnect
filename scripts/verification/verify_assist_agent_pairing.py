"""Pinned real HA pipeline/agent setup validation, without inference or audio.

Ordinary pairing wire is unchanged and tested separately. Not an installed,
Apple native, microphone or actual speech qualification.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', '/candidate'))
sys.path.insert(0, str(ROOT))


async def main():
    from homeassistant import auth, loader
    from homeassistant.core import HomeAssistant, CoreState
    from homeassistant.components import conversation, network
    from homeassistant.components.http import HomeAssistantHTTP
    from homeassistant.components.assist_pipeline.pipeline import (
        PipelineStore, STORAGE_VERSION, STORAGE_KEY, STORAGE_VERSION_MINOR,
        KEY_ASSIST_PIPELINE, async_setup_pipeline_store, async_get_pipeline,
    )
    from homeassistant.helpers import area_registry, device_registry, entity_registry, frame
    from custom_components.djconnect.config_flow import _has_valid_assist_pipeline, DJConnectConfigFlow

    with TemporaryDirectory(prefix='djc-agent-pairing-') as temp:
        hass = HomeAssistant(temp)
        hass.state = CoreState.running
        hass.config.language = 'en'
        device_registry.async_setup(hass)
        await device_registry.async_load(hass, load_empty=True)
        await entity_registry.async_load(hass, load_empty=True)
        await area_registry.async_load(hass, load_empty=True)
        hass.auth = await auth.auth_manager_from_config(hass, [{'type': 'homeassistant'}], [])
        hass.http = HomeAssistantHTTP(hass, None, None, None, ['127.0.0.1'], 0, [], 'modern')
        await hass.http.async_initialize(cors_origins=[], use_x_forwarded_for=False,
            login_threshold=-1, is_ban_enabled=False, use_x_frame_options=True)
        hass.config.components.add('http')
        await network.async_setup(hass, {})
        frame.async_setup(hass)
        loader.async_setup(hass)
        try:
            from homeassistant.components.homeassistant.exposed_entities import ExposedEntities, DATA_EXPOSED_ENTITIES
            exposed = ExposedEntities(hass)
            await exposed.async_initialize()
            hass.data[DATA_EXPOSED_ENTITIES] = exposed
            assert await conversation.async_setup(hass, {})
            rows, configured = [], []
            for index, (stt, tts) in enumerate(((None, None), ('stt.synthetic', None),
                    (None, 'tts.synthetic'), ('stt.synthetic', 'tts.synthetic'))):
                configured.append({'id': 'selected-'+str(index), 'name': 'Selected agent route', 'language': 'en',
                    'conversation_engine': conversation.HOME_ASSISTANT_AGENT, 'conversation_language': 'en',
                    'stt_engine': stt, 'stt_language': None, 'tts_engine': tts,
                    'tts_language': None, 'tts_voice': None, 'wake_word_entity': None, 'wake_word_id': None})
            invalid = {**configured[0], 'id': 'missing-agent', 'conversation_engine': 'conversation.absent'}
            empty = {**configured[0], 'id': 'empty-agent', 'conversation_engine': None}
            await PipelineStore(hass, STORAGE_VERSION, STORAGE_KEY,
                minor_version=STORAGE_VERSION_MINOR).async_save({'items': [*configured, invalid, empty],
                                                              'preferred_item': configured[0]['id']})
            await async_setup_pipeline_store(hass)
            store = hass.data[KEY_ASSIST_PIPELINE].pipeline_store
            for index, settings in enumerate(configured):
                selected = settings['id']
                store.async_set_preferred_item(selected)
                assert async_get_pipeline(hass).id == selected
                for selection in ('', selected, 'missing-agent', 'empty-agent', 'absent'):
                    expected = selection in ('', selected)
                    actual = bool(_has_valid_assist_pipeline(hass, selection))
                    assert actual == expected, (selection, actual, expected)
                    rows.append({'speech_configuration': index, 'selection': selection,
                                 'agent_route_valid': actual})
                # Real HA form code, real pipeline and native agent; no agent
                # process method is called and no provider is loaded/started.
                flow = DJConnectConfigFlow()
                flow.hass = hass
                form = await flow.async_step_user()
                assert form['step_id'] == 'user' and form.get('errors') == {}, form
                store.async_set_preferred_item('missing-agent')
                assert not _has_valid_assist_pipeline(hass)
                assert _has_valid_assist_pipeline(hass, selected)
                form = await flow.async_step_user()
                assert form['errors']['base'] == 'assist_pipeline_required'
                rows.append({'speech_configuration': index, 'case': 'broken_preferred_cannot_borrow_valid_other',
                             'form_error': form['errors']['base']})
            result = {'qualification': 'ACTUAL_ISOLATED_HA_PIPELINE_AGENT_AND_USER_FORM',
                'cases': rows, 'agent': 'real HA native conversation agent',
                'model_calls': 0, 'speech_provider_calls': 0,
                'wire_change': False, 'installed': 'NOT_RUN', 'Apple_native': 'NOT_RUN',
                'source_hashes': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                    'custom_components/djconnect/config_flow.py',
                    'scripts/verification/verify_assist_agent_pairing.py')}}
            Path('/lab/assist-agent-pairing.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps({'qualification': result['qualification'], 'cases': len(rows)}))
        finally:
            await hass.async_stop(force=True)


if __name__ == '__main__':
    asyncio.run(main())
