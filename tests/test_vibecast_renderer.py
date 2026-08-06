from __future__ import annotations

import asyncio
from pathlib import Path
import unittest

from tests.test_http_voice_helpers import install_http_stubs


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "custom_components" / "djconnect" / "vibecast.html"


class VibeCastRendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        from custom_components.djconnect import http

        cls.http = http

    def test_renderer_page_is_ephemeral_and_ambient(self) -> None:
        result = asyncio.run(self.http.DJConnectVibeCastRendererView().get(object()))
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["Cache-Control"], "no-store")
        self.assertIn('data-testid="connection-state"', result.text)
        self.assertIn("@media (orientation:landscape)", result.text)
        self.assertIn("min-height:100dvh", result.text)
        self.assertNotIn("localStorage", result.text)
        self.assertNotIn("fetch(", result.text)

    def test_renderer_uses_only_existing_receiver_transport(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn("broadcast_token", page)
        self.assertIn("/api/djconnect/v1/session/broadcast/ws/", page)
        self.assertNotIn("/api/djconnect/v1/vibecast", page)
