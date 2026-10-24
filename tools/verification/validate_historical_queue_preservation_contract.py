"""Validate the closed V2 denial against original isolated-HA derived wire."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "examples/client_contracts/historical_queue_preservation_v2"


def validate():
    schema = json.loads((DIRECTORY / "unavailable.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    wire = json.loads((DIRECTORY / "actual-ha-wire.json").read_text())
    assert wire["contract_version"] == 2 and wire["effect_count"] == 0
    assert wire["queue_preserving_provider"] == "NOT_QUALIFIED"
    assert all(value == "PASS" for value in wire["cases"].values())
    assert len(wire["source_pins"]) == 264
    for relative, digest in wire["source_pins"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
    assert hashlib.sha256((ROOT / wire["harness"]).read_bytes()).hexdigest() == wire["harness_sha256"]
    examples = wire["examples"]
    replies = [examples[key] for key in ("queue_preservation_unavailable", "legacy_saved_output_denial")]
    for reply in replies:
        validator.validate(reply)
    for key in ("history_entry_v1", "history_entry_v2"):
        assert "playback_actions" not in examples[key]
    original = replies[0]
    bad = [{**original, **change} for change in (
        {"success": True}, {"success": 0}, {"error": "success"},
        {"message": ""}, {"playback_actions": []}, {"queue_preserved": True},
    )]
    bad.extend([{k: v for k, v in original.items() if k != "message"}, None, []])
    for value in bad:
        assert list(validator.iter_errors(value)), value
    for key in ("installed", "native", "audible"):
        assert wire[key] == "NOT_RUN"
    return {"positive": len(replies), "negative": len(bad), "product_files": 264,
            "queue_preserving_provider": "NOT_QUALIFIED", "installed_native": "NOT_RUN"}


if __name__ == "__main__":
    print(json.dumps(validate()))
