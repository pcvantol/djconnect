"""Original list retention and real owner/Store/SQL/HTTP boundaries; no provider effects."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import hashlib
import unittest
from unittest.mock import patch

KEY = "recent_history_presentation"


def presentation():
    return {"schema_version": 1, "item_type": "tracks", "caption": "Original recent-list heading:",
            "omitted_count": 0, "items": [
                {"item_id": "recent-0", "kind": "track", "title": "Original recording",
                 "subtitle": "Original performer", "played_at": "2026-11-01T15:00:00+00:00"}]}


def response():
    return {"success": True, "text": "Original recent-list heading:\n- Original performer - Original recording",
            "intent": {"intent": "recently_played_history", "action": "recently_played", "item_type": "tracks"},
            KEY: presentation()}


class RecentDisplayHistoryTests(unittest.IsolatedAsyncioTestCase):
    def test_current_actual_ha_original_receipt_matches_display_and_all_products(self):
        from custom_components.djconnect.ask_dj.recent_presentation import checked
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root/'examples/client_contracts/ask_dj_recent_list_presentation_v1/actual-ha-wire.json').read_bytes())
        self.assertEqual(fixture['classification'], 'ACTUAL_ISOLATED_HA_SOURCE_ONLY_NOT_INSTALLED_OR_NATIVE')
        self.assertEqual(len(fixture['source_pins']), 302)
        for name, digest in fixture['source_pins'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((root/fixture['harness']).read_bytes()).hexdigest(), fixture['harness_sha256'])
        extension = fixture['original_receipt']['extension']
        self.assertTrue(all(v == 'PASS' for v in extension['cases'].values()))
        self.assertEqual(extension['effect_count'], 0)
        self.assertEqual(extension['model_provider_calls'], 0)
        self.assertEqual(extension['example'], checked(fixture['example']))
        self.assertEqual((fixture['installed'], fixture['native']), ('NOT_RUN', 'NOT_RUN'))

    async def test_original_display_survives_saved_exchange_reload_and_clear(self):
        from tests.test_ask_dj_history import AskDJHistoryManager, FakeStore
        store = FakeStore()
        manager = AskDJHistoryManager(store=store)
        turn = {"turn_id": "original-turn", "context": {}, "provider_display_source": {
            "provider": "Spotify", "source_context": {"backend_id": "synthetic-original-source"}}}
        result = await manager.async_append_exchange("profile:a", {"client_message_id": "list-1", "text": "Recent?"},
                                                     response(), session_turn=turn)
        self.assertEqual(result["assistant_message"].get(KEY), presentation())
        await manager.async_append_exchange("profile:b", {"client_message_id": "list-1", "text": "Other?"},
                                            {"success": True, "text": "Other reply"})
        reread = AskDJHistoryManager(store=store)
        original = await reread.async_saved_exchange("profile:a", "list-1")
        self.assertEqual(original["assistant_message"].get(KEY), presentation())
        self.assertEqual(original["assistant_message"]["id"], result["assistant_message"]["id"])
        await reread.async_clear("profile:a")
        self.assertEqual((await reread.async_history("profile:a"))["messages"], [])
        self.assertEqual(len((await reread.async_history("profile:b"))["messages"]), 2)

    async def test_legacy_or_missing_source_never_retains_display(self):
        from tests.test_ask_dj_history import AskDJHistoryManager, FakeStore
        manager = AskDJHistoryManager(store=FakeStore())
        for ordinal, turn in enumerate((None, {"turn_id": "unbound", "context": {}})):
            result = await manager.async_append_exchange("profile:a", {"client_message_id": str(ordinal), "text": "Recent?"},
                                                         response(), session_turn=turn)
            self.assertNotIn(KEY, result["assistant_message"])

    def test_closed_display_rejects_actions_media_unknowns_and_bad_bounds(self):
        from custom_components.djconnect.ask_dj.recent_presentation import checked, from_response
        value = presentation()
        self.assertEqual(checked(value), value)
        changed = [dict(value, schema_version=True), dict(value, omitted_count=True),
                   dict(value, omitted_count=51), dict(value, caption="bad\ncaption"),
                   dict(value, item_type="unknown"), dict(value, items=[]),
                   dict(value, items=value["items"]*11), dict(value, playback_actions=[])]
        for field in ("uri", "value", "action_id", "image_url", "thumbnail_url", "expires_at", "played_at_label"):
            changed.append(dict(value, items=[{**value["items"][0], field: "must-not-escape"}]))
        for field, bad in (("title", "x"*513), ("title", "control\x00"), ("title", "\ud800"), ("item_id", "recent-9"),
                           ("played_at", "2026-11-01T15:00:00"), ("played_at", "not-a-date"),
                           ("played_at", "9999-12-31T23:59:59-23:59")):
            changed.append(dict(value, items=[{**value["items"][0], field: bad}]))
        for candidate in changed:
            with self.subTest(candidate=candidate):
                self.assertIsNone(checked(candidate))
        self.assertIsNone(from_response({**response(), "success": False}))
        self.assertIsNone(from_response({**response(), "intent": {"intent": "other"}}))
        oversized = dict(value, items=[{**value["items"][0], "item_id": "recent-"+str(i),
                          "title": "😀"*512, "subtitle": "😀"*512} for i in range(10)])
        self.assertIsNone(checked(oversized))

    def test_same_track_occurrences_keep_original_ordinals_and_timestamps_without_media(self):
        from custom_components.djconnect.ask_dj.recent_presentation import build
        original = {"kind": "track", "title": "Same recording", "uri": "spotify:track:"+"A"*22,
                    "image_url": "/expired-image", "played_at": "2026-11-01T16:00:00+01:00"}
        value = build([original, {**original, "played_at": "2026-11-01T16:05:00+01:00"}], "tracks", "Heading:", 2)
        self.assertEqual([v["item_id"] for v in value["items"]], ["recent-0", "recent-1"])
        self.assertEqual([v["played_at"] for v in value["items"]],
                         ["2026-11-01T15:00:00+00:00", "2026-11-01T15:05:00+00:00"])
        self.assertNotIn("uri", json.dumps(value))
        self.assertNotIn("image_url", json.dumps(value))
        value["items"][0]["title"] = "Changed projection"
        self.assertEqual(original["title"], "Same recording")
        self.assertIsNone(build([{**original, "played_at": "9999-12-31T23:59:59-23:59"}], "tracks", "Heading:", 0))
        self.assertIsNone(build([{**original, "title": "\ud800"}], "tracks", "Heading:", 0))


class RecentDisplayApplicationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        from tests import test_history_playback_application as application
        cls.application = application
        application.HistoricalPlaybackApplicationTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.application.HistoricalPlaybackApplicationTests.tearDownClass()

    async def asyncSetUp(self):
        self.app = self.application.HistoricalPlaybackApplicationTests()
        await self.app.asyncSetUp()
        self.calls = []

    async def asyncTearDown(self):
        await self.app.asyncTearDown()

    async def request_list(self):
        app = self.app
        stamp = datetime.now(UTC) - timedelta(minutes=5)
        async def backend(hass, runtime, command, *args, **kwargs):
            self.calls.append(command)
            if command == "status":
                return {"success": True, "playback": {}}
            if command == "recently_played":
                return {"success": True, "tracks": [
                    {"track_name": "Original recording", "artist": "Original performer",
                     "uri": "spotify:track:"+"A"*22, "played_at": stamp.isoformat()},
                    {"track_name": "Original recording", "artist": "Original performer",
                     "uri": "spotify:track:"+"A"*22, "played_at": (stamp-timedelta(minutes=4)).isoformat()}]}
            raise AssertionError("Read-only recent question attempted effect: " + command)
        with patch.object(app.core, "run_music_command", backend):
            result, status = await app.f.handlers.async_handle_ask_dj_message_payload(
                app.hass, {**app.identity, "text": "Welke nummers heb ik afgelopen uur afgespeeld?",
                    "language": "nl", "audio_response": "never", "client_message_id": "original-recent-list",
                    "conversation_context": {"session_id": app.current.session_id}}, headers=app.headers)
        self.assertEqual(status, 200, result)
        return result

    async def test_paired_list_survives_minute_lease_end_store_reload_and_session_end(self):
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
        from custom_components.djconnect.session_conversation import query_service
        app = self.app
        result = await self.request_list()
        display = result[KEY]
        self.assertEqual(result["assistant_message"][KEY], display)
        self.assertEqual(len(display["items"]), 2)
        self.assertNotEqual(*[v["item_id"] for v in display["items"]])
        self.assertEqual(display["caption"], "Dit heb je het afgelopen uur afgespeeld:")
        self.assertNotIn("- Original", display["caption"])
        self.assertIn("Original recording", result["text"])
        self.assertFalse(result["playback_actions"])
        self.assertNotIn("provider_display_source", json.dumps(result))
        saved = await app.history.async_saved_exchange("profile:profile-a", "original-recent-list")
        self.assertEqual(saved["assistant_message"][KEY], display)
        self.assertFalse(saved["assistant_message"]["playback_actions"])
        self.assertFalse(saved["assistant_message"]["images"])
        # Expire only operational RAM, never renew original source/response leases.
        app.history.dialogue.clock = lambda: 10**12
        reread = AskDJHistoryManager(store=app.history._store)
        await reread.async_load()
        app.runtime.ask_dj_history = reread
        app.hass.data["djconnect"]["ask_dj_history_manager"] = reread
        await app.f.manager.async_end(owner_profile_id="profile-a", session_id=app.current.session_id)
        page = await query_service(app.hass, reread).async_timeline_page("profile-a", app.current.session_id)
        entry = next(e for e in page["entries"] if e.get("origin_message_id") == saved["assistant_message"]["id"])
        self.assertEqual(entry[KEY], display)
        self.assertNotIn("playback_actions", entry)
        history, status = await app.f.handlers.async_handle_ask_dj_history_payload(app.hass, app.identity, headers=app.headers)
        self.assertEqual(status, 200, history)
        original = next(m for m in history["messages"] if m["id"] == saved["assistant_message"]["id"])
        self.assertEqual(original[KEY], display)
        self.assertNotIn("provider_display_source", json.dumps(history))
        self.assertTrue(all(c in {"status", "recently_played"} for c in self.calls))

    async def test_source_withdrawal_redacts_cards_and_caption_on_http_and_timeline(self):
        from custom_components.djconnect.session_conversation import query_service
        app = self.app
        result = await self.request_list()
        identifier = result["assistant_message"]["id"]
        query = query_service(app.hass, app.history)
        before = await query.async_timeline_page("profile-a", app.current.session_id)
        original_entry = next(e for e in before["entries"] if e.get("origin_message_id") == identifier)
        app.source.disabled_by = "user"
        history, status = await app.f.handlers.async_handle_ask_dj_history_payload(app.hass, app.identity, headers=app.headers)
        self.assertEqual(status, 200, history)
        message = next(m for m in history["messages"] if m["id"] == identifier)
        self.assertFalse(message.get(KEY))
        self.assertFalse(message["text"])
        page = await query_service(app.hass, app.history).async_timeline_page("profile-a", app.current.session_id)
        entry = next(e for e in page["entries"] if e["entry_id"] == original_entry["entry_id"])
        self.assertNotIn(KEY, entry)
        self.assertEqual(entry["state"], "source_withdrawn")

    async def test_missing_original_source_is_not_requalified_from_label(self):
        from custom_components.djconnect.session_conversation import query_service
        app = self.app
        await self.request_list()
        message = (await app.history.async_saved_exchange("profile:profile-a", "original-recent-list"))["assistant_message"]
        message["session_turn"].pop("provider_display_source")
        self.assertFalse(await query_service(app.hass, app.history).async_conversation_source_visible("profile-a", message))

    async def test_boolean_original_authority_loss_cannot_be_archived(self):
        from custom_components.djconnect.ask_dj import service
        from custom_components.djconnect import reply_artwork
        app = self.app
        # The independent capture callback is an explicit boolean fixture here;
        # the paired request above separately exercises the real source owner.
        source = {"backend_id": "source-spotify", "music_account_id": "source-account",
                  "provider_entry_id": "source-entry", "provider_account_id": "provider-original"}
        allowed = True
        def original():
            return allowed
        self.assertIs(original(), True)
        async def delegate(*args):
            nonlocal allowed
            # A receiver/owner callback can close without an account revision.
            # Archive admission must not ignore its original False result.
            allowed = False
            self.assertIs(original(), False)
            return deepcopy(response())
        async def owner():
            pass
        with self.assertRaises(PermissionError), patch.object(reply_artwork, "source_admission", return_value=(source, original)):
            await service.async_exchange(app.hass, app.runtime,
                {"text": "Welke nummers heb ik afgelopen uur afgespeeld?", "client_message_id": "false-original"},
                profile_id="profile-a", history_manager=app.history, delegate=delegate, validate_owner=owner)
        self.assertIsNone(await app.history.async_saved_exchange("profile:profile-a", "false-original"))

    async def test_original_authority_loss_during_store_save_rolls_back_display(self):
        from custom_components.djconnect.ask_dj import service
        from custom_components.djconnect import reply_artwork
        app = self.app
        source = {"backend_id": "source-spotify", "music_account_id": "source-account",
                  "provider_entry_id": "source-entry", "provider_account_id": "provider-original"}
        allowed = True
        def original():
            return allowed
        async def delegate(*args):
            return deepcopy(response())
        async def owner():
            pass
        save = app.history._store.async_save
        async def withdrawn_after_save(data):
            nonlocal allowed
            await save(data)
            allowed = False
        with patch.object(reply_artwork, "source_admission", return_value=(source, original)), patch.object(
                app.history._store, "async_save", withdrawn_after_save), self.assertRaises(PermissionError):
            await service.async_exchange(app.hass, app.runtime,
                {"text": "Welke nummers heb ik afgelopen uur afgespeeld?", "client_message_id": "false-post-save"},
                profile_id="profile-a", history_manager=app.history, delegate=delegate, validate_owner=owner)
        self.assertIsNone(await app.history.async_saved_exchange("profile:profile-a", "false-post-save"))

    async def test_live_display_is_not_an_archive_grant(self):
        from custom_components.djconnect import reply_artwork
        app = self.app
        with patch.object(reply_artwork, "source_admission", return_value=(None, None)):
            result = await self.request_list()
        self.assertIn(KEY, result)
        self.assertIn(KEY, result["assistant_message"])
        saved = await app.history.async_saved_exchange("profile:profile-a", "original-recent-list")
        self.assertNotIn(KEY, saved["assistant_message"])
