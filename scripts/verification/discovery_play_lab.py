"""Disposable paired HA Discovery transaction proof; external Spotify wires only."""

from __future__ import annotations
import asyncio
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from aiohttp import web

ARTIST = "C" * 22
PLAYLIST = "D" * 22
TRACK = "A" * 22
STATE = {
    "denied": False,
    "empty_search": False,
    "no_output": False,
    "context": "spotify:playlist:" + "O" * 22,
    "writes": 0,
    "disconnect_write": False,
    "block_search": False,
    "block_token": False,
}
ENTERED = asyncio.Event()
RELEASE = asyncio.Event()


async def provider_reply(req):
    path = req.path
    if path == "/api/token" and STATE["block_token"]:
        ENTERED.set()
        await RELEASE.wait()
        return web.json_response({"access_token": "fixture-refreshed-access", "expires_in": 3600})
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
        "album": {"name": "Fixture album", "id": "B" * 22, "uri": "spotify:album:" + "B" * 22},
    }
    playlist = {
        "id": PLAYLIST,
        "uri": "spotify:playlist:" + PLAYLIST,
        "type": "playlist",
        "name": "This is Fixture artist",
        "owner": {"id": "spotify"},
    }
    if path == "/v1/artists/" + ARTIST:
        return web.json_response(artist)
    if path == "/v1/search" and req.query.get("type") == "playlist":
        assert req.query.get("limit") == "10"
        if STATE["block_search"]:
            ENTERED.set()
            await RELEASE.wait()
        return web.json_response(
            {"playlists": {"items": [] if STATE["empty_search"] else [playlist]}}
        )
    if path in {"/v1/playlists/" + PLAYLIST, "/v1/playlists/" + PLAYLIST + "/items"}:
        if STATE["denied"]:
            return web.json_response({"error": {"message": "Synthetic access denial"}}, status=403)
        return web.json_response(
            {**playlist, "items": {"items": [{"item": track}]}}
            if path.endswith(PLAYLIST)
            else {"items": [{"item": track}]}
        )
    if path == "/v1/me/player" and req.method == "GET":
        device = (
            {}
            if STATE["no_output"]
            else {"id": "fixture-output", "is_active": True, "is_restricted": False}
        )
        return web.json_response(
            {"device": device, "context": {"uri": STATE["context"]}, "item": track}
        )
    if path == "/v1/me/player/play":
        assert req.method == "PUT" and req.query.get("device_id") == "fixture-output"
        STATE["writes"] += 1
        body = await req.json()
        assert set(body) in [{"context_uri"}, {"uris"}]
        if STATE["denied"]:
            return web.json_response({"error": {"message": "Synthetic play denial"}}, status=403)
        STATE["context"] = body.get("context_uri", "")
        if STATE["disconnect_write"]:
            req.transport.close()
        return web.Response(status=204)
    return None


async def run(*, hass, runtime, client, headers, identity, network, output, source_hashes):
    from custom_components.djconnect.music_discovery import _cache

    cases = {}
    wires = {}

    async def post(path, payload):
        r = await client.post("/api/djconnect/v1" + path, json=payload, headers=headers)
        body = await r.json()
        assert r.status == 200, (r.status, body)
        return body

    await post("/music_dna/profile", identity)

    async def card(kind="artist"):
        _cache(runtime).clear()
        r = await client.get("/api/djconnect/v1/music_discovery", params=identity, headers=headers)
        feed = await r.json()
        assert r.status == 200 and feed.get("enabled"), feed
        for section in feed["sections"]:
            for item in section["items"]:
                if item["kind"] == kind:
                    return {
                        **identity,
                        "section_id": section["id"],
                        "discovery_item_id": item["id"],
                    }
        raise AssertionError((kind, feed))

    def feedback_count():
        return len(
            runtime.memory.data["memories"]["profile:artwork-profile"].get("discovery_plays", [])
        )

    payload = await card()
    before = feedback_count()
    result = await post("/music_discovery/play", payload)
    assert result["success"] and result["played"] and result["music_dna_feedback_recorded"], result
    assert result["action_outcome"]["readback_confirmed"] and STATE["writes"] == 1
    assert STATE["context"] == "spotify:playlist:" + PLAYLIST and feedback_count() == before + 1
    wires["artist_success"] = result
    cases["artist_real_cached_card_official_playlist_one_context_write"] = "PASS"
    duplicate = await post("/music_discovery/play", payload)
    assert (
        not duplicate["played"]
        and duplicate["error"] == "music_discovery_already_attempted"
        and STATE["writes"] == 1
    )
    wires["duplicate_original_card"] = duplicate
    cases["duplicate_original_card_no_second_write"] = "PASS"
    payload = await card("track")
    before_writes = STATE["writes"]
    result = await post("/music_discovery/play", payload)
    assert result["played"] and STATE["writes"] == before_writes + 1, result
    cases["track_uses_single_track_selection"] = "PASS"
    STATE["empty_search"] = True
    payload = await card()
    before_writes, before_feedback = STATE["writes"], feedback_count()
    result = await post("/music_discovery/play", payload)
    assert not result["played"] and result["error"] == "music_discovery_this_is_not_found", result
    assert STATE["writes"] == before_writes and feedback_count() == before_feedback
    cases["search_miss_is_not_nonexistence_or_permission_denial"] = "PASS"
    probe = {
        **identity,
        "command": "discovery_playlist_identity",
        "play": False,
        "value": {
            "artist_uri": "spotify:artist:" + ARTIST,
            "playlist_uri": "spotify:playlist:" + PLAYLIST,
        },
    }
    result = await post("/command", probe)
    assert result["success"] and result["read_only"] and not result["dispatch_authority"], result
    assert STATE["writes"] == before_writes and feedback_count() == before_feedback
    wires["direct_candidate_read"] = result
    cases["explicit_candidate_read_works_when_search_omits_it_without_play_permission"] = "PASS"
    STATE["empty_search"] = False
    STATE["denied"] = True
    result = await post("/command", probe)
    assert not result["success"] and result["error"] == "music_discovery_playlist_access_denied", (
        result
    )
    assert result["provider_http_status"] == 403 and STATE["writes"] == before_writes
    wires["direct_candidate_denied"] = result
    cases["actual_403_distinguished_from_search_miss"] = "PASS"
    payload = await card()
    before_feedback = feedback_count()
    result = await post("/music_discovery/play", payload)
    assert (
        not result["played"]
        and not result["music_dna_feedback_recorded"]
        and feedback_count() == before_feedback
    )
    cases["denied_artist_resolution_no_play_or_positive_feedback"] = "PASS"
    payload = await card("track")
    before_feedback = feedback_count()
    result = await post("/music_discovery/play", payload)
    assert not result["played"] and not result["music_dna_feedback_recorded"], result
    assert feedback_count() == before_feedback and STATE["writes"] == before_writes + 1
    before_writes = STATE["writes"]
    wires["rejected_transport"] = result
    cases["rejected_transport_never_claims_played_or_positive_feedback"] = "PASS"
    STATE["denied"] = False
    STATE["no_output"] = True
    payload = await card()
    before_writes = STATE["writes"]
    result = await post("/music_discovery/play", payload)
    assert not result["played"] and result["error"] == "music_discovery_output_required", result
    assert STATE["writes"] == before_writes
    wires["output_required"] = result
    cases["missing_output_no_transfer_or_automatic_retry"] = "PASS"
    STATE["no_output"] = False
    for expired in [True, False]:
        payload = await card()
        for cached in _cache(runtime).values():
            cached["generated_at"] += timedelta(seconds=-1801 if expired else 10)
        result = await post("/music_discovery/play", payload)
        assert not result["played"] and result["error"] == "music_discovery_context_changed", result
        assert STATE["writes"] == before_writes
    cases["expired_and_future_original_cache_rejected"] = "PASS"
    payload = await card()
    replies = await asyncio.gather(
        post("/music_discovery/play", payload), post("/music_discovery/play", payload)
    )
    assert sum(bool(x["played"]) for x in replies) == 1 and STATE["writes"] == before_writes + 1
    cases["concurrent_same_card_single_write"] = "PASS"
    payload = await card("track")
    STATE["disconnect_write"] = True
    before_writes, before_feedback = STATE["writes"], feedback_count()
    result = await post("/music_discovery/play", payload)
    STATE["disconnect_write"] = False
    assert not result["played"] and result["action_outcome"]["state"] == "unknown", result
    assert result["error"] == "music_discovery_write_outcome_unknown", result
    assert not result["retry_automatically"] and STATE["writes"] == before_writes + 1
    assert feedback_count() == before_feedback
    wires["connection_lost_after_write"] = result
    cases["actual_aiohttp_disconnect_no_implicit_second_put"] = "PASS"
    for wait in ["search", "token"]:
        payload = await card()
        STATE["block_" + wait] = True
        ENTERED.clear()
        RELEASE.clear()
        if wait == "token":
            runtime.spotify_access_token = None
            runtime.spotify_access_token_expires_at = 0
        before_writes, before_feedback = STATE["writes"], feedback_count()
        pending = asyncio.create_task(post("/music_discovery/play", payload))
        await asyncio.wait_for(ENTERED.wait(), 5)
        original = runtime.device_token
        runtime.device_token = "fixture-replaced-token"
        RELEASE.set()
        result = await pending
        runtime.device_token = original
        STATE["block_" + wait] = False
        assert not result["played"] and result["error"] == "music_discovery_context_changed", result
        assert STATE["writes"] == before_writes and feedback_count() == before_feedback
        cases["pairing_change_during_" + wait + "_wait_no_effect"] = "PASS"
    assert not any(
        c["path"] in {"/v1/me/player/queue", "/v1/me/player"} and c["method"] != "GET"
        for c in network.calls
    )
    record = {
        "cases": cases,
        "wire_examples": wires,
        "source_pins": source_hashes,
        "actual_home_assistant": True,
        "ordinary_pairing": True,
        "external_provider_wires_only": True,
        "real_provider_calls": 0,
        "real_model_calls": 0,
        "installed_mutations": 0,
        "dispatches_are_synthetic": True,
        "aiohttp_default_retry_client": True,
        "native_acceptance": "NOT_RUN",
        "provider_calls": network.calls,
        "source_unchanged": True,
    }
    current = {
        str(p.relative_to(Path(__file__).resolve().parents[2])): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in (Path(__file__).resolve().parents[2] / "custom_components/djconnect").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert current == source_hashes
    (output / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    print("DISCOVERY_PLAY_PASS", len(cases), flush=True)
