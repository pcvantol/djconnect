"""Actual paired profile/SQLite negative scope; no remote/native effects."""
import asyncio
from copy import deepcopy
from unittest.mock import patch
import uuid

from tests import test_host_wake_child_store as fixture
from custom_components.djconnect.direct_rich_wire import RichError
from custom_components.djconnect.host_wake_proxy_attempt import HostWakeAttempt


class HostWakeManagementTests(fixture.HostWakeChildStoreTests):
    async def parked_child(self):
        ready, holder = asyncio.Event(), []

        async def original_prepare():
            attempt = HostWakeAttempt(self.hass, self.headers)
            try:
                attempt.bind_parent("prepare", self.prepare)
                child = self.rich.host_wake_children.capture(attempt, self.prepare)
                await child.reserve(role_request_hash=self.role["request_sha256"], attempt_id=str(uuid.uuid4()))
                holder.append(child)
                ready.set()
                await asyncio.Event().wait()
            finally:
                attempt.close()

        worker, waiter = asyncio.create_task(original_prepare()), asyncio.create_task(ready.wait())
        await asyncio.wait((worker, waiter), return_when=asyncio.FIRST_COMPLETED)
        if worker.done():
            waiter.cancel()
            await worker
        await waiter
        self.addAsyncCleanup(self.finish_worker, worker)
        return worker, holder[0]

    async def finish_worker(self, worker):
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)

    def management(self, *, operation="status", **changes):
        payload = {key: deepcopy(self.prepare[key]) for key in ("contract_version", "device_id", "client_type",
            "session_id", "surface", "purpose_id", "operation_id")}
        payload.update(changes)
        attempt = HostWakeAttempt(self.hass, self.headers)
        self.addCleanup(attempt.close)
        return self.rich.host_wake_children.capture_management(attempt, payload, operation=operation)

    async def test_actual_ended_session_and_retired_child_remain_history_only(self):
        worker, child = await self.parked_child()
        await self.manager.async_end(owner_profile_id="synthetic-owner", session_id=self.active.session_id)
        self.parent.retire()
        await asyncio.gather(worker, return_exceptions=True)
        management = self.management()
        result = await management.run()
        self.assertEqual((result.phase, result.consumed_attempts), ("initial_reserved", 1))
        self.assertTrue(child.closed and management.closed)
        self.assertIsNone(child.context)
        self.assertIsNone(management.child)
        self.assertIsNone(management.snapshot)

    async def test_withdraw_fences_only_child_before_actual_SQL_and_preserves_display_parent(self):
        worker, child = await self.parked_child()
        management = self.management(operation="withdraw")
        transaction = self.service.async_in_transaction

        async def inspect(*args, **kwargs):
            self.assertTrue(child.closed)
            self.assertTrue(worker.cancelling())
            self.assertFalse(self.parent.closed)
            return await transaction(*args, **kwargs)

        with patch.object(self.service, "async_in_transaction", side_effect=inspect):
            result = await management.run()
        self.assertEqual((result.phase, result.consumed_attempts), ("withdrawn", 1))
        self.assertFalse(self.parent.closed)

    async def test_wrong_session_surface_device_and_native_operation_cannot_close_original(self):
        worker, child = await self.parked_child()
        for changes in ({"session_id": "different-session"}, {"surface": "live_activity"},
                {"operation_id": self.parent.original.operation_id}, {"operation_id": str(uuid.uuid4())},
                {"device_id": "djconnect-ios-000000000000"}):
            with self.subTest(changes=changes), self.assertRaises(RichError):
                self.management(operation="withdraw", **changes)
            self.assertFalse(child.closed)
            self.assertFalse(worker.cancelling())
        self.assertEqual((await self.management().run()).phase, "initial_reserved")

    async def test_status_capture_cleanup_never_closes_original_child(self):
        worker, child = await self.parked_child()
        management = self.management()
        self.assertIs(management.attempt.parent, None)
        management.close()
        self.assertFalse(child.closed)
        self.assertFalse(worker.cancelling())
        self.assertIsNone(management.snapshot)

    async def test_competing_management_task_cannot_close_original_request_or_child(self):
        _, child = await self.parked_child()
        management = self.management()
        with self.assertRaises(RichError) as caught:
            await asyncio.create_task(management.run())
        self.assertEqual(caught.exception.status, 409)
        self.assertFalse(management.closed or child.closed)
        self.assertEqual((await management.run()).phase, "initial_reserved")
        self.assertFalse(child.closed)

    async def test_pair_retired_after_SQL_cannot_publish_history_or_close_unrelated_child(self):
        worker, child = await self.parked_child()
        management = self.management()
        attempt = management.attempt
        transaction = self.service.async_in_transaction

        async def retired_after_read(*args, **kwargs):
            result = await transaction(*args, **kwargs)
            attempt.pair.retire()
            return result

        with patch.object(self.service, "async_in_transaction", side_effect=retired_after_read):
            with self.assertRaises(RichError):
                await management.run()
        self.assertTrue(management.closed)
        self.assertFalse(child.closed or worker.cancelling())

    async def test_actual_profile_reassignment_denies_original_management_without_new_child_effect(self):
        worker, child = await self.parked_child()
        await self.storage.async_create_profile("Replacement synthetic owner", profile_id="other-owner")
        await self.storage.async_upsert_device(self.device, "ios", linked_profile_id="other-owner")
        previous = (child.closed, worker.cancelling())
        with self.assertRaises(RichError) as caught:
            self.management(operation="withdraw")
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual((child.closed, worker.cancelling()), previous)

    async def test_management_taskdone_before_run_releases_only_own_request_graph(self):
        worker, child = await self.parked_child()

        async def capture_only():
            management = self.management()
            return management, management.attempt

        management, attempt = await asyncio.create_task(capture_only())
        await asyncio.sleep(0)
        self.assertTrue(management.closed and attempt.closed)
        self.assertIsNone(management.snapshot)
        self.assertIsNone(attempt.pair)
        self.assertFalse(child.closed or worker.cancelling())

    async def test_request_taskdone_after_normal_run_still_releases_original_pair(self):
        worker, child = await self.parked_child()

        async def read_once():
            management = self.management()
            attempt = management.attempt
            result = await management.run()
            self.assertFalse(attempt.closed)  # Response guard still owns this request.
            return management, attempt, result

        management, attempt, result = await asyncio.create_task(read_once())
        await asyncio.sleep(0)
        self.assertEqual(result.phase, "initial_reserved")
        self.assertTrue(management.closed and attempt.closed)
        self.assertIsNone(attempt.pair)
        self.assertFalse(child.closed or worker.cancelling())

    async def test_cancel_after_actual_SQL_read_cannot_publish_metadata_ack(self):
        worker, child = await self.parked_child()
        transaction, holder = self.service.async_in_transaction, []

        async def cancel_after_read(*args, **kwargs):
            result = await transaction(*args, **kwargs)
            asyncio.current_task().cancel()
            return result

        async def request():
            management = self.management()
            holder.append(management)
            return await management.run()

        with patch.object(self.service, "async_in_transaction", side_effect=cancel_after_read):
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.create_task(request())
        self.assertTrue(holder[0].closed)
        self.assertIsNone(holder[0].snapshot)
        self.assertFalse(child.closed or worker.cancelling())
