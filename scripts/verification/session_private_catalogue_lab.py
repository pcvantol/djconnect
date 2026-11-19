"""Actual paired private root projection and original Session fences; external wires only."""

from pathlib import Path
import hashlib
import json
import uuid
from unittest.mock import patch
from aiohttp import web
from artist_collections_lab import (
    setup_agent as ordinary_agent,
    provider_reply as catalogue_provider,
)


async def setup_agent(hass):
    await ordinary_agent(hass)
    from verify_session_speech_http import processor_fixture

    server, calls = await processor_fixture(hass, model_entity_id="collection-fixture-agent")
    hass.data["session_wire_fixture_processor"] = (server, calls)


async def provider_reply(request):
    if request.path == "/v1/me/player":
        return web.Response(status=204)
    if request.path == "/v1/me/player/queue":
        return web.json_response({"currently_playing": None, "queue": []})
    return await catalogue_provider(request)


async def run(*, hass, runtime, client, headers, identity, network, output, source_hashes):
    from custom_components.djconnect import pipeline, api_handlers
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    from custom_components.djconnect.persistence import async_initialize_persistence
    from custom_components.djconnect.persistence.sessions import PersistentSessionRepository
    from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    from custom_components.djconnect.session_runtime import SessionRuntimeManager
    from custom_components.djconnect.domain.profile.dj_settings import DJSettings

    service = await async_initialize_persistence(hass)
    manager = SessionRuntimeManager(
        PersistentSessionRepository(service), HistoricalProjectionRepository(service)
    )
    manager._settings_repository = ProfileDJSettingsRepository(service)
    hass.data["djconnect"]["session_runtime_manager"] = manager

    async def req(method, path, data):
        res = await client.request(
            method,
            "/api/djconnect/v1" + path,
            headers=headers,
            **{"params" if method == "GET" else "json": {**identity, **data}},
        )
        return await res.json(), res.status

    before, code = await req("GET", "/profile/settings", {"contract_version": 3})
    assert code == 200, before
    chosen, code = await req(
        "PATCH",
        "/profile/settings",
        {
            "contract_version": 3,
            "binding": before["binding"],
            "operation_id": str(uuid.uuid7()),
            "patch": DJSettings().as_dict(),
            "expected_defaults_revision": before["snapshot"]["defaults_revision"],
            "expected_session": None,
        },
    )
    assert code == 200, chosen

    async def no_external(*a, **kw):
        pass

    with (
        patch.object(api_handlers, "_async_generate_initial_session_moment", no_external),
        patch.object(PlaybackObservationManager, "async_start_spotify", no_external),
    ):
        started, code = await req("POST", "/session/start", {"mood": "groove", "locale": "nl"})
        assert code == 201, started
    sid = started["session"]["session_id"]
    calls = []
    cases = {}
    examples = {}

    async def interpreted(hass, data, **kwargs):
        assert (
            data["agent_id"] == "collection-fixture-agent"
            and kwargs.get("allow_agent_fallback") is False
        )
        calls.append(1)
        return {
            "response": {
                "speech": {
                    "plain": {
                        "speech": json.dumps(
                            {
                                "read": "artist_collections",
                                "reference": "named",
                                "exclude_current": False,
                                "artist": "HAEVN",
                            }
                        )
                    }
                }
            }
        }

    history_before, code = await req("GET", "/ask_dj/history", {"conversation_scope": "profile"})
    assert code == 200

    def private_shape(body, context, identifier):
        assert body["success"] and body["history_persisted"] is False
        assert (
            body["owner_profile_id"] == "artwork-profile"
            and body["client_message_id"] == identifier
        )
        c = body["conversation"]
        assert (
            c["schema_version"] == 1
            and c["turn_id"]
            and c["context"] == context
            and c["entry_ids"] == []
            and c["input_type"] == "text"
            and c["history_scope"] == "private_ephemeral"
        )
        assert all(
            k not in body
            for k in [
                "assistant_message",
                "user_message",
                "messages",
                "history_revision",
                "clear_revision",
            ]
        )
        assert (
            body["text"]
            and body["action"] == "none"
            and len(body["items"]) == 10
            and len(body["playback_actions"]) == 10
        )
        assert body["result_set"]["result_set_id"] and all(
            a.get("action_id") for a in body["playback_actions"]
        )

    with patch.object(pipeline, "_call_conversation_process_transport", interpreted):
        for locale, question in [
            ("nl", "Heb je iets van de artiest HAEVN?"),
            ("en", "Have you got something by HAEVN?"),
        ]:
            identifier = "private-session-" + locale
            payload = {
                "text": question,
                "language": locale,
                "audio_response": "never",
                "client_message_id": identifier,
                "conversation_context": {"session_id": sid},
                "history_contract_version": 2,
                "speech_contract_version": 3,
            }
            count = len(calls)
            body, code = await req("POST", "/ask_dj/message", payload)
            assert code == 200 and len(calls) == count + 1, body
            private_shape(body, {"session_id": sid}, identifier)
            examples["session_" + locale] = body
            cases[locale + "_fresh_session_history2_speech3_root_only"] = "PASS"
        count = len(calls)
        repeated, code = await req("POST", "/ask_dj/message", payload)
        assert code == 200 and len(calls) == count, repeated
        assert (
            repeated["conversation"]["turn_id"] == body["conversation"]["turn_id"]
            and repeated["result_set"]["result_set_id"] == body["result_set"]["result_set_id"]
        )
        private_shape(repeated, {"session_id": sid}, identifier)
        cases["duplicate_retains_original_turn_actions_without_new_model"] = "PASS"
        history_after, code = await req("GET", "/ask_dj/history", {"conversation_scope": "profile"})
        assert code == 200
        for key in ["messages", "history_revision", "clear_revision"]:
            assert history_before.get(key) == history_after.get(key), key
        cases["profile_store_history_and_revisions_unchanged"] = "PASS"
        tail, code = await req(
            "GET",
            "/session/history/" + sid,
            {"window": "tail", "limit": 50, "history_contract_version": 2},
        )
        assert code == 200, tail
        assert not any(e["kind"].startswith("conversation_") for e in tail["entries"])
        cases["no_session_sql_conversation_rows"] = "PASS"
        ended, code = await req("POST", "/session/end", {"session_id": sid})
        assert code == 200, ended
        count = len(calls)
        refused, code = await req("POST", "/ask_dj/message", payload)
        assert code in [403, 404, 409] and len(calls) == count, refused
        examples["ended_session_refusal"] = {"status": code, "error": refused.get("error")}
        cases["ended_original_session_cannot_reuse_private_delivery"] = "PASS"
        for locale, question in [
            ("nl", "Heb je iets van de artiest HAEVN?"),
            ("en", "Have you got something by HAEVN?"),
        ]:
            identifier = "private-general-" + locale
            general, code = await req(
                "POST",
                "/ask_dj/message",
                {
                    "text": question,
                    "language": locale,
                    "audio_response": "never",
                    "client_message_id": identifier,
                    "history_contract_version": 2,
                    "speech_contract_version": 3,
                },
            )
            assert code == 200, general
            private_shape(general, {}, identifier)
            examples["general_" + locale] = general
        cases["general_nl_en_same_private_root_contract"] = "PASS"
    assert all(call["method"] == "GET" for call in network.calls)
    root = Path(__file__).resolve().parents[2]
    current = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / "custom_components/djconnect").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert current == source_hashes
    record = {
        "actual_home_assistant": True,
        "ordinary_pairing": True,
        "fresh_session_with_no_current_playback": True,
        "accepted_settings_contract": 3,
        "requested_history_contract": 2,
        "requested_speech_contract": 3,
        "cases": cases,
        "examples": examples,
        "source_pins": source_hashes,
        "source_unchanged": True,
        "model_response_fixture": True,
        "spotify_wire_fixture": True,
        "real_model_calls": 0,
        "real_provider_calls": 0,
        "installed_mutations": 0,
        "native_acceptance": "NOT_RUN",
    }
    (output / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    print("SESSION_PRIVATE_CATALOGUE_PASS", len(cases), flush=True)
    server, _ = hass.data["session_wire_fixture_processor"]
    server.close()
    await server.wait_closed()
