# ruff: noqa: E402
"""Own real HA artwork qualification; only external provider/CDN wire is fixture."""

import asyncio
import os
import json
import sys
import time
import socket
import secrets
import hashlib
import struct
import zlib
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
from dataclasses import replace
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry, aiohttp_client

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]
from verify_session_conversation_history_http import entry
from custom_components.djconnect import DJConnectRuntime, register_http_views
from custom_components.djconnect.domain.backend import BackendProvider
from custom_components.djconnect.domain.music_account import MusicAccountKind
from custom_components.djconnect.domain.storage import ProfilePlatformStorage
from custom_components.djconnect.music_dna import MusicDNAManager
from custom_components.djconnect.discovery_artwork import capture_refresh_guard
from custom_components.djconnect.spotify_backend import (
    _normalize_profile_track,
    _normalize_profile_artist,
)

LAB = Path(os.environ.get("DJC_LAB_ROOT", "/private/tmp/djc-core-discovery-artwork-v1"))
LAB.mkdir(exist_ok=True)
TRACK = {
    "id": "A" * 22,
    "uri": "spotify:track:" + "A" * 22,
    "name": "Fixture track",
    "duration_ms": 180000,
    "artists": [{"id": "C" * 22, "name": "Fixture artist", "uri": "spotify:artist:" + "C" * 22}],
    "album": {
        "id": "B" * 22,
        "uri": "spotify:album:" + "B" * 22,
        "name": "Fixture album",
        "images": [{"url": "https://i.scdn.co/image/" + "a" * 40, "width": 300, "height": 300}],
    },
}
ARTIST = {
    "id": "C" * 22,
    "uri": "spotify:artist:" + "C" * 22,
    "name": "Fixture artist",
    "genres": ["jazz"],
    "images": [{"url": "https://i.scdn.co/image/" + "c" * 40, "width": 300, "height": 300}],
}


class Network:
    def __init__(self, client):
        self.client = client
        self.calls = []

    def request(self, method, url, **kwargs):
        u = urlsplit(url)
        assert u.hostname in {"api.spotify.com", "accounts.spotify.com", "i.scdn.co"} and u.scheme == "https"
        self.calls.append({"method": method, "path": u.path, "provider_fixture": True})
        return self.client.request(method, u.path + ("?" + u.query if u.query else ""), **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)


def png(color):
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    pixels = b"".join(b"\x00" + bytes(color) * 64 for _ in range(64))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


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
    mode = {"value": "ok", "provider_delay": False, "provider_art": "valid"}
    entered = asyncio.Event()
    release = asyncio.Event()
    assets = {
        "a" * 40: png((180, 40, 20)),
        "c" * 40: png((20, 70, 180)),
        "d" * 40: png((20, 180, 70)),
    }

    async def provider(req):
        if req.path == "/api/token":
            data = await req.post()
            assert req.method == "POST" and data["grant_type"] == "refresh_token"
            assert data["client_id"] == "fixture-client"
            return web.json_response({
                "access_token": "fixture-provider-access", "expires_in": 3600,
                "refresh_token": "fixture-rotated-provider-only",
            })
        if req.path.startswith("/image/"):
            assert "Authorization" not in req.headers and "Cookie" not in req.headers
            if mode["value"] == "redirect":
                return web.Response(status=302, headers={"Location": "http://127.0.0.1/forbidden"})
            if mode["value"] == "html":
                return web.Response(body=b"<html>wrong</html>", content_type="image/png")
            if mode["value"] == "large":
                return web.Response(body=b"x" * (2 * 1024 * 1024 + 1), content_type="image/png")
            if mode["value"] == "mime":
                return web.Response(body=assets["a" * 40], content_type="text/html")
            if mode["value"] == "upstream_error":
                return web.Response(status=503)
            if mode["value"] == "chunked_large":
                response = web.StreamResponse(headers={"Content-Type": "image/png"})
                await response.prepare(req)
                await response.write(b"x" * (2 * 1024 * 1024 + 1))
                await response.write_eof()
                return response
            if mode["value"] == "timeout":
                await asyncio.sleep(14.2)
            if mode["value"] == "delay":
                entered.set()
                await release.wait()
            return web.Response(
                body=assets[req.match_info["path"].split("/")[-1]], content_type="image/png"
            )
        assert req.headers.get("Authorization") in {
            "Bearer fixture-provider-access",
            "Bearer fixture-second-access",
        }
        if mode["provider_delay"]:
            entered.set()
            await release.wait()
        second = req.headers.get("Authorization") == "Bearer fixture-second-access"
        raw_track = deepcopy(TRACK)
        raw_artist = deepcopy(ARTIST)
        if mode["provider_art"] == "missing":
            raw_track["album"]["images"] = []
            raw_artist["images"] = []
        elif mode["provider_art"] == "conflicting":
            raw_track["album"]["id"] = "Z" * 22
            raw_artist["id"] = "Z" * 22
        if second:
            raw_track["id"] = "D" * 22
            raw_track["uri"] = "spotify:track:" + "D" * 22
            raw_track["album"]["id"] = "E" * 22
            raw_track["album"]["uri"] = "spotify:album:" + "E" * 22
            raw_track["album"]["images"][0]["url"] = "https://i.scdn.co/image/" + "d" * 40
            raw_artist["id"] = "F" * 22
            raw_artist["uri"] = "spotify:artist:" + "F" * 22
            raw_artist["images"][0]["url"] = "https://i.scdn.co/image/" + "d" * 40
        if req.path == "/v1/me/player/play":
            assert req.method == "PUT"
            return web.Response(status=204)
        if req.path == "/v1/me/player":
            return web.json_response(
                {
                    "is_playing": True,
                    "item": raw_track,
                    "context": {"type": "album", "uri": raw_track["album"]["uri"]},
                    "device": {"id": "fixture-output", "name": "Own fixture", "is_active": True},
                    "progress_ms": 0,
                }
            )
        if req.path == "/v1/me/player/devices":
            return web.json_response(
                {
                    "devices": [
                        {
                            "id": "fixture-output",
                            "name": "Own fixture",
                            "is_active": True,
                            "is_restricted": False,
                        }
                    ]
                }
            )
        if req.path.endswith("/recently-played"):
            return web.json_response({"items": [{"track": raw_track}]})
        if req.path.endswith("/top/artists"):
            return web.json_response({"items": [raw_artist]})
        if req.path.endswith("/top/tracks"):
            return web.json_response({"items": [raw_track]})
        return web.json_response({"error": {"message": "Fixture unavailable"}}, status=404)

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", provider)
    async with (
        TestClient(TestServer(app)) as upstream,
        TestClient(TestServer(hass.http.app)) as client,
    ):
        # Replace only the external network session. No Core normalizer/handler/store/cache/feed mock.
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
        s = await setting.json()
        assert setting.status == 200, s
        profile = await client.post(
            "/api/djconnect/v1/music_dna/profile", json=ident, headers=headers
        )
        body = await profile.json()
        assert profile.status == 200, body
        original_dna_track = body["profile"]["top_tracks_by_range"]["short_term"][0]
        # Actual HA Store save/load forces a second compaction before authorized feed.
        await rt.memory.async_save()
        rt.memory = MusicDNAManager(hass)
        await rt.memory.async_load()
        rt2.memory = rt.memory
        old_dna_image = await client.get(original_dna_track["image_url"])
        assert old_dna_image.status == 404  # Previous manager's grant is withdrawn.
        before_reloaded_profile_calls = len(network.calls)
        reloaded_profile = await client.post("/api/djconnect/v1/music_dna/profile", json=ident, headers=headers)
        body = await reloaded_profile.json()
        assert reloaded_profile.status == 200 and len(network.calls) == before_reloaded_profile_calls
        reloaded_dna_track = body["profile"]["top_tracks_by_range"]["short_term"][0]
        assert reloaded_dna_track["image_url"] != original_dna_track["image_url"]
        assert reloaded_dna_track["image_reference_expires_at"] == original_dna_track["image_reference_expires_at"]
        feed = await client.get("/api/djconnect/v1/music_discovery", params=ident, headers=headers)
        result = await feed.json()
        assert feed.status == 200, result
        items = [x for section in result["sections"] for x in section["items"]]
        assert any(x["kind"] == "track" for x in items) and any(
            x["kind"] == "artist" for x in items
        ), result
        record = {
            "assignment": "DJC-CORE-DISCOVERY-ARTWORK-CONTINUITY-V1-20261012",
            "base": os.environ.get("DJC_BASE_SHA", "90fa0463bb40c705c41d4025dc53aee4de514c79"),
            "integration_source_hashes": source_hashes,
            "ordinary_pair_auth": True,
            "core_mocked": False,
            "external_provider_network": "BOUNDED_LOOPBACK_FIXTURE_ONLY",
            "normalized_track_has_artwork": bool(_normalize_profile_track(TRACK).get("image_url")),
            "normalized_artist_has_artwork": bool(
                _normalize_profile_artist(ARTIST).get("image_url")
            ),
            "stored_top_track_has_artwork": bool(
                rt.memory.data["memories"][body["music_dna_key"]]["listening_profile"]["top_tracks_by_range"]["short_term"][0].get("artwork")
            ),
            "stored_top_artist_has_artwork": bool(
                rt.memory.data["memories"][body["music_dna_key"]]["listening_profile"]["top_artists_by_range"]["short_term"][0].get("artwork")
            ),
            "actual_store_reloaded": True,
            "feed": result,
            "provider_calls": network.calls,
            "native": "NOT_RUN",
            "installed": "NOT_RUN",
            "live_spotify": "NOT_RUN",
        }
        assert record["stored_top_track_has_artwork"] and record["stored_top_artist_has_artwork"]
        cases = {}
        # Current profile output must contain loadable leases, not private Store refs.
        assert "asset_id" not in json.dumps(body) and '"artwork"' not in json.dumps(body)
        dna_items = [body["profile"]["top_tracks_by_range"]["short_term"][0],
                     body["profile"]["top_artists_by_range"]["short_term"][0]]
        for dna_item in dna_items:
            assert dna_item["image_subject_uri"] == dna_item["uri"]
            assert dna_item["image_expires_at"] <= dna_item["image_reference_expires_at"]
            dna_image = await client.get(dna_item["image_url"])
            assert dna_image.status == 200
            assert await dna_image.read() == assets["a" * 40 if dna_item["uri"].startswith("spotify:track:") else "c" * 40]
            assert dna_image.headers["Cache-Control"] == "private, no-store"
        before_profile_read_calls = len(network.calls)
        repeat_profile = await client.post("/api/djconnect/v1/music_dna/profile", json=ident, headers=headers)
        repeat_body = await repeat_profile.json()
        assert repeat_profile.status == 200 and len(network.calls) == before_profile_read_calls
        assert repeat_body["profile"]["top_tracks_by_range"]["short_term"][0]["image_reference_expires_at"] == dna_items[0]["image_reference_expires_at"]
        record["music_dna_profile"] = body
        cases["music_dna_store_reload_original_clock_and_new_grant"] = True
        cases["music_dna_track_artist_actual_image_route"] = "200_EXACT_FIXTURE_BYTES_NO_STORE"
        cases["music_dna_repeat_profile_no_provider_or_reference_renewal"] = True
        images = []
        for item in items:
            image = await client.get(item["image_url"])
            raw = await image.read()
            assert image.status == 200 and image.headers["Cache-Control"] == "private, no-store"
            asset = "a" * 40 if item["kind"] == "track" else "c" * 40
            assert raw == assets[asset]
            images.append(
                {
                    "kind": item["kind"],
                    "media_uri": item["image_attribution"]["media_uri"],
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                    "decode": "PNG64x64",
                }
            )
            (LAB / (item["kind"] + ".png")).write_bytes(raw)
        track = next(i for i in items if i["kind"] == "track")
        image_url = track["image_url"]
        bad = await client.get(
            image_url, headers={**headers, "Authorization": "Bearer wrong-device-token"}
        )
        assert bad.status == 401
        cases["wrong_bearer"] = bad.status
        # Existing pairing selects the currently configured setup slot.
        hass.data["djconnect"]["runtime"] = rt2
        second_pair = await client.post(
            "/api/djconnect/v1/pair", json={**ident2, "pair_code": "654321"}
        )
        second_auth = await second_pair.json()
        assert second_pair.status == 200, {
            "status": second_pair.status,
            "error": second_auth.get("error"),
        }
        hass.data["djconnect"]["runtime"] = rt
        second_headers = {
            "Authorization": "Bearer " + second_auth["device_token"],
            "X-DJConnect-Device-ID": ident2["device_id"],
            "X-DJConnect-Client-Type": "ios",
        }
        setting2 = await client.post(
            "/api/djconnect/v1/music_dna/settings",
            json={**ident2, "enabled": True},
            headers=second_headers,
        )
        assert setting2.status == 200
        profile2 = await client.post(
            "/api/djconnect/v1/music_dna/profile", json=ident2, headers=second_headers
        )
        assert profile2.status == 200, await profile2.text()
        feed2 = await client.get(
            "/api/djconnect/v1/music_discovery", params=ident2, headers=second_headers
        )
        second_feed = await feed2.json()
        assert feed2.status == 200, second_feed
        second_items = [i for sec in second_feed["sections"] for i in sec["items"]]
        assert {i["uri"] for i in items}.isdisjoint({i["uri"] for i in second_items})
        second_track = next(i for i in second_items if i["kind"] == "track")
        other_image = await client.get(second_track["image_url"])
        assert other_image.status == 200 and await other_image.read() == assets["d" * 40]
        wrong_profile = await client.get(image_url, headers=second_headers)
        assert wrong_profile.status == 401
        cases["two_profile_wrong_credentials"] = wrong_profile.status
        # Same display names do not borrow the other Profile's exact media/asset.
        assert track["title"] == second_track["title"] and track["uri"] != second_track["uri"]
        cases["same_name_two_profile_exact_identity"] = "DISTINCT_URI_AND_ASSET"
        # Test authority already revoked before a new guard can be captured.
        old_entry_data = dict(slot.data)
        hass.config_entries.async_update_entry(
            slot, data={**old_entry_data, "device_token": "rotated-persisted-only"}
        )
        revoked = await client.get(image_url)
        assert revoked.status == 404
        cases["persisted_pairing_rotation"] = revoked.status
        guard = await capture_refresh_guard(
            rt, {**ident, "music_dna_key": "profile:artwork-profile"}
        )
        assert not guard.valid()
        hass.config_entries.async_update_entry(slot, data=old_entry_data)
        # Ordinary feed renews a usable capability after prior owner-state change.
        renewed = await client.get(
            "/api/djconnect/v1/music_discovery", params=ident, headers=headers
        )
        renewed_feed = await renewed.json()
        assert renewed.status == 200, renewed_feed
        image_url = next(
            i["image_url"]
            for sec in renewed_feed["sections"]
            for i in sec["items"]
            if i["kind"] == "track"
        )
        assert not any(call["method"] in {"POST", "PUT", "DELETE"} for call in network.calls)
        cases["feed_image_reads_playback_free"] = True
        # An arbitrary unshown Play Now must still be rejected. Legacy accepted
        # records below are explicit synthetic Store inputs, not playback authority.
        accepted = await client.post(
            "/api/djconnect/v1/command",
            json={
                **ident,
                "command": "ask_dj_play_recommendation",
                "value": {
                    "uri": TRACK["album"]["uri"],
                    "kind": "album",
                    "title": "Fixture album",
                    "subtitle": "Fixture artist",
                },
                "audio_response": "never",
            },
            headers=headers,
        )
        accepted_body = await accepted.json()
        assert accepted.status == 409 and accepted_body.get("error") == "choice_expired"
        cases["unshown_recommendation_still_rejected"] = "409_CHOICE_EXPIRED"
        # Seed the same compact legacy shape that predates artwork retention.
        # This is disposable server-side fixture data; no playback call is made.
        record_key = "profile:artwork-profile"
        legacy_memory = rt.memory.data["memories"][record_key]
        legacy_memory["recommendation_plays"] = [{
            "uri": TRACK["album"]["uri"], "kind": "album",
            "title": "Fixture album", "subtitle": "Fixture artist",
            "source_intent": "personal_music_recommendations",
        }]
        await rt.memory.async_save()
        album_profile = await client.post("/api/djconnect/v1/music_dna/profile", json=ident, headers=headers)
        album_profile_body = await album_profile.json()
        assert album_profile.status == 200
        album_projection = next(i for i in album_profile_body["profile"]["recommendation_signals"] if i["uri"] == TRACK["album"]["uri"])
        assert album_projection["image_subject_uri"] == TRACK["album"]["uri"]
        assert album_projection["image_attribution"]["media_uri"] == TRACK["album"]["uri"]
        album_profile_image = await client.get(album_projection["image_url"])
        assert album_profile_image.status == 200 and await album_profile_image.read() == assets["a" * 40]
        record["music_dna_exact_album"] = album_projection
        cases["music_dna_album_exact_provider_edition_image"] = "200_EXACT_FIXTURE_BYTES"
        album_feed_response = await client.get(
            "/api/djconnect/v1/music_discovery", params=ident, headers=headers
        )
        album_feed = await album_feed_response.json()
        assert album_feed_response.status == 200, album_feed
        album_item = next(
            i for sec in album_feed["sections"] for i in sec["items"] if i["kind"] == "album"
        )
        assert (
            album_item["uri"] == TRACK["album"]["uri"]
            and album_item["image_attribution"]["media_uri"] == TRACK["album"]["uri"]
        )
        album_image = await client.get(album_item["image_url"])
        assert album_image.status == 200 and await album_image.read() == assets["a" * 40]
        cases["existing_album_positive_exact_reference"] = {
            "image_status": 200,
            "uri": album_item["uri"],
            "provider_boundary": "SYNTHETIC_LEGACY_STORE_INPUT_NO_PLAYBACK",
        }
        exported_response = await client.post(
            "/api/djconnect/v1/music_dna/export", json=ident, headers=headers
        )
        exported = await exported_response.json()
        assert exported_response.status == 200
        assert "asset_id" not in json.dumps(exported) and "image_proxy" not in json.dumps(exported)
        legacy = deepcopy(exported["profile"])
        legacy["profile"]["listening_profile"] = {
            "top_tracks_by_range": {"short_term": [deepcopy(_normalize_profile_track(TRACK))]},
            "last_profile_refresh": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat(),
            "artwork_reference_version": 1,
        }
        legacy["profile"]["listening_profile"]["top_tracks_by_range"]["short_term"][0][
            "image_url"
        ] = "http://127.0.0.1/forbidden-import"
        imported = await client.post(
            "/api/djconnect/v1/music_dna/import", json={**ident, "profile": legacy}, headers=headers
        )
        import_body = await imported.json()
        assert imported.status == 200, import_body
        assert "asset_id" not in json.dumps(import_body) and "forbidden-import" not in json.dumps(
            import_body
        )
        await rt.memory.async_save()
        rt.memory = MusicDNAManager(hass)
        await rt.memory.async_load()
        rt2.memory = rt.memory
        prior_calls = len(network.calls)
        restored = await client.get(
            "/api/djconnect/v1/music_discovery",
            params={
                **ident,
                "music_dna_key": "profile:artwork-second-profile",
                "user_id": "untrusted",
            },
            headers=headers,
        )
        restored_feed = await restored.json()
        assert restored.status == 200, restored_feed
        assert restored_feed["music_dna_key"] == "profile:artwork-profile"
        restored_track = next(
            i for sec in restored_feed["sections"] for i in sec["items"] if i["kind"] == "track"
        )
        assert restored_track.get("image_url") and any(
            c["path"].endswith("/top/tracks") for c in network.calls[prior_calls:]
        )
        restored_image = await client.get(restored_track["image_url"])
        assert restored_image.status == 200 and await restored_image.read() == assets["a" * 40]
        image_url = restored_track["image_url"]
        cases["ordinary_old_store_refresh_no_clear_or_pair"] = "RESTORED_EXACT_ASSET"
        cases["malicious_import_and_export_no_artwork_grants"] = "STRIPPED"
        cases["client_dna_key_and_user_id_cannot_cross_profile"] = "CANONICAL_PROFILE"
        if os.environ.get("DJC_ARTWORK_SKIP_BROWSER") == "1":
            cases["actual_browser_decode"] = "NOT_RUN_ISOLATED_CONTAINER"
        else:
            # Browser reads the actual headerless HA image route; only HTML is an owned test surface.
            base = str(client.make_url("/")).rstrip("/")
            browser_script = LAB / "decode.mjs"
            browser_script.write_text(
                "import {chromium} from '/Volumes/Extra Data/DevelopmentTemp/djc-core-expressive-context-resume-v1/node_modules/playwright/index.mjs';const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});const page=await browser.newPage();await page.goto(process.argv[2]);await page.setContent('<h1>Core artwork transport fixture</h1>'+process.argv.slice(3).map(u=>'<img width=256 height=256 src=\"'+u+'\">').join(''));const sizes=await page.locator('img').evaluateAll(async imgs=>{await Promise.all(imgs.map(i=>i.decode()));return imgs.map(i=>[i.naturalWidth,i.naturalHeight]);});if(sizes.some(s=>s[0]!==64||s[1]!==64))throw Error('decode');await page.screenshot({path:'/private/tmp/djc-core-discovery-artwork-v1/transport.png'});console.log(JSON.stringify(sizes));await browser.close();"
            )
            proc = await asyncio.create_subprocess_exec(
                "/opt/homebrew/bin/node",
                str(browser_script),
                base,
                *(
                    base + i["image_url"]
                    for sec in restored_feed["sections"]
                    for i in sec["items"]
                    if i.get("image_url")
                ),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            assert proc.returncode == 0, err.decode()
            cases["actual_browser_decode"] = json.loads(out)
        for name in ("redirect", "html", "large", "mime", "upstream_error", "chunked_large", "timeout"):
            mode["value"] = name
            failed = await client.get(image_url)
            assert failed.status == 502, (name, failed.status)
            cases[name] = failed.status
        mode["value"] = "delay"
        late = asyncio.create_task(client.get(image_url))
        await asyncio.wait_for(entered.wait(), 5)
        clear = await client.post("/api/djconnect/v1/music_dna/clear", json=ident, headers=headers)
        assert clear.status == 200
        release.set()
        late_response = await late
        assert late_response.status == 404
        cases["inflight_clear"] = late_response.status
        mode["value"] = "ok"
        expired = await client.get(image_url)
        assert expired.status == 404
        cases["cleared_grant"] = expired.status
        # Rate-limited cached refresh must not return a cleared feed/image.
        before_refresh_calls = len(network.calls)
        after = await client.post(
            "/api/djconnect/v1/music_discovery/refresh", json=ident, headers=headers
        )
        after_json = await after.json()
        assert after.status == 200
        cases["clear_refresh_image_count"] = sum(
            bool(i.get("image_url"))
            for sec in after_json.get("sections", [])
            for i in sec.get("items", [])
        )
        assert any(c["path"].endswith("/top/tracks") for c in network.calls[before_refresh_calls:])
        current_key = "profile:artwork-profile"
        current_memory = rt.memory.data["memories"][current_key]
        clear_time = (
            __import__("datetime")
            .datetime.fromisoformat(current_memory["clear_requested_at"])
            .timestamp()
        )
        refs = [
            i["artwork"]
            for rows in current_memory["listening_profile"]["top_tracks_by_range"].values()
            for i in rows
            if i.get("artwork")
        ]
        assert refs and all(ref["captured_at"] >= clear_time for ref in refs)
        cases["clear_explicit_refresh_relearns_only_fresh_provider"] = {
            "new_provider_fetch": True,
            "new_capture_after_clear": True,
            "old_grant_status": 404,
        }
        # Delayed provider publication cannot survive consent ABA or all-clear ABA.
        key = next(k for k in rt.memory.data["memories"] if k.startswith("profile:"))
        original = deepcopy(body["profile"])
        for name in ("off_on", "clear_all"):
            guard = await capture_refresh_guard(rt, {"music_dna_key": key, **ident})
            assert guard is not None
            if name == "off_on":
                await rt.memory.async_set_enabled(rt, False, {"music_dna_key": key})
                await rt.memory.async_set_enabled(rt, True, {"music_dna_key": key})
            else:
                await rt.memory.async_clear()
                await rt.memory.async_set_enabled(rt, True, {"music_dna_key": key})
            await rt.memory.async_update_listening_profile(
                rt, original, {"music_dna_key": key}, refresh_guard=guard
            )
            assert not rt.memory.data["memories"][key].get("listening_profile")
            cases[name] = "REJECTED_LATE_REFRESH"
        entered.clear()
        release.clear()
        mode["provider_delay"] = True
        pending = asyncio.create_task(
            client.post("/api/djconnect/v1/music_dna/profile", json=ident, headers=headers)
        )
        await asyncio.wait_for(entered.wait(), 5)
        opted = await client.post(
            "/api/djconnect/v1/music_dna/settings",
            json={**ident, "enabled": False},
            headers=headers,
        )
        assert opted.status == 200
        opted_on = await client.post(
            "/api/djconnect/v1/music_dna/settings", json={**ident, "enabled": True}, headers=headers
        )
        assert opted_on.status == 200
        release.set()
        mode["provider_delay"] = False
        late_profile = await pending
        late_body = await late_profile.json()
        assert late_profile.status == 409 and late_body == {
            "success": False,
            "error": "music_dna_context_changed",
        }, late_body
        assert not rt.memory.data["memories"][key].get("listening_profile")
        cases["actual_provider_consent_aba"] = late_profile.status
        # Ordinary authorized read must accept supported OAuth rotation while
        # the same canonical account/provider still owns the result.
        rt.spotify_access_token = None
        rt.spotify_access_token_expires_at = 0
        rt.backend_cache.clear()
        rotation = await client.post(
            "/api/djconnect/v1/music_dna/profile", json=ident, headers=headers
        )
        rotation_body = await rotation.json()
        assert rotation.status == 200, rotation_body
        assert slot.data["spotify_refresh_token"] == "fixture-rotated-provider-only"
        assert any(c["path"] == "/api/token" for c in network.calls)
        cases["actual_oauth_rotation_same_provider"] = {"status": 200, "persisted": True}
        # Replacement of the actual registered provider during external I/O
        # must reject old data, even though its ConfigEntry/account names match.
        await rt.memory.async_clear(key)
        rt.backend_cache.clear()
        entered.clear()
        release.clear()
        mode["provider_delay"] = True
        pending = asyncio.create_task(client.post(
            "/api/djconnect/v1/music_dna/profile", json=ident, headers=headers
        ))
        await asyncio.wait_for(entered.wait(), 5)
        replacement = DJConnectRuntime(slot)
        replacement.memory = rt.memory
        replacement.device_token = rt.device_token
        hass.data["djconnect"][slot.entry_id] = replacement
        release.set()
        mode["provider_delay"] = False
        replaced = await pending
        replaced_body = await replaced.json()
        assert replaced.status == 409 and replaced_body == {
            "success": False, "error": "music_dna_context_changed"
        }, replaced_body
        assert not rt.memory.data["memories"][key].get("listening_profile")
        cases["actual_provider_replaced_inflight"] = replaced.status
        hass.data["djconnect"][slot.entry_id] = rt
        # A bounded, authorized Store input with a soon-expiring original
        # reference exercises actual wall-clock expiry, never a mocked clock.
        restored_profile = await client.post(
            "/api/djconnect/v1/music_dna/profile", json=ident, headers=headers
        )
        assert restored_profile.status == 200, await restored_profile.text()
        memory = rt.memory.data["memories"][key]
        now = time.time()
        def shorten_refs(value):
            if isinstance(value, dict):
                ref = value.get("artwork")
                if isinstance(ref, dict):
                    ref["captured_at"] = now - 21600 + 3
                    ref["expires_at"] = now + 3
                for child in value.values():
                    shorten_refs(child)
            elif isinstance(value, list):
                for child in value:
                    shorten_refs(child)
        shorten_refs(memory)
        await rt.memory.async_save()
        rt.memory = MusicDNAManager(hass)
        await rt.memory.async_load()
        rt2.memory = rt.memory
        expiry_feed = await client.get(
            "/api/djconnect/v1/music_discovery", params=ident, headers=headers
        )
        expiry_json = await expiry_feed.json()
        expiry_item = next(i for sec in expiry_json["sections"] for i in sec["items"] if i.get("image_url"))
        expiry_profile = await client.post("/api/djconnect/v1/music_dna/profile", json=ident, headers=headers)
        expiry_profile_body = await expiry_profile.json()
        assert expiry_profile.status == 200
        expiry_profile_track = expiry_profile_body["profile"]["top_tracks_by_range"]["short_term"][0]
        assert expiry_profile_track["image_expires_at"] <= now + 3
        before_expiry = await client.get(expiry_item["image_url"])
        assert before_expiry.status == 200
        await asyncio.sleep(max(0, now + 3 - time.time() + .1))
        after_expiry = await client.get(expiry_item["image_url"])
        assert after_expiry.status == 404
        expired_profile_image = await client.get(expiry_profile_track["image_url"])
        assert expired_profile_image.status == 404
        expired_profile = await client.post("/api/djconnect/v1/music_dna/profile", json=ident, headers=headers)
        expired_profile_body = await expired_profile.json()
        assert expired_profile.status == 200
        assert "image_url" not in json.dumps(expired_profile_body)
        assert "asset_id" not in json.dumps(expired_profile_body)
        cases["music_dna_actual_original_expiry"] = "REAL_WALL_CLOCK_200_TO_404_THEN_OMITTED"
        expired_feed = await client.get(
            "/api/djconnect/v1/music_discovery", params=ident, headers=headers
        )
        expired_json = await expired_feed.json()
        assert expired_feed.status == 200, expired_json
        assert all(not {"image_url", "image_expires_at", "image_attribution"}.intersection(i)
                   for sec in expired_json["sections"] for i in sec["items"])
        cases["actual_original_reference_expiry"] = {
            "before_status": 200, "expired_status": 404,
            "all_three_optional_fields_absent": True,
            "clock": "REAL_WALL_CLOCK", "input": "BOUNDED_ORIGINAL_STORE_REFERENCE",
        }
        for provider_art in ("missing", "conflicting"):
            mode["provider_art"] = provider_art
            await rt.memory.async_clear(key)
            rt.backend_cache.clear()
            ordinary = await client.get(
                "/api/djconnect/v1/music_discovery", params=ident, headers=headers
            )
            ordinary_body = await ordinary.json()
            assert ordinary.status == 200, ordinary_body
            assert ordinary_body["sections"], "Existing safe fallback must remain available"
            assert all(not i.get("image_url") for sec in ordinary_body["sections"] for i in sec["items"])
            calls_after = len(network.calls)
            repeat = await client.get(
                "/api/djconnect/v1/music_discovery", params=ident, headers=headers
            )
            assert repeat.status == 200
            assert len(network.calls) == calls_after, "Missing artwork must not cause a refresh loop"
            cases["actual_" + provider_art + "_provider_art"] = {
                "placeholder": True, "existing_fallback": True, "repeat_provider_calls": 0,
            }
        mode["provider_art"] = "valid"
        if os.environ.get("DJC_ARTWORK_LEASE_PROOF") == "1":
            await rt.memory.async_clear(key)
            rt.backend_cache.clear()
            restore = await client.post(
                "/api/djconnect/v1/music_dna/profile", json=ident, headers=headers
            )
            assert restore.status == 200, await restore.text()
            first_feed = await client.get(
                "/api/djconnect/v1/music_discovery", params=ident, headers=headers
            )
            first_json = await first_feed.json()
            lease_item = next(
                i for sec in first_json["sections"] for i in sec["items"] if i.get("image_url")
            )
            lease_url = lease_item["image_url"]
            deadline = lease_item["image_expires_at"]
            original_profile = deepcopy(rt.memory.data["memories"][key]["listening_profile"])
            lease_entered = time.time()
            (LAB / "lease-start.json").write_text(
                json.dumps(
                    {
                        "expires_at": deadline,
                        "wait_seconds": deadline - time.time() + 1,
                        "scope": "OWN_ISOLATED_HA_ONLY",
                    }
                )
            )
            await asyncio.sleep(max(0, deadline - time.time() + 1))
            gone = await client.get(lease_url)
            assert gone.status == 404
            refreshed = await client.get(
                "/api/djconnect/v1/music_discovery", params=ident, headers=headers
            )
            refresh_json = await refreshed.json()
            fresh_item = next(
                i
                for sec in refresh_json["sections"]
                for i in sec["items"]
                if i["id"] == lease_item["id"]
            )
            assert refresh_json["cache"]["hit"] and fresh_item["image_url"] != lease_url
            fresh_image = await client.get(fresh_item["image_url"])
            assert fresh_image.status == 200
            assert original_profile == rt.memory.data["memories"][key]["listening_profile"]
            cases["real_900s_lease_expiry_and_cached_renewal"] = {
                "expired_status": gone.status,
                "new_status": fresh_image.status,
                "reference_not_renewed": True,
                "cache_hit": True,
                "real_elapsed_seconds": time.time() - lease_entered,
            }
        assert source_hashes == {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "custom_components/djconnect").rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        }, "Integration changed during qualification"
        record["images"] = images
        record["cases"] = cases
        # Tokens are capabilities. Persist only redacted contract fixtures and private proof hashes.
        for section in record["feed"]["sections"]:
            for item in section["items"]:
                item["image_url"] = "/api/djconnect/v1/image_proxy/disc-<opaque-redacted>"
        def redact_delivery(value):
            if isinstance(value, dict):
                return {k: "/api/djconnect/v1/image_proxy/disc-<opaque-redacted>" if k == "image_url" else redact_delivery(v) for k, v in value.items()}
            if isinstance(value, list):
                return [redact_delivery(v) for v in value]
            return value
        record["music_dna_profile"] = redact_delivery(record["music_dna_profile"])
        record["music_dna_exact_album"] = redact_delivery(record["music_dna_exact_album"])
        (
            LAB
            / (
                "qualification-lease.json"
                if os.environ.get("DJC_ARTWORK_LEASE_PROOF") == "1"
                else "qualification.json"
            )
        ).write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({k: v for k, v in record.items()
                          if k not in ("feed", "provider_calls", "integration_source_hashes")}))
        cache.pop(
            key
            if False
            else aiohttp_client._make_key(
                True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT
            )
        )
    await hass.async_stop()


asyncio.run(main())
