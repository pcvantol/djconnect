from __future__ import annotations

import asyncio
import importlib
import types
import unittest

from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()
AskDJHistoryManager = importlib.import_module(
    "custom_components.djconnect.ask_dj_history"
).AskDJHistoryManager
api_handlers = importlib.import_module("custom_components.djconnect.api_handlers")


class FakeStore:
    def __init__(self, data=None):
        self.data = data
        self.saved = None

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.saved = data
        self.data = data


class AskDJHistoryManagerTest(unittest.TestCase):
    def test_history_is_user_scoped_and_shared_by_clients(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            first = await manager.async_append_exchange(
                "ha-user-1",
                {
                    "client_message_id": "watch-1",
                    "client_id": "watch",
                    "client_type": "watchos",
                    "text": "Draai iets rustigers",
                },
                {"success": True, "dj_text": "Ik kies iets rustigers."},
            )
            second_client = await manager.async_history("ha-user-1")
            other_user = await manager.async_history("ha-user-2")
            return first, second_client, other_user

        first, second_client, other_user = asyncio.run(run())

        self.assertEqual(first["history_revision"], 1)
        self.assertEqual(len(second_client["messages"]), 2)
        self.assertEqual(second_client["messages"][0]["client_id"], "watch")
        self.assertEqual(other_user["messages"], [])
        self.assertEqual(other_user["history_revision"], 0)

    def test_history_export_handler_returns_backend_envelope(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())
        runtime = types.SimpleNamespace(
            ask_dj_history=manager,
            device_status={"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
            client_type=lambda: "ios",
        )
        original_resolve_runtime = api_handlers.resolve_runtime
        original_authorize = api_handlers.authorize_runtime_device_request
        api_handlers.resolve_runtime = lambda hass, device_id, headers=None: runtime
        api_handlers.authorize_runtime_device_request = (
            lambda runtime_arg, headers, device_id=None, client_type=None: True
        )

        async def run():
            await manager.async_append_exchange(
                "ha-user-1",
                {
                    "client_message_id": "ios-1",
                    "client_id": "ios",
                    "client_type": "ios",
                    "text": "Wat speelde ik net?",
                },
                {"success": True, "dj_text": "Je luisterde net naar Intro."},
            )
            return await api_handlers.async_handle_ask_dj_history_export_payload(
                types.SimpleNamespace(data={}),
                {
                    "identity": {
                        "device_id": "djconnect-ios-ABCDEFGHIJKL",
                        "client_type": "ios",
                        "device_name": "iPhone",
                    },
                    "app_version": "3.2.21",
                },
                headers={"Authorization": "Bearer token"},
                user_id="ha-user-1",
            )

        try:
            result, status = asyncio.run(run())
        finally:
            api_handlers.resolve_runtime = original_resolve_runtime
            api_handlers.authorize_runtime_device_request = original_authorize

        self.assertEqual(status, 200)
        self.assertTrue(result["success"])
        self.assertEqual(result["format"], "djconnect.ask_dj.history.export")
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["exported_by_client_type"], "ios")
        self.assertEqual(result["app_version"], "3.2.21")
        self.assertEqual(result["user_id"], "ha-user-1")
        self.assertEqual(result["history_revision"], 1)
        self.assertEqual(result["clear_revision"], 0)
        self.assertEqual(result["history_limit"], 1000)
        self.assertIn("exported_at", result)
        self.assertEqual(len(result["messages"]), 2)
        self.assertEqual(result["messages"][0]["text"], "Wat speelde ik net?")

    def test_unauthorized_history_export_is_rejected(self) -> None:
        runtime = types.SimpleNamespace(
            ask_dj_history=AskDJHistoryManager(store=FakeStore()),
            device_status={"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
            client_type=lambda: "ios",
        )
        original_resolve_runtime = api_handlers.resolve_runtime
        original_authorize = api_handlers.authorize_runtime_device_request
        api_handlers.resolve_runtime = lambda hass, device_id, headers=None: runtime
        api_handlers.authorize_runtime_device_request = (
            lambda runtime_arg, headers, device_id=None, client_type=None: False
        )

        try:
            result, status = asyncio.run(
                api_handlers.async_handle_ask_dj_history_export_payload(
                    types.SimpleNamespace(data={}),
                    {"device_id": "djconnect-ios-ABCDEFGHIJKL", "client_type": "ios"},
                    headers={"Authorization": "Bearer wrong"},
                    user_id="ha-user-1",
                )
            )
        finally:
            api_handlers.resolve_runtime = original_resolve_runtime
            api_handlers.authorize_runtime_device_request = original_authorize

        self.assertEqual(status, 401)
        self.assertEqual(result["error"], "unauthorized")

    def test_clear_increments_revisions_for_only_one_user(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            await manager.async_append_exchange(
                "ha-user-1",
                {"client_message_id": "1", "client_id": "ios", "client_type": "ios", "text": "Hoi"},
                {"success": True, "dj_text": "Hoi terug."},
            )
            await manager.async_append_exchange(
                "ha-user-2",
                {"client_message_id": "2", "client_id": "mac", "client_type": "macos", "text": "Hoi"},
                {"success": True, "dj_text": "Hoi terug."},
            )
            cleared = await manager.async_clear("ha-user-1")
            user_one = await manager.async_history("ha-user-1")
            user_two = await manager.async_history("ha-user-2")
            return cleared, user_one, user_two

        cleared, user_one, user_two = asyncio.run(run())

        self.assertEqual(cleared["history_revision"], 2)
        self.assertEqual(cleared["clear_revision"], 1)
        self.assertTrue(cleared["cleared"])
        self.assertTrue(cleared["ask_dj_clear_required"])
        self.assertEqual(cleared["messages"], [])
        self.assertEqual(user_one["messages"], [])
        self.assertEqual(len(user_two["messages"]), 2)

    def test_clear_all_sets_global_clear_revision_for_other_users(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            await manager.async_append_exchange(
                "mac-user",
                {"client_message_id": "1", "client_id": "mac", "client_type": "macos", "text": "Hoi"},
                {"success": True, "dj_text": "Hoi terug."},
            )
            cleared = await manager.async_clear_all()
            iphone_history = await manager.async_history("iphone-user")
            return cleared, iphone_history, manager.data

        cleared, iphone_history, data = asyncio.run(run())

        self.assertEqual(cleared["user_id"], "all")
        self.assertEqual(cleared["clear_revision"], 1)
        self.assertTrue(cleared["cleared"])
        self.assertTrue(cleared["ask_dj_clear_required"])
        self.assertEqual(cleared["messages"], [])
        self.assertEqual(iphone_history["user_id"], "iphone-user")
        self.assertEqual(iphone_history["clear_revision"], 1)
        self.assertEqual(iphone_history["messages"], [])
        self.assertEqual(data["global_clear_revision"], 1)

    def test_duplicate_client_message_id_returns_existing_exchange(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            first = await manager.async_append_exchange(
                "ha-user-1",
                {"client_message_id": "retry-1", "client_id": "ios", "client_type": "ios", "text": "Verras me"},
                {"success": True, "dj_text": "Ik heb iets gevonden."},
            )
            second = await manager.async_append_exchange(
                "ha-user-1",
                {"client_message_id": "retry-1", "client_id": "ios", "client_type": "ios", "text": "Verras me"},
                {"success": True, "dj_text": "Deze zou dubbel zijn."},
            )
            history = await manager.async_history("ha-user-1")
            return first, second, history

        first, second, history = asyncio.run(run())

        self.assertEqual(first["history_revision"], 1)
        self.assertTrue(second["deduplicated"])
        self.assertEqual(second["history_revision"], 1)
        self.assertEqual(len(history["messages"]), 2)
        self.assertEqual(second["assistant_message"]["text"], "Ik heb iets gevonden.")

    def test_assistant_message_keeps_rich_payload(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            result = await manager.async_append_exchange(
                "ha-user-1",
                {"client_message_id": "rich-1", "client_id": "mac", "client_type": "macos", "text": "Tips?"},
                {
                    "success": True,
                    "dj_text": "Deze drie passen goed.",
                    "images": [{"url": "/api/djconnect/image_proxy/abc", "title": "Cover"}],
                    "links": [{"url": "https://example.test", "title": "Bron", "kind": "source"}],
                    "sources": [{"source": "spotify_top_tracks_short_term", "kind": "source"}],
                    "audio_url": "/api/djconnect/tts/123.mp3",
                    "playback_actions": [
                        {
                            "id": "spotify:track:123",
                            "uri": "spotify:track:123",
                            "kind": "track",
                            "title": "Track",
                        }
                    ],
                },
            )
            return result["assistant_message"]

        message = asyncio.run(run())

        self.assertEqual(message["audio_url"], "/api/djconnect/tts/123.mp3")
        self.assertEqual(message["images"][0]["url"], "/api/djconnect/image_proxy/abc")
        self.assertEqual(message["links"][0]["kind"], "source")
        self.assertEqual(message["sources"][0]["source"], "spotify_top_tracks_short_term")
        self.assertEqual(message["playback_actions"][0]["uri"], "spotify:track:123")
        self.assertEqual(message["message_kind"], "assistant")

    def test_assistant_only_message_appends_without_user_bubble(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            await manager.async_append_exchange(
                "ha-user-1",
                {"client_message_id": "1", "client_id": "ios", "client_type": "ios", "text": "Hoi"},
                {"success": True, "dj_text": "Hoi terug."},
            )
            result = await manager.async_append_assistant_message(
                None,
                {"client_message_id": "ambient:radiohead|ok-computer", "client_id": "server"},
                {
                    "success": True,
                    "dj_text": "Leuk feitje over OK Computer.",
                    "intent": {"category": "informational", "intent": "ambient_music_fact"},
                    "action": "none",
                    "message_kind": "system",
                    "origin": "spotify_playback_context",
                    "sources": [{"source": "spotify_playback_context", "kind": "source"}],
                },
            )
            history = await manager.async_history("ha-user-1")
            return result, history

        result, history = asyncio.run(run())

        self.assertEqual(result["assistant_message"]["role"], "assistant")
        self.assertEqual(len(history["messages"]), 3)
        self.assertEqual(history["messages"][-1]["role"], "assistant")
        self.assertEqual(history["messages"][-1]["message_kind"], "system")
        self.assertEqual(history["messages"][-1]["origin"], "spotify_playback_context")
        self.assertEqual(history["messages"][-1]["text"], "Leuk feitje over OK Computer.")
        self.assertEqual(history["messages"][-1]["client_message_id"], "ambient:radiohead|ok-computer")
        self.assertIsNone(history["messages"][-1]["audio_url"])

    def test_assistant_only_message_dedupes_client_message_id(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            first = await manager.async_append_assistant_message(
                "ha-user-1",
                {"client_message_id": "ambient:pitbull|planet-pit", "client_id": "server"},
                {
                    "success": True,
                    "dj_text": "Eerste feitje.",
                    "intent": {"category": "informational", "intent": "ambient_music_fact"},
                    "message_kind": "system",
                    "origin": "spotify_playback_context",
                },
            )
            second = await manager.async_append_assistant_message(
                "ha-user-1",
                {"client_message_id": "ambient:pitbull|planet-pit", "client_id": "server"},
                {
                    "success": True,
                    "dj_text": "Tweede feitje dat niet in de chat mag komen.",
                    "intent": {"category": "informational", "intent": "ambient_music_fact"},
                    "message_kind": "system",
                    "origin": "spotify_playback_context",
                },
            )
            has_message = await manager.async_has_client_message_id(
                "ha-user-1",
                "ambient:pitbull|planet-pit",
            )
            history = await manager.async_history("ha-user-1")
            return first, second, has_message, history

        first, second, has_message, history = asyncio.run(run())

        self.assertEqual(first["history_revision"], 1)
        self.assertTrue(second["deduplicated"])
        self.assertEqual(second["history_revision"], 1)
        self.assertTrue(has_message)
        self.assertEqual(len(history["messages"]), 1)
        self.assertEqual(history["messages"][0]["text"], "Eerste feitje.")

    def test_history_limit_trims_and_adds_retention_system_message(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            for index in range(501):
                await manager.async_append_exchange(
                    "ha-user-1",
                    {
                        "client_message_id": f"message-{index}",
                        "client_id": "ios",
                        "client_type": "ios",
                        "text": f"Vraag {index}",
                    },
                    {"success": True, "dj_text": f"Antwoord {index}"},
                )
            return await manager.async_history("ha-user-1")

        history = asyncio.run(run())

        self.assertEqual(history["history_limit"], 1000)
        self.assertEqual(len(history["messages"]), 1000)
        self.assertEqual(history["history_trimmed_count"], 3)
        self.assertIsNotNone(history["history_trimmed_before"])
        self.assertEqual(history["messages"][-1]["role"], "assistant")
        self.assertEqual(history["messages"][-1]["message_kind"], "system")
        self.assertEqual(history["messages"][-1]["origin"], "history_retention")
        self.assertEqual(
            history["messages"][-1]["intent"],
            {"category": "system", "intent": "history_limit_reached"},
        )
        self.assertEqual(history["messages"][-1]["action"], "none")
        self.assertIsNone(history["messages"][-1]["audio_url"])
        self.assertIn("limiet van 1000 berichten", history["messages"][-1]["text"])

    def test_history_limit_retention_message_is_not_spammed_on_consecutive_trims(self) -> None:
        manager = AskDJHistoryManager(store=FakeStore())

        async def run():
            for index in range(502):
                await manager.async_append_exchange(
                    "ha-user-1",
                    {
                        "client_message_id": f"message-{index}",
                        "client_id": "ios",
                        "client_type": "ios",
                        "text": f"Vraag {index}",
                    },
                    {"success": True, "dj_text": f"Antwoord {index}"},
                )
            return await manager.async_history("ha-user-1")

        history = asyncio.run(run())

        retention_messages = [
            message
            for message in history["messages"]
            if message.get("origin") == "history_retention"
        ]
        self.assertEqual(len(retention_messages), 1)
        self.assertEqual(history["history_trimmed_count"], 5)
        self.assertEqual(len(history["messages"]), 1000)


if __name__ == "__main__":
    unittest.main()
