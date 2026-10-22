from __future__ import annotations

import asyncio
import importlib
import json
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs


install_http_stubs()
http = importlib.import_module("custom_components.djconnect.http")
transport_capabilities = importlib.import_module("custom_components.djconnect.transport_capabilities")


class TransportCapabilitiesTest(unittest.TestCase):
    def test_http_capability_response_reports_current_transport_truth(self) -> None:
        view = types.SimpleNamespace(json=lambda payload: payload)

        response = asyncio.run(http.DJConnectTransportCapabilitiesView.get(view, object()))
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        result = json.loads(response.text)

        self.assertTrue(result["success"])
        self.assertEqual(result["transports"], {"http": True, "websocket": True})
        self.assertEqual(
            result["session_broadcast"],
            transport_capabilities.session_broadcast_transport_capabilities(),
        )
        self.assertTrue(result["session_broadcast"]["http_snapshot"]["available"])
        self.assertTrue(result["session_broadcast"]["websocket_subscription"]["available"])
        self.assertTrue(result["session_broadcast"]["snapshot_recovery"])
        hybrid = result["hybrid_transport"]
        self.assertEqual((hybrid["audience"], hybrid["version"]), ("paired_owner_actions", 1))
        self.assertTrue(hybrid["requires_authenticated_tls"])
        self.assertFalse(hybrid["ha_credentials_issued"])
        self.assertEqual(hybrid["after_send_retry"], "reconcile_original_operation_only")

    def test_websocket_recovery_capabilities_match_the_implemented_contract(self) -> None:
        capability = transport_capabilities.session_broadcast_transport_capabilities()

        self.assertTrue(capability["websocket_recovery"]["available"])
        self.assertEqual(
            capability["websocket_recovery"]["command"],
            "djconnect/session/broadcast/recover",
        )
        self.assertTrue(capability["replay"])
        self.assertTrue(capability["cursor"])
        self.assertFalse(capability["flow_delta"])
        self.assertFalse(capability["sequence"])

    def test_paired_owner_route_is_narrow_and_versioned(self) -> None:
        contract = transport_capabilities.session_broadcast_transport_capabilities()["paired_owner_websocket"]
        self.assertEqual(contract["path"], "/api/djconnect/v1/session/broadcast/paired")
        self.assertEqual(contract["version"], 1)
        self.assertEqual(contract["lease_seconds"], 300)
        self.assertEqual(contract["audience"], "active_owner_broadcast")
        self.assertFalse(contract["ha_credentials_issued"])
        self.assertEqual(contract["commands"], [
            "djconnect/session/broadcast/subscribe", "djconnect/session/broadcast/recover"
        ])

    def test_display_discovery_declares_support_without_fabricating_route_or_consent(self) -> None:
        view = types.SimpleNamespace(json=lambda payload: payload)
        response = asyncio.run(http.DJConnectTransportCapabilitiesView.get(view, object()))
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        result = json.loads(response.text)
        contract = result["session_broadcast"]["paired_display_admission"]
        self.assertTrue(contract["supported"])
        self.assertEqual(contract["version"], 1)
        self.assertEqual(contract["availability"], "owner_context_required")
        self.assertEqual(contract["owner_context_path"], "/api/djconnect/v1/display/owner/context")
        self.assertEqual(contract["entry_path"], "/djconnect/vibecast/display")
        self.assertTrue(contract["requires_external_https"])
        self.assertTrue(contract["read_only"])
        self.assertFalse(contract["rendezvous_a"])
        self.assertEqual(contract["owner_authentication"], "paired_device_bearer")
        self.assertEqual(contract["display_authentication"], "dedicated_display_bearer")
        for private in ("available", "display_entry_url", "session_id", "share_id", "grant_token", "issuer_epoch"):
            self.assertNotIn(private, contract)
