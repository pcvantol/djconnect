"""Licensed artist photographs for the existing private Session-media owner.

No name search, renderer, persistent pixels, AI calls or independent grants.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
import re
from urllib.parse import quote, urlencode, urlsplit, parse_qsl

API = 'https://commons.wikimedia.org/w/api.php'
WD = 'https://www.wikidata.org/w/api.php'
MAX_JSON = 512_000
MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = 'DJConnect/3.3.1 (https://github.com/pcvantol/djconnect)'
LICENSES = {f'CC BY{sa} {version}': (
    f'CC-BY{sa.replace(" ", "-")}-{version}',
    f'https://creativecommons.org/licenses/by{"-sa" if sa else ""}/{version}/')
    for sa in ('', '-SA') for version in ('2.0', '2.5', '3.0', '4.0')}
LICENSES.update({'CC0': ('CC0-1.0','https://creativecommons.org/publicdomain/zero/1.0/'),
    'Public domain': ('PDM-1.0','https://creativecommons.org/publicdomain/mark/1.0/')})


class PhotoUnavailable(ValueError):
    """Closed optional-image failure, never a raw remote diagnostic."""


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script','style'}:
            self.hidden += 1
        elif tag in {'br','p','div','li'}:
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in {'script','style'}:
            self.hidden = max(0,self.hidden-1)
        elif tag in {'p','div','li'}:
            self.parts.append(' ')

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def plain(value, maximum=640):
    if not isinstance(value,str) or len(value)>16000:
        return ''
    parser=_Text()
    parser.feed(value)
    text=' '.join(''.join(parser.parts).split())
    return text if 0<len(text)<=maximum and not any(ord(c)<32 for c in text) else ''


def filenames(entity, qid):
    if not re.fullmatch(r'Q[1-9][0-9]*',qid) or entity.get('id')!=qid:
        return []
    claims=entity.get('claims',{}).get('P18',[])
    if not isinstance(claims,list) or len(claims)>32:
        return []
    selected=[]
    for c in sorted((c for c in claims if isinstance(c,dict)),key=lambda c:c.get('rank')!='preferred'):
        snak=c.get('mainsnak',{})
        name=snak.get('datavalue',{}).get('value')
        if (c.get('rank')=='deprecated' or snak.get('snaktype','value')!='value'
                or not isinstance(name,str) or not 0<len(name)<=240
                or any(ord(v)<32 for v in name) or any(v in name for v in '/\\|#?{}')
                or not re.search(r'\.(?:jpe?g|png|webp)$',name,re.I)
                or re.search(r'(?:\blogo\b|signature|album[ _-]cover)',name,re.I)):
            continue
        title='File:'+name.replace('_',' ')
        if title not in selected:
            selected.append(title)
        if len(selected)==3:
            break
    return selected


def file_url(title):
    return 'https://commons.wikimedia.org/wiki/'+quote(title.replace(' ','_'),safe=':')


def upload_url(value):
    if not isinstance(value,str):
        return False
    p=urlsplit(value)
    return bool(p.scheme=='https' and p.netloc=='upload.wikimedia.org'
        and p.path.startswith('/wikipedia/commons/') and not p.fragment
        and all(k in {'utm_source','utm_campaign','utm_content'} for k,v in parse_qsl(p.query))
        and not any(v in p.path.lower() for v in ('..','\\','%2e','%2f','%5c')))


@dataclass(frozen=True)
class Candidate:
    title: str
    url: str
    width: int
    height: int
    author: str
    credit: str
    attribution: str
    license_id: str
    license_url: str
    revision: str
    live_hint: bool

    def metadata(self):
        return {'provider':'Wikimedia Commons','mark':'wikimedia_commons','url':file_url(self.title),
            'author':self.author,'credit':self.credit,'attribution_text':self.attribution,
            'license':self.license_id,'license_url':self.license_url,'image_revision':self.revision}


def candidates(data, titles):
    pages=data.get('query',{}).get('pages',[])
    if not isinstance(pages,list) or len(pages)>3:
        return []
    result=[]
    for page in pages:
        if not isinstance(page,dict) or page.get('title') not in titles or page.get('ns')!=6 or 'missing' in page:
            continue
        infos=page.get('imageinfo',[])
        if not isinstance(infos,list) or len(infos)!=1 or not isinstance(infos[0],dict):
            continue
        info=infos[0]
        ext=info.get('extmetadata',{})
        if not isinstance(ext,dict):
            continue
        def field(key,limit=640):
            v=ext.get(key,{})
            return plain(v.get('value'),limit) if isinstance(v,dict) else ''
        license=LICENSES.get(field('LicenseShortName'))
        author,credit,attribution=field('Artist'),field('Credit'),field('Attribution')
        w,h=info.get('thumbwidth',info.get('width')),info.get('thumbheight',info.get('height'))
        original_w,original_h=info.get('width'),info.get('height')
        url=info.get('thumburl',info.get('url'))
        if (upload_url(url) and upload_url(info.get('url'))
                and dict(parse_qsl(urlsplit(url).query)).get('utm_content')=='thumbnail_unscaled'
                and urlsplit(url)._replace(query='').geturl()==urlsplit(info['url'])._replace(query='').geturl()
                and type(original_w) is int and type(original_h) is int):
            # Imageinfo can report the requested thumbnail dimensions alongside
            # its explicitly unscaled original URL. Preserve intrinsic pixels;
            # never advertise an upscaled width as real image resolution.
            w,h=original_w,original_h
        revision=info.get('sha1','')
        if (not license or field('LicenseUrl').rstrip('/')!=license[1].rstrip('/') or not author
                or field('Restrictions') or not upload_url(url)
                or info.get('descriptionurl')!=file_url(page['title'])
                or info.get('mediatype')!='BITMAP' or (info.get('thumbmime') or info.get('mime')) not in {'image/jpeg','image/png','image/webp'}
                or type(w) is not int or type(h) is not int or min(w,h)<256 or max(w,h)<320
                or type(original_w) is not int or type(original_h) is not int
                or min(original_w,original_h)<256 or max(original_w,original_h)<320
                or w>original_w or h>original_h
                or max(w,h)>4096 or w*h>16_000_000
                or not isinstance(revision,str) or not re.fullmatch(r'(?:[a-f0-9]{40}|[a-z0-9]{31})',revision)):
            continue
        description=field('ImageDescription',4000)+' '+field('Categories',4000)
        if re.search(r'\b(?:album cover|front cover|back cover|certification|logo|signature|painting|drawing|illustration|collage)\b',page['title']+' '+description,re.I):
            continue
        live=bool(re.search(r'\b(?:concert|live performance|live music|on stage|performing live)\b',description,re.I))
        result.append(Candidate(page['title'],urlsplit(url)._replace(query='').geturl(),w,h,author,credit,attribution or ' — '.join(
            v for v in (author,credit,license[0]) if v),license[0],license[1],revision,live))
    return sorted(result,key=lambda c:(not c.live_hint,-c.width*c.height,c.title))


async def _read(hass, url, guard, *, json_body):
    from aiohttp import ClientTimeout
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    await guard()
    async with async_get_clientsession(hass).get(url,allow_redirects=False,
            headers={'User-Agent':USER_AGENT},timeout=ClientTimeout(total=5)) as response:
        await guard()
        if response.status!=200:
            failure=PhotoUnavailable('source_unavailable')
            failure.http_status=response.status
            raise failure
        mime=response.headers.get('Content-Type','').split(';')[0].strip().lower()
        maximum=MAX_JSON if json_body else MAX_BYTES
        body=bytearray()
        async for chunk in response.content.iter_chunked(16384):
            await guard()
            body.extend(chunk)
            if len(body)>maximum:
                raise PhotoUnavailable('image_too_large')
    if json_body:
        try:
            value=json.loads(body)
            if isinstance(value,dict) and 'error' not in value:
                return value
        except (ValueError,TypeError):
            pass
        raise PhotoUnavailable('source_unavailable')
    return bytes(body),mime


async def _depicted_candidates(hass,qid,guard):
    """Structured QID retrieval is not identity proof; check actual MediaInfo."""
    query=await _read(hass,API+'?'+urlencode({'action':'query','generator':'search',
        'gsrsearch':'haswbstatement:P180='+qid+' (concert OR "live performance" OR "on stage") filetype:bitmap','gsrnamespace':6,'gsrlimit':3,
        'prop':'imageinfo','iiprop':'url|size|mime|mediatype|sha1|extmetadata',
        'iiurlwidth':1024,'iiextmetadatalanguage':'en','format':'json','formatversion':2}),guard,json_body=True)
    pages=query.get('query',{}).get('pages',[])
    if not isinstance(pages,list) or len(pages)>3:
        return []
    pages=[p for p in pages if isinstance(p,dict) and type(p.get('pageid')) is int and p['pageid']>0
           and isinstance(p.get('title'),str) and p['title'].startswith('File:')
           and filenames({'id':qid,'claims':{'P18':[{'mainsnak':{'datavalue':{'value':p['title'][5:]}}}]}},qid)]
    if not pages:
        return []
    mids=['M'+str(p['pageid']) for p in pages]
    raw=await _read(hass,API+'?'+urlencode({'action':'wbgetentities','ids':'|'.join(mids),
        'props':'claims','format':'json'}),guard,json_body=True)
    entities=raw.get('entities',{})
    admitted=[]
    for p,mid in zip(pages,mids):
        value=entities.get(mid,{})
        if value.get('id')!=mid or value.get('type')!='mediainfo':
            continue
        statements=value.get('statements',{}).get('P180',[])
        if not isinstance(statements,list):
            continue
        if any(isinstance(c,dict) and c.get('rank')!='deprecated'
               and c.get('mainsnak',{}).get('property')=='P180'
               and c['mainsnak'].get('snaktype')=='value'
               and c['mainsnak'].get('datavalue',{}).get('type')=='wikibase-entityid'
               and c['mainsnak']['datavalue'].get('value',{}).get('id')==qid for c in statements):
            admitted.append(p)
    return [c for c in candidates({'query':{'pages':admitted}},[p['title'] for p in admitted]) if c.live_hint]


async def fetch(hass, qid, *, guard, decode):
    """One QID; up to three P18 and three proved P180 candidates, one image.

    At most five requests inside the existing outer20second budget.
    """
    if not isinstance(qid,str) or not re.fullmatch(r'Q[1-9][0-9]*',qid):
        raise PhotoUnavailable('insufficient_identity')
    data=await _read(hass,WD+'?'+urlencode({'action':'wbgetentities','ids':qid,
        'props':'claims','format':'json'}),guard,json_body=True)
    entity=data.get('entities',{}).get(qid,{})
    if entity.get('id')!=qid:
        raise PhotoUnavailable('insufficient_identity')
    titles=filenames(entity,qid)
    choices=[]
    if titles:
        data=await _read(hass,API+'?'+urlencode({'action':'query','titles':'|'.join(titles),
            'prop':'imageinfo','iiprop':'url|size|mime|mediatype|sha1|extmetadata',
            'iiurlwidth':1024,'iiextmetadatalanguage':'en','format':'json','formatversion':2}),guard,json_body=True)
        choices=candidates(data,titles)
    if not choices or not choices[0].live_hint:
        try:
            choices.extend(await _depicted_candidates(hass,qid,guard))
        except PhotoUnavailable:
            if not choices:
                raise
        choices.sort(key=lambda c:(not c.live_hint,-c.width*c.height,c.title))
    if not choices:
        raise PhotoUnavailable('missing_image')
    selected=choices[0]  # Never switch to an unqualified/second image after failure.
    body,mime=await _read(hass,selected.url,guard,json_body=False)
    from .forecast_imagery import image_format
    if not image_format(body,mime):
        raise PhotoUnavailable('unsafe_image')
    width,height=await decode(body)
    await guard()
    if (width,height)!=(selected.width,selected.height):
        raise PhotoUnavailable('unsafe_image')
    return body,mime,selected
