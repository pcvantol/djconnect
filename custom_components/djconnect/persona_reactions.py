"""Explicit ephemeral avatar feedback under the existing paired operation owner.

No chat turn, Moment, history body, model, source lookup or music mutation. One
short RAM lease belongs to the initiating device and current confirmed Session.
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import math
import time

from .persona_reaction_text import KINDS, LANGUAGES, render

OPERATION = 'session/persona/reaction'
CANCEL = OPERATION + '/cancel'
MAX_SECONDS = 30
COOLDOWN = 10
WINDOW = 600
MAX_REACTIONS = 6
MAX_SESSIONS = 64
REASONS = frozenset({'completed', 'dismissed', 'background', 'ask_dj_foreground', 'speech_conflict'})


def capability():
    return {'available': True, 'version': 1, 'operation': OPERATION,
            'cancel_operation': CANCEL, 'path': '/api/djconnect/v1/transport/operation',
            'authentication': 'paired_device_bearer', 'owner_only': True,
            'settings_contract_version': 3, 'requires_confirmed_settings': True,
            'session_required': True, 'kinds': list(KINDS), 'language_families': list(LANGUAGES),
            'processors': ['local_on_device', 'ha_configured'], 'local_target': True,
            'ha_speaker_target': False, 'ha_speaker_disposition': 'text_feedback_only_not_qualified',
            'text_only': 'text_feedback_without_synthesis_or_audio_grants',
            'history_publication': False, 'maximum_seconds': MAX_SECONDS,
            'minimum_interval_seconds': COOLDOWN, 'rolling_window_seconds': WINDOW,
            'maximum_per_window': MAX_REACTIONS, 'maximum_pending_or_playing': 1,
            'rate_scope': 'profile_active_session_across_devices', 'queue': False,
            'content_basis': 'core_owned_curated_reaction_v1', 'model_calls': False,
            'actual_audio_start_required': True, 'client_cancel_on_lifecycle_required': True,
            'duplicate': 'original_operation_receipt_no_new_content_or_synthesis',
            'cache_policy': 'private,no-store'}


@dataclass
class _Pending:
    identifier: str
    device: str
    binding: object
    deadline: float
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)


@dataclass
class _State:
    accepted: deque = field(default_factory=deque)
    sequence: int = 0
    lease: object = None
    pending: _Pending | None = None
    interaction_revision: int = 0


class _Book:
    """Only bounded rate timestamps/sequence and one lease; never durable bodies."""
    def __init__(self, manager):
        self.manager = manager
        self.rows = {}
        self.high_water = time.monotonic()

    def now(self):
        self.high_water = max(self.high_water, time.monotonic())
        return self.high_water

    def sweep(self):
        now = self.now()
        for key, state in tuple(self.rows.items()):
            active = self.manager.current_active(key[0])
            current = active is not None and (active.session_id, active.settings_generation) == key[1:]
            if state.pending is not None and (not current or now >= state.pending.deadline):
                state.pending.cancelled.set()
                state.pending = None
            if state.lease is not None:
                try:
                    state.lease()
                except Exception:
                    if state.lease is not None:
                        state.lease.dispose()
            while state.accepted and now - state.accepted[0] >= WINDOW:
                state.accepted.popleft()
            if not current or (not state.accepted and state.lease is None and state.pending is None):
                if state.lease is not None:
                    state.lease.dispose()
                self.rows.pop(key, None)

    def state(self, key):
        self.sweep()
        if key not in self.rows:
            if len(self.rows) >= MAX_SESSIONS:
                raise ValueError('persona_reaction_capacity')
            self.rows[key] = _State()
        return self.rows[key]


def _book(hass, manager):
    domain = hass.data.setdefault('djconnect', {})
    book = domain.get('persona_reaction_book')
    if book is None or book.manager is not manager:
        if book is not None:
            for state in book.rows.values():
                if state.pending is not None:
                    state.pending.cancelled.set()
                if state.lease is not None:
                    state.lease.dispose()
        book = domain['persona_reaction_book'] = _Book(manager)
    return book


def withdraw_for_interaction(hass, profile_id):
    """Called only after an existing owner accepts a foreground interaction."""
    book = hass.data.get('djconnect', {}).get('persona_reaction_book')
    if book is not None:
        for key, state in tuple(book.rows.items()):
            if key[0] == profile_id:
                state.interaction_revision += 1
                if state.pending is not None:
                    state.pending.cancelled.set()
                if state.lease is not None:
                    state.lease.dispose()


class _Lease:
    def __init__(self, hass, book, state, authority, identifier, deadline, guard, session_id):
        from .dj_response import PrivateSpeechSource
        self.book, self.state, self.device, self.binding = book, state, authority.device, authority.binding
        self.identifier, self.deadline = identifier, deadline
        self.cancelled = asyncio.Event()
        self.expires_at = time.time() + max(0, deadline - book.now())
        def validate():
            if self.cancelled.is_set() or book.now() >= deadline or state.lease is not self:
                raise PermissionError('persona_reaction_withdrawn')
            guard()
        self.source = PrivateSpeechSource(hass, validate, expires_at=self.expires_at, session_id=session_id)
        self.source.processor_basis = 'core_owned_persona_reaction_v1'

    def start(self):
        self.state.lease = self
        self.source.on_withdraw(self._withdraw)

    def _withdraw(self):
        self.cancelled.set()
        if self.state.lease is self:
            self.state.lease = None

    def __call__(self):
        self.source()

    def dispose(self):
        self.source.withdraw()


def _identifier(value):
    return type(value) is str and 0 < len(value) <= 128 and value == value.strip() and value.isprintable()


async def async_cancel(hass, authority, payload):
    from .transport_delivery import register_delivery_admission
    fields = {'contract_version', 'session_id', 'reaction_id', 'reason', 'device_id', 'client_type'}
    if (type(payload) is not dict or set(payload) != fields
            or type(payload['contract_version']) is not int or payload['contract_version'] != 1
            or not _identifier(payload['session_id']) or not _identifier(payload['reaction_id'])
            or type(payload['reason']) is not str or payload['reason'] not in REASONS):
        return {'success': False, 'error': 'invalid_request'}, 400
    authority.owner_final_guard()
    register_delivery_admission(authority.owner_final_guard)
    book = hass.data.get('djconnect', {}).get('persona_reaction_book')
    if book is not None:
        for key, state in tuple(book.rows.items()):
            if key[:2] != (authority.context.profile_id, payload['session_id']):
                continue
            for item in (state.pending, state.lease):
                if item is None or item.identifier != payload['reaction_id']:
                    continue
                if (item.device, item.binding) != (authority.device, authority.binding):
                    return {'success': False, 'error': 'persona_reaction_unavailable'}, 404
                if isinstance(item, _Pending):
                    item.cancelled.set()
                else:
                    item.dispose()
    # Content-free idempotent cancellation, also after expiry. No new lease,
    # history clear, proactive budget reset or speaker stop is manufactured.
    return {'success': True, 'persona_reaction_cancelled': True}, 200


async def async_react(hass, authority, payload):
    from .domain.profile.dj_settings import DJSettings
    from .hybrid_service import current_operation_identity, guard_transport_effect
    from .persistence.dj_settings import SettingsCommitError
    from .profile_context import profile_storage
    from .session_runtime import session_runtime_manager, SessionRuntimeState
    from .session_speech import exact_segments, prepare_ha
    from .settings_migration import assessment
    from .speech_processor import voice_options
    from .speech_feedback import notification, SpeechProviderChanged
    from .transport_delivery import register_delivery_admission

    fields = {'contract_version', 'session', 'kind', 'language', 'processor', 'device_id', 'client_type'}
    context = payload.get('session') if type(payload) is dict else None
    if (type(payload) is not dict or set(payload) != fields
            or type(payload['contract_version']) is not int or payload['contract_version'] != 1
            or type(context) is not dict or set(context) != {'session_id', 'generation', 'revision'}
            or not all(_identifier(context[k]) for k in ('session_id', 'generation'))
            or type(context['revision']) is not int or context['revision'] < 0
            or payload['kind'] not in KINDS or payload['language'] not in LANGUAGES
            or payload['processor'] not in ('local_on_device', 'ha_configured')):
        return {'success': False, 'error': 'invalid_request'}, 400
    identifier, operation_expiry_ms = current_operation_identity(authority)
    authority.owner_final_guard()
    register_delivery_admission(authority.owner_final_guard)
    manager = session_runtime_manager(hass)
    profile = authority.context.profile_id
    active = manager.current_active(profile)
    if active is None or active.runtime_state != SessionRuntimeState.ACTIVE:
        return {'success': False, 'error': 'persona_reaction_session_unavailable'}, 409
    if active.selected_presence == 'talkative':
        return {'success': False, 'error': 'settings_migration_choice_required'}, 409
    original = (active.session_id, active.settings_generation, active.settings_revision)
    if tuple(context[k] for k in ('session_id', 'generation', 'revision')) != original:
        return {'success': False, 'error': 'persona_reaction_context_changed'}, 409
    broadcast = active.broadcast
    book = _book(hass, manager)
    try:
        key = (profile, active.session_id, active.settings_generation)
        state = book.state(key)
    except ValueError:
        return {'success': False, 'error': 'persona_reaction_capacity'}, 409
    now = book.now()
    occupied = state.pending or state.lease
    if occupied is not None:
        return {'success': False, 'error': 'persona_reaction_busy',
                'retry_after_seconds': max(1, math.ceil(occupied.deadline - now))}, 409
    if state.accepted and now - state.accepted[-1] < COOLDOWN:
        return {'success': False, 'error': 'persona_reaction_cooldown',
                'retry_after_seconds': math.ceil(COOLDOWN - now + state.accepted[-1])}, 429
    if len(state.accepted) >= MAX_REACTIONS:
        return {'success': False, 'error': 'persona_reaction_rate_limit',
                'retry_after_seconds': math.ceil(WINDOW - now + state.accepted[0])}, 429
    duration = min(MAX_SECONDS, operation_expiry_ms / 1000 - time.time())
    if duration <= 0:
        return {'success': False, 'error': 'persona_reaction_withdrawn'}, 409
    pending = _Pending(identifier, authority.device, authority.binding, now + duration)
    state.pending = pending
    interaction_revision = state.interaction_revision
    # Capture before any Settings/journal await; prepare_ha must never silently
    # adopt a provider configuration changed during durable send admission.
    provider_revision = (voice_options(hass, authority.runtime.config)['revision']
                         if payload['processor'] == 'ha_configured' else None)
    lease = None
    def owner_current():
        authority.owner_final_guard()
        if (book.rows.get(key) is not state or state.interaction_revision != interaction_revision
                or pending.cancelled.is_set() or book.now() >= pending.deadline):
            raise PermissionError('persona_reaction_withdrawn')
        current = manager.current_active(profile)
        if (session_runtime_manager(hass) is not manager or current is None
                or current.runtime_state != SessionRuntimeState.ACTIVE or current.broadcast is not broadcast
                or (current.session_id, current.settings_generation, current.settings_revision) != original):
            raise PermissionError('persona_reaction_withdrawn')
        return True
    try:
        read = asyncio.create_task(manager.async_read_dj_settings(owner_profile_id=profile, authorize=owner_current))
        cancelled = asyncio.create_task(pending.cancelled.wait())
        try:
            async with asyncio.timeout(max(0, pending.deadline - book.now())):
                await asyncio.wait((read, cancelled), return_when=asyncio.FIRST_COMPLETED)
                owner_current()
                snapshot = await read
        finally:
            for task in (read, cancelled):
                if not task.done():
                    task.cancel()
            await asyncio.gather(read, cancelled, return_exceptions=True)
        owner_current()
        acceptance = {k: snapshot[k] for k in ('activated', 'accepted_contract_version')}
        storage = profile_storage(hass)
        if (not snapshot['activated'] or snapshot['contract_version'] != 3
                or assessment(hass, storage.household, authority.context.profile, **acceptance)['requires_review']
                or not snapshot['session'] or snapshot['session'].get('selection_required')):
            return {'success': False, 'error': 'settings_migration_choice_required'}, 409
        selected = DJSettings.from_dict(snapshot['session']['settings'])
        token = manager.dj_settings_fence_token(profile)
        persona_revision, mood_revision = active.persona_revision, active.mood_revision
        def guard():
            owner_current()
            if (manager.dj_settings_fence_token(profile) != token
                    or assessment(hass, storage.household, storage.household.profiles[profile], **acceptance)['requires_review']):
                raise PermissionError('persona_reaction_withdrawn')
            if (provider_revision is not None and selected.announcement_output in ('client_device', 'both')
                    and voice_options(hass, authority.runtime.config)['revision'] != provider_revision):
                raise SpeechProviderChanged('speech_configuration_changed', payload['language'])
        guard()
        now = book.now()
        lease = _Lease(hass, book, state, authority, identifier, pending.deadline, guard, active.session_id)
        lease.start()
        state.pending = None
        from .dj_response import invalidate_private_speech_sources, collect_private_speech_sources
        broadcast.speech_cleanup = lambda: invalidate_private_speech_sources(hass, session_id=active.session_id)
        broadcast.speech_refresh = lambda: collect_private_speech_sources(hass, session_id=active.session_id)
        text = render(persona=selected.persona, mood=selected.mood, language=payload['language'],
                      kind=payload['kind'], sequence=state.sequence)
        state.sequence += 1
        state.accepted.append(now)
        revision = hashlib.sha256(text.encode()).hexdigest()[:24]
        descriptor = {'schema_version': 1, 'reference': {'reaction_id': identifier, 'session_id': active.session_id},
            'source_id': identifier, 'source_kind': 'core_owned_persona_reaction',
            'text_revision': revision, 'presentation_revision': revision,
            'persona': selected.persona, 'persona_revision': persona_revision,
            'mood': selected.mood, 'mood_revision': mood_revision, 'locale': payload['language'],
            'segments': exact_segments(text), 'state': 'available', 'manual_allowed': True,
            'processors': ['local_on_device', 'ha_configured'], 'autoplay_eligible': False,
            'settings_contract_version': 3, 'settings_revision': token,
            'expires_at': datetime.fromtimestamp(lease.expires_at, UTC).isoformat(),
            'cache_policy': 'private,no-store'}
        reaction = {'schema_version': 1, 'reaction_id': identifier, 'session': context,
            'text': text, 'locale': payload['language'], 'kind': payload['kind'],
            'persona': selected.persona, 'mood': selected.mood, 'persona_revision': persona_revision,
            'mood_revision': mood_revision, 'expires_at': descriptor['expires_at'],
            'content_basis': 'core_owned_curated_reaction_v1', 'history_publication': False,
            'cache_policy': 'private,no-store'}
        delivery = {'local': 'not_requested', 'ha_speaker': 'not_requested', 'audible': 'not_proven'}
        if selected.announcement_output == 'text_only':
            speech = {'state': 'unavailable', 'reason': 'announcement_text_only', 'segments': [], 'processors': []}
        elif selected.announcement_output == 'ha_speaker':
            speech = {'state': 'unavailable', 'reason': 'persona_reaction_speaker_not_qualified', 'segments': [], 'processors': []}
            delivery['ha_speaker'] = 'not_qualified'
        else:
            if selected.announcement_output == 'both':
                delivery['ha_speaker'] = 'not_qualified'
            if payload['processor'] == 'local_on_device':
                speech = {**descriptor, 'processor': 'local_on_device', 'audio_state': 'renderer_pending', 'effective_voice': None}
            else:
                data = {'reference': descriptor['reference'], 'voice_preference': selected.gender.value}
                if selected.voice.kind == 'provider_voice':
                    data['voice_id'] = selected.voice.voice_id
                await guard_transport_effect()
                lease()
                prepared = asyncio.create_task(prepare_ha(hass, authority.runtime, profile, data, descriptor, lease.source,
                    expected_provider=selected.voice.provider_id if selected.voice.kind == 'provider_voice' else None))
                cancelled = asyncio.create_task(lease.cancelled.wait())
                try:
                    await asyncio.wait((prepared, cancelled), return_when=asyncio.FIRST_COMPLETED)
                    lease()
                    speech = await prepared
                finally:
                    for task in (prepared, cancelled):
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(prepared, cancelled, return_exceptions=True)
                lease()
                if speech.get('audio_state') == 'ready':
                    from .dj_response import get_private_tts_audio
                    asset = get_private_tts_audio(hass, speech['audio_reference']['asset_id'], profile)
                    asset.delivery_device_id = authority.identity['device_id']
                    register_delivery_admission(asset.admission)
            delivery['local'] = speech.get('audio_state', 'unavailable')
        lease()
        register_delivery_admission(lease)
        reaction['speech'] = speech
        return {'success': True, 'persona_reaction': reaction, 'delivery': delivery}, 200
    except SpeechProviderChanged as exc:
        if lease is not None:
            lease.dispose()
        return {'success': False, 'error': str(exc),
                'notification': notification(str(exc), payload['language'])}, 409
    except SettingsCommitError:
        if lease is not None:
            lease.dispose()
        return {'success': False, 'error': 'settings_unavailable'}, 503
    except (PermissionError, ValueError, TimeoutError) as exc:
        if lease is not None:
            lease.dispose()
        code = 'persona_reaction_capacity' if str(exc) in {'persona_reaction_capacity', 'speech_capacity'} else 'persona_reaction_withdrawn'
        return {'success': False, 'error': code}, 409
    except BaseException:
        if lease is not None:
            lease.dispose()
        raise
    finally:
        if state.pending is pending:
            state.pending = None
