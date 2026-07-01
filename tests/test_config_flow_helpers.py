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


def _hass_with_music_assistant_player() -> types.SimpleNamespace:
    class State:
        state = "playing"
        attributes = {
            "friendly_name": "Living room",
            "mass_player_type": "player",
            "media_title": "Bella",
            "media_artist": "Finnebassen",
            "volume_level": 0.42,
        }

    class States:
        def async_entity_ids(self, domain):
            return ["media_player.mass_living"] if domain == "media_player" else []

        def get(self, entity_id):
            return State() if entity_id == "media_player.mass_living" else None

    return types.SimpleNamespace(
        config=types.SimpleNamespace(language="en-US"),
        data={"music_assistant": object()},
        states=States(),
    )


def _hass_with_music_assistant_data_only_player() -> types.SimpleNamespace:
    class States:
        def async_entity_ids(self, domain):
            return [] if domain == "media_player" else []

        def get(self, entity_id):
            return None

    return types.SimpleNamespace(
        config=types.SimpleNamespace(language="en-US"),
        data={
            "music_assistant": object(),
            "music_assistant_players": {"media_player.mass_missing": "Missing"},
        },
        states=States(),
    )


def _hass_with_music_assistant_and_plain_media_player() -> types.SimpleNamespace:
    mass_state = types.SimpleNamespace(
        state="playing",
        attributes={"friendly_name": "Living room", "mass_player_type": "player"},
    )
    plain_state = types.SimpleNamespace(
        state="idle",
        attributes={"friendly_name": "Kitchen speaker"},
    )

    class States:
        def async_entity_ids(self, domain):
            if domain != "media_player":
                return []
            return ["media_player.mass_living", "media_player.kitchen_speaker"]

        def get(self, entity_id):
            return {
                "media_player.mass_living": mass_state,
                "media_player.kitchen_speaker": plain_state,
            }.get(entity_id)

    return types.SimpleNamespace(
        config=types.SimpleNamespace(language="en-US"),
        data={"music_assistant": object()},
        states=States(),
    )


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

    def test_voice_schema_hides_dj_response_prompt_controls(self) -> None:
        hass = types.SimpleNamespace(states=None)
        schema = asyncio.run(
            self.config_flow._voice_schema(
                hass,
                self.config_flow._voice_defaults(),
            )
        )
        keys = {marker.key for marker in schema.schema}

        self.assertNotIn(self.const.CONF_DJ_RESPONSE_PROMPT_PRESET, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_PROMPT, keys)
        self.assertIn(self.const.CONF_VOICE_PROFILE, keys)

    def test_voice_defaults_store_supported_voice_profile(self) -> None:
        defaults = self.config_flow._voice_defaults(
            {
                self.const.CONF_VOICE_PROFILE: self.const.VOICE_PROFILE_LATE_NIGHT,
            }
        )

        self.assertEqual(
            defaults[self.const.CONF_VOICE_PROFILE],
            self.const.VOICE_PROFILE_LATE_NIGHT,
        )

    def test_voice_defaults_fall_back_for_unknown_voice_profile(self) -> None:
        defaults = self.config_flow._voice_defaults(
            {
                self.const.CONF_VOICE_PROFILE: "celebrity_clone",
            }
        )

        self.assertEqual(
            defaults[self.const.CONF_VOICE_PROFILE],
            self.const.DEFAULT_VOICE_PROFILE,
        )

    def test_voice_defaults_ignore_legacy_dj_response_prompt_input(self) -> None:
        defaults = self.config_flow._voice_defaults(
            {
                self.const.CONF_DJ_RESPONSE_PROMPT: "Maak het kort en eigen.",
            }
        )

        self.assertEqual(
            defaults[self.const.CONF_DJ_RESPONSE_PROMPT],
            self.const.DEFAULT_DJ_RESPONSE_PROMPT,
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
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_PROMPT_PRESET, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_PROMPT, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_ENABLED, keys)

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

    def test_voice_schema_hides_firmware_channel_for_app_clients(self) -> None:
        hass = types.SimpleNamespace(states=None)

        for client_type in (
            self.const.CLIENT_TYPE_IOS,
            self.const.CLIENT_TYPE_MACOS,
            self.const.CLIENT_TYPE_WATCHOS,
            self.const.CLIENT_TYPE_RASPBERRY_PI,
            self.const.CLIENT_TYPE_WINDOWS,
        ):
            with self.subTest(client_type=client_type):
                schema = asyncio.run(
                    self.config_flow._voice_schema(
                        hass,
                        {
                            self.const.CONF_CLIENT_TYPE: client_type,
                            **self.config_flow._voice_defaults(),
                        },
                    )
                )

                keys = {marker.key for marker in schema.schema}

                self.assertNotIn(self.const.CONF_FIRMWARE_CHANNEL, keys)

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
        self.assertIs(result["last_step"], False)

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
        self.assertEqual(result["step_id"], "pair_app_ios_details")
        self.assertEqual(result["errors"]["base"], "assist_pipeline_required")
        self.assertIs(result["last_step"], False)

    def test_app_user_schema_hides_local_url_without_advanced(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        keys = {marker.key for marker in flow._user_schema()}

        self.assertIn(self.const.CONF_DEVICE_NAME, keys)
        self.assertNotIn(self.const.CONF_CLIENT_TYPE, keys)
        self.assertNotIn(self.const.CONF_LOCAL_URL, keys)
        self.assertNotIn(self.const.CONF_DEVICE_LANGUAGE, keys)

    def test_client_type_choices_put_app_clients_before_esp32(self) -> None:
        self.assertEqual(
            list(self.const.CLIENT_TYPE_NAMES),
            [
                self.const.CLIENT_TYPE_IOS,
                self.const.CLIENT_TYPE_MACOS,
                self.const.CLIENT_TYPE_WATCHOS,
                self.const.CLIENT_TYPE_RASPBERRY_PI,
                self.const.CLIENT_TYPE_WINDOWS,
                self.const.CLIENT_TYPE_ESP32,
            ],
        )
        self.assertEqual(
            self.const.CLIENT_TYPE_NAMES[self.const.CLIENT_TYPE_WATCHOS],
            "Apple Watch app",
        )
        self.assertEqual(
            self.const.CLIENT_TYPE_NAMES[self.const.CLIENT_TYPE_RASPBERRY_PI],
            "Linux/Raspberry Pi client",
        )
        self.assertEqual(
            self.const.CLIENT_TYPE_NAMES[self.const.CLIENT_TYPE_WINDOWS],
            "Windows app",
        )

    def test_local_device_schema_does_not_prefill_manual_device_url_from_pair_code(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
        flow._last_pair_code = "123456"

        schema = flow._user_schema()
        local_url_marker = next(
            marker for marker in schema if marker.key == self.const.CONF_LOCAL_URL
        )

        self.assertEqual(local_url_marker.default, "")


    def test_app_user_schema_shows_generated_pairing_placeholders(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="en-US", internal_url="http://ha.local:8123")
        )
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP

        asyncio.run(flow._ensure_app_pairing_defaults())
        schema = flow._user_schema()
        defaults = {marker.key: marker.default for marker in schema}
        placeholders = flow._pair_description_placeholders()

        self.assertNotIn(self.const.CONF_PAIR_CODE, defaults)
        self.assertNotIn(self.const.CONF_LOCAL_URL, defaults)
        self.assertRegex(defaults[self.config_flow.APP_PAIR_CODE_DISPLAY_FIELD], r"^\d{6}$")
        self.assertEqual(
            defaults[self.config_flow.APP_HA_LOCAL_URL_DISPLAY_FIELD],
            "http://ha.local:8123",
        )
        self.assertNotIn(self.config_flow.APP_IPHONE_PAIRING_URI_FIELD, defaults)
        self.assertNotIn(self.config_flow.APP_WATCH_PAIRING_URI_FIELD, defaults)
        self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], "DJConnect iOS")
        self.assertNotIn(self.const.CONF_CLIENT_TYPE, defaults)
        self.assertRegex(placeholders["pair_code"], r"^\d{6}$")
        self.assertEqual(placeholders["ha_local_url"], "http://ha.local:8123")
        self.assertIn("djconnect://pair?", placeholders["pairing_uri"])
        self.assertIn("pair_path=%2Fapi%2Fdjconnect%2Fpair", placeholders["pairing_uri"])
        self.assertIn("client_type=ios", placeholders["iphone_pairing_uri"])
        self.assertIn("client_type=watchos", placeholders["watch_pairing_uri"])
        self.assertIn("iphone_qr_image", placeholders)
        self.assertIn("watch_qr_image", placeholders)

    def test_app_detail_schema_uses_fallback_pairing_fields_for_app_clients(self) -> None:
        for client_type, expected_name in (
            (self.const.CLIENT_TYPE_IOS, "DJConnect iOS"),
            (self.const.CLIENT_TYPE_WATCHOS, "DJConnect Watch"),
            (self.const.CLIENT_TYPE_MACOS, "DJConnect macOS"),
            (self.const.CLIENT_TYPE_WINDOWS, "DJConnect Windows"),
        ):
            with self.subTest(client_type=client_type):
                flow = self.config_flow.DJConnectConfigFlow()
                flow.hass = types.SimpleNamespace(
                    config=types.SimpleNamespace(
                        language="en-US",
                        internal_url="http://ha.local:8123",
                    )
                )
                flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP
                flow._selected_pair_client_type = client_type

                asyncio.run(flow._ensure_app_pairing_defaults())
                schema = flow._user_schema()
                defaults = {marker.key: marker.default for marker in schema}

                self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], expected_name)
                self.assertNotIn(self.const.CONF_CLIENT_TYPE, defaults)
                self.assertRegex(
                    defaults[self.config_flow.APP_PAIR_CODE_DISPLAY_FIELD],
                    r"^\d{6}$",
                )
                self.assertEqual(
                    defaults[self.config_flow.APP_HA_LOCAL_URL_DISPLAY_FIELD],
                    "http://ha.local:8123",
                )

    def test_app_detail_step_resyncs_pending_context_when_client_type_changes(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.flow_id = "flow-1"
        flow.hass = types.SimpleNamespace(
            data={self.const.DOMAIN: {}},
            config=types.SimpleNamespace(
                language="en-US",
                internal_url="http://ha.local:8123",
            ),
        )
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP
        flow._selected_pair_client_type = self.const.CLIENT_TYPE_MACOS
        asyncio.run(flow._ensure_app_pairing_defaults())
        pair_code = flow._discovered_defaults[self.const.CONF_PAIR_CODE]
        pending = flow.hass.data[self.const.DOMAIN]["config_flow_app_pairing_pending"]
        pending[pair_code]["pairing_received"] = {
            self.const.CONF_DEVICE_ID: "djconnect-macos-68B74487726D",
            self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_MACOS,
        }

        flow._selected_pair_client_type = self.const.CLIENT_TYPE_IOS
        asyncio.run(flow._ensure_app_pairing_defaults())
        defaults = flow._discovered_defaults

        self.assertEqual(defaults[self.const.CONF_CLIENT_TYPE], self.const.CLIENT_TYPE_IOS)
        self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], "DJConnect iOS")
        self.assertIn("client_type=ios", defaults[self.const.CONF_PAIRING_URI])
        self.assertEqual(
            pending[pair_code][self.const.CONF_CLIENT_TYPE],
            self.const.CLIENT_TYPE_IOS,
        )
        self.assertFalse(pending[pair_code]["pairing_received"])

    def test_pairing_qr_helper_returns_inline_svg_data_uri(self) -> None:
        save_kwargs = {}

        class FakeQr:
            def save(self, out, **kwargs):
                save_kwargs.update(kwargs)
                out.write(b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h1v1z"/></svg>')

        fake_segno = types.ModuleType("segno")
        fake_segno.make = lambda *_args, **_kwargs: FakeQr()
        original_segno = sys.modules.get("segno")
        sys.modules["segno"] = fake_segno
        try:
            image = self.config_flow._qr_svg_data_uri("djconnect://pair?pair_code=123456")
        finally:
            if original_segno is None:
                sys.modules.pop("segno", None)
            else:
                sys.modules["segno"] = original_segno

        self.assertTrue(image.startswith("data:image/svg+xml;utf8,"))
        self.assertIn("%3Csvg", image)
        self.assertIn("fill%3D%22white%22", image)
        self.assertNotIn("background", save_kwargs)

    def test_pairing_qr_helper_falls_back_when_generation_fails(self) -> None:
        class BrokenQr:
            def save(self, out, **_kwargs):
                raise RuntimeError("qr failed")

        fake_segno = types.ModuleType("segno")
        fake_segno.make = lambda *_args, **_kwargs: BrokenQr()
        original_segno = sys.modules.get("segno")
        sys.modules["segno"] = fake_segno
        try:
            image = self.config_flow._qr_svg_data_uri("djconnect://pair?pair_code=123456")
        finally:
            if original_segno is None:
                sys.modules.pop("segno", None)
            else:
                sys.modules["segno"] = original_segno

        self.assertEqual(image, "")

    def test_app_pairing_defaults_fall_back_when_ha_url_lookup_fails(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP

        async def broken_ha_local_url(_hass, _conf):
            raise RuntimeError("network helper failed")

        original_ha_local_url = self.config_flow.async_ha_local_url
        self.config_flow.async_ha_local_url = broken_ha_local_url
        try:
            asyncio.run(flow._ensure_app_pairing_defaults())
        finally:
            self.config_flow.async_ha_local_url = original_ha_local_url

        self.assertEqual(
            flow._discovered_defaults["ha_local_url"],
            "http://homeassistant.local:8123",
        )
        self.assertIn("djconnect://pair?", flow._discovered_defaults["iphone_pairing_uri"])

    def test_user_schema_manual_defaults_are_not_esp32_specific(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        schema = flow._user_schema()
        defaults = {marker.key: marker.default for marker in schema}

        self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], "DJConnect")
        self.assertNotIn(self.const.CONF_CLIENT_TYPE, defaults)

    def test_pair_step_prefills_single_discovered_raspberry_pi_client(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
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
        self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], "DJConnect Pi")
        self.assertNotIn(self.const.CONF_CLIENT_TYPE, defaults)
        self.assertEqual(defaults[self.const.CONF_LOCAL_URL], "http://192.168.1.66:61234")

    def test_pair_step_ignores_app_discovery_and_generates_pair_code(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="nl-NL", internal_url="http://ha.local:8123")
        )
        clients = [
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.85:59331",
                device_id="djconnect-ios-2BBCE5B4D640",
                client_type=self.const.CLIENT_TYPE_IOS,
                device_name="DJConnect iPhone",
                pair_code="123456",
            ),
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.104:57770",
                device_id="djconnect-macos-1519E672097A",
                client_type=self.const.CLIENT_TYPE_MACOS,
                device_name="DJConnect Mac",
                pair_code="654321",
            ),
        ]

        async def fake_discover(_hass):
            return clients

        original_discover = self.config_flow.async_discover_djconnect_clients
        self.config_flow.async_discover_djconnect_clients = fake_discover
        try:
            result = asyncio.run(flow.async_step_pair())
        finally:
            self.config_flow.async_discover_djconnect_clients = original_discover

        schema = result["data_schema"].schema
        defaults = {marker.key: marker.default for marker in schema}
        placeholders = result["description_placeholders"]

        self.assertNotIn(self.config_flow.DISCOVERY_CLIENT_FIELD, defaults)
        self.assertNotIn(self.const.CONF_PAIR_CODE, defaults)
        self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], "DJConnect iOS")
        self.assertRegex(defaults[self.config_flow.APP_PAIR_CODE_DISPLAY_FIELD], r"^\d{6}$")
        self.assertEqual(
            defaults[self.config_flow.APP_HA_LOCAL_URL_DISPLAY_FIELD],
            "http://ha.local:8123",
        )
        self.assertNotIn(self.config_flow.APP_IPHONE_PAIRING_URI_FIELD, defaults)
        self.assertNotIn(self.config_flow.APP_WATCH_PAIRING_URI_FIELD, defaults)
        self.assertNotIn(self.const.CONF_CLIENT_TYPE, defaults)
        self.assertNotIn(self.const.CONF_LOCAL_URL, defaults)
        self.assertRegex(placeholders["pair_code"], r"^\d{6}$")
        self.assertEqual(placeholders["ha_local_url"], "http://ha.local:8123")

    def test_user_schema_offers_multiple_discovered_clients(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
        flow._discovered_clients = [
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.66:61234",
                device_id="djconnect-raspberry-pi-A1B2C3D4E5F6",
                client_type=self.const.CLIENT_TYPE_RASPBERRY_PI,
                device_name="DJConnect Pi",
            ),
        ]

        schema = flow._user_schema()
        keys = {marker.key for marker in schema}
        discovery_marker = next(
            marker for marker in schema if marker.key == self.config_flow.DISCOVERY_CLIENT_FIELD
        )

        self.assertIn(self.config_flow.DISCOVERY_CLIENT_FIELD, keys)
        self.assertIn(
            "djconnect-raspberry-pi-A1B2C3D4E5F6",
            schema[discovery_marker],
        )
        self.assertNotIn("djconnect-macos-68B74487726D", schema[discovery_marker])

    def test_app_pairing_waits_for_client_payload_before_continuing(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            data={self.const.DOMAIN: {}},
            config=types.SimpleNamespace(language="en-US", internal_url="http://ha.local:8123")
        )
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP
        flow._selected_pair_client_type = self.const.CLIENT_TYPE_MACOS
        flow.flow_id = "flow-1"
        asyncio.run(flow._ensure_app_pairing_defaults())

        result = asyncio.run(
            flow.async_step_pair(
                {
                    self.const.CONF_DEVICE_NAME: "DJConnect Mac",
                    self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_MACOS,
                }
            )
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "pair_app_macos_details")
        self.assertEqual(result["errors"]["base"], "app_pairing_not_received")
        self.assertFalse(getattr(flow, "_pairing", None))

    def test_app_pairing_uses_pending_http_pair_payload(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            data={self.const.DOMAIN: {}},
            config=types.SimpleNamespace(language="en-US", internal_url="http://ha.local:8123"),
        )
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP
        flow._selected_pair_client_type = self.const.CLIENT_TYPE_MACOS
        flow.flow_id = "flow-1"
        asyncio.run(flow._ensure_app_pairing_defaults())
        pair_code = flow._discovered_defaults[self.const.CONF_PAIR_CODE]
        flow.hass.data[self.const.DOMAIN]["config_flow_app_pairing_pending"][pair_code][
            "pairing_received"
        ] = {
            self.const.CONF_DEVICE_ID: "djconnect-macos-68B74487726D",
            self.const.CONF_DEVICE_NAME: "Peter Mac",
            self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_MACOS,
            self.const.CONF_DEVICE_TOKEN: "pending-device-token",
        }

        async def fake_set_unique_id(unique_id):
            flow._unique_id = unique_id

        flow.async_set_unique_id = fake_set_unique_id
        flow._abort_if_unique_id_configured = lambda: None

        async def fake_backend(user_input=None):
            return {"type": "next_step", "pairing": flow._pairing}

        flow.async_step_backend = fake_backend

        result = asyncio.run(
            flow.async_step_pair(
                {
                    self.const.CONF_DEVICE_NAME: "Fallback Name",
                    self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_MACOS,
                }
            )
        )

        self.assertEqual(flow._unique_id, "djconnect-macos-68B74487726D")
        self.assertEqual(
            result["pairing"][self.const.CONF_DEVICE_ID],
            "djconnect-macos-68B74487726D",
        )
        self.assertEqual(result["pairing"][self.const.CONF_DEVICE_NAME], "Peter Mac")
        self.assertEqual(
            result["pairing"][self.const.CONF_DEVICE_TOKEN],
            "pending-device-token",
        )
        self.assertNotIn(
            pair_code,
            flow.hass.data[self.const.DOMAIN]["config_flow_app_pairing_pending"],
        )

    def test_watch_app_pairing_uses_watch_proxy_pairing_uri(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            data={self.const.DOMAIN: {}},
            config=types.SimpleNamespace(language="en-US", internal_url="http://ha.local:8123")
        )
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP
        flow._selected_pair_client_type = self.const.CLIENT_TYPE_WATCHOS
        flow.flow_id = "flow-1"
        asyncio.run(flow._ensure_app_pairing_defaults())
        pair_code = flow._discovered_defaults[self.const.CONF_PAIR_CODE]
        flow.hass.data[self.const.DOMAIN]["config_flow_app_pairing_pending"][pair_code][
            "pairing_received"
        ] = {
            self.const.CONF_DEVICE_ID: "djconnect-watchos-68B74487726D",
            self.const.CONF_DEVICE_NAME: "Peter Apple Watch",
            self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_WATCHOS,
            self.const.CONF_DEVICE_TOKEN: "pending-watch-token",
        }

        async def fake_set_unique_id(unique_id):
            flow._unique_id = unique_id

        flow.async_set_unique_id = fake_set_unique_id
        flow._abort_if_unique_id_configured = lambda: None

        async def fake_backend(user_input=None):
            return {"type": "next_step", "pairing": flow._pairing}

        flow.async_step_backend = fake_backend

        result = asyncio.run(
            flow.async_step_pair(
                {
                    self.const.CONF_DEVICE_NAME: "Peter Apple Watch",
                    self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_WATCHOS,
                }
            )
        )

        self.assertEqual(
            result["pairing"][self.const.CONF_CLIENT_TYPE],
            self.const.CLIENT_TYPE_WATCHOS,
        )
        self.assertIn("client_type=watchos", result["pairing"][self.const.CONF_PAIRING_URI])
        self.assertNotIn(self.const.CONF_LOCAL_URL, result["pairing"])

    def test_user_schema_keeps_selected_local_device_name_without_suffix(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
        flow._discovered_clients = [
            self.config_flow.DiscoveredClient(
                local_url="http://192.168.1.66:61234",
                device_id="djconnect-raspberry-pi-A1B2C3D4E5F6",
                client_type=self.const.CLIENT_TYPE_RASPBERRY_PI,
                device_name="DJConnect Pi",
            ),
        ]
        flow._selected_discovered_key = "djconnect-raspberry-pi-A1B2C3D4E5F6"
        flow._apply_discovered_client(flow._discovered_clients[0])

        schema = flow._user_schema()
        defaults = {marker.key: marker.default for marker in schema}

        self.assertEqual(
            defaults[self.config_flow.DISCOVERY_CLIENT_FIELD],
            "djconnect-raspberry-pi-A1B2C3D4E5F6",
        )
        self.assertEqual(defaults[self.const.CONF_DEVICE_NAME], "DJConnect Pi")

    def test_user_schema_offers_multiple_discovered_clients_including_raspberry_pi(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
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
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
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
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
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

        async def fake_backend(user_input=None):
            return {"type": "next_step", "pairing": flow._pairing}

        flow.async_step_backend = fake_backend

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
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
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

    def test_pair_code_validation_accepts_only_six_digits(self) -> None:
        self.assertEqual(self.config_flow._default_local_url("123456"), "")
        self.assertEqual(self.config_flow._default_local_url("90B70990A994"), "")
        self.assertTrue(self.config_flow._valid_pair_code("123456"))
        self.assertFalse(self.config_flow._valid_pair_code("90B70990A994"))
        self.assertFalse(self.config_flow._valid_pair_code("abc123"))
        self.assertEqual(self.config_flow._default_local_url("12345"), "")

    def test_pairing_defaults_module_keeps_device_name_suffix_idempotent(self) -> None:
        defaults = importlib.import_module("custom_components.djconnect.pairing_defaults")

        self.assertEqual(
            defaults.device_name_for_client_type(
                "macos",
                "DJConnect macOS",
                suffixes={"macos": "macOS"},
            ),
            "DJConnect macOS",
        )
        self.assertEqual(
            defaults.device_name_for_client_type(
                "windows",
                "Studio",
                suffixes={"windows": "Windows"},
            ),
            "Studio Windows",
        )

    def test_client_identity_module_scopes_pairing_client_types(self) -> None:
        identity = importlib.import_module("custom_components.djconnect.client_identity")

        self.assertEqual(identity.default_pair_client_type("pair_local_device"), "esp32")
        self.assertEqual(identity.default_pair_client_type("pair_app"), "ios")
        self.assertEqual(
            identity.pair_client_type_options("pair_app"),
            ["ios", "macos", "watchos", "windows"],
        )
        self.assertTrue(identity.client_type_uses_local_device_api("raspberry_pi"))
        self.assertFalse(identity.client_type_uses_local_device_api("ios"))

    def test_discovery_selection_module_builds_defaults(self) -> None:
        selection = importlib.import_module("custom_components.djconnect.discovery_selection")
        discovery = importlib.import_module("custom_components.djconnect.discovery")
        client = discovery.DiscoveredClient(
            local_url="http://mac.local",
            device_id="djconnect-macos-ABCDEF123456",
            client_type="macos",
            device_name="Peter Mac",
            pair_code="123456",
        )

        self.assertEqual(selection.discovered_client_key(client), "djconnect-macos-ABCDEF123456")
        self.assertEqual(
            selection.discovered_client_options([client]),
            {
                "djconnect-macos-ABCDEF123456": (
                    "Peter Mac · djconnect-macos-ABCDEF123456 · mac.local"
                )
            },
        )
        self.assertEqual(selection.selected_discovered_client([client], "missing"), None)
        self.assertEqual(selection.selected_discovered_client([client], "djconnect-macos-ABCDEF123456"), client)
        self.assertEqual(
            selection.discovered_client_defaults(client),
            {
                "device_id": "djconnect-macos-ABCDEF123456",
                "device_name": "Peter Mac",
                "client_type": "macos",
                "local_url": "http://mac.local",
                "pair_code": "123456",
            },
        )

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
                self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
            ],
            "DJConnect apparaat koppelen ESP32 of Raspberry Pi",
        )
        self.assertEqual(
            self.config_flow._setup_method_names(en_hass)[
                self.const.SETUP_METHOD_PAIR_APP
            ],
            "Pair DJConnect app\n"
            "iPhone/iPad, Apple Watch, macOS or Windows",
        )
        self.assertEqual(
            self.config_flow._setup_method_names(nl_hass)[
                self.const.SETUP_METHOD_CONVERSATION_AGENT
            ],
            "DJConnect DJ Assist-agent\n"
            "Voor Home Assistant Assist-satellites",
        )
        self.assertEqual(
            self.config_flow._setup_method_names(nl_hass)[
                self.const.SETUP_METHOD_BLE_WIFI
            ],
            "ESP32 apparaat WiFi configureren (via Bluetooth)",
        )
        self.assertEqual(
            self.config_flow._setup_method_names(en_hass)[
                self.const.SETUP_METHOD_BLE_WIFI
            ],
            "Configure ESP32 device WiFi (over Bluetooth)",
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
            self.config_flow._options_action_names(nl_hass)[
                self.config_flow.OPTIONS_ACTION_CHANGE_MUSIC_BACKEND
            ],
            "Muziekbackend wijzigen",
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
        self.assertIn(self.config_flow.OPTIONS_ACTION_CHANGE_MUSIC_BACKEND, actions)
        self.assertIn(self.config_flow.OPTIONS_ACTION_SAVE, actions)

    def test_options_actions_hide_spotify_reauth_for_music_assistant(self) -> None:
        hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en-US"))

        actions = self.config_flow._options_actions_for_status(
            hass,
            {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_MUSIC_ASSISTANT},
        )

        self.assertNotIn(self.config_flow.OPTIONS_ACTION_SPOTIFY_REAUTH, actions)
        self.assertIn(self.config_flow.OPTIONS_ACTION_CHANGE_MUSIC_BACKEND, actions)

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

    def test_pair_schema_does_not_repeat_setup_method_choice(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE

        schema = flow._user_schema()
        keys = {marker.key for marker in schema}

        self.assertNotIn(self.const.CONF_SETUP_METHOD, keys)
        self.assertIn(self.const.CONF_PAIR_CODE, keys)

    def test_pair_step_uses_translated_pair_form_for_esp_pi_route(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE

        result = asyncio.run(flow.async_step_pair())

        self.assertEqual(result["step_id"], "pair_local_device_details")

    def test_pair_step_uses_translated_pair_form_for_apple_windows_route(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP

        result = asyncio.run(flow.async_step_pair())

        self.assertEqual(result["step_id"], "pair_app_ios_details")
        self.assertIs(result["last_step"], False)

    def test_pair_client_type_choice_is_not_final_step(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP

        result = asyncio.run(flow.async_step_pair_app())

        self.assertEqual(result["step_id"], "pair_app_type")
        self.assertIs(result["last_step"], False)

    def test_pair_type_step_variants_are_supported_by_flow_handlers(self) -> None:
        for setup_method, step_id, handler_name in (
            (
                self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE,
                "pair_local_device_type",
                "async_step_pair_local_device_type",
            ),
            (
                self.const.SETUP_METHOD_PAIR_APP,
                "pair_app_type",
                "async_step_pair_app_type",
            ),
        ):
            with self.subTest(setup_method=setup_method):
                flow = self.config_flow.DJConnectConfigFlow()
                flow.hass = types.SimpleNamespace(
                    config=types.SimpleNamespace(language="nl-NL")
                )
                flow._pairing_setup_method = setup_method

                self.assertTrue(hasattr(flow, handler_name))
                self.assertEqual(flow._pair_step_id(), step_id)
                result = asyncio.run(getattr(flow, handler_name)())

                self.assertEqual(result["type"], "form")
                self.assertEqual(result["step_id"], step_id)
                self.assertIs(result["last_step"], False)

    def test_app_detail_step_variants_are_supported_by_flow_handlers(self) -> None:
        for client_type, step_id, handler_name in (
            (
                self.const.CLIENT_TYPE_IOS,
                "pair_app_ios_details",
                "async_step_pair_app_ios_details",
            ),
            (
                self.const.CLIENT_TYPE_WATCHOS,
                "pair_app_watch_details",
                "async_step_pair_app_watch_details",
            ),
            (
                self.const.CLIENT_TYPE_MACOS,
                "pair_app_macos_details",
                "async_step_pair_app_macos_details",
            ),
            (
                self.const.CLIENT_TYPE_WINDOWS,
                "pair_app_windows_details",
                "async_step_pair_app_windows_details",
            ),
        ):
            with self.subTest(client_type=client_type):
                flow = self.config_flow.DJConnectConfigFlow()
                flow.hass = types.SimpleNamespace(
                    config=types.SimpleNamespace(language="nl-NL")
                )
                flow._pairing_setup_method = self.const.SETUP_METHOD_PAIR_APP
                flow._selected_pair_client_type = client_type

                self.assertTrue(hasattr(flow, handler_name))
                self.assertEqual(flow._pair_details_step_id(), step_id)
                result = asyncio.run(getattr(flow, handler_name)())

                self.assertEqual(result["type"], "form")
                self.assertEqual(result["step_id"], step_id)
                self.assertIs(result["last_step"], False)

    def test_setup_method_order_puts_conversation_agent_first(self) -> None:
        hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        methods = list(self.config_flow._setup_method_names(hass))

        self.assertEqual(methods[0], self.const.SETUP_METHOD_CONVERSATION_AGENT)

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

        self.assertEqual(result["step_id"], "backend")
        self.assertEqual(unique_ids, ["djconnect-conversation-agent"])
        self.assertTrue(flow._conversation_agent_only)
        self.assertEqual(
            flow._pairing[self.const.CONF_CLIENT_TYPE],
            self.const.CLIENT_TYPE_CONVERSATION_AGENT,
        )
        self.assertNotIn(self.const.CONF_DEVICE_TOKEN, flow._pairing)
        self.assertNotIn(self.const.CONF_LOCAL_URL, flow._pairing)

    def test_user_step_routes_app_setup_to_client_type_choice_first(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        result = asyncio.run(
            flow.async_step_user(
                {self.const.CONF_SETUP_METHOD: self.const.SETUP_METHOD_PAIR_APP}
            )
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "pair_app_type")
        self.assertIs(result["last_step"], False)

    def test_user_step_routes_local_setup_to_client_type_choice_first(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))

        result = asyncio.run(
            flow.async_step_user(
                {
                    self.const.CONF_SETUP_METHOD: (
                        self.const.SETUP_METHOD_PAIR_LOCAL_DEVICE
                    )
                }
            )
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "pair_local_device_type")
        self.assertIs(result["last_step"], False)

    def test_spotify_client_id_is_required_visible_field(self) -> None:
        schema = self.config_flow._spotify_schema()

        keys = {marker.key for marker in schema}

        self.assertIn(self.const.CONF_SPOTIFY_CLIENT_ID, keys)
        self.assertNotIn(self.const.CONF_SPOTIFY_MARKET, keys)

    def test_backend_step_routes_spotify_direct_to_oauth(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace()

        async def fake_spotify(user_input=None):
            return {"type": "form", "step_id": "spotify"}

        flow.async_step_spotify = fake_spotify

        result = asyncio.run(
            flow.async_step_backend(
                {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_SPOTIFY_DIRECT}
            )
        )

        self.assertEqual(result["step_id"], "spotify")
        self.assertEqual(
            flow._backend[self.const.CONF_MUSIC_BACKEND],
            self.const.MUSIC_BACKEND_SPOTIFY_DIRECT,
        )

    def test_backend_step_routes_music_assistant_without_spotify_oauth(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = _hass_with_music_assistant_player()

        async def fake_voice(user_input=None):
            return {"type": "form", "step_id": "voice"}

        flow.async_step_voice = fake_voice

        result = asyncio.run(
            flow.async_step_backend(
                {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_MUSIC_ASSISTANT}
            )
        )

        self.assertEqual(result["step_id"], "music_assistant")
        result = asyncio.run(
            flow.async_step_music_assistant(
                {self.const.CONF_MUSIC_ASSISTANT_PLAYER: "media_player.mass_living"}
            )
        )

        self.assertEqual(result["step_id"], "voice")
        self.assertEqual(flow._spotify, {})
        self.assertEqual(
            flow._backend[self.const.CONF_MUSIC_BACKEND],
            self.const.MUSIC_BACKEND_MUSIC_ASSISTANT,
        )

    def test_conversation_agent_music_assistant_setup_skips_voice_step(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = _hass_with_music_assistant_player()
        flow._conversation_agent_only = True
        flow._pairing = {
            self.const.CONF_SETUP_METHOD: self.const.SETUP_METHOD_CONVERSATION_AGENT,
            self.const.CONF_DEVICE_ID: "djconnect-conversation-agent",
            self.const.CONF_DEVICE_NAME: "DJConnect DJ",
            self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_CONVERSATION_AGENT,
        }

        result = asyncio.run(
            flow.async_step_music_assistant(
                {self.const.CONF_MUSIC_ASSISTANT_PLAYER: "media_player.mass_living"}
            )
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "DJConnect DJ")
        self.assertEqual(
            result["data"][self.const.CONF_MUSIC_BACKEND],
            self.const.MUSIC_BACKEND_MUSIC_ASSISTANT,
        )
        self.assertEqual(
            result["data"][self.const.CONF_MUSIC_ASSISTANT_PLAYER],
            "media_player.mass_living",
        )
        self.assertNotIn(self.const.CONF_DEVICE_TOKEN, result["data"])
        self.assertNotIn(self.const.CONF_LOCAL_URL, result["data"])
        self.assertEqual(
            flow._backend[self.const.CONF_MUSIC_ASSISTANT_PLAYER],
            "media_player.mass_living",
        )

    def test_backend_step_blocks_music_assistant_when_not_installed(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(data={}, states=None)

        result = asyncio.run(
            flow.async_step_backend(
                {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_MUSIC_ASSISTANT}
            )
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "backend")
        self.assertEqual(result["errors"]["base"], "music_assistant_unavailable")

    def test_backend_step_blocks_music_assistant_without_players(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(data={"music_assistant": object()}, states=None)

        result = asyncio.run(
            flow.async_step_backend(
                {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_MUSIC_ASSISTANT}
            )
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "backend")
        self.assertEqual(result["errors"]["base"], "music_assistant_no_players")

    def test_music_assistant_missing_blocks_setup(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(data={}, states=None)

        result = asyncio.run(flow.async_step_music_assistant())

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"]["base"], "music_assistant_unavailable")

    def test_music_assistant_without_players_blocks_setup(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(data={"music_assistant": object()}, states=None)

        result = asyncio.run(flow.async_step_music_assistant())

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"]["base"], "music_assistant_no_players")

    def test_music_assistant_rejects_non_media_player_entity_id(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = _hass_with_music_assistant_player()

        result = asyncio.run(
            flow.async_step_music_assistant(
                {self.const.CONF_MUSIC_ASSISTANT_PLAYER: "sensor.mass_living"}
            )
        )

        self.assertEqual(result["step_id"], "music_assistant")
        self.assertEqual(
            result["errors"][self.const.CONF_MUSIC_ASSISTANT_PLAYER],
            "music_assistant_player_invalid",
        )

    def test_music_assistant_rejects_stale_data_only_player(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = _hass_with_music_assistant_data_only_player()

        result = asyncio.run(
            flow.async_step_music_assistant(
                {self.const.CONF_MUSIC_ASSISTANT_PLAYER: "media_player.mass_missing"}
            )
        )

        self.assertEqual(result["step_id"], "music_assistant")
        self.assertEqual(
            result["errors"][self.const.CONF_MUSIC_ASSISTANT_PLAYER],
            "music_assistant_player_not_found",
        )

    def test_music_assistant_rejects_plain_media_player(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = _hass_with_music_assistant_and_plain_media_player()

        result = asyncio.run(
            flow.async_step_music_assistant(
                {
                    self.const.CONF_MUSIC_ASSISTANT_PLAYER: (
                        "media_player.kitchen_speaker"
                    )
                }
            )
        )

        self.assertEqual(result["step_id"], "music_assistant")
        self.assertEqual(
            result["errors"][self.const.CONF_MUSIC_ASSISTANT_PLAYER],
            "music_assistant_player_not_music_assistant",
        )

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
        self.assertIn(self.const.CONF_VOICE_PROFILE, keys)

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

    def test_spotify_oauth_external_step_has_visible_text(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="nl-NL"))
        flow._oauth = {
            "authorize_url": "https://accounts.spotify.com/authorize",
            "redirect_uri": "https://example.ui.nabu.casa/api/djconnect/spotify/callback",
        }

        result = asyncio.run(flow.async_step_spotify_oauth())

        self.assertEqual(result["type"], "external")
        self.assertEqual(result["title"], "DJConnect autoriseren bij Spotify")
        self.assertIn("Home Assistant opent Spotify", result["description"])

    def test_conversation_agent_spotify_oauth_skips_voice_step_after_callback(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(
            data={
                self.const.DOMAIN: {
                    "config_flow_oauth_results": {
                        "oauth-state": {
                            self.const.CONF_SPOTIFY_REFRESH_TOKEN: "refresh-token",
                            self.const.CONF_SPOTIFY_MARKET: "NL",
                            self.const.CONF_SPOTIFY_SCOPES: self.const.DEFAULT_SPOTIFY_SCOPES,
                        }
                    }
                }
            },
        )
        flow._conversation_agent_only = True
        flow._backend = {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_SPOTIFY_DIRECT}
        flow._pairing = {
            self.const.CONF_SETUP_METHOD: self.const.SETUP_METHOD_CONVERSATION_AGENT,
            self.const.CONF_DEVICE_ID: "djconnect-conversation-agent",
            self.const.CONF_DEVICE_NAME: "DJConnect DJ",
            self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_CONVERSATION_AGENT,
        }
        flow._spotify = {
            self.const.CONF_SPOTIFY_CLIENT_ID: "client-id",
            self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa",
        }

        result = asyncio.run(flow.async_step_spotify_oauth({"state": "oauth-state"}))

        self.assertEqual(result["type"], "external_done")
        self.assertEqual(result["next_step_id"], "finish_conversation_agent")

    def test_finish_conversation_agent_step_creates_entry(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow._conversation_agent_only = True
        flow._backend = {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_SPOTIFY_DIRECT}
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

        result = asyncio.run(flow.async_step_finish_conversation_agent())

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "DJConnect DJ")
        self.assertEqual(
            result["data"][self.const.CONF_CLIENT_TYPE],
            self.const.CLIENT_TYPE_CONVERSATION_AGENT,
        )
        self.assertNotIn(self.const.CONF_DEVICE_TOKEN, result["data"])
        self.assertNotIn(self.const.CONF_LOCAL_URL, result["data"])

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

        self.assertNotIn(self.const.CONF_DJ_RESPONSE_PROMPT_PRESET, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_PROMPT, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_ENABLED, keys)
        self.assertNotIn(self.const.CONF_ASSIST_PIPELINE_ID, keys)
        self.assertNotIn(self.const.CONF_FIRMWARE_CHANNEL, keys)
        self.assertNotIn(self.const.CONF_LOCAL_URL, keys)
        self.assertNotIn("last_step", form)

    def test_voice_step_hides_firmware_channel_for_app_clients(self) -> None:
        flow = self.config_flow.DJConnectConfigFlow()
        flow.hass = types.SimpleNamespace(states=None)
        flow._pairing = {
            self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_MACOS,
        }

        form = asyncio.run(flow.async_step_voice())
        keys = {marker.key for marker in form["data_schema"].schema}

        self.assertNotIn(self.const.CONF_FIRMWARE_CHANNEL, keys)

    def test_voice_defaults_for_app_clients_omit_firmware_channel(self) -> None:
        defaults = self.config_flow._voice_defaults_for_client(
            {
                self.const.CONF_FIRMWARE_CHANNEL: "beta",
            },
            client_type=self.const.CLIENT_TYPE_MACOS,
        )

        self.assertNotIn(self.const.CONF_FIRMWARE_CHANNEL, defaults)

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

        self.assertIs(form["last_step"], False)
        self.assertIn(self.config_flow.OPTIONS_ACTION_FIELD, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_ENABLED, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_PROMPT_PRESET, keys)
        self.assertNotIn(self.const.CONF_DJ_RESPONSE_PROMPT, keys)
        self.assertNotIn(self.const.CONF_SPOTIFY_SOURCE, keys)
        self.assertNotIn(self.const.CONF_LIKED_PROXY, keys)
        self.assertNotIn(self.const.CONF_LOCAL_URL, keys)
        self.assertNotIn(self.const.CONF_ASSIST_PIPELINE_ID, keys)
        self.assertNotIn(self.const.CONF_FIRMWARE_CHANNEL, keys)
        self.assertNotIn(self.const.CONF_MAX_AUDIO_BYTES, keys)
        self.assertNotIn(self.const.CONF_ALLOW_OTA_ON_BATTERY, keys)
        self.assertNotIn(self.const.CONF_MIN_BATTERY_FOR_OTA, keys)
        self.assertNotIn("show_advanced_options", keys)

    def test_options_flow_init_shows_change_music_backend_action(self) -> None:
        entry = types.SimpleNamespace(data={}, options={})
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en"))

        form = asyncio.run(flow.async_step_init())
        action_marker = next(
            marker
            for marker in form["data_schema"].schema
            if marker.key == self.config_flow.OPTIONS_ACTION_FIELD
        )

        self.assertIn(
            self.config_flow.OPTIONS_ACTION_CHANGE_MUSIC_BACKEND,
            form["data_schema"].schema[action_marker],
        )
        self.assertIn(
            self.config_flow.OPTIONS_ACTION_SAVE,
            form["data_schema"].schema[action_marker],
        )
        self.assertEqual(
            action_marker.default,
            self.config_flow.OPTIONS_ACTION_SAVE,
        )

    def test_options_music_backend_step_shows_current_backend(self) -> None:
        entry = types.SimpleNamespace(
            data={self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_SPOTIFY_DIRECT},
            options={},
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en"))

        form = asyncio.run(
            flow.async_step_init(
                {
                    self.config_flow.OPTIONS_ACTION_FIELD:
                        self.config_flow.OPTIONS_ACTION_CHANGE_MUSIC_BACKEND
                }
            )
        )
        marker = next(
            marker
            for marker in form["data_schema"].schema
            if marker.key == self.const.CONF_MUSIC_BACKEND
        )

        self.assertEqual(form["step_id"], "music_backend")
        self.assertEqual(marker.default, self.const.MUSIC_BACKEND_SPOTIFY_DIRECT)

    def test_options_switch_to_music_assistant_without_spotify_fields(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={
                self.const.CONF_DEVICE_TOKEN: "keep-device-token",
                self.const.CONF_SPOTIFY_REFRESH_TOKEN: "keep-refresh-token",
            },
            options={self.const.CONF_MUSIC_BACKEND_REVISION: 2},
        )
        state = types.SimpleNamespace(
            state="idle",
            attributes={
                "friendly_name": "Woonkamer",
                "integration": "music_assistant",
            },
        )
        states = types.SimpleNamespace(
            async_entity_ids=lambda domain: ["media_player.mass_woonkamer"],
            get=lambda entity_id: state,
        )
        runtime = types.SimpleNamespace(
            device_status={},
            memory=types.SimpleNamespace(
                _data={
                    "memories": {
                        "user": {"pending_followup": {"handled": False}}
                    }
                }
            ),
            update=lambda **kwargs: None,
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="en"),
            data={self.const.DOMAIN: {"entry-1": runtime, "music_assistant": object()}},
            states=states,
        )

        player_form = asyncio.run(
            flow.async_step_music_backend(
                {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_MUSIC_ASSISTANT}
            )
        )
        keys = {marker.key for marker in player_form["data_schema"].schema}
        result = asyncio.run(
            flow.async_step_music_assistant_player(
                {self.const.CONF_MUSIC_ASSISTANT_PLAYER: "media_player.mass_woonkamer"}
            )
        )

        self.assertEqual(player_form["step_id"], "music_assistant_player")
        self.assertNotIn(self.const.CONF_SPOTIFY_CLIENT_ID, keys)
        self.assertNotIn(self.const.CONF_HA_EXTERNAL_URL, keys)
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(
            result["data"][self.const.CONF_MUSIC_BACKEND],
            self.const.MUSIC_BACKEND_MUSIC_ASSISTANT,
        )
        self.assertEqual(result["data"][self.const.CONF_MUSIC_BACKEND_REVISION], 3)
        self.assertEqual(entry.data[self.const.CONF_DEVICE_TOKEN], "keep-device-token")
        self.assertEqual(
            entry.data[self.const.CONF_SPOTIFY_REFRESH_TOKEN],
            "keep-refresh-token",
        )
        pending = runtime.memory._data["memories"]["user"]["pending_followup"]
        self.assertTrue(pending["handled"])
        self.assertEqual(pending["stale_reason"], "music_backend_changed")

    def test_options_music_assistant_missing_has_clear_error(self) -> None:
        entry = types.SimpleNamespace(data={}, options={})
        states = types.SimpleNamespace(
            async_entity_ids=lambda domain: [],
            get=lambda entity_id: None,
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="en"),
            data={},
            states=states,
        )

        result = asyncio.run(
            flow.async_step_music_backend(
                {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_MUSIC_ASSISTANT}
            )
        )

        self.assertEqual(result["errors"]["base"], "music_assistant_not_configured")

    def test_options_music_assistant_without_players_has_clear_error(self) -> None:
        entry = types.SimpleNamespace(data={}, options={})
        states = types.SimpleNamespace(
            async_entity_ids=lambda domain: [],
            get=lambda entity_id: None,
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(language="en"),
            data={"music_assistant": object()},
            states=states,
        )

        result = asyncio.run(
            flow.async_step_music_backend(
                {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_MUSIC_ASSISTANT}
            )
        )

        self.assertEqual(result["errors"]["base"], "music_assistant_no_players")

    def test_options_music_assistant_rejects_plain_media_player(self) -> None:
        entry = types.SimpleNamespace(data={"entry_id": "entry-1"}, options={})
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = _hass_with_music_assistant_and_plain_media_player()

        result = asyncio.run(
            flow.async_step_music_assistant_player(
                {
                    self.const.CONF_MUSIC_ASSISTANT_PLAYER: (
                        "media_player.kitchen_speaker"
                    )
                }
            )
        )

        self.assertEqual(result["step_id"], "music_assistant_player")
        self.assertEqual(
            result["errors"][self.const.CONF_MUSIC_ASSISTANT_PLAYER],
            "music_assistant_player_not_music_assistant",
        )

    def test_options_switch_to_spotify_direct_requires_oauth_when_missing(self) -> None:
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={self.const.CONF_HA_EXTERNAL_URL: "https://example.ui.nabu.casa"},
            options={self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_MUSIC_ASSISTANT},
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.flow_id = "flow-1"
        flow.hass = types.SimpleNamespace(data={})

        result = asyncio.run(
            flow.async_step_music_backend(
                {self.const.CONF_MUSIC_BACKEND: self.const.MUSIC_BACKEND_SPOTIFY_DIRECT}
            )
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"]["base"], "oauth_setup_failed")

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
            self.const.DEFAULT_DJ_RESPONSE_PROMPT,
        )

    def test_options_flow_save_drops_firmware_channel_for_app_clients(self) -> None:
        entry = types.SimpleNamespace(
            data={
                self.const.CONF_CLIENT_TYPE: self.const.CLIENT_TYPE_IOS,
                self.const.CONF_FIRMWARE_CHANNEL: "beta",
            },
            options={},
        )
        flow = self.config_flow.DJConnectOptionsFlow(entry)
        flow.hass = types.SimpleNamespace(config=types.SimpleNamespace(language="en"))

        result = asyncio.run(
            flow.async_step_init(
                {
                    self.config_flow.OPTIONS_ACTION_FIELD: self.config_flow.OPTIONS_ACTION_SAVE,
                }
            )
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertNotIn(self.const.CONF_FIRMWARE_CHANNEL, result["data"])

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
        self.assertIn("Home Assistant opens Spotify", external["description"])
        self.assertEqual(
            external["description_placeholders"]["title"],
            "Reauthorize Spotify",
        )
        self.assertIn(
            "Home Assistant opens Spotify",
            external["description_placeholders"]["description"],
        )
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
