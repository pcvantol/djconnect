"""Owning Session HTTP JSON cache policy, including auth and parse errors."""
import asyncio
import importlib
import json
import types
import unittest
from unittest.mock import patch
from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()
http = importlib.import_module('custom_components.djconnect.http')
handlers = importlib.import_module('custom_components.djconnect.api_handlers')


class NativeSessionTransportTest(unittest.TestCase):
    def test_existing_session_http_routes_emit_no_store_on_success_and_errors(self):
        routes = ((http.DJConnectSessionStartView, 'post', 'async_handle_session_start_payload'),
                  (http.DJConnectSessionEndView, 'post', 'async_handle_session_end_payload'),
                  (http.DJConnectActiveSessionView, 'get', 'async_handle_active_session_payload'),
                  (http.DJConnectSessionBroadcastSnapshotView, 'get', 'async_handle_session_broadcast_snapshot_payload'),
                  (http.DJConnectSessionBroadcastTokenView, 'post', 'async_handle_session_broadcast_token_payload'))
        async def payload(): return {'session_id': 'session-1'}
        request = types.SimpleNamespace(json=payload, query={}, app={'hass': object()}, headers={}, context=None)
        for view, method, handler in routes:
            for status in (200, 401, 403, 404, 409):
                async def response(*args, **kwargs):
                    return {'success': status == 200, 'error': None if status == 200 else 'not_authorized'}, status
                with patch.object(handlers, handler, response):
                    call = getattr(view(object()), method)
                    result = asyncio.run(call(request, 'session-1') if view is http.DJConnectSessionBroadcastSnapshotView else call(request))
                self.assertEqual(result.status, status)
                self.assertEqual(result.headers['Cache-Control'], 'no-store')
                self.assertEqual(result.headers['Referrer-Policy'], 'no-referrer')
                self.assertEqual(json.loads(result.text)['success'], status == 200)
        async def invalid(): raise ValueError('invalid json')
        request.json = invalid
        for view, method, _ in routes:
            if method != 'post': continue
            result = asyncio.run(view(object()).post(request))
            self.assertEqual(result.status, 400)
            self.assertEqual(result.headers['Cache-Control'], 'no-store')
