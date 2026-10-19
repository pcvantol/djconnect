"""Fail-closed paid Golden gate over the existing isolated paired-HA harness."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.verification.askdj_contextual_golden import MAX_MODEL_CALLS, cases, manifest_digest  # noqa: E402

IMAGE = "ghcr.io/home-assistant/home-assistant@sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4"
MAX_SECONDS = 600


def validate_report(report, candidate):
    """No omitted cases, anonymous fixture receipt, or zero-paid-call PASS."""
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        return False
    rows = report.get("cases")
    calls = report.get("paid_model_calls")
    usage = report.get("usage")
    return (
        report.get("candidate_sha") == candidate
        and report.get("suite") == "askdj_contextual_golden_v1"
        and report.get("manifest_sha256") == manifest_digest()
        and isinstance(rows, list)
        and all(isinstance(r, dict) for r in rows)
        and [r.get("id") for r in rows] == [c["id"] for c in cases()]
        and all(r.get("status") == "PASS" and r.get("findings") == [] for r in rows)
        and type(calls) is int and len(cases()) <= calls <= MAX_MODEL_CALLS
        and all(type(r.get("paid_attempts")) is int and 1 <= r["paid_attempts"] <= 2 for r in rows)
        and sum(r["paid_attempts"] for r in rows) == calls
        and isinstance(usage, list) and len(usage) == calls
        and all(sum(u.get("case_id") == row["id"] for u in usage if isinstance(u, dict)) == row["paid_attempts"] for row in rows)
        and all(isinstance(r, dict) and r.get("model") == "gpt-6-luna"
                and r.get("attempted") is True and r.get("completed") is True
                and type(r.get("input_tokens")) is int and r["input_tokens"] > 0
                and type(r.get("output_tokens")) is int and r["output_tokens"] > 0
                for r in usage)
        and report.get("status") == "PASS"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--report-path", required=True, type=Path)
    args = parser.parse_args()
    candidate = args.candidate_sha
    if not re.fullmatch("[0-9a-f]{40}", candidate):
        raise ValueError("invalid_candidate_sha")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != candidate:
        raise ValueError("candidate_mismatch")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=ROOT, text=True):
        raise ValueError("candidate_checkout_not_clean")
    key = os.environ.get("DJCONNECT_GOLDEN_OPENAI_API_KEY", "")
    if not key or len(key) > 8192:
        raise ValueError("golden_test_credential_missing")
    name = "djc-golden-" + os.urandom(8).hex()
    with TemporaryDirectory(prefix="djc-golden-") as tmp:
        temp = Path(tmp)
        # Evidence directory is new, never an installed HA directory or workspace mount.
        cmd = ["docker", "run", "--rm", "-i", "--name", name,
               "--memory", "1g", "--cpus", "2", "--pids-limit", "256",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--entrypoint", "python", "-e", "DJC_SOURCE_ROOT=/candidate",
               "-e", "DJC_SAFETY_PROBE=contextual_golden",
               "-e", "DJC_OUTPUT=/lab/golden-contextual.json",
               "-v", str(ROOT) + ":/candidate:ro", "-v", tmp + ":/lab", IMAGE,
               "/candidate/scripts/verification/verify_ask_dj_contextual_dialogue_http.py"]
        try:
            with (temp / "private-run.log").open("w") as log:
                result = subprocess.run(cmd, input=json.dumps({"api_key": key, "model": "gpt-6-luna", "max_tokens": 700}),
                                        text=True, stdout=log, stderr=subprocess.STDOUT, timeout=MAX_SECONDS,
                                        check=False)
        except subprocess.TimeoutExpired:
            result = None
        finally:
            # Exact own unique container only; no broad Docker cleanup.
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False, timeout=30)
            key = ""
        raw = temp / "golden-contextual.json"
        if not raw.is_file() or raw.stat().st_size > 131072:
            raise ValueError("golden_receipt_missing_or_oversized")
        report = json.loads(raw.read_text())
        # Public evidence allowlist: never publish logs, model text or source bodies.
        report = {k: report.get(k) for k in ("schema_version", "suite", "manifest_sha256", "cases",
                                            "paid_model_calls", "usage", "status", "native_installed_hardware")}
        report["candidate_sha"] = candidate
        report["harness_sha256"] = hashlib.sha256((ROOT / "scripts/verification/verify_ask_dj_contextual_dialogue_http.py").read_bytes()).hexdigest()
        passed = result is not None and result.returncode == 0 and validate_report(report, candidate)
        report["status"] = "PASS" if passed else "FAIL"
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(json.dumps(report, indent=2) + "\n")
        print("ASKDJ_CONTEXTUAL_GOLDEN=" + report["status"])
        return 0 if passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        # Type only: remote SDK/CLI exception bodies may contain credentials or text.
        print("ASKDJ_CONTEXTUAL_GOLDEN=FAIL:" + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1) from None
