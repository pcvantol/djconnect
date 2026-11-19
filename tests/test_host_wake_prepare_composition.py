"""Real local pairing/SQL prepare composition; synthetic attestation and HTTP.

No production owner, clock qualification, SDK or provider effect is supplied.
The fixture is composed, not inherited: existing test cases are not rerun here.
"""
import asyncio
import base64
from contextlib import contextmanager
import hashlib
import json
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_host_wake_child_runtime as lab_fixture
from tests import test_host_wake_api as http_fixture
from custom_components.djconnect import host_wake_api as transport
from custom_components.djconnect import host_wake_api_wire as api
from custom_components.djconnect import host_wake_target_wire as target
from custom_components.djconnect import host_wake_withdrawal as negative
from custom_components.djconnect.direct_rich_wire import RichError, canonical, digest
from custom_components.djconnect.host_wake_proxy_attempt import HostWakeAttempt
from custom_components.djconnect.host_wake_runtime import execute


class HostWakePrepareCompositionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        lab_fixture.HostWakeChildRuntimeTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        lab_fixture.HostWakeChildRuntimeTests.tearDownClass()

    async def asyncSetUp(self):
        self.lab = lab_fixture.HostWakeChildRuntimeTests(
            "test_actual_resolve_uses_original_pair_scope_and_consumes_SQL_before_HTTP")
        await self.lab.asyncSetUp()
        self.lab.entry.options.update({"djconnect_install_token": "djci_" + "A" * 43,
            "api_base_url": "https://synthetic.invalid"})
        self.calls = []
        self.bad_ack = False
        self.child = None
        self.native_pending = False
        self.bad_native_ack = False
        self.token = b"T" * 32
        self.lab.hass.async_create_background_task = lambda coro, name: asyncio.create_task(coro, name=name)
        self.wake_status = 200
        self.wake_unknown = False
        self.wake_started = self.wake_release = None
        self.wake_lost = False

    async def asyncTearDown(self):
        tasks = tuple(self.lab.rich.host_wake_children.tasks)
        await self.lab.asyncTearDown()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @contextmanager
    def synthetic_HTTP(self):
        test = self

        class WakeReply(http_fixture.Reply):
            async def __aenter__(self):
                if test.wake_started is not None:
                    test.wake_started.set()
                if test.wake_release is not None:
                    await test.wake_release.wait()
                if test.wake_lost:
                    raise ConnectionError("SYNTHETIC_LOST_ACK")
                return await super().__aenter__()

        class Session(http_fixture.Session):
            def __init__(self, **kwargs):
                super().__init__(None)

            def post(self, url, **kwargs):
                sent = json.loads(kwargs["data"])
                route = url.removeprefix("https://synthetic.invalid" + api.PREFIX)
                test.calls.append((route, sent))
                if route == "authorization/resolve":
                    reply = test.lab.role
                elif route == "issuer/issue":
                    test.assertEqual(route, "issuer/issue")
                    if test.child is None:
                        test.child = test.lab.rich.host_wake_children.children[test.lab.prepare["purpose_id"]]
                    test.assertEqual(test.child.metadata.phase, "issuing")
                    test.assertIsNotNone(test.child._withdrawal)
                    original = sent["original"]
                    reply = {"version": api.VERSION,
                        **{key: sent[key] for key in api.SCOPE_HEADERS},
                        "request_sha256": api.request_hash(route, sent),
                        "generation": original["generation"], "revision": original["revision"],
                        **{key: original[key] for key in api.TIMES}, "state": "issued",
                        "purpose_id": "synthetic-private-purpose", "credential_state": "available",
                        "credential": "djchw_" + "A" * 43,
                        "expires_at_ms": original["original_wake_expires_at_ms"],
                        "native_proof_kind": test.lab.role["native_proof_kind"],
                        "registration_mode": "single_original_no_rotation", "original": original}
                    if test.bad_ack:
                        reply["request_sha256"] = "f" * 64
                elif route.startswith("native/"):
                    # Explicitly modeled API ACK DATA. No Apple proof verifier,
                    # System SDK, native owner or provider exists in this lab.
                    original = test.child._original
                    reply = {"version": api.VERSION,
                        **{key: sent[key] for key in api.SCOPE_HEADERS},
                        "request_sha256": api.request_hash(route, sent),
                        "generation": original["generation"], "revision": original["revision"],
                        **{key: original[key] for key in api.TIMES},
                        "native_proof_kind": test.lab.role["native_proof_kind"]}
                    if route == "native/challenge":
                        at = original["original_wake_issued_at_ms"] + 1
                        challenge = {"challenge_id": sent["challenge_id"],
                            "nonce_b64url": "A" * 43, "captured_at_ms": at,
                            "expires_at_ms": min(at + 30000, original["original_wake_expires_at_ms"])}
                        transcript = canonical({"original": original, "challenge": challenge})
                        reply.update(state="pending", original=original, challenge=challenge,
                            canonical_transcript_utf8=transcript.decode(),
                            client_data_sha256=hashlib.sha256(api.DOMAIN + transcript).hexdigest())
                    else:
                        pending = route == "native/complete" and test.native_pending
                        reply.update(state="pending" if pending else "native_verified",
                            challenge_id=sent["challenge_id"], original_sha256=digest(original))
                        if not pending:
                            reply["native_verified_at_ms"] = test.child._challenge["captured_at_ms"]
                        if test.bad_native_ack:
                            reply["original_sha256"] = "f" * 64
                else:
                    test.assertIn(route, {"register", "status", "wake"})
                    original = test.child._original
                    reply = {"version": target.VERSION, "purpose_id": sent["purpose_id"],
                        "operation_id": sent["operation_id"], "operation_state": "registered",
                        "state": "registered", "generation": original["generation"],
                        "revision": original["revision"],
                        "expires_at_ms": original["original_wake_expires_at_ms"],
                        "transport_expires_at_ms": None, "provider_status": None}
                    if route == "wake":
                        test.assertEqual(test.child.metadata.phase, "registered")
                        test.assertGreaterEqual(test.child.metadata.consumed_attempts, 6)
                        reply.update(operation_state="provider_accepted", provider_status=200,
                            transport_expires_at_ms=original["original_wake_expires_at_ms"])
                    result = (WakeReply if route == "wake" else http_fixture.Reply)(
                        json.dumps(reply).encode(), headers=http_fixture.Headers({
                        "Content-Type": "application/json",
                        target.CORRELATION_HEADER: target.request_hash(route, sent)}))
                    if route == "wake":
                        result.status = test.wake_status
                        if test.wake_unknown:
                            result.status = 202
                            result.body = json.dumps({key: value for key, value in reply.items()
                                if key in {"version", "purpose_id", "operation_id"}} | {
                                    "operation_state": "unknown"}).encode()
                    return result
                return http_fixture.Reply(json.dumps(reply).encode())

        synthetic = SimpleNamespace(ClientSession=Session, DummyCookieJar=object,
            ClientTimeout=lambda **kwargs: SimpleNamespace(**kwargs))
        # Negative-port semantics have their own real fixture qualification.
        # This scope tests prepare failure without starting ANY external task.
        def consume(port):
            port.used = True
        with patch.object(transport, "aiohttp", synthetic), patch.object(
                negative._IssuerWithdrawal, "schedule", autospec=True, side_effect=consume) as withdrawal:
            yield withdrawal

    async def registered_child(self):
        challenge, _complete = await self.modeled_native_chain()
        await asyncio.create_task(self.execute_request("register", self.common_request() | {
            "challenge_id": challenge, "native_token_b64": base64.b64encode(self.token).decode()}))
        return self.child._watch

    async def change_playback(self, state="playing"):
        await self.lab.manager.async_update_playback_projection(owner_profile_id="synthetic-owner",
            session_id=self.lab.active.session_id, state=state,
            media_identity="spotify:track:" + "A" * 22, title="Synthetic", artist="Synthetic")

    async def drain_watch(self, watch):
        task = watch.task
        if task is not None:
            await task
            await asyncio.sleep(0)

    async def test_actual_broadcast_semantic_change_sends_one_content_free_durable_wake(self):
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            self.assertIsNotNone(watch)
            self.assertEqual(len(self.lab.rich.host_wake_children.tasks), 0)
            await self.change_playback()
            await self.drain_watch(watch)
            wakes = [sent for route, sent in self.calls if route == "wake"]
            self.assertEqual(len(wakes), 1)
            self.assertEqual(set(wakes[0]), {"version", "purpose_id", "operation_id", "generation", "revision", "event"})
            self.assertEqual(wakes[0]["event"], "direct_rich_refresh")
            self.assertEqual(await self.metadata(), ("registered", 6))
            count = await self.lab.service.async_in_transaction(lambda tx: tx.fetchone(
                "SELECT COUNT(*) FROM djconnect_host_wake_attempts WHERE kind='target_wake'"))
            self.assertEqual(count, (1,))
            self.assertFalse(self.child.closed)
            self.assertTrue(self.child.context.pair.current())
            self.assertFalse(self.lab.rich.host_wake_children.tasks)

    async def test_observation_progress_and_same_semantics_never_send_or_renew(self):
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            await self.change_playback()
            await self.drain_watch(watch)
            await self.change_playback()
            await self.drain_watch(watch)
            self.lab.active.broadcast._publish(self.lab.runtime_module.BroadcastEventType.PLAYBACK_PROGRESS, {})
            await asyncio.sleep(0)
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)
            self.assertEqual(await self.metadata(), ("registered", 6))

    async def test_parent_close_unsubscribes_synchronously_and_retains_no_owner(self):
        with self.synthetic_HTTP() as withdrawal:
            watch = await self.registered_child()
            broadcast, subscription = watch.broadcast, watch.subscription
            self.child.close()
            self.assertNotIn(subscription, broadcast._subscribers)
            self.assertIsNone(watch.child)
            self.assertIsNone(watch.broadcast)
            self.assertIsNone(watch.registry)
            withdrawal.assert_called_once()

    async def test_capacity_drop_before_claim_keeps_parent_and_original_pair(self):
        from custom_components.djconnect import host_wake_events as events
        with self.synthetic_HTTP(), patch.object(events, "MAX_WORKERS", 0):
            watch = await self.registered_child()
            pair = self.child.context.pair
            await self.change_playback()
            self.assertIsNone(watch.pending)
            self.assertFalse(self.child.closed)
            self.assertTrue(pair.current())
            self.assertEqual(await self.metadata(), ("registered", 5))
            self.assertFalse(any(route == "wake" for route, _ in self.calls))

    async def test_expired_original_event_drops_without_claim_or_parent_retirement(self):
        from dataclasses import replace
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            await self.change_playback()
            watch.pending = replace(watch.pending, mono=time.monotonic() - 31)
            await self.drain_watch(watch)
            self.assertFalse(self.child.closed)
            self.assertTrue(self.child.context.pair.current())
            self.assertEqual(await self.metadata(), ("registered", 5))
            self.assertFalse(any(route == "wake" for route, _ in self.calls))

    async def test_foreground_status_reuses_single_subscription(self):
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            subscription = watch.subscription
            await asyncio.create_task(self.execute_request("status", self.common_request()))
            self.assertIs(self.child._watch, watch)
            self.assertEqual(watch.subscription, subscription)
            self.assertFalse(self.child.closed)

    async def test_durable_send_budget_exhaustion_never_sends_an_extra_wake(self):
        self.lab.role["max_reserved_sends"] = 1
        with self.synthetic_HTTP() as withdrawal:
            watch = await self.registered_child()
            await self.change_playback("playing")
            await self.drain_watch(watch)
            self.assertFalse(self.child.closed)
            await self.change_playback("paused")
            task = watch.task
            if task is not None:
                await task
            self.assertTrue(self.child.closed)
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)
            count = await self.lab.service.async_in_transaction(lambda tx: tx.fetchone(
                "SELECT COUNT(*) FROM djconnect_host_wake_attempts WHERE kind='target_wake'"))
            self.assertEqual(count, (1,))
            withdrawal.assert_called_once()

    async def test_provider_unknown_is_consumed_once_and_never_replayed(self):
        self.wake_unknown = True
        with self.synthetic_HTTP() as withdrawal:
            watch = await self.registered_child()
            await self.change_playback()
            await self.drain_watch(watch)
            self.assertTrue(self.child.closed)
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)
            count = await self.lab.service.async_in_transaction(lambda tx: tx.fetchone(
                "SELECT COUNT(*) FROM djconnect_host_wake_attempts WHERE kind='target_wake'"))
            self.assertEqual(count, (1,))
            await self.change_playback("paused")
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)
            withdrawal.assert_called_once()

    async def test_original_event_waits_for_foreground_without_cancelling_or_replacing_it(self):
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            gate = asyncio.Event()
            async def original_foreground():
                await gate.wait()
                self.child.pending = None
            foreground = asyncio.create_task(original_foreground())
            self.child.pending = foreground
            await self.change_playback()
            await asyncio.sleep(0)
            self.assertFalse(foreground.cancelled())
            self.assertIs(self.child.pending, foreground)
            self.assertFalse(any(route == "wake" for route, _ in self.calls))
            gate.set()
            await self.drain_watch(watch)
            self.assertFalse(foreground.cancelled())
            self.assertFalse(self.child.closed)
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)

    async def test_manager_lock_wait_uses_original_window_and_never_claims_after_expiry(self):
        from dataclasses import replace
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            await self.change_playback()
            watch.pending = replace(watch.pending, mono=time.monotonic() - 29.99)
            lock = self.child.context.manager._lock
            await lock.acquire()
            try:
                await self.drain_watch(watch)
                self.assertTrue(lock.locked())
            finally:
                lock.release()
            self.assertFalse(self.child.closed)
            self.assertEqual(await self.metadata(), ("registered", 5))
            self.assertFalse(any(route == "wake" for route, _ in self.calls))

    async def test_actual_changes_before_worker_coalesce_without_payload_retention(self):
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            await self.change_playback("playing")
            first = watch.pending
            await self.change_playback("paused")
            second = watch.pending
            self.assertGreater(second.sequence, first.sequence)
            self.assertNotEqual(first.operation, second.operation)
            self.assertEqual(set(vars(second)), {"sequence", "signature", "operation", "wall", "mono"})
            await self.drain_watch(watch)
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)
            self.assertIsNone(watch.pending)
            self.assertIsNone(watch.active)

    async def test_uncertain_projection_before_claim_drops_signal_without_revoking_parent(self):
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            await self.change_playback()
            self.lab.active.broadcast.content_pending = True
            try:
                await self.drain_watch(watch)
            finally:
                self.lab.active.broadcast.content_pending = False
            self.assertFalse(self.child.closed)
            self.assertTrue(self.child.context.pair.current())
            self.assertFalse(any(route == "wake" for route, _ in self.calls))
            self.assertEqual(await self.metadata(), ("registered", 5))

    async def test_inflight_coalescing_keeps_active_clocks_and_only_latest_unsent_change(self):
        self.wake_started, self.wake_release = asyncio.Event(), asyncio.Event()
        with self.synthetic_HTTP():
            watch = await self.registered_child()
            await self.change_playback("playing")
            await self.wake_started.wait()
            original = watch.active
            await self.change_playback("paused")
            first_pending = watch.pending
            await self.change_playback("stopped")
            self.assertIs(watch.active, original)
            self.assertGreater(watch.pending.sequence, first_pending.sequence)
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)
            self.wake_release.set()
            await self.drain_watch(watch)
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 2)
            self.assertEqual(await self.metadata(), ("registered", 7))
            self.assertFalse(self.child.closed)

    async def test_cancel_never_started_worker_releases_capacity_and_unsubscribes(self):
        with self.synthetic_HTTP() as withdrawal:
            watch = await self.registered_child()
            registry = self.child.registry
            await self.change_playback()
            task = watch.task
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.sleep(0)
            self.assertFalse(registry.tasks)
            self.assertTrue(watch.closed)
            self.assertTrue(self.child.closed)
            self.assertFalse(any(route == "wake" for route, _ in self.calls))
            self.assertEqual(await self.metadata(), ("registered", 5))
            withdrawal.assert_called_once()

    async def test_cancel_after_SQL_claim_never_refunds_or_retires_borrowed_pair(self):
        self.wake_started, self.wake_release = asyncio.Event(), asyncio.Event()
        with self.synthetic_HTTP() as withdrawal:
            watch = await self.registered_child()
            pair, registry = self.child.context.pair, self.child.registry
            await self.change_playback()
            await self.wake_started.wait()
            task = watch.task
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.sleep(0)
            self.assertTrue(self.child.closed)
            self.assertTrue(pair.current())
            self.assertFalse(registry.tasks)
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)
            row = await self.lab.service.async_in_transaction(lambda tx: tx.fetchone(
                "SELECT phase FROM djconnect_host_wake_attempts WHERE kind='target_wake'"))
            self.assertEqual(row, ("reserved",))
            withdrawal.assert_called_once()

    async def test_lost_ack_after_SQL_claim_stays_consumed_and_no_later_event_retries(self):
        self.wake_lost = True
        with self.synthetic_HTTP() as withdrawal:
            watch = await self.registered_child()
            pair = self.child.context.pair
            await self.change_playback()
            await self.drain_watch(watch)
            self.assertTrue(self.child.closed)
            self.assertTrue(pair.current())
            await self.change_playback("paused")
            self.assertEqual(sum(route == "wake" for route, _ in self.calls), 1)
            row = await self.lab.service.async_in_transaction(lambda tx: tx.fetchone(
                "SELECT phase FROM djconnect_host_wake_attempts WHERE kind='target_wake'"))
            self.assertEqual(row, ("reserved",))
            withdrawal.assert_called_once()

    async def prepare_in_original_request(self, attestation):
        self.child = self.lab.capture_child()
        return await self.child.prepare(attest_original=attestation)

    async def metadata(self):
        return await self.lab.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT phase,consumed_attempts FROM djconnect_host_wake_children"))

    async def execute_request(self, operation, payload):
        attempt = HostWakeAttempt(self.lab.hass, self.lab.headers)
        try:
            return await execute(attempt, operation, payload)
        finally:
            attempt.close()

    async def test_normal_runtime_prepare_uses_actual_local_owner_and_survives_request_close(self):
        with self.synthetic_HTTP() as withdrawal:
            body = await asyncio.create_task(self.execute_request("prepare", self.lab.prepare))
        self.assertEqual(json.loads(body)["state"], "prepared")
        self.assertFalse(self.child.closed)
        self.assertIsNone(self.child.initial_attempt)
        self.assertEqual(await self.metadata(), ("prepared", 2))
        self.assertIs(self.child._owner_attestation.owner, self.lab.rich.host_wake_original_attestor)
        withdrawal.assert_not_called()

    async def test_normal_runtime_missing_local_owner_never_reserves_or_sends(self):
        self.lab.rich.host_wake_original_attestor = None
        with self.synthetic_HTTP(), self.assertRaises(RichError):
            await asyncio.create_task(self.execute_request("prepare", self.lab.prepare))
        self.assertEqual(self.calls, [])
        self.assertIsNone(await self.metadata())

    def common_request(self):
        return {key: self.lab.prepare[key] for key in (
            "contract_version", "device_id", "client_type", "session_id", "surface",
            "purpose_id", "operation_id")}

    async def modeled_native_chain(self):
        self.lab.prepare["native_token_sha256"] = hashlib.sha256(self.token).hexdigest()
        await asyncio.create_task(self.execute_request("prepare", self.lab.prepare))
        challenge = json.loads(await asyncio.create_task(self.execute_request(
            "native/challenge", self.common_request())))["challenge"]["challenge_id"]
        body = await asyncio.create_task(self.execute_request("native/complete", self.common_request() | {
            "challenge_id": challenge, "native_proof": {"kind": self.lab.role["native_proof_kind"],
                "bytes_b64": base64.b64encode(b"MODELED SDK PROOF NOT NATIVE EVIDENCE").decode()}}))
        return challenge, json.loads(body)

    async def test_modeled_native_ACKs_and_real_SQL_precede_registered_response(self):
        with self.synthetic_HTTP():
            challenge, complete = await self.modeled_native_chain()
            self.assertEqual(complete["state"], "native_verified")
            self.assertEqual((await self.metadata())[0], "native_verified")
            body = await asyncio.create_task(self.execute_request("register", self.common_request() | {
                "challenge_id": challenge, "native_token_b64": base64.b64encode(self.token).decode()}))
        self.assertEqual(json.loads(body)["state"], "registered")
        self.assertEqual(await self.metadata(), ("registered", 5))
        self.assertFalse(self.child.closed)
        self.assertNotIn(b"djchw_", body)
        self.assertNotIn(b"synthetic-private-purpose", body)

    async def test_pending_complete_can_only_advance_via_same_original_status(self):
        self.native_pending = True
        with self.synthetic_HTTP():
            challenge, complete = await self.modeled_native_chain()
            self.assertEqual(complete["state"], "pending")
            self.assertEqual((await self.metadata())[0], "verifying")
            body = await asyncio.create_task(self.execute_request("native/status", self.common_request() | {
                "challenge_id": challenge}))
        self.assertEqual(json.loads(body)["state"], "native_verified")
        self.assertEqual(await self.metadata(), ("native_verified", 5))

    async def test_wrong_original_native_ACK_never_advances_or_keeps_credential(self):
        self.bad_native_ack = True
        with self.synthetic_HTTP() as withdrawal, self.assertRaises(RichError):
            await self.modeled_native_chain()
        self.assertEqual((await self.metadata())[0], "completing")
        self.assertTrue(self.child.closed)
        self.assertIsNone(self.child._credential)
        withdrawal.assert_called_once()

    async def test_wrong_token_is_rejected_before_any_registration_HTTP(self):
        with self.synthetic_HTTP() as withdrawal:
            challenge, _ = await self.modeled_native_chain()
            with self.assertRaises(RichError):
                await asyncio.create_task(self.execute_request("register", self.common_request() | {
                    "challenge_id": challenge, "native_token_b64": base64.b64encode(b"X" * 32).decode()}))
        self.assertNotIn("register", [route for route, _ in self.calls])
        self.assertTrue(self.child.closed)
        withdrawal.assert_called_once()

    async def test_fresh_complete_request_cannot_restart_original_local_challenge_budget(self):
        with self.synthetic_HTTP() as withdrawal:
            await asyncio.create_task(self.execute_request("prepare", self.lab.prepare))
            challenge = json.loads(await asyncio.create_task(self.execute_request(
                "native/challenge", self.common_request())))["challenge"]["challenge_id"]
            wall, mono = time.time(), time.monotonic()
            # New inbound request is fresh. Original local challenge custody is
            # already over; no foreign-clock conversion/SDK permission is tested.
            with patch("time.time", return_value=wall + 31), patch("time.monotonic", return_value=mono + 31):
                with self.assertRaises(RichError):
                    await asyncio.create_task(self.execute_request("native/complete", self.common_request() | {
                        "challenge_id": challenge, "native_proof": {"kind": self.lab.role["native_proof_kind"],
                            "bytes_b64": base64.b64encode(b"MODELED LATE PROOF").decode()}}))
        self.assertNotIn("native/complete", [route for route, _ in self.calls])
        self.assertEqual((await self.metadata())[0], "challenge_known")
        self.assertTrue(self.child.closed)
        withdrawal.assert_called_once()

    async def test_normal_runtime_status_keeps_original_prepared_child_without_reissue(self):
        with self.synthetic_HTTP() as withdrawal:
            await asyncio.create_task(self.execute_request("prepare", self.lab.prepare))
            original = self.child._original.copy()
            body = await asyncio.create_task(self.execute_request("status", self.common_request()))
        self.assertEqual(json.loads(body)["state"], "pending")
        self.assertFalse(self.child.closed)
        self.assertEqual(self.child._original, original)
        self.assertEqual(len(self.calls), 2)
        withdrawal.assert_not_called()

    async def test_normal_runtime_withdraw_is_locally_terminal_even_without_remote_ACK(self):
        with self.synthetic_HTTP() as withdrawal:
            await asyncio.create_task(self.execute_request("prepare", self.lab.prepare))
            body = await asyncio.create_task(self.execute_request("withdraw", self.common_request()))
        self.assertEqual(json.loads(body)["state"], "unknown")
        self.assertTrue(self.child.closed)
        self.assertIsNone(self.child._credential)
        withdrawal.assert_called_once()
        self.assertEqual((await self.metadata())[0], "withdrawn")
        self.assertFalse(self.lab.parent.closed)

    async def test_normal_runtime_duplicate_prepare_cannot_replace_original_child(self):
        with self.synthetic_HTTP() as withdrawal:
            await asyncio.create_task(self.execute_request("prepare", self.lab.prepare))
            original = self.child
            with self.assertRaises(RichError):
                await asyncio.create_task(self.execute_request("prepare", self.lab.prepare))
        self.assertIs(self.lab.rich.host_wake_children.children[self.lab.prepare["purpose_id"]], original)
        self.assertFalse(original.closed)
        self.assertEqual(len(self.calls), 2)
        withdrawal.assert_not_called()

    async def test_actual_issuer_ACK_and_SQL_ACK_precede_warm_handoff_and_keep_secret_private(self):
        with self.synthetic_HTTP() as withdrawal:
            body = await asyncio.create_task(self.prepare_in_original_request(lambda child: None))
        result = json.loads(body)
        self.assertEqual([route for route, _ in self.calls], ["authorization/resolve", "issuer/issue"])
        self.assertEqual(await self.metadata(), ("prepared", 2))
        self.assertEqual(result["state"], "prepared")
        self.assertEqual(result["original"], self.child._original)
        self.assertEqual(result["original_wake_issued_at_ms"], self.child.reservation.created_ms)
        self.assertNotIn(b"djchw_", body)
        self.assertNotIn(b"synthetic-private-purpose", body)
        self.assertFalse(self.child.closed)
        self.assertIsNone(self.child.pending)
        self.assertIsNone(self.child.initial_attempt)
        self.assertEqual(self.child._credential, "djchw_" + "A" * 43)
        withdrawal.assert_not_called()
        self.lab.parent.retire()
        self.assertTrue(self.child.closed)
        self.assertIsNone(self.child._credential)

    async def test_missing_attestation_cannot_start_SQL_or_HTTP(self):
        with self.synthetic_HTTP(), self.assertRaises(RichError):
            await asyncio.create_task(self.prepare_in_original_request(None))
        self.assertTrue(self.child.closed)
        self.assertEqual(self.calls, [])
        self.assertIsNone(await self.metadata())

    async def test_truthy_attestation_is_not_a_qualification_receipt(self):
        with self.synthetic_HTTP(), self.assertRaises(RichError):
            await asyncio.create_task(self.prepare_in_original_request(lambda child: True))
        self.assertTrue(self.child.closed)
        self.assertEqual(self.calls, [])
        self.assertIsNone(await self.metadata())

    async def test_wrong_original_issuer_ACK_never_publishes_RAM_or_prepared_SQL(self):
        self.bad_ack = True
        with self.synthetic_HTTP() as withdrawal, self.assertRaises(RichError):
            await asyncio.create_task(self.prepare_in_original_request(lambda child: None))
        self.assertEqual(await self.metadata(), ("issuing", 2))
        self.assertTrue(self.child.closed)
        self.assertIsNone(self.child._credential)
        self.assertIsNone(self.child._private_purpose)
        withdrawal.assert_called_once()

    async def test_cancellation_after_prepared_commit_does_not_publish_the_secret(self):
        transaction = self.lab.service.async_in_transaction

        async def cancel_after_commit(*args, **kwargs):
            result = await transaction(*args, **kwargs)
            if getattr(result, "phase", None) == "prepared":
                self.child.pending.cancel()
            return result

        with self.synthetic_HTTP() as withdrawal, patch.object(
                self.lab.service, "async_in_transaction", side_effect=cancel_after_commit):
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.create_task(self.prepare_in_original_request(lambda child: None))
        self.assertEqual(await self.metadata(), ("prepared", 2))
        self.assertTrue(self.child.closed)
        self.assertIsNone(self.child._credential)
        self.assertIsNone(self.child._private_purpose)
        withdrawal.assert_called_once()

    async def test_shorter_original_wake_expiry_closes_the_warm_child(self):
        self.lab.role["max_original_purpose_ms"] = 1000
        with self.synthetic_HTTP():
            await asyncio.create_task(self.prepare_in_original_request(lambda child: None))
        expires = self.child._original["original_wake_expires_at_ms"]
        self.assertLess(expires, self.lab.parent.original.expires_ms)
        with patch("time.time", return_value=expires / 1000 + 0.01):
            self.assertTrue(self.lab.rich._purpose_current(self.lab.parent))
            with self.assertRaises(RichError):
                self.child.current()
        self.assertTrue(self.child.closed)
        self.assertIsNone(self.child._credential)

    async def test_prepared_commit_ACK_beyond_short_wake_expiry_cannot_publish_RAM(self):
        self.lab.role["max_original_purpose_ms"] = 1000
        transaction = self.lab.service.async_in_transaction
        clock = None

        async def advance_after_commit(*args, **kwargs):
            nonlocal clock
            result = await transaction(*args, **kwargs)
            if getattr(result, "phase", None) == "prepared":
                expires = self.child._original["original_wake_expires_at_ms"]
                clock = patch("time.time", return_value=expires / 1000 + 0.01)
                clock.start()
            return result

        try:
            with self.synthetic_HTTP() as withdrawal, patch.object(
                    self.lab.service, "async_in_transaction", side_effect=advance_after_commit):
                with self.assertRaises(RichError):
                    await asyncio.create_task(self.prepare_in_original_request(lambda child: None))
            self.assertTrue(self.child.closed)
            self.assertIsNone(self.child._credential)
            withdrawal.assert_called_once()
        finally:
            if clock is not None:
                clock.stop()

    async def test_warm_child_monotonic_ceiling_is_not_the_display_parent_ceiling(self):
        self.lab.role["max_original_purpose_ms"] = 1000
        with self.synthetic_HTTP():
            await asyncio.create_task(self.prepare_in_original_request(lambda child: None))
        with patch("time.monotonic", return_value=self.child._mono_start + 1.01):
            self.assertTrue(self.lab.rich._purpose_current(self.lab.parent))
            with self.assertRaises(RichError):
                self.child.current()
        self.assertTrue(self.child.closed)
        self.assertIsNone(self.child._credential)
