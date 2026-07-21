"""Provider-neutral startup reconciliation for durable Sessions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .sessions import INTERRUPTED, PersistentSession, PersistentSessionRepository
class SessionRecoveryPolicy(Protocol):
    def interruption_reason(self, session: PersistentSession) -> str: ...
class NoRecoveryAvailablePolicy:
    def interruption_reason(self, session: PersistentSession) -> str:
        return "startup_reconciliation"
@dataclass(frozen=True)
class StartupReconciliationResult:
    inspected: int = 0
    reconciled: int = 0
    interrupted: int = 0
    terminal: int = 0
    complete: bool = True
class PersistentSessionStartupReconciler:
    def __init__(self, repository: PersistentSessionRepository, policy: SessionRecoveryPolicy | None = None) -> None:
        self._repository = repository
        self._policy = policy or NoRecoveryAvailablePolicy()
    async def async_reconcile(self) -> StartupReconciliationResult:
        candidates = await self._repository.async_reconciliation_candidates()
        for session in candidates:
            await self._repository.async_transition(session.owner_profile_id, session.session_id, INTERRUPTED, reason=self._policy.interruption_reason(session))
        return StartupReconciliationResult(inspected=len(candidates), reconciled=len(candidates), interrupted=len(candidates))
