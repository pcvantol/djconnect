"""Semantic derivative from actual existing Core projections, not a new wire."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'examples/client_contracts/persona_living_avatar_v1/existing-signals-content-delete-20261021.json'


async def build(core):
    manager = core.SessionRuntimeManager()
    owner = 'synthetic-avatar-owner'
    session = await manager.async_start(owner_profile_id=owner, selected_mood='groove', locale='nl')
    rows = []

    def observe(case):
        current = manager.current_active(owner)
        snapshot = session.broadcast.as_dict()
        axes, native = snapshot['session'], snapshot['native_delivery']
        rows.append({'case': case, 'runtime_state': axes['runtime_state'],
            'is_current_owner_session': current is not None and current.session_id == session.session_id,
            'mood': axes['selected_mood'], 'mood_revision': axes['mood_revision'],
            'persona': axes['dj_persona'], 'persona_revision': axes['persona_revision'],
            'presence': axes['selected_presence'], 'presence_revision': axes['presence_revision'],
            'has_current_moment': native['current_moment_id'] is not None,
            'has_intentional_silence': native['current_silence_moment_id'] is not None,
            'silence_has_speech': any(item['reference'].get('moment_id') == native['current_silence_moment_id']
                                      for item in snapshot['session_speech']['moments'])
                                      if native['current_silence_moment_id'] else False,
            'proactive_budget_spent': session.presence_ledger.total_published})

    observe('empty_active')
    await manager.async_update_playback_projection(owner_profile_id=owner, session_id=session.session_id,
        state='playing', media_identity='spotify:track:'+'A'*22, title='Synthetic track',
        artist='Synthetic artist', duration_ms=180000, position_ms=1000)
    session = await manager.async_update_presence(owner_profile_id=owner,
        session_id=session.session_id, selected_presence='music_only', expected_revision=0)
    observe('music_only')
    silence = session.moment_engine.create_silence(session_id=session.session_id,
        selected_mood=session.selected_mood, persona=session.dj_persona, locale=session.locale,
        reason='synthetic_intentional_space')
    session.publish_moment(silence)
    observe('intentional_silence_music_only')
    session = await manager.async_update_mood(owner_profile_id=owner,
        session_id=session.session_id, selected_mood='party', expected_revision=0)
    observe('confirmed_mood_revision')
    session = await manager.async_update_persona(owner_profile_id=owner,
        session_id=session.session_id, dj_persona=core.DJPersona.FESTIVAL_DJ, expected_revision=0)
    observe('confirmed_persona_revision')
    await manager.async_end(owner_profile_id=owner, session_id=session.session_id)
    observe('ended')
    sources = ('custom_components/djconnect/session_runtime.py',
        'custom_components/djconnect/native_moment_delivery.py',
        'custom_components/djconnect/presence_policy.py',
        'custom_components/djconnect/session_speech.py')
    return {'qualification': 'ACTUAL_EXISTING_CORE_SEMANTIC_DERIVATIVE_SYNTHETIC_INPUTS',
        'representation': 'selected semantic fields; not an HTTP payload, client reducer or installed proof',
        'producer_source_pins': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        'cases': rows, 'touch_reactions': 'EXPLICIT_PAIRED_LOCAL_PRODUCER_V1_NATIVE_OPEN',
        'native': 'NOT_RUN', 'audible': 'NOT_RUN', 'installed_avatar': 'NOT_RUN'}
