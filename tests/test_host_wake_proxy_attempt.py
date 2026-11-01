"""Actual paired/Profile/Session/SQLite fixtures, synthetic nonsecret identity."""
import asyncio
import time
import unittest
import uuid

from tests import test_direct_rich_context as fixture
from custom_components.djconnect import direct_rich_runtime as rich
from custom_components.djconnect.direct_rich_wire import RichError
from custom_components.djconnect.host_wake_proxy_attempt import HostWakeAttempt
from custom_components.djconnect.surface_registration import retire_runtime


class HostWakeProxyAttemptTests(fixture.DirectRichContextTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        rich.setup_service(self.hass)
        self.rich = self.domain[rich.KEY]
        self.display_request = {"contract_version": 1, "operation_id": str(uuid.uuid4()),
            "device_id": self.device, "client_type": "ios", "session_id": self.active.session_id,
            "surface": "widget", "enabled": True, "os_snapshot_cache": True, "locked_display": False}
        self.attempts = []

    async def asyncTearDown(self):
        for attempt in self.attempts:
            attempt.close()
        self.rich.close()
        await super().asyncTearDown()

    def capture_request(self):
        attempt = HostWakeAttempt(self.hass, self.headers)
        self.attempts.append(attempt)
        return attempt

    async def parent_request(self):
        display = await self.rich.authorize(self.display_request, self.headers, (time.time(), time.monotonic()))
        return {k: self.display_request[k] for k in ("contract_version", "device_id", "client_type", "session_id", "surface")} | {
            "purpose_id": display["purpose_id"], "operation_id": str(uuid.uuid4())}

    async def test_actual_parent_capture_does_not_renew_or_retire_separate_display(self):
        request = await self.parent_request()
        attempt = self.capture_request()
        parent = attempt.bind_parent("status", request)
        original = (parent.original, parent.mono_start, parent.mono_end, parent.generation)
        self.assertGreater(await attempt.wait(lambda: asyncio.sleep(0, result=1)), 0)
        self.assertEqual((parent.original, parent.mono_start, parent.mono_end, parent.generation), original)
        attempt.close()
        self.assertFalse(parent.closed)
        self.assertIsNone(attempt.parent)

    async def test_pair_retired_during_body_cannot_be_recaptured_or_ABA_restored(self):
        request = await self.parent_request()
        attempt = self.capture_request()
        retire_runtime(self.runtime)
        with self.assertRaises(RichError):
            attempt.bind_parent("status", request)
        self.assertTrue(attempt.closed)
        self.assertIsNone(attempt.pair)

    async def test_service_replaced_during_body_is_not_selected_after_decode(self):
        request = await self.parent_request()
        attempt = self.capture_request()
        self.domain[rich.KEY] = rich.DirectRichService(self.hass, self.service)
        with self.assertRaises(RichError):
            attempt.bind_parent("status", request)
        self.domain[rich.KEY] = self.rich
        with self.assertRaises(RichError):
            attempt.check()

    async def test_wrong_session_surface_or_display_operation_never_bind_parent(self):
        request = await self.parent_request()
        for patch in ({"session_id": "different-session"}, {"surface": "live_activity"},
                {"operation_id": self.display_request["operation_id"]}, {"purpose_id": str(uuid.uuid4())}):
            attempt = self.capture_request()
            with self.subTest(patch=patch), self.assertRaises(RichError):
                attempt.bind_parent("status", request | patch)
            self.assertIsNone(attempt.parent)

    async def test_original_body_and_whole_budget_do_not_restart_after_wait(self):
        attempt = self.capture_request()
        original = (attempt.wall, attempt.mono)
        await attempt.wait(lambda: asyncio.sleep(0))
        self.assertEqual((attempt.wall, attempt.mono), original)
        attempt.mono -= 11  # Explicit synthetic elapsed request, no parent clock mutation.
        with self.assertRaises(RichError):
            attempt.check_body_budget()
        self.assertTrue(attempt.closed)
        attempt = self.capture_request()
        attempt.mono -= 31
        with self.assertRaises(RichError):
            attempt.check()
        self.assertTrue(attempt.closed)

    async def test_actual_retirement_during_await_blocks_late_positive_return(self):
        request = await self.parent_request()
        attempt = self.capture_request()
        attempt.bind_parent("status", request)

        async def delayed():
            await asyncio.sleep(0)
            retire_runtime(self.runtime)
            return "late-positive-DATA"

        with self.assertRaises(RichError):
            await attempt.wait(delayed)
        self.assertTrue(attempt.closed)
        self.assertIsNone(attempt.context)

    async def test_cancel_after_await_never_returns_result_or_retires_parent_display(self):
        request = await self.parent_request()
        parent = self.rich.purposes[request["purpose_id"]]
        entered = asyncio.Event()
        captured = []

        async def worker():
            attempt = self.capture_request()
            captured.append(attempt)
            attempt.bind_parent("status", request)

            async def suspended():
                entered.set()
                await asyncio.Event().wait()

            return await attempt.wait(suspended)

        task = asyncio.create_task(worker())
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(captured[0].closed)
        self.assertFalse(parent.closed)

    async def test_request_task_cannot_borrow_another_tasks_original_capture(self):
        attempt = self.capture_request()

        async def borrower():
            with self.assertRaises(RichError):
                attempt.check()

        await asyncio.create_task(borrower())
        self.assertTrue(attempt.closed)


if __name__ == "__main__":
    unittest.main()
