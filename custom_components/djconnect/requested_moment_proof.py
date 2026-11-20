"""Private semantic admission for the existing Moment/persistence/speech owners."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import time


@dataclass(eq=False, repr=False)
class RequestedMomentProof:
    operation_id: str
    type_id: str
    subject_ref: str
    original_item_id: str
    original_media_identity: str
    guard: object
    deadline: float
    expires_at: str
    device: str
    binding: str
    moment_id: str = ""
    content_sha256: str = ""
    committed: bool = False
    delivered: bool = False
    automatic_cancelled: bool = False
    retained: bool = False
    entry_id: str | None = None
    semantic: tuple = ()

    def bind(self, moment):
        self.moment_id = moment.moment_id
        self.content_sha256 = hashlib.sha256(moment.content.encode()).hexdigest()
        self.semantic = self._semantic(moment)

    @staticmethod
    def _semantic(moment):
        return tuple(
            getattr(moment, key)
            for key in (
                "session_id",
                "moment_type",
                "knowledge_intent",
                "title",
                "summary",
                "source_fact",
                "source_attribution",
                "source_references",
                "generation_metadata",
                "narration_acceptance",
                "live_impression",
                "bulletin",
            )
        )

    def sources_current(self, moment):
        source = getattr(moment, "source_fact", None)
        if source is not None and (
            not source.eligible(self.original_media_identity, time.monotonic())
            or hashlib.sha256(self.original_media_identity.encode()).hexdigest()[:24]
            != self.original_item_id
        ):
            return False
        from .public_artist_narration import ResearchMomentAcceptance, admitted as researched

        if type(moment.narration_acceptance) is ResearchMomentAcceptance and not researched(moment):
            return False
        if moment.live_impression is not None:
            from .live_impression import admitted

            if not admitted(moment):
                return False
        if moment.bulletin is not None:
            from .bulletin_runtime import admitted

            if not admitted(moment):
                return False
        return True

    def valid(self, moment, *, require_committed=False):
        try:
            self.guard()
            return (
                moment.user_requested is self
                and moment.moment_id == self.moment_id
                and hashlib.sha256(moment.content.encode()).hexdigest() == self.content_sha256
                and self._semantic(moment) == self.semantic
                and self.sources_current(moment)
                and time.monotonic() < self.deadline
                and (self.committed or not require_committed)
                and moment.presentation_intent.visibility.value == "owner_only"
                and tuple(c.value for c in moment.presentation_intent.delivery_channels)
                == ("owner",)
            )
        except Exception:
            return False

    def data(self):
        return {
            "contract_version": 1,
            "operation_id": self.operation_id,
            "type_id": self.type_id,
            "subject_ref": self.subject_ref,
            "playback_item_id": self.original_item_id,
        }


def proof(moment):
    value = getattr(moment, "user_requested", None)
    return value if type(value) is RequestedMomentProof else None


def admitted(moment, *, committed=False):
    value = proof(moment)
    return value is not None and value.valid(moment, require_committed=committed)


def display_admission(moment):
    value = proof(moment)
    allowed = admitted(moment, committed=True) and value.delivered
    source = getattr(moment, "source_fact", None)
    deadline = value.deadline if value is not None else time.monotonic()
    if source is not None:
        from .native_moment_delivery import source_deadline

        deadline = min(deadline, source_deadline(source))
    receipt = getattr(moment, "narration_acceptance", None)
    from .public_artist_narration import ResearchMomentAcceptance

    if type(receipt) is ResearchMomentAcceptance:
        deadline = min(deadline, receipt.accepted.expires_at)
    if getattr(moment, "bulletin", None) is not None:
        deadline = min(deadline, moment.bulletin.candidate.monotonic_deadline)
    return {
        "contract_version": 1,
        "moment_id": moment.moment_id,
        "owner_only": True,
        "display_allowed": allowed and time.monotonic() < deadline,
        "expires_at": (
            datetime.fromisoformat(value.expires_at)
            + timedelta(seconds=min(0, deadline - value.deadline))
        ).isoformat()
        if value is not None
        else datetime.now(timezone.utc).isoformat(),
    }


def retained_provenance(entry):
    """Recognize only original request metadata inside an admitted retained entry.

    This never grants reading or processing: the existing history/source/owner
    service must already have admitted the original row before speech prepare.
    """
    value = entry.get("user_requested")
    if (
        type(value) is not dict
        or set(value)
        != {"contract_version", "operation_id", "type_id", "subject_ref", "playback_item_id"}
        or type(value.get("contract_version")) is not int
        or value["contract_version"] != 1
        or entry.get("kind") != "dj_moment"
        or not all(
            type(value.get(k)) is str
            for k in ("operation_id", "type_id", "subject_ref", "playback_item_id")
        )
    ):
        return False
    from .requested_moment_inventory import MOMENT_TYPES
    from .transport_operations import operation_created_ms, OperationError
    from uuid import uuid5, NAMESPACE_URL
    import re

    try:
        operation_created_ms(value["operation_id"])
    except (OperationError, KeyError):
        return False
    return (
        MOMENT_TYPES.get(value.get("type_id")) == entry.get("moment_type")
        and entry.get("moment_id")
        == "moment-"
        + uuid5(NAMESPACE_URL, "djconnect:requested-moment:" + value["operation_id"]).hex
        and isinstance(value.get("subject_ref"), str)
        and re.fullmatch(r"[A-Za-z0-9_-]{32}", value["subject_ref"]) is not None
        and isinstance(value.get("playback_item_id"), str)
        and re.fullmatch(r"[a-f0-9]{24}", value["playback_item_id"]) is not None
    )
