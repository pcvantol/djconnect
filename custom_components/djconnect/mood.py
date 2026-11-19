"""DJConnect mood-zone helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MoodZone:
    """Resolved DJConnect mood zone."""

    value: int
    name: str
    prompt_hint: str


MOOD_ZONE_CHILL = "chill"
MOOD_ZONE_GROOVE = "groove"
MOOD_ZONE_ENERGY = "energy"
MOOD_ZONE_PARTY = "party"

_MOOD_ZONES = (
    (0, 24, MOOD_ZONE_CHILL, "rustig, warm, laag tempo, niet te druk"),
    (25, 59, MOOD_ZONE_GROOVE, "vloeiend, ritmisch, sociaal, medium energie"),
    (60, 84, MOOD_ZONE_ENERGY, "duidelijk meer drive, uptempo, actief"),
    (85, 100, MOOD_ZONE_PARTY, "maximale energie, feestelijk, herkenbaar, momentum vasthouden"),
)


def normalize_mood(value: Any) -> int | None:
    """Return a bounded integer mood value, or None when unavailable."""
    if value is None or value == "":
        return None
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return None


def mood_zone_for_value(value: Any) -> MoodZone | None:
    """Resolve a numeric DJConnect mood value to its Apple Watch mood zone."""
    mood = normalize_mood(value)
    if mood is None:
        return None
    for start, end, name, prompt_hint in _MOOD_ZONES:
        if start <= mood <= end:
            return MoodZone(mood, name, prompt_hint)
    return None


def enrich_payload_with_mood_zone(payload: dict[str, Any]) -> dict[str, Any]:
    """Add normalized mood and mood-zone metadata to a payload copy."""
    enriched = dict(payload)
    mood_value = (
        enriched.get("mood")
        if enriched.get("mood") is not None
        else enriched.get("energy")
    )
    zone = mood_zone_for_value(mood_value)
    if zone is None:
        return enriched
    enriched["mood"] = zone.value
    enriched["mood_zone"] = zone.name
    enriched["mood_zone_prompt"] = zone.prompt_hint
    return enriched


def mood_context_text(payload: dict[str, Any]) -> str:
    """Return compact prompt/debug text for a payload mood."""
    mood_value = (
        payload.get("mood")
        if payload.get("mood") is not None
        else payload.get("energy")
    )
    zone = mood_zone_for_value(mood_value)
    if zone is None:
        return "onbekend"
    return f"{zone.value}/100 ({zone.name}: {zone.prompt_hint})"


def mood_announcement_style_text(payload: dict[str, Any], language: str = "nl") -> str:
    """Return DJ announcement style guidance for a payload mood."""
    mood_value = (
        payload.get("mood")
        if payload.get("mood") is not None
        else payload.get("energy")
    )
    zone = mood_zone_for_value(mood_value)
    if zone is None:
        return ""
    if not str(language or "").lower().startswith("nl"):
        return (
            f"Automatically adapt the DJ announcement to mood={zone.value} "
            f"zone={zone.name}: {zone.prompt_hint}."
        )
    return (
        f"Pas de DJ-aankondiging automatisch aan op mood={zone.value} "
        f"zone={zone.name}: {zone.prompt_hint}."
    )


def mood_play_now_suffix(payload: dict[str, Any], language: str = "nl") -> str:
    """Return a short spoken suffix for deterministic Play Now responses."""
    mood_value = (
        payload.get("mood")
        if payload.get("mood") is not None
        else payload.get("energy")
    )
    zone = mood_zone_for_value(mood_value)
    if zone is None:
        return ""
    if not str(language or "").lower().startswith("nl"):
        return {
            MOOD_ZONE_CHILL: " I’ll keep it warm and easy.",
            MOOD_ZONE_GROOVE: " This should sit nicely in your groove.",
            MOOD_ZONE_ENERGY: " A little extra drive for the moment.",
            MOOD_ZONE_PARTY: " Let’s keep the momentum high.",
        }.get(zone.name, "")
    return {
        MOOD_ZONE_CHILL: " Ik houd het warm en rustig.",
        MOOD_ZONE_GROOVE: " Past mooi in je groove.",
        MOOD_ZONE_ENERGY: " Met wat extra drive erbij.",
        MOOD_ZONE_PARTY: " We houden de energie lekker hoog.",
    }.get(zone.name, "")
