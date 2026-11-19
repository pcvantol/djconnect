"""Compare a separately collected, read-only connector head readback to snapshot.

Does not access GitHub, acquire credentials, or alter the reproducible snapshot.
Missing fresh observations stay UNKNOWN. A changed main is not an offline
snapshot corruption. Input observations must be gathered with the real connector.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from validate_snapshot import load, SHA


def compare(snapshot: dict, observations: dict) -> dict:
    if not isinstance(observations, dict) or not isinstance(observations.get("heads"), dict):
        raise ValueError("Expected {heads: {repository: {sha, observed_date}}}")
    results = []
    for lane in snapshot["lanes"]:
        repo = lane["repository"]
        expected = (
            snapshot["observed_core_delta"]["closing_read"]
            if lane["id"] == "DJC-CORE"
            else lane["baseline_sha"]
        )
        entry = observations["heads"].get(repo)
        status = "UNKNOWN_NO_CLOSING_READBACK"
        actual = None
        if entry is not None:
            if (
                not isinstance(entry, dict)
                or not SHA.fullmatch(str(entry.get("sha", "")))
                or not entry.get("observed_date")
            ):
                raise ValueError(f"Invalid observation for {repo}")
            actual = entry["sha"]
            status = (
                "MATCH_RECORDED_HEAD"
                if actual == expected
                else "CHANGED_NEEDS_READONLY_DELTA_AUDIT"
            )
        results.append(
            dict(repository=repo, expected_head=expected, observed_head=actual, status=status)
        )
    return dict(
        result="COMPLETE_MATCH"
        if all(r["status"] == "MATCH_RECORDED_HEAD" for r in results)
        else "INCOMPLETE_OR_CHANGED",
        source_blob_freshness="NOT_VERIFIED_BY_HEAD_COMPARISON_ALONE",
        repositories=results,
    )


if __name__ == "__main__":
    try:
        result = compare(load(Path(sys.argv[1])), load(Path(sys.argv[2])))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["result"] == "COMPLETE_MATCH" else 1)
    except (IndexError, ValueError, OSError) as exc:
        print(json.dumps({"result": "INVALID_INPUT", "error": str(exc)}))
        sys.exit(2)
