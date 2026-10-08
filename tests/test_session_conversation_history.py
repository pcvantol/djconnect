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

    async def test_revoked_source_withdraws_match_and_copied_answer(self):
        from custom_components.djconnect.domain.music_account import MusicAccountKind
        from custom_components.djconnect.session_history_maintenance import (
            async_maintain_session_history,
        )

        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        response, status = await self.handlers.async_handle_session_history_payload(
            hass,
            {**identity, "session_id": session.session_id},
            operation="timeline",
            headers=headers,
        )
        self.assertEqual(status, 200)
        target = {"session_id": session.session_id, "entry_id": response["entries"][0]["entry_id"]}
        response, status = await self.handlers.async_handle_ask_dj_message_payload(
            hass,
            {
                **identity,
                "client_message_id": "copied",
                "text": "Vertel over deze bijdrage",
                "conversation_context": {
                    "session_id": session.session_id,
                    "selected_entry": target,
                },
            },
            headers=headers,
        )
        self.assertEqual(status, 200, response)
        self.assertIn("Metallica", response["text"])
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        storage = hass.data["djconnect"]["djconnect_profile_platform"]
        await storage.async_upsert_music_account(
            "source-account",
            "source-spotify",
            kind=MusicAccountKind.PERSONAL,
            display_name="Synthetic source account",
            linked_profile_ids=frozenset(),
        )
        response, status = await self.handlers.async_handle_session_history_payload(
            hass,
            {**identity, "action": {"kind": "open_session", **target}},
            operation="open",
            headers=headers,
        )
        self.assertEqual(status, 404, response)
        response, status = await self.handlers.async_handle_session_history_payload(
            hass,
            {**identity, "session_id": session.session_id, "q": "Metallica"},
            operation="search",
            headers=headers,
        )
        self.assertEqual(response["matches"], [])
        await async_maintain_session_history(hass)
        self.assertIsNone(await self.repo.async_entry_record("profile-a", **target))
        self.assertEqual((await history.async_history("profile:profile-a"))["messages"], [])

    async def test_expiry_between_find_and_open_rejects_original_anchor(self):
        from datetime import UTC, datetime, timedelta
        from custom_components.djconnect.historical_projection_retention import (
            HistoricalProjectionRetentionService,
        )

        session = await self.observed_session()
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        result = await self.queries.async_find_playback("profile-a", artist="Metallica")
        target = result["matches"][0]["open_action"]
        future = datetime.now(UTC) + timedelta(days=91)
        await HistoricalProjectionRetentionService(self.repo).async_cleanup(now=future)
        with self.assertRaises(PermissionError):
            await self.queries.async_open_entry(
                "profile-a", target["session_id"], target["entry_id"]
            )
        self.assertEqual((await self.queries.async_session_page("profile-a"))["sessions"], [])
        self.assertIsNone(
            await self.repo.async_entry_record(
                "profile-a", target["session_id"], target["entry_id"]
            )
        )

    async def test_mention_without_playback_has_no_historical_match(self):
        session = await self.manager.async_start(owner_profile_id="profile-a")
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        result = await self.queries.async_find_playback("profile-a", artist="Metallica")
        self.assertEqual(result["matches"], [])
        self.assertFalse(result["full_listens_proven"])

    async def test_duplicate_context_submit_has_one_turn_and_conflict_fails(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        payload = {
            **identity,
            "client_message_id": "same",
            "text": "Wanneer heb ik naar Metallica geluisterd?",
            "conversation_context": {"session_id": session.session_id},
        }
        first, status = await self.handlers.async_handle_ask_dj_message_payload(
            hass, dict(payload), headers=headers
        )
        self.assertEqual(status, 200, first)
        second, status = await self.handlers.async_handle_ask_dj_message_payload(
            hass, dict(payload), headers=headers
        )
        self.assertEqual(status, 200, second)
        self.assertEqual(first["conversation"]["entry_ids"], second["conversation"]["entry_ids"])
        self.assertEqual(len((await history.async_history("profile:profile-a"))["messages"]), 2)
        conflict, status = await self.handlers.async_handle_ask_dj_message_payload(
            hass, {**payload, "text": "When have I listened to another artist?"}, headers=headers
        )
        self.assertEqual(status, 409, conflict)

    async def test_late_privacy_change_during_delegate_persists_nothing(self):
        import asyncio
        from custom_components.djconnect.session_conversation import (
            async_session_exchange,
            SessionConversationError,
        )

        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        entered = asyncio.Event()
        release = asyncio.Event()
        allowed = True

        async def delegate(*args):
            entered.set()
            await release.wait()
            return {"success": True, "text": "Synthetic reply"}

        async def guard():
            if not allowed:
                raise SessionConversationError("history_not_allowed", 403)

        pending = asyncio.create_task(
            async_session_exchange(
                hass,
                runtime,
                {
                    "client_message_id": "late",
                    "text": "Question",
                    "conversation_context": {"session_id": session.session_id},
                },
                profile_id="profile-a",
                history_manager=history,
                delegate=delegate,
                validate_owner=guard,
            )
        )
        await entered.wait()
        allowed = False
        release.set()
        with self.assertRaises(SessionConversationError):
            await pending
        self.assertEqual((await history.async_history("profile:profile-a"))["messages"], [])
        self.assertEqual(
            len(await self.repo.async_entry_records("profile-a", session.session_id)), 1
        )

    async def test_terminal_write_failure_rolls_back_archive_and_keeps_runtime(self):
        session = await self.observed_session()
        original = self.repo._project_terminal_tx

        def fail(tx, stored):
            original(tx, stored)
            raise RuntimeError("synthetic archive transaction failure")

        self.repo._project_terminal_tx = fail
        try:
            with self.assertRaises(RuntimeError):
                await self.manager.async_end(
                    owner_profile_id="profile-a", session_id=session.session_id
                )
        finally:
            self.repo._project_terminal_tx = original
        self.assertIsNotNone(await self.manager.async_get_active("profile-a"))
        self.assertEqual(
            (await self.repo.async_session_record(session.session_id))["lifecycle_status"], "ACTIVE"
        )
        self.assertIsNone(await self.repo.async_get_session_for_originating_id(session.session_id))
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        self.assertIsNotNone(
            await self.repo.async_get_session_for_originating_id(session.session_id)
        )

    async def test_session_keyset_reaches_beyond_old_fixed_window(self):
        for i in range(502):
            session = await self.manager.async_start(owner_profile_id="profile-a")
            await self.manager.async_end(
                owner_profile_id="profile-a", session_id=session.session_id
            )
        cursor = ""
        identifiers = []
        while True:
            page = await self.queries.async_session_page("profile-a", limit=50, cursor=cursor)
            identifiers.extend(row["session_id"] for row in page["sessions"])
            cursor = page["next_cursor"]
            if not cursor:
                break
        self.assertEqual(len(identifiers), 502)
        self.assertEqual(len(set(identifiers)), 502)

    async def test_cancelled_acceptance_finishes_store_and_references_before_end(self):
        import asyncio
        from unittest.mock import patch

        for boundary in ("store", "sqlite"):
            with self.subTest(boundary=boundary):
                hass, runtime, history, identity, headers = await self.transport_fixture()
                session = await self.observed_session()
                entered, release = asyncio.Event(), asyncio.Event()
                calls = []

                async def answer(*args, **kwargs):
                    calls.append(True)
                    return {"success": True, "text": "Accepted synthetic response"}

                owner = history._store if boundary == "store" else self.repo
                method = "async_save" if boundary == "store" else "async_append_entries"
                original = getattr(owner, method)

                async def blocked(*args, **kwargs):
                    entered.set()
                    await release.wait()
                    return await original(*args, **kwargs)

                # The query owns an equivalent repository instance over the same service.
                if boundary == "sqlite":
                    owner = HistoricalProjectionRepository
                    original = owner.async_append_entries

                    async def blocked(repo, *args, **kwargs):
                        entered.set()
                        await release.wait()
                        return await original(repo, *args, **kwargs)

                payload = {
                    **identity, "client_message_id": "cancel-" + boundary,
                    "text": "Tell me about this",
                    "conversation_context": {"session_id": session.session_id},
                }
                with patch.object(owner, method, blocked), patch.object(
                    self.handlers.http_helpers, "async_handle_ask_dj", answer
                ):
                    pending = asyncio.create_task(self.handlers.async_handle_ask_dj_message_payload(
                        hass, dict(payload), headers=headers
                    ))
                    await entered.wait()
                    pending.cancel()
                    await asyncio.sleep(0)
                    pending.cancel()  # Repeated disconnect cancellation cannot release the lock.
                    ending = asyncio.create_task(self.manager.async_end(
                        owner_profile_id="profile-a", session_id=session.session_id
                    ))
                    await asyncio.sleep(0)
                    self.assertFalse(ending.done())
                    release.set()
                    with self.assertRaises(asyncio.CancelledError):
                        await pending
                    await ending
                messages = (await history.async_history("profile:profile-a"))["messages"]
                rows = await self.repo.async_entry_records("profile-a", session.session_id)
                self.assertEqual(len(messages), 2)
                self.assertEqual(len([r for r in rows if r["kind"].startswith("conversation_")]), 2)
                query = HistoricalProjectionQueryService(self.repo, history)
                for row in rows:
                    await query.async_open_entry("profile-a", session.session_id, row["entry_id"])
                self.assertEqual(len(calls), 1)

    async def test_open_rechecks_removed_entry_after_projection(self):
        from unittest.mock import patch
        from custom_components.djconnect.session_history_projection import HistoryQueryError

        session = await self.observed_session()
        row = (await self.repo.async_entry_records("profile-a", session.session_id))[0]
        original = self.queries._project_entry

        async def withdrawn(owner, entry):
            projected = await original(owner, entry)
            await self.repo.async_remove_entry_records(owner, [entry["entry_id"]])
            return projected

        with patch.object(self.queries, "_project_entry", withdrawn):
            with self.assertRaises(HistoryQueryError):
                await self.queries.async_open_entry("profile-a", session.session_id, row["entry_id"])

    async def test_source_identity_and_persisted_repair_change_grant_revision(self):
        from unittest.mock import patch
        from dataclasses import replace
        from custom_components.djconnect.session_conversation import async_history_grant_revision

        hass, runtime, history, identity, headers = await self.transport_fixture()
        storage = hass.data["djconnect"]["djconnect_profile_platform"]
        before = await async_history_grant_revision(hass, "profile-a")
        household = await storage.async_load()
        account = household.music_accounts["source-account"]
        storage._household = replace(household, music_accounts={
            **household.music_accounts,
            account.account_id: replace(account, provider_account_id="different-source-identity"),
        })
        changed = await async_history_grant_revision(hass, "profile-a")
        self.assertNotEqual(before, changed)
        registry = types.SimpleNamespace(async_get=lambda hass: types.SimpleNamespace(
            async_get_issue=lambda *args: types.SimpleNamespace(data={"entry_id": "source-entry"})
        ))
        with patch.dict(sys.modules, {"homeassistant.helpers.issue_registry": registry}), patch.object(
            sys.modules["homeassistant.helpers"], "issue_registry", registry, create=True
        ):
            self.assertNotEqual(changed, await async_history_grant_revision(hass, "profile-a"))
        self.assertEqual(changed, await async_history_grant_revision(hass, "profile-a"))

    async def test_account_change_invalidates_cursor_and_inflight_projection(self):
        from unittest.mock import patch
        from dataclasses import replace
        from custom_components.djconnect.session_conversation import query_service
        from custom_components.djconnect.session_history_projection import HistoryQueryError

        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a", session_id=session.session_id, state="playing",
            media_identity="spotify:track:0000000000000000000001", title="Next",
            duration_ms=120000, position_ms=1000,
        )
        query = query_service(hass, history)
        first = await query.async_timeline_page("profile-a", session.session_id, limit=1)
        self.assertTrue(first["next_cursor"])
        storage = hass.data["djconnect"]["djconnect_profile_platform"]
        household = await storage.async_load()
        account = household.music_accounts["source-account"]

        def change_account():
            storage._household = replace(household, music_accounts={
                **household.music_accounts,
                account.account_id: replace(account, provider_account_id="new-source-owner"),
            })

        original = query._project_entry

        async def changed(owner, row):
            result = await original(owner, row)
            change_account()
            return result

        with patch.object(query, "_project_entry", changed):
            with self.assertRaises(HistoryQueryError):
                await query.async_timeline_page("profile-a", session.session_id)
        with self.assertRaises(HistoryQueryError):
            await query.async_timeline_page(
                "profile-a", session.session_id, limit=1, cursor=first["next_cursor"]
            )

    async def test_legacy_device_clear_preserves_private_profile_conversation(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        payload = {
            **identity, "client_message_id": "private-preserved",
            "text": "When have I listened to Metallica?", "conversation_context": {},
        }
        self.assertEqual((await self.handlers.async_handle_ask_dj_message_payload(
            hass, payload, headers=headers
        ))[1], 200)
        revision = await history.async_scope_revision("profile:profile-a")
        await history.async_clear_all(include_profile_history=False)
        self.assertEqual(revision, await history.async_scope_revision("profile:profile-a"))
        self.assertEqual(len((await history.async_history("profile:profile-a"))["messages"]), 2)
        self.assertFalse(await history.async_session_request_cleared(
            "profile:profile-a", "private-preserved"
        ))

    async def test_pending_profile_turn_and_cursor_survive_legacy_clear(self):
        import asyncio
        from unittest.mock import patch
        from custom_components.djconnect.session_conversation import query_service

        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a", session_id=session.session_id, state="playing",
            media_identity="spotify:track:0000000000000000000001", title="Next",
            duration_ms=120000, position_ms=1000,
        )
        query = query_service(hass, history)
        first = await query.async_timeline_page("profile-a", session.session_id, limit=1)
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return {"success": True, "text": "Unchanged private response"}

        with patch.object(self.handlers.http_helpers, "async_handle_ask_dj", delayed):
            pending = asyncio.create_task(self.handlers.async_handle_ask_dj_message_payload(
                hass, {**identity, "client_message_id": "legacy-during-private",
                       "text": "Tell me about this",
                       "conversation_context": {"session_id": session.session_id}}, headers=headers
            ))
            await entered.wait()
            revision = await history.async_scope_revision("profile:profile-a")
            await history.async_clear_all(include_profile_history=False)
            self.assertEqual(revision, await history.async_scope_revision("profile:profile-a"))
            page = await query.async_timeline_page(
                "profile-a", session.session_id, limit=1, cursor=first["next_cursor"]
            )
            self.assertEqual(len(page["entries"]), 1)
            release.set()
            self.assertEqual((await pending)[1], 200)
        await history.async_append_assistant_message(None, {}, {"text": "Legacy ambient"})
        self.assertEqual(len((await history.async_history("profile:profile-a"))["messages"]), 2)

    async def test_real_handler_rejects_late_track_end_and_privacy_changes(self):
        import asyncio
        from unittest.mock import patch
        from custom_components.djconnect.domain.profile import ProfilePrivacyMode

        for mutation in ("track", "end", "privacy", "clear"):
            with self.subTest(mutation=mutation):
                hass, runtime, history, identity, headers = await self.transport_fixture()
                session = await self.observed_session()
                entered = asyncio.Event()
                release = asyncio.Event()

                async def delayed(*args, **kwargs):
                    entered.set()
                    await release.wait()
                    return {"success": True, "text": "Synthetic delayed response"}

                payload = {
                    **identity,
                    "client_message_id": "late-" + mutation,
                    "text": "Tell me about this",
                    "conversation_context": {"session_id": session.session_id},
                }
                with patch.object(self.handlers.http_helpers, "async_handle_ask_dj", delayed):
                    pending = asyncio.create_task(
                        self.handlers.async_handle_ask_dj_message_payload(
                            hass, payload, headers=headers
                        )
                    )
                    await entered.wait()
                    if mutation == "track":
                        await self.manager.async_update_playback_projection(
                            owner_profile_id="profile-a",
                            session_id=session.session_id,
                            state="playing",
                            media_identity="spotify:track:0000000000000000000001",
                            title="Changed",
                            duration_ms=120000,
                            position_ms=1000,
                        )
                    elif mutation == "end":
                        await self.manager.async_end(
                            owner_profile_id="profile-a", session_id=session.session_id
                        )
                    elif mutation == "privacy":
                        await hass.data["djconnect"][
                            "djconnect_profile_platform"
                        ].async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.SHARED)
                    else:
                        await history.async_clear("profile:profile-a")
                    release.set()
                    result, status = await pending
                self.assertEqual(status, 403 if mutation == "privacy" else 409, result)
                self.assertEqual((await history.async_history("profile:profile-a"))["messages"], [])
                if mutation != "end":
                    await self.manager.async_end(
                        owner_profile_id="profile-a", session_id=session.session_id
                    )

    async def test_old_cursor_cannot_restore_fresh_or_removed_content(self):
        from custom_components.djconnect.session_history_projection import HistoryQueryError

        session = await self.observed_session()
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=session.session_id,
            state="playing",
            media_identity="spotify:track:0000000000000000000001",
            title="Next",
            duration_ms=120000,
            position_ms=1000,
        )
        page = await self.queries.async_timeline_page("profile-a", session.session_id, limit=1)
        await self.repo.async_remove_entry_records("profile-a", [page["entries"][0]["entry_id"]])
        with self.assertRaises(HistoryQueryError):
            await self.queries.async_timeline_page(
                "profile-a", session.session_id, limit=1, cursor=page["next_cursor"]
            )

    async def test_text_client_cannot_claim_confirmed_voice_origin(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        response, status = await self.handlers.async_handle_ask_dj_message_payload(
            hass,
            {
                **identity,
                "client_message_id": "spoof-voice",
                "text": "When have I listened to Metallica?",
                "input_type": "voice",
                "conversation_context": {"session_id": None},
            },
            headers=headers,
        )
        self.assertEqual(status, 200, response)
        self.assertEqual(response["conversation"]["input_type"], "text")

    async def test_scoped_explicit_next_uses_existing_authority_and_actor(self):
        from unittest.mock import patch
        from custom_components.djconnect import ask_dj

        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        commands = []
        runtime.update = lambda **updates: runtime.__dict__.update(updates)

        async def status_read(*args, **kwargs):
            return {
                "success": True,
                "playback": {"state": "playing", "track_name": "One", "artist": "Metallica"},
            }

        async def command(hass, bound_runtime, command_name, *args, **kwargs):
            commands.append(command_name)
            await self.manager.async_update_playback_projection(
                owner_profile_id="profile-a",
                session_id=session.session_id,
                state="playing",
                media_identity="spotify:track:0000000000000000000001",
                title="Next",
                duration_ms=120000,
                position_ms=1000,
            )
            return {"success": True, "playback": {"state": "playing", "track_name": "Next"}}

        payload = {
            **identity,
            "client_message_id": "explicit-next",
            "text": "next",
            "conversation_context": {"session_id": session.session_id},
        }
        with (
            patch.object(ask_dj, "run_music_command", status_read),
            patch.object(ask_dj, "run_text_command", command),
        ):
            result, status = await self.handlers.async_handle_ask_dj_message_payload(
                hass, dict(payload), headers=headers
            )
            self.assertEqual(status, 200, result)
            duplicate, status = await self.handlers.async_handle_ask_dj_message_payload(
                hass, dict(payload), headers=headers
            )
            self.assertEqual(status, 200, duplicate)
        self.assertEqual(commands, ["next"])
        self.assertEqual(
            result["conversation"]["entry_ids"], duplicate["conversation"]["entry_ids"]
        )
        self.assertIsNone(result["user_id"])
        self.assertEqual(result["owner_profile_id"], "profile-a")

    async def test_private_session_minimum_cannot_be_upgraded_by_normal_request(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.manager.async_start(
            owner_profile_id="profile-a", history_enabled=False
        )
        result, status = await self.handlers.async_handle_ask_dj_message_payload(
            hass,
            {
                **identity,
                "client_message_id": "private",
                "text": "When have I listened to Metallica?",
                "conversation_context": {"session_id": session.session_id},
            },
            headers=headers,
        )
        self.assertEqual(status, 200, result)
        self.assertFalse(result["history_persisted"])
        self.assertEqual(result["conversation"]["entry_ids"], [])
        self.assertEqual((await history.async_history("profile:profile-a"))["messages"], [])
        self.assertEqual(await self.repo.async_entry_records("profile-a", session.session_id), [])
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        self.assertIsNone(await self.repo.async_get_session_for_originating_id(session.session_id))

    async def test_global_clear_pending_and_completed_ids_survive_store_reload(self):
        await self._assert_cleared_ids(global_clear=True)

    async def test_cleared_pending_and_completed_request_ids_do_not_reappear(self):
        await self._assert_cleared_ids(global_clear=False)

    async def _assert_cleared_ids(self, *, global_clear):
        import asyncio
        from unittest.mock import patch

        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        payload = {
            **identity,
            "client_message_id": "cleared-pending",
            "text": "Tell me about this",
            "conversation_context": {"session_id": session.session_id},
        }
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return {"success": True, "text": "Synthetic answer"}

        with patch.object(self.handlers.http_helpers, "async_handle_ask_dj", delayed):
            pending = asyncio.create_task(
                self.handlers.async_handle_ask_dj_message_payload(
                    hass, dict(payload), headers=headers
                )
            )
            await entered.wait()
            await history.async_clear("profile:profile-a")
            release.set()
            self.assertEqual((await pending)[1], 409)
        retry, status = await self.handlers.async_handle_ask_dj_message_payload(
            hass, dict(payload), headers=headers
        )
        self.assertEqual(status, 409, retry)
        fresh = {
            **identity,
            "client_message_id": "completed",
            "text": "When have I listened to Metallica?",
            "conversation_context": {"session_id": session.session_id},
        }
        self.assertEqual(
            (
                await self.handlers.async_handle_ask_dj_message_payload(
                    hass, dict(fresh), headers=headers
                )
            )[1],
            200,
        )
        await history.async_clear("profile:profile-a")
        self.assertEqual(
            (
                await self.handlers.async_handle_ask_dj_message_payload(
                    hass, dict(fresh), headers=headers
                )
            )[1],
            409,
        )
        self.assertEqual((await history.async_history("profile:profile-a"))["messages"], [])

    async def test_same_recorded_match_and_navigation_are_localized_in_five_languages(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.observed_session()
        await self.manager.async_end(owner_profile_id="profile-a", session_id=session.session_id)
        examples = {
            "en": ("When did I listen to Metallica?", "Found in your saved sessions"),
            "nl": (
                "Wanneer heb ik eerder naar Metallica geluisterd?",
                "Gevonden in je bewaarde sessies",
            ),
            "de": ("Wann habe ich Metallica gehört?", "In deinen gespeicherten Sessions gefunden"),
            "fr": ("Quand ai-je écouté Metallica ?", "Trouvé dans vos sessions conservées"),
            "es": ("¿Cuándo escuché a Metallica?", "Encontrado en tus sesiones guardadas"),
        }
        entries = set()
        for locale, (question, prefix) in examples.items():
            result, status = await self.handlers.async_handle_ask_dj_message_payload(
                hass,
                {
                    **identity,
                    "client_message_id": "locale-" + locale,
                    "language": locale,
                    "text": question,
                    "conversation_context": {"session_id": None},
                },
                headers=headers,
            )
            self.assertEqual(status, 200, result)
            self.assertTrue(result["text"].startswith(prefix), result)
            self.assertEqual(len(result["historical_matches"]), 1)
            entries.add(result["navigation_actions"][0]["entry_id"])
            self.assertEqual(result["playback_actions"], [])
            self.assertFalse(result["full_listens_proven"])
        self.assertEqual(len(entries), 1)

    async def observed_session(self):
        session = await self.manager.async_start(
            owner_profile_id="profile-a",
            music_backend="spotify_direct",
            history_source_context={
                "backend_id": "source-spotify",
                "music_account_id": "source-account",
                "provider_entry_id": "source-entry",
            },
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
        from custom_components.djconnect.domain.music_account import MusicAccountKind

        await storage.async_upsert_music_backend(
            "source-spotify", BackendProvider.SPOTIFY_DIRECT, display_name="Synthetic source"
        )
        await storage.async_upsert_music_account(
            "source-account",
            "source-spotify",
            kind=MusicAccountKind.PERSONAL,
            display_name="Synthetic source account",
            linked_profile_ids=frozenset({"profile-a"}),
        )
        source_entry = types.SimpleNamespace(
            entry_id="source-entry",
            data={
                "music_account_id": "source-account",
                "spotify_refresh_token": "synthetic-never-sent-source-grant",
            },
            options={},
        )
        hass.config_entries = types.SimpleNamespace(async_entries=lambda domain: [source_entry])
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
            "ask_dj_history_manager": history,
        }
        identity = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"}
        headers = {"Authorization": "Bearer synthetic-fixture-token"}
        return hass, runtime, history, identity, headers

    async def test_real_handlers_bind_text_and_voice_derived_turns_and_archive_restart(self):
        hass, runtime, history, identity, headers = await self.transport_fixture()
        session = await self.manager.async_start(
            owner_profile_id="profile-a",
            selected_mood="energy",
            locale="nl",
            history_source_context={
                "backend_id": "source-spotify",
                "music_account_id": "source-account",
                "provider_entry_id": "source-entry",
            },
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
                voice_input=input_type == "voice",
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
