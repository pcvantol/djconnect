"""Explicit owner confirmation and read-only original-operation reconciliation."""
from __future__ import annotations

from datetime import UTC, datetime
import re
import secrets
import time

from .history_deletion_api import HistoryDeletionAuthority
from .persistence.content_deletion import MAX_UNITS, scope_digest
from .persistence.history_deletion import HistoryDeletionError
from .transport_operations import OperationError, operation_created_ms

_ID = re.compile(r'[A-Za-z0-9_.:\-]{1,200}\Z')
_TOKEN = re.compile(r'[A-Za-z0-9_-]{43}\Z')


class ContentConfirmations:
    """Opaque, bounded, nonrenewing five-minute process-local confirmations."""

    def __init__(self, *, monotonic=None):
        self._mono = monotonic or time.monotonic
        self._records = {}

    def capture(self, owner, binding, snapshot, privacy, fence):
        now = self._mono()
        self._records = {k: v for k, v in self._records.items() if now <= v['deadline']}
        scope, plan = snapshot['scope'], snapshot['plan']
        size = (len(scope['entries']) + len(scope['moments']) + len(scope['request_hashes'])
                + len(plan['remove_message_ids']) + len(plan['redact_message_ids']))
        if (size > MAX_UNITS or len(self._records) >= 128
                or sum(v['owner'] == owner for v in self._records.values()) >= 16
                or sum(v['size'] for v in self._records.values()) + size > 20_000):
            raise HistoryDeletionError('content_delete_capacity')
        token = secrets.token_urlsafe(32)
        self._records[token] = dict(owner=owner, binding=binding, snapshot=snapshot,
                                   privacy=privacy, fence=fence, deadline=now + 300, size=size)
        wall = time.time()
        return {'success': True, 'schema_version': 1, 'owner_profile_id': owner,
                'confirmation_id': token, 'target': snapshot['selector'], 'unit': scope['unit'],
                'affected_entries': [{'session_id': s, 'entry_id': e, 'disposition': mode}
                                     for s, e, _, _, mode in scope['entries']],
                'removed_message_ids': plan['remove_message_ids'],
                'unavailable_message_ids': plan['redact_message_ids'],
                'affected_moments': [{'session_id': s, 'moment_id': m} for s, m in scope['moments']],
                'fenced_request_count': len(scope['request_hashes']),
                'music_playback_undone': False,
                'created_at': datetime.fromtimestamp(wall, UTC).isoformat(),
                'expires_at': datetime.fromtimestamp(wall + 300, UTC).isoformat()}

    def get(self, owner, binding, token):
        record = self._records.get(token)
        if record is None or record['owner'] != owner:
            raise HistoryDeletionError('content_unavailable')
        if record['binding'] != binding or self._mono() > record['deadline']:
            raise HistoryDeletionError('content_delete_scope_conflict')
        return record


def confirmations(hass):
    return hass.data.setdefault('djconnect', {}).setdefault('content_confirmations', ContentConfirmations())


def _valid_selector(selector):
    return (type(selector) is dict and set(selector) == {'kind', 'session_id', 'target_id'}
            and isinstance(selector['kind'], str)
            and selector['kind'] in {'entry', 'moment', 'message', 'request'}
            and isinstance(selector['session_id'], str)
            and (not selector['session_id'] or _ID.fullmatch(selector['session_id']))
            and isinstance(selector['target_id'], str) and _ID.fullmatch(selector['target_id'])
            and (selector['kind'] not in {'entry', 'moment'} or bool(selector['session_id'])))


async def async_handle_content_delete(hass, data, *, headers=None, operation='delete'):
    """Identity comes only from the existing paired Profile; status never executes."""
    from .content_deletion import content_deletion_coordinator
    from .session_conversation import SessionConversationError
    from .persistence.service import PersistenceError
    from .transport_delivery import register_delivery_admission

    fields = {'device_id', 'client_type', 'contract_version'}
    if operation == 'prepare':
        fields.add('target')
    elif operation in {'delete', 'status'}:
        fields.update({'operation_id', 'confirmation_id'})
        if operation == 'delete':
            fields.add('confirmed')
    else:
        return {'success': False, 'error': 'invalid_content_delete_request'}, 400
    if (type(data) is not dict or set(data) != fields or type(data.get('contract_version')) is not int
            or data['contract_version'] != 1
            or (operation == 'prepare' and not _valid_selector(data.get('target')))
            or (operation == 'delete' and data.get('confirmed') is not True)
            or (operation != 'prepare' and (not isinstance(data.get('confirmation_id'), str)
                or not _TOKEN.fullmatch(data['confirmation_id'])))):
        return {'success': False, 'error': 'invalid_content_delete_request'}, 400
    try:
        if operation != 'prepare':
            operation_created_ms(data['operation_id'])
        authority = await HistoryDeletionAuthority.resolve(hass, {k: data[k] for k in ('device_id', 'client_type')}, headers or {})
        authority.validate_now()
        owner, binding = authority.context.profile_id, authority.binding
        coordinator = content_deletion_coordinator(hass)
        if operation == 'status':
            result = await coordinator.journal.async_content_status(owner, data['operation_id'], binding,
                scope_digest({'confirmation_id': data['confirmation_id']}))
            authority.validate_now()
            register_delivery_admission(authority.validate_now)
            if result.get('receipt') is not None:
                result['receipt'] = {**result['receipt'], 'confirmation_id': data['confirmation_id']}
            return {'success': True, 'schema_version': 1, 'owner_profile_id': owner,
                    'operation_id': data['operation_id'], 'confirmation_id': data['confirmation_id'],
                    'request_digest': scope_digest({'confirmation_id': data['confirmation_id']}), **result}, 200
        fence = coordinator.repository.retention_fence
        if operation == 'prepare':
            snapshot = await coordinator.async_preview(owner, data['target'], authorize=authority.validate_now)
            authority.validate_now()
            if fence != coordinator.repository.retention_fence or fence[1]:
                raise HistoryDeletionError('content_delete_scope_conflict')
            result = confirmations(hass).capture(owner, binding, snapshot,
                coordinator.history.scope_revision('profile:' + owner), fence)
            register_delivery_admission(authority.validate_now)
            return result, 200
        key = owner, data['operation_id']
        own = int(key in coordinator._barriers)
        fence = fence[0] - own, fence[1] - own
        digest = scope_digest({'confirmation_id': data['confirmation_id']})
        previous = await coordinator.journal.async_content_operation(owner, data['operation_id'], binding, digest=digest)
        record = None if previous is not None else confirmations(hass).get(owner, binding, data['confirmation_id'])

        def authorize():
            authority.validate_now()
            owned = int(key in coordinator._barriers)
            if coordinator.repository.retention_fence != (fence[0] + owned, fence[1] + owned) or fence[1]:
                raise HistoryDeletionError('content_delete_scope_conflict')
            if record is not None and (record['fence'] != fence
                    or coordinator.history.scope_revision('profile:' + owner) != record['privacy']):
                raise HistoryDeletionError('content_delete_scope_conflict')
            return True

        receipt = await coordinator.async_execute(owner=owner, operation_id=data['operation_id'], binding=binding,
            digest=digest, snapshot=record['snapshot'] if record else None, authorize=authorize)
        authority.validate_now()
        register_delivery_admission(authority.validate_now)
        return {**receipt, 'confirmation_id': data['confirmation_id']}, 200
    except OperationError as error:
        return {'success': False, 'error': 'invalid_content_delete_request' if error.code == 'invalid_operation_id' else error.code}, error.status
    except SessionConversationError as error:
        return {'success': False, 'error': error.code}, error.status
    except HistoryDeletionError as error:
        code = str(error)
        status = (400 if code.startswith('invalid_') else 404 if code in {'content_unavailable', 'history_unavailable'}
                  else 503 if code.endswith(('_capacity', '_outcome_unknown')) else 409)
        return {'success': False, 'error': code}, status
    except (PersistenceError, OSError, RuntimeError, ValueError):
        # No optimistic success and no automatic new operation after ambiguity.
        return {'success': False, 'error': 'content_delete_outcome_unknown'}, 503
