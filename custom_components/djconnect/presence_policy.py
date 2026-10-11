"""Bounded Runtime-owned contribution ledger; no scheduling or content selection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import time

DEFAULT = "balanced"
# minimum interval, contributions per track, contributions per rolling ten minutes
POLICIES = {
    "music_only": (0, 0, 0),
    "occasional": (180, 1, 2),
    "balanced": (35, 3, 6),
    "talkative": (35, 4, 10),
    "presenter": (35, 6, 16),
}


@dataclass
class PresenceLedger:
    """Only successful publications debit; live settings never reset history."""
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    publications: tuple[float, ...] = ()
    track_counts: dict[str, int] = field(default_factory=dict)
    last_at: float | None = None
    last_read_seconds: int = 0
    suppression_reason: str = ""
    total_published: int = 0

    def reason(self, mode: str, track_id: str) -> str:
        now = self.clock()
        self.publications = tuple(t for t in self.publications if now - t < 600)
        gap, track_cap, window_cap = POLICIES[mode]
        if not track_cap:
            return "presence_music_only"
        if self.last_at is not None and now - self.last_at < max(gap, self.last_read_seconds - 5):
            return "presence_readable_interval"
        if self.track_counts.get(track_id, 0) >= track_cap:
            return "presence_track_budget"
        if len(self.publications) >= window_cap:
            return "presence_rolling_budget"
        return ""

    def admits(self, mode: str, track_id: str) -> bool:
        self.suppression_reason = self.reason(mode, track_id)
        return not self.suppression_reason

    def commit(self, track_id: str, read_seconds: int) -> None:
        now = self.clock()
        self.publications = (*self.publications, now)
        self.last_at = now
        self.last_read_seconds = read_seconds
        self.track_counts[track_id] = self.track_counts.get(track_id, 0) + 1
        if len(self.track_counts) > 128:
            self.track_counts.pop(next(iter(self.track_counts)))
        self.total_published += 1
