# ruff: noqa: E402
"""Actual HA current recording proof; only external Spotify wire is a loopback fixture."""

import asyncio
import os
import json
import sys
import time
import socket
import secrets
import hashlib
from copy import deepcopy
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from urllib.parse import urlsplit
from dataclasses import replace
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import ConfigEntry, ConfigEntries, ConfigEntryStore, ConfigEntryState
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


async def main():
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "custom_components/djconnect").rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    config = LAB / ("current-insight-ha-" + secrets.token_hex(4))
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
            "assist_pipeline_id": "current-insight-fixture-pipeline",
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
    # Real SDK agent class/public registration, with a declared offline response boundary.
    # Keep qualify_agent and all owner/privacy/Store guards on the normal route.
    from homeassistant.components import conversation
    from homeassistant.components.openai_conversation.conversation import OpenAIConversationEntity
    from homeassistant.components.assist_pipeline.pipeline import (
        PipelineStore, STORAGE_KEY, STORAGE_VERSION, STORAGE_VERSION_MINOR, async_setup_pipeline_store,
    )
    from unittest.mock import patch
    from custom_components.djconnect import pipeline
    from homeassistant.components.homeassistant.exposed_entities import ExposedEntities
    from homeassistant.components.homeassistant.const import DATA_EXPOSED_ENTITIES
    exposure = ExposedEntities(hass)
    await exposure.async_initialize()
    hass.data[DATA_EXPOSED_ENTITIES] = exposure
    await conversation.async_setup(hass, {})
    model_entry = ConfigEntry(domain="openai_conversation", title="Offline current insight fixture",
        entry_id="current-insight-fixture-agent", data={}, options={}, discovery_keys=MappingProxyType({}),
        source="user", unique_id="current-insight-fixture-agent", version=2, minor_version=7,
        subentries_data=[{"subentry_id":"current-insight-fixture-subentry", "subentry_type":"conversation",
            "title":"Offline current insight fixture", "data":{"llm_hass_api":[], "store_responses":False,
                "web_search":False, "code_interpreter":False,
                "prompt":"Answer only the explicitly supplied synthetic history question."}}])
    model_entry.runtime_data = SimpleNamespace()
    model_agent = OpenAIConversationEntity(model_entry, model_entry.subentries["current-insight-fixture-subentry"])
    model_agent.hass = hass
    conversation.async_set_agent(hass, model_entry, model_agent)
    settings={"id":"current-insight-fixture-pipeline", "name":"Offline current insight fixture", "language":"nl",
        "conversation_engine":model_entry.entry_id, "conversation_language":"nl",
        "stt_engine":None, "stt_language":None, "tts_engine":None, "tts_language":None,
        "tts_voice":None, "wake_word_entity":None, "wake_word_id":None}
    await PipelineStore(hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_VERSION_MINOR).async_save(
        {"items":[settings], "preferred_item":settings["id"]})
    await async_setup_pipeline_store(hass)
    mode = {"uri": "spotify:track:" + "A" * 22, "position": 10000, "reads": 0,
            "delay_at": None, "fail": False}
    entered, release = asyncio.Event(), asyncio.Event()
    provider_calls = []
    model_calls = []
    async def conversation(hass, data, **kwargs):
        assert data.get("agent_id") == model_entry.entry_id and kwargs.get("allow_agent_fallback") is False
        if mode.get("copy_runtime_during_model"):
            original_runtime = manager.current_active("artwork-profile")
            replacement = manager._record_performance_memory("artwork-profile", original_runtime)
            assert replacement is not original_runtime and replacement.broadcast is original_runtime.broadcast
            mode["model_runtime_copies"] = mode.get("model_runtime_copies", 0) + 1
        model_calls.append("EXTERNAL_MODEL_REPLY_FIXTURE_NOT_REAL_PROVIDER")
        assert mode.get("allow_model"), "Catalog-only or old-source context has no model grant"
        body = ({"supported": True, "language_ok": True, "style_ok": True}
                if "Review every claim" in data["text"] else
                {"summary": "Een gekwalificeerde componistbijdrage.",
                 "full_text": "Een gekwalificeerde componistbijdrage.", "listening_cues": []})
        return {"response": {"speech": {"plain": {"speech": json.dumps(body)}}}}

    async def provider(req):
        provider_calls.append({"method": req.method, "path": req.path})
        assert req.method == "GET"
        if req.path == "/v1/me/tracks/contains":
            return web.json_response([False])
        if req.path == "/v1/artists":
            return web.json_response({"artists": [ARTIST]})
        assert req.path == "/v1/me/player", req.path
        mode["reads"] += 1
        if mode.get("copy_runtime_during_provider"):
            original_runtime = manager.current_active("artwork-profile")
            replacement = manager._record_performance_memory("artwork-profile", original_runtime)
            assert replacement is not original_runtime and replacement.broadcast is original_runtime.broadcast
            mode["provider_runtime_copies"] = mode.get("provider_runtime_copies", 0) + 1
        item = deepcopy(TRACK)
        item["uri"] = mode["uri"]
        item["id"] = mode["uri"].split(":")[-1]
        item["name"] = mode.get("metadata_title", TRACK["name"])
        body = {"is_playing": True, "progress_ms": mode["position"], "item": item,
                "device": {"id": "fixture-output", "name": "Fixture output"}}
        if mode["delay_at"] == mode["reads"]:
            entered.set()
            await release.wait()
        if mode["fail"]:
            return web.json_response({"error": {"message": "Synthetic source unavailable"}}, status=503)
        return web.json_response(body)

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", provider)
    cases, responses = {}, {}
    with patch.object(pipeline, "_call_conversation_process_transport", conversation):
        async with TestClient(TestServer(app)) as upstream, TestClient(TestServer(hass.http.app)) as client:
            sessions = hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})
            network_key = aiohttp_client._make_key(True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT)
            network = Network(upstream)
            sessions[network_key] = network
            pair = await client.post("/api/djconnect/v1/pair", json={**ident, "pair_code": "123456"})
            paired = await pair.json()
            assert pair.status == 200, paired
            headers = {"Authorization": "Bearer " + paired["device_token"],
                       "X-DJConnect-Device-ID": ident["device_id"], "X-DJConnect-Client-Type": "ios"}
            selector = {"track_insight_subject": {"schema_version": 1, "mode": "current"}}
            async def detail(extra=None):
                response = await client.post("/api/djconnect/v1/track_insight",
                                             json={**ident, **selector, "language": "nl", **(extra or {})}, headers=headers)
                assert response.headers.get("Cache-Control") == "no-store"
                return response.status, await response.json()
            memory_before = deepcopy(rt.memory.data)
            before_storage = deepcopy(storage.household)
            code, a = await detail()
            assert code == 200, a
            assert a["subject"]["mode"] == "current" and a["subject"]["media_identity"] == mode["uri"]
            assert a["analysis"]["basis"] == "unmeasured_metadata_only_v1" and a["analysis"]["energy"] is None
            assert a["track"]["genres"] == ["jazz"] and rt.last_playback is None
            responses["current"] = deepcopy(a)
            cases["ordinary_pair_exact_current_no_session_no_model"] = "PASS"
            mode["position"] = 12000
            code, cached = await detail()
            assert code == 200 and cached["cache"]["hit"], cached
            assert cached["subject"]["observation_id"] == a["subject"]["observation_id"]
            assert cached["subject"]["expires_at"] == a["subject"]["expires_at"]
            assert cached["track"]["progress_ms"] == 12000
            cases["cache_current_metadata_original_deadline"] = "PASS"
            mode["uri"] = "spotify:track:" + "B" * 22
            code, b = await detail()
            assert code == 200 and b["track"]["title"] == a["track"]["title"], b
            assert b["subject"]["media_identity"] != a["subject"]["media_identity"]
            assert b["subject"]["observation_id"] != a["subject"]["observation_id"]
            cases["same_name_versions_are_distinct"] = "PASS"
            # Actual profile source revision replacement retains exact recording but
            # must not carry an opaque observation epoch into the new source context.
            source_options = dict(slot.options)
            source_options["music_backend_revision"] = 1
            hass.config_entries.async_update_entry(slot, options=source_options)
            code, revised = await detail()
            assert code == 200 and revised["subject"]["media_identity"] == b["subject"]["media_identity"], revised
            assert revised["subject"]["observation_id"] != b["subject"]["observation_id"]
            cases["new_source_revision_same_recording_new_epoch"] = "PASS"
            before_calls = len(provider_calls)
            code, mixed = await detail({"title": "Untrusted alternate"})
            assert code == 400 and mixed["error"] == "invalid_track_insight_subject", mixed
            assert len(provider_calls) == before_calls
            cases["mixed_authority_before_source_read"] = "PASS"
            mode["fail"] = True
            rt.update(last_playback={"uri": mode["uri"], "track_name": "Stale", "artist_name": "Stale"})
            code, unavailable = await detail()
            assert code == 503 and unavailable["error"] == "current_track_unavailable", unavailable
            mode["fail"] = False
            cases["failed_source_never_uses_runtime_fallback"] = "PASS"
            for phase in ("initial", "final"):
                entered.clear()
                release.clear()
                mode["delay_at"] = mode["reads"] + (1 if phase == "initial" else 2)
                pending = asyncio.create_task(detail())
                try:
                    await asyncio.wait_for(entered.wait(), 5)
                    # Actual production Runtime.update, not a mocked service or frame.
                    for uri in ("spotify:track:" + "A" * 22, mode["uri"]):
                        rt.update(last_playback={"uri": uri, "is_playing": True, "progress_ms": 12000,
                                                 "device": {"name": "Fixture output"}})
                    release.set()
                    code, late = await asyncio.wait_for(pending, 5)
                    assert code == 409 and late["error"] == "track_insight_context_changed", late
                finally:
                    release.set()
                    if not pending.done():
                        pending.cancel()
                        await asyncio.gather(pending, return_exceptions=True)
                cases[phase + "_source_await_actual_runtime_aba"] = "PASS"
                mode["delay_at"] = None
            # Build an actual current CC0 opportunity through the existing Runtime
            # producer. Only normalized external evidence and model replies are fixtures.
            assert not model_calls
            from custom_components.djconnect.session_runtime import session_runtime_manager
            from custom_components.djconnect.session_facts import _fact, DisplayFactCore
            manager = session_runtime_manager(hass)
            active = await manager.async_start(owner_profile_id="artwork-profile", locale="nl",
                music_backend="spotify_direct", history_source_context={
                    "backend_id": "spotify_direct", "music_account_id": "artwork-account",
                    "provider_entry_id": slot.entry_id, "provider_account_id": "fixture-client"})
            await manager.async_update_playback_projection(owner_profile_id="artwork-profile", session_id=active.session_id,
                state="playing", media_identity=mode["uri"], title=TRACK["name"], artist=TRACK["artists"][0]["name"],
                album=TRACK["album"]["name"], duration_ms=TRACK["duration_ms"], position_ms=mode["position"],
                target_name="Fixture output")
            fact = _fact("work_composers", {"uri": mode["uri"]}, "track_context",
                ["Fixture composer"] * 5, ["Fixture composer is credited as composer."] * 5,
                "MusicBrainz", "https://musicbrainz.org/work/11111111-1111-1111-1111-111111111111",
                DisplayFactCore("work_composers", roles=(("composer", ("Fixture composer",)),)))
            async def knowledge():
                return {"_qualified_facts": (fact,)}
            await manager.async_process_track_started(owner_profile_id="artwork-profile", session_id=active.session_id,
                media_identity=mode["uri"], insight_provider=knowledge, require_current_playback=True, allow_initial_facts=True)
            opportunity = manager._intra_track_opportunities["artwork-profile"]
            assert any(value is fact for value in opportunity.qualified_facts)
            # Current CC0 knowledge is independent of the Planner's publication
            # decision; no Moment publication is manufactured to make detail available.
            mode["allow_model"] = True
            mode["copy_runtime_during_provider"] = True
            mode["copy_runtime_during_model"] = True
            code, qualified = await detail()
            assert code == 200 and qualified["analysis"]["basis"] == "qualified_credit_and_interpretation_v1", qualified
            assert len(model_calls) == 2
            assert mode["provider_runtime_copies"] >= 2
            assert mode["model_runtime_copies"] == 2
            mode["copy_runtime_during_provider"] = False
            mode["copy_runtime_during_model"] = False
            repeated_subject = qualified["subject"]
            mode["copy_runtime_during_provider"] = True
            code, same_subject = await detail()
            mode["copy_runtime_during_provider"] = False
            assert code == 200, same_subject
            assert same_subject["subject"]["observation_id"] == repeated_subject["observation_id"]
            assert same_subject["subject"]["expires_at"] == repeated_subject["expires_at"]
            assert len(model_calls) == 2  # Real guarded cache; no extra generation.
            cases["actual_Runtime_value_copies_across_provider_generation_assessment_final_read_keep_original_admission"] = "PASS"
            cases["repeated_value_copies_retain_original_frame_and_expiry_without_extra_model_calls"] = "PASS"
            assert qualified["analysis"]["energy"] is None
            cases["actual_cc0_original_source_shared_generation_assessment_fixture"] = "PASS"
            # A real paired owner stays current while contradictory provider
            # metadata withdraws this original subject permanently.
            from custom_components.djconnect.hybrid_service import PairedAuthority
            from custom_components.djconnect.current_track_insight import resolve as resolve_current
            from custom_components.djconnect.track_insight import TrackInsightRequest, TrackInsightError
            bound = await PairedAuthority.resolve(hass, ident, headers)
            metadata_subject = await resolve_current(hass, rt, TrackInsightRequest(locale="nl"),
                owner_profile_id="artwork-profile", validate_owner=bound.validate_now)
            mode["metadata_title"] = "Contradictory provider metadata"
            try:
                await metadata_subject.verify()
            except TrackInsightError as error:
                assert error.code == "track_insight_context_changed"
            else:
                raise AssertionError("contradictory provider metadata was accepted")
            mode.pop("metadata_title")
            bound.validate_now()
            try:
                metadata_subject.guard()
            except TrackInsightError as error:
                assert error.code == "track_insight_context_changed"
            else:
                raise AssertionError("observed metadata denial rearmed original subject")
            cases["contradictory_metadata_with_real_paired_owner_latches_original_subject"] = "PASS"

            assert rt.memory.data == memory_before
            assert storage.household == before_storage
            cases["closed_current_no_profile_dna_history_or_playback_effect"] = "PASS"
            mode["allow_model"] = False
            original_source = manager._history_source_contexts[active.session_id]
            count = len(active.broadcast.state.dj_moments)
            for field in ("backend_id", "music_account_id", "provider_entry_id", "provider_account_id"):
                original_value = original_source[field]
                original_source[field] = "different-original-source"
                code, no_source = await detail()
                assert code == 200 and no_source["analysis"]["basis"] == "unmeasured_metadata_only_v1", no_source
                assert len(model_calls) == 2
                ordinary = await client.post("/api/djconnect/v1/track_insight",
                    json={**ident, "language": "nl"}, headers=headers)
                ordinary_body = await ordinary.json()
                assert ordinary.status == 200 and ordinary_body["analysis"]["basis"] == "unmeasured_metadata_only_v1", ordinary_body
                assert len(model_calls) == 2
                original_source[field] = original_value
            assert len(active.broadcast.state.dj_moments) == count
            cases["four_original_source_fields_cannot_transfer_cc0_model_rights"] = "PASS"
            cases["ordinary_no_selector_has_same_original_source_join"] = "PASS"
            # Legacy ordinary status retains its existing opt-in-aware empty
            # record bookkeeping. It must not learn while opted out; the new
            # closed selector above remains entirely inert.
            for record in rt.memory.data.get("memories", {}).values():
                assert not record.get("enabled")
                for key in ("recent_tracks", "chat_facts", "favorite_artists", "favorite_genres", "track_insight_energy_signals"):
                    assert not record.get(key)
            memory_before = deepcopy(rt.memory.data)
            cases["legacy_status_no_optout_learning"] = "PASS"
            entered.clear()
            release.clear()
            mode["delay_at"] = mode["reads"] + 1
            pending = asyncio.create_task(detail())
            try:
                await asyncio.wait_for(entered.wait(), 5)
                rt.device_token = "synthetic-withdrawn-token"
                release.set()
                code, withdrawn = await asyncio.wait_for(pending, 5)
                assert code == 401, withdrawn
            finally:
                release.set()
                if not pending.done():
                    pending.cancel()
                    await asyncio.gather(pending, return_exceptions=True)
            cases["paired_authority_withdrawn_during_source_read"] = "PASS"
            assert len(model_calls) == 2
            assert rt.memory.data == memory_before
            assert storage.household == before_storage
            cases["withdrawn_closed_current_remains_inert"] = "PASS"
            responses["mixed"] = mixed
            responses["unavailable"] = unavailable
            responses["withdrawn"] = withdrawn
            for response in responses.values():
                if response.get("subject"):
                    response["subject"]["observation_id"] = "<opaque-observation-redacted>"
            after = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sorted((ROOT / "custom_components/djconnect").rglob("*"))
                     if path.is_file() and "__pycache__" not in path.parts}
            assert source_hashes == after
            record = {"schema_version": 1, "qualification": "ACTUAL_ISOLATED_HA_PAIRED_HTTP_SYNTHETIC_ONLY",
                      "ha_sdk_version": __import__("homeassistant.const", fromlist=["__version__"]).__version__,
                      "source_files_sha256": source_hashes, "source_unchanged": True,
                      "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      "cases": cases, "responses": responses, "provider_calls": provider_calls,
                      "model_provider_calls": 0, "model_reply_fixture_calls": len(model_calls), "installed": "NOT_RUN", "native": "NOT_RUN"}
            (LAB / "qualification.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"cases": cases, "source_files": len(source_hashes), "model_calls": 0}))
            sessions.pop(network_key)
    await hass.async_stop()


asyncio.run(main())
