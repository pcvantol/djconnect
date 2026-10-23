"""Closed HTTP adapter tests with a scoped synthetic aiohttp module; zero network."""
import asyncio
import sys
import types
import unittest
from unittest.mock import patch

from tests.test_surface_issuer_owner import capture
from custom_components.djconnect.surface_issuer_transport import IssuerHTTPS
from custom_components.djconnect.surface_issuer_wire import PREFIX
from custom_components.djconnect.surface_push_contract import SurfacePushError


class IssuerHTTPBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original = capture()
        e = self.original.expected
        self.envelope = {'payload': {'contract_version': 1, 'purpose': 'surface_push',
            'action': 'status', 'operation_id': e.operation_id, 'delegation_id': e.delegation_id,
            'delegation_revision': 1, 'key_thumbprint': e.key_thumbprint}, 'signature': 'A' * 86}
        self.calls, self.settings, self.timeout = [], [], []
        self.raw, self.status, self.on_read = b'{"success":false}', 200, None
        self.closed, self.guard_count, self.reads = 0, 0, 0
        self.headers = {'Content-Type': 'application/json'}
        test = self
        class Headers(dict):
            def getall(self, key, default):
                value = self.get(key)
                return default if value is None else value if isinstance(value, list) else [value]
        class Response:
            def __init__(self):
                self.status = test.status
                self.content = self
                self.remaining = bytearray(test.raw)
                self.headers = Headers(test.headers)
            async def __aenter__(self):
                return self
            async def __aexit__(self, *_):
                test.closed += 1
            async def read(self, limit):
                test.reads += 1
                if test.on_read:
                    await test.on_read()
                chunk = bytes(self.remaining[:limit])
                del self.remaining[:limit]
                return chunk
        class Session:
            def __init__(self, **kw):
                test.settings.append(kw)
            async def __aenter__(self):
                return self
            async def __aexit__(self, *_):
                test.closed += 1
            def post(self, url, **kw):
                test.calls.append((url, kw))
                return Response()
        def timeout(**kw):
            test.timeout.append(kw)
            return kw
        self.cookies = object()
        module = types.SimpleNamespace(ClientSession=Session,
            DummyCookieJar=lambda: self.cookies, ClientTimeout=timeout)
        self.module = patch.dict(sys.modules, {'aiohttp': module})
        self.module.start()
        self.addCleanup(self.module.stop)
        self.transport = IssuerHTTPS(monotonic=lambda: 100.0)

    def guard(self):
        self.guard_count += 1

    async def send(self, **kw):
        return await self.transport.post_once(self.original, 'status', self.envelope,
            guard=self.guard, deadline=110.0, **kw)

    async def test_one_exact_origin_post_dedicated_session_no_ambient_authority_or_redirect(self):
        result = await self.send()
        self.assertEqual(result.body, {'success': False})
        self.assertEqual(len(self.calls), 1)
        url, kw = self.calls[0]
        self.assertEqual(url, self.original.origin + PREFIX + 'status')
        self.assertEqual(self.settings[0]['trust_env'], False)
        self.assertIs(self.settings[0]['cookie_jar'], self.cookies)
        self.assertIsNone(self.settings[0]['auth'])
        self.assertIsNone(kw['proxy'])
        self.assertIsNone(kw['auth'])
        self.assertFalse(kw['allow_redirects'])
        self.assertEqual(set(kw['headers']), {'Content-Type', 'Accept', 'Accept-Encoding'})
        self.assertEqual(kw['headers']['Accept-Encoding'], 'identity')
        self.assertNotIn('Authorization', kw['headers'])
        self.assertEqual(self.timeout, [{'total': 10.0}])
        self.assertEqual(self.closed, 2)
        self.assertGreaterEqual(self.guard_count, 6)

    async def test_compression_and_nonjson_rejected_before_any_body_read(self):
        for headers in ({'Content-Type': 'text/html'},
                {'Content-Type': 'application/json', 'Content-Encoding': 'gzip'},
                {'Content-Type': 'application/json', 'Content-Encoding': 'br'},
                {'Content-Type': 'application/json', 'Content-Encoding': 'identity, gzip'},
                {'Content-Type': 'application/json; charset=utf-16'},
                {'Content-Type': ['application/json', 'text/html']},
                {'Content-Type': 'application/json', 'Content-Encoding': ['identity', 'gzip']}, {}):
            self.headers = headers
            before = self.reads
            with self.subTest(headers=headers):
                with self.assertRaises(SurfacePushError):
                    await self.send()
                self.assertEqual(self.reads, before)
        self.assertIs(self.settings[-1].get('auto_decompress'), False)

    async def test_ordinary_json_utf8_identity_positive_control_no_auto_unpacking(self):
        self.headers = {'Content-Type': 'application/json; charset=UTF-8', 'Content-Encoding': 'identity'}
        result = await self.send()
        self.assertEqual(result.body, {'success': False})
        self.assertIs(self.settings[-1].get('auto_decompress'), False)

    async def test_redirect_and_failure_are_unknown_without_retry_or_parsing_body(self):
        for code in (301, 302, 307, 308, 401, 404, 429, 500):
            self.status, self.raw = code, b'private upstream content'
            before = len(self.calls)
            with self.subTest(code=code), self.assertRaisesRegex(SurfacePushError, 'surface_issuer_outcome_unknown'):
                await self.send()
            self.assertEqual(len(self.calls), before + 1)

    async def test_overlarge_or_duplicate_or_nonutf8_response_cannot_become_ack(self):
        for raw in (b'{"x":true,"x":false}', b'{"x":"\xff"}', b' ' * 8193):
            self.raw = raw
            before = len(self.calls)
            with self.subTest(size=len(raw)), self.assertRaises(SurfacePushError):
                await self.send()
            self.assertEqual(len(self.calls), before + 1)

    async def test_original_expiry_before_send_has_zero_session_or_request(self):
        with self.assertRaises(SurfacePushError):
            await self.transport.post_once(self.original, 'status', self.envelope,
                guard=self.guard, deadline=100.0)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.settings, [])

    async def test_owner_loss_during_body_read_blocks_return_and_closes_both_contexts(self):
        def stale():
            raise SurfacePushError('synthetic_original_owner_lost')
        async def read():
            self.guard = stale
        self.on_read = read
        # Transport captures original callable; its underlying authority changes.
        valid = [True]
        def guard():
            if not valid[0]:
                stale()
        async def lose():
            valid[0] = False
        self.on_read = lose
        with self.assertRaises(SurfacePushError):
            await self.transport.post_once(self.original, 'status', self.envelope,
                guard=guard, deadline=110.0)
        self.assertEqual(self.closed, 2)
        self.assertEqual(len(self.calls), 1)

    async def test_cancellation_is_propagated_never_converted_to_ack_or_retry(self):
        async def cancelled():
            raise asyncio.CancelledError
        self.on_read = cancelled
        with self.assertRaises(asyncio.CancelledError):
            await self.send()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.closed, 2)
