"""Fail-closed Phase A contract for existing production and credit metadata.

This module is deliberately not connected to Session Runtime. The current
producers do not carry qualified credit provenance through Track Insight or an
attribution-safe Moment projection; no current field may authorize new copy.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Iterable

SPOTIFY_POLICY_URL = "https://developer.spotify.com/policy"
_SPOTIFY_HANDLE = re.compile(r"^spotify:(track|album):([A-Za-z0-9]{22})$")
_RELEASE_DATE = re.compile(r"^[0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?$")


class CreditCategory(StrEnum):
    """Only credit-adjacent categories present in normalized Core sources."""

    TRACK_PERFORMER = "track_performer"
    ALBUM_ARTIST = "album_artist"
    ALBUM_RELEASE_DATE = "album_release_date"


@dataclass(frozen=True, slots=True)
class CreditSourceField:
    """Machine-readable policy for one *existing* normalized source field."""

    field_id: str
    source_provider: str
    producer_path: str
    value_path: str
    evidence_handle_path: str
    evidence_kind: str
    category: CreditCategory
    reliability_class: str
    min_confidence: float
    freshness: str
    max_age_seconds: int
    conflict_rule: str
    attribution_requirement: str
    rights_reference: str
    usage_rights_qualified: bool
    retention_class: str
    privacy_scope: str
    session_ready: bool
    renderer_safe: bool
    public_safe: bool
    blocker: str

    def as_dict(self) -> dict[str, object]:
        """Expose policy metadata only, never a provider response or fact."""
        return {**asdict(self), "category": self.category.value}


_FIELDS = (
    CreditSourceField(
        field_id="spotify_playback_track_artists",
        source_provider="spotify_web_api",
        producer_path="spotify_backend._normalize_playback",
        value_path="playback.artist",
        evidence_handle_path="playback.uri",
        evidence_kind="track",
        category=CreditCategory.TRACK_PERFORMER,
        reliability_class="provider_catalog_metadata_role_not_preserved",
        min_confidence=0.95,
        freshness="current_playback_observation",
        max_age_seconds=24 * 60 * 60,
        conflict_rule="suppress_all",
        attribution_requirement="spotify_link_and_mark",
        rights_reference=SPOTIFY_POLICY_URL,
        usage_rights_qualified=False,
        retention_class="runtime_only",
        privacy_scope="catalog_metadata_via_authorized_playback",
        session_ready=False,
        renderer_safe=False,
        public_safe=False,
        blocker="Track Insight drops the track URI and artist IDs; no credit-role or safe attribution projection exists.",
    ),
    CreditSourceField(
        field_id="spotify_album_artists",
        source_provider="spotify_web_api",
        producer_path="spotify_backend._normalize_album_item",
        value_path="albums[].artist",
        evidence_handle_path="albums[].uri",
        evidence_kind="album",
        category=CreditCategory.ALBUM_ARTIST,
        reliability_class="provider_catalog_metadata_album_role_only",
        min_confidence=0.95,
        freshness="album_query_observation",
        max_age_seconds=24 * 60 * 60,
        conflict_rule="suppress_all",
        attribution_requirement="spotify_link_and_mark",
        rights_reference=SPOTIFY_POLICY_URL,
        usage_rights_qualified=False,
        retention_class="runtime_only",
        privacy_scope="catalog_metadata_via_authorized_query",
        session_ready=False,
        renderer_safe=False,
        public_safe=False,
        blocker="Album search and artist-albums output is not bound to the observed Session track or Track Insight.",
    ),
    CreditSourceField(
        field_id="spotify_album_release_date",
        source_provider="spotify_web_api",
        producer_path="spotify_backend._normalize_album_item",
        value_path="albums[].release_date",
        evidence_handle_path="albums[].uri",
        evidence_kind="album",
        category=CreditCategory.ALBUM_RELEASE_DATE,
        reliability_class="provider_catalog_metadata_date_precision_not_preserved",
        min_confidence=0.95,
        freshness="album_query_observation",
        max_age_seconds=24 * 60 * 60,
        conflict_rule="suppress_all",
        attribution_requirement="spotify_link_and_mark",
        rights_reference=SPOTIFY_POLICY_URL,
        usage_rights_qualified=False,
        retention_class="runtime_only",
        privacy_scope="catalog_metadata_via_authorized_query",
        session_ready=False,
        renderer_safe=False,
        public_safe=False,
        blocker="The album query is not Session-bound; playback and Track Insight drop release date and attribution.",
    ),
)

CREDIT_SOURCE_FIELDS = MappingProxyType({field.field_id: field for field in _FIELDS})


def credit_source_inventory() -> list[dict[str, object]]:
    """Return a stable, JSON-serializable inventory of current source policy."""
    return [field.as_dict() for field in _FIELDS]


@dataclass(frozen=True, slots=True)
class CreditEvidence:
    """One normalized internal observation; never a provider payload."""

    field_id: str
    source_provider: str
    evidence_handle: str = field(repr=False)
    value: str = field(repr=False)
    confidence: float
    observed_at: datetime
    rights_reference: str
    attribution_url: str = field(repr=False)
    attribution_mark_visible: bool
    retention_class: str


@dataclass(frozen=True, slots=True)
class CreditDecision:
    """Internal decision; the audit form contains no fact or source identity."""

    eligible: bool
    reason: str
    category: CreditCategory | None = None
    value: str = field(default="", repr=False)

    def as_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "reason": self.reason,
            "category": self.category.value if self.category else None,
        }


def qualify_current_moment_credit(
    evidences: Iterable[CreditEvidence], *, field_id: str, now: datetime
) -> CreditDecision:
    """Fail closed for today's producers and renderer attribution boundary."""
    contract = CREDIT_SOURCE_FIELDS.get(field_id)
    if contract is None:
        return CreditDecision(False, "unqualified_field")
    return qualify_credit_evidence(evidences, contract=contract, now=now)


def qualify_credit_evidence(
    evidences: Iterable[CreditEvidence], *, contract: CreditSourceField, now: datetime
) -> CreditDecision:
    """Evaluate one field without letting a candidate define its own policy.

    A future producer must bind this policy to a trusted adapter and provide
    safe attribution before setting ``session_ready`` and ``renderer_safe``.
    This generic evaluator is testable; only the fixed inventory is callable
    through the current-Moment entry point above.
    """
    candidates = tuple(evidences)
    if not candidates:
        return CreditDecision(False, "no_source")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        return CreditDecision(False, "invalid_clock")
    values: set[str] = set()
    handles: set[str] = set()
    for candidate in candidates:
        reason = _reject_reason(candidate, contract, now)
        if reason:
            return CreditDecision(False, reason)
        values.add(" ".join(candidate.value.split()).casefold())
        handles.add(candidate.evidence_handle)
    if len(values) != 1 or len(handles) != 1:
        return CreditDecision(False, "conflict")
    if not contract.session_ready or not contract.renderer_safe or not contract.public_safe:
        return CreditDecision(False, "producer_or_attribution_gate")
    if not contract.usage_rights_qualified:
        return CreditDecision(False, "rights_not_qualified")
    return CreditDecision(True, "qualified", contract.category, " ".join(candidates[0].value.split()))


def _reject_reason(candidate: CreditEvidence, contract: CreditSourceField, now: datetime) -> str:
    if candidate.field_id != contract.field_id or candidate.source_provider != contract.source_provider:
        return "source_mismatch"
    if contract.attribution_requirement != "spotify_link_and_mark" or contract.rights_reference != SPOTIFY_POLICY_URL:
        return "unqualified_rights_policy"
    if not isinstance(candidate.evidence_handle, str):
        return "missing_source_identity"
    match = _SPOTIFY_HANDLE.fullmatch(candidate.evidence_handle)
    if not match or match.group(1) != contract.evidence_kind:
        return "missing_source_identity"
    if (
        isinstance(candidate.confidence, bool)
        or not isinstance(candidate.confidence, (int, float))
        or not math.isfinite(candidate.confidence)
        or not contract.min_confidence <= candidate.confidence <= 1.0
    ):
        return "unreliable"
    observed = candidate.observed_at
    if not isinstance(observed, datetime) or observed.tzinfo is None or observed.utcoffset() is None:
        return "invalid_freshness"
    age_seconds = (now - observed).total_seconds()
    if age_seconds < 0 or age_seconds > contract.max_age_seconds:
        return "stale_or_future"
    if candidate.rights_reference != contract.rights_reference or candidate.retention_class != contract.retention_class:
        return "rights_or_retention_mismatch"
    expected_url = f"https://open.spotify.com/{match.group(1)}/{match.group(2)}"
    if candidate.attribution_url != expected_url or candidate.attribution_mark_visible is not True:
        return "attribution_unavailable"
    value = candidate.value
    if not isinstance(value, str) or not value.strip() or len(value) > 160 or any(ord(char) < 32 for char in value):
        return "invalid_value"
    if contract.category is CreditCategory.ALBUM_RELEASE_DATE and not _valid_release_date(value):
        return "invalid_value"
    return ""


def _valid_release_date(value: str) -> bool:
    if not _RELEASE_DATE.fullmatch(value):
        return False
    parts = [int(part) for part in value.split("-")]
    try:
        datetime(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
    except ValueError:
        return False
    return True
