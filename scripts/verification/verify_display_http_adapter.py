"""Real aiohttp/HA adapter probe in an isolated dependency runtime, not HA E2E.

Run with the HA image and this checkout mounted read-only. No provider/network,
HA startup, auth acceptance or installed/native claim is made by this probe.
"""
import importlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from multidict import CIMultiDict
from pathlib import Path
import sys
import types


class _Content:
    def __init__(self, value):
        self.value = value

    async def iter_chunked(self, size):
        for offset in range(0, len(self.value), size):
            yield self.value[offset:offset + size]


class DisplayTransportTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType("custom_components.djconnect")
        package.__path__ = [str(Path(__file__).resolve().parents[2] / "custom_components/djconnect")]
        sys.modules.setdefault("custom_components.djconnect", package)
        cls.module = importlib.import_module("custom_components.djconnect.display_transport")

    @staticmethod
    def request(raw=b'{}', **changes):
        return SimpleNamespace(content_type="application/json", content_length=len(raw),
            content=_Content(raw), **changes)

    async def test_json_duplicate_nested_fields_non_json_constants_and_depth_fail_closed(self):
        for raw in (b'{"contract_version":1,"contract_version":1}', b'{"share":{"mode":1,"mode":2}}',
                    b'{"a":NaN}', b'[]', b'\xff', b'[' * 1100 + b']' * 1100):
            with self.subTest(raw=raw[:40]), self.assertRaises(self.module.DisplayAdmissionError):
                await self.module.closed_body(self.request(raw))

    async def test_body_limit_with_and_without_content_length(self):
        for declared in (True, False):
            request = self.request(b'{"padding":"' + b'x' * 4096 + b'"}')
            if not declared:
                request.content_length = None
            with self.assertRaises(self.module.DisplayAdmissionError) as failure:
                await self.module.closed_body(request)
            self.assertEqual(failure.exception.status, 413)

    async def test_no_query_insecure_or_duplicate_auth_request_reaches_service(self):
        view = self.module.DisplayTransitionView(SimpleNamespace(), "claim")
        for changes in ({"query_string": "token=forbidden"}, {"secure": False},
                        {"headers": CIMultiDict([("Authorization", "Bearer one"), ("Authorization", "Bearer two")])}):
            fields = {"query_string": "", "secure": True, "headers": CIMultiDict(), **changes}
            response = await view.post(self.request(**fields))
            self.assertIn(response.status, (400, 426))
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    async def test_delayed_body_rechecks_fence_after_awaited_headers(self):
        current = True
        def release():
            if not current:
                raise self.module.DisplayAdmissionError("display_context_changed")
        response = self.module._FencedResponse(SimpleNamespace(payload={"grant_token": "unit-secret"}, release=release))
        transport = Mock()
        response._req = SimpleNamespace(transport=transport)
        current = False
        with patch.object(self.module.web.Response, "write_eof", new_callable=AsyncMock) as write:
            await response.write_eof()
            write.assert_not_called()
        transport.close.assert_called_once()
        self.assertFalse(response.keep_alive)

    async def test_current_response_releases_only_once_through_normal_aiohttp_body_writer(self):
        release = Mock()
        response = self.module._FencedResponse(SimpleNamespace(payload={"success": True}, release=release))
        self.assertEqual(json.loads(response.body), {"success": True})
        with patch.object(self.module.web.Response, "write_eof", new_callable=AsyncMock) as write:
            await response.write_eof()
            write.assert_awaited_once()
        release.assert_called_once()

    async def test_route_list_is_closed_and_read_only_scope_not_catch_all(self):
        views = self.module.transition_views(SimpleNamespace())
        self.assertEqual(len(views), 9)
        self.assertEqual(len({view.url for view in views}), 9)
        self.assertTrue(all("{" not in view.url for view in views))


if __name__ == "__main__":
    unittest.main()
