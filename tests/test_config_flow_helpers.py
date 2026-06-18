from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]


def install_homeassistant_stubs() -> None:
    homeassistant = sys.modules.setdefault(
        "homeassistant",
        types.ModuleType("homeassistant"),
    )
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    core = sys.modules.setdefault(
        "homeassistant.core",
        types.ModuleType("homeassistant.core"),
    )
    data_entry_flow = sys.modules.setdefault(
        "homeassistant.data_entry_flow",
        types.ModuleType("homeassistant.data_entry_flow"),
    )
    voluptuous = sys.modules.setdefault("voluptuous", types.ModuleType("voluptuous"))
    aiohttp = sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_external_step(self, **kwargs):
            return {"type": "external", **kwargs}

        def async_external_step_done(self, **kwargs):
            return {"type": "external_done", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

    class OptionsFlow:
        @property
        def config_entry(self):
            return None

        def async_external_step(self, **kwargs):
            return {"type": "external", **kwargs}

        def async_external_step_done(self, **kwargs):
            return {"type": "external_done", **kwargs}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

    class ConfigEntry:
        pass

    class Schema:
        def __init__(self, schema):
            self.schema = schema

    class Marker:
        def __init__(self, key, default=None):
            self.key = key
            self.default = default

    class ClientTimeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.ConfigEntry = ConfigEntry
    core.callback = lambda func: func
    core.HomeAssistant = object
    data_entry_flow.FlowResult = dict
    voluptuous.Schema = Schema
    voluptuous.Required = Marker
    voluptuous.Optional = Marker
    voluptuous.In = lambda values: values
    aiohttp.ClientTimeout = ClientTimeout

    homeassistant.config_entries = config_entries
    helpers = sys.modules.setdefault(
        "homeassistant.helpers",
        types.ModuleType("homeassistant.helpers"),
    )
    network = sys.modules.setdefault(
        "homeassistant.helpers.network",
        types.ModuleType("homeassistant.helpers.network"),
    )
    selector = sys.modules.setdefault(
        "homeassistant.helpers.selector",
        types.ModuleType("homeassistant.helpers.selector"),
    )
    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
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
    cloud = sys.modules.setdefault(
        "homeassistant.components.cloud",
        types.ModuleType("homeassistant.components.cloud"),
    )
    aiohttp_client.async_get_clientsession = lambda hass: None
    network.async_get_url = lambda *args, **kwargs: ""
    cloud.async_remote_ui_url = lambda hass: ""
    helpers.network = network
    helpers.selector = selector
    assist_pipeline.async_get_pipelines = lambda hass: [
        types.SimpleNamespace(
            id="default",
            name="Default",
            stt_engine="stt.mock",
            tts_engine="tts.mock",
        )
    ]
    assist_pkg.pipeline = assist_pipeline
    components.assist_pipeline = assist_pkg
    components.cloud = cloud

    class TextSelectorConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class TextSelector:
        def __init__(self, config):
            self.config = config

    class SelectSelectorConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class SelectSelector:
        def __init__(self, config):
            self.config = config

    class SelectOptionDict(dict):
        def __init__(self, *, value, label):
            super().__init__(value=value, label=label)

    selector.TextSelectorConfig = TextSelectorConfig
    selector.TextSelector = TextSelector
    selector.SelectSelectorConfig = SelectSelectorConfig
    selector.SelectSelector = SelectSelector
    selector.SelectOptionDict = SelectOptionDict
    entity_registry = sys.modules.setdefault(
        "homeassistant.helpers.entity_registry",
        types.ModuleType("homeassistant.helpers.entity_registry"),
    )
    entity_registry.async_get = lambda hass: getattr(hass, "entity_registry", None)
    helpers.entity_registry = entity_registry

    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    package.register_http_views = lambda hass: None
    sys.modules["custom_components.djconnect"] = package


class ConfigFlowHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_homeassistant_stubs()
        cls.config_flow = importlib.import_module("custom_components.djconnect.config_flow")
        cls.const = importlib.import_module("custom_components.djconnect.const")

    def test_https_url_validation_requires_scheme_and_host(self) -> None:
        self.assertTrue(self.config_flow._is_https_url("https://example.ui.nabu.casa"))
        self.assertFalse(self.config_flow._is_https_url("http://example.ui.nabu.casa"))
        self.assertFalse(self.config_flow._is_https_url("https://"))
        self.assertFalse(self.config_flow._is_https_url("example.ui.nabu.casa"))

    def test_options_with_current_preserves_existing_free_text_value(self) -> None:
        options = self.config_flow._options_with_current({"stable": "Stable"}, "nightly")

        self.assertEqual(options["stable"], "Stable")
        self.assertEqual(options["nightly"], "nightly")

    def test_voice_schema_preserves_explicit_default_values(self) -> None:
        hass = types.SimpleNamespace(states=None)
        defaults = self.config_flow._voice_defaults(
            {
            },
            preserve_empty=True,
        )

        schema = asyncio.run(self.config_flow._voice_schema(hass, defaults))
        marker_defaults = {marker.key: marker.default for marker in schema.schema}

        self.assertNotIn(self.const.CONF_STT_ENGINE, marker_defaults)
        self.assertNotIn(self.const.CONF_TTS_ENGINE, marker_defaults)
        self.assertNotIn(self.const.CONF_TTS_VOICE, marker_defaults)

    def test_voice_schema_hides_tts_settings(self) -> None:
        hass = types.SimpleNamespace(states=None)
        schema = asyncio.run(
            self.config_flow._voice_schema(
                hass,
                self.config_flow._voice_defaults(),
            )
        )
        keys = {marker.key for marker in schema.schema}

        self.assertNotIn(self.const.CONF_TTS_ENGINE, keys)
        self.assertNotIn(self.const.CONF_TTS_LANGUAGE, keys)
        self.assertNotIn(self.const.CONF_TTS_VOICE, keys)

    def test_voice_schema_uses_multiline_dj_response_prompt(self) -> None:
        hass = types.SimpleNamespace(states=None)
        schema = asyncio.run(
            self.config_flow._voice_schema(
                hass,
                self.config_flow._voice_defaults(),
            )
        )
        validators = {
            marker.key: validator
            for marker, validator in schema.schema.items()
        }
        prompt_selector = validators[self.const.CONF_DJ_RESPONSE_PROMPT]

        self.assertTrue(prompt_selector.config.kwargs["multiline"])

    def test_voice_schema_exposes_dj_response_prompt_preset(self) -> None:
        hass = types.SimpleNamespace(states=None)
        schema = asyncio.run(
            self.config_flow._voice_schema(
                hass,
                self.config_flow._voice_defaults(),
            )
        )
        marker_defaults = {marker.key: marker.default for marker in schema.schema}
        validators = {
            marker.key: validator
            for marker, validator in schema.schema.items()
        }

        self.assertEqual(
            marker_defaults[self.const.CONF_DJ_RESPONSE_PROMPT_PRESET],
            self.const.DJ_RESPONSE_PROMPT_PRESET_WARM,
        )
        preset_selector = validators[self.const.CONF_DJ_RESPONSE_PROMPT_PRESET]
        preset_values = [
            option["value"]
            for option in preset_selector.config.kwargs["options"]
        ]
        self.assertEqual(preset_values, self.const.DJ_RESPONSE_PROMPT_PRESETS)

    def test_voice_defaults_apply_dj_response_prompt_preset(self) -> None:
        defaults = self.config_flow._voice_defaults(
            {
                self.const.CONF_DJ_RESPONSE_PROMPT_PRESET: (
                    self.const.DJ_RESPONSE_PROMPT_PRESET_HUMOR
                ),
                self.const.CONF_DJ_RESPONSE_PROMPT: "Custom text",
            }
        )

        self.assertEqual(
            defaults[self.const.CONF_DJ_RESPONSE_PROMPT],
            self.const.DJ_RESPONSE_PROMPT_TEXTS[
                self.const.DJ_RESPONSE_PROMPT_PRESET_HUMOR
            ],
        )

    def test_voice_defaults_preserve_custom_dj_response_prompt(self) -> None:
        defaults = self.config_flow._voice_defaults(
            {
                self.const.CONF_DJ_RESPONSE_PROMPT_PRESET: (
                    self.const.DJ_RESPONSE_PROMPT_PRESET_CUSTOM
                ),
                self.const.CONF_DJ_RESPONSE_PROMPT: "Maak het kort en eigen.",
            }
        )

        self.assertEqual(
            defaults[self.const.CONF_DJ_RESPONSE_PROMPT],
            "Maak het kort en eigen.",
        )

    def test_default_dj_response_prompt_is_multiline_guidance(self) -> None:
        prompt = self.const.DEFAULT_DJ_RESPONSE_PROMPT

        self.assertNotIn("Gebruik deze DJ response prompt", prompt)
        self.assertNotIn("stijl-/inhoudsinstructie", prompt)
        self.assertIn("Noem de artiest, het album en het nummer.", prompt)
        self.assertIn("Geef een leuk feitje over de artiest.", prompt)
        self.assertIn("Klink warm en persoonlijk.", prompt)
        self.assertEqual(prompt.count("\n"), 2)

    def test_voice_schema_hides_internal_compatibility_and_ota_fields(self) -> None:
        hass = types.SimpleNamespace(states=None)

        schema = asyncio.run(
            self.config_flow._voice_schema(
                hass,
                self.config_flow._voice_defaults(),
            )
        )

        keys = {marker.key for marker in schema.schema}
        internal_only = {
            self.const.CONF_MAX_AUDIO_BYTES,
            self.const.CONF_ALLOW_OTA_ON_BATTERY,
            self.const.CONF_MIN_BATTERY_FOR_OTA,
            self.const.CONF_DJ_RESPONSE_TTL_SECONDS,
        }

        self.assertTrue(internal_only.isdisjoint(keys))
        self.assertNotIn("firmware_repo", keys)
        self.assertNotIn("firmware_device", keys)
        self.assertNotIn(self.const.CONF_STT_ENGINE, keys)
        self.assertNotIn(self.const.CONF_TTS_ENGINE, keys)
        self.assertNotIn(self.const.CONF_TTS_LANGUAGE, keys)
        self.assertNotIn(self.const.CONF_TTS_VOICE, keys)
        self.assertNotIn(self.const.CONF_SPOTIFY_SOURCE, keys)
        self.assertNotIn(self.const.CONF_LIKED_PROXY, keys)
        self.assertNotIn("show_advanced_options", keys)
        self.assertIn(self.const.CONF_FIRMWARE_CHANNEL, keys)
        self.assertIn(self.const.CONF_DJ_RESPONSE_PROMPT, keys)
        self.assertIn(self.const.CONF_DJ_RESPONSE_ENABLED, keys)

    def test_firmware_channel_uses_labeled_selector(self) -> None:
        hass = types.SimpleNamespace(states=None)

        schema = asyncio.run(
            self.config_flow._voice_schema(
                hass,
                self.config_flow._voice_defaults(),
            )
        )

        validator = next(
            value
            for marker, value in schema.schema.items()
            if marker.key == self.const.CONF_FIRMWARE_CHANNEL
        )
        labels = {
            option["value"]: option["label"]
            for option in validator.config.kwargs["options"]
        }

        self.assertEqual(labels, {"stable": "Stable", "beta": "Beta"})

    def test_voice_defaults_fill_empty_values(self) -> None:
        data = self.config_flow._voice_defaults(
            {
                self.const.CONF_TTS_LANGUAGE: "",
                self.const.CONF_DJ_RESPONSE_PROMPT: "",
                self.const.CONF_MAX_AUDIO_BYTES: "not-an-int",
                self.const.CONF_MIN_BATTERY_FOR_OTA: "55",
                self.const.CONF_FIRMWARE_CHANNEL: "beta",
            }
        )

        self.assertNotIn(self.const.CONF_TTS_LANGUAGE, data)
        self.assertEqual(
            data[self.const.CONF_DJ_RESPONSE_PROMPT],
            self.const.DEFAULT_DJ_RESPONSE_PROMPT,
        )
        self.assertEqual(data[self.const.CONF_MAX_AUDIO_BYTES], self.const.DEFAULT_MAX_AUDIO_BYTES)
        self.assertTrue(data[self.const.CONF_ALLOW_OTA_ON_BATTERY])
        self.assertEqual(data[self.const.CONF_MIN_BATTERY_FOR_OTA], 55)
        self.assertEqual(data[self.const.CONF_FIRMWARE_CHANNEL], "beta")
        self.assertTrue(data[self.const.CONF_DJ_RESPONSE_ENABLED])
        self.assertEqual(
            data[self.const.CONF_DJ_RESPONSE_TTL_SECONDS],
            self.const.DEFAULT_DJ_RESPONSE_TTL_SECONDS,
        )

    def test_voice_errors_allow_device_owned_spotify_playback(self) -> None:
        self.assertEqual(self.config_flow._voice_errors({}), {})

    def test_assist_pipeline_detection_requires_stt_and_tts(self) -> None:
        hass = types.SimpleNamespace()

        self.assertFalse(
            self.config_flow._assist_pipeline_has_stt_tts(
                types.SimpleNamespace(stt_engine="stt.mock")
            )
        )
        self.assertFalse(
            self.config_flow._assist_pipeline_has_stt_tts(
                types.SimpleNamespace(tts_engine="tts.mock")
            )
        )
        self.assertTrue(
            self.config_flow._assist_pipeline_has_stt_tts(
                types.SimpleNamespace(
                    stt_engine="stt.mock",
                    tts_engine="tts.mock",
                )
            )
        )
        self.assertTrue(self.config_flow._has_valid_assist_pipeline(hass))

    def test_user_step_requires_assist_pipeline_with_stt_and_tts(self) -> None:
        from homeassistant.components.assist_pipeline import pipeline as pipeline_module

        original_get_pipelines = pipeline_module.async_get_pipelines
        pipeline_module.async_get_pipelines = lambda hass: [
            types.SimpleNamespace(
                id="no-tts",
                name="No TTS",
                stt_engine="stt.mock",
                tts_engine="",
            )
        ]
        try:
            flow = self.config_flow.DJConnectConfigFlow()
            flow.hass = types.SimpleNamespace(
                config=types.SimpleNamespace(language="en-US"),
            )

            result = asyncio.run(flow.async_step_user())
        finally:
            pipeline_module.async_get_pipelines = original_get_pipelines

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")
        self.assertEqual(result["errors"]["base"], "assist_pipeline_required")

    def test_user_step_allows_setup_without_spotify_media_player(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="en-US"),
            states=None,
        )

        result = asyncio.run(flow.async_step_user())

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")
        self.assertEqual(result.get("errors"), {})

    def test_pair_step_blocks_when_assist_pipeline_is_missing(self) -> None:
        from homeassistant.components.assist_pipeline import pipeline as pipeline_module

        original_get_pipelines = pipeline_module.async_get_pipelines
        pipeline_module.async_get_pipelines = lambda hass: []
        try:
            flow = self.config_flow.DJConnectConfigFlow()
            flow.hass = types.SimpleNamespace(
                config=types.SimpleNamespace(language="en-US"),
            )

            result = asyncio.run(flow.async_step_pair())
        finally:
            pipeline_module.async_get_pipelines = original_get_pipelines

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "pair")
        self.assertEqual(result["errors"]["base"], "assist_pipeline_required")

    def test_user_schema_shows_client_type_and_local_url_without_advanced(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        keys = {marker.key for marker in flow._user_schema()}

        self.assertIn(self.const.CONF_CLIENT_TYPE, keys)
        self.assertIn(self.const.CONF_LOCAL_URL, keys)
        self.assertNotIn(self.const.CONF_DEVICE_LANGUAGE, keys)

    def test_user_schema_prefills_manual_device_url_from_pair_code(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        flow._last_pair_code = "90B70990A994"

        schema = flow._user_schema()
        local_url_marker = next(
            marker for marker in schema if marker.key == self.const.CONF_LOCAL_URL
        )

        self.assertEqual(
            local_url_marker.default,
            "http://djconnect-lilygo-t-embed-s3-90B70990A994.local",
        )


    def test_user_schema_prefills_single_discovered_app_client(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        client = self.config_flow.DiscoveredClient(
            local_url="http://192.168.1.104:60955",
            device_id="djconnect-macos-68B74487726D",
            client_type=self.const.CLIENT_TYPE_MACOS,
            device_name="DJConnect Mac",
            pair_code="555293",
        )

        flow._apply_discovered_client(client)
        schema = flow._user_schema()
        defaults = {marker.key: marker.default for marker in schema}

        self.assertEqual(defaults[self.const.CONF_PAIR_CODE], "555293")
        self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], "DJConnect Mac macOS")
        self.assertEqual(defaults[self.const.CONF_CLIENT_TYPE], self.const.CLIENT_TYPE_MACOS)
        self.assertEqual(defaults[self.const.CONF_LOCAL_URL], "http://192.168.1.104:60955")

    def test_pair_step_prefills_single_discovered_raspberry_pi_client(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        flow._discovered_clients = [
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.66:61234",
                device_id="djconnect-raspberry-pi-A1B2C3D4E5F6",
                client_type=self.const.CLIENT_TYPE_RASPBERRY_PI,
                device_name="DJConnect Pi",
                pair_code="654321",
                source="pairing-info",
            )
        ]
        flow._discovery_checked = True
        flow._selected_discovered_key = "djconnect-raspberry-pi-A1B2C3D4E5F6"
        flow._apply_discovered_client(flow._discovered_clients[0])

        result = asyncio.run(flow.async_step_pair())
        schema = result["data_schema"].schema
        defaults = {marker.key: marker.default for marker in schema}

        self.assertEqual(
            defaults[self.config_flow.DISCOVERY_CLIENT_FIELD],
            "djconnect-raspberry-pi-A1B2C3D4E5F6",
        )
        self.assertEqual(defaults[self.const.CONF_PAIR_CODE], "654321")
        self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], "DJConnect Pi Raspberry Pi")
        self.assertEqual(
            defaults[self.const.CONF_CLIENT_TYPE],
            self.const.CLIENT_TYPE_RASPBERRY_PI,
        )
        self.assertEqual(defaults[self.const.CONF_LOCAL_URL], "http://192.168.1.66:61234")

    def test_user_schema_offers_multiple_discovered_clients(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        flow._discovered_clients = [
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.104:60955",
                device_id="djconnect-macos-68B74487726D",
                client_type=self.const.CLIENT_TYPE_MACOS,
                device_name="DJConnect Mac",
            ),
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.42:51193",
                device_id="djconnect-ios-9F8FA6931AA3",
                client_type=self.const.CLIENT_TYPE_IOS,
                device_name="DJConnect iPhone",
            ),
        ]

        schema = flow._user_schema()
        keys = {marker.key for marker in schema}
        discovery_marker = next(
            marker for marker in schema if marker.key == self.config_flow.DISCOVERY_CLIENT_FIELD
        )

        self.assertIn(self.config_flow.DISCOVERY_CLIENT_FIELD, keys)
        self.assertIn("djconnect-macos-68B74487726D", schema[discovery_marker])
        self.assertIn("DJConnect iPhone", schema[discovery_marker]["djconnect-ios-9F8FA6931AA3"])

    def test_user_schema_offers_multiple_discovered_clients_including_raspberry_pi(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        flow._discovered_clients = [
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.66:61234",
                device_id="djconnect-raspberry-pi-A1B2C3D4E5F6",
                client_type=self.const.CLIENT_TYPE_RASPBERRY_PI,
                device_name="DJConnect Pi",
            ),
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.42:51193",
                device_id="djconnect-ios-9F8FA6931AA3",
                client_type=self.const.CLIENT_TYPE_IOS,
                device_name="DJConnect iPhone",
            ),
        ]

        schema = flow._user_schema()
        discovery_marker = next(
            marker for marker in schema if marker.key == self.config_flow.DISCOVERY_CLIENT_FIELD
        )

        self.assertIn("djconnect-raspberry-pi-A1B2C3D4E5F6", schema[discovery_marker])
        self.assertIn(
            "DJConnect Pi",
            schema[discovery_marker]["djconnect-raspberry-pi-A1B2C3D4E5F6"],
        )

    def test_pair_step_blocks_unverified_raspberry_pi_discovery_until_url_changes(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        client = self.config_flow.DiscoveredClient(
            local_url="http://djconnect-pi.local:61234",
            device_id="djconnect-raspberry-pi-A1B2C3D4E5F6",
            client_type=self.const.CLIENT_TYPE_RASPBERRY_PI,
            device_name="DJConnect Pi",
            pair_code="654321",
            pairing_info_failed=True,
        )
        flow._discovered_clients = [client]
        flow._selected_discovered_key = "djconnect-raspberry-pi-A1B2C3D4E5F6"
        flow._apply_discovered_client(client)

        result = asyncio.run(
            flow.async_step_pair(
                {
                    self.config_flow.DISCOVERY_CLIENT_FIELD: "djconnect-raspberry-pi-A1B2C3D4E5F6",
                    self.const.CONF_PAIR_CODE: "654321",
                    self.const.CONF_DEVICE_NAME: "DJConnect Pi",
                    self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_RASPBERRY_PI,
                    self.const.CONF_LOCAL_URL: "http://djconnect-pi.local:61234",
                }
            )
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(
            result["errors"]["base"],
            self.config_flow.DISCOVERY_PAIRING_INFO_ERROR,
        )

    def test_raspberry_pi_pairing_uses_discovered_stable_device_id(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        client = self.config_flow.DiscoveredClient(
            local_url="http://192.168.1.66:61234",
            device_id="djconnect-raspberry-pi-A1B2C3D4E5F6",
            client_type=self.const.CLIENT_TYPE_RASPBERRY_PI,
            device_name="DJConnect Pi",
            pair_code="654321",
            source="pairing-info",
        )
        flow._discovered_clients = [client]
        flow._selected_discovered_key = "djconnect-raspberry-pi-A1B2C3D4E5F6"
        flow._apply_discovered_client(client)
        async def fake_set_unique_id(unique_id):
            flow._unique_id = unique_id

        flow.async_set_unique_id = fake_set_unique_id
        flow._abort_if_unique_id_configured = lambda: None

        async def fake_spotify(user_input=None):
            return {"type": "next_step", "pairing": flow._pairing}

        flow.async_step_spotify = fake_spotify

        result = asyncio.run(
            flow.async_step_pair(
                {
                    self.config_flow.DISCOVERY_CLIENT_FIELD: "djconnect-raspberry-pi-A1B2C3D4E5F6",
                    self.const.CONF_PAIR_CODE: "654321",
                    self.const.CONF_DEVICE_NAME: "DJConnect Pi",
                    self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_RASPBERRY_PI,
                    self.const.CONF_LOCAL_URL: "http://192.168.1.66:61234",
                }
            )
        )

        self.assertEqual(flow._unique_id, "djconnect-raspberry-pi-A1B2C3D4E5F6")
        self.assertEqual(
            result["pairing"][self.const.CONF_DEVICE_ID],
            "djconnect-raspberry-pi-A1B2C3D4E5F6",
        )
        self.assertNotEqual(result["pairing"][self.const.CONF_DEVICE_ID], "djconnect-654321")

    def test_raspberry_pi_duplicate_uses_discovered_device_id_for_abort_check(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        client = self.config_flow.DiscoveredClient(
            local_url="http://192.168.1.66:61234",
            device_id="djconnect-raspberry-pi-A1B2C3D4E5F6",
            client_type=self.const.CLIENT_TYPE_RASPBERRY_PI,
            device_name="DJConnect Pi",
            pair_code="654321",
            source="pairing-info",
        )
        flow._discovered_clients = [client]
        flow._selected_discovered_key = "djconnect-raspberry-pi-A1B2C3D4E5F6"
        flow._apply_discovered_client(client)

        async def fake_set_unique_id(unique_id):
            flow._unique_id = unique_id

        def fake_abort_if_configured():
            raise RuntimeError("already_configured")

        flow.async_set_unique_id = fake_set_unique_id
        flow._abort_if_unique_id_configured = fake_abort_if_configured

        with self.assertRaisesRegex(RuntimeError, "already_configured"):
            asyncio.run(
                flow.async_step_pair(
                    {
                        self.config_flow.DISCOVERY_CLIENT_FIELD: "djconnect-raspberry-pi-A1B2C3D4E5F6",
                        self.const.CONF_PAIR_CODE: "654321",
                        self.const.CONF_DEVICE_NAME: "DJConnect Pi",
                        self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_RASPBERRY_PI,
                        self.const.CONF_LOCAL_URL: "http://192.168.1.66:61234",
                    }
                )
            )

        self.assertEqual(flow._unique_id, "djconnect-raspberry-pi-A1B2C3D4E5F6")

    def test_default_local_url_accepts_only_device_suffix(self) -> None:
        self.assertEqual(self.config_flow._default_local_url("123456"), "")
        self.assertEqual(
            self.config_flow._default_local_url("90B70990A994"),
            "http://djconnect-lilygo-t-embed-s3-90B70990A994.local",
        )
        self.assertTrue(self.config_flow._valid_pair_code("123456"))
        self.assertTrue(self.config_flow._valid_pair_code("90B70990A994"))
        self.assertFalse(self.config_flow._valid_pair_code("abc123"))
        self.assertEqual(self.config_flow._default_local_url("12345"), "")

    def test_device_language_default_uses_ha_language_when_supported(self) -> None:
        nl_hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        en_hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))

        self.assertEqual(self.config_flow._ha_device_language(nl_hass), "nl")
        self.assertEqual(self.config_flow._ha_device_language(en_hass), "en")

    def test_setup_method_labels_follow_ha_language(self) -> None:
        nl_hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        en_hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))

        self.assertEqual(
            self.config_flow._setup_method_names(nl_hass)[
                self.const.SETUP_METHOD_PAIR_EXISTING
            ],
            "DJConnect app of device koppelen",
        )
        self.assertEqual(
            self.config_flow._setup_method_names(en_hass)[
                self.const.SETUP_METHOD_PAIR_EXISTING
            ],
            "Pair DJConnect app or device",
        )
        self.assertEqual(
            self.config_flow._setup_method_names(nl_hass)[
                self.const.SETUP_METHOD_CONVERSATION_AGENT
            ],
            "Assist Conversation Agent",
        )

    def test_ble_action_labels_follow_ha_language(self) -> None:
        nl_hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        en_hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))

        self.assertEqual(
            self.config_flow._ble_action_names(nl_hass)[
                self.config_flow.BLE_ACTION_CONTINUE_PAIRING
            ],
            "Doorgaan naar koppelen",
        )
        self.assertEqual(
            self.config_flow._ble_action_names(en_hass)[
                self.config_flow.BLE_ACTION_RETRY_SCAN
            ],
            "Rescan Bluetooth devices",
        )

    def test_options_action_labels_follow_ha_language(self) -> None:
        nl_hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        en_hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))

        self.assertEqual(
            self.config_flow._options_action_names(nl_hass)[
                self.config_flow.OPTIONS_ACTION_REPAIR
            ],
            "Opnieuw koppelen met nieuwe koppelcode",
        )
        self.assertEqual(
            self.config_flow._options_action_names(en_hass)[
                self.config_flow.OPTIONS_ACTION_RETRY_PAIRING
            ],
            "Retry pairing with current code",
        )
        self.assertEqual(
            self.config_flow._options_action_names(en_hass)[
                self.config_flow.OPTIONS_ACTION_SPOTIFY_REAUTH
            ],
            "Reauthorize Spotify",
        )
        self.assertEqual(
            self.config_flow._options_action_names(en_hass)[
                self.config_flow.OPTIONS_ACTION_SAVE
            ],
            "Save options",
        )

    def test_options_actions_hide_pairing_retry_when_not_pending(self) -> None:
        hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))

        actions = self.config_flow._options_actions_for_status(
            hass,
            {"ha_pairing_status": "paired"},
        )

        self.assertNotIn(self.config_flow.OPTIONS_ACTION_RETRY_PAIRING, actions)
        self.assertIn(self.config_flow.OPTIONS_ACTION_REPAIR, actions)
        self.assertIn(self.config_flow.OPTIONS_ACTION_SPOTIFY_REAUTH, actions)
        self.assertIn(self.config_flow.OPTIONS_ACTION_SAVE, actions)

    def test_options_actions_show_pairing_retry_when_pending(self) -> None:
        hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))

        actions = self.config_flow._options_actions_for_status(
            hass,
            {"ha_pairing_status": "pending"},
        )

        self.assertIn(self.config_flow.OPTIONS_ACTION_RETRY_PAIRING, actions)

    def test_ble_wifi_schema_uses_discovered_devices_when_available(self) -> None:
        schema = self.config_flow._ble_wifi_schema({"AA:BB": "DJConnect 1234"})

        keys = {marker.key for marker in schema}
        self.assertIn(self.config_flow.BLE_ACTION_FIELD, keys)
        self.assertIn(self.const.CONF_BLE_ADDRESS, keys)
        self.assertIn(self.const.CONF_WIFI_SSID, keys)
        self.assertIn(self.const.CONF_WIFI_PASSWORD, keys)

    def test_ble_wifi_schema_selects_single_discovered_device_by_default(self) -> None:
        schema = self.config_flow._ble_wifi_schema({"AA:BB": "DJConnect A994"})

        defaults = {marker.key: marker.default for marker in schema}

        self.assertEqual(defaults[self.const.CONF_BLE_ADDRESS], "AA:BB")

    def test_ble_wifi_schema_keeps_placeholder_when_multiple_devices_exist(self) -> None:
        schema = self.config_flow._ble_wifi_schema(
            {"AA:BB": "DJConnect A994", "CC:DD": "DJConnect 1234"}
        )

        defaults = {marker.key: marker.default for marker in schema}

        self.assertEqual(defaults[self.const.CONF_BLE_ADDRESS], "")

    def test_pair_schema_allows_returning_to_ble_setup(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        schema = flow._user_schema()
        keys = {marker.key for marker in schema}

        self.assertIn(self.const.CONF_SETUP_METHOD, keys)
        self.assertIn(self.const.CONF_PAIR_CODE, keys)

    def test_setup_method_order_puts_conversation_agent_first(self) -> None:
        hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        methods = list(self.config_flow._setup_method_names(hass))

        self.assertEqual(methods[0], self.const.SETUP_METHOD_CONVERSATION_AGENT)

    def test_user_schema_selects_conversation_agent_by_default(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        schema = flow._user_schema()
        defaults = {marker.key: marker.default for marker in schema}

        self.assertEqual(
            defaults[self.const.CONF_SETUP_METHOD],
            self.const.SETUP_METHOD_CONVERSATION_AGENT,
        )

    def test_pair_step_can_route_back_to_ble_setup(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        async def fake_ble_wifi(user_input=None):
            return {"type": "form", "step_id": "ble_wifi"}

        flow.async_step_ble_wifi = fake_ble_wifi

        result = asyncio.run(
            flow.async_step_pair({self.const.CONF_SETUP_METHOD: self.config_flow.SETUP_METHOD_BLE_WIFI})
        )

        self.assertEqual(result["step_id"], "ble_wifi")

    def test_user_step_can_route_to_conversation_agent_setup(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="nl-NL"),
            data={self.const.DOMAIN: {}},
        )
        unique_ids = []

        async def fake_set_unique_id(unique_id):
            unique_ids.append(unique_id)

        async def fake_spotify(user_input=None):
            return {"type": "form", "step_id": "spotify"}

        flow.async_set_unique_id = fake_set_unique_id
        flow._abort_if_unique_id_configured = lambda: None
        flow.async_step_spotify = fake_spotify

        result = asyncio.run(
            flow.async_step_user(
                {
                    self.const.CONF_SETUP_METHOD: (
                        self.const.SETUP_METHOD_CONVERSATION_AGENT
                    )
                }
            )
        )

        self.assertEqual(result["step_id"], "spotify")
        self.assertEqual(unique_ids, ["djconnect-conversation-agent"])
        self.assertTrue(flow._conversation_agent_only)
        self.assertEqual(
            flow._pairing[self.const.CONF_CLIENT_TYPE],
            self.const.CLIENT_TYPE_CONVERSATION_AGENT,
        )
        self.assertNotIn(self.const.CONF_DEVICE_TOKEN, flow._pairing)
        self.assertNotIn(self.const.CONF_LOCAL_URL, flow._pairing)

    def test_spotify_client_id_is_required_visible_field(self) -> None:
        schema = self.config_flow._spotify_schema()

        keys = {marker.key for marker in schema}

        self.assertIn(self.const.CONF_SPOTIFY_CLIENT_ID, keys)
        self.assertNotIn("show_advanced_options", keys)

    def test_voice_schema_can_include_options_action(self) -> None:
        hass = types.SimpleNamespace(states=None, config=types.SimpleNamespace(language="nl-NL"))

        schema = asyncio.run(
            self.config_flow._voice_schema(
                hass,
                self.config_flow._voice_defaults({}),
                include_options_action=True,
            )
        ).schema
        keys = {marker.key for marker in schema}

        self.assertIn(self.config_flow.OPTIONS_ACTION_FIELD, keys)

    def test_voice_schema_can_show_readonly_client_api_url(self) -> None:
        hass = types.SimpleNamespace(states=None, config=types.SimpleNamespace(language="nl-NL"))
        local_url = "http://192.168.1.104:60955"

        schema = asyncio.run(
            self.config_flow._voice_schema(
                hass,
                {self.const.CONF_LOCAL_URL: local_url},
                include_readonly_local_url=True,
            )
        ).schema
        marker = next(marker for marker in schema if marker.key == self.const.CONF_LOCAL_URL)

        self.assertEqual(marker.default, local_url)
        self.assertEqual(schema[marker], {local_url: local_url})

    def test_spotify_schema_prefills_external_url(self) -> None:
        schema = self.config_flow._spotify_schema_with_defaults(
            external_url="https://example.ui.nabu.casa"
        )
        marker = next(
            marker for marker in schema if marker.key == self.const.CONF_HA_EXTERNAL_URL
        )

        self.assertEqual(marker.default, "https://example.ui.nabu.casa")

    def test_default_external_url_uses_hass_config_fallback(self) -> None:
        hass = types.SimpleNamespace(
            config=types.SimpleNamespace(external_url="https://example.ui.nabu.casa/")
        )

        self.assertEqual(
            asyncio.run(self.config_flow._async_default_external_url(hass)),
            "https://example.ui.nabu.casa",
        )

    def test_default_external_url_uses_hass_config_api_fallback(self) -> None:
        hass = types.SimpleNamespace(
            config=types.SimpleNamespace(
                api=types.SimpleNamespace(external_url="https://api.ui.nabu.casa/")
            )
        )

        self.assertEqual(
            asyncio.run(self.config_flow._async_default_external_url(hass)),
            "https://api.ui.nabu.casa",
        )

    def test_default_external_url_uses_hass_data_fallback(self) -> None:
        hass = types.SimpleNamespace(
            config=types.SimpleNamespace(),
            data={"external_url": "https://data.ui.nabu.casa/"},
        )

        self.assertEqual(
            asyncio.run(self.config_flow._async_default_external_url(hass)),
            "https://data.ui.nabu.casa",
        )

    def test_spotify_step_prefills_external_url_from_hass(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(
                api=types.SimpleNamespace(external_url="https://api.ui.nabu.casa/")
            )
        )

        result = asyncio.run(flow.async_step_spotify())
        schema = result["data_schema"].schema
        marker = next(
            marker for marker in schema if marker.key == self.const.CONF_HA_EXTERNAL_URL
        )
        client_id_marker = next(
            marker for marker in schema if marker.key == self.const.CONF_SPOTIFY_CLIENT_ID
        )

        self.assertEqual(marker.default, "https://api.ui.nabu.casa")
        self.assertEqual(client_id_marker.default, "")
        self.assertEqual(
            result["description_placeholders"]["redirect_uri"],
            "https://api.ui.nabu.casa/api/djconnect/spotify/callback",
        )

    def test_spotify_step_requires_user_spotify_client_id(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace())

        result = asyncio.run(
            flow.async_step_spotify(
                {
                    self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
                    self.const.CONF_SPOTIFY_MARKET: "NL",
                }
            )
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(
            result["errors"][self.const.CONF_SPOTIFY_CLIENT_ID],
            "spotify_client_id_required",
        )

    def test_spotify_oauth_external_step_has_title(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        flow._oauth = {
            "authorize_url": "https://accounts.spotify.com/authorize",
            "redirect_uri": "https://example.ui.nabu.casa/api/djconnect/spotify/callback",
        }

        result = asyncio.run(flow.async_step_spotify_oauth())

        self.assertEqual(result["type"], "external")
        self.assertEqual(result["title"], "DJConnect autoriseren bij Spotify")

    def test_voice_step_pairs_device_before_creating_entry(self) -> None:
        package = sys.modules["custom_components.djconnect"]
        original_runtime = getattr(package, "DJConnectRuntime", None)
        calls = []

        class Runtime:
            def __init__(self, entry):
                self.entry = entry
                self.device_token = None
                self.pairing_code = None
                self.pairing_device_id = None
                self.device_status = {}

            async def pair_device(self, hass):
                calls.append(
                    {
                        "pairing_code": self.pairing_code,
                        "pairing_device_id": self.pairing_device_id,
                        "device_token": self.device_token,
                    }
                )
                self.device_status["device_id"] = "djconnect-lilygo-90B70990A994"
                self.device_status["local_url"] = "http://djconnect-lilygo-90B70990A994.local"

        package.DJConnectRuntime = Runtime
        try:
            flow = self.config_flow.DJConnectConfigFlow()
            flow.hass = types.SimpleNamespace(states=None)
            flow._pairing = {
                self.const.CONF_PAIR_CODE: "123456",
                self.const.CONF_DEVICE_ID: "djconnect-123456",
                self.const.CONF_DEVICE_NAME: "DJConnect",
                self.const.CONF_DEVICE_TOKEN: "device-token",
                self.const.CONF_LOCAL_URL: "http://djconnect.local",
            }
            flow._spotify = {
                self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
                self.const.CONF_SPOTIFY_REFRESH_TOKEN: "refresh-token",
                self.const.CONF_SPOTIFY_MARKET: "NL",
                self.const.CONF_SPOTIFY_SCOPES: self.const.DEFAULT_SPOTIFY_SCOPES,
                self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
            }

            result = asyncio.run(flow.async_step_voice({}))
        finally:
            if original_runtime is None:
                delattr(package, "DJConnectRuntime")
            else:
                package.DJConnectRuntime = original_runtime

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["pairing_code"], "123456")
        self.assertEqual(calls[0]["pairing_device_id"], "djconnect-123456")
        self.assertEqual(calls[0]["device_token"], "device-token")
        self.assertEqual(
            result["data"][self.const.CONF_DEVICE_ID],
            "djconnect-lilygo-90B70990A994",
        )
        self.assertEqual(
            result["data"][self.const.CONF_LOCAL_URL],
            "http://djconnect-lilygo-90B70990A994.local",
        )

    def test_voice_step_conversation_agent_setup_skips_device_pairing(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(states=None)
        flow._conversation_agent_only = True
        flow._pairing = {
            self.const.CONF_SETUP_METHOD: self.const.SETUP_METHOD_CONVERSATION_AGENT,
            self.const.CONF_DEVICE_ID: "djconnect-conversation-agent",
            self.const.CONF_DEVICE_NAME: "DJConnect DJ",
            self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_CONVERSATION_AGENT,
        }
        flow._spotify = {
            self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
            self.const.CONF_SPOTIFY_REFRESH_TOKEN: "refresh-token",
            self.const.CONF_SPOTIFY_MARKET: "NL",
            self.const.CONF_SPOTIFY_SCOPES: self.const.DEFAULT_SPOTIFY_SCOPES,
            self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
        }

        result = asyncio.run(flow.async_step_voice({}))

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "DJConnect DJ")
        self.assertEqual(
            result["data"][self.const.CONF_CLIENT_TYPE],
            self.const.CLIENT_TYPE_CONVERSATION_AGENT,
        )
        self.assertNotIn(self.const.CONF_DEVICE_TOKEN, result["data"])
        self.assertNotIn(self.const.CONF_LOCAL_URL, result["data"])

    def test_voice_step_conversation_agent_setup_hides_device_fields(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(states=None)
        flow._conversation_agent_only = True

        form = asyncio.run(flow.async_step_voice())
        keys = {marker.key for marker in form["data_schema"].schema}

        self.assertIn(self.const.CONF_DJ_RESPONSE_PROMPT_PRESET, keys)
        self.assertIn(self.const.CONF_DJ_RESPONSE_PROMPT, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_ENABLED, keys)
        self.assertNotIn(self.const.CONF_ASSIST_PIPELINE_ID, keys)
        self.assertNotIn(self.const.CONF_FIRMWARE_CHANNEL, keys)
        self.assertNotIn(self.const.CONF_LOCAL_URL, keys)

    def test_default_external_url_prefers_network_helper(self) -> None:
        from homeassistant.helpers import network

        original = network.async_get_url

        async def network_url(*args, **kwargs):
            return "https://network.ui.nabu.casa/"

        network.async_get_url = network_url
        try:
            self.assertEqual(
                asyncio.run(
                    self.config_flow._async_default_external_url(
                        types.SimpleNamespace(config=types.SimpleNamespace())
                    )
                ),
                "https://network.ui.nabu.casa",
            )
        finally:
            network.async_get_url = original

    def test_default_external_url_uses_sync_network_helper_with_cloud_preference(self) -> None:
        from homeassistant.helpers import network

        original_async = network.async_get_url
        original_sync = getattr(network, "get_url", None)

        def network_url(hass, **kwargs):
            self.assertTrue(kwargs["prefer_external"])
            self.assertTrue(kwargs["prefer_cloud"])
            self.assertFalse(kwargs["allow_internal"])
            self.assertTrue(kwargs["allow_cloud"])
            self.assertTrue(kwargs["require_ssl"])
            return "https://cloud-sync.ui.nabu.casa/"

        network.async_get_url = None
        network.get_url = network_url
        try:
            self.assertEqual(
                asyncio.run(
                    self.config_flow._async_default_external_url(
                        types.SimpleNamespace(config=types.SimpleNamespace())
                    )
                ),
                "https://cloud-sync.ui.nabu.casa",
            )
        finally:
            network.async_get_url = original_async
            if original_sync is None:
                delattr(network, "get_url")
            else:
                network.get_url = original_sync

    def test_default_external_url_uses_cloud_remote_ui_fallback(self) -> None:
        from homeassistant.components import cloud
        from homeassistant.helpers import network

        original_network = network.async_get_url
        original_cloud = cloud.async_remote_ui_url

        async def no_network_url(*args, **kwargs):
            return ""

        async def cloud_url(hass):
            return "https://cloud.ui.nabu.casa/"

        network.async_get_url = no_network_url
        cloud.async_remote_ui_url = cloud_url
        try:
            self.assertEqual(
                asyncio.run(
                    self.config_flow._async_default_external_url(
                        types.SimpleNamespace(config=types.SimpleNamespace())
                    )
                ),
                "https://cloud.ui.nabu.casa",
            )
        finally:
            network.async_get_url = original_network
            cloud.async_remote_ui_url = original_cloud

    def test_default_external_url_uses_sync_cloud_remote_ui_fallback(self) -> None:
        from homeassistant.components import cloud
        from homeassistant.helpers import network

        original_network = network.async_get_url
        original_cloud = cloud.async_remote_ui_url

        async def no_network_url(*args, **kwargs):
            return ""

        def cloud_url(hass):
            return "https://sync-cloud.ui.nabu.casa/"

        network.async_get_url = no_network_url
        cloud.async_remote_ui_url = cloud_url
        try:
            self.assertEqual(
                asyncio.run(
                    self.config_flow._async_default_external_url(
                        types.SimpleNamespace(config=types.SimpleNamespace())
                    )
                ),
                "https://sync-cloud.ui.nabu.casa",
            )
        finally:
            network.async_get_url = original_network
            cloud.async_remote_ui_url = original_cloud

    def test_options_flow_init_does_not_assign_read_only_config_entry(self) -> None:
        entry = types.SimpleNamespace(data={}, options={})

        flow = self.config_flow.DJConnectOptionsFlow(entry)

        self.assertIs(flow._config_entry, entry)

    def test_options_flow_shows_only_conversation_agent_relevant_fields(self) -> None:
        entry = types.SimpleNamespace(
            data={
                self.const.CONF_LOCAL_URL: "http://device.local",
                self.const.CONF_ASSIST_PIPELINE_ID: "pipeline-1",
                self.const.CONF_FIRMWARE_CHANNEL: "beta",
            },
            options={},
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl"))

        form = asyncio.run(flow.async_step_init())
        keys = {marker.key for marker in form["data_schema"].schema}

        self.assertIn(self.config_flow.OPTIONS_ACTION_FIELD, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_ENABLED, keys)
        self.assertIn(self.const.CONF_DJ_RESPONSE_PROMPT_PRESET, keys)
        self.assertIn(self.const.CONF_DJ_RESPONSE_PROMPT, keys)
        self.assertNotIn(self.const.CONF_SPOTIFY_SOURCE, keys)
        self.assertNotIn(self.const.CONF_LIKED_PROXY, keys)
        self.assertNotIn(self.const.CONF_LOCAL_URL, keys)
        self.assertNotIn(self.const.CONF_ASSIST_PIPELINE_ID, keys)
        self.assertNotIn(self.const.CONF_FIRMWARE_CHANNEL, keys)
        self.assertNotIn(self.const.CONF_MAX_AUDIO_BYTES, keys)
        self.assertNotIn(self.const.CONF_ALLOW_OTA_ON_BATTERY, keys)
        self.assertNotIn(self.const.CONF_MIN_BATTERY_FOR_OTA, keys)
        self.assertNotIn("show_advanced_options", keys)

    def test_options_flow_save_preserves_hidden_device_values(self) -> None:
        entry = types.SimpleNamespace(
            data={
                self.const.CONF_ASSIST_PIPELINE_ID: "pipeline-1",
                self.const.CONF_FIRMWARE_CHANNEL: "beta",
                self.const.CONF_MAX_AUDIO_BYTES: 12345,
            },
            options={},
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en"))

        result = asyncio.run(
            flow.async_step_init(
                {
                    self.config_flow.OPTIONS_ACTION_FIELD: self.config_flow.OPTIONS_ACTION_SAVE,
                    self.const.CONF_DJ_RESPONSE_PROMPT_PRESET: "custom",
                    self.const.CONF_DJ_RESPONSE_PROMPT: "Maak het kort.",
                    self.const.CONF_MAX_AUDIO_BYTES: 99999,
                }
            )
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(
            result["data"][self.const.CONF_ASSIST_PIPELINE_ID],
            "pipeline-1",
        )
        self.assertEqual(result["data"][self.const.CONF_FIRMWARE_CHANNEL], "beta")
        self.assertEqual(result["data"][self.const.CONF_MAX_AUDIO_BYTES], 12345)
        self.assertEqual(
            result["data"][self.const.CONF_DJ_RESPONSE_PROMPT],
            "Maak het kort.",
        )

    def test_options_spotify_reauth_finishes_with_done_step(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
                self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
            },
            options={},
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.flow_id = "flow-1"
        flow.hass = types.SimpleNamespace(data={})

        external = asyncio.run(flow.async_step_spotify_reauth())
        self.assertEqual(external["type"], "external")
        self.assertEqual(external["step_id"], "spotify_reauth")
        self.assertEqual(external["title"], "Reauthorize Spotify")
        self.assertIn("https://accounts.spotify.com/authorize", external["url"])
        self.assertIn(
            flow._oauth["state"],
            flow.hass.data[self.const.DOMAIN]["spotify_oauth_pending"],
        )

        done = asyncio.run(
            flow.async_step_spotify_reauth({"state": flow._oauth["state"]})
        )
        self.assertEqual(done["type"], "external_done")
        self.assertEqual(done["next_step_id"], "spotify_reauth_done")

        form = asyncio.run(flow.async_step_spotify_reauth_done())
        self.assertEqual(form["type"], "form")
        self.assertEqual(form["step_id"], "spotify_reauth_done")

        submit = asyncio.run(flow.async_step_spotify_reauth_done({}))
        self.assertEqual(submit["type"], "create_entry")

    def test_options_repair_pairing_does_not_prefill_old_pair_code(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={self.const.CONF_PAIR_CODE: "253940"},
            options={},
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)

        form = asyncio.run(flow.async_step_repair_pairing())

        self.assertEqual(form["type"], "form")
        self.assertEqual(form["step_id"], "repair_pairing")
        markers = list(form["data_schema"].schema)
        self.assertEqual(markers[0].key, self.const.CONF_PAIR_CODE)
        self.assertIsNone(markers[0].default)
        self.assertEqual(markers[1].key, self.const.CONF_LOCAL_URL)
        self.assertIsNone(markers[1].default)

    def test_options_repair_pairing_uses_manual_local_url(self) -> None:
        calls = []

        class Runtime:
            def __init__(self):
                self.device_status = {}
                self.device_token = None
                self.pairing_code = None
                self.pairing_device_id = None

            def update(self, **kwargs):
                calls.append(("update", kwargs))

            async def pair_device(self, hass):
                calls.append(
                    (
                        "pair_device",
                        self.pairing_code,
                        self.pairing_device_id,
                        self.device_status.get("local_url"),
                    )
                )

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={self.const.CONF_PAIR_CODE: "253940"},
            options={},
        )
        runtime = Runtime()

        class ConfigEntries:
            def async_update_entry(self, entry_arg, *, data):
                entry_arg.data = data

        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(
            data={self.const.DOMAIN: {entry.entry_id: runtime}},
            config_entries=ConfigEntries(),
            states=None,
        )

        result = asyncio.run(
            flow.async_step_repair_pairing(
                {
                    self.const.CONF_PAIR_CODE: "555293",
                    self.const.CONF_LOCAL_URL: "http://192.168.1.104:60955",
                }
            )
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertIn(
            (
                "pair_device",
                "555293",
                "djconnect-555293",
                "http://192.168.1.104:60955",
            ),
            calls,
        )
        self.assertEqual(entry.data[self.const.CONF_LOCAL_URL], "http://192.168.1.104:60955")

    def test_options_repair_pairing_empty_local_url_reuses_stored_url(self) -> None:
        calls = []

        class Runtime:
            def __init__(self):
                self.device_status = {
                    "local_url": "http://runtime.local:18080",
                }
                self.device_token = None
                self.pairing_code = None
                self.pairing_device_id = None

            def update(self, **kwargs):
                calls.append(("update", kwargs))

            async def pair_device(self, hass):
                calls.append(
                    (
                        "pair_device",
                        self.pairing_code,
                        self.pairing_device_id,
                        self.device_status.get("local_url"),
                    )
                )

        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_PAIR_CODE: "253940",
                self.const.CONF_LOCAL_URL: "http://192.168.1.104:60955",
            },
            options={},
        )
        runtime = Runtime()

        class ConfigEntries:
            def async_update_entry(self, entry_arg, *, data):
                entry_arg.data = data

        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(
            data={self.const.DOMAIN: {entry.entry_id: runtime}},
            config_entries=ConfigEntries(),
            states=None,
        )

        result = asyncio.run(
            flow.async_step_repair_pairing(
                {
                    self.const.CONF_PAIR_CODE: "555293",
                    self.const.CONF_LOCAL_URL: "",
                }
            )
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertIn(
            (
                "pair_device",
                "555293",
                "djconnect-555293",
                "http://192.168.1.104:60955",
            ),
            calls,
        )
        self.assertEqual(entry.data[self.const.CONF_LOCAL_URL], "http://192.168.1.104:60955")


if __name__ == "__main__":
    unittest.main()
