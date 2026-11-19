"""Actual isolated HA/paired HTTP; declared synthetic research/photo/narration only."""

import asyncio
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]


def accepted_text(fact, *, locale="nl", persona="home_dj", mood="energy"):
    from PIL import Image
    from custom_components.djconnect import live_impression as li

    pixels = io.BytesIO()
    Image.new("RGB", (1024, 768), (30, 65, 120)).save(pixels, format="PNG")
    pixels = pixels.getvalue()
    revision = hashlib.sha256(pixels).hexdigest()
    photo = {
        "photo_id": "photo-fixture",
        "revision": revision,
        "caption": "Nora Vale 1 performed at Fixture Hall, Fixture City, 2020-06-02.",
        "alt_text": {language: "Nora Vale 1 — Fixture Hall" for language in li.LANGUAGES},
        "width": 1024,
        "height": 768,
        "source_url": "https://commons.wikimedia.org/wiki/File:Nora_Vale_concert_fixture.png",
        "author": "Fixture Photographer",
        "credit": "Fixture Photographer · CC BY-SA 4.0",
        "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    }
    payload = {
        "schema_version": 1,
        "event": {
            "event_id": "event-fixture",
            "artist": "Nora Vale 1",
            "date": "2020-06-02",
            "date_precision": "day",
            "venue": "Fixture Hall",
            "city": "Fixture City",
            "relationship": "same_artist",
        },
        "photos": [photo],
    }
    title = "Een avond in Fixture Hall"
    lead = "Nora Vale 1 speelde in Fixture Hall. De foto bewaart die avond."
    text = (
        lead
        + " In Fixture City stond de artiest op 2 juni 2020 op het podium. Dit opgeslagen verhaal en deze foto gaan over dat optreden, ook wanneer er een ander nummer speelt."
    )
    sources = [
        {
            "provider": "Wikimedia Commons",
            "title": "Original concert fixture",
            "url": photo["source_url"],
            "license": photo["license"],
        }
    ]
    reference = {
        "photo_id": photo["photo_id"],
        "revision": revision,
        "source_url": photo["source_url"],
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/fixture.png",
        "original_url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/fixture.png",
        "license": photo["license"],
        "license_url": photo["license_url"],
        "commons_revision": "a" * 40,
    }
    values = (
        fact,
        title,
        lead,
        text,
        li._json(payload),
        li._json(sources),
        li._json(reference),
        locale,
        persona,
        mood,
    )
    proof = li.Acceptance(*values, li._seal(*values))
    return li.LiveImpressionText(proof, pixels, "image/png")


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import api_handlers, session_facts
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    from custom_components.djconnect.ask_dj.service import _live_reference
    from custom_components.djconnect.persistence import persistence_service

    async def no_external(*args, **kwargs):
        return None

    active = manager.current_active("profile-a")
    if active:
        await manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
    from custom_components.djconnect.domain.profile.dj_settings import DJSettings
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    import uuid

    manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
    before, code = await request(
        "GET", "/api/djconnect/v1/profile/settings", {"contract_version": 3}
    )
    assert code == 200, before
    chosen, code = await request(
        "PATCH",
        "/api/djconnect/v1/profile/settings",
        {
            "contract_version": 3,
            "binding": before["binding"],
            "operation_id": str(uuid.uuid7()),
            "patch": DJSettings().as_dict(),
            "expected_defaults_revision": before["snapshot"]["defaults_revision"],
            "expected_session": None,
        },
    )
    assert code == 200, chosen
    with (
        patch.object(api_handlers, "_async_generate_initial_session_moment", no_external),
        patch.object(PlaybackObservationManager, "async_start_spotify", no_external),
    ):
        start, status = await request(
            "POST", "/api/djconnect/v1/session/start", {"mood": "energy", "locale": "nl"}
        )
    assert status == 201, start
    active = manager.current_active("profile-a")
    sid = active.session_id
    catalog = {
        "uri": "spotify:track:" + "1".zfill(22),
        "title": "Amber Lines 1",
        "artist": "Nora Vale 1",
        "album_name": "Paper Windows 1",
    }
    fact = session_facts.artist_facts(
        catalog,
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "name": "Nora Vale 1",
            "type": "Group",
            "life-span": {"begin": "1960-03-04"},
        },
    )[0]
    fact = replace(fact, public_artist_qid="Q1")
    await manager.async_update_playback_projection(
        owner_profile_id="profile-a",
        session_id=sid,
        state="playing",
        media_identity=catalog["uri"],
        title=catalog["title"],
        artist=catalog["artist"],
        duration_ms=300000,
        position_ms=0,
    )
    await manager.async_update_allowed_capability_intents(
        owner_profile_id="profile-a",
        session_id=sid,
        allowed_capability_intents=frozenset({"artist_story"}),
    )
    active = manager.current_active("profile-a")
    calls = []

    async def provider(brief, guard):
        guard()
        calls.append("declared synthetic research/narration")
        return accepted_text(
            brief.fact, locale=brief.locale, persona=brief.persona, mood=brief.mood
        )

    manager.connect_narration("profile-a", sid, provider, lambda: None)

    async def insight():
        return {"_qualified_facts": (fact,)}

    moment = await manager.async_process_track_started(
        owner_profile_id="profile-a",
        session_id=sid,
        media_identity=catalog["uri"],
        insight_provider=insight,
        require_current_playback=True,
        allow_initial_facts=True,
    )
    assert moment is not None, "ordinary runtime did not publish Live-impressie"
    owner, status = await request("GET", "/api/djconnect/v1/session/active")
    assert status == 200
    assert moment.moment_id in json.dumps(owner)
    photo = json.loads(moment.live_impression.payload_json)["photos"][0]
    prepared, status = await request(
        "POST",
        "/api/djconnect/v1/session/media/prepare",
        {
            "contract_version": 3,
            "session_id": sid,
            "targets": [{"moment_id": moment.moment_id, "photo_id": photo["photo_id"]}],
        },
    )
    assert status == 200, prepared
    media = prepared["session_media"][0]
    assert media["artwork"]["state"] == "ready", media
    import inspect

    scope = inspect.getclosurevars(request).nonlocals
    original_headers = scope["headers"]
    response = await client.get(
        media["artwork"]["url"], headers=original_headers, params=scope["identity"]
    )
    assert response.status == 200, (response.status, await response.text())
    assert hashlib.sha256(await response.read()).hexdigest() == photo["revision"]
    page, status = await request(
        "GET",
        "/api/djconnect/v1/session/history/" + sid,
        {"window": "tail", "history_contract_version": 2},
    )
    assert status == 200, (status, page)
    entries = [e for e in page["entries"] if e.get("moment_id") == moment.moment_id]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["live_impression"] == json.loads(moment.live_impression.payload_json)
    speech, status = await request(
        "POST",
        "/api/djconnect/v1/speech/prepare",
        {
            "contract_version": 3,
            "intent": "manual",
            "target": "local",
            "processor": "local_on_device",
            "reference": {"session_id": sid, "moment_id": moment.moment_id},
        },
    )
    assert status == 200, speech
    assert speech["session_speech"]["manual_allowed"]
    await manager.async_update_playback_projection(
        owner_profile_id="profile-a",
        session_id=sid,
        state="playing",
        media_identity="spotify:track:" + "2".zfill(22),
        title="Other track",
        artist="Other artist",
        duration_ms=300000,
        position_ms=0,
    )
    original = await _live_reference(
        manager, "profile-a", {"session_id": sid, "moment_id": moment.moment_id}
    )
    assert original["live_impression"]["event"]["event_id"] == "event-fixture"
    await manager.async_end(owner_profile_id="profile-a", session_id=sid)
    service = persistence_service(hass)
    await service.async_close()
    await service.async_initialize()
    hass.data["djconnect"].pop("session_history_query", None)
    reopened, status = await request(
        "GET",
        "/api/djconnect/v1/session/history/" + sid,
        {"window": "tail", "history_contract_version": 2},
    )
    assert status == 200, reopened
    restored = next(e for e in reopened["entries"] if e.get("moment_id") == moment.moment_id)
    assert (
        restored["text"] == moment.content
        and restored["live_impression"] == entry["live_impression"]
    )
    assert restored["session_speech"]["manual_allowed"]
    assert calls == ["declared synthetic research/narration"]
    return {
        "state": "PASS",
        "declared_synthetic_source_and_narration_calls": 1,
        "real_model_calls": 0,
        "real_public_source_calls": 0,
        "original_story_photo_event_survive_restart": True,
        "ordinary_paired_media_prepare3": True,
        "ordinary_paired_local_speech_prepare3": True,
        "native_or_installed_acceptance": "NOT_RUN",
    }


if __name__ == "__main__":
    from verify_session_conversation_history_http import main

    asyncio.run(main(qualification_extension=qualify))
