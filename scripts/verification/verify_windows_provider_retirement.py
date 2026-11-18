"""Real HA Store/Profile compatibility proof using only isolated synthetic data."""
# ruff: noqa: E402 -- source path is deliberately selected before producer imports.

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import secrets
import sys
import shutil
import threading
import socket
import aiohttp
import sqlite3

from homeassistant.config_entries import (
    ConfigEntries,
    ConfigEntryState,
    ConfigEntryStore,
    ConfigEntryDisabler,
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.helpers import area_registry, device_registry, entity_registry
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(os.environ["DJC_SOURCE_ROOT"])
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/verification"))
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import (
    DJConnectRuntime,
    _async_update_listener,
    register_http_views,
)  # noqa: E402
from custom_components.djconnect.persistence import (
    async_initialize_persistence,
    async_shutdown_persistence,
)  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.domain.profile import ProfilePreferences  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.profile_backend import (
    profile_backend_entry_id,
    profile_backend_runtime,
)  # noqa: E402
from custom_components.djconnect.retired_provider import (
    async_transfer_retired_provider,
    HISTORY_BINDINGS,
)  # noqa: E402
from custom_components.djconnect.session_conversation import (
    async_qualify_history_source,
    async_history_grant_revision,
)  # noqa: E402
from custom_components.djconnect.paired_live_contract import PAIRED_LIVE_PATH


def snapshot_synthetic_storage(config, snapshot):
    """Copy only this lab's real Stores and consistently back up its SQLite."""
    shutil.copytree(
        config / ".storage",
        snapshot / ".storage",
        ignore=shutil.ignore_patterns("djconnect.sqlite3*"),
    )
    with sqlite3.connect(
        f"file:{config / '.storage/djconnect.sqlite3'}?mode=ro", uri=True
    ) as origin:
        with sqlite3.connect(snapshot / ".storage/djconnect.sqlite3") as destination:
            origin.backup(destination)


async def main():
    directory = Path(os.environ["DJC_LAB_ROOT"])
    config = directory / ("provider-config-" + secrets.token_hex(4))
    config.mkdir(parents=True)
    hass = HomeAssistant(str(config))
    hass.state = CoreState.running
    # The genuine cached backend path must never create an SDK zeroconf
    # listener or contact Spotify. Supply a dedicated real HTTP session whose
    # request boundary rejects every network request in this isolated test.
    from homeassistant.helpers import aiohttp_client

    trace = aiohttp.TraceConfig()

    async def reject_external_request(*args):
        raise AssertionError("Provider qualification attempted a network request")

    trace.on_request_start.append(reject_external_request)
    backend_session = aiohttp.ClientSession(trace_configs=[trace])
    key = aiohttp_client._make_key(
        True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT
    )
    hass.data[aiohttp_client.DATA_CLIENTSESSION] = {key: backend_session}
    for registry in (device_registry, entity_registry, area_registry):
        if hasattr(registry, "async_setup"):
            registry.async_setup(hass)
        await registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(
        cors_origins=[],
        use_x_forwarded_for=False,
        login_threshold=-1,
        is_ban_enabled=False,
        use_x_frame_options=True,
    )
    common = {
        "music_backend": "spotify_direct",
        "music_account_id": "account-a",
        "profile_id": "profile-a",
    }
    donor = entry(
        "windows-donor",
        {
            **common,
            "device_id": "djconnect-windows-ABCDEF123456",
            "client_type": "windows",
            "spotify_client_id": "synthetic-public-client",
            "spotify_refresh_token": "synthetic-provider-grant",
        },
    )
    peer = entry(
        "apple-peer",
        {
            **common,
            "device_id": "djconnect-ios-ABCDEF123456",
            "client_type": "ios",
            "pair_code": "123456",
            "profile_backend_entry_id": donor.entry_id,
        },
    )
    store = ConfigEntryStore(hass)
    await store.async_save({"entries": [donor.as_storage_fragment, peer.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    donor, peer = (
        hass.config_entries.async_get_entry(identifier)
        for identifier in (donor.entry_id, peer.entry_id)
    )
    # Synthetic pre-existing loaded slots; all storage and resolution are real.
    for item in (donor, peer):
        item._async_set_state(hass, ConfigEntryState.LOADED, None)
    donor_runtime, peer_runtime = DJConnectRuntime(donor), DJConnectRuntime(peer)
    platform = ProfilePlatformStorage(hass)
    hass.data["djconnect"] = {
        donor.entry_id: donor_runtime,
        peer.entry_id: peer_runtime,
        "runtime": peer_runtime,
        "djconnect_profile_platform": platform,
    }
    await platform.async_upsert_music_backend(
        "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Synthetic connection"
    )
    await platform.async_create_profile(
        "Synthetic listener", profile_id="profile-a", default_backend_id="spotify_direct"
    )
    await platform.async_upsert_music_account(
        "account-a",
        "spotify_direct",
        kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic account",
        provider_account_id="synthetic-public-client",
        linked_profile_ids=frozenset({"profile-a"}),
    )
    await platform.async_update_profile(
        "profile-a",
        preferences=ProfilePreferences(
            default_backend_id="spotify_direct", default_music_account_id="account-a"
        ),
    )
    for item in (donor, peer):
        await platform.async_upsert_device(
            item.data["device_id"], item.data["client_type"], linked_profile_id="profile-a"
        )
    captured = {
        "provider_entry_id": donor.entry_id,
        "backend_id": "spotify_direct",
        "music_account_id": "account-a",
        "provider_account_id": "synthetic-public-client",
    }
    register_http_views(hass)
    initial_users = await hass.auth.async_get_users()
    initial_credentials = sum(len(user.refresh_tokens) for user in initial_users)
    async with TestClient(TestServer(hass.http.app)) as client:
        response = await client.post(
            "/api/djconnect/v1/pair",
            json={"device_id": peer.data["device_id"], "client_type": "ios", "pair_code": "123456"},
        )
        paired = await response.json()
        assert response.status == 200 and paired["success"]
        assert peer.data["device_token"] == paired["device_token"]
    paired_users = await hass.auth.async_get_users()
    assert len(paired_users) == len(initial_users)
    assert sum(len(user.refresh_tokens) for user in paired_users) == initial_credentials
    service = await async_initialize_persistence(hass)
    repository = HistoricalProjectionRepository(service)
    manager = SessionRuntimeManager(PersistentSessionRepository(service), repository)
    hass.data["djconnect"]["session_runtime_manager"] = manager
    session = await manager.async_start(
        owner_profile_id="profile-a",
        music_backend="spotify_direct",
        locale="nl",
        history_source_context=captured,
    )
    await manager.async_update_playback_projection(
        owner_profile_id="profile-a",
        session_id=session.session_id,
        state="playing",
        media_identity="spotify:track:0123456789abcdefghijkL",
        title="Synthetic retained song",
        artist="Synthetic artist",
        album="Synthetic album",
        duration_ms=120000,
        position_ms=1000,
    )
    await manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
    rows = await repository.async_playback_records("profile-a")
    assert len(rows) == 1
    row = rows[0]
    original_body = row["body"]

    async def fresh_history_fixture():
        nonlocal session, row, original_body
        # Negative authority probes can legitimately withdraw their own rows.
        # Use a fresh real Runtime archive for each independent preservation
        # case after those management effects have completely settled.
        await hass.async_block_till_done()
        session = await manager.async_start(
            owner_profile_id="profile-a",
            music_backend="spotify_direct",
            locale="nl",
            history_source_context=captured,
        )
        await manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=session.session_id,
            state="playing",
            media_identity="spotify:track:0123456789abcdefghijkL",
            title="Synthetic retained song",
            artist="Synthetic artist",
            album="Synthetic album",
            duration_ms=120000,
            position_ms=1000,
        )
        await manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        row = next(
            item
            for item in await repository.async_playback_records("profile-a")
            if item["session_id"] == session.session_id
        )
        original_body = row["body"]

    receipts = [
        {
            "stage": "mixed_profile_real_apple_pairing",
            "device_token_from_pair_router": True,
            "ha_user_credentials_issued": 0,
        },
        {
            "stage": "real_runtime_sqlite_history",
            "rows": len(rows),
            "captured_provider_id": donor.entry_id,
        },
    ]
    original_entries = {
        item.entry_id: (dict(item.data), dict(item.options)) for item in (donor, peer)
    }
    listener_calls = []
    reload_dispatches = []

    async def record_reload(entry_id):
        # Loaded fixture slots have no running coordinator. Record the real
        # listener's lifecycle request; full setup/removal is a separate proof.
        reload_dispatches.append(entry_id)
        return True

    hass.config_entries.async_reload = record_reload

    async def eager_listener(host, item):
        listener_calls.append(item.entry_id)
        await _async_update_listener(host, item)

    for item in (donor, peer):
        item.add_update_listener(eager_listener)
    try:
        assert profile_backend_entry_id(hass, "profile-a") == donor.entry_id
        retained_view = profile_backend_runtime(hass, peer_runtime)
        assert retained_view.provider is donor_runtime
        assert await async_qualify_history_source(hass, "profile-a", row)
        before_revision = await async_history_grant_revision(hass, "profile-a")
        token = peer.data["device_token"]
        assert await async_transfer_retired_provider(hass, donor)
        assert profile_backend_entry_id(hass, "profile-a") == peer.entry_id
        assert peer.data["device_token"] == token
        assert (
            "spotify_refresh_token" not in donor.data
            and "spotify_refresh_token" not in donor.options
        )
        assert peer.data["spotify_refresh_token"] == "synthetic-provider-grant"
        assert peer.data[HISTORY_BINDINGS][donor.entry_id]["state"] == "active"
        assert await async_qualify_history_source(hass, "profile-a", row)
        assert row["body"] == original_body
        assert (
            await repository.async_entry_record("profile-a", session.session_id, row["entry_id"])
        )["body"] == original_body
        assert before_revision != await async_history_grant_revision(hass, "profile-a")
        try:
            _ = retained_view.provider
        except ValueError:
            pass
        else:
            raise AssertionError("stale provider view renewed authority")
        receipts.append(
            {
                "stage": "shared_provider_transfer",
                "apple_token_unchanged": True,
                "credential_owners": 1,
                "history_body_unchanged": True,
                "stale_view_rejected": True,
            }
        )
        assert len(listener_calls) >= 3
        assert not reload_dispatches
        receipts.append(
            {"stage": "eager_listener_fence", "calls": len(listener_calls), "reloads": 0}
        )
        first = Path(hass.config_entries._store.path).read_bytes()
        assert await async_transfer_retired_provider(hass, donor)
        assert Path(hass.config_entries._store.path).read_bytes() == first
        receipts.append({"stage": "idempotent_disk_readback", "equal": True})
        cold = await ConfigEntryStore(hass).async_load()
        assert (
            len([item for item in cold["entries"] if item["data"].get("spotify_refresh_token")])
            == 1
        )
        assert (
            next(item for item in cold["entries"] if item["entry_id"] == peer.entry_id)["data"][
                HISTORY_BINDINGS
            ][donor.entry_id]["state"]
            == "active"
        )
        receipts.append({"stage": "real_store_reload", "credential_owners": 1})
        import custom_components.djconnect.retired_provider as retirement

        real_save = retirement._save_verified
        # Preserve the ACTUAL committed intermediate stores before the source
        # transaction continues. A cold manager gets no previous runtime object.
        snapshots = []
        fence = hass.data["djconnect"].setdefault(retirement.TRANSFER_FENCE, set())
        fence.update((donor.entry_id, peer.entry_id))
        for item in (donor, peer):
            before_data, before_options = original_entries[item.entry_id]
            hass.config_entries.async_update_entry(
                item, data=dict(before_data), options=dict(before_options)
            )
        fence.clear()
        donor_runtime.latest_spotify_refresh_token = None
        await real_save(hass)

        async def capture_committed_stage(host):
            await real_save(host)
            snapshot = directory / ("committed-stage-" + secrets.token_hex(4))
            snapshot_synthetic_storage(config, snapshot)
            snapshots.append(snapshot)

        retirement._save_verified = capture_committed_stage
        try:
            assert await async_transfer_retired_provider(hass, donor)
        finally:
            retirement._save_verified = real_save
        assert len(snapshots) == 3
        for boundary, snapshot in enumerate(snapshots, 1):
            reboot = HomeAssistant(str(snapshot))
            reboot.state = CoreState.running
            reboot.config_entries = ConfigEntries(reboot, {})
            await reboot.config_entries.async_initialize()
            reboot_platform = ProfilePlatformStorage(reboot)
            await reboot_platform.async_load()
            reboot.data["djconnect"] = {"djconnect_profile_platform": reboot_platform}
            for loaded in reboot.config_entries.async_entries("djconnect"):
                loaded._async_set_state(reboot, ConfigEntryState.LOADED, None)
                reboot.data["djconnect"][loaded.entry_id] = DJConnectRuntime(loaded)
            try:
                cold_service = await async_initialize_persistence(reboot)
                follower = None
                if boundary in (2, 3):
                    follower_data = {
                        **original_entries[peer.entry_id][0],
                        "device_id": f"djconnect-ios-COLD{boundary:08d}",
                    }
                    follower_data.pop("device_token", None)
                    follower = entry(f"cold-existing-reference-{boundary}", follower_data)
                    follower.disabled_by = ConfigEntryDisabler.USER
                    reboot.config_entries._entries[follower.entry_id] = follower
                    await reboot_platform.async_upsert_device(
                        follower.data["device_id"], "ios", linked_profile_id="profile-a"
                    )
                assert await async_transfer_retired_provider(
                    reboot, reboot.config_entries.async_get_entry(donor.entry_id)
                )
                assert profile_backend_entry_id(reboot, "profile-a") == peer.entry_id
                saved_row = await HistoricalProjectionRepository(cold_service).async_entry_record(
                    "profile-a", session.session_id, row["entry_id"]
                )
                assert saved_row["body"] == original_body
                assert await async_qualify_history_source(reboot, "profile-a", saved_row)
                assert (
                    reboot.config_entries.async_get_entry(peer.entry_id).data["device_token"]
                    == token
                )
                if follower is not None:
                    assert follower.data["profile_backend_entry_id"] == peer.entry_id
                    assert follower.disabled_by is ConfigEntryDisabler.USER
                    assert "device_token" not in follower.data
                    receipts.append(
                        {
                            "stage": "activated_cold_reference_recovery",
                            "boundary": boundary,
                            "existing_reference_rebound": True,
                            "disabled_state_and_no_device_authority_preserved": True,
                        }
                    )
                receipts.append(
                    {
                        "stage": "actual_committed_stage_cold_recovery",
                        "boundary": boundary,
                        "stored_history_body_unchanged": True,
                        "retained_device_token_unchanged": True,
                    }
                )
            finally:
                await async_shutdown_persistence(reboot)
                await reboot.async_stop()
        from custom_components.djconnect.spotify_backend import SpotifyBackend

        retained_backend = SpotifyBackend(hass, peer_runtime)
        peer_runtime.spotify_access_token = "synthetic-cached-access"
        peer_runtime.spotify_access_token_expires_at = 4102444800
        assert await retained_backend._access_token() == "synthetic-cached-access"
        for lifecycle in (
            "runtime_unload",
            "entry_unload",
            "disabled",
            "runtime_replaced",
            "entry_replaced",
        ):
            fence.add(peer.entry_id)
            replacement = None
            if lifecycle == "runtime_unload":
                hass.data["djconnect"].pop(peer.entry_id)
            elif lifecycle == "entry_unload":
                peer._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
            elif lifecycle == "disabled":
                await hass.config_entries.async_set_disabled_by(
                    peer.entry_id, ConfigEntryDisabler.USER
                )
            elif lifecycle == "runtime_replaced":
                hass.data["djconnect"][peer.entry_id] = DJConnectRuntime(peer)
            else:
                replacement = entry(peer.entry_id, dict(peer.data))
                replacement._async_set_state(hass, ConfigEntryState.LOADED, None)
                hass.config_entries._entries[peer.entry_id] = replacement
            fence.clear()
            try:
                await retained_backend._access_token()
            except ValueError:
                pass
            else:
                raise AssertionError("retained backend renewed lifecycle authority: " + lifecycle)
            fence.add(peer.entry_id)
            hass.data["djconnect"][peer.entry_id] = peer_runtime
            if lifecycle == "entry_unload":
                peer._async_set_state(hass, ConfigEntryState.LOADED, None)
            elif lifecycle == "disabled":
                await hass.config_entries.async_set_disabled_by(peer.entry_id, None)
            elif replacement is not None:
                hass.config_entries._entries[peer.entry_id] = peer
            fence.clear()
            assert await retained_backend._access_token() == "synthetic-cached-access"
            receipts.append(
                {
                    "stage": "retained_backend_lifecycle_withdrawal",
                    "condition": lifecycle,
                    "cached_token_denied": True,
                    "no_network_request": True,
                }
            )
        await platform.async_upsert_music_backend(
            "later_manual", BackendProvider.FUTURE_PROVIDER, display_name="Another retained backend"
        )
        await platform.async_update_profile(
            "profile-a", preferences=ProfilePreferences(default_backend_id="later_manual")
        )
        assert await async_qualify_history_source(hass, "profile-a", row)
        try:
            profile_backend_runtime(hass, peer_runtime)
        except ValueError:
            pass
        else:
            raise AssertionError("old account bypassed live default selection")
        try:
            await retained_backend._access_token()
        except ValueError:
            pass
        else:
            raise AssertionError("retained cached backend bypassed live withdrawal")
        assert row["body"] == original_body
        receipts.append(
            {"stage": "default_backend_change", "captured_account_history_retained": True}
        )
        await platform.async_update_profile(
            "profile-a",
            preferences=ProfilePreferences(
                default_backend_id="spotify_direct", default_music_account_id="account-a"
            ),
        )
        await platform.async_create_profile(
            "Other synthetic listener",
            profile_id="profile-other",
            default_backend_id="later_manual",
        )
        await platform.async_upsert_device(
            peer.data["device_id"], "ios", linked_profile_id="profile-other"
        )
        try:
            profile_backend_runtime(hass, peer_runtime)
        except ValueError:
            pass
        else:
            raise AssertionError("handoff followed unrelated Profile")
        assert not await async_qualify_history_source(hass, "profile-a", row)
        await platform.async_upsert_device(
            peer.data["device_id"], "ios", linked_profile_id="profile-a"
        )
        receipts.append(
            {
                "stage": "completed_handoff_profile_reassignment",
                "live_old_account_denied": True,
                "cross_profile_history_alias_denied": True,
            }
        )
        hass.data["djconnect"]["spotify_reauth_issue_throttle"] = {peer.entry_id: 1}
        assert not await async_qualify_history_source(hass, "profile-a", row)
        receipts.append({"stage": "successor_revocation", "history_access": False})
        hass.data["djconnect"].pop("spotify_reauth_issue_throttle")
        import custom_components.djconnect.retired_provider as retirement

        real_save = retirement._save_verified
        fence.update((donor.entry_id, peer.entry_id))
        for item in (donor, peer):
            before_data, before_options = original_entries[item.entry_id]
            hass.config_entries.async_update_entry(
                item, data=dict(before_data), options=dict(before_options)
            )
        unrelated_peer = dict(peer.data)
        unrelated_peer.pop("profile_backend_entry_id")
        hass.config_entries.async_update_entry(peer, data=unrelated_peer)
        donor_runtime.latest_spotify_refresh_token = None
        fence.clear()
        await real_save(hass)
        disk_before = Path(hass.config_entries._store.path).read_bytes()
        await donor.setup_lock.acquire()
        late_transfer = asyncio.create_task(async_transfer_retired_provider(hass, donor))
        try:
            async with asyncio.timeout(2):
                while not donor.setup_lock._waiters:
                    await asyncio.sleep(0)
            fence.add(peer.entry_id)
            hass.config_entries.async_update_entry(
                peer, data={**peer.data, "profile_backend_entry_id": donor.entry_id}
            )
            fence.clear()
        finally:
            donor.setup_lock.release()
        assert not await late_transfer
        assert Path(hass.config_entries._store.path).read_bytes() == disk_before
        assert donor.data["spotify_refresh_token"] == "synthetic-provider-grant"
        receipts.append(
            {
                "stage": "late_related_peer",
                "unlocked_successor_not_used": True,
                "migration_did_not_write": True,
            }
        )
        for boundary in (1, 2, 3):
            fence.update((donor.entry_id, peer.entry_id))
            for item in (donor, peer):
                before_data, before_options = original_entries[item.entry_id]
                hass.config_entries.async_update_entry(
                    item, data=dict(before_data), options=dict(before_options)
                )
            donor_runtime.latest_spotify_refresh_token = None
            fence.clear()
            await real_save(hass)
            calls = 0
            late = None

            async def bind_peer_after_save(host):
                nonlocal calls, late
                calls += 1
                await real_save(host)
                if calls == boundary:
                    late_data = {
                        **original_entries[peer.entry_id][0],
                        "device_id": f"djconnect-ios-LATE{boundary:08d}",
                    }
                    late_data.pop("device_token", None)
                    late = entry(f"late-bound-peer-{boundary}", late_data)
                    hass.config_entries._entries[late.entry_id] = late
                    late._async_set_state(hass, ConfigEntryState.LOADED, None)
                    hass.data["djconnect"][late.entry_id] = DJConnectRuntime(late)
                    await platform.async_upsert_device(
                        late.data["device_id"], "ios", linked_profile_id="profile-a"
                    )
                    await real_save(host)

            retirement._save_verified = bind_peer_after_save
            try:
                await async_transfer_retired_provider(hass, donor)
            except ValueError:
                pass
            else:
                raise AssertionError("new donor reference was stranded")
            finally:
                retirement._save_verified = real_save
            assert late is not None
            assert donor.data["spotify_refresh_token"] == "synthetic-provider-grant"
            assert (
                profile_backend_runtime(hass, hass.data["djconnect"][late.entry_id]).provider
                is donor_runtime
            )
            receipts.append(
                {
                    "stage": "late_reference_rollback",
                    "boundary": boundary,
                    "existing_provider_and_new_reference_retained": True,
                }
            )
            hass.config_entries._entries.pop(late.entry_id)
            hass.data["djconnect"].pop(late.entry_id)
        for condition in (
            "no_loaded_peer",
            "ambiguous_peers",
            "conflicting_grant",
            "malformed_bindings",
            "invalid_prepared_binding",
            "revoked_donor",
        ):
            fence = hass.data["djconnect"].setdefault(retirement.TRANSFER_FENCE, set())
            fence.update((donor.entry_id, peer.entry_id))
            for item in (donor, peer):
                before_data, before_options = original_entries[item.entry_id]
                hass.config_entries.async_update_entry(
                    item, data=dict(before_data), options=dict(before_options)
                )
            donor_runtime.latest_spotify_refresh_token = None
            twin = None
            if condition == "no_loaded_peer":
                hass.data["djconnect"].pop(peer.entry_id)
            elif condition == "ambiguous_peers":
                # Register another source-shaped loaded fixture in the actual
                # manager. No new client setup, token issuance or transport.
                twin = entry(
                    "other-existing-peer", {**peer.data, "device_id": "djconnect-ios-987654ABCDEF"}
                )
                hass.config_entries._entries[twin.entry_id] = twin
                twin._async_set_state(hass, ConfigEntryState.LOADED, None)
                hass.data["djconnect"][twin.entry_id] = DJConnectRuntime(twin)
                await platform.async_upsert_device(
                    twin.data["device_id"], "ios", linked_profile_id="profile-a"
                )
            elif condition == "conflicting_grant":
                hass.config_entries.async_update_entry(
                    peer, data={**peer.data, "spotify_refresh_token": "synthetic-unrelated-grant"}
                )
            elif condition == "malformed_bindings":
                hass.config_entries.async_update_entry(
                    peer, data={**peer.data, HISTORY_BINDINGS: ["unsupported-marker"]}
                )
            elif condition == "invalid_prepared_binding":
                hass.config_entries.async_update_entry(
                    peer,
                    data={
                        **peer.data,
                        HISTORY_BINDINGS: {
                            donor.entry_id: {"state": "prepared", "profile_id": "unrelated"}
                        },
                    },
                )
            else:
                hass.data["djconnect"]["spotify_reauth_issue_throttle"] = {donor.entry_id: 1}
            fence.clear()
            await real_save(hass)
            disk_before = Path(hass.config_entries._store.path).read_bytes()
            assert not await async_transfer_retired_provider(hass, donor)
            assert Path(hass.config_entries._store.path).read_bytes() == disk_before
            assert donor.data["spotify_refresh_token"] == "synthetic-provider-grant"
            assert peer.data["device_token"] == token
            receipts.append(
                {
                    "stage": "closed_quarantine",
                    "condition": condition,
                    "entry_store_unchanged": True,
                    "donor_grant_and_peer_token_retained": True,
                }
            )
            hass.data["djconnect"][peer.entry_id] = peer_runtime
            hass.data["djconnect"].pop("spotify_reauth_issue_throttle", None)
            if twin is not None:
                hass.config_entries._entries.pop(twin.entry_id)
                hass.data["djconnect"].pop(twin.entry_id)
        for boundary in (1, 2, 3):
            fence = hass.data["djconnect"].setdefault(retirement.TRANSFER_FENCE, set())
            fence.update((donor.entry_id, peer.entry_id))
            for item in (donor, peer):
                before_data, before_options = original_entries[item.entry_id]
                hass.config_entries.async_update_entry(
                    item, data=dict(before_data), options=dict(before_options)
                )
            donor_runtime.latest_spotify_refresh_token = None
            fence.clear()
            await real_save(hass)
            calls = 0
            reload_before = len(reload_dispatches)

            async def concurrent_oauth(host):
                nonlocal calls
                calls += 1
                await real_save(host)
                if calls == boundary:
                    fresh = {
                        **donor.data,
                        "spotify_refresh_token": "synthetic-new-oauth-grant",
                        "spotify_client_id": f"synthetic-new-public-client-{boundary}",
                    }
                    hass.config_entries.async_update_entry(donor, data=fresh)
                    donor_runtime.latest_spotify_refresh_token = "synthetic-new-oauth-grant"
                    await real_save(host)

            retirement._save_verified = concurrent_oauth
            try:
                await async_transfer_retired_provider(hass, donor)
            except ValueError:
                pass
            else:
                raise AssertionError("concurrent OAuth was overwritten")
            finally:
                retirement._save_verified = real_save
            await hass.async_block_till_done()
            assert donor.data["spotify_refresh_token"] == "synthetic-new-oauth-grant"
            assert donor.data["spotify_client_id"] == f"synthetic-new-public-client-{boundary}"
            assert "spotify_refresh_token" not in peer.data
            assert donor.entry_id in reload_dispatches[reload_before:]
            cold = await ConfigEntryStore(hass).async_load()
            assert (
                next(item for item in cold["entries"] if item["entry_id"] == donor.entry_id)[
                    "data"
                ]["spotify_refresh_token"]
                == "synthetic-new-oauth-grant"
            )
            receipts.append(
                {
                    "stage": "concurrent_oauth_preserved",
                    "boundary": boundary,
                    "old_copy_not_activated": True,
                    "normal_listener_replayed": True,
                }
            )
        donor_runtime.latest_spotify_refresh_token = None
        for target in (donor, peer):
            for boundary in (1, 2, 3):
                fence.update((donor.entry_id, peer.entry_id))
                for item in (donor, peer):
                    before_data, before_options = original_entries[item.entry_id]
                    hass.config_entries.async_update_entry(
                        item, data=dict(before_data), options=dict(before_options)
                    )
                donor_runtime.latest_spotify_refresh_token = None
                fence.clear()
                await real_save(hass)
                calls = 0
                reload_before = len(reload_dispatches)
                public_client = f"synthetic-rollback-client-{target.entry_id}-{boundary}"

                async def oauth_during_rollback(host):
                    nonlocal calls
                    calls += 1
                    await real_save(host)
                    if calls == boundary:
                        raise OSError("synthetic forward-stage interruption")
                    if calls == boundary + 1:
                        hass.config_entries.async_update_entry(
                            target,
                            data={
                                **target.data,
                                "spotify_refresh_token": "synthetic-rollback-new-grant",
                                "spotify_client_id": public_client,
                            },
                        )
                        await real_save(host)

                retirement._save_verified = oauth_during_rollback
                try:
                    await async_transfer_retired_provider(hass, donor)
                except OSError:
                    pass
                else:
                    raise AssertionError("interrupted forward stage claimed success")
                finally:
                    retirement._save_verified = real_save
                await hass.async_block_till_done()
                assert target.data["spotify_refresh_token"] == "synthetic-rollback-new-grant"
                assert target.entry_id in reload_dispatches[reload_before:]
                cold = await ConfigEntryStore(hass).async_load()
                assert (
                    next(item for item in cold["entries"] if item["entry_id"] == target.entry_id)[
                        "data"
                    ]["spotify_refresh_token"]
                    == "synthetic-rollback-new-grant"
                )
                receipts.append(
                    {
                        "stage": "rollback_oauth_preserved",
                        "target": target.entry_id,
                        "boundary": boundary,
                        "new_grant_retained": True,
                        "normal_listener_replayed": True,
                    }
                )
        for mutation in ("profile_switch", "account_unlink", "successor_runtime_unload"):
            for boundary in (1, 2, 3):
                fence = hass.data["djconnect"].setdefault(retirement.TRANSFER_FENCE, set())
                fence.update((donor.entry_id, peer.entry_id))
                for item in (donor, peer):
                    before_data, before_options = original_entries[item.entry_id]
                    hass.config_entries.async_update_entry(
                        item, data=dict(before_data), options=dict(before_options)
                    )
                fence.clear()
                await real_save(hass)
                calls = 0

                async def mutate_after_save(host):
                    nonlocal calls
                    calls += 1
                    await real_save(host)
                    if calls != boundary:
                        return
                    if mutation == "profile_switch":
                        await platform.async_upsert_device(
                            peer.data["device_id"], "ios", linked_profile_id="profile-other"
                        )
                    elif mutation == "account_unlink":
                        await platform.async_upsert_music_account(
                            "account-a",
                            "spotify_direct",
                            kind=MusicAccountKind.PERSONAL,
                            display_name="Synthetic account",
                            provider_account_id="synthetic-public-client",
                            linked_profile_ids=frozenset(),
                        )
                    else:
                        hass.data["djconnect"].pop(peer.entry_id)

                retirement._save_verified = mutate_after_save
                try:
                    await async_transfer_retired_provider(hass, donor)
                except ValueError:
                    pass
                else:
                    raise AssertionError("changed authority did not abort migration")
                finally:
                    retirement._save_verified = real_save
                assert donor.data["spotify_refresh_token"] == "synthetic-provider-grant"
                assert (
                    peer.data["device_token"] == token and "spotify_refresh_token" not in peer.data
                )
                if mutation == "profile_switch":
                    assert (
                        platform.household.devices[peer.data["device_id"]].linked_profile_id
                        == "profile-other"
                    )
                    await platform.async_upsert_device(
                        peer.data["device_id"], "ios", linked_profile_id="profile-a"
                    )
                elif mutation == "account_unlink":
                    assert not platform.household.music_accounts["account-a"].linked_profile_ids
                    await platform.async_upsert_music_account(
                        "account-a",
                        "spotify_direct",
                        kind=MusicAccountKind.PERSONAL,
                        display_name="Synthetic account",
                        provider_account_id="synthetic-public-client",
                        linked_profile_ids=frozenset({"profile-a"}),
                    )
                else:
                    hass.data["djconnect"][peer.entry_id] = peer_runtime
                receipts.append(
                    {
                        "stage": "changed_authority_abort",
                        "mutation": mutation,
                        "boundary": boundary,
                        "donor_credentials_retained": True,
                        "management_change_preserved": True,
                    }
                )
        for failure_stage in (1, 2, 3):
            fence = hass.data["djconnect"].setdefault(retirement.TRANSFER_FENCE, set())
            fence.update((donor.entry_id, peer.entry_id))
            for item in (donor, peer):
                before_data, before_options = original_entries[item.entry_id]
                hass.config_entries.async_update_entry(
                    item, data=dict(before_data), options=dict(before_options)
                )
            fence.clear()
            await real_save(hass)
            await fresh_history_fixture()
            calls = 0

            async def interrupted_save(host):
                nonlocal calls
                calls += 1
                await real_save(host)
                if calls == failure_stage:
                    raise OSError("synthetic interrupted readback")

            retirement._save_verified = interrupted_save
            try:
                await async_transfer_retired_provider(hass, donor)
            except OSError:
                pass
            else:
                raise AssertionError("injected stage did not fail closed")
            finally:
                retirement._save_verified = real_save
            assert profile_backend_entry_id(hass, "profile-a") == donor.entry_id
            assert await async_qualify_history_source(hass, "profile-a", row)
            assert peer.data["device_token"] == token and row["body"] == original_body
            assert (
                await repository.async_entry_record(
                    "profile-a", session.session_id, row["entry_id"]
                )
            )["body"] == original_body
            cold = await ConfigEntryStore(hass).async_load()
            assert (
                len([item for item in cold["entries"] if item["data"].get("spotify_refresh_token")])
                == 1
            )
            receipts.append(
                {
                    "stage": "interrupted_transfer_rollback",
                    "boundary": failure_stage,
                    "original_owner_restored": True,
                    "history_unchanged": True,
                    "disk_credential_owners": 1,
                }
            )
        for cancellation_stage in (1, 2, 3):
            fence.update((donor.entry_id, peer.entry_id))
            for item in (donor, peer):
                before_data, before_options = original_entries[item.entry_id]
                hass.config_entries.async_update_entry(
                    item, data=dict(before_data), options=dict(before_options)
                )
            fence.clear()
            await real_save(hass)
            await fresh_history_fixture()
            started, release = threading.Event(), threading.Event()
            writer = hass.config_entries._store._write_prepared_data
            writes = 0

            def delayed_writer(mode, payload):
                nonlocal writes
                writes += 1
                if writes == cancellation_stage:
                    started.set()
                    if not release.wait(10):
                        raise TimeoutError("synthetic writer gate")
                writer(mode, payload)

            hass.config_entries._store._write_prepared_data = delayed_writer
            transfer = asyncio.create_task(async_transfer_retired_provider(hass, donor))
            assert await asyncio.to_thread(started.wait, 5)
            transfer.cancel()
            await asyncio.sleep(0)
            assert not transfer.done() and donor.entry_id in fence
            # New and retained provider adapters remain unavailable while the
            # physical writer is unfinished; no fresh refresh lock can escape.
            try:
                profile_backend_runtime(hass, peer_runtime)
            except ValueError:
                pass
            else:
                raise AssertionError("provider exposed during cancellation")
            release.set()
            try:
                await transfer
            except asyncio.CancelledError:
                pass
            else:
                raise AssertionError("cancellation was swallowed")
            finally:
                hass.config_entries._store._write_prepared_data = writer
            assert not fence
            # Reconstruct a cold HA manager and Profile Store from the actual
            # interrupted on-disk stage, without the previous in-memory objects.
            reboot_config = directory / ("cold-provider-" + secrets.token_hex(4))
            snapshot_synthetic_storage(config, reboot_config)
            reboot = HomeAssistant(str(reboot_config))
            reboot.state = CoreState.running
            reboot.config_entries = ConfigEntries(reboot, {})
            await reboot.config_entries.async_initialize()
            reboot_platform = ProfilePlatformStorage(reboot)
            await reboot_platform.async_load()
            reboot.data["djconnect"] = {"djconnect_profile_platform": reboot_platform}
            for loaded in reboot.config_entries.async_entries("djconnect"):
                loaded._async_set_state(reboot, ConfigEntryState.LOADED, None)
                reboot.data["djconnect"][loaded.entry_id] = DJConnectRuntime(loaded)
            try:
                cold_service = await async_initialize_persistence(reboot)
                cold_donor = reboot.config_entries.async_get_entry(donor.entry_id)
                assert await async_transfer_retired_provider(reboot, cold_donor)
                assert profile_backend_entry_id(reboot, "profile-a") == peer.entry_id
                assert await async_qualify_history_source(reboot, "profile-a", row)
                assert (
                    await HistoricalProjectionRepository(cold_service).async_entry_record(
                        "profile-a", session.session_id, row["entry_id"]
                    )
                )["body"] == original_body
                assert (
                    reboot.config_entries.async_get_entry(peer.entry_id).data["device_token"]
                    == token
                )
                receipts.append(
                    {
                        "stage": "cancelled_writer_cold_recovery",
                        "boundary": cancellation_stage,
                        "writer_completed_before_unlock": True,
                        "new_manager_owner": "apple-peer",
                        "history_unchanged": True,
                    }
                )
            finally:
                await async_shutdown_persistence(reboot)
                await reboot.async_stop()
        # Exercise the actual producer quarantine setup and HA manager removal,
        # not a simulated deletion callback or an exception-based deletion veto.
        fence.update((donor.entry_id, peer.entry_id))
        for item in (donor, peer):
            before_data, before_options = original_entries[item.entry_id]
            hass.config_entries.async_update_entry(
                item, data=dict(before_data), options=dict(before_options)
            )
        fence.clear()
        donor_runtime.latest_spotify_refresh_token = None
        await real_save(hass)
        await fresh_history_fixture()
        assert await async_transfer_retired_provider(hass, donor)
        from homeassistant import loader
        from custom_components.djconnect import async_setup_entry
        from homeassistant.helpers import issue_registry

        loader.async_setup(hass)
        assert await async_setup_entry(hass, donor)
        await hass.async_block_till_done()
        assert hass.data["djconnect"]["runtime"] is peer_runtime
        assert not getattr(hass.data["djconnect"][donor.entry_id], "coordinator", None)
        assert issue_registry.async_get(hass).async_get_issue(
            "djconnect", donor.entry_id + "_windows_client_retired"
        )
        receipts.append(
            {
                "stage": "actual_retired_setup",
                "quarantined": True,
                "active_apple_runtime_retained": True,
            }
        )
        await hass.config_entries.async_remove(donor.entry_id)
        assert hass.config_entries.async_get_entry(donor.entry_id) is None
        assert hass.config_entries.async_get_entry(peer.entry_id) is peer
        assert peer.data["device_token"] == token
        assert platform.household.music_accounts["account-a"].linked_profile_ids == frozenset(
            {"profile-a"}
        )
        assert await async_qualify_history_source(hass, "profile-a", row)
        assert (
            await repository.async_entry_record("profile-a", session.session_id, row["entry_id"])
        )["body"] == original_body
        assert not issue_registry.async_get(hass).async_get_issue(
            "djconnect", donor.entry_id + "_windows_client_retired"
        )
        receipts.append(
            {
                "stage": "real_ha_manager_remove",
                "legacy_removed": True,
                "apple_token_and_shared_account_retained": True,
                "persisted_history_body_unchanged": True,
            }
        )
        before_profiles = set(platform.household.profiles)
        reuse = await hass.config_entries.flow.async_init(
            "djconnect", context={"source": "profile_choice"}
        )
        selected = await hass.config_entries.flow.async_configure(
            reuse["flow_id"], {"profile_id": "profile-a"}
        )
        assert selected["type"] == "form" and selected["step_id"] == "voice"
        assert "profile_id" not in selected.get("errors", {})
        hass.config_entries.flow.async_abort(selected["flow_id"])
        draft = await hass.config_entries.flow.async_init(
            "djconnect", context={"source": "profile_setup"}
        )
        duplicate = await hass.config_entries.flow.async_configure(
            draft["flow_id"], {"profile_name": "synthetic LISTENER", "profile_type": "personal"}
        )
        assert (
            duplicate["step_id"] == "profile_setup"
            and duplicate["errors"]["profile_name"] == "profile_name_exists"
        )
        recovered = await hass.config_entries.flow.async_configure(
            duplicate["flow_id"],
            {
                "profile_id": "profile-a",
                "profile_name": "synthetic LISTENER",
                "profile_type": "personal",
            },
        )
        assert recovered["type"] == "form" and recovered["step_id"] == "voice"
        assert set(platform.household.profiles) == before_profiles
        hass.config_entries.flow.async_abort(recovered["flow_id"])
        receipts.append(
            {
                "stage": "actual_flow_manager_profile_reuse",
                "retained_profile_selected": True,
                "duplicate_name_recovers_to_existing_profile": True,
                "no_new_profile_or_oauth": True,
            }
        )
        headers = {
            "Authorization": "Bearer " + token,
            "X-DJConnect-Device-ID": peer.data["device_id"],
        }
        async with TestClient(TestServer(hass.http.app)) as client:
            identity = {"client_type": "ios", "device_id": peer.data["device_id"]}
            path = "/api/djconnect/v1/session/history/" + session.session_id
            response = await client.get(path, params=identity, headers=headers)
            timeline = await response.json()
            assert response.status == 200, (
                response.status,
                timeline.get("error"),
                sorted(timeline),
            )
            assert any(item["entry_id"] == row["entry_id"] for item in timeline["entries"])
            response = await client.get(
                path + "/search", params={**identity, "q": "Synthetic artist"}, headers=headers
            )
            search = await response.json()
            assert response.status == 200 and search["matches"]
            response = await client.post(
                "/api/djconnect/v1/ask_dj/message",
                headers=headers,
                json={
                    **identity,
                    "client_message_id": "retained-history-question",
                    "text": "Wanneer heb ik eerder naar Synthetic artist geluisterd?",
                    "language": "nl",
                    "conversation_context": {"session_id": None},
                },
            )
            answer = await response.json()
            assert response.status == 200 and answer["historical_matches"]
            receipts.append(
                {
                    "stage": "retained_apple_http_after_remove",
                    "ordinary_device_token": True,
                    "timeline_search_and_ask_dj_history": True,
                    "extra_ha_user_credentials": 0,
                }
            )
            live = await manager.async_start(
                owner_profile_id="profile-a",
                music_backend="spotify_direct",
                locale="nl",
                history_source_context={**captured, "provider_entry_id": peer.entry_id},
            )
            async with client.ws_connect(PAIRED_LIVE_PATH) as ws:
                assert (await ws.receive_json(timeout=3))["type"] == "auth_required"
                await ws.send_json(
                    {
                        "type": "auth",
                        "protocol_version": 1,
                        "client_type": "ios",
                        "device_id": peer.data["device_id"],
                        "device_token": token,
                    }
                )
                assert (await ws.receive_json(timeout=3))["type"] == "auth_ok"
                await ws.send_json(
                    {
                        "id": 1,
                        "type": "djconnect/session/broadcast/subscribe",
                        "session_id": live.session_id,
                    }
                )
                snapshot = await ws.receive_json(timeout=3)
                assert snapshot["type"] == "result" and snapshot["success"]
                await manager.async_update_playback_projection(
                    owner_profile_id="profile-a",
                    session_id=live.session_id,
                    state="playing",
                    media_identity="spotify:track:0123456789abcdefghijkL",
                    title="Synthetic live update",
                    artist="Synthetic artist",
                    duration_ms=120000,
                    position_ms=1000,
                )
                update = await ws.receive_json(timeout=3)
                assert update["type"] == "event" and update["data"]["session_id"] == live.session_id
            await manager.async_end(owner_profile_id="profile-a", session_id=live.session_id)
            receipts.append(
                {
                    "stage": "retained_apple_live_after_remove",
                    "actual_pairing_token": True,
                    "auth_snapshot_update": True,
                    "extra_ha_user_credentials": 0,
                }
            )
        output = {
            "assignment": "DJC-CORE-WINDOWS-CLIENT-RETIREMENT-V1-20261011",
            "installed_acceptance": "NOT_CLAIMED",
            "receipts": receipts,
        }
        destination = directory / "windows-provider-candidate.json"
        destination.write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps(output))
    finally:
        await backend_session.close()
        await async_shutdown_persistence(hass)
        await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
