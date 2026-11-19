"""Real paired HTTP/owner/result sets; declared external catalogue and agent fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from aiohttp import web
from discovery_play_lab import ARTIST, provider_reply as default_provider_reply

STATE = {"deny_albums": False, "deny_playlists": False, "foreign": False}


async def provider_reply(request):
    artist = {"id": ARTIST, "uri": "spotify:artist:" + ARTIST, "name": "HAEVN", "images": []}
    if request.path == "/v1/search":
        if request.query.get("type") == "artist":
            return web.json_response({"artists": {"items": [artist]}})
        if request.query.get("type") == "playlist":
            if STATE["deny_playlists"]:
                return web.json_response({"error": {"message": "Declared fixture denial"}}, status=403)
            return web.json_response({"playlists": {"items": [
                {"id": str(i) * 22, "uri": "spotify:playlist:" + str(i) * 22,
                 "name": "Fixture HAEVN playlist " + str(i), "images": [],
                 "owner": {"id": "fixture-owner"}} for i in range(6)
            ]}})
    if request.path == "/v1/artists/" + ARTIST + "/albums":
        if STATE["deny_albums"]:
            return web.json_response({"error": {"message": "Declared fixture denial"}}, status=403)
        return web.json_response({"items": [
            {"id": str(i) * 22, "uri": "spotify:album:" + str(i) * 22,
             "name": "Fixture HAEVN album " + str(i), "album_type": "album", "images": [],
             "artists": [{**artist, "id": "X" * 22} if STATE["foreign"] else artist]}
            for i in range(6)
        ]})
    if request.path.startswith("/v1/playlists/") and request.path.endswith("/items"):
        return web.json_response({"items": [{"item": {
            "type": "track", "is_local": False,
            "artists": [{"id": "X" * 22 if STATE["foreign"] else ARTIST}],
        }}]})
    return await default_provider_reply(request)


async def setup_agent(hass):
    from types import MappingProxyType, SimpleNamespace
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.components import conversation
    from homeassistant.components.openai_conversation.conversation import OpenAIConversationEntity
    from homeassistant.components.assist_pipeline.pipeline import (
        PipelineStore, STORAGE_KEY, STORAGE_VERSION, STORAGE_VERSION_MINOR, async_setup_pipeline_store,
    )
    from homeassistant.components.homeassistant.exposed_entities import ExposedEntities
    from homeassistant.components.homeassistant.const import DATA_EXPOSED_ENTITIES

    # Real HA agent class, public registration and static safe provider metadata.
    # Only its external response boundary below is synthetic; never patch admission.
    exposure = ExposedEntities(hass)
    await exposure.async_initialize()
    hass.data[DATA_EXPOSED_ENTITIES] = exposure
    await conversation.async_setup(hass, {})
    model_entry = ConfigEntry(
        domain="openai_conversation", title="Offline collection fixture",
        entry_id="collection-fixture-agent", data={}, options={}, discovery_keys=MappingProxyType({}),
        source="user", unique_id="collection-fixture-agent", version=2, minor_version=7,
        subentries_data=[{"subentry_id": "collection-fixture-subentry", "subentry_type": "conversation",
                         "title": "Offline collection fixture", "data": {
                             "llm_hass_api": [], "store_responses": False,
                             "web_search": False, "code_interpreter": False,
                             "prompt": "Interpret only the supplied public music fixture question."}}],
    )
    model_entry.runtime_data = SimpleNamespace()
    agent = OpenAIConversationEntity(model_entry, model_entry.subentries["collection-fixture-subentry"])
    agent.hass = hass
    conversation.async_set_agent(hass, model_entry, agent)
    settings = {"id": "collection-fixture-pipeline", "name": "Offline collection fixture", "language": "nl",
                "conversation_engine": model_entry.entry_id, "conversation_language": "nl",
                "stt_engine": None, "stt_language": None, "tts_engine": None, "tts_language": None,
                "tts_voice": None, "wake_word_entity": None, "wake_word_id": None}
    await PipelineStore(hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_VERSION_MINOR).async_save(
        {"items": [settings], "preferred_item": settings["id"]})
    await async_setup_pipeline_store(hass)

    hass.data["collection_fixture_agent"] = model_entry


async def run(*, hass, runtime, client, headers, identity, network, output, source_hashes):
    from custom_components.djconnect import pipeline

    model_entry = hass.data["collection_fixture_agent"]
    calls, cases, examples = [], {}, {}

    async def interpreted(hass, data, **kwargs):
        assert data["agent_id"] == model_entry.entry_id and kwargs.get("allow_agent_fallback") is False
        calls.append(1)
        return {"response": {"speech": {"plain": {"speech": json.dumps({
            "read": "artist_collections", "reference": "named", "exclude_current": False,
            "artist": "HAEVN",
        })}}}}

    async def request(identifier, language, question):
        before = len(calls)
        result = await client.post("/api/djconnect/v1/ask_dj/message", headers=headers, json={
            **identity, "client_message_id": identifier, "text": question,
            "language": language, "audio_response": "never",
        })
        body = await result.json()
        assert result.status == 200 and body["success"], body
        assert len(calls) - before == 1
        assert body["action"] == "none" and not body.get("audio_url"), body
        return body

    with patch.object(pipeline, "_call_conversation_process_transport", interpreted):
        for locale, question in (("nl", "Heb je iets van de artiest haevn"),
                                 ("en", "Have you got something by HAEVN?")):
            body = await request("collections-" + locale, locale, question)
            actions = body.get("playback_actions") or []
            assert [a["kind"] for a in actions].count("album") == 5, body
            assert [a["kind"] for a in actions].count("playlist") == 5, body
            assert all(a.get("action_id") for a in actions), body
            assert len({json.dumps(a["value"], sort_keys=True) for a in actions}) == 10, body
            examples[locale] = body
            cases[locale + "_five_real_fixture_albums_and_credited_playlists"] = "PASS"
        STATE["deny_playlists"] = True
        body = await request("albums-only", "nl", "Heb je iets van HAEVN?")
        assert [a["kind"] for a in body["playback_actions"]] == ["album"] * 5, body
        assert "0 playlists" in body["text"], body
        cases["playlist_denial_preserves_qualified_album_rows"] = "PASS"
        STATE["deny_playlists"], STATE["deny_albums"] = False, True
        body = await request("playlists-only", "en", "Do you have anything by HAEVN?")
        assert [a["kind"] for a in body["playback_actions"]] == ["playlist"] * 5, body
        assert "0 albums" in body["text"], body
        cases["album_denial_preserves_qualified_playlist_rows"] = "PASS"
        STATE["deny_albums"], STATE["foreign"] = False, True
        body = await request("foreign-credits", "nl", "Heb je iets van HAEVN?")
        assert not body.get("playback_actions") and not body.get("items"), body
        cases["foreign_credits_are_not_offered_or_topped_up"] = "PASS"
    assert all(c["method"] == "GET" for c in network.calls), network.calls
    cases["all_external_provider_requests_read_only"] = "PASS"
    root = Path(__file__).resolve().parents[2]
    after = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted((root / "custom_components/djconnect").rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts}
    assert after == source_hashes
    report = {"actual_home_assistant": True, "ordinary_pairing": True,
              "cases": cases, "examples": examples, "source_pins": source_hashes,
              "provider_fixture_calls": network.calls, "source_unchanged": True,
              "declared_agent_plan_fixture": True, "declared_spotify_wire_fixture": True,
              "real_model_calls": 0, "real_provider_calls": 0, "installed_mutations": 0,
              "native_acceptance": "NOT_RUN", "live_provider_acceptance": "NOT_RUN"}
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print("ARTIST_COLLECTIONS_PASS", len(cases), flush=True)
