"""Resolve a contextual performer locally, then reuse public factual narration.

The interpreter proposes only a read intent. Playback metadata is a lookup
identity, never biographical evidence or model input. Research and assessment
remain in the ordinary Ask DJ owner, with no playback authority.
"""
import asyncio
import hashlib
import math
import re
from datetime import UTC, datetime

from .dialogue import current_turn, DialogueError
from .observations import _identified_playback, selected_artist_names
from .public_research import safe_subject, unavailable_answer


async def response(hass, runtime, text, selected, *, recording=False):
    from . import run_music_command, _informational_assist_response
    from ..spotify_backend import SpotifyBackendError
    from ..use_cases import MusicBackendCapabilityError

    turn = current_turn.get()
    started = turn.history.dialogue.clock()
    now = datetime.now(UTC)
    deadline = started + 60
    source_authority = turn.reply_source_authority if recording and callable(turn.reply_source_authority) else None

    def validate():
        if turn.history.dialogue.clock() >= deadline:
            raise DialogueError('playback_observation_expired', 409)
        if recording and source_authority is not None and source_authority() is not True:
            raise DialogueError('source_withdrawn', 409)

    def bind(metadata):
        nonlocal deadline
        stamp = (metadata or {}).get('valid_until') or (metadata or {}).get('expires_at')
        if stamp:
            try:
                expiry = datetime.fromisoformat(stamp)
                if expiry.tzinfo is None:
                    raise ValueError('naive_expiry')
                deadline = min(deadline, started + (expiry.astimezone(UTC) - now).total_seconds())
            except (ValueError, TypeError):
                raise DialogueError('playback_observation_expired', 409) from None
        validate()
        turn.speech_deadline = min(turn.speech_deadline or deadline, deadline)

    turn.delivery_validators.append(validate)
    turn.effect_validators.append(validate)

    async def fresh():
        await turn.guard()
        result = await asyncio.wait_for(run_music_command(hass, runtime, 'status'), 5)
        await turn.guard()
        playback = result.get('playback') if isinstance(result, dict) and result.get('success') is not False else None
        bind(playback)
        return _identified_playback(playback)

    try:
        if selected is None:
            identity = await fresh()
            artist = identity[1] if identity else ''
            if (identity and turn.captured_playback_item_id
                    and hashlib.sha256(identity[0].encode()).hexdigest()[:24] != turn.captured_playback_item_id):
                raise DialogueError('playback_context_changed', 409)
        else:
            bind(selected.get('playback'))
            identity = _identified_playback(selected.get('playback'))
            names = selected_artist_names(selected)
            artist = identity[1] if identity else (names[0] if len(names) == 1 else '')
        subject = safe_subject(artist, qualified=True)
        if recording:
            # Status/selected labels are private lookup hints, not public names.
            # Resolve the actual catalogue by its original public ID first.
            if (identity is None or not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', identity[0])
                    or source_authority is None):
                return production_unavailable(turn.style['language'])
            validate()
            if turn.lookup_calls >= 2:
                raise DialogueError('conversation_lookup_budget', 503)
            turn.lookup_calls += 1
            result = await asyncio.wait_for(run_music_command(hass, runtime, 'track_metadata', identity[0]), 5)
            await turn.guard()
            catalog = result.get('track') if type(result) is dict and result.get('success') is True else None
            if (type(catalog) is not dict or set(catalog) != {'uri', 'title', 'artist', 'artist_id'}
                    or catalog.get('uri') != identity[0]
                    or not isinstance(catalog.get('artist_id'), str)
                    or not re.fullmatch(r'[A-Za-z0-9]{22}', catalog['artist_id'])):
                return production_unavailable(turn.style['language'])
            from .public_research import safe_lookup_topic
            subject = safe_subject(catalog['artist'], qualified=True)
            work = safe_lookup_topic(catalog['title'])
            if not subject or not work:
                return production_unavailable(turn.style['language'])
            turn.interpreted_context_research = True
            answer = await _informational_assist_response(hass, runtime, text, {}, {}, {}, [],
                research_subject=subject, research_angle='production', contextual_research=True,
                recording_lookup=(subject, work))
            await turn.guard()
            if selected is None and await fresh() != identity:
                raise DialogueError('playback_context_changed', 409)
            return answer
        if subject:
            # Exactly one validated interpretation + generation + assessment.
            # No repair retry can buy another call, and no effect grant changes.
            turn.interpreted_artist_research = True
            answer = await _informational_assist_response(hass, runtime, text, {}, {}, {}, [],
                research_subject=subject)
            await turn.guard()
            if selected is None and await fresh() != identity:
                raise DialogueError('playback_context_changed', 409)
            return answer
    except (SpotifyBackendError, MusicBackendCapabilityError, OSError, TimeoutError):
        pass
    if recording:
        return production_unavailable(turn.style['language'])
    message = unavailable_answer(turn.style['language'], ambiguous=True)
    return {'success': True, 'text': message, 'dj_text': message, 'action': 'none',
            'is_generated_text': False, 'text_source': 'core', 'playback_actions': [], 'images': [],
            'intent': {'category': 'informational', 'intent': 'ask_music_info'}}


def production_unavailable(language):
    copy = {
        'nl': 'Ik kan nog geen betrouwbare bron over de opname en productie van dit nummer controleren.',
        'en': 'I cannot yet verify a reliable source about how this recording was recorded and produced.',
        'de': 'Ich kann noch keine verlässliche Quelle zur Aufnahme und Produktion dieses Titels prüfen.',
        'fr': 'Je ne peux pas encore vérifier une source fiable sur l’enregistrement et la production de ce morceau.',
        'es': 'Todavía no puedo verificar una fuente fiable sobre la grabación y producción de este tema.',
    }
    message = copy.get(language, copy['en'])
    return {'success': True, 'text': message, 'dj_text': message, 'action': 'none',
            'images': [], 'playback_actions': [], 'text_source': 'core', 'is_generated_text': False,
            'knowledge_basis': 'public_recording_research_unavailable'}


def recording_reference(text):
    """A bounded explicit selection lens; other wording keeps semantic routing."""
    value = text.strip().casefold().strip(' .?!¿¡')
    if re.fullmatch(r'(?:(?:ik bedoel |i mean |ich meine |je veux dire |me refiero a )?'
        r'(?:(?:het |the |das |der |le |la |el )?(?:huidig(?:e)?|current|aktuelle[rsn]?|actuel|actual) '
        r'(?:nummer|track|song|recording|titel|lied|morceau|titre|canción|tema)|'
        r'(?:het )?nummer (?:dat )?nu (?:speelt|draait)|the (?:song|track) playing now|'
        r'le morceau actuel|la canción actual))', value):
        return 'current'
    if re.fullmatch(r'(?:(?:het |the |das |le |el )?(?:geselecteerde|gekozen|selected|ausgewählte|sélectionné|seleccionado) '
        r'(?:nummer|track|song|recording|titel|morceau|tema))', value):
        return 'selected'
    return None


def stage_production_clarification(turn, text, scope):
    """Keep only an unresolved generic purpose, never its text or recording labels."""
    value = text.strip().casefold().strip(' .?!¿¡')
    generic = re.fullmatch(
        r'(?:vertel (?:me )?(?:eens )?(?:(?:wat|iets) )?over (?:deze|die) (?:productie|opname)|'
        r'tell me (?:(?:a bit|something) )?about (?:this|that) (?:production|recording)|'
        r'erzähl(?:e)? (?:mir )?(?:etwas )?über diese (?:produktion|aufnahme)|'
        r'parle-moi de cet(?:te)? (?:production|enregistrement)|'
        r'háblame de esta (?:producción|grabación))', value)
    if not generic or scope is None or scope.captured_at is None:
        return None
    from ..ask_dj_history import _request_hash
    pending = {'type': 'recording_production', 'purpose': 'production',
        'created_at': scope.captured_at, 'deadline': scope.captured_at + 120,
        'request_hash': _request_hash(turn.scope, turn.client_id),
        'generation': turn.generation, 'read_context_revision': turn.read_context_revision}
    def validate_install():
        _validate_purpose_clock(turn, pending)
        if turn.installed_production_revision is None:
            valid = (turn.frame.pending is turn.pending_at_start
                     and turn.frame.pending_revision == turn.pending_revision_at_start)
        else:
            valid = (turn.frame.pending is turn.installed_production_pending
                     and turn.frame.pending_revision == turn.installed_production_revision
                     and turn.frame.pending == pending)
        if not valid:
            raise DialogueError('conversation_context_changed', 409)
    validate_install()
    turn.effect_validators.append(validate_install)
    turn.delivery_validators.append(validate_install)
    turn.pending = pending
    copy = {
        'nl': 'Bedoel je het huidige nummer of het geselecteerde nummer?',
        'en': 'Do you mean the current recording or the selected recording?',
        'de': 'Meinst du den aktuellen oder den ausgewählten Titel?',
        'fr': 'Tu parles du morceau actuel ou du morceau sélectionné ?',
        'es': '¿Te refieres al tema actual o al seleccionado?',
    }
    message = copy.get(turn.style['language'], copy['en'])
    return {'success': True, 'text': message, 'dj_text': message, 'action': 'none',
            'text_source': 'core', 'is_generated_text': False, 'images': [],
            'clarification_required': True, 'knowledge_basis': 'public_subject_required'}


def _validate_purpose_clock(turn, pending):
    keys = {'type', 'purpose', 'created_at', 'deadline', 'request_hash', 'generation', 'read_context_revision'}
    if (type(pending) is not dict or set(pending) != keys
            or pending['type'] != 'recording_production' or pending['purpose'] != 'production'
            or any(type(pending[k]) not in (int, float) or not math.isfinite(pending[k])
                   for k in ('created_at', 'deadline'))
            or pending['deadline'] != pending['created_at'] + 120
            or not isinstance(pending['request_hash'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', pending['request_hash'])
            or pending['generation'] != turn.frame.generation
            or pending['read_context_revision'] != turn.frame.read_context_revision):
        raise DialogueError('conversation_context_changed', 409)
    if not pending['created_at'] <= turn.history.dialogue.clock() < pending['deadline']:
        raise DialogueError('choice_expired', 409)


def bind_production_purpose(turn):
    """Fence actual semantic consumption, never availability alone."""
    pending = turn.pending_at_start
    if not isinstance(pending, dict) or pending.get('type') != 'recording_production':
        return
    original = dict(pending)
    def validate_original():
        _validate_purpose_clock(turn, original)
        own_consumed = (turn.consumed_production_revision == turn.pending_revision_at_start + 1
                        and turn.frame.pending_revision == turn.consumed_production_revision
                        and turn.frame.pending is None)
        not_consumed = (turn.consumed_production_revision is None
                        and turn.frame.pending is pending and pending == original
                        and turn.frame.pending_revision == turn.pending_revision_at_start)
        if not (own_consumed or not_consumed):
            raise DialogueError('conversation_context_changed', 409)
    validate_original()
    turn.consume_production_pending = True
    turn.source_request_hashes.add(original['request_hash'])
    turn.effect_validators.append(validate_original)
    turn.delivery_validators.append(validate_original)


async def production_continuation(hass, runtime, text):
    """Literal selection shortcut; free wording uses the same semantic execute branch."""
    turn = current_turn.get()
    pending = turn.pending_at_start
    if not isinstance(pending, dict) or pending.get('type') != 'recording_production':
        return None
    turn.clear_production_pending = True
    reference = recording_reference(text)
    if reference is None:
        return None
    from .semantic_reads import ReadPlan, capture_scope, execute_plan
    scope = capture_scope(hass, turn)
    return await execute_plan(hass, runtime, text, ReadPlan('production_story', reference, False),
                              scope)
