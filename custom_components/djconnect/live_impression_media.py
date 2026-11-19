"""Original Live-impressie photos through the existing owner Session image registry."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode

from . import artist_photo
from .live_impression import BASIS, admitted, checked
from .live_impression_research import EventPublicFetch,metadata_revision,original_metadata


def authority(hass, owner):
    from .profile_context import profile_storage
    from .profile_privacy import resolve_profile_privacy_policy
    profile = profile_storage(hass).household.profiles.get(owner)
    return bool(profile is not None and str(profile.state)=='active'
        and resolve_profile_privacy_policy(profile,{}).allow_personal_read)


async def resolve(hass,owner,session_id,target):
    """No latest-track substitution; current and retained entry identities only."""
    from .session_runtime import session_runtime_manager
    manager=session_runtime_manager(hass)
    active=manager._active_by_profile.get(owner)
    if 'moment_id' in target:
        if active is None or active.session_id!=session_id:
            return None
        moment=next((m for m in active.broadcast.state.dj_moments if m.moment_id==target['moment_id']),None)
        admission=next((a for a in active.broadcast.native_delivery()['admissions'] if a['moment_id']==target['moment_id']),{})
        if (moment is None or not admitted(moment) or target['moment_id'] in active.deleted_moment_ids
                or target['moment_id'] in active.broadcast.content_pending_moment_ids
                or not(admission.get('current_display_allowed') or admission.get('active_flow_display_allowed'))):
            return None
        payload=json.loads(moment.live_impression.payload_json)
        reference=json.loads(moment.live_impression.reference_json)
        pixels=mime=None
        historical=False
        scope=(bool(admission.get('current_display_allowed')),False)
        retained_until=None
    else:
        from .session_conversation import query_service
        query=query_service(hass)
        opened=await query.async_open_entry(owner,session_id,target['entry_id'])
        row=await query._repository.async_entry_record(owner,session_id,target['entry_id'])
        if row is None or row['kind']!='dj_moment':
            return None
        body=json.loads(row['body'])
        if body.get('archive_basis')!=BASIS or checked(body.get('live_impression')) is None:
            return None
        payload=body['live_impression']
        reference=body.get('live_impression_reference')
        pixels=mime=None
        historical=opened['read_only']
        scope=(False,bool(historical))
        retained_until=datetime.fromisoformat(row['retained_until']).timestamp()
    photo=next((p for p in payload['photos'] if p['photo_id']==target['photo_id']),None)
    if (photo is None or not isinstance(reference,dict) or reference.get('photo_id')!=photo['photo_id']
            or reference.get('revision')!=photo['revision'] or reference.get('source_url')!=photo['source_url']
            or reference.get('license')!=photo['license'] or reference.get('license_url')!=photo['license_url']):
        return None
    return photo,reference,pixels,mime,scope,retained_until


async def refetch(reference,guard):
    """Resolve one original photo, never search, select or regenerate on a read."""
    from urllib.parse import unquote
    from .session_artwork import _decoded_size
    title=unquote(reference['source_url'].removeprefix('https://commons.wikimedia.org/wiki/')).replace('_',' ')
    if not title.startswith('File:') or artist_photo.file_url(title)!=reference['source_url']:
        raise ValueError('original_photo_identity_invalid')
    async with EventPublicFetch(guard) as fetch:
        status,body,_=await fetch.request(artist_photo.API+'?'+urlencode({
            'action':'query','titles':title,'prop':'imageinfo','iiprop':'url|size|mime|mediatype|sha1|extmetadata',
            'iiurlwidth':1600,'format':'json','formatversion':2}),maximum=512000)
        if status!=200:
            raise ValueError('original_photo_unavailable')
        data=json.loads(body)
        photos=artist_photo.candidates(data,[title])
        photo=next((p for p in photos if p.revision==reference.get('commons_revision')
            and p.url==reference.get('url') and p.original_url==reference.get('original_url')
            and p.license_id==reference['license'] and p.license_url==reference['license_url']),None)
        if photo is None:
            raise PermissionError('original_photo_withdrawn')
        page=next((p for p in data.get('query',{}).get('pages',[]) if p.get('title')==title),None)
        caption,original_date=original_metadata(page)
        if metadata_revision(photo,caption,original_date)!=reference.get('source_metadata_revision'):
            raise PermissionError('original_photo_metadata_withdrawn')
        pixels,mime=await fetch.image(photo.url)
        from .forecast_imagery import image_format
        if not image_format(pixels,mime) or hashlib.sha256(pixels).hexdigest()!=reference['revision']:
            raise ValueError('original_photo_bytes_changed')
        dimensions=await asyncio.to_thread(_decoded_size,pixels)
        if dimensions!=(photo.width,photo.height):
            raise ValueError('original_photo_dimensions_changed')
        await guard()
        return pixels,mime


async def prepare(hass,runtime,context,*,session_id,target,preloaded=None):
    from .image_proxy import session_images
    from .session_artwork import unavailable,PATH,TTL,target_key,project,projection_revision
    registry=session_images(hass)
    key=target_key(context.profile_id,session_id,target,3)
    original=await resolve(hass,context.profile_id,session_id,target)
    if original is None or not authority(hass,context.profile_id):
        return unavailable(session_id,target,'target_unavailable',contract_version=3)
    photo,reference,pixels,mime,scope,retained_until=original
    if preloaded is not None:
        pixels,mime=preloaded
        if hashlib.sha256(pixels).hexdigest()!=photo["revision"]:
            return unavailable(session_id,target,"source_unavailable",contract_version=3)
    lifetime=[True]
    def delivery_scope():
        if not lifetime[0] or retained_until is not None and time.time()>=retained_until:
            return None
        from .session_runtime import session_runtime_manager
        active=session_runtime_manager(hass)._active_by_profile.get(context.profile_id)
        same=active is not None and active.session_id==session_id
        if scope[1]:
            return None if same else (False,True)
        if not same:
            return None
        if 'moment_id' in target:
            a=next((a for a in active.broadcast.native_delivery()['admissions'] if a['moment_id']==target['moment_id']),{})
            return (bool(a.get('current_display_allowed')),False) if a.get('current_display_allowed') or a.get('active_flow_display_allowed') else None
        return False,False
    delivery_scope.history_retained_until=retained_until
    delivery_scope.history_session_created_at=None
    def authorized():
        return (lifetime[0] and authority(hass,context.profile_id) and delivery_scope() is not None
            and not registry.history_blocked(key,{},delivery_scope))
    async def allowed():
        current=await resolve(hass,context.profile_id,session_id,target)
        return bool(current and current[0]==photo and current[1]==reference and current[4][1]==scope[1] and authorized())
    async def guard():
        if not authorized() or not await allowed() or not authorized():
            raise PermissionError('photo_owner_changed')
    cached=registry.get(key)
    if cached and await cached['allowed']() and authorized():
        return project(cached,current=delivery_scope()[0],historical=scope[1])
    if key in registry.inflight:
        return await asyncio.shield(registry.inflight[key])
    registry.collect()
    if key in registry.negative or len(registry.assets)+len(registry.inflight)+len(registry.negative)>=64 or len(registry.inflight)>=8:
        return unavailable(session_id,target,'capacity',contract_version=3)
    async def run():
        try:
            async with asyncio.timeout(20),registry.semaphore:
                await guard()
                body,content_type=(pixels,mime) if pixels is not None else await refetch(reference,guard)
                await guard()
                asset_id=secrets.token_urlsafe(24)
                wall,mono=time.time(),time.monotonic()
                expiry=min(wall+TTL,retained_until if retained_until is not None else wall+TTL)
                artwork={'state':'ready','subject':{'provider':'public_research','type':'event_photo','uri':photo['photo_id']},
                    'role':'live_impression','resolution_basis':'original_bound','edition_basis':'not_applicable',
                    'source_url':photo['source_url'],'attribution':{'provider':'Wikimedia Commons','mark':'wikimedia_commons','url':photo['source_url']},
                    'usage_basis':'licensed_event_image_owner_display',
                    'captured_at':datetime.fromtimestamp(wall,UTC).isoformat(),'expires_at':datetime.fromtimestamp(expiry,UTC).isoformat(),
                    'current_display_allowed':delivery_scope()[0],'active_flow_display_allowed':not scope[1],
                    'historical_display_allowed':scope[1],'cache_policy':'no-store','crop_allowed':False,'upscale_allowed':False,
                    'requires_device_auth':True,'width':photo['width'],'height':photo['height'],
                    'alt_text':photo['alt_text'],
                    'media_revision':photo['revision'],'url':PATH.format(session_id=session_id,asset_id=asset_id)}
                projection={'schema_version':3,'session_id':session_id,**target,'revision':projection_revision(artwork),'artwork':artwork}
                asset={'body':body,'mime':content_type,'deadline':mono+expiry-wall,'captured_monotonic':mono,
                    'authority':authorized,'allowed':allowed,'asset_id':asset_id,'subject':photo['photo_id'],'projection':projection,
                    'historical':scope[1],'expected_source':{},'delivery_scope':delivery_scope}
                if not registry.commit(key,asset):
                    return unavailable(session_id,target,'capacity',contract_version=3)
                return projection
        except asyncio.CancelledError:
            raise
        except PermissionError:
            lifetime[0]=False
            registry.record_state(key,'source_withdrawn')
            return unavailable(session_id,target,'source_withdrawn',contract_version=3)
        except Exception:
            registry.negative[key]=time.monotonic()+60
            return unavailable(session_id,target,'source_unavailable',contract_version=3)
        finally:
            registry.inflight.pop(key,None)
    task=hass.async_create_task(run())
    registry.inflight[key]=task
    return await asyncio.shield(task)
