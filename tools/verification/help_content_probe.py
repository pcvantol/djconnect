"""Trusted development policy; selected results never qualify the catalogue."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unicodedata

MANIFEST = "f6fcebd0349768b83a6824d6dcfeb15e3b229e0c1a168dec4c5a044e1ac43b48"
TARGET = (
    "catalogue-listen.artist-nl",
    "catalogue-listen.artist-fr",
    "catalogue-listen.artist-es",
    "catalogue-chain-speaker-en-offer",
    "catalogue-chain-speaker-en-accept",
    "catalogue-chain-speaker-en-duplicate",
)
# A new closed case version; the historical target6 stays unchanged.
TARGET18_ACTIVITY_V2 = (
    "catalogue-play.cooking-nl", "catalogue-play.cooking-de", "catalogue-play.cooking-es",
    "catalogue-play.quiet-de", "catalogue-play.quiet-fr", "catalogue-play.quiet-es",
    "catalogue-listen.artist-nl", "catalogue-listen.artist-fr", "catalogue-listen.artist-es",
    "catalogue-chain-speaker-en-offer", "catalogue-chain-speaker-en-accept",
    "catalogue-chain-speaker-en-duplicate",
    "catalogue-chain-album-nl-offer", "catalogue-chain-album-nl-accept",
    "catalogue-chain-album-nl-duplicate",
    "catalogue-chain-album-es-offer", "catalogue-chain-album-es-accept",
    "catalogue-chain-album-es-duplicate",
)
# All seven original full100 failures plus the retained18, with whole chains.
TARGET24_DELIVERY_V3 = (
    "catalogue-play.artist-fr",
    "catalogue-play.cooking-nl", "catalogue-play.cooking-de", "catalogue-play.cooking-es",
    "catalogue-play.quiet-en", "catalogue-play.quiet-de", "catalogue-play.quiet-fr", "catalogue-play.quiet-es",
    "catalogue-listen.artist-en", "catalogue-listen.artist-nl", "catalogue-listen.artist-fr", "catalogue-listen.artist-es",
    "catalogue-chain-speaker-en-offer", "catalogue-chain-speaker-en-accept",
    "catalogue-chain-speaker-en-duplicate",
    "catalogue-chain-album-en-offer", "catalogue-chain-album-en-accept", "catalogue-chain-album-en-duplicate",
    "catalogue-chain-album-nl-offer", "catalogue-chain-album-nl-accept", "catalogue-chain-album-nl-duplicate",
    "catalogue-chain-album-es-offer", "catalogue-chain-album-es-accept", "catalogue-chain-album-es-duplicate",
)
EDITABLE = {
    "custom_components/djconnect/playback_request.py": "PLAYBACK_TELLING_STYLE",
    "custom_components/djconnect/ask_dj/dialogue.py": "ARTIST_BRIEF_TELLING_STYLE",
}
CONTROL_FILES = (
    ".github/workflows/help-content-development.yml",
    "tools/verification/help_content_probe.py",
    "tools/verification/help_content_probe_child.py",
    "tools/verification/run_help_content_probe.py",
)


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def mode_policy(mode):
    if mode == "target6":
        return TARGET, 22, 600
    if mode == "target18_activity_v2":
        return TARGET18_ACTIVITY_V2, 62, 900
    if mode == "target24_delivery_v3":
        return TARGET24_DELIVERY_V3, 82, 900
    if mode == "full100":
        return (), 392, 1800
    raise ValueError("unknown_content_probe_mode")


def literal(raw, name):
    """One ordinary literal assignment; never evaluate candidate expressions."""
    text = raw.decode("utf-8", errors="strict")
    tree = ast.parse(text)
    bindings = [
        node
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        )
    ]
    if len(bindings) != 1:
        raise ValueError("instruction_binding_ambiguous")
    node = bindings[0]
    if (
        type(node) is not ast.Assign
        or len(node.targets) != 1
        or type(node.targets[0]) is not ast.Name
        or type(node.value) is not ast.Constant
        or type(node.value.value) is not str
    ):
        raise ValueError("instruction_not_plain_string_assignment")
    value = node.value.value
    if (
        not 20 <= len(value.encode()) <= 4096
        or "\nData:\n" in value
        or any(unicodedata.category(c) in {"Cc", "Cs", "Cf"} and c != "\n" for c in value)
    ):
        raise ValueError("instruction_string_invalid")
    lines = raw.splitlines(keepends=True)
    start = sum(map(len, lines[: node.value.lineno - 1])) + node.value.col_offset
    end = sum(map(len, lines[: node.value.end_lineno - 1])) + node.value.end_col_offset
    return tree, value, start, end


def instruction_only(base, candidate, name):
    """Both AST and exact nonliteral bytes must stay unchanged."""
    before, original, first, last = literal(base, name)
    after, value, begin, end = literal(candidate, name)
    restored = candidate[:begin] + base[first:last] + candidate[end:]
    if restored != base:
        raise ValueError("non_instruction_bytes_changed")
    for node in after.body:
        if (
            type(node) is ast.Assign
            and type(node.targets[0]) is ast.Name
            and node.targets[0].id == name
        ):
            node.value = ast.Constant(original)
    if ast.dump(before, include_attributes=False) != ast.dump(after, include_attributes=False):
        raise ValueError("non_instruction_ast_changed")
    return value, digest(base[:first] + b"<CORE_TELLING_VALUE>" + base[last:])


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    )


def entries(root):
    result = {}
    for row in git(root, "ls-tree", "-rz", "HEAD").split(b"\0"):
        if row:
            fields, name = row.split(b"\t", 1)
            mode, kind, blob = fields.decode().split()
            if kind != "blob":
                raise ValueError("unsupported_candidate_entry")
            result[name.decode("utf-8", errors="strict")] = (mode, blob)
    return result


def validate_candidate(controller, candidate):
    """An unmerged candidate changes two telling values, never executed code."""
    for root in (controller, candidate):
        if (
            root.is_symlink()
            or git(root, "status", "--porcelain", "--untracked-files=normal").strip()
        ):
            raise ValueError("dirty_or_symlink_probe_checkout")
    base, current = entries(controller), entries(candidate)
    if set(base) != set(current):
        raise ValueError("candidate_inventory_changed")
    values, fixed = {}, {}
    for name, (mode, blob) in base.items():
        candidate_mode, candidate_blob = current[name]
        if candidate_mode != mode:
            raise ValueError("candidate_file_mode_changed")
        if name in EDITABLE:
            if mode != "100644":
                raise ValueError("instruction_file_mode_invalid")
            original = git(controller, "cat-file", "blob", blob)
            changed = git(candidate, "cat-file", "blob", candidate_blob)
            values[name], fixed[name] = instruction_only(original, changed, EDITABLE[name])
            if (candidate / name).read_bytes() != changed:
                raise ValueError("candidate_working_blob_changed")
        elif candidate_blob != blob:
            raise ValueError("candidate_outside_instruction_allowlist")
    # Commit names, documentation and source spelling cannot create a fresh
    # content identity. Only actual telling values and fixed execution inputs do.
    controls = {name: digest((controller / name).read_bytes()) for name in CONTROL_FILES}
    from tools.verification import run_help_catalogue_qualification_20261023 as safe

    products = safe.product_hashes(candidate)
    profile = safe.profile_source_hashes(candidate)
    observer = "scripts/verification/artist_public_input_receipts.py"
    profile[observer] = digest((candidate / observer).read_bytes())
    fixed_inputs = {
        name: value for name, value in {**products, **profile}.items() if name not in EDITABLE
    }
    content = digest(
        canonical(
            {
                "telling": values,
                "fixed_instruction_code": fixed,
                "fixed_inputs": fixed_inputs,
                "controls": controls,
                "manifest": MANIFEST,
            }
        )
    )
    return {
        "candidate_sha": git(candidate, "rev-parse", "HEAD").decode().strip(),
        "controller_sha": git(controller, "rev-parse", "HEAD").decode().strip(),
        "content_digest": content,
        "product_hashes": products,
        "profile_hashes": profile,
        "control_hashes": controls,
        "telling_values_sha256": digest(canonical(values)),
        "candidate_inventory_entries": len(current),
    }


class DiagnosticProgress:
    """Closed selected-case reservations before SDK I/O; persistence failure closes."""

    def __init__(self, path, *, content_digest, mode="target6"):
        self.mode = mode
        self.case_ids, self.maximum_attempts, _ = mode_policy(mode)
        if not self.case_ids:
            raise ValueError("selected_progress_mode_required")
        self.path, self.healthy = Path(path), True
        self.value = {
            "schema_version": 1 if mode == "target6" else (3 if mode == "target24_delivery_v3" else 2),
            "scope": "TARGETED_DEVELOPMENT_NOT_FULL100",
            "manifest_sha256": MANIFEST,
            "content_digest": content_digest,
            "selected_case_ids": list(self.case_ids),
            "phase": "setup",
            "outcome": "RUNNING",
            "current_case": None,
            "completed_cases": [],
            "failed_cases": [],
            "sdk_attempts_reserved": 0,
            "sdk_completed_responses": 0,
            "external_billing": "UNKNOWN_NOT_A_BILLING_RECEIPT",
            "qualification": "NOT_QUALIFIED",
        }
        if mode != "target6":
            self.value["mode"] = mode
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        self._save()

    def _save(self):
        if not self.healthy or not validate_progress(
            self.value, content_digest=self.value["content_digest"], mode=self.mode
        ):
            self.healthy = False
            raise ValueError("diagnostic_progress_closed")
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix=".help-diagnostic-", dir=self.path.parent)
            with os.fdopen(fd, "wb") as f:
                f.write(canonical(self.value) + b"\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.path)
            temporary = None
            fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except BaseException:
            self.healthy = False
            raise
        finally:
            if temporary is not None:
                os.unlink(temporary)

    def _running(self):
        if not self.healthy or self.value["outcome"] != "RUNNING":
            raise RuntimeError("diagnostic_progress_closed")

    def phase(self, phase, case=None):
        self._running()
        self.value.update(phase=phase, current_case=case)
        self._save()

    def before_model(self, case):
        self._running()
        if self.value["sdk_attempts_reserved"] >= self.maximum_attempts:
            self.healthy = False
            raise RuntimeError("diagnostic_model_budget_exhausted")
        self.value.update(phase="model", current_case=case)
        self.value["sdk_attempts_reserved"] += 1
        self._save()

    def completed_response(self):
        self._running()
        self.value["sdk_completed_responses"] += 1
        self._save()

    def completed_case(self, case, *, passed):
        self._running()
        self.value["completed_cases"].append(case)
        if not passed:
            self.value["failed_cases"].append(case)
        self.value.update(phase="case", current_case=case)
        self._save()

    def terminal(self, outcome):
        self._running()
        self.value.update(phase="terminal", outcome=outcome, current_case=None)
        self._save()

    def failure_without_masking_primary(self, *, cancelled=False):
        try:
            self.terminal("CANCELLED" if cancelled else "FAIL")
        except BaseException:
            self.healthy = False


def validate_progress(value, *, content_digest, mode="target6"):
    try:
        return _validate_progress(value, content_digest=content_digest, mode=mode)
    except (ValueError, KeyError, TypeError, UnicodeError):
        return False


def _validate_progress(value, *, content_digest, mode):
    selected, maximum_attempts, _ = mode_policy(mode)
    if not selected:
        return False
    expected = {
        "schema_version",
        "scope",
        "manifest_sha256",
        "content_digest",
        "selected_case_ids",
        "phase",
        "outcome",
        "current_case",
        "completed_cases",
        "failed_cases",
        "sdk_attempts_reserved",
        "sdk_completed_responses",
        "external_billing",
        "qualification",
    }
    if mode != "target6":
        expected.add("mode")
    if (
        type(value) is not dict
        or set(value) != expected
        or type(value["schema_version"]) is not int
        or value["schema_version"] != (1 if mode == "target6" else (3 if mode == "target24_delivery_v3" else 2))
        or (mode != "target6" and value.get("mode") != mode)
        or value["scope"] != "TARGETED_DEVELOPMENT_NOT_FULL100"
        or value["manifest_sha256"] != MANIFEST
        or value["content_digest"] != content_digest
        or type(content_digest) is not str
        or re.fullmatch("[a-f0-9]{64}", content_digest) is None
        or value["selected_case_ids"] != list(selected)
        or value["qualification"] != "NOT_QUALIFIED"
        or value["external_billing"] != "UNKNOWN_NOT_A_BILLING_RECEIPT"
        or value["phase"] not in {"setup", "case", "model", "teardown", "report", "terminal"}
        or value["outcome"] not in {"RUNNING", "FAIL", "CANCELLED", "COMPLETE_NOT_QUALIFIED"}
        or ((value["phase"] == "terminal") != (value["outcome"] != "RUNNING"))
        or (value["phase"] == "terminal" and value["current_case"] is not None)
        or value["current_case"] not in {None, "catalogue-start", *selected}
    ):
        return False
    completed, failed = value["completed_cases"], value["failed_cases"]
    attempts, responses = value["sdk_attempts_reserved"], value["sdk_completed_responses"]
    return (
        type(completed) is list
        and completed == list(selected[: len(completed)])
        and type(failed) is list
        and len(set(failed)) == len(failed)
        and set(failed) <= set(completed)
        and type(attempts) is int
        and type(responses) is int
        and 0 <= responses <= attempts <= maximum_attempts
        and (value["outcome"] != "COMPLETE_NOT_QUALIFIED" or len(completed) == len(selected))
    )


def selected_inputs_complete(report, *, mode="target6"):
    """Exact selected artist witnesses; never relabel a subset as five-by-two."""
    from scripts.verification import artist_public_input_receipts as original

    try:
        selected, _, _ = mode_policy(mode)
        if not selected:
            return False
        expected = {
            case: case.rsplit("-", 1)[1]
            for case in selected
            if case.startswith("catalogue-listen.artist-")
        }
        records, indexed = report["artist_public_inputs"], {}
        if type(records) is not list or len(records) != 2 * len(expected):
            return False
        for row in records:
            if (
                type(row) is not dict
                or set(row)
                != {
                    "case_id",
                    "phase",
                    "language",
                    "public_music_research",
                    "literal_anchors",
                    "sha256",
                }
                or row["case_id"] not in expected
                or row["phase"] not in {"generation", "assessment"}
                or row["language"] != expected[row["case_id"]]
                or len(original.canonical(row)) > 131072
                or row["sha256"]
                != digest(original.canonical({k: v for k, v in row.items() if k != "sha256"}))
            ):
                return False
            key = row["case_id"], row["phase"]
            if key in indexed:
                return False
            indexed[key] = original._spans(row["public_music_research"])
            if row["phase"] == "generation":
                original.resolved_literal_commitments(
                    row["public_music_research"], row["literal_anchors"]
                )
            elif row["literal_anchors"] != []:
                return False
        for case in expected:
            if indexed[case, "generation"] != indexed[case, "assessment"]:
                return False
        attempts = [
            (r["case_id"], r["artist_public_input_sha256"])
            for r in report["model_calls"]
            if "artist_public_input_sha256" in r
        ]
        return len(attempts) == 2 * len(expected) and sorted(attempts) == sorted(
            (r["case_id"], r["sha256"]) for r in records
        )
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        return False


def generation_wire_complete(report, *, cases):
    expected = {
        case["id"]: case["language"] for case in cases if case.get("entry_id") == "listen.artist"
    }
    try:
        rows = [row for row in report["model_calls"] if "artist_generation_wire" in row]
        if (
            not expected
            or len(rows) != len(expected)
            or {r["case_id"] for r in rows} != set(expected)
        ):
            return False
        for row in rows:
            wire = row["artist_generation_wire"]
            if (
                type(wire) is not dict
                or set(wire)
                != {
                    "research_schema",
                    "language",
                    "drafts_requested",
                    "wire_contract_first",
                    "trusted_instructions_sha256",
                }
                or type(wire["research_schema"]) is not int
                or wire["research_schema"] != 3
                or wire["language"] != expected[row["case_id"]]
                or wire["drafts_requested"] is not True
                or wire["wire_contract_first"] is not True
                or type(wire["trusted_instructions_sha256"]) is not str
                or re.fullmatch("[a-f0-9]{64}", wire["trusted_instructions_sha256"]) is None
            ):
                return False
        return True
    except (ValueError, KeyError, TypeError):
        return False


def validate_selected_report(report, progress, *, pin, mode="target6"):
    from scripts.verification.askdj_example_catalogue_golden import (
        _validate_execution,
        cases,
        chain_cases,
        manifest_digest,
    )

    original = {c["id"]: c for c in cases() + chain_cases()}
    try:
        selected, maximum_attempts, _ = mode_policy(mode)
        if not selected:
            return False
        rows = report["cases"]
        return (
            manifest_digest() == MANIFEST
            and report["manifest_sha256"] == MANIFEST
            and report["qualification"] == "REAL_PAIRED_HA_SELECTED_CATALOGUE_CASES_V1"
            and report["selected_case_ids"] == list(selected)
            and report["status"] == "PASS"
            and [r["id"] for r in rows] == list(selected)
            and all(
                r["status"] == "PASS"
                and r["findings"] == []
                and r["question_sha256"] == digest(original[r["id"]]["question"].encode())
                for r in rows
            )
            and report["source_hashes"] == pin["profile_hashes"]
            and report["source_unchanged"] is True
            and report["configured_maximum_tokens"] == 3000
            and validate_progress(progress, content_digest=pin["content_digest"], mode=mode)
            and progress["outcome"] == "COMPLETE_NOT_QUALIFIED"
            and progress["failed_cases"] == []
            and progress["sdk_attempts_reserved"]
            == progress["sdk_completed_responses"]
            == len(report["model_calls"])
            == report["paid_model_calls"]
            <= maximum_attempts
            and all(
                r.get("attempted") is True
                and r.get("completed") is True
                and r.get("maximum_output_tokens") == 3000
                for r in report["model_calls"]
            )
            and selected_inputs_complete(report, mode=mode)
            and generation_wire_complete(report, cases=[original[case] for case in selected])
            # Reuse every original transport, effects, language, chain replay,
            # per-request model and source predicate with exactly the closed selected
            # questions. Only the generic validator's empty-selection sentinel
            # is adapted; the original report and qualification stay selected.
            and _validate_execution(
                {**report, "selected_case_ids": []},
                source_hashes=pin["profile_hashes"],
                expected=[original[case] for case in selected],
                qualification="REAL_PAIRED_HA_SELECTED_CATALOGUE_CASES_V1",
                manifest=MANIFEST,
            )
        )
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        return False
