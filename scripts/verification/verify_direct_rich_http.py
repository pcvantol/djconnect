"""Actual isolated HA / ordinary pairing / original Direct rich HTTP acceptance.

Reuses the existing owned HA/Spotify-source fixture bootstrap only. No actual
provider, native, signing, operator, model, deployment or installation effects.
"""
import asyncio
from copy import deepcopy
import time
import uuid

import verify_source_origin_http as bootstrap
from verify_source_origin_http import SourceOriginLab, main

_ordinary_setup = bootstrap.async_setup
_ordinary_provider = SourceOriginLab.provider


async def provider(self, backend, method, path, **kwargs):
    """Declared external Spotify response fixture; real Core admission stays."""
    item = self.raw.get("item", {})
    if method == "GET" and path == "/tracks/" + item.get("id", ""):
        result = deepcopy(item)
        result["external_urls"] = {"spotify": "https://open.spotify.com/track/" + item["id"]}
        album = result["album"]
        album["images"] = [{"url": "https://i.scdn.co/image/" + "a" * 40, "width": 1, "height": 1}]
        return result
    return await _ordinary_provider(self, backend, method, path, **kwargs)


async def setup(hass, config):
    """Same installation-metadata stage as real async_setup_entry, before pair.

    The inherited fixture creates runtime slots without running entry setup.
    It must use the genuine nonsecret installation bootstrap, not invent an ACK
    or learn/repair pairing inside the Direct rich read path.
    """
    from custom_components.djconnect.central_api import ensure_ha_install_id
    result = await _ordinary_setup(hass, config)
    for runtime in (hass.data["djconnect"]["owner-entry"], hass.data["djconnect"]["second-owner"]):
        ensure_ha_install_id(runtime, hass)
    return result


async def qualify(self, client, identity, headers):
    from custom_components.djconnect.direct_rich_runtime import KEY, setup_service
    from custom_components.djconnect.direct_rich_wire import BASE

    self.owner = {"client": client, "identity": identity, "headers": headers}
    await self.start()
    await self.step(1)
    active = self.manager.current_active("profile-a")
    # Keep the genuine observer/source lifetime alive through qualification.
    # Stopping it deliberately cancels owning content/Profile work and is a
    # negative lifecycle boundary, not a way to freeze a positive read source.
    await self.hass.async_block_till_done()
    setup_service(self.hass)  # Same owning setup hook, never initialized by a read.
    paired = {**headers, "X-DJConnect-Client-Type": "ios"}
    # Preparation is an explicit ordinary owning action, before pure reads.
    history_response = await client.get("/api/djconnect/v1/session/history/" + active.session_id,
        params=identity, headers=paired)
    history = await history_response.json()
    assert history_response.status == 200
    playback_entry = next(item for item in history["entries"] if item["kind"] == "playback_observed")
    prepared = await client.post("/api/djconnect/v1/session/media/prepare", headers=paired,
        json={**identity, "contract_version": 1, "session_id": active.session_id,
            "targets": [{"entry_id": playback_entry["entry_id"]}]})
    assert prepared.status == 200
    await self.hass.async_block_till_done()
    request = {"contract_version": 1, "operation_id": str(uuid.uuid4()),
        "device_id": identity["device_id"], "client_type": "ios", "session_id": active.session_id,
        "surface": "widget", "enabled": True, "os_snapshot_cache": True, "locked_display": False}
    # Qualify the actual pure owner capture independently of HTTP error mapping.
    # This exposes only a synthetic lab traceback on failure, never credentials.
    from custom_components.djconnect.direct_rich_context import capture_context
    from custom_components.djconnect import profile_observation
    profile_owner = profile_observation._owner(self.hass)
    profile_manager = profile_owner.manager() if profile_owner is not None and profile_owner.manager else None
    assert profile_observation.capture_committed(self.hass) is not None, {
        "synthetic_lab_Profile_owner_exists": profile_owner is not None,
        "uncertain": profile_owner.uncertain if profile_owner else None,
        "pending": profile_owner.pending if profile_owner else None,
        "manager_exists": profile_manager is not None,
        "loaded": profile_manager._loaded if profile_manager else None,
        "same_committed_household": profile_manager._household is profile_manager._committed_household
            if profile_manager else None}
    probe = capture_context(self.hass, paired, device_id=identity["device_id"],
        client_type="ios", session_id=active.session_id)
    assert probe.attempt().current()
    probe.retire()

    async def post(operation, body, credential_headers, expected=200):
        response = await client.post(BASE + "/" + operation, json=body, headers=credential_headers)
        data = await response.json()
        assert response.status == expected, (operation, response.status, data.get("error"))
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        return data

    issued = await post("authorize", request, paired)
    assert issued["read_credential"].startswith("djcrichread_")
    assert issued["asset_credential"].startswith("djcrichasset_")
    assert issued["read_credential"] != issued["asset_credential"]
    read = {"contract_version": 1, "purpose_id": issued["purpose_id"]}
    read_headers = {"Authorization": "Bearer " + issued["read_credential"]}
    asset_headers = {"Authorization": "Bearer " + issued["asset_credential"]}
    first = await post("read", read, read_headers)
    frame = first["frame"]
    assert frame["state"] == "active" and frame["now_playing"]
    publications = len(active.broadcast.state.dj_moments)
    copies = [await post("read", read, read_headers) for _ in range(12)]
    assert all(item["frame"] == frame for item in copies)
    assert len(active.broadcast.state.dj_moments) == publications
    assert all(item["purpose_expires_at_ms"] == issued["purpose_expires_at_ms"] for item in copies)
    await post("read", read, asset_headers, 401)
    await post("read", read, paired, 400)  # Ambient paired identity is forbidden on this role.
    await post("authorize", {**request, "operation_id": str(uuid.uuid4())}, paired, 409)
    cases = ["actual_paired_Profile_SQL21_HTTP_authorize_and_independent_role_credentials",
        "twelve_reads_same_original_frame_no_publication_or_purpose_renewal",
        "ordinary_and_asset_credentials_cannot_replace_rich_read",
        "same_original_scope_new_UUID_cannot_reissue"]
    assert frame["artwork"], "Actual prepared cover must be exercised, not vacuously skipped"
    for art in frame["artwork"]:
        response = await client.post(BASE + "/asset", json={**read,
            "frame_id": frame["frame_id"], "asset_id": art["asset_id"]}, headers=asset_headers)
        body = await response.read()
        import hashlib
        assert response.status == 200 and len(body) == art["byte_length"]
        assert hashlib.sha256(body).hexdigest() == art["bytes_sha256"]
        assert response.headers["Content-Type"].split(";")[0] == art["mime_type"]
        cases.append("actual_prepared_cover_original_bytes_digest_and_asset_role")
    operation = {k: v for k, v in request.items() if k not in {"enabled", "os_snapshot_cache", "locked_display"}}
    state = await post("status", operation, paired)
    assert state["state"] == "active" and "read_credential" not in state
    purpose = self.hass.data["djconnect"][KEY].purposes[issued["purpose_id"]]
    await self.manager.async_end(owner_profile_id="profile-a", session_id=active.session_id)
    assert purpose.closed and not purpose.read_secret and not purpose.asset_secret
    state = await post("withdraw", operation, paired)
    assert state["state"] == "withdrawn"
    await post("read", read, read_headers, 401)
    cases.append("actual_Session_end_synchronous_secret_scrub_and_original_negative_history")
    return {"status": "PASS", "classification": "DIRECT_RICH_ACTUAL_ISOLATED_HA_SOURCE_ONLY",
        "cases": cases, "original_prepared_covers": len(frame["artwork"]),
        "schema_version": self.manager._persistent_sessions._persistence.readiness.schema_version,
        "original_purpose_retained": True, "read_reissues": 0, "model_calls": 0,
        "actual_operator_enrollment_native_clock_or_APNs_GO": False,
        "clock_observation_only": {"monotonic": vars(time.get_clock_info("monotonic"))}}


SourceOriginLab.qualify = qualify
SourceOriginLab.provider = provider
bootstrap.async_setup = setup

if __name__ == "__main__":
    asyncio.run(main())
