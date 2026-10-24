"""Actual HA paired HTTP with synthetic playback/CDN/reply boundaries only."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
import hashlib
import json
import os
import socket
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import (
        DJConnectRuntime,
        api_handlers,
        http,
        ask_dj,
        session_artwork,
    )
    from custom_components.djconnect.domain.music_account import MusicAccountKind
    from custom_components.djconnect.ask_dj.dialogue import current_turn
    from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.spotify_backend import SpotifyBackendError

    domain = hass.data["djconnect"]
    runtime = domain["owner-entry"]
    storage = domain["djconnect_profile_platform"]
    source_entry = hass.config_entries.async_get_entry("source-entry")
    hass.config_entries.async_update_entry(
        source_entry,
        data={**source_entry.data, "music_backend": "source-spotify", "profile_id": "profile-a"},
    )
    hass.config_entries.async_update_entry(
        runtime.entry,
        data={
            **runtime.entry.data,
            "music_backend": "source-spotify",
            "music_account_id": "source-account",
            "profile_backend_entry_id": "source-entry",
        },
    )
    domain["source-entry"] = DJConnectRuntime(source_entry)
    await storage.async_upsert_music_account(
        "source-account",
        "source-spotify",
        kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic original account",
        linked_profile_ids=frozenset({"profile-a"}),
        provider_account_id="original-provider",
    )
    await storage.async_update_profile(
        "profile-a",
        preferences=replace(
            storage.household.profiles["profile-a"].preferences,
            default_backend_id="source-spotify",
            default_music_account_id="source-account",
        ),
    )
    original_source = {
        "backend_id": "source-spotify",
        "music_account_id": "source-account",
        "provider_entry_id": "source-entry",
        "provider_account_id": "original-provider",
    }
    active = manager.current_active("profile-a")
    if active:
        await manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
    old = await manager.async_start(
        owner_profile_id="profile-a",
        music_backend="spotify_direct",
        history_source_context=original_source,
    )
    await manager.async_update_playback_projection(
        owner_profile_id="profile-a",
        session_id=old.session_id,
        state="playing",
        media_identity="spotify:track:" + "A" * 22,
        title="Synthetic original recording",
        artist="Synthetic artist",
        album="Synthetic original edition",
        album_uri="spotify:album:" + "B" * 22,
    )
    repo = HistoricalProjectionRepository(persistence_service(hass))
    row = next(
        r
        for r in await repo.async_entry_records("profile-a", old.session_id)
        if r["kind"] == "playback_observed"
    )
    await manager.async_end(owner_profile_id="profile-a", session_id=old.session_id)
    active = await manager.async_start(
        owner_profile_id="profile-a",
        music_backend="spotify_direct",
        history_source_context=original_source,
    )
    await manager.async_update_playback_projection(
        owner_profile_id="profile-a",
        session_id=active.session_id,
        state="playing",
        media_identity="spotify:track:" + "Z" * 22,
        title="Different current",
        artist="Different artist",
    )
    ref = {"schema_version": 1, "session_id": old.session_id, "entry_id": row["entry_id"]}
    effects = []
    commands = []
    queue = [("occurrence-a1", "A"), ("occurrence-b", "B"), ("occurrence-a2", "A")]
    original_queue = list(queue)
    no_output = [False]

    async def backend(hass, runtime, command, value=None, **kwargs):
        commands.append(command)
        turn = current_turn.get()
        if command in ("play", "set_output"):
            await turn.guard()
            if command == "play":
                turn.require_effect("play", media=(value,), output_id=turn.play_output_id)
                if no_output[0]:
                    raise SpotifyBackendError("No active device found", http_status=404)
            if not turn.effect_started:
                await turn.before_effect()
            effects.append((command, value))
            if command == "play":
                queue[:] = [("ordinary-context-replacement", value)]
            return {
                "success": True,
                "playback": {
                    "uri": "spotify:track:" + "A" * 22,
                    "is_playing": True,
                    "device": {"id": "synthetic-speaker"},
                },
            }
        if command == "status":
            return {
                "success": True,
                "playback": {"uri": "spotify:track:" + "Z" * 22, "is_playing": True},
            }
        if command == "devices":
            return {
                "success": True,
                "devices": [
                    {
                        "id": "synthetic-speaker",
                        "name": "Synthetic speaker",
                        "is_active": False,
                        "is_restricted": False,
                    }
                ],
            }
        raise AssertionError(command)

    async def tap(client_id, command="play_history_item", value=None):
        return await request(
            "POST",
            "/api/djconnect/v1/command",
            {
                "client_message_id": client_id,
                "command": command,
                "value": ref if value is None else value,
                "audio_response": "never",
            },
        )

    cases = {}
    examples = {}
    with (
        patch.object(http, "run_music_command", backend),
        patch.object(ask_dj, "run_music_command", backend),
    ):
        for version in (1, 2):
            page, status = await request("GET", "/api/djconnect/v1/session/history/" + old.session_id,
                {"session_id": old.session_id, "history_contract_version": 2,
                 "historical_playback_contract_version": version})
            assert status == 200, page
            item = next(e for e in page["entries"] if e["entry_id"] == row["entry_id"])
            assert "playback_actions" not in item and effects == []
            examples["history_entry_v" + str(version)] = item
        cases["legacy_and_v2_browsing_original_row_without_play_offers"] = "PASS"
        for client_id in ("same-tap", "same-tap", "different-tap"):
            denied, status = await tap(client_id)
            assert status == 409 and denied.get("error") == "historical_queue_preservation_unavailable", denied
            assert denied["success"] is False and "playback_actions" not in denied
            assert effects == [] and commands == [] and queue == original_queue
        examples["queue_preservation_unavailable"] = denied
        cases["historical_tap_and_duplicate_before_grants_inventory_transfer_play"] = "PASS"
        no_output[0] = True
        denied, status = await tap("no-output")
        assert status == 409 and effects == [] and commands == [] and queue == original_queue, denied
        no_output[0] = False
        cases["no_output_never_offers_chooser_or_mutates_A_B_A_occurrences"] = "PASS"
        assert manager.current_active("profile-a").broadcast is active.broadcast
        bad, status = await tap("synthetic-forged", value={**ref, "uri": "spotify:track:" + "Z" * 22})
        assert status == 400 and not bad["success"] and effects == [] and commands == [], bad
        cases["closed_reference_rejects_caller_uri"] = "PASS"

        # Persist original V1 receipt shape through the real HA Store, using the
        # current paired application's own normalized request digest. Its source
        # dependency is the original real SQLite retained observation above.
        command = "ask_dj_play_recommendation_on_output"
        value = {"device_id": "synthetic-speaker", "recommendation": {"kind": "track", "uri": "spotify:track:" + "A" * 22}}
        for kind, dependencies, implicit in (("historical", [ref], None), ("ordinary", [], None), ("implicit", [ref], ref)):
            identifier = "legacy-durable-" + kind
            digests = []
            original_reserve = history.dialogue.reserve
            def capture(frame, client_id, digest, fast):
                digests.append(digest)
                return original_reserve(frame, client_id, digest, fast)
            with patch.object(history.dialogue, "reserve", capture):
                initial, status = await tap(identifier, command, value)
            assert not initial.get("success") and len(digests) == 1, initial
            await history.async_append_exchange("profile:profile-a", {"client_message_id": identifier, "text": command},
                {"success": True, "text": "Synthetic original V1 output receipt", "action": "spotify_start_recommendation"},
                session_turn={"turn_id": "legacy-v1-" + kind, "request_digest": digests[0], "profile_id": "profile-a",
                    "context": {}, "dependency_entries": dependencies, "implicit_playback_entry": implicit,
                    "effective_style": {"language": "en", "persona": "home_dj"}})
            history.dialogue.owners.clear()
            replay, status = await tap(identifier, command, value)
            if kind == "historical":
                assert status == 409 and replay.get("error") == "historical_queue_preservation_unavailable", replay
                examples["legacy_saved_output_denial"] = replay
            else:
                assert status == 200 and replay.get("deduplicated"), replay
            assert effects == [] and commands == [] and queue == original_queue
        cases["real_Store_legacy_output_after_RAM_loss_denied_without_effects"] = "PASS"
        cases["ordinary_and_implicit_current_Store_duplicates_preserved"] = "PASS"

    media = {
        "uri": "spotify:track:" + "A" * 22,
        "album_uri": "spotify:album:" + "B" * 22,
        "title": "Synthetic original recording",
        "artist": "Synthetic artist",
        "album_image_url": "https://i.scdn.co/image/" + "a" * 40,
    }

    async def reply(*args, **kwargs):
        images = ask_dj._images_from_context(hass, {"resolved_media": media}, {})
        return {
            "success": True,
            "text": "Synthetic answer about the original recording",
            "images": images,
            "sources": [],
            "links": [],
            "playback_actions": [],
            "action": "none",
        }

    with patch.object(api_handlers.http_helpers, "async_handle_ask_dj", reply):
        accepted, status = await request(
            "POST",
            "/api/djconnect/v1/ask_dj/message",
            {
                "text": "Tell me about this recording",
                "client_message_id": "synthetic-captured-reply",
                "audio_response": "never",
                "conversation_context": {"session_id": active.session_id},
            },
        )
    assert status == 200 and accepted["success"], accepted
    assert "reply_media_reference" not in json.dumps(accepted)
    rows = await repo.async_entry_records("profile-a", active.session_id)
    reply_row = next(
        r
        for r in rows
        if r["kind"] == "conversation_dj"
        and json.loads(r["body"]).get("turn_id") == accepted["conversation"]["turn_id"]
    )
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    async def pixels(*args, **kwargs):
        assert args[2] == media["uri"] and kwargs["expected_album_uri"] == media["album_uri"]
        await kwargs["guard"]()
        return (
            png,
            "image/png",
            "https://open.spotify.com/track/" + "A" * 22,
            media["album_uri"],
            1,
            1,
            "Synthetic recording",
        )

    # Seed the SDK's existing session cache with the real loopback client's
    # session. Only the external CDN/provider fetch below is synthetic.
    from homeassistant.helpers import aiohttp_client

    cache = hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})
    cache_key = aiohttp_client._make_key(
        True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT
    )
    with (
        patch.dict(cache, {cache_key: client.session}),
        patch.object(session_artwork, "_fetch", pixels),
    ):
        prepared, status = await request(
            "POST",
            "/api/djconnect/v1/session/media/prepare",
            {
                "contract_version": 1,
                "session_id": active.session_id,
                "targets": [{"entry_id": reply_row["entry_id"]}],
            },
        )
    assert status == 200, prepared
    image = prepared["session_media"][0]
    art = image["artwork"]
    assert art["state"] == "ready" and art["subject"]["uri"] == media["uri"], prepared
    assert (
        art["reply_display_allowed"]
        and not art["current_display_allowed"]
        and not art["active_flow_display_allowed"]
    )
    cases["captured_reply_original_subject_edition_no_current_or_flow_grant"] = "PASS"
    examples["reply_media"] = image
    exported, status = await request(
        "POST", "/api/djconnect/v1/ask_dj/history/export", {"conversation_scope": "profile"}
    )
    assert status == 200 and "reply_media_reference" not in json.dumps(exported), exported
    cases["private_reply_reference_omitted_from_export"] = "PASS"
    identity = {"device_id": runtime.entry.data["device_id"], "client_type": "ios"}
    headers = {
        "Authorization": "Bearer " + runtime.device_token,
        "X-DJConnect-Device-ID": identity["device_id"],
    }
    unauthorized = await client.get(art["url"])
    assert unauthorized.status == 401
    delivered = await client.get(art["url"], params=identity, headers=headers)
    assert delivered.status == 200 and await delivered.read() == png
    assert delivered.headers["Cache-Control"] == "no-store"
    cleared, status = await request(
        "POST", "/api/djconnect/v1/ask_dj/history/clear", {"conversation_scope": "profile"}
    )
    assert status == 200, cleared
    revoked = await client.get(art["url"], params=identity, headers=headers)
    assert revoked.status == 404
    cases["authenticated_png_delivery_and_clear_revokes_original_resource"] = "PASS"

    # Real current-identification route and real registered image GETs. Only
    # Spotify/CDN I/O is synthetic; no provider/model request leaves this lab.
    from custom_components.djconnect import reply_artwork
    await manager.async_update_playback_projection(
        owner_profile_id='profile-a',session_id=active.session_id,state='playing',
        media_identity=media['uri'],title=media['title'],artist=media['artist'],
        album_uri=media['album_uri'])
    session_artwork.attach_live_projection(hass,'profile-a',active.session_id)
    media_before=active.broadcast.media_projector()
    status_reads=[]
    async def current_status(hass,runtime,command,*args,**kwargs):
        assert command=='status'
        status_reads.append(command)
        return {'success':True,'playback':dict(media)}
    async def current_pixels(hass,url,guard,registry):
        assert url==media['album_image_url']
        await guard()
        return png,'image/png'
    with patch.object(ask_dj,'run_music_command',current_status),patch.object(
            reply_artwork,'_download_observed_cover',current_pixels):
        current,status=await request('POST','/api/djconnect/v1/ask_dj/message',{
            'client_message_id':'current-cover-session','text':'Wie zijn dit?',
            'language':'nl','audio_response':'never',
            'conversation_context':{'session_id':active.session_id}})
        assert status==200 and not current['history_persisted'] and len(current['images'])==1,current
        assert len(status_reads)==2 and not current['playback_actions']
        assert active.broadcast.media_projector()==media_before
        active.broadcast.native_delivery()
        current_url=current['images'][0]['url']
        assert (await client.get(current_url)).status==401
        response=await client.get(current_url,params=identity,headers=headers)
        assert response.status==200 and await response.read()==png
        assert response.headers['Cache-Control']=='no-store'
        registry=domain['session_images']
        asset_id=current_url.rsplit('/',1)[-1]
        next(a for a in registry.assets.values() if a['asset_id']==asset_id)['deadline']=0
        assert (await client.get(current_url,params=identity,headers=headers)).status==404
        assert active.broadcast.media_projector()==media_before
        active.broadcast.native_delivery()
        cases['current_reply_resource_excluded_from_attached_live_projector_even_after_expiry']='PASS'
        cases['current_cover_original_observation_authenticated_GET_and_expiry']='PASS'
        examples['current_identification_reply']=current
        await manager.async_end(owner_profile_id='profile-a',session_id=active.session_id)
        general,status=await request('POST','/api/djconnect/v1/ask_dj/message',{
            'client_message_id':'current-cover-general','text':'Wie zijn dit?',
            'language':'nl','audio_response':'never','conversation_context':{}})
        assert status==200 and not general['history_persisted'] and len(general['images'])==1,general
        assert manager.current_active('profile-a') is None and len(status_reads)==4
        general_url=general['images'][0]['url']
        assert general_url.startswith('/api/djconnect/v1/ask_dj/reply/image/')
        assert (await client.get(general_url)).status==401
        response=await client.get(general_url,params=identity,headers=headers)
        assert response.status==200 and await response.read()==png
        cases['general_Profile_current_cover_without_creating_Session']='PASS'
        provider=domain['source-entry']
        provider._receiver_end_generation=getattr(provider,'_receiver_end_generation',0)+1
        assert (await client.get(general_url,params=identity,headers=headers)).status==404
        cases['general_current_cover_original_source_withdrawal_revokes_GET']='PASS'
        examples['general_current_identification_reply']=general

    return {
        "qualification": "ACTUAL_HA_PAIRED_HTTP_REAL_SQLITE_STORE_RAM_IMAGE_OWNER_SYNTHETIC_PLAYBACK_CDN_REPLY_BOUNDARIES",
        "cases": cases,
        "examples": examples,
        "effect_count": len(effects),
        "model_provider_calls": 0,
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "installed": "NOT_RUN",
        "native": "NOT_RUN",
        "audible": "NOT_RUN",
    }


if __name__ == "__main__":
    from verify_session_conversation_history_http import main

    asyncio.run(main(qualification_extension=qualify))
