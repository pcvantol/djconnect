"""Own networkless HA early speech contract proof; only provider I/O is fixture.

No HA-dev/prod credentials, runtime replacement, consumer or audible claim.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import logging
from types import SimpleNamespace
import secrets
import socket
import sys
import time

from aiohttp import ClientSession
from aiohttp.test_utils import TestClient, TestServer
from homeassistant.helpers import aiohttp_client
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.helpers import area_registry, device_registry, entity_registry

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.domain import ProfilePrivacyMode  # noqa: E402
from custom_components.djconnect.persistence import async_initialize_persistence, async_shutdown_persistence  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402
from custom_components.djconnect.spotify_backend import SpotifyBackend  # noqa: E402
from custom_components.djconnect.session_facts import SessionFactsResolver  # noqa: E402


async def processor_fixture(hass):
    """External Wyoming service only is a fixture; HA entity/inventory/TCP are real."""
    from homeassistant.components import tts, websocket_api
    from homeassistant.components.wyoming.tts import WyomingTtsProvider
    from homeassistant.components.wyoming.data import WyomingService
    from homeassistant.components.assist_pipeline.pipeline import (
        PipelineStore, STORAGE_VERSION, STORAGE_KEY, STORAGE_VERSION_MINOR, async_setup_pipeline_store)
    from homeassistant.helpers.entity_component import EntityComponent
    from wyoming.info import Info, TtsProgram, TtsVoice, Attribution
    from wyoming.event import async_read_event, async_write_event
    from wyoming.audio import AudioChunk, AudioStop
    from wyoming.tts import Synthesize
    from custom_components.djconnect.wav_util import simple_tone_wav
    import io
    import wave
    calls = []
    async def wire(reader, writer):
        try:
            event = await async_read_event(reader)
            assert Synthesize.is_type(event.type)
            request = Synthesize.from_event(event)
            calls.append(request.text)
            with wave.open(io.BytesIO(simple_tone_wav()), "rb") as audio:
                await async_write_event(AudioChunk(rate=audio.getframerate(), width=audio.getsampwidth(),
                    channels=audio.getnchannels(), audio=audio.readframes(audio.getnframes())).event(), writer)
            await async_write_event(AudioStop().event(), writer)
        finally:
            writer.close()
            await writer.wait_closed()
    server = await asyncio.start_server(wire, "127.0.0.1", 0)
    attribution = Attribution("Synthetic installed local fixture", "https://example.invalid/fixture")
    voice = TtsVoice(name="fixture-en", attribution=attribution, installed=True, description="Fixture inventory voice",
                     version="1", languages=["en"])
    info = Info(tts=[TtsProgram(name="piper", attribution=attribution, installed=True,
                               description="External waveform fixture, not audible voice proof", version="1", voices=[voice])])
    service = WyomingService("127.0.0.1", server.sockets[0].getsockname()[1], info)
    coordinator = SimpleNamespace(data=info, async_add_listener=lambda callback: lambda: None)
    entity = WyomingTtsProvider(SimpleNamespace(entry_id="own-wyoming-fixture"), coordinator, service)
    entity.entity_id = "tts.own_piper_fixture"
    component = EntityComponent(logging.getLogger(__name__), "tts", hass)
    hass.data[tts.DATA_COMPONENT] = component
    await component.async_add_entities([entity])
    await websocket_api.async_setup(hass, {})
    settings = {"id": "own-speech-pipeline", "name": "Own speech qualification", "language": "en",
                "conversation_engine": None, "conversation_language": None, "stt_engine": None, "stt_language": None,
                "tts_engine": entity.entity_id, "tts_language": "en", "tts_voice": "fixture-en",
                "wake_word_entity": None, "wake_word_id": None}
    await PipelineStore(hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_VERSION_MINOR).async_save(
        {"items": [settings], "preferred_item": settings["id"]})
    await async_setup_pipeline_store(hass)
    return server, calls


async def main():
    output = Path(os.environ.get("DJC_LAB_ROOT", "/lab"))
    config = output / ("speech-" + secrets.token_hex(4))
    config.mkdir(parents=True)
    hass = HomeAssistant(str(config))
    hass.state = CoreState.running
    hass.config.language = "en"
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(cors_origins=[], use_x_forwarded_for=False,
        login_threshold=-1, is_ban_enabled=False, use_x_frame_options=True)
    identity = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"}
    slot = entry("speech-owner", {**identity, "pair_code": "123456", "profile_id": "profile-a",
        "music_backend": "spotify_direct", "music_account_id": "fixture-account",
        "spotify_client_id": "fixture-client", "spotify_refresh_token": "fixture-not-sent"})
    await ConfigEntryStore(hass).async_save({"entries": [slot.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    slot = hass.config_entries.async_get_entry("speech-owner")
    slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    runtime = DJConnectRuntime(slot)
    hass.data["djconnect"] = {"speech-owner": runtime, "runtime": runtime}
    storage = ProfilePlatformStorage(hass)
    hass.data["djconnect"]["djconnect_profile_platform"] = storage
    await storage.async_upsert_music_backend("spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Fixture Spotify")
    await storage.async_create_profile("Synthetic owner", profile_id="profile-a", default_backend_id="spotify_direct")
    await storage.async_upsert_music_account("fixture-account", "spotify_direct", kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic account", linked_profile_ids=frozenset({"profile-a"}), provider_account_id="fixture-client")
    profile = storage.household.profiles["profile-a"]
    await storage.async_update_profile("profile-a", preferences=replace(profile.preferences, default_music_account_id="fixture-account"))
    await storage.async_upsert_device(identity["device_id"], "ios", linked_profile_id="profile-a")
    service = await async_initialize_persistence(hass)
    manager = SessionRuntimeManager(PersistentSessionRepository(service), HistoricalProjectionRepository(service))
    hass.data["djconnect"]["session_runtime_manager"] = manager
    calls = []
    selected_track = ["A"*22]
    def track_item():
        return {"id": selected_track[0], "uri": "spotify:track:"+selected_track[0], "type": "track",
                "name": "Fixture track", "artists": [{"id": "B"*22, "name": "Fixture artist"}],
                "external_ids": {"isrc": "USAAA0100001"}, "duration_ms": 300000,
                "album": {"id": "C"*22, "uri": "spotify:album:"+"C"*22,
                          "name": "Fixture album", "images": []}}
    async def provider(self, method, path, **kwargs):
        calls.append(path)
        if path == "/me/player":
            return {"is_playing": True, "progress_ms": 15000,
                    "device": {"id": "fixture-output", "name": "Fixture"}, "item": track_item()}
        if path == "/me/player/queue":
            return {"queue": []}
        if path.startswith("/me/tracks/contains"):
            return [False]
        if path.startswith("/tracks/"):
            return track_item()
        if path.startswith("/artists/"):
            return {"id": "B"*22, "name": "Fixture artist", "genres": [], "images": []}
        if path.startswith("/artists"):
            return {"artists": [{"id": "B"*22, "name": "Fixture artist", "genres": [], "images": []}]}
        return {}
    async def facts(self, path, params=None, **kwargs):
        if not os.environ.get("DJC_MOMENT_SPEECH"):
            return {}
        calls.append("knowledge:"+path)
        mbid = "12345678-1234-1234-1234-123456789abc"
        rid = "22345678-1234-1234-1234-123456789abc"
        credit = [{"artist": {"id": mbid, "name": "Fixture artist"}}]
        if path.startswith("isrc/"):
            return {"recordings": [{"id": rid, "title": "Fixture track", "artist-credit": credit}]}
        if path.startswith("recording/"):
            return {"id": rid, "title": "Fixture track", "artist-credit": credit, "relations": []}
        if path.startswith("artist/"):
            return {"id": mbid, "name": "Fixture artist", "type": "Group", "life-span": {"begin": "1991"},
                    "relations": [{"type": "streaming", "url": {"resource": "https://open.spotify.com/artist/"+"B"*22}}]}
        return {}
    SpotifyBackend._request = provider
    SessionFactsResolver._get = facts
    provider_session = ClientSession()
    key = aiohttp_client._make_key(True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT)
    hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})[key] = provider_session
    register_http_views(hass)
    receipts = {}
    fixture_server, synthesis_calls = await processor_fixture(hass)
    try:
        async with TestClient(TestServer(hass.http.app)) as client:
            response = await client.post("/api/djconnect/v1/pair", json={**identity, "pair_code": "123456"})
            paired = await response.json()
            assert response.status == 200 and paired["device_token"] == slot.data["device_token"]
            headers = {"Authorization": "Bearer " + paired["device_token"], "X-DJConnect-Device-ID": identity["device_id"]}
            async def post(path, payload, expected=200):
                response = await client.post("/api/djconnect/v1" + path, json=payload, headers=headers)
                body = await response.json()
                assert response.status == expected, (response.status, body)
                assert response.headers["Cache-Control"] == "no-store"
                return body
            session_started_clock = time.monotonic()
            started = await post("/session/start", {**identity, "mood": "groove", "locale": "en"}, expected=201)
            sid = started["session"]["session_id"]
            changed = await post("/session/persona", {**identity, "contract_version": 1, "session_id": sid,
                "selected_persona": "radio_dj", "expected_persona_revision": 0})
            assert changed["persona_revision"] == 1
            reply = await post("/ask_dj/message", {**identity, "client_message_id": "speech-current-artist",
                "text": "Who is this artist?", "language": "en", "audio_response": "never",
                "speech_contract_version": 1,
                "conversation_context": {"session_id": sid}})
            descriptor = reply["session_speech"]
            assert reply["audio_delivery"] == {"mode": "accepted_reference", "state": "deferred"}
            assert descriptor["manual_allowed"] and descriptor["persona"] == "radio_dj", reply
            assert descriptor["segments"][0]["text"] == reply["text"]
            request = {**identity, "contract_version": 1, "reference": descriptor["reference"],
                       "processor": "local_on_device", "voice_preference": "default"}
            before = len(calls)
            prepared = await post("/speech/prepare", request)
            assert prepared["session_speech"]["audio_state"] == "renderer_pending"
            assert prepared["session_speech"]["expires_at"] == descriptor["expires_at"]
            assert not prepared["session_speech"]["autoplay_eligible"]
            # Old native AVPlayer has no paired POST adapter. Keep semantic text
            # accepted, but never downgrade this private audio to a public GET.
            old_reply = await post("/ask_dj/message", {**identity,
                "client_message_id": "old-speech-client", "text": "help",
                "language": "en", "audio_response": "always"})
            assert old_reply["audio_delivery"]["reason"] == "client_protocol_upgrade_required"
            assert not old_reply.get("audio_url")
            assert not old_reply["session_speech"]["autoplay_eligible"]
            receipts["old_client_protocol_disposition"] = old_reply["audio_delivery"]
            assert len(calls) == before
            receipts.update(pairing="normal_device_minted_and_persisted", persona=changed,
                            accepted_reply=reply, manual_after_never=prepared, manual_provider_calls=0)
            rejected = await post("/speech/prepare", {**request, "text": "Caller replacement"}, expected=400)
            receipts["arbitrary_text_rejected"] = rejected
            voice_request = {**identity, "contract_version": 1}
            provider_calls, audio_calls = len(calls), len(synthesis_calls)
            options = await post("/speech/voice-options", voice_request)
            repeated_options = await post("/speech/voice-options", voice_request)
            voice_options = options["speech_voice_options"]
            assert voice_options["default_available"]
            assert voice_options["gender_selection"]["available"] is False
            assert voice_options["gender_selection"]["values"] == []
            assert voice_options["supported_preferences"] == ["default"]
            assert options == repeated_options
            assert len(calls) == provider_calls and len(synthesis_calls) == audio_calls
            receipts["provider_voice_options"] = options
            receipts["voice_options_music_provider_and_synthesis_calls"] = 0
            synthesized = await post("/speech/prepare", {**request, "processor": "ha_configured", "voice_preference": "default"})
            speech = synthesized["session_speech"]
            assert speech["audio_state"] == "ready", synthesized
            assert synthesis_calls == [reply["text"]]
            cached = await post("/speech/prepare", {**request, "processor": "ha_configured", "voice_preference": "default"})
            assert cached["session_speech"]["audio_reference"] == speech["audio_reference"]
            assert len(synthesis_calls) == 1
            asset = speech["audio_reference"]["asset_id"]
            audio = await client.post("/api/djconnect/v1/speech/audio", json={**identity, "contract_version": 1, "asset_id": asset}, headers=headers)
            assert audio.status == 200 and (await audio.read()).startswith(b"RIFF")
            assert audio.headers["Cache-Control"] == "no-store"
            public = await client.get("/api/djconnect/v1/tts/" + asset + ".wav")
            assert public.status == 404
            female = await post("/speech/prepare", {**request, "processor": "ha_configured", "voice_preference": "female"})
            assert female["session_speech"]["reason"] == "voice_gender_unavailable"
            # Real WAV/header/HTTP adapter, with only external STT decoding
            # represented by its existing explicit provider boundary fixture.
            from custom_components.djconnect.wav_util import simple_tone_wav
            stt_calls = []
            async def external_stt(_hass, wav, _config):
                assert wav.startswith(b"RIFF")
                stt_calls.append(len(wav))
                return "Who is this artist?"
            hass.data["djconnect"]["stt_handler"] = external_stt
            voice_headers = {**headers, "X-DJConnect-Client-Type": "ios",
                "Content-Type": "audio/wav", "X-DJConnect-Language": "en",
                "X-DJConnect-Speech-Contract-Version": "1",
                "X-DJConnect-Client-Message-ID": "wave-speech-contract"}
            response = await client.post("/api/djconnect/v1/voice", headers=voice_headers, data=simple_tone_wav())
            voice_reply = await response.json()
            assert response.status == 200, voice_reply
            assert voice_reply["transcript"] == "Who is this artist?"
            assert voice_reply["audio_delivery"] == {"mode": "accepted_reference", "state": "deferred"}
            assert voice_reply["session_speech"]["manual_allowed"]
            assert voice_reply["session_speech"]["autoplay_eligible"]
            assert len(stt_calls) == 1
            response = await client.post("/api/djconnect/v1/voice",
                headers={**voice_headers, "X-DJConnect-Speech-Contract-Version": "true"}, data=simple_tone_wav())
            invalid_voice = await response.json()
            assert response.status == 400 and invalid_voice["error"] == "unsupported_speech_contract"
            assert len(stt_calls) == 1  # Version rejection precedes STT work.
            receipts["wav_speech_contract"] = {"reply": voice_reply,
                "invalid_version": invalid_voice, "external_stt_calls": len(stt_calls)}
            receipts.update(ha_configured_audio=synthesized, ha_gender_unavailable=female,
                            synthesis_calls=1, legacy_public_audio_status=public.status,
                            audible_acceptance="OPEN_EXTERNAL_WAVEFORM_FIXTURE_ONLY")
            if os.environ.get("DJC_MOMENT_SPEECH"):
                # Respect the real existing35s shared presence/readability budget.
                # No clock patch or ledger reset to manufacture an extra Moment.
                print("WAIT_REAL_PRESENCE_INTERVAL", flush=True)
                while time.monotonic()-session_started_clock < 36:
                    await asyncio.sleep(min(2, 36-(time.monotonic()-session_started_clock)))
                selected_track[0] = "D"*22
                for _ in range(150):
                    active = await manager.async_get_active("profile-a")
                    moment = next((m for m in active.broadcast.state.dj_moments if m.source_fact is not None), None)
                    if moment:
                        break
                    await asyncio.sleep(0.1)
                if moment is None:
                    (output / "moment-start-diagnostic.json").write_text(json.dumps({
                        "provider_calls": calls, "broadcast": active.broadcast.as_dict()}, indent=2))
                assert moment is not None, "No real qualified published Moment from the fixture boundary"
                live_request = {**identity, "contract_version": 1,
                    "reference": {"session_id": sid, "moment_id": moment.moment_id},
                    "processor": "ha_configured", "voice_preference": "default"}
                original_persona = moment.presentation_intent.dj_persona.value
                before_count = len(active.broadcast.state.dj_moments)
                spoken = await post("/speech/prepare", live_request)
                live_speech = spoken["session_speech"]
                assert live_speech["audio_state"] == "ready", spoken
                assert "".join(s["text"] for s in live_speech["segments"]) == moment.content
                assert live_speech["persona"] == original_persona
                assert synthesis_calls[-1] == moment.content
                cached_moment = await post("/speech/prepare", live_request)
                assert cached_moment["session_speech"]["audio_reference"] == live_speech["audio_reference"]
                assert cached_moment["session_speech"]["expires_at"] == live_speech["expires_at"]
                assert len(active.broadcast.state.dj_moments) == before_count
                assert "session_speech" not in active.broadcast.as_dict(include_owner_only=False)
                snapshots = active.broadcast.as_dict()["session_speech"]["moments"]
                assert not any(d["autoplay_eligible"] for d in snapshots)
                changed_again = await post("/session/persona", {**identity, "contract_version": 1, "session_id": sid,
                    "selected_persona": "festival_dj", "expected_persona_revision": active.persona_revision})
                old_style = await post("/speech/prepare", {**live_request, "processor": "local_on_device"})
                assert old_style["session_speech"]["persona"] == original_persona
                live_asset = live_speech["audio_reference"]["asset_id"]
                ended = await post("/session/end", {**identity, "session_id": sid})
                rejected_live = await post("/speech/prepare", live_request, expected=404)
                deleted = await client.post("/api/djconnect/v1/speech/audio",
                    json={**identity, "contract_version": 1, "asset_id": live_asset}, headers=headers)
                assert deleted.status == 404
                response = await client.get("/api/djconnect/v1/session/history/"+sid, params=identity, headers=headers)
                timeline = await response.json()
                assert response.status == 200, timeline
                history_entry = next(e for e in timeline["entries"] if e.get("moment_id") == moment.moment_id)
                projected = history_entry["session_speech"]
                assert projected["reference"] == {"session_id": sid, "entry_id": history_entry["entry_id"]}
                assert projected["persona"] == original_persona
                assert not projected["autoplay_eligible"]
                assert "audio_reference" not in projected
                assert "".join(s["text"] for s in projected["segments"]) == moment.content
                retained_request = {**live_request, "reference": {"session_id": sid, "entry_id": history_entry["entry_id"]}}
                retained = await post("/speech/prepare", retained_request)
                assert retained["session_speech"]["audio_state"] == "ready", retained
                assert retained["session_speech"]["persona"] == original_persona
                assert not retained["session_speech"]["autoplay_eligible"]
                assert "".join(s["text"] for s in retained["session_speech"]["segments"]) == moment.content
                receipts["published_and_retained_moment_speech"] = {"moment": moment.as_dict(),
                    "live": spoken, "same_cache": cached_moment, "persona_change": changed_again,
                    "original_style_replay": old_style, "end": ended, "live_after_end": rejected_live,
                    "old_bytes_after_end": deleted.status, "retained_entry": history_entry,
                    "retained_replay": retained, "new_moments_from_listening": 0}
            await storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.SHARED)
            await storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.NORMAL)
            receipts["profile_aba"] = await post("/speech/prepare", request, expected=404)
            assert not hass.data["djconnect"]["tts_audio"]
            denied = await client.post("/api/djconnect/v1/speech/audio", json={**identity, "contract_version": 1, "asset_id": asset}, headers=headers)
            assert denied.status == 404
            receipts["withdrawn_audio_status"] = denied.status
            # An actual uninterrupted idle TTL run can be enabled for qualification.
            duration = int(os.environ.get("DJC_SPEECH_IDLE_SECONDS", "0"))
            if duration:
                reply = await post("/ask_dj/message", {**identity, "client_message_id": "speech-idle",
                    "text": "Who is this artist?", "language": "en", "audio_response": "never"})
                history = runtime.ask_dj_history
                key = reply["session_speech"]["reference"]["turn_id"]
                began = time.monotonic()
                await asyncio.sleep(duration)
                assert all(key not in f.speech_references for f in history.dialogue.owners["profile:profile-a"].values())
                receipts["idle_expiry"] = {"elapsed_seconds": time.monotonic() - began, "no_reads_or_prepares": True,
                                           "body_absent": True}
            receipts["source_hashes"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT / "custom_components/djconnect").rglob("*.py") if "__pycache__" not in p.parts}
            receipts["scope"] = "EARLY_CORE_TRANSPORT_ONLY_NOT_FULL_SLICE_OR_NATIVE_AUDIO"
            (output / "speech-http-early.json").write_text(json.dumps(receipts, indent=2) + "\n")
            print("SPEECH_EARLY_HTTP_PASS", flush=True)
    finally:
        fixture_server.close()
        await fixture_server.wait_closed()
        await provider_session.close()
        await async_shutdown_persistence(hass)
        await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
