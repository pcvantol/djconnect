"""Closed production URL parser; configured URL is not A trust proof."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("display_origin_unit", Path(__file__).resolve().parents[1] /
                                            "custom_components/djconnect/display_origin.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class DisplayOriginTests(unittest.TestCase):
    def test_only_configured_standard_port_and_root_slash_normalize(self):
        for value in ("https://ha.example.net", "https://ha.example.net/",
                      "https://ha.example.net:443", "https://ha.example.net:443/"):
            self.assertEqual(policy.configured_origin(value), "https://ha.example.net")
        for value in (None, "http://ha.example.net", "https://127.0.0.1", "https://ha.local",
                      "https://ha.example.net/path", "https://ha.example.net//", "https://ha.example.net:8443",
                      "https://ha.example.net?", "https://ha.example.net#", "https://ha.example.net./",
                      "https://xn--host.example.net", "https://HA.example.net", "https://ha.example.net:0443"):
            with self.subTest(value=value):
                self.assertIsNone(policy.configured_origin(value))

    def test_received_origin_is_never_normalized(self):
        self.assertTrue(policy.lexical_route_allowed("https://ha.example.net/djconnect/vibecast/display",
                                                   "https://ha.example.net"))
        for origin in ("https://ha.example.net/", "https://ha.example.net:443", "null"):
            self.assertFalse(policy.lexical_route_allowed(origin + policy.ENTRY_PATH, origin))
