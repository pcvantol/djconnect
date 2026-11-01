"""Closed evidence receipts for band founding and explicit member accession.

This is a factual admission guard, never an input-intent parser. Unknown prose,
pronouns, chronology and inferred relationships stay unqualified. The ordinary
independent semantic and full-answer evidence review remains necessary.
"""
from __future__ import annotations

import re

SCHEMA = 'biographical_event_v1'
KEYS = {'schema','event','claim','actor','group','group_id','year','source_id','evidence_id','quote'}
_UNSAFE = re.compile(
    r'\b(?:not|never|no|niet|nooit|geen|nicht|nie|kein\w*|ne|pas|jamais|aucun\w*|nunca|jamás|'
    r'possibly|perhaps|reportedly|allegedly|might|may|wellicht|mogelijk|vermoedelijk|zou|zouden|'
    r'vielleicht|angeblich|soll|aurait|serait|probablement|habría|quizás|'
    r'before|after|until|but|although|voordat|nadat|totdat|maar|bevor|nachdem|aber|'
    r'avant|après|mais|antes|después|pero)\b', re.I)
_OTHER_EVENT = re.compile(
    r'\b(?:joined|left|released|recorded|produced|born|died|performed|toetred\w*|verliet|'
    r'uitgebracht|opgenomen|geboren|overleden|beigetreten|verließ|veröffentlicht|'
    r'rejoint|quitté|sorti|enregistré|unió|abandonó|lanzó|grabó)\b',re.I)
_FOUNDING = re.compile(r'\b(?:founded|formed|opgericht|gegründet|fondé|formé|fundó|fundad[oa]|formad[oa])\b',re.I)
_YEAR = re.compile(r'(?<!\d)(?:1[5-9]|20)\d{2}(?!\d)')
_NAME = r"[A-ZÀ-Ý][\wÀ-ÿ’'-]+(?: [A-ZÀ-Ý][\wÀ-ÿ’'-]+){1,4}"
_NOT_GROUP_IDENTITY = re.compile(
    r'\b(?:musician|singer|producer|composer|company|member|leader|label|album|song|'
    r'muzikant|zanger|componist|bedrijf|lid|musiker|sänger|komponist|unternehmen|mitglied|'
    r'musicien|chanteur|compositeur|entreprise|membre|músico|cantante|compositor|empresa|miembro|'
    r'in|of|with|to|from|van|met|bij|von|mit|de|avec|dans|con)\b',re.I)


def _patterns(event, actor, group, year):
    a,g,y = map(re.escape,(actor,group,year))
    if event == 'member_joined':
        return (
            rf'{a} joined {g} in {y}',
            rf'{a} trad in {y} toe tot {g}',
            rf'{a} trad toe tot {g} in {y}',
            rf'{a} kwam in {y} bij {g}',
            rf'{a} sloot zich in {y} bij {g} aan',
            rf'{a} trat {g} im (?:Jahr )?{y} bei',
            rf'{a} schloss sich {g} im (?:Jahr )?{y} an',
            rf'{a} (?:a rejoint|rejoignit) {g} en {y}',
            rf'{a} se (?:unió|incorporó) a {g} en {y}',
        )
    if event != 'group_founded' or actor != group:
        return ()
    # Descriptive lead clauses may establish a founding date, not an extra
    # member/event. A location/founder suffix is never an additional fact grant.
    # Case-sensitive proper place words; sentence fragments and conjunctions
    # must not absorb another group's founding before the final year.
    word = r"[A-ZÀ-Ý][a-zà-ÿ]+(?:['’-][A-ZÀ-Ý]?[a-zà-ÿ]+)*"
    place = rf"(?-i:{word}(?:[ -]{word})*(?:, {word}(?:[ -]{word})*)*,?)"
    description = r'(?-i:(?:[A-ZÀ-Ý][a-zà-ÿ]+ )?(?:[a-zà-ÿ-]+ ){0,4})'
    return (
        rf'{g} was (?:founded|formed) in {y}',
        rf'{g} was an? {description}band (?:formed|founded) in (?:{place} in )?{y}',
        rf'{g} (?:werd|is) (?:in {y} opgericht|opgericht in {y})',
        rf'{g} was een {description}(?-i:[a-zà-ÿ-]*)(?:band|groep) die in {y} werd opgericht(?: in {place})?',
        rf'{g} wurde (?:im Jahr |im |){y} gegründet',
        rf'{g} a été (?:fondé|formé) en {y}',
        rf'{g} (?:se fundó|fue fundad[oa]|fue formad[oa]) en {y}',
    )


def matches(sentence, event, actor, group, year):
    """Two names and a date are insufficient; match the closed directed act."""
    if (not isinstance(sentence,str) or not 1 <= len(sentence) <= 1200
            or _UNSAFE.search(sentence) or _YEAR.findall(sentence) != [year]
            or sentence[-1:] != '.' or sentence != sentence.strip()):
        return False
    if event == 'group_founded' and (_OTHER_EVENT.search(sentence) or len(_FOUNDING.findall(sentence)) != 1):
        return False
    if event == 'member_joined' and (actor == group or not re.fullmatch(_NAME,actor)):
        return False
    return any(re.fullmatch(pattern+r'\.',sentence,re.I) for pattern in _patterns(event,actor,group,year))


def _group_source(source, group):
    from .public_research import MUSICAL_GROUP, _sentences
    excerpt = source.get('untrusted_excerpt','')
    sentences = _sentences(excerpt) if isinstance(excerpt,str) else []
    if not (source.get('provider') == 'Wikipedia'
        and re.fullmatch(r'Q[1-9][0-9]*',str(source.get('wikidata_id','')))
        and sentences and re.match(re.escape(group)+r'(?!\w)',sentences[0],re.I)):
        return False
    identity=sentences[0][len(group):]
    noun=MUSICAL_GROUP.search(identity)
    if noun is None:
        return False
    head=identity[:noun.start()]
    return bool(re.match(r'\s+(?:is|was|are|were|ist|war|sind|waren|est|était|sont|étaient|es|fue|son|era)\s+',head,re.I)
        and not _NOT_GROUP_IDENTITY.search(head))


def validate(receipt, answer, research):
    """Return one exact covered sentence/year, or no temporal admission."""
    from .public_research import _sentences, evidence_spans
    if (not isinstance(receipt,dict) or set(receipt) != KEYS
            or any(not isinstance(v,str) or not 1 <= len(v) <= 1200 for v in receipt.values())
            or receipt['schema'] != SCHEMA
            or receipt['event'] not in {'group_founded','member_joined'}
            or receipt['group'] != research.get('resolved_public_subject')
            or not 2 <= len(receipt['group']) <= 120
            or not _YEAR.fullmatch(receipt['year'])
            or not re.fullmatch(r'[0-9a-f]{64}',receipt['source_id'])
            or receipt['claim'] not in _sentences(answer)):
        return None
    source = next((s for s in research.get('sources',[]) if isinstance(s,dict)
        and s.get('content_hash') == receipt['source_id']),None)
    if (source is None or not _group_source(source,receipt['group'])
            or receipt['group_id'] != source.get('wikidata_id')
            or receipt['quote'] not in _sentences(source['untrusted_excerpt'])
            or not any(span['id'] == receipt['evidence_id'] and receipt['quote'] in span['text']
                       for span in evidence_spans(source))):
        return None
    if not all(matches(text,receipt['event'],receipt['actor'],receipt['group'],receipt['year'])
               for text in (receipt['quote'],receipt['claim'])):
        return None
    return receipt['claim'],receipt['year']


def candidates(research):
    """Value-only proofs for the model to copy; no new lookup or authored fact."""
    from .public_research import _sentences, evidence_spans
    group = research.get('resolved_public_subject')
    if not isinstance(group,str) or not 2 <= len(group) <= 120:
        return []
    result=[]
    for source in research.get('sources',[]):
        if not isinstance(source,dict) or not _group_source(source,group):
            continue
        for span in evidence_spans(source):
            for quote in _sentences(span['text']):
                years=_YEAR.findall(quote)
                if len(years) != 1:
                    continue
                year=years[0]
                options=[('group_founded',group)]
                # Only explicit complete names, never a source pronoun or an
                # inferred full name. Final directed-act matching is decisive.
                match=re.match('('+_NAME+r')\b',quote)
                if match:
                    options.append(('member_joined',match[1]))
                for event,actor in options:
                    if matches(quote,event,actor,group,year):
                        receipt=dict(schema=SCHEMA,event=event,claim=quote,actor=actor,group=group,
                            group_id=source['wikidata_id'],year=year,source_id=source['content_hash'],
                            evidence_id=span['id'],quote=quote)
                        if validate(receipt,quote,research) is not None:
                            result.append({k:v for k,v in receipt.items() if k != 'claim'})
                        if len(result) >= 8:
                            return result
    return result
