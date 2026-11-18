"""Exercise direct-local adapters on the real owned HA/pairing/journal lab."""

import asyncio
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

from aiohttp import ClientSession, TCPConnector, WSServerHandshakeError, web
from homeassistant.components.network import async_get_adapters
from custom_components.djconnect.hybrid_ingress_qualification import FILENAME, interface_digest


async def probe(hass, client, plain, identity, headers, tls_context, session_id, new_id, receipts, provider_calls, state):
    previous = hass.config.internal_url
    hass.config.internal_url = plain
    client = ClientSession(connector=TCPConnector(local_addr=("127.0.0.2", 0)))
    qualification_path = Path(hass.config.config_dir) / FILENAME
    assert not qualification_path.exists()
    record = {
        "version": 1, "ha_install_id": tls_context["ha_install_id"], "internal_origin": plain,
        "interface_digest": interface_digest(await async_get_adapters(hass)),
        "allowed_peers": ["127.0.0.2/32"], "excluded_peers": ["127.0.0.1"],
        "source_preserved": True, "proxies_excluded": True,
        "qualified_at": int(time.time()) - 1, "expires_at": int(time.time()) + 600,
        "evidence_sha256": "a" * 64,
    }

    def provision():
        qualification_path.write_text(json.dumps(record))
        qualification_path.chmod(0o600)

    provision()

    async def post(path, body, expected=200, extra=None, authenticated=True):
        async with client.post(
            plain + "/api/djconnect/v1/" + path,
            json=body,
            headers={**(headers if authenticated else {}), **(extra or {})},
        ) as response:
            result = await response.json()
            assert response.status == expected, (path, response.status, result)
            assert response.headers.get("Cache-Control") == "no-store"
            return result

    try:
        # A real headerless forwarding hop reuses identical token, internal Host
        # and Origin; only its actual socket peer differs from the qualified client.
        async def proxy(request):
            async with ClientSession() as forwarding:
                async with forwarding.post(plain + request.path, data=await request.read(), headers={"Host": urlsplit(plain).netloc, "Origin": plain, "Content-Type": "application/json", **headers}) as reply:
                    return web.Response(status=reply.status, body=await reply.read(), headers={"Content-Type": "application/json"})

        proxy_app = web.Application()
        proxy_app.router.add_post("/{tail:.*}", proxy)
        proxy_runner = web.AppRunner(proxy_app)
        await proxy_runner.setup()
        proxy_site = web.TCPSite(proxy_runner, "127.0.0.1", 0)
        await proxy_site.start()
        proxy_url = "http://127.0.0.1:" + str(proxy_site._server.sockets[0].getsockname()[1])
        try:
            async with client.post(proxy_url + "/api/djconnect/v1/transport/context", json={"contract_version": 1, "identity": identity}, headers={**headers, "Host": urlsplit(plain).netloc, "Origin": plain}) as denied_proxy:
                assert denied_proxy.status == 426
                assert (await denied_proxy.json())["error"] == "transport_security_required"
                receipts.append({"case": "real-headerless-proxy-same-token-host-origin-denied", "status": 426})
        finally:
            await proxy_runner.cleanup()
        context = await post("transport/context", {"contract_version": 1, "identity": identity})
        assert not context["requires_authenticated_tls"]
        assert context["transport_security"]["mode"] == "qualified_direct_http"
        assert context["ha_install_id"] == tls_context["ha_install_id"]
        assert context["operation_epoch"] == tls_context["operation_epoch"]
        receipts.append({"case": "real-direct-loopback-context", "body": context})
        await post("transport/context", {"contract_version": 1, "identity": identity}, extra={"Origin": plain})
        for path in ("transport/context", "transport/operation", "transport/operation/status", "session/broadcast/recovery"):
            await post(path, {}, 426, extra={"Forwarded": "for=192.168.1.20"})
        for extra, expected in (({"Origin": "http://foreign.invalid"}, 403), ({"Forwarded": "for=192.168.1.20"}, 426)):
            try:
                socket = await client.ws_connect(plain + "/api/djconnect/v1/actions/paired", headers=extra)
            except WSServerHandshakeError as exc:
                assert exc.status == expected
                receipts.append({"case": "direct-local-ws-negative-" + next(iter(extra)), "status": exc.status})
            else:
                await socket.close()
                raise AssertionError("Unqualified WS ingress accepted")
        await post("transport/context", {"contract_version": 1, "identity": identity}, 401, authenticated=False)
        receipts.append({"case": "local-pairing-still-required", "status": 401})
        for extra, expected in (({"Origin": "http://foreign.invalid"}, 403), ({"Forwarded": "for=192.168.1.20;proto=http"}, 426), ({"Via": "unqualified-proxy"}, 426)):
            await post("transport/context", {"contract_version": 1, "identity": identity}, expected, extra=extra)
            receipts.append({"case": "direct-local-negative-" + next(iter(extra)), "status": expected})
        operation = {
            "identity": identity, "contract_version": 1, "operation_id": new_id(),
            "operation_epoch": context["operation_epoch"], "operation": "command",
            "payload": {"command": "status"},
        }
        accepted = await post("transport/operation", operation)
        assert accepted["operation_receipt"]["phase"] == "confirmed", accepted
        receipts.append({"case": "direct-local-http-operation", "body": accepted})
        provider_count = len(provider_calls)
        status_body = {key: operation[key] for key in ("contract_version", "operation_id", "operation_epoch")}
        for reconnect in range(2):
            async with client.ws_connect(plain + "/api/djconnect/v1/actions/paired") as ws:
                assert (await ws.receive_json())["type"] == "auth_required"
                # The existing ordinary paired device token remains RAM-only.
                token = headers["Authorization"].removeprefix("Bearer ")
                await ws.send_json({"type": "auth", "protocol_version": 1, "audience": "paired_owner_actions", **identity, "device_token": token})
                ready = await ws.receive_json()
                assert ready["type"] == "auth_ok", ready
                assert not ready["requires_authenticated_tls"]
                assert ready["transport_security"]["mode"] == "qualified_direct_http"
                assert ready["ha_install_id"] == tls_context["ha_install_id"]
                assert ready["operation_epoch"] == tls_context["operation_epoch"]
                await ws.send_json({"id": 1, "type": "djconnect/read", "operation": "session/active", "payload": {}})
                active = await ws.receive_json()
                assert active["success"] and active["result"]["session"]["session_id"] == session_id, active
                await ws.send_json({"id": 2, "type": "djconnect/operation/status", **status_body})
                status = await ws.receive_json()
                assert status["result"]["operation_receipt"]["phase"] == "confirmed", status
                await ws.send_json({"id": 3, "type": "djconnect/operation/execute", **{key: value for key, value in operation.items() if key != "identity"}})
                duplicate = await ws.receive_json()
                assert duplicate["result"]["operation_receipt"]["phase"] == "confirmed", duplicate
                assert not duplicate["result"]["result_available"]
                assert len(provider_calls) == provider_count
                receipts.append({"case": "direct-local-ws-reconnect-status", "reconnect": reconnect, "context": ready, "read": active, "status": status})
            await asyncio.sleep(0.05)
        status = await post("transport/operation/status", {**status_body, "identity": identity})
        assert status["operation_receipt"]["phase"] == "confirmed"
        assert len(provider_calls) == provider_count
        receipts.append({"case": "direct-local-original-id-http-status", "body": status})
        recovery = await post("session/broadcast/recovery", {"contract_version": 1, "identity": identity, "session_id": session_id, "recovery_cursor": "0" * 32})
        assert recovery["session_id"] == session_id and recovery["recovery"] == "snapshot_required"
        receipts.append({"case": "direct-local-original-broadcast-recovery", "session_id": session_id})
        # Source I/O is the only held boundary; actual authority/journal/effect
        # revalidation must stop the accepted action after qualification withdrawal.
        async with client.ws_connect(plain + "/api/djconnect/v1/actions/paired") as revoked:
            await revoked.receive_json()
            await revoked.send_json({"type": "auth", "protocol_version": 1, "audience": "paired_owner_actions", **identity, "device_token": headers["Authorization"].removeprefix("Bearer ")})
            assert (await revoked.receive_json())["type"] == "auth_ok"
            state["token_gate"], state["token_entered"] = asyncio.Event(), asyncio.Event()
            before_calls, before_mutations = len(provider_calls), state["mutations"]
            await revoked.send_json({"id": 1, "type": "djconnect/operation/execute", "contract_version": 1, "operation_epoch": context["operation_epoch"], "operation_id": new_id(), "operation": "command", "payload": {"command": "next"}})
            await asyncio.wait_for(state["token_entered"].wait(), 5)
            qualification_path.unlink()
            state["token_gate"].set()
            denial = await asyncio.wait_for(revoked.receive_json(), 3)
            assert denial.get("type") == "auth_invalid" and denial.get("code") == "transport_security_required", denial
            await asyncio.sleep(0.05)
            assert state["mutations"] == before_mutations and len(provider_calls) == before_calls
            receipts.append({"case": "qualification-withdrawal-closes-ws-and-fences-accepted-inflight-effect", "provider_mutation_delta": 0, "body": denial})
            state["token_gate"] = state["token_entered"] = None
        await post("transport/context", {"contract_version": 1, "identity": identity}, 426)

    finally:
        if qualification_path.exists():
            qualification_path.unlink()
        await client.close()
        hass.config.internal_url = previous
