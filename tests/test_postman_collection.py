from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
COLLECTION_PATH = ROOT / "examples" / "djconnect.postman_collection.json"
POSTMAN_SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
AUTH_REQUIRED_PATHS = {
    "/api/djconnect/status",
    "/api/djconnect/command",
    "/api/djconnect/event",
    "/api/djconnect/ask_dj/message",
    "/api/djconnect/ask_dj/history",
    "/api/djconnect/ask_dj/history/clear",
    "/api/djconnect/music_dna/profile",
    "/api/djconnect/music_dna/settings",
    "/api/djconnect/music_dna/clear",
    "/api/djconnect/music_dna/export",
    "/api/djconnect/music_dna/import",
    "/api/djconnect/push/register",
    "/api/djconnect/push/unregister",
    "/api/djconnect/vibecast",
    "/api/djconnect/voice",
}
DEVICE_ID_HEADER_REQUIRED_PATHS = {
    "/api/djconnect/status",
    "/api/djconnect/command",
    "/api/djconnect/event",
    "/api/djconnect/vibecast",
    "/api/djconnect/voice",
}
IDENTITY_REQUIRED_PATHS = {
    "/api/djconnect/pair",
    "/api/djconnect/status",
    "/api/djconnect/command",
    "/api/djconnect/event",
    "/api/djconnect/ask_dj/message",
    "/api/djconnect/ask_dj/history/clear",
    "/api/djconnect/music_dna/profile",
    "/api/djconnect/music_dna/settings",
    "/api/djconnect/music_dna/clear",
    "/api/djconnect/music_dna/export",
    "/api/djconnect/music_dna/import",
    "/api/djconnect/push/register",
    "/api/djconnect/push/unregister",
    "/api/djconnect/voice",
}
FORBIDDEN_SECRET_PATTERNS = (
    re.compile(r"djci_[A-Za-z0-9_-]{8,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{16,}"),
    re.compile(r"APNS_[A-Z_]*KEY"),
    re.compile(r"DJCONNECT_[A-Z_]*SECRET"),
)


def _collection() -> dict:
    return json.loads(COLLECTION_PATH.read_text(encoding="utf-8"))


def _requests(items: list[dict], prefix: str = ""):
    for item in items:
        name = f"{prefix}/{item.get('name', '')}".strip("/")
        children = item.get("item")
        if isinstance(children, list):
            yield from _requests(children, name)
            continue
        request = item.get("request")
        if isinstance(request, dict):
            yield name, request


def _headers(request: dict) -> dict[str, str]:
    return {
        str(header.get("key") or "").lower(): str(header.get("value") or "")
        for header in request.get("header", [])
        if isinstance(header, dict)
    }


def _raw_url(request: dict) -> str:
    url = request.get("url") or {}
    return str(url.get("raw") or "")


def _path(raw_url: str) -> str:
    normalized = raw_url.replace("{{ha_base_url}}", "http://example.local:8123")
    return urlparse(normalized).path


def _raw_json_body(request: dict) -> dict | None:
    body = request.get("body") or {}
    if body.get("mode") != "raw":
        return None
    raw = body.get("raw")
    if not raw or not str(raw).strip().startswith("{"):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid raw JSON body: {raw}") from exc


class PostmanCollectionTest(unittest.TestCase):
    def test_collection_is_valid_json_v21_shape(self) -> None:
        collection = _collection()

        self.assertEqual(collection["info"]["schema"], POSTMAN_SCHEMA)
        self.assertEqual(collection["auth"]["type"], "noauth")
        self.assertGreater(len(list(_requests(collection["item"]))), 10)

    def test_collection_does_not_commit_real_secrets(self) -> None:
        text = COLLECTION_PATH.read_text(encoding="utf-8")

        for pattern in FORBIDDEN_SECRET_PATTERNS:
            self.assertIsNone(pattern.search(text), pattern.pattern)
        self.assertIn("replace-with-djconnect-device-bearer-token", text)
        self.assertNotIn("spotify_refresh_token", text)
        self.assertNotIn("refresh_token", text)

    def test_authenticated_endpoints_include_bearer_header(self) -> None:
        for name, request in _requests(_collection()["item"]):
            path = _path(_raw_url(request))
            if path not in AUTH_REQUIRED_PATHS:
                continue
            headers = _headers(request)
            self.assertEqual(
                headers.get("authorization"),
                "Bearer {{device_token}}",
                f"{name} must include the DJConnect bearer token",
            )
            if path in DEVICE_ID_HEADER_REQUIRED_PATHS:
                self.assertIn(
                    "x-djconnect-device-id",
                    headers,
                    f"{name} must include X-DJConnect-Device-ID",
                )

    def test_json_requests_include_client_identity(self) -> None:
        for name, request in _requests(_collection()["item"]):
            path = _path(_raw_url(request))
            body = _raw_json_body(request)
            if path not in IDENTITY_REQUIRED_PATHS or body is None:
                continue
            identity = body.get("identity") if isinstance(body.get("identity"), dict) else body
            self.assertIn("client_type", identity, f"{name} must include client_type")
            self.assertIn("device_id", identity, f"{name} must include device_id")

    def test_post_requests_have_expected_content_type(self) -> None:
        for name, request in _requests(_collection()["item"]):
            if request.get("method") != "POST":
                continue
            headers = _headers(request)
            body = request.get("body") or {}
            if body.get("mode") == "file":
                continue
            self.assertEqual(
                headers.get("content-type"),
                "application/json",
                f"{name} must declare JSON content type",
            )


if __name__ == "__main__":
    unittest.main()
