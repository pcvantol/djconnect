"""Ingress security: socket provenance and configured origins, never forwarded claims."""

import importlib.util
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location(
    "hybrid_local_policy_unit",
    Path(__file__).resolve().parents[1] / "custom_components/djconnect/hybrid_local_policy.py",
)
policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy)

LAN = {"enabled": True, "index": 3, "ipv4": [{"address": "192.168.1.134", "network_prefix": 24}], "ipv6": [{"address": "fd12::1", "network_prefix": 64}, {"address": "fe80::1", "network_prefix": 64}]}


class LocalIngressTests(unittest.TestCase):
    def allowed(self, peer="192.168.1.20", adapters=None, url="http://192.168.1.134:8123", host="192.168.1.134:8123", headers=()):
        return policy.direct_local_allowed((peer, 50000), [LAN] if adapters is None else adapters, url, host, headers)

    def test_direct_real_subnet_requires_exact_internal_origin(self):
        self.assertTrue(self.allowed())
        for kwargs in ({"url": None}, {"host": "foreign.invalid:8123"}, {"host": "192.168.1.134:8124"}, {"url": "https://192.168.1.134:8123"}, {"adapters": []}, {"adapters": [{**LAN, "enabled": False}]}):
            with self.subTest(kwargs=kwargs):
                self.assertFalse(self.allowed(**kwargs))

    def test_forged_host_never_grants_public_private_other_subnet_or_docker_gateway(self):
        for peer in ("8.8.8.8", "203.0.113.1", "0.0.0.0", "169.254.1.2", "192.168.2.20", "10.0.0.1", "192.168.65.1", "invalid", "::ffff:8.8.8.8"):
            with self.subTest(peer=peer):
                self.assertFalse(self.allowed(peer=peer))
        self.assertFalse(self.allowed(adapters=[{**LAN, "ipv4": [{"address": "172.18.0.2", "network_prefix": 16}]}]))

    def test_forwarded_and_cloud_claims_cannot_turn_peer_into_direct_ingress(self):
        for name in ("Forwarded", "X-Forwarded-For", "x-forwarded-proto", "X-Forwarded-Host", "X-Forwarded-Port", "X-Real-IP", "Via", "CF-Connecting-IP", "True-Client-IP", "X-Original-Forwarded-For"):
            with self.subTest(header=name):
                self.assertFalse(self.allowed(headers=[name]))
        self.assertTrue(self.allowed(headers=["Authorization", "Origin", "Content-Type"]))

    def test_loopback_still_requires_internal_origin_and_no_proxy(self):
        self.assertTrue(self.allowed(peer="127.0.0.1", adapters=[], url="http://127.0.0.1:8123", host="127.0.0.1:8123"))
        self.assertFalse(self.allowed(peer="127.0.0.1", url=None))
        self.assertFalse(self.allowed(peer="127.0.0.1", headers=["Forwarded"]))
        self.assertFalse(policy.direct_peer_allowed(None, [LAN]))

    def test_ipv6_ula_mapping_and_linklocal_interface_scope(self):
        self.assertTrue(policy.direct_peer_allowed(("::ffff:192.168.1.20", 12, 0, 0), [LAN]))
        self.assertTrue(policy.direct_peer_allowed(("fd12::20", 12, 0, 0), [LAN]))
        self.assertFalse(policy.direct_peer_allowed(("fd13::20", 12, 0, 0), [LAN]))
        self.assertTrue(policy.direct_peer_allowed(("fe80::20", 12, 0, 3), [LAN]))
        for scope in (0, 4):
            self.assertFalse(policy.direct_peer_allowed(("fe80::20", 12, 0, scope), [LAN]))

    def test_origin_browser_errors_are_closed_while_native_may_omit(self):
        self.assertTrue(policy.same_origin([], "http", "192.168.1.134:8123"))
        self.assertTrue(policy.same_origin(["http://192.168.1.134:8123"], "http", "192.168.1.134:8123"))
        self.assertTrue(policy.same_origin(["https://ha.example:443"], "https", "ha.example"))
        for origin in ("null", "https://192.168.1.134:8123", "http://foreign.invalid", "http://192.168.1.134:8124", "http://user@192.168.1.134:8123", "http://192.168.1.134:8123/", "http://192.168.1.134:8123?", "http://192.168.1.134:8123#", "http://192.168.1.134:8123/path", "http://192.168.1.134:8123, http://evil.invalid"):
            with self.subTest(origin=origin):
                self.assertFalse(policy.same_origin([origin], "http", "192.168.1.134:8123"))
        self.assertFalse(policy.same_origin(["http://ha.example", "http://ha.example"], "http", "ha.example"))

    def test_unknown_prefix_and_origin_inputs_never_grant(self):
        for address in ({"address": "invalid", "network_prefix": 24}, {"address": "192.168.1.134", "network_prefix": 0}, {}):
            self.assertFalse(self.allowed(adapters=[{**LAN, "ipv4": [address]}]))
        for origin in (None, "", "http://host:", "http://host:65536", "http://host/extra", "http://host?x", "http://host#x", "http://host name"):
            self.assertIsNone(policy.canonical_origin(origin))


if __name__ == "__main__":
    unittest.main()
