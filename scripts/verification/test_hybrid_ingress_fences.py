"""Focused race units, separate from the real HA transport acceptance chain.

Run under the owned HA image. Authority/dispatcher fixtures isolate the final
fence ordering; these units are not presented as genuine pairing/dispatch proof.
"""

import asyncio
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from custom_components.djconnect import hybrid_service as service
from custom_components.djconnect import hybrid_transport as transport
from custom_components.djconnect import hybrid_ingress_qualification as qualification
from custom_components.djconnect.transport_delivery import OwnerDeliveryResult


class FinalIngressFenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / qualification.FILENAME
        self.path.write_text("{}")
        self.path.chmod(0o600)
        self.grant = {"stamp": qualification.read_qualification(self.directory.name)[2], "expires_at": time.time() + 60}

    def check_now(self):
        if not qualification.qualification_current_now(self.directory.name, self.grant):
            raise service.OperationError("transport_security_required", 426)

    def fixture_authority(self):
        check = self.check_now

        class Authority:
            async def validate(self):
                await asyncio.sleep(0)
                check()

            def validate_now(self):
                check()

        return Authority()

    async def test_owner_resolve_await_cannot_outlive_ingress_withdrawal(self):
        authority = object.__new__(service.PairedAuthority)
        authority.hass, authority.identity, authority.headers = None, {}, {}
        authority.runtime, authority.binding = object(), "unit-binding"
        authority.owner_final_guard = lambda: None
        authority.transport_guard_now = self.check_now
        authority.transport_guard = AsyncMock(side_effect=self.check_now)

        async def resolve(*_args):
            self.path.unlink()
            await asyncio.sleep(0)
            return SimpleNamespace(runtime=authority.runtime, binding=authority.binding)

        with patch.object(service.PairedAuthority, "resolve", AsyncMock(side_effect=resolve)):
            with self.assertRaises(service.OperationError):
                await authority.validate()

    async def test_owner_revoked_during_last_ingress_await_is_denied(self):
        authority = object.__new__(service.PairedAuthority)
        authority.hass, authority.identity, authority.headers = None, {}, {}
        authority.runtime, authority.binding = object(), "unit-binding"
        entered, release = asyncio.Event(), asyncio.Event()
        revoked = False

        def owner_final():
            if revoked:
                raise service.OperationError("unauthorized", 401)

        async def ingress():
            entered.set()
            await release.wait()
            self.check_now()

        authority.owner_final_guard = owner_final
        authority.transport_guard = ingress
        authority.transport_guard_now = self.check_now
        current = SimpleNamespace(runtime=authority.runtime, binding=authority.binding)
        with patch.object(service.PairedAuthority, "resolve", AsyncMock(return_value=current)):
            pending = asyncio.create_task(authority.validate())
            await entered.wait()
            revoked = True
            release.set()
            with self.assertRaises(service.OperationError) as caught:
                await pending
            self.assertEqual(caught.exception.code, "unauthorized")

    async def delivery_race(self, *, expiry):
        authority = self.fixture_authority()

        async def owner_admission():
            await asyncio.sleep(0)
            if expiry:
                self.grant["expires_at"] = time.time() - 1
            else:
                self.path.unlink()

        result = OwnerDeliveryResult({"success": True, "text": "unit-private-body", "operation_receipt": {"phase": "confirmed"}}, [owner_admission])
        manager = SimpleNamespace(execute=AsyncMock(return_value=(result, 200)))
        request = SimpleNamespace(headers={})
        with (
            patch.object(transport, "request_error", AsyncMock(return_value=None)),
            patch.object(transport, "json_body", AsyncMock(return_value={"identity": {}})),
            patch.object(transport.PairedAuthority, "resolve", AsyncMock(return_value=authority)),
            patch.object(transport, "bind_ingress_guard"),
            patch.object(transport, "operations", return_value=manager),
        ):
            response = await transport.HybridOperationView(object()).post(request)
        self.assertEqual(response.status, 426)
        self.assertNotIn(b"unit-private-body", response.body)

    async def test_withdrawal_during_admitted_body_never_releases_private_http(self):
        await self.delivery_race(expiry=False)

    async def test_expiry_during_admitted_body_never_releases_private_http(self):
        await self.delivery_race(expiry=True)

    async def test_last_ask_dj_owner_await_cannot_cross_final_effect_fence(self):
        from custom_components.djconnect.ask_dj import dialogue

        authority = self.fixture_authority()
        journal = SimpleNamespace(_failed=False, _state={"records": {"key": {"operation_id": "unit"}}}, _validate_time=lambda _value: None)
        manager = SimpleNamespace(journal=journal)
        guards = 0

        async def owner_guard():
            nonlocal guards
            guards += 1
            await asyncio.sleep(0)
            if guards == 2:
                self.path.unlink()

        turn = SimpleNamespace(guard=owner_guard, effect_started=True, require_effect=lambda *_a, **_k: None)
        op_token = service._current_operation.set([manager, "key", authority])
        turn_token = dialogue.current_turn.set(turn)
        effect_token = dialogue.current_effect.set(SimpleNamespace(family="next", value=None))
        try:
            with patch.object(service, "guard_transport_effect", AsyncMock()):
                with self.assertRaises(service.OperationError):
                    await dialogue.guard_effect_dispatch(method="POST", path="/me/player/next")
            self.assertEqual(guards, 2)
        finally:
            dialogue.current_effect.reset(effect_token)
            dialogue.current_turn.reset(turn_token)
            service._current_operation.reset(op_token)


if __name__ == "__main__":
    unittest.main()
