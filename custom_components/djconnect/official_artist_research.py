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


async def website_reference(fetch, identity, topic):
    from .ask_dj.public_research import PageText, MUSIC, public_url, _source
    from .session_story_variety import passage_score
    if (type(identity) is not tuple or len(identity)!=5 or identity[0]!='artist'
            or identity[3] not in {'Group','Person'}
            or not re.fullmatch(r'Q[1-9][0-9]*',identity[4])
            or fetch.maximum_requests-fetch.requests<3):
        return None
    qid,subject=identity[4],identity[2]
    status,body,_=await fetch.request('https://www.wikidata.org/w/api.php?'+urlencode({
        'action':'wbgetentities','ids':qid,'props':'claims','format':'json'}))
    data=json.loads(body) if status==200 else {}
    entity=data.get('entities',{}).get(qid,{})
    if (entity.get('id')!=qid or type(entity.get('lastrevid')) is not int
            or not 0<entity['lastrevid']<=9_007_199_254_740_991):
        return None
    candidates=[]
    for claim in entity.get('claims',{}).get('P856',[]):
        snak=claim.get('mainsnak',{})
        value=snak.get('datavalue',{}).get('value')
        if (claim.get('rank') not in {'normal','preferred'} or claim.get('qualifiers')
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
