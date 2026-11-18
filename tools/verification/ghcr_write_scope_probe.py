"""Report GHCR-granted token scope without publishing or exposing credentials."""
from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request

from tools.verification.ghcr_readonly_probe import NoRedirect

REPOSITORY = "djconnect-music-dj/djconnect-verification-platform"


def granted_push(bearer: str) -> bool:
    """Inspect response claims; this is not a successful registry write."""
    try:
        parts = bearer.split(".")
        if len(parts) != 3:
            return False
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        access = claims.get("access", [])
        if not isinstance(access, list):
            return False
        return any(item.get("type") == "repository" and item.get("name") == REPOSITORY
                   and isinstance(item.get("actions"), list)
                   and all(isinstance(action, str) for action in item["actions"])
                   and "push" in item["actions"] for item in access if isinstance(item, dict))
    except (ValueError, TypeError, AttributeError):
        return False


def main() -> None:
    actor, token = os.environ.get("GITHUB_ACTOR", ""), os.environ.get("GITHUB_TOKEN", "")
    if not actor or ":" in actor or not token:
        raise SystemExit("GHCR token scope unavailable")
    basic = base64.b64encode((actor + ":" + token).encode()).decode()
    url = "https://ghcr.io/token?" + urllib.parse.urlencode({"scope": "repository:" + REPOSITORY + ":pull,push"})
    request = urllib.request.Request(url, headers={"Authorization": "Basic " + basic, "Accept": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
            value = json.load(response).get("token", "")
        if not granted_push(value):
            raise ValueError("push scope not granted")
    except Exception:
        raise SystemExit("GHCR push scope not established") from None
    print("GHCR_PUSH_SCOPE_GRANTED; registry write was not attempted")


if __name__ == "__main__":
    main()
