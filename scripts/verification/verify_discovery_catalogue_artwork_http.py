# ruff: noqa: E402
"""Actual paired catalogue-fallback artwork; external Spotify and CDN fixtures only."""

import asyncio
import hashlib
import json
from copy import deepcopy
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
from discovery_play_lab import ARTIST, TRACK


class Network:
    def __init__(self, client):
        self.client = client
        # TestClient disables pooled retries; qualify the default production client.
        self.wire_session = ClientSession()
        self.calls = []

    def request(self, method, url, **kwargs):
        u = urlsplit(url)
        assert u.scheme == "https" and u.hostname in {"api.spotify.com", "i.scdn.co"}
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
    await es.async_save({"entries": [slot.as_storage_fragment]})
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
    register_http_views(hass)

    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
        "0000000b4944415478da6364f80f00010501012718e3660000000049454e44ae426082"
    )
    asset = "a" * 40
    artist = {"id": ARTIST, "uri": "spotify:artist:" + ARTIST, "type": "artist",
              "name": "Fixture artist", "genres": ["jazz"], "images": []}
    track = {"id": TRACK, "uri": "spotify:track:" + TRACK, "type": "track",
             "name": "Known track", "artists": [artist],
             "album": {"id": "B" * 22, "uri": "spotify:album:" + "B" * 22,
                       "name": "Known album", "images": []}}
    exact = deepcopy(track)
    exact.update(id="G" * 22, uri="spotify:track:" + "G" * 22, name="Exact catalogue track")
    exact["album"].update(id="H" * 22, uri="spotify:album:" + "H" * 22,
                          name="Exact catalogue album",
                          images=[{"url": "https://i.scdn.co/image/" + asset}])
    conflicting = deepcopy(exact)
    conflicting.update(id="I" * 22, uri="spotify:track:" + "I" * 22,
                       name="Conflicting catalogue track")
    conflicting["album"].update(id="J" * 22, uri="spotify:album:" + "K" * 22,
                                name="Conflicting catalogue album")

    async def provider(req):
        assert req.method == "GET"
        if req.path == "/image/" + asset:
            assert "Authorization" not in req.headers and "Cookie" not in req.headers
            return web.Response(body=png, content_type="image/png")
        assert req.headers.get("Authorization") == "Bearer fixture-provider-access"
        if req.path == "/v1/search" and req.query.get("type") == "track":
            return web.json_response({"tracks": {"items": [exact, conflicting]}})
        if req.path.endswith("/recently-played"):
            return web.json_response({"items": [{"track": track}]})
        if req.path.endswith("/top/artists"):
            return web.json_response({"items": [artist]})
        if req.path.endswith("/top/tracks"):
            return web.json_response({"items": [track]})
        return web.json_response({"error": {"message": "Synthetic missing fixture"}}, status=404)

    app = web.Application()
    app.router.add_route("GET", "/{path:.*}", provider)
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
        try:
            pair = await client.post("/api/djconnect/v1/pair", json={**ident, "pair_code": "123456"})
            paired = await pair.json()
            assert pair.status == 200 and paired["success"]
            headers = {"Authorization": "Bearer " + paired["device_token"],
                       "X-DJConnect-Device-ID": ident["device_id"]}
            setting = await client.post("/api/djconnect/v1/music_dna/settings",
                                        json={**ident, "enabled": True}, headers=headers)
            assert setting.status == 200
            profile = await client.post("/api/djconnect/v1/music_dna/profile", json=ident, headers=headers)
            assert profile.status == 200
            feed = await client.get("/api/djconnect/v1/music_discovery", params=ident, headers=headers)
            assert feed.status == 200
            section = next(s for s in (await feed.json())["sections"] if s["id"] == "new_for_you")
            items = {item["uri"]: item for item in section["items"]}
            assert set(items) == {exact["uri"], conflicting["uri"]}, section
            match = items[exact["uri"]]
            assert match["reason_sources"] == ["spotify_catalog", "djconnect_music_dna"]
            assert match.get("image_url"), "Catalogue fallback discarded exact provider artwork"
            assert match["image_attribution"]["media_uri"] == exact["album"]["uri"]
            assert time.time() < match["image_expires_at"] <= time.time() + 900
            assert not items[conflicting["uri"]].get("image_url")
            assert "asset_id" not in json.dumps(section) and '"_artwork"' not in json.dumps(section)
            assert not any("/v1/tracks/" in call["path"] for call in network.calls)
            image = await client.get(match["image_url"])
            assert image.status == 200 and await image.read() == png
            assert image.headers["Cache-Control"] == "private, no-store"
            search = await client.post("/api/djconnect/v1/command", json={
                **ident, "command": "search_tracks", "play": False,
                "value": {"query": 'artist:"Fixture artist"', "limit": 10, "with_discovery_artwork": True},
            }, headers=headers)
            public_body = await search.json()
            assert search.status == 200 and public_body["tracks"]
            assert all("artwork" not in item and "album_uri" not in item for item in public_body["tracks"])
            assert all(c["method"] == "GET" for c in network.calls)
        finally:
            cache.pop(key)
            await network.wire_session.close()
    await hass.async_stop()
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in source_hashes.items())
    match["image_url"] = "/api/djconnect/v1/image_proxy/disc-<opaque-redacted>"
    record = {"ordinary_pair_auth": True, "core_mocked": False,
              "integration_source_hashes": source_hashes, "catalogue_fallback": section,
              "cases": {"catalogue_fallback_exact_album_image_no_extra_lookup": "200_EXACT_FIXTURE_BYTES",
                        "catalogue_fallback_conflicting_album_stays_placeholder": True,
                        "public_search_cannot_request_private_artwork_reference": True}}
    (LAB / "qualification.json").write_text(json.dumps(record, indent=2) + "\n")
    print("DISCOVERY_CATALOGUE_ARTWORK_PASS", len(record["cases"]))


if __name__ == "__main__":
    asyncio.run(main())
