"""Actual HA seven-route/native-ACK/Broadcast/SQL composition, modeled API only.

The external role, issuer, native verification and provider replies are explicit
synthetic DATA. This qualifies no device, Apple SDK, operator, key or APNs effect.
"""
import asyncio
import base64
import hashlib
import json
from types import SimpleNamespace
import uuid
from unittest.mock import patch

from multidict import CIMultiDict

import verify_direct_rich_http as direct
from verify_source_origin_http import SourceOriginLab, main

original_qualify, original_setup = direct.qualify, direct.setup


async def setup(hass, config):
    result = await original_setup(hass, config)
    entry = hass.data["djconnect"]["owner-entry"].entry
    hass.config_entries.async_update_entry(entry, options={**entry.options,
        "djconnect_install_token": "djci_" + "A" * 43,
        "api_base_url": "https://synthetic.invalid"})
    return result


async def qualify(self, client, identity, headers):
    from custom_components.djconnect import host_wake_api as transport
    from custom_components.djconnect import host_wake_api_wire as api
    from custom_components.djconnect import host_wake_target_wire as target
    from custom_components.djconnect import host_wake_withdrawal as negative
    from custom_components.djconnect.direct_rich_runtime import KEY
    from custom_components.djconnect.direct_rich_wire import canonical, digest
    from custom_components.djconnect.host_wake_proxy_wire import BASE

    paired = {**headers, "X-DJConnect-Client-Type": "ios"}
    original_end, observed, calls = self.manager.async_end, {}, []
    child = role = original = challenge = None

    class Reply:
        def __init__(self, value, correlation=None):
            self.status, self.body, self.content = 200, canonical(value), self
            self.headers = CIMultiDict({"Content-Type": "application/json"})
            if correlation is not None:
                self.headers[target.CORRELATION_HEADER] = correlation

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            self.body = b""

        async def iter_chunked(self, size):
            for start in range(0, len(self.body), size):
                yield self.body[start:start + size]

    class Session:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        def post(self, url, **kwargs):
            nonlocal role, original, challenge
            route = url.removeprefix("https://synthetic.invalid" + api.PREFIX)
            sent = json.loads(kwargs["data"])
            calls.append(route)  # No token, credential or proof retention.
            if route == "authorization/resolve":
                issued = child.reservation.created_ms
                role = {"version": api.VERSION, "resolution": "existing",
                    "authorization_id": "synthetic-role-DATA-not-authority",
                    "request_sha256": api.request_hash(route, sent), "scope_sha256": digest(sent["scope"]),
                    "original_authorization_issued_at_ms": issued - 1,
                    "original_authorization_expires_at_ms": child.reservation.parent.expires_ms,
                    "max_original_purpose_ms": 3600000, "max_operations": 16, "max_reserved_sends": 2,
                    "native_proof_kind": "app_attest_assertion",
                    "registration_mode": "single_original_no_rotation",
                    "selected_ha_origin_sha256": "b" * 64, "identity_policy_sha256": "c" * 64,
                    "deployment_policy_sha256": "d" * 64}
                return Reply(role)
            if route == "issuer/issue":
                original = sent["original"]
            if route.startswith("native/") or route == "issuer/issue":
                value = {"version": api.VERSION, **{key: sent[key] for key in api.SCOPE_HEADERS},
                    "request_sha256": api.request_hash(route, sent),
                    "generation": original["generation"], "revision": original["revision"],
                    **{key: original[key] for key in api.TIMES},
                    "native_proof_kind": role["native_proof_kind"]}
                if route == "issuer/issue":
                    value.update(state="issued", purpose_id="synthetic-private-purpose",
                        credential_state="available", credential="djchw_" + "A" * 43,
                        expires_at_ms=original["original_wake_expires_at_ms"],
                        registration_mode="single_original_no_rotation", original=original)
                elif route == "native/challenge":
                    at = original["original_wake_issued_at_ms"] + 1
                    challenge = {"challenge_id": sent["challenge_id"], "nonce_b64url": "A" * 43,
                        "captured_at_ms": at, "expires_at_ms": min(at + 30000,
                            original["original_wake_expires_at_ms"])}
                    transcript = canonical({"original": original, "challenge": challenge})
                    value.update(state="pending", original=original, challenge=challenge,
                        canonical_transcript_utf8=transcript.decode(),
                        client_data_sha256=hashlib.sha256(api.DOMAIN + transcript).hexdigest())
                else:
                    value.update(state="native_verified", challenge_id=sent["challenge_id"],
                        original_sha256=digest(original), native_verified_at_ms=challenge["captured_at_ms"])
                return Reply(value)
            assert route in {"register", "status", "wake"}
            if route == "wake":
                assert child.metadata.phase == "registered" and child.metadata.consumed_attempts >= 7
            value = {"version": target.VERSION, "purpose_id": sent["purpose_id"],
                "operation_id": sent["operation_id"], "state": "registered",
                "operation_state": "provider_accepted" if route == "wake" else "registered",
                "generation": original["generation"], "revision": original["revision"],
                "expires_at_ms": original["original_wake_expires_at_ms"],
                "transport_expires_at_ms": original["original_wake_expires_at_ms"] if route == "wake" else None,
                "provider_status": 200 if route == "wake" else None}
            return Reply(value, target.request_hash(route, sent))

    async def post(operation, body, expected=200):
        response = await client.post(BASE + operation, json=body, headers=paired)
        data = await response.json()
        assert response.status == expected, (operation, response.status, data.get("error"))
        assert response.headers["Cache-Control"] == "no-store"
        return data

    async def end_with_registered_child(*args, **kwargs):
        nonlocal child
        service = self.hass.data["djconnect"][KEY]
        parents = [parent for parent in service.purposes.values() if parent.issued and not parent.closed]
        if observed or not parents:
            return await original_end(*args, **kwargs)
        assert len(parents) == 1
        parent = parents[0]
        session_id = parent.context.session_id
        token = b"SYNTHETIC-APNS-TOKEN-DATA-ONLY-32!"
        prepare = {"contract_version": 1, "device_id": identity["device_id"], "client_type": "ios",
            "session_id": session_id, "surface": "widget", "purpose_id": parent.original.purpose_id,
            "operation_id": str(uuid.uuid4()), "target": {"host_bundle_id": "fixture.synthetic.host",
                "installation_id": "synthetic-native-installation"}, "platform": "ios",
            "apns_environment": "sandbox", "native_key_id_b64": base64.b64encode(bytes(range(32))).decode(),
            "native_token_sha256": hashlib.sha256(token).hexdigest()}
        common = {key: prepare[key] for key in ("contract_version", "device_id", "client_type", "session_id",
            "surface", "purpose_id", "operation_id")}
        # Observe the actual capture before resolver IO; do not inject a child.
        capture = service.host_wake_children.capture
        def captured(*values, **named):
            nonlocal child
            child = capture(*values, **named)
            return child
        synthetic = SimpleNamespace(ClientSession=Session, DummyCookieJar=object,
            ClientTimeout=lambda **values: SimpleNamespace(**values))
        def consume(port):
            port.used = True  # Explicit modeled negative external port only.
        with patch.object(transport, "aiohttp", synthetic), patch.object(
                negative._IssuerWithdrawal, "schedule", autospec=True, side_effect=consume), patch.object(
                    service.host_wake_children, "capture", side_effect=captured):
            prepared = await post("prepare", prepare)
            assert prepared["state"] == "prepared" and child.initial_attempt is None
            challenged = await post("native/challenge", common)
            challenge_id = challenged["challenge"]["challenge_id"]
            completed = await post("native/complete", common | {"challenge_id": challenge_id,
                "native_proof": {"kind": "app_attest_assertion",
                    "bytes_b64": base64.b64encode(b"MODELED-API-PROOF-NOT-NATIVE").decode()}})
            assert completed["state"] == "native_verified"
            status = await post("native/status", common | {"challenge_id": challenge_id})
            assert status["state"] == "native_verified"
            registered = await post("register", common | {"challenge_id": challenge_id,
                "native_token_b64": base64.b64encode(token).decode()})
            assert registered["state"] == "registered" and child._watch is not None
            watch = child._watch
            assert (await post("status", common))["state"] == "registered"
            await self.manager.async_update_playback_projection(owner_profile_id="profile-a",
                session_id=session_id, state="paused")
            task = watch.task
            assert task is not None
            await task
            await asyncio.sleep(0)
            assert not child.closed and calls.count("wake") == 1
            persistence = self.manager._persistent_sessions._persistence
            count = await persistence.async_in_transaction(lambda tx: tx.fetchone(
                "SELECT COUNT(*) FROM djconnect_host_wake_attempts WHERE kind='target_wake'"))
            assert count == (1,) and child.context.pair.current()
            retired = await post("withdraw", common)
            # No genuine negative API ACK is modeled here: local withdrawal
            # must not be advertised as remotely acknowledged withdrawal.
            assert retired["state"] == "unknown" and child.closed and watch.closed
            assert child.metadata.phase == "withdrawn"
            assert watch.child is None and watch.broadcast is None and not service.host_wake_children.tasks
            observed.update(routes=sorted(set(calls)), wakes=1, durable_wakes=count[0],
                actual_http_operations=7, external_API_native_provider="MODELED_ONLY")
        return await original_end(*args, **kwargs)

    with patch.object(self.manager, "async_end", new=end_with_registered_child):
        result = await original_qualify(self, client, identity, headers)
    assert observed["actual_http_operations"] == 7
    result["cases"].extend(["actual_HA_seven_original_HTTP_routes_and_modeled_native_ACK_chain",
        "actual_HA_original_Broadcast_change_durable_SQL_once_before_content_free_wake",
        "actual_HA_registered_original_pair_retained_then_synchronous_withdrawal_scrub"])
    result["host_wake_runtime"] = observed
    return result


direct.bootstrap.async_setup = setup
SourceOriginLab.qualify = qualify

if __name__ == "__main__":
    asyncio.run(main())
