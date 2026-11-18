"""Actual local pair lifetime; explicitly synthetic HTTP, never external IO."""
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tests import test_direct_rich_context as fixture
from tests.test_direct_rich_pair import Headers
from custom_components.djconnect import direct_rich_runtime as rich
from custom_components.djconnect import host_wake_api as api
from custom_components.djconnect import host_wake_target_wire as target
from custom_components.djconnect.direct_rich_wire import RichError
from custom_components.djconnect.host_wake_proxy_attempt import HostWakeAttempt
from custom_components.djconnect.surface_registration import retire_runtime


class Reply:
    def __init__(self, body=b'{"version":"synthetic-DATA-only"}', status=200, headers=None, before=None):
        self.body, self.status, self.before = body, status, before
        self.headers = headers if headers is not None else Headers({"Content-Type": "application/json"})
        self.content = self
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def iter_chunked(self, size):
        if self.before:
            self.before()
        for at in range(0, len(self.body), size):
            yield self.body[at:at + size]


class Session:
    def __init__(self, reply):
        self.reply, self.calls = reply, []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    def post(self, url, **kwargs):
        self.calls.append((url, {**kwargs, "headers": dict(kwargs["headers"])}))
        return self.reply


class HostWakeApiTests(fixture.DirectRichContextTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        rich.setup_service(self.hass)
        self.rich = self.domain[rich.KEY]
        self.entry.options.update({"djconnect_install_token": "djci_" + "A" * 43,
            "api_base_url": "https://synthetic.invalid"})
        self.attempts = []

    async def asyncTearDown(self):
        for attempt in self.attempts:
            attempt.close()
        self.rich.close()
        await super().asyncTearDown()

    def channel(self):
        attempt = HostWakeAttempt(self.hass, self.headers)
        self.attempts.append(attempt)
        return api.HostWakeApiChannel(attempt)

    @contextmanager
    def http(self, session=None):
        constructor = MagicMock(return_value=session)
        synthetic = SimpleNamespace(ClientSession=constructor, DummyCookieJar=object,
            ClientTimeout=lambda **kwargs: SimpleNamespace(**kwargs))
        with patch.object(api, "aiohttp", synthetic):
            yield constructor

    async def test_existing_local_credentials_exact_bytes_normal_TLS_no_retry_or_bootstrap(self):
        channel, response = self.channel(), Reply()
        session = Session(response)
        with self.http(session) as constructor:
            self.assertEqual(await channel.post("authorization/resolve", b'{}'), (200, response.body))
            self.assertEqual(len(session.calls), 1)
            url, kwargs = session.calls[0]
            self.assertEqual(url, "https://synthetic.invalid" + api.PREFIX + "authorization/resolve")
            self.assertEqual(kwargs["data"], b'{}')
            self.assertFalse(kwargs["allow_redirects"])
            self.assertNotIn("ssl", kwargs)  # No caller CA or disabled verification.
            self.assertEqual(kwargs["headers"], {"Content-Type": "application/json",
                "Authorization": "Bearer djci_" + "A" * 43})
            self.assertFalse(constructor.call_args.kwargs["trust_env"])
            self.assertFalse(constructor.call_args.kwargs["auto_decompress"])
            with self.assertRaises(RichError):
                await channel.post("authorization/resolve", b'{}')
            self.assertEqual(len(session.calls), 1)
        self.assertTrue(session.closed and response.closed)
        self.assertIsNone(channel.original)

    async def test_missing_existing_djci_never_bootstraps_or_opens_HTTP(self):
        self.entry.options.pop("djconnect_install_token")
        with self.http() as constructor, self.assertRaises(RichError):
            self.channel()
        constructor.assert_not_called()

    async def test_fixed_private_routes_and_headers_never_forward_ordinary_device_auth(self):
        channel, session = self.channel(), Session(Reply())
        scope = {"authorization_id": "synthetic-role", "issuer_operation_id": "synthetic-once",
            "core_purpose_id": "synthetic-parent"}
        with self.http(session):
            await channel.post("issuer/status", b'{}', scope)
        headers = session.calls[0][1]["headers"]
        self.assertNotIn("X-DJConnect-Device-ID", headers)
        self.assertNotIn("X-DJConnect-Client-Type", headers)
        self.assertEqual(headers[api.SCOPE_HEADERS["issuer_operation_id"]], "synthetic-once")
        for route in ("../issuer/issue", "issuer/issue?retry=1", "register", "https://other.invalid"):
            with self.subTest(route=route), self.assertRaises(RichError):
                await self.channel().post(route, b'{}', scope)

    async def test_private_target_single_capability_original_event_and_exact_correlation_header(self):
        fixture = json.loads((Path(__file__).parent / "fixtures/host_wake_api_target_18ff8f8.json").read_text())
        scope = {"authorization_id": "fixture-existing-authorization", "issuer_operation_id": "fixture-original-issuer",
            "core_purpose_id": "fixture-original-display"}
        for case in fixture["cases"]:
            response = Reply(body=json.dumps(case["reply"]).encode(), status=case["status"],
                headers=Headers({"Content-Type": "application/json", **case["reply_headers"]}))
            channel, session = self.channel(), Session(response)
            with self.http(session):
                result = await channel.post(case["kind"], json.dumps(case["request"]).encode(), scope,
                    capability="djchw_" + "A" * 43)
            self.assertEqual(result, (case["status"], response.body))
            self.assertEqual(len(session.calls), 1)
            headers = session.calls[0][1]["headers"]
            self.assertEqual(headers, case["request_headers"] | {"Authorization": "Bearer djci_" + "A" * 43})
            self.assertNotIn("X-DJConnect-Device-ID", headers)
            self.assertIsNone(channel.original)

    async def test_missing_duplicate_or_wrong_target_correlation_consumes_attempt_without_retry(self):
        fixture = json.loads((Path(__file__).parent / "fixtures/host_wake_api_target_18ff8f8.json").read_text())
        case = fixture["cases"][0]
        scope = {"authorization_id": "fixture-existing-authorization", "issuer_operation_id": "fixture-original-issuer",
            "core_purpose_id": "fixture-original-display"}
        for values in (None, "0" * 64, [case["request_sha256"]] * 2):
            headers = {"Content-Type": "application/json"}
            if values is not None:
                headers[target.CORRELATION_HEADER] = values
            channel, session = self.channel(), Session(Reply(headers=Headers(headers)))
            with self.http(session), self.assertRaises(RichError):
                await channel.post("register", json.dumps(case["request"]).encode(), scope,
                    capability="djchw_" + "A" * 43)
            self.assertEqual(len(session.calls), 1)
            self.assertTrue(session.closed)
            self.assertIsNone(channel.original)

    async def test_redirect_duplicate_media_compression_empty_oversized_reply_closed(self):
        for response in (Reply(status=302), Reply(headers=Headers({"Content-Type": ["application/json"] * 2})),
                Reply(headers=Headers({"Content-Type": "application/json", "Content-Encoding": "gzip"})),
                Reply(body=b''), Reply(body=b'x' * 16385)):
            channel, session = self.channel(), Session(response)
            attempt = channel.attempt
            with self.http(session), self.assertRaises(RichError):
                await channel.post("authorization/resolve", b'{}')
            self.assertEqual(len(session.calls), 1)
            self.assertTrue(session.closed and response.closed)
            self.assertTrue(attempt.closed)
            self.assertIsNone(channel.attempt)

    async def test_pair_retirement_during_stream_discards_late_response(self):
        channel = self.channel()
        attempt = channel.attempt
        session = Session(Reply(before=lambda: retire_runtime(self.runtime)))
        with self.http(session), self.assertRaises(RichError):
            await channel.post("authorization/resolve", b'{}')
        self.assertTrue(attempt.closed)
        self.assertTrue(session.closed)

    async def test_held_unsent_channel_scrubs_immediately_on_actual_pair_retirement(self):
        channel = self.channel()
        retire_runtime(self.runtime)
        for field in ("original", "runtime", "entry", "attempt"):
            self.assertIsNone(getattr(channel, field))
        with self.http() as constructor, self.assertRaises(RichError):
            await channel.post("authorization/resolve", b'{}')
        constructor.assert_not_called()

    async def test_explicit_attempt_close_and_preflight_error_scrub_held_channel(self):
        channel = self.channel()
        channel.attempt.close()
        self.assertIsNone(channel.original)
        channel.close()
        other = self.channel()
        with self.http() as constructor, self.assertRaises(RichError):
            await other.post("invalid-route", b'{}')
        constructor.assert_not_called()
        for field in ("original", "runtime", "entry", "attempt"):
            self.assertIsNone(getattr(other, field))


if __name__ == "__main__":
    unittest.main()
