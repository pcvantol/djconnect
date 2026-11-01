"""Actual isolated HA paired/Profile/Session/SQL negative child qualification.

Reuses the original Direct rich HTTP/asset lab. The local role-request hash is
explicit synthetic journal DATA: no resolver, issuer, operator, native proof,
clock-admission, provider or model action is exercised or qualified here.
"""
import asyncio
import base64
import uuid
from unittest.mock import patch

import verify_direct_rich_http as direct
from verify_source_origin_http import SourceOriginLab, main

original_qualify = direct.qualify


async def qualify(self, client, identity, headers):
    from custom_components.djconnect.direct_rich_runtime import KEY
    from custom_components.djconnect.direct_rich_wire import RichError, digest
    from custom_components.djconnect.host_wake_proxy_attempt import HostWakeAttempt

    paired = {**headers, "X-DJConnect-Client-Type": "ios"}
    original_end, observed = self.manager.async_end, {}

    async def end_with_negative_child(*args, **kwargs):
        service = self.hass.data["djconnect"].get(KEY)
        parents = [p for p in service.purposes.values() if p.issued and not p.closed] if service else []
        if observed or not parents:
            return await original_end(*args, **kwargs)
        assert len(parents) == 1
        parent = parents[0]
        session_id = parent.context.session_id
        assert kwargs.get("session_id") == session_id and kwargs.get("owner_profile_id") == "profile-a"
        prepare = {"contract_version": 1, "device_id": identity["device_id"], "client_type": "ios",
            "session_id": session_id, "surface": "widget", "purpose_id": parent.original.purpose_id,
            "operation_id": str(uuid.uuid4()), "target": {"host_bundle_id": "fixture.synthetic.host",
                "installation_id": "synthetic-native-installation"}, "platform": "ios",
            "apns_environment": "sandbox", "native_key_id_b64": base64.b64encode(bytes(range(32))).decode(),
            "native_token_sha256": "a" * 64}
        common = {k: prepare[k] for k in ("contract_version", "device_id", "client_type", "session_id",
            "surface", "purpose_id", "operation_id")}
        ready, holder = asyncio.Event(), []

        async def original_prepare():
            attempt = HostWakeAttempt(self.hass, paired)
            try:
                attempt.bind_parent("prepare", prepare)
                child = service.host_wake_children.capture(attempt, prepare)
                await child.reserve(role_request_hash=digest(["SYNTHETIC-JOURNAL-DATA-NOT-RECEIVED-ROLE"]),
                    attempt_id=str(uuid.uuid4()))
                holder.append(child)
                ready.set()
                await asyncio.Event().wait()
            finally:
                attempt.close()

        worker, waiter = asyncio.create_task(original_prepare()), asyncio.create_task(ready.wait())
        try:
            await asyncio.wait((worker, waiter), return_when=asyncio.FIRST_COMPLETED)
            if worker.done():
                await worker
            await waiter
            child = holder[0]

            async def management(operation, payload):
                attempt = HostWakeAttempt(self.hass, paired)
                try:
                    return await service.host_wake_children.capture_management(attempt, payload,
                        operation=operation).run()
                finally:
                    attempt.close()

            before = await management("status", common)
            assert before.phase == "initial_reserved" and before.consumed_attempts == 1
            for changed in ({"session_id": "different-original-session"},
                    {"operation_id": parent.original.operation_id}, {"surface": "live_activity"}):
                try:
                    await management("withdraw", common | changed)
                except RichError as error:
                    assert error.status == 403
                else:
                    raise AssertionError("Mismatched management accepted")
                assert not child.closed and not worker.cancelling()
            result = await original_end(*args, **kwargs)
            assert parent.closed and child.closed
            await asyncio.gather(worker, return_exceptions=True)
            after = await management("withdraw", common)
            assert after.phase == "withdrawn" and after.consumed_attempts == 1
            assert child.context is None and child.registry is None
            observed.update(before=before.phase, after=after.phase, attempts=after.consumed_attempts)
            return result
        finally:
            worker.cancel()
            waiter.cancel()
            await asyncio.gather(worker, waiter, return_exceptions=True)

    with patch.object(self.manager, "async_end", new=end_with_negative_child):
        result = await original_qualify(self, client, identity, headers)
    assert observed == {"before": "initial_reserved", "after": "withdrawn", "attempts": 1}
    assert result["schema_version"] == 21
    result["cases"].extend([
        "actual_HA_original_paired_committed_Profile_child_SQL21_once_metadata",
        "actual_HA_wrong_Session_native_operation_and_surface_denied_before_child_fence",
        "actual_HA_Session_end_child_retirement_preserves_original_negative_metadata_only",
    ])
    result["host_wake_management"] = {**observed, "remote_API_or_native_ack": False,
        "role_request_hash": "EXPLICIT_SYNTHETIC_JOURNAL_DATA_NOT_RECEIVED_AUTHORITY",
        "actual_issuer_operator_enrollment_clock_or_provider_permission": False}
    return result


SourceOriginLab.qualify = qualify

if __name__ == "__main__":
    asyncio.run(main())
