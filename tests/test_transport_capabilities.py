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

    def test_unimplemented_recovery_capabilities_remain_explicitly_false(self) -> None:
        capability = transport_capabilities.session_broadcast_transport_capabilities()

        self.assertFalse(capability["replay"])
        self.assertFalse(capability["cursor"])
        self.assertFalse(capability["flow_delta"])
        self.assertFalse(capability["sequence"])
