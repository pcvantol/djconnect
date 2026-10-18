"""Bounded B delivery accounting owned by the existing Runtime manager."""
from __future__ import annotations

from .display_admission import DisplayAdmissionError
from .display_projection import MAX_FRAME_BYTES


class DisplayLiveHub:
    """Runtime-owned transport accounting; transitions still use its sole lock."""
    def __init__(self, manager):
        self.manager = manager
        self.preauth = 0
        self.sources = {}
        self.connections = {}
        self.reserved_bytes = 0
        self.projections = 0
        self.projecting = {}
        self.peak_reserved_bytes = 0
        self.peak_projections = 0
        self.peak_preauth = 0

    def reserve_projection(self, display_id):
        size = 2 * MAX_FRAME_BYTES
        if (display_id in self.projecting or self.projections >= 8
                or self.reserved_bytes + size > 4 * 1024 * 1024):
            raise DisplayAdmissionError("display_capacity", 429)
        marker = object()
        self.projecting[display_id] = marker
        self.projections += 1
        self.reserved_bytes += size
        self.peak_reserved_bytes = max(self.peak_reserved_bytes, self.reserved_bytes)
        self.peak_projections = max(self.peak_projections, self.projections)
        def release():
            if self.projecting.get(display_id) is marker:
                del self.projecting[display_id]
                self.projections -= 1
                self.reserved_bytes -= size
        return release

    def reserve_preauth(self, source):
        if self.preauth >= 16 or self.sources.get(source, 0) >= 2:
            raise DisplayAdmissionError("display_capacity", 429)
        self.preauth += 1
        self.peak_preauth = max(self.peak_preauth, self.preauth)
        self.sources[source] = self.sources.get(source, 0) + 1

    def release_preauth(self, source):
        self.preauth -= 1
        count = self.sources[source] - 1
        if count:
            self.sources[source] = count
        else:
            del self.sources[source]


def display_live_hub(manager):
    hub = getattr(manager, "_display_live_hub", None)
    if hub is None:
        hub = manager._display_live_hub = DisplayLiveHub(manager)
    return hub
