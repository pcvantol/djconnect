"""Actual HA Cloud inventory/arguments and paired Core; waveform service fixture.

No Cloud account, installed HA mount, configuration mutation or audible claim.
Public music questions use the existing bounded HA conversation test route.
"""
from dataclasses import asdict
import hashlib
import json
from types import SimpleNamespace


async def run(hass, runtime, client, post, identity, output, bundle, headers):
    from homeassistant.components import tts
    from homeassistant.components.cloud.tts import CloudTTSEntity
    from homeassistant.components.assist_pipeline.pipeline import KEY_ASSIST_PIPELINE, async_get_pipeline
    from hass_nabucasa.voice import MAP_VOICE

    calls = []
    async def external_waveform(**kwargs):
        assert len(calls) < 20
        assert kwargs["gender"] is None  # No deprecated-gender Repair side effect.
        calls.append({"voice": kwargs["voice"], "language": kwargs["language"],
                      "text_sha256": hashlib.sha256(kwargs["text"].encode()).hexdigest()})
        frame = b"\xff\xfb\x90\x00" + bytes(413)
        return frame * 2

    prefs = SimpleNamespace(tts_default_voice=("nl-NL", "ColetteNeural"),
                            async_listen_updates=lambda callback: lambda: None)
    cloud = SimpleNamespace(client=SimpleNamespace(prefs=prefs),
                            voice=SimpleNamespace(process_tts=external_waveform))
    entity = CloudTTSEntity(cloud)
    entity.entity_id = "tts.owned_cloud_fixture"
    await hass.data[tts.DATA_COMPONENT].async_add_entities([entity])
    store = hass.data[KEY_ASSIST_PIPELINE].pipeline_store
    previous = async_get_pipeline(hass)
    selected = await store.async_create_item({
        "name": "Owned Cloud inventory qualification", "language": "nl",
        "conversation_engine": previous.conversation_engine, "conversation_language": "*",
        "stt_engine": None, "stt_language": None, "tts_engine": entity.entity_id,
        "tts_language": "nl-NL", "tts_voice": "ColetteNeural",
        "wake_word_entity": None, "wake_word_id": None})
    hass.config_entries.async_update_entry(runtime.entry,
        data={**runtime.entry.data, "assist_pipeline_id": selected.id})
    rows = []
    for language in ("en-US", "nl-NL", "de-DE", "fr-FR", "es-ES"):
        locale = language[:2]
        targets = {getattr(g, "value", g): v for (lang, g), v in MAP_VOICE.items() if lang == language}
        update = asdict(selected)
        update.pop("id")
        await store.async_update_item(selected.id, {**update, "language": locale,
            "tts_language": language, "tts_voice": targets["female"]})
        session = await post("/session/start", {**identity, "mood": "groove", "locale": locale}, expected=201)
        sid = session["session"]["session_id"]
        await post("/session/presence", {**identity, "contract_version": 1, "session_id": sid,
            "selected_presence": "music_only", "expected_presence_revision": 0})
        before = len(calls)
        options = await post("/speech/voice-options", {**identity, "contract_version": 1})
        repeated = await post("/speech/voice-options", {**identity, "contract_version": 1})
        assert options == repeated and len(calls) == before
        assert options["speech_voice_options"]["gender_selection"]["voice_ids"] == targets
        reply = await post("/ask_dj/message", {**identity,
            "client_message_id": "gender-real-" + locale,
            "text": "Explain briefly what an ostinato is in music.", "language": locale,
            "audio_response": "never", "speech_contract_version": 1,
            "conversation_context": {"session_id": sid}})
        request = {**identity, "contract_version": 1, "reference": reply["session_speech"]["reference"],
                   "processor": "ha_configured", "voice_preference": "male"}
        result = await post("/speech/prepare", request)
        descriptor = result["session_speech"]
        assert descriptor["audio_state"] == "ready", result
        assert descriptor["effective_voice"]["voice_id"] == targets["male"]
        assert descriptor["effective_voice"]["gender"] == "male"
        cached = await post("/speech/prepare", request)
        assert cached["session_speech"]["audio_reference"] == descriptor["audio_reference"]
        assert len(calls) == before + 1
        audio_request = {**identity, "contract_version": 1,
                         "asset_id": descriptor["audio_reference"]["asset_id"]}
        audio = await client.post("/api/djconnect/v1/speech/audio", json=audio_request, headers=headers)
        assert audio.status == 200 and len(await audio.read()) == 834
        conflict = await post("/speech/prepare", {**request, "voice_id": targets["female"]})
        assert conflict["session_speech"]["reason"] == "no_matching_voice"
        # Same instance/voice/locale, but a changed inventory permission revokes old bytes.
        key = next(k for k in MAP_VOICE if k[0] == language and getattr(k[1], "value", k[1]) == "male")
        removed = MAP_VOICE.pop(key)
        try:
            revoked = await post("/speech/voice-options", {**identity, "contract_version": 1})
            assert revoked["speech_voice_options"]["gender_selection"]["values"] == ["female"]
            stale = await client.post("/api/djconnect/v1/speech/audio", json=audio_request, headers=headers)
            assert stale.status == 409, await stale.text()
            error = await stale.json()
            assert error["notification"]["code"] == "tts_voice_language_unavailable"
        finally:
            MAP_VOICE[key] = removed
        await post("/session/end", {**identity, "session_id": sid})
        rows.append({"locale": locale, "options": options, "prepared": result,
                     "cache_single_synthesis": True, "metadata_withdrawal_audio_status": 409})
    assert len(calls) == 5
    assert async_get_pipeline(hass).id == previous.id
    receipt = {"scope": "real isolated HA/Cloud entity and ordinary paired Core; external waveform fixture",
               "native_audible": "NOT_RUN", "rows": rows, "waveform_calls": calls,
               "actual_model_calls": len(bundle[2]), "deprecated_gender_parameters": 0}
    (output / "provider-voice-gender.http.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("PROVIDER_VOICE_GENDER_HTTP_PASS", flush=True)
