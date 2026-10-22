"""Offline issuer crypto against pinned API public vectors in isolated actual HA.

No HA config/runtime, network, enrolled key, private-key persistence or issuer
request. Software-only source compatibility is the entire qualification scope.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import types

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
# Load the product wire package without starting the HA integration lifecycle.
for name, directory in (("custom_components", ROOT / "custom_components"),
                        ("custom_components.djconnect", ROOT / "custom_components/djconnect")):
    module = types.ModuleType(name)
    module.__path__ = [str(directory)]
    sys.modules[name] = module

from custom_components.djconnect import surface_issuer_wire as wire  # noqa: E402
from custom_components.djconnect.surface_push_contract import SurfacePushError  # noqa: E402
from cryptography.exceptions import InvalidSignature  # noqa: E402
from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec, utils  # noqa: E402


def denied(callback):
    try:
        callback()
    except SurfacePushError:
        return
    raise AssertionError("invalid issuer proof was accepted")


def main():
    fixture_path = ROOT / "tests/fixtures/surface_push/api_2a6_issuer_public_vectors.json"
    raw = fixture_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "aa64043ad7f65681a55c694b0635d898703a7632c2e8dfdd5b0647b6815e5c6e"
    fixture = json.loads(raw)
    positives = negatives = 0
    for vector in fixture["vectors"]:
        envelope = {"payload": vector["payload"], "signature": vector["signature"]}
        assert wire.signing_bytes(vector["path"], vector["payload"]) == vector["signing_bytes_utf8"].encode()
        assert wire.verify_envelope(vector["path"], envelope, fixture["public_key"])
        positives += 1
        for patch in ({"delegation_id": "different"}, {"key_thumbprint": "e" * 64},
                      {"operation_id": "019a0000-0000-7000-8000-000000000002"}):
            bad = deepcopy(envelope)
            bad["payload"].update(patch)
            denied(lambda: wire.verify_envelope(vector["path"], bad, fixture["public_key"]))
            negatives += 1
        for signature in (base64.urlsafe_b64encode(bytes(64)).decode().rstrip("="),
                          vector["signature"] + "=", vector["signature"][:-2]):
            denied(lambda: wire.verify_envelope(vector["path"], envelope | {"signature": signature}, fixture["public_key"]))
            negatives += 1
        # Verify independently that even one literal space in the signed domain
        # is rejected by standard crypto, rather than canonicalized into success.
        jwk = fixture["public_key"]
        key = ec.EllipticCurvePublicNumbers(int.from_bytes(wire.decoded(jwk["x"], 32)),
            int.from_bytes(wire.decoded(jwk["y"], 32)), ec.SECP256R1()).public_key()
        sig = wire.decoded(vector["signature"], 64)
        der = utils.encode_dss_signature(int.from_bytes(sig[:32]), int.from_bytes(sig[32:]))
        try:
            key.verify(der, vector["signing_bytes_utf8"].encode() + b" ", ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            negatives += 1
        else:
            raise AssertionError("one-byte tampered message was accepted")
        denied(lambda: wire.verify_envelope(vector["path"], envelope | {
            "signature": base64.urlsafe_b64encode(der).decode().rstrip("=")}, jwk))
        negatives += 1
    invalid_point = {"kty": "EC", "crv": "P-256", "x": "A" * 43, "y": "A" * 43}
    vector = fixture["vectors"][0]
    bad = {"payload": vector["payload"] | {"key_thumbprint": wire.public_key_thumbprint(invalid_point)},
           "signature": vector["signature"]}
    denied(lambda: wire.verify_envelope(vector["path"], bad, invalid_point))
    negatives += 1
    result = {"scope": "OFFLINE_ACTUAL_HA_CRYPTO_PUBLIC_EXPIRED_VECTORS_ONLY",
        "api_source": "2a6cd1240fe86581dea7810c1f62ce094d725639",
        "public_vector_sha256": hashlib.sha256(raw).hexdigest(), "positive": positives,
        "negative": negatives, "operator_actions": 0, "network_calls": 0,
        "private_keys_created_or_persisted": 0, "runtime_credentials_adopted": 0,
        "source_hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (ROOT / "custom_components/djconnect").rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}}
    target = Path(os.environ["DJC_LAB_ROOT"]) / "issuer-offline-crypto-receipt.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "source_hashes"}))


if __name__ == "__main__":
    main()
