"""Paired actual HA private Bulletin manual speech; RSS/waveform fixtures only.

No installed configuration, credentials, model, external provider or native acceptance.
The actual selected pipeline is created with HA public pipeline/config-entry APIs.
"""
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

from verify_news_bulletin_http import PublicFeedFixture
from verify_session_conversation_history_http import main


async def qualify(hass, manager, history, request, client):
    from aiohttp import ClientSession, TCPConnector, web
    from verify_hybrid_transport_http import tls
    from custom_components.djconnect import api_handlers, pipeline
    from custom_components.djconnect.bulletin_intake import PRIVATE_SOURCES
    from custom_components.djconnect.bulletin_service import (
        async_close_bulletin_service, async_start_bulletin_service,
    )
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    from custom_components.djconnect.session_speech import moment_projection

    async def no_external_music(*args, **kwargs):
        pass

    async def forbidden_model(*args, **kwargs):
        raise AssertionError("private Bulletin used the model transport")

    from verify_session_speech_http import processor_fixture
    from homeassistant.components import websocket_api
    async def already_registered(*args, **kwargs):
        return True  # This extension uses existing HTTP routes, not websocket setup.
    with patch.object(websocket_api, 'async_setup', already_registered):
        processor_server, synthesis_calls = await processor_fixture(hass)
    from homeassistant.components.assist_pipeline.pipeline import KEY_ASSIST_PIPELINE, async_get_pipeline
    from dataclasses import asdict
    runtime = hass.data['djconnect']['runtime']
    original = async_get_pipeline(hass)
    settings = asdict(original)
    settings.pop('id')
    settings.update(language='en', tts_engine='tts.own_piper_fixture', tts_language='en', tts_voice='fixture-en')
    selected = await hass.data[KEY_ASSIST_PIPELINE].pipeline_store.async_create_item(settings)
    hass.config_entries.async_update_entry(runtime.entry, data={**runtime.entry.data, 'assist_pipeline_id':selected.id})
    from custom_components.djconnect.speech_processor import voice_options
    options = voice_options(hass, runtime.config)
    assert options['state'] == 'available', options
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    from custom_components.djconnect.domain.profile.dj_settings import DJSettings
    import uuid
    manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
    before, code = await request('GET', '/api/djconnect/v1/profile/settings', {'contract_version':3})
    assert code == 200, before
    # End any fixture-owned Session before accepting the complete explicit settings.
    existing = manager.current_active('profile-a')
    if existing:
        await manager.async_end(owner_profile_id='profile-a', session_id=existing.session_id)
    before, code = await request('GET', '/api/djconnect/v1/profile/settings', {'contract_version':3})
    chosen, code = await request('PATCH', '/api/djconnect/v1/profile/settings', {
        'contract_version':3, 'binding':before['binding'], 'operation_id':str(uuid.uuid7()),
        'patch':DJSettings().as_dict(), 'expected_defaults_revision':before['snapshot']['defaults_revision'],
        'expected_session':None})
    assert code == 200, chosen
    owner = "profile-a"
    active = manager.current_active(owner)
    if active:
        await manager.async_end(owner_profile_id=owner, session_id=active.session_id)
    with patch.object(api_handlers, "_async_generate_initial_session_moment", no_external_music), \
            patch.object(PlaybackObservationManager, "async_start_spotify", no_external_music):
        body, status = await request("POST", "/api/djconnect/v1/session/start", {"mood": "groove", "locale": "en"})
    assert status == 201, body
    active = manager.current_active(owner)
    sid = active.session_id
    media = "synthetic-private-news-music"
    await manager.async_update_playback_projection(owner_profile_id=owner, session_id=sid,
        state="playing", media_identity=media, title="Synthetic music", artist="Synthetic artist",
        target_name="Synthetic output", position_ms=10000, duration_ms=300000)
    feeds = PublicFeedFixture(PRIVATE_SOURCES)
    try:
        with patch("aiohttp.ClientSession", return_value=feeds), \
                patch.object(pipeline, "_call_conversation_process_transport", side_effect=forbidden_model) as model:
            await async_start_bulletin_service(hass)
            service = hass.data["djconnect"]["bulletin_service"]
            await asyncio.wait_for(service._task, 10)
            assert service.ready(owner, sid) is not None and service.ready("other-owner", sid) is None
            assert not active.broadcast.state.dj_moments
            moment = await manager.async_maybe_publish_intra_track_moment(
                owner_profile_id=owner, session_id=sid, media_identity=media)
            assert moment is not None and moment.moment_type.value == "dj_bulletin"
            assert await manager.async_maybe_publish_intra_track_moment(
                owner_profile_id=owner, session_id=sid, media_identity=media) is None
            assert model.call_count == 0
        assert feeds.calls == [source.url for source in PRIVATE_SOURCES]
        owner_view, status = await request("GET", "/api/djconnect/v1/session/active")
        assert status == 200 and moment.moment_id in json.dumps(owner_view)
        payload = moment.as_dict()
        assert payload["visibility"] == "owner_only" and payload["delivery_channels"] == ["owner"]
        assert "Tweakers: " in moment.content and "NU.nl: " in moment.content
        assert "explicitly synthetic metadata" not in moment.content
        speech = moment_projection(active.broadcast, moment, autoplay=True)
        assert speech['manual_allowed'] and speech['processors'] == ['local_on_device','ha_configured']
        assert not speech['autoplay_eligible']
        reference = {'session_id':sid, 'moment_id':moment.moment_id}
        prepared, code = await request('POST', '/api/djconnect/v1/speech/prepare', {
            'contract_version':3, 'intent':'manual', 'target':'local',
            'processor':'ha_configured', 'reference':reference})
        assert code == 200, prepared
        assert prepared['session_speech']['audio_state'] == 'ready', prepared
        assert synthesis_calls == [moment.content], synthesis_calls
        again, again_code = await request('POST', '/api/djconnect/v1/speech/prepare', {
            'contract_version':3, 'intent':'manual', 'target':'local',
            'processor':'ha_configured', 'reference':reference})
        assert again_code == 200 and again['session_speech']['audio_state'] == 'ready', again
        assert len(synthesis_calls) == 1
        automatic, auto_code = await request('POST', '/api/djconnect/v1/speech/prepare', {
            'contract_version':3, 'intent':'automatic', 'target':'local',
            'processor':'ha_configured', 'reference':reference})
        assert auto_code == 200 and automatic['session_speech']['reason'] == 'source_processor_not_qualified', automatic
        assert len(synthesis_calls) == 1
        local, local_code = await request('POST', '/api/djconnect/v1/speech/prepare', {
            'contract_version':3, 'intent':'manual', 'target':'local',
            'processor':'local_on_device', 'reference':reference})
        assert local_code == 200 and local['session_speech']['audio_state'] == 'renderer_pending', local
        import os
        Path(os.environ['DJC_LAB_ROOT'],'bulletin-manual-ha-tts.json').write_text(json.dumps({
            'fresh_original_private_bulletin':True, 'settings_contract':3,
            'ha_configured_reply':prepared, 'local_on_device_reply':local,
            'automatic_refused':automatic, 'repeat_same_asset':again['session_speech']['audio_reference']==prepared['session_speech']['audio_reference'],
            'synthetic_wyoming_synthesis_calls':len(synthesis_calls),
            'model_provider_calls':0, 'real_external_provider_calls':0,
            'installed_mutations':0, 'http_prepare_route':'actual_paired_HA'},indent=2))

        server_ssl, client_ssl = tls(Path(hass.config.config_dir))
        site = web.TCPSite(client.server.runner, "127.0.0.1", 0, ssl_context=server_ssl)
        await site.start()
        try:
            port = site._server.sockets[0].getsockname()[1]
            url = (f"https://127.0.0.1:{port}/api/djconnect/v1/session/broadcast/ws/{sid}"
                   f"?broadcast_token={active.broadcast.broadcast_token}")
            async with ClientSession(connector=TCPConnector(ssl=client_ssl)) as viewer:
                async with viewer.ws_connect(url) as ws:
                    shared = await asyncio.wait_for(ws.receive_json(), 10)
            assert shared["type"] == "snapshot" and moment.moment_id not in json.dumps(shared)
        finally:
            await site.stop()
        from custom_components.djconnect.dj_response import get_private_tts_audio
        asset = prepared['session_speech']['audio_reference']['asset_id']
        from custom_components.djconnect import speech_processor
        from custom_components.djconnect.dj_response import invalidate_private_speech_sources
        invalidate_private_speech_sources(hass, session_id=sid)
        original_synthesize = speech_processor.synthesize
        async def withdrawn_after_waveform(*args, **kwargs):
            waveform = await original_synthesize(*args, **kwargs)
            await async_close_bulletin_service(hass)
            return waveform
        with patch.object(speech_processor, 'synthesize', withdrawn_after_waveform):
            withdrawn, withdrawn_code = await request('POST', '/api/djconnect/v1/speech/prepare', {
                'contract_version':3, 'intent':'manual', 'target':'local',
                'processor':'ha_configured', 'reference':reference})
        assert withdrawn_code == 404 and not withdrawn['success'], withdrawn
        assert len(synthesis_calls) == 2
        try:
            get_private_tts_audio(hass, asset, owner)
        except PermissionError:
            pass
        else:
            raise AssertionError('withdrawn Bulletin audio remained usable')
        return {"state": "PASS", "manual_ha_synthesis_calls":len(synthesis_calls), "late_source_withdrawal_discards_waveform":True, "automatic_ha_denied":True, "source_withdrawal_audio_denied":True, "external_RSS_calls": 0, "model_provider_calls": 0,
                "installed_or_native_acceptance": "NOT_RUN", "visibility": payload["visibility"],
                "speech_processors": speech["processors"], "shared_tls_snapshot_excludes_moment": True}
    finally:
        processor_server.close()
        await processor_server.wait_closed()
        await async_close_bulletin_service(hass)
        await manager.async_end(owner_profile_id=owner, session_id=sid)


if __name__ == "__main__":
    asyncio.run(main(qualification_extension=qualify))
