"""Bounded transport regressions; actual HA/aiohttp routing separately verified."""

from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import uuid

from tests.test_http_voice_helpers import install_http_stubs


class VisualHTTPTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        install_http_stubs()
        cls.module = importlib.import_module("custom_components.djconnect.visual_director_http")

    def setUp(self):
        self.hass = SimpleNamespace(is_stopping=False)
        self.view = self.module.VibeScapeContextView(self.hass)
        self.body = {
            "schema_version": 1,
            "client_type": "ios",
            "device_id": "djconnect-ios-ABCDEF123456",
            "session_id": "synthetic-session",
            "visit_id": str(uuid.uuid4()),
        }
        self.reads = []

    def request(self, raw=None, **changes):
        remaining = json.dumps(self.body).encode() if raw is None else raw

        async def read(maximum):
            nonlocal remaining
            amount = min(maximum, 31)
            self.reads.append(amount)
            chunk, remaining = remaining[:amount], remaining[amount:]
            return chunk

        return SimpleNamespace(
            query_string="",
            content_type="application/json",
            charset="utf-8",
            content_length=None,
            headers={},
            content=SimpleNamespace(read=read),
            **changes,
        )

    async def test_valid_partial_stream_reaches_only_dedicated_adapter_and_clears_body_refs(self):
        seen = []

        async def handle(hass, kind, data, **kwargs):
            seen.append(data)
            return {"success": True, "status": "synthetic"}, 200

        with patch.object(self.module, "handle", handle):
            response = await self.view.post(self.request())
        self.assertEqual(response.status, 200)
        self.assertEqual(seen, [{}])
        self.assertGreater(len(self.reads), 1)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")

    async def test_size_encoding_query_and_contenttype_fail_before_admission(self):
        cases = [
            (None, {"content_type": "text/plain"}, 415),
            (None, {"charset": "latin-1"}, 415),
            (None, {"query_string": "text=private"}, 400),
            (None, {"content_length": 8193}, 413),
            (b" " * 8193, {}, 413),
            (b'{"x":NaN}', {}, 400),
            (b'{"x":1,"x":2}', {}, 400),
            (b"\xff", {}, 400),
        ]
        for raw, changes, status in cases:
            with self.subTest(status=status, changes=changes):
                request = self.request(raw)
                for key, value in changes.items():
                    setattr(request, key, value)
                stub = AsyncMock(side_effect=AssertionError("no adapter admission"))
                with patch.object(self.module, "handle", stub):
                    response = await self.view.post(request)
                self.assertEqual(response.status, status)
                self.assertEqual(json.loads(response.text)["schema_version"], 1)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                stub.assert_not_awaited()

    async def test_unknown_and_wrong_typed_closed_fields_rejected_before_adapter(self):
        for change in [
            {"prompt": "private"},
            {"schema_version": True},
            {"client_type": "watchos"},
            {"visit_id": "not-a-uuid"},
        ]:
            with self.subTest(change=change):
                stub = AsyncMock(side_effect=AssertionError("no admission"))
                with patch.object(self.module, "handle", stub):
                    response = await self.view.post(
                        self.request(json.dumps({**self.body, **change}).encode())
                    )
                self.assertEqual(response.status, 400)
                stub.assert_not_awaited()

    async def test_all_other_methods_are_owned_405_no_store_and_shutdown_503(self):
        routes = []
        self.view.register(
            self.hass, None, SimpleNamespace(add_route=lambda *args: routes.append(args))
        )
        self.assertEqual(
            [(x[0], x[1]) for x in routes], [("POST", self.view.url), ("*", self.view.url)]
        )
        response = await self.view.unsupported(self.request())
        self.assertEqual(response.status, 405)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Allow"], "POST")
        self.hass.is_stopping = True
        with patch.object(
            self.module, "handle", AsyncMock(side_effect=AssertionError("no admission"))
        ):
            response = await self.view.post(self.request())
        self.assertEqual(response.status, 503)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertFalse(self.reads)

    async def test_transport_and_unexpected_adapter_failure_never_reflect_private_input(self):
        for error in (TimeoutError("private transcript"), RuntimeError("private transcript")):
            request = self.request()
            request.content.read = AsyncMock(side_effect=error)
            response = await self.view.post(request)
            self.assertEqual(response.status, 503)
            self.assertNotIn("private transcript", response.text)
            self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        with patch.object(
            self.module, "handle", AsyncMock(side_effect=RuntimeError("private body"))
        ):
            response = await self.view.post(self.request())
        self.assertEqual(response.status, 503)
        self.assertNotIn("private body", response.text)

    async def test_cancelled_request_releases_own_transient_body_reference(self):
        entered, release = asyncio.Event(), asyncio.Event()
        seen = []

        async def handle(hass, kind, data, **kwargs):
            seen.append(data)
            entered.set()
            await release.wait()

        with patch.object(self.module, "handle", handle):
            pending = asyncio.create_task(self.view.post(self.request()))
            await entered.wait()
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
        self.assertEqual(seen, [{}])
