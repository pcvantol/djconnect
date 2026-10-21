"""Pure source/purpose qualification within the existing passive projection.

No research, narration, state mutation or second opportunity/Planner.
"""
from datetime import datetime
import math
import re
import time
from urllib.parse import parse_qs, unquote, urlsplit


SOURCE_FIELDS = {'provider', 'title', 'url', 'kind', 'language', 'fetched_at',
                 'expires_at', 'license', 'revision_url', 'wikidata_id',
                 'content_hash', 'claim_scope'}
WIKIPEDIA_HOSTS = {f'{language}.wikipedia.org' for language in ('en', 'nl', 'de', 'fr', 'es')}


def status(reason, state='unavailable'):
    return {'state': state, 'reason': reason}


def researched_sources(moment, now):
    """Sealed full copy plus EACH source's explicit passive-purpose policy."""
    from .public_artist_narration import admitted, sources_for
    from .ask_dj.public_research import public_url
    if not admitted(moment, now):
        return None
    sources = sources_for(moment)
    if not 1 <= len(sources) <= 3:
        return None
    wikipedia = False
    for source in sources:
        if (not isinstance(source, dict) or set(source) != SOURCE_FIELDS
                or source.get('kind') != 'source' or not public_url(source.get('url'))
                or source.get('language') not in {'en', 'nl', 'de', 'fr', 'es'}
                or not isinstance(source.get('title'), str) or not source['title']
                or source.get('claim_scope') != 'fetched_public_music_reference'
                or not re.fullmatch('[0-9a-f]{64}', source.get('content_hash', ''))):
            return None
        try:
            expiry = datetime.fromisoformat(source['expires_at'])
            if expiry.tzinfo is None or not time.time() < expiry.timestamp():
                return None
            url = urlsplit(source['url'])
            if source['provider'] == 'Wikipedia' and source['license'] == 'CC-BY-SA-4.0':
                if not public_url(source['revision_url']):
                    return None
                revision = urlsplit(source['revision_url'])
                query = parse_qs(revision.query)
                if (url.hostname not in WIKIPEDIA_HOSTS or not url.path.startswith('/wiki/')
                        or revision.hostname != url.hostname or revision.path != '/w/index.php'
                        or not re.fullmatch('[1-9][0-9]*', query.get('oldid', [''])[0])
                        or unquote(url.path[6:]).replace('_', ' ') != source['title'].replace('_', ' ')
                        or ('title' in query and query['title'] != [source['title']])):
                    return None
                wikipedia = True
            elif source['provider'] in {'MusicBrainz', 'Wikidata'} and source['license'] == 'CC0-1.0':
                if not (re.fullmatch(r'https://musicbrainz\.org/(artist|recording|release-group)/[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', source['url'])
                        if source['provider'] == 'MusicBrainz' else
                        re.fullmatch(r'https://www\.wikidata\.org/wiki/Q[1-9][0-9]*', source['url'])):
                    return None
            else:
                return None  # Generic web references have no passive-purpose permission.
        except (ValueError, TypeError, KeyError, OverflowError):
            return None
    return sources if wikipedia else None


def contribution(broadcast, now, *, projection_version=1):
    """Select the original newest eligible publication; Silence is a barrier."""
    if broadcast.content_pending or broadcast.content_current_withdrawn:
        return None, status('source_not_qualified')
    if broadcast.state.selected_presence == 'music_only':
        return None, status('presence_music_only', 'suppressed')
    admissions = {a['moment_id']: a for a in broadcast.native_delivery()['admissions']}
    reason = None
    for moment in reversed(broadcast.state.dj_moments):
        if moment.moment_type.value == 'silence':
            return None, status('intentional_silence', 'suppressed')
        admission = admissions.get(moment.moment_id, {})
        boundary = broadcast._moment_delivery_boundaries.get(moment.moment_id)
        if (not boundary or admission.get('qualification') != 'qualified'
                or not (admission.get('current_display_allowed') or admission.get('active_flow_display_allowed'))
                or moment.presentation_intent.visibility.value == 'owner_only' or not moment.content):
            reason = reason or ('original_deadline_expired' if admission.get('qualification') == 'expired'
                                else 'source_not_qualified')
            continue
        if len(moment.content) > 640:
            reason = reason or 'copy_too_long'
            continue
        from .public_artist_narration import ResearchMomentAcceptance
        researched = type(moment.narration_acceptance) is ResearchMomentAcceptance
        sources = None
        if researched:
            if projection_version == 1:
                reason = reason or 'representation_not_supported'
                continue
            sources = researched_sources(moment, now)
            if sources is None:
                reason = reason or 'source_not_qualified'
                continue
        fact = moment.source_fact
        cc0 = not researched and fact is not None and fact.provider in {'MusicBrainz', 'Wikidata'} and fact.license == 'CC0-1.0'
        authored = fact is None and moment.source_references == ('session_direction',)
        if not (cc0 or authored or sources):
            reason = reason or 'source_not_qualified'
            continue
        try:
            deadline = datetime.fromisoformat(admission['display_expires_at'])
            valid = (deadline.tzinfo is not None and math.isfinite(now)
                     and boundary.published_monotonic <= now < boundary.published_monotonic + min(
                         120, moment.presentation_intent.maximum_duration_seconds)
                     and time.time() < deadline.timestamp())
        except (TypeError, ValueError, KeyError, OverflowError):
            valid = False
        if not valid:
            reason = reason or 'original_deadline_expired'
            continue
        body = {'moment_id': moment.moment_id, 'published_at': boundary.published_at,
                'text': moment.content, 'persona': moment.presentation_intent.dj_persona.value,
                'source_attribution': dict(moment.source_attribution),
                'usage_basis': ('public_artist_narration_v1' if sources else
                    'cc0_facts_authored_expression' if cc0 else 'runtime_authored_direction'),
                'expires_at': deadline.isoformat()}
        if projection_version == 2:
            body['rights'] = {'passive_cache': True, 'os_snapshot': True,
                              'external_relay': False, 'watch_replication': False}
        if sources:
            body['sources'] = sources
            body['expression_license'] = {'id': 'CC-BY-SA-4.0',
                'url': 'https://creativecommons.org/licenses/by-sa/4.0/',
                'adapted': True, 'attribution_required': True}
        return body, status('qualified', 'available')
    return None, status(reason or 'no_publication')
