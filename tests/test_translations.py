from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "custom_components" / "djconnect" / "translations"
INTEGRATION = ROOT / "custom_components" / "djconnect"
SUPPORTED_LANGUAGES = ("en", "nl", "de", "fr", "es")
DOCS = [
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
    ROOT / "HANDOFF.md",
    ROOT / "TODO.md",
    ROOT / "ISSUES.md",
    ROOT / "SYNC_PROMPTS.md",
]

CONFIG_FLOW_ERROR_KEYS = {
    "missing_pair_code",
    "invalid_pair_code",
    "spotify_client_id_required",
    "external_url_required",
    "external_url_https_required",
    "external_url_invalid",
    "oauth_setup_failed",
    "oauth_not_completed",
    "oauth_failed",
    "assist_pipeline_required",
    "ble_device_required",
    "wifi_ssid_required",
    "ble_wifi_failed",
    "repair_pairing_failed",
    "pairing_info_unavailable",
}

BLE_WIFI_DATA_KEYS = {
    "ble_action",
    "ble_address",
    "wifi_ssid",
    "wifi_password",
}

PAIR_DATA_KEYS = {
    "pair_code",
    "device_name",
    "client_type",
    "local_url",
    "discovered_client",
}

REPAIR_PAIRING_DATA_KEYS = {
    "pair_code",
    "local_url",
}

APP_DETAIL_STEPS = {
    "pair_app_ios_details",
    "pair_app_watch_details",
    "pair_app_macos_details",
    "pair_app_windows_details",
}

VOICE_OPTION_DATA_KEYS = {
    "assist_pipeline_id",
    "client_type",
    "local_url",
    "firmware_channel",
    "options_action",
    "voice_profile",
}

ENTITY_TRANSLATION_KEYS = {
    ("sensor", "status"),
    ("sensor", "last_command"),
    ("sensor", "battery"),
    ("sensor", "wifi_rssi"),
    ("sensor", "firmware_version"),
    ("sensor", "last_track"),
    ("sensor", "spotify_status"),
    ("sensor", "ha_pairing_status"),
    ("sensor", "sound_output"),
    ("sensor", "playback_available"),
    ("sensor", "queue"),
    ("sensor", "playlists"),
    ("sensor", "outputs"),
    ("sensor", "screen_state"),
    ("sensor", "led_state"),
    ("button", "test_dj_response"),
    ("button", "next_track"),
    ("button", "previous_track"),
    ("button", "play_pause"),
    ("button", "refresh_up_next"),
    ("button", "reboot_device"),
    ("button", "restart_device"),
    ("button", "shutdown_device"),
    ("number", "volume"),
    ("number", "brightness"),
    ("number", "screen_timeout"),
    ("number", "speaker_volume"),
    ("select", "sound_output"),
    ("select", "repeat_state"),
    ("select", "language"),
    ("select", "turn_off_after"),
    ("select", "theme"),
    ("select", "log_level"),
    ("switch", "shuffle"),
    ("switch", "wake_word"),
    ("update", "firmware"),
}

ISSUE_TRANSLATION_KEYS = {
    "missing_device_token",
    "missing_spotify_oauth_scopes",
    "missing_spotify_refresh_token",
    "spotify_refresh_token_revoked",
}

SPOTIFY_DISCLAIMER_PARTS = {
    "en": (
        "Spotify is a trademark of Spotify AB.",
        "DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.",
    ),
    "nl": (
        "Spotify is een handelsmerk van Spotify AB.",
        "DJConnect is niet verbonden aan, goedgekeurd door of gesponsord door Spotify AB.",
    ),
    "de": (
        "Spotify is a trademark of Spotify AB.",
        "DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.",
    ),
    "fr": (
        "Spotify is a trademark of Spotify AB.",
        "DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.",
    ),
    "es": (
        "Spotify is a trademark of Spotify AB.",
        "DJConnect is not affiliated with, endorsed by, or sponsored by Spotify AB.",
    ),
}

NON_ENGLISH_FORBIDDEN_PHRASES = (
    "Start with the route that matches your setup",
    "Choose an automatically discovered DJConnect client",
    "Use this code in macOS/Windows",
    "Choose which local DJConnect device",
    "The 6 digit pairing code shown",
    "Use this route for ESP32",
    "Use this route for iPhone/iPad",
    "Select a DJConnect device in setup mode",
    "Assist pipeline used by DJConnect devices",
    "Put the DJConnect device in pairing mode",
    "Enter the pairing code shown",
    "Create your own Spotify Developer app",
    "External Home Assistant URL Spotify returns",
    "After approval you return to Home Assistant",
    "DJConnect Spotify OAuth succeeded",
    "Choose the backend DJConnect uses",
    "Spotify authorization could not be started",
    "Spotify authorization has not completed yet",
    "No usable Music Assistant players were found",
    "Manage DJConnect actions such as changing",
    "Configured local Client address",
    "This DJConnect client is missing",
    "Finish Spotify authorization",
    "If you approved Spotify access",
    "DJConnect needs Spotify permission",
    "expired or was revoked",
    "DJConnect has not received pairing details",
    "could not rotate the install token",
    "not installed or configured in Home Assistant",
    "does not appear to be a Music Assistant player",
)

ALLOWED_IDENTICAL_NON_ENGLISH_VALUES = {
    "nl": {
        "config.step.pair.data.app_iphone_pairing_uri",
        "config.step.pair.data.app_watch_pairing_uri",
        "config.step.pair_app.data.app_iphone_pairing_uri",
        "config.step.pair_app.data.app_watch_pairing_uri",
        "config.step.central_api.data.ha_install_id",
        "config.step.music_assistant.title",
        "config.step.music_assistant.data.music_assistant_player",
        "config.step.init.data.music_assistant_player",
        "options.step.init.data.music_assistant_player",
        "options.step.music_assistant_player.title",
        "options.step.music_assistant_player.data.music_assistant_player",
        "options.step.central_api.data.ha_install_id",
    },
    "de": {
        "config.step.pair.data.app_iphone_pairing_uri",
        "config.step.pair.data.app_watch_pairing_uri",
        "config.step.pair_app.data.app_iphone_pairing_uri",
        "config.step.pair_app.data.app_watch_pairing_uri",
    },
    "fr": {
        "config.step.pair.data.app_iphone_pairing_uri",
        "config.step.pair.data.app_watch_pairing_uri",
        "config.step.pair_app.data.app_iphone_pairing_uri",
        "config.step.pair_app.data.app_watch_pairing_uri",
    },
    "es": {
        "config.step.pair.data.app_iphone_pairing_uri",
        "config.step.pair.data.app_watch_pairing_uri",
        "config.step.pair_app.data.app_iphone_pairing_uri",
        "config.step.pair_app.data.app_watch_pairing_uri",
    },
}


class TranslationTest(unittest.TestCase):
    def test_translation_files_cover_base_strings_schema(self) -> None:
        base = _leaf_paths(json.loads((INTEGRATION / "strings.json").read_text()))
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                data = json.loads((TRANSLATIONS / f"{language}.json").read_text())
                missing = base - _leaf_paths(data)
                self.assertFalse(
                    missing,
                    f"Missing {language} schema translations: {sorted(missing)}",
                )

    def test_config_flow_error_keys_are_translated(self) -> None:
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                data = json.loads((TRANSLATIONS / f"{language}.json").read_text())
                errors = data["config"]["error"]
                missing = CONFIG_FLOW_ERROR_KEYS - set(errors)
                self.assertFalse(missing, f"Missing {language} translations: {sorted(missing)}")

    def test_spotify_reauth_options_external_step_has_visible_text(self) -> None:
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                data = json.loads((TRANSLATIONS / f"{language}.json").read_text())
                steps = data["options"]["step"]
                for step_id in ("spotify_reauth", "spotify_reauth_done"):
                    self.assertIn(step_id, steps)
                    self.assertTrue(steps[step_id].get("title"))
                    self.assertTrue(steps[step_id].get("description"))

    def test_repair_issues_have_user_visible_text(self) -> None:
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                data = json.loads((TRANSLATIONS / f"{language}.json").read_text())
                issues = data["issues"]
                for issue_key in ISSUE_TRANSLATION_KEYS:
                    self.assertIn(issue_key, issues)
                    self.assertTrue(issues[issue_key].get("title"))
                    self.assertTrue(
                        issues[issue_key].get("description")
                        or issues[issue_key].get("fix_flow")
                    )
                self.assertTrue(issues["missing_device_token"].get("description"))

    def test_ble_wifi_fields_are_translated(self) -> None:
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                data = json.loads((TRANSLATIONS / f"{language}.json").read_text())
                step = data["config"]["step"]["ble_wifi"]
                missing_labels = BLE_WIFI_DATA_KEYS - set(step["data"])
                missing_descriptions = BLE_WIFI_DATA_KEYS - set(step["data_description"])
                self.assertFalse(
                    missing_labels,
                    f"Missing {language} BLE labels: {sorted(missing_labels)}",
                )
                self.assertFalse(
                    missing_descriptions,
                    f"Missing {language} BLE descriptions: {sorted(missing_descriptions)}",
                )

    def test_pair_fields_are_translated(self) -> None:
        base = json.loads((INTEGRATION / "strings.json").read_text())
        for data, language in [(base, "base")] + [
            (json.loads((TRANSLATIONS / f"{language}.json").read_text()), language)
            for language in SUPPORTED_LANGUAGES
        ]:
            with self.subTest(language=language):
                step = data["config"]["step"]["pair"]
                missing_labels = PAIR_DATA_KEYS - set(step["data"])
                missing_descriptions = PAIR_DATA_KEYS - set(step["data_description"])
                self.assertFalse(
                    missing_labels,
                    f"Missing {language} pair labels: {sorted(missing_labels)}",
                )
                self.assertFalse(
                    missing_descriptions,
                    f"Missing {language} pair descriptions: {sorted(missing_descriptions)}",
                )

    def test_repair_pairing_fields_are_translated(self) -> None:
        base = json.loads((INTEGRATION / "strings.json").read_text())
        for data, language in [(base, "base")] + [
            (json.loads((TRANSLATIONS / f"{language}.json").read_text()), language)
            for language in SUPPORTED_LANGUAGES
        ]:
            with self.subTest(language=language):
                for section in ("config", "options"):
                    step = data[section]["step"].get("repair_pairing")
                    if step is None:
                        continue
                    missing_labels = REPAIR_PAIRING_DATA_KEYS - set(step["data"])
                    missing_descriptions = REPAIR_PAIRING_DATA_KEYS - set(
                        step["data_description"]
                    )
                    self.assertFalse(
                        missing_labels,
                        f"Missing {language} {section} repair labels: {sorted(missing_labels)}",
                    )
                    self.assertFalse(
                        missing_descriptions,
                        f"Missing {language} {section} repair descriptions: {sorted(missing_descriptions)}",
                    )

    def test_app_pairing_copy_uses_iphone_ipad_label(self) -> None:
        for path in [
            INTEGRATION / "strings.json",
            TRANSLATIONS / "en.json",
            TRANSLATIONS / "nl.json",
            TRANSLATIONS / "de.json",
            TRANSLATIONS / "fr.json",
            TRANSLATIONS / "es.json",
        ]:
            with self.subTest(path=path.name):
                steps = json.loads(path.read_text())["config"]["step"]
                app_text = json.dumps(
                    {
                        key: steps[key]
                        for key in steps
                        if key.startswith("pair_app")
                    }
                )
                self.assertIn("iPhone/iPad", app_text)
                self.assertNotIn("iPhone app", app_text)
                self.assertNotIn("iPhone App", app_text)

    def test_app_detail_titles_include_djconnect_brand(self) -> None:
        expected_prefix = {
            "strings.json": "DJConnect ",
            "nl.json": "DJConnect ",
            "en.json": "Pair DJConnect ",
            "de.json": "DJConnect ",
            "fr.json": "Associer l’application DJConnect ",
            "es.json": "Emparejar la app DJConnect ",
        }
        for path in [
            INTEGRATION / "strings.json",
            TRANSLATIONS / "en.json",
            TRANSLATIONS / "nl.json",
            TRANSLATIONS / "de.json",
            TRANSLATIONS / "fr.json",
            TRANSLATIONS / "es.json",
        ]:
            with self.subTest(path=path.name):
                steps = json.loads(path.read_text())["config"]["step"]
                for step_id in APP_DETAIL_STEPS:
                    title = steps[step_id]["title"]
                    self.assertTrue(
                        title.startswith(expected_prefix[path.name]),
                        f"{path.name} {step_id} title lacks DJConnect prefix: {title}",
                    )

    def test_options_flow_voice_fields_are_translated(self) -> None:
        base = json.loads((INTEGRATION / "strings.json").read_text())
        missing_base = VOICE_OPTION_DATA_KEYS - set(
            base["options"]["step"]["init"]["data"]
        )
        missing_base_descriptions = VOICE_OPTION_DATA_KEYS - set(
            base["options"]["step"]["init"]["data_description"]
        )
        self.assertNotIn("dj_response_enabled", base["options"]["step"]["init"]["data"])
        self.assertNotIn(
            "dj_response_enabled",
            base["options"]["step"]["init"]["data_description"],
        )
        self.assertFalse(missing_base, f"Missing base option labels: {sorted(missing_base)}")
        self.assertFalse(
            missing_base_descriptions,
            f"Missing base option descriptions: {sorted(missing_base_descriptions)}",
        )
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                data = json.loads((TRANSLATIONS / f"{language}.json").read_text())
                step = data["options"]["step"]["init"]
                missing_labels = VOICE_OPTION_DATA_KEYS - set(step["data"])
                missing_descriptions = VOICE_OPTION_DATA_KEYS - set(
                    step["data_description"]
                )
                self.assertNotIn("dj_response_enabled", step["data"])
                self.assertNotIn("dj_response_enabled", step["data_description"])
                self.assertFalse(
                    missing_labels,
                    f"Missing {language} option labels: {sorted(missing_labels)}",
                )
                self.assertFalse(
                    missing_descriptions,
                    f"Missing {language} option descriptions: {sorted(missing_descriptions)}",
                )

    def test_entity_translation_keys_are_translated(self) -> None:
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                data = json.loads((TRANSLATIONS / f"{language}.json").read_text())
                entity = data["entity"]
                missing = [
                    f"{platform}.{key}"
                    for platform, key in ENTITY_TRANSLATION_KEYS
                    if key not in entity.get(platform, {})
                ]
                self.assertFalse(missing, f"Missing {language} entity translations: {missing}")

    def test_entities_use_translation_keys(self) -> None:
        for filename in (
            "sensor.py",
            "button.py",
            "number.py",
            "select.py",
            "switch.py",
            "update.py",
        ):
            with self.subTest(filename=filename):
                text = (INTEGRATION / filename).read_text()
                self.assertIn("_attr_translation_key", text)
                self.assertNotIn("_attr_name =", text)

    def test_all_supported_translation_files_exist(self) -> None:
        missing = [
            language
            for language in SUPPORTED_LANGUAGES
            if not (TRANSLATIONS / f"{language}.json").exists()
        ]
        self.assertFalse(missing, f"Missing supported translation files: {missing}")

    def test_spotify_disclaimer_is_preserved_in_supported_languages(self) -> None:
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                data = json.loads((TRANSLATIONS / f"{language}.json").read_text())
                text = json.dumps(data, ensure_ascii=False)
                for required in SPOTIFY_DISCLAIMER_PARTS[language]:
                    self.assertIn(required, text)

    def test_non_english_translations_do_not_keep_obvious_english_copy(self) -> None:
        for language in ("de", "fr", "es"):
            with self.subTest(language=language):
                text = (TRANSLATIONS / f"{language}.json").read_text()
                hits = [phrase for phrase in NON_ENGLISH_FORBIDDEN_PHRASES if phrase in text]
                self.assertFalse(hits, f"{language} keeps English copy: {hits}")

    def test_non_english_translations_do_not_silently_copy_long_english_values(
        self,
    ) -> None:
        english = _leaf_values(json.loads((TRANSLATIONS / "en.json").read_text()))
        for language in ("nl", "de", "fr", "es"):
            with self.subTest(language=language):
                data = _leaf_values(json.loads((TRANSLATIONS / f"{language}.json").read_text()))
                copied = [
                    path
                    for path, value in data.items()
                    if (
                        isinstance(value, str)
                        and len(value) >= 20
                        and value == english.get(path)
                        and path
                        not in ALLOWED_IDENTICAL_NON_ENGLISH_VALUES.get(language, set())
                    )
                ]
                self.assertFalse(
                    copied,
                    f"{language} copies English values without an allowlist entry: {copied}",
                )

    def test_no_old_branding_in_user_facing_integration_files(self) -> None:
        checked_files = [
            *TRANSLATIONS.glob("*.json"),
            INTEGRATION / "services.yaml",
            INTEGRATION / "strings.json",
        ]
        forbidden = ("openai", "open ai", "lilygo", "t-embed")
        for path in checked_files:
            with self.subTest(path=path.name):
                text = path.read_text().lower()
                hits = [word for word in forbidden if word in text]
                self.assertFalse(hits, f"{path} contains old branding: {hits}")

    def test_removed_message_bus_wording_stays_out_of_docs_and_ui(self) -> None:
        checked_files = [
            *DOCS,
            *TRANSLATIONS.glob("*.json"),
            INTEGRATION / "services.yaml",
            INTEGRATION / "strings.json",
        ]
        for path in checked_files:
            if not path.exists():
                continue
            with self.subTest(path=path.name):
                self.assertNotIn("m" + "qtt", path.read_text().lower())


def _leaf_paths(value: object, prefix: str = "") -> set[str]:
    if not isinstance(value, dict):
        return {prefix}
    paths: set[str] = set()
    for key, child in value.items():
        child_prefix = f"{prefix}.{key}" if prefix else str(key)
        paths.update(_leaf_paths(child, child_prefix))
    return paths


def _leaf_values(value: object, prefix: str = "") -> dict[str, object]:
    if not isinstance(value, dict):
        return {prefix: value}
    values: dict[str, object] = {}
    for key, child in value.items():
        child_prefix = f"{prefix}.{key}" if prefix else str(key)
        values.update(_leaf_values(child, child_prefix))
    return values


if __name__ == "__main__":
    unittest.main()
