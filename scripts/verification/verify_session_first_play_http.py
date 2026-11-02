"""Actual paired HA HTTP/SQLite first-play; only Spotify wire is synthetic."""
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


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import mood_music_steering as first
    from custom_components.djconnect import spotify_backend
    from custom_components.djconnect.profile_context import profile_storage
    from custom_components.djconnect.domain.music_account import MusicAccountKind
    from custom_components.djconnect.ask_dj.dialogue import current_turn
    from custom_components.djconnect.ask_dj_history import _request_hash
    storage = profile_storage(hass)
    await storage.async_upsert_music_account("source-account", "source-spotify", kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic first-play account", linked_profile_ids=frozenset({"profile-a"}),
        provider_account_id="synthetic-first-play-provider")
    profile = storage.household.profiles["profile-a"]
    await storage.async_update_profile("profile-a", preferences=replace(profile.preferences,
        default_backend_id="source-spotify", default_music_account_id="source-account"))
    # The reusable history harness only needs a readable historical connection.
    # This fixture needs an actually loaded, Profile-bound provider Runtime too;
    # build it normally rather than replacing the production source authority.
    from custom_components.djconnect import DJConnectRuntime
    source_entry = hass.config_entries.async_get_entry("source-entry")
    hass.config_entries.async_update_entry(source_entry, data={**source_entry.data,
        "profile_id": "profile-a", "music_backend": "source-spotify",
        "spotify_client_id": "synthetic-first-play-provider"})
    hass.data["djconnect"]["source-entry"] = DJConnectRuntime(source_entry, device_token="")
    owner_entry = hass.config_entries.async_get_entry("owner-entry")
    hass.config_entries.async_update_entry(owner_entry, data={**owner_entry.data,
        "profile_backend_entry_id": "source-entry", "music_backend": "source-spotify",
        "music_account_id": "source-account"})
    source = {"backend_id": "source-spotify", "music_account_id": "source-account",
              "provider_entry_id": "source-entry", "provider_account_id": "synthetic-first-play-provider"}
    state = {"active": True, "playing": False, "track": None, "effects": [], "reads": [], "missing": ""}
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
                genre = query["q"][0].split(":", 1)[1]
                assert int(query["limit"][0]) == 8 and query["type"] == ["track"]
                tracks = [] if state["missing"] == genre else [track(genre, i) for i in range(3)]
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
                state["track"] = next(track(g, i) for g in first.FIRST_PLAY_LABELS for i in range(3)
                                      if track(g, i)["uri"] == uris[0])
            return Response({})
    def track(genre, index):
        identifier = hashlib.sha256((genre+str(index)).encode()).hexdigest()[:22]
        return {"id": identifier, "uri": "spotify:track:"+identifier, "type": "track",
            "name": "Synthetic first-play track", "is_playable": True, "is_local": False,
            "artists": [{"id": "A"*22, "name": "Synthetic artist"}], "duration_ms": 180000,
            "album": {"name": "Synthetic album", "images": []}}
    async def token(*args, **kwargs):
        return "SYNTHETIC_OFFLINE_UNUSABLE_TOKEN"
    cases, examples = {}, []
    async def fresh(mood="groove", locale="nl"):
        previous = manager.current_active("profile-a")
        if previous:
            await manager.async_end(owner_profile_id="profile-a", session_id=previous.session_id)
        state.update(playing=False, track=None, active=True, effects=[], reads=[], missing="")
        return await manager.async_start(owner_profile_id="profile-a", music_backend="source-spotify",
            selected_mood=mood, locale=locale, history_source_context=source)
    async def submit(session, identifier, *, locale="nl", choice=None):
        payload = {"client_message_id": identifier, "text": first.FIRST_PLAY_COPY[locale][1] if choice is None else "",
            "language": locale, "audio_response": "never", "conversation_context": {"session_id": session.session_id}}
        if choice is not None:
            payload.update(text=choice["title"], choice_action={"result_set_id": choice["result_set_id"],
                "action_id": choice["action_id"], "operation": "select"})
        return await request("POST", "/api/djconnect/v1/ask_dj/message", payload)
    with patch.object(spotify_backend, "async_get_clientsession", return_value=Wire()), \
            patch.object(spotify_backend.SpotifyBackend, "_access_token", token):
        for mood in first.FIRST_PLAY_GENRES:
            for locale in first.FIRST_PLAY_COPY:
                session = await fresh(mood, locale)
                catalog, status = await request("GET", "/api/djconnect/v1/session/active")
                assert status == 200 and catalog["first_play_action"]["available"], catalog
                assert set(catalog["first_play_action"]["localizations"]) == set(first.FIRST_PLAY_COPY)
                result, status = await submit(session, "first-play-"+mood+locale, locale=locale)
                assert status == 200 and result["success"], result
                actions = result["result_set"]["items"]
                assert tuple(a["genre"] for a in actions) == first.FIRST_PLAY_GENRES[mood]
                assert len({a["action_id"] for a in actions}) == 3 and all(len(a["uris"]) == 3 for a in actions)
                assert not state["effects"]
                cases[mood+"_"+locale+"_actual_owner_catalog_and_three_backed_genres_without_play"] = "PASS"
        session = await fresh()
        state["active"] = False
        catalog_before, status = await request("GET", "/api/djconnect/v1/session/active")
        assert status == 200 and catalog_before["first_play_action"]["available"]
        before, status = await submit(session, "first-play-no-output")
        assert status == 200 and before["first_play"]["state"] == "output", before
        assert not state["effects"] and "/search" not in state["reads"]
        genre, status = await submit(session, "first-play-choose-output", choice=before["result_set"]["items"][0])
        assert status == 200 and genre["first_play"]["state"] == "genres", genre
        assert state["effects"] == [{"kind": "output", "play": False}]
        assert genre["first_play"]["expires_in"] <= before["first_play"]["expires_in"]
        chosen = genre["result_set"]["items"][1]
        played, status = await submit(session, "first-play-choose-genre", choice=chosen)
        assert status == 200 and played["success"], played
        assert played["action_outcome"] == {"state": "dispatched", "readback_confirmed": True, "retry_automatically": False}
        assert state["effects"][-1] == {"kind": "play", "uris": chosen["uris"], "output": "synthetic-first-play-output"}
        assert len(state["effects"]) == 2 and not played["playback_actions"]
        saved = await history._store.async_load()
        receipts = saved["users"]["profile:profile-a"]["dialogue_effect_receipts"]
        for identifier in ("first-play-choose-output", "first-play-choose-genre"):
            assert _request_hash("profile:profile-a", identifier) in receipts
        replay, status = await submit(session, "first-play-choose-genre", choice=chosen)
        assert status == 200 and replay.get("deduplicated"), replay
        denied, status = await submit(session, "first-play-new-id-same-genre", choice=chosen)
        assert status == 409, denied
        assert len(state["effects"]) == 2
        catalog, status = await request("GET", "/api/djconnect/v1/session/active")
        assert status == 200 and not catalog["first_play_action"]["available"], catalog
        cases["actual_output_then_three_genres_then_one_ordered_mix_no_extra_PlayNow"] = "PASS"
        cases["real_durable_effect_journal_before_both_wire_effects"] = "PASS"
        cases["same_id_replay_and_new_id_original_action_never_redispatch"] = "PASS"
        cases["consumed_first_play_action_is_retired"] = "PASS"
        examples.append({"catalogue_before": catalog_before["first_play_action"],
            "catalogue_after": catalog["first_play_action"],
            "output": before, "genres": genre, "played": played, "denied": denied})
    return {"qualification": "ACTUAL_ISOLATED_HA_PAIRED_HTTP_STORE_FIRST_PLAY_SYNTHETIC_PROVIDER_ONLY",
        "cases": cases, "examples": examples, "model_provider_calls": 0, "real_provider_calls": 0,
        "native_installed_acceptance": "NOT_RUN", "paid_or_DNA_dependency": False,
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == "__main__":
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
