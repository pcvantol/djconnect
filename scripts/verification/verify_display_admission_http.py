"""Own real HA HTTPS pairing/B transition chain, with external provider fixtures.

No snapshot/live/renderer, public TLS, rendezvous A, installed or native PASS.
Run networkless in the existing HA image with source read-only and /lab tmpfs.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import ssl
import sys

from aiohttp import ClientSession, TCPConnector
from aiohttp.test_utils import TestClient, TestServer
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from homeassistant import auth
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import ConfigEntries, ConfigEntryStore, ConfigEntryState
from homeassistant.core import HomeAssistant, CoreState
from homeassistant.helpers import aiohttp_client, area_registry, device_registry, entity_registry

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", "/work"))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]
from verify_session_conversation_history_http import entry  # noqa: E402
from custom_components.djconnect import DJConnectRuntime, register_http_views  # noqa: E402
from custom_components.djconnect.display_transport import transition_views  # noqa: E402
from custom_components.djconnect.domain.backend import BackendProvider  # noqa: E402
from custom_components.djconnect.domain.music_account import MusicAccountKind  # noqa: E402
from custom_components.djconnect.domain.storage import ProfilePlatformStorage  # noqa: E402
from custom_components.djconnect.domain import ProfilePrivacyMode  # noqa: E402
from custom_components.djconnect.persistence import async_initialize_persistence, async_shutdown_persistence  # noqa: E402
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository  # noqa: E402
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository  # noqa: E402
from custom_components.djconnect.session_facts import SessionFactsResolver  # noqa: E402
from custom_components.djconnect.session_runtime import SessionRuntimeManager  # noqa: E402
from custom_components.djconnect.spotify_backend import SpotifyBackend  # noqa: E402


def local_tls(directory):
    """Ephemeral isolated-lab CA trust only; no public hostname qualification."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Own B loopback probe")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1)).add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .sign(key, hashes.SHA256()))
    private = directory / "loopback-key.pem"
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    private.chmod(0o600)
    public = directory / "loopback-cert.pem"
    public.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(public, private)
    client = ssl.create_default_context(cafile=str(public))
    return server, client


async def main():
    directory = Path("/lab") / ("display-b-" + secrets.token_hex(4))
    directory.mkdir(parents=True)
    hass = HomeAssistant(str(directory))
    hass.state = CoreState.running
    hass.config.language = "en"
    selected = "https://ha.display-lab.djconnect.dev"
    hass.config.external_url = selected
    device_registry.async_setup(hass)
    await device_registry.async_load(hass, load_empty=True)
    await entity_registry.async_load(hass, load_empty=True)
    await area_registry.async_load(hass, load_empty=True)
    hass.auth = await auth.auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    hass.http = HomeAssistantHTTP(hass, None, None, None, ["127.0.0.1"], 0, [], "modern")
    await hass.http.async_initialize(cors_origins=[], use_x_forwarded_for=False,
        login_threshold=-1, is_ban_enabled=False, use_x_frame_options=True)
    identity = {"device_id": "djconnect-ios-ABCDEF123456", "client_type": "ios"}
    slot = entry("display-owner", {**identity, "pair_code": "123456", "profile_id": "profile-a",
        "music_backend": "spotify_direct", "music_account_id": "fixture-account",
        "spotify_client_id": "fixture-client", "spotify_refresh_token": "fixture-never-sent"})
    await ConfigEntryStore(hass).async_save({"entries": [slot.as_storage_fragment]})
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    slot = hass.config_entries.async_get_entry("display-owner")
    slot._async_set_state(hass, ConfigEntryState.LOADED, None)
    runtime = DJConnectRuntime(slot)
    hass.data["djconnect"] = {slot.entry_id: runtime, "runtime": runtime}
    storage = ProfilePlatformStorage(hass)
    hass.data["djconnect"]["djconnect_profile_platform"] = storage
    await storage.async_upsert_music_backend("spotify_direct", BackendProvider.SPOTIFY_DIRECT,
                                            display_name="Isolated provider fixture")
    await storage.async_create_profile("Synthetic owner", profile_id="profile-a", default_backend_id="spotify_direct")
    await storage.async_upsert_music_account("fixture-account", "spotify_direct", kind=MusicAccountKind.PERSONAL,
        display_name="Synthetic account", linked_profile_ids=frozenset({"profile-a"}), provider_account_id="fixture-client")
    profile = storage.household.profiles["profile-a"]
    await storage.async_update_profile("profile-a", preferences=replace(profile.preferences,
                                                                       default_music_account_id="fixture-account"))
    await storage.async_upsert_device(identity["device_id"], "ios", linked_profile_id="profile-a")
    service = await async_initialize_persistence(hass)
    manager = SessionRuntimeManager(PersistentSessionRepository(service), HistoricalProjectionRepository(service))
    hass.data["djconnect"]["session_runtime_manager"] = manager
    calls = []

    async def provider(self, method, path, **kwargs):
        assert method.upper() == "GET", "No mutation is allowed in provider fixture"
        calls.append(path)
        if path == "/me/player":
            return {"is_playing": True, "progress_ms": 1000, "device": {"id": "fixture", "name": "Fixture"},
                "item": {"id": "A" * 22, "uri": "spotify:track:" + "A" * 22, "type": "track",
                         "name": "Fixture track", "artists": [{"id": "B" * 22, "name": "Fixture artist"}],
                         "duration_ms": 300000, "album": {"id": "C" * 22, "name": "Fixture album", "images": []}}}
        if path == "/me/player/queue":
            return {"queue": []}
        if path.startswith("/me/tracks/contains"):
            return [False]
        return {}

    async def facts(self, path, params=None, **kwargs):
        calls.append("knowledge:" + path)
        return {}

    SpotifyBackend._request = provider
    SessionFactsResolver._get = facts
    provider_session = ClientSession()
    key = aiohttp_client._make_key(True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT)
    hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})[key] = provider_session
    register_http_views(hass)
    # Actual production views, manually registered until the whole B surface is
    # implemented/qualified; no incomplete capability is advertised in product.
    for view in transition_views(hass):
        hass.http.register_view(view)
    server_ssl, client_ssl = local_tls(directory)
    server = TestServer(hass.http.app, scheme="https")
    await server.start_server(ssl=server_ssl)
    checks = []
    try:
        async with TestClient(server, connector=TCPConnector(ssl=client_ssl)) as client:
            paired_response = await client.post("/api/djconnect/v1/pair", json={**identity, "pair_code": "123456"})
            paired = await paired_response.json()
            assert paired_response.status == 200 and paired["device_token"] == slot.data["device_token"]
            checks.append("normal_pairing_minted_persisted_device_token")
            owner_headers = {"Authorization": "Bearer " + paired["device_token"]}

            async def post(action, body, *, owner=False, headers=None, expected=200, origin=selected):
                request_headers = {**(owner_headers if owner else {}), **(headers or {})}
                if origin is not None:
                    request_headers["Origin"] = origin
                payload = {"contract_version": 1, **body}
                if owner:
                    payload["identity"] = identity
                response = await client.post("/api/djconnect/v1/display/" + action,
                                             json=payload, headers=request_headers)
                result = await response.json()
                assert response.status == expected, (action, response.status, result)
                assert response.headers["Cache-Control"] == "no-store"
                return result

            response = await client.post("/api/djconnect/v1/session/start", headers=owner_headers,
                json={**identity, "mood": "groove", "locale": "en"})
            started = await response.json()
            assert response.status == 201, started
            sid = started["session"]["session_id"]
            context = await post("owner/context", {}, owner=True, origin=None)
            assert context["session_id"] == sid
            checks.append("existing_session_start_and_native_owner_context")
            before = len(calls)
            nonce = secrets.token_urlsafe(32)
            claim = await post("claim", {"browser_nonce": nonce})
            await post("claim", {"browser_nonce": nonce}, origin=None, expected=403)
            await post("claim", {"browser_nonce": nonce}, origin="https://foreign.example.net", expected=403)
            resolved = await post("owner/resolve", {"code": claim["code"]}, owner=True)
            assert resolved["claim_id"] == claim["claim_id"] and "claim_secret" not in resolved
            fields = {name: claim[name] for name in ("issuer_epoch", "claim_id", "browser_generation", "code")}
            approval = await post("owner/approve", fields | {"session_id": sid,
                "share": {"mode": "create", "consent": True}}, owner=True)
            retry = await post("owner/approve", fields | {"session_id": sid,
                "share": {"mode": "create", "consent": True}}, owner=True)
            assert retry["display_id"] == approval["display_id"]
            assert "grant_token" not in approval
            browser = {name: claim[name] for name in ("issuer_epoch", "claim_id", "claim_secret", "browser_generation")}
            admitted = await post("collect", browser | {"browser_nonce": nonce})
            await post("collect", browser | {"browser_nonce": nonce}, expected=404)
            checks.append("claim_resolve_explicit_approve_retry_one_time_collection")
            grant = {name: admitted[name] for name in ("issuer_epoch", "display_id")}
            display_headers = {"Authorization": "Bearer " + admitted["grant_token"]}
            await post("owner/context", {"identity": identity}, headers=display_headers, expected=401)
            renewed = await post("renew", grant | {"renew_sequence": 1}, headers=display_headers)
            retry = await post("renew", grant | {"renew_sequence": 1}, headers=display_headers)
            assert renewed["lease_revision"] == retry["lease_revision"] == 1
            await post("renew", grant | {"renew_sequence": 3}, headers=display_headers, expected=409)
            assert len(calls) == before, "B reads/transitions must not call providers"
            checks.append("dedicated_read_only_grant_origin_fence_idempotent_renew_no_provider_effect")
            await post("owner/revoke", {"session_id": sid, "share_id": admitted["share_id"],
                "display_id": admitted["display_id"]}, owner=True)
            await post("renew", grant | {"renew_sequence": 2}, headers=display_headers, expected=401)
            assert manager.current_active("profile-a").session_id == sid
            checks.append("explicit_display_revoke_preserves_owner_session")
            # New admission in the same explicit share, then actual persisted
            # privacy A→B→A writes with no intermediate authority read/prune.
            nonce2 = secrets.token_urlsafe(32)
            claim2 = await post("claim", {"browser_nonce": nonce2})
            fields2 = {name: claim2[name] for name in ("issuer_epoch", "claim_id", "browser_generation", "code")}
            await post("owner/approve", fields2 | {"session_id": sid, "share": {"mode": "existing",
                "share_id": admitted["share_id"], "share_generation": admitted["share_generation"]}}, owner=True)
            browser2 = {name: claim2[name] for name in ("issuer_epoch", "claim_id", "claim_secret", "browser_generation")}
            admitted2 = await post("collect", browser2 | {"browser_nonce": nonce2})
            await storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.PRIVATE)
            await storage.async_update_profile("profile-a", privacy_mode=ProfilePrivacyMode.NORMAL)
            await post("renew", {name: admitted2[name] for name in ("issuer_epoch", "display_id")} |
                {"renew_sequence": 1}, headers={"Authorization": "Bearer " + admitted2["grant_token"]}, expected=401)
            assert not manager._display_admission._shares
            assert manager.current_active("profile-a").session_id == sid
            checks.append("real_profile_storage_privacy_ABA_irreversibly_revokes_share_without_session_end")
            response = await client.post("/api/djconnect/v1/session/end", headers=owner_headers,
                                         json={**identity, "session_id": sid})
            ended = await response.json()
            assert response.status == 200, ended
            assert not manager._display_admission._shares
            checks.append("ordinary_session_end_clears_all_share_authority")
            print(json.dumps({"qualification": "REAL_ISOLATED_HA_HTTPS_PAIRING_B_TRANSITIONS_ONLY",
                "checks": checks, "provider_calls_during_B": 0,
                "credentials": "ephemeral ordinary device pairing only; never exported",
                "snapshot_live_renderer_A_public_TLS_native_installed_hardware": "NOT_QUALIFIED"}), flush=True)
    finally:
        await server.close()
        await provider_session.close()
        await async_shutdown_persistence(hass)
        await hass.async_stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
