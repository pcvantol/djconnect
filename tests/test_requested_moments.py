"""Real Runtime/Knowledge/Moment/SQLite/operation owners; public/model inputs are declared fixtures."""

import asyncio
from copy import deepcopy
from contextlib import ExitStack
from dataclasses import replace
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from tests import test_personal_dj_narration_public_artist as base
from tests import test_live_impression as live_fixtures
from tests.test_transport_operation_journal import Store, identifier


class RequestedMomentsTest(unittest.IsolatedAsyncioTestCase):
    setUpClass = live_fixtures.LiveImpressionTest.__dict__["setUpClass"]
    tearDownClass = live_fixtures.LiveImpressionTest.__dict__["tearDownClass"]
    fetch = base.PublicArtistNarrationTest.fetch
    model = base.PublicArtistNarrationTest.model

    async def asyncSetUp(self):
        await base.PublicArtistNarrationTest.asyncSetUp(self)
        from custom_components.djconnect import requested_moments as requested, hybrid_service

        self.requested, self.hybrid = requested, hybrid_service
        self.operations = hybrid_service.HybridOperations(self.hass, Store())
        self.sequence = 0
        self.manager._hass = self.hass
        from types import SimpleNamespace

        self.runtime.entry = SimpleNamespace(
            entry_id="owner-entry",
            data={**self.runtime.config, "device_token": self.runtime.device_token},
            options={},
            disabled_by=None,
            state=SimpleNamespace(value="loaded"),
        )
        self.hass.config_entries.async_get_entry = lambda eid: (
            self.runtime.entry if eid == "owner-entry" else None
        )
        self.hass.data["djconnect"]["hybrid_operation_manager"] = self.operations

        async def provider(brief, guard):
            return await self.pipeline.realize_session_narration(
                self.hass,
                narration=brief,
                admission=guard,
                fallback_text=brief.seed,
                conf=self.runtime.config,
                debug=self.debug,
            )

        def authorize():
            if not self.authorized:
                raise PermissionError("fixture-source-withdrawn")

        self.manager.connect_narration("profile-a", self.session.session_id, provider, authorize)
        self.manager._intra_track_opportunities["profile-a"] = self.r.IntraTrackOpportunity(
            self.session.session_id,
            self.catalog["uri"],
            self.session.broadcast.state.playback.item_id,
            ("backend", "account", "provider", "provider-account"),
            qualified_facts=(self.fact,),
        )

    async def asyncTearDown(self):
        await self.operations.close()
        await base.PublicArtistNarrationTest.asyncTearDown(self)

    def emit(self, name, payload):
        output = os.getenv("DJC_AVATAR_FIXTURE_DIRECTORY")
        if output:
            from datetime import datetime, timezone
            from custom_components.djconnect.requested_moment_inventory import capability

            Path(output).mkdir(parents=True, exist_ok=True)
            (Path(output) / (name + ".json")).write_text(
                json.dumps(
                    {
                        "contract_version": 1,
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                        "evidence_scope": "declared synthetic public/model fixtures; real owners/SQLite",
                        "capability": capability(),
                        **payload,
                    },
                    indent=2,
                )
            )

    async def other_client(self):
        from types import SimpleNamespace

        identity = {"device_id": "djconnect-ios-0123456789AB", "client_type": "ios"}
        storage = self.hass.data["djconnect"]["djconnect_profile_platform"]
        await storage.async_upsert_device(
            identity["device_id"], "ios", linked_profile_id="profile-a"
        )
        other = SimpleNamespace(**self.runtime.__dict__)
        other.config = {**self.runtime.config, **identity}
        other.device_status = dict(identity)
        other.device_token = "synthetic-second-owner-token"
        headers = {"Authorization": "Bearer " + other.device_token}
        other.authorize_device_request = lambda h, device_id=None, client_type=None: (
            h.get("Authorization") == headers["Authorization"]
            and device_id == identity["device_id"]
            and client_type == "ios"
        )
        other.entry = SimpleNamespace(
            entry_id="second-owner-entry",
            data={**other.config, "device_token": other.device_token},
            options={},
            disabled_by=None,
            state=SimpleNamespace(value="loaded"),
        )
        self.hass.data["djconnect"]["second-owner-entry"] = other
        entries = {"owner-entry": self.runtime.entry, "second-owner-entry": other.entry}
        self.hass.config_entries.async_get_entry = lambda eid: entries.get(eid)
        return identity, headers, other

    async def output_settings(self, output):
        from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
        from custom_components.djconnect import profile_settings

        self.manager._settings_repository = ProfileDJSettingsRepository(self.fixture.service)
        before, status = await profile_settings.async_handle_settings(
            self.hass, {**self.identity, "contract_version": 3}, headers=self.headers
        )
        self.assertEqual(status, 200, before)
        current = before["snapshot"]["session"]
        answer, status = await profile_settings.async_handle_settings(
            self.hass,
            {
                **self.identity,
                "contract_version": 3,
                "binding": before["binding"],
                "operation_id": identifier(int(time.time() * 1000), 999),
                "expected_defaults_revision": before["snapshot"]["defaults_revision"],
                "expected_session": {
                    k: current[k] for k in ("session_id", "generation", "revision")
                }
                if current
                else None,
                "patch": {"announcement_output": output, "presence": "music_only"},
            },
            headers=self.headers,
            write=True,
        )
        self.assertEqual(status, 200, answer)
        self.session = self.manager.current_active("profile-a")
        return answer

    async def authority(self):
        return await self.hybrid.PairedAuthority.resolve(self.hass, self.identity, self.headers)

    def envelope(self, operation, payload):
        self.sequence += 1
        return {
            "contract_version": 1,
            "operation_id": identifier(int(time.time() * 1000), self.sequence),
            "operation_epoch": self.operations.journal.epoch,
            "operation": operation,
            "payload": payload,
        }

    async def menu(self):
        result, status = await self.operations.read(
            await self.authority(),
            "ask_dj/moments",
            {"contract_version": 1, "session_id": self.session.session_id},
        )
        self.assertEqual(status, 200)
        return result

    def make_request(self, menu, type_id="artist_story"):
        row = next(x for x in menu["types"] if x["type_id"] == type_id)
        return self.envelope(
            "ask_dj/moments/request",
            {
                "contract_version": 1,
                "session_id": self.session.session_id,
                "type_id": type_id,
                "subject_ref": row["subject"]["subject_ref"],
            },
        )

    async def execute(self, request, authority=None):
        result, status = await self.operations.execute(
            authority or await self.authority(), request, transport="http"
        )
        return (
            await result.admitted_body() if hasattr(result, "admitted_body") else result
        ), status

    async def submit(self, menu, type_id="artist_story"):
        request = self.make_request(menu, type_id)
        result, status = await self.execute(request)
        return result, status, request

    def production(self):
        stack = ExitStack()
        stack.enter_context(
            patch.object(
                self.pipeline, "_assist_context", return_value={"agent_id": "fixture-agent"}
            )
        )
        stack.enter_context(self.sources())
        stack.enter_context(
            patch.object(self.pipeline, "call_conversation_process_with_agent_retry", self.model)
        )
        return stack

    async def read_status(self, envelope):
        return await self.operations.read(
            await self.authority(),
            "ask_dj/moments/status",
            {
                "contract_version": 1,
                "session_id": self.session.session_id,
                "operation_id": envelope["operation_id"],
            },
        )

    async def cancel_request(self, envelope):
        self.last_cancel_envelope = self.envelope(
            "ask_dj/moments/cancel",
            {
                "contract_version": 1,
                "session_id": self.session.session_id,
                "request_operation_id": envelope["operation_id"],
            },
        )
        return await self.execute(self.last_cancel_envelope)

    def sources(self):
        return patch.object(
            self.research.PublicFetch,
            "request",
            lambda fetch, url, **kw: self.fetch(fetch, url, **kw),
        )

    async def test_real_request_music_only_paused_immediate_history_and_fixture(self):
        from custom_components.djconnect.requested_moment_inventory import capability

        with (
            patch.object(
                self.pipeline, "_assist_context", return_value={"agent_id": "fixture-agent"}
            ),
            self.sources(),
            patch.object(self.pipeline, "call_conversation_process_with_agent_retry", self.model),
        ):
            self.session = await self.manager.async_update_presence(
                owner_profile_id="profile-a",
                session_id=self.session.session_id,
                selected_presence="music_only",
            )
            await self.manager.async_update_playback_projection(
                owner_profile_id="profile-a",
                session_id=self.session.session_id,
                state="paused",
                media_identity=self.catalog["uri"],
                title=self.catalog["title"],
                artist=self.catalog["artist"],
                duration_ms=300000,
                position_ms=0,
            )
            self.session = self.manager.current_active("profile-a")
            ledger = deepcopy(self.session.presence_ledger.__dict__)
            menu = await self.menu()
            self.assertEqual(len(menu["types"]), 10)
            self.assertEqual((self.calls, self.urls), ([], []))
            result, status, envelope = await self.submit(menu)
            self.assertIn("state", result, result)
            self.assertEqual((status, result["state"]), (200, "accepted"), result)
            rich = result["result"]
            moment = rich["moment"]
            self.assertEqual(moment["type"], "artist")
            self.assertEqual(moment["content"], self.answer)
            self.assertEqual(rich["retention"], "retained")
            self.assertTrue(rich["presentation_admission"]["display_allowed"])
            self.assertEqual(len(self.calls), 2)
            self.assertEqual(self.session.presence_ledger.__dict__, ledger)
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            saved = next(x for x in rows if x["reference_id"] == moment["moment_id"])
            self.assertEqual(saved["entry_id"], rich["entry_id"])
            self.assertEqual(json.loads(saved["body"])["text"], moment["content"])
            read, status = await self.operations.read(
                await self.authority(),
                "ask_dj/moments/status",
                {
                    "contract_version": 1,
                    "session_id": self.session.session_id,
                    "operation_id": envelope["operation_id"],
                },
            )
            self.assertEqual(read["result"]["moment"]["moment_id"], moment["moment_id"])
            self.assertEqual(
                read["result"]["presentation_admission"], rich["presentation_admission"]
            )
            from custom_components.djconnect.session_history_projection import project_entry

            history = project_entry(saved)
            self.assertNotIn("user_requested_owner", history)
            self.emit(
                "producer",
                {
                    "inventory": menu,
                    "request_envelope": envelope,
                    "accepted_http_response": result,
                    "status_response": read,
                    "history_entry": history,
                },
            )
            if output := os.getenv("DJC_AVATAR_FIXTURE_OUTPUT"):
                Path(output).write_text(
                    json.dumps(
                        {
                            "contract_version": 1,
                            "evidence_scope": "declared synthetic public/model fixtures; real owners/SQLite",
                            "capability": capability(),
                            "inventory": menu,
                            "request_envelope": envelope,
                            "accepted_http_response": result,
                            "status_response": read,
                            "history_entry": history,
                        },
                        indent=2,
                    )
                )

    async def test_real_pending_status_concurrent_busy_cancel_and_no_late_history(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def hold():
            started.set()
            await release.wait()

        self.after_draft = hold
        with self.production():
            menu = await self.menu()
            envelope = self.make_request(menu)
            task = asyncio.create_task(self.execute(envelope))
            try:
                await asyncio.wait_for(started.wait(), 1)
                pending, status = await asyncio.wait_for(self.read_status(envelope), 1)
                self.assertEqual((status, pending["state"]), (200, "pending"))
                self.assertIn("voor je", pending["pending_text"])
                self.assertIsNone(pending["result"])
                self.assertEqual(len(self.calls), 1)
                with self.assertRaises(self.hybrid.OperationError) as busy:
                    await self.submit(menu)
                self.assertEqual(busy.exception.code, "moment_request_busy")
                cancelled, status = await asyncio.wait_for(self.cancel_request(envelope), 1)
                self.assertEqual((status, cancelled["state"]), (200, "cancelled"))
                self.emit(
                    "pending-cancel",
                    {
                        "inventory": menu,
                        "request_envelope": envelope,
                        "pending_response": pending,
                        "cancel_envelope": self.last_cancel_envelope,
                        "cancel_response": cancelled,
                    },
                )
            finally:
                release.set()
            await asyncio.wait_for(task, 2)
            self.assertEqual(self.session.broadcast.state.dj_moments, ())
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            self.assertFalse(any(x["kind"] == "dj_moment" for x in rows))
            self.assertEqual(len(self.calls), 1)

    async def test_original_subject_survives_track_change_during_real_source_fetch(self):
        original = self.session.broadcast.state.playback.item_id

        async def change():
            await self.manager.async_update_playback_projection(
                owner_profile_id="profile-a",
                session_id=self.session.session_id,
                state="paused",
                media_identity="spotify:track:" + "Z" * 22,
                title="Other recording",
                artist="Other artist",
                duration_ms=10000,
                position_ms=0,
            )

        self.after_fetch = change
        with self.production():
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            self.assertEqual((status, result.get("state")), (200, "accepted"), result)
            self.assertEqual(result["result"]["moment"]["playback_item_id"], original)
            self.assertIn("Nora Vale 1", result["result"]["moment"]["content"])
            current = self.manager.current_active("profile-a")
            admission = next(
                a
                for a in current.broadcast.native_delivery()["admissions"]
                if a["moment_id"] == result["moment_id"]
            )
            self.assertFalse(admission["current_display_allowed"])
            self.assertTrue(admission["active_flow_display_allowed"])
            self.assertEqual(current.broadcast.state.playback.title, "Other recording")
            self.assertTrue(result["result"]["presentation_admission"]["display_allowed"])

    async def test_retry_cancel_after_acceptance_and_restart_read_original_locator(self):
        with self.production():
            menu = await self.menu()
            result, _, envelope = await self.submit(menu)
            self.assertEqual(result["state"], "accepted", result)
            original = result["moment_id"]
            entry = result["entry_id"]
            duplicate, status = await self.execute(envelope)
            self.assertEqual(duplicate["operation_receipt"]["phase"], "confirmed")
            self.assertEqual(len(self.calls), 2)
            cancelled, status = await self.cancel_request(envelope)
            self.assertEqual(cancelled["state"], "accepted_result_unavailable")
            self.assertEqual(cancelled["entry_id"], entry)
            self.assertEqual(cancelled["moment_id"], original)
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            self.assertEqual(sum(x["reference_id"] == original for x in rows), 1)
            self.hass.data["djconnect"].pop("requested_moments")
            recovered, status = await self.read_status(envelope)
            self.assertEqual((status, recovered["state"]), (200, "accepted_result_unavailable"))
            self.assertEqual((recovered["entry_id"], recovered["moment_id"]), (entry, original))
            self.assertIsNone(recovered["result"])
            self.assertEqual(len(self.calls), 2)

    async def test_cancel_before_request_durable_fence_prevents_generation(self):
        with self.production():
            menu = await self.menu()
            envelope = self.make_request(menu)
            cancelled, status = await self.cancel_request(envelope)
            self.assertEqual(cancelled["state"], "cancelled")
            result, status = await self.execute(envelope)
            self.assertEqual(result["operation_receipt"]["phase"], "cancelled")
            self.assertEqual((self.calls, self.urls), ([], []))
            self.assertEqual(self.session.broadcast.state.dj_moments, ())

    async def test_plain_text_fallback_is_not_rich_success_or_history(self):
        async def fallback(*args, narration, **kwargs):
            return narration.seed

        with self.production(), patch.object(self.pipeline, "realize_session_narration", fallback):
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            self.assertEqual((status, result["state"]), (200, "not_found"), result)
            self.assertIsNone(result["result"])
            self.assertEqual(self.session.broadcast.state.dj_moments, ())
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            self.assertFalse(any(x["kind"] == "dj_moment" for x in rows))
            self.emit(
                "not-found",
                {"inventory": menu, "request_envelope": envelope, "not_found_response": result},
            )
            if output := os.getenv("DJC_AVATAR_FAILURE_FIXTURE_OUTPUT"):
                Path(output).write_text(
                    json.dumps(
                        {"request_envelope": envelope, "not_found_response": result}, indent=2
                    )
                )

    async def test_settings_change_withdraws_pending_without_history(self):
        async def change():
            await self.manager.async_update_presence(
                owner_profile_id="profile-a",
                session_id=self.session.session_id,
                selected_presence="music_only",
            )

        self.after_fetch = change
        with self.production():
            menu = await self.menu()
            result, status, _ = await self.submit(menu)
            self.assertEqual(result["state"], "denied", result)
            self.assertIsNone(result["result"])
            self.assertEqual(self.session.broadcast.state.dj_moments, ())

    async def test_session_end_prevents_late_writes_and_keeps_original_identity(self):
        async def end():
            await self.manager.async_end(
                owner_profile_id="profile-a", session_id=self.session.session_id
            )

        self.after_draft = end
        with self.production():
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            self.assertEqual(result["state"], "denied", result)
            self.assertEqual(result["operation_id"], envelope["operation_id"])
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            self.assertFalse(any(x["kind"] == "dj_moment" for x in rows))

    async def test_private_no_retention_acceptance_never_claims_history(self):
        await self.fixture.service.async_in_transaction(
            lambda tx: tx.execute(
                "UPDATE djconnect_persistent_sessions SET history_enabled=0 WHERE session_id=?",
                (self.session.session_id,),
            )
        )
        with self.production():
            menu = await self.menu()
            result, status, _ = await self.submit(menu)
            self.assertEqual(result["state"], "accepted", result)
            self.assertEqual(result["result"]["retention"], "not_retained")
            self.assertIsNone(result["entry_id"])
            self.assertEqual(len(self.calls), 2)
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            self.assertFalse(any(x["kind"] == "dj_moment" for x in rows))

    async def test_source_and_owner_withdrawal_after_commit_keep_truth_not_content(self):
        with self.production():
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            original = result["moment_id"]
            await self.manager.async_update_presence(
                owner_profile_id="profile-a",
                session_id=self.session.session_id,
                selected_presence="music_only",
            )
            read, status = await self.read_status(envelope)
            self.assertEqual(read["state"], "accepted_result_unavailable")
            self.assertEqual(read["moment_id"], original)
            self.assertIsNone(read["result"])
            self.assertEqual(len(self.calls), 2)

    async def test_existing_producer_and_composer_story_owners_are_explicitly_reachable(self):
        prepare = (
            ("recording_story", base.PublicArtistNarrationTest.prepare_producer),
            ("work_composers", base.PublicArtistNarrationTest.prepare_composer),
        )
        for type_id, setup in prepare:
            with self.subTest(type_id=type_id):
                await setup(self)
                self.manager._intra_track_opportunities["profile-a"].qualified_facts = (self.fact,)
                with self.production():
                    menu = await self.menu()
                    result, status, _ = await self.submit(menu, type_id)
                    self.assertEqual((status, result["state"]), (200, "accepted"), result)
                    self.assertEqual(result["result"]["moment"]["type"], "track")
                    self.assertEqual(result["result"]["moment"]["content"], self.answer)
                    self.assertEqual(result["type_id"], type_id)
                # A newly loaded original credit is a new menu capture, not an
                # alteration of the capture already handed to the first request.
                self.hass.data["djconnect"]["requested_moments"].captures.clear()
                self.calls.clear()
                self.producer_mode = False
                self.composer_mode = False

    async def test_live_request_is_same_photo_story_media3_and_artist_cannot_replace_it(self):
        from custom_components.djconnect.image_proxy import ManagedSessionImages

        registry = ManagedSessionImages()
        self.hass.data["djconnect"]["session_images"] = registry
        self.addCleanup(registry.close)
        self.hass.async_create_task = asyncio.create_task

        async def live(*args, narration, admission, **kwargs):
            admission()
            return live_fixtures.accepted_text(
                narration.fact,
                locale=narration.locale,
                persona=narration.persona,
                mood=narration.mood,
            )

        with self.production(), patch.object(self.pipeline, "realize_session_narration", live):
            menu = await self.menu()
            result, status, envelope = await self.submit(menu, "live_impression")
            self.assertEqual((status, result["state"]), (200, "accepted"), result)
            rich = result["result"]
            self.assertEqual(rich["moment"]["type"], "live_impression")
            self.assertEqual(
                rich["moment"]["live_impression"]["photos"][0]["photo_id"], "photo-fixture"
            )
            self.assertEqual(rich["session_media"][0]["schema_version"], 3)
            self.assertEqual(rich["session_media"][0]["moment_id"], result["moment_id"])
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            saved = next(x for x in rows if x["reference_id"] == result["moment_id"])
            self.assertEqual(
                json.loads(saved["body"])["live_impression"], rich["moment"]["live_impression"]
            )
            self.emit(
                "live",
                {"inventory": menu, "request_envelope": envelope, "accepted_http_response": result},
            )
            if output := os.getenv("DJC_AVATAR_LIVE_FIXTURE_OUTPUT"):
                Path(output).write_text(
                    json.dumps(
                        {"request_envelope": envelope, "accepted_http_response": result}, indent=2
                    )
                )
            wrong, status, _ = await self.submit(menu, "artist_story")
            self.assertEqual(wrong["state"], "not_found", wrong)
            self.assertIsNone(wrong["result"])

    async def test_private_bulletin_reuses_collector_builder_limits_at_music_only_and_receipt_history(
        self,
    ):
        from datetime import datetime, timezone
        from email.utils import format_datetime
        from tests.test_bulletin_intake import HTTP, Response, rss
        from custom_components.djconnect.bulletin_intake import PRIVATE_SOURCES
        from custom_components.djconnect.bulletin_service import BulletinService

        http = HTTP()
        titles = (
            "Tech publisher announces new processor",
            "Parliament discusses transport funding",
        )
        stamp = format_datetime(datetime.fromtimestamp(time.time() - 20, timezone.utc))

        def reply(source):
            body = rss(
                source,
                date=stamp,
                title=titles[PRIVATE_SOURCES.index(source)],
                description="Must not enter narrative",
            )
            return Response(200, body)

        http.reply = reply

        async def close():
            pass

        http.close = close

        async def forbidden_model(*args):
            raise AssertionError("Private headlines must not buy a model call")

        self.manager.connect_bulletin(
            "profile-a",
            self.session.session_id,
            forbidden_model,
            lambda: None,
            lambda: lambda: None,
        )
        service = BulletinService(
            self.manager,
            Store(),
            http,
            create_task=asyncio.create_task,
            subscribe=lambda callback: lambda: None,
            sources=PRIVATE_SOURCES,
        )
        await service.builder.initialize()
        self.manager._bulletin_service = service
        try:
            self.session = await self.manager.async_update_presence(
                owner_profile_id="profile-a",
                session_id=self.session.session_id,
                selected_presence="music_only",
            )
            ledger = deepcopy(self.session.presence_ledger.__dict__)
            with self.production():
                menu = await self.menu()
                news_row = next(row for row in menu["types"] if row["type_id"] == "dj_bulletin")
                self.assertEqual(news_row["subject"]["subtitle"], "")
                self.assertNotEqual(news_row["subject"]["title"], self.session.session_id)
                self.assertEqual(http.calls, [])
                result, status, envelope = await self.submit(menu, "dj_bulletin")
                self.assertEqual((status, result["state"]), (200, "accepted"), result)
                self.assertEqual(result["result"]["moment"]["type"], "dj_bulletin")
                self.assertEqual(result["result"]["retention"], "not_retained")
                self.assertEqual(result["result"]["history_state"], "receipt_only")
                self.assertIsNotNone(result["entry_id"])
                self.emit(
                    "bulletin",
                    {
                        "inventory": menu,
                        "request_envelope": envelope,
                        "accepted_http_response": result,
                    },
                )
                self.assertFalse(
                    result["result"]["session_speech"]["moments"][0]["autoplay_eligible"]
                )
                self.assertEqual(len(http.calls), 2)
                self.assertEqual(self.calls, [])
                self.assertEqual(self.session.presence_ledger.__dict__, ledger)
                rows = await self.manager._historical_projections.async_entry_records(
                    "profile-a", self.session.session_id
                )
                saved = next(x for x in rows if x["reference_id"] == result["moment_id"])
                self.assertEqual(saved["kind"], "dj_publication")
                original = json.loads(saved["body"])
                self.assertEqual(
                    original["user_requested"]["operation_id"], envelope["operation_id"]
                )
                self.assertEqual(original["moment_id"], result["moment_id"])
                speech = result["result"]["session_speech"]["moments"][0]
                self.assertTrue(speech["user_requested"])
                self.assertEqual(speech["reference"]["moment_id"], result["moment_id"])
                from custom_components.djconnect.requested_moment_proof import retained_provenance

                self.assertFalse(retained_provenance(original))
                self.assertNotIn(titles[0], saved["body"])
                self.hass.data["djconnect"].pop("requested_moments")
                recovered, status = await self.read_status(envelope)
                self.assertEqual(recovered["state"], "accepted_result_unavailable")
                self.assertEqual(recovered["entry_id"], result["entry_id"])
                self.assertEqual(recovered["moment_id"], result["moment_id"])
                self.assertEqual(recovered["operation_id"], envelope["operation_id"])
                self.assertIsNone(recovered["result"])
        finally:
            await service.close()

    async def test_ordinary_status_cache_updates_do_not_withdraw_original_subject(self):
        async def status_update():
            self.runtime.entry.data = {
                **self.runtime.entry.data,
                "last_device_status": {
                    "app_version": "4.1.0",
                    "playback": {"title": "Later track", "uri": "spotify:track:" + "Z" * 22},
                },
            }

        self.after_draft = status_update
        with self.production():
            menu = await self.menu()
            result, status, _ = await self.submit(menu)
            self.assertEqual((status, result["state"]), (200, "accepted"), result)
            self.assertIn("Nora Vale 1", result["result"]["moment"]["content"])

    async def test_actual_configuration_change_during_generation_withdraws_request(self):
        async def config_update():
            self.runtime.entry.data = {
                **self.runtime.entry.data,
                "assist_pipeline_id": "different-original-provider",
            }

        self.after_draft = config_update
        with self.production():
            menu = await self.menu()
            result, status, _ = await self.submit(menu)
            self.assertEqual(result["state"], "denied", result)
            self.assertEqual(self.session.broadcast.state.dj_moments, ())

    async def test_committed_then_withdrawn_is_confirmed_unavailable_not_cancelled_and_no_ledger(
        self,
    ):
        repository = self.manager._historical_projections
        original = repository.async_accept_moment

        async def committed_then_changed(*args, **kwargs):
            accepted = await original(*args, **kwargs)
            self.runtime.entry.data = {
                **self.runtime.entry.data,
                "assist_pipeline_id": "changed-after-sql",
            }
            return accepted

        with self.production():
            menu = await self.menu()
            ledger = deepcopy(self.session.presence_ledger.__dict__)
            envelope = self.make_request(menu)
            with patch.object(repository, "async_accept_moment", committed_then_changed):
                result, status = await self.execute(envelope)
            self.assertEqual(result["operation_receipt"]["phase"], "confirmed", result)
            self.assertFalse(result["result_available"])
            read, status = await self.read_status(envelope)
            self.assertEqual(read["state"], "accepted_result_unavailable")
            self.assertIsNotNone(read["entry_id"])
            self.assertEqual(
                read["moment_id"], self.requested.moment_identifier(envelope["operation_id"])
            )
            rows = await repository.async_entry_records("profile-a", self.session.session_id)
            self.assertEqual(sum(x["reference_id"] == read["moment_id"] for x in rows), 1)
            self.assertEqual(self.session.presence_ledger.__dict__, ledger)
            self.assertEqual(self.session.broadcast.state.dj_moments, ())

    async def test_cancel_during_real_sql_stage_rolls_back_and_never_publishes(self):
        import threading

        provider = self.fixture.service._provider
        original = provider._async_guarded_transaction
        loop = asyncio.get_running_loop()
        staged, release = asyncio.Event(), threading.Event()
        armed = [False]

        async def arm():
            armed[0] = True

        self.after_draft = arm

        async def held(operation, finalize_authorize):
            if not armed[0]:
                return await original(operation, finalize_authorize)
            armed[0] = False

            def stage(tx):
                result = operation(tx)
                loop.call_soon_threadsafe(staged.set)
                if not release.wait(3):
                    raise RuntimeError("fixture-stage-timeout")
                return result

            return await original(stage, finalize_authorize)

        with self.production():
            menu = await self.menu()
            envelope = self.make_request(menu)
            with patch.object(provider, "_async_guarded_transaction", held):
                task = asyncio.create_task(self.execute(envelope))
                cancellation = None
                try:
                    await asyncio.wait_for(staged.wait(), 1)
                    cancellation = asyncio.create_task(self.cancel_request(envelope))
                    for _ in range(100):
                        row = self.hass.data["djconnect"]["requested_moments"].requests[
                            envelope["operation_id"]
                        ]
                        if row.cancelled:
                            break
                        await asyncio.sleep(0)
                    self.assertTrue(row.cancelled)
                finally:
                    release.set()
                result, status = await asyncio.wait_for(task, 3)
                if cancellation is not None:
                    await asyncio.wait_for(cancellation, 3)
            self.assertEqual(result["operation_receipt"]["phase"], "cancelled", result)
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            self.assertFalse(any(x["kind"] == "dj_moment" for x in rows))
            self.assertEqual(self.session.broadcast.state.dj_moments, ())

    async def test_delayed_seed_keeps_chronology_but_uses_actual_publication_clock(self):
        from datetime import datetime, timezone, timedelta

        old = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        before = datetime.now(timezone.utc)
        real_timestamp = self.r._timestamp
        seed = [True]

        async def after():
            seed[0] = False

        self.after_draft = after

        def stamp():
            return old if seed[0] else real_timestamp()

        with self.production(), patch.object(self.r, "_timestamp", stamp):
            menu = await self.menu()
            result, status, _ = await self.submit(menu)
            self.assertEqual(result["state"], "accepted", result)
            moment = self.session.broadcast.state.dj_moments[-1]
            boundary = self.session.broadcast._moment_delivery_boundaries[moment.moment_id]
            self.assertEqual(moment.created_at, old)
            self.assertGreaterEqual(datetime.fromisoformat(boundary.published_at), before)
            automatic = result["result"]["session_speech"]["moments"][0][
                "automatic_start_expires_at"
            ]
            self.assertEqual(automatic, boundary.utc_at(boundary.published_monotonic + 12))
            expiry = datetime.fromisoformat(
                result["result"]["presentation_admission"]["expires_at"]
            )
            self.assertGreater(expiry, before + timedelta(seconds=200))

    async def test_short_original_source_expiry_wins_over_request_and_ui_hold(self):
        from types import SimpleNamespace
        from custom_components.djconnect import requested_moment_proof as proofs

        self.fact = replace(self.fact, source_expires_at=time.monotonic() + 10)
        self.manager._intra_track_opportunities["profile-a"].qualified_facts = (self.fact,)
        with self.production():
            menu = await self.menu()
            result, status, _ = await self.submit(menu)
            self.assertEqual(result["state"], "accepted", result)
            moment = self.session.broadcast.state.dj_moments[-1]
            proof = moment.user_requested
            original = proofs.display_admission(moment)
            self.assertLessEqual(proof.deadline, self.fact.source_expires_at)
            real_time = proofs.time
            for offset, allowed in ((-0.001, True), (0, False), (0.001, False)):
                fake = SimpleNamespace(
                    monotonic=lambda: proof.deadline + offset, time=real_time.time
                )
                with patch.object(proofs, "time", fake):
                    current = proofs.display_admission(moment)
                self.assertEqual(current["display_allowed"], allowed)
                self.assertEqual(current["expires_at"], original["expires_at"])

    async def test_existing_genre_writer_is_explicitly_reachable_without_new_facts(self):
        from tests.context_variation_fixtures import source
        from custom_components.djconnect.session_facts import observed_genre_facts

        catalog, raw = source("genre", 0)
        fact = observed_genre_facts(
            raw["_session_narrative_evidence"],
            media_identity=catalog["uri"],
            title=catalog["title"],
            artist=catalog["artist"],
        )[0]
        await self.manager.async_update_allowed_capability_intents(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            allowed_capability_intents=frozenset({"genre_story"}),
        )
        self.session = self.manager.current_active("profile-a")
        self.manager._intra_track_opportunities["profile-a"].qualified_facts = (fact,)

        async def symbolic(hass, data, **kwargs):
            self.calls.append(data["text"])
            answer = (
                {
                    "text": "Even bij {artist} blijven: Spotify noemt {genre} bij de artiestgenres. Je hoort {track}."
                }
                if len(self.calls) % 2
                else {"supported": True, "language_ok": True, "style_ok": True}
            )
            return {"response": {"speech": {"plain": {"speech": json.dumps(answer)}}}}

        with (
            self.production(),
            patch.object(self.pipeline, "call_conversation_process_with_agent_retry", symbolic),
        ):
            menu = await self.menu()
            result, status, _ = await self.submit(menu, "genre_context")
            self.assertEqual((status, result["state"]), (200, "accepted"), result)
            self.assertEqual(result["result"]["moment"]["type"], "genre")
            self.assertIn("ambient", result["result"]["moment"]["content"])
            self.assertTrue(
                result["result"]["presentation_admission"]["requires_spotify_attribution"]
            )
            self.assertEqual(len(self.calls), 2)

    async def test_album_story_uses_existing_exact_edition_research_owner(self):
        from tests import test_personal_dj_narration_album as album_fixture
        from custom_components.djconnect.session_facts import catalog_facts

        album = album_fixture.AlbumNarrationTest()
        album.base = self
        album.artist_id = "A" * 22
        album.mbid = "00000000-0000-0000-0000-000000000001"
        album.group_id = "00000000-0000-0000-0000-000000000002"
        album.resource = "https://open.spotify.com/artist/" + album.artist_id
        album.mode = ""
        album.urls = []
        album.owners = []
        album.calls = []
        album.after_draft = None
        self.fact = catalog_facts({**self.catalog, "artist_ids": [album.artist_id]})[0]
        self.answer = (
            "Voor Paper Windows 1 nam Nora Vale 1 zes stukken op met een orkest. "
            "Daar schuif ik graag even bij aan."
        )
        self.fetch, self.model = album.fetch, album.model
        await self.manager.async_update_allowed_capability_intents(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            allowed_capability_intents=frozenset({"album_story"}),
        )
        self.session = self.manager.current_active("profile-a")
        self.manager._intra_track_opportunities["profile-a"].qualified_facts = (self.fact,)
        with self.production():
            menu = await self.menu()
            result, status, _ = await self.submit(menu, "album_story")
            self.assertEqual((status, result["state"]), (200, "accepted"), result)
            self.assertEqual(result["result"]["moment"]["type"], "album")
            self.assertEqual(result["result"]["moment"]["content"], self.answer)
            self.assertEqual(len(album.calls), 2)
            self.assertTrue(result["entry_id"])

    async def test_published_shared_producer_and_recommendation_keep_exact_prior_context(self):
        from custom_components.djconnect.session_facts import recording_facts

        def fact(catalog, identifier):
            return recording_facts(
                catalog,
                {
                    "id": identifier,
                    "title": catalog["title"],
                    "artist-credit": [{"artist": {"name": catalog["artist"]}}],
                    "relations": [
                        {
                            "type": "producer",
                            "target-type": "artist",
                            "artist": {
                                "id": "00000000-0000-0000-0000-000000000020",
                                "name": "Ada Reed",
                            },
                        }
                    ],
                },
            )[0]

        previous_catalog = {
            **self.catalog,
            "uri": "spotify:track:" + "B" * 22,
            "title": "Earlier exact track",
        }
        previous = fact(previous_catalog, "00000000-0000-0000-0000-000000000011")
        current = fact(self.catalog, "00000000-0000-0000-0000-000000000012")
        await self.manager.async_update_allowed_capability_intents(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            allowed_capability_intents=frozenset({"track_context", "recommendation"}),
        )
        self.manager._narration_providers.pop("profile-a", None)
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            state="playing",
            media_identity=previous_catalog["uri"],
            title=previous_catalog["title"],
            artist=previous_catalog["artist"],
            duration_ms=300000,
            position_ms=0,
        )

        async def original():
            return {"_qualified_facts": (previous,)}

        published = await self.manager.async_process_track_started(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            media_identity=previous_catalog["uri"],
            insight_provider=original,
            require_current_playback=True,
            allow_initial_facts=True,
        )
        self.assertIsNotNone(published)
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            state="paused",
            media_identity=self.catalog["uri"],
            title=self.catalog["title"],
            artist=self.catalog["artist"],
            duration_ms=300000,
            position_ms=0,
        )
        self.session = self.manager.current_active("profile-a")
        self.manager._intra_track_opportunities["profile-a"].qualified_facts = (current,)

        async def symbolic(hass, data, **kwargs):
            self.calls.append(data["text"])
            if len(self.calls) % 2:
                family = json.loads(data["text"].split("\nData:\n")[1])["family"]
                frame = (
                    "Op {current_track} en {previous_track} staat {producer} als producer vermeld."
                    if family == "shared_producer"
                    else "Via producer {producer} kun je {previous_track} nog eens ontdekken, ook verbonden aan {current_track}."
                )
                answer = {"text": frame}
            else:
                answer = {"supported": True, "language_ok": True, "style_ok": True}
            return {"response": {"speech": {"plain": {"speech": json.dumps(answer)}}}}

        with (
            self.production(),
            patch.object(self.pipeline, "call_conversation_process_with_agent_retry", symbolic),
        ):
            menu = await self.menu()
            for type_id, render_type in (
                ("shared_producer", "track"),
                ("producer_recommendation", "recommendation"),
            ):
                with self.subTest(type_id=type_id):
                    result, status, _ = await self.submit(menu, type_id)
                    self.assertEqual((status, result["state"]), (200, "accepted"), result)
                    self.assertEqual(result["result"]["moment"]["type"], render_type)
                    self.assertIn("Earlier exact track", result["result"]["moment"]["content"])
                    self.assertIn("Ada Reed", result["result"]["moment"]["content"])
                    self.assertEqual(
                        result["result"]["moment"]["user_requested"]["type_id"], type_id
                    )
            self.assertEqual(len(self.calls), 4)

    async def test_second_real_paired_client_cannot_steal_capture_or_interrupt_first_pending(self):
        identity, headers, _ = await self.other_client()
        started, release = asyncio.Event(), asyncio.Event()

        async def hold():
            started.set()
            await release.wait()

        self.after_draft = hold
        with self.production():
            menu = await self.menu()
            original_provider = self.manager._narration_providers.get("profile-a")
            other = await self.hybrid.PairedAuthority.resolve(self.hass, identity, headers)
            wrong = self.make_request(menu)
            with self.assertRaises(self.hybrid.OperationError) as denied:
                await self.execute(wrong, authority=other)
            self.assertEqual(denied.exception.code, "moment_request_unavailable")
            envelope = self.make_request(menu)
            task = asyncio.create_task(self.execute(envelope))
            try:
                await asyncio.wait_for(started.wait(), 1)
                other_menu, status = await self.operations.read(
                    other,
                    "ask_dj/moments",
                    {"contract_version": 1, "session_id": self.session.session_id},
                )
                self.assertEqual(status, 200)
                self.assertIs(self.manager._narration_providers.get("profile-a"), original_provider)
                second = self.make_request(other_menu)
                with self.assertRaises(self.hybrid.OperationError) as busy:
                    await self.execute(second, authority=other)
                self.assertEqual(busy.exception.code, "moment_request_busy")
                self.assertEqual(len(self.calls), 1)
            finally:
                release.set()
            result, status = await asyncio.wait_for(task, 2)
            self.assertEqual(result["state"], "accepted", result)
            self.assertEqual(len(self.calls), 2)
            with self.assertRaises(self.hybrid.OperationError) as private:
                await self.operations.read(
                    other,
                    "ask_dj/moments/status",
                    {
                        "contract_version": 1,
                        "session_id": self.session.session_id,
                        "operation_id": envelope["operation_id"],
                    },
                )
            self.assertEqual(private.exception.code, "moment_request_unavailable")

    async def test_requested_moment_never_reenters_ordinary_current_on_playing_reconnect(self):
        with self.production():
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            self.assertEqual(result["state"], "accepted", result)
            for _ in range(3):
                wire = self.session.broadcast.as_dict()
                self.assertNotEqual(
                    wire["native_delivery"]["current_moment_id"], result["moment_id"]
                )
                self.assertNotEqual(
                    self.session.broadcast.current_delivery_candidate_id(), result["moment_id"]
                )
                self.assertIn(
                    result["moment_id"], wire["native_delivery"]["active_flow_moment_ids"]
                )
            rows = await self.manager._historical_projections.async_entry_records(
                "profile-a", self.session.session_id
            )
            self.assertEqual(sum(row["reference_id"] == result["moment_id"] for row in rows), 1)
            self.assertEqual(len(self.calls), 2)

    async def test_text_only_manual_local_speech_uses_original_accepted_text(self):
        from custom_components.djconnect import session_speech

        with self.production():
            await self.output_settings("text_only")
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            self.assertEqual(result["state"], "accepted", result)
            descriptor = result["result"]["session_speech"]["moments"][0]
            self.assertFalse(descriptor["autoplay_eligible"])
            self.assertTrue(descriptor["manual_allowed"])
            reference = {"session_id": self.session.session_id, "moment_id": result["moment_id"]}
            prepared, status = await session_speech.async_handle_prepare(
                self.hass,
                {
                    **self.identity,
                    "contract_version": 3,
                    "processor": "local_on_device",
                    "intent": "manual",
                    "target": "local",
                    "reference": reference,
                },
                headers=self.headers,
            )
            self.assertEqual(status, 200, prepared)
            self.assertEqual(
                prepared["session_speech"]["audio_state"], "renderer_pending", prepared
            )
            self.assertEqual(
                "".join(x["text"] for x in prepared["session_speech"]["segments"]), self.answer
            )
            denied, status = await session_speech.async_handle_prepare(
                self.hass,
                {
                    **self.identity,
                    "contract_version": 3,
                    "processor": "local_on_device",
                    "intent": "automatic",
                    "target": "local",
                    "reference": reference,
                },
                headers=self.headers,
            )
            self.assertFalse(denied["session_speech"]["manual_allowed"])
            self.assertEqual(len(self.calls), 2)

    async def test_automatic_local_speech_is_only_original_requester_and_not_status_replay(self):
        from custom_components.djconnect import session_speech

        identity, headers, _ = await self.other_client()
        with self.production():
            await self.output_settings("client_device")
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            self.assertEqual(result["state"], "accepted", result)
            first = result["result"]["session_speech"]["moments"][0]
            self.assertTrue(first["autoplay_eligible"])
            read, status = await self.read_status(envelope)
            self.assertFalse(read["result"]["session_speech"]["moments"][0]["autoplay_eligible"])
            reference = {"session_id": self.session.session_id, "moment_id": result["moment_id"]}
            payload = {
                "contract_version": 3,
                "processor": "local_on_device",
                "intent": "automatic",
                "target": "local",
                "reference": reference,
            }
            prepared, status = await session_speech.async_handle_prepare(
                self.hass, {**payload, **self.identity}, headers=self.headers
            )
            self.assertEqual(status, 200, prepared)
            self.assertEqual(prepared["session_speech"]["audio_state"], "renderer_pending")
            other, status = await session_speech.async_handle_prepare(
                self.hass, {**payload, **identity}, headers=headers
            )
            self.assertEqual(status, 404, other)
            await self.cancel_request(envelope)
            late, status = await session_speech.async_handle_prepare(
                self.hass, {**payload, **self.identity}, headers=self.headers
            )
            self.assertEqual(status, 404, late)
            self.assertEqual(len(self.calls), 2)

    async def test_temporary_model_failure_is_not_a_no_found_story(self):
        async def unavailable(*args, **kwargs):
            raise TimeoutError("declared offline fixture timeout")

        with (
            self.production(),
            patch.object(self.pipeline, "call_conversation_process_with_agent_retry", unavailable),
        ):
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            self.assertEqual((status, result["state"]), (200, "temporarily_unavailable"), result)
            self.assertEqual(result["operation_receipt"]["phase"], "rejected")
            self.assertIsNone(result["result"])
            self.assertEqual(self.session.broadcast.state.dj_moments, ())
            self.emit(
                "temporary-failure",
                {"inventory": menu, "request_envelope": envelope, "failure_response": result},
            )

    async def test_missing_agent_is_a_visible_disabled_producer_without_io(self):
        with patch.object(self.pipeline, "_assist_context", return_value={}):
            menu = await self.menu()
            row = next(x for x in menu["types"] if x["type_id"] == "artist_story")
            self.assertFalse(row["available"])
            self.assertEqual(row["reason"], "producer_unavailable")
            self.assertTrue(row["reason_text"])
            self.assertEqual((self.calls, self.urls), ([], []))

    async def test_retained_requested_entry_keeps_manual_local_rights_after_session_end_restart(
        self,
    ):
        from custom_components.djconnect import session_speech
        from custom_components.djconnect.session_conversation import query_service

        with self.production():
            settings = await self.output_settings("text_only")
            menu = await self.menu()
            result, status, envelope = await self.submit(menu)
            self.assertEqual(result["state"], "accepted", result)
            sid = self.session.session_id
            await self.manager.async_end(owner_profile_id="profile-a", session_id=sid)
            await self.fixture.service.async_close()
            await self.fixture.service.async_initialize()
            from custom_components.djconnect import profile_settings

            current_settings, settings_status = await profile_settings.async_handle_settings(
                self.hass, {**self.identity, "contract_version": 3}, headers=self.headers
            )
            self.assertEqual(settings_status, 200, current_settings)
            self.assertIsNone(current_settings["snapshot"]["session"])
            self.assertEqual(
                current_settings["snapshot"]["defaults"]["announcement_output"], "text_only"
            )
            query = query_service(self.hass, self.history)
            page = await query.async_timeline_page("profile-a", sid)
            entry = next(x for x in page["entries"] if x["entry_id"] == result["entry_id"])
            self.assertTrue(entry["session_speech"]["user_requested"])
            self.assertTrue(entry["session_speech"]["manual_allowed"])
            self.assertFalse(entry["session_speech"]["autoplay_eligible"])
            self.assertNotIn("user_requested_owner", entry)
            payload = {
                **self.identity,
                "contract_version": 3,
                "processor": "local_on_device",
                "intent": "manual",
                "target": "local",
                "reference": {"session_id": sid, "entry_id": entry["entry_id"]},
            }
            prepared, status = await session_speech.async_handle_prepare(
                self.hass, payload, headers=self.headers
            )
            self.assertEqual(status, 200, prepared)
            self.assertEqual(
                prepared["session_speech"]["audio_state"], "renderer_pending", prepared
            )
            self.assertTrue(prepared["session_speech"]["user_requested"])
            self.assertEqual(
                "".join(x["text"] for x in prepared["session_speech"]["segments"]), self.answer
            )
            self.emit(
                "retained-manual-text-only",
                {
                    "inventory": menu,
                    "request_envelope": envelope,
                    "accepted_http_response": result,
                    "settings_response": settings,
                    "current_settings_response": current_settings,
                    "history_entry": entry,
                    "manual_prepare_request": payload,
                    "manual_prepare_response": prepared,
                },
            )
            from custom_components.djconnect.requested_moment_proof import retained_provenance

            self.assertTrue(retained_provenance(entry))
            for key, value in (
                ("contract_version", True),
                ("operation_id", "not-original"),
                ("type_id", []),
                ("subject_ref", "replaced"),
                ("playback_item_id", "f" * 24),
            ):
                forged = {**entry, "user_requested": {**entry["user_requested"], key: value}}
                if key == "playback_item_id":
                    # A structurally valid original locator is not a new source grant;
                    # existing source/privacy/entry authority remains independently required.
                    continue
                self.assertFalse(retained_provenance(forged), (key, value))
            self.assertEqual(len(self.calls), 2)

    async def test_album_continuity_requires_actual_prior_published_edition(self):
        from custom_components.djconnect.session_facts import catalog_facts

        await self.manager.async_end(
            owner_profile_id="profile-a", session_id=self.session.session_id
        )
        self.session = await self.manager.async_start(
            owner_profile_id="profile-a",
            locale="nl",
            selected_mood="energy",
            music_backend="spotify_direct",
            session_start_strategy=self.r.SessionStartStrategy.DISCOVER,
            allowed_capability_intents=frozenset({"album_story", "track_context"}),
        )
        current = catalog_facts(self.catalog)[0]
        previous_catalog = {
            **self.catalog,
            "uri": "spotify:track:" + "B" * 22,
            "title": "Earlier album track",
        }
        previous = catalog_facts(previous_catalog)[0]
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            state="playing",
            media_identity=previous_catalog["uri"],
            title=previous_catalog["title"],
            artist=previous_catalog["artist"],
            album=previous_catalog["album_name"],
            duration_ms=300000,
            position_ms=0,
        )

        async def original():
            return {"_qualified_facts": (previous,)}

        first = await self.manager.async_process_track_started(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            media_identity=previous_catalog["uri"],
            insight_provider=original,
            require_current_playback=True,
            allow_initial_facts=True,
        )
        self.assertIsNotNone(first)
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a",
            session_id=self.session.session_id,
            state="paused",
            media_identity=self.catalog["uri"],
            title=self.catalog["title"],
            artist=self.catalog["artist"],
            album=self.catalog["album_name"],
            duration_ms=300000,
            position_ms=0,
        )
        self.session = self.manager.current_active("profile-a")
        self.manager._intra_track_opportunities["profile-a"].qualified_facts = (current,)

        async def symbolic(hass, data, **kwargs):
            self.calls.append(data["text"])
            response = (
                {
                    "text": "Deze uitgave van {album} staat bij Spotify op {date}; die editie kennen we al van een eerdere bijdrage."
                }
                if len(self.calls) % 2
                else {"supported": True, "language_ok": True, "style_ok": True}
            )
            return {"response": {"speech": {"plain": {"speech": json.dumps(response)}}}}

        with (
            self.production(),
            patch.object(self.pipeline, "call_conversation_process_with_agent_retry", symbolic),
        ):
            menu = await self.menu()
            row = next(x for x in menu["types"] if x["type_id"] == "album_continuity")
            self.assertEqual(row["moment_type"], "track")
            self.assertTrue(row["available"], row)
            result, status, _ = await self.submit(menu, "album_continuity")
            self.assertEqual((status, result["state"]), (200, "accepted"), result)
            self.assertEqual(result["result"]["moment"]["type"], "track")
            self.assertIn("Paper Windows 1", result["result"]["moment"]["content"])
            self.assertEqual(len(self.calls), 2)
            self.assertEqual(len(self.session.published_album_context.used_relations), 1)

    def test_actual_verified_https_gate_binds_exact_current_source_and_declared_scope(self):
        import hashlib

        root = Path(__file__).resolve().parents[1]
        proof = json.loads(
            (
                root / "examples/client_contracts/requested_moments_v1/actual-ha-wire.json"
            ).read_text()
        )
        self.assertTrue(proof["source_before_after_equal"])
        self.assertEqual(len(proof["source_pins"]), 321)
        for name, digest in {**proof["source_pins"], **proof["harness_pins"]}.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)
        receipt = proof["receipt"]
        self.assertEqual(
            hashlib.sha256(json.dumps(receipt, indent=2, ensure_ascii=False).encode()).hexdigest(),
            proof["raw_receipt_sha256"],
        )
        self.assertEqual(receipt["ha_sdk_version"], "2026.11.1")
        self.assertTrue(receipt["source_unchanged"])
        self.assertEqual(receipt["setup_fixture_model_calls"], 0)
        for name, digest in receipt["source_files_sha256"].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)
        extension = receipt["extension"]
        self.assertEqual(extension["inventory_count"], 10)
        self.assertEqual(
            (extension["fixture_model_calls"], extension["fixture_public_reads"]), (2, 3)
        )
        self.assertEqual(extension["live_provider_calls"], 0)
        self.assertTrue(extension["proactive_ledger_unchanged"])
        self.assertEqual(len(extension["requests"]), 6)
        self.assertEqual({row["scheme"] for row in extension["requests"]}, {"https"})
        self.assertIn(401, [row["status"] for row in extension["requests"]])
        self.assertEqual(
            (proof["installed"], proof["live_model"], proof["native"]),
            ("NOT_RUN", "NOT_RUN", "NOT_RUN"),
        )
        self.assertEqual(proof["editorial_acceptance"], "OPEN")
