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

    def test_retired_persisted_identity_cannot_gain_authority_from_status_or_options(self) -> None:
        for stored, options in (
            ({"client_type": "windows", "device_id": "djconnect-windows-AAAAAAAAAAAA"}, {"client_type": "ios"}),
            ({"client_type": "ios", "device_id": "djconnect-windows-AAAAAAAAAAAA"}, {}),
            ({"client_type": "ios", "device_id": "djconnect-ios-AAAAAAAAAAAA"}, {"client_type": "windows"}),
        ):
            with self.subTest(stored=stored, options=options):
                calls = []
                runtime = types.SimpleNamespace(
                    entry=types.SimpleNamespace(data=stored, options=options),
                    device_status={"client_type": "ios", "device_id": "djconnect-ios-AAAAAAAAAAAA"},
                    device_token="retired-test-token",
                    authorize_device_request=lambda *args: calls.append(args) or True,
                )
                hass = types.SimpleNamespace(data={"djconnect": {"old": runtime, "runtime": runtime}})
                headers = {"Authorization": "Bearer retired-test-token"}
                self.assertIsNone(self.auth.resolve_runtime(hass, "djconnect-ios-AAAAAAAAAAAA", headers))
                self.assertFalse(self.auth.authorize_runtime_device_request(runtime, headers, "djconnect-ios-AAAAAAAAAAAA", "ios"))
                self.assertFalse(calls)

    def test_retired_ingress_is_not_a_canonical_supported_device(self) -> None:
        self.assertIsNone(self.auth.validate_required_client_type({"client_type": "windows"}))
        self.assertFalse(self.auth.is_real_device_id("djconnect-windows-AAAAAAAAAAAA"))
        self.assertTrue(self.auth.is_real_device_id("djconnect-ios-AAAAAAAAAAAA"))


if __name__ == "__main__":
    unittest.main()
