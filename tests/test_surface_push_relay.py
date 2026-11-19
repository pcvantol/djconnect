"""Synthetic HTTP boundary: one request, closed origin, no bootstrap/redirect."""

import asyncio
from copy import deepcopy
from dataclasses import replace, FrozenInstanceError
import json
import importlib
import types
import sys
import unittest

from tests.test_central_api import install_stubs
from tests.test_transport_operation_journal import identifier

# Scope the import-time SDK bootstrap: its HTTP stub must not become the
# transport of unrelated backend fixtures collected later in the same suite.
_previous_client_module = sys.modules.get("homeassistant.helpers.aiohttp_client")
_previous_client = getattr(_previous_client_module, "async_get_clientsession", None)
install_stubs()
SurfacePushError = importlib.import_module(
    "custom_components.djconnect.surface_push_contract"
).SurfacePushError
relay = importlib.import_module("custom_components.djconnect.surface_push_relay")
if _previous_client_module is not None:
    if _previous_client is None:
        delattr(_previous_client_module, "async_get_clientsession")
    else:
        _previous_client_module.async_get_clientsession = _previous_client


class Content:
    def __init__(self, data):
        self.data = bytearray(data)

    async def read(self, limit):
        chunk = self.data[:limit]
        del self.data[:limit]
        return bytes(chunk)


class Response:
    def __init__(self, body=b'{"success":true}', status=200):
        self.content, self.status = Content(body), status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.config = {
            "api_base_url": "https://api.djconnect.dev",
            "ha_install_id": "ha-synthetic",
            "djconnect_install_token": "djci_synthetic",
        }
        self.runtime = types.SimpleNamespace(config=self.config)
        self.calls = []
        self.response = Response()
        self.valid = True
        self.hook = None

        def post(url, **kwargs):
            self.calls.append((url, kwargs))
            if self.hook:
                return self.hook()
            return self.response

        self.hass = types.SimpleNamespace(session=types.SimpleNamespace(post=post))
        self.original = relay.async_get_clientsession
        relay.async_get_clientsession = lambda hass: hass.session
        from custom_components.djconnect.surface_push_purpose import SurfacePurposeCredential
        from custom_components.djconnect.surface_push_wire import canonical
        self.now = 1792695600000
        self.clock = [self.now, 100.0]
        self.body = {"contract_version":1,"registration_id":"surface-synthetic","generation":"original",
            "revision":1,"operation_id":identifier(self.now,1),"binding_id":"a"*64,
            "device_binding":"b"*64,"owner_binding":"c"*64,"expires_at_ms":self.now+28800000,
            "token_role":"widget","platform":"ios","apns_environment":"sandbox",
            "target":{"instance_id":"synthetic","app_bundle_id":"dev.djconnect.ios",
                "extension_bundle_id":"dev.djconnect.ios.widget","widget_kind":"DJConnectSessionWidget"},
            "apns_token":"a"*64}
        policy = {k:self.body[k] for k in ("token_role","platform","apns_environment")}
        policy.update(target={k:v for k,v in self.body["target"].items() if k!="instance_id"},
            activity_profile=None,external_content_allowed=False,original_grant_expires_at_ms=self.body["expires_at_ms"],
            max_operations=100,max_events=20,max_challenges=4)
        self.purpose = SurfacePurposeCredential("djcs_"+"A"*43,"https://api.djconnect.dev",
            "capability-synthetic","delegation-synthetic","d"*64,"a"*64,"b"*64,"c"*64,
            "e"*64,"f"*64,canonical(policy),self.now,100.0,lambda:self.valid,
            wall=lambda:self.clock[0],monotonic=lambda:self.clock[1])
        self.admission = types.SimpleNamespace(validate=self.validate,purpose=self.purpose)

    async def asyncTearDown(self):
        relay.async_get_clientsession = self.original

    def validate(self):
        if not self.valid:
            raise SurfacePushError("surface_authority_changed", 403)

    async def call(self, action="register", payload=None):
        return await relay.post_once(
            self.hass, self.runtime, action, payload or self.body, self.admission
        )

    async def test_one_call_no_redirect_and_does_not_mutate_config_or_input(self):
        before = deepcopy(self.config)
        payload = deepcopy(self.body)
        result = await self.call(payload=payload)
        self.assertTrue(result["success"])
        self.assertEqual(self.config, before)
        self.assertNotIn("ha_install_id", payload)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.calls[0][1]["allow_redirects"])
        self.assertEqual(self.calls[0][0], "https://api.djconnect.dev/v1/push/surface/register")

    async def test_failure_redirect_and_exception_never_retry_or_return_upstream_text(self):
        for status in (301, 429, 500, 503):
            self.response = Response(
                json.dumps({"error": "private-upstream-text"}).encode(), status
            )
            before = len(self.calls)
            result = await self.call()
            self.assertEqual(len(self.calls), before + 1)
            self.assertEqual(result, {"success": False, "error": "surface_relay_outcome_unknown"})

        def fail():
            raise OSError("secret/token/origin")

        self.hook = fail
        self.assertEqual(
            await self.call(), {"success": False, "error": "surface_relay_outcome_unknown"}
        )

    async def test_missing_purpose_never_bootstraps_or_creates_config(self):
        self.admission.purpose = None
        before = deepcopy(self.config)
        with self.assertRaisesRegex(SurfacePushError, "surface_purpose_unavailable"):
            await self.call()
        self.assertEqual(self.config, before)
        self.assertFalse(self.calls)

    async def test_closed_routes_and_origins_reject_before_network(self):
        for action in ("https://elsewhere.invalid", "../install/token", "rotate", []):
            with self.assertRaises(SurfacePushError):
                await self.call(action)
        for origin in (
            "http://api.djconnect.dev",
            "https://user:pass@api.djconnect.dev",
            "https://api.djconnect.dev/path",
            "https://api.djconnect.dev?q=secret",
        ):
            self.config["api_base_url"] = origin
            with self.assertRaisesRegex(SurfacePushError, "surface_relay_origin_invalid"):
                await self.call()
        self.assertFalse(self.calls)

    async def test_response_size_and_type_are_bounded(self):
        for body in (b" " * 8193, b"[]"):
            self.response = Response(body)
            with self.assertRaisesRegex(SurfacePushError, "surface_relay_response_invalid"):
                await self.call()

    async def test_response_json_cannot_normalize_duplicate_fields_or_non_utf8(self):
        for body in (b'{"success":false,"success":true}',
                     b'{"success":true,"nested":{"revision":1,"revision":2}}',
                     '{"success":true}'.encode("utf-16"),
                     b'{"success":true,"revision":NaN}',
                     b'{"success":true,"revision":1e999}',
                     b'{"success":true,"message":"\\ud800"}'):
            with self.subTest(body=body), self.assertRaisesRegex(
                    SurfacePushError, "surface_relay_response_invalid"):
                self.response = Response(body)
                before = len(self.calls)
                try:
                    await self.call()
                finally:
                    self.assertEqual(len(self.calls), before + 1)

    async def test_authority_withdrawn_during_reply_cannot_accept_result(self):
        def withdraw():
            self.valid = False
            return self.response

        self.hook = withdraw
        with self.assertRaisesRegex(SurfacePushError, "surface_authority_changed"):
            await self.call()
        self.assertEqual(len(self.calls), 1)

    async def test_cancellation_is_propagated_without_retry(self):
        def cancel():
            raise asyncio.CancelledError()

        self.hook = cancel
        with self.assertRaises(asyncio.CancelledError):
            await self.call()
        self.assertEqual(len(self.calls), 1)

    async def test_ordinary_install_bearer_never_grants_surface_relay_authority(self):
        self.admission.purpose = None
        with self.assertRaisesRegex(SurfacePushError, "surface_purpose_unavailable"):
            await self.call()
        self.assertFalse(self.calls)

    async def test_purpose_only_header_exact_body_no_install_identity_or_secret_export(self):
        await self.call()
        sent = self.calls[0][1]
        self.assertEqual(sent["json"], self.body)
        self.assertEqual(sent["headers"]["Authorization"], "Bearer " + self.purpose.bearer)
        self.assertNotIn("djci_", repr(sent))
        self.assertNotIn("ha_install_id", sent["json"])
        self.assertNotIn(self.purpose.bearer, repr(self.purpose))

    async def test_purpose_origin_mismatch_never_sends(self):
        self.config["api_base_url"] = "https://other.invalid"
        with self.assertRaisesRegex(SurfacePushError, "surface_purpose_origin_mismatch"):
            await self.call()
        self.assertFalse(self.calls)

    async def test_expiry_frozen_utc_and_owner_loss_permanently_discard_bearer(self):
        self.clock[1] += 28800
        with self.assertRaisesRegex(SurfacePushError, "surface_purpose_expired"):
            await self.call()
        self.assertEqual(self.purpose.bearer, "")
        self.clock[1] = 100
        with self.assertRaisesRegex(SurfacePushError, "surface_purpose_withdrawn"):
            await self.call()
        self.assertFalse(self.calls)

    async def test_background_and_install_tokens_are_never_purpose_credentials(self):
        for token in ("djci_synthetic", "djcsurface_"+"A"*43, "Bearer root", "djcs_"+"B"*43):
            self.purpose = replace(self.purpose, bearer=token)
            self.admission.purpose = self.purpose
            with self.assertRaises(SurfacePushError):
                await self.call()
        self.assertFalse(self.calls)

    async def test_wrong_binding_policy_or_extended_original_expiry_never_sends(self):
        for patch in ({"owner_binding":"0"*64},{"binding_id":"0"*64},
                      {"expires_at_ms":self.body["expires_at_ms"]+1},
                      {"platform":"macos"}):
            self.purpose = replace(self.purpose, bearer="djcs_"+"A"*43)
            self.admission.purpose = self.purpose
            with self.assertRaises(SurfacePushError):
                await self.call(payload=self.body | patch)
        self.assertFalse(self.calls)

    async def test_admitted_scope_and_original_anchor_cannot_be_mutated_to_renew(self):
        for name,value in (("original_wall_ms",self.now+1000),
                           ("policy_json",self.purpose.policy_json+" "),
                           ("origin","https://other.invalid")):
            with self.assertRaises(FrozenInstanceError):
                setattr(self.purpose,name,value)
