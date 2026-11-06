"""Stable owner metadata conversation retention, without transient image authority."""

from copy import deepcopy
import unittest
from unittest.mock import patch
from tests import test_captured_reply_artwork as fixtures


class CurrentMetadataHistoryTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(fixtures.CapturedReplyArtworkTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.CapturedReplyArtworkTests.tearDownClass.__func__)
    asyncSetUp = fixtures.CapturedReplyArtworkTests.asyncSetUp
    asyncTearDown = fixtures.CapturedReplyArtworkTests.asyncTearDown
    current_identification = fixtures.CapturedReplyArtworkTests.current_identification

    async def test_current_question_and_literal_answer_are_in_original_session(self):
        result, status, reads = await self.current_identification(question="Wie is dit?")
        self.assertEqual(status, 200, result)
        self.assertEqual(result["conversation"]["history_scope"], "profile", result)
        self.assertEqual(reads, ["status", "status"])
        history = await self.app.history.async_history("profile:profile-a")
        pair = [
            m
            for m in history["messages"]
            if m.get("client_message_id") == result["client_message_id"]
        ]
        self.assertEqual(len(pair), 2)
        self.assertEqual(pair[1]["text"], result["text"])
        self.assertEqual(pair[1]["images"], [])
        self.assertFalse(pair[1].get("audio_url"))
        self.assertEqual(pair[1]["playback_actions"], [])
        self.assertNotIn("reply_media_reference", str(pair))
        entries = await self.app.f.repo.async_entry_records(
            "profile-a", self.app.current.session_id
        )
        self.assertEqual(
            [e["kind"] for e in entries if e["kind"].startswith("conversation_")],
            ["conversation_user", "conversation_dj"],
        )
        self.assertEqual(len(result["conversation"]["entry_ids"]), 2)
        self.assertEqual(len(result["images"]), 1, "The live photo remains a separate short lease")
        frame = self.app.history.dialogue.owners["profile:profile-a"]["default"]
        self.assertNotIn(
            result["text"], str(frame.messages), "Retention grants no model-processing basis"
        )
        self.assertEqual(self.app.effects, [])

    async def test_changed_track_does_not_gain_history(self):
        changed = {**deepcopy(self.media), "uri": "spotify:track:" + "Z" * 22}
        result, status, _ = await self.current_identification(
            second=changed, question="Wie is dit?"
        )
        self.assertEqual(status, 409, result)
        entries = await self.app.f.repo.async_entry_records(
            "profile-a", self.app.current.session_id
        )
        self.assertFalse(any(e["kind"].startswith("conversation_") for e in entries))

    async def test_private_thread_does_not_copy_old_prose_or_unlock_other_private_turns(self):
        from unittest.mock import AsyncMock

        private_reply = AsyncMock(
            return_value={
                "success": True,
                "text": "Original RAM-only prose",
                "_private_current_context": True,
            }
        )
        with patch.object(self.app.f.handlers.http_helpers, "async_handle_ask_dj", private_reply):
            private, status = await self.app.f.handlers.async_handle_ask_dj_message_payload(
                self.hass,
                {
                    **self.app.identity,
                    "client_message_id": "original-private-source",
                    "text": "An independent musical idea",
                    "audio_response": "never",
                    "conversation_context": {"session_id": self.app.current.session_id},
                },
                headers=self.app.headers,
            )
        self.assertEqual(status, 200, private)
        self.assertFalse(private["history_persisted"])
        result, status, _ = await self.current_identification(question="Wie is dit?")
        self.assertEqual(status, 200, result)
        self.assertEqual(result["conversation"]["history_scope"], "profile")
        frame = self.app.history.dialogue.owners["profile:profile-a"]["default"]
        # A qualified independent literal read cannot grant retention to the old thread.
        self.assertFalse(frame.archiveable)
        history = await self.app.history.async_history("profile:profile-a")
        self.assertEqual(
            len(
                [
                    m
                    for m in history["messages"]
                    if m.get("client_message_id") == result["client_message_id"]
                ]
            ),
            2,
        )
        self.assertNotIn("Original RAM-only prose", str(history))

    async def test_disabled_session_history_keeps_current_reply_ephemeral(self):
        sid = self.app.current.session_id
        await self.app.f.repo._async_in_transaction(
            lambda tx: tx.execute(
                "UPDATE djconnect_persistent_sessions SET history_enabled=0 WHERE session_id=?",
                (sid,),
            )
        )
        result, status, _ = await self.current_identification(question="Wie is dit?")
        self.assertEqual(status, 200, result)
        self.assertFalse(result["history_persisted"])
        entries = await self.app.f.repo.async_entry_records("profile-a", sid)
        self.assertFalse(any(e["kind"].startswith("conversation_") for e in entries))

    async def test_real_source_withdrawal_after_archive_check_prevents_commit(self):
        from custom_components.djconnect import session_conversation

        original = session_conversation.async_metadata_archive_admission

        async def withdraw(*args, **kwargs):
            guard = await original(*args, **kwargs)
            self.app.source.disabled_by = "user"
            return guard

        with patch.object(session_conversation, "async_metadata_archive_admission", withdraw):
            result, status, _ = await self.current_identification(question="Wie is dit?")
        self.assertNotEqual(status, 200, result)
        self.assertFalse(result.get("success"))
        entries = await self.app.f.repo.async_entry_records(
            "profile-a", self.app.current.session_id
        )
        self.assertFalse(any(e["kind"].startswith("conversation_") for e in entries))
        self.assertEqual(self.app.effects, [])

    async def test_wire_or_model_dictionary_cannot_mint_metadata_archive_admission(self):
        from unittest.mock import AsyncMock

        bogus = {
            "uri": self.media["uri"],
            "text": "Unqualified copied text",
            "source_binding": self.source,
        }
        delegate = AsyncMock(
            return_value={
                "success": True,
                "text": bogus["text"],
                "_private_current_context": True,
                "current_metadata_history": bogus,
            }
        )
        with patch.object(self.app.f.handlers.http_helpers, "async_handle_ask_dj", delegate):
            result, status = await self.app.f.handlers.async_handle_ask_dj_message_payload(
                self.hass,
                {
                    **self.app.identity,
                    "client_message_id": "fake-wire-admission",
                    "text": "A musical thought",
                    "audio_response": "never",
                    "current_metadata_history": bogus,
                    "conversation_context": {"session_id": self.app.current.session_id},
                },
                headers=self.app.headers,
            )
        self.assertEqual(status, 200, result)
        self.assertFalse(result["history_persisted"])
        entries = await self.app.f.repo.async_entry_records(
            "profile-a", self.app.current.session_id
        )
        self.assertFalse(any(e["kind"].startswith("conversation_") for e in entries))

    async def test_provider_runtime_epoch_withdrawal_is_a_strict_archive_denial(self):
        from custom_components.djconnect import session_conversation

        original = session_conversation.async_metadata_archive_admission

        async def retire_original_runtime(*args, **kwargs):
            guard = await original(*args, **kwargs)
            self.app.provider._receiver_end_generation += 1
            return guard

        with patch.object(
            session_conversation, "async_metadata_archive_admission", retire_original_runtime
        ):
            result, status, _ = await self.current_identification(question="Wie is dit?")
        self.assertNotEqual(status, 200, result)
        entries = await self.app.f.repo.async_entry_records(
            "profile-a", self.app.current.session_id
        )
        self.assertFalse(any(e["kind"].startswith("conversation_") for e in entries))

    async def test_provider_epoch_withdrawal_during_store_ack_rolls_back_both_stores(self):
        original = self.app.history._store.async_save
        changed = False

        async def acknowledge_then_withdraw(data):
            nonlocal changed
            await original(data)
            messages = data.get("users", {}).get("profile:profile-a", {}).get("messages", [])
            if not changed and any(
                m.get("client_message_id", "").startswith("current-identification-art-")
                for m in messages
            ):
                changed = True
                self.app.provider._receiver_end_generation += 1

        with patch.object(self.app.history._store, "async_save", acknowledge_then_withdraw):
            result, status, _ = await self.current_identification(question="Wie is dit?")
        self.assertTrue(changed)
        self.assertNotEqual(status, 200, result)
        entries = await self.app.f.repo.async_entry_records(
            "profile-a", self.app.current.session_id
        )
        self.assertFalse(any(e["kind"].startswith("conversation_") for e in entries))
        stored = await self.app.history._store.async_load()
        messages = stored.get("users", {}).get("profile:profile-a", {}).get("messages", [])
        self.assertFalse(
            any(
                m.get("client_message_id", "").startswith("current-identification-art-")
                for m in messages
            )
        )
