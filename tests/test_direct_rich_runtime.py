"""Original purpose / actual paired Profile / real platform SQLite integration."""
import asyncio
from dataclasses import replace
from fractions import Fraction
import time
import unittest
from unittest.mock import patch
import uuid

from tests import test_direct_rich_context as context_fixture
from tests.test_direct_rich_pair import Headers
from custom_components.djconnect import direct_rich_runtime as rich
from custom_components.djconnect.direct_rich_wire import RichError, digest


class DirectRichRuntimeTests(context_fixture.DirectRichContextTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        rich.setup_service(self.hass)
        self.rich = self.domain[rich.KEY]
        self.request = {"contract_version": 1, "operation_id": str(uuid.uuid4()),
            "device_id": self.device, "client_type": "ios", "session_id": self.active.session_id,
            "surface": "widget", "enabled": True, "os_snapshot_cache": True, "locked_display": False}

    async def asyncTearDown(self):
        self.rich.close()
        await super().asyncTearDown()

    async def authorize(self, request=None):
        return await self.rich.authorize(request or self.request, self.headers, (time.time(), time.monotonic()))

    def read(self, result, *, asset=False, **fields):
        prefix = "asset" if asset else "read"
        return self.rich.read({"contract_version": 1, "purpose_id": result["purpose_id"], **fields},
            Headers({"Authorization": "Bearer " + result[prefix + "_credential"]}), asset=asset)

    def management(self):
        return {k: v for k, v in self.request.items() if k not in {"enabled", "os_snapshot_cache", "locked_display"}}

    async def test_authorize_and_read_use_actual_SQL_original_and_never_recover_secrets(self):
        result = await self.authorize()
        read = self.read(result)
        self.assertEqual(read["purpose_id"], result["purpose_id"])
        self.assertEqual(read["purpose_expires_at_ms"], result["purpose_expires_at_ms"])
        self.assertEqual(read["frame"]["frame_id"], result["frame"]["frame_id"])
        self.assertEqual(read["frame"]["frame_id"], digest({k: v for k, v in read["frame"].items() if k != "frame_id"}))
        self.assertNotIn("read_credential", read)
        self.assertNotEqual(result["read_credential"], result["asset_credential"])
        with self.assertRaises(RichError) as caught:
            await self.authorize({**self.request, "operation_id": str(uuid.uuid4())})
        self.assertEqual(caught.exception.code, "rich_purpose_consumed")
        self.rich.close()
        self.domain[rich.KEY] = rich.DirectRichService(self.hass, self.service)
        self.rich = self.domain[rich.KEY]
        with self.assertRaises(RichError) as caught:
            await self.authorize()
        self.assertEqual(caught.exception.code, "rich_purpose_consumed")
        state = await self.rich.manage(self.management(), self.headers)
        self.assertEqual(state["state"], "unknown")
        self.assertNotIn("read_credential", state)

    async def test_role_credentials_and_ambient_identity_never_substitute(self):
        result = await self.authorize()
        request = {"contract_version": 1, "purpose_id": result["purpose_id"]}
        for secret in (result["asset_credential"], "SYNTHETIC-ONLY", "djcrichread_" + "A" * 43):
            with self.assertRaises(RichError):
                self.rich.read(request, Headers({"Authorization": "Bearer " + secret}))
        with self.assertRaises(RichError):
            self.rich.read(request, Headers({"Authorization": "Bearer " + result["read_credential"],
                "X-DJConnect-Device-ID": self.device}))

    async def test_pending_original_latch_prevents_concurrent_or_new_UUID_reissue(self):
        entered, release = asyncio.Event(), asyncio.Event()
        reserve = self.rich.journal.reserve

        async def delayed(*args, **kwargs):
            entered.set()
            await release.wait()
            return await reserve(*args, **kwargs)

        with patch.object(self.rich.journal, "reserve", side_effect=delayed):
            first = asyncio.create_task(self.authorize())
            await entered.wait()
            with self.assertRaises(RichError) as caught:
                await self.authorize({**self.request, "operation_id": str(uuid.uuid4())})
            self.assertEqual(caught.exception.code, "rich_purpose_consumed")
            release.set()
            await first

    async def test_cancel_after_original_SQL_commit_closes_RAM_without_uncancel_or_retry(self):
        issued = self.rich.journal.issued

        async def cancelled(*args, **kwargs):
            await issued(*args, **kwargs)
            asyncio.current_task().cancel()

        with patch.object(self.rich.journal, "issued", side_effect=cancelled):
            task = asyncio.create_task(self.authorize())
            with self.assertRaises(asyncio.CancelledError):
                await task
        purpose = next(iter(self.rich.purposes.values()))
        self.assertTrue(purpose.closed)
        self.assertEqual(purpose.read_secret, "")
        with self.assertRaises(RichError):
            await self.authorize()

    async def test_late_mood_revision_cannot_replace_original_authorize_attempt(self):
        issued = self.rich.journal.issued

        async def changed(*args, **kwargs):
            await issued(*args, **kwargs)
            await self.manager.async_update_mood(owner_profile_id='synthetic-owner',
                session_id=self.active.session_id, selected_mood='energy')

        with patch.object(self.rich.journal, "issued", side_effect=changed):
            with self.assertRaises(RichError):
                await self.authorize()
        purpose = next(iter(self.rich.purposes.values()))
        self.assertTrue(purpose.closed)
        self.assertEqual(purpose.asset_secret, "")

    async def test_real_privacy_intent_scrubs_original_credentials_synchronously(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result["purpose_id"]]
        original = self.storage.household
        owner = original.profiles['synthetic-owner']
        from custom_components.djconnect.domain import ProfilePrivacyMode
        self.storage._household = replace(original, profiles={**original.profiles,
            owner.profile_id: replace(owner, privacy_mode=ProfilePrivacyMode.PRIVATE)})
        self.assertTrue(purpose.closed)
        self.assertIsNone(purpose.context)
        self.assertEqual(purpose.read_secret, "")
        self.storage._household = original
        with self.assertRaises(RichError):
            self.read(result)

    async def test_withdraw_scrubs_before_journal_await_and_preserves_original_operation(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result["purpose_id"]]
        history = self.rich.journal.history

        async def assert_closed(*args, **kwargs):
            self.assertTrue(purpose.closed)
            self.assertEqual(purpose.read_secret, "")
            return await history(*args, **kwargs)

        with patch.object(self.rich.journal, "history", side_effect=assert_closed):
            state = await self.rich.manage(self.management(), self.headers, withdraw=True)
        self.assertEqual(state["state"], "withdrawn")
        self.assertEqual(state["operation_id"], self.request["operation_id"])
        with self.assertRaises(RichError):
            self.read(result)

    async def test_negative_consent_new_operation_withdraws_exact_original_after_restart(self):
        result = await self.authorize()
        self.rich.close()
        self.rich = rich.DirectRichService(self.hass, self.service)
        self.domain[rich.KEY] = self.rich
        with self.assertRaises(RichError) as caught:
            await self.authorize({**self.request, "operation_id": str(uuid.uuid4()), "enabled": False})
        self.assertEqual(caught.exception.code, "rich_not_allowed")
        state = await self.rich.manage(self.management(), self.headers)
        self.assertEqual(state["state"], "withdrawn")
        self.assertEqual(state["purpose_id"], result["purpose_id"])

    async def test_end_closes_local_credentials_but_management_remains_available(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result["purpose_id"]]
        await self.manager.async_end(owner_profile_id='synthetic-owner', session_id=self.active.session_id)
        self.assertTrue(purpose.closed)
        self.assertEqual(purpose.asset_secret, "")
        state = await self.rich.manage(self.management(), self.headers, withdraw=True)
        self.assertEqual(state["state"], "withdrawn")

    async def test_expiry_and_clock_rollback_never_reanchor_original_window(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result["purpose_id"]]
        with patch.object(rich.time, "time", return_value=purpose.wall_start - 1):
            with self.assertRaises(RichError):
                self.read(result)
        self.assertTrue(purpose.closed)
        self.assertEqual(purpose.read_secret, "")

    async def test_original_monotonic_deadline_closes_even_when_wall_is_unchanged(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result["purpose_id"]]
        with patch.object(rich.time, "monotonic", return_value=float(purpose.mono_end) + 1):
            with self.assertRaises(RichError):
                self.read(result)
        self.assertTrue(purpose.closed)
        self.assertEqual(purpose.asset_secret, "")

    async def test_original_pre_body_clock_bounds_purpose_without_receive_time_renewal(self):
        before = (time.time() - 30, time.monotonic() - 30)
        result = await self.rich.authorize(self.request, self.headers, before)
        self.assertLessEqual(result["purpose_expires_at_ms"], (Fraction(before[0]) * 1000 + rich.PURPOSE_MS).__floor__())
        self.assertLess(result["purpose_expires_at_ms"], int(time.time() * 1000) + rich.PURPOSE_MS - 29000)
        self.assertEqual(self.read(result)["purpose_expires_at_ms"], result["purpose_expires_at_ms"])

    async def test_storage_close_and_reopen_scrubs_instead_of_adopting_old_lifetime(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result["purpose_id"]]
        await self.service.async_close()
        await self.service.async_initialize()
        with self.assertRaises(RichError):
            self.read(result)
        self.assertTrue(purpose.closed)
        self.assertEqual(purpose.read_secret, "")

    async def test_genuine_same_content_observation_changes_frame_without_renewing_purpose(self):
        fields = dict(owner_profile_id='synthetic-owner', session_id=self.active.session_id,
            state='playing', media_identity='spotify:track:' + 'A' * 22,
            title='Synthetic track', artist='Synthetic artist')
        await self.manager.async_update_playback_projection(**fields)
        result = await self.authorize()
        first = self.read(result)
        await asyncio.sleep(.003)
        self.assertFalse(await self.manager.async_update_playback_projection(**fields))
        second = self.read(result)
        self.assertEqual(first['frame']['delivery_sequence'], second['frame']['delivery_sequence'])
        self.assertNotEqual(first['frame']['frame_id'], second['frame']['frame_id'])
        self.assertGreater(second['frame']['observed_at_ms'], first['frame']['observed_at_ms'])
        for field in ('purpose_id', 'purpose_issued_at_ms', 'purpose_expires_at_ms'):
            self.assertEqual(first[field], second[field])
        self.assertEqual(second['frame']['now_playing']['track'], 'Synthetic track')

    async def test_known_pending_content_suspends_read_without_changing_original_credentials(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result['purpose_id']]
        self.active.broadcast.content_pending = True
        with self.assertRaises(RichError) as caught:
            self.read(result)
        self.assertEqual(caught.exception.code, 'rich_frame_unavailable')
        self.assertEqual(purpose.read_secret, result['read_credential'])
        self.active.broadcast.content_pending = False
        self.assertEqual(self.read(result)['purpose_id'], result['purpose_id'])

    async def test_wrong_original_management_operation_cannot_withdraw_other_purpose(self):
        result = await self.authorize()
        with self.assertRaises(RichError) as caught:
            await self.rich.manage({**self.management(), 'operation_id': str(uuid.uuid4())},
                self.headers, withdraw=True)
        self.assertEqual(caught.exception.code, 'rich_history_unknown')
        self.assertEqual(self.read(result)['purpose_id'], result['purpose_id'])

    async def test_genuine_withdraw_scrubs_before_pending_cosmetic_Profile_lookup_can_fail(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result['purpose_id']]
        await self.storage._write_lock.acquire()
        queued = asyncio.create_task(self.storage.async_save())
        await asyncio.sleep(0)
        try:
            with self.assertRaises(RichError):
                await self.rich.manage(self.management(), self.headers, withdraw=True)
            self.assertTrue(purpose.closed)
            self.assertEqual(purpose.read_secret, '')
        finally:
            self.storage._write_lock.release()
            await queued
        with self.assertRaises(RichError):
            self.read(result)

    async def test_genuine_disable_scrubs_before_pending_cosmetic_Profile_lookup_can_fail(self):
        result = await self.authorize()
        purpose = self.rich.purposes[result['purpose_id']]
        await self.storage._write_lock.acquire()
        queued = asyncio.create_task(self.storage.async_save())
        await asyncio.sleep(0)
        try:
            with self.assertRaises(RichError):
                await self.authorize({**self.request, 'enabled': False})
            self.assertTrue(purpose.closed)
            self.assertEqual(purpose.asset_secret, '')
        finally:
            self.storage._write_lock.release()
            await queued
        with self.assertRaises(RichError):
            self.read(result)

    async def test_widget_and_locked_Activity_have_distinct_original_scopes_and_negative_fences(self):
        widget = await self.authorize()
        activity_request = {**self.request, 'surface': 'live_activity', 'locked_display': True,
            'operation_id': str(uuid.uuid4())}
        activity = await self.authorize(activity_request)
        self.assertNotEqual(widget['purpose_id'], activity['purpose_id'])
        self.assertNotEqual(widget['read_credential'], activity['read_credential'])
        await self.rich.manage(self.management(), self.headers, withdraw=True)
        with self.assertRaises(RichError):
            self.read(widget)
        self.assertEqual(self.read(activity)['purpose_id'], activity['purpose_id'])
        # Ordinary settings changes retain both the Activity original purpose
        # and its credential; they may produce a new independently current frame.
        await self.manager.async_update_mood(owner_profile_id='synthetic-owner',
            session_id=self.active.session_id, selected_mood='energy')
        refreshed = self.read(activity)
        self.assertEqual(refreshed['purpose_expires_at_ms'], activity['purpose_expires_at_ms'])

    async def test_Activity_without_locked_display_consumes_no_positive_scope(self):
        with self.assertRaises(RichError) as caught:
            await self.authorize({**self.request, 'surface': 'live_activity', 'locked_display': False})
        self.assertEqual(caught.exception.code, 'rich_not_allowed')
        self.assertEqual(self.rich.purposes, {})


if __name__ == "__main__":
    unittest.main()
