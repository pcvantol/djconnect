"""Synthetic flow witnesses plus real SQL; actual HA flow tests are separate."""
from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from tests.test_config_flow_helpers import install_homeassistant_stubs
from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()
install_homeassistant_stubs()

from custom_components.djconnect.config_flow import DJConnectConfigFlow  # noqa: E402
from custom_components.djconnect.persistence import PERSISTENCE_SERVICE_KEY, PersistenceService  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.surface_registration import PairingRetirement  # noqa: E402
from custom_components.djconnect import surface_pair_journal as journal  # noqa: E402


class PendingOriginTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = PersistenceService(Path(self.directory.name) / "pairs.sqlite3", SQLitePersistenceProvider())
        await self.service.async_initialize()
        self.entries = []
        self.pending = {}
        self.hass = SimpleNamespace(is_stopping=False, data={"djconnect": {
            PERSISTENCE_SERVICE_KEY: self.service,
            "config_flow_app_pairing_pending": self.pending}},
            config_entries=SimpleNamespace(async_entries=lambda _: self.entries),
            async_create_task=asyncio.create_task)
        self.flow = self.new_flow("flow-original")
        self.received = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios",
                         "device_token": "SYNTHETIC-PENDING-ONLY", "device_name": "Synthetic"}
        self.context = self.context_for(self.flow)

    async def asyncTearDown(self):
        for runtime in tuple(self.hass.data["djconnect"].values()):
            record = getattr(runtime, "surface_pair_registration", None)
            if record:
                while record.tasks:
                    await asyncio.gather(*tuple(record.tasks))
        await self.service.async_close()
        self.directory.cleanup()

    def new_flow(self, flow_id):
        flow = DJConnectConfigFlow()
        flow.hass, flow.flow_id = self.hass, flow_id
        return flow

    def context_for(self, flow):
        context = journal.pending_context_for_flow(flow, self.pending, "123456")
        context.update(flow_id=flow.flow_id, pair_code="123456", client_type="ios",
                       device_token="SYNTHETIC-PENDING-ONLY")
        return context

    def post(self, received=None):
        value = dict(self.received if received is None else received)
        self.context["pairing_received"] = journal.note_pending_pair(self.hass, self.context, value)
        return journal.capture_pending_origin(self.flow, "123456")

    def handoff(self, origin):
        self.flow._surface_pending_origin = origin
        self.flow._pairing = dict(self.context["pairing_received"])
        self.assertTrue(origin.handoff(self.flow))
        journal.clear_pending_context(self.flow, "123456")

    def created(self, *, state="loaded", token=None):
        data = {**self.received, "ha_install_id": "synthetic-install"}
        if token is not None:
            data["device_token"] = token
        entry = SimpleNamespace(entry_id="entry-created", data=data, options={},
                                state=SimpleNamespace(value=state), disabled_by=None)
        runtime = SimpleNamespace(entry=entry, device_token=data["device_token"],
            pairing_device_id=data["device_id"], surface_registration_retirement=PairingRetirement())
        self.entries.append(entry)
        self.hass.data["djconnect"][entry.entry_id] = runtime
        return entry, runtime

    async def rows(self):
        return await self.service.async_in_transaction(lambda tx: tx.fetchall(
            "SELECT auth_generation,state FROM djconnect_surface_pairs"))

    async def test_original_created_hook_transfers_once_to_real_SQL_record(self):
        original = self.post()
        self.handoff(original)
        entry, runtime = self.created()
        result = {"result": entry, "unchanged": "ordinary-flow"}
        self.assertIs(await self.flow.async_on_create_entry(result), result)
        self.assertEqual(original.phase, "consumed")
        self.assertIsNone(self.flow._surface_pending_origin)
        record = runtime.surface_pair_registration
        while record.tasks:
            await asyncio.gather(*tuple(record.tasks))
        self.assertEqual(record.phase, "recorded")
        await self.flow.async_on_create_entry(result)
        self.assertEqual(len(await self.rows()), 1)

    async def test_duplicate_POST_keeps_original_object_not_a_new_validation(self):
        original = self.post()
        received = self.context["pairing_received"]
        again = self.post({**self.received, "device_name": "Updated ordinary metadata"})
        self.assertIs(original, again)
        self.assertIs(self.context["pairing_received"], received)
        self.assertEqual(received["device_name"], "Updated ordinary metadata")

    async def test_conflicting_POST_and_ABA_never_replace_retired_original(self):
        original = self.post()
        self.post({**self.received, "device_id": "djconnect-ios-ZZZZZZ123456"})
        self.assertEqual(original.phase, "retired")
        self.assertIsNone(self.post())
        self.assertIs(self.context[journal._PENDING_ORIGIN], original)
        entry, _ = self.created()
        await self.flow.async_on_create_entry({"result": entry})
        self.assertEqual(await self.rows(), [])

    async def test_new_flow_same_code_cannot_inherit_token_or_received_object(self):
        original = self.post()
        other = self.new_flow("flow-new")
        context = journal.pending_context_for_flow(other, self.pending, "123456")
        self.assertIsNot(context, self.context)
        self.assertNotIn("pairing_received", context)
        self.assertNotIn("device_token", context)
        self.assertEqual(original.phase, "retired")
        journal.clear_pending_context(self.flow, "123456")
        self.assertIs(self.pending["123456"], context)

    async def test_removal_before_created_hook_prevents_registration(self):
        original = self.post()
        self.handoff(original)
        journal.abandon_pending_flow(self.flow)
        entry, _ = self.created()
        await self.flow.async_on_create_entry({"result": entry})
        self.assertEqual(original.phase, "retired")
        self.assertEqual(await self.rows(), [])

    async def test_pending_abort_removes_only_its_own_context(self):
        original = self.post()
        journal.abandon_pending_flow(self.flow)
        self.assertFalse(self.pending)
        self.assertEqual(original.phase, "retired")
        self.assertEqual(await self.rows(), [])

    async def test_setup_failure_consumes_without_minting_even_a_tombstone(self):
        original = self.post()
        self.handoff(original)
        entry, runtime = self.created(state="setup_error")
        await self.flow.async_on_create_entry({"result": entry})
        self.assertFalse(hasattr(runtime, "surface_pair_registration"))
        self.assertEqual(await self.rows(), [])

    async def test_replaced_token_after_setup_closes_original(self):
        original = self.post()
        self.handoff(original)
        entry, runtime = self.created(token="SYNTHETIC-REPLACEMENT")
        await self.flow.async_on_create_entry({"result": entry})
        self.assertFalse(hasattr(runtime, "surface_pair_registration"))
        self.assertEqual(await self.rows(), [])

    async def test_historical_entry_equal_tuple_is_not_created_entry(self):
        entry, runtime = self.created()
        # This entry already existed when the genuine POST was captured.
        original = self.post()
        self.handoff(original)
        await self.flow.async_on_create_entry({"result": entry})
        self.assertFalse(hasattr(runtime, "surface_pair_registration"))
        self.assertEqual(await self.rows(), [])

    async def test_untagged_equal_pairing_copy_never_acquires_origin(self):
        self.context["pairing_received"] = dict(self.received)
        self.assertIsNone(journal.capture_pending_origin(self.flow, "123456"))
        entry, _ = self.created()
        await self.flow.async_on_create_entry({"result": entry})
        self.assertEqual(await self.rows(), [])

    async def test_reopened_pair_step_retires_previous_handoff(self):
        original = self.post()
        self.handoff(original)
        journal.pending_context_for_flow(self.flow, self.pending, "123456")
        self.assertEqual(original.phase, "retired")
        self.assertIsNone(self.flow._surface_pending_origin)

    async def test_entry_callback_consumes_before_scheduler_can_reenter(self):
        original = self.post()
        self.handoff(original)
        entry, _ = self.created()
        def inspect_before_schedule(hass, runtime):
            self.assertEqual(original.phase, "consumed")
            self.assertIsNone(self.flow._surface_pending_origin)
        with patch.object(journal, "schedule_pair_registration", inspect_before_schedule):
            await self.flow.async_on_create_entry({"result": entry})

    async def test_capture_precedes_unique_id_await_and_conflict_suppresses_handoff(self):
        original = self.post()
        self.flow._discovered_defaults = {"pair_code": "123456", "client_type": "ios"}
        self.flow._selected_pair_client_type = "ios"
        self.flow._ensure_app_pairing_defaults = AsyncMock()
        self.flow._async_update_discovered_pair_selection = AsyncMock(return_value=False)
        self.flow._abort_if_unique_id_configured = lambda: None
        self.flow.async_step_profile_choice = AsyncMock(return_value={"type": "next_step"})
        entered, release = asyncio.Event(), asyncio.Event()
        async def held_unique_id(value):
            self.assertIs(self.flow._surface_pending_origin, original)
            entered.set()
            await release.wait()
        self.flow.async_set_unique_id = held_unique_id
        with patch("custom_components.djconnect.config_flow._has_valid_assist_pipeline", return_value=True):
            task = asyncio.create_task(self.flow.async_step_pair({"client_type": "ios"}))
            await asyncio.wait_for(entered.wait(), 2)
            self.post({**self.received, "device_id": "djconnect-ios-ZZZZZZ123456"})
            release.set()
            self.assertEqual(await task, {"type": "next_step"})
        self.assertIsNone(self.flow._surface_pending_origin)
        entry, _ = self.created()
        await self.flow.async_on_create_entry({"result": entry})
        self.assertEqual(await self.rows(), [])

    async def test_cancelled_created_callback_does_not_schedule_SQL(self):
        original = self.post()
        self.handoff(original)
        entry, _ = self.created()
        async def cancelled():
            asyncio.current_task().cancel()
            return await self.flow.async_on_create_entry({"result": entry})
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.create_task(cancelled())
        self.assertEqual(original.phase, "consumed")
        self.assertEqual(await self.rows(), [])

    async def test_successful_native_removal_does_not_retire_transferred_runtime(self):
        original = self.post()
        self.handoff(original)
        entry, runtime = self.created()
        await self.flow.async_on_create_entry({"result": entry})
        journal.abandon_pending_flow(self.flow)
        record = runtime.surface_pair_registration
        while record.tasks:
            await asyncio.gather(*tuple(record.tasks))
        self.assertFalse(record.retired)
        self.assertEqual(record.phase, "recorded")

    async def test_equal_flow_id_different_original_object_cannot_inherit(self):
        original = self.post()
        other = self.new_flow(self.flow.flow_id)
        context = journal.pending_context_for_flow(other, self.pending, "123456")
        self.assertIsNot(context, self.context)
        self.assertEqual(original.phase, "retired")
        self.assertNotIn("pairing_received", context)
