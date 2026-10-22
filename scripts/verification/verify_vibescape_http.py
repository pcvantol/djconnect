"""Actual registered HA visual-only HTTP and SQLite; synthetic source I/O only."""

from __future__ import annotations

import asyncio
import gc
import weakref
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import DJConnectRuntime, playback_observation as observation
    from custom_components.djconnect.domain.music_account import MusicAccountKind
    from custom_components.djconnect.visual_director_catalogue import capability
    from custom_components.djconnect import visual_director_runtime as adapter

    domain = hass.data["djconnect"]
    runtime = domain["owner-entry"]
    storage = domain["djconnect_profile_platform"]
    source_entry = hass.config_entries.async_get_entry("source-entry")
    hass.config_entries.async_update_entry(
        source_entry,
        data={**source_entry.data, "music_backend": "source-spotify", "profile_id": "profile-a"},
    )
    hass.config_entries.async_update_entry(
        runtime.entry,
        data={
            **runtime.entry.data,
            "music_backend": "source-spotify",
            "music_account_id": "source-account",
            "profile_backend_entry_id": "source-entry",
        },
    )
    domain["source-entry"] = DJConnectRuntime(source_entry)
    await storage.async_upsert_music_account(
        "source-account",
        "source-spotify",
        kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic source",
        linked_profile_ids=frozenset({"profile-a"}),
        provider_account_id="synthetic-provider",
    )
    await storage.async_update_profile(
        "profile-a",
        preferences=replace(
            storage.household.profiles["profile-a"].preferences,
            default_backend_id="source-spotify",
            default_music_account_id="source-account",
        ),
    )
    active = manager.current_active("profile-a")
    if active:
        await manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
    source = {
        "backend_id": "source-spotify",
        "music_account_id": "source-account",
        "provider_entry_id": "source-entry",
        "provider_account_id": "synthetic-provider",
    }
    active = await manager.async_start(
        owner_profile_id="profile-a",
        selected_mood="energy",
        music_backend="spotify_direct",
        history_source_context=source,
    )
    observers = observation.PlaybackObservationManager(hass)

    async def no_insight():
        raise AssertionError("Visual request must not call Track Insight")

    observed = observation._SpotifyObservationSession(
        runtime, "profile-a", active.session_id, no_insight
    )
    observers._spotify_sessions["profile-a"] = observed
    domain["playback_observation_manager"] = observers
    result = SimpleNamespace(
        media_identity="spotify:track:" + "A" * 22,
        state="playing",
        is_playing=True,
        title="Synthetic visual recording",
        artist="Synthetic artist",
        target_name="Synthetic output",
        target_id="synthetic-exact-output-a",
        position_ms=1000,
    )
    calls = []
    failure = None

    class Backend:
        def __init__(self, *args):
            pass

        async def async_observe_current_playback(self):
            calls.append("current")
            if failure is not None:
                raise failure
            return result

        async def async_observe_next_item(self, media):
            calls.append("existing_queue")
            return {}

    async def poll():
        with (
            patch.object(observation, "SpotifyBackend", Backend),
            patch.object(manager, "async_process_track_started", AsyncMock(return_value=None)),
        ):
            await observers._async_poll_spotify(observed)

    identity = {
        "schema_version": 1,
        "client_type": "ios",
        "device_id": runtime.entry.data["device_id"],
        "session_id": active.session_id,
        "visit_id": str(uuid.uuid4()),
    }
    prefix = "/api/djconnect/v1/vibescape/"
    receipts = []
    examples = {}

    async def post(kind, data, expected=200, **kwargs):
        answer, status = await request("POST", prefix + kind, data, **kwargs)
        assert status == expected, (kind, status, answer)
        assert answer["schema_version"] == 1
        assert "text" not in answer and "audio_url" not in answer and "applied" not in answer
        receipts.append({"kind": kind, "status": status, "body": answer})
        return answer

    def sql_snapshot():
        database = next(Path(hass.config.config_dir).rglob("*.sqlite3"))
        connection = sqlite3.connect("file:" + str(database) + "?mode=ro", uri=True)
        try:
            return tuple(connection.iterdump())
        finally:
            connection.close()

    from custom_components.djconnect.persistence import persistence_service

    service = persistence_service(hass)
    await hass.async_block_till_done()
    initial_sql, initial_household = sql_snapshot(), storage.household
    with (
        patch.object(
            storage, "async_save", side_effect=AssertionError("Initial Profile write")
        ) as initial_profile,
        patch.object(
            history, "async_append_exchange", side_effect=AssertionError("Initial history write")
        ) as initial_history,
        patch.object(
            service, "async_in_transaction", side_effect=AssertionError("Initial SQL access")
        ) as initial_access,
    ):
        await post("context", identity, 503)
        await hass.async_block_till_done()
        initial_profile.assert_not_awaited()
        initial_history.assert_not_awaited()
        initial_access.assert_not_awaited()
    assert sql_snapshot() == initial_sql and storage.household is initial_household
    await poll()
    context = await post("context", identity)
    examples["context_request"] = identity
    examples["context_response"] = context
    scene = {
        "palette": [0.3, 0.8, 0.6],
        "motion": 0.4,
        "depth": 0.5,
        "roughness": 0.3,
        "deformation": 0.2,
    }

    def turn(c, text, visit=identity, revision=1):
        return {
            **visit,
            "client_turn_id": str(uuid.uuid4()),
            "base_scene_revision": revision,
            "context_lease_id": c["context_lease_id"],
            "observed_occurrence_id": c["observed_occurrence_id"],
            "text": text,
            "active_scene": scene,
            "dynamics_bias": 0.5,
            "scope": "current_track",
        }

    caps_response = await client.get("/api/djconnect/v1/capabilities")
    caps = await caps_response.json()
    assert caps_response.status == 200 and caps["vibescape_visual_director"] == capability()
    assert caps_response.headers["Cache-Control"] == "no-store"
    assert caps_response.headers["Referrer-Policy"] == "no-referrer"
    from custom_components.djconnect import visual_director_catalogue

    next_catalogue = capability()
    next_catalogue["help"]["nl"]["examples"].reverse()
    with patch.object(visual_director_catalogue, "capability", return_value=next_catalogue):
        refreshed_response = await client.get("/api/djconnect/v1/capabilities")
        refreshed = await refreshed_response.json()
        assert refreshed_response.status == 200
        assert refreshed_response.headers["Cache-Control"] == "no-store"
        assert refreshed["vibescape_visual_director"] == next_catalogue
        assert refreshed["vibescape_visual_director"] != caps["vibescape_visual_director"]
    examples["capability"] = caps["vibescape_visual_director"]
    cases = {
        "actual_bootstrap_view_registration_and_capability": "PASS",
        "live_help_GET_no_store_reads_current_server_catalogue_each_time": "PASS",
        "initial_context_requires_actual_stage1_sample": "PASS",
        "initial_unavailable_context_no_SQL_Profile_history_access_after_task_drain": "PASS",
    }

    # Quiesce prior synthetic HA fixture tasks before the measured window.
    await hass.async_block_till_done()
    before = sql_snapshot()
    household = storage.household
    provider_calls_before = list(calls)
    with (
        patch.object(
            storage, "async_save", side_effect=AssertionError("Profile write")
        ) as profile_writes,
        patch.object(
            history, "async_append_exchange", side_effect=AssertionError("history write")
        ) as history_writes,
        patch.object(
            service, "async_in_transaction", side_effect=AssertionError("SQL access")
        ) as sql_access,
    ):
        for locale, help_content in capability()["help"].items():
            visit = {**identity, "visit_id": str(uuid.uuid4())}
            current = await post("context", visit)
            for index, example in enumerate(help_content["examples"]):
                data = turn(current, example["text"], visit, index)
                answer = await post("interpret", data)
                assert answer["status"] == "interpreted"
                assert answer["client_turn_id"] == data["client_turn_id"]
                if locale == "nl" and index == 0:
                    examples["interpret_request"] = data
                    examples["interpret_response"] = answer
            await post("revoke", visit)
        for text in (
            "less fluid",
            "less a bit calm",
            "no faster",
            "more depth 播放音乐",
            "Speel muziek",
            "Meer diepte en zet de lamp aan",
        ):
            await post("interpret", turn(context, text), 422)
        await post("context", identity, 401, authorized=False)
        # Keep spies installed while all HA-owned tasks from the requests drain.
        await hass.async_block_till_done()
        profile_writes.assert_not_awaited()
        history_writes.assert_not_awaited()
        sql_access.assert_not_awaited()
    assert calls == provider_calls_before, "Visual HTTP unexpectedly queried a provider"
    after = sql_snapshot()
    if after != before:
        print(
            "SYNTHETIC_SQL_DIFF",
            sorted(set(before) - set(after)),
            sorted(set(after) - set(before)),
            flush=True,
        )
    assert after == before, "Visual requests changed synthetic SQLite"
    assert storage.household is household, "Visual requests replaced Profile household"
    cases["forty_examples_across_five_locales_interpreted_not_applied"] = "PASS"
    cases["visual_only_reads_leave_SQLite_Profile_history_and_provider_unchanged"] = "PASS"
    cases["unsupported_mixed_script_negated_music_and_HA_intents_rejected"] = "PASS"
    cases["ordinary_pairing_token_enforced"] = "PASS"
    for method in ("GET", "HEAD", "OPTIONS", "PUT", "DELETE", "PATCH", "TRACE"):
        for kind in ("context", "interpret", "revoke"):
            response = await client.request(method, prefix + kind)
            assert response.status == 405 and response.headers["Cache-Control"] == "no-store"
            assert response.headers["Referrer-Policy"] == "no-referrer"
            await response.read()
    cases["all_twenty_one_unsupported_method_routes_private_no_store"] = "PASS"
    examples["transport_errors"] = []
    for raw, content_type, expected in (
        (b" " * 8193, "application/json", 413),
        (b'{"schema_version":1,"schema_version":1}', "application/json", 400),
        (b"\xff", "application/json", 400),
        (b"{}", "text/plain", 415),
    ):
        response = await client.post(
            prefix + "context", data=raw, headers={"Content-Type": content_type}
        )
        assert response.status == expected and response.headers["Cache-Control"] == "no-store"
        error = await response.json()
        assert error["schema_version"] == 1
        examples["transport_errors"].append({"status": response.status, "body": error})
    cases["raw_byte_duplicate_UTF8_content_type_bounds"] = "PASS"
    for failure in (observation.SpotifyBackendError("synthetic"), RuntimeError("synthetic")):
        await poll()
        await post("context", identity, 503)
        assert "Synthetic visual recording" not in repr(vars(adapter.engine(hass)))
    failure = None
    await poll()
    changed = await post("context", identity)
    assert changed["observed_occurrence_id"] != context["observed_occurrence_id"]
    cases["both_provider_error_paths_clear_metadata_then_new_occurrence"] = "PASS"
    old_output = turn(changed, "Meer diepte")
    result.target_id = "synthetic-exact-output-b"
    result.position_ms += 1000
    await poll()
    output_changed = await post("context", identity)
    assert output_changed["observed_occurrence_id"] != changed["observed_occurrence_id"]
    assert "synthetic-exact-output" not in str(output_changed)
    await post("interpret", old_output, 409)
    cases["different_output_ids_with_same_name_fence_original_lease"] = "PASS"
    old = turn(output_changed, "Meer diepte")
    result.media_identity = "spotify:track:" + "B" * 22
    await poll()
    result.media_identity = "spotify:track:" + "A" * 22
    await poll()
    await post("interpret", old, 409)
    cases["actual_stage1_A_B_A_invalidates_original_turn"] = "PASS"
    old_admission = adapter.capture_observer(hass, observed)
    old_projection = weakref.ref(active.broadcast.passive_observation[2])
    await post("revoke", identity)
    await post("context", identity, 410)
    result.media_identity = "spotify:track:" + "C" * 22
    result.title = "Synthetic non-Vibe recording"
    await poll()
    gc.collect()
    assert old_projection() is None, "Visual state retained a prior projection after revoke"
    assert isinstance(old_admission.previous_sample_serial, int)
    assert isinstance(observed.visual_sample_serial, int)
    cases["revoke_then_non_Vibe_poll_releases_old_projection_with_only_contentfree_serials"] = (
        "PASS"
    )
    cases["revoke_tombstone_prevents_late_rearm"] = "PASS"
    adapter.withdraw_all(hass)
    return {
        "qualification": "ACTUAL_HA_REGISTERED_PAIRED_HTTP_STAGE1_SQLITE_VISUAL_ONLY_SYNTHETIC_PROVIDER_IO",
        "cases": cases,
        "examples": examples,
        "visual_receipts": receipts,
        "model_provider_calls": 0,
        "real_microphone_native_GPU_user_acceptance": "NOT_RUN",
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    from verify_session_conversation_history_http import main

    asyncio.run(main(qualification_extension=qualify))
