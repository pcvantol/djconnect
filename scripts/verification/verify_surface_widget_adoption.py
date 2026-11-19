"""Disposable actual HA widget adoption/ES256/SQL15+14/routes; synthetic owner/API boundary.

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


async def adopt_original_widget(hass, service, manager, authority, identity, headers, sid, now, policy):
    """Actual service/SQL15/ES256, explicitly synthetic pre-enrollment and RPC."""
    import base64
    import hashlib
    import weakref
    from dataclasses import replace
    from uuid import UUID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    from custom_components.djconnect.surface_issuer_owner import WidgetIssuerOwner, IssuerOwnerCapture
    from custom_components.djconnect.surface_issuer_responses import ExpectedIssuerReply
    from custom_components.djconnect.surface_issuer_wire import DOMAIN, public_key_thumbprint, verify_envelope
    from custom_components.djconnect.surface_issuer_transport import IssuerTransport, IssuerHTTPReply
    from custom_components.djconnect.surface_issuer_journal import IssuerStageJournal, IssuerStageStore
    from custom_components.djconnect.surface_issuer_lifecycle import IssuerLifecycle
    from custom_components.djconnect.surface_push_wire import canonical
    from custom_components.djconnect.surface_push_contract import SurfacePushError
    from custom_components.djconnect.persistence import persistence_service
    from custom_components.djconnect.hybrid_service import PairedAuthority
    def encoded(raw):
        return base64.urlsafe_b64encode(raw).decode().rstrip('=')
    operation_id = str(UUID(int=(now<<80)|(7<<76)|(2<<62)|101))
    persistence = persistence_service(hass)
    class EphemeralWidgetOwner(WidgetIssuerOwner):
        def __init__(self):
            self.key = ec.generate_private_key(ec.SECP256R1())  # Synthetic process RAM only.
            numbers = self.key.public_key().public_numbers()
            jwk = {'kty':'EC','crv':'P-256','x':encoded(numbers.x.to_bytes(32)),
                'y':encoded(numbers.y.to_bytes(32))}
            thumb = public_key_thumbprint(jwk)
            fields = dict(binding_id=authority.binding,device_binding=authority.device,
                owner_binding=authority.owner,grant_binding='e'*64,source_binding='f'*64)
            digest = hashlib.sha256(canonical([DOMAIN,'delegation','synthetic-widget-delegation',1,
                'synthetic-widget-install',fields['device_binding'],fields['owner_binding'],
                fields['grant_binding'],fields['source_binding'],fields['binding_id'],thumb,policy]).encode()).hexdigest()
            expected = ExpectedIssuerReply('synthetic-widget-delegation',operation_id,thumb,digest,
                policy['original_grant_expires_at_ms'],now,time.monotonic())
            self.original = IssuerOwnerCapture(expected,'https://synthetic.example.invalid',
                'synthetic-widget-install',canonical(jwk),canonical(policy),**fields,witness=object())
            self.current = True
        def capture_live(self, operation_id):
            return replace(self.original,expected=replace(self.original.expected,operation_id=operation_id))
        def validate_live(self, original):
            assert self.current and original.witness is self.original.witness
        def validate_status(self, original):
            assert original.witness is self.original.witness
        def validate_withdrawal(self, original):
            assert original.witness is self.original.witness
        def validate_widget_adoption(self, original, capture):
            self.validate_live(original)
            assert capture.service is service and capture.manager is manager
            assert capture.session_id == sid and capture.broadcast is manager.current_active('profile-a').broadcast
            assert capture.owner_binding == authority.owner and capture.device_binding == authority.device
            assert capture.source_current()
        async def sign(self, original, path, message, *, action):
            self.validate_status(original)
            r,s = utils.decode_dss_signature(self.key.sign(message,ec.ECDSA(hashes.SHA256())))
            return encoded(r.to_bytes(32)+s.to_bytes(32))
    class SyntheticIssuer(IssuerTransport):
        def __init__(self):
            self.calls=[]
        async def post_once(self, original, action, envelope, *, guard, deadline):
            guard()
            verify_envelope('/v1/push/surface/issuer/'+action,envelope,json.loads(original.public_key_json))
            row = await persistence.async_in_transaction(lambda tx:tx.fetchone(
                'SELECT body FROM djconnect_surface_issuer_journal WHERE singleton=1'))
            phase = next(iter(json.loads(row[0])['records'].values()))['phase']
            assert phase == {'challenge':'challenge_reserved','issue':'issue_reserved'}[action]
            self.calls.append(action)
            e=original.expected
            reply={'contract_version':1,'success':True,'operation_id':e.operation_id,
                'delegation_id':e.delegation_id,'delegation_revision':1,
                'expires_at_ms':e.original_grant_expires_ms,'state':action,'replayed':False,
                'scope_digest':e.scope_digest}
            if action=='challenge':
                reply.update(challenge_id='synthetic-challenge',nonce='A'*43,
                    key_thumbprint=e.key_thumbprint,expires_at_ms=now+120000)
            else:
                reply.update(state='issued',capability_id='synthetic-capability',credential='djcs_'+'A'*43)
            return IssuerHTTPReply(200,reply)
    owner, rpc = EphemeralWidgetOwner(), SyntheticIssuer()
    lifecycle = IssuerLifecycle(owner,IssuerStageJournal(IssuerStageStore(persistence)),rpc)
    # Original actual Session capture is fenced BEFORE the task is even started.
    first = service.begin_widget_adoption(lifecycle,operation_id,identity,headers)
    first_ref=weakref.ref(first.capture)
    service.invalidate_entry('owner-entry')
    try:
        await service.adopt_widget(first)
    except SurfacePushError:
        pass
    else:
        raise AssertionError('pre-scheduling unload adopted')
    assert first_ref() is None and first.capture is None and first.authority is None and not rpc.calls
    # The actual PairedAuthority resolver executes; the wrapper only interposes
    # a synchronous unload immediately before its late result is returned.
    original_resolve=PairedAuthority.resolve
    async def late(*args,**kwargs):
        result=await original_resolve(*args,**kwargs)
        service.invalidate_entry('owner-entry')
        return result
    second=service.begin_widget_adoption(lifecycle,operation_id,identity,headers)
    with patch.object(PairedAuthority,'resolve',late):
        try:
            await service.adopt_widget(second)
        except SurfacePushError:
            pass
        else:
            raise AssertionError('late paired result adopted')
    assert second.capture is None and second.authority is None and not rpc.calls
    handle=service.begin_widget_adoption(lifecycle,operation_id,identity,headers)
    purpose=await service.adopt_widget(handle)
    assert rpc.calls==['challenge','issue'] and purpose is lifecycle._retained(handle.issuer_handle).purpose
    assert await service.adopt_widget(handle) is purpose and rpc.calls==['challenge','issue']
    service._widget_qualification = {'pre_scheduling_unload_denied':True,'late_paired_authority_scrubbed':True,
        'original_ES256_and_SQL15_before_RPC':True,'once_original_winner_no_renewal':True,
        'synthetic_issuer_calls':rpc.calls,'operator_enrollments':0,'provider_calls':0,'private_keys_persisted':0}
    owner.key=None  # No later signing in this qualification; no retained key or output.
    return purpose, handle

async def qualify(hass,manager,history,request,client):
    from custom_components.djconnect import api_handlers
    from custom_components.djconnect.playback_observation import PlaybackObservationManager
    from custom_components.djconnect.surface_push_service import start_surface_service,close_surface_service
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
        v2context = {**context,"contract_version":2,"operation_id":context_operation}
        await raw("POST","context",401,json=v2context)
        before_unauthorized = (len(service.contexts._starts), len(service.contexts._contexts))
        for sequence in range(64):
            forged = {**v2context, "operation_id":str(UUID(int=(context_now<<80)|(7<<76)|(2<<62)|(1000+sequence)))}
            await raw("POST","context",401,json=forged)
        assert (len(service.contexts._starts), len(service.contexts._contexts)) == before_unauthorized
        await raw("POST","context",503,json=v2context,headers=headers)
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
        purpose, adoption_handle = await adopt_original_widget(hass,service,manager,authority,
            identity,headers,sid,now,policy)
        # Actual paired/source admission is completed before the interposed late
        # failure. Only the disposable clock/error boundary is synthetic.
        from custom_components.djconnect.surface_push_context import SurfaceContextContinuations
        from custom_components.djconnect.surface_push_contract import SurfacePushError
        real_admission = service.admission
        for number, failure in enumerate((SurfacePushError("surface_purpose_unavailable",503), OSError("synthetic-offline"))):
            clock = [int(time.time()*1000), time.monotonic()]
            isolated = SurfaceContextContinuations(service,wall=lambda:clock[0],monotonic=lambda:clock[1])
            attempt = {**v2context,"operation_id":str(UUID(int=(clock[0]<<80)|(7<<76)|(2<<62)|(2000+number)))}
            async def fail_after_paired(payload, request_headers):
                original = await real_admission(payload, request_headers)
                original.validate()
                clock[0] += 31000
                clock[1] += 31
                raise failure
            with patch.object(service,"admission",fail_after_paired):
                try:
                    await isolated.acquire(attempt,headers)
                except type(failure):
                    pass
                else:
                    raise AssertionError("late admission error was not observed")
            assert attempt["operation_id"] in isolated._starts
            try:
                await isolated.acquire(attempt,headers)
            except SurfacePushError as problem:
                assert problem.code=="surface_context_expired"
            else:
                raise AssertionError("late admission failure reanchored submit lease")
        assert not calls
        captured = await raw("POST","context",200,json=v2context,headers=headers)
        recovered = await raw("POST","context",200,json=v2context,headers=headers)
        assert recovered == captured and captured["expires_at_ms"]==expiry
        assert captured["context_expires_at_ms"] < expiry
        async def context_for(body):
            reply = await raw("POST","context",200,
                json={**context,"contract_version":2,"operation_id":body["operation_id"]},headers=headers)
            assert reply["purpose_ref"]==captured["purpose_ref"] and reply["expires_at_ms"]==expiry
            return reply["context_handle"]
        operation = context_operation
        payload = {**context,"contract_version":2,"context_handle":captured["context_handle"],
            "operation_id":operation,"platform":"ios","os_version":"26.0",
            "token_role":"widget","target":target,"apns_token":"a"*64,
            "apns_environment":"sandbox","expected_registration":None,
            "consent":{"background_read":True,"os_snapshot_cache":True,"locked_display":False,
                "external_push_content":False,"allow_remote_start":False}}
        legacy = {k:v for k,v in payload.items() if k!="context_handle"}
        legacy["contract_version"] = 1
        await raw("POST","register",409,json=legacy,headers=headers)
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
        assert adoption_handle.capture is None and adoption_handle.authority is None
        await raw("POST","read",401,json=read,headers=bg_headers)
        assert len(calls)==effect_count and not service._signals
        return {"scenario":"actual_ha_widget_adoption_SQL15_SQL14_HTTP_crypto_and_lifecycle",
            "widget_adoption":service._widget_qualification,
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
