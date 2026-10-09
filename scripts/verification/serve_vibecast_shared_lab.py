"""Isolated real HA/Runtime/Broadcast lab, with synthetic qualified source input.

No HA-dev config, provider calls or production credentials. Start only in the
bounded disposable renderer container; TLS/browser trust is local to its profile.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import hashlib
import os
from pathlib import Path
import ssl
import sys

from aiohttp import web
from homeassistant.helpers import device_registry, entity_registry, area_registry
from homeassistant import auth
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components.http import HomeAssistantHTTP

ROOT = Path(os.environ["DJC_SOURCE_ROOT"])
sys.path.insert(0, str(ROOT))
from custom_components.djconnect import register_http_views  # noqa: E402
from custom_components.djconnect.broadcast_handoff import broadcast_handoff_manager  # noqa: E402
from custom_components.djconnect.session_runtime import (  # noqa: E402
    SessionRuntimeManager,
    SessionStartStrategy,
    SessionDirectionType,
    DJPersona,
)
from custom_components.djconnect.session_facts import recording_facts, catalog_facts  # noqa: E402


async def main():
    lab = Path(os.environ["DJC_LAB_ROOT"])
    ha_port = int(os.environ.get("DJC_HA_PORT", "18193"))
    cast_port = int(os.environ.get("DJC_CAST_PORT", "18194"))
    config = lab / "config"
    config.mkdir(exist_ok=True)
    hass = HomeAssistant(str(config))
    hass.state = CoreState.running
    hass.config.language = "nl"
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], ha_port, [], "modern")
    await hass.http.async_initialize(
        cors_origins=[f"https://localhost:{cast_port}"],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    now = [100.0]
    manager = SessionRuntimeManager(monotonic_source=lambda: now[0])
    hass.data["djconnect"] = {"session_runtime_manager": manager}
    from custom_components.djconnect.http import DJConnectImageProxyView

    async def synthetic_art(self, request, token):
        # Synthetic image-provider adapter only; real HA route remains registered.
        return web.Response(
            text='<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="#493768"/><circle cx="300" cy="300" r="210" fill="#bb87ae"/></svg>',
            content_type="image/svg+xml",
        )

    DJConnectImageProxyView.get = synthetic_art
    register_http_views(hass)
    source_hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "custom_components/djconnect").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    state = {"session": None, "receipts": []}

    async def setup(request):
        old = state["session"]
        if old:
            await manager.async_end(owner_profile_id="synthetic-owner", session_id=old.session_id)
        lang = request.query.get("lang", "nl")
        session = await manager.async_start(
            owner_profile_id="synthetic-owner",
            locale=lang,
            music_backend="spotify_direct",
            dj_persona=DJPersona.RADIO_DJ,
            session_start_strategy=SessionStartStrategy.DISCOVER,
        )
        session = replace(
            session,
            session_direction=replace(
                session.session_direction, direction=SessionDirectionType.EXPLORING
            ),
        )
        manager._active_by_profile[session.owner_profile_id] = session
        state.update(session=session, receipts=[])
        return web.json_response(
            {
                "session_id": session.session_id,
                "broadcast_token": session.broadcast.broadcast_token,
                "kind": "vibecast_handoff",
                "version": 1,
                "ha_url": f"https://localhost:{ha_port}",
                "locale": lang,
            },
            headers={"Cache-Control": "no-store"},
        )

    async def publish(request):
        number = int(request.query.get("number", "0"))
        session = await manager.async_get_active("synthetic-owner")
        if not session:
            return web.json_response({"error": "no_session"}, status=409)
        now[0] += 40
        catalog = {
            "uri": "spotify:track:" + chr(65 + number) * 22,
            "title": f"Recording {number}",
            "artist": f"Artist {number}",
            "album_name": "Synthetic edition",
            "album_uri": "spotify:album:" + "C" * 22,
            "isrc": "USABC0100001",
            "release_date": "2001-03-04",
            "release_date_precision": "day",
        }
        await manager.async_update_playback_projection(
            owner_profile_id=session.owner_profile_id,
            session_id=session.session_id,
            state="playing",
            media_identity=catalog["uri"],
            title=catalog["title"],
            artist=catalog["artist"],
            album=catalog["album_name"],
            duration_ms=300000,
            position_ms=0,
            artwork_url="/api/djconnect/v1/image_proxy/software-art",
        )
        recording = {
            "id": f"00000000-0000-0000-0000-{number + 1:012d}",
            "title": catalog["title"],
            "artist-credit": [{"artist": {"name": catalog["artist"]}}],
            "relations": [
                {
                    "type": "producer",
                    "target-type": "artist",
                    "attributes": [],
                    "artist": {"id": "00000000-0000-0000-0000-000000000008", "name": "Producer 8"},
                }
            ],
        }

        async def insight():
            return {
                "_qualified_facts": tuple(recording_facts(catalog, recording))
                + (tuple(catalog_facts(catalog)) if number else ())
            }

        moment = await manager.async_process_track_started(
            owner_profile_id=session.owner_profile_id,
            session_id=session.session_id,
            media_identity=catalog["uri"],
            insight_provider=insight,
            require_current_playback=True,
            allow_initial_facts=True,
        )
        state["receipts"].append(moment.as_dict() if moment else None)
        return web.json_response(
            {
                "moment": moment.as_dict() if moment else None,
                "snapshot": session.broadcast.as_dict(include_owner_only=False),
            },
            headers={"Cache-Control": "no-store"},
        )

    async def approve(request):
        session = state["session"]
        claim = request.query["code"]
        ok = await broadcast_handoff_manager(hass).approve(
            claim,
            owner_profile_id=session.owner_profile_id,
            session_id=session.session_id,
            broadcast_token=session.broadcast.broadcast_token,
        )
        return web.json_response({"success": bool(ok)})

    async def action(request):
        session = state["session"]
        name = request.query["name"]
        if name == "end":
            await manager.async_end(
                owner_profile_id=session.owner_profile_id, session_id=session.session_id
            )
        elif name == "later":
            now[0] += 40
            await manager.async_update_playback_projection(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                state="playing",
                media_identity="spotify:track:" + "B" * 22,
                title="Recording 1",
                artist="Artist 1",
                album="Synthetic edition",
                duration_ms=300000,
                position_ms=40000,
                artwork_url="/api/djconnect/v1/image_proxy/software-art",
            )
            moment = await manager.async_maybe_publish_intra_track_moment(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                media_identity="spotify:track:" + "B" * 22,
            )
            return web.json_response(
                {"success": True, "moment": moment.as_dict() if moment else None}
            )
        elif name == "pause":
            await manager.async_update_playback_projection(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                state="paused",
                media_identity="spotify:track:" + "B" * 22,
                title="Recording 1",
                artist="Artist 1",
                duration_ms=300000,
                position_ms=10000,
            )
        elif name == "seek":
            await manager.async_update_playback_projection(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                state="playing",
                media_identity="spotify:track:" + "B" * 22,
                title="Recording 1",
                artist="Artist 1",
                duration_ms=300000,
                position_ms=220000,
            )
        return web.json_response({"success": True})

    async def art(request):
        return web.Response(
            text='<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="#493768"/><circle cx="300" cy="300" r="210" fill="#bb87ae"/></svg>',
            content_type="image/svg+xml",
        )

    for path, handler in [
        ("setup", setup),
        ("publish", publish),
        ("approve", approve),
        ("action", action),
        ("art.svg", art),
    ]:
        hass.http.app.router.add_get("/__lab/" + path, handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(lab / "server.pem", lab / "server-key.pem")

    async def before(request):
        return web.Response(
            text=(lab / "before.html").read_text(),
            content_type="text/html",
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )

    # Registered before router freeze, below.
    hass.http.app.router.add_get("/__lab/before", before)
    runner = web.AppRunner(hass.http.app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", ha_port, ssl_context=tls).start()
    static = web.Application()

    async def index(request):
        return web.Response(
            text=(lab / "build/cast/index.html").read_text(),
            content_type="text/html",
            headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )

    static.router.add_get("/", index)
    sr = web.AppRunner(static)
    await sr.setup()
    await web.TCPSite(sr, "127.0.0.1", cast_port, ssl_context=tls).start()
    (lab / "ready").write_text(
        json.dumps(
            {
                "ha_version": "2026.10.0",
                "source_hashes": source_hashes,
                "local": f"https://localhost:{ha_port}/djconnect/vibecast",
                "static": f"https://localhost:{cast_port}/",
                "source": "synthetic MusicBrainz CC0 fixture, no provider call",
            }
        )
    )
    try:
        await asyncio.Event().wait()
    finally:
        await sr.cleanup()
        await runner.cleanup()
        await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
