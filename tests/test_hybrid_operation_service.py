"""Operation service state/race units; domain and Store boundaries are explicit fixtures."""

import asyncio
import json
import time
from types import SimpleNamespace
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

    async def test_last_ask_dj_guard_await_cannot_extend_dispatch_lifetime(self):
        from custom_components.djconnect.ask_dj import dialogue

        now = [int(time.time() * 1000)]
        self.manager.journal._wall = lambda: now[0]
        self.manager.journal._mono = lambda: self.manager.journal._anchor_mono
        calls = []

        async def slow_owner():
            await asyncio.sleep(0)
            now[0] += 300_001

        async def domain(*args):
            turn = SimpleNamespace(
                guard=slow_owner, effect_started=True, require_effect=lambda *a, **k: None
            )
            tt = dialogue.current_turn.set(turn)
            et = dialogue.current_effect.set(SimpleNamespace(family="next", value=None))
            try:
                await dialogue.guard_effect_dispatch(method="POST", path="/me/player/next")
                calls.append("forbidden")
            finally:
                dialogue.current_effect.reset(et)
                dialogue.current_turn.reset(tt)

        with patch.object(self.service, "invoke", domain):
            with self.assertRaises(self.service.OperationError) as error:
                await self.manager.execute(self.authority, self.request, transport="http")
        self.assertEqual(error.exception.code, "operation_expired")
        self.assertEqual(calls, [])

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
        delivered = await result.admitted_body()
        self.assertEqual(delivered["text"], "private-source-body")
        self.assertTrue(delivered["result_available"])
        self.assertTrue(delivered["operation_receipt"]["result_available"])
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

    async def test_setting_cas_rejection_is_known_but_after_send_stays_unknown(self):
        self.request["operation"] = "session/mood"

        async def reject(*args):
            return {"success": False, "error": "mood_revision_conflict"}, 409

        with patch.object(self.service, "invoke", reject):
            result, code = await self.manager.execute(
                self.authority, self.request, transport="websocket"
            )
        body = await result.admitted_body()
        self.assertEqual(
            (code, body["operation_receipt"]["phase"], body["error"]),
            (409, "rejected", "mood_revision_conflict"),
        )
        stored, code = await self.manager.status(self.authority, self.status_request())
        self.assertEqual((code, stored["operation_receipt"]["phase"]), (409, "rejected"))
        self.request["operation_id"] = identifier(int(time.time() * 1000), sequence=2)

        async def sent_then_failed(*args):
            await self.service.guard_transport_effect()
            return await reject(*args)

        with patch.object(self.service, "invoke", sent_then_failed):
            result, code = await self.manager.execute(
                self.authority, self.request, transport="http"
            )
        self.assertEqual(result["operation_receipt"]["phase"], "unknown")

    async def test_outgoing_frame_limit_preserves_receipt_or_refuses_projection(self):
        from custom_components.djconnect.hybrid_contract import bounded_frame

        base = {"id": 1, "connection_id": "own-connection", "type": "result", "status": 200}
        oversized = {**base, "result": {"text": "private-source-content" * 4000}}
        refused = json.loads(bounded_frame(oversized))
        self.assertEqual(refused["error"]["code"], "projection_too_large")
        self.assertNotIn("result", refused)
        from custom_components.djconnect.transport_delivery import OwnerDeliveryResult

        oversized["result"]["operation_receipt"] = {"phase": "confirmed", "result_available": False}
        oversized["result"] = await OwnerDeliveryResult(
            oversized["result"], [lambda: None]
        ).admitted_body()
        self.assertTrue(oversized["result"]["operation_receipt"]["result_available"])
        compact = json.loads(bounded_frame(oversized))
        self.assertTrue(compact["success"])
        self.assertFalse(compact["result"]["result_available"])
        self.assertFalse(compact["result"]["operation_receipt"]["result_available"])
        self.assertNotIn("text", compact["result"])

    async def test_identity_and_flattened_compatibility_payload_cannot_override_owner(self):
        authority = self.service.PairedAuthority(
            object(),
            {"device_id": "own-device", "client_type": "ios"},
            {},
            object(),
            SimpleNamespace(profile_id="own-profile"),
            "binding",
        )
        for payload in (
            {"identity": []},
            {"identity": {"device_token": "forbidden"}},
            {"command": "ask_dj_message", "value": {"profile_id": "other-profile"}},
            {"command": "ask_dj_message", "value": {"device_id": "other-device"}},
        ):
            with self.assertRaises(self.service.OperationError):
                authority.payload(payload)
        with self.assertRaises(self.service.OperationError) as failure:
            await self.service.PairedAuthority.resolve(
                object(), {"device_id": "own-device", "client_type": []}, {}
            )
        self.assertEqual(failure.exception.status, 400)

    async def test_close_during_reservation_cannot_start_a_late_domain_task(self):
        entered, release = asyncio.Event(), asyncio.Event()
        save = self.store.async_save
        calls, unsubscribed = [], []
        self.manager._unsubscribe_stop = lambda: unsubscribed.append(True)

        async def delayed_save(value):
            entered.set()
            await release.wait()
            await save(value)

        async def domain(*args):
            calls.append("forbidden-after-close")
            return {"success": True}, 200

        with (
            patch.object(self.store, "async_save", delayed_save),
            patch.object(self.service, "invoke", domain),
        ):
            request = asyncio.create_task(
                self.manager.execute(self.authority, self.request, transport="http")
            )
            await entered.wait()
            await self.manager.close()
            release.set()
            with self.assertRaises(self.service.OperationError) as failure:
                await request
        self.assertEqual(failure.exception.code, "operation_unavailable")
        await self.manager.close()
        self.assertEqual((calls, unsubscribed), ([], [True]))
        self.assertFalse(self.manager.tasks)
        self.assertFalse(self.manager.journal._active)
        self.assertEqual(next(iter(self.store.data["records"].values()))["phase"], "rejected")
