"""Validate versioned decoder fixtures with the existing JSON Schema toolchain.

Runtime authority, UTF8 byte caps and nonfinite rejection are tested separately.
No provider, model, device or HA configuration is accessed by this validator.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "examples/client_contracts/vibescape_visual_director_v1"


def validate():
    validators = {}
    for path in DIRECTORY.glob("*.schema.json"):
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        validators[path.name.removesuffix(".schema.json")] = Draft202012Validator(
            schema, format_checker=FormatChecker()
        )
    structural = json.loads((DIRECTORY / "structural-cases.json").read_text())
    positive = negative = 0
    for row in structural["schema_positive"]:
        validators[row["schema"]].validate(row["value"])
        positive += 1
    for row in structural["schema_negative"]:
        assert list(validators[row["schema"]].iter_errors(row["value"])), row["name"]
        negative += 1
    fixture = json.loads((DIRECTORY / "actual-ha-wire-story-recovery-20261022.json").read_text())
    examples = fixture["examples"]
    for key, schema in (
        ("context_request", "context-request"),
        ("context_response", "context-response"),
        ("interpret_request", "interpret-request"),
        ("interpret_response", "interpret-response"),
    ):
        validators[schema].validate(examples[key])
        positive += 1
    for row in fixture["visual_receipts"]:
        schema = "error-response" if row["status"] != 200 else row["kind"] + "-response"
        validators[schema].validate(row["body"])
        positive += 1
    for row in examples["transport_errors"]:
        validators["error-response"].validate(row["body"])
        positive += 1
    return {
        "schemas": len(validators),
        "positive": positive,
        "negative": negative,
        "runtime_authority": "separate actual owner/SQLite/HTTP regressions",
        "native_microphone_GPU_user_acceptance": "NOT_RUN",
    }


if __name__ == "__main__":
    print(json.dumps(validate()))
