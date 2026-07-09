from __future__ import annotations

import asyncio
import importlib
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs


class FakeState:
    def __init__(self, state="idle", **attributes):
        self.state = state
        self.attributes = attributes


class FakeStates:
    def __init__(self, states):
        self._states = states

    def async_entity_ids(self, domain):
        return [entity_id for entity_id in self._states if entity_id.startswith(f"{domain}.")]

    def get(self, entity_id):
        return self._states.get(entity_id)


class FakeServices:
    def __init__(self):
        self.calls = []

    async def async_call(self, domain, service, data, blocking=False):
        self.calls.append((domain, service, data, blocking))


class AnnouncementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_http_stubs()
        cls.const = importlib.import_module("custom_components.djconnect.const")
        cls.announcements = importlib.import_module("custom_components.djconnect.announcements")

    def _hass(self):
        return types.SimpleNamespace(
            states=FakeStates(
                {
                    "media_player.voice_preview": FakeState(
                        "idle",
                        friendly_name="Voice Preview",
                        supported_features=512,
                    ),
                    "media_player.display_only": FakeState(
                        "idle",
                        friendly_name="Display Only",
                        supported_features=0,
                    ),
                    "light.kitchen": FakeState("on", friendly_name="Kitchen"),
                }
            ),
            services=FakeServices(),
        )

    def _runtime(self, client_type="ios", speaker="media_player.voice_preview", output=None):
        config = {
            self.const.CONF_CLIENT_TYPE: client_type,
            self.const.CONF_DJ_ANNOUNCEMENT_SPEAKER: speaker,
        }
        if output:
            config[self.const.CONF_DJ_ANNOUNCEMENT_OUTPUT] = output
        return types.SimpleNamespace(
            config=config,
            device_status={"client_type": client_type},
        )

    def test_speaker_options_filter_on_play_media(self):
        options = self.announcements.announcement_speaker_options(self._hass())

        self.assertIn("media_player.voice_preview", options)
        self.assertNotIn("media_player.display_only", options)
        self.assertNotIn("light.kitchen", options)

    def test_pi_supports_text_only_without_speaker(self):
        runtime = self._runtime(client_type="raspberry_pi", speaker="")

        capabilities = self.announcements.announcement_capabilities(runtime)

        self.assertEqual(capabilities["supported_outputs"], ["text_only"])
        self.assertEqual(capabilities["output"], "text_only")

    def test_app_without_speaker_locks_speaker_modes(self):
        runtime = self._runtime(client_type="ios", speaker="", output="both")

        capabilities = self.announcements.announcement_capabilities(runtime)

        self.assertEqual(capabilities["supported_outputs"], ["client_device", "text_only"])
        self.assertIn("both", capabilities["locked_outputs"])
        self.assertIn("ha_speaker", capabilities["locked_outputs"])
        self.assertEqual(capabilities["output"], "client_device")

    def test_pi_with_speaker_defaults_to_ha_speaker(self):
        runtime = self._runtime(client_type="raspberry_pi", speaker="media_player.voice_preview")

        capabilities = self.announcements.announcement_capabilities(runtime)

        self.assertEqual(capabilities["supported_outputs"], ["text_only", "ha_speaker"])
        self.assertEqual(capabilities["default_output"], "ha_speaker")
        self.assertEqual(capabilities["output"], "ha_speaker")

    def test_speaker_validation_rejects_non_play_media_player(self):
        error = self.announcements.validate_announcement_speaker(
            self._hass(),
            "media_player.display_only",
        )

        self.assertEqual(error, "announcement_speaker_no_play_media")

    def test_both_returns_audio_url_and_calls_ha_speaker(self):
        hass = self._hass()
        runtime = self._runtime(output="both")
        response = {"text": "Hallo", "dj_text": "Hallo", "assistant_message": {}}
        original = self.announcements.async_create_dj_audio_url

        async def audio_url(*args):
            return "http://ha.local/api/djconnect/v1/tts/abc.mp3"

        self.announcements.async_create_dj_audio_url = audio_url
        try:
            result = asyncio.run(
                self.announcements.async_apply_announcement_output(
                    hass,
                    runtime,
                    response,
                    payload={"client_type": "ios"},
                    generate_audio=True,
                )
            )
        finally:
            self.announcements.async_create_dj_audio_url = original

        self.assertEqual(result["audio_url"], "http://ha.local/api/djconnect/v1/tts/abc.mp3")
        self.assertEqual(result["announcement"]["delivery"], "both")
        self.assertEqual(hass.services.calls[0][0:2], ("media_player", "play_media"))
        self.assertEqual(
            hass.services.calls[0][2]["entity_id"],
            "media_player.voice_preview",
        )

    def test_ha_speaker_does_not_return_client_audio_url(self):
        hass = self._hass()
        runtime = self._runtime(output="ha_speaker")
        response = {"text": "Hallo", "dj_text": "Hallo", "assistant_message": {}}
        original = self.announcements.async_create_dj_audio_url

        async def audio_url(*args):
            return "http://ha.local/api/djconnect/v1/tts/abc.mp3"

        self.announcements.async_create_dj_audio_url = audio_url
        try:
            result = asyncio.run(
                self.announcements.async_apply_announcement_output(
                    hass,
                    runtime,
                    response,
                    payload={"client_type": "ios"},
                    generate_audio=True,
                )
            )
        finally:
            self.announcements.async_create_dj_audio_url = original

        self.assertNotIn("audio_url", result)
        self.assertEqual(result["announcement"]["audio_url"], None)
        self.assertEqual(result["announcement"]["audio_response_effective"], "server_only")
        self.assertEqual(hass.services.calls[0][2]["entity_id"], "media_player.voice_preview")

    def test_text_only_skips_tts_and_service_call(self):
        hass = self._hass()
        runtime = self._runtime(output="text_only")
        response = {"text": "Hallo", "dj_text": "Hallo", "assistant_message": {}}
        calls = []
        original = self.announcements.async_create_dj_audio_url

        async def audio_url(*args):
            calls.append(args)
            return "http://ha.local/api/djconnect/v1/tts/abc.mp3"

        self.announcements.async_create_dj_audio_url = audio_url
        try:
            result = asyncio.run(
                self.announcements.async_apply_announcement_output(
                    hass,
                    runtime,
                    response,
                    payload={"client_type": "ios"},
                    generate_audio=True,
                )
            )
        finally:
            self.announcements.async_create_dj_audio_url = original

        self.assertEqual(calls, [])
        self.assertEqual(hass.services.calls, [])
        self.assertEqual(result["announcement"]["delivery"], "text_only")
        self.assertNotIn("audio_url", result)


if __name__ == "__main__":
    unittest.main()
