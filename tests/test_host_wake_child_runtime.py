"""Actual normal setup/parent/SQLite lifetime; no network/native/clock permission."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import uuid

from tests import test_host_wake_child_store as fixture
from tests import test_host_wake_api as http_fixture
from custom_components.djconnect.direct_rich_wire import RichError
from custom_components.djconnect.direct_rich_wire import digest
from custom_components.djconnect import host_wake_api_wire as api
from custom_components.djconnect import host_wake_api as transport
from custom_components.djconnect.host_wake_proxy_attempt import HostWakeAttempt


class HostWakeChildRuntimeTests(fixture.HostWakeChildStoreTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ram_attempts = []

    async def asyncTearDown(self):
        for attempt in self.ram_attempts:
            attempt.close()
        await super().asyncTearDown()

    def capture_child(self, prepare=None):
        prepare = self.prepare if prepare is None else prepare
        attempt = HostWakeAttempt(self.hass, self.headers)
        self.ram_attempts.append(attempt)
        try:
            attempt.bind_parent("prepare", prepare)
            return self.rich.host_wake_children.capture(attempt, prepare)
        except BaseException:
            attempt.close()  # This request pair is NOT the parent's context pair.
            raise

    async def reserve_runtime_child(self, child):
        return await child.reserve(role_request_hash=self.role["request_sha256"], attempt_id=str(uuid.uuid4()))

    async def sealed_runtime_child(self):
        child = self.capture_child()
        await self.reserve_runtime_child(child)
        original = deepcopy(self.original)
        original["original_wake_issued_at_ms"] = child.reservation.created_ms
        original["original_wake_expires_at_ms"] = min(child.reservation.created_ms + 3600000,
            self.role["original_authorization_expires_at_ms"], self.parent.original.expires_ms)
        await child.seal(prepare=self.prepare, sent_resolve=self.sent, role=self.role, original=original)
        return child, original

    def resolver_HTTP(self, role):
        self.entry.options.update({"djconnect_install_token": "djci_" + "A" * 43,
            "api_base_url": "https://synthetic.invalid"})
        session = http_fixture.Session(http_fixture.Reply(json.dumps(role).encode()))
        synthetic = SimpleNamespace(ClientSession=MagicMock(return_value=session), DummyCookieJar=object,
            ClientTimeout=lambda **kwargs: SimpleNamespace(**kwargs))
        return session, patch.object(transport, "aiohttp", synthetic)

    async def test_actual_resolve_uses_original_pair_scope_and_consumes_SQL_before_HTTP(self):
        child = self.capture_child()
        session, http = self.resolver_HTTP(self.role)
        post = session.post

        def after_SQL_only(*args, **kwargs):
            self.assertTrue(child.reserved)
            self.assertEqual(child.metadata.phase, "initial_reserved")
            self.assertIs(child.pending, asyncio.current_task())
            return post(*args, **kwargs)

        with http, patch.object(session, "post", side_effect=after_SQL_only):
            role = await child.resolve()
        self.assertEqual(child._resolved_request, self.sent)
        self.assertEqual(role, self.role)
        self.assertEqual(json.loads(session.calls[0][1]["data"]), self.sent)
        self.assertEqual(len(session.calls), 1)
        role["authorization_id"] = "caller-mutated-output"
        self.assertEqual(child._resolved_role, self.role)
        self.assertIs(child.initial_attempt, self.ram_attempts[-1])
        self.assertIs(child.pending, asyncio.current_task())

    async def test_actual_resolve_wrong_original_correlation_closes_without_reissue(self):
        child = self.capture_child()
        bad = deepcopy(self.role)
        bad["request_sha256"] = "f" * 64
        session, http = self.resolver_HTTP(bad)
        with http, self.assertRaises(RichError):
            await child.resolve()
        self.assertTrue(child.closed)
        self.assertIsNone(child._resolved_role)
        self.assertIsNone(child._prepare)
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT phase,consumed_attempts FROM djconnect_host_wake_children")), ("initial_reserved", 1))

    async def test_competing_resolve_cannot_retire_original_prepare(self):
        child = self.capture_child()
        session, http = self.resolver_HTTP(self.role)
        with http:
            with self.assertRaises(RichError):
                await asyncio.create_task(child.resolve())
            self.assertFalse(child.closed)
            self.assertEqual(session.calls, [])
            await child.resolve()

    async def test_received_role_is_sealed_from_owned_reply_not_mutated_return_value(self):
        child = self.capture_child()
        _, http = self.resolver_HTTP(self.role)
        with http:
            returned = await child.resolve()
        returned["authorization_id"] = "caller-substitute"
        original = deepcopy(self.original)
        original["original_wake_issued_at_ms"] = child.reservation.created_ms
        original["original_wake_expires_at_ms"] = child.reservation.created_ms + 3600000
        result = await child.seal_resolved(original=original)
        self.assertEqual(result.role_hash, digest(self.role))
        self.assertEqual(child._role["authorization_id"], self.role["authorization_id"])
        self.assertEqual(child._resolved_request, self.sent)
        self.assertIs(child.pending, asyncio.current_task())

    async def test_caller_cannot_replace_valid_same_scope_authenticated_role(self):
        child = self.capture_child()
        _, http = self.resolver_HTTP(self.role)
        with http:
            await child.resolve()
        original = deepcopy(self.original)
        original["original_wake_issued_at_ms"] = child.reservation.created_ms
        original["original_wake_expires_at_ms"] = child.reservation.created_ms + 3600000
        substituted = deepcopy(self.role)
        substituted["authorization_id"] = "different-valid-same-scope-role"
        with self.assertRaises(RichError) as caught:
            await child.seal(prepare=self.prepare, sent_resolve=self.sent, role=substituted, original=original)
        self.assertEqual(caught.exception.status, 403)
        self.assertTrue(child.closed)
        self.assertIsNone(child._resolved_role)
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT phase,consumed_attempts FROM djconnect_host_wake_children")), ("initial_reserved", 1))

    async def test_owned_issuer_claim_matches_actual_SQL_UUID_hash_and_original_task(self):
        child, original = await self.sealed_runtime_child()
        claim = await child.begin_issuer()
        self.assertIs(claim, child._issuer_claim)
        self.assertEqual(child._issuer_request["issuer_operation_id"], claim.attempt_id)
        self.assertEqual(child._issuer_request["original"], original)
        self.assertEqual(claim.request_hash, api.request_hash("issuer/issue", child._issuer_request))
        row = await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT attempt_id,request_hash,kind FROM djconnect_host_wake_attempts WHERE ordinal=2"))
        self.assertEqual(row, (claim.attempt_id, claim.request_hash, "issuer_issue"))
        self.assertIs(child.pending, asyncio.current_task())
        self.assertEqual((child.metadata.phase, child.metadata.consumed_attempts), ("issuing", 2))

    async def test_competing_issuer_request_cannot_close_original_prepare(self):
        child, _ = await self.sealed_runtime_child()
        with self.assertRaises(RichError):
            await asyncio.create_task(child.begin_issuer())
        self.assertFalse(child.closed)
        self.assertEqual(child.metadata.phase, "sealed")
        await child.begin_issuer()

    async def test_issuer_lost_SQL_reply_keeps_consumption_without_RAM_claim(self):
        child, _ = await self.sealed_runtime_child()
        transaction = self.service.async_in_transaction

        async def lost_after_commit(*args, **kwargs):
            await transaction(*args, **kwargs)
            raise OSError("synthetic lost reply")

        with patch.object(self.service, "async_in_transaction", side_effect=lost_after_commit):
            with self.assertRaises(RichError) as caught:
                await child.begin_issuer()
        self.assertEqual(caught.exception.code, "rich_unavailable")
        self.assertTrue(child.closed)
        self.assertIsNone(child._issuer_claim)
        self.assertIsNone(child._original)
        self.assertEqual(await transaction(lambda tx: tx.fetchone(
            "SELECT phase,consumed_attempts FROM djconnect_host_wake_children")), ("issuing", 2))

    async def test_seal_freezes_caller_maps_before_actual_transaction_await(self):
        child = self.capture_child()
        await self.reserve_runtime_child(child)
        original = deepcopy(self.original)
        original["original_wake_issued_at_ms"] = child.reservation.created_ms
        original["original_wake_expires_at_ms"] = child.reservation.created_ms + 3600000
        expected_original, expected_role = digest(original), digest(self.role)
        transaction = self.service.async_in_transaction

        async def mutate_before_SQL(*args, **kwargs):
            original["native_token_sha256"] = "f" * 64
            self.role["authorization_id"] = "caller-mutated-after-await"
            self.sent["scope"]["target"]["installation_id"] = "caller-mutated-after-await"
            self.prepare["target"]["installation_id"] = "caller-mutated-after-await"
            return await transaction(*args, **kwargs)

        with patch.object(self.service, "async_in_transaction", side_effect=mutate_before_SQL):
            result = await child.seal(prepare=self.prepare, sent_resolve=self.sent, role=self.role, original=original)
        self.assertEqual((result.original_hash, result.role_hash), (expected_original, expected_role))
        self.assertEqual(digest(child._original), expected_original)
        self.assertEqual(digest(child._role), expected_role)

    async def test_actual_setup_owns_one_registry_and_capture_spends_before_any_SQL(self):
        registry = self.rich.host_wake_children
        child = self.capture_child()
        self.assertIs(registry.service, self.rich)
        self.assertIs(child.parent, self.parent)
        self.assertIs(child.context, self.parent.context)
        self.assertIs(registry.children[self.parent.original.purpose_id], child)
        self.assertIs(child.pending, asyncio.current_task())
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT count(*) FROM djconnect_host_wake_children")[0]), 0)
        await self.reserve_runtime_child(child)
        self.assertTrue(child.reserved)
        self.assertEqual(child.metadata.phase, "initial_reserved")
        self.assertIs(child.pending, asyncio.current_task())
        self.assertIs(child.initial_attempt, self.ram_attempts[-1])

    async def test_second_prepare_or_fresh_UUID_never_replaces_closed_spent_RAM_scope(self):
        captured = asyncio.Event()
        holder = []

        async def original_request():
            holder.append(self.capture_child())
            captured.set()
            await asyncio.Event().wait()

        worker = asyncio.create_task(original_request())
        await captured.wait()
        child = holder[0]
        child.close()
        with self.assertRaises(asyncio.CancelledError):
            await worker
        changed = deepcopy(self.prepare)
        changed["operation_id"] = str(uuid.uuid4())
        with self.assertRaises(RichError) as caught:
            self.capture_child(changed)
        self.assertEqual(caught.exception.status, 409)
        self.assertIs(self.rich.host_wake_children.children[self.parent.original.purpose_id], child)
        self.assertFalse(self.parent.closed)

    async def test_actual_parent_retirement_synchronously_closes_child_without_metadata_restoration(self):
        reserved = asyncio.Event()
        holder = []

        async def original_request():
            child = self.capture_child()
            holder.append(child)
            await self.reserve_runtime_child(child)
            reserved.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(original_request())
        await reserved.wait()
        child = holder[0]
        self.parent.retire()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(child.closed)
        self.assertIsNone(child.context)
        self.assertIsNone(child.parent)
        self.assertIsNone(child.registry)
        self.assertEqual(child.metadata.phase, "initial_reserved")  # DATA, not a RAM restoration.

    async def test_competing_task_cannot_steal_original_pending_latch_or_retire_it(self):
        child = self.capture_child()
        other = asyncio.create_task(self.reserve_runtime_child(child))
        with self.assertRaises(RichError) as caught:
            await other
        self.assertEqual(caught.exception.status, 409)
        self.assertFalse(child.closed)
        self.assertIs(child.pending, asyncio.current_task())
        await self.reserve_runtime_child(child)

    async def test_cancel_before_first_SQL_run_closes_original_RAM_but_scope_stays_spent(self):
        captured = asyncio.Event()
        parked = asyncio.Event()
        holder = []

        async def original_request():
            holder.append(self.capture_child())
            captured.set()
            await parked.wait()
            await self.reserve_runtime_child(holder[0])

        task = asyncio.create_task(original_request())
        await captured.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)  # Observe original task done-callback cleanup.
        child = holder[0]
        self.assertTrue(child.closed)
        self.assertIsNone(child.context)
        self.assertFalse(self.parent.closed)
        with self.assertRaises(RichError):
            self.capture_child()
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT count(*) FROM djconnect_host_wake_children")[0]), 0)

    async def test_cancel_after_SQL_commit_cannot_publish_RAM_metadata_or_refund_scope(self):
        original = self.service.async_in_transaction
        holder = []

        async def committed_then_cancel(*args, **kwargs):
            result = await original(*args, **kwargs)
            asyncio.current_task().cancel()
            return result

        async def request():
            child = self.capture_child()
            holder.append(child)
            await self.reserve_runtime_child(child)

        with patch.object(self.service, "async_in_transaction", side_effect=committed_then_cancel):
            task = asyncio.create_task(request())
            with self.assertRaises(asyncio.CancelledError):
                await task
        child = holder[0]
        self.assertTrue(child.closed and child.reserved)
        self.assertIsNone(child.metadata)
        rows = await original(lambda tx: tx.fetchall("SELECT phase FROM djconnect_host_wake_children"))
        self.assertEqual(rows, [("initial_reserved",)])
        with self.assertRaises(RichError):
            self.capture_child()

    async def test_zero_capacity_is_closed_without_SQL_or_replacement_registry(self):
        registry = self.rich.host_wake_children
        with patch("custom_components.djconnect.host_wake_child_runtime.MAX_CHILDREN", 0):
            with self.assertRaises(RichError) as caught:
                self.capture_child()
        self.assertEqual(caught.exception.code, "rich_capacity")
        self.assertEqual(registry.children, {})
        self.assertIs(self.rich.host_wake_children, registry)

    async def test_initial_SQL_cannot_use_closed_original_request(self):
        holder = []

        async def request():
            child = self.capture_child()
            holder.append(child)
            self.ram_attempts[-1].close()
            await self.reserve_runtime_child(child)

        worker = asyncio.create_task(request())
        with self.assertRaises((RichError, asyncio.CancelledError)):
            await worker
        self.assertTrue(holder[0].closed)
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT count(*) FROM djconnect_host_wake_children")[0]), 0)
        self.assertFalse(self.parent.closed)

    async def test_original_prebody_deadline_is_not_reanchored_at_SQL_start(self):
        holder = []

        async def request():
            child = self.capture_child()
            holder.append(child)
            # Explicit elapsed-window fixture, not a clock qualification. The
            # actual parent's hours-long local lifetime remains unchanged.
            original = self.ram_attempts[-1]
            original.wall -= 31
            original.mono -= 31
            await self.reserve_runtime_child(child)

        worker = asyncio.create_task(request())
        with self.assertRaises((RichError, asyncio.CancelledError)):
            await worker
        self.assertTrue(holder[0].closed)
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT count(*) FROM djconnect_host_wake_children")[0]), 0)
        self.assertFalse(self.parent.closed)

    async def test_held_unsent_request_close_immediately_scrubs_child_before_task_or_SQL(self):
        holder = []

        async def original_request():
            child = self.capture_child()
            holder.append(child)
            self.ram_attempts[-1].close()
            # Assert synchronously: no SQL/currentness read/taskdone can do the
            # cleanup on our behalf. Closing its pending task is also required.
            self.assertTrue(child.closed)
            for field in ("parent", "context", "registry", "initial_attempt", "pending"):
                self.assertIsNone(getattr(child, field), field)
            self.assertTrue(asyncio.current_task().cancelling())

        task = asyncio.create_task(original_request())
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertIs(self.rich.host_wake_children.children[self.parent.original.purpose_id], holder[0])
        self.assertFalse(self.parent.closed)

    async def test_SQL_success_alone_cannot_release_original_prepare_request_or_its_dependency(self):
        reserved = asyncio.Event()
        holder = []

        async def original_request():
            child = self.capture_child()
            holder.append(child)
            await self.reserve_runtime_child(child)
            reserved.set()
            await asyncio.Event().wait()

        worker = asyncio.create_task(original_request())
        await reserved.wait()
        child, attempt = holder[0], self.ram_attempts[-1]
        self.assertIn(child, attempt.dependents)
        self.assertIn(child, self.parent.dependents)
        self.assertIs(child.initial_attempt, attempt)
        self.assertIs(child.pending, worker)
        attempt.close()
        with self.assertRaises(asyncio.CancelledError):
            await worker
        self.assertTrue(child.closed)
        self.assertFalse(self.parent.closed)
        self.assertIsNone(child.metadata.original_hash)
        self.assertEqual(child.metadata.phase, "initial_reserved")


if __name__ == "__main__":
    unittest.main()
