"""Resolve a contextual performer locally, then reuse public factual narration.

The interpreter proposes only a read intent. Playback metadata is a lookup
identity, never biographical evidence or model input. Research and assessment
remain in the ordinary Ask DJ owner, with no playback authority.
"""
import asyncio
import hashlib
from datetime import UTC, datetime

from .dialogue import current_turn, DialogueError
from .observations import _identified_playback, selected_artist_names
from .public_research import safe_subject, unavailable_answer


async def response(hass, runtime, text, selected):
    from . import run_music_command, _informational_assist_response
    from ..spotify_backend import SpotifyBackendError
    from ..use_cases import MusicBackendCapabilityError

    turn = current_turn.get()
    started = turn.history.dialogue.clock()
    now = datetime.now(UTC)
    deadline = started + 60

    def validate():
        if turn.history.dialogue.clock() >= deadline:
            raise DialogueError('playback_observation_expired', 409)

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
    message = unavailable_answer(turn.style['language'], ambiguous=True)
    return {'success': True, 'text': message, 'dj_text': message, 'action': 'none',
            'is_generated_text': False, 'text_source': 'core', 'playback_actions': [], 'images': [],
            'intent': {'category': 'informational', 'intent': 'ask_music_info'}}
