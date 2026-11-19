"""Real aiohttp/HA adapter probe in an isolated dependency runtime, not HA E2E.

Run with the HA image and this checkout mounted read-only. No provider/network,
HA startup, auth acceptance or installed/native claim is made by this probe.
"""
import importlib
import asyncio
import json
import secrets
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from multidict import CIMultiDict
from pathlib import Path
import sys
import types


class _Content:
    def __init__(self, value):
        self.value = value

    async def iter_chunked(self, size):
        for offset in range(0, len(self.value), size):
            yield self.value[offset:offset + size]


class DisplayTransportTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        root = types.ModuleType("custom_components")
        root.__path__ = [str(Path(__file__).resolve().parents[2] / "custom_components")]
        sys.modules.setdefault("custom_components", root)
        package = types.ModuleType("custom_components.djconnect")
        package.__path__ = [str(Path(__file__).resolve().parents[2] / "custom_components/djconnect")]
        sys.modules.setdefault("custom_components.djconnect", package)
        cls.module = importlib.import_module("custom_components.djconnect.display_transport")

    @staticmethod
    def request(raw=b'{}', **changes):
        return SimpleNamespace(content_type="application/json", content_length=len(raw),
            content=_Content(raw), **changes)

    async def test_json_duplicate_nested_fields_non_json_constants_and_depth_fail_closed(self):
        for raw in (b'{"contract_version":1,"contract_version":1}', b'{"share":{"mode":1,"mode":2}}',
                    b'{"a":NaN}', b'[]', b'\xff', b'[' * 1100 + b']' * 1100):
            with self.subTest(raw=raw[:40]), self.assertRaises(self.module.DisplayAdmissionError):
                await self.module.closed_body(self.request(raw))

    async def test_body_limit_with_and_without_content_length(self):
        for declared in (True, False):
            request = self.request(b'{"padding":"' + b'x' * 4096 + b'"}')
            if not declared:
                request.content_length = None
            with self.assertRaises(self.module.DisplayAdmissionError) as failure:
                await self.module.closed_body(request)
            self.assertEqual(failure.exception.status, 413)

    async def test_no_query_insecure_or_duplicate_auth_request_reaches_service(self):
        view = self.module.DisplayTransitionView(SimpleNamespace(), "claim")
        for changes in ({"query_string": "token=forbidden"}, {"secure": False},
                        {"headers": CIMultiDict([("Authorization", "Bearer one"), ("Authorization", "Bearer two")])}):
            fields = {"query_string": "", "secure": True, "headers": CIMultiDict(), **changes}
            response = await view.post(self.request(**fields))
            self.assertIn(response.status, (400, 426))
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    async def test_delayed_body_rechecks_fence_after_awaited_headers(self):
        current = True
        def release():
            if not current:
                raise self.module.DisplayAdmissionError("display_context_changed")
        response = self.module._FencedResponse(SimpleNamespace(payload={"grant_token": "unit-secret"}, release=release, complete=Mock()))
        transport = Mock()
        response._req = SimpleNamespace(transport=transport)
        current = False
        with patch.object(self.module.web.Response, "write_eof", new_callable=AsyncMock) as write:
            await response.write_eof()
            write.assert_not_called()
        transport.close.assert_called_once()
        self.assertFalse(response.keep_alive)

    async def test_current_response_releases_only_once_through_normal_aiohttp_body_writer(self):
        release = Mock()
        response = self.module._FencedResponse(SimpleNamespace(payload={"success": True}, release=release, complete=Mock()))
        self.assertEqual(json.loads(response.body), {"success": True})
        with patch.object(self.module.web.Response, "write_eof", new_callable=AsyncMock) as write:
            await response.write_eof()
            write.assert_awaited_once()
        release.assert_called_once()

    async def test_route_list_is_closed_and_read_only_scope_not_catch_all(self):
        views = self.module.transition_views(SimpleNamespace())
        self.assertEqual(len(views), 10)
        self.assertEqual(len({view.url for view in views}), 10)
        self.assertTrue(all("{" not in view.url for view in views))

    async def test_blocked_prepare_aborts_and_frees_actual_shared_reservation(self):
        from custom_components.djconnect.display_delivery import display_live_hub
        hub = display_live_hub(SimpleNamespace())
        complete = hub.reserve_projection("blocked")
        response = self.module._FencedResponse(SimpleNamespace(payload={"success": True}, release=Mock(), complete=complete))
        request = SimpleNamespace(transport=Mock())
        async def blocked(*_args):
            await asyncio.Event().wait()
        with patch.object(self.module, "SEND_TIMEOUT_SECONDS", 0.02), \
             patch.object(self.module.web.Response, "prepare", side_effect=blocked):
            with self.assertRaises(TimeoutError):
                await response.prepare(request)
        request.transport.close.assert_called_once()
        self.assertIsNone(response.body)
        self.assertEqual(hub.reserved_bytes, 0)
        hub.reserve_projection("new-viewer")()

    async def test_blocked_eof_has_remaining_total_deadline_and_frees_reservation(self):
        from custom_components.djconnect.display_delivery import display_live_hub
        hub = display_live_hub(SimpleNamespace())
        complete = hub.reserve_projection("blocked")
        response = self.module._FencedResponse(SimpleNamespace(payload={"success": True}, release=Mock(), complete=complete))
        response._req = SimpleNamespace(transport=Mock())
        response._display_send_deadline = asyncio.get_running_loop().time() + 0.02
        async def blocked(*_args):
            await asyncio.Event().wait()
        with patch.object(self.module.web.Response, "write_eof", side_effect=blocked):
            await response.write_eof()
        response._req.transport.close.assert_called_once()
        self.assertIsNone(response.body)
        self.assertEqual(hub.reserved_bytes, 0)
        hub.reserve_projection("new-viewer")()

    async def test_live_total_admission_deadline_covers_prepare_and_runtime_lock(self):
        display_live = importlib.import_module("custom_components.djconnect.display_live")
        session_runtime = importlib.import_module("custom_components.djconnect.session_runtime")
        from custom_components.djconnect.display_delivery import display_live_hub
        origin = "https://ha.display-lab.djconnect.dev"
        for phase in ("prepare", "lock"):
            with self.subTest(phase=phase):
                lock = asyncio.Lock()
                if phase == "lock":
                    await lock.acquire()
                manager = SimpleNamespace(_lock=lock)
                hub = display_live_hub(manager)
                request = SimpleNamespace(query_string="", secure=True,
                    headers=CIMultiDict({"Origin": origin}), transport=Mock())
                request.transport.get_extra_info.return_value = ("127.0.0.1", 1234)
                async def prepare(*_args):
                    if phase == "prepare":
                        await asyncio.Event().wait()
                frame = {"type": "authenticate", "contract_version": 1,
                    "grant_token": "djcd_" + "A" * 43, "issuer_epoch": "A" * 43,
                    "display_id": "B" * 43, "connection_nonce": "C" * 43}
                message = SimpleNamespace(type=display_live.WSMsgType.TEXT, data=json.dumps(frame))
                with patch.object(session_runtime, "session_runtime_manager", return_value=manager), \
                     patch.object(display_live, "selected_ha_origin", return_value=origin), \
                     patch.object(display_live, "ADMISSION_TIMEOUT_SECONDS", 0.02), \
                     patch.object(display_live.web.WebSocketResponse, "prepare", side_effect=prepare), \
                     patch.object(display_live.web.WebSocketResponse, "receive", new=AsyncMock(return_value=message)):
                    await asyncio.wait_for(display_live.DisplayLiveView(SimpleNamespace()).get(request), 0.5)
                if lock.locked():
                    lock.release()
                request.transport.close.assert_called()
                self.assertEqual(hub.preauth, 0)
                self.assertFalse(hub.sources)
                hub.reserve_preauth("127.0.0.1")
                hub.release_preauth("127.0.0.1")

    async def test_old_upgrade_cannot_clear_new_origin_display_authority(self):
        live = importlib.import_module("custom_components.djconnect.display_live")
        runtime = importlib.import_module("custom_components.djconnect.session_runtime")
        authority = importlib.import_module("custom_components.djconnect.display_admission")
        old, new = "https://old.example.test", "https://new.example.test"
        selected = old
        manager = SimpleNamespace(_lock=asyncio.Lock(), _display_admission=authority.DisplayAdmissionState())
        service = live.DisplayAdmissionService(SimpleNamespace(), manager)
        service._sync_origin(old)
        entered, release = asyncio.Event(), asyncio.Event()
        async def prepare(*_args):
            entered.set()
            await release.wait()
        frame = {"type": "authenticate", "contract_version": 1, "grant_token": "djcd_" + "A" * 43,
            "issuer_epoch": "A" * 43, "display_id": "B" * 43, "connection_nonce": "C" * 43}
        request = SimpleNamespace(query_string="", secure=True, headers=CIMultiDict({"Origin": old}), transport=Mock())
        request.transport.get_extra_info.return_value = ("127.0.0.1", 1234)
        message = SimpleNamespace(type=live.WSMsgType.TEXT, data=json.dumps(frame))
        with patch.object(runtime, "session_runtime_manager", return_value=manager), \
             patch.object(live, "selected_ha_origin", side_effect=lambda _hass: selected), \
             patch.object(live.web.WebSocketResponse, "prepare", side_effect=prepare), \
             patch.object(live.web.WebSocketResponse, "receive", new=AsyncMock(return_value=message)):
            task = asyncio.create_task(live.DisplayLiveView(SimpleNamespace()).get(request))
            await asyncio.wait_for(entered.wait(), 0.5)
            selected = new
            service._sync_origin(new)
            state = manager._display_admission
            owner = authority.DisplayOwnerBinding("profile", "session", "entry", "stamp", lambda: True)
            nonce = secrets.token_urlsafe(32)
            claim = state.create_claim(source="new-origin", browser_nonce=nonce)
            state.approve(owner=owner, **{key: claim[key] for key in (
                "issuer_epoch", "claim_id", "browser_generation", "code")}, share={"mode": "create", "consent": True})
            grant = state.collect(**{key: claim[key] for key in (
                "issuer_epoch", "claim_id", "claim_secret", "browser_generation")}, browser_nonce=nonce)
            epoch = state.issuer_epoch
            release.set()
            await asyncio.wait_for(task, 0.5)
            self.assertEqual(state.selected_origin, new)
            self.assertEqual(state.issuer_epoch, epoch)
            self.assertEqual(len(state._shares), 1)
            self.assertEqual(state.authorize(token=grant["grant_token"], display_id=grant["display_id"],
                issuer_epoch=epoch).display_id, grant["display_id"])

    async def test_public_shell_origin_query_tls_fences_and_actual_generated_app(self):
        shell = importlib.import_module("custom_components.djconnect.display_shell")
        origin = "https://ha.example.test"
        executor = AsyncMock(side_effect=asyncio.to_thread)
        view = shell.DisplayShellView(SimpleNamespace(async_add_executor_job=executor))
        for supplied in ([], [origin]):
            request = SimpleNamespace(secure=True, query_string="", headers=CIMultiDict(
                [("Origin", value) for value in supplied]))
            with patch.object(shell, "selected_ha_origin", return_value=origin):
                response = await view.get(request)
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
            self.assertIn("DJC_VIBECAST_MODE", response.text)
        for changes in ({"secure": False}, {"query_string": "token=forbidden"},
                        {"headers": CIMultiDict({"Origin": "null"})},
                        {"headers": CIMultiDict([("Origin", origin), ("Origin", origin)])}):
            request = SimpleNamespace(**{"secure": True, "query_string": "", "headers": CIMultiDict(), **changes})
            executor.reset_mock()
            with patch.object(shell, "selected_ha_origin", return_value=origin):
                response = await view.get(request)
            self.assertEqual(response.status, 403)
            executor.assert_not_awaited()

    async def test_public_shell_cannot_release_old_origin_app_after_executor_wait(self):
        shell = importlib.import_module("custom_components.djconnect.display_shell")
        entered, release = asyncio.Event(), asyncio.Event()
        async def executor(job):
            entered.set()
            await release.wait()
            return await asyncio.to_thread(job)
        selected = "https://old.example.test"
        request = SimpleNamespace(secure=True, query_string="", headers=CIMultiDict())
        with patch.object(shell, "selected_ha_origin", side_effect=lambda _hass: selected):
            task = asyncio.create_task(shell.DisplayShellView(SimpleNamespace(async_add_executor_job=executor)).get(request))
            await asyncio.wait_for(entered.wait(), 0.5)
            selected = "https://new.example.test"
            release.set()
            response = await asyncio.wait_for(task, 0.5)
        self.assertEqual(response.status, 409)
        self.assertNotIn("<html", response.text)


if __name__ == "__main__":
    unittest.main()
