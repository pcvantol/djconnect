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
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/verification"))
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.persistence import (  # noqa: E402
    async_initialize_persistence,
    async_shutdown_persistence,
)
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402
from custom_components.djconnect.paired_live_contract import PAIRED_LIVE_PATH  # noqa: E402


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
        cors_origins=["https://localhost:18204"]
        if os.environ.get("DJC_MOOD_BROWSER") == "1"
        else [],
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
    second_identity = {"device_id": "djconnect-macos-ABCDEF123457", "client_type": "macos"}
    second_slot = entry(
        "second-owner",
        {
            **second_identity,
            "pair_code": "234567",
            "music_backend": "later_manual",
            "profile_id": "profile-a",
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
    hass.data["djconnect"] = {
        "owner-entry": runtime,
        "second-owner": second_runtime,
        "runtime": runtime,
    }
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
    register_http_views(hass)
    await websocket_api.async_setup(hass, {})
    browser_serve = None
    if os.environ.get("DJC_MOOD_BROWSER") == "1":
        from active_session_mood_browser_lab import register

        browser_serve = register(hass, manager, clock)
    initial_users = await hass.auth.async_get_users()
    initial_credentials = sum(len(user.refresh_tokens) for user in initial_users)
    receipts = []
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "custom_components/djconnect").rglob("*"))
        if path.is_file() and path.suffix in {".py", ".json", ".js", ".html", ".css"}
    }
    async with TestClient(TestServer(hass.http.app)) as client:
        tokens = []
        for ident, code, rt in [
            (identity, "123456", runtime),
            (second_identity, "234567", second_runtime),
        ]:
            # Select only the synthetic configured slot; real pairing mints its token.
            hass.data["djconnect"]["runtime"] = rt
            response = await client.post(
                "/api/djconnect/v1/pair", json={**ident, "pair_code": code}
            )
            paired = await response.json()
            assert response.status == 200 and paired["success"], {
                "status": response.status,
                "error": paired.get("error"),
                "message": paired.get("message"),
            }
            assert rt.entry.data["device_token"] == paired["device_token"]
            tokens.append(paired["device_token"])
        await store.async_save(
            {"entries": [slot.as_storage_fragment, second_slot.as_storage_fragment]}
        )
        stored = await ConfigEntryStore(hass).async_load()
        assert [e["data"]["device_token"] for e in stored["entries"]] == tokens
        receipts.append(
            {
                "stage": "two_ordinary_paired_clients",
                "tokens_minted_and_persisted": True,
                "ha_user_credentials_issued": 0,
            }
        )
        headers = {
            "Authorization": "Bearer " + tokens[0],
            "X-DJConnect-Device-ID": identity["device_id"],
        }
        second_headers = {
            "Authorization": "Bearer " + tokens[1],
            "X-DJConnect-Device-ID": second_identity["device_id"],
        }
        caps = await (await client.get("/api/djconnect/v1/capabilities")).json()
        assert (
            caps["capabilities"]["active_session_mood"]
            and caps["contract_versions"]["active_session_mood"] == 1
        )
        assert caps["active_session_mood"]["moods"] == ["chill", "groove", "energy", "party"]
        receipts.append(
            {
                "stage": "versioned_capability_catalogue",
                "contract_version": 1,
                "path": caps["active_session_mood"]["path"],
            }
        )
        clock.advance(1)
        session = await manager.async_start(
            owner_profile_id="profile-a",
            selected_mood="groove",
            locale="nl",
            elapsed_time_source=clock.monotonic,
        )
        sid = session.session_id

        async def insight():
            return {
                "track": {
                    "title": "Synthetic music",
                    "artist": "Synthetic artist",
                    "producer": "Synthetic producer",
                },
                "analysis": {
                    "summary": "Synthetic bounded context.",
                    "full_text": "Synthetic source-shaped musical context.",
                },
            }

        # Explicit synthetic music input enters the actual production orchestration.
        prior = await manager.async_process_track_started(
            owner_profile_id="profile-a", session_id=sid, insight_provider=insight
        )
        assert prior is not None
        session = await manager.async_get_active("profile-a")
        frozen = json.dumps(
            [m.as_dict() for m in session.broadcast.state.dj_moments], sort_keys=True
        )
        frozen_presentations = json.dumps(
            [p.as_dict() for p in session.broadcast.state.presentations], sort_keys=True
        )
        stable = (
            session.session_id,
            session.started_at,
            session.initial_session_mood,
            session.dj_persona,
            session.session_start_strategy,
            session.broadcast.state.playback.as_dict(),
        )
        ws = await client.ws_connect(PAIRED_LIVE_PATH)
        assert (await ws.receive_json())["type"] == "auth_required"
        await ws.send_json(
            {"type": "auth", "protocol_version": 1, **identity, "device_token": tokens[0]}
        )
        assert (await ws.receive_json())["type"] == "auth_ok"
        await ws.send_json(
            {"id": 1, "type": "djconnect/session/broadcast/subscribe", "session_id": sid}
        )
        live = await ws.receive_json()
        assert live["success"] and live["result"]["snapshot"]["session"]["mood_revision"] == 0
        cursor = live["result"]["recovery_cursor"]

        def payload(value, revision, ident=identity):
            return {
                **ident,
                "contract_version": 1,
                "session_id": sid,
                "selected_mood": value,
                "expected_mood_revision": revision,
            }

        async def post(value, revision, ident=identity, auth_headers=None):
            response = await client.post(
                "/api/djconnect/v1/session/mood",
                headers=auth_headers or headers,
                json=payload(value, revision, ident),
            )
            result = await response.json()
            assert response.headers.get("Cache-Control") == "no-store"
            return response.status, result

        status, result = await post("energy", 0)
        assert status == 200 and result["mood_revision"] == 1 and result["changed"]
        event = await ws.receive_json()
        assert event["data"]["event_type"] == "mood_changed"
        assert (
            event["data"]["payload"]["session"]["selected_mood"] == "energy"
            and event["data"]["payload"]["session"]["mood_revision"] == 1
        )
        current = await manager.async_get_active("profile-a")
        assert stable == (
            current.session_id,
            current.started_at,
            current.initial_session_mood,
            current.dj_persona,
            current.session_start_strategy,
            current.broadcast.state.playback.as_dict(),
        )
        assert frozen == json.dumps(
            [m.as_dict() for m in current.broadcast.state.dj_moments], sort_keys=True
        )
        assert frozen_presentations == json.dumps(
            [p.as_dict() for p in current.broadcast.state.presentations], sort_keys=True
        )
        receipts.append(
            {
                "stage": "ordinary_owner_mood_to_broadcast",
                "status": 200,
                "selected_mood": "energy",
                "mood_revision": 1,
                "session_start_music_and_immutable_moments_unchanged": True,
            }
        )
        before = current.broadcast.delivery_sequence
        status, result = await post("energy", 1)
        assert status == 200 and not result["changed"] and result["mood_revision"] == 1
        assert current.broadcast.delivery_sequence == before
        receipts.append({"stage": "same_value_noop", "revision_and_delivery_unchanged": True})
        status, result = await post("party", 0)
        assert (
            status == 409
            and result["error"] == "mood_revision_conflict"
            and result["current"]["mood_revision"] == 1
        )
        results = await asyncio.gather(
            post("party", 1), post("chill", 1, second_identity, second_headers)
        )
        assert sorted(s for s, r in results) == [200, 409]
        winner = next(r for s, r in results if s == 200)
        assert winner["mood_revision"] == 2
        event = await ws.receive_json()
        assert event["data"]["payload"]["session"]["mood_revision"] == 2
        receipts.append(
            {"stage": "two_clients_cas", "one_accepted_one_conflict": True, "mood_revision": 2}
        )
        # Set an energetic existing mood at the latest revision; no forced Moment.
        current = await manager.async_get_active("profile-a")
        count = len(current.broadcast.state.dj_moments)
        status, result = await post("party", 2)
        assert status == 200
        rev = result["mood_revision"]
        assert (
            len((await manager.async_get_active("profile-a")).broadcast.state.dj_moments) == count
        )
        if result["changed"]:
            await ws.receive_json()
        for bad in [True, 42, 1.5, None, "ENERGY", "energy ", "focus", [], {}]:
            status, result = await post(bad, rev)
            assert status == 400 and result["error"] == "invalid_selected_mood"
        for bad in [True, 1.0, -1, "0", None]:
            status, result = await post("energy", bad)
            assert status == 400 and result["error"] == "invalid_mood_revision"
        for auth_headers in [
            {"Authorization": "Bearer wrong"},
            {"Authorization": tokens[0]},
            {"Authorization": "Bearer " + current.broadcast.broadcast_token},
        ]:
            status, result = await post("energy", rev, auth_headers=auth_headers)
            assert status == 401
        assert (await manager.async_get_active("profile-a")).mood_revision == rev
        receipts.append(
            {
                "stage": "invalid_schema_and_readonly_receiver_refused",
                "no_mood_or_event_mutation": True,
            }
        )
        clock.advance(90)
        future = await manager.async_process_track_started(
            owner_profile_id="profile-a", session_id=sid, insight_provider=insight
        )
        assert future is not None and future.presentation_intent.source_session_mood == "party"
        receipts.append(
            {
                "stage": "future_silence_preserved",
                "moment_type": future.moment_type.value,
                "source_session_mood": "party",
                "same_session": future.session_id == sid,
            }
        )
        from custom_components.djconnect.session_facts import catalog_facts

        # Source-shaped synthetic catalog input, through actual eligibility/planning.
        catalog = {
            "uri": "spotify:track:" + "A" * 22,
            "title": "Synthetic recording",
            "artist": "Synthetic artist",
            "album_name": "Synthetic edition",
            "album_uri": "spotify:album:" + "B" * 22,
            "release_date": "2001-03-04",
            "release_date_precision": "day",
        }
        await manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=sid,
            state="playing",
            media_identity=catalog["uri"],
            title=catalog["title"],
            artist=catalog["artist"],
            album=catalog["album_name"],
            duration_ms=300000,
            position_ms=0,
        )

        async def qualified_insight():
            return {"_qualified_facts": tuple(catalog_facts(catalog))}

        fact_moment = await manager.async_process_track_started(
            owner_profile_id="profile-a",
            session_id=sid,
            media_identity=catalog["uri"],
            insight_provider=qualified_insight,
            require_current_playback=True,
            allow_initial_facts=True,
        )
        assert fact_moment is not None and fact_moment.moment_type.value == "album"
        assert fact_moment.presentation_intent.source_session_mood == "party"
        assert (
            dict(fact_moment.source_attribution)["url"]
            == "https://open.spotify.com/album/" + "B" * 22
        )
        receipts.append(
            {
                "stage": "qualified_future_moment_chain",
                "moment_type": "album",
                "source_session_mood": "party",
                "facts_and_attribution_preserved": True,
            }
        )
        await ws.close()
        ws = await client.ws_connect(PAIRED_LIVE_PATH)
        await ws.receive_json()
        await ws.send_json(
            {"type": "auth", "protocol_version": 1, **identity, "device_token": tokens[0]}
        )
        assert (await ws.receive_json())["type"] == "auth_ok"
        await ws.send_json(
            {
                "id": 1,
                "type": "djconnect/session/broadcast/recover",
                "session_id": sid,
                "recovery_cursor": cursor,
            }
        )
        recovered = await ws.receive_json()
        assert recovered["success"]
        if recovered["result"]["recovery"] == "replayed":
            mood_events = [
                e for e in recovered["result"]["events"] if e["event_type"] == "mood_changed"
            ]
            assert mood_events[-1]["payload"]["session"]["mood_revision"] == rev
        # Both existing recovery modes converge with the actual owner HTTP snapshot.
        response = await client.get(
            "/api/djconnect/v1/session/broadcast/" + sid,
            headers=headers,
            params=identity,
        )
        assert response.status == 200
        snapshot = (await response.json())["snapshot"]
        assert (
            snapshot["session"]["selected_mood"] == "party"
            and snapshot["session"]["mood_revision"] == rev
        )
        receipts.append(
            {"stage": "ordinary_reconnect_recovery", "selected_mood": "party", "mood_revision": rev}
        )
        await ws.close()
        response = await client.get(
            "/api/djconnect/v1/session/active", headers=headers, params=identity
        )
        active_reply = await response.json()
        assert response.status == 200 and active_reply["session"]["mood_revision"] == rev
        # Fault wrappers delay actual resolver output; they never replace auth/results.
        from custom_components.djconnect import api_handlers
        from custom_components.djconnect.domain.profile.models import ProfileState
        from unittest.mock import patch

        original_resolve = api_handlers.async_resolve_device_bound_request_context

        async def resolver_race(label, change, restore):
            reached, release = asyncio.Event(), asyncio.Event()

            async def delayed(*args, **kwargs):
                context = await original_resolve(*args, **kwargs)
                if kwargs.get("request_source") == "active_session_mood":
                    reached.set()
                    await release.wait()
                return context

            active = await manager.async_get_active("profile-a")
            before = (
                active.selected_mood,
                active.mood_revision,
                active.broadcast.delivery_sequence,
                tuple(m.as_dict() for m in active.broadcast.state.dj_moments),
            )
            with patch.object(api_handlers, "async_resolve_device_bound_request_context", delayed):
                pending = asyncio.create_task(post("energy", active.mood_revision))
                await asyncio.wait_for(reached.wait(), 5)
                await change()
                release.set()
                status, rejected = await asyncio.wait_for(pending, 5)
            assert status == 401 and rejected["error"] == "unauthorized", label
            current = await manager.async_get_active("profile-a")
            assert before == (
                current.selected_mood,
                current.mood_revision,
                current.broadcast.delivery_sequence,
                tuple(m.as_dict() for m in current.broadcast.state.dj_moments),
            ), label
            await restore()
            receipts.append(
                {
                    "stage": "owner_authority_withdrawal_during_resolver",
                    "condition": label,
                    "status": 401,
                    "no_mood_event_or_existing_moment_mutation": True,
                }
            )

        from dataclasses import replace

        async def set_profile_state(state):
            # Declared synthetic management state, persisted through the actual Store.
            household = storage.household
            await storage.async_save(
                replace(
                    household,
                    profiles={
                        **household.profiles,
                        "profile-a": replace(household.profiles["profile-a"], state=state),
                    },
                )
            )

        async def disable_profile():
            await set_profile_state(ProfileState.DISABLED)

        async def activate_profile():
            await set_profile_state(ProfileState.ACTIVE)

        await resolver_race("disabled_profile", disable_profile, activate_profile)

        async def archive_profile():
            await set_profile_state(ProfileState.ARCHIVED)

        await resolver_race("archived_profile", archive_profile, activate_profile)

        async def change_profile():
            await storage.async_upsert_device(
                identity["device_id"], "ios", linked_profile_id="profile-other"
            )

        async def restore_profile():
            await storage.async_upsert_device(
                identity["device_id"], "ios", linked_profile_id="profile-a"
            )

        await resolver_race("device_profile_switch", change_profile, restore_profile)

        async def withdraw_runtime():
            hass.data["djconnect"].pop("owner-entry")

        async def restore_runtime():
            hass.data["djconnect"]["owner-entry"] = runtime

        await resolver_race("runtime_unregistered", withdraw_runtime, restore_runtime)

        async def unload_entry():
            slot._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)

        async def load_entry():
            slot._async_set_state(hass, ConfigEntryState.LOADED, None)

        await resolver_race("entry_unloaded", unload_entry, load_entry)

        async def rotate_pairing():
            # Owned management-state fixture: withdraw the persisted and runtime
            # bearer while real owner resolution is pending. Ordinary pairing is
            # idempotent; this does not claim to test an options-flow rotation.
            replacement = secrets.token_urlsafe(32)
            runtime.device_token = replacement
            hass.config_entries.async_update_entry(
                slot, data={**slot.data, "device_token": replacement}
            )

        async def adopt_new_pairing():
            tokens[0] = runtime.device_token
            headers["Authorization"] = "Bearer " + tokens[0]

        await resolver_race("stored_pairing_token_withdrawal", rotate_pairing, adopt_new_pairing)
        # Separately hold the final Runtime mutation lock after real owner resolution.

        original_update = manager.async_update_mood
        reached, release = asyncio.Event(), asyncio.Event()

        async def wait_at_commit(**kwargs):
            reached.set()
            await release.wait()
            return await original_update(**kwargs)

        active = await manager.async_get_active("profile-a")
        with patch.object(manager, "async_update_mood", wait_at_commit):
            pending = asyncio.create_task(post("energy", active.mood_revision))
            await asyncio.wait_for(reached.wait(), 5)
            await manager._lock.acquire()
            release.set()
            await asyncio.sleep(0)
            await disable_profile()
            manager._lock.release()
            status, rejected = await asyncio.wait_for(pending, 5)
        assert status == 401 and rejected["error"] == "unauthorized"
        assert (await manager.async_get_active("profile-a")).mood_revision == active.mood_revision
        await activate_profile()
        receipts.append(
            {
                "stage": "profile_disabled_during_final_runtime_lock_wait",
                "status": 401,
                "no_mutation": True,
            }
        )
        # A real committed response is delayed at the HTTP boundary. Later writes
        # still proceed; reconnect/snapshot is authoritative after response loss.
        from custom_components.djconnect import session_mood

        original_handle = session_mood.async_handle_mood
        committed, release_reply = asyncio.Event(), asyncio.Event()
        old_revision = (await manager.async_get_active("profile-a")).mood_revision

        async def delayed_reply(*args, **kwargs):
            reply = await original_handle(*args, **kwargs)
            if reply[1] == 200 and reply[0]["mood_revision"] == old_revision + 1:
                committed.set()
                await release_reply.wait()
            return reply

        with patch.object(session_mood, "async_handle_mood", delayed_reply):
            pending = asyncio.create_task(post("energy", old_revision))
            await asyncio.wait_for(committed.wait(), 5)
            newer_status, newer = await post("chill", old_revision + 1)
            assert newer_status == 200 and newer["mood_revision"] == old_revision + 2
            release_reply.set()
            older_status, older = await asyncio.wait_for(pending, 5)
        assert older_status == 200 and older["mood_revision"] < newer["mood_revision"]
        snapshot = await (
            await client.get("/api/djconnect/v1/session/active", headers=headers, params=identity)
        ).json()
        assert snapshot["session"]["selected_mood"] == "chill"
        assert snapshot["session"]["mood_revision"] == newer["mood_revision"]
        stale_status, stale = await post("energy", old_revision)
        assert stale_status == 409 and stale["current"]["mood_revision"] == newer["mood_revision"]
        receipts.append(
            {
                "stage": "late_response_and_lost_reply_readback",
                "older_response_cannot_reverse_server_state": True,
                "snapshot_highest_revision": newer["mood_revision"],
                "blind_retry_status": 409,
            }
        )

        # Strict schema and absent/mismatched owner credentials do not mutate.
        before = (await manager.async_get_active("profile-a")).broadcast.delivery_sequence
        for request_headers in [{}, {**headers, "X-DJConnect-Device-ID": "other-device"}]:
            response = await client.post(
                "/api/djconnect/v1/session/mood",
                headers=request_headers,
                json=payload("party", newer["mood_revision"]),
            )
            assert response.status == 401
        for change in [
            {"contract_version": True},
            {"contract_version": 2},
            {"profile_id": "profile-other"},
        ]:
            response = await client.post(
                "/api/djconnect/v1/session/mood",
                headers=headers,
                json={**payload("party", newer["mood_revision"]), **change},
            )
            assert response.status == 400
        wrong = await client.post(
            "/api/djconnect/v1/session/mood",
            headers=headers,
            json={**payload("party", newer["mood_revision"]), "session_id": "other-session"},
        )
        assert wrong.status == 404
        assert before == (await manager.async_get_active("profile-a")).broadcast.delivery_sequence
        receipts.append(
            {"stage": "anonymous_wrong_identity_schema_and_session", "no_mutation": True}
        )

        # End the exact Session during real owner resolution, then start another.
        reached, release = asyncio.Event(), asyncio.Event()

        async def delayed_end(*args, **kwargs):
            context = await original_resolve(*args, **kwargs)
            if kwargs.get("request_source") == "active_session_mood":
                reached.set()
                await release.wait()
            return context

        with patch.object(api_handlers, "async_resolve_device_bound_request_context", delayed_end):
            pending = asyncio.create_task(post("party", newer["mood_revision"]))
            await asyncio.wait_for(reached.wait(), 5)
            ended = await manager.async_end(owner_profile_id="profile-a", session_id=sid)
            replacement = await manager.async_start(
                owner_profile_id="profile-a", selected_mood="groove"
            )
            release.set()
            ended_status, ended_reply = await asyncio.wait_for(pending, 5)
        assert ended_status == 404 and ended_reply["error"] == "active_session_not_found"
        assert ended.selected_mood == "chill" and ended.mood_revision == newer["mood_revision"]
        current = await manager.async_get_active("profile-a")
        assert current.session_id == replacement.session_id != sid
        assert current.selected_mood == "groove" and current.mood_revision == 0
        receipts.append(
            {
                "stage": "session_end_during_request_and_replacement",
                "status": 404,
                "ended_session_not_revived": True,
                "new_session_unchanged": True,
            }
        )
        users = await hass.auth.async_get_users()
        assert sum(len(user.refresh_tokens) for user in users) == initial_credentials
        if browser_serve is not None:
            await browser_serve(client, identity, headers)
    await async_shutdown_persistence(hass)
    await hass.async_stop()
    result = {
        "assignment": "DJC-CORE-ACTIVE-SESSION-MOOD-V1-20261011",
        "qualification": "EARLY_TRANSPORT_AND_BASIC_CASES",
        "installed_acceptance": "NOT_CLAIMED",
        "receipts": receipts,
        "source_hashes": source_hashes,
    }
    (directory / "early-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"qualification": result["qualification"], "receipts": receipts}))


asyncio.run(main())
