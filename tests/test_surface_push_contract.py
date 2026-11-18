"""Role/platform isolation and exact original registration intent, no APNs I/O."""

from copy import deepcopy
from datetime import UTC, datetime
import unittest
from tests.test_profile_dj_settings_persistence import operation
from custom_components.djconnect import surface_push_contract as contract


class SurfacePushContractTests(unittest.TestCase):
    def setUp(self):
        self.now = int(datetime.now(UTC).timestamp() * 1000)
        self.payload = {
            "contract_version": 1,
            "device_id": "djconnect-ios-ABCDEF123456",
            "client_type": "ios",
            "operation_id": operation(self.now, 1),
            "session_id": "session-synthetic",
            "platform": "ios",
            "os_version": "26.0",
            "token_role": "widget",
            "target": {
                "instance_id": "synthetic-widget",
                "app_bundle_id": "dev.djconnect.ios",
                "extension_bundle_id": "dev.djconnect.ios.widget",
                "widget_kind": "DJConnectSessionWidget",
            },
            "apns_token": "a" * 64,
            "apns_environment": "sandbox",
            "expected_registration": None,
            "consent": {
                "background_read": True,
                "os_snapshot_cache": True,
                "locked_display": False,
                "external_push_content": False,
                "allow_remote_start": False,
            },
        }

    def validate(self, value=None):
        return contract.validate_registration(
            self.payload if value is None else value, now_ms=self.now
        )

    def test_widget_platforms_and_minimum_os_do_not_invent_tv_or_old_os_support(self):
        for platform, client in contract.PLATFORM_CLIENT.items():
            p = deepcopy(self.payload)
            p.update(
                platform=platform,
                client_type=client,
                device_id="djconnect-" + client + "-ABCDEF123456",
            )
            if platform == "tvos":
                with self.assertRaisesRegex(contract.SurfacePushError, "surface_not_supported"):
                    self.validate(p)
            else:
                self.assertEqual(self.validate(p).metadata()["platform"], platform)
                p["os_version"] = "25.9"
                with self.assertRaisesRegex(contract.SurfacePushError, "surface_not_supported"):
                    self.validate(p)

    def test_activity_is_native_ios_ipados_not_a_mac_watch_or_island_token(self):
        p = deepcopy(self.payload)
        p.update(
            token_role="live_activity_update",
            target={
                "instance_id": "activity-instance",
                "app_bundle_id": "dev.djconnect.ios",
                "activity_id": "activity-original",
                "attributes_type": "DJConnectSessionLiveActivityAttributes",
            },
        )
        p["consent"]["locked_display"] = True
        self.validate(p)
        for platform in ("macos", "watchos", "visionos", "tvos", "maccatalyst"):
            with self.subTest(platform=platform):
                q = deepcopy(p)
                q.update(
                    platform=platform,
                    client_type=contract.PLATFORM_CLIENT[platform],
                    device_id="djconnect-" + contract.PLATFORM_CLIENT[platform] + "-ABCDEF123456",
                )
                with self.assertRaisesRegex(contract.SurfacePushError, "surface_not_supported"):
                    self.validate(q)
        p["token_role"] = "dynamic_island"
        with self.assertRaisesRegex(contract.SurfacePushError, "unsupported_surface_platform"):
            self.validate(p)

    def test_role_specific_targets_and_consent_are_closed(self):
        for change in (
            {"token_role": "app"},
            {"token_role": []},
            {"platform": []},
            {"contract_version": True},
            {"apns_token": "https://secret.invalid"},
            {"apns_token": "a" * 65},
            {"apns_token": " A" * 32},
            {"apns_environment": "development"},
            {"operation_id": "retry"},
            {"caller_profile": "untrusted"},
            {"target": {"instance_id": "widget"}},
            {
                "expected_registration": {
                    "registration_id": "r",
                    "generation": "g",
                    "revision": True,
                }
            },
        ):
            with self.subTest(change=list(change)):
                with self.assertRaises(contract.SurfacePushError):
                    self.validate({**self.payload, **change})
        for key in ("os_snapshot_cache", "background_read"):
            p = deepcopy(self.payload)
            p["consent"][key] = False
            with self.assertRaises(contract.SurfacePushError):
                self.validate(p)
        for key in ("allow_remote_start", "external_push_content"):
            p = deepcopy(self.payload)
            p["consent"][key] = True
            with self.assertRaises(contract.SurfacePushError):
                self.validate(p)

    def test_original_intent_is_immutable_and_token_never_appears_in_repr_or_metadata(self):
        accepted = self.validate()
        self.payload["target"]["instance_id"] = "mutated"
        self.assertEqual(accepted.metadata()["target"]["instance_id"], "synthetic-widget")
        self.assertNotIn("a" * 64, repr(accepted))
        self.assertNotIn("apns_token", accepted.metadata())
        self.assertEqual(accepted.relay_registration()["apns_token"], "a" * 64)
        copy = self.validate(
            {
                **self.payload,
                "target": {**self.payload["target"], "instance_id": "synthetic-widget"},
            }
        )
        self.assertEqual(copy.fingerprint, accepted.fingerprint)

    def test_widget_reload_is_content_free_and_each_call_returns_independent_value(self):
        first = contract.widget_notification()
        first["aps"]["private"] = "not-shared"
        self.assertEqual(contract.widget_notification(), {"aps": {"content-changed": True}})
