"""One exact-QID artist website inside the existing narration fetch owner.

An official-site relationship selects a source, never authenticates its claims.
No new agent, opportunity, endpoint, retry, network profile or durable corpus.
"""
import asyncio
from dataclasses import dataclass
import json
import re
from urllib.parse import urlencode, urlsplit

from .ask_dj.public_research import PublicSource


@dataclass(frozen=True)
class ArtistWebsiteSource(PublicSource):
    artist_identity: tuple[str, ...] = ()
    website_claim: str = ''
    entity_revision: int = 0

    def metadata(self):
        return {**super().metadata(), 'usage_basis':'public_page_short_reference',
            'publisher':urlsplit(self.url).hostname,
            'official_site_reference':{'basis':'wikidata_p856_v1',
                'entity_id':self.entity_id,'claim_id':self.website_claim,
                'revision':self.entity_revision}}


def language_qualifiers_only(claim):
    """P407 describes website language, never subject, validity or time scope."""
    qualifiers=claim.get('qualifiers',{})
    if not isinstance(qualifiers,dict) or set(qualifiers)-{'P407'}:
        return False
    if not qualifiers:
        return True
    values=qualifiers['P407']
    if not isinstance(values,list) or not values:
        return False
    for value in values:
        if not isinstance(value,dict):
            return False
        data=value.get('datavalue',{})
        if not isinstance(data,dict):
            return False
        entity=data.get('value',{})
        if (value.get('property')!='P407' or value.get('snaktype')!='value'
                or value.get('datatype')!='wikibase-item' or data.get('type')!='wikibase-entityid'
                or not isinstance(entity,dict) or entity.get('entity-type')!='item'
                or not re.fullmatch(r'Q[1-9][0-9]*',str(entity.get('id','')))
                or type(entity.get('numeric-id')) is not int
                or str(entity['numeric-id'])!=entity['id'][1:]):
            return False
    return True


async def website_entity(fetch, qid):
    """Known Wikibase version token, not a claim of representation-byte equality."""
    url='https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/'+qid+'/statements?'+urlencode({'property':'P856'})
    status,body,final,etag=await fetch.request(url,with_etag=True)
    if status!=200 or final!=url or not isinstance(etag,str) or not re.fullmatch(r'(?:W/)?"[1-9][0-9]*"',etag):
        return None
    # Wikibase encodes this entity revision in the same property response;
    # an intermediary may mark the representation validator weak. Only this
    # exact provider/endpoint gives the numeric token entity-version meaning.
    revision=int(etag.removeprefix('W/')[1:-1])
    if revision>9_007_199_254_740_991:
        return None
    data=json.loads(body)
    if not isinstance(data,dict) or set(data)-{'P856'} or not isinstance(data.get('P856',[]),list):
        return None
    claims=[]
    for statement in data.get('P856',[]):
        if not isinstance(statement,dict):
            return None
        if statement.get('rank') not in {'normal','preferred'}:
            continue
        prop,value=statement.get('property'),statement.get('value')
        qualifiers=statement.get('qualifiers',[])
        if (not isinstance(prop,dict) or prop.get('id')!='P856' or prop.get('data_type')!='url'
                or not isinstance(value,dict) or value.get('type')!='value'
                or not isinstance(value.get('content'),str) or not isinstance(qualifiers,list)):
            return None
        languages=[]
        for qualifier in qualifiers:
            if not isinstance(qualifier,dict):
                return None
            qp,qv=qualifier.get('property'),qualifier.get('value')
            if (not isinstance(qp,dict) or qp.get('id')!='P407' or qp.get('data_type')!='wikibase-item'
                    or not isinstance(qv,dict) or qv.get('type')!='value'
                    or not isinstance(qv.get('content'),str) or not re.fullmatch(r'Q[1-9][0-9]*',qv['content'])):
                return None
            languages.append({'property':'P407','snaktype':'value','datatype':'wikibase-item',
                'datavalue':{'type':'wikibase-entityid','value':{'entity-type':'item',
                    'id':qv['content'],'numeric-id':int(qv['content'][1:])}}})
        claims.append({'id':statement.get('id'),'rank':statement.get('rank'),
            'qualifiers':{'P407':languages} if languages else {},
            'mainsnak':{'property':'P856','datatype':'url','snaktype':'value',
                'datavalue':{'value':value['content']}}})
    return {'id':qid,'lastrevid':revision,'claims':{'P856':claims}}


async def website_reference(fetch, identity, topic):
    from .ask_dj.public_research import PageText, MUSIC, public_url, _source
    from .session_story_variety import passage_score
    if (type(identity) is not tuple or len(identity)!=5 or identity[0]!='artist'
            or identity[3] not in {'Group','Person'}
            or not re.fullmatch(r'Q[1-9][0-9]*',identity[4])
            or fetch.maximum_requests-fetch.requests<3):
        return None
    qid,subject=identity[4],identity[2]
    entity=await website_entity(fetch,qid)
    if (not isinstance(entity,dict) or entity.get('id')!=qid or type(entity.get('lastrevid')) is not int
            or not 0<entity['lastrevid']<=9_007_199_254_740_991):
        return None
    candidates=[]
    for claim in entity.get('claims',{}).get('P856',[]):
        snak=claim.get('mainsnak',{})
        value=snak.get('datavalue',{}).get('value')
        if (claim.get('rank') not in {'normal','preferred'} or not language_qualifiers_only(claim)
                or not re.fullmatch(re.escape(qid)+r'\$[0-9a-fA-F-]{36}',str(claim.get('id','')))
                or snak.get('snaktype')!='value' or snak.get('property')!='P856'
                or snak.get('datatype')!='url' or type(value) is not str or not public_url(value)):
            continue
        candidates.append((claim['rank'],value,claim['id']))
    preferred=[c for c in candidates if c[0]=='preferred']
    candidates=preferred or candidates
    if len({c[1] for c in candidates})!=1:
        return None
    _,url,claim_id=sorted(candidates)[0]
    if not await fetch.robots(url):
        return None
    status,body,final=await fetch.request(url)
    # Do not transfer the exact source/robots witness to a different destination.
    if status!=200 or final!=url:
        return None
    parser=PageText(omit_headings=True)
    parser.feed(body)
    original=parser.text()
    mentions=re.compile(r'(?<!\w)'+re.escape(subject)+r'(?!\w)',re.I)
    paragraphs=[p for p in re.finditer(r'[^\n]+',original)
        if mentions.search(p[0]) and MUSIC.search(p[0])
        and re.search(r'[.!?][\"\x27’”»\)\]]*$',p[0]) and len(p[0])<=600]
    if not paragraphs:
        return None
    selected=[]
    size=0
    for paragraph in sorted(paragraphs,key=lambda p:(-passage_score(p[0],topic),p.start())):
        if size+len(paragraph[0])+bool(selected)>600 or len(selected)>=2:
            continue
        selected.append(paragraph)
        size+=len(paragraph[0])+bool(size)
    selected.sort(key=lambda p:p.start())
    value=_source('Artist website',subject,url,'\n'.join(p[0] for p in selected),parser.language,
        entity_id=qid,current=topic=='live_performance',source_anchors=parser.source_anchors,
        original_text=original,paragraph_ranges=tuple((p.start(),p.end()) for p in selected))
    return ArtistWebsiteSource(**value.__dict__,artist_identity=identity,
        website_claim=claim_id,entity_revision=entity['lastrevid']) if value else None


async def artist_references(subject, question, locale, guard, *, identity, roles, topic):
    from .ask_dj import public_research as research
    sources=[]
    # Wiki resolution and the optional website share the same eight requests
    # and original twelve-second deadline, including all identity/robots work.
    try:
        async with asyncio.timeout(12):
            async with research.PublicFetch(guard) as fetch:
                sources,_=await research.research(subject,question,locale,guard,
                    qualified_music=True,expected_roles=roles,expected_entity_id=identity[4],
                    allow_web=False,fetch=fetch,original_paragraphs=True,story_topic=topic)
                if sources:
                    try:
                        extra=await website_reference(fetch,identity,topic)
                        if extra:
                            # Keep the preferred locale's exact-QID reference
                            # and one independent publisher. The original
                            # three-source claim cap also includes the CC0 seed.
                            sources=[sources[0],extra]
                    except PermissionError:
                        raise
                    except (research.ResearchUnavailable,OSError,TimeoutError,ValueError,TypeError,AttributeError,KeyError):
                        pass
    except TimeoutError:
        pass
    await guard()
    return sources
