"""Real HA/OpenAI TTS via selected pipeline and ordinary paired Core routes.

Only synthetic owners, public musical questions and their exact accepted answers.
No installed HA configuration is mounted or modified; credentials arrive on stdin
through the existing bounded lab transport and are never written or printed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from dataclasses import asdict


async def run(hass, runtime, client, post, identity, output, bundle, headers):
    from homeassistant.components import tts
    from homeassistant.components.openai_conversation.tts import OpenAITTSEntity
    from homeassistant.components.assist_pipeline.pipeline import async_get_pipeline, KEY_ASSIST_PIPELINE
    from custom_components.djconnect import speech_processor
    from custom_components.djconnect.domain import ProfilePrivacyMode

    entry = hass.config_entries.async_get_entry(bundle[0].entry_id)
    subentry = entry.subentries["own-generic-tts"]
    entity = OpenAITTSEntity(entry, subentry)
    entity.entity_id = "tts.owned_actual_openai"
    await hass.data[tts.DATA_COMPONENT].async_add_entities([entity])
    store = hass.data[KEY_ASSIST_PIPELINE].pipeline_store
    preferred = async_get_pipeline(hass)
    selected = await store.async_create_item({
        "name": "Owned explicit OpenAI selection", "language": "nl",
        "conversation_engine": preferred.conversation_engine, "conversation_language": "*",
        "stt_engine": None, "stt_language": None, "tts_engine": entity.entity_id,
        "tts_language": "nl-NL", "tts_voice": "marin",
        "wake_word_entity": None, "wake_word_id": None})
    hass.config_entries.async_update_entry(runtime.entry,
        data={**runtime.entry.data, "assist_pipeline_id": selected.id})
    assert runtime.config["assist_pipeline_id"] == selected.id
    assert preferred.tts_engine != entity.entity_id
    assert async_get_pipeline(hass).id == preferred.id
    api = bundle[1]
    speech = api.audio.speech.with_streaming_response
    create = speech.create
    calls = []
    def measured(**kwargs):
        assert len(calls) < 5
        assert kwargs["model"] == subentry.data["chat_model"]
        assert kwargs["voice"] == "marin"
        assert "spotify:" not in kwargs["input"]
        calls.append({"model": kwargs["model"], "voice": kwargs["voice"],
                      "input_sha256": hashlib.sha256(kwargs["input"].encode()).hexdigest(),
                      "input_characters": len(kwargs["input"]), "format": kwargs["response_format"]})
        return create(**kwargs)
    speech.create = measured
    questions = {
        "en": ("en-US", "Explain in one short sentence what an ostinato is in music."),
        "nl": ("nl-NL", "Leg in één korte zin uit wat een ostinato is in muziek."),
        "de": ("de-DE", "Erkläre in einem kurzen Satz, was ein Ostinato in der Musik ist."),
        "fr": ("fr-FR", "Explique en une courte phrase ce qu’est un ostinato en musique."),
        "es": ("es-ES", "Explica en una frase corta qué es un ostinato en música.")}
    rows = []
    failure_fixture = None
    for locale, (language, question) in questions.items():
        update = asdict(selected)
        update.pop("id")
        await store.async_update_item(selected.id, {**update, "language": locale, "tts_language": language})
        started_session = await post("/session/start", {**identity, "mood": "groove", "locale": locale}, expected=201)
        session_id = started_session["session"]["session_id"]
        await post("/session/presence", {**identity, "contract_version": 1,
            "session_id": session_id, "selected_presence": "music_only", "expected_presence_revision": 0})
        before = len(calls)
        options = await post("/speech/voice-options", {**identity, "contract_version": 1})
        assert options["speech_voice_options"]["state"] == "available", options
        assert options["speech_voice_options"]["provider_voice"]["engine"] == entity.entity_id
        assert len(calls) == before
        answer = await post("/ask_dj/message", {**identity,
            "client_message_id": "generic-real-" + locale, "text": question,
            "language": locale, "audio_response": "never", "speech_contract_version": 1,
            "conversation_context": {"session_id": session_id}})
        descriptor = answer["session_speech"]
        exact = "".join(segment["text"] for segment in descriptor["segments"])
        assert exact == answer["text"]
        request = {**identity, "contract_version": 1, "reference": descriptor["reference"],
                   "processor": "ha_configured", "voice_preference": "default"}
        started = time.monotonic()
        prepared = await post("/speech/prepare", request)
        actual = prepared["session_speech"]
        assert actual["audio_state"] == "ready", prepared
        assert actual["effective_voice"]["pipeline_id"] == selected.id
        assert actual["effective_voice"]["voice_id"] == "marin"
        assert actual["effective_voice"]["locale"] == language
        assert len(calls) == before + 1
        assert calls[-1]["input_sha256"] == hashlib.sha256(exact.encode()).hexdigest()
        asset = actual["audio_reference"]["asset_id"]
        audio = await client.post("/api/djconnect/v1/speech/audio",
            json={**identity, "contract_version": 1, "asset_id": asset}, headers=headers)
        body = await audio.read()
        assert audio.status == 200 and audio.headers["Cache-Control"] == "no-store"
        assert audio.content_type == "audio/mpeg" and speech_processor._valid_mp3(body)
        cached = await post("/speech/prepare", request)
        assert cached["session_speech"]["audio_reference"] == actual["audio_reference"]
        assert len(calls) == before + 1
        female = await post("/speech/prepare", {**request, "voice_preference": "female"})
        assert female["session_speech"]["reason"] == "voice_gender_unavailable"
        assert len(calls) == before + 1
        unauthenticated = await client.post("/api/djconnect/v1/speech/audio",
            json={**identity, "contract_version": 1, "asset_id": asset})
        assert unauthenticated.status == 401
        if locale == "es":
            # Only the external provider's failure is a fixture. Actual HA
            # pipeline/owner/prepare/byte/status handlers and fences stay real.
            from openai import OpenAIError
            await store.async_update_item(selected.id, {**update, "language": locale,
                "tts_language": language, "tts_voice": "cedar"})
            stale = await client.post("/api/djconnect/v1/speech/audio",
                json={**identity, "contract_version": 1, "asset_id": asset}, headers=headers)
            stale_body = await stale.json()
            assert stale.status == 409
            assert stale.content_type == "application/json" and stale.headers["Cache-Control"] == "no-store"
            assert stale_body["notification"]["code"] == "tts_configuration_changed"
            external_failures = []
            def failure(**kwargs):
                external_failures.append(True)
                raise OpenAIError("SYNTHETIC_PROVIDER_FAILURE_DO_NOT_EXPOSE")
            speech.create = failure
            failed = await post("/speech/prepare", request)
            assert failed["session_speech"]["notification"]["code"] == "tts_preparation_failed"
            assert "SYNTHETIC_PROVIDER_FAILURE" not in json.dumps(failed)
            failure_status = await post("/speech/voice-options", {**identity, "contract_version": 1})
            state = failure_status["speech_voice_options"]["provider_status"]
            assert state["synthesis_state"] == "failed"
            assert state["notification"]["actions"][0] == "review_ha_tts_configuration"
            blocked = await post("/speech/prepare", request)
            assert blocked["session_speech"]["reason"] == "speech_retry_backoff"
            assert external_failures == [True]
            entity._attr_available = False
            disconnected = await post("/speech/voice-options", {**identity, "contract_version": 1})
            assert disconnected["speech_voice_options"]["notification"]["code"] == "tts_provider_unavailable"
            entity._attr_available = True
            speech.create = measured
            failure_fixture = {"scope": "EXTERNAL_OPENAI_FAILURE_ONLY_IS_FIXTURE",
                "configuration_change_audio": stale_body, "configuration_change_audio_status": stale.status,
                "failed_prepare": failed, "provider_status": failure_status,
                "provider_unavailable": disconnected, "external_failure_attempts": 1,
                "no_automatic_retry_or_extra_model_tts_call": True}
        await post("/session/end", {**identity, "session_id": session_id})
        ended = await client.post("/api/djconnect/v1/speech/audio",
            json={**identity, "contract_version": 1, "asset_id": asset}, headers=headers)
        assert ended.status == 404
        rows.append({"locale": locale, "accepted_answer": exact, "voice_options": options,
                     "prepared": prepared, "audio_status": audio.status, "content_type": audio.content_type,
                     "audio_bytes": len(body), "audio_sha256": hashlib.sha256(body).hexdigest(),
                     "latency_seconds": round(time.monotonic()-started, 3),
                     "cached_no_new_call": True, "gender_unavailable": True,
                     "active_session_manual_speech_in_music_only": True,
                     "session_end_audio_status": ended.status,
                     "unauthenticated_status": unauthenticated.status})
    # Real authority withdrawal, no API/model/synthesis replay.
    storage = hass.data["djconnect"]["djconnect_profile_platform"]
    await storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.SHARED)
    await storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.NORMAL)
    gone = await client.post("/api/djconnect/v1/speech/audio",
        json={**identity, "contract_version": 1, "asset_id": asset}, headers=headers)
    assert gone.status == 404
    root = Path(__file__).resolve().parents[2]
    receipt = {"scope": "REAL_ISOLATED_HA_PAIRED_CORE_AND_ACTUAL_OPENAI_TTS_NOT_INSTALLED_OR_NATIVE_AUDIBLE",
               "ordinary_pairing": True, "selected_not_preferred": True, "rows": rows,
               "synthesis_calls": calls, "model_calls": len(bundle[2]), "withdrawal_status": gone.status,
               "runtime_failure_fixture": failure_fixture,
               "no_playback_or_installed_config_change": True,
               "source_hashes": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (root / "custom_components/djconnect").rglob("*.py")}}
    (output / "generic-ha-tts-real.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("GENERIC_HA_TTS_REAL_PAIRED_PASS_5_LANGUAGES", flush=True)
