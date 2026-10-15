"""Exercise direct-local adapters on the real owned HA/pairing/journal lab."""

import asyncio


async def probe(hass, client, plain, identity, headers, tls_context, session_id, new_id, receipts):
    previous = hass.config.internal_url
    hass.config.internal_url = plain

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
        context = await post("transport/context", {"contract_version": 1, "identity": identity})
        assert not context["requires_authenticated_tls"]
        assert context["transport_security"]["mode"] == "qualified_direct_http"
        assert context["ha_install_id"] == tls_context["ha_install_id"]
        assert context["operation_epoch"] == tls_context["operation_epoch"]
        receipts.append({"case": "real-direct-loopback-context", "body": context})
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
                receipts.append({"case": "direct-local-ws-reconnect-status", "reconnect": reconnect, "context": ready, "read": active, "status": status})
            await asyncio.sleep(0.05)
        status = await post("transport/operation/status", {**status_body, "identity": identity})
        assert status["operation_receipt"]["phase"] == "confirmed"
        receipts.append({"case": "direct-local-original-id-http-status", "body": status})
        recovery = await post("session/broadcast/recovery", {"contract_version": 1, "identity": identity, "session_id": session_id, "recovery_cursor": "0" * 32})
        assert recovery["session_id"] == session_id and recovery["recovery"] == "snapshot_required"
        receipts.append({"case": "direct-local-original-broadcast-recovery", "session_id": session_id})
    finally:
        hass.config.internal_url = previous
