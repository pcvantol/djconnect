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
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlparse
from uuid import UUID

from aiohttp import ClientSession, TCPConnector, web, ClientConnectorCertificateError
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
        state = {"index": 1, "mutations": 0}

        async def provider_token(self, **kwargs):
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
                    self.status, self.payload = 200, {"queue": []}
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
        plain_site = web.TCPSite(runner, "127.0.0.1", 0)
        await plain_site.start()
        secure = "https://127.0.0.1:" + str(secure_site._server.sockets[0].getsockname()[1])
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
                            receipts.append({"path": path, "status": result.status, "body": data})
                            assert result.status == expected, (path, result.status, data)
                            assert result.headers.get("Cache-Control") == "no-store"
                            return data

                    ctx = await post(
                        "transport/context", {"contract_version": 1, "identity": identity}
                    )
                    assert ctx["ha_install_id"] == "ha_owned_hybrid_fixture"
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
                        "session/start",
                        {**identity, "mood": "groove", "dj_persona": "home_dj", "language": "en"},
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
                    async with client.ws_connect(
                        secure + "/api/djconnect/v1/actions/paired"
                    ) as wrong:
                        await wrong.receive_json()
                        await wrong.send_json(
                            {
                                "type": "auth",
                                "protocol_version": 1,
                                "audience": "paired_owner_broadcast",
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
                        receipts.append({"case": "actual-wss-next", "body": executed})
                        before = state["mutations"]
                        duplicate = await post(
                            "transport/operation", {"identity": identity, **request}
                        )
                        assert (
                            duplicate["operation_receipt"]["phase"] == "confirmed"
                            and state["mutations"] == before
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
                    # Reopen durable journal under a fresh boot epoch: known result stays confirmed.
                    old = operations(h)
                    await old.close()
                    h.data["djconnect"].pop("hybrid_operation_manager")
                    await post("transport/operation/status", {"identity": identity, **status})
                    await post("transport/operation", {"identity": identity, **request}, 409)
                    end = await post("session/end", {**identity, "session_id": session_id})
                    assert end["success"]
            source_hashes = {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((ROOT / "custom_components/djconnect").rglob("*.py"))
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
                        "expected_mutations": 2,
                        "real_model_calls": 0,
                        "native": "OPEN",
                        "installed": "NOT_RUN",
                        "provider_boundary": "explicit external music/source fixtures only",
                        "remaining": "full races/revocation/recovery/liveness and consumer qualification still required",
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
