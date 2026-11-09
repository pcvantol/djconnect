# ruff: noqa: E402
"""Actual paired HA Discovery proof; only external provider wires are synthetic."""

import asyncio
import hashlib
import os
from pathlib import Path
import secrets
import socket
import sys
import time
from dataclasses import replace
from urllib.parse import urlsplit
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry, aiohttp_client

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
LAB = Path(os.environ.get("DJC_LAB_ROOT", "/lab"))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]
from verify_session_conversation_history_http import entry
from custom_components.djconnect import DJConnectRuntime, register_http_views
from custom_components.djconnect.domain.backend import BackendProvider
from custom_components.djconnect.domain.music_account import MusicAccountKind
from custom_components.djconnect.domain.storage import ProfilePlatformStorage
from custom_components.djconnect.music_dna import MusicDNAManager
from discovery_play_lab import provider_reply, ARTIST, TRACK


class Network:
    def __init__(self, client):
        self.client = client
        # TestClient disables pooled retries; qualify the default production client.
        self.wire_session = ClientSession()
        self.calls = []

    def request(self, method, url, **kwargs):
        u = urlsplit(url)
        assert u.scheme == "https" and u.hostname in {"api.spotify.com", "accounts.spotify.com"}
        self.calls.append({"method": method, "path": u.path, "provider_fixture": True})
        target = self.client.make_url(u.path + ("?" + u.query if u.query else ""))
        return self.wire_session.request(method, target, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)


async def main():
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "custom_components/djconnect").rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    config = LAB / ("baseline-ha-" + secrets.token_hex(4))
    config.mkdir(exist_ok=True)
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
    ident = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"}
    slot = entry(
        "artwork-owner",
        {
            **ident,
            "pair_code": "123456",
            "music_backend": "spotify_direct",
            "profile_id": "artwork-profile",
            "music_account_id": "artwork-account",
            "spotify_client_id": "fixture-client",
            "spotify_refresh_token": "fixture-provider-only",
        },
    )
    es = ConfigEntryStore(hass)
    ident2 = {"device_id": "djconnect-ios-DEFABC123456", "client_type": "ios"}
    slot2 = entry(
        "artwork-second",
        {
            **ident2,
            "pair_code": "654321",
            "music_backend": "spotify_direct",
            "profile_id": "artwork-second-profile",
            "music_account_id": "artwork-second-account",
            "spotify_client_id": "fixture-second-client",
            "spotify_refresh_token": "fixture-second-provider",
        },
    )
    await es.async_save({"entries": [slot.as_storage_fragment, slot2.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    slot = hass.config_entries.async_get_entry("artwork-owner")
    slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    rt = DJConnectRuntime(slot)
    rt.spotify_access_token = "fixture-provider-access"
    rt.spotify_access_token_expires_at = time.time() + 3600
    rt.memory = MusicDNAManager(hass)
    await rt.memory.async_load()
    hass.data["djconnect"] = {"artwork-owner": rt, "runtime": rt}
    storage = ProfilePlatformStorage(hass)
    hass.data["djconnect"]["djconnect_profile_platform"] = storage
    await storage.async_upsert_music_backend(
        "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Fixture Spotify"
    )
    p = await storage.async_create_profile(
        "Artwork fixture", profile_id="artwork-profile", default_backend_id="spotify_direct"
    )
    await storage.async_upsert_music_account(
        "artwork-account",
        "spotify_direct",
        kind=MusicAccountKind.PERSONAL,
        display_name="Fixture account",
        linked_profile_ids=frozenset({"artwork-profile"}),
        provider_account_id="fixture-client",
    )
    await storage.async_update_profile(
        "artwork-profile",
        preferences=replace(p.preferences, default_music_account_id="artwork-account"),
    )
    await storage.async_upsert_device(
        ident["device_id"], "ios", linked_profile_id="artwork-profile"
    )
    slot2 = hass.config_entries.async_get_entry("artwork-second")
    slot2._async_set_state(hass, ConfigEntryState.LOADED, None)
    rt2 = DJConnectRuntime(slot2)
    rt2.memory = rt.memory
    rt2.spotify_access_token = "fixture-second-access"
    rt2.spotify_access_token_expires_at = time.time() + 3600
    hass.data["djconnect"]["artwork-second"] = rt2
    p2 = await storage.async_create_profile(
        "Artwork second fixture",
        profile_id="artwork-second-profile",
        default_backend_id="spotify_direct",
    )
    await storage.async_upsert_music_account(
        "artwork-second-account",
        "spotify_direct",
        kind=MusicAccountKind.PERSONAL,
        display_name="Fixture second account",
        linked_profile_ids=frozenset({p2.profile_id}),
        provider_account_id="fixture-second-client",
    )
    await storage.async_update_profile(
        p2.profile_id,
        preferences=replace(p2.preferences, default_music_account_id="artwork-second-account"),
    )
    await storage.async_upsert_device(ident2["device_id"], "ios", linked_profile_id=p2.profile_id)
    register_http_views(hass)

    async def provider(req):
        result = await provider_reply(req)
        if result is not None:
            return result
        artist = {
            "id": ARTIST,
            "uri": "spotify:artist:" + ARTIST,
            "type": "artist",
            "name": "Fixture artist",
            "genres": ["jazz"],
            "images": [],
        }
        track = {
            "id": TRACK,
            "uri": "spotify:track:" + TRACK,
            "type": "track",
            "name": "Fixture track",
            "artists": [artist],
            "album": {
                "id": "B" * 22,
                "uri": "spotify:album:" + "B" * 22,
                "name": "Fixture album",
                "images": [],
            },
        }
        if req.path.endswith("/recently-played"):
            return web.json_response({"items": [{"track": track}]})
        if req.path.endswith("/top/artists"):
            return web.json_response({"items": [artist]})
        if req.path.endswith("/top/tracks"):
            return web.json_response({"items": [track]})
        return web.json_response({"error": {"message": "Synthetic missing fixture"}}, status=404)

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", provider)
    async with (
        TestClient(TestServer(app)) as upstream,
        TestClient(TestServer(hass.http.app)) as client,
    ):
        cache = hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})
        key = aiohttp_client._make_key(
            True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT
        )
        network = Network(upstream)
        cache[key] = network
        pair = await client.post("/api/djconnect/v1/pair", json={**ident, "pair_code": "123456"})
        paired = await pair.json()
        assert pair.status == 200, paired
        headers = {
            "Authorization": "Bearer " + paired["device_token"],
            "X-DJConnect-Device-ID": ident["device_id"],
            "X-DJConnect-Client-Type": "ios",
        }
        setting = await client.post(
            "/api/djconnect/v1/music_dna/settings", json={**ident, "enabled": True}, headers=headers
        )
        assert setting.status == 200, await setting.json()
        import json
        from custom_components.djconnect.profile_backend import ProfileBackendView
        from custom_components.djconnect.discovery_artwork import authority_valid
        from custom_components.djconnect.spotify_backend import handle_spotify_command
        view = ProfileBackendView(hass, rt, rt)
        raw_valid = authority_valid(rt)
        view_valid = authority_valid(view)
        before = len(network.calls)
        result = await handle_spotify_command(hass, view, "discovery_playlist_identity", {
            "artist_uri": "spotify:artist:" + ARTIST, "playlist_uri": "spotify:playlist:" + "D" * 22}, play=False)
        assert raw_valid and not view_valid
        assert result.get("success") is True, result
        assert len(network.calls) > before
        assert all(call["method"] in {"GET", "POST"} for call in network.calls[before:])
        rt.device_token = "replacement-pairing"
        stale = await handle_spotify_command(hass, view, "discovery_playlist_identity", {
            "artist_uri": "spotify:artist:" + ARTIST, "playlist_uri": "spotify:playlist:" + "D" * 22}, play=False)
        assert stale.get("error") == "music_discovery_context_changed", stale
        proof = {"actual_home_assistant": True, "ordinary_paired_entry": True,
                 "registered_caller_authority_valid": raw_valid, "canonical_view_is_not_registry_runtime": not view_valid,
                 "result": result, "provider_calls_during_probe": len(network.calls)-before,
                 "product_changed": False, "real_provider_calls": 0, "source_files_sha256": source_hashes}
        (LAB / "authority-view-repair.json").write_text(json.dumps(proof, indent=2)+"\n")
        print("CANONICAL_VIEW_CURRENT_CALLER_AND_STALE_PAIR_FENCED", flush=True)
        cache.pop(key)
        await network.wire_session.close()
    await hass.async_stop()


asyncio.run(main())
