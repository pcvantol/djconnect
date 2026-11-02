"""Closed first-play public shapes, genuine source fixture and denial vectors."""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT/"examples/client_contracts/session_first_play_v1"


def main():
    schema = json.loads((DIRECTORY/"schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    wire = json.loads((DIRECTORY/"actual-ha-wire.json").read_text())
    positives = []
    for example in wire["examples"]:
        positives.extend((example["catalogue_before"], example["catalogue_after"]))
        positives.extend(example[key]["first_play"] for key in ("output", "genres", "played"))
    for value in positives:
        validator.validate(value)
    catalogue, phase = positives[0], positives[2]
    negatives = []
    for key, value in (("schema_version", True), ("schema_version", 2), ("available", "true"),
                       ("automatic_playback", True), ("mix_availability", "ready"),
                       ("id", "play_without_owner"), ("operator_attestation", {})):
        negatives.append({**deepcopy(catalogue), key: value})
    bad = deepcopy(catalogue)
    bad["localizations"].pop("nl")
    negatives.append(bad)
    bad = deepcopy(catalogue)
    bad["localizations"]["it"] = bad["localizations"]["en"]
    negatives.append(bad)
    for key, value in (("expires_in", -1), ("expires_in", 61), ("state", "auto_play"),
                       ("reason", "qualified_native"), ("owner", "fabricated")):
        negatives.append({**deepcopy(phase), key: value})
    for value in negatives:
        assert list(validator.iter_errors(value)), "Invalid public action shape was accepted"
    print(json.dumps({"positive_actual_wire": len(positives), "negative_closed_vectors": len(negatives),
                      "classification": "SCHEMA_AND_SOURCE_FIXTURE_ONLY_NOT_PROVIDER_NATIVE_ACCEPTANCE"}))


if __name__ == "__main__":
    main()
