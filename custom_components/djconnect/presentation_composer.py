"""Server-side composition of renderer-safe Presentations from DJMoments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SpeakerRole(StrEnum):
    """Semantic presentation role, never a voice or renderer identity."""

    DJ = "dj"
    SIDEKICK = "sidekick"


class SpeechPresentationMode(StrEnum):
    """The bounded first speech-composition modes."""

    PRIMARY_ONLY = "primary_only"
    PRIMARY_WITH_SIDEKICK = "primary_with_sidekick"


@dataclass(frozen=True)
class PresentationContext:
    """Shared Runtime-derived emotional and stylistic presentation context."""

    session_mood: str
    dj_persona: str
    session_direction: str
    session_energy: str
    presentation_style: str
    constraints: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_mood": self.session_mood,
            "dj_persona": self.dj_persona,
            "session_direction": self.session_direction,
            "session_energy": self.session_energy,
            "presentation_style": self.presentation_style,
            "constraints": dict(self.constraints),
        }


@dataclass(frozen=True)
class SpeechSegment:
    """One immutable renderer-safe segment for local role-to-voice mapping."""

    ordinal: int
    speaker_role: SpeakerRole
    text: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "speaker_role": self.speaker_role.value,
            "text": self.text,
        }


@dataclass(frozen=True)
class SpeechPresentation:
    """The first Presentation capability: ordered immutable speech segments."""

    mode: SpeechPresentationMode
    segments: tuple[SpeechSegment, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "segments": [segment.as_dict() for segment in self.segments],
        }


@dataclass(frozen=True)
class Presentation:
    """One immutable renderer-safe realization of exactly one source DJMoment."""

    presentation_id: str
    source_moment_id: str
    session_id: str
    source_moment_type: str
    context: PresentationContext
    speech: SpeechPresentation | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "presentation_id": self.presentation_id,
            "source_moment_id": self.source_moment_id,
            "session_id": self.session_id,
            "source_moment_type": self.source_moment_type,
            "context": self.context.as_dict(),
        }
        if self.speech is not None:
            result["speech"] = self.speech.as_dict()
        return result


@dataclass(frozen=True)
class PresentationComposer:
    """Compose presentations without owning planning, knowledge or rendering."""

    def compose(self, *, moment: Any, context: PresentationContext) -> Presentation:
        """Create one deterministic Presentation from one approved DJMoment.

        The Composer deliberately consumes only immutable source fields. Its
        optional Sidekick segment repeats the already-approved summary verbatim,
        which prevents new facts, knowledge retrieval or semantic expansion.
        """
        source_moment_id = _safe_text(getattr(moment, "moment_id", ""), 128)
        session_id = _safe_text(getattr(moment, "session_id", ""), 128)
        if not source_moment_id or not session_id:
            raise ValueError("Presentation requires an identified source DJMoment")

        moment_type = _enum_value(getattr(moment, "moment_type", ""))
        primary_text = _safe_text(getattr(moment, "content", ""), 1200)
        summary = _safe_text(getattr(moment, "summary", ""), 320)
        speech = self._compose_speech(
            moment=moment,
            primary_text=primary_text,
            summary=summary,
        )
        return Presentation(
            presentation_id=f"presentation-{source_moment_id}",
            source_moment_id=source_moment_id,
            session_id=session_id,
            source_moment_type=moment_type,
            context=context,
            speech=speech,
        )

    def _compose_speech(
        self, *, moment: Any, primary_text: str, summary: str
    ) -> SpeechPresentation | None:
        """Use the source's approved text only, with Primary Only as fallback."""
        if not primary_text:
            return None
        primary = SpeechSegment(ordinal=1, speaker_role=SpeakerRole.DJ, text=primary_text)
        if not self._is_sidekick_eligible(moment=moment, summary=summary):
            return SpeechPresentation(SpeechPresentationMode.PRIMARY_ONLY, (primary,))
        return SpeechPresentation(
            SpeechPresentationMode.PRIMARY_WITH_SIDEKICK,
            (
                primary,
                SpeechSegment(ordinal=2, speaker_role=SpeakerRole.SIDEKICK, text=summary),
            ),
        )

    @staticmethod
    def _is_sidekick_eligible(*, moment: Any, summary: str) -> bool:
        """Allow one bounded secondary role only for an approved Artist Story."""
        intent = getattr(moment, "knowledge_intent", None)
        intent_type = _enum_value(getattr(intent, "intent_type", ""))
        moment_type = _enum_value(getattr(moment, "moment_type", ""))
        return bool(summary) and intent_type == "artist_story" and moment_type == "artist"


def _enum_value(value: Any) -> str:
    candidate = getattr(value, "value", value)
    return _safe_text(candidate, 80)


def _safe_text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:limit]
