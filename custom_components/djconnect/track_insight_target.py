"""Exact, temporary owner target for the existing shared Track Insight service."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass
import hashlib
import json
import re
import time
from typing import Any

from .native_moment_delivery import admission, source_deadline
from .session_conversation import history_grant_revision
from .session_runtime import session_runtime_manager
from .track_insight import TrackInsightError

from .moment_navigation import (
    CAPABILITY as CAPABILITY,
    TTL_SECONDS as TTL_SECONDS,
    LABELS as LABELS,
    navigation as navigation,
)


@dataclass(frozen=True)
class TrackInsightTarget:
    track: tuple[tuple[str, Any], ...]
    model_context: dict
    reference: dict
    expires_at: float
    validate: Any

    def guard(self):
        self.validate()
        if time.monotonic() >= self.expires_at:
            raise TrackInsightError(
                "track_insight_target_expired",
                "The selected Track Insight target has expired.",
                status=410,
            )


async def resolve_target(
    hass,
    runtime,
    payload,
    *,
    owner_profile_id: str,
    reference: dict | None = None,
    allow_current: bool = True,
):
    """Only published exact media proof; never resolve names or substitute playback."""
    target = reference if reference is not None else payload.get("track_insight_target")
    if target is None:
        context = payload.get("conversation_context") or {}
        if context.get("selected_moment"):
            ref = context["selected_moment"]
            target = {
                "schema_version": 1,
                **ref,
                "action_id": "insight-" + str(ref.get("moment_id") or ""),
            }
        elif context.get("selected_entry"):
            from .session_conversation import query_service

            ref = context["selected_entry"]
            result = await query_service(hass).async_open_entry(
                owner_profile_id, ref["session_id"], ref["entry_id"]
            )
            mid = result["entry"].get("moment_id")
            if not mid:
                raise TrackInsightError(
                    "track_insight_target_unavailable",
                    "This entry has no qualified live detail target.",
                    status=410,
                )
            target = {
                "schema_version": 1,
                "session_id": ref["session_id"],
                "moment_id": mid,
                "action_id": "insight-" + mid,
            }
        else:
            if not allow_current:
                return None
            current = (
                await session_runtime_manager(hass).async_get_active(owner_profile_id)
                if owner_profile_id
                else None
            )
            if current is None:
                return None
            mid = current.broadcast.native_delivery().get("current_moment_id")
            offered = next(
                (m for m in current.broadcast.state.dj_moments if m.moment_id == mid), None
            )
            if offered is None or not any(navigation(a) for a in offered.actions):
                return None
            target = {
                "schema_version": 1,
                "session_id": current.session_id,
                "moment_id": mid,
                "action_id": "insight-" + mid,
            }
    if (
        not isinstance(target, dict)
        or set(target) != {"schema_version", "session_id", "moment_id", "action_id"}
        or type(target["schema_version"]) is not int
        or target["schema_version"] != 1
        or not all(
            isinstance(target[k], str) and 0 < len(target[k]) <= 128
            for k in ("session_id", "moment_id", "action_id")
        )
    ):
        raise TrackInsightError(
            "invalid_track_insight_target", "Invalid Track Insight target.", status=400
        )
    if not owner_profile_id:
        raise TrackInsightError(
            "track_insight_target_forbidden", "An authorized owner is required.", status=403
        )
    manager = session_runtime_manager(hass)
    active = await manager.async_get_active(owner_profile_id)
    if active is None or active.session_id != target["session_id"]:
        raise TrackInsightError(
            "track_insight_target_unavailable",
            "The selected Session is no longer active.",
            status=410,
        )
    moment = next(
        (m for m in active.broadcast.state.dj_moments if m.moment_id == target["moment_id"]), None
    )
    boundary = active.broadcast._moment_delivery_boundaries.get(target["moment_id"])
    from .session_facts import QualifiedSessionFact

    fact = getattr(moment, "source_fact", None)
    if (
        moment is None
        or boundary is None
        or moment.moment_type.value != "track"
        or not isinstance(fact, QualifiedSessionFact)
        or fact.provider not in {"MusicBrainz", "Wikidata"}
        or fact.license != "CC0-1.0"
        or not re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", fact.media_identity)
        or not any(
            (a := navigation(action)) and a["action_id"] == target["action_id"]
            for action in moment.actions
        )
    ):
        raise TrackInsightError(
            "track_insight_target_unqualified",
            "No qualified exact-track detail is available.",
            status=403,
        )
    grant = history_grant_revision(hass, owner_profile_id)
    style_revision = (active.mood_revision, active.persona_revision)
    expires = min(boundary.published_monotonic + TTL_SECONDS, source_deadline(fact))

    def validate():
        current = manager.current_active(owner_profile_id)
        if (
            current is None
            or current.session_id != target["session_id"]
            or history_grant_revision(hass, owner_profile_id) != grant
        ):
            raise TrackInsightError(
                "track_insight_target_withdrawn", "The target is no longer authorized.", status=410
            )
        if (current.mood_revision, current.persona_revision) != style_revision:
            raise TrackInsightError(
                "track_insight_context_changed",
                "The confirmed presentation style changed.",
                status=409,
            )
        published = next(
            (m for m in current.broadcast.state.dj_moments if m.moment_id == target["moment_id"]),
            None,
        )
        delivery = admission(
            moment,
            boundary,
            session_id=current.session_id,
            active=current.runtime_state.value == "active",
            flow_ids={i.moment_id for i in current.broadcast.state.session_flow.items},
            playback_item_id=current.broadcast.state.playback.item_id,
            playing=current.broadcast.state.playback.state == "playing",
            now=time.monotonic(),
        )
        if (
            published is not moment
            or delivery["qualification"] != "qualified"
            or not (delivery["current_display_allowed"] or delivery["active_flow_display_allowed"])
        ):
            raise TrackInsightError(
                "track_insight_target_withdrawn",
                "The target is no longer visible or qualified.",
                status=410,
            )

    from .ask_dj.dialogue import model_source, normalized_subjects

    model = model_source(
        {
            "archive_basis": "cc0_normalized_fields_v1",
            "text": moment.content,
            "qualified_fact_text": fact.copy_for(active.locale)[1],
            "source_attribution": dict(moment.source_attribution),
            "dialogue_subjects": normalized_subjects(fact),
        }
    )
    track = {
        **dict(boundary.track_snapshot),
        "uri": fact.media_identity,
        "media_identity": fact.media_identity,
        "backend": str(
            getattr(runtime, "profile_context_backend_id", "")
            or runtime.config.get("music_backend")
            or ""
        ),
        "_owner_scope": hashlib.sha256((owner_profile_id + ":" + grant).encode()).hexdigest()[:24],
        "subject_mode": "explicit",
        "is_playing": False,
        "progress_ms": None,
    }
    qualified = TrackInsightTarget(tuple(track.items()), model, dict(target), expires, validate)
    qualified.guard()
    return qualified


def current_knowledge_context(hass, profile_id, track, *, source_authority=None):
    """Exact current CC0 knowledge, independently of which Moment was published."""
    from .session_facts import QualifiedSessionFact
    from .ask_dj.dialogue import model_source, normalized_subjects
    if not callable(source_authority) or not source_authority():
        return None
    uri = track.get('_media_identity')
    if not profile_id or not re.fullmatch(r'spotify:track:[A-Za-z0-9]{22}', str(uri or '')):
        return None
    manager = session_runtime_manager(hass)
    active = manager.current_active(profile_id)
    opportunity = manager._intra_track_opportunities.get(profile_id)
    if active is None or opportunity is None:
        return None
    playback = active.broadcast.state.playback
    identity = hashlib.sha256(uri.encode()).hexdigest()[:24]
    if (opportunity.session_id != active.session_id or opportunity.media_identity != uri
            or opportunity.item_id != identity or playback.item_id != identity or playback.state != 'playing'
            or playback.title != track.get('title') or playback.artist != track.get('artist')):
        return None
    facts = [f for f in opportunity.qualified_facts if type(f) is QualifiedSessionFact
        and f.key in {'recording_credits','work_composers'} and f.provider == 'MusicBrainz'
        and f.license == 'CC0-1.0' and f.eligible(uri, time.monotonic())]
    if not facts or any(a.key == b.key and a != b for a in facts for b in facts):
        return None
    fact = min(facts, key=lambda f:(f.key, f.source_url))
    grant = history_grant_revision(hass, profile_id)
    from .current_track_insight import session_scope
    captured = (opportunity.generation, session_scope(active))
    withdrawn = False
    def guard():
        nonlocal withdrawn
        try:
            current = manager.current_active(profile_id)
            if (withdrawn or not source_authority()
                    or current is None or current.broadcast is not active.broadcast
                    or manager._intra_track_opportunities.get(profile_id) is not opportunity
                    or (opportunity.generation, session_scope(current)) != captured
                    or history_grant_revision(hass, profile_id) != grant
                    or active.broadcast.state.playback.item_id != identity
                    or active.broadcast.state.playback.state != 'playing'
                    or not any(f is fact for f in opportunity.qualified_facts)
                    or not fact.eligible(uri, time.monotonic())):
                raise TrackInsightError('track_insight_context_changed', 'The current qualified recording context changed.', status=409)
        except BaseException:
            withdrawn = True
            raise
    guard()
    context = model_source({'archive_basis':'cc0_normalized_fields_v1',
        'text':fact.copy_for(active.locale)[1], 'qualified_fact_text':fact.copy_for(active.locale)[1],
        'source_attribution':{'provider':fact.provider,'url':fact.source_url,'license':fact.license},
        'dialogue_subjects':normalized_subjects(fact)})
    if not context:
        return None
    return context, guard, hashlib.sha256(json.dumps([profile_id, grant, captured, fact.source_url,
        fact.observed_at, fact.source_expires_at, context],sort_keys=True).encode()).hexdigest(), active, source_deadline(fact)


async def resolve_current_knowledge(hass, profile_id, current):
    """User-requested exact CC0 detail, without requiring a published Moment.

    A playback descriptor is only a lookup key. Original Session/source authority
    and the independently qualified public recording fact remain mandatory.
    This does not create or amend an opportunity, publication or source grant.
    """
    from .current_track_insight import session_scope
    from .session_facts import QualifiedSessionFact, session_facts_resolver
    from .ask_dj.dialogue import model_source, normalized_subjects

    authority = current.knowledge_authority
    if not callable(authority) or not authority():
        return None
    current.guard()
    manager = session_runtime_manager(hass)
    active = manager.current_active(profile_id)
    if active is None:
        return None
    scope = session_scope(active)
    grant = history_grant_revision(hass, profile_id)
    uri = current.frame.uri
    identity = hashlib.sha256(uri.encode()).hexdigest()[:24]
    playback = active.broadcast.state.playback
    if (playback.item_id != identity or playback.state != "playing"
            or playback.title != current.track.get("title")
            or playback.artist != current.track.get("artist")
            or playback.target_name != current.observed.target_name):
        return None
    observed_catalog = getattr(current.observed, "catalog", {}) or {}
    # Only immutable scalar lookup anchors; no mutable provider payload or
    # caller-controlled metadata may change identity during a source await.
    catalog = {key: value for key, value in observed_catalog.items()
               if key in {"uri", "title", "artist", "isrc"} and type(value) is str}
    if (catalog.get("uri") != uri or catalog.get("title") != current.track.get("title")
            or catalog.get("artist") != current.track.get("artist")
            or not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}\d{7}", str(catalog.get("isrc") or "").upper())):
        return None
    withdrawn = False

    def guard():
        nonlocal withdrawn
        try:
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise asyncio.CancelledError
            current.guard()
            now = manager.current_active(profile_id)
            playback = now.broadcast.state.playback if now is not None else None
            if (withdrawn or not authority() or now is None or session_scope(now) != scope
                    or history_grant_revision(hass, profile_id) != grant
                    or playback.item_id != identity or playback.state != "playing"
                    or playback.title != current.track.get("title")
                    or playback.artist != current.track.get("artist")
                    or playback.target_name != current.observed.target_name):
                raise TrackInsightError("track_insight_context_changed",
                    "The current qualified recording context changed.", status=409)
        except BaseException:
            withdrawn = True
            raise

    guard()
    try:
        async with asyncio.timeout(min(5.0, max(0.0, current.original_deadline - time.monotonic()))):
            resolved = await session_facts_resolver(hass).resolve(
                catalog, authorize=guard, credits_only=True)
    except (TimeoutError, ValueError, TypeError, KeyError):
        guard()
        return None
    guard()
    facts = [fact for fact in resolved if type(fact) is QualifiedSessionFact
             and fact.key in {"recording_credits", "work_composers"}
             and fact.provider == "MusicBrainz" and fact.license == "CC0-1.0"
             and fact.eligible(uri, time.monotonic())]
    if not facts or any(a.key == b.key and a != b for a in facts for b in facts):
        return None
    fact = min(facts, key=lambda item: (item.key, item.source_url))
    context = model_source({"archive_basis": "cc0_normalized_fields_v1",
        "text": fact.copy_for(active.locale)[1], "qualified_fact_text": fact.copy_for(active.locale)[1],
        "source_attribution": {"provider": fact.provider, "url": fact.source_url, "license": fact.license},
        "dialogue_subjects": normalized_subjects(fact)})
    if not context:
        return None

    def fact_guard():
        guard()
        if not fact.eligible(uri, time.monotonic()):
            raise TrackInsightError("track_insight_context_changed",
                "The current qualified recording context expired.", status=409)

    deadline = min(current.original_deadline, source_deadline(fact))
    current.limit_deadline(deadline)
    fact_guard()
    fingerprint = hashlib.sha256(json.dumps([profile_id, grant, scope, fact.source_url,
        fact.observed_at, fact.source_expires_at, context], sort_keys=True).encode()).hexdigest()
    return context, fact_guard, fingerprint, active, deadline
