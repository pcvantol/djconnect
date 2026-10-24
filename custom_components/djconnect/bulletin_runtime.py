"""Owner-only bulletin admission within the existing Session/Planner chain."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import time

from .bulletin_builder import BulletinCandidate, BulletinSession, BuilderError

LABELS = {"en": "DJ Bulletin", "nl": "DJ Bulletin", "de": "DJ-Bulletin",
    "fr": "Bulletin du DJ", "es": "Boletín del DJ"}


def session_snapshot(active, provider):
    """Private stable admission values; normal playback progress may replace Runtime."""
    return BulletinSession(active.session_id, str(id(active.broadcast)), str(id(provider)),
        active.settings_generation, active.settings_revision, active.persona_revision,
        active.mood_revision, active.presence_revision, active.dj_persona.value,
        active.selected_mood, active.selected_presence, active.locale)


@dataclass(frozen=True)
class BulletinWork:
    owner: str
    session: BulletinSession
    guard: object
    generate: object


def capture_work(manager, owner):
    active = manager.current_active(owner)
    provider = manager._bulletin_providers.get(owner)
    if (active is None or provider is None or provider[0] != active.session_id
            or active.broadcast.content_pending or not active.allows_proactive()
            or not callable(provider[3])):
        return None
    authority = provider[3]()  # Capture original entry/source/provider revisions BEFORE awaits.
    session = session_snapshot(active, provider)

    def guard():
        authority()
        current = manager.current_active(owner)
        if (current is None or manager._bulletin_providers.get(owner) is not provider
                or session_snapshot(current, provider) != session
                or current.broadcast.content_pending or not current.publication_context_is_current()):
            raise PermissionError("bulletin_original_context_changed")
    guard()
    return BulletinWork(owner, session, guard, provider[1])


@dataclass(frozen=True)
class BulletinProof:
    candidate: BulletinCandidate
    original_guard: object


def admitted(moment, *, monotonic=None, wall=None):
    proof = getattr(moment, "bulletin", None)
    if type(proof) is not BulletinProof or type(proof.candidate) is not BulletinCandidate:
        return False
    if not callable(proof.original_guard):
        return False
    try:
        proof.original_guard()
    except Exception:  # noqa: BLE001 - original authority fails closed at every delivery boundary.
        return False
    candidate = proof.candidate
    mono = time.monotonic() if monotonic is None else monotonic
    utc = time.time() if wall is None else wall
    return (moment.moment_type.value == "dj_bulletin"
        and moment.knowledge_intent.intent_type.value == "dj_bulletin"
        and moment.session_id == candidate.session.session_id
        and moment.moment_id == "moment-" + candidate.candidate_id[:32]
        and moment.content == candidate.text and not moment.summary
        and not moment.actions and not moment.artwork_url and not moment.source_attribution
        and moment.source_references == ("fixed_rss_metadata_v1",)
        and moment.presentation_intent.visibility.value == "session_shared"
        and tuple(c.value for c in moment.presentation_intent.delivery_channels) == ("broadcast", "owner", "shared")
        and moment.presentation_intent.dj_persona.value == candidate.session.persona
        and moment.presentation_intent.source_session_mood == (candidate.session.mood.strip() or "neutral")
        and candidate.eligible(session=candidate.session, now=utc, monotonic=mono))


def sources(moment):
    proof = getattr(moment, "bulletin", None)
    if type(proof) is not BulletinProof:
        return []
    return [{"provider": i.source_title, "url": i.source_url, "license": i.license,
        "title": i.title, "published_at": datetime.fromtimestamp(i.published_at, timezone.utc).isoformat()}
        for i in proof.candidate.items]


def create_moment(core, candidate, original_guard):
    session = candidate.session
    intent = replace(core._presentation_intent(session.mood, core.DJPersona(session.persona),
        reading_characters=len(candidate.text)), delivery_style="short source-grounded news story")
    language = session.locale.replace("_", "-").split("-", 1)[0].lower()
    return core.DJMoment(moment_id="moment-" + candidate.candidate_id[:32],
        session_id=session.session_id, created_at=core._timestamp(),
        moment_type=core.DJMomentType.DJ_BULLETIN,
        knowledge_intent=core.KnowledgeIntent(core.KnowledgeIntentType.DJ_BULLETIN,
            "Share two independently fresh public news developments."),
        presentation_intent=intent, title=LABELS[language], summary="", content=candidate.text,
        artwork_url=None, actions=(), source_references=("fixed_rss_metadata_v1",),
        generation_metadata=(("context_source", "fixed_rss_metadata_v1"),
            ("bulletin_schema", "1"), ("candidate_id", candidate.candidate_id)),
        bulletin=BulletinProof(candidate, original_guard))


async def publish_if_selected(manager, *, owner_profile_id, session_id, media_identity):
    """Only called AFTER the existing higher-priority music opportunity returned none."""
    service = manager._bulletin_service
    if service is None:
        return None
    ready = service.ready(owner_profile_id, session_id)
    if ready is None:
        return None
    builder, candidate, work = ready
    from . import session_runtime as core
    import copy
    try:
        async with manager._lock:
            work.guard()
            active = manager.current_active(owner_profile_id)
            opportunity = manager._intra_track_opportunities.get(owner_profile_id)
            if (active is None or active.session_id != session_id or opportunity is None
                    or opportunity.session_id != session_id or opportunity.media_identity != media_identity
                    or opportunity.pending or opportunity.blocked or opportunity.pending_transition is not None
                    or not active.allows_proactive()):
                return None
            playback = active.broadcast.state.playback
            now = manager._monotonic_source()
            age = now - opportunity.last_observed_monotonic
            if (playback.state != "playing" or playback.item_id != opportunity.item_id
                    or not 0 <= age <= 30 or opportunity.last_observed_position_ms is None
                    or playback.duration_ms is None or now < opportunity.resume_ready_at):
                return None
            withdrawn = False
            def original_guard():
                nonlocal withdrawn
                try:
                    if withdrawn or service.closed or manager._bulletin_service is not service:
                        raise PermissionError("bulletin_original_service_withdrawn")
                    work.guard()
                except Exception:
                    withdrawn = True
                    raise PermissionError("bulletin_original_authority_withdrawn") from None
            moment = create_moment(core, candidate, original_guard)
            position = max(playback.position_ms or 0,
                opportunity.last_observed_position_ms + int(age * 1000))
            remaining = (playback.duration_ms - position) / 1000
            planner = copy.deepcopy(active.planner)
            if planner.evaluate_bulletin_candidate(
                    ready=admitted(moment, monotonic=now),
                    duration=moment.presentation_intent.maximum_duration_seconds,
                    remaining=remaining) is None:
                return None
            def final_guard():
                work.guard()
                if (service.closed or manager._bulletin_service is not service
                        or not admitted(moment, monotonic=manager._monotonic_source())):
                    raise PermissionError("bulletin_publication_withdrawn")
            if await builder.take(candidate, session=work.session, guard=final_guard) is None:
                return None
            final_guard()
            if not await manager._async_persist_moment(active, moment, final_authorize=final_guard):
                return None
            final_guard()
            active.planner.__dict__.update(planner.__dict__)
            active.moment_engine.moments = (*active.moment_engine.moments, moment)
            active.publish_moment(moment)
            manager._record_performance_memory(owner_profile_id, active)
            return moment
    except (PermissionError, BuilderError):
        return None
