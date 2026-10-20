"""Explicit B shared-screen allowlist over immutable accepted publications.

Never serialize an owner snapshot, Planner, Flow, private media or a proposal.
No provider I/O, publication, text rewriting, action execution or persistence.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import time

from .display_admission import DisplayAdmissionError
from .native_moment_delivery import admission, source_deadline
from .session_facts import QualifiedSessionFact
from .presence_policy import POLICIES

MAX_FRAME_BYTES = 128 * 1024


def _label(value):
    return getattr(value, "value", value)


def public_citation(source):
    """Citation provenance only, never excerpts, owner IDs or model receipts."""
    result={key:source[key] for key in ('provider','title','url','language','license','revision_url')}
    if source.get('provider') == 'Artist website':
        result.update({key:source[key] for key in ('usage_basis','publisher','wikidata_id')})
        result['official_site_reference']={key:source['official_site_reference'][key]
            for key in ('basis','entity_id','claim_id','revision')}
    elif source.get('provider') == 'Public web':
        result.update({key:source[key] for key in ('usage_basis','attributed_author','author_status')})
        result['work_reference']={key:source['work_reference'][key] for key in ('title','artist','url')}
    return result


def projection_release_guard(active, authority, state, snapshot):
    """Capture immutable original proof clocks; final check performs no encoding."""
    broadcast = active.broadcast
    sequence = snapshot["broadcast"]["snapshot_watermark"]
    selected_ids = {item["moment_id"] for item in snapshot["dj_moments"]}
    originals = {moment.moment_id: moment for moment in broadcast.state.dj_moments[-64:]
                 if moment.moment_id in selected_ids}
    deadlines = []
    for moment in originals.values():
        boundary = broadcast._moment_delivery_boundaries[moment.moment_id]
        deadlines.append(boundary.published_monotonic + moment.presentation_intent.maximum_duration_seconds)
        if isinstance(moment.source_fact, QualifiedSessionFact):
            deadlines.append(source_deadline(moment.source_fact))
        from .public_artist_narration import ResearchMomentAcceptance
        if type(moment.narration_acceptance) is ResearchMomentAcceptance:
            deadlines.append(moment.narration_acceptance.accepted.expires_at)
        if moment.observed_playback is not None:
            deadlines.append(moment.observed_playback.observed_at + 30)
        if moment.genre_transition is not None:
            deadlines.extend((source_deadline(moment.genre_transition.earlier),
                              moment.genre_transition.current.observed_at + 30))

    def current():
        share = state._shares.get(authority.share_id)
        if (state._displays.get(authority.display_id) is not authority or not authority.owner.valid()
                or share is None or not share.owner.valid() or state._clock() >= share.deadline
                or state._clock() >= authority.lease_deadline or broadcast.delivery_sequence != sequence
                or _label(broadcast.state.runtime_state) != "active"):
            return False
        available = {moment.moment_id: moment for moment in broadcast.state.dj_moments[-64:]}
        if any(available.get(key) is not moment or key in broadcast._invalidated_current_moment_ids
               for key, moment in originals.items()) or len(originals) != len(selected_ids):
            return False
        # This clock read follows all validation and serialization/preparation.
        return not deadlines or time.monotonic() < min(deadlines)

    return current


def shared_snapshot(active, authority, state, *, now=None, wall=None):
    """Call under the Runtime lock and recheck full authority at body release.

    Only latest bounded, currently display-qualified publications are examined.
    The existing native qualification validates exact source field/provider/
    license/subject, attribution, original publication/source clocks and proof.
    B additionally requires actual shared channel/audience, current playback and
    Flow membership. Its current owner/source stamp fences withdrawn accounts.
    """
    now = time.monotonic() if now is None else now
    wall = datetime.now(timezone.utc) if wall is None else wall
    broadcast = active.broadcast
    current = broadcast.state
    if (state._displays.get(authority.display_id) is not authority
            or not authority.owner.valid() or authority.owner.session_id != active.session_id
            or _label(current.runtime_state) != "active"):
        raise DisplayAdmissionError("display_grant_invalid", 401)
    share = state._shares.get(authority.share_id)
    if (share is None or not share.owner.valid() or share.deadline <= state._clock()
            or authority.lease_deadline <= state._clock()):
        raise DisplayAdmissionError("display_grant_invalid", 401)
    locale = current.locale
    if locale not in {"en", "nl", "de", "fr", "es"}:
        raise DisplayAdmissionError("display_context_changed", 409)
    playback = current.playback
    # No artwork, target/output, queue/up-next, backend/provider or account data.
    public_playback = {"state": playback.state}
    if playback.state in {"playing", "paused"} and playback.item_id:
        public_playback.update(item_id=playback.item_id, title=playback.title,
            artist=playback.artist, album=playback.album, updated_at=playback.updated_at)
        for field in ("duration_ms", "position_ms"):
            value = getattr(playback, field)
            if type(value) is int and value >= 0:
                public_playback[field] = value
        if re.fullmatch(r"https://open\.spotify\.com/track/[A-Za-z0-9]{22}", playback.source_url):
            public_playback["source_url"] = playback.source_url
    flow_ids = {item.moment_id for item in current.session_flow.items if item.moment_id}
    moments = []
    for moment in current.dj_moments[-64:]:
        presentation = moment.presentation_intent
        channels = {_label(channel) for channel in presentation.delivery_channels}
        if (moment.session_id != active.session_id or moment.moment_id not in flow_ids
                or _label(moment.moment_type) == "silence"
                or _label(presentation.visibility) not in {"session_shared", "public_broadcast"}
                or not channels.intersection({"broadcast", "shared"})):
            continue
        proof = admission(moment, broadcast._moment_delivery_boundaries.get(moment.moment_id),
            session_id=active.session_id, active=True, flow_ids=flow_ids,
            playback_item_id=playback.item_id, playing=playback.state == "playing", now=now)
        if proof["qualification"] != "qualified" or not proof["current_display_allowed"]:
            continue
        if moment.moment_id in broadcast._invalidated_current_moment_ids:
            continue
        # Keep published text and attribution byte-for-byte. Do not export generic
        # actions/knowledge goals/generation metadata or infer media rights from it.
        item = {"moment_id": moment.moment_id, "session_id": moment.session_id,
            "created_at": moment.created_at, "type": _label(moment.moment_type),
            "title": moment.title, "summary": moment.summary, "content": moment.content,
            "playback_item_id": playback.item_id, "display_expires_at": proof["display_expires_at"],
            "source_expires_at": proof["source_expires_at"],
            "source_attribution": dict(moment.source_attribution),
            "presentation_intent": {"source_session_mood": presentation.source_session_mood,
                "dj_persona": _label(presentation.dj_persona), "visual_theme": presentation.visual_theme,
                "maximum_duration_seconds": presentation.maximum_duration_seconds}}
        from .public_artist_narration import sources_for
        sources = sources_for(moment)
        if sources:
            # Only public citation fields; no excerpts, evidence spans, proof,
            # retrieval/owner metadata or model context cross this audience.
            item['sources'] = [public_citation(s) for s in sources]
        moments.append(item)
    # Display is a current surface, never an archive/catch-up history. Selecting
    # complete items does not truncate immutable facts or required source links.
    result = {"contract_version": 1, "issuer_epoch": state.issuer_epoch,
        "display_id": authority.display_id, "share_id": share.share_id,
        "share_generation": share.generation, "session_id": active.session_id,
        "lease_revision": authority.lease_revision,
        "session": {"session_id": active.session_id, "runtime_state": "active", "locale": locale},
        "playback": public_playback, "dj_moments": moments[-24:],
        "broadcast": {"snapshot_watermark": broadcast.delivery_sequence}}
    labels = {"mood": current.selected_mood, "persona": current.dj_persona, "presence": current.selected_presence}
    allowed = {"mood": {"chill", "groove", "energy", "party"},
        "persona": {"home_dj", "radio_dj", "club_dj", "festival_dj"}, "presence": set(POLICIES)}
    result["session_presentation"] = {key: _label(value) for key, value in labels.items()
                                      if _label(value) in allowed[key]}
    result["projection_revision"] = hashlib.sha256(json.dumps(result, sort_keys=True,
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()[:32]
    result["as_of"] = wall.isoformat()
    clock = state._clock()
    result["lease_expires_at"] = (wall + timedelta(seconds=authority.lease_deadline - clock)).isoformat()
    result["share_expires_at"] = (wall + timedelta(seconds=share.deadline - clock)).isoformat()
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode()) > MAX_FRAME_BYTES:
        raise DisplayAdmissionError("display_capacity", 503)
    return result
