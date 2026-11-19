"""Confirmed owner archive deletion at the existing paired authority boundary."""
from __future__ import annotations

import hashlib
import json

from .hybrid_service import PairedAuthority
from .persistence.history_deletion import HistoryDeletionError
from .transport_operations import OperationError, operation_created_ms


class HistoryDeletionAuthority(PairedAuthority):
    """Shared history uses the same paired Profile authority on supported clients."""

    client_types = frozenset({'ios', 'macos', 'watchos', 'raspberry_pi', 'esp32'})


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _identifier(value, limit=200):
    return isinstance(value, str) and 0 < len(value) <= limit and value == value.strip()


async def async_handle_history_delete(hass, data, *, headers=None, operation="single"):
    """No HA-user fallback, implicit consent, lifecycle action or optimistic result."""
    from .history_deletion import deletion_coordinator
    from .session_conversation import query_service, SessionConversationError
    from .historical_projection_query import HistoricalProjectionAccessDenied
    from .session_history_projection import HistoryQueryError
    from .persistence.service import PersistenceError
    from .transport_delivery import register_delivery_admission
    from .history_entry_contract import request_version, version_context

    fields = {'device_id', 'client_type'}
    if operation == 'single':
        fields |= {'session_id', 'expected_revision', 'operation_id', 'confirmed'}
    elif operation == 'all':
        fields |= {'snapshot_id', 'operation_id', 'confirmed'}
    elif operation != 'snapshot':
        return {'success': False, 'error': 'invalid_history_delete_request'}, 400
    if (not isinstance(data, dict) or not fields <= set(data)
            or set(data) - fields - {'history_contract_version'}
            or (operation != 'snapshot' and data.get('confirmed') is not True)
            or (operation == 'single' and (not _identifier(data.get('session_id'))
                or not _identifier(data.get('expected_revision'), 4096)))
            or (operation == 'all' and not _identifier(data.get('snapshot_id')))):
        return {'success': False, 'error': 'invalid_history_delete_request'}, 400
    version_token = None
    coordinator = None
    owner = None
    try:
        if operation != 'snapshot':
            operation_created_ms(data['operation_id'])
        version_token = version_context.set(request_version(data.get('history_contract_version')))
        identity = {k: data[k] for k in ('device_id', 'client_type')}
        authority = await HistoryDeletionAuthority.resolve(hass, identity, headers or {})
        authority.validate_now()
        owner = authority.context.profile_id
        coordinator = deletion_coordinator(hass)
        query = query_service(hass, coordinator.history)
        fence = query._repository.retention_fence
        from .history_deletion_snapshots import deletion_snapshots
        from .session_history_projection import session_retained
        snapshots = deletion_snapshots(hass)
        if operation == 'snapshot':
            retention = await query._repository.async_retention_policy()
            rows = await coordinator.journal.async_terminal_records(owner)
            rows = [r for r in rows if session_retained(r, retention_days=retention[0])]
            targets = tuple((r['session_id'], r['revision']) for r in rows)
            ids = frozenset(t[0] for t in targets)
            scope = (await coordinator.history.async_archive_scope_digest(
                owner, ids, entry_index=lambda messages: coordinator.journal.async_scope_index(owner, messages, ids))
                if ids else '')
            basis = {'privacy': coordinator.history.scope_revision('profile:' + owner),
                     'retention': retention, 'fence': fence, 'records': rows}
            authority.validate_now()
            if query._repository.retention_fence != fence or fence[1]:
                raise HistoryDeletionError('history_delete_snapshot_conflict')
            # Recheck the captured set only. A new terminal Session is outside it.
            await coordinator.journal.async_validate_targets(owner, targets, authorize=lambda: True)
            authority.validate_now()
            result = snapshots.capture(owner, authority.binding, targets, scope, basis)
            register_delivery_admission(authority.validate_now)
            return result, 200
        key = (owner, data['operation_id'])
        prior_own = int(key in coordinator._barriers)
        fence = (fence[0] - prior_own, fence[1] - prior_own)
        target_ids = frozenset({data['session_id']}) if operation == 'single' else frozenset()
        snapshot = None
        digest = _hash({'session_id': data['session_id'], 'expected_revision': data['expected_revision']}
                       if operation == 'single' else {'snapshot_id': data['snapshot_id']})

        def authorize():
            authority.validate_now()
            manager = hass.data.get('djconnect', {}).get('session_runtime_manager')
            if any(getattr(runtime, 'session_id', None) in target_ids
                   for runtime in getattr(manager, '_active_by_profile', {}).values()):
                raise HistoryDeletionError('session_not_archived')
            own = int(key in coordinator._barriers)
            if query._repository.retention_fence != (fence[0] + own, fence[1] + own) or fence[1]:
                raise HistoryDeletionError('history_revision_conflict')
            if snapshot is not None:
                if (coordinator.history.scope_revision('profile:' + owner) != snapshot['basis']['privacy']
                        or any(not session_retained(r, retention_days=snapshot['basis']['retention'][0])
                               for r in snapshot['basis']['records'])):
                    raise HistoryDeletionError('history_delete_snapshot_conflict')
            return True

        previous = await coordinator.journal.async_lookup(owner, data['operation_id'], authority.binding, digest)
        if previous is not None:
            target_ids = frozenset(t[0] for t in previous['targets'])
        authorize()
        targets, scope = (), None
        if previous is None and operation == 'single':
            session = await query._session(owner, data['session_id'])
            if session['lifecycle_status'] not in {'ENDED', 'INTERRUPTED'}:
                raise HistoryDeletionError('session_not_archived')
            if session['revision'] != data['expected_revision']:
                raise HistoryDeletionError('history_revision_conflict')
            row = await query._repository.async_session_record(data['session_id'])
            if row is None:
                raise HistoryDeletionError('history_unavailable')
            if row['revision'] != session['_sql_revision']:
                raise HistoryDeletionError('history_revision_conflict')
            targets = ((data['session_id'], row['revision']),)
            scope = session['_deletion_scope']
        if previous is None and operation == 'all':
            snapshot = snapshots.get(owner, authority.binding, data['snapshot_id'])
            if not snapshot['targets']:
                raise HistoryDeletionError('invalid_history_delete_request')
            if (await query._repository.async_retention_policy() != snapshot['basis']['retention']
                    or fence != snapshot['basis']['fence']):
                raise HistoryDeletionError('history_delete_snapshot_conflict')
            targets, scope = snapshot['targets'], snapshot['scope']
            target_ids = frozenset(t[0] for t in targets)
            authorize()
        result = await coordinator.async_delete(
            owner=owner, operation_id=data['operation_id'], binding=authority.binding,
            digest=digest, targets=targets, authorize=authorize, expected_scope=scope)
        # Own completion deliberately advanced the epoch. Fresh paired authority
        # still gates delivery; never renew the original request or public scope.
        authority.validate_now()
        register_delivery_admission(authority.validate_now)
        receipt = {'success': True, 'schema_version': 1, 'operation_id': result['operation_id'],
                   'owner_profile_id': owner, 'deleted': True}
        if operation == 'single':
            receipt['deleted_session_id'] = data['session_id']
        else:
            receipt.update(snapshot_id=data['snapshot_id'], deleted_session_count=len(result['deleted_session_ids']))
        return receipt, 200
    except OperationError as error:
        code = 'invalid_history_delete_request' if error.code == 'invalid_operation_id' else error.code
        return {'success': False, 'error': code}, error.status
    except HistoryDeletionError as error:
        code = str(error)
        if operation == 'all' and code in {'history_revision_conflict', 'session_not_archived', 'history_unavailable'}:
            # Unknown/other-owner snapshot itself stays a private 404. A target
            # withdrawn after a known snapshot is a whole-operation conflict.
            if snapshot is not None:
                code = 'history_delete_snapshot_conflict'
        if code == 'history_delete_operation_expired':
            code = 'history_delete_operation_conflict'
        status = (400 if code == 'invalid_history_delete_request' else
                  404 if code == 'history_unavailable' else
                  503 if code in {'history_delete_capacity', 'history_delete_outcome_unknown'} else 409)
        return {'success': False, 'error': code}, status
    except HistoricalProjectionAccessDenied:
        return {'success': False, 'error': 'history_unavailable'}, 404
    except SessionConversationError as error:
        return {'success': False, 'error': error.code}, error.status
    except HistoryQueryError:
        return {'success': False, 'error': 'history_revision_conflict'}, 409
    except (PersistenceError, OSError, RuntimeError, ValueError):
        try:
            pending = await coordinator.journal.async_pending() if coordinator is not None else []
        except Exception:
            return {'success': False, 'error': 'history_delete_outcome_unknown'}, 503
        code = ('history_delete_outcome_unknown' if any(
            i['owner'] == owner and i['operation_id'] == data.get('operation_id') for i in pending)
                else 'history_unavailable')
        return {'success': False, 'error': code}, 503
    finally:
        if version_token is not None:
            version_context.reset(version_token)


async def async_handle_history_delete_status(hass, data, *, headers=None):
    """Status of the exact original archive operation; never executes a POST."""
    from .history_deletion import deletion_coordinator
    from .persistence.service import PersistenceError
    from .transport_delivery import register_delivery_admission
    base = {'device_id', 'client_type', 'contract_version', 'operation_id', 'operation'}
    mode = data.get('operation') if isinstance(data, dict) else None
    body_keys = {'session_id', 'expected_revision'} if mode == 'single' else {'snapshot_id'}
    if (not isinstance(mode, str) or mode not in {'single', 'all'} or set(data) != base | body_keys
            or type(data.get('contract_version')) is not int or data['contract_version'] != 1
            or any(not _identifier(data.get(k), 4096 if k == 'expected_revision' else 200) for k in body_keys)):
        return {'success': False, 'error': 'invalid_history_delete_request'}, 400
    try:
        operation_created_ms(data['operation_id'])
        authority = await HistoryDeletionAuthority.resolve(hass, {k: data[k] for k in ('device_id', 'client_type')}, headers or {})
        authority.validate_now()
        digest = _hash({k: data[k] for k in body_keys})
        result = await deletion_coordinator(hass).journal.async_operation_status(
            authority.context.profile_id, data['operation_id'], authority.binding, digest)
        authority.validate_now()
        register_delivery_admission(authority.validate_now)
        if result.get('receipt'):
            stored = result['receipt']
            result['receipt'] = {'success': True, 'schema_version': 1, 'operation_id': data['operation_id'],
                'owner_profile_id': authority.context.profile_id, 'deleted': True}
            if mode == 'single':
                result['receipt']['deleted_session_id'] = data['session_id']
            else:
                result['receipt'].update(snapshot_id=data['snapshot_id'], deleted_session_count=len(stored['deleted_session_ids']))
        return {'success': True, 'schema_version': 1, 'owner_profile_id': authority.context.profile_id,
                'operation_id': data['operation_id'], 'operation': mode, 'request_digest': digest,
                **{k: data[k] for k in body_keys}, **result}, 200
    except OperationError as error:
        return {'success': False, 'error': 'invalid_history_delete_request' if error.code == 'invalid_operation_id' else error.code}, error.status
    except HistoryDeletionError as error:
        return {'success': False, 'error': str(error)}, 409
    except (PersistenceError, OSError, RuntimeError, ValueError):
        return {'success': False, 'error': 'history_delete_outcome_unknown'}, 503
