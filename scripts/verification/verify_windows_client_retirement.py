"""Bounded real-HA retirement proof with synthetic configuration and device auth.

Never point this script at an installed Home Assistant configuration. Baseline
mode records existing defects before producer changes; it does not claim PASS.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth, loader
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry

ROOT = Path(os.environ["DJC_SOURCE_ROOT"])
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/verification"))
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.config_flow import DJConnectConfigFlow  # noqa: E402


async def main():
    directory = Path(os.environ["DJC_LAB_ROOT"])
    config = directory / ("windows-config-" + secrets.token_hex(4))
    config.mkdir(parents=True)
    (config / "custom_components").symlink_to(ROOT / "custom_components", target_is_directory=True)
    hass = HomeAssistant(str(config))
    loader.async_setup(hass)
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.state = CoreState.running
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(
        cors_origins=[],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    identity = {"client_type": "windows", "device_id": "djconnect-windows-ABCDEF123456"}
    legacy_token = None
    if "--baseline" not in sys.argv:
        # Reuse only the token actually minted by the baseline pair router.
        for previous in sorted(directory.glob("windows-config-*/.storage/core.config_entries")):
            recorded = json.loads(previous.read_text())
            for previous_entry in recorded["data"]["entries"]:
                if previous_entry["data"].get("client_type") == "windows":
                    legacy_token = previous_entry["data"].get("device_token") or legacy_token
        if not legacy_token:
            raise RuntimeError("Real baseline pairing receipt/token required")
    slot = entry(
        "synthetic-windows",
        {
            **identity,
            "pair_code": "123456",
            "music_backend": "later_manual",
            **({"device_token": legacy_token} if legacy_token else {}),
        },
    )
    store = ConfigEntryStore(hass)
    await store.async_save({"entries": [slot.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    integration = await loader.async_get_integration(hass, "djconnect")
    await integration.async_get_platform("config_flow")
    slot = hass.config_entries.async_get_entry(slot.entry_id)
    runtime = DJConnectRuntime(slot)
    hass.data["djconnect"] = {slot.entry_id: runtime, "runtime": runtime}
    register_http_views(hass)
    receipts = []
    try:
        if "--baseline" not in sys.argv:
            result = await hass.config_entries.options.async_init(slot.entry_id)
            assert result["type"] == "abort" and result["reason"] == "client_retired"
            receipts.append(
                {
                    "stage": "real_legacy_options_flow",
                    "type": result["type"],
                    "reason": result["reason"],
                }
            )
        for language in ("en", "nl", "de", "fr", "es"):
            hass.config.language = language
            form = await hass.config_entries.flow.async_init(
                "djconnect", context={"source": "pair_app"}
            )
            validator = next(iter(form["data_schema"].schema.values()))
            choices = list(validator.container)
            receipts.append(
                {
                    "stage": "actual_config_flow_catalog",
                    "language": language,
                    "choices": choices,
                    "windows_offered": "windows" in choices,
                }
            )
            hass.config_entries.flow.async_abort(form["flow_id"])
        async with TestClient(TestServer(hass.http.app)) as client:
            response = await client.post(
                "/api/djconnect/v1/pair", json={**identity, "pair_code": "123456"}
            )
            paired = await response.json()
            receipts.append(
                {
                    "stage": "real_pair_router",
                    "status": response.status,
                    "success": paired.get("success"),
                    "error": paired.get("error"),
                }
            )
            token = paired.get("device_token") or legacy_token
            if token:
                persisted = await ConfigEntryStore(hass).async_load()
                # The live ConfigEntry is persisted by the real pair handler.
                await store.async_save({"entries": [slot.as_storage_fragment]})
                persisted = await ConfigEntryStore(hass).async_load()
                receipts.append(
                    {
                        "stage": "real_pair_store",
                        "token_equal": persisted["entries"][0]["data"].get("device_token") == token,
                    }
                )
                for typ, device in (
                    ("windows", identity["device_id"]),
                    ("ios", "djconnect-ios-ABCDEF123456"),
                    (None, None),
                ):
                    accepted = runtime.authorize_device_request(
                        {"Authorization": "Bearer " + token}, device, typ
                    )
                    receipts.append(
                        {
                            "stage": "retired_token_authority",
                            "request_type": typ,
                            "accepted": accepted,
                        }
                    )
            for payload in (
                {"client_type": "ios", "device_id": identity["device_id"], "pair_code": "123456"},
                {"identity": {**identity}, "pair_code": "123456"},
                {
                    "client_type": "unknown",
                    "device_id": "djconnect-ios-ABCDEF123456",
                    "pair_code": "123456",
                },
            ):
                response = await client.post("/api/djconnect/v1/pair", json=payload)
                body = await response.json()
                receipts.append(
                    {
                        "stage": "direct_identity_refusal",
                        "status": response.status,
                        "error": body.get("error"),
                    }
                )
                if "--baseline" not in sys.argv:
                    assert response.status == 400 and not body.get("device_token")
            for value in ("windows", "unknown", ""):
                flow = DJConnectConfigFlow()
                flow.hass = hass
                flow.context = {"source": "user"}
                result = await flow.async_step_pair_app({"client_type": value})
                receipts.append(
                    {
                        "stage": "explicit_flow_selection",
                        "input": value,
                        "type": result["type"],
                        "reason": result.get("reason"),
                    }
                )
                if "--baseline" not in sys.argv:
                    assert result["type"] == "abort" and result["reason"] in {
                        "client_retired",
                        "invalid_client_type",
                    }
        if "--baseline" not in sys.argv:
            assert all(
                not item["windows_offered"]
                for item in receipts
                if item["stage"] == "actual_config_flow_catalog"
            )
            assert all(
                not item["accepted"]
                for item in receipts
                if item["stage"] == "retired_token_authority"
            )
            assert (
                next(item for item in receipts if item["stage"] == "real_pair_router")["status"]
                >= 400
            )
        else:
            assert all(
                item["windows_offered"]
                for item in receipts
                if item["stage"] == "actual_config_flow_catalog"
            )
            assert (
                next(item for item in receipts if item["stage"] == "real_pair_router")["status"]
                == 200
            )
        output = {
            "assignment": "DJC-CORE-WINDOWS-CLIENT-RETIREMENT-V1-20261011",
            "mode": "BASELINE_DEFECT_CAPTURE" if "--baseline" in sys.argv else "candidate",
            "installed_acceptance": "NOT_CLAIMED",
            "ha_user_credentials_issued": sum(
                len(user.refresh_tokens) for user in await hass.auth.async_get_users()
            ),
            "source_hashes": {
                str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted((ROOT / "custom_components/djconnect").rglob("*"))
                if path.is_file() and path.suffix in {".py", ".json", ".html", ".js", ".css"}
            },
            "receipts": receipts,
        }
        destination = directory / (
            "windows-baseline.json" if "--baseline" in sys.argv else "windows-candidate.json"
        )
        destination.write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps({"receipt": str(destination), "receipts": receipts}))
    finally:
        await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
