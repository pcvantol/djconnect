"""Bounded occurrence/preparation data for the existing Session/Planner owner.

No listener, timer, provider, playback command or second publication path lives
here. Queue slots remain private hints; only an actual playing sample can mint
an occurrence. Catalog values never enter the model frame projection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from datetime import datetime, UTC
import re
from typing import Callable
from uuid import uuid4

START_WINDOW_SECONDS = 12.0
PREPARATION_TTL_SECONDS = 30.0
MAX_PREPARED = 3
LABELS = dict(zip(('en', 'nl', 'de', 'fr', 'es'), (
    'Music announcement', 'Muziek aankondiging', 'Musikankündigung',
    'Annonce musicale', 'Anuncio musical')))
TRACK_URI = re.compile(r'spotify:track:[A-Za-z0-9]{22}')
ALBUM_URI = re.compile(r'spotify:album:[A-Za-z0-9]{22}')


def safe_label(value):
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= 512
            and all(ord(c) >= 32 and ord(c) != 127 for c in value))


@dataclass(frozen=True)
class Occurrence:
    occurrence_id: str
    media_uri: str
    title: str
    artist: str
    album_uri: str
    observed_at: float
    deadline: float
    source_context: tuple
    duration_ms: int | None = None
    repeated: bool = False

    @property
    def item_id(self):
        return hashlib.sha256(self.media_uri.encode()).hexdigest()[:24]

    def current(self, now):
        return self.observed_at <= now < self.deadline


@dataclass(frozen=True)
class PreparedIntro:
    """No future occurrence ID or publication. Duplicate queue slots stay distinct."""
    media_uri: str
    queue_slot: int
    queue_revision: str
    settings_context: tuple
    source_context: tuple
    frame: str
    prepared_at: float
    expires_at: float
    authorize: Callable[[], bool] = field(repr=False, compare=False)

    def valid(self, now, *, settings_context, source_context, queue_revision):
        return (self.prepared_at <= now < self.expires_at and self.authorize() is True
                and self.settings_context == settings_context
                and self.source_context == source_context and self.queue_revision == queue_revision)


@dataclass
class AnnouncementState:
    """One existing Session's RAM state, discarded with that Session."""
    clock: Callable[[], float]
    media_uri: str = ''
    position_ms: int | None = None
    duration_ms: int | None = None
    sample_at: float | None = None
    sample_state: str = ''
    current_occurrence: Occurrence | None = None
    attempted_id: str = ''
    published_id: str = ''
    recent_frames: tuple[str, ...] = ()
    preparations: tuple[PreparedIntro, ...] = ()
    queue_revision: str = ''
    source_context: tuple = ()
    generation_attempts: int = 0
    generated: int = 0
    degraded: int = 0
    last_completed_at: float | None = None
    preparing: bool = False
    preparation_attempt: tuple = ()
    selected_prepared: PreparedIntro | None = None
    missed_reasons: dict[str, int] = field(default_factory=dict)

    def observe(self, *, state, media_uri, title, artist, album_uri='',
                position_ms=None, duration_ms=None, source_context=(), authorize,
                deliberate_restart=False):
        """One accepted provider sample; seek/pause/reconnect are not new starts.

        A same-recording natural restart needs a recently observed playing tail,
        sufficient elapsed time to cross the end, and a fresh start position.
        Explicit restart is supplied only by the existing confirmed command owner.
        Ambiguous/unobserved seeks never mint a guessed future occurrence.
        """
        now = self.clock()
        if authorize() is not True:
            self.preparations = ()
            return None
        position = position_ms if type(position_ms) is int and position_ms >= 0 else None
        duration = duration_ms if type(duration_ms) is int and duration_ms > 0 else None
        playing = (state == 'playing' and isinstance(media_uri, str)
                   and TRACK_URI.fullmatch(media_uri) and safe_label(title) and safe_label(artist))
        same = media_uri == self.media_uri
        elapsed = now - self.sample_at if self.sample_at is not None else None
        natural_restart = bool(same and playing and self.sample_state == 'playing'
            and elapsed is not None and 0 < elapsed <= 15 and position is not None and position <= 4000
            and self.position_ms is not None and self.duration_ms is not None
            and self.duration_ms - self.position_ms <= 4000
            and self.position_ms + elapsed * 1000 >= self.duration_ms
            and self.position_ms - position > 4000)
        new = playing and (not same or natural_restart or deliberate_restart)
        if self.source_context != source_context:
            self.preparations = ()
            self.source_context = source_context
        self.sample_at, self.sample_state = now, state
        self.position_ms, self.duration_ms = position, duration
        if not playing:
            return None
        self.media_uri = media_uri
        if not new:
            return None
        self.current_occurrence = None
        if position is None or position > START_WINDOW_SECONDS * 1000:
            self.miss('start_window_already_elapsed')
            return None
        # Provider music continues independently; elapsed track time shortens the
        # single original automatic deadline, it never resets it on a later poll.
        occurrence = Occurrence('occurrence-' + uuid4().hex, media_uri, title, artist,
            album_uri if ALBUM_URI.fullmatch(album_uri or '') else '', now,
            now + START_WINDOW_SECONDS - position / 1000, source_context, duration,
            repeated=same and (natural_restart or deliberate_restart))
        self.current_occurrence = occurrence
        return occurrence

    def begin(self, occurrence):
        if (self.current_occurrence is not occurrence or not occurrence.current(self.clock())
                or self.attempted_id == occurrence.occurrence_id):
            return False
        self.attempted_id = occurrence.occurrence_id
        self.generation_attempts += 1
        return True

    def committed(self, occurrence, *, frame='', generated=False):
        if self.published_id == occurrence.occurrence_id:
            return False
        self.published_id = occurrence.occurrence_id
        if generated:
            self.generated += 1
            self.recent_frames = (*self.recent_frames, frame)[-8:]
        else:
            self.degraded += 1
        return True

    def miss(self, reason):
        # Fixed internal reasons only, never exception text, history or prompts.
        if reason in {'start_window_already_elapsed', 'context_changed', 'deadline',
                      'provider_unavailable', 'publication_unavailable'}:
            self.missed_reasons[reason] = self.missed_reasons.get(reason, 0) + 1

    def accept_preparations(self, queue_revision, candidates):
        self.queue_revision = queue_revision
        self.preparations = tuple(candidates[:MAX_PREPARED])

    def take_prepared(self, occurrence, settings_context):
        for index, candidate in enumerate(self.preparations):
            if (candidate.media_uri == occurrence.media_uri
                    and candidate.valid(self.clock(), settings_context=settings_context,
                        source_context=occurrence.source_context, queue_revision=self.queue_revision)):
                self.preparations = self.preparations[index + 1:]
                return candidate
        return None


@dataclass(frozen=True)
class Contribution:
    """Original recording/occurrence, plus its actual durable acceptance only.

    The start deadline is never an archive or manual-replay deadline. The latter
    is supplied by the existing repository after its real acceptance transaction.
    """
    occurrence: Occurrence
    locale: str
    settings_context: tuple
    generated: bool = False
    accepted_digest: str = ''
    retained_until: str = ''

    def data(self):
        return {'schema_version': 1, 'occurrence_id': self.occurrence.occurrence_id,
                'media_uri': self.occurrence.media_uri, 'title': self.occurrence.title,
                'artist': self.occurrence.artist, 'album_uri': self.occurrence.album_uri,
                'realization': 'generated' if self.generated else 'degraded',
                'automatic_deadline_seconds': START_WINDOW_SECONDS}


def contribution(moment):
    value = getattr(moment, 'track_announcement', None)
    if (type(value) is Contribution and moment.moment_type.value == 'music_announcement'
            and moment.knowledge_intent.intent_type.value == 'track_context'
            and moment.source_references == ('spotify_playback_status',)
            and dict(moment.source_attribution) == {'provider': 'Spotify',
                'url': 'https://open.spotify.com/track/' + value.occurrence.media_uri.rsplit(':', 1)[1],
                'license': 'Spotify-Policy'}):
        return value
    return None


def accepted(moment):
    value = contribution(moment)
    return bool(value is not None and value.accepted_digest
        and value.accepted_digest == acceptance_digest(moment))


def acceptance_digest(moment):
    """Bind the accepted original, never just its text or an expiring URL."""
    value = contribution(moment)
    if value is None:
        return ''
    payload = [moment.moment_id, moment.session_id, moment.created_at,
        moment.moment_type.value, moment.title, moment.summary, moment.content,
        moment.presentation_intent.dj_persona.value, moment.presentation_intent.source_session_mood,
        moment.source_attribution, value.data(), value.occurrence.observed_at,
        value.occurrence.deadline, value.occurrence.source_context, value.occurrence.duration_ms,
        value.locale, value.settings_context, value.retained_until]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def retained(moment):
    value = contribution(moment)
    if not accepted(moment) or not value.retained_until:
        return False
    try:
        return datetime.fromisoformat(value.retained_until) > datetime.now(UTC)
    except (TypeError, ValueError):
        return False


_FALLBACK_INTROS = {
    'en': {
        'home_dj': 'Settle in and give this one a little room.',
        'radio_dj': 'Stay with me for the next few minutes.',
        'club_dj': 'Your floor now. Find your own way into it.',
        'festival_dj': 'Make a little space and take this moment in.',
    },
    'nl': {
        'home_dj': 'Ga er even goed voor zitten en geef dit nummer de ruimte.',
        'radio_dj': 'Blijf nog even bij me voor de komende minuten.',
        'club_dj': 'De vloer is van jou. Beweeg op je eigen manier.',
        'festival_dj': 'Maak wat ruimte en neem dit moment helemaal in je op.',
    },
    'de': {
        'home_dj': 'Mach es dir bequem und gib diesem Stück etwas Raum.',
        'radio_dj': 'Bleib noch ein paar Minuten bei mir.',
        'club_dj': 'Die Tanzfläche gehört dir. Beweg dich, wie du magst.',
        'festival_dj': 'Mach ein bisschen Platz und genieß diesen Moment.',
    },
    'fr': {
        'home_dj': 'Installe-toi et laisse un peu de place à ce morceau.',
        'radio_dj': 'Reste encore quelques minutes avec moi.',
        'club_dj': 'La piste est à toi. Bouge comme tu en as envie.',
        'festival_dj': 'Fais un peu de place et profite de ce moment.',
    },
    'es': {
        'home_dj': 'Ponte a gusto y dale un poco de espacio a este tema.',
        'radio_dj': 'Quédate conmigo unos minutos más.',
        'club_dj': 'La pista es tuya. Muévete a tu manera.',
        'festival_dj': 'Haz un poco de espacio y disfruta de este momento.',
    },
}


def fallback(occurrence, locale, persona):
    intro = _FALLBACK_INTROS[locale][persona]
    return f'{intro} {occurrence.title} — {occurrence.artist}.'


def capture(manager, *, owner_profile_id, session_id, observed, authorize):
    """Called only by the existing canonical observer, after its accepted sample."""
    active = manager.current_active(owner_profile_id)
    registration = manager._narration_providers.get(owner_profile_id)
    if (active is None or active.session_id != session_id or registration is None
            or registration[0] != session_id or authorize() is not True):
        return None
    source = manager._history_source_contexts.get(session_id, {})
    if not all(isinstance(source.get(k), str) and source[k] for k in (
            'backend_id', 'music_account_id', 'provider_entry_id', 'provider_account_id')):
        return None
    state = getattr(active.broadcast, 'track_announcements', None)
    if state is None:
        state = AnnouncementState(manager._monotonic_source)
        active.broadcast.track_announcements = state
    catalog = getattr(observed, 'catalog', {}) or {}
    occurrence = state.observe(state=observed.state, media_uri=observed.media_identity,
        title=observed.title, artist=observed.artist, position_ms=observed.position_ms,
        duration_ms=observed.duration_ms, album_uri=catalog.get('album_uri', ''),
        source_context=(*sorted(source.items()), ('output_id', getattr(observed, 'target_id', ''))),
        authorize=authorize)
    if occurrence is not None:
        state.selected_prepared = state.take_prepared(occurrence, text_context(active))
    return occurrence


def text_context(active):
    """Voice/output choices do not alter an already prepared value-free text."""
    return (active.session_id, active.owner_profile_id, active.locale,
            active.selected_mood, active.dj_persona.value)


async def prepare_next(manager, *, owner_profile_id, session_id, observed, preview, authorize):
    """One private near-end queue hint through the existing qualified realizer.

    No Moment, occurrence, Planner entry, archive, audio or publication is created.
    One attempt per actual queue/source/text context, no retry loop on reads.
    """
    import asyncio
    from .narration_brief import PreparedNarrationBrief, NarratedText, candidate
    active = manager.current_active(owner_profile_id)
    registration = manager._narration_providers.get(owner_profile_id)
    state = active.broadcast.track_announcements if active is not None else None
    candidates = preview.get('_announcement_candidates') if isinstance(preview, dict) else None
    revision = hashlib.sha256(json.dumps(candidates[:3], sort_keys=True).encode()).hexdigest() if candidates else ''
    if state is not None and state.queue_revision and state.queue_revision != revision:
        state.preparations = ()
        state.queue_revision = revision
    if (active is None or active.session_id != session_id or registration is None
            or registration[0] != session_id or observed.state != 'playing'
            or type(observed.position_ms) is not int or type(observed.duration_ms) is not int
            or not 0 < observed.duration_ms-observed.position_ms <= 20000):
        return
    deadline = preview.get('deadline') if isinstance(preview, dict) else None
    if (state is None or state.preparing or not candidates or not isinstance(deadline, (int, float))
            or deadline <= manager._monotonic_source() or authorize() is not True):
        return
    row = candidates[0]  # A bounded window of one; no speculative bulk/audio.
    if not isinstance(row, dict) or not TRACK_URI.fullmatch(str(row.get('uri', ''))):
        return
    context, source = text_context(active), state.source_context
    attempt = (revision, context, source)
    if state.preparation_attempt == attempt:
        return
    state.preparation_attempt, state.preparing = attempt, True
    source_guard = registration[3]() if registration[3] is not None else registration[2]
    def guard():
        source_guard()
        current = manager.current_active(owner_profile_id)
        if (current is None or current.broadcast is not active.broadcast
                or text_context(current) != context or state.source_context != source
                or state.preparation_attempt != attempt or authorize() is not True
                or manager._monotonic_source() >= deadline
                or manager._narration_providers.get(owner_profile_id) is not registration):
            raise PermissionError('queue_preparation_changed')
    try:
        # Fact remains absent: a queue position must never masquerade as a
        # playing recording or a future occurrence. Values remain local.
        brief = PreparedNarrationBrief(None, active.locale, active.dj_persona.value, active.selected_mood,
            '', ('{track}', '{artist}'),
            'One short subjective invitation; no sound claim, music fact, memory, selection or playback claim.',
            'Private queue hint only. This recording has NOT started and no publication is authorized.',
            (('{track}', ''), ('{artist}', '')), recent_frames=state.recent_frames,
            kind='music_announcement', preparation_guard=guard)
        async with asyncio.timeout(min(6, deadline-manager._monotonic_source())):
            text = await registration[1](brief, guard)
        guard()
        frame = candidate(brief, json.dumps({'text': text.frame})) if type(text) is NarratedText else None
        if frame is not None and len(frame) <= 320:
            now = manager._monotonic_source()
            state.accept_preparations(revision, [PreparedIntro(row['uri'], 0, revision,
                context, source, frame, now, min(deadline, now+PREPARATION_TTL_SECONDS),
                lambda: preparation_current(guard))])
    except (PermissionError, TimeoutError, ValueError, TypeError):
        return
    finally:
        state.preparing = False


def preparation_current(guard):
    try:
        guard()
        return True
    except PermissionError:
        return False


async def publish(manager, *, owner_profile_id, session_id, occurrence, authorize):
    """One normal Planner/publication transaction, never a second engine."""
    import asyncio
    import time
    from dataclasses import replace
    from .current_track_insight import session_scope
    from .session_runtime import (DJMoment, DJMomentType, KnowledgeIntent, KnowledgeIntentType,
        SessionFlowPosition, _presentation_intent, _timestamp)
    from .narration_brief import RuntimeNarrationAcceptance
    active = manager.current_active(owner_profile_id)
    if active is None or active.session_id != session_id or occurrence is None:
        return None
    state = active.broadcast.track_announcements
    if not state.begin(occurrence):
        return None
    scope = session_scope(active)
    epoch = active.broadcast.content_epoch
    registration = manager._narration_providers.get(owner_profile_id)
    if registration is None or registration[0] != session_id:
        state.miss('provider_unavailable')
        return None
    source_guard = registration[3]() if registration[3] is not None else registration[2]
    def guard():
        source_guard()
        current = manager.current_active(owner_profile_id)
        if (current is None or session_scope(current) != scope or current.broadcast.content_epoch != epoch
                or current.broadcast.content_pending or current.broadcast.track_announcements is not state
                or state.current_occurrence is not occurrence or authorize() is not True
                or not occurrence.current(manager._monotonic_source())
                or current.broadcast.state.playback.state != 'playing'
                or current.broadcast.state.playback.item_id != occurrence.item_id):
            raise PermissionError('announcement_context_changed')
    try:
        guard()
        value = Contribution(occurrence, active.locale, scope)
        content = fallback(occurrence, active.locale, active.dj_persona.value)
        seed = DJMoment(moment_id='moment-'+uuid4().hex, session_id=session_id, created_at=_timestamp(),
            moment_type=DJMomentType.MUSIC_ANNOUNCEMENT,
            knowledge_intent=KnowledgeIntent(KnowledgeIntentType.TRACK_CONTEXT,
                'Introduce this actually started recording.', occurrence.item_id),
            presentation_intent=_presentation_intent(active.selected_mood, active.dj_persona,
                reading_characters=len(content), minimum_duration_seconds=6),
            title=LABELS[active.locale], summary=occurrence.title+' — '+occurrence.artist,
            content=content, artwork_url=None, actions=(), source_references=('spotify_playback_status',),
            source_attribution=(('provider','Spotify'),('url','https://open.spotify.com/track/'+occurrence.media_uri.rsplit(':',1)[1]),
                                ('license','Spotify-Policy')),
            generation_metadata=(('context_source','track_start_announcement'),
                ('occurrence_id',occurrence.occurrence_id),('realization','degraded')),
            track_announcement=value)
        # The existing expressive realizer and its independent reviewer receive
        # placeholders only. Text delivery never waits for audio synthesis.
        prepared = state.selected_prepared
        if prepared is not None and prepared.valid(manager._monotonic_source(),
                settings_context=text_context(active), source_context=occurrence.source_context,
                queue_revision=state.queue_revision):
            from .narration_brief import qualify_runtime_moment
            brief = qualify_runtime_moment(seed, locale=active.locale)
            text = brief.render(prepared.frame)
            moment = replace(seed, content=text,
                presentation_intent=_presentation_intent(active.selected_mood, active.dj_persona,
                    reading_characters=len(text), minimum_duration_seconds=6),
                narration_acceptance=RuntimeNarrationAcceptance(seed, text, prepared.frame, active.locale, guard))
        else:
            try:
                async with asyncio.timeout(min(8, max(0, occurrence.deadline-manager._monotonic_source()-1))):
                    moment = await manager._async_enrich_runtime_moment(active, seed)
            except (TimeoutError, ValueError, TypeError):
                moment = seed
        state.selected_prepared = None
        guard()
        generated = type(moment.narration_acceptance) is RuntimeNarrationAcceptance
        moment = replace(moment, generation_metadata=tuple((k,v) for k,v in moment.generation_metadata if k != 'realization')+
            (('realization','generated' if generated else 'degraded'),),
            track_announcement=replace(value, generated=generated))
        async with manager._lock:
            guard()
            current = manager.current_active(owner_profile_id)
            if not await manager._async_persist_moment(current, moment, final_authorize=guard):
                state.miss('publication_unavailable')
                return None
            retained_until = ''
            if manager._historical_projections is not None:
                entry = await manager._historical_projections.async_entry_record(
                    owner_profile_id, session_id, '', moment_id=moment.moment_id)
                if entry is not None:
                    body = json.loads(entry['body'])
                    if body.get('archive_basis') == 'owner_metadata_narration_v1':
                        retained_until = entry['retained_until']
            guard()
            moment = replace(moment, track_announcement=replace(moment.track_announcement,
                retained_until=retained_until))
            moment = replace(moment, track_announcement=replace(moment.track_announcement,
                accepted_digest=acceptance_digest(moment)))
            current.moment_engine.moments = (*current.moment_engine.moments, moment)
            current.publish_moment(moment, SessionFlowPosition.NEXT)
            frame = getattr(moment.narration_acceptance, 'frame', '')
            state.committed(occurrence, frame=frame, generated=generated)
            return moment
    except PermissionError:
        state.miss('context_changed')
        return None
    finally:
        # Timing evidence contains only monotonic durations, never source text.
        state.last_completed_at = time.monotonic()
