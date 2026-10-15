"""Owned ordinary paired HA + real Spotify normalizer/observer/Runtime chain.
Only the external Spotify response boundary is a declared fixture.
"""

from __future__ import annotations

import asyncio
import json
import hashlib
import os
from pathlib import Path
import secrets
import sys
import socket
from dataclasses import replace
from aiohttp import ClientSession
from homeassistant.helpers import aiohttp_client

from aiohttp.test_utils import TestClient, TestServer
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/verification"))
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.music_dna import MusicDNAManager  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.persistence import (  # noqa: E402
    async_initialize_persistence,
    async_shutdown_persistence,
)
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402


from custom_components.djconnect.verification_clock import VerificationClock  # noqa: E402


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
        cors_origins=["https://localhost:18234"],
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
            "music_backend": "spotify_direct",
            "profile_id": "profile-a",
            "music_account_id":"fixture-account",
            "spotify_client_id":"fixture-client",
            "spotify_refresh_token":"fixture-provider-only",
        },
    )
    # A configured slot, not a paired token. The real HTTP pair handler mints it.
    second_identity = {"device_id": "djconnect-macos-ABCDEF123457", "client_type": "macos"}
    second_slot = entry(
        "second-owner",
        {
            **second_identity,
            "profile_backend_entry_id":"owner-entry",
            "pair_code": "234567",
            "music_backend": "spotify_direct",
            "profile_id": "profile-a",
            "music_account_id":"fixture-account",
            "spotify_client_id":"fixture-client",
            "spotify_refresh_token":"fixture-provider-only",
        },
    )
    store = ConfigEntryStore(hass)
    await store.async_save({"entries": [slot.as_storage_fragment, second_slot.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    slot = hass.config_entries.async_get_entry("owner-entry")
    slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    second_slot = hass.config_entries.async_get_entry("second-owner")
    second_slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    second_runtime = DJConnectRuntime(second_slot)
    runtime = DJConnectRuntime(slot)
    runtime.memory = MusicDNAManager(hass)
    await runtime.memory.async_load()
    hass.data["djconnect"] = {
        "owner-entry": runtime,
        "second-owner": second_runtime,
        "runtime": runtime,
    }
    storage = ProfilePlatformStorage(hass)
    hass.data["djconnect"]["djconnect_profile_platform"] = storage
    await storage.async_upsert_music_backend(
        "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Fixture Spotify"
    )
    for profile in ("profile-a", "profile-other"):
        await storage.async_create_profile(
            profile, profile_id=profile, default_backend_id="spotify_direct"
        )
    await storage.async_upsert_music_account("fixture-account","spotify_direct",
        kind=MusicAccountKind.PERSONAL, display_name="Fixture provider account",
        linked_profile_ids=frozenset({"profile-a"}), provider_account_id="fixture-client")
    profile=storage.household.profiles["profile-a"]
    await storage.async_update_profile("profile-a",preferences=replace(profile.preferences,
        default_music_account_id="fixture-account"))
    await storage.async_upsert_device(identity["device_id"], "ios", linked_profile_id="profile-a")
    await storage.async_upsert_device(
        second_identity["device_id"], "macos", linked_profile_id="profile-a"
    )
    service = await async_initialize_persistence(hass)
    clock = VerificationClock()
    manager = SessionRuntimeManager(
        PersistentSessionRepository(service),
        HistoricalProjectionRepository(service),
        monotonic_source=clock.monotonic,
    )
    hass.data["djconnect"]["session_runtime_manager"] = manager
    provider_session = ClientSession()
    cache_key = aiohttp_client._make_key(True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT)
    hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})[cache_key] = provider_session
    register_http_views(hass)
    await websocket_api.async_setup(hass, {})
    from narrative_album_runtime_acceptance import AlbumLab
    lab = AlbumLab(hass, manager, clock, runtime)
    serve = lab.register_browser()
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((ROOT / "custom_components/djconnect").rglob("*"))
                    if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    users_before = await hass.auth.async_get_users()
    async with TestClient(TestServer(hass.http.app)) as client:
        response = await client.post("/api/djconnect/v1/pair", json={**identity, "pair_code": "123456"})
        paired = await response.json()
        assert response.status == 200 and paired["success"]
        assert runtime.entry.data["device_token"] == paired["device_token"]
        headers = {"Authorization": "Bearer " + paired["device_token"],
                   "X-DJConnect-Device-ID": identity["device_id"]}
        result = await lab.qualify(client, identity, headers)
        result["source_sha256"] = source_hashes
        result["ordinary_pairing"] = True
        result["ha_credentials_issued"] = 0
        assert len(await hass.auth.async_get_users()) == len(users_before)
        (directory / "narrative-ha-receipt.json").write_text(json.dumps(result, indent=2)+"\n")
        if os.environ.get("DJC_NARRATIVE_BROWSER") == "1":
            await serve(client, identity, headers)
        await lab.stop()
    await provider_session.close()
    await async_shutdown_persistence(hass)
    await hass.async_stop()
    print("NARRATIVE_ISOLATED_HA_RUNTIME_PASS", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
