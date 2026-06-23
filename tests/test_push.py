from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def install_push_stubs() -> None:
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    homeassistant.helpers = helpers
    if not hasattr(aiohttp_client, "async_get_clientsession"):
        aiohttp_client.async_get_clientsession = lambda hass: hass.session
    package = types.ModuleType("custom_components.djconnect")
    package.__path__ = [str(ROOT / "custom_components" / "djconnect")]
    sys.modules.setdefault("custom_components.djconnect", package)


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status = status
        self.data = data if data is not None else {"success": True}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self.data


class FakeSession:
    def __init__(self):
        self.calls = []
        self.response = FakeResponse()

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class PushTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_push_stubs()
        cls.push = importlib.import_module("custom_components.djconnect.push")
        cls.central_api = importlib.import_module("custom_components.djconnect.central_api")

    def setUp(self) -> None:
        self.original_session = self.central_api.async_get_clientsession
        self.central_api.async_get_clientsession = lambda hass: hass.session

    def tearDown(self) -> None:
        self.central_api.async_get_clientsession = self.original_session

    def _runtime(self, *, token: str | None = "djci_test_install_token"):
        options = {
            "api_base_url": "https://api.djconnect.dev",
            "ha_install_id": "ha-install-1",
        }
        if token:
            options["djconnect_install_token"] = token
        return types.SimpleNamespace(
            entry=types.SimpleNamespace(entry_id="entry-1", data={}, options=options)
        )

    def test_disabled_without_relay_config_does_not_raise(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime(token=None)

        result = asyncio.run(
            self.push.async_send_event(
                hass,
                runtime,
                user_id="user-1",
                event_type="ask_dj_response",
                history_revision=1,
                explicit_user_request=True,
            )
        )

        self.assertTrue(result["success"])
        self.assertFalse(result["push_supported"])
        self.assertTrue(result["disabled"])
        self.assertEqual(hass.session.calls, [])

    def test_register_bootstraps_install_token_with_pairing_proof(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession(), config_entries=types.SimpleNamespace())
        hass.config_entries.async_update_entry = lambda entry, **kwargs: setattr(entry, "options", kwargs["options"])
        hass.session.response = FakeResponse(data={"success": True, "install_token": "djci_created_token"})
        runtime = self._runtime(token=None)

        result = asyncio.run(
            self.push.async_register(
                hass,
                runtime,
                user_id="user-1",
                payload={
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "push_token": "token-secret-value",
                    "push_environment": "sandbox",
                    "bootstrap_proof": "djcboot_registration_proof",
                },
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(len(hass.session.calls), 2)
        bootstrap_call = hass.session.calls[0]
        register_call = hass.session.calls[1]
        self.assertEqual(bootstrap_call["url"], "https://api.djconnect.dev/v1/install/token")
        self.assertNotIn("Authorization", bootstrap_call["headers"])
        self.assertEqual(bootstrap_call["json"]["bootstrap_proof"], "djcboot_registration_proof")
        self.assertEqual(bootstrap_call["json"]["device_id"], "djconnect-ios-ABCDEFGHIJKL")
        self.assertEqual(bootstrap_call["json"]["client_type"], "ios")
        self.assertEqual(register_call["url"], "https://api.djconnect.dev/v1/push/register")
        self.assertEqual(register_call["headers"]["Authorization"], "Bearer djci_created_token")
        self.assertNotIn("bootstrap_proof", register_call["json"])

    def test_register_forwards_to_relay_without_local_storage(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime()

        result = asyncio.run(
            self.push.async_register(
                hass,
                runtime,
                user_id="user-1",
                payload={
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "push_token": "token-secret-value",
                    "push_environment": "production",
                    "app_bundle_id": "dev.djconnect.ios",
                    "app_version": "3.1.68",
                    "locale": "nl-NL",
                    "notification_categories": ["ask_dj_response", "playback_change"],
                },
            )
        )

        self.assertTrue(result["success"])
        call = hass.session.calls[0]
        self.assertEqual(call["url"], "https://api.djconnect.dev/v1/push/register")
        self.assertEqual(call["headers"]["Authorization"], "Bearer djci_test_install_token")
        self.assertEqual(call["json"]["device_id"], "djconnect-ios-ABCDEFGHIJKL")
        self.assertEqual(call["json"]["push_token"], "token-secret-value")
        self.assertEqual(call["json"]["push_environment"], "production")
        self.assertEqual(call["json"]["ha_install_id"], "ha-install-1")
        self.assertNotEqual(call["json"]["ha_user_hash"], "user-1")
        self.assertFalse(hasattr(self.push, "APNsClient"))
        self.assertFalse(hasattr(self.push, "PushRegistrationManager"))

    def test_register_accepts_ios_macos_and_watchos_payloads(self) -> None:
        for client_type, device_id, bundle_id in (
            ("ios", "djconnect-ios-ABCDEFGHIJKL", "dev.djconnect.ios"),
            ("macos", "djconnect-macos-ABCDEFGHIJKL", "dev.djconnect.macos"),
            ("watchos", "djconnect-watchos-ABCDEFGHIJKL", "dev.djconnect.watchkitapp"),
        ):
            with self.subTest(client_type=client_type):
                hass = types.SimpleNamespace(session=FakeSession())
                runtime = self._runtime()

                result = asyncio.run(
                    self.push.async_register(
                        hass,
                        runtime,
                        user_id="user-1",
                        payload={
                            "device_id": device_id,
                            "client_type": client_type,
                            "push_token": f"{client_type}-token-secret-value",
                            "push_environment": "sandbox",
                            "app_bundle_id": bundle_id,
                            "app_version": "3.1.79",
                            "locale": "nl-NL",
                            "notification_categories": ["ask_dj_response", "ask_dj_confirm"],
                        },
                    )
                )

                self.assertTrue(result["success"])
                call = hass.session.calls[0]
                self.assertEqual(call["url"], "https://api.djconnect.dev/v1/push/register")
                self.assertEqual(call["json"]["device_id"], device_id)
                self.assertEqual(call["json"]["client_type"], client_type)
                self.assertEqual(call["json"]["push_environment"], "sandbox")
                self.assertEqual(call["json"]["app_bundle_id"], bundle_id)
                self.assertEqual(
                    call["json"]["notification_categories"],
                    ["ask_dj_confirm", "ask_dj_response"],
                )

    def test_register_rejects_client_type_device_id_mismatch(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime()

        result = asyncio.run(
            self.push.async_register(
                hass,
                runtime,
                user_id="user-1",
                payload={
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "macos",
                    "push_token": "token-secret-value",
                    "push_environment": "sandbox",
                },
            )
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "invalid_push_registration")
        self.assertEqual(hass.session.calls, [])

    def test_register_rejects_invalid_token_or_environment(self) -> None:
        for payload in (
            {
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
                "push_token": "<token-secret-value>",
                "push_environment": "sandbox",
            },
            {
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
                "push_token": "token secret value",
                "push_environment": "sandbox",
            },
            {
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
                "push_token": "token-secret-value",
                "push_environment": "invalid",
            },
            {
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
                "push_token": "token-secret-value",
            },
        ):
            with self.subTest(payload=payload):
                hass = types.SimpleNamespace(session=FakeSession())
                runtime = self._runtime()

                result = asyncio.run(
                    self.push.async_register(
                        hass,
                        runtime,
                        user_id="user-1",
                        payload=payload,
                    )
                )

                self.assertFalse(result["success"])
                self.assertEqual(result["error"], "invalid_push_registration")
                self.assertEqual(hass.session.calls, [])

    def test_register_without_install_token_reports_missing_bootstrap_proof(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime(token=None)

        result = asyncio.run(
            self.push.async_register(
                hass,
                runtime,
                user_id="user-1",
                payload={
                    "device_id": "djconnect-ios-ABCDEFGHIJKL",
                    "client_type": "ios",
                    "push_token": "token-secret-value",
                    "push_environment": "sandbox",
                },
            )
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["push_registered"])
        self.assertEqual(result["last_push_error"], "missing_bootstrap_proof")
        self.assertEqual(hass.session.calls, [])

    def test_register_reports_push_relay_unavailable_on_transport_failure(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime()

        async def failing_post(hass_arg, runtime_arg, path, payload):
            raise RuntimeError("boom")

        original = self.push.async_central_post
        self.push.async_central_post = failing_post
        try:
            result = asyncio.run(
                self.push.async_register(
                    hass,
                    runtime,
                    user_id="user-1",
                    payload={
                        "device_id": "djconnect-ios-ABCDEFGHIJKL",
                        "client_type": "ios",
                        "push_token": "token-secret-value",
                        "push_environment": "sandbox",
                    },
                )
            )
        finally:
            self.push.async_central_post = original

        self.assertFalse(result["success"])
        self.assertFalse(result["push_registered"])
        self.assertEqual(result["last_push_error"], "push_relay_unavailable")

    def test_unregister_forwards_to_relay(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime()

        result = asyncio.run(
            self.push.async_unregister(
                hass,
                runtime,
                user_id="user-1",
                payload={
                    "device_id": "djconnect-watchos-ABCDEFGHIJKL",
                    "client_type": "watchos",
                    "push_token": "watch-token",
                    "push_environment": "production",
                },
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(hass.session.calls[0]["url"], "https://api.djconnect.dev/v1/push/unregister")
        self.assertFalse(result["push_registered"])

    def test_event_payload_contains_no_prompt_response_or_tokens(self) -> None:
        runtime = self._runtime()

        payload = self.push.build_relay_event_payload(
            runtime,
            user_id="user-1",
            event_type="ask_dj_confirm",
            history_revision=124,
            client_message_id="client-1",
        )
        rendered = str(payload)

        self.assertEqual(payload["event_type"], "ask_dj_confirm")
        self.assertEqual(payload["history_revision"], 124)
        self.assertEqual(payload["open_target"], "ask_dj")
        self.assertEqual(payload["ha_install_id"], "ha-install-1")
        self.assertEqual(payload["client_types"], ["ios", "macos", "watchos"])
        self.assertNotIn("aps", payload)
        self.assertNotIn("raw prompt", rendered)
        self.assertNotIn("assistant response", rendered)
        self.assertNotIn("spotify_refresh_token", rendered)
        self.assertNotIn("push_token", rendered)

    def test_event_without_optional_sync_fields_is_valid(self) -> None:
        runtime = self._runtime()

        payload = self.push.build_relay_event_payload(
            runtime,
            user_id=None,
            event_type="ask_dj_response",
        )

        self.assertEqual(payload["event_type"], "ask_dj_response")
        self.assertNotIn("history_revision", payload)
        self.assertNotIn("client_message_id", payload)

    def test_status_uses_runtime_flag_not_token_store(self) -> None:
        runtime = self._runtime()
        self.push._remember_status(
            runtime,
            "djconnect-ios-ABCDEFGHIJKL",
            "ios",
            registered=True,
            environment="sandbox",
            error=None,
        )

        status = asyncio.run(
            self.push.async_status(
                types.SimpleNamespace(),
                runtime,
                user_id="user-1",
                device_id="djconnect-ios-ABCDEFGHIJKL",
                client_type="ios",
            )
        )

        self.assertTrue(status["push_supported"])
        self.assertTrue(status["push_registered"])
        self.assertEqual(status["push_environment"], "sandbox")

    def test_non_ask_dj_events_are_default_disabled(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime()

        for event_type in ("track_change", "playback_change", "queue_change", "volume_change", "mood_change", "idle_suggestion"):
            result = asyncio.run(
                self.push.async_send_event(
                    hass,
                    runtime,
                    user_id="user-1",
                    event_type=event_type,
                    source_device_id="djconnect-ios-ABCDEFGHIJKL",
                    client_type="ios",
                    explicit_user_request=True,
                )
            )
            self.assertEqual(result["sent"], 0)
            self.assertEqual(result["suppressed"], "event_not_pushable")
        self.assertEqual(hass.session.calls, [])

    def test_ask_dj_response_requires_explicit_user_request(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime()

        result = asyncio.run(
            self.push.async_send_event(
                hass,
                runtime,
                user_id="user-1",
                event_type="ask_dj_response",
                source_device_id="djconnect-ios-ABCDEFGHIJKL",
                client_type="ios",
            )
        )

        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["suppressed"], "not_explicit_user_request")
        self.assertEqual(hass.session.calls, [])

    def test_explicit_ask_dj_response_posts_generic_payload(self) -> None:
        hass = types.SimpleNamespace(session=FakeSession())
        runtime = self._runtime()

        result = asyncio.run(
            self.push.async_send_event(
                hass,
                runtime,
                user_id="user-1",
                event_type="ask_dj_response",
                history_revision=123,
                client_message_id="client-1",
                source_device_id="djconnect-ios-ABCDEFGHIJKL",
                client_type="ios",
                explicit_user_request=True,
            )
        )

        self.assertEqual(result["sent"], 1)
        payload = hass.session.calls[0]["json"]
        self.assertEqual(payload["event_type"], "ask_dj_response")
        self.assertEqual(payload["open_target"], "ask_dj")
        self.assertEqual(payload["history_revision"], 123)
        self.assertEqual(payload["ha_install_id"], "ha-install-1")
        self.assertEqual(hass.session.calls[0]["headers"]["Authorization"], "Bearer djci_test_install_token")
        self.assertNotIn("aps", payload)
        self.assertNotIn("source_device_id", payload)
        self.assertNotIn("client_type", payload)

    def test_rate_limit_blocks_frequent_pushes(self) -> None:
        runtime = self._runtime()

        first = self.push.should_send_push(
            runtime,
            user_id="user-1",
            event_type="ask_dj_response",
            source_device_id="djconnect-ios-ABCDEFGHIJKL",
            client_type="ios",
            explicit_user_request=True,
            now=1000,
        )
        second = self.push.should_send_push(
            runtime,
            user_id="user-1",
            event_type="ask_dj_response",
            source_device_id="djconnect-ios-ABCDEFGHIJKL",
            client_type="ios",
            explicit_user_request=True,
            now=1020,
        )

        self.assertTrue(first["send"])
        self.assertFalse(second["send"])
        self.assertEqual(second["reason"], "rate_limited")

    def test_rate_limit_blocks_more_than_five_in_ten_minutes(self) -> None:
        runtime = self._runtime()
        decisions = [
            self.push.should_send_push(
                runtime,
                user_id="user-1",
                event_type="ask_dj_confirm",
                source_device_id="djconnect-ios-ABCDEFGHIJKL",
                client_type="ios",
                now=1000 + index * 31,
            )
            for index in range(6)
        ]

        self.assertTrue(all(item["send"] for item in decisions[:5]))
        self.assertFalse(decisions[5]["send"])
        self.assertEqual(decisions[5]["reason"], "rate_limited")

    def test_foreground_recent_active_client_suppresses_push(self) -> None:
        runtime = types.SimpleNamespace(
            entry=types.SimpleNamespace(
                entry_id="entry-1",
                data={},
                options={
                    "api_base_url": "https://api.djconnect.dev",
                    "ha_install_id": "ha-install-1",
                    "djconnect_install_token": "djci_test_install_token",
                },
            ),
            device_status={
                "device_id": "djconnect-ios-ABCDEFGHIJKL",
                "client_type": "ios",
                "app_state": "active",
            },
        )

        asyncio.run(
            self.push.async_status(
                types.SimpleNamespace(),
                runtime,
                user_id="user-1",
                device_id="djconnect-ios-ABCDEFGHIJKL",
                client_type="ios",
            )
        )
        decision = self.push.should_send_push(
            runtime,
            user_id="user-1",
            event_type="ask_dj_response",
            source_device_id="djconnect-ios-ABCDEFGHIJKL",
            client_type="ios",
            explicit_user_request=True,
            now=self.push._now_monotonic(),
        )

        self.assertFalse(decision["send"])
        self.assertEqual(decision["reason"], "client_recently_active")


if __name__ == "__main__":
    unittest.main()
