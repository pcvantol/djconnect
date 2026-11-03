"""Actual paired HA/history and licensed-photo lifecycle with declared fixtures.

The registered HA agent/source transports are synthetic, never real prose or
provider acceptance. The public photo decoder and HTTP delivery are real.
"""
import asyncio
import io
import json
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]


async def qualify(hass, manager, history, request, client):
    from PIL import Image
    from custom_components.djconnect import artist_photo, pipeline
    from custom_components.djconnect.ask_dj import public_research as r
    from custom_components.djconnect.ask_dj.band_story import images
    from custom_components.djconnect.const import DOMAIN
    from custom_components.djconnect.persistence import persistence_service

    pixels = io.BytesIO()
    Image.new("RGB", (512, 512), "navy").save(pixels, format="PNG")
    original_pixels = pixels.getvalue()
    title = "File:Synthetic musical group.png"
    upload = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Synthetic_musical_group.png"
    excerpt = ("Example Band is a rock band. Example Band consists of Ava Example and Bo Sample. "
               "Ava Example sings and Bo Sample plays guitar.")
    source = r._source("Wikipedia", "Example Band", "https://en.wikipedia.org/wiki/Example_Band",
        excerpt, "en", entity_id="Q123", original_text=excerpt,
        paragraph_ranges=((0, len(excerpt)),))
    model_calls, source_reads, photo_reads, cases, urls = [], [], [], [], []
    selected = ["nl"]
    answers = {
        "nl": "Example Band bestaat uit Ava Example en Bo Sample. Ava Example zingt en Bo Sample speelt gitaar.",
        "en": "Example Band consists of Ava Example and Bo Sample. Ava Example sings and Bo Sample plays guitar.",
        "de": "Example Band besteht aus Ava Example und Bo Sample. Ava Example singt und Bo Sample spielt Gitarre.",
        "fr": "Example Band se compose d’Ava Example et de Bo Sample. Ava Example chante et Bo Sample joue de la guitare.",
        "es": "Example Band está formada por Ava Example y Bo Sample. Ava Example canta y Bo Sample toca la guitarra.",
    }
    questions = {
        "nl": "Uit welke bandleden bestaat Example Band?", "en": "Who are the members of Example Band?",
        "de": "Wer sind die Mitglieder von Example Band?", "fr": "Qui sont les membres de Example Band ?",
        "es": "¿Quiénes son los miembros de Example Band?",
    }

    async def research(subject, question, language, guard, **kwargs):
        await guard()
        assert subject == "Example Band" and kwargs.get("original_paragraphs") is True
        source_reads.append({"subject": subject, "declared_synthetic_sources": True})
        return [source], {"state": "available", "fixture": "declared_synthetic_group"}

    async def photo_read(hass_arg, url, guard, *, json_body):
        await guard()
        assert hass_arg is hass
        photo_reads.append({"kind": "metadata" if json_body else "pixels", "declared_synthetic_transport": True})
        if url == upload:
            assert not json_body
            return original_pixels, "image/png"
        assert json_body
        parsed = urlsplit(url)
        query = parse_qs(parsed.query)
        if parsed.netloc == "www.wikidata.org":
            assert query["ids"] == ["Q123"]
            return {"entities": {"Q123": {"id": "Q123", "claims": {"P18": [
                {"rank": "normal", "mainsnak": {"datavalue": {"value": title[5:]}}}]}}}}
        assert parsed.netloc == "commons.wikimedia.org" and query["titles"] == [title]
        return {"query": {"pages": [{"ns": 6, "title": title, "imageinfo": [{
            "url": upload, "thumburl": upload, "width": 512, "height": 512,
            "thumbwidth": 512, "thumbheight": 512, "mime": "image/png", "thumbmime": "image/png",
            "mediatype": "BITMAP", "sha1": "a" * 40, "descriptionurl": artist_photo.file_url(title),
            "extmetadata": {key: {"value": value} for key, value in {
                "Artist": "Synthetic Photographer", "Credit": "Explicit qualification image",
                "Attribution": "Synthetic Photographer — CC BY 4.0",
                "LicenseShortName": "CC BY 4.0", "LicenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                "ImageDescription": "Synthetic musical group performing live on stage"}.items()}}]}]}}

    def review(projection):
        spans = [span for s in projection["evidence"]["public_music_research"]["sources"]
                 for span in s["evidence_spans"]]
        result = []
        for row in projection["drafts"]:
            words = list(re.finditer(r"\S+", row["text"]))
            checks, cursor = [], 0
            for sentence in r._sentences(row["text"]):
                start = row["text"].index(sentence, cursor)
                end = start + len(sentence)
                first = next(i for i, w in enumerate(words) if w.start() == start)
                last = next(i for i, w in enumerate(words) if w.end() >= end)
                checks.append({"answer_from": row["answer_words"][first][0],
                    "answer_to": row["answer_words"][last][0], "kind": "fact", "evidence_ids": [spans[0]["id"]]})
                cursor = words[last].end()
            result.append({"index": row["index"], "sha256": row["sha256"], "review": {
                "review_schema": "source_answer_ids_review_v1", "supported": True,
                "language_ok": True, "style_ok": True, "unsupported_claims": [],
                "temporal_claims": [], "claim_checks": checks}})
        return {"draft_reviews": result}

    async def agent(hass_arg, data, **kwargs):
        assert hass_arg is hass and kwargs.get("allow_agent_fallback") is False
        projection = json.loads(data["text"].split("\nData:\n", 1)[1])
        if "available" in projection:
            value = {"read": "research", "reference": "named", "subject": "Example Band",
                     "exclude_current": False, "angle": "members"}
        elif "drafts" in projection:
            value = review(projection)
        else:
            assert projection["artist_draft_schema"] == "artist_evidence_drafts_v1"
            assert projection["style"]["language"] == selected[0]
            value = {"schema": "artist_evidence_drafts_v1", "drafts": [
                {"anchors": [projection["literal_anchors"][0]["id"]], "text": answers[selected[0]]}]}
        model_calls.append({"locale": selected[0], "declared_synthetic_reply": True})
        return {"response": {"speech": {"plain": {"speech": json.dumps(value, ensure_ascii=False)}}}}

    # The common history harness begins in manual mode. Configure real SDK
    # entries and the real Profile graph with declared synthetic provider data;
    # never replace the product authority factory with a boolean fixture.
    from dataclasses import replace
    from custom_components.djconnect import DJConnectRuntime
    from custom_components.djconnect.domain.music_account import MusicAccountKind
    storage = hass.data[DOMAIN]["djconnect_profile_platform"]
    source_entry = hass.config_entries.async_get_entry("source-entry")
    hass.config_entries.async_update_entry(source_entry, data={**source_entry.data,
        "music_backend": "source-spotify", "profile_id": "profile-a"})
    paired = hass.config_entries.async_get_entry("owner-entry")
    hass.config_entries.async_update_entry(paired, data={**paired.data,
        "music_backend": "source-spotify", "music_account_id": "source-account",
        "profile_backend_entry_id": "source-entry"})
    hass.data[DOMAIN]["source-entry"] = DJConnectRuntime(source_entry)
    await storage.async_upsert_music_account("source-account", "source-spotify",
        kind=MusicAccountKind.PERSONAL, display_name="Synthetic original source",
        linked_profile_ids=frozenset({"profile-a"}), provider_account_id="synthetic-original-provider")
    await storage.async_update_profile("profile-a", preferences=replace(
        storage.household.profiles["profile-a"].preferences,
        default_backend_id="source-spotify", default_music_account_id="source-account"))
    # A normal separate retained Session makes targeted archive erasure observable.
    session = await manager.async_start(owner_profile_id="profile-a", music_backend="spotify_direct", locale="nl")
    sid = session.session_id
    for locale in (*questions, "nl-lower"):
        selected[0] = "nl" if locale == "nl-lower" else locale
        question = questions[selected[0]].lower() if locale == "nl-lower" else questions[locale]
        before_calls, before_reads = len(model_calls), len(photo_reads)
        with patch.object(r, "research", research), patch.object(artist_photo, "_read", photo_read), \
             patch.object(pipeline, "_call_conversation_process_transport", agent):
            result, status = await request("POST", "/api/djconnect/v1/ask_dj/message", {
                "client_message_id": "band-members-" + locale, "text": question,
                "language": selected[0], "audio_response": "never", "conversation_context": {"session_id": sid}})
        assert status == 200 and result["text"] == answers[selected[0]], result
        assert result["knowledge_basis"] == "fetched_public_music_research_v1"
        assert len(result["images"]) == 1, result
        photo = result["images"][0]
        assert photo["attribution"]["author"] == "Synthetic Photographer"
        assert photo["attribution"]["license"] == "CC-BY-4.0" and photo["width"] == photo["height"] == 512
        assert result["assistant_message"]["images"] == result["images"]
        assert len(model_calls) - before_calls == (3 if locale == "nl-lower" else 2)
        assert len(photo_reads) - before_reads == 3 and not result.get("playback_actions")
        urls.append(photo["url"])
        async with client.get(photo["url"]) as response:
            assert response.status == 200 and await response.read() == original_pixels
            assert response.headers["Cache-Control"] == "private, no-store"
        assert len(photo_reads) - before_reads == 3, "GET must never re-fetch external pixels"
        cases.append({"kind": "membership_and_photo", "language": locale, "state": "PASS",
                      "declared_model_responses": len(model_calls) - before_calls})
    # New-topic turns did not steal earlier photographs; the original bytes remain.
    async with client.get(urls[0]) as response:
        assert response.status == 200 and await response.read() == original_pixels
    original, status = await request("GET", "/api/djconnect/v1/ask_dj/history", {"conversation_scope": "profile"})
    assert status == 200 and any(m.get("images") for m in original["messages"]), {"status": status, "keys": list(original)}
    from custom_components.djconnect.session_conversation import query_service
    query = query_service(hass, history)
    timeline = await query.async_timeline_page("profile-a", sid)
    illustrated = [e for e in timeline["entries"] if e.get("images")]
    assert len(illustrated) == 6, timeline
    assert {e["images"][0]["url"] for e in illustrated} == set(urls)
    entry = illustrated[0]
    opened = await query.async_open_entry("profile-a", sid, entry["entry_id"])
    assert opened["entry"]["images"] == entry["images"]
    source_view = await query.async_open_source_entry("profile-a", sid, entry["entry_id"])
    assert "images" not in source_view["entry"], "photo capabilities must not enter dependent source input"
    window = await query.async_timeline_window("profile-a", sid, window="tail")
    assert sum(bool(e.get("images")) for e in window["entries"]) == 6
    cases.append({"kind": "session_page_window_open_preserve_original_photo_source_input_excludes_it", "state": "PASS"})
    persisted = await history._store.async_load()
    assert "/image_proxy/band-" not in json.dumps(persisted), "capability URLs must not enter Store"
    await manager.async_end(owner_profile_id="profile-a", session_id=sid)
    old_dialogue = history.scope_revision("profile:profile-a")
    old_media = history.media_privacy_revision("profile:profile-a")
    removed = await history.async_forget_archived_sessions("profile-a", frozenset({sid}))
    assert removed > 0 and history.scope_revision("profile:profile-a") == old_dialogue
    assert history.media_privacy_revision("profile:profile-a") != old_media
    assert images(hass).assets == {}, "committed targeted privacy change scrubs without another GET"
    before = len(photo_reads)
    async with client.get(urls[0]) as response:
        assert response.status == 404
    assert len(photo_reads) == before
    assert not any(a.get("body") for a in images(hass).assets.values() if not a["allowed"]())
    cases.append({"kind": "original_targeted_forget_closes_capability", "state": "PASS"})
    # A newly authorized question can create a new original lease. Exercise the
    # actual SDK's callback phase for the DISTINCT provider entry in this lab;
    # this is not real integration installation/device lifecycle acceptance.
    selected[0] = "nl"
    with patch.object(r, "research", research), patch.object(artist_photo, "_read", photo_read), \
         patch.object(pipeline, "_call_conversation_process_transport", agent):
        after_erase, status = await request("POST", "/api/djconnect/v1/ask_dj/message", {
            "client_message_id": "band-new-original-after-erase", "text": questions["nl"],
            "language": "nl", "audio_response": "never", "conversation_context": {"session_id": None}})
    assert status == 200 and len(after_erase["images"]) == 1, after_erase
    token = after_erase["images"][0]["url"].rsplit("/", 1)[1]
    retained = images(hass).assets[token]
    from homeassistant.config_entries import ConfigEntryState
    source_entry._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
    await source_entry._async_process_on_unload(hass)
    assert retained == {} and images(hass).assets == {}, "SDK provider unload scrubs before any GET"
    cases.append({"kind": "distinct_original_provider_sdk_unload_scrubs", "state": "PASS"})
    count = await persistence_service(hass).async_in_transaction(lambda tx: tx.fetchone(
        "SELECT COUNT(*) AS n FROM djconnect_session_acceptances WHERE session_id=? AND kind='dj_moment'", (sid,)))
    assert count[0] == 0
    images(hass).close()
    assert hass.data[DOMAIN]["public_band_images"].assets == {}
    return {"state": "PASS", "cases": cases, "source_reads": source_reads,
        "declared_model_replies": len(model_calls), "declared_photo_reads": len(photo_reads),
        "actual_original_pixel_bytes": len(original_pixels), "external_network_calls": 0, "paid_model_calls": 0,
        "scope": "Actual paired HA/history/word-ID review/Commons licence+Pillow+typed HTTP lifecycle. Sources and prose explicitly synthetic, not real editorial/native/installed acceptance."}


if __name__ == "__main__":
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
