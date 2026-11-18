"""Transport regressions: a Profile request must reach the existing owner handler."""
from __future__ import annotations

import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from tests.test_http_voice_helpers import install_http_stubs


class ProfileHistoryHTTPTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        install_http_stubs()
        cls.http = importlib.import_module("custom_components.djconnect.http")

    async def test_scope_identity_and_privacy_reach_handler_without_namespace_forgery(self):
        request = SimpleNamespace(
            app={"hass": object()}, headers={"Authorization": "Bearer synthetic"},
            context=SimpleNamespace(user_id="authenticated-actor"),
            query={"device_id": "paired-id", "client_type": "ios", "client_id": "install-id",
                   "conversation_scope": "profile", "profile_id": "profile-a",
                   "privacy_mode": "shared", "since_revision": "12",
                   "user_id": "forged", "owner_profile_id": "forged"},
        )
        handler = AsyncMock(return_value=({"success": False, "error": "history_not_allowed"}, 403))
        with patch("custom_components.djconnect.api_handlers.async_handle_ask_dj_history_payload", handler):
            await self.http.DJConnectAskDjHistoryView(None).get(request)
        handler.assert_awaited_once_with(
            request.app["hass"],
            {"device_id": "paired-id", "client_type": "ios", "client_id": "install-id",
             "conversation_scope": "profile", "profile_id": "profile-a",
             "privacy_mode": "shared", "since_revision": 12},
            headers=request.headers, user_id="authenticated-actor",
        )

    async def test_legacy_request_does_not_invent_profile_scope(self):
        request = SimpleNamespace(app={"hass": object()}, headers={}, query={"since_revision": "4"})
        handler = AsyncMock(return_value=({"success": True}, 200))
        with patch("custom_components.djconnect.api_handlers.async_handle_ask_dj_history_payload", handler):
            await self.http.DJConnectAskDjHistoryView(None).get(request)
        handler.assert_awaited_once_with(
            request.app["hass"], {"since_revision": 4}, headers={}, user_id=None,
        )

    async def test_invalid_revision_preserves_existing_no_revision_semantics(self):
        request = SimpleNamespace(app={"hass": object()}, headers={},
                                  query={"conversation_scope": "profile", "since_revision": "invalid"})
        handler = AsyncMock(return_value=({"success": True}, 200))
        with patch("custom_components.djconnect.api_handlers.async_handle_ask_dj_history_payload", handler):
            await self.http.DJConnectAskDjHistoryView(None).get(request)
        self.assertEqual(handler.await_args.args[1], {"conversation_scope": "profile", "since_revision": None})
