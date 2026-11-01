"""Real local pair/SQL ownership, synthetic HTTP only; no external effects."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tests import test_host_wake_child_store as fixture
from tests import test_host_wake_api as http_fixture
from custom_components.djconnect import host_wake_api as transport
from custom_components.djconnect import host_wake_api_wire as wire
from custom_components.djconnect import host_wake_child_store as child_store
from custom_components.djconnect import host_wake_withdrawal as negative
from custom_components.djconnect.direct_rich_wire import RichError
from custom_components.djconnect.host_wake_proxy_attempt import HostWakeAttempt
from custom_components.djconnect.surface_registration import retire_runtime


class HostWakeWithdrawalTests(fixture.HostWakeChildStoreTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.entry.options.update({"djconnect_install_token": "djci_" + "A" * 43,
            "api_base_url": "https://synthetic.invalid"})

    def HTTP(self, module, session):
        constructor = MagicMock(return_value=session)
        return constructor, patch.object(module, "aiohttp", SimpleNamespace(ClientSession=constructor,
            DummyCookieJar=object, ClientTimeout=lambda **kwargs: SimpleNamespace(**kwargs)))

    async def acquire(self):
        attempt = HostWakeAttempt(self.hass, self.headers)
        attempt.bind_parent("prepare", self.prepare)
        child = self.rich.host_wake_children.capture(attempt, self.prepare)
        response = http_fixture.Session(http_fixture.Reply(json.dumps(self.role).encode()))
        _, http = self.HTTP(transport, response)
        with http:
            await child.resolve()
        original = deepcopy(self.original)
        original["original_wake_issued_at_ms"] = child.reservation.created_ms
        original["original_wake_expires_at_ms"] = child.reservation.created_ms + 3600000
        await child.seal_resolved(original=original)
        await child.begin_issuer()
        return child, child.capture_withdrawal()

    async def parked_owner(self):
        ready, holder = asyncio.Event(), []

        async def request():
            holder.extend(await self.acquire())
            ready.set()
            await asyncio.Event().wait()

        worker = asyncio.create_task(request())
        # Propagate fixture failures rather than hang awaiting readiness.
        waiter = asyncio.create_task(ready.wait())
        await asyncio.wait((worker, waiter), return_when=asyncio.FIRST_COMPLETED)
        if worker.done():
            waiter.cancel()
            await worker
        await waiter
        return worker, *holder

    def reply(self, port, **changes):
        value = {**port.sent, "request_sha256": wire.request_hash("issuer/withdraw", port.sent),
            "state": "withdrawn", "generation": port.original["generation"], "revision": port.original["revision"],
            **{key: port.original[key] for key in wire.TIMES}, **changes}
        return http_fixture.Session(http_fixture.Reply(json.dumps(value).encode()))

    def scrubbed(self, port):
        self.assertTrue(port.closed and port.used)
        for name in ("hass", "domain", "entry", "data", "options", "service", "runtime", "installation",
                "sent", "original", "proof_kind", "task", "started"):
            self.assertIsNone(getattr(port, name), name)

    async def test_parent_pair_retirement_keeps_only_exact_negative_installation_authority(self):
        worker, child, port = await self.parked_owner()
        session = self.reply(port)
        expected = deepcopy(port.sent)
        retire_runtime(self.runtime)
        with self.assertRaises(asyncio.CancelledError):
            await worker
        self.assertTrue(child.closed)
        self.assertFalse(port.closed)
        constructor, http = self.HTTP(negative, session)
        with http:
            status, reply = await child.withdraw()
        self.assertEqual((status, reply["state"]), (200, "withdrawn"))
        self.assertEqual(len(session.calls), 1)
        url, values = session.calls[0]
        self.assertEqual(url, "https://synthetic.invalid" + wire.PREFIX + "issuer/withdraw")
        self.assertEqual(json.loads(values["data"]), expected)
        self.assertNotIn("X-DJConnect-Host-Wake-Capability", values["headers"])
        self.assertNotIn("X-DJConnect-Device-ID", values["headers"])
        self.assertFalse(values["allow_redirects"])
        self.assertNotIn("ssl", values)
        self.assertFalse(constructor.call_args.kwargs["trust_env"])
        self.assertTrue(session.closed and session.reply.closed)
        self.scrubbed(port)
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT phase,consumed_attempts FROM djconnect_host_wake_children")), ("issuing", 2))

    async def test_cancellation_before_worker_first_run_scrubs_and_never_sends(self):
        worker, child, port = await self.parked_owner()
        constructor, http = self.HTTP(negative, self.reply(port))
        with http:
            task = child.withdraw()
            self.assertTrue(child.closed)  # Local fence precedes scheduling/await.
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0)
        constructor.assert_not_called()
        self.scrubbed(port)
        with self.assertRaises(asyncio.CancelledError):
            await worker
        with self.assertRaises(RichError):
            child.withdraw()

    async def test_options_replacement_even_equal_values_denies_before_HTTP(self):
        worker, child, port = await self.parked_owner()
        constructor, http = self.HTTP(negative, self.reply(port))
        self.entry.options = dict(self.entry.options)
        with http, self.assertRaises(RichError):
            child.withdraw()
        constructor.assert_not_called()
        self.scrubbed(port)
        with self.assertRaises(asyncio.CancelledError):
            await worker

    async def test_entry_unload_scrubs_unsent_port_without_parent_authority(self):
        worker, child, port = await self.parked_owner()
        negative.invalidate_entry(self.entry)
        self.scrubbed(port)
        with self.assertRaises(RichError):
            child.withdraw()
        with self.assertRaises(asyncio.CancelledError):
            await worker

    async def test_service_shutdown_scrubs_even_held_unsent_port(self):
        worker, _, port = await self.parked_owner()
        self.rich.close()
        self.scrubbed(port)
        with self.assertRaises(asyncio.CancelledError):
            await worker

    async def test_original_execution_deadline_includes_time_before_worker_starts(self):
        worker, child, port = await self.parked_owner()
        constructor, http = self.HTTP(negative, self.reply(port))
        with http:
            task = child.withdraw()
            wall, mono = port.started
            with patch.object(negative, "time", SimpleNamespace(time=lambda: float(wall + 31),
                    monotonic=lambda: float(mono + 31))):
                with self.assertRaises(RichError):
                    await task
        constructor.assert_not_called()
        self.scrubbed(port)
        with self.assertRaises(asyncio.CancelledError):
            await worker

    async def test_negative_unknown_is_inconclusive_and_does_not_refund_positive_quota(self):
        worker, child, port = await self.parked_owner()
        session = self.reply(port, state="unknown")
        _, http = self.HTTP(negative, session)
        with http, patch.object(child_store, "MAX_CHILDREN", 0), \
                patch.object(child_store, "MAX_ATTEMPTS", 0), \
                patch.object(self.service, "async_in_transaction", side_effect=AssertionError("No new positive SQL")):
            status, value = await child.withdraw()
        self.assertEqual((status, value["state"]), (200, "unknown"))
        self.scrubbed(port)
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT phase,consumed_attempts FROM djconnect_host_wake_children")), ("issuing", 2))
        with self.assertRaises(asyncio.CancelledError):
            await worker

    async def test_configuration_change_during_reply_stream_cancels_closed_once(self):
        worker, child, port = await self.parked_owner()
        session = self.reply(port)
        session.reply.before = lambda: setattr(self.entry, "options", dict(self.entry.options))
        _, http = self.HTTP(negative, session)
        with http, self.assertRaises(RichError):
            await child.withdraw()
        self.assertEqual(len(session.calls), 1)
        self.assertTrue(session.closed and session.reply.closed)
        self.scrubbed(port)
        with self.assertRaises(asyncio.CancelledError):
            await worker

    async def test_duplicate_during_pending_HTTP_cannot_cancel_original_withdrawal(self):
        worker, child, port = await self.parked_owner()
        session = self.reply(port)
        entered, release = asyncio.Event(), asyncio.Event()
        original_stream = session.reply.iter_chunked

        async def held_stream(size):
            entered.set()
            await release.wait()
            async for chunk in original_stream(size):
                yield chunk

        session.reply.iter_chunked = held_stream
        _, http = self.HTTP(negative, session)
        with http:
            first = child.withdraw()
            await entered.wait()
            try:
                with self.assertRaises(RichError) as caught:
                    child.withdraw()
                self.assertEqual(caught.exception.status, 409)
                self.assertFalse(first.cancelling())
                self.assertFalse(port.closed)
            finally:
                release.set()
                result = await asyncio.gather(first, return_exceptions=True)
                await asyncio.gather(worker, return_exceptions=True)
            self.assertFalse(isinstance(result[0], BaseException))
            self.assertEqual(result[0][1]["state"], "withdrawn")
        self.assertEqual(len(session.calls), 1)
        self.scrubbed(port)

    async def test_wrong_original_reply_is_closed_once_and_never_retried(self):
        worker, child, port = await self.parked_owner()
        session = self.reply(port, issuer_operation_id="different-original")
        _, http = self.HTTP(negative, session)
        with http:
            with self.assertRaises(RichError):
                await child.withdraw()
            with self.assertRaises(RichError):
                child.withdraw()
        self.assertEqual(len(session.calls), 1)
        self.scrubbed(port)
        with self.assertRaises(asyncio.CancelledError):
            await worker
