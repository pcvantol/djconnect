"""Disposable real HA lifecycle/paired HTTP/agent metadata/SQLite bulletin proof.

External RSS, initial music observation and model response transport are declared
synthetic boundaries. No provider, installed HA, native audio or device effects.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from email.utils import format_datetime
from html import escape
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]


class Response:
    def __init__(self, body, status=200):
        self.body, self.status, self.headers, self.content = body, status, {}, self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def iter_chunked(self, size):
        for offset in range(0, len(self.body), size):
            yield self.body[offset:offset + size]


class PublicFeedFixture:
    def __init__(self, sources):
        self.sources, self.calls, self.closed = sources, [], False
        stamp = format_datetime(datetime.fromtimestamp(time.time() - 20, UTC))
        titles = ("Household income statistics released by institute",
                  "Coastal weather research station opens for scientists")
        self.bodies = {}
        for index, source in enumerate(sources[:2]):
            self.bodies[source.url] = ("<rss><channel><item><guid>synthetic-" + str(index)
                + "</guid><title>" + titles[index] + "</title><description>"
                + "This is explicitly synthetic metadata for isolated qualification."
                + "</description><link>https://" + source.article_hosts[0]
                + "/news/isolated-" + str(index) + "</link><pubDate>" + escape(stamp)
                + "</pubDate></item></channel></rss>").encode()

    def get(self, url, **kwargs):
        assert url in {s.url for s in self.sources}
        assert kwargs.get("allow_redirects") is False
        self.calls.append(url)
        return Response(self.bodies.get(url, b""), 200 if url in self.bodies else 503)

    async def close(self):
        self.closed = True


async def qualify(hass, manager, history, request, client):
    from aiohttp import ClientSession as ViewerClientSession, TCPConnector, web
    from verify_hybrid_transport_http import tls
    from custom_components.djconnect import api_handlers, pipeline
    from custom_components.djconnect.bulletin_intake import SOURCES
    from custom_components.djconnect.bulletin_runtime import capture_work
    from custom_components.djconnect.bulletin_service import (
        async_start_bulletin_service, async_close_bulletin_service)
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    from custom_components.djconnect.session_speech import moment_projection

    owner = "profile-a"
    active = manager.current_active(owner)
    if active:
        await manager.async_end(owner_profile_id=owner, session_id=active.session_id)
    music_boundaries = []

    async def no_initial_external_music(**kwargs):
        music_boundaries.append("initial_music_provider_not_part_of_news_qualification")

    async def no_external_observer(*args, **kwargs):
        music_boundaries.append("external_music_poll_replaced_by_normalized_observation")

    # Only external music acquisition is absent. Pairing, route, source fence,
    # model admission, Runtime, Planner and reservation transactions are real.
    with patch.object(api_handlers, "_async_generate_initial_session_moment", no_initial_external_music), \
            patch.object(PlaybackObservationManager, "async_start_spotify", no_external_observer):
        body, status = await request("POST", "/api/djconnect/v1/session/start",
                                     {"mood": "groove", "locale": "nl"})
    assert status == 201, body
    active = manager.current_active(owner)
    assert active and owner in manager._bulletin_providers
    sid = active.session_id
    await manager.async_update_playback_projection(owner_profile_id=owner,
        session_id=sid, state="playing", media_identity="synthetic-news-music",
        title="Synthetic music", artist="Synthetic artist", target_name="Synthetic output",
        position_ms=10000, duration_ms=300000)
    work = capture_work(manager, owner)
    assert work is not None, "real paired owner and no-tools HA agent must qualify"
    http = PublicFeedFixture(SOURCES)
    calls = []
    text = " ".join(["Dit is een synthetische nieuwstest met uitsluitend gecontroleerde voorbeeldgegevens voor de luisteraar."] * 6)

    async def fixture_transport(hass_arg, data, **kwargs):
        assert hass_arg is hass and data["agent_id"] == "history-fixture-agent"
        assert kwargs.get("allow_agent_fallback") is False
        persistence = persistence_service(hass)
        rows = await persistence.async_in_transaction(lambda tx: tx.fetchall(
            "SELECT story_hash FROM djconnect_bulletin_attempts"))
        assert len(rows) == 4, "actual SQLite commit must precede both model calls"
        prompt = data["text"]
        calls.append({"declared_synthetic_response": True, "committed_hashes_before_call": len(rows)})
        if "Assess every" in prompt:
            value = {"supported": True, "independent_stories": True,
                     "language_ok": True, "style_ok": True}
        else:
            facts = json.loads(prompt.rsplit("\n", 1)[1])["stories"]
            value = {"text": text, "story_ids": [item["id"] for item in facts]}
        return {"response": {"speech": {"plain": {"speech": json.dumps(value)}}}}

    # Public SDK metadata must reject control-capable agents before any model call.
    from homeassistant.components import conversation
    agent = conversation.async_get_agent(hass, "history-fixture-agent")
    with patch.object(agent, "supported_features", conversation.ConversationEntityFeature.CONTROL):
        try:
            work.guard()
        except PermissionError:
            pass
        else:
            raise AssertionError("control-capable agent admitted")
    # Capture a new work only after explicit safe original admission; old work stays revoked.
    work = capture_work(manager, owner)
    assert work is not None
    service = secure_site = viewer_client = viewer_ws = None
    try:
        with patch("aiohttp.ClientSession", return_value=http) as factory, \
                patch.object(pipeline, "_call_conversation_process_transport", fixture_transport):
            await async_start_bulletin_service(hass)
            service = hass.data["djconnect"]["bulletin_service"]
            await asyncio.wait_for(service._task, 10)
            assert not service.closed and service.ready(owner, sid) is not None, "actual service did not prepare"
            assert len(calls) == 2 and len(http.calls) == 5
            assert factory.call_count == 1
            config = factory.call_args.kwargs
            assert config["trust_env"] is False and config["timeout"].total == 8
            assert type(config["cookie_jar"]).__name__ == "DummyCookieJar"
            original_task = service._task
            await async_start_bulletin_service(hass)
            assert factory.call_count == 1 and service._task is original_task
            assert not active.broadcast.state.dj_moments, "collector may never publish"
            assert service.ready("other-owner", sid) is None
            server_ssl, client_ssl = tls(Path(hass.config.config_dir))
            secure_site = web.TCPSite(client.server.runner, "127.0.0.1", 0, ssl_context=server_ssl)
            await secure_site.start()
            viewer_client = ViewerClientSession(connector=TCPConnector(ssl=client_ssl))
            viewer_url = ("https://127.0.0.1:" + str(secure_site._server.sockets[0].getsockname()[1])
                + "/api/djconnect/v1/session/broadcast/ws/" + sid
                + "?broadcast_token=" + active.broadcast.broadcast_token)
            viewer_ws = await viewer_client.ws_connect(viewer_url)
            initial = await asyncio.wait_for(viewer_ws.receive_json(), 10)
            assert initial["type"] == "snapshot" and not initial["snapshot"]["dj_moments"]
            before = active.presence_ledger.total_published
            moment = await manager.async_maybe_publish_intra_track_moment(
                owner_profile_id=owner, session_id=sid, media_identity="synthetic-news-music")
            assert moment is not None and moment.moment_type.value == "dj_bulletin"
            assert active.presence_ledger.total_published == before + 1
            assert active.planner.last_decision.decision_type.value == "create_dj_bulletin"
            assert await manager.async_maybe_publish_intra_track_moment(
                owner_profile_id=owner, session_id=sid, media_identity="synthetic-news-music") is None
            response, code = await request("GET", "/api/djconnect/v1/session/active")
            assert code == 200 and text in json.dumps(response), response
            assert text in json.dumps(active.broadcast.as_dict(include_owner_only=False))
            for _ in range(10):
                shared_event = await asyncio.wait_for(viewer_ws.receive_json(), 10)
                if text in json.dumps(shared_event):
                    break
            else:
                raise AssertionError("real TLS readonly Broadcast did not deliver bulletin")
            await viewer_ws.close()
            viewer_ws = await viewer_client.ws_connect(viewer_url)
            shared_reconnect = await asyncio.wait_for(viewer_ws.receive_json(), 10)
            assert shared_reconnect["type"] == "snapshot" and text in json.dumps(shared_reconnect)
            assert "session_speech" not in shared_reconnect["snapshot"]
            off = moment_projection(active.broadcast, moment, autoplay=False)
            on = moment_projection(active.broadcast, moment, autoplay=True)
            from custom_components.djconnect.bulletin_source_policy import source_notice
            notice = source_notice(moment.bulletin.candidate.items,
                moment.bulletin.candidate.session.locale)
            assert moment.content == text + '\n\n' + notice
            assert moment.as_dict()['content'] == moment.content
            assert notice in json.dumps(response, ensure_ascii=False)
            assert notice in json.dumps(on, ensure_ascii=False)
            assert 60 <= len(moment.content.split()) <= 110 and len(moment.content) <= 1200
            assert off["manual_allowed"] and not off["autoplay_eligible"]
            assert on["autoplay_eligible"] and off["expires_at"] == on["expires_at"]
            assert len(moment.as_dict()["sources"]) == 2
            original_candidate = moment.bulletin.candidate
            with patch("time.time", return_value=original_candidate.expires_at + 1):
                assert text not in json.dumps(active.broadcast.as_dict())
                assert not moment_projection(active.broadcast, moment)["manual_allowed"]
            rows = await persistence_service(hass).async_in_transaction(lambda tx: tx.fetchall(
                "SELECT body FROM djconnect_session_entries WHERE reference_id=?", (moment.moment_id,)))
            assert rows and text not in str(rows)
            assert "source_retention_not_qualified" in str(rows)
            sample = {"moment": moment.as_dict(), "speech_off": off, "speech_on": on,
                      "native_delivery": active.broadcast.native_delivery(),
                      "owner_snapshot": active.broadcast.as_dict(),
                      "initial_shared_snapshot": initial["snapshot"],
                      "shared_snapshot": shared_reconnect["snapshot"], "shared_event": shared_event}
            assert sample["native_delivery"]["current_moment_id"] == moment.moment_id
            # Original source/entry change cannot be rearmed by returning to the same value.
            runtime = hass.data["djconnect"]["owner-entry"]
            hass.config_entries.async_update_entry(runtime.entry,
                data={**runtime.entry.data, "bulletin_fixture_change": 1})
            try:
                work.guard()
            except PermissionError:
                pass
            else:
                raise AssertionError("original paired authority was revived")
            assert not moment_projection(active.broadcast, moment)["manual_allowed"]
            assert text not in json.dumps(active.broadcast.as_dict())
            revoked = active.broadcast.native_delivery()
        return {"state": "PASS", "cases": ["paired_start_connects_approved_agent",
            "one_HA_lifecycle_cookie_free_client", "control_capable_HA_agent_denied", "actual_SQL_commit_before_two_model_calls",
            "collector_prepares_never_publishes", "existing_Planner_and_shared_Presence_once",
            "owner_HTTP_and_real_TLS_readonly_shared_snapshot_event_reconnect", "existing_autoplay_toggle_original_expiry",
            "complete_source_notice_retained_in_HTTP_native_and_speech",
            "expired_source_redacts_text_and_speech", "metadata_only_history",
            "original_authority_withdrawal", "service_closed_and_task_removed"],
            "sample": sample, "revoked_native_delivery": revoked, "model_provider_calls": 0, "external_RSS_calls": 0,
            "declared_model_transport_calls": calls, "synthetic_music_boundaries": music_boundaries,
            "installed_or_native_acceptance": "NOT_RUN"}
    finally:
        if viewer_ws:
            await viewer_ws.close()
        if viewer_client:
            await viewer_client.close()
        if secure_site:
            await secure_site.stop()
        await async_close_bulletin_service(hass)
        if service:
            assert service.closed and http.closed and manager._bulletin_service is None
            service.tick()
            assert service._task.done()
        await manager.async_end(owner_profile_id=owner, session_id=sid)


if __name__ == "__main__":
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
