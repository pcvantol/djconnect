"""Actual isolated HA R5/committed Store/public Task qualification, network-none.

Only synthetic pairing/provider configuration is used. No provider/model method
is invoked. The public HA component lifecycle is exercised with its dependency
setup boundary replaced by the real integration async_setup; hardware discovery
and full native HA bootstrap are explicitly outside this proof.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
from types import MappingProxyType
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import UUID, uuid4

from aiohttp.test_utils import TestClient, TestServer
from yarl import URL
from openai import AsyncOpenAI
from homeassistant import auth, loader, setup
from homeassistant.config_entries import (
    ConfigEntries, ConfigEntry, ConfigEntryState, ConfigEntryStore, ConfigSubentry)
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components import conversation, ai_task, network
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.helpers import area_registry, device_registry, entity_registry, frame

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
from custom_components.djconnect import DJConnectRuntime, async_setup  # noqa: E402
from custom_components.djconnect import profile_observation, profile_context, profile_backend  # noqa: E402
from custom_components.djconnect.ask_dj import example_catalogue  # noqa: E402
from custom_components.djconnect.ask_dj.help_configuration import (  # noqa: E402
    QUALIFIED_AGENT_PROMPT, loaded_model_configuration)
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402


def entry(identifier, domain, data, subentries=None):
    return ConfigEntry(domain=domain, title="Synthetic isolated Help qualification",
        entry_id=identifier, data=data, options={}, discovery_keys=MappingProxyType({}),
        source="user", unique_id=identifier, version=2 if domain == "openai_conversation" else 1,
        minor_version=7 if domain == "openai_conversation" else 1, subentries_data=subentries)


def source_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "custom_components/djconnect").rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


async def main():
    before = source_hashes()
    lab = Path(os.environ.get("DJC_LAB_ROOT", "/lab"))
    config = lab / "empty-ha-config"
    config.mkdir(parents=True, exist_ok=False)
    hass = HomeAssistant(str(config))
    hass.state = CoreState.running
    hass.config.language = "nl"
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(cors_origins=[], use_x_forwarded_for=False,
        login_threshold=-1, is_ban_enabled=False, use_x_frame_options=True)
    hass.config.components.add("http")
    from homeassistant.components.homeassistant.exposed_entities import ExposedEntities
    from homeassistant.components.homeassistant.const import DATA_EXPOSED_ENTITIES
    exposed = ExposedEntities(hass)
    await exposed.async_initialize()
    hass.data[DATA_EXPOSED_ENTITIES] = exposed

    await conversation.async_setup(hass, {})
    hass.config.components.add("conversation")
    await network.async_setup(hass, {})
    hass.config.components.add("network")
    frame.async_setup(hass)
    loader.async_setup(hass)

    bootstrap_calls = []
    async def dependency_fixture(current_hass, domain, configuration):
        assert current_hass is hass and domain == "djconnect"
        bootstrap_calls.append(domain)
        return await async_setup(hass, configuration)
    with patch.object(setup, "_async_setup_component", dependency_fixture):
        assert await setup.async_setup_component(hass, "djconnect", {})
        assert await setup.async_setup_component(hass, "djconnect", {})
    assert bootstrap_calls == ["djconnect"]

    device = "djconnect-ios-ABCDEF123456"
    client_entry = entry("help-owner-entry", "djconnect", {
        "device_id": device, "client_type": "ios", "profile_id": "profile-a",
        "pair_code": "123456", "music_backend": "spotify_direct", "music_account_id": "source-account",
        "spotify_client_id": "SYNTHETIC_CLIENT_ID", "spotify_refresh_token": "SYNTHETIC_NEVER_SENT",
        "assist_pipeline_id": "help-qualified-pipeline"})
    model_options = dict(chat_model="gpt-6-luna", max_tokens=3000, reasoning_effort="medium",
        llm_hass_api=[], store_responses=False, web_search=False, code_interpreter=False,
        prompt=QUALIFIED_AGENT_PROMPT)
    model_entry = entry("help-official-model-entry", "openai_conversation",
        {"api_key": "SYNTHETIC_NOT_AN_AUTHORIZED_PROVIDER_CREDENTIAL"}, [{
            "subentry_id": "help-agent", "subentry_type": "conversation",
            "title": "Synthetic Help profile", "data": model_options}])
    await ConfigEntryStore(hass).async_save({"entries": [e.as_storage_fragment for e in (client_entry, model_entry)]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    client_entry = hass.config_entries.async_get_entry(client_entry.entry_id)
    model_entry = hass.config_entries.async_get_entry(model_entry.entry_id)
    for current in (client_entry, model_entry):
        current._async_set_state(hass, ConfigEntryState.LOADED, None)
    api = AsyncOpenAI(api_key="SYNTHETIC_NOT_SENT", max_retries=0, timeout=25)
    model_entry.runtime_data = api
    assert await hass.data[conversation.DATA_COMPONENT].async_setup_entry(model_entry)
    registry = entity_registry.async_get(hass)
    agent_id = next(e.entity_id for e in registry.entities.values()
        if e.config_entry_id == model_entry.entry_id and e.config_subentry_id == "help-agent")
    assert await ai_task.async_setup(hass, {})
    task_options = {key: model_options[key] for key in (
        "chat_model", "max_tokens", "reasoning_effort", "store_responses", "web_search", "code_interpreter")}
    task_options["service_tier"] = "auto"
    subentry = ConfigSubentry(subentry_id="help-task", subentry_type="ai_task_data",
        title="Synthetic Help typed task", data=MappingProxyType(task_options), unique_id=None)
    hass.config_entries.async_add_subentry(model_entry, subentry)
    assert await ai_task.async_setup_entry(hass, model_entry)
    task_id = next(e.entity_id for e in registry.entities.values()
        if e.config_entry_id == model_entry.entry_id and e.config_subentry_id == "help-task")
    hass.config_entries.async_update_entry(client_entry,
        data={**client_entry.data, "assist_structured_task_id": task_id})
    from homeassistant.components.assist_pipeline.pipeline import (
        PipelineStore, STORAGE_VERSION, STORAGE_KEY, STORAGE_VERSION_MINOR, async_setup_pipeline_store)
    pipeline = dict(id="help-qualified-pipeline", name="Synthetic exact Help profile", language="nl",
        conversation_engine=agent_id, conversation_language="nl", stt_engine=None, stt_language=None,
        tts_engine=None, tts_language=None, tts_voice=None, wake_word_entity=None, wake_word_id=None)
    await PipelineStore(hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_VERSION_MINOR).async_save(
        {"items": [pipeline], "preferred_item": pipeline["id"]})
    await async_setup_pipeline_store(hass)
    assert loaded_model_configuration(hass, {**client_entry.data, **client_entry.options})

    runtime = DJConnectRuntime(client_entry, device_token=secrets.token_urlsafe(32))
    runtime.device_status.update(device_id=device, client_type="ios")
    domain = hass.data["djconnect"]
    domain[client_entry.entry_id] = domain["runtime"] = runtime
    storage = profile_context.profile_storage(hass)
    await storage.async_upsert_music_backend("spotify_direct", BackendProvider.SPOTIFY_DIRECT,
                                            display_name="Synthetic source")
    profile = await storage.async_create_profile("Synthetic owner", profile_id="profile-a",
                                                default_backend_id="spotify_direct")
    await storage.async_upsert_music_account("source-account", "spotify_direct",
        kind=MusicAccountKind.PERSONAL, display_name="Synthetic account", linked_profile_ids=frozenset({"profile-a"}))
    await storage.async_update_profile("profile-a", preferences=replace(
        profile.preferences, default_music_account_id="source-account"))
    await storage.async_upsert_device(device, "ios", linked_profile_id="profile-a")
    await hass.async_block_till_done()
    manager = SessionRuntimeManager()
    domain["session_runtime_manager"] = manager
    active = await manager.async_start(owner_profile_id="profile-a", music_backend="spotify_direct",
        history_source_context={"backend_id": "spotify_direct", "music_account_id": "source-account",
                                "provider_entry_id": client_entry.entry_id, "provider_account_id": ""})
    await manager.async_update_playback_projection(owner_profile_id="profile-a", session_id=active.session_id,
        state="playing", media_identity="spotify:track:" + "A" * 22, title="Synthetic recording",
        artist="Synthetic artist", album="Synthetic album", duration_ms=180000, position_ms=1000)
    assert profile_observation.capture_committed(hass).current()
    pin = example_catalogue.capability()
    assert pin["qualified"] is True
    query = dict(schema_version="1", request_id=str(uuid4()), surface="ask_dj", language="nl",
        catalogue_id=pin["catalogue_id"], catalogue_revision=str(pin["revision"]), catalogue_sha256=pin["sha256"])
    headers = {"Authorization": "Bearer " + runtime.device_token, "X-DJConnect-Device-ID": device}
    receipts = []
    async with TestClient(TestServer(hass.http.app)) as client:
        response = await client.post("/api/djconnect/v1/pair", json={
            "device_id": device, "client_type": "ios", "pair_code": "123456"})
        paired = await response.json()
        assert response.status == 200 and paired["success"] is True
        headers["Authorization"] = "Bearer " + paired["device_token"]
        del paired
        await hass.async_block_till_done()
        # Set-up writes above are ordinary disposable lab operations. Everything
        # below is a read test: Store/provider/auth-learner/creating config denied.
        async def request(changes=None, *, raw=None, body=None, supplied_headers=None):
            values = {**query, **(changes or {}), "request_id": str(uuid4())}
            url = "/api/djconnect/v1/ask_dj/help-context?" + (raw if raw is not None else urlencode(values))
            response = await client.get(URL(url, encoded=True),
                headers=headers if supplied_headers is None else supplied_headers, data=body)
            result = await response.json()
            assert response.headers.get("Cache-Control") == "no-store"
            assert len(await response.read()) <= 16384
            if response.status == 200:
                assert set(result) == {"schema_version", "request_id", "surface", "language", "session_id",
                    "track_id", "catalogue", "available", "observation_id", "eligible_entry_ids"}
                assert type(result["schema_version"]) is int and result["schema_version"] == 1
                assert result["request_id"] == values["request_id"]
                assert result["surface"] == values["surface"] and result["language"] == values["language"]
                assert result["session_id"] == values.get("session_id")
                assert type(result["available"]) is bool
                descriptor = result["catalogue"]
                if descriptor is not None:
                    assert set(descriptor) == {"schema_version", "catalogue_id", "revision", "sha256", "qualified"}
                    assert type(descriptor["revision"]) is int and type(descriptor["qualified"]) is bool
                    assert descriptor["revision"] == int(values["catalogue_revision"])
                    assert descriptor["sha256"] == values["catalogue_sha256"]
                    assert descriptor["catalogue_id"] == values["catalogue_id"]
                identifiers = result["eligible_entry_ids"]
                ordered = [e["id"] for e in example_catalogue.catalogue()["entries"]]
                assert type(identifiers) is list and len(identifiers) <= 14 and len(set(identifiers)) == len(identifiers)
                assert identifiers == [identifier for identifier in ordered if identifier in identifiers]
                if result["available"]:
                    assert descriptor is not None and descriptor["qualified"] is True
                    observation_id = UUID(result["observation_id"])
                    assert observation_id.version == 4 and str(observation_id) == result["observation_id"]
                else:
                    assert result["track_id"] is None and result["observation_id"] is None and identifiers == []
            receipts.append({"status": response.status, "available": result.get("available"),
                             "eligible_entry_ids": result.get("eligible_entry_ids"),
                             "synthetic_request": values, "response_body": result})
            return result, response.status

        owner = storage._observation_owner()
        stable = (dict(domain), dict(vars(runtime)), owner.revision, owner.pending, owner.uncertain,
                  {str(p.relative_to(config)): p.read_bytes() for p in config.rglob("*") if p.is_file()})
        with patch.object(DJConnectRuntime, "config", property(lambda _: (_ for _ in ()).throw(
                AssertionError("GET creating config accessor forbidden")))), patch.object(
                profile_backend, "profile_backend_runtime", side_effect=AssertionError("GET adapter creation forbidden")), patch.object(
                storage._store, "async_load", side_effect=AssertionError("GET Store load forbidden")), patch.object(
                storage._store, "async_save", side_effect=AssertionError("GET Store save forbidden")), patch.object(
                runtime, "authorize_device_request", side_effect=AssertionError("GET auth learning forbidden")):
            result, code = await request()
            assert code == 200 and result["available"] is True and result["track_id"] is None
            assert result["session_id"] is None and len(result["eligible_entry_ids"]) == 9, result
            result, code = await request({"surface": "active_session", "session_id": active.session_id})
            assert code == 200 and result["available"] is True and len(result["eligible_entry_ids"]) == 14, result
            for language in ("de", "fr", "es"):
                result, code = await request({"language": language})
                assert code == 200 and result["eligible_entry_ids"] == []
            result, code = await request({"catalogue_revision": str(pin["revision"] + 1)})
            assert code == 200 and result["available"] is False and result["catalogue"] is None
            for session in ("null", "None", "foreign"):
                result, code = await request({"session_id": session})
                assert code == 200 and result["available"] is False
            for suffix in ("&language=nl", "&catalogue_%72evision=2", "&session_id=%GG", "&extra=1"):
                _, code = await request(raw=urlencode(query) + suffix)
                assert code == 400, (suffix, code)
            _, code = await request(body=b"not a GET payload")
            assert code == 400
            _, code = await request(supplied_headers={})
            assert code == 401
        after = (dict(domain), dict(vars(runtime)), owner.revision, owner.pending, owner.uncertain,
                 {str(p.relative_to(config)): p.read_bytes() for p in config.rglob("*") if p.is_file()})
        assert stable == after, "pure GET changed committed/runtime/Store state"
        # Lost task metadata closes only the actual four model-dependent entries.
        original_options = dict(subentry.data)
        hass.config_entries.async_update_subentry(model_entry, subentry,
            data={**original_options, "reasoning_effort": "low"})
        result, code = await request({"surface": "active_session", "session_id": active.session_id})
        assert code == 200 and result["available"] and len(result["eligible_entry_ids"]) == 10
        assert not {"play.artist", "play.cooking", "play.quiet", "listen.artist"} & set(result["eligible_entry_ids"])
        # A genuine queued storage writer, not an arbitrary runtime boolean.
        await storage._write_lock.acquire()
        writer = asyncio.create_task(storage.async_save())
        await asyncio.sleep(0)
        try:
            result, code = await request()
            assert code == 200 and not result["available"]
        finally:
            storage._write_lock.release()
            await writer
        # Two lost anchors do not bootstrap through normal public setup again.
        del profile_observation._owners[hass]
        del hass.data[profile_observation._WITNESS]
        with patch.object(setup, "_async_setup_component", dependency_fixture):
            assert await setup.async_setup_component(hass, "djconnect", {})
        assert bootstrap_calls == ["djconnect"]
        result, code = await request()
        assert code == 200 and not result["available"]
    await api.close()
    assert source_hashes() == before
    result = {"status": "PASS", "scope": "actual_HA_2026.10_paired_loopback_R5_committed_Store_public_Task_only",
        "source_hashes": before, "source_before_after_equal": True, "cases": receipts,
        "normal_public_component_setup_calls": len(bootstrap_calls),
        "setup_dependency_boundary": "synthetic dependency resolution invoking real Core async_setup; no hardware discovery",
        "all14_selected_class_eligible": True, "global9_no_borrow": True,
        "DE_FR_ES_pending": True, "GET_Store_runtime_owner_state_unchanged": True,
        "model_calls": 0, "external_provider_calls": 0,
        "installed_native_audio_or_physical_acceptance": "NOT_RUN"}
    (lab / "http-producer-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "cases": len(receipts), "model_calls": 0}))


if __name__ == "__main__":
    asyncio.run(main())
