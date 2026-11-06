"""Real paired Mac/iPhone/Watch history reads; no native or STT-provider claim."""

from __future__ import annotations
import hashlib
import json
from unittest.mock import AsyncMock, patch


async def run(*, hass, runtime, client, headers, identity, network, output, source_hashes):
    from custom_components.djconnect import http
    from discovery_play_lab import TRACK

    actors = [(identity, headers)]
    for entry_id in ("shared-watch", "shared-phone"):
        entry = hass.config_entries.async_get_entry(entry_id)
        # The legacy ordinary pairing route owns the currently selected setup
        # slot. Select the real configured slot, then let it mint/persist tokens.
        hass.data["djconnect"]["runtime"] = hass.data["djconnect"][entry_id]
        who = {k: entry.data[k] for k in ("device_id", "client_type")}
        pair = await client.post(
            "/api/djconnect/v1/pair",
            json={**who, "pair_code": entry.data["pair_code"]},
            headers={
                "X-DJConnect-Device-ID": who["device_id"],
                "X-DJConnect-Client-Type": who["client_type"],
            },
        )
        paired = await pair.json()
        assert pair.status == 200 and paired["success"], paired
        actors.append(
            (
                who,
                {
                    "Authorization": "Bearer " + paired["device_token"],
                    "X-DJConnect-Device-ID": who["device_id"],
                    "X-DJConnect-Client-Type": who["client_type"],
                },
            )
        )

    hass.data["djconnect"]["runtime"] = runtime

    async def request(method, path, data, actor=0):
        who, auth = actors[actor]
        kwargs = {"params" if method == "GET" else "json": {**who, **data}, "headers": auth}
        response = await client.request(method, "/api/djconnect/v1" + path, **kwargs)
        return await response.json(), response.status

    from custom_components.djconnect.persistence import async_initialize_persistence
    from custom_components.djconnect.persistence.sessions import PersistentSessionRepository
    from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
    from custom_components.djconnect.session_runtime import SessionRuntimeManager

    service = await async_initialize_persistence(hass)
    manager = SessionRuntimeManager(
        PersistentSessionRepository(service), HistoricalProjectionRepository(service)
    )
    hass.data["djconnect"]["session_runtime_manager"] = manager
    source = {
        "backend_id": "spotify_direct",
        "music_account_id": "artwork-account",
        "provider_entry_id": "artwork-owner",
        "provider_account_id": "fixture-client",
    }
    active = await manager.async_start(
        owner_profile_id="artwork-profile",
        music_backend="spotify_direct",
        history_source_context=source,
        locale="nl",
    )
    await manager.async_update_playback_projection(
        owner_profile_id="artwork-profile",
        session_id=active.session_id,
        state="playing",
        media_identity="spotify:track:" + TRACK,
        title="Fixture track",
        artist="Fixture artist",
    )
    context = {"session_id": active.session_id}
    cases, examples = {}, {}
    first, code = await request(
        "POST",
        "/ask_dj/message",
        {
            "text": "Wie is dit?",
            "language": "nl",
            "audio_response": "never",
            "client_message_id": "actual-mac-identification",
            "conversation_context": context,
        },
    )
    assert (
        code == 200 and first["success"] and first["conversation"]["history_scope"] == "profile"
    ), first
    assert len(first["conversation"]["entry_ids"]) == 2
    examples["mac_text"] = first
    cases["literal_current_metadata_committed_to_original_session"] = "PASS"

    transcript = AsyncMock(return_value="Wie is dit?")
    who, auth = actors[1]
    voice_headers = {
        **auth,
        "Content-Type": "audio/wav",
        "X-DJConnect-Language": "nl",
        "X-DJConnect-Conversation-Scope": "profile",
        "X-DJConnect-Session-ID": active.session_id,
        "X-DJConnect-Client-Message-ID": "actual-watch-voice",
        "X-DJConnect-Speech-Contract-Version": "3",
    }
    with patch.object(http, "transcribe_wav_with_assist", transcript):
        response = await client.post(
            "/api/djconnect/v1/voice",
            data=b"Synthetic WAV transport fixture",
            headers=voice_headers,
        )
        voice = await response.json()
    assert response.status == 200 and voice["success"], (response.status, voice)
    assert (
        voice["conversation"]["input_type"] == "voice"
        and len(voice["conversation"]["entry_ids"]) == 2
    )
    transcript.assert_awaited_once()
    examples["watch_voice"] = voice
    cases["watch_voice_after_declared_transcript_uses_same_persistence_owner"] = "PASS"
    expected = set(first["conversation"]["entry_ids"] + voice["conversation"]["entry_ids"])
    for index, (who, _) in enumerate(actors):
        tail, code = await request(
            "GET",
            "/session/history/" + active.session_id,
            {"window": "tail", "limit": 50, "history_contract_version": 2},
            actor=index,
        )
        assert code == 200, (code, tail)
        visible = {e["entry_id"] for e in tail["entries"] if e["kind"].startswith("conversation_")}
        assert visible == expected, (who["client_type"], tail)
        examples[who["client_type"] + "_tail"] = tail
    cases["mac_phone_watch_see_same_four_original_conversation_entries"] = "PASS"
    from custom_components.djconnect.api_handlers import _history_manager

    stored = await _history_manager(hass, runtime).async_history("profile:artwork-profile")
    messages = [
        m
        for m in stored["messages"]
        if m.get("client_message_id") in {"actual-mac-identification", "actual-watch-voice"}
    ]
    assert len(messages) == 4
    assert all(
        not m.get("images") and not m.get("audio_url") and not m.get("playback_actions")
        for m in messages
    )
    assert "reply_media_reference" not in json.dumps(messages)
    cases["retained_literal_has_no_image_audio_action_or_pixel_grant"] = "PASS"
    duplicate, code = await request(
        "POST",
        "/ask_dj/message",
        {
            "text": "Wie is dit?",
            "language": "nl",
            "audio_response": "never",
            "client_message_id": "actual-mac-identification",
            "conversation_context": context,
        },
    )
    assert code == 200 and duplicate.get("deduplicated"), duplicate
    tail, code = await request(
        "GET",
        "/session/history/" + active.session_id,
        {"window": "tail", "limit": 50, "history_contract_version": 2},
    )
    assert (
        code == 200
        and {e["entry_id"] for e in tail["entries"] if e["kind"].startswith("conversation_")}
        == expected
    )
    cases["same_original_request_never_adds_duplicate_exchange"] = "PASS"
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager

    await service.async_close()
    await service.async_initialize()
    restored = AskDJHistoryManager(hass)
    hass.data["djconnect"]["ask_dj_history_manager"] = restored
    hass.data["djconnect"].pop("session_history_query", None)
    for entry_id in ("artwork-owner", "shared-watch", "shared-phone"):
        hass.data["djconnect"][entry_id].ask_dj_history = restored
    reloaded, code = await request(
        "GET",
        "/session/history/" + active.session_id,
        {"window": "tail", "limit": 50, "history_contract_version": 2},
        actor=2,
    )
    assert (
        code == 200
        and {e["entry_id"] for e in reloaded["entries"] if e["kind"].startswith("conversation_")}
        == expected
    ), reloaded
    cases["real_sqlite_and_ha_store_reload_preserve_original_exchange_ids"] = "PASS"
    foreign = hass.config_entries.async_get_entry("artwork-second")
    hass.data["djconnect"]["runtime"] = hass.data["djconnect"]["artwork-second"]
    foreign_identity = {k: foreign.data[k] for k in ("device_id", "client_type")}
    pair = await client.post(
        "/api/djconnect/v1/pair", json={**foreign_identity, "pair_code": foreign.data["pair_code"]}
    )
    paired = await pair.json()
    assert pair.status == 200 and paired["success"], paired
    foreign_response = await client.get(
        "/api/djconnect/v1/session/history/" + active.session_id,
        params={**foreign_identity, "history_contract_version": 2},
        headers={
            "Authorization": "Bearer " + paired["device_token"],
            "X-DJConnect-Device-ID": foreign_identity["device_id"],
        },
    )
    foreign_body = await foreign_response.json()
    assert foreign_response.status != 200 and "entries" not in foreign_body, foreign_body
    cases["separately_paired_other_profile_cannot_read_original_conversation"] = "PASS"
    hass.data["djconnect"]["runtime"] = runtime
    cleared, code = await request(
        "POST", "/ask_dj/history/clear", {"conversation_scope": "profile"}
    )
    assert code == 200, cleared
    for index in range(3):
        tail, code = await request(
            "GET",
            "/session/history/" + active.session_id,
            {"window": "tail", "limit": 50, "history_contract_version": 2},
            actor=index,
        )
        assert code == 200 and not any(
            e["kind"].startswith("conversation_") for e in tail["entries"]
        ), tail
    cases["owner_clear_withdraws_shared_conversation_from_mac_phone_and_watch"] = "PASS"
    assert all(c["method"] == "GET" for c in network.calls), network.calls
    record = {
        "actual_home_assistant": True,
        "ordinary_pairing": True,
        "cases": cases,
        "examples": examples,
        "source_pins": source_hashes,
        "provider_fixture_calls": network.calls,
        "source_unchanged": True,
        "real_model_calls": 0,
        "real_provider_calls": 0,
        "installed_mutations": 0,
        "native_acceptance": "NOT_RUN",
        "stt_engine_acceptance": "NOT_RUN",
        "declared_stt_transcript_fixture": True,
    }
    from pathlib import Path

    current = {
        str(p.relative_to(Path(__file__).resolve().parents[2])): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in (Path(__file__).resolve().parents[2] / "custom_components/djconnect").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert current == source_hashes
    (output / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    print("CURRENT_METADATA_HISTORY_PASS", len(cases), flush=True)
