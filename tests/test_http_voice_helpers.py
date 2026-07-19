from __future__ import annotations

import importlib
import asyncio
import json
import logging
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]


def install_http_stubs() -> None:
    if "homeassistant.components.http" in sys.modules:
        core = sys.modules.setdefault(
            "homeassistant.core",
            types.ModuleType("homeassistant.core"),
        )
        if not hasattr(core, "Context"):
            class Context:
                pass

            core.Context = Context
        storage = sys.modules.setdefault(
            "homeassistant.helpers.storage",
            types.ModuleType("homeassistant.helpers.storage"),
        )
        if not hasattr(storage, "Store"):
            class Store:
                def __init__(self, *args, **kwargs):
                    self.data = None

                async def async_load(self):
                    return self.data

                async def async_save(self, data):
                    self.data = data

            storage.Store = Store
        return

    aiohttp = sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))

    homeassistant = sys.modules.setdefault(
        "homeassistant", types.ModuleType("homeassistant")
    )
    components = types.ModuleType("homeassistant.components")
    http = types.ModuleType("homeassistant.components.http")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    storage = types.ModuleType("homeassistant.helpers.storage")

    class HomeAssistantView:
        def json(self, payload, status_code=200):
            return {"payload": payload, "status_code": status_code}

    class ClientTimeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class Response:
        def __init__(self, *, status=200, text=None, body=None, content_type=None, headers=None):
            self.status = status
            self.text = text
            self.body = body
            self.content_type = content_type
            self.headers = headers or {}

    class Context:
        pass

    http.HomeAssistantView = HomeAssistantView
    core.Context = Context
    core.HomeAssistant = object
    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.web = types.SimpleNamespace(Response=Response)
    aiohttp_client.async_get_clientsession = lambda hass: None
    class Store:
        def __init__(self, *args, **kwargs):
            self.data = None

        async def async_load(self):
            return self.data

        async def async_save(self, data):
            self.data = data

    storage.Store = Store

    homeassistant.components = components
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.http"] = http
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client
    sys.modules["homeassistant.helpers.storage"] = storage

    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault("custom_components.djconnect", package)


class VoiceHttpHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        cls.http = importlib.import_module("custom_components.djconnect.http")

    def test_text_from_header_takes_precedence(self) -> None:
        text = self.http._text_from_payload(
            {"X-DJConnect-Text": " Speel Pearl Jam "},
            {"text": "Speel Nirvana"},
        )

        self.assertEqual(text, "Speel Pearl Jam")

    def test_debug_redaction_hides_auth_prompt_history_and_memory(self) -> None:
        redacted = self.http._redact_debug_payload(
            {
                "Authorization": "Bearer device-token",
                "device_token": "device-secret",
                "bootstrap_proof": "proof-secret",
                "raw_prompt": "prompt with private details",
                "ask_dj_history": ["private history"],
                "runtime_memory": {"secret": "memory-secret"},
                "raw_audio_bytes": "audio-bytes",
                "safe": {"client_id": "public-client-id"},
            }
        )

        self.assertEqual(redacted["Authorization"], "<redacted>")
        self.assertEqual(redacted["device_token"], "<redacted>")
        self.assertEqual(redacted["bootstrap_proof"], "<redacted>")
        self.assertEqual(redacted["raw_prompt"], "<redacted>")
        self.assertEqual(redacted["ask_dj_history"], "<redacted>")
        self.assertEqual(redacted["runtime_memory"], "<redacted>")
        self.assertEqual(redacted["raw_audio_bytes"], "<redacted>")
        self.assertEqual(redacted["safe"]["client_id"], "public-client-id")

    def test_safe_backend_error_message_hides_secret_bearing_text(self) -> None:
        message = self.http._safe_backend_error_message(
            RuntimeError("HTTP failed with Authorization: Bearer super-secret-token")
        )

        self.assertEqual(
            message,
            "The selected music backend could not complete playback.",
        )
        self.assertNotIn("super-secret-token", message)

    def test_backend_unavailable_payload_hides_secret_bearing_exception(self) -> None:
        runtime = types.SimpleNamespace(
            config={},
            last_playback={},
        )

        payload = self.http._backend_unavailable_payload(
            "play",
            runtime,
            RuntimeError("password leaked in backend exception"),
        )

        self.assertEqual(
            payload["message"],
            "The selected music backend could not complete playback.",
        )
        self.assertNotIn("password leaked", payload["message"])

    def test_normalized_status_payload_aliases_app_version(self) -> None:
        payload = self.http._normalized_status_payload(
            {
                "client_type": "macos",
                "device_id": "djconnect-macos-ABCDEFGHIJKL",
                "app_version": "3.2.46",
            }
        )

        self.assertEqual(payload["app_version"], "3.2.46")
        self.assertEqual(payload["version"], "3.2.46")
        self.assertEqual(payload["firmware"], "3.2.46")

    def test_runtime_version_check_prefers_app_version(self) -> None:
        runtime = types.SimpleNamespace(
            device_status={
                "client_type": "macos",
                "app_version": self.http.VERSION,
                "firmware": "3.0.1",
            }
        )

        self.assertEqual(self.http._runtime_firmware_version(runtime), self.http.VERSION)
        self.assertTrue(self.http._runtime_versions_compatible(runtime))

    def test_text_from_json_payload(self) -> None:
        text = self.http._text_from_payload({}, {"text": " Speel Nirvana "})

        self.assertEqual(text, "Speel Nirvana")

    def test_missing_text_response_documents_assist_flow(self) -> None:
        response = self.http._missing_text_response(self.http.DJConnectVoiceView(None))

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(response["payload"]["error"], "missing_text")
        self.assertIn("X-DJConnect-Text", response["payload"]["message"])
        self.assertIn("WAV audio", response["payload"]["message"])

    def test_command_failed_text_uses_device_language(self) -> None:
        nl_runtime = types.SimpleNamespace(device_language=lambda: "nl")
        en_runtime = types.SimpleNamespace(device_language=lambda: "en")
        unknown_runtime = types.SimpleNamespace()

        self.assertIn(
            "Spotify kon nu niet starten",
            self.http._command_failed_text(
                nl_runtime,
                RuntimeError("Spotify playback device unavailable"),
            ),
        )
        self.assertIn(
            "Spotify",
            self.http._command_failed_text(
                en_runtime,
                RuntimeError("media_player.play_media failed"),
            ),
        )
        self.assertIn(
            "could not turn that into a DJConnect request",
            self.http._command_failed_text(
                en_runtime,
                RuntimeError("HA Assist pipeline failed"),
            ),
        )
        self.assertIn(
            "Er ging iets mis bij DJConnect",
            self.http._command_failed_text(unknown_runtime),
        )
        leaked_prompt_error = (
            "Sorry, ik kan Noem de artiest en het nummer Media type artist "
            "artiest Nirvana niet vinden"
        )
        self.assertNotIn(
            "Noem de artiest",
            self.http._command_failed_text(nl_runtime, RuntimeError(leaked_prompt_error)),
        )
        self.assertIn(
            "geen DJConnect verzoek",
            self.http._command_failed_text(nl_runtime, RuntimeError(leaked_prompt_error)),
        )

    def test_voice_view_text_request_runs_direct_dj_response_test(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def device_language(self):
                return "nl"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        async def fail_command(hass, runtime, user_text, play=True, correct_stt=False):
            raise AssertionError("text-only voice test must not run command parser")

        async def dj_response(hass, runtime, text):
            return {"success": True, "spoken": False}

        original_command = self.http.run_text_command
        original_dj_response = self.http.async_send_dj_response_best_effort
        self.http.run_text_command = fail_command
        self.http.async_send_dj_response_best_effort = dj_response

        class Request:
            headers = {
                "X-DJConnect-Text": "Test",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
            }
            app = {"hass": hass}

            async def read(self):
                return b""

        try:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))
        finally:
            self.http.run_text_command = original_command
            self.http.async_send_dj_response_best_effort = original_dj_response

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(
            response["payload"]["dj_text"],
            "DJConnect is klaar voor je volgende verzoek.",
        )
        self.assertEqual(response["payload"]["recognized_text"], "Test")
        self.assertEqual(response["payload"]["dj_response"], {"success": True, "spoken": False})
        self.assertIsNone(runtime.last_update["last_error"])

    def test_voice_view_json_text_request_runs_direct_dj_response_test(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Memory:
            def __init__(self):
                self.payloads = []

            async def async_update_client_metadata(self, runtime, payload, *, user_id=None):
                self.payloads.append((payload, user_id))
                self.mood = payload.get("mood")
                return "djconnect-watchos-68B74487726D"

        class Runtime:
            config = {}
            device_status = {
                "device_id": "djconnect-watchos-68B74487726D",
                "client_type": "watchos",
            }
            memory = Memory()

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def device_language(self):
                return "en"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        async def fail_command(hass, runtime, user_text, play=True, correct_stt=False):
            raise AssertionError("JSON text test must not run command parser")

        async def dj_response(hass, runtime, text):
            return {
                "success": True,
                "spoken": True,
                "audio_url_value": "http://ha/api/djconnect/v1/tts/test.mp3",
            }

        original_command = self.http.run_text_command
        original_dj_response = self.http.async_send_dj_response_best_effort
        self.http.run_text_command = fail_command
        self.http.async_send_dj_response_best_effort = dj_response

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-watchos-68B74487726D",
                "Content-Type": "application/json",
            }
            app = {"hass": hass}

            async def json(self):
                return {
                    "text": "Test",
                    "device_id": "djconnect-watchos-68B74487726D",
                    "client_type": "watchos",
                    "platform": "watchos",
                    "mood": 64,
                    "dj_style": "warm_radio_dj",
                }

        try:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))
        finally:
            self.http.run_text_command = original_command
            self.http.async_send_dj_response_best_effort = original_dj_response

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(
            response["payload"]["dj_text"],
            "DJConnect is ready for your next request.",
        )
        self.assertEqual(
            response["payload"]["audio_url"],
            "http://ha/api/djconnect/v1/tts/test.mp3",
        )
        self.assertEqual(response["payload"]["audio_type"], "mp3")
        self.assertEqual(response["payload"]["music_dna_key"], "djconnect-watchos-68B74487726D")
        self.assertEqual(runtime.memory.mood, 64)

    def test_voice_view_accepts_wav_upload_and_returns_audio_url(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {const.CONF_MAX_AUDIO_BYTES: 100}
            device_status = {
                "device_id": "djconnect-watchos-68B74487726D",
                "client_type": "watchos",
                "firmware": "3.3.34",
            }
            device_token = "device-token"

            def authorize_device_request(self, headers, body_device_id=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and body_device_id == "djconnect-watchos-68B74487726D"
                )

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        async def transcribe(hass, wav, conf):
            self.assertEqual(wav, b"RIFFxxxxWAVEdata")
            return "Speel Pearl Jam"

        async def ask_dj(hass, runtime, payload, *, user_id=None):
            self.assertEqual(payload["text"], "Speel Pearl Jam")
            self.assertEqual(payload["mood"], 100)
            self.assertEqual(payload["mood_zone"], "party")
            self.assertEqual(payload["dj_style"], "warm_radio_dj")
            self.assertEqual(payload["music_dna_key"], "shared")
            self.assertEqual(payload["profile_id"], "profile-peter")
            self.assertEqual(payload["satellite_id"], "satellite-kitchen")
            self.assertEqual(payload["ha_device_id"], "ha-device-kitchen")
            self.assertEqual(payload["area_id"], "kitchen")
            self.assertEqual(payload["room_id"], "kitchen")
            self.assertEqual(payload["player_id"], "ma-player-kitchen")
            self.assertEqual(payload["playback_zone_id"], "zone-kitchen")
            self.assertEqual(payload["session_id"], "voice-session")
            return {
                "success": True,
                "text": "Daar gaan we",
                "dj_text": "Daar gaan we",
                "message": "Daar gaan we",
                "transcript": "Speel Pearl Jam",
                "audio_url": "http://ha/api/djconnect/v1/tts/token.mp3",
                "images": [],
                "links": [],
                "sources": [{"source": "djconnect_music_dna"}],
                "intent": {"category": "hybrid", "intent": "play_music"},
                "action": "play_music",
            }

        original_transcribe = self.http.transcribe_wav_with_assist
        original_ask_dj = self.http.async_handle_ask_dj
        self.http.transcribe_wav_with_assist = transcribe
        self.http.async_handle_ask_dj = ask_dj

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-watchos-68B74487726D",
                "client_type": "watchos",
                "Content-Type": "audio/wav",
                "X-DJConnect-Mood": "100",
                "X-DJConnect-DJ-Style": "warm_radio_dj",
                "X-DJConnect-Music-DNA-Key": "shared",
                "X-DJConnect-Profile-ID": "profile-peter",
                "X-DJConnect-Satellite-ID": "satellite-kitchen",
                "X-DJConnect-HA-Device-ID": "ha-device-kitchen",
                "X-DJConnect-Area-ID": "kitchen",
                "X-DJConnect-Room-ID": "kitchen",
                "X-DJConnect-Player-ID": "ma-player-kitchen",
                "X-DJConnect-Playback-Zone-ID": "zone-kitchen",
                "X-DJConnect-Session-ID": "voice-session",
            }
            app = {"hass": hass}

            async def read(self):
                return b"RIFFxxxxWAVEdata"

        try:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))
        finally:
            self.http.transcribe_wav_with_assist = original_transcribe
            self.http.async_handle_ask_dj = original_ask_dj

        self.assertNotIn(self.http.VOICE_DEBUG_KEY, hass.data[const.DOMAIN])
        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["transcript"], "Speel Pearl Jam")
        self.assertEqual(response["payload"]["recognized_text"], "Speel Pearl Jam")
        self.assertEqual(response["payload"]["text"], "Daar gaan we")
        self.assertEqual(
            response["payload"]["audio_url"],
            "http://ha/api/djconnect/v1/tts/token.mp3",
        )
        self.assertEqual(response["payload"]["audio_type"], "mp3")
        self.assertEqual(response["payload"]["sources"], [{"source": "djconnect_music_dna"}])

    def test_voice_debug_view_returns_last_debug_wav(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        hass = types.SimpleNamespace(
            data={
                const.DOMAIN: {
                    self.http.VOICE_DEBUG_KEY: {
                        "wav": b"RIFFxxxxWAVEdata",
                        "device_id": "djconnect-lilygo-90B70990A994",
                    }
                }
            }
        )

        class Request:
            app = {"hass": hass}

        response = asyncio.run(self.http.DJConnectVoiceDebugView(None).get(Request()))

        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, b"RIFFxxxxWAVEdata")
        self.assertEqual(response.content_type, "audio/wav")
        self.assertEqual(
            response.headers["X-DJConnect-Device-ID"],
            "djconnect-lilygo-90B70990A994",
        )

    def test_voice_debug_wav_is_not_stored_without_debug_logging(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        hass = types.SimpleNamespace(data={const.DOMAIN: {}})
        previous = self.http._LOGGER.level
        self.http._LOGGER.setLevel(logging.INFO)
        try:
            self.http._store_debug_voice_wav(
                hass,
                "djconnect-lilygo-90B70990A994",
                "audio/wav",
                b"RIFFxxxxWAVEdata",
            )
        finally:
            self.http._LOGGER.setLevel(previous)

        self.assertNotIn(self.http.VOICE_DEBUG_KEY, hass.data[const.DOMAIN])

    def test_ask_dj_voice_stt_failure_returns_422_for_app_client(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {}
            device_token = "device-token"
            pairing_device_id = "djconnect-ios-68B74487726D"
            device_status = {
                "device_id": "djconnect-ios-68B74487726D",
                "client_type": "ios",
            }

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        async def fail_stt(hass, wav, conf):
            raise RuntimeError("STT did not recognize speech")

        original_transcribe = self.http.transcribe_wav_with_assist
        self.http.transcribe_wav_with_assist = fail_stt

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
                "client_type": "ios",
                "Content-Type": "audio/wav",
            }
            app = {"hass": hass}

            async def read(self):
                return b"RIFFxxxxWAVEdata"

        try:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))
        finally:
            self.http.transcribe_wav_with_assist = original_transcribe

        self.assertEqual(response["status_code"], 422)
        self.assertFalse(response["payload"]["success"])
        self.assertEqual(response["payload"]["error"], "stt_failed")
        self.assertIn("STT did not recognize speech", response["payload"]["message"])

    def test_voice_view_wav_command_failure_returns_friendly_200(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {const.CONF_MAX_AUDIO_BYTES: 100}
            device_status = {"device_id": "djconnect-lilygo-90B70990A994"}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def device_language(self):
                return "nl"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        async def transcribe(hass, wav, conf):
            return "Test"

        async def fail_command(hass, runtime, user_text, play=True, correct_stt=False):
            self.assertTrue(correct_stt)
            raise RuntimeError("Sorry, ik kan geen apparaat vinden met de naam Test")

        async def dj_response(hass, runtime, text):
            return {"success": True, "spoken": False}

        original_transcribe = self.http.transcribe_wav_with_assist
        original_command = self.http.run_text_command
        original_dj_response = self.http.async_send_dj_response_best_effort
        self.http.transcribe_wav_with_assist = transcribe
        self.http.run_text_command = fail_command
        self.http.async_send_dj_response_best_effort = dj_response

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
                "Content-Type": "audio/wav",
            }
            app = {"hass": hass}

            async def read(self):
                return b"RIFFxxxxWAVEdata"

        try:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))
        finally:
            self.http.transcribe_wav_with_assist = original_transcribe
            self.http.run_text_command = original_command
            self.http.async_send_dj_response_best_effort = original_dj_response

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["error"], "command_failed")
        self.assertIn("geen DJConnect verzoek", response["payload"]["dj_text"])
        self.assertNotIn("geen apparaat vinden", response["payload"]["dj_text"])
        self.assertEqual(response["payload"]["recognized_text"], "Test")
        self.assertEqual(response["payload"]["dj_response"], {"success": True, "spoken": False})

    def test_voice_view_rejects_oversized_wav_upload(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {const.CONF_MAX_AUDIO_BYTES: 4}
            device_status = {"device_id": "djconnect-lilygo-90B70990A994"}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
                "Content-Type": "audio/x-wav",
            }
            app = {"hass": hass}

            async def read(self):
                return b"RIFFxxxxWAVEdata"

        response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))

        self.assertEqual(response["status_code"], 413)
        self.assertEqual(response["payload"]["error"], "audio_too_large")

    def test_voice_view_reports_stt_failure(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {const.CONF_MAX_AUDIO_BYTES: 100}
            device_status = {"device_id": "djconnect-lilygo-90B70990A994"}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        async def fail_stt(hass, wav, conf):
            raise RuntimeError("STT unavailable")

        original_transcribe = self.http.transcribe_wav_with_assist
        self.http.transcribe_wav_with_assist = fail_stt

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
                "Content-Type": "application/octet-stream",
            }
            app = {"hass": hass}

            async def read(self):
                return b"RIFFxxxxWAVEdata"

        try:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))
        finally:
            self.http.transcribe_wav_with_assist = original_transcribe

        self.assertEqual(response["status_code"], 500)
        self.assertEqual(response["payload"]["error"], "stt_failed")
        self.assertIn("STT unavailable", response["payload"]["message"])

    def test_voice_view_reports_no_stt_provider_as_503(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")

        class Runtime:
            config = {const.CONF_MAX_AUDIO_BYTES: 100}
            device_status = {"device_id": "djconnect-lilygo-90B70990A994"}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        async def no_provider(hass, wav, conf):
            raise assist_stt.DJConnectNoSttProviderError(
                assist_stt.NO_STT_PROVIDER
            )

        original_transcribe = self.http.transcribe_wav_with_assist
        self.http.transcribe_wav_with_assist = no_provider

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
                "Content-Type": "audio/wav",
            }
            app = {"hass": hass}

            async def read(self):
                return b"RIFFxxxxWAVEdata"

        try:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))
        finally:
            self.http.transcribe_wav_with_assist = original_transcribe

        self.assertEqual(response["status_code"], 503)
        self.assertEqual(response["payload"]["error"], "stt_failed")
        self.assertIn(assist_stt.NO_STT_PROVIDER, response["payload"]["message"])
        self.assertIn("Assist pipeline", response["payload"]["message"])

    def test_transcribe_wav_uses_home_assistant_stt_helper(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        assist_pkg = types.ModuleType("homeassistant.components.assist_pipeline")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        async def async_process_audio_stream(hass, metadata, stream, engine=None):
            chunks = []
            async for chunk in stream:
                chunks.append(chunk)
            self.assertEqual(engine, "mock_stt")
            self.assertEqual(b"".join(chunks), b"RIFFxxxxWAVEdata")
            self.assertEqual(metadata.kwargs["format"], "wav")
            return types.SimpleNamespace(text="Speel Pearl Jam")

        class Pipelines:
            def async_get_pipeline(self, pipeline_id):
                self.pipeline_id = pipeline_id
                return types.SimpleNamespace(
                    id=pipeline_id,
                    stt_engine="mock_stt",
                    stt_language="nl-NL",
                )

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        stt_module.async_process_audio_stream = async_process_audio_stream
        pipeline_module.async_get_pipelines = lambda hass: Pipelines()

        originals = {
            name: sys.modules.get(name)
            for name in (
                "homeassistant.components.stt",
                "homeassistant.components.assist_pipeline",
                "homeassistant.components.assist_pipeline.pipeline",
            )
        }
        sys.modules["homeassistant.components.stt"] = stt_module
        sys.modules["homeassistant.components.assist_pipeline"] = assist_pkg
        sys.modules[
            "homeassistant.components.assist_pipeline.pipeline"
        ] = pipeline_module

        try:
            text = asyncio.run(
                assist_stt.transcribe_wav_with_assist(
                    types.SimpleNamespace(data={}),
                    b"RIFFxxxxWAVEdata",
                    {const.CONF_ASSIST_PIPELINE_ID: "preferred"},
                )
            )
        finally:
            for name, original in originals.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original

        self.assertEqual(text, "Speel Pearl Jam")

    def test_transcribe_wav_ignores_legacy_stt_option_and_uses_pipeline(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        calls = []

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        async def async_process_audio_stream(hass, metadata, stream, engine=None):
            calls.append(engine)
            async for _chunk in stream:
                pass
            return {"text": "Speel via OpenAI"}

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        stt_module.async_process_audio_stream = async_process_audio_stream

        pipeline_module.async_get_pipelines = lambda hass: [
            types.SimpleNamespace(
                id="preferred",
                name="Preferred",
                stt_engine="pipeline-openai",
                stt_language="nl-NL",
            )
        ]
        originals = self._install_stt_modules(stt_module, pipeline_module)
        try:
            text = asyncio.run(
                assist_stt.transcribe_wav_with_assist(
                    types.SimpleNamespace(data={}),
                    b"RIFFxxxxWAVEdata",
                    {"stt_engine": "openai"},
                )
            )
        finally:
            self._restore_modules(originals)

        self.assertEqual(text, "Speel via OpenAI")
        self.assertEqual(calls, ["pipeline-openai"])

    def test_transcribe_wav_uses_real_ha_stt_engine_provider_pattern(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        calls = []

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        class Provider:
            def check_metadata(self, metadata):
                return metadata.kwargs["format"] == "wav"

            async def internal_async_process_audio_stream(self, metadata, stream):
                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)
                calls.append((metadata.kwargs["language"], b"".join(chunks)))
                return types.SimpleNamespace(text="Real HA provider text")

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        stt_module.async_get_speech_to_text_engine = (
            lambda hass, engine: Provider() if engine == "stt.openai_stt" else None
        )
        pipeline_module.async_get_pipelines = lambda hass: [
            types.SimpleNamespace(
                id="preferred",
                name="Preferred",
                stt_engine="stt.openai_stt",
                stt_language="nl-NL",
            )
        ]
        originals = self._install_stt_modules(stt_module, pipeline_module)
        try:
            text = asyncio.run(
                assist_stt.transcribe_wav_with_assist(
                    types.SimpleNamespace(data={}),
                    b"RIFFxxxxWAVEdata",
                    {"stt_engine": "stt.openai_stt"},
                )
            )
        finally:
            self._restore_modules(originals)

        self.assertEqual(text, "Real HA provider text")
        self.assertEqual(calls, [("nl-NL", b"RIFFxxxxWAVEdata")])

    def test_transcribe_wav_uses_public_ha_stt_provider_processor(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        calls = []

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        class Provider:
            def check_metadata(self, metadata):
                calls.append(("metadata", metadata.kwargs["format"]))
                return True

            async def async_process_audio_stream(self, metadata, stream):
                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)
                calls.append(
                    (
                        "process",
                        metadata.kwargs["language"],
                        metadata.kwargs["sample_rate"],
                        b"".join(chunks),
                    )
                )
                return types.SimpleNamespace(text="Public HA provider text")

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        stt_module.async_get_speech_to_text_engine = (
            lambda hass, engine: Provider() if engine == "cloud" else None
        )
        pipeline_module.async_get_pipelines = lambda hass: [
            types.SimpleNamespace(
                id="preferred",
                name="Home Assistant Cloud",
                stt_engine="cloud",
                stt_language="nl-NL",
            )
        ]
        originals = self._install_stt_modules(stt_module, pipeline_module)
        try:
            text = asyncio.run(
                assist_stt.transcribe_wav_with_assist(
                    types.SimpleNamespace(data={}),
                    b"RIFFxxxxWAVEdata",
                    {},
                )
            )
        finally:
            self._restore_modules(originals)

        self.assertEqual(text, "Public HA provider text")
        self.assertEqual(
            calls,
            [
                ("metadata", "wav"),
                ("process", "nl-NL", 16000, b"RIFFxxxxWAVEdata"),
            ],
        )

    def test_voice_view_ptt_runs_through_public_ha_stt_provider(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        stt_module = types.ModuleType("homeassistant.components.stt")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        calls = []

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        class Provider:
            def check_metadata(self, metadata):
                calls.append(("metadata", metadata.kwargs["format"]))
                return True

            async def async_process_audio_stream(self, metadata, stream):
                chunks = []
                async for chunk in stream:
                    chunks.append(chunk)
                calls.append(("audio", b"".join(chunks)))
                return types.SimpleNamespace(text="Speel Eefje de Visser")

        class Runtime:
            config = {
                const.CONF_ASSIST_PIPELINE_ID: "cloud-pipeline",
                const.CONF_MAX_AUDIO_BYTES: 100,
            }
            device_token = "device-token"
            pairing_device_id = "djconnect-ios-68B74487726D"
            device_status = {
                "device_id": "djconnect-ios-68B74487726D",
                "client_type": "ios",
                "firmware": self.http.VERSION,
            }

            def authorize_device_request(self, headers, body_device_id=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and body_device_id == "djconnect-ios-68B74487726D"
                )

            def update(self, **kwargs):
                self.last_update = kwargs

        async def ask_dj(hass, runtime, payload, *, user_id=None):
            calls.append(("ask_dj", payload["text"], payload["input_type"]))
            return {
                "success": True,
                "text": "Ik zet Eefje klaar.",
                "dj_text": "Ik zet Eefje klaar.",
                "message": "Ik zet Eefje klaar.",
                "transcript": payload["text"],
                "images": [],
                "links": [],
                "sources": [],
            }

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        stt_module.async_get_speech_to_text_engine = (
            lambda hass, engine: Provider() if engine == "cloud" else None
        )
        pipeline_module.async_get_pipelines = lambda hass: [
            types.SimpleNamespace(
                id="cloud-pipeline",
                name="Home Assistant Cloud",
                stt_engine="cloud",
                stt_language="nl-NL",
            )
        ]
        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})
        originals = self._install_stt_modules(stt_module, pipeline_module)
        original_ask_dj = self.http.async_handle_ask_dj
        self.http.async_handle_ask_dj = ask_dj

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
                "X-DJConnect-Client-Type": "ios",
                "Content-Type": "audio/wav",
            }
            app = {"hass": hass}

            async def read(self):
                return b"RIFFxxxxWAVEdata"

        try:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))
        finally:
            self.http.async_handle_ask_dj = original_ask_dj
            self._restore_modules(originals)

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["transcript"], "Speel Eefje de Visser")
        self.assertEqual(response["payload"]["recognized_text"], "Speel Eefje de Visser")
        self.assertEqual(
            calls,
            [
                ("metadata", "wav"),
                ("audio", b"RIFFxxxxWAVEdata"),
                ("ask_dj", "Speel Eefje de Visser", "voice"),
            ],
        )

    def test_transcribe_wav_falls_back_to_first_stt_entity(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        calls = []

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        class States:
            def async_entity_ids(self, domain):
                self.domain = domain
                return ["stt.openai_stt"]

        async def async_process_audio_stream(hass, metadata, stream, engine=None):
            calls.append(engine)
            async for _chunk in stream:
                pass
            return {"text": "OpenAI entity fallback"}

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        stt_module.async_process_audio_stream = async_process_audio_stream
        pipeline_module.async_get_pipelines = lambda hass: []
        originals = self._install_stt_modules(stt_module, pipeline_module)
        try:
            text = asyncio.run(
                assist_stt.transcribe_wav_with_assist(
                    types.SimpleNamespace(data={}, states=States()),
                    b"RIFFxxxxWAVEdata",
                    {},
                )
            )
        finally:
            self._restore_modules(originals)

        self.assertEqual(text, "OpenAI entity fallback")
        self.assertEqual(calls, ["stt.openai_stt"])

    def test_transcribe_wav_uses_assist_pipeline_helper_when_no_engine_resolved(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        assist_pkg = types.ModuleType("homeassistant.components.assist_pipeline")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        calls = []

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        class PipelineStage:
            STT = "stt"

        async def async_pipeline_from_audio_stream(*args, **kwargs):
            calls.append({"args": args, **kwargs})
            chunks = []
            async for chunk in kwargs["stt_stream"]:
                chunks.append(chunk)
            await kwargs["event_callback"](
                {"type": "stt-end", "data": {"stt_output": {"text": "Pipeline text"}}}
            )

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        assist_pkg.async_pipeline_from_audio_stream = async_pipeline_from_audio_stream
        pipeline_module.PipelineStage = PipelineStage
        pipeline_module.async_get_pipelines = lambda hass: []

        originals = self._install_stt_modules(stt_module, pipeline_module)
        original_assist = sys.modules.get("homeassistant.components.assist_pipeline")
        sys.modules["homeassistant.components.assist_pipeline"] = assist_pkg
        try:
            text = asyncio.run(
                assist_stt.transcribe_wav_with_assist(
                    types.SimpleNamespace(data={}),
                    b"RIFFxxxxWAVEdata",
                    {},
                )
            )
        finally:
            if original_assist is None:
                sys.modules.pop("homeassistant.components.assist_pipeline", None)
            else:
                sys.modules["homeassistant.components.assist_pipeline"] = original_assist
            self._restore_modules(originals)

        self.assertEqual(text, "Pipeline text")
        self.assertEqual(calls[0]["start_stage"], "stt")
        self.assertEqual(calls[0]["end_stage"], "stt")

    def test_stt_diagnostic_helpers_do_not_log_text(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")

        events = [
            {"type": "stt-start", "data": {}},
            {"type": "stt-end", "data": {"stt_output": {"text": "secret words"}}},
        ]
        result = types.SimpleNamespace(state="success", text="secret words")

        self.assertEqual(assist_stt._event_types(events), ["stt-start", "stt-end"])
        self.assertEqual(assist_stt._result_state(result), "success")
        self.assertNotIn("secret words", repr(assist_stt._event_types(events)))
        self.assertNotIn("secret words", str(assist_stt._result_state(result)))

    def test_stt_metadata_uses_bits_per_sample_not_stream_bitrate(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioBitRates(int):
            @property
            def value(self):
                return int(self)

        class AudioSampleRates(int):
            @property
            def value(self):
                return int(self)

        class AudioChannels(int):
            @property
            def value(self):
                return int(self)

        stt_module = types.SimpleNamespace(
            SpeechMetadata=SpeechMetadata,
            AudioFormats=types.SimpleNamespace(WAV="wav"),
            AudioCodecs=types.SimpleNamespace(PCM="pcm"),
            AudioBitRates=AudioBitRates,
            AudioSampleRates=AudioSampleRates,
            AudioChannels=AudioChannels,
        )
        info = assist_stt.SttInfo(
            ha_version="test",
            pipeline_id=None,
            pipeline_name=None,
            engine="stt.google_ai_stt",
            language="nl-NL",
            audio_format="wav",
            sample_rate=16000,
            channels=1,
            sample_width=2,
            byte_length=6700,
        )

        metadata = assist_stt._speech_metadata(stt_module, info)

        self.assertEqual(metadata.kwargs["bit_rate"].value, 16)
        self.assertEqual(metadata.kwargs["channel"].value, 1)
        self.assertNotEqual(metadata.kwargs["bit_rate"].value, 256000)

    def test_stt_metadata_falls_back_to_channels_keyword(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")

        class SpeechMetadata:
            def __init__(self, **kwargs):
                if "channel" in kwargs:
                    raise TypeError("unexpected keyword argument 'channel'")
                self.kwargs = kwargs

        stt_module = types.SimpleNamespace(
            SpeechMetadata=SpeechMetadata,
            AudioFormats=types.SimpleNamespace(WAV="wav"),
            AudioCodecs=types.SimpleNamespace(PCM="pcm"),
        )
        info = assist_stt.SttInfo(
            ha_version="test",
            pipeline_id=None,
            pipeline_name=None,
            engine="legacy",
            language="nl-NL",
            audio_format="wav",
            sample_rate=16000,
            channels=1,
            sample_width=2,
            byte_length=6700,
        )

        metadata = assist_stt._speech_metadata(stt_module, info)

        self.assertEqual(metadata.kwargs["channels"], 1)
        self.assertNotIn("channel", metadata.kwargs)

    def test_transcribe_wav_finds_default_cloud_stt_pipeline(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )
        calls = []

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        async def async_process_audio_stream(hass, metadata, stream, engine=None):
            calls.append(
                {
                    "engine": engine,
                    "language": metadata.kwargs["language"],
                    "audio": b"".join([chunk async for chunk in stream]),
                }
            )
            return {"text": "Speel Eefje de Visser"}

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        stt_module.async_process_audio_stream = async_process_audio_stream
        pipeline_module.async_get_pipelines = lambda hass: [
            types.SimpleNamespace(
                id="default",
                name="Home Assistant Cloud",
                stt_engine="cloud",
                stt_language="nl-NL",
            )
        ]

        originals = self._install_stt_modules(stt_module, pipeline_module)
        try:
            text = asyncio.run(
                assist_stt.transcribe_wav_with_assist(
                    types.SimpleNamespace(data={}),
                    b"RIFFxxxxWAVEdata",
                    {},
                )
            )
        finally:
            self._restore_modules(originals)

        self.assertEqual(text, "Speel Eefje de Visser")
        self.assertEqual(calls[0]["engine"], "cloud")
        self.assertEqual(calls[0]["language"], "nl-NL")
        self.assertEqual(calls[0]["audio"], b"RIFFxxxxWAVEdata")

    def test_transcribe_wav_missing_stored_pipeline_falls_back_to_default(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )

        class SpeechMetadata:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class AudioFormats:
            WAV = "wav"

        class AudioCodecs:
            PCM = "pcm"

        async def async_process_audio_stream(hass, metadata, stream, engine=None):
            return types.SimpleNamespace(text=f"engine={engine}")

        class Pipelines:
            def __init__(self):
                self.default = types.SimpleNamespace(
                    id="default",
                    name="Default Assist",
                    stt_engine="cloud",
                    stt_language="nl-NL",
                )

            def async_get_pipeline(self, pipeline_id):
                return None

            def async_get_preferred_pipeline(self):
                return self.default

        stt_module.SpeechMetadata = SpeechMetadata
        stt_module.AudioFormats = AudioFormats
        stt_module.AudioCodecs = AudioCodecs
        stt_module.async_process_audio_stream = async_process_audio_stream
        pipeline_module.async_get_pipelines = lambda hass: Pipelines()

        originals = self._install_stt_modules(stt_module, pipeline_module)
        try:
            text = asyncio.run(
                assist_stt.transcribe_wav_with_assist(
                    types.SimpleNamespace(data={}),
                    b"RIFFxxxxWAVEdata",
                    {const.CONF_ASSIST_PIPELINE_ID: "deleted-pipeline"},
                )
            )
        finally:
            self._restore_modules(originals)

        self.assertEqual(text, "engine=cloud")

    def test_transcribe_wav_pipeline_without_stt_returns_no_provider(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        stt_module = types.ModuleType("homeassistant.components.stt")
        pipeline_module = types.ModuleType(
            "homeassistant.components.assist_pipeline.pipeline"
        )

        class Pipelines:
            def async_get_pipeline(self, pipeline_id):
                return types.SimpleNamespace(id=pipeline_id, name="No STT")

        stt_module.async_process_audio_stream = object()
        pipeline_module.async_get_pipelines = lambda hass: Pipelines()
        originals = self._install_stt_modules(stt_module, pipeline_module)
        try:
            with self.assertRaises(assist_stt.DJConnectNoSttProviderError) as raised:
                asyncio.run(
                    assist_stt.transcribe_wav_with_assist(
                        types.SimpleNamespace(data={}),
                        b"RIFFxxxxWAVEdata",
                        {const.CONF_ASSIST_PIPELINE_ID: "no-stt"},
                    )
                )
        finally:
            self._restore_modules(originals)

        self.assertIn(assist_stt.NO_STT_PROVIDER, str(raised.exception))
        self.assertIn("Assist pipeline", str(raised.exception))

    def test_transcribe_wav_no_stt_provider_error(self) -> None:
        assist_stt = importlib.import_module("custom_components.djconnect.assist_stt")
        originals = {
            name: sys.modules.get(name)
            for name in (
                "homeassistant.components.stt",
                "homeassistant.components.assist_pipeline.pipeline",
            )
        }
        sys.modules.pop("homeassistant.components.stt", None)
        sys.modules.pop("homeassistant.components.assist_pipeline.pipeline", None)

        try:
            with self.assertRaises(assist_stt.DJConnectNoSttProviderError) as raised:
                asyncio.run(
                    assist_stt.transcribe_wav_with_assist(
                        types.SimpleNamespace(data={}),
                        b"RIFFxxxxWAVEdata",
                        {},
                    )
                )
        finally:
            for name, original in originals.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original

        self.assertIn(assist_stt.NO_STT_PROVIDER, str(raised.exception))
        self.assertIn("Assist pipeline", str(raised.exception))

    def _install_stt_modules(self, stt_module, pipeline_module):
        assist_pkg = types.ModuleType("homeassistant.components.assist_pipeline")
        originals = {
            name: sys.modules.get(name)
            for name in (
                "homeassistant.components.stt",
                "homeassistant.components.assist_pipeline",
                "homeassistant.components.assist_pipeline.pipeline",
            )
        }
        sys.modules["homeassistant.components.stt"] = stt_module
        sys.modules["homeassistant.components.assist_pipeline"] = assist_pkg
        sys.modules[
            "homeassistant.components.assist_pipeline.pipeline"
        ] = pipeline_module
        return originals

    def _restore_modules(self, originals):
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def test_pair_view_rejects_wrong_pair_code(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {const.CONF_PAIR_CODE: "123456"}

            def update(self, **kwargs):
                self.last_update = kwargs

        class Request:
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-device",
                    "client_type": "esp32",
                    "pair_code": "654321",
                }

        response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

        self.assertEqual(response["status_code"], 401)
        self.assertEqual(response["payload"]["error"], "invalid_pair_code")
        self.assertIn("does not match", response["payload"]["message"])

    def test_pair_view_accepts_open_config_flow_app_pairing_without_runtime(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        pending = {
            "604128": {
                const.CONF_PAIR_CODE: "604128",
                const.CONF_CLIENT_TYPE: const.CLIENT_TYPE_MACOS,
                const.CONF_DEVICE_TOKEN: "pending-device-token",
                const.CONF_ASSIST_PIPELINE_ID: "assist-pipeline",
                "flow_id": "flow-1",
                "ha_local_url": "https://victory-curvy-refold.ngrok-free.dev",
                "pairing_received": {},
            }
        }
        hass = types.SimpleNamespace(
            data={
                const.DOMAIN: {
                    "config_flow_app_pairing_pending": pending,
                }
            },
            config=types.SimpleNamespace(
                internal_url="https://victory-curvy-refold.ngrok-free.dev",
            ),
        )

        class Request:
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": "djconnect-macos-68B74487726D",
                    "device_name": "Peter Mac",
                    "client_type": "macos",
                    "pair_code": "604128",
                }

        response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertTrue(response["payload"]["setup_pending"])
        self.assertEqual(response["payload"]["device_token"], "pending-device-token")
        self.assertEqual(response["payload"]["client_type"], "macos")
        self.assertIn("ha_install_id", response["payload"])
        self.assertEqual(response["payload"]["integration_version"], const.VERSION)
        self.assertEqual(response["payload"]["pairing_session_id"], "flow-1")
        self.assertEqual(
            pending["604128"]["pairing_received"][const.CONF_DEVICE_ID],
            "djconnect-macos-68B74487726D",
        )
        self.assertEqual(
            pending["604128"]["pairing_received"][const.CONF_DEVICE_NAME],
            "Peter Mac",
        )

    def test_pair_view_prioritizes_open_app_pairing_over_conversation_runtime(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        pending = {
            "533968": {
                const.CONF_PAIR_CODE: "533968",
                const.CONF_CLIENT_TYPE: const.CLIENT_TYPE_MACOS,
                const.CONF_DEVICE_TOKEN: "pending-macos-token",
                const.CONF_ASSIST_PIPELINE_ID: "assist-pipeline",
                "flow_id": "flow-macos",
                "ha_local_url": "https://victory-curvy-refold.ngrok-free.dev",
                "pairing_received": {},
            }
        }

        class Runtime:
            config = {
                const.CONF_CLIENT_TYPE: const.CLIENT_TYPE_CONVERSATION_AGENT,
                const.CONF_DEVICE_ID: "djconnect-conversation-agent",
            }
            device_status = {"device_id": "djconnect-conversation-agent"}

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(
            data={
                const.DOMAIN: {
                    "runtime": runtime,
                    "config_flow_app_pairing_pending": pending,
                }
            },
            config=types.SimpleNamespace(
                internal_url="https://victory-curvy-refold.ngrok-free.dev",
            ),
        )

        class Request:
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": "djconnect-macos-160F462296C9",
                    "device_name": "DJConnect Mac",
                    "client_type": "macos",
                    "pair_code": "533968",
                }

        response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["setup_pending"])
        self.assertEqual(response["payload"]["client_type"], "macos")
        self.assertEqual(response["payload"]["device_token"], "pending-macos-token")
        self.assertEqual(
            pending["533968"]["pairing_received"][const.CONF_DEVICE_ID],
            "djconnect-macos-160F462296C9",
        )
        self.assertFalse(hasattr(runtime, "last_update"))

    def test_pair_view_rejects_pending_app_client_type_mismatch_distinctly(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        pending = {
            "604128": {
                const.CONF_PAIR_CODE: "604128",
                const.CONF_CLIENT_TYPE: const.CLIENT_TYPE_MACOS,
                const.CONF_DEVICE_TOKEN: "pending-device-token",
                const.CONF_ASSIST_PIPELINE_ID: "assist-pipeline",
                "flow_id": "flow-1",
                "ha_local_url": "https://victory-curvy-refold.ngrok-free.dev",
                "pairing_received": {},
            }
        }
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {"config_flow_app_pairing_pending": pending}},
            config=types.SimpleNamespace(
                internal_url="https://victory-curvy-refold.ngrok-free.dev",
            ),
        )

        class Request:
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "device_name": "Peter iPhone",
                    "client_type": "ios",
                    "pair_code": "604128",
                }

        response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(response["payload"]["error"], "client_type_mismatch")
        self.assertEqual(response["payload"]["expected_client_type"], "macos")
        self.assertEqual(response["payload"]["received_client_type"], "ios")
        self.assertNotEqual(response["payload"]["error"], "invalid_pair_code")
        self.assertFalse(pending["604128"]["pairing_received"])

    def test_pair_view_ignores_stale_pending_app_pairing_without_flow_id(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        pending = {
            "604128": {
                const.CONF_PAIR_CODE: "604128",
                const.CONF_CLIENT_TYPE: const.CLIENT_TYPE_MACOS,
                const.CONF_DEVICE_TOKEN: "old-device-token",
                const.CONF_ASSIST_PIPELINE_ID: "assist-pipeline",
                "pairing_received": {
                    const.CONF_DEVICE_ID: "djconnect-macos-68B74487726D",
                    const.CONF_CLIENT_TYPE: const.CLIENT_TYPE_MACOS,
                },
            }
        }
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {"config_flow_app_pairing_pending": pending}},
            config=types.SimpleNamespace(
                internal_url="https://victory-curvy-refold.ngrok-free.dev",
            ),
        )

        class Request:
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": "djconnect-macos-68B74487726D",
                    "device_name": "Peter Mac",
                    "client_type": "macos",
                    "pair_code": "604128",
                }

        response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

        self.assertEqual(response["status_code"], 503)
        self.assertEqual(response["payload"]["error"], "not_configured")
        self.assertNotIn("604128", pending)

    def test_track_insight_view_uses_djconnect_bearer_auth_not_ha_auth(self) -> None:
        self.assertFalse(self.http.DJConnectTrackInsightView.requires_auth)

    def test_pair_view_does_not_include_spotify_oauth_secrets(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {
                const.CONF_PAIR_CODE: "123456",
                const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
            }
            device_status = {}

            def ensure_device_token(self):
                self.device_token = "device-token"
                return self.device_token


            def spotify_payload(self):
                return {
                    "client_id": "client-id",
                    "refresh_token": "refresh-token",
                    "spotify_client_id": "client-id",
                    "spotify_refresh_token": "refresh-token",
                    "market": "NL",
                    "scopes": ["scope-a"],
                }

            def device_language(self):
                return "nl"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-device",
                    "client_type": "esp32",
                    "pair_code": "123456",
                    "local_url": "http://djconnect.local",
                }

        with self.assertLogs(self.http._LOGGER, level="DEBUG") as captured:
            response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(
            response["payload"]["ha_local_url"],
            "http://homeassistant.local:8123",
        )
        self.assertNotIn("ha_remote_url", response["payload"])
        self.assertNotIn("ha_url", response["payload"])
        self.assertNotIn("spotify", response["payload"])
        self.assertNotIn("refresh_token", response["payload"])
        self.assertNotIn("spotify_refresh_token", response["payload"])
        self.assertNotIn("client_id", response["payload"])
        self.assertNotIn("spotify_client_id", response["payload"])
        self.assertEqual(response["payload"]["device_language"], "nl")
        self.assertEqual(response["payload"]["language"], "nl")
        self.assertEqual(runtime.device_status["ha_pairing_status"], "pending")
        self.assertNotEqual(runtime.device_status.get("ha_pairing_status"), "paired")
        logs = "\n".join(captured.output)
        self.assertIn("DJConnect pairing request payload=", logs)
        self.assertIn("DJConnect pairing response status=200", logs)
        self.assertIn("'device_token': '<redacted>'", logs)
        self.assertNotIn("device-token", logs)

    def test_pair_view_rejects_runtime_client_type_mismatch_distinctly(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            config = {
                const.CONF_PAIR_CODE: "604128",
                const.CONF_CLIENT_TYPE: const.CLIENT_TYPE_MACOS,
            }
            device_status = {}

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "pair_code": "604128",
                }

        response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(response["payload"]["error"], "client_type_mismatch")
        self.assertEqual(response["payload"]["expected_client_type"], "macos")
        self.assertEqual(response["payload"]["received_client_type"], "ios")
        self.assertEqual(
            runtime.last_update["last_error"],
            self.http.ERROR_MESSAGES["client_type_mismatch"],
        )

    def test_pair_view_omits_device_language_for_app_clients(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        for client_type, device_id in (
            ("macos", "djconnect-macos-68B74487726D"),
            ("ios", "djconnect-ios-68B74487726D"),
            ("watchos", "djconnect-watchos-68B74487726D"),
            ("raspberry_pi", "djconnect-raspberry-pi-68B74487726D"),
            ("windows", "djconnect-windows-68B74487726D"),
        ):
            with self.subTest(client_type=client_type):
                class Runtime:
                    config = {
                        const.CONF_PAIR_CODE: "555293",
                        const.CONF_CLIENT_TYPE: client_type,
                    }
                    device_status = {const.CONF_CLIENT_TYPE: client_type}

                    def ensure_device_token(self):
                        self.device_token = "device-token"
                        return self.device_token

                    def device_language(self):
                        return "nl"

                    def update(self, **kwargs):
                        self.last_update = kwargs

                runtime = Runtime()

                class Request:
                    app = {
                        "hass": types.SimpleNamespace(
                            config=types.SimpleNamespace(
                                external_url="https://example.ui.nabu.casa"
                            ),
                            data={const.DOMAIN: {"runtime": runtime}},
                        )
                    }

                    async def json(self):
                        return {
                            "device_id": device_id,
                            "client_type": client_type,
                            "pair_code": "555293",
                            "local_url": "http://192.168.1.104:60955",
                        }

                response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

                self.assertEqual(response["status_code"], 200)
                self.assertEqual(response["payload"]["client_type"], client_type)
                self.assertNotIn("device_language", response["payload"])
                self.assertNotIn("language", response["payload"])
                self.assertEqual(response["payload"]["device_token"], "device-token")
                if client_type in {"ios", "macos", "windows"}:
                    self.assertEqual(
                        response["payload"]["ha_remote_url"],
                        "https://example.ui.nabu.casa",
                    )
                else:
                    self.assertNotIn("ha_remote_url", response["payload"])

    def test_app_pair_view_contract_for_inbound_remote_capable_clients(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        for client_type, device_id in (
            ("ios", "djconnect-ios-68B74487726D"),
            ("macos", "djconnect-macos-68B74487726D"),
            ("windows", "djconnect-windows-68B74487726D"),
        ):
            with self.subTest(client_type=client_type):
                class Runtime:
                    config = {
                        const.CONF_PAIR_CODE: "555293",
                        const.CONF_CLIENT_TYPE: client_type,
                        const.CONF_HA_EXTERNAL_URL: "https://remote.example.test",
                    }
                    device_status = {const.CONF_CLIENT_TYPE: client_type}

                    def ensure_device_token(self):
                        self.device_token = f"{client_type}-token"
                        return self.device_token

                    def device_language(self):
                        return "nl"

                    def update(self, **kwargs):
                        self.last_update = kwargs

                runtime = Runtime()

                class Request:
                    app = {
                        "hass": types.SimpleNamespace(
                            config=types.SimpleNamespace(
                                external_url="https://fallback.example.test"
                            ),
                            data={const.DOMAIN: {"runtime": runtime}},
                        )
                    }

                    async def json(self):
                        return {
                            "device_id": device_id,
                            "client_type": client_type,
                            "pair_code": "555293",
                            "device_name": f"Field {client_type}",
                        }

                response = asyncio.run(self.http.DJConnectPairView(None).post(Request()))

                self.assertEqual(response["status_code"], 200)
                payload = response["payload"]
                self.assertTrue(payload["success"])
                self.assertEqual(payload["client_type"], client_type)
                self.assertIn("ha_install_id", payload)
                self.assertEqual(payload["integration_version"], const.VERSION)
                self.assertNotIn("pairing_session_id", payload)
                self.assertEqual(payload["device_token"], f"{client_type}-token")
                self.assertEqual(payload["api_base"], "/api/djconnect/v1")
                self.assertEqual(payload["voice_path"], self.http.API_VOICE)
                self.assertEqual(payload["status_path"], self.http.API_STATUS)
                self.assertEqual(payload["ha_local_url"], "http://homeassistant.local:8123")
                self.assertEqual(payload["ha_remote_url"], "https://remote.example.test")
                self.assertNotIn("device_language", payload)
                self.assertNotIn("language", payload)
                self.assertNotIn("spotify_refresh_token", payload)
                self.assertNotIn("refresh_token", payload)
                self.assertEqual(runtime.device_status["device_id"], device_id)
                self.assertEqual(runtime.device_status["client_type"], client_type)
                self.assertEqual(runtime.device_status["ha_pairing_status"], "pending")
                self.assertIsNone(runtime.device_status.get("local_url"))

    def test_app_clients_can_send_remote_playback_commands_after_inbound_pairing(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        for client_type, device_id in (
            ("ios", "djconnect-ios-68B74487726D"),
            ("macos", "djconnect-macos-68B74487726D"),
            ("windows", "djconnect-windows-68B74487726D"),
        ):
            with self.subTest(client_type=client_type):
                calls = []

                class Runtime:
                    device_token = f"{client_type}-token"
                    pairing_device_id = device_id
                    device_status = {
                        "device_id": device_id,
                        "client_type": client_type,
                        "ha_pairing_status": "pending",
                    }
                    config = {
                        const.CONF_CLIENT_TYPE: client_type,
                        const.CONF_DEVICE_TOKEN: f"{client_type}-token",
                    }

                    def authorize_device_request(self, headers, body_device_id=None):
                        return (
                            headers.get("Authorization")
                            == f"Bearer {client_type}-token"
                            and body_device_id == device_id
                        )

                    def update(self, **kwargs):
                        self.last_update = kwargs

                runtime = Runtime()

                async def command_handler(hass, runtime, command, value=None, *, play=None):
                    calls.append(
                        {
                            "command": command,
                            "value": value,
                            "play": play,
                            "client_type": runtime.device_status["client_type"],
                        }
                    )
                    return {
                        "success": True,
                        "playback": {"has_playback": True, "source": "field-test"},
                    }

                class Request:
                    headers = {
                        "Authorization": f"Bearer {client_type}-token",
                        "X-DJConnect-Device-ID": device_id,
                    }
                    app = {
                        "hass": types.SimpleNamespace(
                            data={const.DOMAIN: {"runtime": runtime}}
                        )
                    }

                    async def json(self):
                        return {
                            "device_id": device_id,
                            "client_type": client_type,
                            "command": "play",
                            "value": "spotify:track:123",
                            "play": True,
                        }

                original = self.http.run_music_command
                self.http.run_music_command = command_handler
                try:
                    response = asyncio.run(
                        self.http.DJConnectCommandView(None).post(Request())
                    )
                finally:
                    self.http.run_music_command = original

                self.assertEqual(response["status_code"], 200)
                self.assertTrue(response["payload"]["success"])
                self.assertEqual(
                    response["payload"]["playback"],
                    {"has_playback": True, "source": "field-test"},
                )
                self.assertEqual(
                    calls,
                    [
                        {
                            "command": "play",
                            "value": "spotify:track:123",
                            "play": True,
                            "client_type": client_type,
                        }
                    ],
                )
                self.assertEqual(runtime.device_status["client_type"], client_type)
                self.assertEqual(runtime.device_status["backend_available"], True)
                self.assertEqual(runtime.last_update["last_error"], None)

    def test_status_view_accepts_watchos_client_payload(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-watchos-68B74487726D"}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and body_device_id == "djconnect-watchos-68B74487726D"
                )

            def get_current_spotify_credentials(self):
                return {}

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-watchos-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-watchos-68B74487726D",
                    "client_type": "watchos",
                    "platform": "watchos",
                    "device_name": "Peter Apple Watch",
                    "firmware": "3.3.34",
                    "app_version": "3.3.34",
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["client_type"], "watchos")
        self.assertIn("ha_install_id", response["payload"])
        self.assertEqual(response["payload"]["integration_version"], const.VERSION)
        self.assertNotIn("pairing_session_id", response["payload"])
        self.assertNotIn("device_language", response["payload"])
        self.assertNotIn("language", response["payload"])
        self.assertEqual(runtime.device_status["client_type"], "watchos")
        self.assertEqual(runtime.device_status["platform"], "watchos")
        self.assertEqual(runtime.device_status["device_name"], "Peter Apple Watch")
        self.assertEqual(runtime.device_status["app_version"], "3.3.34")

    def test_status_view_watchos_returns_live_playback_snapshot(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        seen_commands = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-watchos-68B74487726D"}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def get_current_spotify_credentials(self):
                return {}

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            seen_commands.append((command, value, play))
            return {
                "success": True,
                "playback": {
                    "has_playback": True,
                    "is_playing": True,
                    "track_name": "Alive",
                    "artist_name": "Pearl Jam",
                    "album_name": "Ten",
                    "album_image_url": "https://example.test/ten.jpg",
                    "progress_ms": 12345,
                    "duration_ms": 234567,
                    "volume_percent": 35,
                    "device": {
                        "id": "speaker-1",
                        "name": "Living room",
                        "type": "speaker",
                        "active": True,
                        "volume_percent": 35,
                    },
                },
            }

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-watchos-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-watchos-68B74487726D",
                    "client_type": "watchos",
                    "platform": "watchos",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["client_type"], "watchos")
        self.assertTrue(response["payload"]["backend_available"])
        self.assertTrue(response["payload"]["playback"]["has_playback"])
        self.assertEqual(response["payload"]["playback"]["track_name"], "Alive")
        self.assertEqual(response["payload"]["playback"]["device"]["name"], "Living room")
        self.assertEqual(seen_commands, [("status", None, None)])

    def test_status_view_watchos_backend_unavailable_returns_explicit_no_playback(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-watchos-68B74487726D"}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def get_current_spotify_credentials(self):
                return {}

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            raise self.http.SpotifyBackendError("secret Spotify OAuth details")

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-watchos-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-watchos-68B74487726D",
                    "client_type": "watchos",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertFalse(response["payload"]["backend_available"])
        self.assertEqual(response["payload"]["playback"], {"has_playback": False})
        self.assertEqual(response["payload"]["playback_error"], "playback_backend_unavailable")
        self.assertNotIn("secret", str(response["payload"]))

    def test_status_view_clamps_mood_and_stores_latest_zone(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Memory:
            def __init__(self):
                self.payload = None

            async def async_update_client_metadata(self, runtime, payload, *, user_id=None):
                self.payload = dict(payload)
                return "djconnect-watchos-68B74487726D"

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}
            memory = Memory()

            def authorize_device_request(self, headers, body_device_id=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and body_device_id == "djconnect-watchos-68B74487726D"
                )

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-watchos-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}
            context = types.SimpleNamespace(user_id="user-1")

            async def json(self):
                return {
                    "device_id": "djconnect-watchos-68B74487726D",
                    "client_type": "watchos",
                    "mood": 120,
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(runtime.device_status["mood"], 100)
        self.assertEqual(runtime.device_status["mood_zone"], "party")
        self.assertEqual(runtime.memory.payload["mood"], 100)
        self.assertEqual(runtime.memory.payload["mood_zone"], "party")

    def test_push_register_requires_auth(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-ABCDEFGHIJKL"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return False

        class Request:
            headers = {"X-DJConnect-Device-ID": "djconnect-ios-ABCDEFGHIJKL"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "push_token": "secret-push-token",
                }

        response = asyncio.run(self.http.DJConnectPushRegisterView(None).post(Request()))

        self.assertEqual(response["status_code"], 401)

    def test_push_register_and_unregister_use_relay(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-ABCDEFGHIJKL"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and body_device_id == "djconnect-ios-ABCDEFGHIJKL"
                )

        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})

        class Context:
            user_id = "user-1"

        class RegisterRequest:
            context = Context()
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-ABCDEFGHIJKL",
            }
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "push_token": "secret-push-token",
                    "push_environment": "sandbox",
                    "notification_categories": ["ask_dj_response"],
                }

        calls = []

        async def bootstrap_push(hass_arg, runtime_arg, **kwargs):
            calls.append(("bootstrap", hass_arg, runtime_arg, kwargs))
            return {
                "success": False,
                "push_supported": True,
                "push_registered": False,
                "push_environment": "sandbox",
                "error": "bootstrap_proof_unavailable",
                "last_push_error": "bootstrap_proof_unavailable",
            }

        async def register_push(hass_arg, runtime_arg, **kwargs):
            calls.append(("register", hass_arg, runtime_arg, kwargs))
            return {
                "success": True,
                "push_supported": True,
                "push_registered": True,
                "push_environment": "sandbox",
            }

        async def unregister_push(hass_arg, runtime_arg, **kwargs):
            calls.append(("unregister", hass_arg, runtime_arg, kwargs))
            return {
                "success": True,
                "push_supported": True,
                "push_registered": False,
            }

        original_bootstrap = self.http.async_bootstrap_push
        original_register = self.http.async_register_push
        original_unregister = self.http.async_unregister_push
        self.http.async_bootstrap_push = bootstrap_push
        self.http.async_register_push = register_push
        self.http.async_unregister_push = unregister_push
        try:
            bootstrap = asyncio.run(self.http.DJConnectPushBootstrapView(None).post(RegisterRequest()))
            register = asyncio.run(self.http.DJConnectPushRegisterView(None).post(RegisterRequest()))
            unregister = asyncio.run(self.http.DJConnectPushUnregisterView(None).post(RegisterRequest()))
        finally:
            self.http.async_bootstrap_push = original_bootstrap
            self.http.async_register_push = original_register
            self.http.async_unregister_push = original_unregister

        self.assertEqual(bootstrap["status_code"], 400)
        self.assertEqual(bootstrap["payload"]["error"], "bootstrap_proof_unavailable")
        self.assertNotIn("bootstrap_proof", bootstrap["payload"])
        self.assertEqual(register["status_code"], 200)
        self.assertTrue(register["payload"]["push_registered"])
        self.assertEqual(unregister["status_code"], 200)
        self.assertFalse(unregister["payload"]["push_registered"])
        self.assertEqual(calls[0][0], "bootstrap")
        self.assertEqual(calls[1][0], "register")
        self.assertEqual(calls[1][3]["user_id"], "user-1")
        self.assertEqual(calls[1][3]["payload"]["push_token"], "secret-push-token")
        self.assertEqual(calls[2][0], "unregister")

    def test_push_register_finds_watchos_runtime_by_device_id(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-watchos-ABCDEFGHIJKL"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and body_device_id == "djconnect-watchos-ABCDEFGHIJKL"
                    and client_type == "watchos"
                )

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"entry-1": runtime}})

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-watchos-ABCDEFGHIJKL",
            }
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": "djconnect-watchos-ABCDEFGHIJKL",
                    "client_type": "watchos",
                    "push_token": "watch-token",
                    "push_environment": "sandbox",
                }

        calls = []

        async def register_push(hass_arg, runtime_arg, **kwargs):
            calls.append((hass_arg, runtime_arg, kwargs))
            return {
                "success": True,
                "push_supported": True,
                "push_registered": True,
                "push_environment": "sandbox",
            }

        original_register = self.http.async_register_push
        self.http.async_register_push = register_push
        try:
            response = asyncio.run(self.http.DJConnectPushRegisterView(None).post(Request()))
        finally:
            self.http.async_register_push = original_register

        self.assertEqual(response["status_code"], 200)
        self.assertIs(calls[0][1], runtime)
        self.assertEqual(calls[0][2]["payload"]["client_type"], "watchos")

    def test_push_register_accepts_macos_identity_from_headers(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-macos-ABCDEFGHIJKL"}
            config = {"client_type": "macos"}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and body_device_id == "djconnect-macos-ABCDEFGHIJKL"
                    and client_type == "macos"
                )

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"entry-1": runtime}})

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-macos-ABCDEFGHIJKL",
                "X-DJConnect-Client-ID": "djconnect-macos-ABCDEFGHIJKL",
                "X-DJConnect-Client-Type": "macos",
                "X-DJConnect-Device-Name": "MacBook DJ",
            }
            app = {"hass": hass}

            async def json(self):
                return {
                    "push_token": "macos-token-secret-value",
                    "push_environment": "development",
                    "app_bundle_id": "dev.djconnect.mac",
                }

        calls = []

        async def register_push(hass_arg, runtime_arg, **kwargs):
            calls.append((hass_arg, runtime_arg, kwargs))
            return {
                "success": True,
                "push_supported": True,
                "push_registered": True,
                "push_environment": "development",
            }

        original_register = self.http.async_register_push
        self.http.async_register_push = register_push
        try:
            response = asyncio.run(self.http.DJConnectPushRegisterView(None).post(Request()))
        finally:
            self.http.async_register_push = original_register

        self.assertEqual(response["status_code"], 200)
        payload = calls[0][2]["payload"]
        self.assertEqual(payload["device_id"], "djconnect-macos-ABCDEFGHIJKL")
        self.assertEqual(payload["client_id"], "djconnect-macos-ABCDEFGHIJKL")
        self.assertEqual(payload["client_type"], "macos")
        self.assertEqual(payload["device_name"], "MacBook DJ")
        self.assertEqual(payload["authorization"], "<present>")

    def test_status_view_reports_push_registration(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-ABCDEFGHIJKL"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        class Context:
            user_id = "user-1"

        class Request:
            context = Context()
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-ABCDEFGHIJKL",
            }
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                }

        async def push_status(hass_arg, runtime_arg, **kwargs):
            return {
                "push_supported": True,
                "push_registered": True,
                "push_environment": "sandbox",
                "last_push_error": None,
            }

        original_status = self.http.async_push_status
        self.http.async_push_status = push_status
        try:
            response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))
        finally:
            self.http.async_push_status = original_status

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["push_registered"])
        self.assertEqual(response["payload"]["push_environment"], "sandbox")

    def test_status_view_reprovisions_when_spotify_configured_false(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {
                const.CONF_ASSIST_PIPELINE_ID: "pipeline",
                const.CONF_HA_EXTERNAL_URL: "https://ha.example",
            }

            def authorize_device_request(self, headers, body_device_id=None):
                return True


            def spotify_payload(self):
                return {
                    "client_id": "client-id",
                    "refresh_token": "refresh-token",
                    "spotify_client_id": "client-id",
                    "spotify_refresh_token": "refresh-token",
                }

            def device_language(self):
                return "en"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}
            remote = "192.168.1.109"

            async def json(self):
                return {
                    "device_id": "djconnect-device",
                    "client_type": "esp32",
                    "spotify_configured": False,
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(
            response["payload"]["ha_local_url"],
            "http://homeassistant.local:8123",
        )
        self.assertNotIn("ha_remote_url", response["payload"])
        self.assertNotIn("ha_url", response["payload"])
        self.assertTrue(response["payload"]["backend_available"])
        self.assertNotIn("refresh_token", response["payload"])
        self.assertNotIn("spotify_refresh_token", response["payload"])
        self.assertNotIn("spotify", response["payload"])
        self.assertEqual(runtime.device_status["local_ip"], "192.168.1.109")

    def test_status_view_persists_reported_device_identity_and_local_url(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        entry = types.SimpleNamespace(data={const.CONF_PAIR_CODE: "981032"})

        class ConfigEntries:
            def __init__(self):
                self.updates = []

            def async_update_entry(self, entry, *, data):
                self.updates.append(data)
                entry.data = data

        config_entries = ConfigEntries()

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True


            def spotify_payload(self):
                return {}

            def device_language(self):
                return "en"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        runtime.entry = entry

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {
                "hass": types.SimpleNamespace(
                    data={const.DOMAIN: {"runtime": runtime}},
                    config_entries=config_entries,
                )
            }

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "local_url": "http://djconnect-lilygo-90B70990A994.local",
                    "spotify_configured": True,
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["client_type"], "esp32")
        self.assertEqual(
            config_entries.updates[0][const.CONF_DEVICE_ID],
            "djconnect-lilygo-90B70990A994",
        )
        self.assertEqual(config_entries.updates[0][const.CONF_DEVICE_TOKEN], "device-token")
        self.assertEqual(config_entries.updates[0][const.CONF_CLIENT_TYPE], "esp32")
        self.assertEqual(
            config_entries.updates[0][const.CONF_LOCAL_URL],
            "http://djconnect-lilygo-90B70990A994.local",
        )

    def test_status_view_rejects_missing_client_type(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {"device_id": "djconnect-lilygo-90B70990A994"}

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(response["payload"]["error"], "invalid_client_type")
        self.assertIn("client_type", response["payload"]["message"])
        self.assertIn("client_type=esp32", runtime.last_update["last_error"])

    def test_status_view_accepts_lilygo_device_id_and_flattens_device_settings(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-981032"}
            ota_in_progress = True
            ota_last_error = None
            config = {}
            pairing_device_id = "djconnect-981032"

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def get_current_spotify_credentials(self):
                return {}

            def device_language(self):
                return "nl"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "ios",
                    "update_state": "idle",
                    "firmware": "3.3.6",
                    "wake_word_enabled": False,
                    "settings": {
                        "screen_brightness_percent": 91,
                        "screen_off_timeout_ms": 60000,
                        "turn_off_after_ms": 300000,
                        "speaker_volume_percent": 45,
                        "wake_word_enabled": True,
                        "language": "nl",
                        "theme": "dark",
                        "log_level": "info",
                    },
                    "screen": {"state": "on", "brightness_level": 88},
                    "led": {"state": "off"},
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["client_type"], "ios")
        self.assertNotIn("device_language", response["payload"])
        self.assertNotIn("language", response["payload"])
        self.assertFalse(runtime.ota_in_progress)
        self.assertEqual(runtime.device_status["device_id"], "djconnect-lilygo-90B70990A994")
        self.assertEqual(runtime.device_status["client_type"], "ios")
        self.assertEqual(runtime.device_status["screen_brightness"], 91)
        self.assertEqual(runtime.device_status["screen_timeout_ms"], 60000)
        self.assertEqual(runtime.device_status["turn_off_after_ms"], 300000)
        self.assertEqual(runtime.device_status["speaker_volume"], 45)
        self.assertIs(runtime.device_status["wake_word_enabled"], True)
        self.assertEqual(runtime.device_status["screen_state"], "on")
        self.assertEqual(runtime.device_status["screen_brightness_level"], 88)
        self.assertEqual(runtime.device_status["led_state"], "off")
        self.assertNotIn("device_token", response["payload"])

    def test_status_view_sparse_heartbeat_does_not_clear_existing_sensor_values(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {
                "device_id": "djconnect-lilygo-90B70990A994",
                "client_type": "esp32",
                "battery_percent": 85,
                "wifi_rssi": -55,
                "firmware": "3.3.11",
                "screen_state": "on",
                "led_state": "idle",
                "sound_output": "Living room",
                "available_outputs": [{"id": "dev-1", "name": "Living room"}],
            }
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def get_current_spotify_credentials(self):
                return {}

            def device_language(self):
                return "nl"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "battery_percent": None,
                    "wifi_rssi": None,
                    "firmware": "",
                    "screen": {"state": None},
                    "led": {"state": None},
                    "sound_output": "",
                    "available_outputs": [],
                    "ha_pairing_status": "paired",
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(runtime.device_status["battery_percent"], 85)
        self.assertEqual(runtime.device_status["wifi_rssi"], -55)
        self.assertEqual(runtime.device_status["firmware"], "3.3.11")
        self.assertEqual(runtime.device_status["screen_state"], "on")
        self.assertEqual(runtime.device_status["led_state"], "idle")
        self.assertEqual(runtime.device_status["sound_output"], "Living room")
        self.assertEqual(
            runtime.device_status["available_outputs"],
            [{"id": "dev-1", "name": "Living room"}],
        )
        self.assertEqual(runtime.device_status["ha_pairing_status"], "paired")

    def test_status_view_unknown_pairing_status_does_not_replace_paired(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {
                "device_id": "djconnect-lilygo-90B70990A994",
                "client_type": "esp32",
                "ha_pairing_status": "paired",
            }
            ota_in_progress = False
            ota_last_error = None
            last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

            def get_current_spotify_credentials(self):
                return {}

            def device_language(self):
                return "nl"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "ha_pairing_status": "unknown",
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(runtime.device_status["ha_pairing_status"], "paired")
        self.assertEqual(runtime.last_update, {"last_error": None})

    def test_persist_paired_device_stores_last_known_status_without_secrets(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={const.CONF_DEVICE_ID: "old"},
            options={},
        )
        updates = []

        class ConfigEntries:
            def async_update_entry(self, entry_arg, *, data):
                updates.append(data)
                entry_arg.data = data

        runtime = types.SimpleNamespace(
            entry=entry,
            device_status={
                "device_id": "djconnect-lilygo-90B70990A994",
                "client_type": "esp32",
                "ha_pairing_status": "paired",
                "battery_percent": 85,
                "firmware": "3.0.23",
                "sound_output": "Living room",
                "device_token": "secret-device-token",
                "nested": {"refresh_token": "secret-refresh", "state": "ok"},
            },
        )
        hass = types.SimpleNamespace(config_entries=ConfigEntries())

        self.http._persist_paired_device(
            hass,
            runtime,
            "djconnect-lilygo-90B70990A994",
            "http://djconnect-lilygo-90B70990A994.local",
            "device-token",
            "esp32",
        )

        status = updates[0]["last_device_status"]
        self.assertEqual(status["ha_pairing_status"], "paired")
        self.assertEqual(status["battery_percent"], 85)
        self.assertEqual(status["firmware"], "3.0.23")
        self.assertEqual(status["sound_output"], "Living room")
        self.assertNotIn("device_token", status)
        self.assertNotIn("refresh_token", status["nested"])
        self.assertEqual(status["nested"]["state"], "ok")

    def test_persist_runtime_device_status_stores_last_track_and_dj_text(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"device_id": "djconnect-lilygo-90B70990A994"},
            options={},
        )
        updates = []

        class ConfigEntries:
            def async_update_entry(self, entry_arg, *, data):
                updates.append(data)
                entry_arg.data = data

        runtime = types.SimpleNamespace(
            entry=entry,
            device_status={
                "device_id": "djconnect-lilygo-90B70990A994",
                "last_track": "Nirvana",
                "last_command": "Daar is Nirvana",
                "last_dj_text": "Daar is Nirvana",
                "device_token": "secret-device-token",
            },
        )
        hass = types.SimpleNamespace(config_entries=ConfigEntries())

        self.http._persist_runtime_device_status(hass, runtime)

        status = updates[0]["last_device_status"]
        self.assertEqual(status["last_track"], "Nirvana")
        self.assertEqual(status["last_command"], "Daar is Nirvana")
        self.assertEqual(status["last_dj_text"], "Daar is Nirvana")
        self.assertNotIn("device_token", status)

    def test_status_view_accepts_same_major_minor_firmware(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def get_current_spotify_credentials(self):
                return {}

            def device_language(self):
                return "nl"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "firmware": "v3.3.99",
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(runtime.device_status["firmware"], "v3.3.99")

    def test_status_view_rejects_different_major_minor_firmware(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def get_current_spotify_credentials(self):
                return {}

            def device_language(self):
                return "nl"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "firmware": "3.0.99",
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 426)
        self.assertEqual(response["payload"]["error"], "version_mismatch")
        self.assertEqual(response["payload"]["ha_major_minor"], "3.3")
        self.assertEqual(response["payload"]["firmware_major_minor"], "3.0")

    def test_command_view_rejects_known_different_major_minor_firmware(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {
                "device_id": "djconnect-lilygo-90B70990A994",
                "firmware": "4.0.0",
            }
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

        runtime = Runtime()

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "command": "status",
                }

        response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))

        self.assertEqual(response["status_code"], 426)
        self.assertEqual(response["payload"]["error"], "version_mismatch")
        self.assertEqual(response["payload"]["firmware"], "4.0.0")

    def test_command_view_accepts_authenticated_pi_upgrade_version(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {
                "device_id": "djconnect-raspberry-pi-90B70990A994",
                "app_version": "3.2.20",
            }
            config = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=False):
            self.assertIs(runtime_arg, runtime)
            self.assertEqual(command, "status")
            return {"success": True}

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-raspberry-pi-90B70990A994",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-raspberry-pi-90B70990A994",
                    "client_type": "raspberry_pi",
                    "command": "status",
                    "app_version": "3.3.0",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(runtime.device_status["app_version"], "3.3.0")

    def test_dev_firmware_zero_version_skips_major_minor_check(self) -> None:
        self.assertTrue(self.http._versions_compatible("3.0.7", "0.0.0"))
        self.assertTrue(self.http._versions_compatible("3.0.7", " 0.0.0 "))
        self.assertFalse(self.http._versions_compatible("3.1.0", "3.2.0"))
        self.assertFalse(self.http._versions_compatible("3.0.7", "4.0.0"))

    def test_command_view_accepts_nested_repeat_action_value(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=False):
            calls.append((command, value))
            if command == "set_repeat":
                return {"success": True, "playback": {"repeat_state": value}}
            raise AssertionError(f"unexpected command: {command}")

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "set_repeat",
                    "value": {"command": "set_repeat", "value": "track", "label": "Repeat nummer"},
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(calls, [("set_repeat", "track")])

    def test_command_view_handles_save_current_track_from_now_playing(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}

            def __init__(self):
                self.memory = types.SimpleNamespace(
                    blocked=[],
                    async_record_blocked_music_preference=self._record_blocked,
                )

            async def _record_blocked(self, runtime, item, payload=None, *, user_id=None):
                self.memory.blocked.append((item, payload, user_id))
                return payload.get("music_dna_key") if payload else self.device_status["device_id"]

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=False):
            calls.append((command, value, play))
            if command == "set_current_track_favorite":
                return {
                    "success": True,
                    "playback": {
                        "track_name": "Karma Police",
                        "artist": "Radiohead",
                        "uri": "spotify:track:karma-police",
                        "is_liked": False,
                    },
                }
            raise AssertionError(f"unexpected command: {command}")

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "set_current_track_favorite",
                    "value": False,
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(calls, [("set_current_track_favorite", False, False)])
        self.assertEqual(response["payload"]["playback"]["uri"], "spotify:track:karma-police")
        self.assertFalse(response["payload"]["playback"]["is_liked"])
        self.assertEqual(len(runtime.memory.blocked), 1)
        blocked_item, blocked_payload, blocked_user_id = runtime.memory.blocked[0]
        self.assertEqual(blocked_item["kind"], "track")
        self.assertEqual(blocked_item["name"], "Radiohead - Karma Police")
        self.assertEqual(blocked_item["uri"], "spotify:track:karma-police")
        self.assertEqual(blocked_item["reason"], "removed_from_favorites")
        self.assertEqual(blocked_payload["client_type"], "ios")
        self.assertIsNone(blocked_user_id)

    def test_command_view_accepts_ask_dj_message_prompt_fallback(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def ask_handler(hass, runtime_arg, payload, **kwargs):
            calls.append(payload["text"])
            return {"success": True, "text": "ok", "dj_text": "ok"}

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_message",
                    "prompt": "Meer van Scooter",
                }

        original = self.http.async_handle_ask_dj
        self.http.async_handle_ask_dj = ask_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.async_handle_ask_dj = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(calls, ["Meer van Scooter"])

    def test_command_view_routes_help_command_to_ask_dj(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        ask_calls = []
        music_calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def ask_handler(hass, runtime_arg, payload, **kwargs):
            ask_calls.append(payload["text"])
            return {
                "success": True,
                "text": "Dit kun je aan Ask DJ vragen",
                "dj_text": "Dit kun je aan Ask DJ vragen",
                "action": "none",
                "playback_actions": [],
            }

        async def command_handler(hass, runtime_arg, command, value=None, *, play=False):
            music_calls.append(command)
            return {"success": True}

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "help",
                }

        original_ask = self.http.async_handle_ask_dj
        original_command = self.http.run_music_command
        self.http.async_handle_ask_dj = ask_handler
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.async_handle_ask_dj = original_ask
            self.http.run_music_command = original_command

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(ask_calls, ["help"])
        self.assertEqual(music_calls, [])
        self.assertEqual(response["payload"]["action"], "none")
        self.assertEqual(response["payload"]["playback_actions"], [])

    def test_command_view_handles_volume_delta_action(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=False):
            calls.append((command, value))
            if command == "status":
                return {"success": True, "playback": {"volume_percent": 30}}
            if command == "set_volume":
                return {"success": True, "playback": {"volume_percent": value}}
            raise AssertionError(f"unexpected command: {command}")

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "volume_delta",
                    "value": {"command": "volume_delta", "value": -10, "label": "Zachter"},
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(calls, [("status", None), ("set_volume", 20)])
        self.assertEqual(response["payload"]["images"], [])
        self.assertEqual(response["payload"]["items"], [])

    def test_status_view_prefers_current_spotify_credentials(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True


            def spotify_payload(self):
                return {
                    "client_id": "client-id",
                    "refresh_token": "stale-token",
                    "spotify_refresh_token": "stale-token",
                }

            def get_current_spotify_credentials(self):
                return {
                    "client_id": "client-id",
                    "refresh_token": "rotated-token",
                    "spotify_client_id": "client-id",
                    "spotify_refresh_token": "rotated-token",
                }

            def device_language(self):
                return "en"

            def update(self, **kwargs):
                self.last_update = kwargs

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-device",
                    "client_type": "esp32",
                    "spotify_configured": False,
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["backend_available"])
        self.assertEqual(response["payload"]["ha_version"], const.VERSION)
        self.assertEqual(response["payload"]["ha_major_minor"], "3.3")
        self.assertIn("playback", response["payload"])
        self.assertNotIn("refresh_token", response["payload"])
        self.assertNotIn("spotify_refresh_token", response["payload"])

    def test_status_view_uses_entry_spotify_token_after_fresh_app_pairing(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        entry = types.SimpleNamespace(
            data={
                const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                const.CONF_SPOTIFY_REFRESH_TOKEN: "fresh-refresh-token",
                const.CONF_SPOTIFY_SCOPES: const.DEFAULT_SPOTIFY_SCOPES,
            },
            options={},
        )

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-macos-68B74487726D"}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def __init__(self):
                self.entry = entry

            def authorize_device_request(self, headers, body_device_id=None):
                return body_device_id == "djconnect-macos-68B74487726D"

            def get_current_spotify_credentials(self):
                return {}

            def device_language(self):
                return "en"

            def update(self, **kwargs):
                self.last_update = kwargs

        class ConfigEntries:
            def async_entries(self, domain=None):
                return [entry]

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {
                "hass": types.SimpleNamespace(
                    data={const.DOMAIN: {"runtime": Runtime()}},
                    config_entries=ConfigEntries(),
                )
            }

            async def json(self):
                return {
                    "device_id": "djconnect-macos-68B74487726D",
                    "client_type": "macos",
                    "spotify_configured": False,
                }

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            return {"success": True, "playback": {"has_playback": False}}

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["backend_available"])
        self.assertEqual(response["payload"]["playback"], {"has_playback": False})
        self.assertNotIn("refresh_token", response["payload"])
        self.assertNotIn("spotify_refresh_token", response["payload"])

    def test_status_view_reprovision_log_does_not_include_token(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True


            def get_current_spotify_credentials(self):
                return {
                    "client_id": "client-id",
                    "refresh_token": "secret-refresh-token",
                    "spotify_client_id": "client-id",
                    "spotify_refresh_token": "secret-refresh-token",
                }

            def device_language(self):
                return "en"

            def update(self, **kwargs):
                self.last_update = kwargs

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-device",
                    "client_type": "esp32",
                    "spotify_configured": False,
                }

        with self.assertLogs(self.http._LOGGER, level="DEBUG") as captured:
            response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        log_output = "\n".join(captured.output)
        self.assertEqual(response["status_code"], 200)
        self.assertIn("spotify_configured=False", log_output)
        self.assertIn("backend_available=True", log_output)
        self.assertNotIn("secret-refresh-token", log_output)

    def test_status_view_omits_spotify_when_configured_true(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True


            def spotify_payload(self):
                return {
                    "client_id": "client-id",
                    "refresh_token": "refresh-token",
                    "spotify_client_id": "client-id",
                    "spotify_refresh_token": "refresh-token",
                }

            def device_language(self):
                return "en"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-device",
                    "client_type": "esp32",
                    "spotify_configured": True,
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertNotIn("spotify", response["payload"])
        self.assertNotIn("spotify_refresh_token", response["payload"])

    def test_status_view_handles_missing_spotify_config_without_empty_tokens(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            ota_in_progress = False
            ota_last_error = None
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True


            def spotify_payload(self):
                return {}

            def device_language(self):
                return "en"

            def update(self, **kwargs):
                self.last_update = kwargs

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-device",
                    "client_type": "esp32",
                    "spotify_configured": False,
                }

        response = asyncio.run(self.http.DJConnectStatusView(None).post(Request()))

        self.assertEqual(response["status_code"], 200)
        self.assertNotIn("spotify", response["payload"])
        self.assertNotIn("spotify_refresh_token", response["payload"])

    def test_command_view_dispatches_backend_command(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-lilygo-90B70990A994"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {"success": True, "devices": [{"name": "iPhone"}]}

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "command": "devices",
                    "value": "",
                    "play": False,
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["devices"][0]["name"], "iPhone")
        self.assertEqual(calls, [("devices", "", False)])

    def test_command_view_routes_current_track_question_to_ask_dj_not_playback(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        ask_calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-macos-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def fail_command(hass, runtime_arg, command, value=None, *, play=None):
            raise AssertionError("current-track question must not reach playback")

        async def ask_handler(hass, runtime_arg, payload, **kwargs):
            ask_calls.append(payload)
            return {
                "success": True,
                "text": "Je hoort nu Gave It All van HAEVN.",
                "dj_text": "Je hoort nu Gave It All van HAEVN.",
                "audio_url": "/api/djconnect/v1/tts/current.mp3",
                "is_generated_text": True,
                "text_source": "generated",
            }

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-macos-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-macos-68B74487726D",
                    "client_type": "macos",
                    "command": "play",
                    "value": "wat speelt er",
                    "play": True,
                }

        original_command = self.http.run_music_command
        original_ask = self.http.async_handle_ask_dj
        self.http.run_music_command = fail_command
        self.http.async_handle_ask_dj = ask_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original_command
            self.http.async_handle_ask_dj = original_ask

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["audio_url"], "/api/djconnect/v1/tts/current.mp3")
        self.assertEqual(ask_calls[0]["text"], "wat speelt er")
        self.assertEqual(ask_calls[0]["audio_response"], "auto")

    def test_command_view_unsupported_backend_capability_contract(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        use_cases = importlib.import_module("custom_components.djconnect.use_cases")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {
                const.CONF_MUSIC_BACKEND: const.MUSIC_BACKEND_MUSIC_ASSISTANT,
                const.CONF_MUSIC_ASSISTANT_PLAYER: "media_player.mass_woonkamer",
            }

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            raise use_cases.MusicBackendCapabilityError(
                command,
                "supports_recently_played",
                "music_assistant",
            )

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "recently_played",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 400)
        payload = response["payload"]
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "unsupported_backend_capability")
        self.assertEqual(payload["capability"], "supports_recently_played")
        self.assertEqual(payload["backend"], "music_assistant")
        self.assertEqual(payload["music_backend"], "music_assistant")

    def test_command_view_rejects_stale_backend_action(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {
                const.CONF_MUSIC_BACKEND: const.MUSIC_BACKEND_MUSIC_ASSISTANT,
                const.CONF_MUSIC_BACKEND_REVISION: 4,
                const.CONF_MUSIC_ASSISTANT_PLAYER: "media_player.mass_woonkamer",
            }

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_play_recommendation",
                    "value": {
                        "backend": "spotify_direct",
                        "music_backend_revision": 3,
                        "kind": "track",
                        "uri": "spotify:track:old",
                        "title": "Old Track",
                    },
                }

        response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))

        self.assertEqual(response["status_code"], 400)
        payload = response["payload"]
        self.assertEqual(payload["error"], "stale_backend_action")
        self.assertEqual(payload["music_backend"], "music_assistant")
        self.assertEqual(payload["music_backend_revision"], 4)

    def test_command_view_plays_ask_dj_recommendation_and_records_memory(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Memory:
            def __init__(self):
                self.recorded = []

            async def async_update_client_metadata(self, runtime, payload=None, *, user_id=None):
                return payload.get("music_dna_key") or "shared"

            async def async_record_recommendation_play(self, runtime, recommendation, payload=None, *, user_id=None):
                self.recorded.append((recommendation, payload, user_id))
                return payload.get("music_dna_key") or "shared"

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}
            memory = Memory()

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {
                "success": True,
                "playback": {
                    "track_name": "Track Title",
                    "artist": "Artist Name",
                    "album_name": "Album Title",
                },
            }

        delivered = []

        async def dj_response(hass, runtime_arg, text):
            delivered.append(text)
            raise AssertionError("Play Now should not directly deliver a device DJ response")

        async def create_audio(hass, runtime_arg, text):
            self.assertIn("Track Title", text)
            self.assertIn("Artist Name", text)
            return "http://ha/api/djconnect/v1/tts/play-now.mp3"

        async def generate_dj_response(hass, *, media, fallback_text, conf, memory_context=None, debug=None):
            self.assertEqual(media["track_name"], "Track Title")
            self.assertEqual(media["artist"], "Artist Name")
            self.assertEqual(media["album_name"], "Album Title")
            if debug is not None:
                debug["fallback_used"] = False
            return "Daar gaan we: Track Title van Artist Name, vanaf Album Title."

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_play_recommendation",
                    "play": True,
                    "value": {
                        "title": "Track Title",
                        "subtitle": "Artist Name",
                        "uri": "spotify:track:123",
                        "context_uri": "spotify:album:456",
                        "offset_uri": "spotify:track:123",
                        "kind": "track",
                        "music_dna_key": "shared",
                        "reason": "Past bij je profiel.",
                    },
                }

        original = self.http.run_music_command
        original_dj_response = self.http.async_send_dj_response_best_effort
        original_create_audio = self.http.async_create_dj_audio_url
        original_generate = self.http.generate_dj_response_with_assist
        self.http.run_music_command = command_handler
        self.http.async_send_dj_response_best_effort = dj_response
        self.http.async_create_dj_audio_url = create_audio
        self.http.generate_dj_response_with_assist = generate_dj_response
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original
            self.http.async_send_dj_response_best_effort = original_dj_response
            self.http.async_create_dj_audio_url = original_create_audio
            self.http.generate_dj_response_with_assist = original_generate

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["action"], "spotify_start_recommendation")
        self.assertEqual(
            response["payload"]["dj_text"],
            "Daar gaan we: Track Title van Artist Name, vanaf Album Title.",
        )
        self.assertEqual(delivered, [])
        self.assertFalse(response["payload"]["dj_response"]["delivered"])
        self.assertFalse(response["payload"]["dj_response"]["spoken"])
        self.assertFalse(response["payload"]["dj_response"]["displayed"])
        self.assertEqual(
            response["payload"]["audio_url"],
            "http://ha/api/djconnect/v1/tts/play-now.mp3",
        )
        self.assertEqual(response["payload"]["assistant_message"]["origin"], "play_now")
        self.assertEqual(response["payload"]["assistant_message"]["text"], response["payload"]["dj_text"])
        self.assertEqual(
            response["payload"]["assistant_message"]["audio_url"],
            "http://ha/api/djconnect/v1/tts/play-now.mp3",
        )
        self.assertEqual(response["payload"]["assistant_message"]["playback_actions"], [])
        self.assertEqual(response["payload"]["audio_type"], "mp3")
        self.assertEqual(
            calls,
            [
                (
                    "play_context_at",
                    {
                        "context_uri": "spotify:album:456",
                        "offset_uri": "spotify:track:123",
                    },
                    True,
                )
            ],
        )
        self.assertEqual(runtime.memory.recorded[0][0]["uri"], "spotify:track:123")
        self.assertEqual(runtime.memory.recorded[0][1]["music_dna_key"], "shared")

    def test_command_view_play_now_fallback_uses_voice_profile_style(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {const.CONF_VOICE_PROFILE: const.VOICE_PROFILE_LATE_NIGHT}

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            return {
                "success": True,
                "playback": {
                    "track_name": "Dream On",
                    "artist": "Scala & Kolacny Brothers",
                    "album_name": "Dream On",
                },
            }

        async def generate_dj_response(hass, *, media, fallback_text, conf, memory_context=None, debug=None):
            self.assertIn("Volume in je hoofd omhoog", fallback_text)
            self.assertIn("Met wat extra drive erbij", fallback_text)
            self.assertNotEqual(fallback_text, "Ik speel Dream On nu af.")
            if debug is not None:
                debug["fallback_used"] = True
            return fallback_text

        async def create_audio(hass, runtime_arg, text):
            return "http://ha/api/djconnect/v1/tts/play-now.mp3"

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_play_recommendation",
                    "mood": 70,
                    "value": {
                        "title": "Dream On",
                        "subtitle": "Scala & Kolacny Brothers",
                        "uri": "spotify:album:456",
                        "kind": "album",
                    },
                }

        original = self.http.run_music_command
        original_create_audio = self.http.async_create_dj_audio_url
        original_generate = self.http.generate_dj_response_with_assist
        self.http.run_music_command = command_handler
        self.http.async_create_dj_audio_url = create_audio
        self.http.generate_dj_response_with_assist = generate_dj_response
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original
            self.http.async_create_dj_audio_url = original_create_audio
            self.http.generate_dj_response_with_assist = original_generate

        self.assertEqual(response["status_code"], 200)
        self.assertIn("Dream On van Scala & Kolacny Brothers", response["payload"]["dj_text"])
        self.assertIn("Volume in je hoofd omhoog", response["payload"]["dj_text"])
        self.assertIn("Met wat extra drive erbij", response["payload"]["dj_text"])
        self.assertEqual(response["payload"]["text_source"], "fallback")
        self.assertFalse(response["payload"]["is_generated_text"])
        self.assertEqual(response["payload"]["assistant_message"]["text_source"], "fallback")
        self.assertFalse(response["payload"]["assistant_message"]["is_generated_text"])
        self.assertNotEqual(response["payload"]["dj_text"], "Ik speel Dream On nu af.")

    def test_command_view_play_now_fallback_prefers_mood_over_request_voice_profile(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-macos-68B74487726D"}
            config = {const.CONF_VOICE_PROFILE: const.VOICE_PROFILE_LATE_NIGHT}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            return {
                "success": True,
                "playback": {
                    "track_name": "Strong",
                    "artist": "London Grammar",
                },
            }

        async def generate_dj_response(hass, *, media, fallback_text, conf, memory_context=None, debug=None):
            self.assertIn("Gestart:", fallback_text)
            self.assertIn("We houden de energie lekker hoog", fallback_text)
            self.assertNotIn("Volume in je hoofd omhoog", fallback_text)
            self.assertNotIn("Leun maar even achterover", fallback_text)
            if debug is not None:
                debug["fallback_used"] = True
            return fallback_text

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-macos-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-macos-68B74487726D",
                    "client_type": "macos",
                    "command": "ask_dj_play_recommendation",
                    "mood": 95,
                    "voice_profile": const.VOICE_PROFILE_ENERGY,
                    "value": {
                        "title": "Strong",
                        "subtitle": "London Grammar",
                        "uri": "spotify:track:strong",
                        "kind": "track",
                    },
                }

        original = self.http.run_music_command
        original_generate = self.http.generate_dj_response_with_assist
        self.http.run_music_command = command_handler
        self.http.generate_dj_response_with_assist = generate_dj_response
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original
            self.http.generate_dj_response_with_assist = original_generate

        self.assertEqual(response["status_code"], 200)
        self.assertIn("Gestart:", response["payload"]["dj_text"])
        self.assertIn("We houden de energie lekker hoog", response["payload"]["dj_text"])

    def test_command_view_returns_output_choices_when_recommendation_has_no_active_speaker(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {
                "device_id": "djconnect-ios-68B74487726D",
                "available_outputs": [{"id": "fallback", "name": "Fallback speaker"}],
            }
            config = {}
            memory = None

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append((command, value, play))
            if command == "play":
                raise self.http.SpotifyBackendError("No active device")
            if command == "devices":
                return {
                    "success": True,
                    "devices": [
                        {"id": "speaker-1", "name": "Woonkamer", "type": "Speaker"},
                        {"id": "speaker-2", "name": "Keuken", "type": "Speaker"},
                    ],
                }
            raise AssertionError(f"unexpected command: {command}")

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_play_recommendation",
                    "value": {
                        "title": "I Think Of Home",
                        "subtitle": "Snow Patrol",
                        "uri": "spotify:album:home",
                        "kind": "album",
                    },
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["action"], "select_output")
        self.assertIn("Kies een speaker", response["payload"]["dj_text"])
        self.assertEqual([action["title"] for action in response["payload"]["playback_actions"]], ["Woonkamer", "Keuken"])
        first = response["payload"]["playback_actions"][0]
        self.assertEqual(first["command"], "ask_dj_play_recommendation_on_output")
        self.assertEqual(first["value"]["output_id"], "speaker-1")
        self.assertEqual(first["value"]["recommendation"]["uri"], "spotify:album:home")
        self.assertEqual([call[0] for call in calls], ["play", "devices"])

    def test_command_view_plays_recommendation_after_output_choice(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}
            memory = None

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {"success": True, "playback": {"track_name": "I Think Of Home"}}

        async def dj_response(hass, runtime_arg, text):
            return {"delivered": True}

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_play_recommendation_on_output",
                    "value": {
                        "output_id": "speaker-1",
                        "recommendation": {
                            "title": "I Think Of Home",
                            "uri": "spotify:album:home",
                            "kind": "album",
                        },
                    },
                }

        original = self.http.run_music_command
        original_dj_response = self.http.async_send_dj_response_best_effort
        self.http.run_music_command = command_handler
        self.http.async_send_dj_response_best_effort = dj_response
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original
            self.http.async_send_dj_response_best_effort = original_dj_response

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["action"], "spotify_start_recommendation")
        self.assertEqual(
            calls,
            [
                ("set_output", "speaker-1", False),
                ("play", "spotify:album:home", True),
            ],
        )

    def test_command_view_replays_ask_dj_playback_request_after_output_choice(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        ask_dj = importlib.import_module("custom_components.djconnect.ask_dj")
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {
                "device_id": "djconnect-ios-68B74487726D",
                "client_type": "ios",
            }
            config = {}
            memory = None
            last_playback = {}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return headers.get("Authorization") == "Bearer device-token"

            def device_language(self):
                return "nl"

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append((command, value, play))
            if command == "set_output":
                return {"success": True}
            if command == "status":
                return {"success": True, "playback": {}}
            return {"success": True}

        async def process_handler(hass, runtime_arg, text, *, play=True, correct_stt=False):
            calls.append(("process", text, play))
            return {
                "success": True,
                "text": "Daar is London Grammar.",
                "dj_text": "Daar is London Grammar.",
                "playback": {"artist": "London Grammar"},
            }

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_play_request_on_output",
                    "value": {
                        "output_id": "speaker-1",
                        "request": {
                            "text": "speel london grammar",
                            "client_type": "ios",
                            "audio_response": "never",
                        },
                    },
                }

        original_command = self.http.run_music_command
        original_process = self.http.run_text_command
        original_ask_dj_process = ask_dj.run_text_command
        self.http.run_music_command = command_handler
        self.http.run_text_command = process_handler
        ask_dj.run_text_command = process_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original_command
            self.http.run_text_command = original_process
            ask_dj.run_text_command = original_ask_dj_process

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["intent"]["intent"], "play_music")
        self.assertIn("London Grammar", response["payload"]["dj_text"])
        self.assertEqual(
            calls,
            [
                ("set_output", "speaker-1", False),
                ("process", "speel london grammar", True),
            ],
        )

    def test_command_view_accepts_ask_dj_followup_yes_and_appends_history(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Memory:
            async def async_update_client_metadata(self, runtime, payload=None, *, user_id=None):
                return payload.get("music_dna_key") or "shared"

            async def async_pending_followup(self, runtime, payload=None, *, user_id=None):
                return {
                    "id": "followup-1",
                    "proposed_action": "ask_dj_play_recommendation",
                    "proposed_payload": {
                        "title": "Morning Track",
                        "uri": "spotify:track:morning",
                        "kind": "track",
                    },
                }

            async def async_consume_pending_followup(self, runtime, payload=None, *, user_id=None):
                return await self.async_pending_followup(runtime, payload, user_id=user_id)

            async def async_record_recommendation_play(self, runtime, recommendation, payload=None, *, user_id=None):
                return payload.get("music_dna_key") or "shared"

        class History:
            def __init__(self):
                self.messages = []

            async def async_append_assistant_message(self, user_id, request_payload, assistant_response):
                self.messages.append((user_id, request_payload, assistant_response))
                return {"history_revision": len(self.messages), "clear_revision": 0}

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}
            memory = Memory()
            ask_dj_history = History()

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {"success": True, "playback": {"track_name": "Morning Track"}}

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}
            context = types.SimpleNamespace(user_id="user-1")

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_followup_response",
                    "value": {
                        "kind": "confirmation",
                        "action_style": "confirmation",
                        "response_value": "yes",
                        "music_dna_key": "shared",
                    },
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["intent"]["intent"], "followup_accepted")
        self.assertIn("Morning Track", response["payload"]["dj_text"])
        self.assertEqual(calls, [("play", "spotify:track:morning", True)])
        self.assertEqual(runtime.ask_dj_history.messages[0][0], "user-1")
        self.assertEqual(runtime.ask_dj_history.messages[0][2]["intent"]["intent"], "followup_accepted")

    def test_command_view_accepts_ask_dj_followup_no_without_playback(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Memory:
            async def async_update_client_metadata(self, runtime, payload=None, *, user_id=None):
                return payload.get("music_dna_key") or "shared"

            async def async_pending_followup(self, runtime, payload=None, *, user_id=None):
                return {"id": "followup-1", "proposed_action": "ask_dj_play_recommendation"}

            async def async_consume_pending_followup(self, runtime, payload=None, *, user_id=None):
                return {"id": "followup-1", "proposed_action": "ask_dj_play_recommendation"}

        class History:
            def __init__(self):
                self.messages = []

            async def async_append_assistant_message(self, user_id, request_payload, assistant_response):
                self.messages.append((user_id, request_payload, assistant_response))
                return {"history_revision": len(self.messages), "clear_revision": 0}

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}
            memory = Memory()
            ask_dj_history = History()

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {"success": True}

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}
            context = types.SimpleNamespace(user_id="user-1")

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_followup_response",
                    "value": {
                        "kind": "confirmation",
                        "action_style": "confirmation",
                        "response_value": "no",
                        "music_dna_key": "shared",
                    },
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(response["payload"]["action"], "none")
        self.assertEqual(calls, [])
        self.assertIn("laat de muziek", response["payload"]["dj_text"])
        self.assertEqual(runtime.ask_dj_history.messages[0][2]["intent"]["intent"], "followup_declined")

    def test_command_view_rejects_recommendation_without_spotify_uri(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_play_recommendation",
                    "value": {"uri": "https://example.test/not-spotify"},
                }

        response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))

        self.assertEqual(response["status_code"], 400)
        self.assertFalse(response["payload"]["success"])
        self.assertEqual(response["payload"]["error"], "unsupported_recommendation_kind")

    def test_command_view_play_now_track_mix_plays_uris_and_suggests_save(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        calls = []

        class Memory:
            def __init__(self):
                self.recorded = []

            async def async_record_recommendation_play(self, runtime, recommendation, payload=None, *, user_id=None):
                self.recorded.append((recommendation, payload, user_id))

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-ios-68B74487726D"}
            config = {}
            memory = Memory()

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {"success": True, "playback": {"track_name": "One"}}

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-ios-68B74487726D",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-ios-68B74487726D",
                    "client_type": "ios",
                    "command": "ask_dj_play_recommendation",
                    "play": True,
                    "value": {
                        "title": "DJConnect mix",
                        "uri": "spotify:track:one",
                        "uris": ["spotify:track:one", "spotify:track:two"],
                        "kind": "track_mix",
                        "music_dna_key": "shared",
                    },
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertEqual(calls, [("play_uris", ["spotify:track:one", "spotify:track:two"], True)])
        self.assertIn("opsla als Spotify playlist", response["payload"]["dj_text"])
        self.assertEqual(runtime.memory.recorded[0][0]["uris"], ["spotify:track:one", "spotify:track:two"])

    def test_command_view_playlists_marks_backend_available_when_idle(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-lilygo-90B70990A994"}
            config = {}
            last_playback = {"has_playback": False, "is_playing": False}

            def authorize_device_request(self, headers, body_device_id=None):
                return headers.get("Authorization") == "Bearer device-token"

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            self.assertEqual(command, "playlists")
            self.assertEqual(value, {"client_type": "esp32", "limit": 20})
            self.assertEqual(runtime_arg.last_playback["has_playback"], False)
            return {
                "success": True,
                "playlists": [
                    {
                        "name": f"DJConnect {index}",
                        "uri": f"spotify:playlist:{index}",
                        "owner": "Peter",
                        "image_url": f"https://example.test/cover-{index}.jpg",
                    }
                    for index in range(3)
                ],
            }

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "command": "playlists",
                    "limit": 20,
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertTrue(response["payload"]["backend_available"])
        self.assertTrue(runtime.device_status["backend_available"])
        self.assertEqual(
            response["payload"]["playlists"],
            [
                {
                    "name": "DJConnect 0",
                    "owner": "Peter",
                    "uri": "spotify:playlist:0",
                    "image_url": "https://example.test/cover-0.jpg",
                },
                {
                    "name": "DJConnect 1",
                    "owner": "Peter",
                    "uri": "spotify:playlist:1",
                    "image_url": "https://example.test/cover-1.jpg",
                },
                {
                    "name": "DJConnect 2",
                    "owner": "Peter",
                    "uri": "spotify:playlist:2",
                    "image_url": "https://example.test/cover-2.jpg",
                },
            ],
        )
        self.assertEqual(response["payload"]["items"], response["payload"]["playlists"])
        self.assertNotIn("data", response["payload"])
        self.assertNotIn("result", response["payload"])
        self.assertEqual(response["payload"]["count"], 3)
        self.assertTrue(all(item.get("uri") for item in response["payload"]["playlists"]))
        self.assertTrue(all(item.get("image_url") for item in response["payload"]["playlists"]))

    def test_command_view_playlists_returns_json_for_model_specific_esp32_payload(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        device_id = "djconnect-lilygo-t-embed-s3-90B70990A994"
        calls = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": device_id, "client_type": "esp32"}
            config = {"client_type": "esp32"}
            last_playback = {"has_playback": False, "is_playing": False}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and headers.get("X-DJConnect-Device-ID") == device_id
                    and body_device_id == device_id
                    and client_type == "esp32"
                )

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            calls.append((command, value, play))
            return {
                "success": True,
                "backend_available": True,
                "playlists": [
                    {
                        "name": "Roadtrip",
                        "uri": "spotify:playlist:roadtrip",
                        "owner": "Peter",
                        "image_url": "https://example.test/roadtrip.jpg",
                    }
                ],
            }

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": device_id,
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"entry-1": runtime}})}

            async def json(self):
                return {
                    "command": "playlists",
                    "limit": 20,
                    "device_id": device_id,
                    "client_type": "esp32",
                    "payload_type": "command",
                    "firmware": "0.0.0",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertIsInstance(response["payload"], dict)
        self.assertTrue(response["payload"])
        self.assertEqual(
            calls,
            [("playlists", {"client_type": "esp32", "limit": 20}, False)],
        )
        self.assertTrue(response["payload"]["success"])
        self.assertTrue(response["payload"]["backend_available"])
        self.assertEqual(response["payload"]["playlists"][0]["name"], "Roadtrip")
        self.assertEqual(response["payload"]["playlists"][0]["uri"], "spotify:playlist:roadtrip")
        self.assertEqual(response["payload"]["items"], response["payload"]["playlists"])
        self.assertNotIn("data", response["payload"])
        self.assertNotIn("result", response["payload"])
        self.assertEqual(response["payload"]["count"], 1)

    def test_command_view_playlists_compacts_rich_esp32_playlist_payload(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        device_id = "djconnect-lilygo-t-embed-s3-90B70990A994"

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": device_id, "client_type": "esp32"}
            config = {"client_type": "esp32"}

            def authorize_device_request(self, headers, body_device_id=None, client_type=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        rich_playlists = [
            {
                "id": f"spotify:playlist:{index}",
                "name": f"Roadtrip playlist with a fairly long display name {index}",
                "title": f"Roadtrip playlist with a fairly long display name {index}",
                "display_title": f"Roadtrip playlist with a fairly long display name {index}",
                "owner": "Peter",
                "subtitle": "Peter",
                "uri": f"spotify:playlist:{index}",
                "value": f"spotify:playlist:{index}",
                "playlist_uri": f"spotify:playlist:{index}",
                "image_url": f"https://image-cdn.example.test/playlists/{index}/cover-640.jpg",
                "imageUrl": f"https://image-cdn.example.test/playlists/{index}/cover-640.jpg",
                "album_image_url": f"https://image-cdn.example.test/playlists/{index}/cover-640.jpg",
                "albumImageUrl": f"https://image-cdn.example.test/playlists/{index}/cover-640.jpg",
                "album_art_url": f"https://image-cdn.example.test/playlists/{index}/cover-640.jpg",
                "media_image_url": f"https://image-cdn.example.test/playlists/{index}/cover-640.jpg",
                "entity_picture": f"https://image-cdn.example.test/playlists/{index}/cover-640.jpg",
                "thumbnail_url": f"https://image-cdn.example.test/playlists/{index}/cover-640.jpg",
            }
            for index in range(20)
        ]

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            return {
                "success": True,
                "backend_available": True,
                "playlists": rich_playlists,
                "items": rich_playlists,
                "data": {"playlists": rich_playlists, "items": rich_playlists},
                "result": {"playlists": rich_playlists, "items": rich_playlists},
            }

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": device_id,
            }
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"entry-1": Runtime()}})}

            async def json(self):
                return {
                    "command": "playlists",
                    "limit": 20,
                    "device_id": device_id,
                    "client_type": "esp32",
                    "payload_type": "command",
                    "firmware": "0.0.0",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        body = json.dumps(response["payload"], separators=(",", ":"))
        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["count"], 20)
        self.assertEqual(len(response["payload"]["playlists"]), 20)
        self.assertEqual(response["payload"]["items"], response["payload"]["playlists"])
        self.assertNotIn("data", response["payload"])
        self.assertNotIn("result", response["payload"])
        self.assertLess(len(body), 12000)

    def test_command_view_playlists_merges_client_context_from_value(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        seen_values = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-macos-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            seen_values.append(value)
            return {
                "success": True,
                "playlists": [],
            }

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-macos-68B74487726D",
                    "client_type": "macos",
                    "command": "playlists",
                    "limit": 80,
                    "value": {},
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(seen_values, [{"client_type": "macos", "limit": 80}])
        self.assertEqual(response["payload"]["playlists"], [])
        self.assertEqual(response["payload"]["items"], [])
        self.assertEqual(response["payload"]["data"]["playlists"], [])
        self.assertEqual(response["payload"]["data"]["items"], [])
        self.assertEqual(response["payload"]["result"]["playlists"], [])
        self.assertEqual(response["payload"]["result"]["items"], [])
        self.assertEqual(response["payload"]["count"], 0)

    def test_command_view_accepts_watchos_client_payload(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        seen_commands = []

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-watchos-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return (
                    headers.get("Authorization") == "Bearer device-token"
                    and body_device_id == "djconnect-watchos-68B74487726D"
                )

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            seen_commands.append((command, value, play))
            return {"success": True, "command": command}

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-watchos-68B74487726D",
                    "client_type": "watchos",
                    "platform": "watchos",
                    "command": "status",
                    "firmware": "3.3.0",
                    "app_version": "3.3.0",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["command"], "status")
        self.assertIn("ha_install_id", response["payload"])
        self.assertEqual(response["payload"]["integration_version"], const.VERSION)
        self.assertNotIn("pairing_session_id", response["payload"])
        self.assertEqual(runtime.device_status["client_type"], "watchos")
        self.assertEqual(seen_commands, [("status", None, False)])

    def test_command_view_rejects_unknown_client_type(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"device_id": "djconnect-android-68B74487726D"}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

        runtime = Runtime()

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-android-68B74487726D",
                    "client_type": "android",
                    "command": "status",
                }

        response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))

        self.assertEqual(response["status_code"], 400)
        self.assertEqual(response["payload"]["error"], "invalid_client_type")

    def test_command_view_playlists_normalizes_nested_response_shapes(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        playlist = {
            "name": "Nested",
            "uri": "spotify:playlist:nested",
            "owner": "Peter",
            "image_url": "https://example.test/nested.jpg",
        }

        async def command_handler(hass, runtime_arg, command, value=None, *, play=None):
            return {
                "success": True,
                "result": {"playlists": {"items": [playlist]}},
            }

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-macos-68B74487726D",
                    "client_type": "macos",
                    "command": "playlists",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["playlists"], [playlist])
        self.assertEqual(response["payload"]["items"], [playlist])
        self.assertEqual(response["payload"]["data"]["playlists"], [playlist])
        self.assertEqual(response["payload"]["data"]["items"], [playlist])
        self.assertEqual(response["payload"]["result"]["playlists"], [playlist])
        self.assertEqual(response["payload"]["result"]["items"], [playlist])
        self.assertEqual(response["payload"]["count"], 1)

    def test_command_view_playlists_backend_failure_returns_non_empty_body(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        async def command_handler(hass, runtime, command, value=None, *, play=None):
            raise self.http.SpotifyBackendError("Spotify OAuth is not configured")

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "command": "playlists",
                    "limit": 20,
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertFalse(response["payload"]["success"])
        self.assertFalse(response["payload"]["backend_available"])
        self.assertEqual(response["payload"]["error"], "playback_backend_unavailable")
        self.assertEqual(response["payload"]["message"], "Spotify OAuth is not configured")
        self.assertEqual(response["payload"]["playlists"], [])
        self.assertEqual(response["payload"]["items"], [])
        self.assertEqual(response["payload"]["data"]["playlists"], [])
        self.assertEqual(response["payload"]["data"]["items"], [])
        self.assertEqual(response["payload"]["result"]["playlists"], [])
        self.assertEqual(response["payload"]["result"]["items"], [])
        self.assertEqual(response["payload"]["count"], 0)

    def test_command_view_status_returns_backend_available_and_version_metadata(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        async def command_handler(hass, runtime, command, value=None, *, play=None):
            return {
                "success": True,
                "playback": {
                    "has_playback": False,
                    "is_playing": False,
                    "title": "",
                },
            }

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-macos-68B74487726D",
                    "client_type": "macos",
                    "command": "status",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertTrue(response["payload"]["backend_available"])
        self.assertEqual(response["payload"]["ha_version"], const.VERSION)
        self.assertEqual(response["payload"]["ha_major_minor"], "3.3")
        self.assertEqual(response["payload"]["playback"]["has_playback"], False)

    def test_command_view_returns_backend_unavailable_json(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        async def command_handler(hass, runtime, command, value=None, *, play=None):
            raise self.http.SpotifyBackendError("Spotify OAuth is not configured")

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "command": "status",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertFalse(response["payload"]["success"])
        self.assertEqual(response["payload"]["error"], "backend_unavailable")
        self.assertFalse(response["payload"]["backend_available"])
        self.assertIn("Spotify OAuth", response["payload"]["message"])

    def test_command_view_returns_200_for_generic_backend_failure(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {}
            last_playback = {"has_playback": False}
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        async def command_handler(hass, runtime, command, value=None, *, play=None):
            raise RuntimeError("Temporary backend timeout")

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": Runtime()}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "command": "status",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertFalse(response["payload"]["success"])
        self.assertEqual(response["payload"]["error"], "backend_unavailable")
        self.assertFalse(response["payload"]["backend_available"])
        self.assertEqual(response["payload"]["playback"], {"has_playback": False})

    def test_command_view_does_not_repair_device_during_normal_command(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {"ha_pairing_status": "paired"}
            config = {}
            pair_called = False

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            async def pair_device(self, hass):
                self.pair_called = True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime, command, value=None, *, play=None):
            return {"success": True, "playback": {"has_playback": True}}

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "command": "next",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertTrue(response["payload"]["success"])
        self.assertFalse(runtime.pair_called)

    def test_command_payload_does_not_reset_existing_sensor_values(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {
                "device_id": "djconnect-lilygo-90B70990A994",
                "client_type": "esp32",
                "ha_pairing_status": "paired",
                "battery_percent": 85,
                "firmware": "3.3.15",
                "wifi_rssi": -55,
                "screen_state": "on",
                "led_state": "idle",
                "sound_output": "Living room",
                "last_track": "Alive",
            }
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()

        async def command_handler(hass, runtime, command, value=None, *, play=None):
            return {"success": True, "playback": {"has_playback": True}}

        class Request:
            headers = {"Authorization": "Bearer device-token"}
            app = {"hass": types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "payload_type": "command",
                    "command": "status",
                }

        original = self.http.run_music_command
        self.http.run_music_command = command_handler
        try:
            with self.assertLogs(self.http._LOGGER, level="DEBUG") as captured:
                response = asyncio.run(self.http.DJConnectCommandView(None).post(Request()))
        finally:
            self.http.run_music_command = original

        self.assertEqual(response["status_code"], 200)
        self.assertIn("Ignoring command payload for device sensor update", "\n".join(captured.output))
        self.assertEqual(runtime.device_status["ha_pairing_status"], "paired")
        self.assertEqual(runtime.device_status["battery_percent"], 85)
        self.assertEqual(runtime.device_status["firmware"], "3.3.15")
        self.assertEqual(runtime.device_status["wifi_rssi"], -55)
        self.assertEqual(runtime.device_status["screen_state"], "on")
        self.assertEqual(runtime.device_status["led_state"], "idle")
        self.assertEqual(runtime.device_status["sound_output"], "Living room")
        self.assertEqual(runtime.device_status["last_track"], "Alive")

    def test_voice_only_payload_does_not_reset_existing_sensor_values(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class Runtime:
            device_token = "device-token"
            device_status = {
                "device_id": "djconnect-lilygo-90B70990A994",
                "client_type": "esp32",
                "ha_pairing_status": "paired",
                "battery_percent": 85,
                "firmware": "3.3.15",
                "wifi_rssi": -55,
                "screen_state": "on",
                "led_state": "idle",
                "sound_output": "Living room",
            }
            config = {}

            def authorize_device_request(self, headers, body_device_id=None):
                return True

            def update(self, **kwargs):
                self.last_update = kwargs

        runtime = Runtime()
        hass = types.SimpleNamespace(data={const.DOMAIN: {"runtime": runtime}})

        class Request:
            headers = {
                "Authorization": "Bearer device-token",
                "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
                "Content-Type": "application/json",
            }
            app = {"hass": hass}

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "recording": False,
                    "state": "idle",
                    "last_error": "",
                }

        with self.assertLogs(self.http._LOGGER, level="DEBUG") as captured:
            response = asyncio.run(self.http.DJConnectVoiceView(None).post(Request()))

        self.assertEqual(response["status_code"], 400)
        self.assertIn("Ignoring voice-only payload for device sensor update", "\n".join(captured.output))
        self.assertEqual(runtime.device_status["ha_pairing_status"], "paired")
        self.assertEqual(runtime.device_status["battery_percent"], 85)
        self.assertEqual(runtime.device_status["firmware"], "3.3.15")
        self.assertEqual(runtime.device_status["wifi_rssi"], -55)
        self.assertEqual(runtime.device_status["screen_state"], "on")
        self.assertEqual(runtime.device_status["led_state"], "idle")
        self.assertEqual(runtime.device_status["sound_output"], "Living room")

    def test_store_rotated_spotify_refresh_token_persists_without_logging_secret(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        updates = []

        class ConfigEntries:
            def async_update_entry(self, entry, *, data):
                updates.append(data)
                entry.data = data

        class Runtime:
            latest_spotify_refresh_token = "old-token"

            def update_spotify_refresh_token(self, token):
                self.latest_spotify_refresh_token = token
                return True

        entry = types.SimpleNamespace(
            data={const.CONF_SPOTIFY_REFRESH_TOKEN: "old-token"}
        )
        hass = types.SimpleNamespace(config_entries=ConfigEntries())

        with self.assertLogs(self.http._LOGGER, level="DEBUG") as captured:
            changed = self.http._store_rotated_spotify_refresh_token(
                hass,
                entry,
                Runtime(),
                "new-secret-token",
            )

        self.assertTrue(changed)
        self.assertEqual(updates[0][const.CONF_SPOTIFY_REFRESH_TOKEN], "new-secret-token")
        self.assertIn("refresh_token=rotated", "\n".join(captured.output))
        self.assertNotIn("new-secret-token", "\n".join(captured.output))

    def test_spotify_callback_succeeds_when_options_flow_is_closed(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class ConfigFlow:
            async def async_configure(self, flow_id, user_input):
                raise RuntimeError()

        class ConfigEntries:
            flow = ConfigFlow()

            def __init__(self, entry):
                self.entry = entry
                self.updated = None
                self.reloaded = None

            def async_get_entry(self, entry_id):
                return self.entry

            def async_update_entry(self, entry, *, data):
                self.updated = data
                entry.data = data

            async def async_reload(self, entry_id):
                self.reloaded = entry_id

        class Query:
            def get(self, key):
                return {"state": "state-1", "code": "code-1"}.get(key)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
            },
            options={},
        )
        config_entries = ConfigEntries(entry)
        hass = types.SimpleNamespace(
            data={
                const.DOMAIN: {
                    "spotify_oauth_pending": {
                        "state-1": {
                            "flow_id": "closed-flow",
                            "entry_id": "entry-1",
                            "client_id": "client-id",
                            "code_verifier": "verifier",
                            "redirect_uri": "https://example.ui.nabu.casa/api/djconnect/v1/spotify/callback",
                            "market": "NL",
                            "scopes": "scope",
                        }
                    }
                }
            },
            config_entries=config_entries,
        )
        request = types.SimpleNamespace(app={"hass": hass}, query=Query())

        async def exchange(*args, **kwargs):
            return {"refresh_token": "new-refresh-token"}

        original_exchange = self.http.exchange_code_for_refresh_token
        self.http.exchange_code_for_refresh_token = exchange
        try:
            response = asyncio.run(self.http.DJConnectSpotifyCallbackView(None).get(request))
        finally:
            self.http.exchange_code_for_refresh_token = original_exchange

        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "text/html")
        self.assertIn("DJConnect is reauthorized", response.text)
        self.assertIn("Spotify is linked with DJConnect again", response.text)
        self.assertNotIn("refresh token", response.text)
        self.assertNotIn("Open DJConnect in Home Assistant", response.text)
        self.assertNotIn("/config/integrations/integration/djconnect", response.text)
        self.assertIn("Close window", response.text)
        self.assertIn("data:image/png;base64,", response.text)
        self.assertIn("DJConnect app icon", response.text)
        self.assertEqual(entry.data[const.CONF_SPOTIFY_REFRESH_TOKEN], "new-refresh-token")
        self.assertEqual(config_entries.reloaded, "entry-1")

    def test_spotify_oauth_html_response_uses_ha_language(self) -> None:
        hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl"))
        response = asyncio.run(
            self.http._spotify_oauth_html_response(
                hass,
                title=self.http._oauth_copy(hass, "reauth_title"),
                message=self.http._oauth_copy(hass, "reauth_message"),
            )
        )

        self.assertIn('<html lang="nl">', response.text)
        self.assertIn("DJConnect is opnieuw geautoriseerd", response.text)
        self.assertIn("Spotify is opnieuw gekoppeld met DJConnect", response.text)
        self.assertIn("Sluit venster", response.text)

    def test_spotify_oauth_logo_is_loaded_in_executor(self) -> None:
        calls = []

        class Hass:
            async def async_add_executor_job(self, func, *args):
                calls.append(func.__name__)
                return func(*args)

        self.http._LOGO_DATA_URI = None
        try:
            response = asyncio.run(
                self.http._spotify_oauth_html_response(
                    Hass(),
                    title="OAuth klaar",
                    message="Gelukt",
                )
            )
        finally:
            self.http._LOGO_DATA_URI = None

        self.assertEqual(calls, ["_read_djconnect_logo_data_uri"])
        self.assertIn("data:image/png;base64,", response.text)

    def test_spotify_callback_completes_open_repair_flow(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")

        class ConfigFlow:
            def __init__(self):
                self.configured = None

            async def async_configure(self, flow_id, user_input):
                self.configured = (flow_id, user_input)

        class ConfigEntries:
            def __init__(self, entry):
                self.entry = entry
                self.flow = ConfigFlow()
                self.updated = None
                self.reloaded = None

            def async_get_entry(self, entry_id):
                return self.entry

            def async_update_entry(self, entry, *, data):
                self.updated = data
                entry.data = data

            async def async_reload(self, entry_id):
                self.reloaded = entry_id

        class Query:
            def get(self, key):
                return {"state": "state-1", "code": "code-1"}.get(key)

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
            },
            options={},
        )
        config_entries = ConfigEntries(entry)
        hass = types.SimpleNamespace(
            data={
                const.DOMAIN: {
                    "spotify_oauth_pending": {
                        "state-1": {
                            "flow_id": "repair-flow-1",
                            "entry_id": "entry-1",
                            "client_id": "client-id",
                            "code_verifier": "verifier",
                            "redirect_uri": "https://example.ui.nabu.casa/api/djconnect/v1/spotify/callback",
                            "market": "NL",
                            "scopes": "scope",
                        }
                    }
                }
            },
            config_entries=config_entries,
        )
        request = types.SimpleNamespace(app={"hass": hass}, query=Query())

        async def exchange(*args, **kwargs):
            return {"refresh_token": "new-refresh-token"}

        original_exchange = self.http.exchange_code_for_refresh_token
        self.http.exchange_code_for_refresh_token = exchange
        try:
            response = asyncio.run(self.http.DJConnectSpotifyCallbackView(None).get(request))
        finally:
            self.http.exchange_code_for_refresh_token = original_exchange

        self.assertEqual(response.status, 200)
        self.assertEqual(
            config_entries.flow.configured,
            ("repair-flow-1", {"state": "state-1"}),
        )
        self.assertEqual(entry.data[const.CONF_SPOTIFY_REFRESH_TOKEN], "new-refresh-token")
        self.assertEqual(config_entries.reloaded, "entry-1")

    def test_tts_view_returns_audio_for_valid_token(self) -> None:
        const = importlib.import_module("custom_components.djconnect.const")
        dj_response = importlib.import_module("custom_components.djconnect.dj_response")
        hass = types.SimpleNamespace(data={})
        token = dj_response.store_tts_audio(
            hass,
            b"ID3 mp3 data",
            120,
            content_type="audio/mpeg",
            extension="mp3",
        )
        request = types.SimpleNamespace(app={"hass": hass})

        response = asyncio.run(
            self.http.DJConnectTtsView(None).get(request, token, "mp3")
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "audio/mpeg")
        self.assertEqual(response.body, b"ID3 mp3 data")
        self.assertEqual(response.headers["Content-Length"], "12")
        self.assertIn("tts_audio", hass.data[const.DOMAIN])

    def test_tts_view_returns_410_for_expired_token(self) -> None:
        dj_response = importlib.import_module("custom_components.djconnect.dj_response")
        hass = types.SimpleNamespace(data={})
        token = dj_response.store_tts_audio(hass, b"RIFFxxxxWAVEdata", 120)
        dj_response._store(hass)[token].expires_at = 0
        request = types.SimpleNamespace(app={"hass": hass})

        response = asyncio.run(self.http.DJConnectTtsView(None).get(request, token))

        self.assertEqual(response.status, 410)

    def test_tts_view_returns_404_for_unknown_token(self) -> None:
        request = types.SimpleNamespace(app={"hass": types.SimpleNamespace(data={})})

        response = asyncio.run(self.http.DJConnectTtsView(None).get(request, "unknown"))

        self.assertEqual(response.status, 404)


if __name__ == "__main__":
    unittest.main()
