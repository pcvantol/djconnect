"""Actual SQL21 parent/once joins, explicit synthetic role DATA, no API effect."""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import time
import unittest
from unittest.mock import patch
import uuid

from tests import test_direct_rich_context as fixture
from custom_components.djconnect import direct_rich_runtime as rich
from custom_components.djconnect import host_wake_api_wire as wire
from custom_components.djconnect.host_wake_child_store import ChildReservation, HostWakeChildJournal
from custom_components.djconnect.host_wake_proxy_wire import request_sha256
from custom_components.djconnect.direct_rich_wire import RichError, digest
from custom_components.djconnect.persistence import PersistenceError


class HostWakeChildStoreTests(fixture.DirectRichContextTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        rich.setup_service(self.hass)
        self.rich = self.domain[rich.KEY]
        display = {"contract_version": 1, "operation_id": str(uuid.uuid4()), "device_id": self.device,
            "client_type": "ios", "session_id": self.active.session_id, "surface": "widget",
            "enabled": True, "os_snapshot_cache": True, "locked_display": False}
        result = await self.rich.authorize(display, self.headers, (time.time(), time.monotonic()))
        self.parent = self.rich.purposes[result["purpose_id"]]
        operation = str(uuid.uuid4())
        self.prepare = {k: display[k] for k in ("contract_version", "device_id", "client_type", "session_id", "surface")} | {
            "purpose_id": result["purpose_id"], "operation_id": operation,
            "target": {"host_bundle_id": "example.fixture.host", "installation_id": "synthetic-native-install"},
            "platform": "ipados", "apns_environment": "sandbox",
            "native_key_id_b64": base64.b64encode(bytes(range(32))).decode(), "native_token_sha256": "a" * 64}
        self.reservation = ChildReservation(self.parent.original, operation, self.parent.generation,
            request_sha256("prepare", self.prepare), self.parent.original.issued_ms)
        context, pair = self.parent.context, self.parent.context.pair
        scope = {k: deepcopy(self.prepare[k]) for k in ("target", "platform", "apns_environment", "native_key_id_b64")}
        scope.update(owner_binding=self.parent.original.owner_hash, device_binding=self.parent.original.device_hash,
            source_binding=digest(["DJC-DIRECT-RICH-SOURCE-V1", dict(context.source)]),
            paired_subject_binding_sha256=digest(["DJC-DIRECT-RICH-PAIRED-SUBJECT-V1", pair.acknowledgement.instance_id,
                pair.acknowledgement.auth_generation, pair.entry.entry_id, pair.device_id, pair.client_type]))
        self.sent = {"version": wire.VERSION, "scope": scope}
        issued = self.reservation.created_ms
        self.role = {"version": wire.VERSION, "resolution": "existing", "authorization_id": "synthetic-role-DATA-NOT-AUTHORITY",
            "request_sha256": wire.request_hash("authorization/resolve", self.sent), "scope_sha256": digest(scope),
            "original_authorization_issued_at_ms": issued - 1, "original_authorization_expires_at_ms": self.parent.original.expires_ms,
            "max_original_purpose_ms": 3600000, "max_operations": 16, "max_reserved_sends": 8,
            "native_proof_kind": "app_attest_assertion", "registration_mode": "single_original_no_rotation",
            "selected_ha_origin_sha256": "b" * 64, "identity_policy_sha256": "c" * 64, "deployment_policy_sha256": "d" * 64}
        self.original = {**deepcopy(scope), **{k: self.role[k] for k in wire.POLICY},
            "version": wire.NATIVE, "core_purpose_id": self.parent.original.purpose_id, "operation_id": operation,
            "generation": self.parent.generation, "revision": 1, "token_role": "host_app_wake",
            "native_token_sha256": self.prepare["native_token_sha256"], "original_wake_issued_at_ms": issued,
            "original_wake_expires_at_ms": issued + 3600000, "original_display_expires_at_ms": self.parent.original.expires_ms}
        self.journal = HostWakeChildJournal(self.service)
        self.args = {"session_id": self.active.session_id, "owner_id": "synthetic-owner", "current": self.positive_current}

    async def asyncTearDown(self):
        self.rich.close()
        await super().asyncTearDown()

    def positive_current(self):
        return self.rich._purpose_current(self.parent) and self.parent.context is not None and self.parent.context._inspect() is not None

    async def reserve_child(self, reservation=None, **changes):
        return await self.journal.reserve(reservation or self.reservation, **(self.args | changes),
            role_request_hash=self.role["request_sha256"], attempt_id=str(uuid.uuid4()))

    async def seal_child(self, **changes):
        values = {"prepare": self.prepare, "sent_resolve": self.sent, "role": self.role, "original": self.original}
        return await self.journal.seal(self.reservation, **self.args, **(values | changes))

    async def begin_stage(self, kind, **changes):
        metadata = await self.journal.history(self.reservation, **self.args)
        values = {"expected_revision": metadata.cas_revision, "kind": kind,
            "semantic_hash": digest([kind, str(uuid.uuid4())]), "request_hash": "e" * 64,
            "attempt_id": str(uuid.uuid4())}
        return await self.journal.begin(self.reservation, **self.args, **(values | changes))

    async def finish_stage(self, attempt, destination, **changes):
        return await self.journal.finish(self.reservation, attempt, destination=destination,
            result_hash="f" * 64, **(self.args | changes))

    async def prepare_sealed(self):
        await self.reserve_child()
        return await self.seal_child()

    async def test_journal_seal_freezes_validated_DATA_before_transaction_await(self):
        await self.reserve_child()
        expected = (digest(self.original), digest(self.role))
        transaction = self.service.async_in_transaction

        async def mutate_after_validation(*args, **kwargs):
            self.original["native_token_sha256"] = "f" * 64
            self.role["authorization_id"] = "changed-after-validation"
            self.sent["scope"]["target"]["installation_id"] = "changed-after-validation"
            self.prepare["target"]["installation_id"] = "changed-after-validation"
            return await transaction(*args, **kwargs)

        with patch.object(self.service, "async_in_transaction", side_effect=mutate_after_validation):
            result = await self.seal_child()
        self.assertEqual((result.original_hash, result.role_hash), expected)

    async def advance_metadata_to_pending_native(self):
        # Synthetic ACK metadata validates SQL transitions only. This never
        # constructs a native permission, SDK proof or operational RAM child.
        await self.prepare_sealed()
        for kind, destination in (("issuer_issue", "prepared"), ("native_challenge", "challenge_known"),
                ("native_complete", "verifying")):
            await self.finish_stage(await self.begin_stage(kind), destination)

    async def test_concurrent_original_CAS_has_one_winner_and_no_second_issue(self):
        sealed = await self.prepare_sealed()
        outcomes = await asyncio.gather(*(self.begin_stage("issuer_issue", expected_revision=sealed.cas_revision)
            for _ in range(2)), return_exceptions=True)
        self.assertEqual(sum(not isinstance(value, BaseException) for value in outcomes), 1)
        self.assertEqual(sum(isinstance(value, RichError) for value in outcomes), 1)
        with self.assertRaises(RichError):
            await self.begin_stage("issuer_issue")
        metadata = await self.journal.history(self.reservation, **self.args)
        self.assertEqual((metadata.phase, metadata.consumed_attempts), ("issuing", 2))

    async def test_exact_pending_claim_is_required_and_completed_ACK_cannot_repeat(self):
        await self.prepare_sealed()
        claim = await self.begin_stage("issuer_issue")
        for changed in (replace(claim, attempt_id=str(uuid.uuid4())), replace(claim, request_hash="a" * 64),
                replace(claim, semantic_hash="b" * 64), replace(claim, pending_revision=claim.pending_revision + 1)):
            with self.subTest(changed=changed), self.assertRaises(RichError):
                await self.finish_stage(changed, "prepared")
        with self.assertRaises(RichError):
            await self.finish_stage(claim, "registered")
        metadata = await self.finish_stage(claim, "prepared")
        self.assertEqual(metadata.phase, "prepared")
        with self.assertRaises(RichError):
            await self.finish_stage(claim, "prepared")

    async def test_status_cannot_turn_issuer_or_unknown_history_into_registration(self):
        await self.prepare_sealed()
        for kind in ("issuer_status", "native_status", "target_status"):
            claim = await self.begin_stage(kind)
            for destination in ("prepared", "native_verified", "registered"):
                with self.subTest(kind=kind, destination=destination), self.assertRaises(RichError):
                    await self.finish_stage(claim, destination)
            await self.finish_stage(claim, "sealed")
        issued = await self.begin_stage("issuer_issue")
        unknown = await self.journal.unknown(self.reservation, **self.args)
        self.assertEqual((unknown.phase, unknown.consumed_attempts), ("unknown", 5))
        with self.assertRaises(RichError):
            await self.finish_stage(issued, "prepared")
        with self.assertRaises(RichError):
            await self.begin_stage("issuer_issue")
        claim = await self.begin_stage("native_status")
        with self.assertRaises(RichError):
            await self.finish_stage(claim, "native_verified")
        await self.finish_stage(claim, "unknown")

    async def test_known_pending_native_status_advances_only_with_original_completed_job(self):
        await self.advance_metadata_to_pending_native()
        claim = await self.begin_stage("native_status")
        metadata = await self.finish_stage(claim, "native_verified")
        self.assertEqual(metadata.phase, "native_verified")
        with self.assertRaises(RichError):
            await self.begin_stage("target_wake")
        metadata = await self.finish_stage(await self.begin_stage("target_register"), "registered")
        self.assertEqual(metadata.phase, "registered")
        with self.assertRaises(RichError):
            await self.begin_stage("target_register")

    async def test_native_status_positive_advance_denies_ended_actual_parent(self):
        await self.advance_metadata_to_pending_native()
        claim = await self.begin_stage("native_status")
        await self.manager.async_end(owner_profile_id="synthetic-owner", session_id=self.active.session_id)
        negative = {"current": lambda: self.service.readiness.ready}
        with self.assertRaises(RichError):
            await self.finish_stage(claim, "native_verified", **negative)
        result = await self.journal.history(self.reservation, **(self.args | negative), withdraw=True)
        self.assertEqual(result.phase, "withdrawn")

    async def test_full_attempt_budget_does_not_block_unknown_or_withdraw_or_refill(self):
        await self.prepare_sealed()
        claim = await self.begin_stage("issuer_issue")
        # Global quota seam on this disposable DB, while retaining genuine rows.
        with patch("custom_components.djconnect.host_wake_child_store.MAX_ATTEMPTS", 2):
            with self.assertRaises(RichError):
                await self.begin_stage("issuer_status")
            result = await self.journal.unknown(self.reservation, **self.args)
            self.assertEqual((result.phase, result.consumed_attempts), ("unknown", 2))
            result = await self.journal.history(self.reservation, **self.args, withdraw=True)
            self.assertEqual((result.phase, result.consumed_attempts), ("withdrawn", 2))
        with self.assertRaises(RichError):
            await self.finish_stage(claim, "prepared")
        parent_row = await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT phase FROM djconnect_rich_purposes WHERE purpose_id=?", (self.parent.original.purpose_id,)))
        self.assertEqual(parent_row[0], "issued")

    async def test_same_semantic_wake_cannot_be_replayed_with_fresh_attempt_UUID(self):
        await self.advance_metadata_to_pending_native()
        await self.finish_stage(await self.begin_stage("native_status"), "native_verified")
        await self.finish_stage(await self.begin_stage("target_register"), "registered")
        semantic = digest(["synthetic-original-broadcast-event", 1])
        claim = await self.begin_stage("target_wake", semantic_hash=semantic)
        await self.finish_stage(claim, "registered")
        with self.assertRaises(RichError):
            await self.begin_stage("target_wake", semantic_hash=semantic)
        next_claim = await self.begin_stage("target_wake", semantic_hash=digest(["synthetic-original-broadcast-event", 2]))
        self.assertEqual(next_claim.ordinal, claim.ordinal + 1)

    async def test_actual_SQL_initial_reservation_contains_no_placeholder_original_or_secret(self):
        metadata = await self.reserve_child()
        self.assertEqual((metadata.phase, metadata.cas_revision, metadata.consumed_attempts), ("initial_reserved", 0, 1))
        self.assertIsNone(metadata.original_hash)
        self.assertIsNone(metadata.expires_ms)
        rows = await self.service.async_in_transaction(lambda tx: tx.fetchall("SELECT * FROM djconnect_host_wake_children"))
        text = repr(rows)
        for private in (self.prepare["native_key_id_b64"], self.prepare["target"]["installation_id"], "djci_", "djchw_", "nonce", "proof"):
            self.assertNotIn(private, text)
        self.assertFalse(hasattr(metadata, "credential"))

    async def test_same_parent_new_UUID_or_fresh_journal_never_reissues(self):
        await self.reserve_child()
        for journal in (self.journal, HostWakeChildJournal(self.service)):
            self.journal = journal
            with self.assertRaises(RichError) as caught:
                await self.reserve_child(replace(self.reservation, native_operation_id=str(uuid.uuid4())))
            self.assertEqual(caught.exception.status, 409)

    async def test_wrong_actual_parent_owner_session_and_phase_have_no_row_or_role_lookup(self):
        for changes in ({"owner_id": "another-owner"}, {"session_id": "another-session"}):
            with self.subTest(changes=changes), self.assertRaises(RichError):
                await self.reserve_child(**changes)
        await self.service.async_in_transaction(lambda tx: tx.execute(
            "UPDATE djconnect_rich_purposes SET phase='withdrawn' WHERE purpose_id=?", (self.parent.original.purpose_id,)))
        with self.assertRaises(RichError):
            await self.reserve_child()
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT count(*) FROM djconnect_host_wake_children")[0]), 0)

    async def test_one_seal_joins_actual_parent_request_role_and_original_without_renewal(self):
        await self.reserve_child()
        metadata = await self.seal_child()
        self.assertEqual((metadata.phase, metadata.cas_revision, metadata.consumed_attempts), ("sealed", 1, 1))
        self.assertEqual(metadata.original_hash, digest(self.original))
        with self.assertRaises(RichError):
            await self.seal_child()
        self.assertEqual((await self.journal.history(self.reservation, **self.args)).expires_ms,
            self.original["original_wake_expires_at_ms"])

    async def test_seal_denies_changed_original_or_reanchored_deadline(self):
        await self.reserve_child()
        for field, value in (("owner_binding", "e" * 64), ("native_token_sha256", "e" * 64),
                ("original_wake_issued_at_ms", self.reservation.created_ms + 1),
                ("original_wake_expires_at_ms", self.parent.original.expires_ms)):
            changed = deepcopy(self.original)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(RichError):
                await self.seal_child(original=changed)
        self.assertEqual((await self.journal.history(self.reservation, **self.args)).phase, "initial_reserved")

    async def test_actual_DDL_rejects_sealed_original_with_NULL_expiry(self):
        await self.reserve_child()
        with self.assertRaises(PersistenceError):
            await self.service.async_in_transaction(lambda tx: tx.execute(
                "UPDATE djconnect_host_wake_children SET original_hash=?,role_hash=?,phase='sealed',"
                "expires_ms=NULL,cas_revision=1 WHERE parent_purpose_id=?",
                ("b" * 64, "c" * 64, self.parent.original.purpose_id)))

    async def test_partial_or_corrupt_sealed_readback_is_closed_not_a_metadata_handle(self):
        await self.reserve_child()

        def corrupt_disposable_database(tx):
            # Synthetic disposable corruption probe only, never a production
            # recovery path. Restore enforcement before leaving this transaction.
            tx.execute("PRAGMA ignore_check_constraints=ON")
            try:
                tx.execute("UPDATE djconnect_host_wake_children SET original_hash=?,role_hash=?,phase='sealed',"
                    "expires_ms=NULL,cas_revision=1 WHERE parent_purpose_id=?",
                    ("b" * 64, "c" * 64, self.parent.original.purpose_id))
            finally:
                tx.execute("PRAGMA ignore_check_constraints=OFF")

        await self.service.async_in_transaction(corrupt_disposable_database)
        with self.assertRaises(RichError):
            await self.journal.history(self.reservation, **self.args)

    async def test_committed_reservation_then_cancel_remains_consumed_without_RAM_handle(self):
        transaction = self.service.async_in_transaction

        async def commit_then_cancel(*args, **kwargs):
            result = await transaction(*args, **kwargs)
            asyncio.current_task().cancel()
            return result

        with patch.object(self.service, "async_in_transaction", side_effect=commit_then_cancel):
            worker = asyncio.create_task(self.reserve_child())
            with self.assertRaises(asyncio.CancelledError):
                await worker
        self.assertEqual((await self.journal.history(self.reservation, **self.args)).phase, "initial_reserved")
        with self.assertRaises(RichError):
            await self.reserve_child(replace(self.reservation, native_operation_id=str(uuid.uuid4())))

    async def test_full_quota_and_real_parent_end_still_allow_reserved_negative_terminal_update(self):
        await self.reserve_child()
        await self.service.async_in_transaction(lambda tx: tx.execute(
            "UPDATE djconnect_host_wake_children SET consumed_attempts=256 WHERE parent_purpose_id=?",
            (self.parent.original.purpose_id,)))
        await self.manager.async_end(owner_profile_id="synthetic-owner", session_id=self.active.session_id)
        # Storage-only callback qualifies this journal test, NOT a production
        # Core-installation negative transport/admission port.
        negative = self.args | {"current": lambda: self.service.readiness.ready}
        result = await self.journal.history(self.reservation, **negative, withdraw=True)
        self.assertEqual((result.phase, result.consumed_attempts), ("withdrawn", 256))
        self.assertEqual(await self.service.async_in_transaction(lambda tx: tx.fetchone(
            "SELECT count(*) FROM djconnect_host_wake_attempts")[0]), 1)
        self.assertEqual(await self.journal.history(self.reservation, **negative, withdraw=True), result)


if __name__ == "__main__":
    unittest.main()
