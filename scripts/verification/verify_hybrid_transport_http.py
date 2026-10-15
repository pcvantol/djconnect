"""Owned real HA/TLS/paired-WS/Store qualification; only provider I/O is a fixture.

No installed config, real account credentials, model calls or native acceptance.
Run only in the bounded networkless owner lab with /candidate and /lab mounts.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import ssl
import sys
import time
import resource
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlparse
from uuid import UUID

from aiohttp import (
    ClientSession,
    TCPConnector,
    web,
    ClientConnectorCertificateError,
    ClientConnectionError,
    WSMsgType,
    WSServerHandshakeError,
)
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/candidate"))
sys.path.insert(0, str(ROOT))
# ruff: noqa: E402
from scripts.verification.verify_ask_dj_contextual_dialogue_http import configured_entry
from homeassistant import auth, loader
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.config_entries import ConfigEntryStore, ConfigEntries, ConfigEntryState
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.components import network
from homeassistant.helpers import device_registry, entity_registry, area_registry, frame
from custom_components.djconnect import DJConnectRuntime, register_http_views
from custom_components.djconnect.domain.storage import ProfilePlatformStorage
from custom_components.djconnect.domain.backend import BackendProvider
from custom_components.djconnect.domain.music_account import MusicAccountKind
from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
from custom_components.djconnect.persistence import (
    async_initialize_persistence,
    async_shutdown_persistence,
)
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository
from custom_components.djconnect.session_runtime import SessionRuntimeManager
from custom_components.djconnect.spotify_backend import SpotifyBackend
from custom_components.djconnect.session_facts import SessionFactsResolver
from custom_components.djconnect.hybrid_service import operations


def tls(directory):
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "owned-hybrid-lab")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cp = directory / "ephemeral-test-cert.pem"
    kp = directory / "ephemeral-test-key.pem"
    cp.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    kp.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    kp.chmod(0o600)
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(cp, kp)
    client = ssl.create_default_context(cafile=str(cp))
    return server, client


def new_id():
    import time

    return str(
        UUID(int=(int(time.time() * 1000) << 80) | (7 << 76) | (2 << 62) | secrets.randbits(62))
    )


async def main():
    receipts = []
    provider_calls = []
    with TemporaryDirectory(prefix="djc-owned-hybrid-") as tmp:
        directory = Path(tmp)
        h = HomeAssistant(tmp)
        h.state = CoreState.running
        h.config.language = "en"
        device_registry.async_setup(h)
        await device_registry.async_load(h, load_empty=True)
        await entity_registry.async_load(h, load_empty=True)
        await area_registry.async_load(h, load_empty=True)
        h.auth = await auth.auth_manager_from_config(h, [{"type": "homeassistant"}], [])
        h.http = HomeAssistantHTTP(h, None, None, None, ["127.0.0.1"], 0, [], "modern")
        await h.http.async_initialize(
            cors_origins=[],
            use_x_forwarded_for=False,
            login_threshold=-1,
            is_ban_enabled=False,
            use_x_frame_options=True,
        )
        h.config.components.add("http")
        await network.async_setup(h, {})
        frame.async_setup(h)
        loader.async_setup(h)
        device = "djconnect-ios-ABCDEF123456"
        identity = {"device_id": device, "client_type": "ios"}
        owner = configured_entry(
            "owner-entry",
            "djconnect",
            {
                **identity,
                "profile_id": "profile-a",
                "pair_code": "123456",
                "ha_install_id": "ha_owned_hybrid_fixture",
                "music_backend": "spotify_direct",
                "music_account_id": "source-account",
                "spotify_client_id": "SYNTHETIC_CLIENT_ID",
                "spotify_refresh_token": "SYNTHETIC_SOURCE_GRANT",
            },
        )
        source = configured_entry(
            "source-entry",
            "djconnect",
            {
                "music_account_id": "source-account",
                "spotify_refresh_token": "SYNTHETIC_SOURCE_GRANT",
            },
        )
        await ConfigEntryStore(h).async_save(
            {"entries": [e.as_storage_fragment for e in (owner, source)]}
        )
        h.config_entries = ConfigEntries(h, {})
        await h.config_entries.async_initialize()
        owner, source = [h.config_entries.async_get_entry(e.entry_id) for e in (owner, source)]
        for e in (owner, source):
            e._async_set_state(h, ConfigEntryState.LOADED, None)
        runtime = DJConnectRuntime(owner, device_token=secrets.token_urlsafe(32))
        runtime.device_status.update(identity)
        storage = ProfilePlatformStorage(h)
        history = AskDJHistoryManager(h)
        runtime.ask_dj_history = history
        h.data["djconnect"] = {
            "owner-entry": runtime,
            "runtime": runtime,
            "djconnect_profile_platform": storage,
            "ask_dj_history_manager": history,
        }
        await storage.async_upsert_music_backend(
            "spotify_direct", BackendProvider.SPOTIFY_DIRECT, display_name="Fixture provider"
        )
        profile = await storage.async_create_profile(
            "Synthetic owner", profile_id="profile-a", default_backend_id="spotify_direct"
        )
        await storage.async_upsert_music_account(
            "source-account",
            "spotify_direct",
            kind=MusicAccountKind.PERSONAL,
            linked_profile_ids=frozenset({"profile-a"}),
            display_name="Fixture account",
        )
        await storage.async_update_profile(
            "profile-a",
            preferences=replace(profile.preferences, default_music_account_id="source-account"),
        )
        await storage.async_upsert_device(device, "ios", linked_profile_id="profile-a")
        persistence = await async_initialize_persistence(h)
        manager = SessionRuntimeManager(
            PersistentSessionRepository(persistence), HistoricalProjectionRepository(persistence)
        )
        h.data["djconnect"]["session_runtime_manager"] = manager
        register_http_views(h)
        state = {
            "index": 1,
            "mutations": 0,
            "token_gate": None,
            "token_entered": None,
            "fail_after_effect": False,
            "large_queue": False,
        }

        async def provider_token(self, **kwargs):
            from custom_components.djconnect.hybrid_service import _current_operation

            if state["token_gate"] is not None and _current_operation.get():
                state["token_entered"].set()
                await state["token_gate"].wait()
            return "UNUSED_SYNTHETIC_PROVIDER_TOKEN"

        async def no_fact(self, *args, **kwargs):
            return None

        class ProviderResponse:
            def __init__(self, method, url, body):
                self.method, self.path, self.body = method, urlparse(url).path, body

            async def __aenter__(self):
                provider_calls.append({"method": self.method, "path": self.path})
                if self.method in {"POST", "PUT", "DELETE", "PATCH"}:
                    state["mutations"] += 1
                    if self.path.endswith("/next"):
                        state["index"] += 1
                    if state["fail_after_effect"]:
                        state["fail_after_effect"] = False
                        raise ClientConnectionError("synthetic external acknowledgement loss")
                    self.status, self.payload = 204, {}
                elif self.path.endswith("/devices"):
                    self.status, self.payload = (
                        200,
                        {
                            "devices": [
                                {"id": "own-speaker", "name": "Fixture speaker", "is_active": True}
                            ]
                        },
                    )
                elif self.path.endswith("/queue"):
                    self.status, self.payload = (
                        200,
                        {
                            "queue": [
                                {
                                    "id": str(i).zfill(22),
                                    "uri": "spotify:track:" + str(i).zfill(22),
                                    "name": "Synthetic large queue title " + "x" * 700,
                                    "artists": [{"name": "Fixture artist"}],
                                    "album": {
                                        "id": "b" * 22,
                                        "name": "Fixture album",
                                        "images": [],
                                    },
                                }
                                for i in range(100)
                            ]
                            if state["large_queue"]
                            else []
                        },
                    )
                elif self.path.endswith("/player"):
                    self.status, self.payload = (
                        200,
                        {
                            "item": {
                                "id": str(state["index"]) * 22,
                                "uri": "spotify:track:" + str(state["index"]) * 22,
                                "name": "Fixture work",
                                "artists": [{"id": "a" * 22, "name": "Fixture artist"}],
                                "album": {"id": "b" * 22, "name": "Fixture album", "images": []},
                                "duration_ms": 300000,
                            },
                            "is_playing": True,
                            "progress_ms": 1000,
                            "device": {
                                "id": "own-speaker",
                                "is_active": True,
                                "volume_percent": 40,
                            },
                            "repeat_state": "off",
                            "shuffle_state": False,
                        },
                    )
                else:
                    self.status, self.payload = 200, {}
                return self

            async def __aexit__(self, *args):
                return False

            async def json(self, **kwargs):
                return self.payload

            async def text(self):
                return json.dumps(self.payload)

            async def read(self):
                return json.dumps(self.payload).encode()

        class ProviderSession:
            def request(self, method, url, **kwargs):
                return ProviderResponse(method, url, kwargs.get("json"))

        server_ssl, client_ssl = tls(directory)
        runner = web.AppRunner(h.http.app)
        await runner.setup()
        secure_site = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=server_ssl)
        await secure_site.start()
        external_entry = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=server_ssl)
        await external_entry.start()
        plain_site = web.TCPSite(runner, "127.0.0.1", 0)
        await plain_site.start()
        secure = "https://127.0.0.1:" + str(secure_site._server.sockets[0].getsockname()[1])
        external = "https://127.0.0.1:" + str(external_entry._server.sockets[0].getsockname()[1])
        plain = "http://127.0.0.1:" + str(plain_site._server.sockets[0].getsockname()[1])
        try:
            with (
                patch(
                    "custom_components.djconnect.spotify_backend.async_get_clientsession",
                    return_value=ProviderSession(),
                ),
                patch.object(SpotifyBackend, "_access_token", provider_token),
                patch.object(SessionFactsResolver, "_get", no_fact),
            ):
                async with ClientSession(connector=TCPConnector(ssl=client_ssl)) as client:
                    async with client.get(secure + "/api/djconnect/v1/capabilities") as advertised:
                        metadata = await advertised.json()
                        assert metadata["hybrid_transport"]["audience"] == "paired_owner_actions"
                        assert metadata["hybrid_transport"]["requires_authenticated_tls"]
                        assert (
                            metadata["session_broadcast"]["paired_owner_websocket"]["audience"]
                            == "active_owner_broadcast"
                        )
                        receipts.append(
                            {
                                "case": "additive-disjoint-capability",
                                "body": metadata["hybrid_transport"],
                            }
                        )
                    async with client.post(
                        secure + "/api/djconnect/v1/pair", json={**identity, "pair_code": "123456"}
                    ) as paired:
                        pair = await paired.json()
                        assert paired.status == 200 and pair["success"]
                    token = pair["device_token"]
                    headers = {"Authorization": "Bearer " + token, "X-DJConnect-Device-ID": device}

                    async def post(path, body, expected=200):
                        async with client.post(
                            secure + "/api/djconnect/v1/" + path, json=body, headers=headers
                        ) as result:
                            data = await result.json()
                            receipts.append(
                                {
                                    "path": path,
                                    "status": result.status,
                                    "request": body,
                                    "body": data,
                                }
                            )
                            assert result.status == expected, (path, result.status, data)
                            assert result.headers.get("Cache-Control") == "no-store"
                            return data

                    ctx = await post(
                        "transport/context", {"contract_version": 1, "identity": identity}
                    )
                    assert ctx["ha_install_id"] == "ha_owned_hybrid_fixture"
                    async with client.post(
                        secure + "/api/djconnect/v1/transport/context",
                        headers={"Origin": "https://foreign.invalid"},
                        json={"contract_version": 1, "identity": identity},
                    ) as foreign:
                        assert (
                            foreign.status == 403
                            and (await foreign.json())["error"] == "origin_not_allowed"
                        )
                        receipts.append(
                            {
                                "case": "foreign-browser-origin-before-secret",
                                "status": foreign.status,
                            }
                        )
                    async with client.post(
                        secure + "/api/djconnect/v1/transport/context",
                        json={"contract_version": 1, "identity": identity},
                    ) as denied:
                        assert denied.status == 401
                        receipts.append(
                            {"case": "ordinary-pairing-required", "status": denied.status}
                        )
                    async with client.post(
                        plain + "/api/djconnect/v1/transport/context",
                        json={"contract_version": 1, "identity": identity},
                    ) as insecure:
                        assert insecure.status == 426
                        receipts.append(
                            {"case": "plaintext-rejected-before-secret", "status": insecure.status}
                        )
                    async with ClientSession() as untrusted:
                        try:
                            await untrusted.get(secure + "/api/djconnect/v1/capabilities")
                            raise AssertionError("Untrusted fixture certificate accepted")
                        except ClientConnectorCertificateError:
                            receipts.append(
                                {"case": "untrusted-certificate-rejected", "before_secret": True}
                            )
                    start = await post(
                        "transport/operation",
                        {
                            "identity": identity,
                            "contract_version": 1,
                            "operation_id": new_id(),
                            "operation_epoch": ctx["operation_epoch"],
                            "operation": "session/start",
                            "payload": {
                                "mood": "groove",
                                "dj_persona": "home_dj",
                                "language": "en",
                            },
                        },
                        201,
                    )
                    session_id = start["session"]["session_id"]
                    recovery = await post(
                        "session/broadcast/recovery",
                        {
                            "contract_version": 1,
                            "identity": identity,
                            "session_id": session_id,
                            "recovery_cursor": "0" * 32,
                        },
                    )
                    assert recovery["recovery"] == "snapshot_required"
                    assert recovery["session_id"] == session_id
                    opening_moments = recovery["snapshot"]["dj_moments"]
                    assert opening_moments and all(m["type"] != "silence" for m in opening_moments)
                    original_cursor = recovery["recovery_cursor"]
                    assert not manager.current_active("profile-a").broadcast._subscribers
                    from scripts.verification.hybrid_direct_local_probe import probe

                    await probe(h, client, plain, identity, headers, ctx, session_id, new_id, receipts)
                    async with client.ws_connect(
                        secure + "/api/djconnect/v1/actions/paired"
                    ) as wrong:
                        await wrong.receive_json()
                        await wrong.send_json(
                            {
                                "type": "auth",
                                "protocol_version": 1,
                                "audience": "active_owner_broadcast",
                                **identity,
                                "device_token": token,
                            }
                        )
                        rejected = await wrong.receive_json()
                        assert rejected == {"type": "auth_invalid", "code": "invalid_auth"}
                        receipts.append(
                            {
                                "case": "broadcast-audience-cannot-authorize-actions",
                                "body": rejected,
                            }
                        )
                    held = []
                    try:
                        for number in range(3):
                            socket = await client.ws_connect(
                                secure + "/api/djconnect/v1/actions/paired"
                            )
                            held.append(socket)
                            await socket.receive_json()
                            await socket.send_json(
                                {
                                    "type": "auth",
                                    "protocol_version": 1,
                                    "audience": "paired_owner_actions",
                                    **identity,
                                    "device_token": token,
                                }
                            )
                            allocation = await socket.receive_json()
                            assert allocation["type"] == (
                                "auth_ok" if number < 2 else "auth_invalid"
                            )
                            if number == 2:
                                assert allocation["code"] == "connection_capacity"
                        receipts.append(
                            {
                                "case": "actual-two-device-connection-bound",
                                "accepted": 2,
                                "denied": 1,
                            }
                        )
                    finally:
                        await asyncio.gather(*(s.close() for s in held))
                    await asyncio.sleep(0.05)
                    held = []
                    try:
                        for _ in range(16):
                            socket = await client.ws_connect(
                                secure + "/api/djconnect/v1/actions/paired"
                            )
                            held.append(socket)
                            assert (await socket.receive_json())["type"] == "auth_required"
                        try:
                            await client.ws_connect(secure + "/api/djconnect/v1/actions/paired")
                            raise AssertionError("Unbounded unauthenticated socket allocation")
                        except WSServerHandshakeError as limit:
                            assert limit.status == 429
                        receipts.append(
                            {
                                "case": "actual-sixteen-total-connection-bound",
                                "accepted": 16,
                                "denied": 1,
                            }
                        )
                    finally:
                        await asyncio.gather(*(s.close() for s in held))
                    await asyncio.sleep(0.05)
                    async with client.ws_connect(secure + "/api/djconnect/v1/actions/paired") as ws:
                        assert (await ws.receive_json())["type"] == "auth_required"
                        await ws.send_json(
                            {
                                "type": "auth",
                                "protocol_version": 1,
                                "audience": "paired_owner_actions",
                                **identity,
                                "device_token": token,
                            }
                        )
                        ready = await ws.receive_json()
                        assert ready["type"] == "auth_ok", ready
                        epoch = ready["operation_epoch"]
                        cid = ready["connection_id"]
                        await ws.send_json(
                            {
                                "id": 1,
                                "type": "djconnect/read",
                                "operation": "session/active",
                                "payload": {},
                            }
                        )
                        active = await ws.receive_json()
                        assert (
                            active["id"] == 1
                            and active["connection_id"] == cid
                            and active["success"]
                        ), active
                        assert active["result"]["session"]["session_id"] == session_id
                        request = {
                            "contract_version": 1,
                            "operation_id": new_id(),
                            "operation_epoch": epoch,
                            "operation": "command",
                            "payload": {"command": "next"},
                        }
                        await ws.send_json(
                            {"id": 2, "type": "djconnect/operation/execute", **request}
                        )
                        executed = await ws.receive_json()
                        assert executed["success"], executed
                        assert executed["result"]["operation_receipt"]["phase"] == "confirmed"
                        receipts.append(
                            {
                                "case": "actual-wss-next",
                                "request": {
                                    "id": 2,
                                    "type": "djconnect/operation/execute",
                                    **request,
                                },
                                "body": executed,
                            }
                        )
                        before = state["mutations"]
                        duplicate = await post(
                            "transport/operation", {"identity": identity, **request}
                        )
                        assert (
                            duplicate["operation_receipt"]["phase"] == "confirmed"
                            and state["mutations"] == before
                        )
                        async with client.post(
                            external + "/api/djconnect/v1/transport/operation",
                            json={"identity": identity, **request},
                            headers=headers,
                            allow_redirects=False,
                        ) as remote:
                            remote_receipt = await remote.json()
                            assert (
                                remote.status == 200
                                and remote_receipt["operation_receipt"]["phase"] == "confirmed"
                            )
                            assert state["mutations"] == before
                            receipts.append(
                                {
                                    "case": "second-qualified-http-entry-reconciles-original-id",
                                    "body": remote_receipt,
                                    "boundary": "two TLS entry points on one isolated HA; not native cellular routing",
                                }
                            )
                        conflict = {**request, "payload": {"command": "previous"}}
                        await post("transport/operation", {"identity": identity, **conflict}, 409)
                        status = {
                            k: request[k]
                            for k in ("contract_version", "operation_id", "operation_epoch")
                        }
                        await ws.send_json(
                            {"id": 3, "type": "djconnect/operation/status", **status}
                        )
                        assert (await ws.receive_json())["result"]["operation_receipt"][
                            "phase"
                        ] == "confirmed"
                        # New intentional action gets a fresh ID, not a replay identity.
                        await post(
                            "transport/operation",
                            {"identity": identity, **request, "operation_id": new_id()},
                        )
                        assert state["mutations"] == before + 1
                        await ws.send_json(
                            {
                                "id": 4,
                                "type": "djconnect/read",
                                "operation": "session/active",
                                "payload": {},
                            }
                        )
                        await ws.send_json(
                            {
                                "id": 5,
                                "type": "djconnect/read",
                                "operation": "session/active",
                                "payload": {},
                            }
                        )
                        concurrent = [await ws.receive_json(), await ws.receive_json()]
                        assert {v["id"] for v in concurrent} == {4, 5}
                        receipts.append(
                            {"case": "concurrent-correlation", "ids": [v["id"] for v in concurrent]}
                        )

                        async def execute(rid, operation, payload):
                            intent = {
                                "contract_version": 1,
                                "operation_id": new_id(),
                                "operation_epoch": epoch,
                                "operation": operation,
                                "payload": payload,
                            }
                            await ws.send_json(
                                {"id": rid, "type": "djconnect/operation/execute", **intent}
                            )
                            reply = await ws.receive_json()
                            receipts.append(
                                {
                                    "case": "actual-wss-" + operation,
                                    "request": {
                                        "id": rid,
                                        "type": "djconnect/operation/execute",
                                        **intent,
                                    },
                                    "body": reply,
                                }
                            )
                            return intent, reply

                        mood_intent, mood = await execute(
                            7,
                            "session/mood",
                            {
                                "contract_version": 1,
                                "session_id": session_id,
                                "selected_mood": "energy",
                                "expected_mood_revision": 0,
                            },
                        )
                        assert mood["success"] and mood["result"]["mood_revision"] == 1
                        assert mood["result"]["selected_mood"] == "energy"
                        await post("transport/operation", {"identity": identity, **mood_intent})
                        _stale, stale = await execute(
                            8,
                            "session/mood",
                            {
                                "contract_version": 1,
                                "session_id": session_id,
                                "selected_mood": "party",
                                "expected_mood_revision": 0,
                            },
                        )
                        assert (
                            stale["status"] == 409
                            and stale["result"]["operation_receipt"]["phase"] == "rejected"
                        )
                        await post(
                            "transport/operation/status",
                            {
                                "identity": identity,
                                **{
                                    k: _stale[k]
                                    for k in ("contract_version", "operation_id", "operation_epoch")
                                },
                            },
                            409,
                        )
                        _presence, presence = await execute(
                            9,
                            "session/presence",
                            {
                                "contract_version": 1,
                                "session_id": session_id,
                                "selected_presence": "occasional",
                                "expected_presence_revision": 0,
                            },
                        )
                        assert presence["success"] and presence["result"]["presence_revision"] == 1
                        hp = await post(
                            "transport/operation",
                            {
                                "identity": identity,
                                "contract_version": 1,
                                "operation_id": new_id(),
                                "operation_epoch": epoch,
                                "operation": "session/presence",
                                "payload": {
                                    "contract_version": 1,
                                    "session_id": session_id,
                                    "selected_presence": "balanced",
                                    "expected_presence_revision": 1,
                                },
                            },
                        )
                        assert (
                            hp["selected_presence"] == "balanced" and hp["presence_revision"] == 2
                        )
                        _help, helped = await execute(
                            10,
                            "ask_dj/message",
                            {
                                "text": "help",
                                "client_message_id": "hybrid-owned-help-1",
                                "language": "en",
                                "audio_response": "never",
                            },
                        )
                        assert helped["success"] and helped["result"].get("text")
                        await post("transport/operation", {"identity": identity, **_help})
                        _insight, insight = await execute(
                            11,
                            "track_insight",
                            {"title": "Fixture work", "artist": "Fixture artist", "locale": "en"},
                        )
                        assert insight["success"] and insight["result"].get("track"), insight
                        await ws.send_json(
                            {
                                "id": 12,
                                "type": "djconnect/read",
                                "operation": "session/forecast",
                                "payload": {"contract_version": 1, "session_id": session_id},
                            }
                        )
                        forecast = await ws.receive_json()
                        assert (
                            forecast["success"] and forecast["result"]["session_id"] == session_id
                        )
                        receipts.append(
                            {"case": "actual-wss-forecast-after-mood", "body": forecast}
                        )
                        recovered = await post(
                            "session/broadcast/recovery",
                            {
                                "contract_version": 1,
                                "identity": identity,
                                "session_id": session_id,
                                "recovery_cursor": original_cursor,
                            },
                        )
                        assert recovered["recovery"] == "snapshot_required"
                        current_moments = {
                            m["moment_id"]: m for m in recovered["snapshot"]["dj_moments"]
                        }
                        assert all(
                            current_moments.get(m["moment_id"]) == m for m in opening_moments
                        )
                        state["large_queue"] = True
                        queue_before = sum(v["path"].endswith("/queue") for v in provider_calls)
                        large_intent, large = await execute(14, "command", {"command": "queue"})
                        assert (
                            large["success"]
                            and large["result"]["operation_receipt"]["phase"] == "confirmed"
                        )
                        assert large["result"]["result_available"] is False
                        assert large["result"]["operation_receipt"]["result_available"] is False
                        assert "queue" not in large["result"]
                        queue_after = sum(v["path"].endswith("/queue") for v in provider_calls)
                        assert queue_after == queue_before + 1
                        await post("transport/operation", {"identity": identity, **large_intent})
                        assert (
                            sum(v["path"].endswith("/queue") for v in provider_calls) == queue_after
                        )
                        state["large_queue"] = False
                        assert not manager.current_active("profile-a").broadcast._subscribers
                        _outputs, outputs = await execute(13, "command", {"command": "devices"})
                        assert outputs["success"] and outputs["result"].get("devices"), outputs
                        http_outputs = await post(
                            "transport/operation",
                            {"identity": identity, **_outputs, "operation_id": new_id()},
                        )
                        ws_devices, http_devices = (
                            outputs["result"]["devices"],
                            http_outputs["devices"],
                        )

                        # Each deliberate query records its actual observation
                        # time in the existing provider cache. Compare every
                        # other canonical field and require time to advance.
                        def stable(rows):
                            return [
                                {k: v for k, v in row.items() if k != "last_seen_at"}
                                for row in rows
                            ]

                        if stable(http_devices) != stable(ws_devices):
                            Path("/lab/device-parity-mismatch.json").write_text(
                                json.dumps(
                                    {
                                        "http": http_outputs["devices"],
                                        "ws": outputs["result"]["devices"],
                                    },
                                    indent=2,
                                )
                            )
                            raise AssertionError("Canonical device projection parity mismatch")
                        assert all(
                            h["last_seen_at"] >= w["last_seen_at"]
                            for h, w in zip(http_devices, ws_devices, strict=True)
                        )
                        await ws.send_json(
                            {"id": 6, "type": "djconnect/read", "operation": [], "payload": {}}
                        )
                        invalid = await ws.receive_json()
                        assert (
                            invalid["status"] == 400
                            and invalid["error"]["code"] == "unsupported_read"
                        )
                        receipts.append({"case": "closed-read-policy", "body": invalid})
                        # A second use of an ID cannot be mistaken for its older reply.
                        await ws.send_json(
                            {
                                "id": 6,
                                "type": "djconnect/read",
                                "operation": "session/active",
                                "payload": {},
                            }
                        )
                        duplicate_id = await ws.receive_json()
                        assert duplicate_id == {
                            "type": "auth_invalid",
                            "code": "invalid_request_id",
                        }
                        receipts.append(
                            {"case": "request-id-reuse-closes-connection", "body": duplicate_id}
                        )
                    # Disconnect after durable admission, before the external token
                    # boundary completes. The original owner continues once; HTTP
                    # reconciliation cannot cause another provider execution.
                    async with client.ws_connect(
                        secure + "/api/djconnect/v1/actions/paired"
                    ) as cancelled:
                        await cancelled.receive_json()
                        await cancelled.send_json(
                            {
                                "type": "auth",
                                "protocol_version": 1,
                                "audience": "paired_owner_actions",
                                **identity,
                                "device_token": token,
                            }
                        )
                        cancelled_auth = await cancelled.receive_json()
                        state["token_gate"], state["token_entered"] = (
                            asyncio.Event(),
                            asyncio.Event(),
                        )
                        cancelled_intent = {**request, "operation_id": new_id()}
                        await cancelled.send_json(
                            {"id": 1, "type": "djconnect/operation/execute", **cancelled_intent}
                        )
                        await asyncio.wait_for(state["token_entered"].wait(), 5)
                        # The genuine external provider boundary holds ID1. A pure
                        # owner read ID2 must complete first, without a second reader.
                        await cancelled.send_json({
                            "id": 2, "type": "djconnect/read",
                            "operation": "session/active", "payload": {},
                        })
                        out_of_order = await asyncio.wait_for(cancelled.receive_json(), 5)
                        assert out_of_order["id"] == 2
                        assert out_of_order["connection_id"] == cancelled_auth["connection_id"]
                        assert out_of_order["result"]["session"]["session_id"] == session_id
                        receipts.append({"case": "actual-out-of-order-held-effect-fast-read",
                                         "received_id": 2, "still_pending_id": 1})
                        async with client.ws_connect(
                            secure + "/api/djconnect/v1/actions/paired"
                        ) as replacement:
                            await replacement.receive_json()
                            await replacement.send_json({
                                "type": "auth", "protocol_version": 1,
                                "audience": "paired_owner_actions", **identity,
                                "device_token": token,
                            })
                            replacement_auth = await replacement.receive_json()
                            assert replacement_auth["connection_id"] != cancelled_auth["connection_id"]
                            await replacement.send_json({
                                "id": 1, "type": "djconnect/operation/status",
                                **{k: cancelled_intent[k] for k in
                                   ("contract_version", "operation_id", "operation_epoch")},
                            })
                            replacing = await asyncio.wait_for(replacement.receive_json(), 5)
                            assert replacing["id"] == 1
                            assert replacing["connection_id"] == replacement_auth["connection_id"]
                            assert replacing["result"]["operation_receipt"]["phase"] == "accepted"
                            receipts.append({"case": "replacement-socket-original-id-status",
                                             "body": replacing, "new_connection_id": True})
                    pending = await post(
                        "transport/operation", {"identity": identity, **cancelled_intent}, 202
                    )
                    assert pending["operation_receipt"]["phase"] == "accepted"
                    state["token_gate"].set()
                    await asyncio.wait_for(
                        asyncio.gather(
                            *tuple(operations(h).tasks.values()), return_exceptions=True
                        ),
                        5,
                    )
                    state["token_gate"] = None
                    settled = await post(
                        "transport/operation", {"identity": identity, **cancelled_intent}
                    )
                    assert (
                        settled["operation_receipt"]["phase"] == "confirmed"
                        and state["mutations"] == 3
                    )
                    receipts.append(
                        {
                            "case": "disconnect-before-provider-send-no-duplicate",
                            "mutations": state["mutations"],
                        }
                    )
                    # External provider accepted but its acknowledgement was lost.
                    state["fail_after_effect"] = True
                    uncertain_intent = {**request, "operation_id": new_id()}
                    async with client.post(
                        secure + "/api/djconnect/v1/transport/operation",
                        json={"identity": identity, **uncertain_intent},
                        headers=headers,
                    ) as uncertain:
                        uncertain_body = await uncertain.json()
                        assert uncertain_body["operation_receipt"]["phase"] == "unknown"
                        receipts.append(
                            {
                                "case": "actual-provider-ack-loss",
                                "status": uncertain.status,
                                "body": uncertain_body,
                            }
                        )
                    before_retry = state["mutations"]
                    async with client.post(
                        secure + "/api/djconnect/v1/transport/operation",
                        json={"identity": identity, **uncertain_intent},
                        headers=headers,
                    ) as retry:
                        assert (await retry.json())["operation_receipt"]["phase"] == "unknown"
                    assert state["mutations"] == before_retry == 4
                    # A real Profile-store reassignment during an external-token
                    # await invalidates original authority before the send guard.
                    await storage.async_create_profile("Synthetic other", profile_id="profile-b")
                    state["token_gate"], state["token_entered"] = asyncio.Event(), asyncio.Event()
                    revoked_intent = {**request, "operation_id": new_id()}
                    revoked_call = asyncio.create_task(
                        client.post(
                            secure + "/api/djconnect/v1/transport/operation",
                            json={"identity": identity, **revoked_intent},
                            headers=headers,
                        )
                    )
                    await asyncio.wait_for(state["token_entered"].wait(), 5)
                    await storage.async_upsert_device(device, "ios", linked_profile_id="profile-b")
                    records_before = len(operations(h).journal._state["records"])
                    async with client.post(
                        secure + "/api/djconnect/v1/transport/operation",
                        json={"identity": identity, **request},
                        headers=headers,
                    ) as foreign_retry:
                        assert foreign_retry.status in {403, 409}
                        await foreign_retry.read()
                    assert len(operations(h).journal._state["records"]) == records_before
                    state["token_gate"].set()
                    denied = await revoked_call
                    assert denied.status in {401, 403}
                    await denied.read()
                    denied.release()
                    state["token_gate"] = None
                    assert state["mutations"] == 4
                    await storage.async_upsert_device(device, "ios", linked_profile_id="profile-a")
                    receipts.append(
                        {
                            "case": "profile-reassignment-before-send",
                            "status": denied.status,
                            "additional_mutations": 0,
                        }
                    )
                    async with client.ws_connect(
                        secure + "/api/djconnect/v1/actions/paired"
                    ) as bounded:
                        await bounded.receive_json()
                        await bounded.send_json(
                            {
                                "type": "auth",
                                "protocol_version": 1,
                                "audience": "paired_owner_actions",
                                **identity,
                                "device_token": token,
                            }
                        )
                        await bounded.receive_json()
                        state["token_gate"], state["token_entered"] = (
                            asyncio.Event(),
                            asyncio.Event(),
                        )
                        for rid in range(1, 9):
                            await bounded.send_json(
                                {
                                    "id": rid,
                                    "type": "djconnect/operation/execute",
                                    **request,
                                    "operation_id": new_id(),
                                    "payload": {"command": "status"},
                                }
                            )

                        async def all_reserved():
                            while len(operations(h).tasks) != 8:
                                await asyncio.sleep(0.01)

                        await asyncio.wait_for(all_reserved(), 5)
                        await bounded.send_json(
                            {
                                "id": 9,
                                "type": "djconnect/operation/execute",
                                **request,
                                "operation_id": new_id(),
                                "payload": {"command": "status"},
                            }
                        )
                        capacity = await bounded.receive_json()
                        assert capacity["id"] == 9 and capacity["status"] == 429
                        receipts.append({"case": "actual-eight-pending-bound", "body": capacity})
                        state["token_gate"].set()
                        replies = [await bounded.receive_json() for _ in range(8)]
                        assert {v["id"] for v in replies} == set(range(1, 9))
                        assert all(v["success"] for v in replies) and state["mutations"] == 4
                        state["token_gate"] = None
                    async with client.ws_connect(
                        secure + "/api/djconnect/v1/actions/paired", autoping=False
                    ) as half_open:
                        await half_open.receive_json()
                        await half_open.send_json(
                            {
                                "type": "auth",
                                "protocol_version": 1,
                                "audience": "paired_owner_actions",
                                **identity,
                                "device_token": token,
                            }
                        )
                        await half_open.receive_json()
                        began = time.monotonic()
                        ping = await half_open.receive(timeout=20)
                        assert ping.type == WSMsgType.PING
                        # Deliberately omit pong on this own socket only.
                        closed = await half_open.receive(timeout=12)
                        elapsed = time.monotonic() - began
                        assert closed.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}
                        assert 20 <= elapsed < 30
                        receipts.append(
                            {"case": "actual-idle-missing-pong-close", "elapsed_seconds": elapsed}
                        )
                    # Authoritative Store changes invalidate an otherwise quiet
                    # socket without needing a new playback/Broadcast event.
                    for fault in ("source-withdrawal", "token-rotation"):
                        async with client.ws_connect(
                            secure + "/api/djconnect/v1/actions/paired"
                        ) as withdrawn:
                            await withdrawn.receive_json()
                            await withdrawn.send_json(
                                {
                                    "type": "auth",
                                    "protocol_version": 1,
                                    "audience": "paired_owner_actions",
                                    **identity,
                                    "device_token": token,
                                }
                            )
                            assert (await withdrawn.receive_json())["type"] == "auth_ok"
                            if fault == "source-withdrawal":
                                before_profile = storage.household.profiles["profile-a"]
                                await storage.async_update_profile(
                                    "profile-a",
                                    preferences=replace(
                                        before_profile.preferences, default_music_account_id=""
                                    ),
                                )
                            else:
                                rotated = secrets.token_urlsafe(32)
                                h.config_entries.async_update_entry(
                                    owner, data={**owner.data, "device_token": rotated}
                                )
                                runtime.device_token = rotated
                            began = time.monotonic()
                            denied = await withdrawn.receive_json(timeout=3)
                            assert denied["type"] == "auth_invalid", denied
                            receipts.append(
                                {
                                    "case": "actual-idle-" + fault,
                                    "elapsed_seconds": time.monotonic() - began,
                                    "body": denied,
                                }
                            )
                            if fault == "source-withdrawal":
                                await storage.async_update_profile(
                                    "profile-a", preferences=before_profile.preferences
                                )
                            else:
                                h.config_entries.async_update_entry(
                                    owner, data={**owner.data, "device_token": token}
                                )
                                runtime.device_token = token
                    # Reopen durable journal under a fresh boot epoch: known result stays confirmed.
                    old = operations(h)
                    await old.close()
                    h.data["djconnect"].pop("hybrid_operation_manager")
                    await post("transport/operation/status", {"identity": identity, **status})
                    await post("transport/operation", {"identity": identity, **request}, 409)
                    journal_pre_idle_bytes = (
                        (directory / ".storage/djconnect_transport_operations").stat().st_size
                    )
                    if os.environ.get("DJC_HYBRID_LEASE_PROBE") == "1":
                        # Actual production timers, no patched clock or shortened lease.
                        await post(
                            "session/presence",
                            {
                                **identity,
                                "contract_version": 1,
                                "session_id": session_id,
                                "selected_presence": "music_only",
                                "expected_presence_revision": 2,
                            },
                        )
                        async with client.ws_connect(
                            secure + "/api/djconnect/v1/actions/paired"
                        ) as quiet:
                            await quiet.receive_json()
                            began = time.monotonic()
                            missing_auth = await quiet.receive_json(timeout=7)
                            assert missing_auth["type"] == "auth_invalid"
                            receipts.append(
                                {
                                    "case": "actual-auth-deadline",
                                    "elapsed_seconds": time.monotonic() - began,
                                    "body": missing_auth,
                                }
                            )
                        async with client.ws_connect(
                            secure + "/api/djconnect/v1/actions/paired"
                        ) as quiet:
                            await quiet.receive_json()
                            await quiet.send_json(
                                {
                                    "type": "auth",
                                    "protocol_version": 1,
                                    "audience": "paired_owner_actions",
                                    **identity,
                                    "device_token": token,
                                }
                            )
                            lease_auth = await quiet.receive_json()
                            assert lease_auth["lease_seconds"] == 300
                            began = time.monotonic()
                            expired = await quiet.receive_json(timeout=304)
                            elapsed = time.monotonic() - began
                            assert expired == {"type": "auth_invalid", "code": "auth_expired"}
                            assert 299 <= elapsed < 304
                            receipts.append(
                                {
                                    "case": "actual-300s-idle-music-only-lease",
                                    "elapsed_seconds": elapsed,
                                    "body": expired,
                                    "lease_connection_id": lease_auth["connection_id"],
                                }
                            )
                        async with client.ws_connect(
                            secure + "/api/djconnect/v1/actions/paired"
                        ) as renewed:
                            await renewed.receive_json()
                            await renewed.send_json(
                                {
                                    "type": "auth",
                                    "protocol_version": 1,
                                    "audience": "paired_owner_actions",
                                    **identity,
                                    "device_token": token,
                                }
                            )
                            renewal = await renewed.receive_json()
                            assert (
                                renewal["type"] == "auth_ok"
                                and renewal["connection_id"] != lease_auth["connection_id"]
                            )
                            await renewed.send_json(
                                {
                                    "id": 1,
                                    "type": "djconnect/read",
                                    "operation": "session/active",
                                    "payload": {},
                                }
                            )
                            same = await renewed.receive_json()
                            assert same["result"]["session"]["session_id"] == session_id
                            receipts.append(
                                {
                                    "case": "lease-renewal-retains-pairing-and-session",
                                    "same_session": True,
                                }
                            )
                    fresh_context = await post(
                        "transport/context", {"contract_version": 1, "identity": identity}
                    )
                    end = await post(
                        "transport/operation",
                        {
                            "identity": identity,
                            "contract_version": 1,
                            "operation_id": new_id(),
                            "operation_epoch": fresh_context["operation_epoch"],
                            "operation": "session/end",
                            "payload": {"session_id": session_id},
                        },
                    )
                    assert end["success"] and end["session"]["session_id"] == session_id
                    withdrawn_recovery = await post(
                        "session/broadcast/recovery",
                        {
                            "contract_version": 1,
                            "identity": identity,
                            "session_id": session_id,
                            "recovery_cursor": original_cursor,
                        },
                        404,
                    )
                    assert "snapshot" not in withdrawn_recovery
            source_hashes = {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "custom_components/djconnect").rglob("*"))
                if p.is_file() and "__pycache__" not in p.parts
            }
            source_hashes[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest()
            Path("/lab/hybrid.json").write_text(
                json.dumps(
                    {
                        "qualification": "PASS_CORE_TLS_HA_BASELINE",
                        "source_hashes": source_hashes,
                        "transport_receipts": receipts,
                        "provider_calls": provider_calls,
                        "accepted_provider_mutations": state["mutations"],
                        "expected_mutations": 4,
                        "real_model_calls": 0,
                        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        "journal_bytes": (directory / ".storage/djconnect_transport_operations")
                        .stat()
                        .st_size,
                        "journal_pre_idle_bytes": journal_pre_idle_bytes,
                        "native": "OPEN",
                        "installed": "NOT_RUN",
                        "provider_boundary": "explicit external music/source fixtures only",
                        "remaining": "Exact independent review and separately owned native/installed/hardware/joint qualification; physical routing remains OPEN",
                    },
                    indent=2,
                )
                + "\n"
            )
            print(
                json.dumps(
                    {
                        "qualification": "PASS_CORE_TLS_HA_BASELINE",
                        "cases": len(receipts),
                        "mutations": state["mutations"],
                    }
                )
            )
        finally:
            if "hybrid_operation_manager" in h.data["djconnect"]:
                await operations(h).close()
            await runner.cleanup()
            await async_shutdown_persistence(h)
            await h.async_stop(force=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        import traceback

        print(
            json.dumps(
                {
                    "failure_type": type(exc).__name__,
                    "frames": [
                        (Path(f.filename).name, f.lineno, f.name)
                        for f in traceback.extract_tb(exc.__traceback__)
                    ],
                }
            )
        )
        raise SystemExit(1)
