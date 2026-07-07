from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import time
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]


def install_integration_stubs() -> None:
    aiohttp = sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
    voluptuous = sys.modules.setdefault("voluptuous", types.ModuleType("voluptuous"))
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    core = sys.modules.setdefault(
        "homeassistant.core",
        types.ModuleType("homeassistant.core"),
    )
    helpers = sys.modules.setdefault(
        "homeassistant.helpers",
        types.ModuleType("homeassistant.helpers"),
    )
    components = sys.modules.setdefault(
        "homeassistant.components",
        types.ModuleType("homeassistant.components"),
    )
    http = sys.modules.setdefault(
        "homeassistant.components.http",
        types.ModuleType("homeassistant.components.http"),
    )
    repairs = sys.modules.setdefault(
        "homeassistant.components.repairs",
        types.ModuleType("homeassistant.components.repairs"),
    )
    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    config_validation = sys.modules.setdefault(
        "homeassistant.helpers.config_validation",
        types.ModuleType("homeassistant.helpers.config_validation"),
    )
    issue_registry = sys.modules.setdefault(
        "homeassistant.helpers.issue_registry",
        types.ModuleType("homeassistant.helpers.issue_registry"),
    )
    typing = sys.modules.setdefault(
        "homeassistant.helpers.typing",
        types.ModuleType("homeassistant.helpers.typing"),
    )

    class ClientTimeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class HomeAssistantView:
        def json(self, payload, status_code=200):
            return {"payload": payload, "status_code": status_code}

    class RepairsFlow:
        pass

    class Response:
        def __init__(self, *, status=200, text=None, body=None, content_type=None, headers=None):
            self.status = status
            self.text = text
            self.body = body
            self.content_type = content_type
            self.headers = headers or {}

    sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.web = getattr(aiohttp, "web", types.SimpleNamespace())
    voluptuous.Schema = lambda schema: schema
    voluptuous.Optional = lambda key, *args, **kwargs: key
    voluptuous.Required = lambda key, *args, **kwargs: key
    config_entries.ConfigEntry = object
    core.HomeAssistant = object
    core.Context = object
    core.ServiceCall = object
    http.HomeAssistantView = HomeAssistantView
    repairs.RepairsFlow = RepairsFlow
    aiohttp_client.async_get_clientsession = lambda hass: None
    config_validation.config_entry_only_config_schema = lambda domain: voluptuous.Schema({})
    issue_registry.IssueSeverity = types.SimpleNamespace(WARNING="warning")
    issue_registry.async_create_issue = lambda *args, **kwargs: None
    helpers.issue_registry = issue_registry
    helpers.config_validation = config_validation
    typing.ConfigType = dict
    aiohttp.web = types.SimpleNamespace(Response=Response)
    sys.modules["homeassistant"].components = components
    components.repairs = repairs


class TtsHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_integration_stubs()
        for module_name in (
            "custom_components.djconnect.http",
            "custom_components.djconnect.tts",
            "custom_components.djconnect.dj_response",
            "custom_components.djconnect",
        ):
            sys.modules.pop(module_name, None)
        cls.integration = importlib.import_module("custom_components.djconnect")
        cls.const = importlib.import_module("custom_components.djconnect.const")
        cls.dj_response = importlib.import_module("custom_components.djconnect.dj_response")
        cls.http = importlib.import_module("custom_components.djconnect.http")
        cls.tts = importlib.import_module("custom_components.djconnect.tts")

    def test_conversation_agent_entry_only_loads_conversation_and_sensor_platforms(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_CONVERSATION_AGENT},
            options={},
            entry_id="entry-assist",
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)

        self.assertEqual(self.integration._platforms_for_runtime(runtime), ["conversation", "sensor"])

    def test_device_entry_loads_full_platform_set(self) -> None:
        for client_type in (
            self.const.CLIENT_TYPE_ESP32,
            self.const.CLIENT_TYPE_IOS,
            self.const.CLIENT_TYPE_MACOS,
            self.const.CLIENT_TYPE_WATCHOS,
            self.const.CLIENT_TYPE_RASPBERRY_PI,
            self.const.CLIENT_TYPE_WINDOWS,
        ):
            with self.subTest(client_type=client_type):
                entry = types.SimpleNamespace(
                    data={self.const.CONF_CLIENT_TYPE: client_type},
                    options={},
                    entry_id=f"entry-{client_type}",
                )
                runtime = self.integration.DJConnectRuntime(entry=entry)

                self.assertEqual(self.integration._platforms_for_runtime(runtime), self.const.PLATFORMS)

    def test_push_debug_payload_reports_flags_without_secrets(self) -> None:
        entry = types.SimpleNamespace(
            data={},
            options={
                self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_MACOS,
                self.const.CONF_DEVICE_ID: "djconnect-macos-ABCDEFGHIJKL",
                self.const.CONF_HA_INSTALL_ID: "ha-install-1",
                self.const.CONF_DJCONNECT_INSTALL_TOKEN: "djci_secret",
            },
            entry_id="entry-mac",
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_status[self.const.CONF_CENTRAL_API_BOOTSTRAP_PROOF] = "proof-secret"
        runtime.push_status = {
            "djconnect-macos-ABCDEFGHIJKL|macos": {
                "push_registered": False,
                "last_push_error": "missing_bootstrap_proof",
            }
        }

        payload = self.integration._push_debug_payload(
            runtime,
            device_id="djconnect-macos-ABCDEFGHIJKL",
            client_type="macos",
            event_type="ask_dj_confirm",
            user_id="user-1",
            explicit_user_request=True,
            send=True,
            decision={"send": True},
            result={"success": False, "sent": 0, "error": "missing_bootstrap_proof"},
        )

        rendered = str(payload)
        self.assertTrue(payload["central_api_configured"])
        self.assertTrue(payload["install_token_present"])
        self.assertTrue(payload["bootstrap_proof_present"])
        self.assertEqual(payload["error"], "missing_bootstrap_proof")
        self.assertNotIn("djci_secret", rendered)
        self.assertNotIn("proof-secret", rendered)

    def test_daily_music_discovery_push_requires_enabled_music_dna(self) -> None:
        class Memory:
            async def async_context_for_runtime(self, runtime, payload, *, user_id=None):
                return {"memory": {"enabled": False}, "music_dna_key": "client:test"}

        entry = types.SimpleNamespace(
            data={},
            options={
                self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_IOS,
                self.const.CONF_DEVICE_ID: "djconnect-ios-ABCDEFGHIJKL",
            },
            entry_id="entry-ios",
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.memory = Memory()

        result = asyncio.run(
            self.integration._async_send_daily_music_discovery_push(
                object(),
                runtime,
            )
        )

        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["suppressed"], "music_dna_disabled")

    def test_daily_music_discovery_push_sends_discovery_refresh_event_once_per_day(self) -> None:
        class Memory:
            async def async_context_for_runtime(self, runtime, payload, *, user_id=None):
                return {"memory": {"enabled": True}, "music_dna_key": "client:test"}

        calls = []

        async def send_push(*args, **kwargs):
            calls.append(kwargs)
            return {"success": True, "sent": 1}

        entry = types.SimpleNamespace(
            data={},
            options={
                self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_IOS,
                self.const.CONF_DEVICE_ID: "djconnect-ios-ABCDEFGHIJKL",
            },
            entry_id="entry-ios",
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.memory = Memory()
        original = self.integration.async_send_push_event
        self.integration.async_send_push_event = send_push
        try:
            first = asyncio.run(
                self.integration._async_send_daily_music_discovery_push(
                    object(),
                    runtime,
                    now=types.SimpleNamespace(date=lambda: __import__("datetime").date(2026, 7, 5)),
                )
            )
            second = asyncio.run(
                self.integration._async_send_daily_music_discovery_push(
                    object(),
                    runtime,
                    now=types.SimpleNamespace(date=lambda: __import__("datetime").date(2026, 7, 5)),
                )
            )
        finally:
            self.integration.async_send_push_event = original

        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertEqual(second["suppressed"], "already_sent_today")
        self.assertEqual(calls[0]["event_type"], "music_discovery_ready")
        self.assertEqual(calls[0]["source_device_id"], "djconnect-ios-ABCDEFGHIJKL")
        self.assertEqual(calls[0]["client_type"], "ios")

    def test_device_command_posts_to_local_command_api(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def text(self):
                return '{"success": true, "status": {"volume": 35}}'

        class Session:
            def __init__(self):
                self.calls = []

            def post(self, url, **kwargs):
                self.calls.append({"url": url, **kwargs})
                return Response()

        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-lilygo-90B70990A994"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "device-token"
        runtime.device_status["local_url"] = "http://djconnect.local"
        session = Session()
        original_session = self.integration.async_get_clientsession
        self.integration.async_get_clientsession = lambda hass: session
        try:
            result = asyncio.run(
                runtime.async_device_command(object(), "set_volume", value=35)
            )
        finally:
            self.integration.async_get_clientsession = original_session

        self.assertTrue(result["success"])
        self.assertEqual(
            session.calls[0]["url"],
            "http://djconnect.local/api/device/command",
        )
        self.assertEqual(session.calls[0]["headers"]["Authorization"], "Bearer device-token")
        self.assertEqual(
            session.calls[0]["json"],
            {"command": "set_volume", "value": 35},
        )
        self.assertEqual(runtime.device_status["volume"], 35)

    def test_device_command_sparse_status_does_not_clear_cached_sensors(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def text(self):
                return (
                    '{"success": true, "status": {'
                    '"firmware": null, "battery_percent": null, "wifi_rssi": null, '
                    '"ha_pairing_status": "", "sound_output": ""'
                    '}, "sound_output": ""}'
                )

        class Session:
            def post(self, url, **kwargs):
                return Response()

        entry = types.SimpleNamespace(data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "device-token"
        runtime.device_status.update(
            {
                "local_url": "http://djconnect.local",
                "firmware": "3.0.16",
                "battery_percent": 85,
                "wifi_rssi": -55,
                "ha_pairing_status": "paired",
                "sound_output": "Living room",
            }
        )
        original_session = self.integration.async_get_clientsession
        self.integration.async_get_clientsession = lambda hass: Session()
        try:
            asyncio.run(runtime.async_device_command(object(), "status"))
        finally:
            self.integration.async_get_clientsession = original_session

        self.assertEqual(runtime.device_status["firmware"], "3.0.16")
        self.assertEqual(runtime.device_status["battery_percent"], 85)
        self.assertEqual(runtime.device_status["wifi_rssi"], -55)
        self.assertEqual(runtime.device_status["ha_pairing_status"], "paired")
        self.assertEqual(runtime.device_status["sound_output"], "Living room")

    def test_device_info_sparse_refresh_does_not_clear_cached_sensors(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def text(self):
                return (
                    '{"success": true, "firmware": null, "battery_percent": null, '
                    '"wifi_rssi": null, "screen_state": "", "led_state": "", '
                    '"ha_pairing_status": null}'
                )

        class Session:
            def get(self, url, **kwargs):
                return Response()

        entry = types.SimpleNamespace(data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "device-token"
        runtime.device_status.update(
            {
                "local_url": "http://djconnect.local",
                "firmware": "3.0.16",
                "battery_percent": 85,
                "wifi_rssi": -55,
                "screen_state": "on",
                "led_state": "idle",
                "ha_pairing_status": "paired",
            }
        )
        original_session = self.integration.async_get_clientsession
        self.integration.async_get_clientsession = lambda hass: Session()
        try:
            asyncio.run(runtime.async_refresh_device_info(object()))
        finally:
            self.integration.async_get_clientsession = original_session

        self.assertEqual(runtime.device_status["firmware"], "3.0.16")
        self.assertEqual(runtime.device_status["battery_percent"], 85)
        self.assertEqual(runtime.device_status["wifi_rssi"], -55)
        self.assertEqual(runtime.device_status["screen_state"], "on")
        self.assertEqual(runtime.device_status["led_state"], "idle")
        self.assertEqual(runtime.device_status["ha_pairing_status"], "paired")

    def test_service_text_accepts_ui_specific_aliases_and_legacy_text(self) -> None:
        self.assertEqual(
            self.integration._service_text(
                types.SimpleNamespace(data={"command_text": "Speel Pearl Jam"}),
                "default",
                "command_text",
            ),
            "Speel Pearl Jam",
        )
        self.assertEqual(
            self.integration._service_text(
                types.SimpleNamespace(data={"text": "Legacy Pearl Jam"}),
                "default",
                "command_text",
            ),
            "Legacy Pearl Jam",
        )
        self.assertEqual(
            self.integration._service_text(
                types.SimpleNamespace(data={"dj_response_text": "Daar gaan we"}),
                "default",
                "dj_response_text",
            ),
            "Daar gaan we",
        )

    def test_spotify_payload_contains_refresh_token_aliases(self) -> None:
        entry = types.SimpleNamespace(
            data={
                self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                self.const.CONF_SPOTIFY_REFRESH_TOKEN: "refresh-token",
                self.const.CONF_SPOTIFY_MARKET: "NL",
                self.const.CONF_SPOTIFY_SCOPES: "scope-a scope-b",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)

        payload = runtime.spotify_payload()

        self.assertEqual(payload["client_id"], "client-id")
        self.assertEqual(payload["refresh_token"], "refresh-token")
        self.assertEqual(payload["spotify_client_id"], "client-id")
        self.assertEqual(payload["spotify_refresh_token"], "refresh-token")
        self.assertEqual(payload["market"], "NL")
        self.assertEqual(payload["scopes"], ["scope-a", "scope-b"])

    def test_spotify_payload_uses_latest_rotated_refresh_token(self) -> None:
        entry = types.SimpleNamespace(
            data={
                self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                self.const.CONF_SPOTIFY_REFRESH_TOKEN: "old-token",
                self.const.CONF_SPOTIFY_MARKET: "NL",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.latest_spotify_refresh_token = "new-token"

        payload = runtime.get_current_spotify_credentials()

        self.assertEqual(payload["refresh_token"], "new-token")
        self.assertEqual(payload["spotify_refresh_token"], "new-token")

    def test_restore_runtime_restores_persisted_pairing_identity(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_DEVICE_ID: "djconnect-lilygo-90B70990A994",
                self.const.CONF_PAIR_CODE: "981032",
                self.const.CONF_DEVICE_TOKEN: "device-token",
                self.const.CONF_LOCAL_URL: "http://djconnect-lilygo-90B70990A994.local",
                "last_device_status": {
                    "ha_pairing_status": "paired",
                    "battery_percent": 85,
                    "wifi_rssi": -55,
                    "firmware": "3.0.23",
                    "sound_output": "Living room",
                    "screen_state": "on",
                    "led_state": "idle",
                    "last_command": "ik wil pearl jam starten",
                    "last_track": "Pearl Jam",
                },
            },
            options={},
        )
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {}})

        runtime = self.integration._restore_runtime(hass, entry)

        self.assertEqual(runtime.device_token, "device-token")
        self.assertEqual(runtime.pairing_device_id, "djconnect-lilygo-90B70990A994")
        self.assertEqual(runtime.pairing_code, "981032")
        self.assertEqual(runtime.device_status["device_id"], "djconnect-lilygo-90B70990A994")
        self.assertEqual(runtime.device_status["ha_pairing_status"], "paired")
        self.assertEqual(runtime.device_status["battery_percent"], 85)
        self.assertEqual(runtime.device_status["firmware"], "3.0.23")
        self.assertEqual(runtime.device_status["sound_output"], "Living room")
        self.assertEqual(runtime.device_status["last_command"], "ik wil pearl jam starten")
        self.assertEqual(runtime.device_status["last_track"], "Pearl Jam")
        self.assertEqual(
            runtime.device_status["local_url"],
            "http://djconnect-lilygo-90B70990A994.local",
        )

    def test_update_listener_skips_reload_for_spotify_refresh_token_rotation(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                self.const.CONF_SPOTIFY_REFRESH_TOKEN: "old-token",
                self.const.CONF_CLIENT_TYPE: "ios",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        reloads = []

        class ConfigEntries:
            async def async_reload(self, entry_id):
                reloads.append(entry_id)

        hass = types.SimpleNamespace(
            data={
                self.const.DOMAIN: {
                    "entry_reload_signatures": {
                        "entry-1": self.integration._entry_reload_signature(entry)
                    },
                    "entry-1": runtime,
                }
            },
            config_entries=ConfigEntries(),
        )
        entry.data = {
            **entry.data,
            self.const.CONF_SPOTIFY_REFRESH_TOKEN: "new-token",
        }

        asyncio.run(self.integration._async_update_listener(hass, entry))

        self.assertEqual(reloads, [])
        self.assertEqual(runtime.latest_spotify_refresh_token, "new-token")
        self.assertEqual(runtime.config[self.const.CONF_SPOTIFY_REFRESH_TOKEN], "new-token")

    def test_update_listener_skips_reload_for_status_cache_update(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_CLIENT_TYPE: "ios",
                "last_device_status": {"battery_percent": 10},
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        reloads = []

        class ConfigEntries:
            async def async_reload(self, entry_id):
                reloads.append(entry_id)

        hass = types.SimpleNamespace(
            data={
                self.const.DOMAIN: {
                    "entry_reload_signatures": {
                        "entry-1": self.integration._entry_reload_signature(entry)
                    },
                    "entry-1": runtime,
                }
            },
            config_entries=ConfigEntries(),
        )
        entry.data = {
            **entry.data,
            "last_device_status": {"battery_percent": 85, "last_track": "Song"},
        }

        asyncio.run(self.integration._async_update_listener(hass, entry))

        self.assertEqual(reloads, [])
        self.assertEqual(runtime.device_status["battery_percent"], 85)
        self.assertEqual(runtime.device_status["last_track"], "Song")

    def test_update_listener_reloads_for_non_token_config_change(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                self.const.CONF_SPOTIFY_REFRESH_TOKEN: "token",
                self.const.CONF_CLIENT_TYPE: "ios",
            },
            options={},
        )
        reloads = []

        class ConfigEntries:
            async def async_reload(self, entry_id):
                reloads.append(entry_id)

        hass = types.SimpleNamespace(
            data={
                self.const.DOMAIN: {
                    "entry_reload_signatures": {
                        "entry-1": self.integration._entry_reload_signature(entry)
                    },
                }
            },
            config_entries=ConfigEntries(),
        )
        entry.data = {**entry.data, self.const.CONF_SPOTIFY_MARKET: "NL"}

        asyncio.run(self.integration._async_update_listener(hass, entry))

        self.assertEqual(reloads, ["entry-1"])

    def test_runtime_update_caches_last_command_and_track_in_device_status(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)

        runtime.update(
            last_text="ik wil pearl jam starten",
            last_dj_text="Daar is Pearl Jam",
            last_playback={"resolved_media": {"artist": "unused"}},
            last_resolved_media={"artist": "Pearl Jam"},
        )

        self.assertEqual(runtime.device_status["last_command"], "Daar is Pearl Jam")
        self.assertEqual(runtime.device_status["last_dj_text"], "Daar is Pearl Jam")
        self.assertEqual(runtime.device_status["last_track"], "Pearl Jam")

        runtime.update(last_text=None, last_dj_text=None, last_playback={}, last_resolved_media={})

        self.assertEqual(runtime.device_status["last_command"], "Daar is Pearl Jam")
        self.assertEqual(runtime.device_status["last_dj_text"], "Daar is Pearl Jam")
        self.assertEqual(runtime.device_status["last_track"], "Pearl Jam")

    def test_runtime_update_skips_listeners_when_values_are_unchanged(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        calls: list[str] = []
        runtime.listeners.append(lambda: calls.append("called"))

        runtime.update(last_error=None)
        runtime.update(last_error="boom")
        runtime.update(last_error="boom")
        runtime.update()

        self.assertEqual(calls, ["called"])

    def test_runtime_update_notifies_once_for_changed_in_place_device_status(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        calls: list[str] = []
        runtime.listeners.append(lambda: calls.append("called"))

        runtime.update(last_error=None)
        runtime.device_status["ha_pairing_status"] = "paired"
        runtime.update()
        runtime.update()

        self.assertEqual(calls, ["called"])

    def test_runtime_update_ignores_playback_progress_only_changes(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        calls: list[str] = []
        runtime.listeners.append(lambda: calls.append("called"))

        runtime.update(
            last_playback={
                "has_playback": True,
                "is_playing": True,
                "track_name": "Alive",
                "artist_name": "Pearl Jam",
                "progress_ms": 1000,
            }
        )
        runtime.update(
            last_playback={
                "has_playback": True,
                "is_playing": True,
                "track_name": "Alive",
                "artist_name": "Pearl Jam",
                "progress_ms": 2500,
            }
        )

        self.assertEqual(calls, ["called"])

    def test_runtime_update_ignores_nested_device_playback_progress_only_changes(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        calls: list[str] = []
        runtime.listeners.append(lambda: calls.append("called"))

        runtime.device_status["playback"] = {
            "has_playback": True,
            "track_name": "Alive",
            "progress_ms": 1000,
        }
        runtime.update()
        runtime.device_status["playback"]["progress_ms"] = 2000
        runtime.update()

        self.assertEqual(calls, ["called"])

    def test_restore_runtime_ignores_obsolete_pair_code_local_url(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_DEVICE_ID: "djconnect-981032",
                self.const.CONF_DEVICE_TOKEN: "device-token",
                self.const.CONF_LOCAL_URL: "http://djconnect-981032.local",
            },
            options={},
        )
        hass = types.SimpleNamespace(data={self.const.DOMAIN: {}})

        runtime = self.integration._restore_runtime(hass, entry)

        self.assertNotIn("local_url", runtime.device_status)

    def test_initial_provisioning_skips_when_token_already_stored(self) -> None:
        class Runtime:
            device_token = "device-token"
            device_status = {}
            pair_called = False
            last_error = "previous"

            async def pair_device(self, hass):
                self.pair_called = True

            def update(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        runtime = Runtime()

        asyncio.run(self.integration._try_initial_device_provisioning(object(), runtime))

        self.assertFalse(runtime.pair_called)
        self.assertIsNone(runtime.last_error)

    def test_initial_provisioning_pairs_only_when_no_token_exists(self) -> None:
        class Runtime:
            device_token = None
            device_status = {}
            pair_called = False
            last_error = "previous"

            async def pair_device(self, hass):
                self.pair_called = True

            def update(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        runtime = Runtime()

        asyncio.run(self.integration._try_initial_device_provisioning(object(), runtime))

        self.assertTrue(runtime.pair_called)
        self.assertIsNone(runtime.last_error)

    def test_initial_provisioning_skips_when_device_confirmed_pairing(self) -> None:
        class Runtime:
            device_token = "device-token"
            device_status = {"ha_pairing_status": "paired"}
            pair_called = False
            last_error = "previous"

            async def pair_device(self, hass):
                self.pair_called = True

            def update(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        runtime = Runtime()

        asyncio.run(self.integration._try_initial_device_provisioning(object(), runtime))

        self.assertFalse(runtime.pair_called)
        self.assertIsNone(runtime.last_error)

    def test_initial_pairing_defers_unknown_local_url_without_last_error(self) -> None:
        class Runtime:
            device_token = None
            device_status = {}
            last_error = None

            async def pair_device(self, hass):
                raise RuntimeError("DJConnect device local_url is unknown")

            def update(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        runtime = Runtime()

        asyncio.run(self.integration._try_initial_device_provisioning(object(), runtime))

        self.assertEqual(runtime.device_status, {})
        self.assertIsNone(runtime.last_error)

    def test_initial_pairing_logs_empty_exception_type(self) -> None:
        class EmptyError(Exception):
            def __str__(self):
                return ""

        class Runtime:
            device_token = None
            device_status = {}
            last_error = None

            async def pair_device(self, hass):
                raise EmptyError()

            def update(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        runtime = Runtime()

        asyncio.run(self.integration._try_initial_device_provisioning(object(), runtime))

        self.assertIn("EmptyError", runtime.last_error)

    def test_persist_paired_device_updates_config_entry_data(self) -> None:
        class ConfigEntries:
            def __init__(self):
                self.calls = []

            def async_update_entry(self, entry, *, data):
                self.calls.append((entry, data))
                entry.data = data

        entry = types.SimpleNamespace(data={self.const.CONF_PAIR_CODE: "981032"})
        runtime = types.SimpleNamespace(entry=entry)
        config_entries = ConfigEntries()
        hass = types.SimpleNamespace(config_entries=config_entries)

        self.http._persist_paired_device(
            hass,
            runtime,
            "djconnect-lilygo-90B70990A994",
            "http://djconnect-lilygo-90B70990A994.local",
            "device-token",
        )

        self.assertEqual(config_entries.calls[0][1][self.const.CONF_PAIR_CODE], "981032")
        self.assertEqual(
            entry.data[self.const.CONF_DEVICE_ID],
            "djconnect-lilygo-90B70990A994",
        )
        self.assertEqual(entry.data[self.const.CONF_DEVICE_TOKEN], "device-token")
        self.assertEqual(
            entry.data[self.const.CONF_LOCAL_URL],
            "http://djconnect-lilygo-90B70990A994.local",
        )

    def test_pair_device_payload_omits_spotify_credentials(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def text(self):
                return '{"success": true}'

        class PairingInfoResponse(Response):
            async def text(self):
                return (
                    '{"device_id":"djconnect-lilygo-90B70990A994",'
                    '"pair_code":"123456","local_url":"http://djconnect.local"}'
                )

        class Session:
            def __init__(self):
                self.calls = []

            def get(self, url, **kwargs):
                self.calls.append({"method": "GET", "url": url, **kwargs})
                return PairingInfoResponse()

            def post(self, url, **kwargs):
                self.calls.append({"method": "POST", "url": url, **kwargs})
                return Response()

        entry = types.SimpleNamespace(
            data={
                self.const.CONF_DEVICE_ID: "djconnect-123456",
                self.const.CONF_PAIR_CODE: "123456",
                self.const.CONF_DEVICE_LANGUAGE: "nl",
                self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
                self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                self.const.CONF_SPOTIFY_REFRESH_TOKEN: "refresh-token",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.latest_spotify_refresh_token = "rotated-token"
        runtime.device_status["local_url"] = "http://djconnect.local"
        session = Session()
        original_session = self.integration.async_get_clientsession
        self.integration.async_get_clientsession = lambda hass: session
        try:
            hass = types.SimpleNamespace(
                config=types.SimpleNamespace(
                    internal_url="http://homeassistant.local:8123",
                    external_url="https://fallback.example",
                )
            )
            result = asyncio.run(runtime.pair_device(hass))
        finally:
            self.integration.async_get_clientsession = original_session

        self.assertTrue(result["success"])
        self.assertEqual(
            session.calls[0]["url"],
            "http://djconnect.local/api/device/pairing-info",
        )
        payload = session.calls[1]["json"]
        self.assertEqual(payload["device_id"], "djconnect-lilygo-90B70990A994")
        self.assertEqual(payload["client_type"], "esp32")
        self.assertEqual(payload["ha_local_url"], "http://homeassistant.local:8123")
        self.assertNotIn("ha_remote_url", payload)
        self.assertNotIn("ha_url", payload)
        self.assertEqual(payload["device_language"], "nl")
        self.assertEqual(payload["language"], "nl")
        self.assertNotIn("spotify", payload)
        self.assertNotIn("refresh_token", payload)
        self.assertNotIn("spotify_refresh_token", payload)
        self.assertNotIn("client_id", payload)
        self.assertNotIn("spotify_client_id", payload)

    def test_pair_device_uses_reported_macos_client_type_and_local_url(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def text(self):
                return '{"success": true}'

        class PairingInfoResponse(Response):
            async def text(self):
                return (
                    '{"device_id":"djconnect-macos-68B74487726D",'
                    '"firmware":"3.1.0",'
                    '"device_name":"DJConnect Mac",'
                    '"client_type":"macos",'
                    '"local_url":"http://192.168.1.104:60955",'
                    '"pair_code":"555293",'
                    '"platform":"macos"}'
                )

        class Session:
            def __init__(self):
                self.calls = []

            def get(self, url, **kwargs):
                self.calls.append({"method": "GET", "url": url, **kwargs})
                return PairingInfoResponse()

            def post(self, url, **kwargs):
                self.calls.append({"method": "POST", "url": url, **kwargs})
                return Response()

        entry = types.SimpleNamespace(
            data={
                self.const.CONF_DEVICE_ID: "djconnect-555293",
                self.const.CONF_PAIR_CODE: "555293",
                self.const.CONF_DEVICE_TOKEN: "device-token",
                self.const.CONF_CLIENT_TYPE: "esp32",
                self.const.CONF_LOCAL_URL: "http://192.168.1.104:60955",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "device-token"
        session = Session()
        original_session = self.integration.async_get_clientsession
        self.integration.async_get_clientsession = lambda hass: session
        try:
            result = asyncio.run(runtime.pair_device(types.SimpleNamespace()))
        finally:
            self.integration.async_get_clientsession = original_session

        self.assertTrue(result["success"])
        self.assertEqual(
            session.calls[0]["url"],
            "http://192.168.1.104:60955/api/device/pairing-info",
        )
        self.assertEqual(
            session.calls[1]["url"],
            "http://192.168.1.104:60955/api/device/pair",
        )
        payload = session.calls[1]["json"]
        self.assertEqual(payload["device_id"], "djconnect-macos-68B74487726D")
        self.assertEqual(payload["client_type"], "macos")
        self.assertEqual(payload["pair_code"], "555293")
        self.assertNotIn("device_language", payload)
        self.assertNotIn("language", payload)
        self.assertEqual(runtime.device_status["device_id"], "djconnect-macos-68B74487726D")
        self.assertEqual(runtime.device_status["client_type"], "macos")

    def test_ha_url_payload_sends_remote_only_to_remote_capable_clients(self) -> None:
        ha_urls = importlib.import_module("custom_components.djconnect.ha_urls")
        hass = types.SimpleNamespace(
            config=types.SimpleNamespace(external_url="https://fallback.ui.nabu.casa")
        )

        esp_payload = asyncio.run(
            ha_urls.async_ha_url_payload(
                hass,
                {self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa"},
                client_type=self.const.CLIENT_TYPE_ESP32,
            )
        )
        ios_payload = asyncio.run(
            ha_urls.async_ha_url_payload(
                hass,
                {self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa"},
                client_type=self.const.CLIENT_TYPE_IOS,
            )
        )

        self.assertEqual(esp_payload["ha_local_url"], "http://homeassistant.local:8123")
        self.assertNotIn("ha_remote_url", esp_payload)
        self.assertEqual(ios_payload["ha_local_url"], "http://homeassistant.local:8123")
        self.assertEqual(ios_payload["ha_remote_url"], "https://example.ui.nabu.casa")

    def test_ha_local_url_uses_source_ip_fallback(self) -> None:
        helpers = sys.modules["homeassistant.helpers"]
        network = types.ModuleType("homeassistant.helpers.network")

        async def async_get_url(hass, prefer_external=False):
            return "https://example.ui.nabu.casa"

        async def async_get_source_ip(hass):
            return "192.168.1.23"

        network.async_get_url = async_get_url
        network.async_get_source_ip = async_get_source_ip
        previous_attr = getattr(helpers, "network", None)
        previous_module = sys.modules.get("homeassistant.helpers.network")
        helpers.network = network
        sys.modules["homeassistant.helpers.network"] = network
        try:
            ha_urls = importlib.import_module("custom_components.djconnect.ha_urls")
            local_url = asyncio.run(ha_urls.async_ha_local_url(object(), {}))
        finally:
            if previous_attr is None:
                delattr(helpers, "network")
            else:
                helpers.network = previous_attr
            if previous_module is None:
                sys.modules.pop("homeassistant.helpers.network", None)
            else:
                sys.modules["homeassistant.helpers.network"] = previous_module

        self.assertEqual(local_url, "http://192.168.1.23:8123")

    def test_ha_local_url_handles_missing_network_async_get_url(self) -> None:
        helpers = sys.modules["homeassistant.helpers"]
        network = types.ModuleType("homeassistant.helpers.network")
        previous_attr = getattr(helpers, "network", None)
        previous_module = sys.modules.get("homeassistant.helpers.network")
        helpers.network = network
        sys.modules["homeassistant.helpers.network"] = network
        try:
            ha_urls = importlib.import_module("custom_components.djconnect.ha_urls")
            hass = types.SimpleNamespace(
                config=types.SimpleNamespace(internal_url="http://192.168.1.50:8123")
            )
            local_url = asyncio.run(ha_urls.async_ha_local_url(hass, {}))
        finally:
            if previous_attr is None:
                delattr(helpers, "network")
            else:
                helpers.network = previous_attr
            if previous_module is None:
                sys.modules.pop("homeassistant.helpers.network", None)
            else:
                sys.modules["homeassistant.helpers.network"] = previous_module

        self.assertEqual(local_url, "http://192.168.1.50:8123")

    def test_setup_code_pairing_accepts_real_device_id_after_token_sync(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_DEVICE_ID: "djconnect-328823",
                self.const.CONF_DEVICE_TOKEN: "token-new",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-328823"
        runtime.device_status["device_id"] = "djconnect-328823"

        headers = {
            "Authorization": " Bearer token-new ",
            "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
        }
        with self.assertLogs(self.integration._LOGGER, level="DEBUG") as captured:
            allowed = runtime.authorize_device_request(
                headers,
                "djconnect-lilygo-90B70990A994",
            )

        self.assertTrue(allowed)
        self.assertEqual(runtime.pairing_device_id, "djconnect-lilygo-90B70990A994")
        self.assertEqual(runtime.device_status["device_id"], "djconnect-lilygo-90B70990A994")
        logs = "\n".join(captured.output)
        self.assertIn("token_match=True", logs)
        self.assertNotIn("token-new", logs)

    def test_repair_replaces_old_token_for_device_auth(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-lilygo-90B70990A994"
        runtime.device_status["device_id"] = "djconnect-lilygo-90B70990A994"
        headers = {"X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994"}

        self.assertTrue(
            runtime.authorize_device_request(
                {**headers, "Authorization": "Bearer token-new"},
                "djconnect-lilygo-90B70990A994",
            )
        )
        self.assertFalse(
            runtime.authorize_device_request(
                {**headers, "Authorization": "Bearer token-old"},
                "djconnect-lilygo-90B70990A994",
            )
        )

    def test_device_auth_accepts_model_specific_lilygo_id_with_matching_token(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-lilygo-90B70990A994"
        runtime.device_status["device_id"] = "djconnect-lilygo-90B70990A994"
        device_id = "djconnect-lilygo-t-embed-s3-90B70990A994"
        headers = {
            "Authorization": "Bearer token-new",
            "X-DJConnect-Device-ID": device_id,
        }

        self.assertTrue(runtime.authorize_device_request(headers, device_id, "esp32"))
        self.assertEqual(runtime.pairing_device_id, device_id)
        self.assertEqual(runtime.device_status["device_id"], device_id)

    def test_device_auth_accepts_model_specific_box3_id_with_matching_token(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-328823"
        runtime.device_status["device_id"] = "djconnect-328823"
        device_id = "djconnect-esp32-s3-box-3-90B70990A994"
        headers = {
            "Authorization": "Bearer token-new",
            "X-DJConnect-Device-ID": device_id,
        }

        self.assertTrue(runtime.authorize_device_request(headers, device_id, "esp32"))
        self.assertEqual(runtime.pairing_device_id, device_id)
        self.assertEqual(runtime.device_status["device_id"], device_id)

    def test_device_auth_accepts_ios_app_id_with_matching_token(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-328823"
        runtime.device_status["device_id"] = "djconnect-328823"
        device_id = "djconnect-ios-AbC123xYz789"
        headers = {
            "Authorization": "Bearer token-new",
            "X-DJConnect-Device-ID": device_id,
        }

        self.assertTrue(runtime.authorize_device_request(headers, device_id, "ios"))
        self.assertEqual(runtime.pairing_device_id, device_id)
        self.assertEqual(runtime.device_status["device_id"], device_id)
        self.assertIsNone(self.integration._device_id_mdns_fallback_url(device_id))

    def test_device_auth_accepts_macos_app_id_with_matching_token(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-328823"
        runtime.device_status["device_id"] = "djconnect-328823"
        device_id = "djconnect-macos-AbC123xYz789"
        headers = {
            "Authorization": "Bearer token-new",
            "X-DJConnect-Device-ID": device_id,
        }

        self.assertTrue(runtime.authorize_device_request(headers, device_id, "macos"))
        self.assertEqual(runtime.pairing_device_id, device_id)
        self.assertEqual(runtime.device_status["device_id"], device_id)
        self.assertIsNone(self.integration._device_id_mdns_fallback_url(device_id))

    def test_device_auth_accepts_watchos_app_id_with_matching_token(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-328823"
        runtime.device_status["device_id"] = "djconnect-328823"
        device_id = "djconnect-watchos-AbC123xYz789"
        headers = {
            "Authorization": "Bearer token-new",
            "X-DJConnect-Device-ID": device_id,
        }

        self.assertTrue(runtime.authorize_device_request(headers, device_id, "watchos"))
        self.assertEqual(runtime.pairing_device_id, device_id)
        self.assertEqual(runtime.device_status["device_id"], device_id)
        self.assertIsNone(self.integration._device_id_mdns_fallback_url(device_id))

    def test_device_auth_accepts_raspberry_pi_id_with_matching_token(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-328823"
        runtime.device_status["device_id"] = "djconnect-328823"
        device_id = "djconnect-raspberry-pi-AbC123xYz789"
        headers = {
            "Authorization": "Bearer token-new",
            "X-DJConnect-Device-ID": device_id,
        }

        self.assertTrue(
            runtime.authorize_device_request(headers, device_id, "raspberry_pi")
        )
        self.assertEqual(runtime.pairing_device_id, device_id)
        self.assertEqual(runtime.device_status["device_id"], device_id)
        self.assertIsNone(self.integration._device_id_mdns_fallback_url(device_id))

    def test_device_auth_rejects_client_type_device_id_mismatch(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-328823"
        runtime.device_status["device_id"] = "djconnect-328823"
        device_id = "djconnect-ios-AbC123xYz789"
        headers = {
            "Authorization": "Bearer token-new",
            "X-DJConnect-Device-ID": device_id,
        }

        with self.assertLogs(self.integration._LOGGER, level="WARNING") as captured:
            allowed = runtime.authorize_device_request(headers, device_id, "esp32")

        self.assertFalse(allowed)
        self.assertIn("reason=device_id_client_type_mismatch", "\n".join(captured.output))

    def test_device_auth_logs_401_reason_without_token_value(self) -> None:
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-new"
        runtime.pairing_device_id = "djconnect-lilygo-t-embed-s3-90B70990A994"
        runtime.device_status["device_id"] = "djconnect-lilygo-t-embed-s3-90B70990A994"
        request_device = "djconnect-esp32-s3-box-3-90B70990A994"
        headers = {
            "Authorization": "Bearer wrong-token",
            "X-DJConnect-Device-ID": request_device,
        }

        with self.assertLogs(self.integration._LOGGER, level="WARNING") as captured:
            allowed = runtime.authorize_device_request(headers, request_device, "esp32")

        self.assertFalse(allowed)
        logs = "\n".join(captured.output)
        self.assertIn("DJConnect client request rejected", logs)
        self.assertIn("reason=bearer_token_mismatch_for_entry", logs)
        self.assertIn(f"received_device_id={request_device}", logs)
        self.assertIn("client_type=esp32", logs)
        self.assertIn("bearer_token_present=True", logs)
        self.assertNotIn("ESP request rejected", logs)
        self.assertNotIn("wrong-token", logs)
        self.assertNotIn("token-new", logs)

    def test_status_command_and_voice_share_same_runtime_token_lookup(self) -> None:
        const = self.const
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                const.CONF_DEVICE_ID: "djconnect-328823",
                const.CONF_DEVICE_TOKEN: "token-shared",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "token-shared"
        runtime.pairing_device_id = "djconnect-328823"
        runtime.device_status["device_id"] = "djconnect-328823"

        class ConfigEntries:
            def async_update_entry(self, entry, *, data):
                entry.data = data

        hass = types.SimpleNamespace(
            data={const.DOMAIN: {entry.entry_id: runtime, "runtime": runtime}},
            config_entries=ConfigEntries(),
        )
        headers = {
            "Authorization": "Bearer token-shared",
            "X-DJConnect-Device-ID": "djconnect-lilygo-90B70990A994",
            "Content-Type": "application/json",
        }

        class StatusRequest:
            def __init__(self):
                self.app = {"hass": hass}
                self.headers = headers

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                }

        async def command_handler(hass, runtime, command, value=None, *, play=None):
            return {"success": True, "playback": {"has_playback": False}}

        async def dj_response_handler(hass, runtime, text):
            return {"audio_url_value": ""}

        class CommandRequest:
            def __init__(self):
                self.app = {"hass": hass}
                self.headers = headers

            async def json(self):
                return {
                    "device_id": "djconnect-lilygo-90B70990A994",
                    "client_type": "esp32",
                    "command": "status",
                }

        class VoiceRequest:
            def __init__(self):
                self.app = {"hass": hass}
                self.headers = headers

            async def json(self):
                return {"text": "test"}

        original_command = self.http.run_music_command
        original_dj_response = self.http.async_send_dj_response_best_effort
        self.http.run_music_command = command_handler
        self.http.async_send_dj_response_best_effort = dj_response_handler
        try:
            status_response = asyncio.run(self.http.DJConnectStatusView(None).post(StatusRequest()))
            command_response = asyncio.run(self.http.DJConnectCommandView(None).post(CommandRequest()))
            voice_response = asyncio.run(self.http.DJConnectVoiceView(None).post(VoiceRequest()))
        finally:
            self.http.run_music_command = original_command
            self.http.async_send_dj_response_best_effort = original_dj_response

        self.assertEqual(status_response["status_code"], 200)
        self.assertEqual(command_response["status_code"], 200)
        self.assertEqual(voice_response["status_code"], 200)

    def test_runtime_lookup_prefers_token_over_stale_duplicate_device_id(self) -> None:
        const = self.const
        stale = types.SimpleNamespace(
            device_token="old-token",
            pairing_device_id="djconnect-lilygo-90B70990A994",
            device_status={"device_id": "djconnect-lilygo-90B70990A994"},
            config={const.CONF_DEVICE_ID: "djconnect-lilygo-90B70990A994"},
            authorize_device_request=lambda headers, body_device_id=None: False,
        )
        active = types.SimpleNamespace(
            device_token="new-token",
            pairing_device_id="djconnect-lilygo-90B70990A994",
            device_status={"device_id": "djconnect-lilygo-90B70990A994"},
            config={const.CONF_DEVICE_ID: "djconnect-lilygo-90B70990A994"},
            authorize_device_request=lambda headers, body_device_id=None: True,
        )
        hass = types.SimpleNamespace(
            data={
                const.DOMAIN: {
                    "stale-entry": stale,
                    "active-entry": active,
                    "runtime": active,
                }
            }
        )

        resolved = self.http._runtime(
            hass,
            "djconnect-lilygo-90B70990A994",
            {"Authorization": "Bearer new-token"},
        )

        self.assertIs(resolved, active)

    @unittest.skipUnless(sys.platform == "darwin", "log-capture stale auth contract is covered on macOS")
    def test_runtime_lookup_rejects_stale_device_without_fallback(self) -> None:
        const = self.const
        self.http._last_stale_auth_log.clear()
        active = types.SimpleNamespace(
            device_token="active-token",
            pairing_device_id="djconnect-ios-ACTIVE123456",
            device_status={"device_id": "djconnect-ios-ACTIVE123456"},
            config={const.CONF_DEVICE_ID: "djconnect-ios-ACTIVE123456"},
            authorize_device_request=lambda headers, body_device_id=None: True,
        )
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {"active-entry": active, "runtime": active}}
        )

        with self.assertLogs(self.http._LOGGER, level="WARNING") as captured:
            resolved = self.http._runtime(
                hass,
                "djconnect-macos-STALE123456",
                {"Authorization": "Bearer old-token"},
            )

        self.assertIsNone(resolved)
        self.assertIn("no runtime matched bearer token", "\n".join(captured.output))

    @unittest.skipUnless(sys.platform == "darwin", "log-capture throttle contract is covered on macOS")
    def test_runtime_lookup_throttles_repeated_stale_token_warnings(self) -> None:
        const = self.const
        self.http._last_stale_auth_log.clear()
        active = types.SimpleNamespace(
            device_token="active-token",
            pairing_device_id="djconnect-ios-ACTIVE123456",
            device_status={"device_id": "djconnect-ios-ACTIVE123456"},
            config={const.CONF_DEVICE_ID: "djconnect-ios-ACTIVE123456"},
            authorize_device_request=lambda headers, body_device_id=None: True,
        )
        hass = types.SimpleNamespace(
            data={const.DOMAIN: {"active-entry": active, "runtime": active}}
        )

        with self.assertLogs(self.http._LOGGER, level="WARNING") as captured:
            first = self.http._runtime(
                hass,
                None,
                {"Authorization": "Bearer old-token"},
            )
            second = self.http._runtime(
                hass,
                None,
                {"Authorization": "Bearer old-token"},
            )

        self.assertIsNone(first)
        self.assertIsNone(second)
        logs = "\n".join(captured.output)
        self.assertEqual(logs.count("no runtime matched bearer token"), 1)

    def test_unload_last_entry_clears_memory_and_history_managers(self) -> None:
        const = self.const
        entry = types.SimpleNamespace(entry_id="entry-1", data={}, options={})

        class Runtime:
            def __init__(self, runtime_entry):
                self.entry = runtime_entry

            def client_type(self):
                return const.CLIENT_TYPE_IOS

            def authorize_device_request(self):
                return True

        class ConfigEntries:
            async def async_unload_platforms(self, unloaded_entry, platforms):
                self.platforms = platforms
                return True

        class Memory:
            cleared = False

            async def async_clear(self):
                self.cleared = True

        class History:
            cleared = False

            async def async_clear_all(self):
                self.cleared = True

        memory = Memory()
        history = History()
        runtime = Runtime(entry)
        hass = types.SimpleNamespace(
            config_entries=ConfigEntries(),
            data={
                const.DOMAIN: {
                    entry.entry_id: runtime,
                    "runtime": runtime,
                    "memory_manager": memory,
                    "ask_dj_history_manager": history,
                }
            },
        )

        unloaded = asyncio.run(self.integration.async_unload_entry(hass, entry))

        self.assertTrue(unloaded)
        self.assertTrue(memory.cleared)
        self.assertTrue(history.cleared)
        self.assertNotIn("memory_manager", hass.data[const.DOMAIN])
        self.assertNotIn("ask_dj_history_manager", hass.data[const.DOMAIN])

    def test_start_ota_payload_uses_manifest_device_target(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def text(self):
                return '{"success": true}'

        class Session:
            def __init__(self):
                self.calls = []

            def post(self, url, **kwargs):
                self.calls.append({"url": url, **kwargs})
                return Response()

        entry = types.SimpleNamespace(
            data={
                self.const.CONF_DEVICE_ID: "djconnect-lilygo-90B70990A994",
                self.const.CONF_DEVICE_TOKEN: "device-token",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "device-token"
        runtime.device_status["local_url"] = "http://djconnect-lilygo-90B70990A994.local"
        release = types.SimpleNamespace(
            version="3.0.6",
            firmware_url="https://example/djconnect-lilygo-t-embed-s3-v3.0.6.bin",
            sha256="a" * 64,
            device="lilygo-t-embed-s3",
            firmware_asset="djconnect-lilygo-t-embed-s3-v3.0.6.bin",
        )
        session = Session()
        original_session = self.integration.async_get_clientsession
        self.integration.async_get_clientsession = lambda hass: session
        try:
            asyncio.run(runtime.start_ota(object(), release))
        finally:
            self.integration.async_get_clientsession = original_session

        call = session.calls[0]
        self.assertEqual(call["url"], "http://djconnect-lilygo-90B70990A994.local/api/device/ota")
        self.assertEqual(call["headers"]["Authorization"], "Bearer device-token")
        self.assertEqual(
            call["json"],
            {
                "version": "3.0.6",
                "url": "https://example/djconnect-lilygo-t-embed-s3-v3.0.6.bin",
                "sha256": "a" * 64,
                "device": "lilygo-t-embed-s3",
                "asset": "djconnect-lilygo-t-embed-s3-v3.0.6.bin",
            },
        )

    def test_start_ota_falls_back_to_cached_status_ip(self) -> None:
        class Response:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def text(self):
                return '{"success": true}'

        class Session:
            def __init__(self):
                self.calls = []

            def post(self, url, **kwargs):
                self.calls.append({"url": url, **kwargs})
                if ".local" in url:
                    raise OSError("MDNS lookup failed")
                return Response()

        entry = types.SimpleNamespace(
            data={
                self.const.CONF_DEVICE_ID: "djconnect-lilygo-t-embed-s3-90B70990A994",
                self.const.CONF_DEVICE_TOKEN: "device-token",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_token = "device-token"
        runtime.device_status["local_url"] = "http://djconnect-lilygo-t-embed-s3-90B70990A994.local"
        runtime.device_status["wifi"] = {"ip": "192.168.1.109"}
        release = types.SimpleNamespace(
            version="3.1.32",
            firmware_url="https://example/djconnect-lilygo-t-embed-s3-v3.1.32.bin",
            sha256="a" * 64,
            device="lilygo-t-embed-s3",
            firmware_asset="djconnect-lilygo-t-embed-s3-v3.1.32.bin",
        )
        session = Session()
        original_session = self.integration.async_get_clientsession
        self.integration.async_get_clientsession = lambda hass: session
        try:
            asyncio.run(runtime.start_ota(object(), release))
        finally:
            self.integration.async_get_clientsession = original_session

        self.assertEqual(
            [call["url"] for call in session.calls],
            [
                "http://192.168.1.109/api/device/ota",
            ],
        )
        self.assertEqual(runtime.device_status["local_url"], "http://192.168.1.109")

    def test_start_ota_preserves_wrong_device_target_error(self) -> None:
        class Response:
            status = 400

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return None

            async def text(self):
                return "Wrong device target"

        class Session:
            def post(self, url, **kwargs):
                return Response()

        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-lilygo-90B70990A994"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_status["local_url"] = "http://djconnect-lilygo-90B70990A994.local"
        release = types.SimpleNamespace(
            version="3.0.6",
            firmware_url="https://example/djconnect-lilygo-t-embed-s3-v3.0.6.bin",
            sha256="a" * 64,
            device="djconnect-device",
            firmware_asset="djconnect-lilygo-t-embed-s3-v3.0.6.bin",
        )
        original_session = self.integration.async_get_clientsession
        self.integration.async_get_clientsession = lambda hass: Session()
        try:
            with self.assertRaisesRegex(RuntimeError, "Wrong device target"):
                asyncio.run(runtime.start_ota(object(), release))
        finally:
            self.integration.async_get_clientsession = original_session

        self.assertIn("Wrong device target", runtime.ota_last_error)

    def test_url_from_service_info_matches_device_id(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-123456"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        info = types.SimpleNamespace(
            name="djconnect-123456._djconnect._tcp.local.",
            server="djconnect-123456.local.",
            port=8080,
        )

        url = self.integration._url_from_service_info(info, runtime)

        self.assertEqual(url, "http://djconnect-123456.local:8080")

    def test_async_get_mdns_service_info_uses_ha_zeroconf_getter(self) -> None:
        class AsyncZeroconf:
            async def async_get_service_info(self, service_type, service_name):
                return types.SimpleNamespace(
                    name=service_name,
                    server="djconnect-lilygo-90B70990A994.local.",
                    port=80,
                )

        info = asyncio.run(
            self.integration._async_get_mdns_service_info(
                AsyncZeroconf(),
                "DJConnect 90B70990A994._djconnect._tcp.local.",
            )
        )

        self.assertEqual(info.server, "djconnect-lilygo-90B70990A994.local.")

    def test_url_from_service_info_matches_friendly_mdns_name(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-123456"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        info = types.SimpleNamespace(
            name="DJConnect 123456._djconnect._tcp.local.",
            server="djconnect-123456.local.",
            port=80,
        )

        url = self.integration._url_from_service_info(info, runtime)

        self.assertEqual(url, "http://djconnect-123456.local")

    def test_url_from_service_info_ignores_other_devices(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-123456"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        info = types.SimpleNamespace(
            name="djconnect-other._djconnect._tcp.local.",
            server="djconnect-other.local.",
            port=80,
        )

        self.assertIsNone(self.integration._url_from_service_info(info, runtime))

    def test_mdns_service_name_candidates_include_device_and_friendly_names(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-123456"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)

        names = self.integration._mdns_service_name_candidates(runtime)

        self.assertIn("djconnect-123456._djconnect._tcp.local.", names)
        self.assertIn("DJConnect 123456._djconnect._tcp.local.", names)

    def test_device_local_url_falls_back_to_mdns_hostname(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-lilygo-90B70990A994"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)

        url = asyncio.run(runtime.async_device_local_url(hass=object()))

        self.assertEqual(url, "http://djconnect-lilygo-90B70990A994.local")

    def test_device_local_url_does_not_fallback_to_pair_code_hostname(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-981032"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)

        url = asyncio.run(runtime.async_device_local_url(hass=object()))

        self.assertIsNone(url)

    def test_device_local_url_ignores_stored_pair_code_hostname(self) -> None:
        entry = types.SimpleNamespace(
            data={
                self.const.CONF_DEVICE_ID: "djconnect-981032",
                self.const.CONF_LOCAL_URL: "http://djconnect-981032.local",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)

        url = asyncio.run(runtime.async_device_local_url(hass=object()))

        self.assertIsNone(url)

    def test_device_local_url_uses_mdns_browse_for_pair_code_entry(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-981032"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)

        async def discover(hass, runtime):
            return "http://djconnect-lilygo-90B70990A994.local"

        original_discover = self.integration.async_discover_device_url
        self.integration.async_discover_device_url = discover
        try:
            url = asyncio.run(runtime.async_device_local_url(hass=object()))
        finally:
            self.integration.async_discover_device_url = original_discover

        self.assertEqual(url, "http://djconnect-lilygo-90B70990A994.local")

    def test_device_local_url_falls_back_to_cached_wifi_ip_when_mdns_unavailable(self) -> None:
        entry = types.SimpleNamespace(
            data={
                self.const.CONF_DEVICE_ID: "djconnect-lilygo-t-embed-s3-90B70990A994",
                self.const.CONF_LOCAL_URL: "http://djconnect-lilygo-t-embed-s3-90B70990A994.local:61234",
            },
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_status["wifi"] = {"ip": "192.168.1.109"}

        async def discover(hass, runtime):
            return None

        original_discover = self.integration.async_discover_device_url
        self.integration.async_discover_device_url = discover
        try:
            url = asyncio.run(runtime.async_device_local_url(hass=object()))
        finally:
            self.integration.async_discover_device_url = original_discover

        self.assertEqual(url, "http://192.168.1.109:61234")
        self.assertEqual(runtime.device_status["local_url"], "http://192.168.1.109:61234")

    def test_device_local_url_falls_back_to_cached_status_ip_without_stored_url(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_DEVICE_ID: "djconnect-lilygo-t-embed-s3-90B70990A994"},
            options={},
        )
        runtime = self.integration.DJConnectRuntime(entry=entry)
        runtime.device_status["network"] = {"ip_address": "192.168.1.110", "api_port": 61234}

        async def discover(hass, runtime):
            return None

        original_discover = self.integration.async_discover_device_url
        self.integration.async_discover_device_url = discover
        try:
            url = asyncio.run(runtime.async_device_local_url(hass=object()))
        finally:
            self.integration.async_discover_device_url = original_discover

        self.assertEqual(url, "http://192.168.1.110:61234")

    def test_tts_audio_store_returns_wav_and_unknown_404(self) -> None:
        hass = types.SimpleNamespace(data={})

        token = self.dj_response.store_tts_audio(hass, b"RIFFxxxxWAVEdata", 120)

        status, audio = self.dj_response.get_tts_audio(hass, token)
        self.assertEqual(status, 200)
        self.assertEqual(audio.data, b"RIFFxxxxWAVEdata")
        self.assertEqual(audio.content_type, "audio/wav")
        self.assertEqual(audio.extension, "wav")
        status, audio = self.dj_response.get_tts_audio(hass, "missing")
        self.assertEqual(status, 404)
        self.assertIsNone(audio)

    def test_tts_audio_store_uses_unique_tokens_and_default_one_hour_ttl(self) -> None:
        hass = types.SimpleNamespace(data={})

        first = self.dj_response.store_tts_audio(hass, b"first")
        second = self.dj_response.store_tts_audio(hass, b"second")
        store = self.dj_response._store(hass)

        self.assertNotEqual(first, second)
        self.assertEqual(store[first].data, b"first")
        self.assertEqual(store[second].data, b"second")
        self.assertGreaterEqual(
            store[first].expires_at - time.time(),
            self.const.DEFAULT_DJ_RESPONSE_TTL_SECONDS - 5,
        )

    def test_tts_audio_store_expired_returns_410(self) -> None:
        hass = types.SimpleNamespace(data={})

        token = self.dj_response.store_tts_audio(hass, b"RIFFxxxxWAVEdata", 1)
        self.dj_response._store(hass)[token].expires_at = 0

        status, audio = self.dj_response.get_tts_audio(hass, token)
        self.assertEqual(status, 410)
        self.assertIsNone(audio)

    def test_default_tts_engine_omits_engine_argument(self) -> None:
        calls = []
        pipeline_module_name = "homeassistant.components.assist_pipeline.pipeline"
        original_pipeline_module = sys.modules.pop(pipeline_module_name, None)

        class TtsModule:
            @staticmethod
            def generate_media_source_id(hass, **kwargs):
                calls.append(kwargs)
                return "media-source://tts/default"

        try:
            result = asyncio.run(
                self.tts._async_generate_tts_media_source_id(
                    TtsModule,
                    object(),
                    "Daar gaan we.",
                    {
                        self.const.CONF_TTS_ENGINE: "",
                        self.const.CONF_TTS_LANGUAGE: "nl-NL",
                    },
                )
            )
        finally:
            if original_pipeline_module is not None:
                sys.modules[pipeline_module_name] = original_pipeline_module

        self.assertEqual(result, "media-source://tts/default")
        self.assertEqual(calls[0], {"message": "Daar gaan we."})

    def test_tts_media_source_supports_positional_generator_signature(self) -> None:
        calls = []
        pipeline_module_name = "homeassistant.components.assist_pipeline.pipeline"
        original_pipeline_module = sys.modules.pop(pipeline_module_name, None)

        class TtsModule:
            @staticmethod
            def generate_media_source_id(
                hass,
                message,
                engine=None,
                language=None,
                options=None,
            ):
                calls.append(
                    {
                        "message": message,
                        "engine": engine,
                        "language": language,
                        "options": options,
                    }
                )
                return "media-source://tts/positional"

        try:
            result = asyncio.run(
                self.tts._async_generate_tts_media_source_id(
                    TtsModule,
                    object(),
                    "Daar gaan we.",
                    {},
                )
            )
        finally:
            if original_pipeline_module is not None:
                sys.modules[pipeline_module_name] = original_pipeline_module

        self.assertEqual(result, "media-source://tts/positional")
        self.assertEqual(
            calls[0],
            {
                "message": "Daar gaan we.",
                "engine": None,
                "language": None,
                "options": None,
            },
        )

    def test_tts_media_source_supports_async_positional_pipeline_signature(self) -> None:
        calls = []
        pipeline_module_name = "homeassistant.components.assist_pipeline.pipeline"
        original_pipeline_module = sys.modules.get(pipeline_module_name)
        pipeline_module = types.ModuleType(pipeline_module_name)
        pipeline_module.async_get_pipelines = lambda hass: [
            types.SimpleNamespace(
                id="living-room",
                tts_engine="cloud",
                tts_language="nl-NL",
                tts_voice="Fenna",
            )
        ]
        sys.modules[pipeline_module_name] = pipeline_module

        class TtsModule:
            @staticmethod
            async def async_generate_media_source_id(
                hass,
                message,
                engine=None,
                language=None,
                options=None,
            ):
                calls.append(
                    {
                        "message": message,
                        "engine": engine,
                        "language": language,
                        "options": options,
                    }
                )
                return "media-source://tts/async-positional"

        try:
            result = asyncio.run(
                self.tts._async_generate_tts_media_source_id(
                    TtsModule,
                    object(),
                    "Daar gaan we.",
                    {self.const.CONF_ASSIST_PIPELINE_ID: "living-room"},
                )
            )
        finally:
            if original_pipeline_module is None:
                sys.modules.pop(pipeline_module_name, None)
            else:
                sys.modules[pipeline_module_name] = original_pipeline_module

        self.assertEqual(result, "media-source://tts/async-positional")
        self.assertEqual(
            calls[0],
            {
                "message": "Daar gaan we.",
                "engine": "cloud",
                "language": "nl-NL",
                "options": {"voice": "Fenna"},
            },
        )

    def test_tts_text_candidates_add_english_title_language_hints(self) -> None:
        text = (
            'Je luistert naar Nirvana met het nummer "Heart-Shaped Box" '
            'van het album "In Utero (Deluxe Edition)".'
        )

        plain, ssml = self.tts._tts_text_candidates(text)

        self.assertEqual(plain, text)
        self.assertTrue(ssml.startswith("<speak>"))
        self.assertIn('<lang xml:lang="en-US">Heart-Shaped Box</lang>', ssml)
        self.assertIn('<lang xml:lang="en-US">In Utero (Deluxe Edition)</lang>', ssml)

    def test_tts_media_source_tries_plain_before_ssml_for_english_titles(self) -> None:
        calls = []
        pipeline_module_name = "homeassistant.components.assist_pipeline.pipeline"
        original_pipeline_module = sys.modules.pop(pipeline_module_name, None)

        class TtsModule:
            @staticmethod
            def generate_media_source_id(hass, **kwargs):
                calls.append(kwargs)
                return "media-source://tts/plain"

        text = 'Je luistert naar "Heart-Shaped Box".'
        try:
            result = asyncio.run(
                self.tts._async_generate_tts_media_source_id(
                    TtsModule,
                    object(),
                    text,
                    {},
                )
            )
        finally:
            if original_pipeline_module is not None:
                sys.modules[pipeline_module_name] = original_pipeline_module

        self.assertEqual(result, "media-source://tts/plain")
        self.assertEqual(calls[0], {"message": text})

    def test_tts_media_source_can_fallback_to_ssml_when_plain_fails(self) -> None:
        calls = []
        pipeline_module_name = "homeassistant.components.assist_pipeline.pipeline"
        original_pipeline_module = sys.modules.pop(pipeline_module_name, None)

        class TtsModule:
            @staticmethod
            def generate_media_source_id(hass, **kwargs):
                calls.append(kwargs)
                if str(kwargs.get("message") or "") == 'Je luistert naar "Heart-Shaped Box".':
                    return None
                return "media-source://tts/ssml"

        text = 'Je luistert naar "Heart-Shaped Box".'
        try:
            result = asyncio.run(
                self.tts._async_generate_tts_media_source_id(
                    TtsModule,
                    object(),
                    text,
                    {},
                )
            )
        finally:
            if original_pipeline_module is not None:
                sys.modules[pipeline_module_name] = original_pipeline_module

        self.assertEqual(result, "media-source://tts/ssml")
        self.assertEqual(calls[0], {"message": text})
        self.assertTrue(calls[1]["message"].startswith("<speak>"))


if __name__ == "__main__":
    unittest.main()
