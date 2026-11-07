"""Actual paired HA HTTP/SQLite For-you; only Spotify/model response wires are synthetic."""
from __future__ import annotations
import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT/"scripts/verification")]


async def qualify(hass, manager, history, request, client, *, after=None, backend_id="source-spotify"):
    locale = os.environ.get("DJC_GOLDEN_LOCALE", "nl")
    if locale not in {"en", "nl"}:
        raise ValueError("unsupported_golden_locale")
    from custom_components.djconnect import mood_music_steering as first
    from custom_components.djconnect import spotify_backend
    from custom_components.djconnect.profile_context import profile_storage
    from custom_components.djconnect.domain.music_account import MusicAccountKind
    from custom_components.djconnect.ask_dj.dialogue import current_turn
    from custom_components.djconnect.ask_dj_history import _request_hash
    storage = profile_storage(hass)
    if backend_id != "source-spotify":
        from custom_components.djconnect.domain.backend import BackendProvider
        await storage.async_upsert_music_backend(backend_id, BackendProvider.SPOTIFY_DIRECT,
            display_name="Synthetic actual-observer source")
    await storage.async_upsert_music_account("source-account", backend_id, kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic first-play account", linked_profile_ids=frozenset({"profile-a"}),
        provider_account_id="synthetic-first-play-provider")
    profile = storage.household.profiles["profile-a"]
    await storage.async_update_profile("profile-a", preferences=replace(profile.preferences,
        default_backend_id=backend_id, default_music_account_id="source-account"))
    # The reusable history harness only needs a readable historical connection.
    # This fixture needs an actually loaded, Profile-bound provider Runtime too;
    # build it normally rather than replacing the production source authority.
    from custom_components.djconnect import DJConnectRuntime
    source_entry = hass.config_entries.async_get_entry("source-entry")
    hass.config_entries.async_update_entry(source_entry, data={**source_entry.data,
        "profile_id": "profile-a", "music_backend": backend_id,
        "spotify_client_id": "synthetic-first-play-provider"})
    hass.data["djconnect"]["source-entry"] = DJConnectRuntime(source_entry, device_token="")
    owner_entry = hass.config_entries.async_get_entry("owner-entry")
    hass.config_entries.async_update_entry(owner_entry, data={**owner_entry.data,
        "profile_backend_entry_id": "source-entry", "music_backend": backend_id,
        "music_account_id": "source-account"})
    from homeassistant.helpers.storage import Store
    from custom_components.djconnect.music_dna import MusicDNAManager
    dna_genres = ("neo soul", "r&b", "indie rock")
    dna_store = Store(hass, 1, "first_play_dna_synthetic_fixture")
    owner_runtime = hass.data["djconnect"]["owner-entry"]
    async def install_dna(*, enabled=True, genres=dna_genres, owner="profile-a"):
        # Original persisted data is explicitly synthetic owner consent/taste;
        # the actual MusicDNAManager and HA Store are not replaced by an adapter.
        await dna_store.async_save({"version": 1, "memories": {"profile:"+owner: {
            "enabled": enabled, "generation": 4, "favorite_genres": list(genres)}}})
        memory = MusicDNAManager(hass, store=dna_store)
        await memory.async_load()
        owner_runtime.memory = memory
        return memory
    await install_dna()
    source = {"backend_id": backend_id, "music_account_id": "source-account",
              "provider_entry_id": "source-entry", "provider_account_id": "synthetic-first-play-provider"}
    state = {"active": True, "playing": False, "track": None, "effects": [], "reads": [], "missing": "", "tracks": {}, "legacy_mode": False}
    class Response:
        status = 200
        headers = {}
        def __init__(self, value):
            self.value = value
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def json(self, **kwargs):
            return self.value
        async def text(self):
            return json.dumps(self.value)
    class Wire:
        def request(self, method, url, **kwargs):
            parsed = urlsplit(url)
            assert parsed.scheme == "https" and parsed.hostname == "api.spotify.com"
            path = parsed.path.removeprefix("/v1")
            if method == "GET":
                state["reads"].append(path)
                if path == "/me/player/devices":
                    return Response({"devices": [{"id": "synthetic-first-play-output", "name": "Synthetic speaker",
                        "is_active": state["active"], "is_restricted": False, "type": "Speaker"}]})
                if path == "/me/player":
                    return Response({"is_playing": state["playing"], "progress_ms": 0, "item": state["track"],
                        "device": {"id": "synthetic-first-play-output", "name": "Synthetic speaker"}})
                if path == "/me/player/queue":
                    return Response({"queue": [], "currently_playing": state["track"]})
                if path == "/me/tracks/contains":
                    return Response([False])
                if path == "/artists":
                    return Response({"artists": []})
                assert path == "/search", path
                query = parse_qs(parsed.query)
                genre = query["q"][0].split(":", 1)[1].strip('"')
                assert int(query["limit"][0]) == 8 and query["type"] == ["track"]
                tracks = [] if state["missing"] == genre else [track(genre, i) for i in range(3)]
                state["tracks"].update({item["uri"]: item for item in tracks})
                return Response({"tracks": {"items": tracks}})
            assert method == "PUT" and path in {"/me/player", "/me/player/play"}, (method, path)
            body = kwargs["json"]
            # This external seam is reached only after the ACTUAL shared normal
            # adapter has validated/reserved the effect in the actual HA Store.
            turn = current_turn.get()
            assert turn is not None and turn.effect_started
            receipt = history._data["users"][turn.scope]["dialogue_effect_receipts"].get(
                _request_hash(turn.scope, turn.client_id))
            assert receipt, "effect crossed network boundary before durable journal"
            if path == "/me/player":
                assert body == {"device_ids": ["synthetic-first-play-output"], "play": False}
                state["active"] = True
                state["effects"].append({"kind": "output", "play": False})
            else:
                assert parse_qs(parsed.query)["device_id"] == ["synthetic-first-play-output"]
                assert turn.first_play_admission.play_dispatched
                uris = body["uris"]
                state["effects"].append({"kind": "play", "uris": list(uris), "output": "synthetic-first-play-output"})
                state["playing"] = True
                state["track"] = state["tracks"][uris[0]]
            return Response({})
    def track(genre, index):
        identifier = hashlib.sha256((genre+str(index)).encode()).hexdigest()[:22]
        return {"id": identifier, "uri": "spotify:track:"+identifier, "type": "track",
            "name": "Synthetic first-play track", "is_playable": True, "is_local": False,
            "artists": [{"id": "A"*22, "name": "Synthetic artist"}], "duration_ms": 180000,
            "album": {"name": "Synthetic album", "images": []}}
    async def token(*args, **kwargs):
        if state.get("replace_on_token"):
            state["replace_on_token"] = False
            old = manager.current_active("profile-a")
            await manager.async_end(owner_profile_id="profile-a", session_id=old.session_id)
            state["replacement"] = await manager.async_start(owner_profile_id="profile-a", music_backend=backend_id,
                selected_mood="groove", locale="nl", history_source_context=source)
        return "SYNTHETIC_OFFLINE_UNUSABLE_TOKEN"
    cases, examples = {}, []
    from custom_components.djconnect import api_handlers
    async def no_background(*args, **kwargs):
        return None
    async def fallback_intro(hass, runtime, admission, directions):
        return first.FOR_YOU_INTRO[admission.locale], False
    async def start(locale=locale):
        previous = manager.current_active("profile-a")
        if previous:
            await manager.async_end(owner_profile_id="profile-a", session_id=previous.session_id)
        state.update(active=True, playing=False, track=None, effects=[], reads=[], tracks={})
        result, status = await request("POST", "/api/djconnect/v1/session/start", {"mood": "groove", "language": locale})
        assert status == 201, result
        offer = result["for_you"]
        assert offer["state"] == "available" and len(offer["options"]) == 3, offer
        assert offer["visible"] and offer["actions_available"]
        assert not state["effects"]
        examples.append({"stage": "session_start", "body": result})
        return result, offer
    async def select(offer, index, identifier):
        item = offer["result_set"]["items"][index]
        result, status = await request("POST", "/api/djconnect/v1/ask_dj/message", {
            "client_message_id": identifier, "text": item["title"], "language": locale, "audio_response": "never",
            "conversation_context": offer["conversation_context"],
            "choice_action": {"result_set_id": offer["result_set"]["result_set_id"],
                              "action_id": item["action_id"], "operation": "select"}})
        assert status == 200 and result["success"], result
        examples.append({"stage": identifier, "body": result})
        return result
    with patch.object(spotify_backend, "async_get_clientsession", return_value=Wire()), \
            patch.object(spotify_backend.SpotifyBackend, "_access_token", token), \
            patch.object(first, "_for_you_intro", fallback_intro), \
            patch.object(api_handlers, "_async_generate_initial_session_moment", no_background), \
            patch.object(api_handlers, "_connect_session_narration"), \
            patch("custom_components.djconnect.speaker_delivery.connect_automatic"), \
            patch.object(api_handlers, "playback_observation_manager") as observations:
        observations.return_value.async_start_spotify = no_background
        for locale in ((locale,) if "DJC_GOLDEN_LOCALE" in os.environ else first.FOR_YOU_LABELS):
            result, offer = await start(locale)
            assert offer["title"] == first.FOR_YOU_LABELS[locale]
            assert result["session_start_actions"]["schema_version"] == 2
            assert result["session_start_actions"]["items"][0]["kind"] == "inline_offer"
            assert set(o["genre"] for o in offer["options"]) == set(dna_genres)
            assert len({o["visual_recipe"]["artistic_direction"] for o in offer["options"]}) == 3
            assert all("uris" not in o["visual_recipe"] and "action_id" not in o["visual_recipe"] for o in offer["options"])
            reads = list(state["reads"])
            for _ in range(2):
                active, status = await request("GET", "/api/djconnect/v1/session/active")
                assert status == 200 and active["for_you"]["options"] == offer["options"], active
            assert state["reads"] == reads and not state["effects"]
            cases[locale+"_genuine_start_prepares_three_genres_polling_no_provider_or_effects"] = "PASS"
        locale = os.environ.get("DJC_GOLDEN_LOCALE", "nl")
        from types import SimpleNamespace
        watch = api_handlers._session_offer_fields(hass, owner_runtime,
            SimpleNamespace(client_type='watchos', profile_id='profile-a', device_id='synthetic-watch'),
            manager.current_active('profile-a'))
        assert watch['for_you'] is None and not watch['session_start_actions']['available']
        cases['watch_no_card_or_startup_actions'] = 'PASS'
        result, offer = await start()
        chosen = offer["result_set"]["items"][1]
        played = await select(offer, 1, "for-you-known-output")
        assert played["action_outcome"]["readback_confirmed"], played
        original_effects = list(state["effects"])
        repeated = await select(offer, 1, "for-you-known-output")
        assert repeated["assistant_message"]["id"] == played["assistant_message"]["id"]
        assert state["effects"] == original_effects
        cases["duplicate_original_turn_never_starts_twice"] = "PASS"
        assert state["effects"] == [{"kind": "play", "uris": chosen["uris"], "output": "synthetic-first-play-output"}]
        active, status = await request("GET", "/api/djconnect/v1/session/active")
        assert status == 200 and not active["for_you"]["visible"]
        assert not active["for_you"]["options"]
        cases["known_speaker_exact_mix_one_play_confirmation_closes_card"] = "PASS"
        result, offer = await start()
        state["active"] = False
        chosen = offer["result_set"]["items"][0]
        speakers = await select(offer, 0, "for-you-needs-output")
        assert speakers["first_play"]["state"] == "output" and not state["effects"], speakers
        played = await select({**offer, "result_set": speakers["result_set"]}, 0, "for-you-speaker-finishes-mix")
        assert played["action_outcome"]["readback_confirmed"], played
        assert state["effects"] == [{"kind": "output", "play": False},
            {"kind": "play", "uris": chosen["uris"], "output": "synthetic-first-play-output"}]
        cases["genre_before_speaker_one_flow_bubble_then_same_mix_no_second_genre"] = "PASS"
        old_context = offer['conversation_context']
        result, offer = await start()
        before_offer = offer['offer_id']
        stale, status = await request('POST', '/api/djconnect/v1/ask_dj/message', {
            'client_message_id': 'stale-old-session-refresh', 'text': first.FIRST_PLAY_COPY[locale][1],
            'language': locale, 'audio_response': 'never', 'conversation_context': old_context})
        assert status == 409, stale
        active, status = await request('GET', '/api/djconnect/v1/session/active')
        assert status == 200 and active['for_you']['offer_id'] == before_offer
        cases['old_session_refresh_cannot_rebind_or_replace_new_offer'] = 'PASS'
        refreshed, status = await request('POST', '/api/djconnect/v1/ask_dj/message', {
            'client_message_id': 'explicit-same-session-refresh', 'text': first.FIRST_PLAY_COPY[locale][1],
            'language': locale, 'audio_response': 'never', 'conversation_context': offer['conversation_context']})
        assert status == 200 and refreshed['success'] and not state['effects'], refreshed
        assert refreshed['for_you']['state'] == 'available', refreshed['for_you']
        active, status = await request('GET', '/api/djconnect/v1/session/active')
        assert active['for_you']['offer_id'] == refreshed['result_set']['result_set_id'] != before_offer
        offer = active['for_you']
        cases['explicit_refresh_updates_same_card_without_playback'] = 'PASS'
        dismissed, status = await request("POST", "/api/djconnect/v1/ask_dj/message", {
            "conversation_context": offer["conversation_context"],
            "choice_action": {"operation": "dismiss", "result_set_id": offer["offer_id"], "action_id": ""}})
        assert status == 200 and not dismissed["for_you"]["visible"], dismissed
        active, status = await request("GET", "/api/djconnect/v1/session/active")
        assert status == 200 and not active["for_you"]["visible"] and not state["effects"]
        cases["authenticated_dismissal_no_effects_polls_remain_hidden"] = "PASS"
        # Expire only the choice owner's clock; no real sleep or HA auth clock change.
        result, offer = await start()
        original_clock = history.dialogue.clock
        with patch.object(history.dialogue, "clock", lambda: original_clock() + 3600):
            item = offer["result_set"]["items"][0]
            expired, status = await request("POST", "/api/djconnect/v1/ask_dj/message", {
                "client_message_id": "expired-for-you-choice", "text": item["title"],
                "language": locale, "audio_response": "never",
                "conversation_context": offer["conversation_context"],
                "choice_action": {"result_set_id": offer["offer_id"],
                    "action_id": item["action_id"], "operation": "select"}})
            assert status == 409 and not state["effects"], expired
        cases["expired_choice_cannot_start_or_transfer_output"] = "PASS"
        if after is not None:
            cases.update(await after(hass, manager, history, request, state))
    return {"qualification": "ACTUAL_ISOLATED_HA_PAIRED_HTTP_STORE_FOR_YOU_SYNTHETIC_PROVIDER_ONLY",
        "language": locale, "cases": cases, "examples": examples, "real_provider_calls": 0, "model_provider_calls": 0,
        "native_installed_acceptance": "NOT_RUN", "paid_dependency": False,
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == "__main__":
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
