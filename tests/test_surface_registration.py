"""Pure paired discovery and monotonic negative fences; no positive admission."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.test_http_voice_helpers import install_http_stubs
install_http_stubs()

from custom_components.djconnect import surface_registration as registration  # noqa: E402
from custom_components.djconnect.surface_registration_http import registration_views  # noqa: E402


class Headers(dict):
    def getall(self, key, default):
        value = self.get(key, default)
        return value if type(value) is list else [value]


class Runtime:
    @property
    def config(self):
        raise AssertionError("GET must never construct Profile-backed config")


class PassiveRegistrationTests(unittest.IsolatedAsyncioTestCase):
    def test_actual_HA_fixture_joins_exact_product_and_closed_acceptance(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / 'examples/client_contracts/passive_surface_registration_v1/actual-ha-wire.json').read_text())
        self.assertEqual(proof['status'], 'PASS')
        self.assertEqual(len(proof['source_hashes']), 274)
        for name, digest in proof['source_hashes'].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((root / proof['harness']).read_bytes()).hexdigest(), proof['harness_sha256'])
        self.assertEqual(len(proof['cases']), 12)
        self.assertTrue(proof['actual_temporary_entry_rotation_failed_await_ABA_stays_retired'])
        self.assertEqual(proof['model_calls'], 0)
        self.assertEqual(proof['external_provider_calls'], 0)
        for key in ('installed', 'native', 'provider_activation'):
            self.assertEqual(proof[key], 'NOT_RUN')

    def setUp(self):
        self.entry = SimpleNamespace(entry_id="synthetic-entry", domain="djconnect", disabled_by=None,
            state=SimpleNamespace(value="loaded"), options={}, data={
                "device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios",
                "device_token": "SYNTHETIC-ONLY-ORDINARY-PAIR", "ha_install_id": "synthetic-ha"})
        self.runtime = Runtime()
        self.runtime.entry = self.entry
        self.runtime.device_token = self.entry.data["device_token"]
        self.runtime.pairing_device_id = self.entry.data["device_id"]
        self.runtime.surface_registration_retirement = registration.PairingRetirement()
        self.entries = [self.entry]
        self.hass = SimpleNamespace(is_stopping=False, data={"djconnect": {self.entry.entry_id: self.runtime}},
            config_entries=SimpleNamespace(async_entries=lambda _: self.entries))
        self.headers = Headers({"Authorization": "Bearer " + self.runtime.device_token,
            "X-DJConnect-Device-ID": self.runtime.pairing_device_id, "X-DJConnect-Client-Type": "ios"})

    def request(self, **changes):
        values = dict(headers=self.headers, raw_path="/api/djconnect/v1/surface_registration/widget_transport/state",
                      body_exists=False, can_read_body=False, content_length=None)
        values.update(changes)
        return SimpleNamespace(**values)

    async def test_two_exact_role_routes_authenticate_without_profile_session_or_creation(self):
        before = deepcopy(self.entry.data)
        domain_before = dict(self.hass.data["djconnect"])
        fence = self.runtime.surface_registration_retirement
        for view in registration_views(self.hass):
            with self.subTest(view=view.url):
                reply = await view.get(self.request(raw_path=view.url))
                self.assertEqual(reply.status, 503)
                self.assertEqual(reply.body, b'{"version":1,"state":"UNAVAILABLE"}')
                self.assertEqual(reply.headers["Cache-Control"], "no-store")
        self.assertEqual(len(registration_views(self.hass)), 2)
        self.assertEqual(self.entry.data, before)
        self.assertEqual(self.hass.data["djconnect"], domain_before)
        self.assertEqual((fence.revision, fence.retired), (0, False))

    async def test_no_query_empty_query_body_stream_or_wrong_method(self):
        view = registration_views(self.hass)[0]
        for changes in ({"raw_path": view.url + "?"}, {"raw_path": view.url + "?version=1"},
                        {"body_exists": True}, {"can_read_body": True}, {"content_length": 1},
                        {"headers": {**self.headers, "Transfer-Encoding": "chunked"}}):
            self.assertEqual((await view.get(self.request(**changes))).status, 400)
        reply = await view.unsupported(self.request())
        self.assertEqual(reply.status, 405)
        self.assertEqual(reply.headers["Allow"], "GET")

    async def test_all_critical_header_duplicates_or_missing_rejected(self):
        for key in self.headers:
            for value in ([], [self.headers[key], self.headers[key]]):
                headers = Headers(self.headers)
                headers[key] = value
                with self.assertRaises(registration.RegistrationReadError) as caught:
                    registration.observe_pair(self.hass, headers)
                self.assertEqual(caught.exception.status, 400)

    async def test_no_administrator_purpose_read_or_management_token_substitute(self):
        for token in ("HA-ADMIN", "djcs_" + "A" * 43, "djcsurface_" + "B" * 43, "MANAGEMENT"):
            headers = Headers({**self.headers, "Authorization": "Bearer " + token})
            with self.assertRaises(registration.RegistrationReadError) as caught:
                registration.observe_pair(self.hass, headers)
            self.assertEqual(caught.exception.status, 401)

    async def test_ambiguous_entry_runtime_and_direct_entry_token_mismatch_closed(self):
        original = registration.observe_pair(self.hass, self.headers)
        other = SimpleNamespace(**vars(self.entry))
        other.entry_id = "other"
        second = Runtime()
        second.entry = other
        self.entries.append(other)
        self.hass.data["djconnect"]["other"] = second
        with self.assertRaises(registration.RegistrationReadError):
            registration.observe_pair(self.hass, self.headers)
        self.entries.remove(other)
        self.entry.options = {"device_token": "DIFFERENT"}
        self.assertFalse(original.current(self.hass))
        with self.assertRaises(registration.RegistrationReadError):
            registration.observe_pair(self.hass, self.headers)

    async def test_original_object_and_all_auth_coordinates_rechecked(self):
        for key, value in (("device_id", "djconnect-ios-ZZZZZZ123456"), ("client_type", "macos"),
                           ("device_token", "CHANGED"), ("ha_install_id", "other-ha")):
            captured = registration.observe_pair(self.hass, self.headers)
            previous = self.entry.data[key]
            self.entry.data[key] = value
            self.assertFalse(captured.current(self.hass), key)
            self.entry.data[key] = previous
        for change in (lambda: setattr(self.entry, "options", {}),
                       lambda: setattr(self.entry, "data", dict(self.entry.data)),
                       lambda: setattr(self.runtime, "entry", SimpleNamespace(**vars(self.entry)))):
            captured = registration.observe_pair(self.hass, self.headers)
            change()
            self.assertFalse(captured.current(self.hass))
            self.runtime.entry = self.entry

    async def test_unload_transfer_shutdown_and_final_recheck_closed(self):
        from custom_components.djconnect.retired_provider import TRANSFER_FENCE
        for change in (lambda: setattr(self.hass, "is_stopping", True),
                       lambda: self.hass.data["djconnect"].update({TRANSFER_FENCE: {self.entry.entry_id}}),
                       lambda: setattr(self.entry.state, "value", "not_loaded")):
            snapshot = registration.observe_pair(self.hass, self.headers)
            change()
            self.assertFalse(snapshot.current(self.hass))
            self.hass.is_stopping = False
            self.hass.data["djconnect"].pop(TRANSFER_FENCE, None)
            self.entry.state.value = "loaded"
        view = registration_views(self.hass)[0]
        with patch.object(registration.PairedObservation, "current", side_effect=[True, False]):
            self.assertEqual((await view.get(self.request())).status, 503)

    async def test_change_fence_is_synchronous_terminal_and_duplicates_do_not_reissue(self):
        snapshot = registration.observe_pair(self.hass, self.headers)
        fence = self.runtime.surface_registration_retirement
        registration.fence_pairing_change(self.runtime, token=self.runtime.device_token,
                                          device_id=self.runtime.pairing_device_id)
        self.assertEqual(fence.revision, 0)
        registration.fence_pairing_change(self.runtime, token="NEW-SYNTHETIC-TOKEN")
        self.assertEqual(self.runtime.device_token, self.entry.data["device_token"])
        self.assertTrue(fence.retired)
        self.assertFalse(snapshot.current(self.hass))
        registration.retire_runtime(self.runtime)
        self.assertEqual(fence.revision, 1)
        with self.assertRaises(registration.RegistrationReadError) as caught:
            registration.observe_pair(self.hass, self.headers)
        self.assertEqual(caught.exception.status, 503)
        self.assertNotIn("SYNTHETIC", repr(snapshot))

    async def test_registered_router_has_get_and_rejects_all_other_methods(self):
        calls = []
        router = SimpleNamespace(add_route=lambda *args: calls.append(args))
        for view in registration_views(self.hass):
            view.register(self.hass, None, router)
        self.assertEqual([c[0] for c in calls], ["GET", "*", "GET", "*"])
        self.assertEqual(len({c[1] for c in calls}), 2)
