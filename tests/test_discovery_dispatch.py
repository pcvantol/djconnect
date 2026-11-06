"""Causal transport regressions: one real adapter dispatch, no provider effects."""

import asyncio
import importlib
from types import SimpleNamespace
from urllib.parse import urlsplit
import unittest
from tests.test_http_voice_helpers import install_http_stubs


class DiscoveryDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        install_http_stubs()
        self.m = importlib.import_module("custom_components.djconnect.spotify_backend")
        self.valid = True
        self.reserved = 0
        self.calls = []
        self.mode = "ok"
        self.context = "spotify:playlist:" + "B" * 22
        self.old = "spotify:playlist:" + "O" * 22
        self.observed = {
            "device": {"id": "fixture-output", "is_active": True, "is_restricted": False},
            "context": {"uri": self.old},
        }
        outer = self

        class Response:
            def __init__(self, method, path, body):
                self.method, self.path, self.body = method, path, body
                self.status = 204 if method == "PUT" else 200
                if method == "PUT" and outer.mode == "denied":
                    self.status = 403
                if method == "PUT" and outer.mode == "unauthorized":
                    self.status = 401

            async def __aenter__(self):
                if self.method == "PUT" and outer.mode == "timeout":
                    raise TimeoutError()
                if self.method == "PUT" and self.status == 204:
                    outer.observed["context"] = {"uri": self.body.get("context_uri")}
                return self

            async def __aexit__(self, *args):
                pass

            async def json(self, **kwargs):
                return outer.observed

            async def text(self):
                return "synthetic denied"

        class Session:
            def request(self, method, url, **kw):
                path = urlsplit(url).path.removeprefix("/v1")
                outer.calls.append((method, path, kw.get("json")))
                return Response(method, path, kw.get("json"))

        self.b = object.__new__(self.m.SpotifyBackend)
        self.b.runtime = SimpleNamespace(config={})
        self.b.session = Session()
        self.b._retire_startup = lambda: None

        async def token(**kwargs):
            return "synthetic-test-access"

        self.b._access_token = token

    def reserve(self):
        self.reserved += 1

    def scope(self):
        return self.m.discovery_dispatch(lambda: self.valid, self.reserve)

    async def test_context_only_starts_once_on_observed_output_and_confirms_new_context(self):
        with self.scope() as scope:
            scope.approved_uri = self.context
            result = await self.b.play_discovery_selection({"context_uri": self.context})
            self.assertTrue(result["success"])
            self.assertTrue(result["action_outcome"]["readback_confirmed"])
            self.assertFalse(result["action_outcome"]["queue_replacement_verified"])
            self.assertEqual(self.reserved, 1)
            with self.assertRaises(self.m.SpotifyDiscoveryError):
                await self.b.play_discovery_selection({"context_uri": self.context})
        self.assertEqual([p for m, p, _ in self.calls if m != "GET"], ["/me/player/play"])
        self.assertEqual(self.observed["context"]["uri"], self.context)

    async def test_no_active_or_restricted_output_never_transfers(self):
        for device in [
            {},
            {"id": "x", "is_active": False, "is_restricted": False},
            {"id": "x", "is_active": True, "is_restricted": True},
        ]:
            self.observed["device"] = device
            with self.scope() as scope:
                scope.approved_uri = self.context
                with self.assertRaisesRegex(self.m.SpotifyDiscoveryError, "output_required"):
                    await self.b.play_discovery_selection({"context_uri": self.context})
        self.assertTrue(all(m == "GET" for m, _, _ in self.calls))
        self.assertEqual(self.reserved, 0)

    async def test_token_wait_owner_change_prevents_mutation(self):
        original = self.b._access_token

        async def token(**kwargs):
            if len(self.calls) == 1:
                self.valid = False
            return await original(**kwargs)

        self.b._access_token = token
        with self.scope() as scope:
            scope.approved_uri = self.context
            with self.assertRaisesRegex(self.m.SpotifyDiscoveryError, "context_changed"):
                await self.b.play_discovery_selection({"context_uri": self.context})
        self.assertEqual([m for m, _, _ in self.calls], ["GET"])
        self.assertEqual(self.reserved, 0)

    async def test_401_or_unknown_write_does_not_automatically_replay(self):
        for mode in ["unauthorized", "timeout", "denied"]:
            self.mode = mode
            self.calls.clear()
            with self.scope() as scope:
                scope.approved_uri = self.context
                with self.assertRaises((self.m.SpotifyBackendError, TimeoutError)):
                    await self.b.play_discovery_selection({"context_uri": self.context})
                self.assertTrue(scope.attempted)
                self.assertFalse(scope.acknowledged)
            self.assertEqual(sum(m == "PUT" for m, _, _ in self.calls), 1)

    async def test_json_cannot_mint_or_broaden_private_dispatch_scope(self):
        with self.assertRaises(self.m.SpotifyDiscoveryError):
            await self.b.play_discovery_selection({"context_uri": self.context})
        with self.scope() as scope:
            scope.approved_uri = self.context
            with self.assertRaises(self.m.SpotifyDiscoveryError):
                await self.b.play_discovery_selection({"context_uri": self.old})
        self.assertEqual(self.calls, [])

    async def test_child_task_cannot_inherit_dispatch_authority(self):
        with self.scope() as scope:
            scope.approved_uri = self.context
            with self.assertRaises(self.m.SpotifyDiscoveryError):
                await asyncio.create_task(
                    self.b.play_discovery_selection({"context_uri": self.context})
                )
        self.assertEqual(self.calls, [])
