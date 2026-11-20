"""Explicit rich-Moment adapter inside the paired Ask DJ operation boundary.

Uses the same source resolver, Knowledge/Moment/narration/persistence/Flow owners.
The bounded RAM rows contain no independent durable intelligence or authority.
"""

from __future__ import annotations
import asyncio
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from uuid import uuid5, NAMESPACE_URL

from .requested_moment_inventory import (
    TYPE_KEYS,
    MAX_CAPTURES,
    CAPTURE_SECONDS,
    capture,
    descriptors,
    language,
    candidate_facts,
    feedback,
    loaded_facts,
)
from .requested_moment_proof import RequestedMomentProof, display_admission
from .transport_operations import OperationError, operation_created_ms

OPERATION = "ask_dj/moments/request"


def moment_identifier(identifier):
    return "moment-" + uuid5(NAMESPACE_URL, "djconnect:requested-moment:" + identifier).hex


@dataclass
class Request:
    identifier: str
    captured: object
    type_id: str
    pending_text: str
    cancelled: bool = False
    presentation_closed: bool = False
    state: str = "pending"
    error: str | None = None
    moment: object = None
    proof: object = None


class Book:
    def __init__(self, manager):
        self.manager = manager
        self.captures = {}
        self.requests = {}
        self.pending = {}

    def sweep(self):
        now = time.monotonic()
        self.captures = {
            k: v for k, v in self.captures.items() if now < v.captured_at + CAPTURE_SECONDS
        }
        self.requests = {
            k: v
            for k, v in self.requests.items()
            if v.state == "pending" or now < v.captured.captured_at + CAPTURE_SECONDS
        }


def book(hass, manager):
    data = hass.data["djconnect"]
    value = data.get("requested_moments")
    if value is None or value.manager is not manager:
        value = data["requested_moments"] = Book(manager)
    value.sweep()
    return value


def validate(payload, fields):
    if (
        type(payload) is not dict
        or set(payload) != set(fields) | {"contract_version", "device_id", "client_type"}
        or type(payload.get("contract_version")) is not int
        or payload["contract_version"] != 1
        or payload.get("client_type") not in {"ios", "macos"}
        or any(
            not isinstance(payload.get(k), str) or not 0 < len(payload[k]) <= 128 for k in fields
        )
    ):
        raise OperationError("invalid_request", 400)


def active_session(manager, authority, identifier):
    active = manager.current_active(authority.context.profile_id)
    authority.validate_now()
    if (
        active is None
        or active.session_id != identifier
        or str(active.runtime_state) != "active"
        or active.broadcast.content_pending
        or not active.publication_context_is_current()
    ):
        raise OperationError("moment_request_context_changed", 409)
    return active


async def inventory(hass, authority, payload):
    validate(payload, {"session_id"})
    from .session_runtime import session_runtime_manager

    manager = session_runtime_manager(hass)
    active = active_session(manager, authority, payload["session_id"])
    b = book(hass, manager)
    # Reuse one original menu capture while it remains valid; opening cannot
    # extend source evidence or churn server state into an unbounded registry.
    existing = next(
        (
            c
            for c in b.captures.values()
            if (c.profile, c.device, c.binding, c.session_id)
            == (
                authority.context.profile_id,
                authority.device,
                authority.binding,
                active.session_id,
            )
            and c.playback.item_id == active.broadcast.state.playback.item_id
            and c.facts == loaded_facts(manager, authority.context.profile_id, active)
        ),
        None,
    )
    if existing is not None:
        try:
            existing.current(manager, authority)
        except PermissionError:
            existing = None
    if existing is None:
        if len(b.captures) >= MAX_CAPTURES:
            raise OperationError("moment_request_capacity", 429)
        existing = capture(hass, authority, manager, active)
        b.captures[existing.reference] = existing
    return {
        "success": True,
        "contract_version": 1,
        "session_id": active.session_id,
        "language": language(active),
        "title": "Ask DJ: Moments",
        "types": descriptors(existing, manager),
    }, 200


def domain_response(request, *, initial=False):
    captured = request.captured
    result = None
    state = request.state
    if request.proof is not None and request.proof.committed:
        state = "accepted"
        admission = display_admission(request.moment)
        admission["display_allowed"] = (
            admission["display_allowed"] and not request.presentation_closed
        )
        if not admission["display_allowed"]:
            state = "accepted_result_unavailable"
        else:
            result = {
                "moment": request.moment.as_dict(),
                "entry_id": request.proof.entry_id,
                "retention": "retained" if request.proof.retained else "not_retained",
                "history_state": "content_retained"
                if request.proof.retained
                else "receipt_only"
                if request.proof.entry_id
                else "not_retained",
                "presentation_admission": admission,
                "session_media": [],
            }
            result["moment"]["playback_item_id"] = captured.playback.item_id
            from .session_speech import moment_projection

            result["session_speech"] = {
                "schema_version": 1,
                "moments": [
                    moment_projection(
                        captured.original_active.broadcast,
                        request.moment,
                        autoplay=initial,
                        requested_initiator=initial,
                    )
                ],
            }
            broadcast = captured.original_active.broadcast
            native = next(
                (
                    a
                    for a in broadcast.native_delivery()["admissions"]
                    if a["moment_id"] == request.moment.moment_id
                ),
                {},
            )
            admission["requires_spotify_attribution"] = native.get(
                "requires_spotify_attribution", False
            )
            admission["source_expires_at"] = native.get("source_expires_at")
            media = broadcast.media_projector() if broadcast.media_projector is not None else []
            result["session_media"] = [
                m for m in media if m.get("moment_id") == request.moment.moment_id
            ]
    return {
        "success": state in {"pending", "accepted", "accepted_result_unavailable"},
        "contract_version": 1,
        "session_id": captured.session_id,
        "operation_id": request.identifier,
        "type_id": request.type_id,
        "language": language(captured.original_active),
        "state": state,
        "pending_text": request.pending_text,
        "message": feedback(captured.original_active, state),
        "result": result,
        "entry_id": request.proof.entry_id if request.proof and request.proof.committed else None,
        "moment_id": request.moment.moment_id
        if request.proof and request.proof.committed
        else None,
        "error": request.error,
    }


async def status(hass, authority, payload):
    validate(payload, {"session_id", "operation_id"})
    operation_created_ms(payload["operation_id"])
    from .session_runtime import session_runtime_manager

    manager = session_runtime_manager(hass)
    b = book(hass, manager)
    row = b.requests.get(payload["operation_id"])
    if row is not None:
        if (
            row.captured.profile,
            row.captured.device,
            row.captured.binding,
            row.captured.session_id,
        ) != (
            authority.context.profile_id,
            authority.device,
            authority.binding,
            payload["session_id"],
        ):
            raise OperationError("moment_request_unavailable", 404)
        authority.validate_now()
        try:
            row.captured.current(manager, authority)
        except PermissionError:
            if row.proof is None or not row.proof.committed:
                row.cancelled = True
                row.state = "denied"
                row.error = "moment_request_context_changed"
        return domain_response(row), 200
    # Recovery returns only the original owner-scoped durable locator. Rich
    # history is read through the existing source/privacy-qualified history API.
    repository = manager._historical_projections
    original = (
        await repository.async_requested_moment_entry(
            authority.context.profile_id, payload["session_id"], payload["operation_id"]
        )
        if repository is not None
        else None
    )
    authority.validate_now()
    if original is not None:
        body = json.loads(original["body"])
        if body.get("user_requested_owner") == {
            "device": authority.device,
            "binding": authority.binding,
        }:
            return {
                "success": True,
                "contract_version": 1,
                "session_id": payload["session_id"],
                "operation_id": payload["operation_id"],
                "state": "accepted_result_unavailable",
                "type_id": body.get("user_requested", {}).get("type_id"),
                "result": None,
                "entry_id": original["entry_id"],
                "moment_id": body.get("moment_id"),
                "error": None,
                "pending_text": None,
            }, 200
    raise OperationError("moment_request_unavailable", 404)


async def cancel(hass, authority, payload):
    validate(payload, {"session_id", "request_operation_id"})
    operation_created_ms(payload["request_operation_id"])
    from .session_runtime import session_runtime_manager
    from .hybrid_service import cancel_original_reaction

    manager = session_runtime_manager(hass)
    b = book(hass, manager)
    row = b.requests.get(payload["request_operation_id"])
    if row is not None:
        if (
            row.captured.profile,
            row.captured.device,
            row.captured.binding,
            row.captured.session_id,
        ) != (
            authority.context.profile_id,
            authority.device,
            authority.binding,
            payload["session_id"],
        ):
            raise OperationError("moment_request_unavailable", 404)
        row.cancelled = True  # Negative intent precedes any lock/Store await.
        row.presentation_closed = True
        if row.proof is not None:
            row.proof.automatic_cancelled = True
    async with manager._lock:
        authority.validate_now()
        if row is not None and row.proof is not None and row.proof.committed:
            return domain_response(row), 200  # Closing presentation cannot erase acceptance.
        await cancel_original_reaction(
            authority, payload["request_operation_id"], operation=OPERATION
        )
    if row is not None:
        row.state = "cancelled"
        row.error = "moment_request_cancelled"
        return {**domain_response(row), "success": True, "error": None}, 200
    return {
        "success": True,
        "contract_version": 1,
        "session_id": payload["session_id"],
        "operation_id": payload["request_operation_id"],
        "state": "cancelled",
        "result": None,
        "error": None,
        "pending_text": None,
    }, 200


def _guard(request, manager, authority):
    current = request.captured.current(manager, authority)
    if request.moment is not None and (
        request.moment.moment_id in current.deleted_moment_ids
        or request.moment.moment_id in current.broadcast.content_pending_moment_ids
    ):
        raise PermissionError("moment_request_content_withdrawn")
    if request.cancelled and not (request.proof is not None and request.proof.committed):
        raise PermissionError("moment_request_cancelled")
    return current


async def _fact(hass, request, manager, authority):
    from .session_facts import session_facts_resolver

    captured = request.captured
    facts = captured.facts
    candidates = [
        f
        for f in candidate_facts(captured, _guard(request, manager, authority))
        if f.key in TYPE_KEYS[request.type_id]
    ]
    if not candidates and captured.catalog:
        facts = await session_facts_resolver(hass).resolve(
            captured.catalog,
            authorize=lambda: _guard(request, manager, authority),
            credits_only=request.type_id in {"recording_story", "work_composers"},
        )
        captured.facts = facts
        candidates = [
            f
            for f in candidate_facts(captured, _guard(request, manager, authority))
            if f.key in TYPE_KEYS[request.type_id]
        ]
    # No query, narration or evidence from a different family is a fallback.
    active = _guard(request, manager, authority)
    return active.planner.select_requested_fact(
        facts=candidates,
        keys=TYPE_KEYS[request.type_id],
        locale=active.locale,
        allowed_intents=active.allowed_capability_intents,
        media_identity=captured.catalog.get("uri")
        or (captured.facts[0].media_identity if captured.facts else ""),
    )


async def _music(hass, request, manager, authority):
    from .session_runtime import DJMomentType
    from .narration_brief import NarratedText
    from .public_artist_narration import ResearchedArtistText
    from .live_impression import LiveImpressionText

    selected = await _fact(hass, request, manager, authority)
    if selected is None:
        return None, None
    intent, fact = selected
    active = _guard(request, manager, authority)
    knowledge = active.knowledge_engine.assemble_qualified_fact(
        intent=intent, fact=fact, media_identity=fact.media_identity, locale=active.locale
    )
    if knowledge is None:
        return None, None
    working = copy.deepcopy(active.moment_engine)
    # The selected explicit request is not a second spontaneous opportunity.
    # Exact existing accepted contributions are reused before this producer runs.
    working._track_keys = set()
    realization = working.preview_qualified_fact(
        fact=fact,
        selected_mood=active.selected_mood,
        persona=active.dj_persona,
        locale=active.locale,
        remaining_seconds=3600,
    )
    moment = working.create_track_context(
        session_id=active.session_id,
        knowledge_intent=intent,
        selected_mood=active.selected_mood,
        persona=active.dj_persona,
        locale=active.locale,
        insight=knowledge.as_insight(),
        fact_realization=realization,
    )
    if moment.moment_type is DJMomentType.SILENCE:
        return None, None
    from dataclasses import replace

    old = moment
    moment = replace(moment, moment_id=moment_identifier(request.identifier))
    working.moments = tuple(moment if m is old else m for m in working.moments)
    seed = moment.content
    moment, text, _, _ = await manager._async_realize_qualified_moment(
        active,
        fact,
        moment,
        working,
        request.captured.narration_provider,
        lambda: _guard(request, manager, authority),
        requested_type=request.type_id,
    )
    if (
        type(text) not in {NarratedText, ResearchedArtistText, LiveImpressionText}
        or str(text) == seed
        or (request.type_id == "live_impression") != (type(text) is LiveImpressionText)
    ):
        return None, None
    return moment, text


async def _bulletin(hass, request, manager, authority):
    from . import session_runtime as core
    from .bulletin_runtime import create_moment, BulletinManualSpeechUse
    from .bulletin_source_policy import private_headlines

    service = manager._bulletin_service
    if service is None:
        return None, None
    ready = await service.requested(
        request.captured.profile,
        lambda: _guard(request, manager, authority),
        provider=request.captured.bulletin_provider,
    )
    if ready is None:
        return None, None
    candidate, work = ready

    def guard():
        _guard(request, manager, authority)
        work.guard()

    use = (
        BulletinManualSpeechUse(candidate, guard)
        if private_headlines(candidate.items) is not None
        else None
    )
    return create_moment(core, candidate, guard, manual_speech_use=use), None


async def request(hass, authority, payload):
    validate(payload, {"session_id", "type_id", "subject_ref"})
    if payload["type_id"] not in TYPE_KEYS:
        raise OperationError("unsupported_moment_type", 400)
    from .session_runtime import session_runtime_manager, DeliveryChannel, DJMomentVisibility
    from .hybrid_service import current_operation_identity
    from .persona_reactions import withdraw_for_interaction
    from dataclasses import replace

    manager = session_runtime_manager(hass)
    active = active_session(manager, authority, payload["session_id"])
    b = book(hass, manager)
    captured = b.captures.get(payload["subject_ref"])
    if captured is None:
        raise OperationError("moment_request_subject_expired", 409)
    if (captured.profile, captured.device, captured.binding) != (
        authority.context.profile_id,
        authority.device,
        authority.binding,
    ):
        raise OperationError("moment_request_unavailable", 404)
    try:
        captured.current(manager, authority)
    except PermissionError:
        raise OperationError("moment_request_context_changed", 409) from None
    if captured.session_id != payload["session_id"]:
        raise OperationError("moment_request_context_changed", 409)
    identifier, expiry = current_operation_identity(authority)
    if identifier in b.requests:
        return domain_response(b.requests[identifier]), 200
    key = (captured.profile, captured.session_id)
    if key in b.pending:
        raise OperationError("moment_request_busy", 409)
    if len(b.requests) >= MAX_CAPTURES or manager._historical_projections is None:
        raise OperationError("moment_request_unavailable", 503)
    descriptor = next(
        x for x in descriptors(captured, manager) if x["type_id"] == payload["type_id"]
    )
    if not descriptor["available"]:
        raise OperationError(descriptor["reason"], 409)
    row = Request(identifier, captured, payload["type_id"], descriptor["pending_text"])
    b.requests[identifier] = row
    b.pending[key] = row
    active.broadcast.explicit_moment_pending = True
    from .transport_delivery import register_delivery_admission

    def delivery():
        authority.validate_now()
        if (
            row.proof is not None
            and row.proof.committed
            and not row.proof.valid(row.moment, require_committed=True)
        ):
            raise PermissionError("moment_request_result_withdrawn")

    register_delivery_admission(delivery)
    withdraw_for_interaction(hass, captured.profile)
    from .ask_dj.public_research import operation_source_outcome

    source_outcome = {}
    source_token = operation_source_outcome.set(source_outcome)
    try:
        async with asyncio.timeout(min(90, max(0, expiry / 1000 - time.time()))):
            moment, text = await (_bulletin if row.type_id == "dj_bulletin" else _music)(
                hass, row, manager, authority
            )
            _guard(row, manager, authority)
            if moment is None:
                row.state = (
                    "temporarily_unavailable" if source_outcome.get("temporary") else "not_found"
                )
                row.error = "moment_request_" + row.state
                return domain_response(row), 200
            deadline = min(
                captured.captured_at + CAPTURE_SECONDS,
                time.monotonic() + max(0, expiry / 1000 - time.time()),
            )
            if moment.source_fact is not None:
                from .native_moment_delivery import source_deadline

                deadline = min(deadline, source_deadline(moment.source_fact))
            if moment.bulletin is not None:
                deadline = min(deadline, moment.bulletin.candidate.monotonic_deadline)
            proof = RequestedMomentProof(
                identifier,
                row.type_id,
                captured.reference,
                captured.playback.item_id,
                moment.source_fact.media_identity if moment.source_fact is not None else "",
                lambda: _guard(row, manager, authority),
                deadline,
                datetime.fromtimestamp(
                    time.time() + max(0, deadline - time.monotonic()), timezone.utc
                ).isoformat(),
                authority.device,
                authority.binding,
            )
            moment = replace(
                moment,
                user_requested=proof,
                presentation_intent=replace(
                    moment.presentation_intent,
                    visibility=DJMomentVisibility.OWNER_ONLY,
                    delivery_channels=(DeliveryChannel.OWNER,),
                ),
            )
            proof.bind(moment)
            row.moment = moment
            row.proof = proof
            async with manager._lock:
                active = _guard(row, manager, authority)
                accepted = await manager._async_persist_moment(
                    active, moment, final_authorize=lambda: _guard(row, manager, authority)
                )
                if not accepted:
                    row.state = "cancelled" if row.cancelled else "denied"
                    row.error = (
                        "moment_request_cancelled"
                        if row.cancelled
                        else "moment_request_not_accepted"
                    )
                    return domain_response(row), 200
                # Durable acceptance is irreversible by cosmetic closing/cancel.
                row.state = "accepted"
                if proof.valid(moment, require_committed=True):
                    active.moment_engine.moments = (*active.moment_engine.moments, moment)
                    active.publish_moment(moment)
                    proof.delivered = any(m is moment for m in active.broadcast.state.dj_moments)
                    if proof.delivered:
                        if moment.source_fact is not None:
                            source = moment.source_fact
                            active.moment_engine._track_keys.add(
                                active.moment_engine.fact_key(source)
                            )
                            active.published_recording_context.commit(
                                source, time.monotonic(), moment.moment_id
                            )
                            if (
                                active.session_start_strategy.value == "discover"
                                and active.session_direction.direction.value == "exploring"
                            ):
                                active.published_album_context.commit(source, time.monotonic())
                        active = manager._record_performance_memory(captured.profile, active)
            if proof.delivered and proof.valid(moment, require_committed=True):
                # Existing publication TTS owner, captured for this requesting
                # actor only; never replace the Session's proactive callback.
                from .speaker_delivery import connect_automatic

                publication = connect_automatic(
                    hass,
                    authority.runtime,
                    active,
                    authority.identity,
                    authority.headers,
                    register=False,
                )
                publication(moment)
            if moment.live_impression is not None and proof.valid(moment, require_committed=True):
                from .live_impression_media import prepare
                from .session_artwork import attach_live_projection
                from types import SimpleNamespace

                photo = json.loads(moment.live_impression.payload_json)["photos"][0]
                await prepare(
                    hass,
                    None,
                    SimpleNamespace(profile_id=captured.profile),
                    session_id=captured.session_id,
                    target={"moment_id": moment.moment_id, "photo_id": photo["photo_id"]},
                    preloaded=(text.pixels, text.mime),
                )
                attach_live_projection(hass, captured.profile, captured.session_id)
            return domain_response(row, initial=True), 200
    except (PermissionError, OperationError):
        row.state = "cancelled" if row.cancelled else "denied"
        row.error = (
            "moment_request_cancelled" if row.cancelled else "moment_request_context_changed"
        )
        return domain_response(row), 200
    except asyncio.CancelledError:
        row.cancelled = True
        row.state = "cancelled"
        row.error = "moment_request_cancelled"
        raise
    except Exception:
        row.state = "temporarily_unavailable"
        row.error = "moment_request_temporarily_unavailable"
        return domain_response(row), 200
    finally:
        operation_source_outcome.reset(source_token)
        b.pending.pop(key, None)
        captured.original_active.broadcast.explicit_moment_pending = False
