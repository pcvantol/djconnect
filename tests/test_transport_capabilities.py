from __future__ import annotations

import asyncio
import importlib
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs


install_http_stubs()
http = importlib.import_module("custom_components.djconnect.http")
transport_capabilities = importlib.import_module("custom_components.djconnect.transport_capabilities")


class TransportCapabilitiesTest(unittest.TestCase):
    def test_http_capability_response_reports_current_transport_truth(self) -> None:
        view = types.SimpleNamespace(json=lambda payload: payload)

        result = asyncio.run(http.DJConnectTransportCapabilitiesView.get(view, object()))

        self.assertTrue(result["success"])
        self.assertEqual(result["transports"], {"http": True, "websocket": True})
        self.assertEqual(
            result["session_broadcast"],
            transport_capabilities.session_broadcast_transport_capabilities(),
        )
        self.assertTrue(result["session_broadcast"]["http_snapshot"]["available"])
        self.assertTrue(result["session_broadcast"]["websocket_subscription"]["available"])
        self.assertTrue(result["session_broadcast"]["snapshot_recovery"])

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
