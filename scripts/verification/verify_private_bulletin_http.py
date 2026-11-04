"""Qualify the private headline route in paired HA using synthetic RSS bytes."""
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

    owner = "profile-a"
    active = manager.current_active(owner)
    if active:
        await manager.async_end(owner_profile_id=owner, session_id=active.session_id)
    with patch.object(api_handlers, "_async_generate_initial_session_moment", no_external_music), \
            patch.object(PlaybackObservationManager, "async_start_spotify", no_external_music):
        body, status = await request("POST", "/api/djconnect/v1/session/start", {"mood": "groove", "locale": "nl"})
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
        assert speech["manual_allowed"] and speech["processors"] == ["local_on_device"]
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
        return {"state": "PASS", "external_RSS_calls": 0, "model_provider_calls": 0,
                "installed_or_native_acceptance": "NOT_RUN", "visibility": payload["visibility"],
                "speech_processors": speech["processors"], "shared_tls_snapshot_excludes_moment": True}
    finally:
        await async_close_bulletin_service(hass)
        await manager.async_end(owner_profile_id=owner, session_id=sid)


if __name__ == "__main__":
    asyncio.run(main(qualification_extension=qualify))
