"""Bounded raw HTTP ingress over the actual purpose/SQLite owner."""
import asyncio
import importlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from tests import test_direct_rich_runtime as runtime_fixture
from tests.test_direct_rich_pair import Headers
from tests.test_http_voice_helpers import install_http_stubs


class Content:
    def __init__(self, body, before=None):
        self.body, self.before = body, before

    async def iter_chunked(self, _):
        if self.before is not None:
            await self.before()
        for offset in range(0, len(self.body), 317):
            yield self.body[offset:offset + 317]


class DirectRichHTTPTests(runtime_fixture.DirectRichRuntimeTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        install_http_stubs()
        cls.http = importlib.import_module('custom_components.djconnect.direct_rich_http')

    def request_http(self, kind, payload=None, *, raw=None, headers=None, suffix='', before=None):
        body = raw if raw is not None else json.dumps(payload or self.request).encode()
        values = {**self.headers, 'Content-Type': 'application/json'} if headers is None else headers
        return SimpleNamespace(raw_path=self.http.BASE + '/' + kind + suffix,
            headers=Headers(values), content_length=None, content=Content(body, before))

    async def test_HTTP_actual_authorize_read_and_management_use_separate_roles_and_closed_responses(self):
        response = await self.http.DirectRichView(self.hass, 'authorize').post(self.request_http('authorize'))
        self.assertEqual(response.status, 200)
        issued = json.loads(response.body)
        response = await self.http.DirectRichView(self.hass, 'read').post(self.request_http('read',
            {'contract_version': 1, 'purpose_id': issued['purpose_id']},
            headers=Headers({'Content-Type': 'application/json', 'Authorization': 'Bearer ' + issued['read_credential']})))
        self.assertEqual(response.status, 200)
        self.assertNotIn('read_credential', json.loads(response.body))
        for key, value in self.http.HEADERS.items():
            self.assertEqual(response.headers[key], value)

    async def test_HTTP_duplicates_oversize_and_bad_UTF8_never_reserve_a_purpose(self):
        view = self.http.DirectRichView(self.hass, 'authorize')
        for raw in (b'\xff', b'{"contract_version":1,"contract_version":1}', b' ' * 8193):
            response = await view.post(self.request_http('authorize', raw=raw))
            self.assertEqual(response.status, 400)
            self.assertEqual(json.loads(response.body), {'success': False, 'contract_version': 1, 'error': 'invalid_request'})
            self.assertEqual(self.rich.scopes, {})

    async def test_HTTP_exact_raw_path_browser_and_encoding_guards_are_before_body_IO(self):
        async def forbidden():
            raise AssertionError('body must not be read')
        view = self.http.DirectRichView(self.hass, 'authorize')
        for suffix in ('?', '?access_token=secret', '/', '%2f'):
            response = await view.post(self.request_http('authorize', suffix=suffix, before=forbidden))
            self.assertEqual(response.status, 400)
        for field, value in (('Origin', 'https://foreign.invalid'), ('Cookie', 'private'), ('Content-Encoding', 'gzip')):
            response = await view.post(self.request_http('authorize',
                headers=Headers({**self.headers, 'Content-Type': 'application/json', field: value}), before=forbidden))
            self.assertEqual(response.status, 400)
        self.assertEqual(self.rich.scopes, {})

    async def test_HTTP_original_clock_is_captured_before_first_body_await(self):
        async def before():
            await asyncio.sleep(.003)
        authorize = self.rich.authorize
        capture = []

        async def inspect(payload, headers, captured, **kwargs):
            capture.append(captured)
            return await authorize(payload, headers, captured, **kwargs)

        with patch.object(self.rich, 'authorize', side_effect=inspect):
            response = await self.http.DirectRichView(self.hass, 'authorize').post(
                self.request_http('authorize', before=before))
        self.assertEqual(response.status, 200)
        self.assertEqual(next(iter(self.rich.purposes.values())).wall_start, capture[0][0])

    async def test_HTTP_routes_register_only_exact_POST_and_fixed_no_store_rejections(self):
        routes = []
        router = SimpleNamespace(add_route=lambda *args: routes.append(args))
        for view in self.http.rich_views(self.hass):
            view.register(self.hass, None, router)
            response = await view.unsupported(None)
            self.assertEqual(response.headers['Allow'], 'POST')
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(len(routes), 10)
        self.assertEqual({r[0] for r in routes}, {'POST', '*'})
