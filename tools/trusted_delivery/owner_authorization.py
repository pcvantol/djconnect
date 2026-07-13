"""Fail-closed validation for Trusted Delivery Owner Authorization evidence."""

from __future__ import annotations

from datetime import UTC, datetime
import argparse
import json
from pathlib import Path
import re
from typing import Any


_SHA = re.compile(r"^[0-9a-f]{40}$")


class AuthorizationError(ValueError):
    """Raised when an owner authorization request cannot be trusted."""


def evaluate(request: dict[str, Any]) -> dict[str, Any]:
    """Validate one exact HIGH_RISK candidate authorization request."""
    required = (
        "repository", "branch", "pr_number", "candidate_sha", "current_head_sha",
        "classification", "trusted_delivery_status", "authorization_status", "owner",
        "github_actor", "workflow_run_id",
    )
    missing = [name for name in required if not request.get(name)]
    if missing:
        raise AuthorizationError(f"missing required authorization evidence: {', '.join(missing)}")
    candidate_sha = str(request["candidate_sha"])
    if not _SHA.fullmatch(candidate_sha) or request["current_head_sha"] != candidate_sha:
        raise AuthorizationError("authorization candidate SHA is not the current immutable PR head")
    if request["classification"] != "HIGH_RISK":
        raise AuthorizationError("Owner Authorization applies only to HIGH_RISK changes")
    if request["trusted_delivery_status"] != "PASS":
        raise AuthorizationError("Trusted Delivery technical qualification is not PASS")
    if request["authorization_status"] != "REQUIRED":
        raise AuthorizationError("Trusted Delivery did not require Owner Authorization for this SHA")
    if request["github_actor"] != request["owner"]:
        raise AuthorizationError("GitHub actor is not the configured repository owner")
    return {
        "schema_version": 1,
        "kind": "trusted_delivery_owner_authorization",
        "repository": request["repository"],
        "branch": request["branch"],
        "pr_number": int(request["pr_number"]),
        "candidate_sha": candidate_sha,
        "classification": "HIGH_RISK",
        "owner": request["owner"],
        "github_actor": request["github_actor"],
        "workflow_run_id": str(request["workflow_run_id"]),
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "result": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    evidence = evaluate(request)
    args.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
