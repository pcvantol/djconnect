"""Owner-bound archive erasure through the existing Store and SQL writers.

A committed private intent is an obligation to finish, including after transport
expiry or restart. It is never a public receipt until BOTH owners acknowledge.
The paired API remains responsible for fresh authority and confirmation checks.
"""
from __future__ import annotations

import asyncio

from .persistence.history_deletion import HistoryDeletionRepository


class ArchiveDeletionCoordinator:
    """One serial cross-store operation, with fail-closed durable recovery."""

    def __init__(self, persistence, history, *, begin=None, end=None):
        self.persistence, self.history = persistence, history
        self.journal = HistoryDeletionRepository(persistence)
        self._lock = asyncio.Lock()
        self._barriers = {}
        self._begin, self._end = begin, end

    def _fence(self, intent):
        key = (intent['owner'], intent['operation_id'])
        self.history._deletion_barriers.add(key)
        if key not in self._barriers:
            self.persistence.history_retention_epoch = getattr(self.persistence, 'history_retention_epoch', 0) + 1
            self.persistence.history_retention_writes = getattr(self.persistence, 'history_retention_writes', 0) + 1
            # Install before callbacks: a failed invalidator must also recover.
            self._barriers[key] = None
        return key

    def _release(self, intent):
        key = (intent['owner'], intent['operation_id'])
        if key in self._barriers:
            if self._end is not None and self._barriers[key] is not None:
                self._end(intent, self._barriers[key])
            self.persistence.history_retention_epoch = getattr(self.persistence, 'history_retention_epoch', 0) + 1
            self.persistence.history_retention_writes -= 1
            self._barriers.pop(key)
        self.history._deletion_barriers.discard(key)

    async def _settle(self, intent, *, prepare=None, authorize=None):
        owner, operation_id, binding = (intent[k] for k in ('owner', 'operation_id', 'binding'))
        targets = frozenset(t[0] for t in intent['targets'])
        key = self._fence(intent)

        async def durable_plan(plan):
            plan = await prepare(plan) if prepare is not None else intent['store_plan']
            intent['store_plan'] = plan
            if self._begin is not None and self._barriers[key] is None:
                self._barriers[key] = self._begin(intent)
            return plan

        async def index(messages):
            result = await self.journal.async_scope_index(owner, messages, targets)
            intent['entry_index'] = result[0]
            return result

        plan = await self.history.async_erase_archived_sessions(
            owner, targets, prepare_intent=durable_plan, entry_index=index)
        await self.journal.async_store_erased(owner, operation_id, binding)
        result = await self.journal.async_complete(
            owner, operation_id, binding,
            lambda tx: self.journal.erase_sql(tx, owner, targets, plan),
            authorize=authorize, finalize_authorize=authorize)
        self._release(intent)
        return result

    async def async_recover(self):
        """Called before startup reconciliation, maintenance or private serving."""
        async with self._lock:
            pending = await self.journal.async_pending()
            # Every pending owner is closed before the first asynchronous save.
            for intent in pending:
                self._fence(intent)
            for intent in pending:
                await self._settle(intent)
            return len(pending)

    async def async_delete(self, *, owner, operation_id, binding, digest, targets,
                           authorize, now_ms=None, expected_scope=None):
        """Private entry point; caller has checked the public detail revision."""
        async with self._lock:
            if not authorize():
                raise PermissionError("unauthorized")
            previous = await self.journal.async_lookup(owner, operation_id, binding, digest, now_ms=now_ms)
            if not authorize():
                raise PermissionError("unauthorized")
            if previous is not None:
                if previous['state'] == 'completed':
                    self._release(dict(owner=owner, operation_id=operation_id, binding=binding, **previous))
                    return previous['receipt']
                intent = dict(owner=owner, operation_id=operation_id, binding=binding, **previous)
                return await self._settle(intent, authorize=authorize)

            await self.journal.async_validate_targets(owner, targets, authorize=authorize)
            intent = dict(owner=owner, operation_id=operation_id, binding=binding, targets=targets)

            async def prepare(plan):
                if expected_scope is not None:
                    from .ask_dj_history import archive_scope_digest
                    if archive_scope_digest(plan) != expected_scope:
                        from .persistence.history_deletion import HistoryDeletionError
                        raise HistoryDeletionError('history_revision_conflict')
                await self.journal.async_reserve(
                    owner=owner, operation_id=operation_id, binding=binding, digest=digest,
                    targets=targets, store_plan=plan, now_ms=now_ms,
                    authorize=authorize, finalize_authorize=authorize)
                intent['store_plan'] = plan
                return plan

            try:
                return await self._settle(intent, prepare=prepare, authorize=authorize)
            except BaseException:
                # A failed admission may have happened before an intent existed.
                # A lost acknowledgement is different: inspect actual SQL state
                # before reopening Store or dropping any media/read barrier.
                pending = await self.journal.async_pending()
                if not any(i['owner'] == owner and i['operation_id'] == operation_id for i in pending):
                    await self.history.async_settle_rejected_deletion((owner, operation_id))
                    self._release(intent)
                raise


def deletion_coordinator(hass, history=None):
    """Reuse the same application coordinator and existing private Store owner."""
    from .const import DOMAIN
    from .ask_dj_history import AskDJHistoryManager
    from .persistence import persistence_service
    from .dj_response import invalidate_private_speech_sources
    domain = hass.data.setdefault(DOMAIN, {})
    service = persistence_service(hass)
    current = domain.get('history_deletion_coordinator')
    if current is not None and current.persistence is service:
        return current
    if history is None:
        history = domain.get('ask_dj_history_manager')
    if history is None:
        history = AskDJHistoryManager(hass)
        domain['ask_dj_history_manager'] = history

    def revoke(intent):
        for session_id, _ in intent['targets']:
            invalidate_private_speech_sources(hass, session_id=session_id)
        entries = {intent['entry_index'][m][1] for m in intent['store_plan']['redact_message_ids']
                   if m in intent.get('entry_index', {})}
        if entries:
            invalidate_private_speech_sources(hass, entry_ids=entries)

    def begin(intent):
        revoke(intent)
        media = getattr(service, 'session_image_owner', None)
        token = media.begin_history_change(owner=intent['owner']) if media is not None else None
        return media, token

    def end(intent, token):
        revoke(intent)
        if token is not None:
            media, value = token
            if media is not None:
                media.end_history_change(value, owner=intent['owner'])

    current = ArchiveDeletionCoordinator(service, history, begin=begin, end=end)
    domain['history_deletion_coordinator'] = current
    return current
