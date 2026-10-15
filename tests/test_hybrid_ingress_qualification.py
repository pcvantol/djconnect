"""Operator qualification is an explicit, revocable filesystem trust boundary."""

import copy
import importlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import patch

package = types.ModuleType("djc_ingress_unit")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/djconnect")]
sys.modules[package.__name__] = package
qualification = importlib.import_module("djc_ingress_unit.hybrid_ingress_qualification")

ADAPTERS = [{"name": "eth0", "index": 3, "enabled": True, "ipv4": [{"address": "172.18.0.2", "network_prefix": 16}], "ipv6": []}]


class IngressQualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / qualification.FILENAME
        self.record = {"version": 1, "ha_install_id": "ha_owned", "internal_origin": "http://172.18.0.2:8123", "interface_digest": qualification.interface_digest(ADAPTERS), "allowed_peers": ["172.18.0.3/32"], "excluded_peers": ["172.18.0.1", "127.0.0.1"], "source_preserved": True, "proxies_excluded": True, "qualified_at": 100, "expires_at": 200, "evidence_sha256": "a" * 64}

    def write(self, record=None):
        self.path.write_text(json.dumps(self.record if record is None else record))
        self.path.chmod(0o600)
        return qualification.read_qualification(self.tmp.name)

    def allowed(self, record=None, peer="172.18.0.3", adapters=None, installs=None, now=150):
        return qualification.qualify(self.write(record), (peer, 5000), ADAPTERS if adapters is None else adapters, self.record["internal_origin"], "172.18.0.2:8123", [], {"ha_owned"} if installs is None else installs, now=now)

    def test_missing_explicit_record_never_grants_even_loopback(self):
        self.assertIsNone(qualification.read_qualification(self.tmp.name))
        self.assertIsNone(qualification.qualify(None, ("127.0.0.1", 1), [], "http://127.0.0.1", "127.0.0.1", [], {"ha_owned"}, now=150))
        self.assertIsNotNone(self.allowed())

    def test_same_subnet_snat_gateway_and_proxy_are_denied_even_if_allowed(self):
        for peer in ("172.18.0.1", "127.0.0.1"):
            record = copy.deepcopy(self.record)
            record["allowed_peers"].append(peer + "/32")
            self.assertIsNone(self.allowed(record, peer=peer))
        self.assertIsNone(self.allowed(peer="172.18.0.4"))

    def test_identity_interface_expiry_and_replacement_binding(self):
        self.assertIsNone(self.allowed(installs={"other-install"}))
        self.assertIsNone(self.allowed(adapters=[{**ADAPTERS[0], "index": 4}]))
        for now in (99, 200, 201):
            self.assertIsNone(self.allowed(now=now))
        first = self.allowed()
        record = {**self.record, "evidence_sha256": "b" * 64}
        second = self.allowed(record)
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.path.unlink()
        self.assertIsNone(qualification.read_qualification(self.tmp.name))

    def test_schema_types_no_unknown_nonfinite_or_implicit_subnet_grants(self):
        changes = [{"extra": 1}, {"version": True}, {"source_preserved": 1}, {"proxies_excluded": False}, {"ha_install_id": None}, {"internal_origin": "http://foreign.invalid"}, {"interface_digest": "invalid"}, {"evidence_sha256": "g" * 64}, {"qualified_at": True}, {"expires_at": 86402 + 100}, {"expires_at": float("nan")}, {"allowed_peers": ["172.18.0.0/16"]}, {"allowed_peers": []}, {"allowed_peers": [True]}, {"allowed_peers": ["invalid"]}, {"allowed_peers": ["172.18.0.3/32"] * 2}, {"excluded_peers": []}, {"excluded_peers": [True]}, {"excluded_peers": ["invalid"]}]
        for change in changes:
            with self.subTest(change=change):
                self.assertIsNone(self.allowed({**self.record, **change}))
        missing = dict(self.record)
        missing.pop("evidence_sha256")
        self.assertIsNone(self.allowed(missing))

    def test_no_symlinks_group_write_fifo_oversize_or_duplicate_json(self):
        self.write()
        self.path.chmod(0o620)
        self.assertIsNone(qualification.read_qualification(self.tmp.name))
        self.path.unlink()
        target = Path(self.tmp.name) / "operator.json"
        target.write_text(json.dumps(self.record))
        self.path.symlink_to(target)
        self.assertIsNone(qualification.read_qualification(self.tmp.name))
        self.path.unlink()
        os.mkfifo(self.path)
        self.assertIsNone(qualification.read_qualification(self.tmp.name))
        self.path.unlink()
        for raw in ("x" * 8193, '{"version":1,"version":1}', "[]", "{bad", '{"x":Infinity}'):
            self.path.write_text(raw)
            self.assertIsNone(qualification.read_qualification(self.tmp.name))

    def test_atomic_path_replacement_during_read_is_not_a_valid_snapshot(self):
        self.write()
        original = qualification.os.read

        def replace_after_read(fd, size):
            result = original(fd, size)
            other = self.path.with_suffix(".replacement")
            other.write_text(json.dumps(self.record))
            other.replace(self.path)
            return result

        with patch.object(qualification.os, "read", replace_after_read):
            self.assertIsNone(qualification.read_qualification(self.tmp.name))


if __name__ == "__main__":
    unittest.main()
