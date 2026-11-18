"""Actual isolated HA auth/middleware/admin preparation; synthetic users only.

No real credentials, custody key, principal, API/provider or device operation.
Run in an owned network-none HA container with an empty disposable config.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from types import MappingProxyType
from unittest.mock import patch
import uuid

from aiohttp.test_utils import TestClient, TestServer
from aiohttp.client_exceptions import ServerDisconnectedError
from homeassistant import auth, loader
from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_USER
from homeassistant.auth import models
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState, ConfigEntryStore
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry, frame

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
from custom_components.djconnect import async_setup, _restore_runtime  # noqa: E402
from custom_components.djconnect import installation_management as mgmt  # noqa: E402


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "custom_components/djconnect").rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


async def main():
    before = hashes()
    lab = Path(os.environ["DJC_LAB_ROOT"])
    config = lab / "empty-ha-config"
    config.mkdir(parents=True, exist_ok=False)
    hass = HomeAssistant(str(config))
    hass.state = CoreState.running
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(cors_origins=[], use_x_forwarded_for=False,
        login_threshold=-1, is_ban_enabled=False, use_x_frame_options=True)
    hass.config.components.add("http")
    frame.async_setup(hass)
    loader.async_setup(hass)
    assert await async_setup(hass, {})
    entry = ConfigEntry(domain="djconnect", title="Synthetic management context",
        entry_id="management-fixture", data={"device_id": "djconnect-ios-ABCDEF123456",
            "client_type": "ios", "device_token": "SYNTHETIC-PAIR-NOT-HA-AUTH",
            "ha_install_id": "ha_synthetic_context_metadata"}, options={},
        discovery_keys=MappingProxyType({}), source="user", unique_id="synthetic-management",
        version=1, minor_version=1, subentries_data=None)
    await ConfigEntryStore(hass).async_save({"entries": [entry.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    entry = hass.config_entries.async_get_entry(entry.entry_id)
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    runtime = _restore_runtime(hass, entry)
    path = "/api/djconnect/v1/installation/" + entry.entry_id + "/management/prepare"
    receipts = []

    async def credentials(*, admin=True, system=False, long_lived=False):
        name = "Synthetic-" + uuid.uuid4().hex
        if system:
            user = await hass.auth.async_create_system_user(name, group_ids=[GROUP_ID_ADMIN])
        else:
            user = await hass.auth.async_create_user(name,
                group_ids=[GROUP_ID_ADMIN if admin else GROUP_ID_USER])
        token_type = (models.TOKEN_TYPE_SYSTEM if system else
            models.TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN if long_lived else models.TOKEN_TYPE_NORMAL)
        refresh = await hass.auth.async_create_refresh_token(user,
            client_id="http://synthetic.invalid" if token_type == models.TOKEN_TYPE_NORMAL else None,
            client_name=name if long_lived else None, token_type=token_type)
        access = hass.auth.async_create_access_token(refresh)
        return user, refresh, {"Authorization": "Bearer " + access}

    def body(operation=None):
        return {"contract_version": 1, "operation_id": operation or str(uuid.uuid4()),
            "action": "prepare_custody", "policy_id": "software_p256_ha_file_v1",
            "acknowledgement": "preparation_only_no_key_effect"}

    async with TestClient(TestServer(hass.http.app)) as client:
        async def post(label, headers, status, *, payload=None, raw=None, url=path):
            kwargs = {"json": body() if payload is None else payload} if raw is None else {
                "data": raw, "headers": {**headers, "Content-Type": "application/json"}}
            if "headers" not in kwargs:
                kwargs["headers"] = headers
            async with client.post(url, allow_redirects=False, **kwargs) as response:
                data = await response.read()
                assert response.status == status, (label, response.status, data)
                result = json.loads(data) if status != 401 else {}
                if status != 401:  # Middleware's own unauthenticated reply is HA-owned.
                    assert response.headers.get("Cache-Control") == "no-store"
                assert b"SYNTHETIC-PAIR" not in data and b"Bearer " not in data
                assert b"refresh_token" not in data and b"ha_synthetic_context" not in data
                receipts.append({"case": label, "status": status,
                    "body_sha256": hashlib.sha256(data).hexdigest()})
                return result

        # HA makes its first ordinary user the owner. Create that isolated
        # bootstrap owner first so the negative really exercises a non-admin.
        owner, _, _ = await credentials()
        assert owner.is_owner and owner.is_admin
        await post("paired bearer is not HA auth", {"Authorization": "Bearer SYNTHETIC-PAIR-NOT-HA-AUTH"}, 401)
        regular, _, nonadmin = await credentials(admin=False)
        assert not regular.is_owner and not regular.is_admin
        await post("real nonadmin HA user", nonadmin, 403)
        _, _, system = await credentials(system=True)
        await post("real system HA user", system, 403)
        _, _, long_lived = await credentials(long_lived=True)
        await post("explicit LLAT rejection", long_lived, 403)
        user, refresh, headers = await credentials()
        operation = str(uuid.uuid4())
        prepared = await post("actual normal admin preparation", headers, 200, payload=body(operation))
        assert prepared["classification"] == "HA_ADMIN_PREPARATION_ONLY"
        assert prepared["execution_available"] is False
        registry = hass.data["djconnect"][mgmt.KEY]
        scope = registry._handles[prepared["handle"]]
        assert scope._operation == operation and not scope._retired
        assert not isinstance(scope, __import__("custom_components.djconnect.installation_custody_once",
            fromlist=["CustodyOperationOwner"]).CustodyOperationOwner)
        assert not any(hasattr(scope, name) for name in ("generate", "generate_once", "sign", "bootstrap_possession_once"))
        await post("same original operation not reissued", headers, 409, payload=body(operation))
        second = await post("same refresh second independent preparation", headers, 200)
        second_scope = registry._handles[second["handle"]]
        hass.auth.async_remove_refresh_token(refresh)
        assert scope._retired and prepared["handle"] not in registry._handles
        assert second_scope._retired and second["handle"] not in registry._handles
        assert registry._operations[operation] is None
        receipts.append({"case": "actual synchronous refresh revoke fence", "pass": True})

        user, refresh, headers = await credentials()
        prepared = await post("prepare before admin ABA", headers, 200)
        scope = registry._handles[prepared["handle"]]
        await hass.auth.async_update_user(user, group_ids=[GROUP_ID_USER])
        assert scope._retired
        await hass.auth.async_update_user(user, group_ids=[GROUP_ID_ADMIN])
        assert scope._retired and prepared["handle"] not in registry._handles
        receipts.append({"case": "actual HA admin removal/readd ABA remains retired", "pass": True})

        _, _, headers = await credentials()
        await post("query rejected", headers, 400, url=path + "?authSig=not-a-management-credential")
        await post("closed request rejects owner bool", headers, 400, payload={**body(), "owner": True})
        raw = json.dumps(body()).encode()
        await post("duplicate original version rejected", headers, 400,
            raw=b'{"contract_version":1,' + raw[1:])
        await post("oversize body rejected", headers, 413, raw=b" " * 4097)
        await post("boolean version rejected", headers, 400, payload={**body(), "contract_version": True})
        await post("noncanonical operation rejected", headers, 400,
            payload={**body(), "operation_id": str(uuid.uuid4()).upper()})
        await post("invalid UTF8 rejected", headers, 400, raw=b'{"x":"\xff"}')
        await post("duplicate bearer refused", [("Authorization", headers["Authorization"]),
            ("Authorization", headers["Authorization"])], 401)

        # Real selected entry/config/runtime checks, without a device operation.
        for change in ("configuration", "runtime", "entry_state"):
            _, _, context_headers = await credentials()
            prepared_context = await post("prepare before " + change, context_headers, 200)
            captured = registry._handles[prepared_context["handle"]]
            old_options = dict(entry.options)
            if change == "configuration":
                hass.config_entries.async_update_entry(entry, options={**old_options, "synthetic_revision": 1})
            elif change == "runtime":
                hass.data["djconnect"][entry.entry_id] = object()
            else:
                entry._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
            try:
                captured.require_current()
            except mgmt.ManagementError:
                pass
            else:
                raise AssertionError("Changed selected context accepted: " + change)
            assert captured._retired and prepared_context["handle"] not in registry._handles
            if change == "configuration":
                hass.config_entries.async_update_entry(entry, options=old_options)
            elif change == "runtime":
                hass.data["djconnect"][entry.entry_id] = runtime
            else:
                entry._async_set_state(hass, ConfigEntryState.LOADED, None)
            assert captured._retired  # Restoring state cannot revive this original.
            receipts.append({"case": "selected " + change + " rejects and remains retired after restore", "pass": True})

        # Actual HTTP/middleware request held across a body await. The real HA
        # auth mutation retires the server scope before the original resumes.
        user, refresh, headers = await credentials()
        release = asyncio.Event()

        async def stream():
            yield b'{"contract_version":1,'
            await release.wait()
            yield json.dumps(body()).encode().split(b",", 1)[1]

        task = asyncio.create_task(client.post(path, data=stream(), headers={
            **headers, "Content-Type": "application/json"}))
        for _ in range(200):
            if registry._pending:
                break
            await asyncio.sleep(.005)
        assert len(registry._pending) == 1
        pending = next(iter(registry._pending))
        hass.auth.async_remove_refresh_token(refresh)
        assert pending._retired
        release.set()
        response = await task
        assert response.status == 410, await response.read()
        await response.read()
        receipts.append({"case": "real refresh revoke during body await rejects late reply", "pass": True})

        # Cancel the actual server request task while its real body read waits.
        # This checks the handler's cancellation/finally path, not a fake owner.
        _, _, headers = await credentials()
        release = asyncio.Event()
        task = asyncio.create_task(client.post(path, data=stream(), headers={
            **headers, "Content-Type": "application/json"}))
        for _ in range(200):
            if registry._pending:
                break
            await asyncio.sleep(.005)
        assert len(registry._pending) == 1
        cancelled = next(iter(registry._pending))
        cancelled._task.cancel()
        try:
            await task
        except ServerDisconnectedError:
            pass
        else:
            raise AssertionError("Cancelled server request returned a response")
        finally:
            release.set()
        assert cancelled._retired and cancelled not in registry._pending
        assert cancelled._token == "" and cancelled.user is None
        receipts.append({"case": "actual request cancellation during body await leaves no authority", "pass": True})

        # Actual HA public configuration updates cannot restore the captured
        # mapping object, even when the same original values return (A→B→A).
        _, _, headers = await credentials()
        before_aba = await post("prepare before HA config ABA", headers, 200)
        config_scope = registry._handles[before_aba["handle"]]
        original_options = entry.options
        hass.config_entries.async_update_entry(entry, options={**original_options, "synthetic_aba": 1})
        hass.config_entries.async_update_entry(entry, options=original_options)
        assert entry.options == original_options and entry.options is not original_options
        try:
            config_scope.require_current()
        except mgmt.ManagementError:
            pass
        else:
            raise AssertionError("HA configuration ABA restored original preparation")
        assert config_scope._retired
        receipts.append({"case": "actual HA public configuration ABA cannot restore original mapping identity", "pass": True})

        # Exercise the real OptionsFlow's temporary-entry/finally-restore path.
        # Only the provider effect port is replaced: no request is actually sent.
        from custom_components.djconnect import config_flow
        original_entry = runtime.entry
        existing = await post("prepare before real temporary entry flow", headers, 200)
        existing_scope = registry._handles[existing["handle"]]
        body_release, rotate_entered, rotate_release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_body = json.dumps(body()).encode()

        async def held_body():
            yield original_body[:1]
            await body_release.wait()
            yield original_body[1:]

        pending_request = asyncio.create_task(client.post(path, data=held_body(), headers={
            **headers, "Content-Type": "application/json"}))
        for _ in range(200):
            if registry._pending:
                break
            await asyncio.sleep(.005)
        assert len(registry._pending) == 1
        original_pending = next(iter(registry._pending))

        async def failed_rotate(_hass, actual_runtime):
            assert actual_runtime is runtime and actual_runtime.entry is not original_entry
            rotate_entered.set()
            await rotate_release.wait()
            raise RuntimeError("synthetic bounded rotation failure")

        flow = config_flow.DJConnectOptionsFlow(entry)
        flow.hass = hass
        with patch.object(config_flow, "async_rotate_install_token", failed_rotate):
            rotation = asyncio.create_task(flow.async_step_central_api({
                config_flow.OPTIONS_ACTION_FIELD: config_flow.OPTIONS_ACTION_ROTATE_INSTALL_TOKEN,
                config_flow.CONF_API_BASE_URL: "https://synthetic.invalid",
                config_flow.CONF_HA_INSTALL_ID: "ha_synthetic_context_metadata",
                config_flow.CONF_DJCONNECT_INSTALL_TOKEN: config_flow.TOKEN_PREFIX + "SYNTHETIC"}))
            await asyncio.wait_for(rotate_entered.wait(), 2)
            # Restore A before releasing the original request. Current identities
            # alone cannot detect this genuine A→temporary→A product flow.
            rotate_release.set()
            try:
                await rotation
            except RuntimeError as error:
                assert str(error) == "synthetic bounded rotation failure"
            else:
                raise AssertionError("Synthetic rotation unexpectedly completed")
        assert runtime.entry is original_entry
        body_release.set()
        reply = await pending_request
        actual_status = reply.status
        await reply.read()
        assert existing_scope._retired and original_pending._retired
        assert existing["handle"] not in registry._handles and actual_status == 410
        receipts.append({"case": "real OptionsFlow failed temporary entry ABA retires pending and prepared management", "pass": True})

        # Canonical runtime.update uses the same synchronous negative hook before
        # token setters. A cleanup error cannot keep a sibling preparation alive.
        a = await post("prepare before runtime setter A", headers, 200)
        b = await post("prepare before runtime setter B", headers, 200)
        first_scope, second_scope = registry._handles[a["handle"]], registry._handles[b["handle"]]

        def broken_cleanup():
            raise RuntimeError("synthetic unsubscribe failure")

        first_scope._unsubscribers.append(broken_cleanup)
        original_token = runtime.device_token
        runtime.update(device_token="SYNTHETIC-NEW-PAIRING-TOKEN")
        runtime.update(device_token=original_token)
        assert first_scope._retired and second_scope._retired
        assert first_scope._cleanup_incomplete and not second_scope._cleanup_incomplete
        assert a["handle"] not in registry._handles and b["handle"] not in registry._handles
        receipts.append({"case": "runtime setter ABA retires all siblings despite cleanup failure", "pass": True})

        # Synthetic deterministic clock samples affect ONLY this module, not HA
        # JWT validation, the event loop or any live server clock.
        _, _, headers = await credentials()
        with patch.object(mgmt, "_samples", return_value=(1000.0, 200.0)):
            prepared = await post("fixed original local clock", headers, 200)
            assert prepared["expires_at_ms"] == 1120000
            scope = registry._handles[prepared["handle"]]
            with patch.object(mgmt, "_samples", return_value=(1120.0, 320.0)):
                try:
                    scope.require_current()
                except mgmt.ManagementError:
                    pass
                else:
                    raise AssertionError("Exact original expiry accepted")
            assert scope._retired
        receipts.append({"case": "exact original wall and mono expiry closes", "pass": True})
        assert hass.data["djconnect"][entry.entry_id] is runtime and runtime.entry is entry

    assert hashes() == before
    result = {"classification": "ACTUAL_ISOLATED_HA_ADMIN_PREPARATION_TESTS_ONLY",
        "source_sha256": before, "cases": receipts,
        "actual_HA_auth_users_tokens_middleware": True,
        "real_service_key_or_custody_effect": False, "provider_or_device_effect": False,
        "native_or_push_acceptance": False}
    (lab / "installation-management-ha-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print("HA_ADMIN_MANAGEMENT_PASS", len(receipts))
    await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
