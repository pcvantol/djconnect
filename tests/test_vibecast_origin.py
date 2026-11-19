"""Exact existing HA origin configuration, never wildcard credential authority."""

from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
from tests.test_http_voice_helpers import install_http_stubs


class VibeCastOriginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_http_stubs()
        from custom_components.djconnect import http

        cls.http = http

    def test_same_origin_native_and_exact_https_allowlist(self):
        with patch.dict(sys.modules, {"aiohttp_cors": SimpleNamespace(APP_CONFIG_KEY="cors")}):
            for origin, allowed in [
                (None, True),
                ("https://ha.test", True),
                ("https://receiver.test", True),
                ("https://other.test", False),
                ("http://receiver.test", False),
                ("null", False),
                ("*", False),
            ]:
                request = SimpleNamespace(
                    headers={"Origin": origin} if origin else {},
                    scheme="https",
                    host="ha.test",
                    app={
                        "cors": SimpleNamespace(
                            defaults={"https://receiver.test": object(), "*": object()}
                        )
                    },
                )
                self.assertEqual(self.http._vibecast_origin_allowed(request), allowed, origin)

    def test_unconfigured_remote_origin_fails_closed(self):
        with patch.dict(sys.modules, {"aiohttp_cors": SimpleNamespace(APP_CONFIG_KEY="cors")}):
            request = SimpleNamespace(
                headers={"Origin": "https://receiver.test"}, scheme="https", host="ha.test", app={}
            )
            self.assertFalse(self.http._vibecast_origin_allowed(request))
