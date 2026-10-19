"""Receipt transactions/clock tests; real HA Store/socket qualification is separate."""

import asyncio
from copy import deepcopy
import unittest
from uuid import UUID

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "transport_operation_journal_unit",
    Path(__file__).resolve().parents[1] / "custom_components/djconnect/transport_operations.py",
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
OperationJournal, OperationError, LIFETIME_MS = (
    _module.OperationJournal,
    _module.OperationError,
    _module.LIFETIME_MS,
)


def identifier(ms, sequence=1):
    return str(UUID(int=(ms << 80) | (7 << 76) | (2 << 62) | sequence))


class Store:
    def __init__(self):
        self.data = None
        self.fail = False
        self.fail_after = False

    async def async_load(self):
        return deepcopy(self.data)

    async def async_save(self, data):
        if self.fail:
            raise OSError("synthetic store failure")
        self.data = deepcopy(data)
        if self.fail_after:
            raise OSError("synthetic lost acknowledgement")


class JournalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clock = [1_800_000_000_000, 0]
        self.store = Store()
        self.journal = self.make()
        self.args = dict(
            owner="ownerhash",
            device="devicehash",
            binding="bindinghash",
            identifier=identifier(self.clock[0]),
            epoch=self.journal.epoch,
            operation="command",
            digest="payloaddigest",
        )

    def make(self):
        return OperationJournal(
            self.store, wall_ms=lambda: self.clock[0], monotonic=lambda: self.clock[1]
        )

    async def test_owner_and_global_capacity_never_evict_unexpired_receipts(self):
        for sequence in range(256):
            args = {
                **self.args,
                "owner": "owner-" + str(sequence // 64),
                "identifier": identifier(self.clock[0], sequence + 1),
            }
            key, _, _ = await self.journal.reserve(**args)
            await self.journal.transition(key, "confirmed", response_status=200)
            self.journal.release(key)
            if sequence == 63:
                with self.assertRaises(OperationError) as error:
                    await self.journal.reserve(
                        **{**args, "identifier": identifier(self.clock[0], 1000)}
                    )
                self.assertEqual(error.exception.code, "operation_capacity")
        before = deepcopy(self.store.data)
        with self.assertRaises(OperationError) as error:
            await self.journal.reserve(
                **{**self.args, "owner": "new-owner", "identifier": identifier(self.clock[0], 1001)}
            )
        self.assertEqual(error.exception.code, "operation_capacity")
        self.assertEqual(self.store.data, before)
        self.assertEqual(len(self.store.data["records"]), 256)

    async def test_unknown_store_fields_or_unbounded_error_fail_closed(self):
        key, _, _ = await self.journal.reserve(**self.args)
        valid = deepcopy(self.store.data)
        for extra in (
            {"body": "private body must never be retained"},
            {"error": "private arbitrary sentence"},
            {"response_status": 999},
        ):
            self.store.data = deepcopy(valid)
            self.store.data["records"][key].update(extra)
            with self.assertRaises(OperationError) as error:
                await self.make().status(
                    **{k: v for k, v in self.args.items() if k not in {"operation", "digest"}}
                )
            self.assertEqual(error.exception.code, "operation_unavailable")

    async def test_concurrent_same_identity_reserves_once_and_conflict_never_replaces(self):
        results = await asyncio.gather(*(self.journal.reserve(**self.args) for _ in range(6)))
        self.assertEqual(sum(r[2] for r in results), 1)
        self.assertEqual(len(self.store.data["records"]), 1)
        with self.assertRaises(OperationError) as error:
            await self.journal.reserve(**{**self.args, "digest": "changed"})
        self.assertEqual(error.exception.code, "operation_conflict")

    async def test_original_uuid_cannot_reexecute_after_profile_or_device_change(self):
        key, _, _ = await self.journal.reserve(**self.args)
        await self.journal.transition(key, "confirmed", response_status=200)
        self.journal.release(key)
        before = deepcopy(self.store.data)
        for change in (
            {"owner": "other-owner"},
            {"device": "other-device"},
            {"binding": "other-source"},
        ):
            with self.assertRaises(OperationError) as error:
                await self.journal.reserve(**{**self.args, **change})
            self.assertEqual(error.exception.code, "operation_conflict")
        self.assertEqual(self.store.data, before)

    async def test_gc_and_clock_rollback_cannot_reopen_same_id_even_after_restart(self):
        key, _, _ = await self.journal.reserve(**self.args)
        await self.journal.transition(key, "confirmed", response_status=200)
        self.journal.release(key)
        self.clock[0] += LIFETIME_MS + 1
        self.clock[1] += (LIFETIME_MS + 1) / 1000
        await self.journal.collect_expired()
        self.assertFalse(self.store.data["records"])
        self.clock[0] -= LIFETIME_MS + 1
        with self.assertRaises(OperationError) as e:
            await self.journal.reserve(**self.args)
        self.assertEqual(e.exception.code, "operation_expired")
        restarted = self.make()
        with self.assertRaises(OperationError) as e:
            await restarted.reserve(**{**self.args, "epoch": restarted.epoch})
        self.assertEqual(e.exception.code, "operation_expired")

    async def test_restart_preserves_confirmed_but_not_nonterminal_execution_certainty(self):
        key, _, _ = await self.journal.reserve(**self.args)
        await self.journal.transition(key, "confirmed", response_status=200)
        self.journal.release(key)
        restarted = self.make()
        result = await restarted.status(
            **{k: v for k, v in self.args.items() if k not in {"operation", "digest"}}
        )
        self.assertEqual(result["phase"], "confirmed")
        self.assertFalse(result["result_available"])
        with self.assertRaises(OperationError) as e:
            await restarted.reserve(**self.args)
        self.assertEqual(e.exception.code, "operation_epoch_changed")
        second = {**self.args, "identifier": identifier(self.clock[0], 2), "epoch": restarted.epoch}
        await restarted.reserve(**second)
        again = self.make()
        result = await again.status(
            **{k: v for k, v in second.items() if k not in {"operation", "digest"}}
        )
        self.assertEqual(result["phase"], "unknown")

    async def test_store_failure_before_or_after_write_never_allows_ram_retry(self):
        for after in (False, True):
            self.store = Store()
            self.journal = self.make()
            self.args["epoch"] = self.journal.epoch
            self.store.fail = not after
            self.store.fail_after = after
            with self.assertRaises(OperationError):
                await self.journal.reserve(**self.args)
            self.store.fail = False
            self.store.fail_after = False
            with self.assertRaises(OperationError) as e:
                await self.journal.reserve(**self.args)
            self.assertEqual(e.exception.code, "operation_unavailable")
            reload = self.make()
            if after:
                result = await reload.status(
                    **{k: v for k, v in self.args.items() if k not in {"operation", "digest"}}
                )
                self.assertEqual(result["phase"], "unknown")

    async def test_active_capacity_does_not_evict_dedup_and_expired_active_is_pinned(self):
        keys = []
        for i in range(8):
            key, _, created = await self.journal.reserve(
                **{**self.args, "identifier": identifier(self.clock[0], i + 1)}
            )
            self.assertTrue(created)
            keys.append(key)
        with self.assertRaises(OperationError) as e:
            await self.journal.reserve(**{**self.args, "identifier": identifier(self.clock[0], 9)})
        self.assertEqual(e.exception.code, "operation_capacity")
        self.assertEqual(len(self.store.data["records"]), 8)
        self.clock[0] += LIFETIME_MS + 1
        await self.journal.collect_expired()
        self.assertEqual(len(self.store.data["records"]), 8)
        for key in keys:
            self.journal.release(key)
        await self.journal.collect_expired()
        self.assertFalse(self.store.data["records"])

    async def test_status_does_not_write_and_other_binding_never_gets_receipt(self):
        await self.journal.reserve(**self.args)
        before = deepcopy(self.store.data)
        status = {k: v for k, v in self.args.items() if k not in {"operation", "digest"}}
        await self.journal.status(**status)
        self.assertEqual(self.store.data, before)
        with self.assertRaises(OperationError):
            await self.journal.status(**{**status, "binding": "other"})
        with self.assertRaises(OperationError):
            await self.journal.status(**{**status, "owner": "other"})

    async def test_cancellation_capacity_preserves_existing_fences_and_reclaims_only_expired(self):
        args = {k: v for k, v in self.args.items() if k not in {'operation', 'digest'}}
        for sequence in range(256):
            await self.journal.cancel_reaction(**{**args, 'owner': 'owner-' + str(sequence // 64),
                'identifier': identifier(self.clock[0], sequence + 1)})
            if sequence == 63:
                with self.assertRaises(OperationError) as error:
                    await self.journal.cancel_reaction(**{**args, 'owner': 'owner-0',
                        'identifier': identifier(self.clock[0], 1000)})
                self.assertEqual((error.exception.code, error.exception.status), ('operation_capacity', 429))
        before = deepcopy(self.store.data)
        with self.assertRaises(OperationError) as error:
            await self.journal.cancel_reaction(**{**args, 'owner': 'other',
                'identifier': identifier(self.clock[0], 1001)})
        self.assertEqual(error.exception.code, 'operation_capacity')
        self.assertEqual(self.store.data, before)
        self.clock[0] += LIFETIME_MS + 1
        await self.journal.cancel_reaction(**{**args, 'identifier': identifier(self.clock[0], 1002)})
        self.assertEqual(len(self.store.data['records']), 1)

    async def test_uncertain_cancellation_save_closes_execution_and_retains_persisted_fence(self):
        for after in (False, True):
            self.store = Store()
            journal = self.make()
            args = {k: v for k, v in self.args.items() if k not in {'operation', 'digest'}}
            args['epoch'] = journal.epoch
            self.store.fail, self.store.fail_after = not after, after
            with self.assertRaises(OperationError) as error:
                await journal.cancel_reaction(**args)
            self.assertEqual(error.exception.code, 'operation_unavailable')
            self.store.fail = self.store.fail_after = False
            with self.assertRaises(OperationError) as error:
                await journal.reserve(**{**args, 'operation': 'session/persona/reaction', 'digest': 'original'})
            self.assertEqual(error.exception.code, 'operation_unavailable')
            restarted = self.make()
            if after:
                receipt = await restarted.status(**args)
                self.assertEqual(receipt['phase'], 'cancelled')
                with self.assertRaises(OperationError) as error:
                    await restarted.reserve(**{**args, 'epoch': restarted.epoch,
                        'operation': 'session/persona/reaction', 'digest': 'original'})
                self.assertEqual(error.exception.code, 'operation_conflict')

    async def test_cancellation_of_running_intent_is_terminal_but_completed_receipt_is_preserved(self):
        args = {**self.args, 'operation': 'session/persona/reaction'}
        key, _, _ = await self.journal.reserve(**args)
        target = {k: v for k, v in args.items() if k not in {'operation', 'digest'}}
        await self.journal.cancel_reaction(**target)
        late = await self.journal.transition(key, 'confirmed', response_status=200)
        self.assertEqual(late['phase'], 'cancelled')
        self.journal.release(key)
        args['identifier'] = identifier(self.clock[0], 2)
        key, _, _ = await self.journal.reserve(**args)
        original = await self.journal.transition(key, 'confirmed', response_status=200)
        self.journal.release(key)
        await self.journal.cancel_reaction(**{**target, 'identifier': args['identifier']})
        final = await self.journal.status(**{**target, 'identifier': args['identifier']})
        self.assertEqual(final, original)

    async def test_another_device_same_uuid_cannot_hide_own_cancellation_receipt(self):
        args = {k: v for k, v in self.args.items() if k not in {'operation', 'digest'}}
        await self.journal.cancel_reaction(**args)
        await self.journal.reserve(**{**args, 'device': 'other-device', 'binding': 'other-binding',
            'operation': 'session/persona/reaction', 'digest': 'another-original'})
        receipt = await self.journal.status(**args)
        self.assertEqual(receipt['phase'], 'cancelled')
        self.assertEqual(receipt['error'], 'persona_reaction_withdrawn')
        _, same, created = await self.journal.reserve(**{**args,
            'operation': 'session/persona/reaction', 'digest': 'original'})
        self.assertFalse(created)
        self.assertEqual(same, receipt)
