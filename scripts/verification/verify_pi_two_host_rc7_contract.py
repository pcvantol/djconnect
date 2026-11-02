"""Pure rc.7 producer qualification; no operational files, network or effects.

Requires an existing jsonschema Draft202012 environment. In-memory specimens
are unqualified test data. Schema success cannot approve a real transaction.
"""
from __future__ import annotations

import copy
import datetime
import re
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/release"
REQUEST = "PI_TWO_HOST_DEPLOYMENT_REQUEST_V4.schema.json"
MANIFEST = "PI_TWO_HOST_OPERATIONAL_MANIFEST_V4.schema.json"
CONTRACT = "PI_TWO_HOST_DEPLOYMENT_CONTRACT_V3.md"


def synthetic(rule: dict):
    """Build an unqualified, memory-only specimen for structural testing."""
    if "const" in rule:
        return copy.deepcopy(rule["const"])
    if "enum" in rule:
        return rule["enum"][0]
    if rule.get("type") == "object":
        result = {key: synthetic(rule["properties"][key]) for key in rule["required"]}
        if "oneOf" in rule:
            for key, value in rule["oneOf"][0]["properties"].items():
                result[key] = synthetic(value)
        return result
    if rule.get("type") == "array":
        items = rule["items"]
        variants = items.get("oneOf", [items])
        return [synthetic(variants[i % len(variants)]) for i in range(rule["minItems"])]
    if rule.get("format") == "date-time":
        return "2026-11-02T08:00:00Z"
    if rule.get("minLength") in (40, 64):
        return "f" * rule["minLength"]
    if "release-" in rule.get("pattern", ""):
        return "release-rc7-SYNTHETIC-UNQUALIFIED"
    return "SYNTHETIC-UNQUALIFIED-NOT-AUTHORITY"


def validators():
    from jsonschema import Draft202012Validator, FormatChecker

    schemas = {name: json.loads((RELEASE / name).read_text()) for name in (REQUEST, MANIFEST)}
    formats = FormatChecker()

    @formats.checks("date-time", raises=(ValueError, TypeError))
    def timestamp(value):
        if not isinstance(value, str) or re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z", value) is None:
            return False
        datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True

    result = {}
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        result[name] = Draft202012Validator(schema, format_checker=formats)
    return schemas, result


def joined(request: dict, manifest: dict, *, expected_producer: dict,
           expected_consumer: dict, checks: dict) -> bool:
    """Pure reference equality checks, NOT validation of real owner authority.

    Callers must independently authenticate pinned records and their original
    qualification receipts. This function is deliberately not a Pi admission API.
    """
    if not checks[REQUEST].is_valid(request) or not checks[MANIFEST].is_valid(manifest):
        return False
    if manifest["producer"] != expected_producer or manifest["consumer"] != expected_consumer:
        return False
    for name in ("producer", "consumer"):
        if manifest[name]["source_sha"] == manifest[name]["final_sha"]:
            return False
    actual_hashes = {
        "contract_sha256": hashlib.sha256((RELEASE / CONTRACT).read_bytes()).hexdigest(),
        "request_schema_sha256": hashlib.sha256((RELEASE / REQUEST).read_bytes()).hexdigest(),
        "manifest_schema_sha256": hashlib.sha256((RELEASE / MANIFEST).read_bytes()).hexdigest(),
    }
    if any(manifest["producer"][key] != value for key, value in actual_hashes.items()):
        return False
    if manifest["candidate_sha"] != manifest["repositories"][0]["source_sha"]:
        return False
    if any(request[key] != manifest[key] for key in (
            "candidate_sha", "manifest_id", "platform_version", "release_profile", "inventory_sha256")):
        return False
    if request["guard_contract_id"] != manifest["consumer"]["guard_contract_id"]:
        return False
    target = next(row for row in manifest["required_targets"]
                  if row["deployment_instance"] == request["deployment_instance"])
    artifact = next(row for row in manifest["artifact_bindings"]
                    if row["deployment_instance"] == request["deployment_instance"])
    return all(request[key] == target[key] == artifact[key] for key in (
        "target", "deployment_instance", "device_profile")) and all(
        request[key] == artifact[key] for key in ("artifact_id", "artifact_sha256"))


def qualify() -> dict:
    schemas, checks = validators()
    cases = []

    def record(name, passed):
        if not passed:
            raise AssertionError(name)
        cases.append(name)

    specimens = {name: synthetic(rule) for name, rule in schemas.items()}
    for name, specimen in specimens.items():
        check = checks[name]
        record(name + ":valid-structure", check.is_valid(specimen))

        def change(path, value=None, *, remove=False):
            changed = copy.deepcopy(specimen)
            parent = changed
            for key in path[:-1]:
                parent = parent[key]
            if remove:
                del parent[path[-1]]
            else:
                parent[path[-1]] = value
            record(name + ":reject:" + repr(path) + (":missing" if remove else ":changed:" + repr(value)),
                   not check.is_valid(changed))

        def traverse(node, rule, path=()):
            if "const" in rule:
                change(path, None)
                if isinstance(node, dict):
                    for key, value in node.items():
                        change(path + (key,), remove=True)
                        change(path + (key,), "UNSAFE-OVERRIDE")
                        if isinstance(value, list):
                            for index in range(len(value)):
                                shortened = value[:index] + value[index + 1:]
                                change(path + (key,), shortened)
                return
            if "oneOf" in rule and "properties" not in rule:
                from jsonschema import Draft202012Validator
                rule = next(r for r in rule["oneOf"] if Draft202012Validator(r).is_valid(node))
            if rule.get("type") == "object":
                changed = copy.deepcopy(specimen)
                parent = changed
                for key in path:
                    parent = parent[key]
                parent["unexpected_override"] = True
                record(name + ":closed:" + repr(path), not check.is_valid(changed))
                for key in rule["required"]:
                    change(path + (key,), remove=True)
                    traverse(node[key], rule["properties"][key], path + (key,))
            elif rule.get("type") == "array":
                change(path, [])
                change(path, node * (rule["maxItems"] + 1))
                if "oneOf" in rule["items"]:
                    change(path, [node[0]] * len(node))
                for index, value in enumerate(node):
                    traverse(value, rule["items"], path + (index,))
            elif rule.get("format") == "date-time":
                for invalid in ("not-a-date", "2026-11-02T08:00:00", "2026-02-30T08:00:00Z"):
                    change(path, invalid)
            elif rule.get("type") == "string":
                change(path, node + "\n")
                change(path, "")
        traverse(specimen, schemas[name])

    manifest = specimens[MANIFEST]
    manifest["producer"]["source_sha"], manifest["producer"]["final_sha"] = "a" * 40, "b" * 40
    manifest["consumer"]["source_sha"], manifest["consumer"]["final_sha"] = "c" * 40, "d" * 40
    for key, filename in (("contract_sha256", CONTRACT), ("request_schema_sha256", REQUEST),
                          ("manifest_schema_sha256", MANIFEST)):
        manifest["producer"][key] = hashlib.sha256((RELEASE / filename).read_bytes()).hexdigest()
    producer, consumer = copy.deepcopy(manifest["producer"]), copy.deepcopy(manifest["consumer"])

    def join(q, m, p=producer, c=consumer):
        return joined(q, m, expected_producer=p, expected_consumer=c, checks=checks)

    for index, artifact in enumerate(manifest["artifact_bindings"]):
        request = copy.deepcopy(specimens[REQUEST])
        for key in ("deployment_instance", "device_profile", "artifact_id", "artifact_sha256"):
            request[key] = artifact[key]
        record(f"instance-{index}:exact-join", join(request, manifest))
        reordered = copy.deepcopy(manifest)
        reordered["required_targets"].reverse()
        reordered["artifact_bindings"].reverse()
        record(f"instance-{index}:row-order-independent", join(request, reordered))
        for key, wrong in (("manifest_id", "release-other"), ("inventory_sha256", "0" * 64),
                           ("candidate_sha", "0" * 40), ("artifact_sha256", "0" * 64),
                           ("deployment_instance", artifact["deployment_instance"] + "-other"),
                           ("device_profile", manifest["artifact_bindings"][1-index]["device_profile"])):
            changed = copy.deepcopy(request)
            changed[key] = wrong
            record(f"instance-{index}:reject-{key}", not join(changed, manifest))
        for group in ("producer", "consumer"):
            for key in manifest[group]:
                if key.endswith(("_sha", "_sha256")):
                    changed = copy.deepcopy(manifest)
                    changed[group][key] = "0" * len(changed[group][key])
                    record(f"instance-{index}:reject-{group}-{key}", not join(request, changed))
            changed = copy.deepcopy(manifest)
            changed[group]["final_sha"] = changed[group]["source_sha"]
            altered_pin = changed[group]
            record(f"instance-{index}:reject-{group}-same-source-final", not join(
                request, changed, altered_pin if group == "producer" else producer,
                altered_pin if group == "consumer" else consumer))
        for key in ("contract_sha256", "request_schema_sha256", "manifest_schema_sha256"):
            changed = copy.deepcopy(manifest)
            changed["producer"][key] = "0" * 64
            record(f"instance-{index}:reject-even-matching-wrong-normative-{key}",
                   not join(request, changed, changed["producer"]))
    for name, old in ((REQUEST, "PI_TWO_HOST_DEPLOYMENT_REQUEST_V3.schema.json"),
                      (MANIFEST, "PI_TWO_HOST_OPERATIONAL_MANIFEST_V3.schema.json")):
        from jsonschema import Draft202012Validator
        record(name + ":legacy-rejects-new", not Draft202012Validator(json.loads(
            (RELEASE / old).read_text())).is_valid(specimens[name]))
    return {"scope": "PURE_SCHEMA_AND_REFERENCE_JOINS_ONLY_NO_PID1_OR_DEVICE_GO",
            "passed": len(cases), "case_ids": cases,
            "normative_sha256": {name: hashlib.sha256((RELEASE / name).read_bytes()).hexdigest()
                                 for name in (CONTRACT, REQUEST, MANIFEST)}}


if __name__ == "__main__":
    print(json.dumps(qualify(), indent=2))
