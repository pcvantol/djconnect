"""Exact public person dates and local calendar arithmetic, never model maths."""
import json
import re
from datetime import UTC, date, datetime
from urllib.parse import urlencode, urlsplit


class PublicDateConflict(Exception):
    """Original same-entity date evidence must not choose one side silently."""


def entity_url(qid, language):
    if not re.fullmatch(r'Q[1-9][0-9]*', str(qid)) or language not in {'en','nl','de','fr','es'}:
        return ''
    return 'https://www.wikidata.org/w/api.php?'+urlencode({
        'action':'wbgetentities', 'ids':qid, 'props':'claims|sitelinks',
        'sitefilter':language+'wiki', 'format':'json'})


def _date_claim(claims, property_id):
    rows = claims.get(property_id)
    if not isinstance(rows, list) or not rows:
        return None
    preferred = [row for row in rows if isinstance(row, dict) and row.get('rank') == 'preferred']
    rows = preferred or [row for row in rows if isinstance(row, dict) and row.get('rank') == 'normal']
    if len(rows) != 1 or rows[0].get('qualifiers'):
        return None
    snak = rows[0].get('mainsnak', {})
    value = snak.get('datavalue', {})
    if (snak.get('property') != property_id or snak.get('snaktype') != 'value'
            or snak.get('datatype') != 'time'
            or value.get('type') != 'time' or not isinstance(value.get('value'), dict)):
        return None
    value = value['value']
    if (any(type(value.get(key)) is not int for key in ('precision','before','after','timezone'))
            or value.get('precision') != 11 or value.get('before') != 0 or value.get('after') != 0
            or value.get('timezone') != 0
            or value.get('calendarmodel') != 'http://www.wikidata.org/entity/Q1985727'):
        return None
    match = re.fullmatch(r'\+(\d{4})-(\d{2})-(\d{2})T00:00:00Z', str(value.get('time')))
    if not match:
        return None
    try:
        return date(*map(int, match.groups()))
    except ValueError:
        return None


def linked_entity(sources, subject):
    """Shared exact reciprocal identity/expiry/duplicate-JSON boundary."""
    from .public_research import PublicSource
    wiki = [s for s in sources if type(s) is PublicSource and s.provider == 'Wikipedia' and s.entity_id]
    data = [s for s in sources if type(s) is PublicSource and s.provider == 'Wikidata']
    if not wiki or len(data) != 1:
        return None
    source = data[0]
    expected_url = entity_url(source.entity_id, source.language)
    if source.url != expected_url:
        return None
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate_public_date_field')
            result[key] = value
        return result
    try:
        if any(datetime.fromisoformat(s.expires_at) <= datetime.now(UTC) for s in wiki):
            return None
        if datetime.fromisoformat(source.expires_at) <= datetime.now(UTC):
            return None
        document = json.loads(source.text, object_pairs_hook=unique)
        entity = document['entities'][source.entity_id]
        if entity.get('id') != source.entity_id or entity.get('type') != 'item':
            return None
        linked = [s for s in wiki if s.entity_id == source.entity_id
                  and entity.get('sitelinks', {}).get(s.language+'wiki', {}).get('title') == s.title
                  and urlsplit(s.url).hostname == s.language+'.wikipedia.org']
        if not linked or len({s.entity_id for s in wiki}) != 1:
            return None
        if not any(s.title.casefold() == subject.casefold() for s in linked):
            return None
        return entity, linked
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, RecursionError):
        return None


def _age_answer(sources, subject, language, *, today=None):
    """One fresh reciprocal Wiki/QID person, exact Gregorian birthday/death.

    Incomplete dates, conflicting statements, groups and unknown death claims
    stay in the ordinary evidence-reviewed research route.
    """
    today = today or datetime.now(UTC).date()
    bound = linked_entity(sources, subject)
    if bound is None:
        return None
    entity, linked = bound
    try:
        claims = entity['claims']
        kinds = claims.get('P31', [])
        if not isinstance(kinds, list) or not kinds:
            return None
        for row in kinds:
            snak = row.get('mainsnak', {})
            value = snak.get('datavalue', {})
            if (row.get('rank') not in {'normal', 'preferred'} or row.get('qualifiers')
                    or snak.get('property') != 'P31' or snak.get('snaktype') != 'value'
                    or snak.get('datatype') != 'wikibase-item'
                    or value.get('type') != 'wikibase-entityid'
                    or value.get('value') != {'entity-type':'item', 'numeric-id':5, 'id':'Q5'}
                    or type(value['value']['numeric-id']) is not int):
                return None
        born = _date_claim(claims, 'P569')
        died = _date_claim(claims, 'P570') if 'P570' in claims else None
        if born is None or ('P570' in claims and died is None):
            return None
        # A missing death property is not evidence of life. Require consistent
        # freshly read person prose too; explicit death or past-tense identity
        # cannot be silently discarded in favour of an incomplete date record.
        from .public_research import _sentences
        leads = [(_sentences(s.text) or [''])[0] for s in linked]
        death_words = re.compile(r'\b(?:died|dead|overleden|gestorven|verstorben|starb|mort|morte|décédé|falleció|fallecido|murió)\b', re.I)
        present = re.compile(r'\b(?:is|ist|est|es)\s+(?:an?|een|ein(?:e[rsnm]?)?|un(?:e|a|o)?)\b', re.I)
        past = re.compile(r'\b(?:was|war|était|fue|era)\s+(?:an?|een|ein(?:e[rsnm]?)?|un(?:e|a|o)?)\b', re.I)
        if died is None:
            if (any(death_words.search(s.text) for s in linked)
                    or any(past.search(lead) or not present.search(lead) for lead in leads)):
                return None
        elif any(present.search(lead) and not death_words.search(s.text)
                 for s, lead in zip(linked, leads, strict=True)):
            return None
        for source in linked:
            for sentence in _sentences(source.text):
                if re.search(r'\b(?:born|geboren|geborene|né|née|nació|nacido|nacida)\b', sentence, re.I):
                    years = re.findall(r'(?<!\d)(?:1[5-9]|20)\d{2}(?!\d)', sentence)
                    if any(int(year) != born.year for year in years):
                        raise PublicDateConflict()
        end = died or today
        if not born <= end <= today:
            return None
        age = end.year-born.year-((end.month, end.day) < (born.month, born.day))
        if not 0 <= age <= 125:
            return None
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, RecursionError):
        return None
    live = {
        'nl': '{name} is {age} jaar oud.', 'en': '{name} is {age} years old.',
        'de': '{name} ist {age} Jahre alt.', 'fr': '{name} a {age} ans.',
        'es': '{name} tiene {age} años.',
    }
    deceased = {
        'nl': '{name} is {age} jaar geworden.', 'en': '{name} was {age} years old when they died.',
        'de': '{name} wurde {age} Jahre alt.', 'fr': '{name} avait {age} ans à sa mort.',
        'es': '{name} tenía {age} años cuando falleció.',
    }
    return (deceased if died else live).get(language, live['en']).format(name=linked[0].title, age=age)


def age_answer(sources, subject, language, *, today=None):
    """A conflict never becomes an accepted deterministic answer."""
    try:
        return _age_answer(sources, subject, language, today=today)
    except PublicDateConflict:
        return None
