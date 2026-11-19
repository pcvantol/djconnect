"""Real isolated HA OAuth callback/entry Store proof; no live OAuth or HA-dev.

Token exchange and entry reload are explicit fixtures. The router, current
Profile/account/device model, ConfigEntry manager and disk Store are actual HA.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from aiohttp.test_utils import TestClient, TestServer
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import (
    ConfigEntries,
    ConfigEntry,
    ConfigEntryStore,
    ConfigEntryDisabler,
)
from homeassistant.helpers import frame, device_registry, entity_registry, area_registry
from homeassistant import loader, auth

ROOT = Path(os.environ["DJC_SOURCE_ROOT"])
sys.path.insert(0, str(ROOT))
from custom_components.djconnect.domain.storage import ProfilePlatformStorage, STORE_KEY  # noqa: E402
from custom_components.djconnect.domain import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect import http  # noqa: E402
from custom_components.djconnect.spotify_connection_repair import reauthorization_binding  # noqa: E402
from custom_components.djconnect.retired_provider import _save_verified  # noqa: E402


def pins():
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "custom_components/djconnect").rglob("*"))
        if p.is_file() and p.suffix in {".py", ".json", ".js", ".css"}
    }


async def main():
    original = pins()
    lab = Path(os.environ["DJC_LAB_ROOT"])
    config = lab / "empty-ha-config"
    config.mkdir(parents=True)
    hass = HomeAssistant(str(config))
    hass.state = CoreState.running
    frame.async_setup(hass)
    loader.async_setup(hass)
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(
        cors_origins=[],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    hass.config.components.add("http")
    data = {
        "device_id": "djconnect-raspberry-pi-ABCDEF123456",
        "client_type": "raspberry_pi",
        "profile_backend_entry_id": "absent-provider",
        "profile_id": "stale-profile",
    }
    staged = ConfigEntry(
        domain="djconnect",
        title="Synthetic OAuth repair",
        entry_id="paired-pi",
        data=data,
        options={},
        discovery_keys=MappingProxyType({}),
        source="user",
        unique_id="synthetic-repair",
        version=1,
        minor_version=1,
        subentries_data=None,
    )
    from verify_session_conversation_history_http import entry as make_entry
    from homeassistant.config_entries import ConfigEntryState
    staged_owner = make_entry("profile-owner", {"music_backend": "spotify_direct"})
    await ConfigEntryStore(hass).async_save({"entries": [staged.as_storage_fragment, staged_owner.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    entry = hass.config_entries.async_get_entry("paired-pi")
    manager = ProfilePlatformStorage(hass)
    profile = await manager.async_create_profile("DEFAULT")
    await manager.async_upsert_device(
        data["device_id"], "raspberry_pi", linked_profile_id=profile.profile_id
    )
    backend = await manager.async_upsert_music_backend(
        "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Spotify"
    )
    account = await manager.async_upsert_music_account(
        "same-account",
        "spotify_direct",
        kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic account",
        linked_profile_ids=frozenset({profile.profile_id}),
        provider_account_id="a" * 32,
    )
    await manager.async_bind_device_profile_backend(
        data["device_id"], "raspberry_pi", backend, account=account
    )
    hass.data["djconnect"] = {STORE_KEY: manager}
    from custom_components.djconnect import DJConnectRuntime, _async_update_listener, _entry_reload_signature
    from custom_components.djconnect.config_flow import DJConnectOptionsFlow, _options_actions_for_status
    from custom_components.djconnect.spotify_oauth import store_spotify_scope_evidence
    owner = hass.config_entries.async_get_entry("profile-owner")
    owner_data = {"profile_id": profile.profile_id, "music_account_id": account.account_id,
                  "music_backend": "spotify_direct", "spotify_client_id": "a" * 32,
                  "spotify_refresh_token": "SYNTHETIC-ORIGINAL",
                  "ha_external_url": "https://fixture.invalid"}
    caller_data = {**data, "profile_backend_entry_id": owner.entry_id}
    original_household = manager.household
    tokens, wrong_tokens, reloads, completions, exchanges = [], [], [], [], []
    cases = {}
    hass.http.register_view(http.DJConnectSpotifyCallbackView(hass))
    async with TestClient(TestServer(hass.http.app)) as client:
        for scenario in ("success", "duplicate", "profile_changed", "account_changed", "owner_unloaded", "owner_disabled", "requester_replaced", "dead_reference"):
            manager._household = original_household
            owner._async_set_state(hass, ConfigEntryState.LOADED, None)
            if owner.disabled_by is not None:
                await hass.config_entries.async_set_disabled_by(owner.entry_id, None)
            hass.config_entries.async_update_entry(owner, data=dict(owner_data), options={})
            selected = {**caller_data}
            if scenario == "dead_reference":
                selected["profile_backend_entry_id"] = "deleted-owner"
            hass.config_entries.async_update_entry(entry, data=selected, options={})
            owner_runtime = SimpleNamespace(entry=owner, update_spotify_refresh_token=tokens.append)
            unrelated = SimpleNamespace(update_spotify_refresh_token=wrong_tokens.append)
            hass.data["djconnect"][owner.entry_id] = owner_runtime
            hass.data["djconnect"]["runtime"] = unrelated
            assert "spotify_reauthorize" in _options_actions_for_status(hass, dict(entry.data))
            flow = DJConnectOptionsFlow(entry)
            flow.hass, flow.flow_id = hass, "synthetic-options"
            result = await flow.async_step_spotify_reauth()
            assert result["type"] == "external", result
            state = flow._oauth["state"]
            pending = hass.data["djconnect"]["spotify_oauth_pending"][state]
            assert pending["entry_id"] == owner.entry_id
            assert pending["profile_reauthorization"] == reauthorization_binding(hass, entry)
            assert "SYNTHETIC-ORIGINAL" not in repr(pending)
            before = len(tokens)
            async def exchange(*args, **kwargs):
                exchanges.append(scenario)
                household = manager.household
                if scenario == "profile_changed":
                    device = household.devices[data["device_id"]]
                    manager._household = replace(household, devices={device.device_id: replace(device, linked_profile_id="other")})
                elif scenario == "account_changed":
                    manager._household = replace(household, music_accounts={account.account_id: replace(account, provider_account_id="b" * 32)})
                elif scenario == "owner_unloaded":
                    owner._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
                elif scenario == "owner_disabled":
                    await hass.config_entries.async_set_disabled_by(owner.entry_id, ConfigEntryDisabler.USER)
                elif scenario == "requester_replaced":
                    # Exact identity lookup changes across the provider await.
                    lookup = hass.config_entries.async_get_entry
                    replacement = SimpleNamespace(**{k: getattr(entry,k) for k in ("entry_id", "data", "options", "disabled_by")})
                    replacement_holder.append(patch.object(hass.config_entries, "async_get_entry", lambda key: replacement if key == entry.entry_id else lookup(key)))
                    replacement_holder[-1].start()
                return {"refresh_token": "SYNTHETIC-NEW", "scope": "user-read-playback-state"}
            async def reload(entry_id):
                reloads.append(entry_id)
            async def complete(flow_id, user_input):
                completions.append(flow_id)
            replacement_holder = []
            with patch.object(http, "exchange_code_for_refresh_token", exchange), patch.object(hass.config_entries, "async_reload", reload), patch.object(hass.config_entries.options, "async_configure", complete):
                response = await client.get(http.API_SPOTIFY_CALLBACK, params={"state":state,"code":"synthetic"})
                text = await response.text()
                assert "SYNTHETIC-NEW" not in text
                for replacement_patch in replacement_holder:
                    replacement_patch.stop()
                if scenario in {"success", "duplicate", "dead_reference"}:
                    assert response.status == 200, (scenario, response.status, text[:120])
                    assert owner.data["spotify_refresh_token"] == "SYNTHETIC-NEW"
                    assert "spotify_refresh_token" not in entry.data and "spotify_refresh_token" not in entry.options
                    assert entry.options["profile_backend_entry_id"] == owner.entry_id
                    assert len(tokens) == before + 1 and not wrong_tokens
                    assert reloads[-1] == owner.entry_id and completions[-1] == "synthetic-options"
                    await _save_verified(hass)
                    stored = json.loads(Path(hass.config_entries._store.path).read_text())["data"]["entries"]
                    saved = {e["entry_id"]:e for e in stored}
                    assert saved[owner.entry_id]["data"]["spotify_refresh_token"] == "SYNTHETIC-NEW"
                    assert "spotify_refresh_token" not in saved[entry.entry_id]["data"]
                    if scenario == "duplicate":
                        count = len(exchanges)
                        repeated = await client.get(http.API_SPOTIFY_CALLBACK, params={"state":state,"code":"synthetic"})
                        assert repeated.status == 400 and len(exchanges) == count
                else:
                    assert response.status == 500, (scenario, response.status)
                    assert owner.data["spotify_refresh_token"] == "SYNTHETIC-ORIGINAL"
                    assert len(tokens) == before and not wrong_tokens
            cases[scenario] = "PASS"
        manager._household = original_household
        owner._async_set_state(hass, ConfigEntryState.LOADED, None)
        if owner.disabled_by is not None:
            await hass.config_entries.async_set_disabled_by(owner.entry_id, None)
        hass.config_entries.async_update_entry(owner, data=dict(owner_data), options={})
        runtime = DJConnectRuntime(entry=owner)
        hass.data["djconnect"][owner.entry_id] = runtime
        hass.data["djconnect"]["entry_reload_signatures"] = {owner.entry_id: _entry_reload_signature(owner)}
        count = len(reloads)
        with patch.object(hass.config_entries, "async_reload", reload):
            store_spotify_scope_evidence(hass, owner, {"scope":"user-read-playback-state"}, client_id="a"*32)
            await _async_update_listener(hass, owner)
            store_spotify_scope_evidence(hass, owner, {"scope":"user-read-playback-state"}, client_id="a"*32)
            await _async_update_listener(hass, owner)
            assert len(reloads) == count
            hass.config_entries.async_update_entry(owner, data={**owner.data,"spotify_client_id":"b"*32})
            await _async_update_listener(hass, owner)
            assert len(reloads) == count + 1
        cases["metadata_persists_without_reload_real_client_change_reloads"] = "PASS"
        # Initial setup must never overwrite an unrelated existing connection.
        original_token = owner.data["spotify_refresh_token"]
        hass.data["djconnect"]["config_flow_oauth_pending"] = {"initial": {"client_id":"a"*32,"code_verifier":"synthetic","redirect_uri":"https://fixture.invalid"}}
        async def initial_exchange(*args, **kwargs):
            return {"refresh_token":"SYNTHETIC-INITIAL"}
        with patch.object(http, "exchange_code_for_refresh_token", initial_exchange):
            response = await client.get(http.API_SPOTIFY_CALLBACK, params={"state":"initial","code":"synthetic"})
            assert response.status == 200 and owner.data["spotify_refresh_token"] == original_token and not wrong_tokens
        cases["initial_setup_does_not_touch_existing_runtime"] = "PASS"
    assert pins() == original
    (lab/"receipt.json").write_text(json.dumps({"cases":cases,"source_files_sha256":original,
        "source_unchanged":True,"real_oauth_calls":0,"installed_mutations":0,
        "actual_ha_store_readback":True,"token_exchange_reload_options_completion_are_fixtures":True},indent=2))
    await hass.async_stop(force=True)
    print(json.dumps(cases))


if __name__ == "__main__":
    asyncio.run(main())
