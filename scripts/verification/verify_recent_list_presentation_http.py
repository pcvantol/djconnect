"""Actual isolated HA/paired HTTP/Store/SQL; recent provider reads are synthetic DATA."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from unittest.mock import patch


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import DJConnectRuntime, ask_dj
    from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
    from custom_components.djconnect.domain.music_account import MusicAccountKind

    key = "recent_history_presentation"
    domain = hass.data["djconnect"]
    runtime = domain["owner-entry"]
    storage = domain["djconnect_profile_platform"]
    source_entry = hass.config_entries.async_get_entry("source-entry")
    hass.config_entries.async_update_entry(source_entry,
        data={**source_entry.data, "music_backend": "source-spotify", "profile_id": "profile-a"})
    hass.config_entries.async_update_entry(runtime.entry, data={**runtime.entry.data,
        "music_backend": "source-spotify", "music_account_id": "source-account",
        "profile_backend_entry_id": "source-entry"})
    domain["source-entry"] = DJConnectRuntime(source_entry)
    await storage.async_upsert_music_account("source-account", "source-spotify",
        kind=MusicAccountKind.PERSONAL, display_name="Synthetic original account",
        linked_profile_ids=frozenset({"profile-a"}), provider_account_id="original-provider")
    await storage.async_update_profile("profile-a", preferences=replace(
        storage.household.profiles["profile-a"].preferences,
        default_backend_id="source-spotify", default_music_account_id="source-account"))
    active = manager.current_active("profile-a")
    if active:
        await manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
    session = await manager.async_start(owner_profile_id="profile-a", music_backend="spotify_direct", locale="nl",
        history_source_context={"backend_id": "source-spotify", "music_account_id": "source-account",
                                "provider_entry_id": "source-entry", "provider_account_id": "original-provider"})
    stamp = datetime.now(UTC) - timedelta(minutes=5)
    calls = []
    async def backend(hass, runtime, command, *args, **kwargs):
        calls.append(command)
        if command == "status":
            return {"success": True, "playback": {}}
        assert command == "recently_played", command
        return {"success": True, "tracks": [{"track_name": "Synthetic original recording",
            "artist": "Synthetic performer", "uri": "spotify:track:"+"A"*22,
            "played_at": (stamp-timedelta(minutes=i)).isoformat()} for i in range(12)]}
    with patch.object(ask_dj, "run_music_command", backend):
        direct, status = await request("POST", "/api/djconnect/v1/ask_dj/message", {
            "client_message_id": "recent-list-original", "text": "Welke nummers heb ik afgelopen uur afgespeeld?",
            "language": "nl", "audio_response": "never", "conversation_context": {"session_id": session.session_id}})
    assert status == 200, direct
    display = direct[key]
    assert display == direct["assistant_message"][key]
    assert len(display["items"]) == 10 and display["omitted_count"] == 2
    assert len({v["item_id"] for v in display["items"]}) == 10
    assert "- Synthetic" not in display["caption"]
    assert "Synthetic original recording" in direct["text"] and not direct["playback_actions"]
    assert not any(k in json.dumps(display) for k in ('"uri"', 'image_url', 'playback_actions', 'audio_url'))
    assert "provider_display_source" not in json.dumps(direct)
    identifier = direct["assistant_message"]["id"]
    saved = await history.async_saved_exchange("profile:profile-a", "recent-list-original")
    assert saved["assistant_message"][key] == display
    assert not saved["assistant_message"]["images"] and not saved["assistant_message"]["playback_actions"]
    history.dialogue.clock = lambda: 10**12  # Original operational window is over; no wall/source renewal.
    reread = AskDJHistoryManager(store=history._store)
    await reread.async_load()
    runtime.ask_dj_history = reread
    domain["ask_dj_history_manager"] = reread
    await manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
    body, status = await request("GET", "/api/djconnect/v1/ask_dj/history", {})
    assert status == 200, body
    retained = next(v for v in body["messages"] if v["id"] == identifier)
    assert retained[key] == display and not retained["playback_actions"]
    path = "/api/djconnect/v1/session/history/" + session.session_id
    page, status = await request("GET", path, {"session_id": session.session_id, "history_contract_version": 2})
    assert status == 200, page
    original_entry = next(e for e in page["entries"] if e.get("origin_message_id") == identifier)
    assert original_entry[key] == display and "playback_actions" not in original_entry
    assert "provider_display_source" not in json.dumps(body)
    # Age is a closed semantic read. Core can ask which meaning is intended
    # without paying for a biography draft/review or guessing a birth date.
    from custom_components.djconnect import pipeline
    from custom_components.djconnect.ask_dj import public_research
    age_calls = []
    async def age_plan(hass, data, **kwargs):
        projection = json.loads(data["text"].split("\nData:\n", 1)[1])
        assert "available" in projection
        assert projection["question"] == "Hoe oud is Example Band?"
        age_calls.append("declared_synthetic_interpretation")
        return {"response": {"speech": {"plain": {"speech": json.dumps({
            "read": "research", "reference": "named", "exclude_current": False,
            "subject": "Example Band", "angle": "age"})}}}}
    async def age_source(subject, question, language, guard, **kwargs):
        assert subject == "Example Band"
        await guard()
        source = public_research._source("Wikipedia", "Example Band",
            "https://en.wikipedia.org/wiki/Example_Band", "Example Band is a rock band.", "en", entity_id="Q1")
        return [source], {"state": "fetched", "requests": 0, "source_boundary": "synthetic_DATA"}
    with patch.object(pipeline, "_call_conversation_process_transport", age_plan), patch.object(
            public_research, "research", age_source):
        age, status = await request("POST", "/api/djconnect/v1/ask_dj/message", {
            "client_message_id": "age-group-clarification", "text": "Hoe oud is Example Band?",
            "language": "nl", "audio_response": "never"})
    assert status == 200 and age["clarification_required"] is True, age
    assert age["knowledge_basis"] == "public_subject_clarification_v1"
    assert age["text"] == "Bedoel je hoe lang de band Example Band bestaat, of de leeftijd van een specifieke muzikant?"
    assert not age.get("playback_actions") and "model_processing_basis" not in age
    assert age["conversation"]["metrics"]["agent_calls"] == len(age_calls) == 1
    source_data = dict(source_entry.data)
    source_data.pop("spotify_refresh_token", None)
    hass.config_entries.async_update_entry(source_entry, data=source_data)
    withdrawn, status = await request("GET", "/api/djconnect/v1/ask_dj/history", {})
    assert status == 200, withdrawn
    closed = next(v for v in withdrawn["messages"] if v["id"] == identifier)
    assert not closed.get(key) and not closed.get("items") and not closed["text"]
    page, status = await request("GET", path, {"session_id": session.session_id, "history_contract_version": 2})
    assert status == 200, page
    closed_entry = next(e for e in page["entries"] if e["entry_id"] == original_entry["entry_id"])
    assert key not in closed_entry and closed_entry["state"] == "source_withdrawn"
    exported, status = await request("POST", "/api/djconnect/v1/ask_dj/history/export", {"conversation_scope": "profile"})
    assert status == 200, exported
    assert not any(m.get(key) for m in exported["messages"])
    assert calls and all(c in {"status", "recently_played"} for c in calls)
    return {"qualification": "ACTUAL_ISOLATED_HA_PAIRED_HTTP_STORE_SQL_SYNTHETIC_PROVIDER_READS",
        "cases": {name: "PASS" for name in (
            "original_direct_assistant_value_matches", "twelve_original_occurrences_ten_cards_two_omitted",
            "closed_metadata_no_media_tokens_or_actions", "full_legacy_text_and_separate_explicit_caption",
            "Store_reload_operational_expiry_and_Session_end_preserve_original_cards",
            "paired_history_and_timeline_match_original", "source_withdrawal_redacts_http_and_timeline",
            "export_does_not_resurrect_withdrawn_cards", "age_question_closed_group_read_one_interpretation_no_invented_age")},
        "example": display, "effect_count": 0, "model_provider_calls": 0,
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "installed": "NOT_RUN", "native": "NOT_RUN", "audible": "NOT_RUN"}


if __name__ == "__main__":
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
