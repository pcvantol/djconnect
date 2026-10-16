"""Own real HA HTTPS pairing/B transition/snapshot chain, external provider fixtures.

Basic live is exercised; no public TLS, rendezvous A, installed or native PASS.
Run networkless in the existing HA image with source read-only and /lab tmpfs.
"""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
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
import time
import resource
import hashlib
import signal
import base64

from aiohttp import ClientSession, TCPConnector, WSMsgType, web
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
from custom_components.djconnect.display_delivery import display_live_hub  # noqa: E402
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


def public_transport_fixture(examples):
    """Only synthetic-lab wire data; replace every credential/nonce/claim ID.

    Replacements depend solely on ordinal position, never hash a real secret.
    Preserve equality/shape for consumers, but no fixture can authenticate.
    """
    opaque = {"grant_token", "claim_secret", "browser_nonce", "connection_nonce",
              "issuer_epoch", "claim_id", "browser_generation", "display_id", "share_id"}
    replacements, originals = {}, set()
    def clean(value, key=""):
        if key not in opaque and any(term in key.lower() for term in (
                "token", "secret", "password", "proof", "authorization", "raw_audio", "prompt", "history", "memory")):
            raise AssertionError("Unexpected private field in public fixture")
        if isinstance(value, dict):
            return {name: clean(item, name) for name, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if key in opaque and isinstance(value, str):
            originals.add(value)
            if value not in replacements:
                fake = base64.urlsafe_b64encode(hashlib.sha256(
                    ("public noncredential fixture " + str(len(replacements))).encode()).digest()).decode().rstrip("=")
                replacements[value] = ("djcd_" if value.startswith("djcd_") else "") + fake
            return replacements[value]
        if key == "code":
            return "000000" if value != "000000" else "999999"
        return value
    result = {"fixture_version": 1, "scope": "actual_isolated_HA_B_transport",
        "credentials": "replaced_nonfunctional_examples_not_replayable", "A": "unavailable",
        "examples": clean(examples)}
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    assert len(encoded.encode()) <= 1024 * 1024
    assert not any(secret in encoded for secret in originals), "Credential redaction failed"
    return encoded


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
    paths = sorted((ROOT / "custom_components/djconnect").rglob("*.py")) + [Path(__file__)]
    qualified_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
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
    request_path = ContextVar("display_probe_request_path", default="background")

    @web.middleware
    async def trace_provider_origin(request, handler):
        trace = request_path.set(request.path)
        began = time.monotonic()
        trace_http = bool(os.environ.get("DJC_DISPLAY_BROWSER_PORT")) and request.path in {
            "/api/djconnect/v1/display/claim", "/api/djconnect/v1/display/cancel"}
        if trace_http:
            print("DISPLAY_LAB_REQUEST " + request.path, flush=True)
        try:
            return await handler(request)
        finally:
            request_path.reset(trace)
            if trace_http:
                print("DISPLAY_LAB_HANDLER_SECONDS " + str(round(time.monotonic()-began, 3)), flush=True)

    hass.http.app.middlewares.append(trace_provider_origin)

    async def provider(self, method, path, **kwargs):
        assert method.upper() == "GET", "No mutation is allowed in provider fixture"
        calls.append({"provider_path": path, "request_path": request_path.get()})
        if path == "/me/player":
            # Optional real-browser test controls only this external provider
            # fixture. Runtime/Planner/publication clocks are never rewritten.
            if os.environ.get("DJC_DISPLAY_BROWSER_PORT") and not Path("/lab/display-playback-ready").exists():
                return {}
            return {"is_playing": True, "progress_ms": 1000, "device": {"id": "fixture", "name": "Fixture"},
                "item": {"id": "A" * 22, "uri": "spotify:track:" + "A" * 22, "type": "track",
                         "name": "Fixture track", "artists": [{"id": "B" * 22, "name": "Fixture artist"}],
                         "external_ids": {"isrc": "USAAA0100001"},
                         "duration_ms": 300000, "album": {"id": "C" * 22, "name": "Fixture album", "images": []}}}
        if path == "/me/player/queue":
            return {"queue": []}
        if path.startswith("/me/tracks/contains"):
            return [False]
        if path.startswith("/artists/"):
            return {"id": "B" * 22, "name": "Fixture artist", "genres": []}
        if path.startswith("/artists"):
            return {"artists": [{"id": "B" * 22, "name": "Fixture artist", "genres": []}]}
        return {}

    async def facts(self, path, params=None, **kwargs):
        calls.append({"provider_path": "knowledge:" + path, "request_path": request_path.get()})
        if os.environ.get("DJC_DISPLAY_BROWSER_PORT"):
            artist, recording = "12345678-1234-1234-1234-123456789abc", "22345678-1234-1234-1234-123456789abc"
            credit = [{"artist": {"id": artist, "name": "Fixture artist"}}]
            if path.startswith("isrc/"):
                return {"recordings": [{"id": recording, "title": "Fixture track", "artist-credit": credit}]}
            if path.startswith("recording/"):
                return {"id": recording, "title": "Fixture track", "artist-credit": credit, "relations": []}
            if path.startswith("artist/"):
                return {"id": artist, "name": "Fixture artist", "type": "Group", "life-span": {"begin": "1991"},
                    "relations": [{"type": "streaming", "url": {"resource": "https://open.spotify.com/artist/" + "B" * 22}}]}
        return {}

    SpotifyBackend._request = provider
    SessionFactsResolver._get = facts
    provider_session = ClientSession()
    key = aiohttp_client._make_key(True, socket.AF_UNSPEC, aiohttp_client.ssl_util.SSLCipherList.PYTHON_DEFAULT)
    hass.data.setdefault(aiohttp_client.DATA_CLIENTSESSION, {})[key] = provider_session
    register_http_views(hass)
    # Exercise normal production registration; no parallel lab-only B routes.
    server_ssl, client_ssl = local_tls(directory)
    browser_port = int(os.environ.get("DJC_DISPLAY_BROWSER_PORT", "0"))
    server = TestServer(hass.http.app, scheme="https", host="0.0.0.0" if browser_port else "127.0.0.1", port=browser_port)
    await server.start_server(ssl=server_ssl)
    checks = []
    wire_examples = []
    try:
        if browser_port:
            finished = asyncio.Event()
            asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, finished.set)
            print("DISPLAY_BROWSER_LAB_READY", flush=True)
            for _ in range(20):
                try:
                    await asyncio.wait_for(finished.wait(), 15)
                    break
                except TimeoutError:
                    active = manager.current_active("profile-a")
                    if active is not None:
                        current = active.broadcast.state
                        print("DISPLAY_LAB_RUNTIME " + json.dumps({
                            "published_types": [getattr(m.moment_type, "value", m.moment_type)
                                                for m in current.dj_moments[-8:]],
                            "flow_count": len(current.session_flow.items),
                            "provider_calls": len(calls),
                            "presence": getattr(current.selected_presence, "value", current.selected_presence),
                            "broadcast_sequence": active.broadcast.delivery_sequence,
                        }), flush=True)
            if not finished.is_set():
                await finished.wait()
            return
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
                assert len(wire_examples) < 64
                wire_examples.append({"transport": "HTTP", "method": "POST",
                    "path": "/api/djconnect/v1/display/" + action,
                    "authentication": "ordinary_paired_owner" if owner else "dedicated_display" if headers else "none",
                    "origin": origin, "request": payload, "status": response.status,
                    "cache_control": response.headers["Cache-Control"], "response": result})
                return result

            response = await client.post("/api/djconnect/v1/session/start", headers=owner_headers,
                json={**identity, "mood": "groove", "locale": "en"})
            started = await response.json()
            assert response.status == 201, started
            sid = started["session"]["session_id"]
            context = await post("owner/context", {}, owner=True, origin=None)
            assert context["session_id"] == sid
            checks.append("existing_session_start_and_native_owner_context")
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
            # Even with the real paired device identity copied into a body, a
            # dedicated display token is never ordinary owner/control authority.
            for path, body in (
                ("session/end", {"session_id": sid}),
                ("session/mood", {"contract_version": 1, "session_id": sid,
                    "selected_mood": "party", "expected_mood_revision": 0}),
                ("session/presence", {"contract_version": 1, "session_id": sid,
                    "selected_presence": "music_only", "expected_presence_revision": 0}),
                ("command", {"command": "pause"}),
                ("ask_dj/message", {"client_message_id": "own-display-denial-probe",
                    "text": "What is playing?", "audio_response": "never"}),
            ):
                response = await client.post("/api/djconnect/v1/" + path,
                    headers=display_headers, json={**identity, **body})
                assert response.status in {401, 403}, (path, response.status)
            assert manager.current_active("profile-a").session_id == sid
            checks.append("display_bearer_denied_owner_end_mood_presence_playback_and_private_Ask_DJ")
            snapshot = (await post("snapshot", grant, headers=display_headers))["snapshot"]
            assert snapshot["session"]["session_id"] == sid
            assert set(snapshot["session_presentation"]) <= {"mood", "persona", "presence"}
            wire = json.dumps(snapshot)
            for private in ("profile_id", "account_id", "device_id", "planner", "session_flow", "conversation",
                            "history", "voice", "gender", "announcement_output", "up_next", "artwork_url"):
                assert '"' + private + '"' not in wire, private
            checks.append("dedicated_display_snapshot_explicit_closed_shared_allowlist")
            # Real pending-upgrade source budget: existing two sockets survive,
            # a third cannot evict them, and closing frees both reservations.
            pending = [await client.ws_connect("/api/djconnect/v1/display/live", headers={"Origin": selected})
                       for _ in range(2)]
            try:
                try:
                    await client.ws_connect("/api/djconnect/v1/display/live", headers={"Origin": selected})
                except Exception as error:
                    assert getattr(error, "status", None) == 429
                else:
                    raise AssertionError("Third unauthenticated source connection was admitted")
                assert display_live_hub(manager).preauth == 2
            finally:
                for connection in pending:
                    await connection.close()
            for _ in range(20):
                if display_live_hub(manager).preauth == 0:
                    break
                await asyncio.sleep(0.01)
            assert display_live_hub(manager).preauth == 0 and not display_live_hub(manager).sources
            checks.append("real_source_preauth_capacity_no_eviction_and_released_slots")
            live = await client.ws_connect("/api/djconnect/v1/display/live", headers={"Origin": selected})
            auth_frame = {"type": "authenticate", "contract_version": 1, "grant_token": admitted["grant_token"],
                "issuer_epoch": admitted["issuer_epoch"], "display_id": admitted["display_id"],
                "connection_nonce": secrets.token_urlsafe(32)}
            await live.send_json(auth_frame)
            first_live = await live.receive_json(timeout=5)
            assert first_live["type"] == "snapshot" and first_live["snapshot"]["session_id"] == sid
            wire_examples.append({"transport": "WSS", "path": "/api/djconnect/v1/display/live",
                "authentication": "dedicated_display_first_frame", "frame": first_live})
            # Existing owner mutation/Broadcast publication, no direct injection
            # of an accepted Moment or display event into the Core chain.
            response = await client.post("/api/djconnect/v1/session/mood", headers=owner_headers,
                json={**identity, "contract_version": 1, "session_id": sid,
                      "selected_mood": "energy", "expected_mood_revision": 0})
            mood_reply = await response.json()
            assert response.status == 200, mood_reply
            for _ in range(6):
                next_live = await live.receive_json(timeout=5)
                if next_live["snapshot"]["session_presentation"].get("mood") == "energy":
                    break
            else:
                raise AssertionError("Live did not reflect confirmed Runtime Mood")
            replacement = await client.ws_connect("/api/djconnect/v1/display/live", headers={"Origin": selected})
            await replacement.send_json(auth_frame | {"connection_nonce": secrets.token_urlsafe(32)})
            second_live = await replacement.receive_json(timeout=5)
            assert second_live["connection_generation"] > first_live["connection_generation"]
            await live.receive(timeout=5)
            await live.close()
            checks.append("real_WSS_snapshot_Broadcast_mood_update_and_superseded_generation")
            renewed = await post("renew", grant | {"renew_sequence": 1}, headers=display_headers)
            retry = await post("renew", grant | {"renew_sequence": 1}, headers=display_headers)
            assert renewed["lease_revision"] == retry["lease_revision"] == 1
            await post("renew", grant | {"renew_sequence": 3}, headers=display_headers, expected=409)
            assert not any(call["request_path"].startswith("/api/djconnect/v1/display/") for call in calls), (
                "B reads/transitions must not call providers")
            checks.append("dedicated_read_only_grant_origin_fence_idempotent_renew_no_provider_effect")
            duration = int(os.environ.get("DJC_DISPLAY_LONG_RUN_SECONDS", "0"))
            assert 0 <= duration <= 120
            duration_receipt = {"state": "NOT_RUN"}
            if duration:
                began, renewed_at, sequence = time.monotonic(), time.monotonic(), 1
                frames, peak_bytes, peak_tasks = 0, 0, 0
                rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                while time.monotonic() - began < duration:
                    try:
                        message = await replacement.receive(timeout=1)
                        assert message.type == WSMsgType.TEXT, (message.type, message.data)
                        update = message.json()
                        assert update["snapshot"]["session_id"] == sid
                        frames += 1
                    except TimeoutError:
                        pass
                    if time.monotonic() - renewed_at >= 20:
                        sequence += 1
                        await post("renew", grant | {"renew_sequence": sequence}, headers=display_headers)
                        renewed_at = time.monotonic()
                    hub = display_live_hub(manager)
                    assert len(hub.connections) == 1 and hub.preauth == 0
                    assert hub.projections <= 8 and hub.reserved_bytes <= 4 * 1024 * 1024
                    peak_bytes = max(peak_bytes, hub.reserved_bytes)
                    peak_tasks = max(peak_tasks, len(asyncio.all_tasks()))
                duration_receipt = {"state": "MEASURED_SINGLE_VIEWER", "elapsed_seconds": round(time.monotonic()-began, 3),
                    "frames": frames, "renewals": sequence-1, "sampled_serialized_reserved_bytes": peak_bytes,
                    "peak_serialized_reserved_bytes": hub.peak_reserved_bytes,
                    "peak_projections": hub.peak_projections, "peak_preauth": hub.peak_preauth,
                    "peak_all_HA_tasks": peak_tasks, "rss_highwater_before_kib": rss_before,
                    "rss_highwater_after_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    "scope": "one viewer, ordinary observation background, no catch-up or lease reset"}
                checks.append("bounded_real_duration_with_online_renewals_no_backlog")
            await post("owner/revoke", {"session_id": sid, "share_id": admitted["share_id"],
                "display_id": admitted["display_id"]}, owner=True)
            await post("renew", grant | {"renew_sequence": 2}, headers=display_headers, expected=401)
            await replacement.receive(timeout=5)
            await replacement.close()
            await asyncio.sleep(0.05)
            hub = display_live_hub(manager)
            assert hub.preauth == 0 and not hub.sources and not hub.connections
            assert hub.reserved_bytes == 0 and hub.projections == 0
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
            assert qualified_hashes == {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                        for path in paths}, "Source changed during acceptance; receipt is not qualified"
            fixture_path = os.environ.get("DJC_DISPLAY_FIXTURE_OUTPUT")
            if fixture_path:
                Path(fixture_path).write_text(public_transport_fixture(wire_examples))
            print(json.dumps({"qualification": "REAL_ISOLATED_HA_HTTPS_DISPLAY_TRANSITIONS_SNAPSHOT_BASIC_LIVE",
                "checks": checks, "provider_calls_during_B": 0,
                "duration": duration_receipt,
                "source_files": len(qualified_hashes), "source_sha256": hashlib.sha256(json.dumps(
                    qualified_hashes, sort_keys=True).encode()).hexdigest(),
                "credentials": "ephemeral ordinary device pairing only; never exported",
                "complete_live_renderer_A_public_TLS_native_installed_hardware": "NOT_QUALIFIED"}), flush=True)
    finally:
        await server.close()
        await provider_session.close()
        await async_shutdown_persistence(hass)
        await hass.async_stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
