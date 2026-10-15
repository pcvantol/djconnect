"""Operation service state/race units; domain and Store boundaries are explicit fixtures."""

import asyncio
import json
import time
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as fixtures
from tests.test_transport_operation_journal import Store, identifier


class Authority:
    owner = "owner-fingerprint"
    device = "device-fingerprint"
    binding = "binding-fingerprint"
    revoked = False

    async def validate(self):
        if self.revoked:
            from custom_components.djconnect.transport_operations import OperationError

            raise OperationError("operation_context_changed", 403)

    def payload(self, value):
        return dict(value)


class OperationServiceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.SharedDialogueTest.setUpClass()
        from custom_components.djconnect import hybrid_service

        cls.service = hybrid_service

    @classmethod
    def tearDownClass(cls):
        fixtures.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        self.store = Store()
        self.manager = self.service.HybridOperations(object(), self.store)
        self.authority = Authority()
        self.request = {
            "contract_version": 1,
            "operation_id": identifier(int(time.time() * 1000)),
            "operation_epoch": self.manager.journal.epoch,
            "operation": "command",
            "payload": {"command": "next", "private_value": "fixture-private-body"},
        }

    async def asyncTearDown(self):
        await self.manager.close()

    def status_request(self):
        return {k: self.request[k] for k in ("contract_version", "operation_id", "operation_epoch")}

    async def test_http_ws_retry_dispatches_once_and_never_persists_body(self):
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def domain(*args):
            entered.set()
            await release.wait()
            await self.service.guard_transport_effect()
            calls.append("next")
            return {"success": True, "text": "private accepted response"}, 200

        with patch.object(self.service, "invoke", domain):
            first = asyncio.create_task(
                self.manager.execute(self.authority, self.request, transport="websocket")
            )
            await entered.wait()
            duplicate, status = await self.manager.execute(
                self.authority, self.request, transport="http"
            )
            self.assertEqual(status, 202)
            self.assertEqual(duplicate["operation_receipt"]["phase"], "accepted")
            release.set()
            original, status = await first
            again, status = await self.manager.execute(
                self.authority, self.request, transport="http"
            )
        self.assertEqual(calls, ["next"])
        self.assertEqual(original["text"], "private accepted response")
        self.assertEqual(again["operation_receipt"]["phase"], "confirmed")
        self.assertFalse(again["result_available"])
        self.assertNotIn("fixture-private-body", json.dumps(self.store.data))
        self.assertNotIn("private accepted response", json.dumps(self.store.data))

    async def test_caller_cancel_after_admission_keeps_one_execution(self):
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def domain(*args):
            entered.set()
            await release.wait()
            await self.service.guard_transport_effect()
            calls.append("next")
            return {"success": True}, 200

        with patch.object(self.service, "invoke", domain):
            first = asyncio.create_task(
                self.manager.execute(self.authority, self.request, transport="websocket")
            )
            await entered.wait()
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            self.assertEqual(len(self.manager.tasks), 1)
            release.set()
            await asyncio.gather(*tuple(self.manager.tasks.values()))
            result, status = await self.manager.execute(
                self.authority, self.request, transport="http"
            )
        self.assertEqual(calls, ["next"])
        self.assertEqual(result["operation_receipt"]["phase"], "confirmed")

    async def test_save_failure_prevents_domain_and_after_send_ack_loss_is_unknown(self):
        calls = []

        async def domain(*args):
            await self.service.guard_transport_effect()
            calls.append("sent")
            self.store.fail_after = True
            return {"success": True}, 200

        self.store.fail = True
        with patch.object(self.service, "invoke", domain):
            with self.assertRaises(self.service.OperationError):
                await self.manager.execute(self.authority, self.request, transport="http")
        self.assertEqual(calls, [])
        await self.manager.close()
        self.store = Store()
        self.manager = self.service.HybridOperations(object(), self.store)
        self.request["operation_epoch"] = self.manager.journal.epoch
        with patch.object(self.service, "invoke", domain):
            with self.assertRaises(self.service.OperationError):
                await self.manager.execute(self.authority, self.request, transport="http")
            self.store.fail_after = False
            with self.assertRaises(self.service.OperationError):
                await self.manager.execute(self.authority, self.request, transport="websocket")
        self.assertEqual(calls, ["sent"])
        # The atomic save itself succeeded before its acknowledgement was lost:
        # reloading sees the durable confirmed receipt, never re-executes.
        await self.manager.close()
        self.manager = self.service.HybridOperations(object(), self.store)
        status, code = await self.manager.status(self.authority, self.status_request())
        self.assertEqual(status["operation_receipt"]["phase"], "confirmed")
        self.assertFalse(status["result_available"])

    async def test_revocation_before_send_leaves_no_provider_effect(self):
        calls = []

        async def domain(*args):
            self.authority.revoked = True
            await self.service.guard_transport_effect()
            calls.append("forbidden")

        with patch.object(self.service, "invoke", domain):
            with self.assertRaises(self.service.OperationError):
                await self.manager.execute(self.authority, self.request, transport="http")
        self.assertEqual(calls, [])
        self.authority.revoked = False
        result, code = await self.manager.status(self.authority, self.status_request())
        self.assertEqual(result["operation_receipt"]["phase"], "unknown")
        self.assertEqual(code, 403)

    async def test_slow_save_cannot_extend_provider_dispatch_deadline(self):
        now = [int(time.time() * 1000)]
        self.manager.journal._wall = lambda: now[0]
        self.manager.journal._mono = lambda: self.manager.journal._anchor_mono
        save = self.store.async_save
        calls = []

        async def delayed_save(value):
            await save(value)
            if any(r["phase"] == "sent_unknown" for r in value["records"].values()):
                now[0] += 300_001

        async def domain(*args):
            await self.service.guard_transport_effect()
            calls.append("forbidden-expired-dispatch")
            return {"success": True}, 200

        with (
            patch.object(self.store, "async_save", delayed_save),
            patch.object(self.service, "invoke", domain),
        ):
            with self.assertRaises(self.service.OperationError) as failure:
                await self.manager.execute(self.authority, self.request, transport="http")
        self.assertEqual(failure.exception.code, "operation_expired")
        self.assertEqual(calls, [])

    async def test_malformed_read_is_a_typed_contract_rejection(self):
        with self.assertRaises(self.service.OperationError) as failure:
            await self.manager.read(self.authority, [], {})
        self.assertEqual(
            (failure.exception.code, failure.exception.status), ("unsupported_read", 400)
        )

    async def test_queued_rich_result_reuses_original_owner_admission(self):
        from custom_components.djconnect.transport_delivery import register_delivery_admission

        valid = [True]
        checked = []

        async def original_owner_guard():
            checked.append(True)
            if not valid[0]:
                raise PermissionError("source or Session expired")

        async def domain(*args):
            register_delivery_admission(original_owner_guard)
            return {"success": True, "text": "private-source-body"}, 200

        with patch.object(self.service, "invoke", domain):
            result, status = await self.manager.execute(
                self.authority, self.request, transport="websocket"
            )
        self.assertEqual((await result.admitted_body())["text"], "private-source-body")
        valid[0] = False
        withdrawn = await result.admitted_body()
        self.assertNotIn("text", withdrawn)
        self.assertEqual(withdrawn["operation_receipt"]["phase"], "confirmed")
        self.assertFalse(withdrawn["result_available"])
        self.assertEqual(len(checked), 2)
        self.assertNotIn("private-source-body", json.dumps(self.store.data))

    async def test_missing_rich_result_admission_returns_only_known_receipt(self):
        async def domain(*args):
            return {"success": True, "images": [{"url": "private-fixture-image"}]}, 200

        with patch.object(self.service, "invoke", domain):
            result, status = await self.manager.execute(
                self.authority, self.request, transport="http"
            )
        body = await result.admitted_body()
        self.assertNotIn("images", body)
        self.assertFalse(body["result_available"])
        self.assertEqual(body["operation_receipt"]["phase"], "confirmed")
