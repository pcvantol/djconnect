"""Owned loopback browser adapter; real ordinary-owner requests, synthetic music."""

from __future__ import annotations

import asyncio
import json
import os
import ssl
from pathlib import Path

from aiohttp import web


def register(hass, manager, clock):
    """Register bounded fixture inputs before freezing the actual HA router."""
    from custom_components.djconnect.session_facts import catalog_facts

    lab = Path(os.environ["DJC_LAB_ROOT"])
    ha_port, cast_port = 18203, 18204
    state = {}

    async def setup(request):
        await manager.async_end(owner_profile_id="profile-a")
        session = await manager.async_start(
            owner_profile_id="profile-a",
            selected_mood="groove",
            locale="nl",
            elapsed_time_source=clock.monotonic,
        )
        state["session_id"] = session.session_id
        return web.json_response(
            {
                "kind": "vibecast_handoff",
                "version": 1,
                "session_id": session.session_id,
                "broadcast_token": session.broadcast.broadcast_token,
                "ha_url": f"https://localhost:{ha_port}",
                "locale": "nl",
            }
        )

    async def mood(request):
        active = await manager.async_get_active("profile-a")
        response = await state["client"].post(
            "/api/djconnect/v1/session/mood",
            headers=state["headers"],
            json={
                **state["identity"],
                "contract_version": 1,
                "session_id": active.session_id,
                "selected_mood": request.query["value"],
                "expected_mood_revision": active.mood_revision,
            },
        )
        data = await response.json()
        assert response.status == 200
        return web.json_response(data)

    async def publish(request):
        number = int(request.query["number"])
        active = await manager.async_get_active("profile-a")
        clock.advance(300)
        catalog = {
            "uri": "spotify:track:" + chr(65 + number) * 22,
            "title": f"Synthetic recording {number}",
            "artist": "Synthetic artist",
            "album_name": f"Synthetic edition {number}",
            "album_uri": "spotify:album:" + chr(65 + number) * 22,
            "release_date": "2001-03-04",
            "release_date_precision": "day",
        }
        await manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=active.session_id,
            state="playing",
            media_identity=catalog["uri"],
            title=catalog["title"],
            artist=catalog["artist"],
            album=catalog["album_name"],
            duration_ms=300000,
            position_ms=0,
        )

        async def insight():
            return {"_qualified_facts": tuple(catalog_facts(catalog))}

        moment = await manager.async_process_track_started(
            owner_profile_id="profile-a",
            session_id=active.session_id,
            media_identity=catalog["uri"],
            insight_provider=insight,
            require_current_playback=True,
            allow_initial_facts=True,
        )
        assert moment is not None
        return web.json_response(
            {"moment": moment.as_dict(), "snapshot": active.broadcast.as_dict(include_owner_only=False)}
        )

    async def snapshot(request):
        active = await manager.async_get_active("profile-a")
        return web.json_response(active.broadcast.as_dict(include_owner_only=False))

    async def end(request):
        ended = await manager.async_end(
            owner_profile_id="profile-a", session_id=state["session_id"]
        )
        return web.json_response({"ended": ended is not None})

    for name, handler in [
        ("setup", setup),
        ("mood", mood),
        ("publish", publish),
        ("snapshot", snapshot),
        ("end", end),
    ]:
        hass.http.app.router.add_get("/__mood_lab/" + name, handler)

    async def serve(client, identity, headers):
        state.update(client=client, identity=identity, headers=headers)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(lab / "server.pem", lab / "server-key.pem")
        local = web.TCPSite(client.server.runner, "127.0.0.1", ha_port, ssl_context=tls)
        await local.start()
        static = web.Application()

        async def index(request):
            return web.Response(
                text=(lab / "build/cast/index.html").read_text(),
                content_type="text/html",
                headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
            )

        static.router.add_get("/", index)
        runner = web.AppRunner(static)
        await runner.setup()
        await web.TCPSite(runner, "127.0.0.1", cast_port, ssl_context=tls).start()
        (lab / "browser-ready.json").write_text(json.dumps({"local": ha_port, "cast": cast_port}))
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
            await local.stop()

    return serve
