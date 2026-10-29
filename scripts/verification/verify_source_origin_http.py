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
from homeassistant import auth, loader
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry, frame

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/verification"))
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, async_setup  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.music_dna import MusicDNAManager  # noqa: E402
from custom_components.djconnect.profile_context import profile_storage  # noqa: E402
from custom_components.djconnect.persistence import (  # noqa: E402
    async_initialize_persistence,
    async_shutdown_persistence,
)


from custom_components.djconnect.verification_clock import VerificationClock  # noqa: E402


from session_forecast_runtime_acceptance import ForecastLab  # noqa: E402
from unittest.mock import patch  # noqa: E402


class SourceOriginLab(ForecastLab):
    async def qualify(self, client, identity, headers):
        self.owner = {"client": client, "identity": identity, "headers": headers}
        await self.start()
        active = self.manager.current_active("profile-a")
        original = getattr(self.manager, "_source_origins", {}).get(active.session_id)
        assert original is not None, "Actual Session/source adoption has no original SourceOrigin"
        from custom_components.djconnect import surface_source_origin as origins, profile_observation
        from custom_components.djconnect.profile_context import profile_storage
        accepted = original.validate_original_capture()
        assert accepted.phase == "accepted" and accepted.revision == 1
        assert original.observer is self.observer._spotify_sessions["profile-a"]
        await self.step(1)
        assert accepted.origin != active.broadcast.original_status_sample.sample_id
        cases = ["actual_component_bootstrap_committed_Profile_HTTP_Session_ACTIVE_and_observer_source_origin"]
        async def rows():
            return await self.manager._persistent_sessions._persistence.async_in_transaction(lambda tx:
                tx.fetchall("SELECT origin_id,phase,revision FROM djconnect_source_origins"))
        before = await rows()
        response = await client.post("/api/djconnect/v1/session/start", headers=headers,
            json={**identity,"session_start_strategy":"discover"})
        assert response.status == 409
        assert await rows() == before and original.validate_original_capture() == accepted
        cases.append("duplicate_start_and_new_sample_do_not_mint_or_renew_original_source_origin")
        await self.manager._lock.acquire()
        try:
            task = asyncio.create_task(self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id))
            await asyncio.sleep(0)
            assert original.retired and original.committed is None and original.runtime is None
            try:
                original.validate_original_capture()
            except PermissionError:
                pass
            else:
                raise AssertionError("Source origin survived original end before lock")
        finally:
            self.manager._lock.release()
        await task
        await self.hass.async_block_till_done()
        assert (accepted.origin,"retired",2) in await rows()
        cases.append("actual_end_retires_original_source_before_manager_lock_and_uses_reserved_terminal")
        async def fresh():
            active = await self.start()
            original = self.manager._source_origins.get(active.session_id)
            assert original is not None
            original.validate_original_capture()
            return active, original
        active, original = await fresh()
        assert self.integration.surface_registration_retirement.retired  # Old public role stays closed.
        before = await rows()
        for role in ("widget_transport", "status_activity_transport"):
            reply = await client.get("/api/djconnect/v1/surface_registration/" + role + "/state",
                headers={**headers,"X-DJConnect-Client-Type":"ios"})
            assert reply.status == 503 and await reply.read() == b'{"version":1,"state":"UNAVAILABLE"}'
        assert before == await rows() and not original.retired
        cases.append("new_source_DATA_does_not_rearm_old_public_role_fence_or_expose_positive_HTTP")
        store = profile_storage(self.hass)
        old_reader = profile_observation.capture_committed(self.hass)
        await store.async_load()  # Actual cached path, not a new snapshot/adoption.
        assert not old_reader.current() and original.validate_original_capture().origin == original.origin
        assert before == await rows()
        cases.append("actual_cached_Store_read_preserves_original_source_but_old_Help_snapshot_semantics_remain")

        await self.manager._lock.acquire()
        try:
            writer = asyncio.create_task(store.async_update_profile("profile-a", display_name="Changed fixture owner"))
            await asyncio.sleep(0)
            assert original.retired and original.committed is None and original.runtime is None
            assert not writer.done()
        finally:
            self.manager._lock.release()
        await writer
        await self.hass.async_block_till_done()
        assert (original.origin,"retired",2) in await rows()
        cases.append("queued_real_Profile_write_retires_and_drops_original_before_manager_lock_or_commit")

        active, original = await fresh()
        entered, release = asyncio.Event(), asyncio.Event()
        from custom_components.djconnect import api_handlers
        discover = api_handlers._discover_context_for_session
        captured = []
        capture = origins.capture_session_source
        def take_capture(*args):
            result = capture(*args)
            captured.append(result)
            return result
        async def hold_discover(*args):
            entered.set()
            await release.wait()
            return await discover(*args)
        await self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id)
        before = await rows()
        with patch.object(origins,"capture_session_source",take_capture), \
             patch.object(api_handlers,"_discover_context_for_session",hold_discover):
            task = asyncio.create_task(client.post("/api/djconnect/v1/session/start",headers=headers,
                json={**identity,"session_start_strategy":"discover"}))
            try:
                await asyncio.wait_for(entered.wait(),5)
                assert len(captured)==1 and captured[0] is not None
                await store.async_update_profile("profile-a",display_name="Changed while discovering")
                assert captured[0].retired
            finally:
                release.set()
            reply = await asyncio.wait_for(task,10)
            assert reply.status == 201, await reply.json()
        active = self.manager.current_active("profile-a")
        assert active.session_id not in self.manager._source_origins and before == await rows()
        cases.append("actual_discovery_await_uses_original_preawait_source_and_late_result_cannot_adopt")

        active, original = await fresh()
        await self.manager.async_update_mood(owner_profile_id="profile-a",session_id=active.session_id,
            selected_mood="party",expected_revision=active.mood_revision)
        assert original.retired and original.committed is None
        await self.hass.async_block_till_done()
        assert (original.origin,"retired",2) in await rows()
        cases.append("real_settings_axis_change_retires_original_source_without_new_UUID_or_replay")

        active, original = await fresh()
        observed = self.observer._spotify_sessions["profile-a"]
        await self.observer.async_stop("profile-a",active.session_id)
        assert original.retired and original.observer is None
        origins.attach_observer(self.manager,observed)
        assert active.session_id not in self.manager._source_origins
        cases.append("actual_observer_withdrawal_cannot_rebind_retired_source_from_equal_observer")

        # Hold the actual initial-narration boundary of request A. End A and
        # start B through real HTTP while A is suspended; A must never replace
        # B's observer, even if both use the very same integration runtime.
        second_identity = {"device_id":"djconnect-macos-ABCDEF123457","client_type":"macos"}
        # The legacy ordinary pairing endpoint uses its selected config-flow slot.
        self.hass.data["djconnect"]["runtime"] = self.hass.data["djconnect"]["second-owner"]
        try:
            paired_reply = await client.post("/api/djconnect/v1/pair",
                json={**second_identity,"pair_code":"234567"})
            second_pair = await paired_reply.json()
        finally:
            self.hass.data["djconnect"]["runtime"] = self.integration
        assert paired_reply.status == 200
        second_headers = {"Authorization":"Bearer "+second_pair["device_token"],
            "X-DJConnect-Device-ID":second_identity["device_id"]}
        narration = api_handlers._async_generate_initial_session_moment
        for different_runtime in (False, True):
            active = self.manager.current_active("profile-a")
            if active:
                await self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id)
            entered, release = asyncio.Event(), asyncio.Event()
            suspended = []
            async def hold_first_narration(*args, **kwargs):
                if not suspended:
                    suspended.append(kwargs["session"])
                    entered.set()
                    await release.wait()
                return await narration(*args, **kwargs)
            with patch.object(api_handlers,"_async_generate_initial_session_moment",hold_first_narration):
                task = asyncio.create_task(client.post("/api/djconnect/v1/session/start",headers=headers,
                    json={**identity,"session_start_strategy":"discover"}))
                try:
                    await asyncio.wait_for(entered.wait(),5)
                    first = suspended[0]
                    await self.manager.async_end(owner_profile_id="profile-a",session_id=first.session_id)
                    reply = await client.post("/api/djconnect/v1/session/start",
                        headers=second_headers if different_runtime else headers,
                        json={**(second_identity if different_runtime else identity),"session_start_strategy":"discover"})
                    assert reply.status == 201, await reply.json()
                    current = self.manager.current_active("profile-a")
                    bound = self.manager._source_origins[current.session_id]
                    observer = self.observer._spotify_sessions["profile-a"]
                    expected_runtime = self.hass.data["djconnect"]["second-owner"] if different_runtime else self.integration
                    assert observer.integration_runtime is expected_runtime
                    assert bound.validate_original_capture().origin == bound.origin
                finally:
                    release.set()
                stale = await asyncio.wait_for(task,10)
                await stale.read()  # Delivery is denied separately by its original Session guard.
                assert self.observer._spotify_sessions["profile-a"] is observer
                assert observer.integration_runtime is expected_runtime
                assert bound.validate_original_capture().origin == bound.origin
            cases.append("late_original_narration_cannot_replace_new_Session_observer_"+
                ("different_runtime" if different_runtime else "same_runtime"))

        active = self.manager.current_active("profile-a")
        await self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id)
        async def failed_initial_narration(*args, **kwargs):
            raise RuntimeError("synthetic_initial_narration_failure_before_observer")
        with patch.object(api_handlers,"_async_generate_initial_session_moment",failed_initial_narration):
            failed = await client.post("/api/djconnect/v1/session/start",headers=headers,
                json={**identity,"session_start_strategy":"discover"})
            assert failed.status == 500
            await failed.read()
        await self.hass.async_block_till_done()
        active = self.manager.current_active("profile-a")
        original = self.manager._source_origins[active.session_id]
        assert original.phase == "accepted" and original.observer is None
        assert original._creator_done and original._creator_ref is None
        # Obtain a real observer through the shipping observation manager. Its
        # new task cannot adopt the orphaned accepted DATA root either.
        await self.observer.async_start_spotify(integration_runtime=self.integration,session=active,
            insight_provider_factory=lambda runtime, session:
                api_handlers._session_track_insight_provider(self.hass,runtime,session))
        observed = self.observer._spotify_sessions["profile-a"]
        assert original.observer is None
        finished = asyncio.get_running_loop().create_future()
        def actual_no_task_callback():
            assert asyncio.current_task() is None
            origins.attach_observer(self.manager,observed)
            finished.set_result(None)
        asyncio.get_running_loop().call_soon(actual_no_task_callback)
        await finished
        assert original.observer is None
        try:
            original.validate_original_capture()
        except PermissionError:
            pass
        else:
            raise AssertionError("Callback adopted a source after original creator completed")
        cases.append("actual_creator_done_after_narration_failure_cannot_adopt_new_observer_from_taskless_callback")

        for phase, retired_revision in (("prepare",1),("accept",2)):
            active = self.manager.current_active("profile-a")
            await self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id)
            original_method = getattr(origins.SourceJournal,phase)
            calls = []
            async def lose_original_ACK(journal, original_input, current):
                result = await original_method(journal,original_input,current)
                calls.append((original_input,result))
                raise OSError("synthetic_lost_original_"+phase+"_ACK")
            with patch.object(origins.SourceJournal,phase,lose_original_ACK):
                reply = await client.post("/api/djconnect/v1/session/start",headers=headers,
                    json={**identity,"session_start_strategy":"discover"})
                assert reply.status == 201, await reply.json()
            await self.hass.async_block_till_done()
            current = self.manager.current_active("profile-a")
            assert current.session_id not in self.manager._source_origins
            assert len(calls)==1
            original_input, result = calls[0]
            assert result.phase == ("prepared" if phase=="prepare" else "accepted")
            assert (original_input.origin,"retired",retired_revision) in await rows()
            before = await rows()
            duplicate = await client.post("/api/djconnect/v1/session/start",headers=headers,
                json={**identity,"session_start_strategy":"discover"})
            assert duplicate.status == 409 and await rows() == before
            cases.append("lost_real_"+phase+"_ACK_preserves_SQL_truth_original_terminal_no_reissue_and_ordinary_Session")

        active, original = await fresh()
        async def unknown_terminal(journal, original_input):
            raise OSError("synthetic_terminal_storage_unavailable")
        with patch.object(origins.SourceJournal,"retire",unknown_terminal):
            await self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id)
            assert original.retired and original.runtime is None and original.committed is None
            assert await original._terminal_task == ("UNKNOWN",None)
        assert (original.origin,"accepted",1) in await rows()  # Actual failed SQL remains unchanged.
        assert not original.current() and active.session_id not in self.manager._source_origins
        cases.append("failed_terminal_storage_stays_explicit_UNKNOWN_without_replay_or_SQL_success_claim")

        active, original = await fresh()
        wrong_runtime = self.hass.data["djconnect"]["second-owner"]
        observed = original.observer
        observed.integration_runtime = wrong_runtime
        assert not original.current() and original.retired and original.observer is None
        observed.integration_runtime = self.integration
        assert not original.current()
        cases.append("actual_observer_runtime_change_and_ABA_cannot_keep_or_restore_original_source")

        active = self.manager.current_active("profile-a")
        await self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id)
        repository = type(self.manager._persistent_sessions)
        transition = repository.async_transition
        entered, release = asyncio.Event(), asyncio.Event()
        held = []
        async def hold_activation(repository_self, owner, sid, state, **kwargs):
            if state == "ACTIVE" and not held:
                held.append(sid)
                entered.set()
                await release.wait()
            return await transition(repository_self,owner,sid,state,**kwargs)
        with patch.object(repository,"async_transition",hold_activation):
            request = asyncio.create_task(client.post("/api/djconnect/v1/session/start",headers=headers,
                json={**identity,"session_start_strategy":"discover"}))
            try:
                await asyncio.wait_for(entered.wait(),5)
                original = next(v for v in self.manager._source_origin_intents.values() if v.session==held[0])
                assert original.phase == "prepared"
                ending = asyncio.create_task(self.manager.async_end(owner_profile_id="profile-a",session_id=held[0]))
                await asyncio.sleep(0)
                assert original.retired and original.runtime is None and not ending.done()
            finally:
                release.set()
            await asyncio.wait_for(ending,10)
            reply = await asyncio.wait_for(request,10)
            await reply.read()
        await self.hass.async_block_till_done()
        assert (original.origin,"retired",1) in await rows()
        assert held[0] not in self.manager._source_origins
        cases.append("real_end_queued_during_ACTIVE_SQL_await_retires_prelock_and_late_commit_cannot_accept_source")

        active, original = await fresh()
        count = len(await rows())
        with patch.object(origins,"MAX_ROWS",count),patch.object(origins,"MAX_OPERATIONS",3*count):
            await self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id)
            await self.hass.async_block_till_done()
            assert (original.origin,"retired",2) in await rows()
            active = await self.start()
            assert active.session_id not in self.manager._source_origins
            assert len(await rows()) == count
        cases.append("full_actual_source_journal_preserves_original_terminal_and_ordinary_Session_baseline")
        # Cancel the real server request only after its actual prepare commit.
        # Its ordinary SQL Session remains OPENING: no fake rollback/recovery.
        await self.manager.async_end(owner_profile_id="profile-a",session_id=active.session_id)
        prepare = origins.SourceJournal.prepare
        entered, release = asyncio.Event(), asyncio.Event()
        committed = []
        async def hold_committed_prepare(journal, original_input, current):
            result = await prepare(journal,original_input,current)
            committed.append(original_input)
            entered.set()
            await release.wait()
            return result
        with patch.object(origins.SourceJournal,"prepare",hold_committed_prepare):
            request = asyncio.create_task(client.post("/api/djconnect/v1/session/start",headers=headers,
                json={**identity,"session_start_strategy":"discover"}))
            try:
                await asyncio.wait_for(entered.wait(),5)
                original = next(v for v in self.manager._source_origin_intents.values()
                    if v.session==committed[0].session)
                creator = original._creator_ref()
                assert creator is not None and creator is not asyncio.current_task()
                creator.cancel()
                await asyncio.gather(creator,return_exceptions=True)
                assert original.retired and original.runtime is None
            finally:
                release.set()
            await asyncio.gather(request,return_exceptions=True)
        await self.hass.async_block_till_done()
        assert len(committed)==1 and (committed[0].origin,"retired",1) in await rows()
        assert committed[0].session not in self.manager._source_origins
        persisted = await self.manager._persistent_sessions._persistence.async_in_transaction(lambda tx:
            tx.fetchone("SELECT lifecycle_status FROM djconnect_persistent_sessions WHERE session_id=?",
                (committed[0].session,)))
        assert persisted == ("OPENING",)
        cases.append("actual_request_cancellation_after_prepare_commit_preserves_original_SQL_OPENING_and_terminal_no_reissue")
        return {"state":"PASS","cases":cases,"source_origin_DATA_only":True,
            "af201_native_mapping":"NOT_IMPLEMENTED","installed_native_provider":"NOT_RUN",
            "external_boundary":"Synthetic Spotify/CDN and fixture config entries/Profile selection; actual product component setup, committed Store, pair/session HTTP, manager/factory, observer and SQL18"}


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
    hass.config.components.add("http")
    frame.async_setup(hass)
    loader.async_setup(hass)
    assert await async_setup(hass, {})
    storage = profile_storage(hass)
    await storage.async_load()
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
    await async_initialize_persistence(hass)
    clock = VerificationClock()
    from custom_components.djconnect.session_runtime import session_runtime_manager
    manager = session_runtime_manager(hass)
    manager._monotonic_source = clock.monotonic
    provider_session = ClientSession()
    cache_key = aiohttp_client._make_key(True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT)
    hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})[cache_key] = provider_session
    await websocket_api.async_setup(hass, {})
    lab = SourceOriginLab(hass, manager, clock, runtime)
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
        (directory / "source-origin-ha-receipt.json").write_text(json.dumps(result, indent=2)+"\n")
        if os.environ.get("DJC_NARRATIVE_BROWSER") == "1":
            await serve(client, identity, headers)
        await lab.stop()
    await provider_session.close()
    await async_shutdown_persistence(hass)
    await hass.async_stop()
    print("SOURCE_ORIGIN_ISOLATED_HA_PASS", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
