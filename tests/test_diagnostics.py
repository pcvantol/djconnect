from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]


def install_diagnostics_stubs() -> None:
    sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    aiohttp = sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
    core = sys.modules.setdefault(
        "homeassistant.core",
        types.ModuleType("homeassistant.core"),
    )
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    helpers = sys.modules.setdefault(
        "homeassistant.helpers",
        types.ModuleType("homeassistant.helpers"),
    )
    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    core.HomeAssistant = object
    config_entries.ConfigEntry = object
    aiohttp_client.async_get_clientsession = lambda hass: None
    helpers.aiohttp_client = aiohttp_client
    components = sys.modules.setdefault(
        "homeassistant.components",
        types.ModuleType("homeassistant.components"),
    )
    assist_pkg = sys.modules.setdefault(
        "homeassistant.components.assist_pipeline",
        types.ModuleType("homeassistant.components.assist_pipeline"),
    )
    assist_pipeline = sys.modules.setdefault(
        "homeassistant.components.assist_pipeline.pipeline",
        types.ModuleType("homeassistant.components.assist_pipeline.pipeline"),
    )
    stt_module = sys.modules.setdefault(
        "homeassistant.components.stt",
        types.ModuleType("homeassistant.components.stt"),
    )
    tts_module = sys.modules.setdefault(
        "homeassistant.components.tts",
        types.ModuleType("homeassistant.components.tts"),
    )
    components.assist_pipeline = assist_pkg
    components.stt = stt_module
    components.tts = tts_module
    assist_pkg.pipeline = assist_pipeline
    assist_pipeline.async_get_pipelines = lambda hass: []
    class SpeechMetadata:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    stt_module.SpeechMetadata = SpeechMetadata
    stt_module.AudioFormats = types.SimpleNamespace(WAV="wav")
    stt_module.AudioCodecs = types.SimpleNamespace(PCM="pcm")
    stt_module.AudioBitRates = lambda value: value
    stt_module.AudioSampleRates = lambda value: value
    stt_module.AudioChannels = lambda value: value
    tts_module.async_generate_media_source_id = lambda *args, **kwargs: "media-source://tts/test"
    async def async_get_media_source_audio(*args, **kwargs):
        return "audio/wav", b"RIFF....WAVE"

    tts_module.async_get_media_source_audio = async_get_media_source_audio
    if not hasattr(aiohttp, "ClientTimeout"):
        class ClientTimeout:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        aiohttp.ClientTimeout = ClientTimeout

    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault("custom_components.djconnect", package)


class DiagnosticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_diagnostics_stubs()
        cls.diagnostics = importlib.import_module("custom_components.djconnect.diagnostics")

    def test_redact_hides_token_password_and_secret_aliases(self) -> None:
        data = {
            "device_token": "device-secret",
            "refresh_token": "refresh-secret",
            "spotify_refresh_token": "spotify-secret",
            "push_token": "push-secret",
            "wifi_password": "wifi-secret",
            "nested": {
                "password": "nested-secret",
                "client_id": "safe-client-id",
                "tts_voice": "private-voice-id",
                "Authorization": "Bearer device-token",
                "bootstrap_proof": "proof-secret",
                "raw_prompt": "prompt with hidden details",
                "ask_dj_history": ["private history"],
                "runtime_memory": {"secret": "memory-secret"},
                "raw_audio_bytes": "audio-bytes",
            },
        }

        redacted = self.diagnostics._redact(data)

        self.assertEqual(redacted["device_token"], "REDACTED")
        self.assertEqual(redacted["refresh_token"], "REDACTED")
        self.assertEqual(redacted["spotify_refresh_token"], "REDACTED")
        self.assertEqual(redacted["push_token"], "REDACTED")
        self.assertEqual(redacted["wifi_password"], "REDACTED")
        self.assertEqual(redacted["nested"]["password"], "REDACTED")
        self.assertEqual(redacted["nested"]["tts_voice"], "REDACTED")
        self.assertEqual(redacted["nested"]["Authorization"], "REDACTED")
        self.assertEqual(redacted["nested"]["bootstrap_proof"], "REDACTED")
        self.assertEqual(redacted["nested"]["raw_prompt"], "REDACTED")
        self.assertEqual(redacted["nested"]["ask_dj_history"], "REDACTED")
        self.assertEqual(redacted["nested"]["runtime_memory"], "REDACTED")
        self.assertEqual(redacted["nested"]["raw_audio_bytes"], "REDACTED")
        self.assertEqual(redacted["nested"]["client_id"], "safe-client-id")

    def test_diagnostics_include_legal_metadata_and_redact_secrets(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            title="DJConnect",
            data={
                "spotify_refresh_token": "refresh-secret",
                "spotify_scopes": "user-read-playback-state user-modify-playback-state",
            },
            options={"wifi_password": "wifi-secret"},
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": None}})

        result = asyncio.run(
            self.diagnostics.async_get_config_entry_diagnostics(hass, entry)
        )

        self.assertEqual(
            result["legal"]["copyright"],
            "Copyright (c) 2026 Peter van Tol. All rights reserved.",
        )
        self.assertEqual(
            result["legal"]["spotify_trademark"],
            "Spotify is a trademark of Spotify AB.",
        )
        self.assertEqual(
            result["legal"]["affiliation"],
            "DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.",
        )
        self.assertIn(
            "playlist-read-private",
            result["spotify_oauth"]["missing_scopes"],
        )
        self.assertTrue(result["spotify_oauth"]["reauthorization_required"])
        self.assertEqual(result["entry"]["data"]["spotify_refresh_token"], "REDACTED")
        self.assertEqual(result["entry"]["options"]["wifi_password"], "REDACTED")

    def test_music_assistant_diagnostics_do_not_require_spotify_oauth(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            title="DJConnect",
            data={
                "music_backend": "music_assistant",
                "music_assistant_player": "media_player.mass_living",
            },
            options={},
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": None}})

        result = asyncio.run(
            self.diagnostics.async_get_config_entry_diagnostics(hass, entry)
        )

        self.assertEqual(result["music_backend"]["selected"], "music_assistant")
        self.assertFalse(result["spotify_oauth"]["required"])
        self.assertFalse(result["spotify_oauth"]["reauthorization_required"])
        self.assertTrue(result["music_backend"]["capabilities"]["supports_volume"])
        self.assertFalse(
            result["music_backend"]["capabilities"]["supports_recently_played"]
        )

    def test_assist_diagnostics_include_stt_tts_pipeline_summary(self) -> None:
        from homeassistant.components.assist_pipeline import pipeline as pipeline_module
        from homeassistant.components import stt as stt_module

        original_get_pipelines = pipeline_module.async_get_pipelines
        original_get_stt = getattr(stt_module, "async_get_speech_to_text_engine", None)
        pipeline_module.async_get_pipelines = lambda hass: [
            types.SimpleNamespace(
                id="pipeline-1",
                name="Living Room Assist",
                stt_engine="stt.local",
                stt_language="nl-NL",
                tts_engine="tts.local",
                tts_language="nl-NL",
                tts_voice="private-voice-id",
            )
        ]
        stt_module.async_get_speech_to_text_engine = lambda *args, **kwargs: object()
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            title="DJConnect",
            data={
                "assist_pipeline_id": "pipeline-1",
                "spotify_scopes": " ".join(self.diagnostics.SPOTIFY_SCOPES),
            },
            options={},
        )
        hass = types.SimpleNamespace(data={"djconnect": {"entry-1": None}})

        try:
            result = asyncio.run(
                self.diagnostics.async_get_config_entry_diagnostics(hass, entry)
            )
        finally:
            pipeline_module.async_get_pipelines = original_get_pipelines
            if original_get_stt is None:
                delattr(stt_module, "async_get_speech_to_text_engine")
            else:
                stt_module.async_get_speech_to_text_engine = original_get_stt
            components = sys.modules.get("homeassistant.components")
            if components is not None and getattr(components, "stt", None) is stt_module:
                delattr(components, "stt")

        self.assertTrue(result["assist"]["ready"])
        self.assertEqual(result["assist"]["configured_pipeline_id"], "pipeline-1")
        self.assertEqual(result["assist"]["stt"]["pipeline_id"], "pipeline-1")
        self.assertEqual(result["assist"]["stt"]["pipeline_name"], "Living Room Assist")
        self.assertEqual(result["assist"]["stt"]["stt_engine"], "stt.local")
        self.assertEqual(result["assist"]["tts"]["pipeline_id"], "pipeline-1")
        self.assertEqual(result["assist"]["tts"]["pipeline_name"], "Living Room Assist")
        self.assertEqual(result["assist"]["tts"]["tts_engine"], "tts.local")
        self.assertTrue(result["assist"]["tts"]["voice_configured"])
        self.assertNotIn("private-voice-id", str(result))


if __name__ == "__main__":
    unittest.main()
