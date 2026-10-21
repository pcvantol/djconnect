"""Bounded process-local bulk confirmations; no source body or client target set."""
from __future__ import annotations

from datetime import UTC, datetime
import secrets
import time

from .persistence.history_deletion import HistoryDeletionError


class ArchiveDeletionSnapshots:
    """Five-minute nonrenewing authority-bound snapshots; restart invalidates all."""

    def __init__(self, *, monotonic=None, capacity=128):
        self._mono = monotonic or time.monotonic
        self._records = {}
        self._capacity = capacity

    def capture(self, owner, binding, targets, scope, basis):
        now = self._mono()
        self._records = {k: r for k, r in self._records.items() if r['deadline'] >= now}
        if (len(self._records) >= self._capacity
                or sum(len(r['targets']) for r in self._records.values()) + len(targets) > 20_000
                or sum(r['owner'] == owner for r in self._records.values()) >= 16):
            raise HistoryDeletionError('history_delete_capacity')
        token = secrets.token_urlsafe(32)
        self._records[token] = dict(owner=owner, binding=binding, targets=targets, scope=scope,
                                    basis=basis, deadline=now + 300)
        wall = time.time()
        return {'success': True, 'schema_version': 1, 'owner_profile_id': owner,
                'snapshot_id': token, 'target_count': len(targets),
                'created_at': datetime.fromtimestamp(wall, UTC).isoformat(),
                'expires_at': datetime.fromtimestamp(wall + 300, UTC).isoformat()}

    def get(self, owner, binding, token):
        record = self._records.get(token)
        if record is None or record['owner'] != owner:
            raise HistoryDeletionError('history_unavailable')
        if record['binding'] != binding or self._mono() > record['deadline']:
            raise HistoryDeletionError('history_delete_snapshot_conflict')
        return record


def deletion_snapshots(hass):
    domain = hass.data.setdefault('djconnect', {})
    if 'history_deletion_snapshots' not in domain:
        domain['history_deletion_snapshots'] = ArchiveDeletionSnapshots()
    return domain['history_deletion_snapshots']
