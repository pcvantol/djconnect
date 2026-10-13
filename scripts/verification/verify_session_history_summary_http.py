"""Isolated ordinary paired HA / real Session acceptance and summary transport.
Only existing external Spotify and HA-conversation provider responses are fixtures.
Expected: two canonical observations, two semantic Moments, one readable body;
energy predominates after two seconds chill and more than fifty seconds energy.
No source installation, HA-dev restart, public effects or broad HA credentials.
"""

from __future__ import annotations

import asyncio
import json
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
    manager = SessionRuntimeManager(
        PersistentSessionRepository(service),
        HistoricalProjectionRepository(service),
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

    selected = ["1"]
    calls = []

    async def provider(self, method, path, **kwargs):
        calls.append(path)
        if path == "/me/player":
            n = selected[0]
            return {
                "is_playing": True,
                "progress_ms": 20000,
                "item": {
                    "name": "Anchor " + n,
                    "uri": "spotify:track:" + n * 22,
                    "id": n * 22,
                    "duration_ms": 240000,
                    "artists": [{"name": "Northline", "id": "2" * 22}],
                    "album": {
                        "name": "Fixture Edition",
                        "uri": "spotify:album:" + "3" * 22,
                        "id": "3" * 22,
                        "release_date": "2001-04-02",
                        "release_date_precision": "day",
                    },
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
        speech = json.dumps(
            {
                "summary": "A spacious ambient texture.",
                "full_text": "The spacious texture offers a calm listening context.",
                "genre": "ambient",
                "energy": 25,
            }
        )
        return {"response": {"speech": {"plain": {"speech": speech}}}}

    hass.services.async_register(
        "conversation", "process", conversation, supports_response=SupportsResponse.ONLY
    )
    receipts = []
    async with TestClient(TestServer(hass.http.app)) as client:
        pair = await client.post("/api/djconnect/v1/pair", json={**identity, "pair_code": "123456"})
        paired = await pair.json()
        assert pair.status == 200 and paired["success"]
        headers = {
            "Authorization": "Bearer " + paired["device_token"],
            "X-DJConnect-Device-ID": identity["device_id"],
        }

        async def post(path, payload):
            response = await client.post("/api/djconnect/v1" + path, json=payload, headers=headers)
            body = await response.json()
            receipts.append({"path": path, "status": response.status, "body": body})
            assert response.status in (200, 201), body
            return body

        started = await post("/session/start", {**identity, "mood": "chill", "locale": "nl"})
        sid = started["session"]["session_id"]
        print("STARTED", sid, flush=True)
        await asyncio.sleep(2)
        response = await client.get(
            "/api/djconnect/v1/session/history",
            params={**identity, "include_active": "true"},
            headers=headers,
        )
        first = await response.json()
        receipts.append({"path": "history-open", "status": response.status, "body": first})
        print(json.dumps(first), flush=True)
        await post(
            "/session/mood",
            {
                **identity,
                "contract_version": 1,
                "session_id": sid,
                "selected_mood": "energy",
                "expected_mood_revision": 0,
            },
        )
        await asyncio.sleep(55)
        selected[0] = "4"
        await asyncio.sleep(17)
        await post("/session/end", {**identity, "session_id": sid})
        await async_shutdown_persistence(hass)
        hass.data["djconnect"].pop("session_history_query", None)
        reopened = await async_initialize_persistence(hass)
        hass.data["djconnect"]["session_runtime_manager"] = SessionRuntimeManager(
            PersistentSessionRepository(reopened), HistoricalProjectionRepository(reopened)
        )
        for path in ("/session/history", "/session/history/" + sid):
            response = await client.get(
                "/api/djconnect/v1" + path, params=identity, headers=headers
            )
            body = await response.json()
            assert response.status == 200, body
            receipts.append(
                {
                    "path": path,
                    "status": response.status,
                    "body": body,
                    "cache_control": response.headers.get("Cache-Control"),
                }
            )
            summary = (body["sessions"][0] if path == "/session/history" else body["session"])[
                "summary"
            ]
            assert summary["tracks_observed"]["value"] == 2, summary
            assert summary["moments_published"]["value"] == 2, summary
            assert summary["mood"]["value"] == "energy", summary
            assert summary["state"] == "final", summary
            if "entries" in body:
                assert sum(e["kind"] == "dj_moment" for e in body["entries"]) == 1, body
            print(path, json.dumps(body), flush=True)
        (directory / "paired-chain-progress.json").write_text(
            json.dumps(
                {
                    "ordinary_pairing": True,
                    "broad_ha_credentials": False,
                    "fixtures": [
                        "external Spotify responses",
                        "existing HA conversation provider response",
                    ],
                    "receipts": receipts,
                    "provider_calls": calls,
                },
                indent=2,
            )
            + "\n"
        )
    await provider_session.close()
    await async_shutdown_persistence(hass)
    await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
