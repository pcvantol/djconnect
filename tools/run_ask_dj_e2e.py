#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.ask_dj_e2e_contract import AskDjE2ETrace, load_cases, validate_case_result  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ask DJ E2E contract cases against a live Home Assistant instance.")
    parser.add_argument("--base-url", required=True, help="Home Assistant base URL, for example http://localhost:8123")
    parser.add_argument("--token", required=True, help="Home Assistant/DJConnect bearer token for the paired test client")
    parser.add_argument("--cases", default=str(ROOT / "examples" / "ask_dj_e2e_cases.json"))
    parser.add_argument("--out", help="Optional JSON report path")
    parser.add_argument("--device-id", default="djconnect-watchos-e2etest0001")
    parser.add_argument("--device-name", default="DJConnect E2E Watch")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for case in cases:
        response = _post_case(args, case)
        trace = AskDjE2ETrace()
        errors = validate_case_result(case, response, trace)
        failures.extend(errors)
        results.append(
            {
                "id": case["id"],
                "ok": not errors,
                "errors": errors,
                "response": response,
            }
        )
        status = "OK" if not errors else "FAIL"
        print(f"{status} {case['id']}")
        for error in errors:
            print(f"  - {error}")

    report = {"ok": not failures, "results": results}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if not failures else 1


def _post_case(args: argparse.Namespace, case: dict[str, Any]) -> dict[str, Any]:
    request_payload = {
        "client_id": args.device_id,
        "device_id": args.device_id,
        "device_name": args.device_name,
        "client_message_id": f"live-e2e-{case['id']}",
        "audio_response": "never",
        **case["request"],
    }
    client_type = request_payload.get("client_type") or "watchos"
    request_payload["client_type"] = client_type
    body = json.dumps(request_payload).encode("utf-8")
    url = args.base_url.rstrip("/") + "/api/djconnect/ask_dj/message"
    request = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {args.token}",
            "Content-Type": "application/json",
            "X-DJConnect-Device-ID": args.device_id,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"success": False, "error": f"http_{exc.code}", "message": payload}
    except URLError as exc:
        return {"success": False, "error": "request_failed", "message": str(exc)}


if __name__ == "__main__":
    raise SystemExit(main())
