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
from custom_components.djconnect.spotify_connection_repair import binding  # noqa: E402
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
    await ConfigEntryStore(hass).async_save({"entries": [staged.as_storage_fragment]})
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
    original_household = manager.household
    runtime_tokens = []
    reloads = []
    exchanges = []
    hass.data["djconnect"][entry.entry_id] = SimpleNamespace(
        update_spotify_refresh_token=runtime_tokens.append
    )
    hass.http.register_view(http.DJConnectSpotifyCallbackView(hass))
    cases = {}
    async with TestClient(TestServer(hass.http.app)) as client:
        for scenario in [
            "success",
            "profile_changed",
            "account_changed",
            "duplicate_callback",
            "entry_disabled",
        ]:
            manager._household = original_household
            hass.config_entries.async_update_entry(
                entry, data=dict(data), options={"spotify_refresh_token": "SYNTHETIC-OLD"}
            )
            expected = binding(hass, entry)
            assert expected
            state = "fixture-" + scenario
            hass.data["djconnect"]["spotify_oauth_pending"] = {
                state: {
                    "entry_id": entry.entry_id,
                    "client_id": "a" * 32,
                    "code_verifier": "SYNTHETIC-PKCE",
                    "redirect_uri": "https://fixture.invalid/api/djconnect/v1/spotify/callback",
                    "scopes": "user-read-playback-state user-modify-playback-state",
                    "market": "NL",
                    "profile_connection_repair": expected,
                }
            }

            async def exchange(*args, **kwargs):
                exchanges.append(scenario)
                h = manager.household
                if scenario == "profile_changed":
                    device = h.devices[data["device_id"]]
                    manager._household = replace(
                        h, devices={data["device_id"]: replace(device, linked_profile_id="other")}
                    )
                elif scenario == "account_changed":
                    a = h.music_accounts[account.account_id]
                    manager._household = replace(
                        h, music_accounts={a.account_id: replace(a, provider_account_id="b" * 32)}
                    )
                elif scenario == "entry_disabled":
                    await hass.config_entries.async_set_disabled_by(
                        entry.entry_id, ConfigEntryDisabler.USER
                    )
                return {"refresh_token": "SYNTHETIC-NEW"}

            async def reload(entry_id):
                reloads.append(entry_id)

            before_tokens = len(runtime_tokens)
            with (
                patch.object(http, "exchange_code_for_refresh_token", exchange),
                patch.object(hass.config_entries, "async_reload", reload),
            ):
                response = await client.get(
                    "/api/djconnect/v1/spotify/callback",
                    params={"state": state, "code": "synthetic-code"},
                )
                text = await response.text()
                assert "SYNTHETIC-NEW" not in text
                if scenario in {"success", "duplicate_callback"}:
                    assert response.status == 200, (scenario, response.status, text[:200])
                    assert entry.data["profile_id"] == profile.profile_id
                    assert entry.data["music_account_id"] == account.account_id
                    assert entry.data["spotify_refresh_token"] == "SYNTHETIC-NEW"
                    assert "profile_backend_entry_id" not in entry.data
                    assert "spotify_refresh_token" not in entry.options
                    assert len(runtime_tokens) == before_tokens + 1
                    await _save_verified(hass)
                    saved = json.loads(Path(hass.config_entries._store.path).read_text())["data"][
                        "entries"
                    ][0]
                    assert saved["data"]["spotify_refresh_token"] == "SYNTHETIC-NEW"
                    assert "profile_backend_entry_id" not in saved["data"]
                    if scenario == "duplicate_callback":
                        count = len(exchanges)
                        again = await client.get(
                            "/api/djconnect/v1/spotify/callback",
                            params={"state": state, "code": "synthetic-code"},
                        )
                        assert again.status == 400 and len(exchanges) == count
                else:
                    assert response.status == 500
                    assert entry.data == data and len(runtime_tokens) == before_tokens
            cases[scenario] = "PASS"
    assert pins() == original
    (lab / "receipt.json").write_text(
        json.dumps(
            {
                "cases": cases,
                "source_unchanged": True,
                "source_files_sha256": original,
                "real_oauth_calls": 0,
                "installed_mutations": 0,
                "reload_is_fixture": True,
                "actual_ha_store_readback": True,
            },
            indent=2,
        )
    )
    await hass.async_stop(force=True)
    print(json.dumps(cases))


if __name__ == "__main__":
    asyncio.run(main())
