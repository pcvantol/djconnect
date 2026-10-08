"""Source-shaped producer receipts through actual Runtime and owner routes.

No live provider, HA installation, Apple rendering or deployment is implied.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.test_http_voice_helpers import install_http_stubs  # noqa: E402
from tests.test_native_moment_delivery import NativeMomentDeliveryTest  # noqa: E402

BASE = 'ee05c9422cd7a7a08bbe769925248632fa651961'


def capture():
    install_http_stubs()
    handlers = importlib.import_module('custom_components.djconnect.api_handlers')
    http = importlib.import_module('custom_components.djconnect.http')
    NativeMomentDeliveryTest.setUpClass()
    fixture = NativeMomentDeliveryTest()
    fixture.run_sequence(fixture.runtime.DJPersona.HOME_DJ, count=1)
    manager, session = fixture.manager, fixture.session
    events=[]
    clock=[101.0]
    stamp=[session.broadcast.state.dj_moments[0].created_at]
    device={'device_id': 'djconnect-ios-ABCDEFGHIJKL', 'client_type': 'ios', 'session_id': session.session_id}
    request=types.SimpleNamespace(query=device, app={'hass':object()}, headers={}, context=None)

    async def bound(*args, **kwargs):
        return types.SimpleNamespace(profile_id='owner')

    async def scenario():
        response=await http.DJConnectSessionBroadcastSnapshotView(object()).get(request,session.session_id)
        initial=json.loads(response.text)
        subscribed,status,activate,cleanup=await handlers.async_handle_session_broadcast_subscribe_payload(
            object(),dict(device),callback=events.append)
        assert status == 200
        await activate()
        clock[0]=400.0
        stamp[0]=(datetime.fromisoformat(stamp[0])+timedelta(seconds=299)).isoformat()
        catalog, recording=fixture.source_pair(1)
        await manager.async_update_playback_projection(owner_profile_id='owner',session_id=session.session_id,
            state='playing', media_identity=catalog['uri'], title=catalog['title'],artist=catalog['artist'],
            album=catalog['album_name'],duration_ms=300000,position_ms=0)
        async def source():
            return {'_qualified_facts':tuple(fixture.facts.recording_facts(catalog,recording))}
        moment=await manager.async_process_track_started(owner_profile_id='owner',session_id=session.session_id,
            media_identity=catalog['uri'],insight_provider=source,require_current_playback=True,allow_initial_facts=True)
        assert moment and 'url_previous' in dict(moment.source_attribution)
        second_response=await http.DJConnectSessionBroadcastSnapshotView(object()).get(request,session.session_id)
        second=json.loads(second_response.text)
        cursor=subscribed['recovery_cursor']
        clock[0]=1901.0
        stamp[0]=(datetime.fromisoformat(stamp[0])+timedelta(seconds=1501)).isoformat()
        await manager.async_advance_playback_progress(owner_profile_id='owner',session_id=session.session_id)
        expired=session.broadcast.as_dict()
        recovery=session.broadcast.recover_owner(cursor)
        await manager.async_end(owner_profile_id='owner',session_id=session.session_id)
        terminal=session.broadcast.as_dict()
        await cleanup()
        return {'http_initial':initial,'websocket_initial':subscribed,
            'http_shared_producer':second,'events':events,'expired':expired,
            'reconnect':recovery,'terminal':terminal,
            'http_headers':dict(response.headers)}

    with (patch.object(handlers,'resolve_runtime',lambda *a,**k:object()),
          patch.object(handlers,'authorize_runtime_device_request',lambda *a,**k:True),
          patch.object(handlers,'async_resolve_device_bound_request_context',bound),
          patch.object(handlers,'session_runtime_manager',lambda hass:manager),
          patch('time.monotonic',lambda:clock[0]),
          patch.object(fixture.runtime,'_timestamp',lambda:stamp[0])):
        after=asyncio.run(scenario())
    # Exact baseline source, not an approximation of the old producer projection.
    baseline=subprocess.check_output(['git','show',f'{BASE}:custom_components/djconnect/session_runtime.py'],cwd=ROOT,text=True)
    exec(compile(baseline,f'{BASE}:session_runtime.py','exec'),fixture.runtime.__dict__)
    fixture.run_sequence(fixture.runtime.DJPersona.HOME_DJ,count=2)
    with patch('time.monotonic',lambda:1901.0):
        before={'initial':fixture.last_capture['snapshots'][0],
                'shared_producer':fixture.last_capture['snapshots'][1],
                'expired':fixture.session.broadcast.as_dict()}
    NativeMomentDeliveryTest.tearDownClass()
    return {'assignment_id':'DJC-CORE-NATIVE-MOMENT-DELIVERY-V1-20261008',
            'evidence_class':'SOFTWARE_SOURCE_SHAPED_PROVIDER_NO_LIVE_HA_OR_NATIVE_RENDER',
            'base':BASE,'before':before,'after':after,
            'candidate_files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
                'custom_components/djconnect/session_runtime.py',
                'custom_components/djconnect/native_moment_delivery.py',
                'custom_components/djconnect/http.py',
                'custom_components/djconnect/transport_capabilities.py')}}


if __name__ == '__main__':
    destination=Path(sys.argv[1])
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(capture(),ensure_ascii=False,indent=2)+'\n')
    print(destination)
