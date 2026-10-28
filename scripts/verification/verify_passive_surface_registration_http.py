"""Actual isolated HA/HTTP and negative pairing hooks; synthetic pair only.

No positive push-purpose commit, key, native request, external network or model.
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

from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth, loader
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState, ConfigEntryStore
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.helpers import area_registry, device_registry, entity_registry, frame

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
from custom_components.djconnect import (  # noqa: E402
    DJConnectRuntime, async_setup, async_unload_entry, _restore_runtime,
)
from custom_components.djconnect.http import _persist_paired_device  # noqa: E402
from custom_components.djconnect import surface_registration as registration  # noqa: E402


def source_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "custom_components/djconnect").rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


async def main():
    before = source_hashes()
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
    assert await async_setup(hass, {})  # Actual registration is idempotent.
    device = "djconnect-ios-ABCDEF123456"
    token = "SYNTHETIC-ONLY-NOT-AN-EXTERNAL-CREDENTIAL"
    original = ConfigEntry(domain="djconnect", title="Synthetic isolated passive pair",
        entry_id="passive-owner", data={"device_id": device, "client_type": "ios",
            "device_token": token, "ha_install_id": "synthetic-ha"}, options={},
        discovery_keys=MappingProxyType({}), source="user", unique_id="synthetic-passive",
        version=1, minor_version=1, subentries_data=None)
    await ConfigEntryStore(hass).async_save({"entries": [original.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    entry = hass.config_entries.async_get_entry(original.entry_id)
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    runtime = _restore_runtime(hass, entry)
    # Startup restoration can retire a local negative fence, never mint A.
    assert runtime.surface_registration_retirement.retired
    assert "surface_registration_authority" not in hass.data["djconnect"]
    headers = {"Authorization": "Bearer " + token, "X-DJConnect-Device-ID": device,
               "X-DJConnect-Client-Type": "ios"}
    receipts = []
    async with TestClient(TestServer(hass.http.app)) as client:
        async def request(method, path, status, *, request_headers=None, **kwargs):
            async with client.request(method, path, headers=headers if request_headers is None else request_headers,
                                      allow_redirects=False, **kwargs) as reply:
                raw = await reply.read()
                assert reply.status == status, (method, path, reply.status, raw)
                assert raw == b'{"version":1,"state":"UNAVAILABLE"}', raw
                assert reply.headers["Cache-Control"] == "no-store"
                assert "Location" not in reply.headers
                receipts.append({"method": method, "path": path, "status": status,
                                 "body_sha256": hashlib.sha256(raw).hexdigest()})

        async def forbidden(*args, **kwargs):
            raise AssertionError("Pure GET attempted state load/write/provider work")
        from homeassistant.helpers.storage import Store
        with patch.object(DJConnectRuntime, "config", new=property(lambda _: (_ for _ in ()).throw(
                AssertionError("GET read Profile-backed runtime.config")))), \
                patch.object(Store, "async_load", forbidden), patch.object(Store, "async_save", forbidden):
            for role in registration.ROLES:
                path = "/api/djconnect/v1/surface_registration/" + role + "/state"
                await request("GET", path, 503)
                await request("GET", path + "?x=1", 400)
                await request("GET", path, 400, data=b"{}")
                await request("POST", path, 405)
                await request("GET", path, 401, request_headers={**headers, "Authorization": "Bearer HA-ADMIN"})
                await request("GET", path, 400, request_headers=[*headers.items(), ("Authorization", "Bearer " + token)])
            assert hass.data["djconnect"][entry.entry_id] is runtime
            assert runtime.entry is entry
        # Actual existing runtime methods; each fresh witness below is explicitly
        # synthetic test pre-state, never a shipping admission/reactivation path.
        def test_runtime():
            current = DJConnectRuntime(entry)
            current.device_token = token
            current.pairing_device_id = device
            current.device_status["device_id"] = device
            return current
        same = test_runtime()
        _persist_paired_device(hass, same, device, None, token, "ios")
        assert not same.surface_registration_retirement.retired
        changed = test_runtime()
        old_retire = registration.PairingRetirement.retire
        pre_assignment = []
        def retire_before_assign(fence):
            pre_assignment.append(changed.pairing_device_id == device)
            old_retire(fence)
        with patch.object(registration.PairingRetirement, "retire", retire_before_assign):
            changed._learn_device_id("djconnect-ios-ZZZZZZ123456")
        assert pre_assignment == [True] and changed.surface_registration_retirement.retired
        empty = DJConnectRuntime(entry)
        assert empty.ensure_device_token() and empty.surface_registration_retirement.retired
        updated = test_runtime()
        updated.update(device_token="SYNTHETIC-REPLACEMENT")
        assert updated.surface_registration_retirement.retired
        # Exercise the actual options repair method up to its first device
        # await, replacing only that external device boundary with a failure.
        from custom_components.djconnect.config_flow import DJConnectOptionsFlow
        paired_data = dict(entry.data)
        repair = test_runtime()
        hass.data["djconnect"][entry.entry_id] = repair
        flow = DJConnectOptionsFlow(entry)
        flow.hass = hass
        class SyntheticRepairStop(BaseException):
            pass
        async def pair_stops(current, current_hass):
            assert current is repair and current_hass is hass
            assert repair.surface_registration_retirement.retired
            assert repair.device_token != token
            raise SyntheticRepairStop
        with patch.object(DJConnectRuntime, "pair_device", pair_stops):
            try:
                await flow._async_retry_pairing()
            except SyntheticRepairStop:
                pass
            else:
                raise AssertionError("Expected synthetic failed device await")
        assert repair.surface_registration_retirement.retired
        hass.config_entries.async_update_entry(entry, data=paired_data)
        # The existing central-install rotation temporarily substitutes entry
        # across an await and restores it in finally: that ABA stays retired.
        from custom_components.djconnect import config_flow
        rotation = test_runtime()
        hass.data["djconnect"][entry.entry_id] = rotation
        captured = registration.observe_pair(hass, headers)
        async def rotation_stops(current_hass, current):
            assert current is rotation and current_hass is hass
            assert rotation.entry is not entry and rotation.surface_registration_retirement.retired
            assert not captured.current(hass)
            raise SyntheticRepairStop
        with patch.object(config_flow, "async_rotate_install_token", rotation_stops):
            try:
                await flow.async_step_central_api({"options_action": "rotate_install_token",
                    "api_base_url": "https://synthetic.example.invalid", "ha_install_id": "synthetic-ha",
                    "djconnect_install_token": "djci_" + "A" * 43})
            except SyntheticRepairStop:
                pass
            else:
                raise AssertionError("Expected synthetic failed install rotation")
        assert rotation.entry is entry and rotation.surface_registration_retirement.retired
        assert not captured.current(hass)
        try:
            registration.observe_pair(hass, headers)
        except registration.RegistrationReadError as error:
            assert error.status == 503
        else:
            raise AssertionError("Retired entry ABA must not allow a fresh capture")
        hass.data["djconnect"][entry.entry_id] = runtime
        # Deliberately fail the first actual unload await, checking local fence
        # is already terminal and remains so on failed unload.
        class SyntheticStop(Exception):
            pass
        runtime.surface_registration_retirement = registration.PairingRetirement()
        async def unload_stops(*args, **kwargs):
            assert runtime.surface_registration_retirement.retired
            raise SyntheticStop
        with patch.object(hass.config_entries, "async_unload_platforms", unload_stops):
            try:
                await async_unload_entry(hass, entry)
            except SyntheticStop:
                pass
            else:
                raise AssertionError("Expected synthetic failed unload")
        assert runtime.surface_registration_retirement.retired
    assert source_hashes() == before
    result = {"status": "PASS", "scope": "Actual HA paired passive role HTTP and pre-assignment/pre-await negative hooks",
        "source_hashes": before, "source_before_after_equal": True, "cases": receipts,
        "no_profile_or_session_required": True, "no_GET_store_load_write_or_runtime_config": True,
        "duplicate_pair_no_new_fence": True, "actual_runtime_learning_fenced_before_assignment": True,
        "actual_unload_fenced_before_failed_await": True, "restore_does_not_mint_authority": True,
        "actual_options_repair_fenced_before_failed_device_await": True,
        "actual_runtime_update_token_fenced": True,
        "actual_temporary_entry_rotation_failed_await_ABA_stays_retired": True,
        "model_calls": 0, "external_provider_calls": 0,
        "positive_purpose_commit_native_installed_provider": "NOT_RUN"}
    (lab / "http-producer-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "cases": len(receipts)}))


if __name__ == "__main__":
    asyncio.run(main())
