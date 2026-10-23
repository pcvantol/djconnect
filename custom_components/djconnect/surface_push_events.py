"""Bounded semantic widget signals from the ORIGINAL accepted Broadcast.

No progress timer, replay listener, source fetch, grant renewal or content body
is transported. One worker retains at most one later original change digest.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
from uuid import UUID

from .surface_push_wire import canonical

CHANGES = frozenset({'playback_changed','track_changed','mood_changed','presence_changed',
    'persona_changed','dj_moment_published','session_flow_updated','presentation_published'})
ENDED = frozenset({'runtime_ended','broadcast_stopped'})


def fingerprint(frame):
    """Only meaningful display values; observation ticks never create content."""
    music,contribution = frame.get('now_playing') or {},frame.get('contribution') or {}
    value = {'state':frame.get('state'),'playback_state':frame.get('playback_state'),
        'mood':frame.get('mood'),
        'presence':frame.get('presence'),'persona':frame.get('persona'),
        'music':{k:music.get(k) for k in ('item_id','track','artist','album')},
        'contribution':{k:contribution.get(k) for k in ('moment_id','text','persona')}}
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def operation_id(now):
    # UUIDv7 is stamped at the original callback, never after an await/retry.
    return str(UUID(int=(now<<80)|(7<<76)|(secrets.randbits(12)<<64)|(2<<62)|secrets.randbits(62)))


class WidgetSignals:
    def __init__(self, service, row, broadcast):
        self.service,self.row,self.broadcast = service,row,broadcast
        self.coordinate = row.coordinate()
        self.closed,self.pending,self.task = False,None,None
        self.last = fingerprint(row.admission.projection())
        self.subscription = broadcast.register_subscription(self.changed)
        row.retire_callback = self.stop

    def current(self):
        registry = self.service.registry
        return (not self.closed and not self.service.closed
            and registry._entries.get(self.row.registration_id) is self.row
            and self.row.coordinate()==self.coordinate
            and self.row.live(registry.journal.now_ms()))

    def stop(self):
        if self.closed:
            return
        self.closed,self.pending = True,None
        self.broadcast.unsubscribe(self.subscription)
        key = self.row.registration_id
        if self.row.retire_callback == self.stop:
            self.row.retire_callback = None
        if self.service._signals.get(key) is self:
            self.service._signals.pop(key,None)
        if self.task is not None and self.task is not asyncio.current_task():
            self.task.cancel()
        # A retired watch must not keep the former owner/admission/Broadcast.
        self.row,self.broadcast,self.coordinate,self.last = None,None,{},""

    def changed(self, event):
        try:
            if not self.current() or event.get('event_type') in ENDED:
                self.stop()
                return
            if event.get('event_type') not in CHANGES:
                return
            # Build only an already accepted passive projection, synchronously.
            # Never retain the event payload or a new observation lease.
            signature = fingerprint(self.row.admission.projection())
            if signature==self.last:
                return
            self.last = signature
            self.pending = operation_id(self.service.registry.journal.now_ms())
            if self.task is None or self.task.done():
                self.task = self.service.spawn(self.work())
                if self.task is None:
                    self.pending = None
        except Exception:
            self.stop()  # No event/exception/source/body logging.

    async def work(self):
        try:
            while self.pending is not None and self.current():
                original,self.pending = self.pending,None
                await self.service.registry.signal_widget(self.row.admission,
                    self.coordinate,operation_id=original)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.stop()  # Unknown outcomes never trigger a new operation.
