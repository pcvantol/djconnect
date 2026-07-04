from __future__ import annotations

import asyncio
import json
from pathlib import Path
import types
import unittest
from typing import Any

from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()

from custom_components.djconnect.const import CONF_CLIENT_TYPE, CONF_DEVICE_ID  # noqa: E402
from custom_components.djconnect import vibecast  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "examples" / "vibecast_e2e_cases.json"


class VibeCastE2EContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with CASES_PATH.open(encoding="utf-8") as file:
            cls.cases = json.load(file)

    def test_case_file_is_not_empty_and_has_unique_ids(self) -> None:
        self.assertGreaterEqual(len(self.cases), 1)
        ids = [case.get("id") for case in self.cases]
        self.assertEqual(sorted({case_id for case_id in ids if ids.count(case_id) > 1}), [])

    def test_vibecast_e2e_cases(self) -> None:
        failures: list[str] = []
        for case in self.cases:
            with self.subTest(case=case["id"]):
                response, status = asyncio.run(_run_case(case))
                errors = _validate_case_result(case, response, status)
                failures.extend(errors)
                self.assertEqual(errors, [])
        if failures:
            self.fail("\n".join(failures))

    def test_ios_and_macos_same_active_track_have_equivalent_contract_and_flow(self) -> None:
        ios_case = _case_by_id(self.cases, "ios_active_track_success")
        macos_case = _case_by_id(self.cases, "macos_active_track_success")
        ios, ios_status = asyncio.run(_run_case(ios_case))
        macos, macos_status = asyncio.run(_run_case(macos_case))

        self.assertEqual(ios_status, 200)
        self.assertEqual(macos_status, 200)
        for response in (ios, macos):
            self.assertTrue(response["enabled"])
            self.assertEqual(response["ttl_seconds"], 45)
            self.assertEqual(response["poll_after_seconds"], 20)

        ignored = {"revision", "cache"}
        ios_contract = {key: value for key, value in ios.items() if key not in ignored}
        macos_contract = {key: value for key, value in macos.items() if key not in ignored}
        self.assertEqual(ios_contract, macos_contract)


async def _run_case(case: dict[str, Any]) -> tuple[dict[str, Any], int]:
    request = case.get("request") or {}
    client_type = str(request.get("client_type") or "ios")
    runtime = _Runtime(client_type if client_type in {"ios", "macos", "watchos"} else "ios")
    hass = types.SimpleNamespace(
        data={"djconnect": {"runtime": runtime}},
        states=types.SimpleNamespace(get=lambda entity_id: None),
    )
    original_command = vibecast.run_music_command

    async def command(hass_arg, runtime_arg, command_name, value=None, *, play=None):
        if command_name != "status":
            raise AssertionError(f"unexpected VibeCast command: {command_name}")
        status_kind = case.get("status") or "active"
        if status_kind == "provider_unavailable":
            raise RuntimeError("provider exploded with token secret")
        if status_kind == "no_active_playback":
            return {"success": True, "playback": {"has_playback": False, "is_playing": False}}
        return _status_payload()

    vibecast.run_music_command = command
    try:
        return await vibecast.async_handle_vibecast_payload(
            hass,
            {
                "client_type": client_type,
                "device_id": f"djconnect-{client_type}-ABCDEF123456",
                "client_id": f"djconnect-{client_type}-ABCDEF123456",
                "device_name": f"DJConnect {client_type}",
                "locale": request.get("locale") or "nl-NL",
                "render_capabilities": request.get("render_capabilities") or "",
            },
            headers={
                "Authorization": "Bearer token",
                "X-DJConnect-Device-ID": f"djconnect-{client_type}-ABCDEF123456",
                "X-DJConnect-Client-Type": client_type,
                "X-DJConnect-Locale": request.get("locale") or "nl-NL",
                "X-DJConnect-Render-Capabilities": request.get("render_capabilities") or "",
            },
        )
    finally:
        vibecast.run_music_command = original_command


def _validate_case_result(case: dict[str, Any], response: dict[str, Any], status: int) -> list[str]:
    expect = case.get("expect") or {}
    errors: list[str] = []

    def fail(message: str) -> None:
        errors.append(f"{case.get('id', '<unknown>')}: {message}")

    if status != expect.get("status"):
        fail(f"HTTP status expected {expect.get('status')!r}, got {status!r}")
    for key in ("enabled", "reason", "ttl_seconds", "poll_after_seconds"):
        if key in expect and response.get(key) != expect[key]:
            fail(f"{key} expected {expect[key]!r}, got {response.get(key)!r}")
    if "items_count" in expect and len(response.get("items") or []) != int(expect["items_count"]):
        fail(f"items count expected {expect['items_count']}, got {len(response.get('items') or [])}")
    if "item_kinds" in expect:
        actual = [item.get("kind") for item in response.get("items") or [] if isinstance(item, dict)]
        if actual != expect["item_kinds"]:
            fail(f"item kinds expected {expect['item_kinds']!r}, got {actual!r}")
    for key, value in (expect.get("context") or {}).items():
        context = response.get("context") if isinstance(response.get("context"), dict) else {}
        if context.get(key) != value:
            fail(f"context.{key} expected {value!r}, got {context.get(key)!r}")
    allowed_segment_types = set(expect.get("allowed_segment_types") or vibecast.ALLOWED_TEXT_SEGMENT_TYPES)
    for item in response.get("items") or []:
        if not isinstance(item, dict):
            fail(f"item expected object, got {type(item).__name__}")
            continue
        if item.get("kind") not in vibecast.VIBECAST_ITEM_KINDS:
            fail(f"unknown item kind returned: {item.get('kind')!r}")
        for segment in item.get("text") or []:
            if segment.get("type") not in allowed_segment_types:
                fail(f"segment type {segment.get('type')!r} not in {sorted(allowed_segment_types)!r}")
            if "<" in str(segment.get("value") or "") or ">" in str(segment.get("value") or ""):
                fail(f"segment value should not contain raw markup: {segment.get('value')!r}")
    raw = json.dumps(response, sort_keys=True).lower()
    for forbidden in expect.get("forbidden_text") or []:
        if str(forbidden).lower() in raw:
            fail(f"response should not expose {forbidden!r}: {raw!r}")
    return errors


def _case_by_id(cases: list[dict[str, Any]], case_id: str) -> dict[str, Any]:
    for case in cases:
        if case.get("id") == case_id:
            return case
    raise AssertionError(f"missing VibeCast E2E case {case_id!r}")


def _status_payload() -> dict[str, Any]:
    return {
        "success": True,
        "playback": {
            "has_playback": True,
            "is_playing": True,
            "state": "playing",
            "track_id": "spotify:track:vibe-song",
            "title": "Vibe Song",
            "artist": "The Contexts",
            "album": "Contract Album",
        },
    }


class _Runtime:
    def __init__(self, client_type: str) -> None:
        device_id = f"djconnect-{client_type}-ABCDEF123456"
        self.device_token = "token"
        self.config = {
            CONF_CLIENT_TYPE: client_type,
            CONF_DEVICE_ID: device_id,
        }
        self.device_status = {
            CONF_CLIENT_TYPE: client_type,
            CONF_DEVICE_ID: device_id,
        }

    def client_type(self) -> str:
        return self.config[CONF_CLIENT_TYPE]

    def authorize_device_request(self, headers, body_device_id=None, client_type=None) -> bool:
        return (
            headers.get("Authorization") == "Bearer token"
            and body_device_id == self.config[CONF_DEVICE_ID]
            and client_type == self.config[CONF_CLIENT_TYPE]
        )
