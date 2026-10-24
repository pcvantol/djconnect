"""Disposable actual HA routes/SQLite/lifecycle; explicit synthetic issuer/API boundary.

Original-clock v3 producer qualification; historical v2 harness remains unchanged.
No operator enrolment, key custody, remote request, APNs or native proof.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
ROOT = Path(os.environ.get("DJC_SOURCE_ROOT",Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT),str(ROOT/"scripts/verification")]

async def qualify(hass,manager,history,request,client):
    from custom_components.djconnect import api_handlers
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    from custom_components.djconnect.surface_push_service import start_surface_service,close_surface_service
    from custom_components.djconnect.surface_push_purpose import SurfacePurposeCredential
    from custom_components.djconnect.surface_push_wire import canonical
    from custom_components.djconnect.hybrid_service import PairedAuthority
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect import surface_push_relay
    owner = "profile-a"
    old = manager.current_active(owner)
    if old:
        await manager.async_end(owner_profile_id=owner,session_id=old.session_id)
    # Build an actual loaded synthetic provider connection, not a patched
    # authority check. The reused history harness starts in manual mode.
    from dataclasses import replace
    from custom_components.djconnect import DJConnectRuntime
    from custom_components.djconnect.profile_context import profile_storage
    storage = profile_storage(hass)
    profile = storage.household.profiles[owner]
    await storage.async_update_profile(owner,preferences=replace(profile.preferences,
        default_backend_id="source-spotify",default_music_account_id="source-account"))
    source = hass.config_entries.async_get_entry("source-entry")
    hass.config_entries.async_update_entry(source,data={**source.data,"music_backend":"source-spotify",
        "profile_id":owner,"spotify_client_id":"synthetic-source-client"})
    hass.data["djconnect"]["source-entry"] = DJConnectRuntime(source)
    paired = hass.config_entries.async_get_entry("owner-entry")
    hass.config_entries.async_update_entry(paired,data={**paired.data,
        "profile_backend_entry_id":"source-entry","music_backend":"source-spotify",
        "music_account_id":"source-account"})
    async def no_external(*args,**kwargs):
        pass
    with patch.object(api_handlers,"_async_generate_initial_session_moment",no_external), patch.object(
            PlaybackObservationManager,"async_start_spotify",no_external):
        body,status = await request("POST","/api/djconnect/v1/session/start",{"mood":"groove","locale":"nl"})
    assert status==201,body
    sid = manager.current_active(owner).session_id
    start_surface_service(hass)
    service = hass.data["djconnect"]["surface_push_service"]
    base = "/api/djconnect/v1/push/surface/"
    secrets = inspect.getclosurevars(request).nonlocals
    headers,identity = secrets["headers"],secrets["identity"]
    evidence = []
    async def raw(method,kind,expected,**kwargs):
        response = await client.request(method,base+kind,**kwargs)
        value = await response.json()
        assert response.status==expected,(method,kind,response.status,value)
        for name,wanted in (("Cache-Control","no-store"),("Referrer-Policy","no-referrer")):
            assert response.headers.get(name)==wanted
        evidence.append({"method":method,"kind":kind,"status":response.status,"no_store":True,
            "request_json":deepcopy(kwargs.get("json")),"response_body":deepcopy(value),
            "authentication_kind":("synthetic_background_read" if
                str((kwargs.get("headers") or {}).get("Authorization","")).startswith("Bearer djcsurface_")
                else "synthetic_paired" if kwargs.get("headers")==headers else "none"),
            "fixture_boundary":"disposable synthetic identities/credentials; not operator/native authority"})
        return value
    calls = []
    async def relay(hass_arg,runtime,action,payload,admission):
        assert hass_arg is hass
        admission.validate()
        rows = await persistence_service(hass).async_in_transaction(lambda tx:tx.fetchone(
            "SELECT body FROM djconnect_surface_journal WHERE singleton=1"))
        assert any(r["phase"]=="sent_unknown" for r in json.loads(rows[0])["records"].values())
        calls.append(action)
        return {**{k:payload[k] for k in ("registration_id","generation","revision","operation_id")},
            "success":True,"contract_version":1,"replayed":False,
            "expires_at_ms":payload["expires_at_ms"] if action=="register" else expiry if action=="event" else 0,
            "state":"registered" if action in {"register","event"} else "revoked",
            "operation_state":"registered" if action=="register" else "provider_accepted" if action=="event" else "revoked",
            "current_revision":payload["revision"],"provider_status":200 if action=="event" else None}
    try:
        for method in ("GET","PUT","PATCH","DELETE","OPTIONS","HEAD"):
            if method=="HEAD":
                response = await client.request(method,base+"context")
                assert response.status==405 and response.headers.get("Cache-Control")=="no-store"
                await response.read()
                evidence.append({"method":method,"kind":"context","status":405,"no_store":True})
            else:
                await raw(method,"context",405)
        for data,status in ((b'{"contract_version":1,"contract_version":1}',400),
                (b'{"x":NaN}',400),(b'x'*16385,413)):
            await raw("POST","context",status,data=data,headers={"Content-Type":"application/json"})
        context = {**identity,"contract_version":1,"session_id":sid}
        await raw("POST","context",409,json=context,headers=headers)
        from uuid import UUID
        context_now = int(time.time()*1000)
        context_operation = str(UUID(int=(context_now<<80)|(7<<76)|(2<<62)|1))
        v3context = {**context,"contract_version":3,"operation_id":context_operation}
        await raw("POST","context",409,json={**v3context,"contract_version":2},headers=headers)
        await raw("POST","context",401,json=v3context)
        await raw("POST","context",503,json=v3context,headers=headers)
        assert not service._purposes and not calls
        authority = await PairedAuthority.resolve(hass,identity,headers)
        authority.validate_now()
        from custom_components.djconnect.forecast_imagery import artist_authority
        assert artist_authority(hass,authority.runtime,owner_profile_id=owner,
            expected_source=manager._history_source_contexts.get(sid,{}))(), "synthetic source must really qualify"
        now = int(time.time()*1000)
        expiry = now+600000
        target = {"instance_id":"synthetic-widget","app_bundle_id":"dev.djconnect.ios",
            "extension_bundle_id":"dev.djconnect.ios.widget","widget_kind":"DJConnectSessionWidget"}
        policy = {"token_role":"widget","platform":"ios","apns_environment":"sandbox",
            "target":{k:v for k,v in target.items() if k!="instance_id"},"activity_profile":None,
            "external_content_allowed":False,"original_grant_expires_at_ms":expiry,
            "max_operations":100,"max_events":20,"max_challenges":4}
        purpose = SurfacePurposeCredential("djcs_"+"A"*43,"https://api.djconnect.dev",
            "synthetic-capability","synthetic-delegation","d"*64,authority.binding,authority.device,
            authority.owner,"e"*64,"f"*64,canonical(policy),now,time.monotonic(),lambda:True)
        # Declared synthetic issuer boundary. The production default map stays empty.
        service._purposes[(authority.owner,authority.device,authority.binding,sid)] = purpose
        # The original absent root is retained: later adoption cannot attach it.
        await raw("POST","context",409,json=v3context,headers=headers)
        context_now = int(time.time()*1000)
        context_operation = str(UUID(int=(context_now<<80)|(7<<76)|(2<<62)|3))
        v3context = {**v3context,"operation_id":context_operation}
        captured = await raw("POST","context",200,json=v3context,headers=headers)
        recovered = await raw("POST","context",200,json=v3context,headers=headers)
        assert recovered == captured and captured["expires_at_ms"]==expiry
        assert captured["context_expires_at_ms"] < expiry
        assert set(captured) == {"success","contract_version","available","context_handle",
            "operation_id","purpose_ref","expires_at_ms","context_expires_at_ms",
            "purpose_remaining_at_original_start_ms","context_remaining_at_original_start_ms","cache_policy"}
        assert captured["contract_version"] == 3
        assert 0 < captured["context_remaining_at_original_start_ms"] <= 30000
        assert captured["context_remaining_at_original_start_ms"] <= captured["purpose_remaining_at_original_start_ms"] <= 28800000
        original_start = service.contexts._starts[context_operation]
        assert original_start.runtime() is authority.runtime and isinstance(authority.runtime,DJConnectRuntime)
        assert original_start.mono_clock is purpose.monotonic is time.monotonic

        async def context_for(body):
            reply = await raw("POST","context",200,
                json={**context,"contract_version":3,"operation_id":body["operation_id"]},headers=headers)
            assert reply["purpose_ref"]==captured["purpose_ref"] and reply["expires_at_ms"]==expiry
            return reply["context_handle"]
        operation = context_operation
        payload = {**context,"contract_version":3,"context_handle":captured["context_handle"],
            "operation_id":operation,"platform":"ios","os_version":"26.0",
            "token_role":"widget","target":target,"apns_token":"a"*64,
            "apns_environment":"sandbox","expected_registration":None,
            "consent":{"background_read":True,"os_snapshot_cache":True,"locked_display":False,
                "external_push_content":False,"allow_remote_start":False}}
        legacy = {k:v for k,v in payload.items() if k!="context_handle"}
        legacy["contract_version"] = 1
        await raw("POST","register",409,json=legacy,headers=headers)
        await raw("POST","register",409,json={**payload,"contract_version":2},headers=headers)
        assert not calls
        with patch.object(surface_push_relay,"post_once",relay):
            registered = await raw("POST","register",200,json=payload,headers=headers)
            assert all(registered[k]==captured[k] for k in ("context_handle","purpose_ref","operation_id"))
            assert registered["success"] and calls==["register"]
            replay = await raw("POST","register",200,json=payload,headers=headers)
            assert replay["replayed"] and calls==["register"]
        grant = registered["background_read"]
        read = {"contract_version":1,"registration_id":grant["registration_id"]}
        await raw("POST","read",401,json=read,headers=headers)
        bg_headers = {"Authorization":"Bearer "+grant["credential"]}
        result = await raw("POST","read",200,json=read,headers=bg_headers)
        assert result["registration"]["expires_at_ms"]==expiry
        assert result["passive_session"]["artwork"]==[]
        with patch.object(surface_push_relay,"post_once",relay):
            admission = await service.admission(payload,headers)
            coordinate = {k:registered["registration"][k] for k in ("registration_id","generation","revision")}
            event_id = str(UUID(int=(now<<80)|(7<<76)|(2<<62)|2))
            signal = await service.run(service.registry.signal_widget(admission,coordinate,operation_id=event_id))
            again = await service.run(service.registry.signal_widget(admission,coordinate,operation_id=event_id))
            assert signal["provider_accepted"] and again["replayed"] and calls==["register","event"]
            # Original real Broadcast subscription: progress is signal-free;
            # an accepted Runtime Mood change queues one bounded widget signal.
            from custom_components.djconnect.session_runtime import BroadcastEventType
            broadcast = manager.current_active(owner).broadcast
            assert len(service._signals)==1
            for _ in range(100):
                broadcast._publish(BroadcastEventType.PLAYBACK_PROGRESS,{})
            await asyncio.sleep(0)
            assert calls==["register","event"]
            await manager.async_update_mood(owner_profile_id=owner,session_id=sid,selected_mood="energy")
            for _ in range(5):
                tasks = tuple(service._tasks)
                if not tasks:
                    break
                await asyncio.gather(*tasks)
                await asyncio.sleep(0)
            assert calls==["register","event","event"],calls
            assert not service._tasks
            previous = len(calls)
            recording = None
            for playback_state in ("playing","paused","playing"):
                await manager.async_update_playback_projection(owner_profile_id=owner,session_id=sid,
                    state=playback_state,media_identity="spotify:track:"+"A"*22,
                    title="Synthetic recording",artist="Synthetic artist",album="Synthetic edition",
                    duration_ms=300000,position_ms=10000)
                for _ in range(5):
                    tasks = tuple(service._tasks)
                    if not tasks:
                        break
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(0)
                current_frame = admission.projection()
                observed = current_frame["now_playing"]
                assert observed is not None and current_frame["playback_state"]==playback_state
                identity_fields = {k:observed[k] for k in ("item_id","track","artist","album")}
                if recording is not None:
                    assert identity_fields==recording
                recording = identity_fields
                previous += 1
                assert len(calls)==previous and calls[-1]=="event",calls
            assert len(calls)==6
            # Capture actual closed HTTP replies for native consumers. Every
            # credential and identity belongs only to this disposable harness.
            old_bg_headers = bg_headers
            rotated_payload = deepcopy(payload)
            rotated_payload.update(operation_id=str(UUID(int=(now<<80)|(7<<76)|(2<<62)|20)),
                expected_registration=coordinate,apns_token="b"*64)
            rotated_payload["context_handle"] = await context_for(rotated_payload)
            rotated = await raw("POST","register",200,json=rotated_payload,headers=headers)
            assert rotated["success"] and rotated["registration"]["generation"]==coordinate["generation"]
            assert rotated["registration"]["revision"]==coordinate["revision"]+1
            assert rotated["registration"]["expires_at_ms"]==expiry
            await raw("POST","read",401,json=read,headers=old_bg_headers)
            bg_headers = {"Authorization":"Bearer "+rotated["background_read"]["credential"]}
            await raw("POST","read",200,json=read,headers=bg_headers)
            await raw("POST","status",200,json={**context,
                "registration_id":read["registration_id"]},headers=headers)
            separate = deepcopy(payload)
            separate["target"]["instance_id"]="synthetic-revoked-widget"
            separate["operation_id"]=str(UUID(int=(now<<80)|(7<<76)|(2<<62)|21))
            separate["context_handle"] = await context_for(separate)
            extra = await raw("POST","register",200,json=separate,headers=headers)
            extra_read = {"contract_version":1,"registration_id":extra["registration"]["registration_id"]}
            extra_headers = {"Authorization":"Bearer "+extra["background_read"]["credential"]}
            revoke = {**context,"operation_id":str(UUID(int=(now<<80)|(7<<76)|(2<<62)|22)),
                "expected_registration":{k:extra["registration"][k] for k in
                    ("registration_id","generation","revision")}}
            revoked = await raw("POST","revoke",200,json=revoke,headers=headers)
            assert revoked["success"] and revoked["registration"]["state"]=="revoked"
            await raw("POST","read",401,json=extra_read,headers=extra_headers)
            async def unknown_relay(*args,**kwargs):
                raise TimeoutError("synthetic lost reply")
            separate["target"]["instance_id"]="synthetic-unknown-widget"
            separate["operation_id"]=str(UUID(int=(now<<80)|(7<<76)|(2<<62)|23))
            separate["context_handle"] = await context_for(separate)
            with patch.object(surface_push_relay,"post_once",unknown_relay):
                unknown = await raw("POST","register",200,json=separate,headers=headers)
                assert not unknown["success"] and unknown["operation"]["phase"]=="unknown"
                assert "background_read" not in unknown
                again_unknown = await raw("POST","register",200,json=separate,headers=headers)
                assert again_unknown["replayed"] and "background_read" not in again_unknown
            effect_count = len(calls)
            assert effect_count==9 and calls[-3:]==["register","register","revoke"]
            # Fixture-only clock boundary: registration collection must retire
            # an idle/paused owner's watch WITHOUT any Broadcast callback.
            watch = next(iter(service._signals.values()))
            object.__setattr__(purpose,"wall",lambda:expiry)
            service.registry.journal._wall = lambda:expiry+1
            service.registry._collect()
            assert not service._signals and watch.row is None and watch.broadcast is None
            broadcast._publish(BroadcastEventType.PLAYBACK_PROGRESS,{})
            assert len(calls)==effect_count  # No expiry retry, replay or renewal.
        await manager.async_end(owner_profile_id=owner,session_id=sid)
        assert not purpose.is_current() and not service._purposes
        await raw("POST","read",401,json=read,headers=bg_headers)
        assert len(calls)==effect_count and not service._signals
        return {"scenario":"actual_ha_surface_http_SQL14_and_lifecycle",
            "requests":evidence,"SQL_commit_before_synthetic_relay":True,
            "synthetic_issuer_admission":True,"synthetic_API_responses":calls,
            "actual_operator_enrolment":"NOT_RUN","external_API_calls":0,
            "APNs_native_or_installed_acceptance":"NOT_RUN"}
    finally:
        await close_surface_service(hass)
        assert service.closed and not service._tasks
        await manager.async_end(owner_profile_id=owner,session_id=sid)

if __name__=="__main__":
    from verify_session_conversation_history_http import main
    asyncio.run(main(qualification_extension=qualify))
