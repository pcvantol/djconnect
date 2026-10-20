"""Real public-photo adapter probe in pinned HA; no credentials or publication."""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types

from homeassistant.core import HomeAssistant, CoreState
from homeassistant.components import network
from homeassistant.helpers import frame

ROOT=Path(os.environ.get('DJC_SOURCE_ROOT','/candidate'))
sys.path.insert(0,str(ROOT))
# Import the actual adapter without starting the integration or any paired owner.
# This is source/metadata/pixel qualification, not a Session/HTTP/native claim.
for name,folder in (('custom_components',ROOT/'custom_components'),
                    ('custom_components.djconnect',ROOT/'custom_components/djconnect')):
    module=types.ModuleType(name)
    module.__path__=[str(folder)]
    sys.modules[name]=module
from custom_components.djconnect import artist_photo  # noqa: E402 - isolated namespace above
from custom_components.djconnect.session_artwork import _decoded_size  # noqa: E402


async def main():
    names=['custom_components/djconnect/'+f for f in ('artist_photo.py','session_artwork.py','session_facts.py','session_runtime.py')]
    names.append('scripts/verification/verify_session_artist_photo.py')
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names}
    report={'scope':'ACTUAL_PINNED_HA_PUBLIC_PHOTO_ADAPTER_NOT_SESSION_OR_INSTALLED',
        'subject_qid':'Q11649','subject_boundary':'Controlled public Nirvana sample, not inferred from live playback',
        'source_hashes':pins,'requests':[],'paid_model_calls':0,'installed':'NOT_RUN','native':'NOT_RUN',
        'publication':'NOT_RUN'}
    original=artist_photo._read
    async def recorded(hass,url,guard,*,json_body):
        row={'url':url,'kind':'json' if json_body else 'image'}
        report['requests'].append(row)
        try:
            value=await original(hass,url,guard,json_body=json_body)
            row['status']='RECEIVED'
            if json_body:
                row['public_summary']={}
                if 'entities' in value:
                    row['public_summary']['entities']=[{
                        'id':e.get('id'),'type':e.get('type'),
                        'P18':[c.get('mainsnak',{}).get('datavalue',{}).get('value')
                               for c in e.get('claims',{}).get('P18',[])][:4],
                        'P180':[c.get('mainsnak',{}).get('datavalue',{}).get('value')
                                for c in e.get('statements',{}).get('P180',[])][:12]}
                        for e in value['entities'].values()][:3]
                if 'query' in value:
                    row['public_summary']['pages']=value['query'].get('pages',[])[:3]
            return value
        except Exception as e:
            row.update(status='UNAVAILABLE',failure_type=type(e).__name__,http_status=getattr(e,'http_status',None))
            raise
    async def guard():
        pass
    with TemporaryDirectory() as directory:
        hass=HomeAssistant(directory)
        hass.state=CoreState.running
        frame.async_setup(hass)
        await network.async_setup(hass,{})
        async def decode(body):
            return await hass.async_add_executor_job(_decoded_size,body)
        artist_photo._read=recorded
        try:
            async with asyncio.timeout(22):
                body,mime,candidate=await artist_photo.fetch(hass,'Q11649',guard=guard,decode=decode)
            suffix={'image/png':'png','image/jpeg':'jpg','image/webp':'webp'}[mime]
            filename='licensed-artist-photo.'+suffix
            (Path('/lab')/filename).write_bytes(body)
            report.update(status='PASS_ADAPTER_ONLY',image_file=filename,image_sha256=hashlib.sha256(body).hexdigest(),
                mime=mime,width=candidate.width,height=candidate.height,metadata=candidate.metadata(),
                live_selection_hint=candidate.live_hint,visual_review='NOT_RUN')
        except Exception as e:
            report.update(status='UNAVAILABLE',failure_type=type(e).__name__,reason=str(e) if isinstance(e,artist_photo.PhotoUnavailable) else 'probe_failed',
                http_status=getattr(e,'http_status',None))
        finally:
            artist_photo._read=original
            await hass.async_stop(force=True)
    report['source_unchanged']=pins=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names}
    Path('/lab/public-artist-photo.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k) for k in ('status','reason','http_status','image_file','source_unchanged')}))


if __name__=='__main__':
    asyncio.run(main())
