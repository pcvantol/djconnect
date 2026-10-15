"""Ordinary paired HA status/history/DNA/Track Insight before/after convergence.

Run against a pinned baseline checkout or the candidate using DJC_SOURCE_ROOT.
Only external Spotify, HA conversation provider and Wikipedia responses are fixtures.
Own empty DJC_LAB_ROOT; no installed HA or consumer/hardware acceptance implied.
"""

from __future__ import annotations

import asyncio
import json
import hashlib
import os
from pathlib import Path
import secrets
import sys
import socket
from dataclasses import replace
from aiohttp import ClientSession
from homeassistant.helpers import aiohttp_client

from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/verification"))
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.music_dna import MusicDNAManager  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.persistence import (  # noqa: E402
    async_initialize_persistence,
    async_shutdown_persistence,
)
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402


from custom_components.djconnect.verification_clock import VerificationClock  # noqa: E402


async def main():
    directory = Path(os.environ.get("DJC_LAB_ROOT", "/lab"))
    config = directory / ("paired-config-" + secrets.token_hex(4))
    config.mkdir(parents=True)
    hass = HomeAssistant(str(config))
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.state = CoreState.running
    hass.config.language = "nl"
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(
        cors_origins=[],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    identity = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"}
    slot = entry(
        "owner-entry",
        {
            **identity,
            "pair_code": "123456",
            "music_backend": "spotify_direct",
            "profile_id": "profile-a",
            "music_account_id": "fixture-account",
            "spotify_client_id": "fixture-client",
            "spotify_refresh_token": "fixture-provider-only",
        },
    )
    # A configured slot, not a paired token. The real HTTP pair handler mints it.
    second_identity = {"device_id": "djconnect-macos-ABCDEF123457", "client_type": "macos"}
    second_slot = entry(
        "second-owner",
        {
            **second_identity,
            "profile_backend_entry_id": "owner-entry",
            "pair_code": "234567",
            "music_backend": "spotify_direct",
            "profile_id": "profile-a",
            "music_account_id": "fixture-account",
            "spotify_client_id": "fixture-client",
            "spotify_refresh_token": "fixture-provider-only",
        },
    )
    store = ConfigEntryStore(hass)
    await store.async_save({"entries": [slot.as_storage_fragment, second_slot.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    slot = hass.config_entries.async_get_entry("owner-entry")
    slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    second_slot = hass.config_entries.async_get_entry("second-owner")
    second_slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    second_runtime = DJConnectRuntime(second_slot)
    runtime = DJConnectRuntime(slot)
    runtime.memory = MusicDNAManager(hass)
    await runtime.memory.async_load()
    hass.data["djconnect"] = {
        "owner-entry": runtime,
        "second-owner": second_runtime,
        "runtime": runtime,
    }
    storage = ProfilePlatformStorage(hass)
    hass.data["djconnect"]["djconnect_profile_platform"] = storage
    await storage.async_upsert_music_backend(
        "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Fixture Spotify"
    )
    for profile in ("profile-a", "profile-other"):
        await storage.async_create_profile(
            profile, profile_id=profile, default_backend_id="spotify_direct"
        )
    await storage.async_upsert_music_account(
        "fixture-account",
        "spotify_direct",
        kind=MusicAccountKind.PERSONAL,
        display_name="Fixture provider account",
        linked_profile_ids=frozenset({"profile-a"}),
        provider_account_id="fixture-client",
    )
    profile = storage.household.profiles["profile-a"]
    await storage.async_update_profile(
        "profile-a",
        preferences=replace(profile.preferences, default_music_account_id="fixture-account"),
    )
    await storage.async_upsert_device(identity["device_id"], "ios", linked_profile_id="profile-a")
    await storage.async_upsert_device(
        second_identity["device_id"], "macos", linked_profile_id="profile-a"
    )
    service = await async_initialize_persistence(hass)
    clock = VerificationClock()
    manager = SessionRuntimeManager(
        PersistentSessionRepository(service),
        HistoricalProjectionRepository(service),
        monotonic_source=clock.monotonic,
    )
    hass.data["djconnect"]["session_runtime_manager"] = manager
    provider_session = ClientSession()
    cache_key = aiohttp_client._make_key(
        True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT
    )
    hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})[cache_key] = provider_session
    register_http_views(hass)
    await websocket_api.async_setup(hass, {})
    from homeassistant.core import SupportsResponse
    from custom_components.djconnect.spotify_backend import SpotifyBackend
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager

    try:
        from custom_components.djconnect import ambient_ask_dj
    except ImportError:
        ambient_ask_dj = None
    baseline = ambient_ask_dj is not None
    history = AskDJHistoryManager(hass)
    runtime.ask_dj_history = history
    hass.data["djconnect"]["ask_dj_history_manager"] = history
    for scope in ("owner-ha", "other-ha", "profile:profile-a"):
        await history.async_append_assistant_message(
            scope,
            {"client_message_id": "seed-" + scope},
            {
                "text": "Existing operational notice",
                "message_kind": "system",
                "origin": "qualification_seed",
            },
        )
    calls = {"conversation": [], "spotify": [], "wiki": []}
    album = ["Fixture Edition A"]

    async def provider(self, method, path, **kwargs):
        calls["spotify"].append({"method": method, "path": path})
        if path == "/me/player":
            return {
                "is_playing": True,
                "progress_ms": 20000,
                "item": {
                    "name": "First Light",
                    "uri": "spotify:track:" + "1" * 22,
                    "id": "1" * 22,
                    "duration_ms": 240000,
                    "artists": [{"name": "Northline", "id": "2" * 22}],
                    "album": {"name": album[0], "uri": "spotify:album:" + "3" * 22, "id": "3" * 22},
                },
                "device": {"name": "Own fixture output", "id": "fixture-output"},
            }
        if path.startswith("/me/tracks/contains"):
            return [False]
        if path.startswith("/artists"):
            return {"artists": [{"id": "2" * 22, "genres": ["ambient"]}]}
        raise AssertionError("Undeclared provider boundary: " + path)

    SpotifyBackend._request = provider

    async def conversation(call):
        text = call.data["text"]
        calls["conversation"].append({"text": text, "language": call.data.get("language")})
        speech = (
            json.dumps(
                {
                    "summary": "A spacious ambient texture.",
                    "full_text": "The spacious texture offers a calm listening context.",
                    "genre": "ambient",
                    "energy": 25,
                }
            )
            if "JSON" in text
            else "Northline werd in 1994 opgericht."
        )
        return {"response": {"speech": {"plain": {"speech": speech}}}}

    hass.services.async_register(
        "conversation", "process", conversation, supports_response=SupportsResponse.ONLY
    )

    class WikiResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def json(self, **kwargs):
            return {
                "title": "Northline",
                "description": "Fixture artist summary; not claim proof",
                "thumbnail": {"source": "https://fixture.invalid/artist.png"},
                "content_urls": {"desktop": {"page": "https://fixture.invalid/artist"}},
            }

    class WikiSession:
        def get(self, url, **kwargs):
            calls["wiki"].append(url)
            return WikiResponse()

    if baseline:
        ambient_ask_dj.async_get_clientsession = lambda _: WikiSession()
    receipts = []
    async with TestClient(TestServer(hass.http.app)) as client:
        pair = await client.post("/api/djconnect/v1/pair", json={**identity, "pair_code": "123456"})
        paired = await pair.json()
        assert pair.status == 200 and paired["success"]
        headers = {
            "Authorization": "Bearer " + paired["device_token"],
            "X-DJConnect-Device-ID": identity["device_id"],
        }

        async def status(label):
            resp = await client.post("/api/djconnect/v1/status", json=identity, headers=headers)
            body = await resp.json()
            assert resp.status == 200 and body["playback"]["has_playback"], body
            receipts.append(
                {
                    "label": label,
                    "status": resp.status,
                    "body": body,
                    "history": {
                        scope: await history.async_history(scope)
                        for scope in ("owner-ha", "other-ha", "profile:profile-a")
                    },
                    "memory": json.loads(json.dumps(runtime.memory._data)),
                    "conversation_calls": len(calls["conversation"]),
                    "wiki_calls": len(calls["wiki"]),
                }
            )

        await status("no-session-optout")
        await status("repeat-dedup")
        await runtime.memory.async_set_enabled(runtime, True, identity)
        album[0] = "Fixture Edition B"
        await status("no-session-optin-album-change")
        races = []
        if not baseline:
            from unittest.mock import patch

            async def broken_history_store(data):
                raise OSError("Owned synthetic history Store failure")

            with patch.object(history._store, "async_save", broken_history_store):
                album[0] = "Fixture Edition C"
                await status("history-store-unavailable")
            for condition in ("late_provider", "cancelled_read", "provider_timeout"):
                entered, release = asyncio.Event(), asyncio.Event()

                async def delayed(self, method, path, **kwargs):
                    if path == "/me/player":
                        entered.set()
                        await release.wait()
                        if condition == "provider_timeout":
                            raise TimeoutError("Owned external provider timeout")
                    return await provider(self, method, path, **kwargs)

                with patch.object(SpotifyBackend, "_request", delayed):
                    pending = asyncio.create_task(
                        client.post("/api/djconnect/v1/status", json=identity, headers=headers)
                    )
                    await asyncio.wait_for(entered.wait(), 5)
                    if condition == "cancelled_read":
                        pending.cancel()
                        try:
                            await pending
                        except asyncio.CancelledError:
                            pass
                    release.set()
                    if condition != "cancelled_read":
                        response = await pending
                        body = await response.json()
                        assert response.status == 200
                        assert body["playback"]["has_playback"] is (condition != "provider_timeout")
                    await hass.async_block_till_done()
                assert calls["conversation"] == [] and calls["wiki"] == []
                races.append(
                    {"condition": condition, "ambient_generation": 0, "ambient_publication": 0}
                )
            denied = await client.post("/api/djconnect/v1/status", json=identity)
            assert denied.status == 401
            # Select the configured second setup slot, as the ordinary pairing UI does.
            hass.data["djconnect"]["runtime"] = second_runtime
            try:
                peer = await client.post(
                    "/api/djconnect/v1/pair", json={**second_identity, "pair_code": "234567"}
                )
                peer_body = await peer.json()
            finally:
                hass.data["djconnect"]["runtime"] = runtime
            assert peer.status == 200 and peer_body["success"], peer_body
            peer_headers = {
                "Authorization": "Bearer " + peer_body["device_token"],
                "X-DJConnect-Device-ID": second_identity["device_id"],
            }
            second_runtime.memory = runtime.memory
            second_runtime.ask_dj_history = history
            peer_status = await client.post(
                "/api/djconnect/v1/status", json=second_identity, headers=peer_headers
            )
            assert (
                peer_status.status == 200 and (await peer_status.json())["playback"]["has_playback"]
            )
            wrong = await client.post(
                "/api/djconnect/v1/status", json=identity, headers=peer_headers
            )
            assert wrong.status == 401
            assert calls["conversation"] == [] and calls["wiki"] == []
        insight = await client.post(
            "/api/djconnect/v1/track_insight",
            json={
                **identity,
                "title": "First Light",
                "artist": "Northline",
                "album": album[0],
                "locale": "nl",
                "force_refresh": True,
            },
            headers=headers,
        )
        insight_body = await insight.json()
        assert insight.status == 200, insight_body
        reloaded = AskDJHistoryManager(hass)
        persisted = {
            scope: await reloaded.async_history(scope)
            for scope in ("owner-ha", "other-ha", "profile:profile-a")
        }
        result = {
            "base": "de0e1fccbfdb0f8ffc5a58c77c209919f4cf00de",
            "boundary_fixtures": [
                "Spotify HTTP response",
                "HA conversation provider response",
                "Wikipedia HTTP response",
            ],
            "ordinary_pairing": True,
            "ha_test_credentials": False,
            "active_session": False,
            "receipts": receipts,
            "race_cases": races,
            "calls": calls,
            "track_insight": {"status": insight.status, "body": insight_body},
            "store_reopen": persisted,
        }
        result["mode"] = "baseline" if baseline else "candidate"
        result["source_sha256"] = {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "custom_components/djconnect").rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts
        }
        if baseline:
            assert [r["conversation_calls"] for r in receipts] == [1, 1, 2]
            assert [r["wiki_calls"] for r in receipts] == [1, 1, 2]
            assert len(persisted["owner-ha"]["messages"]) == 3
            assert len(persisted["other-ha"]["messages"]) == 3
        else:
            assert all(r["conversation_calls"] == 0 and r["wiki_calls"] == 0 for r in receipts)
            assert all(len(v["messages"]) == 1 for v in persisted.values())
            assert all(not v.get("last_ask_dj") for v in runtime.memory._data["memories"].values())
        assert len(persisted["profile:profile-a"]["messages"]) == 1
        assert insight_body["analysis"]["summary"] == "A spacious ambient texture."
        (directory / ("ambient-" + result["mode"] + "-receipt.json")).write_text(
            json.dumps(result, indent=2) + "\n"
        )
    await provider_session.close()
    await async_shutdown_persistence(hass)
    await hass.async_stop()
    print("AMBIENT_PAIRED_STATUS_STORE_PASS", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
