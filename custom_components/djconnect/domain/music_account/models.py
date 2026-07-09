"""Provider account bindings for DJConnect Profiles and Households."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..models import clean_identifier


class MusicAccountKind(StrEnum):
    """Music Account ownership shape."""

    PERSONAL = "personal"
    SHARED = "shared"
    HOUSEHOLD = "household"


class MusicAccountState(StrEnum):
    """Music Account binding lifecycle."""

    ACTIVE = "active"
    DISABLED = "disabled"
    NEEDS_REAUTH = "needs_reauth"


@dataclass(frozen=True)
class MusicAccount:
    """A provider account binding without OAuth implementation."""

    account_id: str
    backend_id: str
    kind: MusicAccountKind
    display_name: str
    linked_profile_ids: frozenset[str] = field(default_factory=frozenset)
    provider_account_id: str = ""
    state: MusicAccountState = MusicAccountState.ACTIVE
    scopes: frozenset[str] = field(default_factory=frozenset)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate music account identity."""
        if not clean_identifier(self.account_id):
            raise ValueError("account_id is required")
        if not clean_identifier(self.backend_id):
            raise ValueError("backend_id is required")
        if not clean_identifier(self.display_name):
            raise ValueError("display_name is required")
