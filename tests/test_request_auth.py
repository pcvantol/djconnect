from __future__ import annotations

import importlib
import types
import unittest

from tests.test_config_flow_helpers import install_homeassistant_stubs


class RequestAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_homeassistant_stubs()
        cls.auth = importlib.import_module("custom_components.djconnect.request_auth")

    def test_identity_payload_merges_nested_and_top_level_values(self) -> None:
        payload = self.auth.identity_payload(
            {
                "identity": {"device_id": "nested", "client_type": "ios"},
                "device_id": "top",
                "text": "hello",
            }
        )

        self.assertEqual(
            payload,
            {"device_id": "top", "client_type": "ios", "text": "hello"},
        )

    def test_resolve_runtime_prefers_matching_device_id(self) -> None:
        first = types.SimpleNamespace(
            device_token="one",
            device_status={"device_id": "djconnect-ios-AAAAAAAAAAAA"},
            authorize_device_request=lambda *_args: True,
        )
        second = types.SimpleNamespace(
            device_token="two",
            device_status={"device_id": "djconnect-macos-BBBBBBBBBBBB"},
            authorize_device_request=lambda *_args: True,
        )
        hass = types.SimpleNamespace(data={"djconnect": {"first": first, "second": second}})

        self.assertIs(
            self.auth.resolve_runtime(hass, "djconnect-macos-BBBBBBBBBBBB", {}),
            second,
        )

    def test_authorize_runtime_device_request_accepts_legacy_two_arg_runtime(self) -> None:
        calls = []

        def authorize(headers, device_id):
            calls.append((headers, device_id))
            return True

        runtime = types.SimpleNamespace(authorize_device_request=authorize)
        headers = {"Authorization": "Bearer token"}

        self.assertTrue(
            self.auth.authorize_runtime_device_request(
                runtime,
                headers,
                "device",
                "ios",
            )
        )
        self.assertEqual(calls, [(headers, "device")])


if __name__ == "__main__":
    unittest.main()
