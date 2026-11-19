"""Durable receipt/rotation races using real journal, synthetic relay only."""

import asyncio
from copy import deepcopy
from dataclasses import replace
import unittest

from tests.test_surface_push_contract import SurfacePushContractTests
from tests.test_transport_operation_journal import Store, identifier

from custom_components.djconnect.surface_push_contract import (
    SurfacePushError,
    validate_registration,
)
from custom_components.djconnect.surface_push_registry import (
    GRANT_SECONDS,
    SurfaceAdmission,
    SurfacePushRegistry,
)
from custom_components.djconnect.transport_operations import OperationJournal


class SurfaceRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fixture = SurfacePushContractTests()
        fixture.setUp()
        self.payload = fixture.payload
        self.clock = [fixture.now, 0]
        self.store = Store()
        self.journal = OperationJournal(
            self.store, wall_ms=lambda: self.clock[0], monotonic=lambda: self.clock[1]
        )
        self.valid = True
        from custom_components.djconnect.surface_push_purpose import SurfacePurposeCredential
        from custom_components.djconnect.surface_push_wire import canonical
        policy = {k:self.payload[k] for k in ("token_role","platform","apns_environment")}
        policy.update(target={k:v for k,v in self.payload["target"].items() if k!="instance_id"},
            activity_profile=None,external_content_allowed=False,
            original_grant_expires_at_ms=self.clock[0]+GRANT_SECONDS*1000,
            max_operations=100,max_events=20,max_challenges=4)
        self.purpose_valid = True
        self.purpose = SurfacePurposeCredential("djcs_"+"A"*43,"https://api.djconnect.dev",
            "capability-synthetic","delegation-synthetic","d"*64,"3"*64,"2"*64,"1"*64,
            "e"*64,"f"*64,canonical(policy),self.clock[0],0.0,lambda:self.purpose_valid,
            wall=lambda:self.clock[0],monotonic=lambda:self.clock[1])
        self.admission = SurfaceAdmission(
            "1"*64,
            "2"*64,
            "3"*64,
            "session-synthetic",
            lambda: self.valid,
            lambda: {"observed_at_ms": fixture.now, "expires_at_ms": fixture.now + 120000},
            purpose=self.purpose,
        )
        self.calls = []
        self.hook = None

        async def relay(action, request, admission):
            self.calls.append((action, deepcopy(request)))
            if self.hook:
                return await self.hook(action, request)
            return self.ack(action, request)

        self.registry = SurfacePushRegistry(self.journal, relay)

    @staticmethod
    def ack(action, request):
        return {
            **{k: request[k] for k in ("registration_id", "generation", "revision", "operation_id")},
            "success": True, "contract_version": 1, "replayed": False,
            "expires_at_ms": request["expires_at_ms"] if action == "register" else 0,
            "state": "registered" if action == "register" else "revoked",
            "operation_state": "registered" if action == "register" else "revoked",
            "current_revision": request["revision"], "provider_status": None,
        }

    def intent(self, sequence=1, **changes):
        return validate_registration(
            {**self.payload, "operation_id": identifier(self.clock[0], sequence), **changes},
            now_ms=self.clock[0],
        )

    async def test_lost_response_replay_recovers_same_original_credential_without_second_send(self):
        intent = self.intent()
        first = await self.registry.register(intent, self.admission)
        replay = await self.registry.register(intent, self.admission)
        self.assertTrue(replay["replayed"])
        self.assertEqual(first["background_read"], replay["background_read"])
        self.assertEqual(len(self.calls), 1)
        encoded = repr(self.store.data)
        self.assertNotIn(self.payload["apns_token"], encoded)
        self.assertNotIn(first["background_read"]["credential"], encoded)
        self.assertFalse(self.journal._active)

    async def test_rotation_invalidates_old_secret_keeps_original_deadline_and_no_replay_new_grant(
        self,
    ):
        original = self.intent()
        first = await self.registry.register(original, self.admission)
        self.clock[0] += 1000
        expected = {
            k: first["registration"][k] for k in ("registration_id", "generation", "revision")
        }
        second = await self.registry.register(
            self.intent(2, expected_registration=expected, apns_token="b" * 64),
            self.admission,
        )
        self.assertEqual(
            first["registration"]["expires_at_ms"], second["registration"]["expires_at_ms"]
        )
        self.assertEqual(second["registration"]["revision"], 2)
        with self.assertRaisesRegex(SurfacePushError, "surface_read_unauthorized"):
            self.registry.read(expected["registration_id"], first["background_read"]["credential"])
        replay = await self.registry.register(original, self.admission)
        self.assertNotIn("background_read", replay)
        self.assertEqual(len(self.calls), 2)

    async def test_read_never_renews_observation_or_registration_and_owner_loss_withdraws(self):
        result = await self.registry.register(self.intent(), self.admission)
        grant = result["background_read"]
        a = self.registry.read(grant["registration_id"], grant["credential"])
        self.clock[0] += 110000
        b = self.registry.read(grant["registration_id"], grant["credential"])
        self.assertEqual(a["passive_session"], b["passive_session"])
        self.assertEqual(a["registration"]["expires_at_ms"], b["registration"]["expires_at_ms"])
        self.valid = False
        with self.assertRaisesRegex(SurfacePushError, "surface_read_withdrawn"):
            self.registry.read(grant["registration_id"], grant["credential"])

    async def test_revoke_while_register_waits_cannot_be_undone_by_late_ack(self):
        entered, finish = asyncio.Event(), asyncio.Event()

        async def hook(action, request):
            if action == "register":
                entered.set()
                await finish.wait()
            return self.ack(action, request)

        self.hook = hook
        task = asyncio.create_task(self.registry.register(self.intent(), self.admission))
        await entered.wait()
        row = next(iter(self.registry._entries.values()))
        result = await self.registry.revoke(
            self.admission,
            row.coordinate(),
            operation_id=identifier(self.clock[0], 2),
            digest="d" * 64,
        )
        self.assertTrue(result["success"])
        self.assertEqual(row.phase, "revoked")
        finish.set()
        with self.assertRaisesRegex(SurfacePushError, "surface_authority_changed"):
            await task
        self.assertEqual(row.phase, "revoked")
        self.assertEqual(row.read_secret, "")
        self.assertFalse(self.journal._active)

    async def test_cancelled_register_is_unknown_not_retryable_and_has_no_read_grant(self):
        entered = asyncio.Event()

        async def hook(action, request):
            entered.set()
            await asyncio.Event().wait()

        self.hook = hook
        intent = self.intent()
        task = asyncio.create_task(self.registry.register(intent, self.admission))
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        replay = await self.registry.register(intent, self.admission)
        self.assertFalse(replay["success"])
        self.assertNotIn("background_read", replay)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(next(iter(self.registry._entries.values())).read_secret, "")
        self.assertFalse(self.journal._active)

    async def test_ack_boolean_version_or_wrong_cas_cannot_activate_registration(self):
        for seq, changes in enumerate(
            (
                {"contract_version": True},
                {"revision": True},
                {"generation": "wrong"},
                {"expires_at_ms": 1},
            ),
            1,
        ):

            async def hook(action, request):
                return {**self.ack(action, request), **changes}

            self.hook = hook
            result = await self.registry.register(
                self.intent(seq, target={**self.payload["target"], "instance_id": f"widget-{seq}"}),
                self.admission,
            )
            self.assertFalse(result["success"])
            self.assertNotIn("background_read", result)
            self.assertEqual(result["registration"]["state"], "unknown")

    async def test_journal_reserve_failure_prevents_any_remote_effect(self):
        self.store.fail = True
        with self.assertRaises(Exception):
            await self.registry.register(self.intent(), self.admission)
        self.assertFalse(self.calls)
        self.assertFalse(self.registry._entries)

    async def test_authority_changed_during_reservation_releases_and_never_sends(self):
        original_save = self.store.async_save

        async def save(data):
            await original_save(data)
            self.valid = False

        self.store.async_save = save
        with self.assertRaisesRegex(SurfacePushError, "surface_authority_changed"):
            await self.registry.register(self.intent(), self.admission)
        self.assertFalse(self.calls)
        self.assertFalse(self.journal._active)

    async def test_original_expiry_withdraws_even_if_register_ack_arrives_after_deadline(self):
        async def hook(action, request):
            self.clock[0] += GRANT_SECONDS * 1000 + 1
            return self.ack(action, request)

        self.hook = hook
        with self.assertRaisesRegex(SurfacePushError, "surface_authority_changed"):
            await self.registry.register(self.intent(), self.admission)
        self.assertFalse(self.journal._active)
        self.assertEqual(next(iter(self.registry._entries.values())).read_secret, "")

    async def test_conflicting_rotation_is_durably_rejected_without_second_network_call(self):
        await self.registry.register(self.intent(), self.admission)
        conflicting = self.intent(2)
        with self.assertRaisesRegex(SurfacePushError, "surface_registration_conflict"):
            await self.registry.register(conflicting, self.admission)
        replay = await self.registry.register(conflicting, self.admission)
        self.assertTrue(replay["replayed"])
        self.assertFalse(replay["success"])
        self.assertEqual(replay["operation"]["phase"], "rejected")
        self.assertNotIn("background_read", replay)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.journal._active)

    async def test_confirm_store_failure_cannot_publish_read_credential(self):
        async def hook(action, request):
            self.store.fail = True
            return self.ack(action, request)

        self.hook = hook
        with self.assertRaises(Exception):
            await self.registry.register(self.intent(), self.admission)
        row = next(iter(self.registry._entries.values()))
        self.assertEqual(row.phase, "withdrawn")
        self.assertEqual(row.read_secret, "")
        self.assertFalse(self.journal._active)
        self.assertEqual(len(self.calls), 1)

    async def test_revoke_reservation_owner_loss_releases_journal_without_remote_effect(self):
        await self.registry.register(self.intent(), self.admission)
        row = next(iter(self.registry._entries.values()))
        original_save = self.store.async_save

        async def save(data):
            await original_save(data)
            self.valid = False

        self.store.async_save = save
        with self.assertRaisesRegex(SurfacePushError, "surface_authority_changed"):
            await self.registry.revoke(
                self.admission,
                row.coordinate(),
                operation_id=identifier(self.clock[0], 2),
                digest="d" * 64,
            )
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.journal._active)

    async def test_unacknowledged_revoke_still_ends_local_read_before_remote_call(self):
        registered = await self.registry.register(self.intent(), self.admission)
        row = next(iter(self.registry._entries.values()))
        original_secret = registered["background_read"]["credential"]

        async def hook(action, request):
            self.assertEqual(row.phase, "revoked")
            self.assertEqual(row.read_secret, "")
            with self.assertRaises(SurfacePushError):
                self.registry.read(row.registration_id, original_secret)
            return {**self.ack(action, request), "contract_version": True}

        self.hook = hook
        result = await self.registry.revoke(
            self.admission,
            row.coordinate(),
            operation_id=identifier(self.clock[0], 2),
            digest="d" * 64,
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["operation"]["phase"], "unknown")
        self.assertEqual(row.phase, "revoked")
        self.assertFalse(self.journal._active)

    async def test_revoke_confirmation_owner_loss_does_not_deliver_receipt(self):
        await self.registry.register(self.intent(), self.admission)
        row = next(iter(self.registry._entries.values()))
        original_save = self.store.async_save

        async def save(data):
            await original_save(data)
            if any(
                r["operation"] == "push/surface/revoke" and r["phase"] == "confirmed"
                for r in data["records"].values()
            ):
                self.valid = False

        self.store.async_save = save
        with self.assertRaisesRegex(SurfacePushError, "surface_authority_changed"):
            await self.registry.revoke(
                self.admission,
                row.coordinate(),
                operation_id=identifier(self.clock[0], 2),
                digest="d" * 64,
            )
        self.assertEqual(row.phase, "revoked")
        self.assertEqual(row.read_secret, "")
        self.assertFalse(self.journal._active)

    async def test_revoke_replay_owner_loss_during_receipt_lookup_denies_delivery(self):
        await self.registry.register(self.intent(), self.admission)
        row = next(iter(self.registry._entries.values()))
        operation_id = identifier(self.clock[0], 2)
        await self.registry.revoke(
            self.admission, row.coordinate(), operation_id=operation_id, digest="d" * 64
        )
        original_reserve = self.journal.reserve

        async def reserve(**kwargs):
            result = await original_reserve(**kwargs)
            self.valid = False
            return result

        self.journal.reserve = reserve
        with self.assertRaisesRegex(SurfacePushError, "surface_authority_changed"):
            await self.registry.revoke(
                self.admission, row.coordinate(), operation_id=operation_id, digest="d" * 64
            )
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(row.phase, "revoked")

    async def test_close_during_durable_reservation_never_recreates_row_or_sends(self):
        saving, resume = asyncio.Event(), asyncio.Event()
        original_save = self.store.async_save

        async def save(data):
            if not saving.is_set():
                saving.set()
                await resume.wait()
            await original_save(data)

        self.store.async_save = save
        task = asyncio.create_task(self.registry.register(self.intent(), self.admission))
        await saving.wait()
        await self.registry.close()
        resume.set()
        with self.assertRaisesRegex(SurfacePushError, "surface_registry_unavailable"):
            await task
        self.assertFalse(self.calls)
        self.assertFalse(self.registry._entries)
        self.assertFalse(self.journal._active)

    async def test_close_revokes_all_local_secrets_and_refuses_replay(self):
        first = await self.registry.register(self.intent(), self.admission)
        await self.registry.close()
        with self.assertRaisesRegex(SurfacePushError, "surface_registry_unavailable"):
            self.registry.read(
                first["registration"]["registration_id"], first["background_read"]["credential"]
            )
        with self.assertRaisesRegex(SurfacePushError, "surface_registry_unavailable"):
            await self.registry.register(self.intent(), self.admission)

    async def test_wrong_original_operation_ACK_cannot_confirm_registration(self):
        async def wrong(action, request):
            return self.ack(action, request) | {"operation_id": identifier(self.clock[0], 99)}
        self.hook = wrong
        result = await self.registry.register(self.intent(), self.admission)
        self.assertFalse(result["success"])
        self.assertNotIn("background_read", result)
        self.assertEqual(result["operation"]["phase"], "unknown")

    async def test_historical_registered_ACK_with_newer_current_revision_cannot_grant(self):
        async def wrong(action, request):
            return self.ack(action, request) | {"current_revision": request["revision"] + 1}
        self.hook = wrong
        result = await self.registry.register(self.intent(), self.admission)
        self.assertFalse(result["success"])
        self.assertNotIn("background_read", result)

    async def test_delayed_registration_keeps_original_purpose_deadline_and_wire_acceptance(self):
        original_expiry = self.clock[0] + GRANT_SECONDS*1000
        self.clock[0] += 1000
        async def checked(action, request):
            self.purpose.authorize(action, request)
            return self.ack(action, request)
        self.hook = checked
        result = await self.registry.register(self.intent(), self.admission)
        self.assertTrue(result["success"])
        self.assertEqual(result["registration"]["expires_at_ms"], original_expiry)

    async def test_revoke_actual_closed_wire_contains_version_and_only_original_coordinate(self):
        from custom_components.djconnect.surface_push_wire import COORDINATE, operation_body
        result = await self.registry.register(self.intent(), self.admission)
        row = self.registry._entries[result["registration"]["registration_id"]]
        async def checked(action, request):
            self.assertEqual(set(request), COORDINATE)
            self.assertEqual(operation_body(action, request, now_ms=self.clock[0]), request)
            return self.ack(action, request)
        self.hook = checked
        result = await self.registry.revoke(self.admission,row.coordinate(),
            operation_id=identifier(self.clock[0],2),digest="d"*64)
        self.assertTrue(result["success"])

    async def test_separate_purpose_withdrawal_during_confirmation_commit_never_returns_read_secret(self):
        original = self.store.async_save
        async def save(data):
            await original(data)
            if any(r["phase"]=="confirmed" for r in data["records"].values()):
                self.purpose.withdraw()
        self.store.async_save = save
        with self.assertRaises(SurfacePushError):
            await self.registry.register(self.intent(),self.admission)
        self.assertTrue(self.valid)
        row = next(iter(self.registry._entries.values()))
        self.assertEqual(row.read_secret, "")
        self.assertFalse(row.live(self.clock[0]))

    async def test_separate_purpose_loss_withdraws_read_and_replay_even_when_pairing_remains(self):
        intent = self.intent()
        result = await self.registry.register(intent,self.admission)
        self.purpose_valid = False
        grant = result["background_read"]
        with self.assertRaises(SurfacePushError):
            self.registry.read(grant["registration_id"],grant["credential"])
        with self.assertRaises(SurfacePushError):
            await self.registry.register(intent,self.admission)
        self.assertTrue(self.valid)

    async def test_replay_with_new_purpose_object_never_recovers_old_background_credential(self):
        intent = self.intent()
        await self.registry.register(intent,self.admission)
        equivalent_new = replace(self.purpose)
        response = await self.registry.register(intent,replace(self.admission,purpose=equivalent_new))
        self.assertFalse(response["success"])
        self.assertNotIn("background_read",response)
        self.assertEqual(len(self.calls),1)
