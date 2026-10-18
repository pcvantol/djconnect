"""Bounded Runtime-owned contribution ledger; no scheduling or content selection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
import time
import hashlib

DEFAULT = "balanced"
# minimum interval, contributions per track, contributions per rolling ten minutes
POLICIES = {
    "music_only": (0, 0, 0),
    "occasional": (180, 1, 2),
    "balanced": (90, 2, 4),
    "presenter": (45, 4, 8),
}


def canonical_presence(value: str) -> str:
    """Decode the one retired value without adding a selectable fifth choice."""
    if type(value) is not str:
        raise ValueError("invalid_presence")
    if value == "talkative":
        return "presenter"
    if value not in POLICIES:
        raise ValueError("invalid_presence")
    return value


@dataclass
class PresenceLedger:
    """Only successful publications debit; live settings never reset history."""
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    publications: tuple[float, ...] = ()
    # Saturating fixed buckets preserve old debits for the entire Session.
    # A hash collision can only suppress, never grant additional contributions.
    track_counts: bytearray = field(default_factory=lambda: bytearray(65536))
    last_at: float | None = None
    last_read_seconds: int = 0
    suppression_reason: str = ""
    total_published: int = 0
    persona_revision: int = 0

    @staticmethod
    def bucket(track_id: str) -> int:
        return int.from_bytes(hashlib.sha256(track_id.encode()).digest()[:2], "big")

    def reason(self, mode: str, track_id: str) -> str:
        now = self.clock()
        self.publications = tuple(t for t in self.publications if now - t < 600)
        gap, track_cap, window_cap = POLICIES[canonical_presence(mode)]
        if not track_cap:
            return "presence_music_only"
        if self.last_at is not None and now - self.last_at < max(gap, self.last_read_seconds - 5):
            return "presence_readable_interval"
        if track_id and self.track_counts[self.bucket(track_id)] >= track_cap:
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
        bucket = self.bucket(track_id)
        self.track_counts[bucket] = min(6, self.track_counts[bucket] + 1)
        self.total_published += 1
