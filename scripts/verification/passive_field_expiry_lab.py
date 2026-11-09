"""Read-only comparison over a genuine original disposable grant and real expiry."""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime


async def run(**kw):
    from custom_components.djconnect.playback_observation import playback_observation_manager
    from custom_components.djconnect.passive_session import BASE

    hass, manager, sid = (kw["hass"], kw["manager"], kw["sid"])
    client = kw["client"]
    identity = kw["second_identity"]
    headers = kw["second_headers"]
    await playback_observation_manager(hass).async_stop("profile-a", sid)
    await manager.async_update_playback_projection(
        owner_profile_id="profile-a", session_id=sid, state="idle"
    )
    base = {
        **identity,
        "contract_version": 1,
        "projection_version": 3,
        "session_id": sid,
        "surface": "widget",
    }

    async def request(path, payload):
        response = await client.post(BASE + path, json=payload, headers=headers)
        body = await response.json()
        assert response.status == 200 and body["success"], (response.status, body)
        return body

    a = await request(
        "/authorize", {**base, "enabled": True, "os_snapshot_cache": True, "locked_display": False}
    )
    read = {**base, "grant_id": a["grant_id"]}
    before = await request("/read", read)
    p = before["passive_session"]
    c = p.get("contribution")
    assert c
    delay = datetime.fromisoformat(c["expires_at"]).timestamp() - time.time() + 0.05
    assert 0 < delay < 45 and datetime.fromisoformat(p["expires_at"]) > datetime.fromisoformat(
        c["expires_at"]
    )
    await asyncio.sleep(delay)
    after = await request("/read", read)
    q = after["passive_session"]
    report = {
        "same_original_grant": before["grant_id"] == after["grant_id"],
        "same_binding": p["binding_id"] == q["binding_id"],
        "same_generation": p["generation"] == q["generation"],
        "same_delivery_sequence": p["delivery_sequence"] == q["delivery_sequence"],
        "waited_real_seconds": delay,
        "no_new_backend_observation": True,
        "changed_fields": [k for k in p if p[k] != q.get(k)],
        "root_still_unexpired": datetime.fromisoformat(q["expires_at"]).timestamp() > time.time(),
        "contribution_before": bool(c),
        "contribution_after": bool(q.get("contribution")),
        "before": before,
        "after": after,
        "real_provider_calls": 0,
        "installed_mutations": 0,
        "original_live_wire_reconstructed": False,
        "native_acceptance": "NOT_RUN",
    }
    assert report["same_original_grant"] and report["same_binding"] and report["same_generation"]
    assert report["same_delivery_sequence"] and report["root_still_unexpired"]
    assert report["contribution_before"] and (not report["contribution_after"])
    assert (
        p["revision"] == q["revision"]
        and p["observed_at"] == q["observed_at"]
        and (p["expires_at"] == q["expires_at"])
    )
    for _ in range(2):
        again = (await request("/read", read))["passive_session"]
        assert {k: v for k, v in again.items() if k != "as_of"} == {
            k: v for k, v in q.items() if k != "as_of"
        }
    report["cases"] = {
        "natural_field_expiry_same_frame": "PASS",
        "original_deadlines_preserved": "PASS",
        "repeated_read_no_renewal": "PASS",
    }
    report["source_pins"] = kw["source_hashes"]
    target = Path(kw["output"]) / "field-expiry-comparison.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    target.chmod(384)
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "same_original_grant",
                    "same_delivery_sequence",
                    "changed_fields",
                    "root_still_unexpired",
                    "contribution_before",
                    "contribution_after",
                    "waited_real_seconds",
                ]
            }
        ),
        flush=True,
    )
