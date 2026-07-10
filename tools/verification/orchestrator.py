"""Compatibility wrapper for verification orchestration lifecycle."""

from .core import VerificationCore


class VerificationOrchestrator(VerificationCore):
    pass


__all__ = ["VerificationOrchestrator"]
