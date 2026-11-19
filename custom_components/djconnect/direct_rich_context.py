"""Pure real owner/Session/source capture for Direct rich, not a display lease.

No request starts/loads a Profile, Session, provider or pairing. Original policy
continuity is separate from one exact post-await read snapshot. The consuming
purpose still needs its own original consent, clocks, SQL once and credentials.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import weakref

from .direct_rich_wire import RichError, require

_EPOCH = object()
if "_contexts" not in globals():
    _contexts = weakref.WeakSet()


def _relation(household, device_id, client_type):
    """Only actual bound policy/source coordinates; no request/default owner."""
    from .profile_privacy import resolve_profile_privacy_policy
    device = household.devices.get(device_id)
    require(device is not None and device.client_type == client_type
        and str(device.pairing_state) == "paired"
        and type(device.binding_generation) is str
        and re.fullmatch(r"[a-f0-9]{32}", device.binding_generation) is not None,
        "rich_not_allowed", 403)
    profile = household.profiles.get(device.linked_profile_id)
    require(profile is not None and str(profile.state) == "active"
        and str(profile.privacy_mode) == "normal"
        and resolve_profile_privacy_policy(profile, {}).allow_personal_read,
        "rich_not_allowed", 403)
    prefs = profile.preferences
    backend = household.music_backends.get(prefs.default_backend_id)
    account = household.music_accounts.get(prefs.default_music_account_id)
    require(backend is not None and str(backend.state) == "active"
        and str(backend.provider) in {"spotify_direct", "music_assistant"}
        and account is not None and str(account.state) == "active"
        and account.backend_id == backend.backend_id
        and profile.profile_id in account.linked_profile_ids,
        "rich_not_allowed", 403)
    return (profile.profile_id, device.binding_generation, profile.profile_type,
        profile.state, profile.privacy_mode, profile.entitlements, profile.capabilities,
        profile.capability_policy, backend.backend_id, backend.provider,
        account.account_id, account.provider_account_id, account.kind, account.scopes)


def retire_runtime(runtime):
    for context in tuple(_contexts):
        if context.pair.runtime is runtime or context.provider is runtime:
            context.retire()


def retire_session(manager, owner, session_id=""):
    for context in tuple(_contexts):
        if (context.manager is manager and context.owner == owner
                and (not session_id or context.session_id == session_id)):
            context.retire()


def retire_profile_owner(owner):
    for context in tuple(_contexts):
        if context.profile.owner is owner:
            context.retire()


def fence_profile_household(manager, household):
    """Actual staging intent, before assignment/await; cosmetic data is separate."""
    for context in tuple(_contexts):
        if context.profile.manager is not manager:
            continue
        try:
            same = _relation(household, context.device_id, context.client_type) == context.relation
        except Exception:
            same = False
        if not same:
            context.retire()


@dataclass(frozen=True, repr=False)
class _AttemptStamp:
    settings: tuple
    state: object
    sequence: int
    content_epoch: int
    observation_serial: int
    observation: object
    state_observed: object


def _stamp(active):
    broadcast = active.broadcast
    settings = (active.settings_generation, active.settings_revision, active.defaults_revision,
        active.mood_revision, active.persona_revision, active.presence_revision,
    )
    return _AttemptStamp(settings, broadcast.state, broadcast.delivery_sequence,
        broadcast.content_epoch, broadcast.passive_observation_serial,
        broadcast.passive_observation, broadcast.passive_state_observed)


@dataclass(eq=False, repr=False)
class RichReadAttempt:
    context: object
    snapshot: object
    active: object
    stamp: _AttemptStamp
    closed: bool = False

    def retire(self):
        self.closed = True
        if self.context is not None and self.context.attempts is not None:
            self.context.attempts.discard(self)
        self.context = self.snapshot = self.active = self.stamp = None

    def current(self):
        """Recheck THIS original attempt, never replace it after an await."""
        if self.closed:
            return False
        snapshot, context, original, stamp = self.snapshot, self.context, self.active, self.stamp
        valid = False
        try:
            if snapshot.current():
                _snapshot, active = context._inspect()
                broadcast = active.broadcast
                valid = (not self.closed and active is original
                    and broadcast.state is stamp.state
                    and broadcast.passive_observation is stamp.observation
                    and broadcast.passive_state_observed is stamp.state_observed
                    and _stamp(active) == stamp)
        except RichError:
            pass
        if not valid:
            self.retire()
        return valid


@dataclass(eq=False, repr=False)
class DirectRichContext:
    pair: object
    profile: object
    relation: tuple
    owner: str
    device_id: str
    client_type: str
    manager: object
    session_id: str
    broadcast: object
    source: tuple
    provider: object
    provider_entry: object
    provider_data: object
    provider_options: object
    provider_generation: int
    epoch: object
    retired: bool = False
    attempts: object = field(default_factory=weakref.WeakSet)
    on_retire: object = None

    def retire(self):
        if self.retired:
            return
        self.retired = True
        callback, self.on_retire = self.on_retire, None
        if callback is not None:
            callback()
        _contexts.discard(self)
        if self.attempts is not None:
            for attempt in tuple(self.attempts):
                attempt.retire()
        if self.pair is not None:
            self.pair.retire()
        if self.profile is not None:
            self.profile.retire()
        for name in self.__dataclass_fields__:
            if name != "retired":
                setattr(self, name, None)

    def _inspect(self):
        from .profile_observation import ProfileObservationUnavailable
        from .profile_backend import profile_backend_entry_id
        from .client_retirement import is_retired_entry
        from .retired_provider import TRANSFER_FENCE
        if self.retired:
            raise RichError("rich_unavailable", 503)
        try:
            require(self.epoch is _EPOCH and self.pair.current(), "rich_unavailable", 503)
            snapshot = self.profile.attempt()
            if snapshot is None:
                raise RichError("rich_frame_unavailable", 503)
            require(_relation(snapshot.household, self.device_id, self.client_type) == self.relation,
                "rich_not_allowed", 403)
            domain = self.pair.domain
            require(domain.get("session_runtime_manager") is self.manager
                and self.manager._persistent_sessions._persistence is self.pair.persistence,
                "rich_unavailable", 503)
            active = self.manager.current_active(self.owner)
            require(active is not None and active.session_id == self.session_id
                and active.broadcast is self.broadcast and str(active.runtime_state) == "active"
                and str(self.broadcast.state.runtime_state) == "active",
                "rich_unavailable", 503)
            actual_source = self.manager._history_source_contexts.get(self.session_id)
            require(type(actual_source) is dict and tuple(sorted(actual_source.items())) == self.source,
                "rich_not_allowed", 403)
            entry, provider = self.provider_entry, self.provider
            require(domain.get(entry.entry_id) is provider and provider.entry is entry
                and any(e is entry for e in self.pair.hass.config_entries.async_entries("djconnect"))
                and entry.disabled_by is None and entry.state.value == "loaded"
                and not is_retired_entry(entry)
                and entry.entry_id not in domain.get(TRANSFER_FENCE, set())
                and entry.data is self.provider_data and entry.options is self.provider_options
                and getattr(provider, "_receiver_end_generation", 0) == self.provider_generation
                and self.manager.receiver_entry_generation(entry.entry_id) == self.provider_generation
                and profile_backend_entry_id(self.pair.hass, self.owner) == entry.entry_id,
                "rich_not_allowed", 403)
            require(self.manager.receiver_entry_generation(self.pair.entry.entry_id)
                == getattr(self.pair.runtime, "_receiver_end_generation", 0), "rich_not_allowed", 403)
            if (self.manager._lock.locked() or self.owner in self.manager._pending_settings_confirmations
                    or self.broadcast.content_pending):
                raise RichError("rich_frame_unavailable", 503)
            require(snapshot.current(), "rich_frame_unavailable", 503)
            return snapshot, active
        except RichError as error:
            if error.code != "rich_frame_unavailable":
                self.retire()
            raise
        except (ProfileObservationUnavailable, AttributeError, KeyError, TypeError, ValueError):
            self.retire()
            raise RichError("rich_unavailable", 503) from None

    def attempt(self):
        snapshot, active = self._inspect()
        attempt = RichReadAttempt(self, snapshot, active, _stamp(active))
        self.attempts.add(attempt)
        return attempt


def capture_context(hass, headers, *, device_id, client_type, session_id):
    from .direct_rich_pair import capture_pair
    from .profile_observation import capture_committed_lifetime
    from .profile_backend import profile_backend_entry_id
    from .session_runtime import SessionRuntimeManager
    pair = capture_pair(hass, headers, device_id=device_id, client_type=client_type)
    profile = None
    try:
        profile = capture_committed_lifetime(hass)
        require(profile is not None, "rich_frame_unavailable", 503)
        snapshot = profile.attempt()
        require(snapshot is not None, "rich_frame_unavailable", 503)
        relation = _relation(snapshot.household, device_id, client_type)
        owner = relation[0]
        manager = pair.domain.get("session_runtime_manager")
        require(type(manager) is SessionRuntimeManager, "rich_unavailable", 503)
        active = manager.current_active(owner)
        require(active is not None and active.session_id == session_id, "rich_not_allowed", 403)
        source = manager._history_source_contexts.get(session_id)
        source_id = profile_backend_entry_id(hass, owner)
        expected = {"backend_id": relation[8], "music_account_id": relation[10],
            "provider_entry_id": source_id, "provider_account_id": relation[11]}
        require(type(source) is dict and source == expected, "rich_not_allowed", 403)
        provider = pair.domain.get(source_id)
        require(provider is not None, "rich_not_allowed", 403)
        entry = provider.entry
        context = DirectRichContext(pair, profile, relation, owner, device_id, client_type,
            manager, session_id, active.broadcast, tuple(sorted(source.items())), provider,
            entry, entry.data, entry.options, getattr(provider, "_receiver_end_generation", 0), _EPOCH)
        context.attempt()
        _contexts.add(context)
        return context
    except BaseException as error:
        pair.retire()
        if profile is not None:
            profile.retire()
        if isinstance(error, RichError) or not isinstance(error, Exception):
            raise
        raise RichError("rich_unavailable", 503) from None
