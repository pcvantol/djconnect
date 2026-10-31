"""Actual private pair ACK and lifecycle, synthetic identities, no permission."""
import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()

from custom_components.djconnect import direct_rich_pair as pair  # noqa: E402
from custom_components.djconnect.direct_rich_wire import RichError  # noqa: E402
from custom_components.djconnect.persistence import PersistenceService, PERSISTENCE_SERVICE_KEY  # noqa: E402
from custom_components.djconnect.persistence.sqlite import SQLitePersistenceProvider  # noqa: E402
from custom_components.djconnect.surface_pair_journal import schedule_pair_registration  # noqa: E402
from custom_components.djconnect.surface_registration import PairingRetirement, retire_runtime  # noqa: E402


class Headers(dict):
    def getall(self, key, default):
        value = self.get(key, default)
        return value if type(value) is list else [value]


class Runtime:
    @property
    def config(self):
        raise AssertionError('No runtime.config, cold load or auth learning on capture')


class DirectRichPairTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.persistence = PersistenceService(Path(self.temp.name) / 'pair.sqlite', SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        self.entry = SimpleNamespace(entry_id='synthetic-entry', disabled_by=None,
            state=SimpleNamespace(value='loaded'), options={}, data={
                'device_id': 'djconnect-ios-ABCDEF123456', 'client_type': 'ios',
                'device_token': 'SYNTHETIC-ONLY-PAIR', 'ha_install_id': 'synthetic-ha'})
        self.runtime = Runtime()
        self.runtime.entry = self.entry
        self.runtime.device_token = self.entry.data['device_token']
        self.runtime.pairing_device_id = self.entry.data['device_id']
        self.runtime.surface_registration_retirement = PairingRetirement()
        self.entries = [self.entry]
        self.domain = {self.entry.entry_id: self.runtime, PERSISTENCE_SERVICE_KEY: self.persistence}
        self.hass = SimpleNamespace(is_stopping=False, data={'djconnect': self.domain},
            config_entries=SimpleNamespace(async_entries=lambda _: self.entries),
            async_create_task=asyncio.create_task)
        self.headers = Headers({'Authorization': 'Bearer ' + self.runtime.device_token,
            'X-DJConnect-Device-ID': self.runtime.pairing_device_id, 'X-DJConnect-Client-Type': 'ios'})
        schedule_pair_registration(self.hass, self.runtime)
        self.registration = self.runtime.surface_pair_registration
        await self.settle()
        self.assertEqual(self.registration.phase, 'recorded')

    async def settle(self):
        while self.registration.tasks:
            await asyncio.gather(*tuple(self.registration.tasks), return_exceptions=True)

    async def asyncTearDown(self):
        await self.settle()
        await self.persistence.async_close()
        self.temp.cleanup()

    def capture(self, headers=None, **changes):
        identity = {'device_id': self.runtime.pairing_device_id, 'client_type': 'ios', **changes}
        return pair.capture_pair(self.hass, self.headers if headers is None else headers, **identity)

    async def rows(self):
        return await self.persistence.async_in_transaction(lambda tx: tx.fetchall(
            'SELECT binding,auth_generation,state FROM djconnect_surface_pairs'))

    async def test_capture_is_pure_and_uses_original_real_ACK_without_permission(self):
        before = await self.rows()
        with patch.object(self.persistence, 'async_in_transaction', side_effect=AssertionError('No IO')):
            captured = self.capture()
            self.assertTrue(captured.current())
            self.assertIs(captured.acknowledgement, self.registration.acknowledgement)
            self.assertEqual((captured.device_id, captured.client_type),
                (self.runtime.pairing_device_id, 'ios'))
        self.assertEqual(await self.rows(), before)
        self.assertNotIn('SYNTHETIC', repr(captured))
        self.assertFalse(any(hasattr(captured, name) for name in ('credential', 'permission', 'expires_ms')))

    async def test_duplicate_header_wrong_identity_and_ordinary_token_substitution_denied(self):
        for key in self.headers:
            for value in ([], [self.headers[key], self.headers[key]]):
                headers = Headers({**self.headers, key: value})
                with self.subTest(key=key, value=value), self.assertRaises(RichError) as caught:
                    self.capture(headers)
                self.assertEqual(caught.exception.status, 400)
        for token in ('HA-ADMIN', 'djcrichread_' + 'A' * 43, 'djcrichasset_' + 'A' * 43):
            with self.subTest(token=token), self.assertRaises(RichError) as caught:
                self.capture(Headers({**self.headers, 'Authorization': 'Bearer ' + token}))
            self.assertEqual(caught.exception.status, 401)
        for changes in ({'device_id': 'djconnect-ios-000000000000'}, {'client_type': 'macos'},
                {'client_type': {}}, {'device_id': None}):
            with self.subTest(changes=changes), self.assertRaises(RichError):
                self.capture(**changes)

    async def test_missing_pending_retired_or_replaced_ack_never_minted_by_capture(self):
        original = self.registration.acknowledgement
        for state in ('pending', 'unavailable', 'retired'):
            self.registration.phase = state
            with self.subTest(state=state), self.assertRaises(RichError):
                self.capture()
        self.registration.phase = 'recorded'
        self.registration.acknowledgement = None
        with self.assertRaises(RichError):
            self.capture()
        self.assertIsNone(self.registration.acknowledgement)
        self.registration.acknowledgement = original
        captured = self.capture()
        from dataclasses import replace
        self.registration.acknowledgement = replace(original)
        self.assertFalse(captured.current())  # Equal DATA is not its original witness.

    async def test_actual_runtime_retirement_fences_synchronously_and_survives_ABA(self):
        captured = self.capture()
        old = self.runtime.device_token
        retire_runtime(self.runtime)
        self.assertTrue(captured.retired)  # Before background SQLite retirement.
        self.runtime.device_token = 'SYNTHETIC-B'
        self.runtime.device_token = old
        self.assertFalse(captured.current())
        await self.settle()
        with self.assertRaises(RichError):
            self.capture()

    async def test_held_retired_capture_synchronously_scrubs_private_snapshots(self):
        captured = self.capture()
        old_token = self.runtime.device_token
        self.assertIn(old_token, captured.coordinates)
        retire_runtime(self.runtime)
        self.runtime.device_token = 'SYNTHETIC-B'
        self.runtime.device_token = old_token
        self.assertTrue(captured.retired)
        for name in ('hass', 'domain', 'runtime', 'entry', 'data', 'options',
                'coordinates', 'registration', 'acknowledgement', 'persistence',
                'provider', 'readiness', 'path', 'epoch'):
            with self.subTest(name=name):
                self.assertIsNone(getattr(captured, name))
        self.assertNotIn(captured, pair._captures)
        self.assertIsNone(captured.device_id)
        self.assertIsNone(captured.client_type)
        self.assertFalse(captured.current())

    async def test_legacy_family_bit_alone_is_not_parent_auth_revocation(self):
        # That family's bit has no ordinary-auth semantics. The real ACK and
        # exact revision still must be current; no reader replaces either.
        self.runtime.surface_registration_retirement.retired = True
        self.assertTrue(self.capture().current())
        self.runtime.surface_registration_retirement.revision += 1
        with self.assertRaises(RichError):
            self.capture()

    async def test_entry_domain_unload_transfer_and_shutdown_loss_irreversibly_close(self):
        from custom_components.djconnect.retired_provider import TRANSFER_FENCE
        for enter, leave in (
            (lambda: setattr(self.entry, 'data', dict(self.entry.data)), lambda: None),
            (lambda: setattr(self.entry, 'disabled_by', 'user'), lambda: setattr(self.entry, 'disabled_by', None)),
            (lambda: setattr(self.hass, 'is_stopping', True), lambda: setattr(self.hass, 'is_stopping', False)),
            (lambda: self.domain.update({TRANSFER_FENCE: {self.entry.entry_id}}), lambda: self.domain.pop(TRANSFER_FENCE)),
            (lambda: self.hass.data.update({'djconnect': dict(self.domain)}), lambda: self.hass.data.update({'djconnect': self.domain})),
        ):
            captured = self.capture()
            old_data = self.entry.data
            enter()
            self.assertFalse(captured.current())
            leave()
            self.entry.data = old_data
            self.assertFalse(captured.current())

    async def test_duplicate_loaded_device_does_not_select_first_match(self):
        other = SimpleNamespace(**vars(self.entry))
        other.entry_id = 'synthetic-other'
        runtime = Runtime()
        runtime.entry = other
        self.entries.append(other)
        self.domain[other.entry_id] = runtime
        with self.assertRaises(RichError) as caught:
            self.capture()
        self.assertEqual(caught.exception.status, 401)

    async def test_storage_close_reopen_cannot_adopt_old_ACK_even_on_first_capture(self):
        await self.persistence.async_close()
        await self.persistence.async_initialize()
        with self.assertRaises(RichError):
            self.capture()
        self.assertFalse(self.registration.current())

    async def test_storage_provider_or_domain_replacement_is_terminal(self):
        captured = self.capture()
        provider = self.persistence._provider
        self.persistence._provider = SQLitePersistenceProvider()
        self.assertFalse(captured.current())
        self.persistence._provider = provider
        self.assertFalse(captured.current())
        captured = self.capture()
        self.domain[PERSISTENCE_SERVICE_KEY] = object()
        self.assertFalse(captured.current())
        self.domain[PERSISTENCE_SERVICE_KEY] = self.persistence
        self.assertFalse(captured.current())
