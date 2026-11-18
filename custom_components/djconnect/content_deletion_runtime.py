"""Individual erasure at the existing Runtime-manager ownership boundary."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json


def moment_dependencies(moment):
    """Minimal explicit IDs, including ordinary transitions without genre proof."""
    metadata = dict(moment.generation_metadata)
    result = {metadata.get(key) for key in ('transition_from_moment_id', 'transition_to_moment_id')}
    relation = moment.genre_transition
    if relation is not None:
        result.update((relation.source_moment_id, relation.target_moment_id))
    return frozenset(value for value in result if isinstance(value, str) and value)


def moment_closure(active, identifiers):
    """Only explicit runtime Moment provenance; no text matching or adjacency."""
    result = set(identifiers)
    while True:
        added = {m.moment_id for m in active.broadcast.state.dj_moments
                 if moment_dependencies(m) & result}
        if added <= result:
            return frozenset(result)
        result.update(added)


def runtime_digest(manager, owner, moments):
    active = manager.current_active(owner) if manager is not None else None
    data = []
    if active is not None:
        selected = {mid for sid, mid in moments if sid == active.session_id}
        if selected:
            data = [active.session_id, active.planner.output.session_flow.flow_revision,
                    [m.as_dict() for m in active.broadcast.state.dj_moments if m.moment_id in selected]]
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def apply_runtime_content(manager, owner, scope):
    """Synchronous and idempotent; caller ALREADY holds manager → Store → SQL order."""
    if manager is None:
        return
    if not manager._lock.locked():
        raise RuntimeError('content_runtime_lock_required')
    active = manager.current_active(owner)
    if active is None:
        return
    identifiers = {m for s, m in scope['moments'] if s == active.session_id}
    if not identifiers:
        return
    broadcast = active.broadcast
    current = broadcast.native_delivery().get('current_moment_id')
    active.deleted_moment_ids.update(identifiers)
    broadcast.deleted_moment_ids.update(identifiers)
    # Removing the current contribution never promotes an old one to current.
    latest = next((m.moment_id for m in reversed(broadcast.state.dj_moments)
        if broadcast._moment_playback_item_ids.get(m.moment_id) == broadcast.state.playback.item_id), None)
    if current in identifiers or latest in identifiers:
        broadcast.content_current_withdrawn = True
        broadcast.invalidate_current_delivery()
    changed = any(m.moment_id in identifiers for m in broadcast.state.dj_moments)
    active.moment_engine.moments = tuple(m for m in active.moment_engine.moments if m.moment_id not in identifiers)
    for identifier in identifiers:
        active.prepared_presentations.pop(identifier, None)
        broadcast._moment_delivery_boundaries.pop(identifier, None)
        broadcast._moment_playback_item_ids.pop(identifier, None)
    broadcast._owner_only_moment_ids.difference_update(identifiers)
    broadcast.state = replace(broadcast.state,
        dj_moments=tuple(m for m in broadcast.state.dj_moments if m.moment_id not in identifiers),
        presentations=tuple(p for p in broadcast.state.presentations if p.source_moment_id not in identifiers))
    flow = active.planner.output.session_flow
    items = tuple(i for i in flow.items if i.moment_id not in identifiers)
    retained_old_flow = any(i.moment_id in identifiers for change in active.planner.flow_change_journal for i in change.flow.items)
    if changed or items != flow.items or retained_old_flow:
        from .session_runtime import SessionFlowChangeType
        # Retire old cached semantic snapshots rather than change their bodies
        # under existing revisions. Recovery must obtain the fresh revision.
        active.planner.dispose_flow_change_journal()
        flow = active.planner._commit_session_flow(replace(flow, items=items), SessionFlowChangeType.CONTENT_WITHDRAWN)
        broadcast.state = replace(broadcast.state, session_flow=flow)
        broadcast.replay_log = ()
        broadcast.recovery_cursor = None
        for events in broadcast._pending_subscriptions.values():
            events.clear()
    manager._record_performance_memory(owner, active)
    line = active.planner.discover_narrative_line
    if line is not None and line.source_moment_id in identifiers:
        active.planner.discover_narrative_line = None
    opportunity = getattr(manager, '_intra_track_opportunities', {}).get(owner)
    if opportunity is not None and opportunity.pending_transition is not None:
        decision = opportunity.pending_transition[0]
        if set(getattr(decision, 'transition_moment_ids', ())) & identifiers:
            opportunity.pending_transition = None


def finish_runtime_content(manager, owner, scope):
    """Publish current ordinary projection only once the operation is durable."""
    if manager is None:
        return
    active = manager.current_active(owner)
    if active is None:
        return
    if any(s == active.session_id for s, _ in scope['sessions']):
        active.broadcast.content_pending_moment_ids.difference_update(
            mid for sid, mid in scope['moments'] if sid == active.session_id)
        active.broadcast.content_pending = False
        if any(s == active.session_id for s, _ in scope['moments']):
            active.broadcast.update_forecast(active)
            active.broadcast.publish_session_flow(active.planner.output.session_flow)
