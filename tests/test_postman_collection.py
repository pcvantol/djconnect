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
    "/api/djconnect/v1/push/surface/context",
    "/api/djconnect/v1/push/surface/register",
    "/api/djconnect/v1/session/content/delete/prepare",
    "/api/djconnect/v1/session/content/delete",
    "/api/djconnect/v1/session/content/delete/status",
    "/api/djconnect/v1/session/history/delete/status",

    "/api/djconnect/v1/session/history/delete",
    "/api/djconnect/v1/session/history/delete_snapshot",
    "/api/djconnect/v1/session/history/delete_all",
    "/api/djconnect/v1/transport/context",
    "/api/djconnect/v1/transport/operation",
    "/api/djconnect/v1/status",
    "/api/djconnect/v1/command",
    "/api/djconnect/v1/event",
    "/api/djconnect/v1/ask_dj/message",
    "/api/djconnect/v1/ask_dj/history",
    "/api/djconnect/v1/ask_dj/history/clear",
    "/api/djconnect/v1/ask_dj/history/export",
    "/api/djconnect/v1/music_dna/profile",
    "/api/djconnect/v1/music_dna/settings",
    "/api/djconnect/v1/music_dna/clear",
    "/api/djconnect/v1/music_dna/export",
    "/api/djconnect/v1/music_dna/import",
    "/api/djconnect/v1/push/bootstrap",
    "/api/djconnect/v1/push/register",
    "/api/djconnect/v1/push/unregister",
    "/api/djconnect/v1/vibecast",
    "/api/djconnect/v1/voice",
}
DEVICE_ID_HEADER_REQUIRED_PATHS = {
    "/api/djconnect/v1/push/surface/context",
    "/api/djconnect/v1/push/surface/register",
    "/api/djconnect/v1/session/content/delete/prepare",
    "/api/djconnect/v1/session/content/delete",
    "/api/djconnect/v1/session/content/delete/status",
    "/api/djconnect/v1/session/history/delete/status",

    "/api/djconnect/v1/transport/context",
    "/api/djconnect/v1/transport/operation",
    "/api/djconnect/v1/status",
    "/api/djconnect/v1/command",
    "/api/djconnect/v1/event",
    "/api/djconnect/v1/vibecast",
    "/api/djconnect/v1/voice",
}
IDENTITY_REQUIRED_PATHS = {
    "/api/djconnect/v1/push/surface/context",
    "/api/djconnect/v1/push/surface/register",
    "/api/djconnect/v1/session/content/delete/prepare",
    "/api/djconnect/v1/session/content/delete",
    "/api/djconnect/v1/session/content/delete/status",
    "/api/djconnect/v1/session/history/delete/status",

    "/api/djconnect/v1/transport/context",
    "/api/djconnect/v1/transport/operation",
    "/api/djconnect/v1/pair",
    "/api/djconnect/v1/status",
    "/api/djconnect/v1/command",
    "/api/djconnect/v1/event",
    "/api/djconnect/v1/ask_dj/message",
    "/api/djconnect/v1/ask_dj/history/clear",
    "/api/djconnect/v1/ask_dj/history/export",
    "/api/djconnect/v1/music_dna/profile",
    "/api/djconnect/v1/music_dna/settings",
    "/api/djconnect/v1/music_dna/clear",
    "/api/djconnect/v1/music_dna/export",
    "/api/djconnect/v1/music_dna/import",
    "/api/djconnect/v1/push/bootstrap",
    "/api/djconnect/v1/push/register",
    "/api/djconnect/v1/push/unregister",
    "/api/djconnect/v1/voice",
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

    def test_individual_delete_examples_require_explicit_scope_and_preserve_original_ids(self):
        requests = {_path(_raw_url(request)): request for _, request in _requests(_collection()['item'])
                    if '/session/content/delete' in _path(_raw_url(request))}
        prefix = '/api/djconnect/v1/session/content/delete'
        self.assertEqual(set(requests), {prefix, prefix+'/prepare', prefix+'/status'})
        prepare = _raw_json_body(requests[prefix+'/prepare'])
        self.assertEqual(set(prepare), {'device_id', 'client_type', 'contract_version', 'target'})
        self.assertEqual(set(prepare['target']), {'kind', 'session_id', 'target_id'})
        delete = _raw_json_body(requests[prefix])
        self.assertEqual(set(delete), {'device_id', 'client_type', 'contract_version', 'confirmation_id', 'operation_id', 'confirmed'})
        self.assertIs(delete['confirmed'], False)
        self.assertEqual(delete['contract_version'], 1)
        self.assertEqual(delete['operation_id'], '{{content_delete_operation_id}}')
        status = requests[prefix+'/status']
        self.assertEqual(status['method'], 'GET')
        self.assertNotIn('body', status)
        query = {q['key']: q['value'] for q in status['url']['query']}
        self.assertEqual(query['operation_id'], delete['operation_id'])
        self.assertEqual(query['confirmation_id'], delete['confirmation_id'])
        self.assertEqual(query['contract_version'], '1')
        for request in requests.values():
            self.assertIn('No automatic POST replay', request['description'])
            self.assertNotIn('event', request)

    def test_archive_status_examples_use_original_single_or_all_scope_without_confirmation(self):
        requests = [request for _, request in _requests(_collection()['item'])
                    if _path(_raw_url(request)) == '/api/djconnect/v1/session/history/delete/status']
        self.assertEqual(len(requests), 2)
        scopes = {}
        for request in requests:
            self.assertEqual(request['method'], 'GET')
            self.assertNotIn('body', request)
            query = {q['key']: q['value'] for q in request['url']['query']}
            self.assertEqual(query['contract_version'], '1')
            self.assertEqual(query['operation_id'], '{{deletion_operation_id}}')
            self.assertNotIn('confirmation_id', query)
            self.assertNotIn('profile_id', query)
            scopes[query['operation']] = query
        common = {'device_id', 'client_type', 'contract_version', 'operation', 'operation_id'}
        self.assertEqual(set(scopes['single']), common | {'session_id', 'expected_revision'})
        self.assertEqual(set(scopes['all']), common | {'snapshot_id'})

    def test_touch_examples_keep_semantic_intent_and_cancel_identity_separate(self):
        bodies = {_raw_json_body(r).get('operation'): _raw_json_body(r)
                  for _, r in _requests(_collection()['item'])
                  if _raw_json_body(r) and _path(_raw_url(r)) == '/api/djconnect/v1/transport/operation'}
        reaction = bodies['session/persona/reaction']
        cancel = bodies['session/persona/reaction/cancel']
        self.assertEqual(set(reaction['payload']), {'contract_version', 'session', 'kind', 'language', 'processor'})
        self.assertEqual(set(reaction['payload']['session']), {'session_id', 'generation', 'revision'})
        self.assertEqual(set(cancel['payload']), {'contract_version', 'session_id', 'reaction_id', 'reason'})
        self.assertEqual(cancel['operation_id'], '{{operation_id}}')
        self.assertEqual(cancel['payload']['reaction_id'], '{{reaction_operation_id}}')


if __name__ == "__main__":
    unittest.main()
