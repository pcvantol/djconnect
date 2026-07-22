"""Restricted, runtime-scoped elapsed-time source for approved verification."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VerificationClock:
    """A deterministic monotonic source owned only by one verification Runtime.

    Production never creates this object: its Runtime continues to compose the
    existing monotonic source.  The clock has no persistence, transport or
    business-logic role; an approved scenario may only advance its own instance.
    """

    _elapsed_seconds: float = 0.0
    _advance_count: int = 0

    def monotonic(self) -> float:
        """Return elapsed monotonic seconds for the composed Runtime."""
        return self._elapsed_seconds

    def advance(self, seconds: float) -> float:
        """Advance deterministically; time may never move backwards or stand still."""
        if seconds <= 0:
            raise ValueError("verification clock advance must be positive")
        self._elapsed_seconds += seconds
        self._advance_count += 1
        return self._elapsed_seconds

    @property
    def elapsed_seconds(self) -> float:
        """Expose bounded verification evidence without exposing Runtime state."""
        return self._elapsed_seconds

    @property
    def advance_count(self) -> int:
        """Expose bounded verification evidence without exposing Runtime state."""
        return self._advance_count
