"""Editorial variety from published Flow only; never new factual authority.

No opportunity, source cache, transport, timer or parallel history is owned here.
"""
import hashlib
import re

TOPICS = ('live_performance', 'members', 'recording', 'background')
PURPOSES = {
    'live_performance': 'Tell one documented episode at a named concert, festival or live performance.',
    'members': 'Tell one documented activity or meeting involving the band members, with their actual roles.',
    'recording': 'Tell one documented recording or creative episode on a named musical work.',
    'background': 'Tell one documented episode in the artist history beyond a date, description or credit list.',
}
# Retrieval hints only. They select original passages, not a claim or an input
# intent. Semantic topic fit and complete evidence review are still required.
HINTS = {
    'live_performance': r'concert\w*|festival\w*|performed|performance|live|optreden\w*|auftritt\w*|aufgetreten|scène|concierto\w*|actuaci[oó]n',
    'members': r'member\w*|joined|met|bandleden|ontmoet\w*|lid|mitglieder\w*|membre\w*|rejoint|miembro\w*|conoci[oó]',
    'recording': r'record\w*|studio\w*|opnam\w*|aufnahm\w*|enregistr\w*|grab\w*',
    'background': r'formed|founded|began|naam|opgericht|begon|gegr[uü]ndet|fond[ée]\w*|form[oó]|fund[oó]',
}


def passage_score(text, topic):
    score = min(16, len(re.findall(r'\b(?:'+HINTS[topic]+r')\b', text, re.I))) if topic in HINTS else 0
    if topic == 'live_performance' and score and re.search(
            r'\b(?:concert\w*|festival\w*|stage|podium|scène|bühne)\b', text, re.I) and re.search(
            r'\b(?:performed|played|appeared|opgetreden|speelde|aufgetreten|spielte|joua\w*|actu[oó]\w*|toc[oó]\w*)\b', text, re.I):
        # An actual event/action outranks a list of live-album/DVD releases.
        score += 20
    return score


def span_key(text):
    return hashlib.sha256(' '.join(text.casefold().split()).encode()).hexdigest()


def subject_id(fact):
    identity = getattr(fact, 'artwork_artist_identity', None)
    if identity is not None and identity.eligible():
        return identity.wikidata_id
    qid = getattr(fact, 'public_artist_qid', '')
    return qid if isinstance(qid, str) and re.fullmatch(r'Q[1-9][0-9]*', qid) else ''


def fact_topic(fact):
    key = getattr(fact, 'key', '')
    subject = subject_id(fact)
    if not subject:
        return None
    family = 'credits' if key in {'recording_credits', 'work_composers'} else key
    return (subject, family)


def credit_cooldown(fact, recent):
    topic = fact_topic(fact)
    return bool(topic and topic[1] == 'credits' and topic in recent[-3:])


def published_context(moments, qid):
    """Only sealed, actually published public artist stories, at most eight.

    Text is already public-evidence-bound DJ prose, not user chat, playback
    metadata, DNA or a copied source corpus. The caller supplies published Flow.
    """
    from .public_artist_narration import artist_story_memory
    rows = []
    for moment in moments:
        accepted = artist_story_memory(moment)
        if accepted is not None and accepted.subject_identity[4] == qid:
            rows.append((accepted.editorial_topic, accepted.text, accepted.episode_keys))
    return tuple(rows[-8:])


def next_topic(previous):
    used = [row[0] for row in previous if row[0] in TOPICS]
    return min(TOPICS, key=lambda topic: (used.count(topic),
        max((len(used)-i for i, value in enumerate(used) if value == topic), default=len(used)+1) * -1,
        TOPICS.index(topic)))


def select_focus(projection, topic, previous):
    from .ask_dj.public_research import evidence_spans
    used = {key for row in previous for key in row[2]}
    choices = []
    for order, source in enumerate(projection.get('sources', [])):
        if source.get('provider') != 'Wikipedia':
            continue
        for index, span in enumerate(evidence_spans(source)):
            key = span_key(span['text'])
            # Retrieval words also occur in reference/link labels. A complete
            # sentence is a minimum focus requirement, not semantic episode
            # qualification; the full original corpus and model review remain.
            complete = re.search(r'[.!?][\"\x27’”»\)\]]*$', span['text'].rstrip())
            if complete and key not in used and passage_score(span['text'], topic):
                choices.append((passage_score(span['text'], topic), index > 0, source.get('language') == 'en', -order, -index, source, span))
    if not choices:
        return None
    *_, source, span = max(choices, key=lambda row: row[:-2])
    return {'kind': 'documented_artist_topic', 'topic': topic,
        'source_id': source['content_hash'], 'episode_span_ids': [span['id']],
        'authority': 'telling_focus_only_full_original_context_remains_evidence'}


def reviewed_episode(review, projection, focus, previous):
    """Actual focused claim receipts plus semantic novelty, not model booleans alone."""
    from .ask_dj.public_research import evidence_spans
    if (not focus or review.get('topic_preserved') is not True
            or review.get('novel_episode') is not True):
        return ()
    spans = {s['id']: s['text'] for source in projection['sources']
             if source.get('provider') == 'Wikipedia' for s in evidence_spans(source)}
    keys = tuple(dict.fromkeys(span_key(spans[i]) for c in review.get('claim_checks', [])
        if c.get('kind') in {'fact', 'relationship'} for i in c.get('evidence_ids', [])
        if i in focus['episode_span_ids'] and i in spans and c.get('quote') == spans[i]))
    used = {key for row in previous for key in row[2]}
    return keys if keys and not used.intersection(keys) else ()
