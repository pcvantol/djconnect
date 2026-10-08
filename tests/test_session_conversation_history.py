"""Causal Session history regressions at the existing Runtime/storage boundary."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import sys
import types

package = types.ModuleType("custom_components.djconnect")
package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components" / "djconnect")]
sys.modules.setdefault("custom_components.djconnect", package)

from tests.test_session_runtime import _load_runtime_module  # noqa: E402
from custom_components.djconnect.persistence.service import PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.historical_projection_query import HistoricalProjectionQueryService  # noqa: E402


class SessionConversationHistoryTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()
        if cls.previous_const is not None:
            sys.modules["custom_components.djconnect.const"] = cls.previous_const
        else:
            sys.modules.pop("custom_components.djconnect.const", None)
        import importlib
        from tests.test_http_voice_helpers import install_http_stubs

        install_http_stubs()
        cls.handlers = importlib.import_module("custom_components.djconnect.api_handlers")
        cls.http = importlib.import_module("custom_components.djconnect.http")

    @classmethod
    def tearDownClass(cls):
        if cls.previous_const is None:
            sys.modules.pop("custom_components.djconnect.const", None)
        else:
            sys.modules["custom_components.djconnect.const"] = cls.previous_const
        sys.modules.pop("custom_components.djconnect.session_runtime", None)

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "history.sqlite3"
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.repo = HistoricalProjectionRepository(self.service)
        self.sessions = PersistentSessionRepository(self.service)
        self.manager = self.runtime.SessionRuntimeManager(self.sessions, self.repo)
        self.queries = HistoricalProjectionQueryService(self.repo)

    async def asyncTearDown(self):
        await self.service.async_close()
        self.tmp.cleanup()

    async def test_tail_window_discovers_new_entries_beyond_first_page(self):
        session = await self.observed_session()
        for i in range(25):
            await self.manager.async_update_playback_projection(
                owner_profile_id="profile-a",
                session_id=session.session_id,
                state="playing",
                media_identity=f"spotify:track:{i:022d}",
                title=f"Track {i}",
                artist="Metallica",
                duration_ms=120000,
                position_ms=1000,
            )
        first = await self.queries.async_timeline_page("profile-a", session.session_id)
        tail = await self.queries.async_timeline_window(
            "profile-a", session.session_id, window="tail", limit=3
        )
        self.assertEqual(
            [e["playback"]["title"] for e in tail["entries"]], ["Track 22", "Track 23", "Track 24"]
        )
        anchor_id = first["entries"][10]["entry_id"]
        window = await self.queries.async_timeline_window(
            "profile-a", session.session_id, window="anchor", anchor_entry_id=anchor_id, limit=3
        )
        self.assertEqual(window["entries"][0]["entry_id"], anchor_id)
        self.assertEqual([e["order"] for e in window["entries"]], [11, 12, 13])
        import os
        import json

        capture = os.environ.get("DJC_HISTORY_CAPTURE_DIR")
        if capture:
            Path(capture).mkdir(parents=True, exist_ok=True)
            (Path(capture) / "window-producer-receipt.json").write_text(
                json.dumps(
                    {
                        "qualification": "actual Runtime accepted playback and repository/query window; synthetic inputs, not installed/native proof",
                        "first_page": first,
                        "tail_window": tail,
                        "anchor_window": window,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        with self.assertRaises(PermissionError):
            await self.queries.async_timeline_window("profile-b", session.session_id, window="tail")
        with self.assertRaises(PermissionError):
            await self.queries.async_timeline_window(
                "profile-a", session.session_id, window="anchor", anchor_entry_id="missing"
            )

    async def test_full_normalization_cross_character_utf16_highlights(self):
        from custom_components.djconnect.session_history_projection import text_highlights

        for text, query, length in [("가", "가", 2), ("ｶﾞ", "ガ", 2), ("Straße", "STRASSE", 6)]:
            self.assertEqual(
                text_highlights(text, query), [{"start_utf16": 0, "length_utf16": length}]
            )

    async def test_profile_history_effective_shared_privacy_denies(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        payload = {**identity, "privacy_mode": "shared", "conversation_scope": "profile"}
        for handler in (
            self.handlers.async_handle_ask_dj_history_payload,
            self.handlers.async_handle_ask_dj_history_clear_payload,
        ):
            result, status = await handler(hass, payload, headers=headers)
            self.assertEqual(status, 403, result)
            self.assertEqual(result["error"], "history_not_allowed")

    async def test_http_capabilities_advertises_same_history_versions(self):
        response = await self.http.DJConnectTransportCapabilitiesView().get(None)
        body = response["payload"]
        self.assertTrue(body["capabilities"]["session_conversation_history"])
        self.assertTrue(body["capabilities"]["session_flow_text_search"])
        self.assertEqual(body["contract_versions"]["session_conversation_history"], 1)
        self.assertEqual(body["contract_versions"]["session_flow_text_search"], 1)

    async def observed_session(self):
        session = await self.manager.async_start(
            owner_profile_id="profile-a", music_backend="spotify_direct"
        )
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=session.session_id,
            state="playing",
            media_identity="spotify:track:0123456789abcdefghijkL",
            title="One",
            artist="Metallica",
            album="…And Justice for All",
            duration_ms=120000,
            position_ms=1000,
        )
        return session

    async def test_ended_session_list_is_available_after_new_query_instance(self):
        session = await self.observed_session()
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.queries = HistoricalProjectionQueryService(
            HistoricalProjectionRepository(self.service)
        )
        page = await self.queries.async_session_page("profile-a")
        self.assertEqual([s["session_id"] for s in page["sessions"]], [session.session_id])
        self.assertEqual(page["sessions"][0]["lifecycle_status"], "ENDED")

    async def test_real_playback_observation_is_in_durable_timeline(self):
        session = await self.observed_session()
        page = await self.queries.async_timeline_page("profile-a", session.session_id)
        tracks = [e for e in page["entries"] if e["kind"] == "playback_observed"]
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["playback"]["artist"], "Metallica")
        self.assertEqual(tracks[0]["playback"]["coverage"], "observed_playing_not_full_listen")

    async def test_historical_match_has_proven_open_target_without_runtime_start(self):
        session = await self.observed_session()
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        result = await self.queries.async_find_playback("profile-a", artist="Metallica")
        self.assertEqual(len(result["matches"]), 1)
        target = result["matches"][0]["open_action"]
        self.assertEqual(target["kind"], "open_session")
        self.assertEqual(target["session_id"], session.session_id)
        opened = await self.queries.async_open_entry(
            "profile-a", target["session_id"], target["entry_id"]
        )
        self.assertTrue(opened["read_only"])
        self.assertIsNone(await self.manager.async_get_active("profile-a"))

    async def test_literal_search_finds_casefold_phrase_outside_loaded_page(self):
        session = await self.observed_session()
        for i in range(3):
            await self.manager.async_update_playback_projection(
                owner_profile_id="profile-a",
                session_id=session.session_id,
                state="playing",
                media_identity=f"spotify:track:{i:022d}",
                title=f"Track {i}",
                artist="Another artist",
                duration_ms=120000,
                position_ms=1000,
            )
        page = await self.queries.async_timeline_page("profile-a", session.session_id, limit=1)
        self.assertEqual(len(page["entries"]), 1)
        found = await self.queries.async_search_entries(
            "profile-a", session.session_id, "another ART"
        )
        self.assertEqual(len(found["matches"]), 3)
        self.assertTrue(all(m["highlights"] for m in found["matches"]))

    async def test_other_profile_cannot_query_or_search_private_timeline(self):
        session = await self.observed_session()
        with self.assertRaises(PermissionError):
            await self.queries.async_timeline_page("profile-b", session.session_id)
        with self.assertRaises(PermissionError):
            await self.queries.async_search_entries("profile-b", session.session_id, "Metallica")

    async def transport_fixture(self):
        from custom_components.djconnect.domain.storage import ProfilePlatformStorage
        from custom_components.djconnect.domain.backend import BackendProvider
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
        from tests.test_ask_dj_history import FakeStore

        hass = types.SimpleNamespace(data={}, config=types.SimpleNamespace(language="nl"))
        storage = ProfilePlatformStorage()
        await storage.async_upsert_music_backend(
            "later_manual", BackendProvider.FUTURE_PROVIDER, display_name="Manual fixture"
        )
        await storage.async_create_profile(
            "Owner", profile_id="profile-a", default_backend_id="later_manual"
        )
        await storage.async_upsert_device(
            "djconnect-ios-ABCDEF123456", "ios", linked_profile_id="profile-a"
        )
        history = AskDJHistoryManager(store=FakeStore())
        runtime = types.SimpleNamespace(
            config={
                "device_id": "djconnect-ios-ABCDEF123456",
                "client_type": "ios",
                "music_backend": "later_manual",
            },
            device_status={"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"},
            ask_dj_history=history,
            device_token="synthetic-fixture-token",
            authorize_device_request=lambda headers, device_id=None, client_type=None: (
                headers.get("Authorization") == "Bearer synthetic-fixture-token"
                and device_id == "djconnect-ios-ABCDEF123456"
                and client_type == "ios"
            ),
        )
        hass.data["djconnect"] = {
            "runtime": runtime,
            "owner-entry": runtime,
            "djconnect_profile_platform": storage,
            "persistence_service": self.service,
            "session_runtime_manager": self.manager,
        }
        identity = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"}
        headers = {"Authorization": "Bearer synthetic-fixture-token"}
        return hass, runtime, history, identity, headers

    async def test_real_handlers_bind_text_and_voice_derived_turns_and_archive_restart(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.manager.async_start(
            owner_profile_id="profile-a", selected_mood="energy", locale="nl"
        )
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=session.session_id,
            state="playing",
            media_identity="spotify:track:0123456789abcdefghijkL",
            title="One",
            artist="Metallica",
            album="…And Justice for All",
            duration_ms=120000,
            position_ms=1000,
        )

        async def insight():
            return {}

        moment = await self.manager.async_process_track_started(
            owner_profile_id="profile-a", session_id=session.session_id, insight_provider=insight
        )
        self.assertIsNotNone(moment)
        payload, status = await self.handlers.async_handle_session_history_payload(
            hass,
            {**identity, "session_id": session.session_id},
            operation="timeline",
            headers=headers,
        )
        self.assertEqual(status, 200, payload)
        moments = [e for e in payload["entries"] if e["kind"] == "dj_moment"]
        self.assertEqual(len(moments), 1)
        target = {"session_id": session.session_id, "entry_id": moments[0]["entry_id"]}
        responses = []
        for index, input_type in enumerate(("text", "voice")):
            response, status = await self.handlers.async_handle_ask_dj_message_payload(
                hass,
                {
                    **identity,
                    "client_message_id": f"question-{index}",
                    "text": "Vertel over deze bijdrage",
                    "language": "nl",
                    "input_type": input_type,
                    "conversation_context": {
                        "session_id": session.session_id,
                        "selected_entry": target,
                    },
                },
                headers=headers,
            )
            responses.append(response)
            self.assertEqual(status, 200, response)
            self.assertIn(moment.content, response["text"])
            self.assertEqual(response["conversation"]["input_type"], input_type)
            self.assertEqual(len(response["conversation"]["entry_ids"]), 2)
        live = session.broadcast.as_dict()
        self.assertNotIn("Vertel over deze bijdrage", str(live))
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        await self.service.async_close()
        self.service = PersistenceService(self.path, SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.queries = HistoricalProjectionQueryService(
            HistoricalProjectionRepository(self.service), history
        )
        timeline = await self.queries.async_timeline_page("profile-a", session.session_id)
        self.assertEqual(
            [e["kind"] for e in timeline["entries"]],
            [
                "playback_observed",
                "dj_moment",
                "conversation_user",
                "conversation_dj",
                "conversation_user",
                "conversation_dj",
            ],
        )
        self.assertTrue(timeline["session"]["read_only"])
        # Existing transport and exact Ask DJ historical interpreter; no static match.
        hass.data["djconnect"]["persistence_service"] = self.service
        hass.data["djconnect"].pop("session_history_query", None)
        hass.data["djconnect"]["session_runtime_manager"] = self.runtime.SessionRuntimeManager(
            PersistentSessionRepository(self.service), HistoricalProjectionRepository(self.service)
        )
        before_entries = list(timeline["entries"])
        later, status = await self.handlers.async_handle_ask_dj_message_payload(
            hass,
            {
                **identity,
                "client_message_id": "history-later",
                "text": "Wanneer heb ik eerder naar Metallica geluisterd?",
                "language": "nl",
                "conversation_context": {"session_id": None},
            },
            headers=headers,
        )
        self.assertEqual(status, 200, later)
        self.assertEqual(len(later["historical_matches"]), 1)
        opened, status = await self.handlers.async_handle_session_history_payload(
            hass,
            {**identity, "action": later["navigation_actions"][0]},
            operation="open",
            headers=headers,
        )
        self.assertEqual(status, 200, opened)
        self.assertTrue(opened["read_only"])
        self.assertEqual(
            (await self.queries.async_timeline_page("profile-a", session.session_id))["entries"],
            before_entries,
        )
        import os
        import json

        capture = os.environ.get("DJC_HISTORY_CAPTURE_DIR")
        if capture:
            Path(capture).mkdir(parents=True, exist_ok=True)
            receipt = {
                "qualification": "actual Core Runtime/storage/Ask DJ/query/handler chain with synthetic device and HA SDK/STT fixtures; not native microphone/live provider/installed HA proof",
                "session_id": session.session_id,
                "moment": moment.as_dict(),
                "text_turn": responses[0],
                "voice_derived_turn": responses[1],
                "archived_timeline": timeline,
                "later_historical_answer": later,
                "validated_open_target": opened,
                "archive_entries_unchanged": True,
            }
            (Path(capture) / "producer-receipt.json").write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False)
            )

    async def test_real_auth_denies_no_token_and_cross_profile_hint(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        response, status = await self.handlers.async_handle_session_history_payload(
            hass, dict(identity), headers={}
        )
        self.assertEqual(status, 401, response)
        response, status = await self.handlers.async_handle_session_history_payload(
            hass, {**identity, "profile_id": "profile-b"}, headers=headers
        )
        self.assertEqual(status, 403, response)

    async def test_literal_search_unicode_highlights_use_original_utf16(self):
        from custom_components.djconnect.session_history_projection import text_highlights

        marks = text_highlights("🎵 Straße Café", "STRASSE")
        self.assertEqual(marks, [{"start_utf16": 3, "length_utf16": 6}])
        self.assertEqual(
            text_highlights("Cafe\u0301", "CAFÉ"), [{"start_utf16": 0, "length_utf16": 5}]
        )

    async def test_existing_voice_completion_route_confirms_scoped_turn_and_no_store(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        page = await self.queries.async_timeline_page("profile-a", session.session_id)
        target = page["entries"][0]
        voice_headers = {
            **headers,
            "X-DJConnect-Conversation-Scope": "profile",
            "X-DJConnect-Client-Message-ID": "voice-route-1",
            "X-DJConnect-Session-ID": session.session_id,
            "X-DJConnect-Entry-ID": target["entry_id"],
            "X-DJConnect-Reference-Session-ID": session.session_id,
        }
        request = types.SimpleNamespace(headers=voice_headers, context=None)
        # Declared STT adapter fixture; route receives the actual normalized transcript.
        result = await self.http._ask_dj_voice_response(
            self.http.DJConnectSessionHistoryListView(hass),
            request,
            hass,
            runtime,
            identity["device_id"],
            "ios",
            "Vertel over deze bijdrage",
        )
        import json

        body = json.loads(result.text)
        self.assertEqual(result.status, 200, body)
        self.assertEqual(result.headers["Cache-Control"], "no-store")
        self.assertEqual(body["conversation"]["input_type"], "voice")
        self.assertEqual(body["transcript"], "Vertel over deze bijdrage")
        self.assertEqual(body["recognized_text"], body["transcript"])
