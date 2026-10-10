"""Real isolated HA pairing/Store/router proof; no HA user credentials.

Configured slots and music are synthetic. Pairing and authorization are real.
Never run against an installed HA or reuse another lane's configuration.
"""

from __future__ import annotations

import asyncio
import json
import hashlib
import os
from pathlib import Path
import secrets
import sys

from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/verification"))
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.persistence import (
    async_initialize_persistence,
    async_shutdown_persistence,
)  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402
from custom_components.djconnect.paired_live_contract import PAIRED_LIVE_PATH, LEASE_SECONDS  # noqa: E402


async def main():
    directory = Path(os.environ.get("DJC_LAB_ROOT", "/lab"))
    config = directory / ("paired-config-" + secrets.token_hex(4))
    config.mkdir(parents=True)
    hass = HomeAssistant(str(config))
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.state = CoreState.running
    hass.config.language = "nl"
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(
        cors_origins=[],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    identity = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"}
    slot = entry(
        "owner-entry",
        {
            **identity,
            "pair_code": "123456",
            "music_backend": "later_manual",
            "profile_id": "profile-a",
        },
    )
    # A configured slot, not a paired token. The real HTTP pair handler mints it.
    store = ConfigEntryStore(hass)
    await store.async_save({"entries": [slot.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    slot = hass.config_entries.async_get_entry("owner-entry")
    runtime = DJConnectRuntime(slot)
    hass.data["djconnect"] = {"owner-entry": runtime, "runtime": runtime}
    storage = ProfilePlatformStorage(hass)
    hass.data["djconnect"]["djconnect_profile_platform"] = storage
    await storage.async_upsert_music_backend(
        "later_manual", BackendProvider.FUTURE_PROVIDER, display_name="Synthetic"
    )
    for profile in ("profile-a", "profile-other"):
        await storage.async_create_profile(
            profile, profile_id=profile, default_backend_id="later_manual"
        )
    await storage.async_upsert_device(identity["device_id"], "ios", linked_profile_id="profile-a")
    service = await async_initialize_persistence(hass)
    manager = SessionRuntimeManager(
        PersistentSessionRepository(service), HistoricalProjectionRepository(service)
    )
    hass.data["djconnect"]["session_runtime_manager"] = manager
    register_http_views(hass)
    await websocket_api.async_setup(hass, {})
    initial_users = await hass.auth.async_get_users()
    initial_credentials = sum(len(user.refresh_tokens) for user in initial_users)
    receipts = []
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "custom_components/djconnect").rglob("*"))
        if path.is_file() and path.suffix in {".py", ".json", ".js", ".html", ".css"}
    }
    async with TestClient(TestServer(hass.http.app)) as client:
        response = await client.post(
            "/api/djconnect/v1/pair", json={**identity, "pair_code": "123456"}
        )
        paired = await response.json()
        assert response.status == 200 and paired["success"]
        token = paired["device_token"]
        assert runtime.device_token == token and slot.data["device_token"] == token
        # Flush through the real HA Store and read it back; no substitute manager.
        await store.async_save({"entries": [slot.as_storage_fragment]})
        stored = await ConfigEntryStore(hass).async_load()
        assert stored["entries"][0]["data"]["device_token"] == token
        users = await hass.auth.async_get_users()
        assert len(users) == len(initial_users)
        assert sum(len(user.refresh_tokens) for user in users) == initial_credentials
        receipts.append(
            {
                "stage": "ordinary_pairing",
                "status": response.status,
                "device_token_persisted": True,
                "ha_credentials_issued": 0,
            }
        )
        response = await client.post(
            "/api/djconnect/v1/websocket/session",
            headers={"Authorization": "Bearer " + token},
            json=identity,
        )
        assert response.status == 404
        receipts.append({"stage": "apple_expected_issuer", "status": response.status})
        async with client.ws_connect("/api/websocket") as ws:
            required = await ws.receive_json()
            assert required["type"] == "auth_required"
            await ws.send_json({"type": "auth", "access_token": token})
            rejected = await ws.receive_json()
            assert rejected["type"] == "auth_invalid"
            receipts.append({"stage": "device_token_native_ha_auth", "type": rejected["type"]})
        if "--baseline" not in sys.argv:
            caps_response = await client.get("/api/djconnect/v1/capabilities")
            caps = await caps_response.json()
            contract = caps["session_broadcast"]["paired_owner_websocket"]
            assert contract["path"] == PAIRED_LIVE_PATH and contract["version"] == 1
            assert contract["lease_seconds"] == LEASE_SECONDS
            receipts.append(
                {"stage": "capability_discovery", "version": 1, "path": PAIRED_LIVE_PATH}
            )

            async def receipt(stage, ws, expected_type=None):
                frame = await asyncio.wait_for(ws.receive_json(), 7)
                if expected_type:
                    assert frame["type"] == expected_type, {
                        "stage": stage,
                        "type": frame.get("type"),
                    }
                receipts.append(
                    {
                        "stage": stage,
                        "type": frame.get("type"),
                        "success": frame.get("success"),
                        "code": frame.get("code") or frame.get("error", {}).get("code"),
                        "event": frame.get("data", {}).get("event_type"),
                    }
                )
                return frame

            async def connect(overrides=None):
                ws = await client.ws_connect(PAIRED_LIVE_PATH)
                await receipt("challenge", ws, "auth_required")
                await ws.send_json(
                    {
                        "type": "auth",
                        "protocol_version": 1,
                        **identity,
                        "device_token": token,
                        **(overrides or {}),
                    }
                )
                return ws

            session = await manager.async_start(
                owner_profile_id="profile-a", selected_mood="energy", locale="nl"
            )
            other = await manager.async_start(
                owner_profile_id="profile-other", selected_mood="energy", locale="nl"
            )
            session_id = session.session_id
            command = {
                "id": 1,
                "type": "djconnect/session/broadcast/subscribe",
                "session_id": session_id,
            }
            for stage, overrides in (
                ("wrong_token", {"device_token": "wrong"}),
                ("missing_token", {"device_token": ""}),
                ("wrong_device", {"device_id": "djconnect-ios-OTHER1234567"}),
                ("wrong_client_type", {"client_type": "windows"}),
                ("wrong_version", {"protocol_version": 2}),
                ("boolean_version", {"protocol_version": True}),
                ("float_version", {"protocol_version": 1.0}),
            ):
                ws = await connect(overrides)
                await receipt(stage, ws, "auth_invalid")
                await ws.close()
            response = await client.get(PAIRED_LIVE_PATH + "?device_token=forbidden")
            assert response.status == 400
            receipts.append({"stage": "query_credential", "status": response.status})
            ws = await client.ws_connect(PAIRED_LIVE_PATH)
            await receipt("challenge", ws, "auth_required")
            await receipt("auth_timeout", ws, "auth_invalid")
            await ws.close()
            ws = await connect()
            await receipt("ordinary_device_auth", ws, "auth_ok")
            for stage, changed in (
                ("forbidden_ha_service", {"type": "call_service"}),
                ("forged_profile", {"profile_id": "profile-other"}),
                ("other_session", {"session_id": other.session_id}),
                (
                    "invalid_cursor",
                    {"type": "djconnect/session/broadcast/recover", "recovery_cursor": "invalid"},
                ),
            ):
                await ws.send_json({**command, **changed})
                rejected = await receipt(stage, ws, "result")
                assert rejected["success"] is False
            await ws.send_json(command)
            snapshot = await receipt("active_snapshot", ws, "result")
            assert snapshot["success"] and snapshot["result"]["session_id"] == session_id
            cursor = snapshot["result"]["recovery_cursor"]

            async def update(title):
                await manager.async_update_playback_projection(
                    owner_profile_id="profile-a",
                    session_id=session_id,
                    state="playing",
                    media_identity="synthetic:track:one",
                    title=title,
                    artist="Synthetic",
                    duration_ms=120000,
                    position_ms=1000,
                )

            await update("Synthetic update")
            event = await receipt("runtime_update", ws, "event")
            assert event["data"]["session_id"] == session_id
            await ws.close()
            await update("Synthetic offline update")
            ws = await connect()
            await receipt("reconnect", ws, "auth_ok")
            await ws.send_json(
                {
                    "id": 1,
                    "type": "djconnect/session/broadcast/recover",
                    "session_id": session_id,
                    "recovery_cursor": cursor,
                }
            )
            recovered = await receipt("cursor_recovery", ws, "result")
            assert recovered["success"]
            await ws.close()
            ws = await connect()
            await receipt("before_profile_change", ws, "auth_ok")
            await ws.send_json(command)
            await receipt("before_profile_snapshot", ws, "result")
            await storage.async_upsert_device(
                identity["device_id"], "ios", linked_profile_id="profile-other"
            )
            revoked = await receipt("profile_switch_withdrawal", ws, "auth_invalid")
            assert revoked["code"] == "profile_changed"
            assert (await manager.async_get_active("profile-a")).session_id == session_id
            await ws.close()
            ws = await connect()
            await receipt("new_profile_auth", ws, "auth_ok")
            await ws.send_json(command)
            result = await receipt("old_profile_reconnect", ws, "result")
            assert result["success"] is False
            await ws.close()
            await storage.async_upsert_device(
                identity["device_id"], "ios", linked_profile_id="profile-a"
            )
            ws = await connect()
            await receipt("before_rotation", ws, "auth_ok")
            runtime.device_token = secrets.token_urlsafe(32)
            revoked = await receipt("pairing_rotation_withdrawal", ws, "auth_invalid")
            assert revoked["code"] == "pairing_revoked"
            await ws.close()
            ws = await connect()
            await receipt("stale_pairing_reconnect", ws, "auth_invalid")
            await ws.close()
            runtime.device_token = token
            if "--faults" in sys.argv:
                # Fault injection wraps the real resolver; pairing/auth remains real.
                from custom_components.djconnect import paired_live
                from custom_components.djconnect import api_handlers

                original_resolver = paired_live.async_resolve_device_bound_request_context
                entered, release = asyncio.Event(), asyncio.Event()

                async def stalled_resolver(*args, **kwargs):
                    resolved = await original_resolver(*args, **kwargs)
                    if kwargs.get("request_source") == "paired_live_revalidate":
                        entered.set()
                        await release.wait()
                    return resolved

                paired_live.async_resolve_device_bound_request_context = stalled_resolver
                try:
                    ws = await connect()
                    await entered.wait()
                    runtime.device_token = secrets.token_urlsafe(32)
                    release.set()
                    invalid = await receipt("rotation_during_resolution", ws, "auth_invalid")
                    assert invalid["code"] == "pairing_revoked"
                    await ws.close()
                finally:
                    paired_live.async_resolve_device_bound_request_context = original_resolver
                    runtime.device_token = token
                original_lease = paired_live.LEASE_SECONDS
                original_snapshot = api_handlers._async_owner_broadcast_snapshot_query
                paired_live.LEASE_SECONDS = (
                    2  # Fault-only short timer; real 300s proof is separate.
                )
                entered = asyncio.Event()

                async def stalled_snapshot(*args, **kwargs):
                    entered.set()
                    await asyncio.Future()

                api_handlers._async_owner_broadcast_snapshot_query = stalled_snapshot
                try:
                    ws = await connect()
                    await receipt("fault_deadline_auth", ws, "auth_ok")
                    await ws.send_json(command)
                    await entered.wait()
                    invalid = await receipt("deadline_during_pending_snapshot", ws, "auth_invalid")
                    assert invalid["code"] == "auth_expired"
                    await ws.close()
                    await asyncio.sleep(0.05)
                    assert not session.broadcast._subscribers
                    receipts.append(
                        {"stage": "cancelled_pending_cleanup", "remaining_subscriptions": 0}
                    )
                finally:
                    paired_live.LEASE_SECONDS = original_lease
                    api_handlers._async_owner_broadcast_snapshot_query = original_snapshot
            if "--expiry" in sys.argv:
                ws = await connect()
                await receipt("expiry_auth", ws, "auth_ok")
                frame = await asyncio.wait_for(ws.receive_json(), LEASE_SECONDS + 5)
                assert frame == {"type": "auth_invalid", "code": "auth_expired"}
                receipts.append(
                    {"stage": "real_lease_expiry", "seconds": LEASE_SECONDS, "code": frame["code"]}
                )
                assert (await manager.async_get_active("profile-a")).session_id == session_id
                await ws.close()
            ws = await connect()
            await receipt("before_end", ws, "auth_ok")
            await ws.send_json(command)
            await receipt("end_snapshot", ws, "result")
            await manager.async_end(owner_profile_id="profile-a", session_id=session_id)
            ended = await receipt("session_end", ws, "event")
            for _ in range(8):
                if ended["data"]["event_type"] in {"runtime_ended", "broadcast_stopped"}:
                    break
                ended = await receipt("session_end_followup", ws, "event")
            assert ended["data"]["event_type"] in {"runtime_ended", "broadcast_stopped"}, ended[
                "data"
            ]["event_type"]
            await ws.close()
    result = "BEFORE_CONFIRMED" if "--baseline" in sys.argv else "PASS"
    output = directory / (
        "paired-live-baseline.json" if "--baseline" in sys.argv else "paired-live-acceptance.json"
    )
    output.write_text(
        json.dumps(
            {"result": result, "receipts": receipts, "source_hashes": source_hashes}, indent=2
        )
    )
    print(json.dumps({"result": result, "receipts": receipts}))
    await async_shutdown_persistence(hass)
    await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
