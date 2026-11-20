"""Independent real-HA/paired HTTP proof with declared offline source/model fixtures.

Run only against an immutable candidate mounted read-only in a network-none HA
container and an empty private lab. Never use the installed HA-dev configuration.
This proves integration, not real-provider, editorial or physical acceptance.
"""
import ast
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import ipaddress
import inspect
import json
import os
from pathlib import Path
import ssl
import sys
import textwrap
import traceback
from types import SimpleNamespace
from unittest.mock import patch
import uuid
from datetime import datetime, timedelta, timezone

ROOT = Path(os.environ["DJC_SOURCE_ROOT"])
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]
import verify_session_conversation_history_http as owning_harness


def targeted_driver():
    """Reuse exact real-HA setup/pairing, without claiming the old turn suite.

    The untouched complete old suite is separately baseline-tested. This is a
    new gate for new Moments operations, not a weakened old expected result.
    Fail closed if the owning setup/pairing anchor no longer has that shape.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(owning_harness.main)))
    original = tree.body[0]
    block_index = next(i for i, node in enumerate(original.body) if isinstance(node, ast.AsyncWith))
    block = original.body[block_index]
    pairing_index = next(i for i, node in enumerate(block.body)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "append"
        and any(isinstance(x, ast.Constant) and x.value == "ha_user_credentials_issued" for x in ast.walk(node)))
    block.body = block.body[:pairing_index + 1] + ast.parse(
        "extension_result = await qualification_extension(hass, manager, history, request, client)").body
    ending = ast.parse('''
await async_shutdown_persistence(hass)
assert source_hashes() == qualified_sources, "source changed during qualification"
assert len(fixture_agent_calls) == 0, "New driver must not run unrelated model turns"
from homeassistant.const import __version__ as sdk_version
result = {"qualification": "actual isolated HA SDK/verified TLS/paired auth/Hybrid/SQLite; declared offline public/model inputs", "legacy_turn_suite": "NOT_EXECUTED_BY_THIS_NEW_GATE; separate pristine baseline evidence retained", "ha_sdk_version": sdk_version, "source_files_sha256": qualified_sources, "source_unchanged": True, "setup_fixture_model_calls": len(fixture_agent_calls), "extension": extension_result}
output = directory / "http-requested-moments-receipt.json"
output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(json.dumps({"result": "PASS", "receipt": str(output), "targeted_https_requests": len(extension_result["requests"])}))
''').body
    original.name = "_requested_http_main"
    original.body = original.body[:block_index] + [block] + ending
    ast.fix_missing_locations(tree)
    exec(compile(tree, "declared-owning-setup-requested-http-driver", "exec"), owning_harness.__dict__)
    return owning_harness._requested_http_main


def offline_fixture(research):
    """Reuse audited source/model vectors, without importing HA-stub test setup."""
    from source_fixture_urls import fixture_host, fixture_location, wikipedia_api_fixture
    path = ROOT / "tests/test_personal_dj_narration_public_artist.py"
    source = path.read_text()
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "PublicArtistNarrationTest")
    namespace = {"json": json, "fixture_host": fixture_host,
                 "fixture_location": fixture_location, "wikipedia_api_fixture": wikipedia_api_fixture}
    for method in cls.body:
        if isinstance(method, ast.AsyncFunctionDef) and method.name in {"model", "fetch"}:
            exec(compile(textwrap.dedent(ast.get_source_segment(source, method)), str(path), "exec"), namespace)
    fixture = SimpleNamespace(research=research, calls=[], urls=[], fetch_owners=[],
        answer="Bij Paper Lanterns werkte Nora Vale 1 samen met Ada Reed. Zo kijk ik graag even mee achter een naam.",
        fetch_qid="Q1", bad_review=False, after_fetch=None, source_index=0, second_only=False,
        producer_mode=False, composer_mode=False, actor_name_override=None,
        reciprocal_id_override=None, producer_unsupported=False, after_draft=None,
        recording_focus_preserved=True, article_fixture=None)
    fixture.fetch = lambda *a, **k: namespace["fetch"](fixture, *a, **k)
    fixture.model = lambda *a, **k: namespace["model"](fixture, *a, **k)
    fixture.vector_sha256 = hashlib.sha256(source.encode()).hexdigest()
    return fixture


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import api_handlers, pipeline, session_facts
    from custom_components.djconnect.ask_dj import public_research
    from custom_components.djconnect.hybrid_service import operations
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    from custom_components.djconnect.domain.profile.dj_settings import DJSettings
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.persistence.dj_settings import ProfileDJSettingsRepository
    from custom_components.djconnect.session_runtime import IntraTrackOpportunity
    from tests.context_variation_fixtures import source

    async def no_external(*a, **k):
        return None

    active = manager.current_active("profile-a")
    if active:
        await manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
    manager._settings_repository = ProfileDJSettingsRepository(persistence_service(hass))
    before, code = await request("GET", "/api/djconnect/v1/profile/settings", {"contract_version": 3})
    assert code == 200
    configured, code = await request("PATCH", "/api/djconnect/v1/profile/settings", {
        "contract_version": 3, "binding": before["binding"], "operation_id": str(uuid.uuid7()),
        "patch": DJSettings(presence="music_only").as_dict(), "expected_defaults_revision": before["snapshot"]["defaults_revision"],
        "expected_session": None})
    assert code == 200
    with patch.object(api_handlers, "_async_generate_initial_session_moment", no_external), \
         patch.object(PlaybackObservationManager, "async_start_spotify", no_external):
        started, code = await request("POST", "/api/djconnect/v1/session/start", {"mood": "energy", "locale": "nl"})
    assert code == 201
    active = manager.current_active("profile-a")
    sid = active.session_id
    catalog, fact = source("formation", 0)
    fact = replace(fact, public_artist_qid="Q1")
    await manager.async_update_playback_projection(owner_profile_id="profile-a", session_id=sid,
        state="paused", media_identity=catalog["uri"], title=catalog["title"], artist=catalog["artist"],
        duration_ms=300000, position_ms=0)
    active = manager.current_active("profile-a")
    assert active.selected_presence == "music_only"
    fixture = offline_fixture(public_research)
    narration_debug = {}
    original_realize = pipeline.realize_session_narration
    original_agent_call = pipeline.call_conversation_process_with_agent_retry
    async def traced_agent_call(*args, **kwargs):
        try:
            return await original_agent_call(*args, **kwargs)
        except Exception as error:
            narration_debug["agent_exception_type"] = type(error).__name__
            narration_debug["agent_exception_frames"] = [
                {"file": Path(f.filename).name, "function": f.name, "line": f.lineno}
                for f in traceback.extract_tb(error.__traceback__)]
            raise
    async def traced_realize(*args, **kwargs):
        if kwargs.get("debug") is None:
            kwargs["debug"] = {}
        result = await original_realize(*args, **kwargs)
        supplied = kwargs.get("debug") or {}
        narration_debug.update({k: supplied[k] for k in ("block_reason", "model_attempts", "agent_retry_without_agent_id") if k in supplied})
        narration_debug["owner_invocations"] = narration_debug.get("owner_invocations", 0) + 1
        return result
    runtime = hass.data["djconnect"]["owner-entry"]
    manager._hass = hass
    async def provider(brief, guard):
        return await pipeline.realize_session_narration(hass, narration=brief, admission=guard,
            fallback_text=brief.seed, conf=runtime.config, debug=narration_debug)
    manager.connect_narration("profile-a", sid, provider, lambda: None)
    manager._intra_track_opportunities["profile-a"] = IntraTrackOpportunity(sid, catalog["uri"],
        active.broadcast.state.playback.item_id, ("backend", "account", "provider", "provider-account"),
        qualified_facts=(fact,))
    device_id = runtime.entry.data["device_id"]
    identity = {"device_id": device_id, "client_type": "ios"}
    headers = {"Authorization": "Bearer " + runtime.entry.data["device_token"], "X-DJConnect-Device-ID": device_id}
    receipts = []
    async def http(path, body, *, authorized=True):
        response = await client.post(path, json={"identity": identity, **body}, headers=headers if authorized else {})
        data = await response.json()
        receipts.append({"path": path, "status": response.status, "scheme": response.url.scheme})
        assert response.url.scheme == "https"
        assert response.headers.get("Cache-Control") == "no-store"
        return data, response.status
    async def read(operation, payload):
        return await http("/api/djconnect/v1/transport/read", {
            "contract_version": 1, "operation": operation, "payload": {"contract_version": 1, **payload}})
    context, code = await http("/api/djconnect/v1/transport/context", {"contract_version": 1})
    assert code == 200
    epoch = operations(hass).journal.epoch
    with patch.object(public_research.PublicFetch, "request", lambda fetch, url, **kw: fixture.fetch(fetch, url, **kw)), \
         patch.object(pipeline, "realize_session_narration", traced_realize), \
         patch.object(pipeline, "call_conversation_process_with_agent_retry", traced_agent_call), \
         patch.object(pipeline, "_call_conversation_process_transport", fixture.model):
        inventory, code = await read("ask_dj/moments", {"session_id": sid})
        assert code == 200 and len(inventory["types"]) == 10
        assert fixture.calls == fixture.urls == []
        chosen = next(t for t in inventory["types"] if t["type_id"] == "artist_story")
        envelope = {"contract_version": 1, "operation_id": str(uuid.uuid7()), "operation_epoch": epoch,
            "operation": "ask_dj/moments/request", "payload": {"contract_version": 1,
                "session_id": sid, "type_id": "artist_story", "subject_ref": chosen["subject"]["subject_ref"]}}
        ledger = deepcopy(active.presence_ledger.__dict__)
        accepted, code = await http("/api/djconnect/v1/transport/operation", envelope)
        if code != 200 or accepted.get("state") != "accepted":
            (Path(os.environ["DJC_LAB_ROOT"]) / "fixture-diagnostic.json").write_text(json.dumps({
                "http_status": code, "state": accepted.get("state"),
                "fixture_model_calls": len(fixture.calls), "fixture_public_reads": len(fixture.urls),
                "debug": narration_debug,
                "captured_fact_kinds": [x.key for x in hass.data["djconnect"]["requested_moments"].requests[envelope["operation_id"]].captured.facts],
                "captured_catalog_present": bool(hass.data["djconnect"]["requested_moments"].requests[envelope["operation_id"]].captured.catalog),
                "subject_type": chosen["subject"]["kind"], "selected_available": chosen["available"]}, indent=2) + "\n")
        assert code == 200 and accepted["state"] == "accepted", accepted
        result = accepted["result"]
        assert result["retention"] == "retained" and result["moment"]["type"] == "artist"
        assert len(fixture.calls) == 2 and active.presence_ledger.__dict__ == ledger
        status, code = await read("ask_dj/moments/status", {"session_id": sid, "operation_id": envelope["operation_id"]})
        assert code == 200 and status["moment_id"] == result["moment"]["moment_id"]
        assert status["result"]["presentation_admission"] == result["presentation_admission"]
        retry, code = await http("/api/djconnect/v1/transport/operation", envelope)
        assert code == 200 and len(fixture.calls) == 2
        denied, code = await http("/api/djconnect/v1/transport/read", {
            "contract_version": 1, "operation": "ask_dj/moments", "payload": {"contract_version": 1, "session_id": sid}}, authorized=False)
        assert code in {401, 403}
    return {"scope": "real HA HTTP/paired auth/operation/Knowledge/Moment/SQLite; declared offline public/model vectors",
        "requests": receipts, "fixture_model_calls": len(fixture.calls), "fixture_public_reads": len(fixture.urls),
        "live_provider_calls": 0, "source_vector_sha256": fixture.vector_sha256,
        "operation_id": envelope["operation_id"], "moment_id": result["moment"]["moment_id"],
        "entry_id": result["entry_id"], "inventory_count": 10, "proactive_ledger_unchanged": True,
        "installed_or_physical_acceptance": "NOT_CLAIMED"}


async def run():
    """Use real TLS instead of inventing a positive LAN qualification receipt."""
    from aiohttp import TCPConnector
    from aiohttp.test_utils import TestClient, TestServer
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    lab = Path(os.environ["DJC_LAB_ROOT"])
    cert, key = lab / "fixture-localhost-cert.pem", lab / "fixture-localhost-private-key.pem"
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DJConnect isolated fixture CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = (x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca_name).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))
    ca_path = lab / "fixture-localhost-ca.pem"
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert.write_bytes(leaf.public_bytes(serialization.Encoding.PEM) + ca.public_bytes(serialization.Encoding.PEM))
    with key.open("xb") as output:
        key.chmod(0o600)
        output.write(server_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert, key)
    client_context = ssl.create_default_context(cafile=str(ca_path))
    class LocalTLSServer(TestServer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, scheme="https", **kwargs)
        async def start_server(self, **kwargs):
            return await super().start_server(ssl=server_context, **kwargs)
    def trusted_client(server):
        return TestClient(server, connector=TCPConnector(ssl=client_context))
    # HA 2026.11 registry loading awaits ConfigEntries initialization. The older
    # owning harness initializes its fixture entries later; initialize the empty
    # manager first through the real SDK, without faking its initialized event.
    from homeassistant.config_entries import ConfigEntries
    load_registry = owning_harness.entity_registry.async_load
    async def load_after_empty_entries(hass, *args, **kwargs):
        from homeassistant.helpers import frame
        from homeassistant import loader
        frame.async_setup(hass)
        if not hass.data.get("requested_http_fixture_loader_ready"):
            custom = Path(hass.config.config_dir) / "custom_components"
            custom.symlink_to(ROOT / "custom_components", target_is_directory=True)
            loader.async_setup(hass)
            await loader.async_get_integration(hass, "djconnect")
            hass.data["requested_http_fixture_loader_ready"] = True
        if hass.config_entries is None:
            hass.config_entries = ConfigEntries(hass, {})
            await hass.config_entries.async_initialize()
        return await load_registry(hass, *args, **kwargs)
    with patch.object(owning_harness, "TestServer", LocalTLSServer), \
         patch.object(owning_harness, "TestClient", trusted_client), \
         patch.object(owning_harness.entity_registry, "async_load", load_after_empty_entries):
        try:
            driver = owning_harness.main if os.environ.get("DJC_BASELINE_ONLY") == "1" else targeted_driver()
            await driver(qualification_extension=None if os.environ.get("DJC_BASELINE_ONLY") == "1" else qualify)
        except AssertionError as error:
            tb = error.__traceback__
            while tb is not None:
                values = tb.tb_frame.f_locals
                if tb.tb_frame.f_code.co_name == "main" and "fixture_agent_calls" in values:
                    (lab / "owning-harness-diagnostic.json").write_text(json.dumps({
                        "baseline_fixture_calls": len(values["fixture_agent_calls"]),
                        "extension_completed": values.get("extension_result") is not None,
                        "extension_result": values.get("extension_result"),
                        "failed_line": tb.tb_lineno}, indent=2) + "\n")
                tb = tb.tb_next
            raise


if __name__ == "__main__":
    asyncio.run(run())
