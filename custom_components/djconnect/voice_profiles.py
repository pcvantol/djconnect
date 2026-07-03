"""DJConnect voice profile helpers."""
from __future__ import annotations

from typing import Any

from .const import (
    CONF_VOICE_PROFILE,
    DEFAULT_VOICE_PROFILE,
    VOICE_PROFILE_CLASSIC_RADIO,
    VOICE_PROFILE_CLEAN_HOST,
    VOICE_PROFILE_ENERGY,
    VOICE_PROFILE_LATE_NIGHT,
    VOICE_PROFILES,
)
from .mood import (
    MOOD_ZONE_CHILL,
    MOOD_ZONE_ENERGY,
    MOOD_ZONE_GROOVE,
    MOOD_ZONE_PARTY,
    mood_zone_for_value,
)


VOICE_PROFILE_LABELS: dict[str, dict[str, str]] = {
    "en": {
        VOICE_PROFILE_CLASSIC_RADIO: "Classic radio host",
        VOICE_PROFILE_LATE_NIGHT: "Late-night radio",
        VOICE_PROFILE_ENERGY: "Energy host",
        VOICE_PROFILE_CLEAN_HOST: "Clean host",
    },
    "nl": {
        VOICE_PROFILE_CLASSIC_RADIO: "Klassieke radiopresentator",
        VOICE_PROFILE_LATE_NIGHT: "Late-night radiopresentator",
        VOICE_PROFILE_ENERGY: "Energieke presentator",
        VOICE_PROFILE_CLEAN_HOST: "Strakke presentator",
    },
    "de": {
        VOICE_PROFILE_CLASSIC_RADIO: "Klassischer Radiomoderator",
        VOICE_PROFILE_LATE_NIGHT: "Late-Night-Radio",
        VOICE_PROFILE_ENERGY: "Energie-Moderator",
        VOICE_PROFILE_CLEAN_HOST: "Klarer Moderator",
    },
    "fr": {
        VOICE_PROFILE_CLASSIC_RADIO: "Animateur radio classique",
        VOICE_PROFILE_LATE_NIGHT: "Radio de nuit",
        VOICE_PROFILE_ENERGY: "Animateur énergique",
        VOICE_PROFILE_CLEAN_HOST: "Animateur sobre",
    },
    "es": {
        VOICE_PROFILE_CLASSIC_RADIO: "Presentador de radio clásico",
        VOICE_PROFILE_LATE_NIGHT: "Radio nocturna",
        VOICE_PROFILE_ENERGY: "Presentador enérgico",
        VOICE_PROFILE_CLEAN_HOST: "Presentador claro",
    },
}

VOICE_PROFILE_BY_MOOD_ZONE: dict[str, str] = {
    MOOD_ZONE_CHILL: VOICE_PROFILE_LATE_NIGHT,
    MOOD_ZONE_GROOVE: VOICE_PROFILE_CLASSIC_RADIO,
    MOOD_ZONE_ENERGY: VOICE_PROFILE_ENERGY,
    MOOD_ZONE_PARTY: VOICE_PROFILE_CLEAN_HOST,
}

_STYLE_TEXT: dict[str, dict[str, str]] = {
    "nl": {
        VOICE_PROFILE_CLASSIC_RADIO: (
            "Voice profile: klink als een herkenbare Nederlandse/Engelse radio-DJ: "
            "warm, strak, natuurlijk en professioneel. Gebruik radiopacing, geen "
            "overdreven typetjes en geen imitatie van een bekende presentator."
        ),
        VOICE_PROFILE_LATE_NIGHT: (
            "Voice profile: klink als late-night radio: rustig, warm, intiem en "
            "kort. Houd de energie laag tenzij de mood expliciet hoger is."
        ),
        VOICE_PROFILE_ENERGY: (
            "Voice profile: klink als een energieke radiohost: helder, vlot en "
            "enthousiast, maar niet schreeuwerig. Laat mood de intensiteit bepalen."
        ),
        VOICE_PROFILE_CLEAN_HOST: (
            "Voice profile: klink als een strakke, neutrale presentator: compact, "
            "duidelijk en zonder grapjes tenzij de opdracht daarom vraagt."
        ),
    },
    "en": {
        VOICE_PROFILE_CLASSIC_RADIO: (
            "Voice profile: sound like a recognizable radio host: warm, tight, "
            "natural and professional. Use radio pacing, no caricature and no "
            "imitation of a known presenter."
        ),
        VOICE_PROFILE_LATE_NIGHT: (
            "Voice profile: sound like late-night radio: calm, warm, intimate and "
            "brief. Keep energy low unless mood explicitly asks for more."
        ),
        VOICE_PROFILE_ENERGY: (
            "Voice profile: sound like an energetic radio host: clear, brisk and "
            "enthusiastic, but not shouty. Let mood control the intensity."
        ),
        VOICE_PROFILE_CLEAN_HOST: (
            "Voice profile: sound like a clean neutral host: compact, clear and "
            "without jokes unless the request asks for them."
        ),
    },
}


def normalize_voice_profile(value: Any) -> str:
    """Return a supported voice profile value."""
    profile = str(value or DEFAULT_VOICE_PROFILE).strip()
    return profile if profile in VOICE_PROFILES else DEFAULT_VOICE_PROFILE


def voice_profile_for_mood_or_config(conf: dict[str, Any], payload: dict[str, Any] | None = None) -> str:
    """Resolve the effective DJ voice profile, preferring realtime client mood."""
    payload = payload or {}
    mood_value = payload.get("mood") if payload.get("mood") is not None else payload.get("energy")
    zone = mood_zone_for_value(mood_value)
    if zone is not None:
        return VOICE_PROFILE_BY_MOOD_ZONE[zone.name]
    return normalize_voice_profile(conf.get(CONF_VOICE_PROFILE))


def voice_profile_options(language: str) -> dict[str, str]:
    """Return localized config-flow option labels."""
    lang = _language_key(language)
    labels = VOICE_PROFILE_LABELS.get(lang) or VOICE_PROFILE_LABELS["en"]
    return {profile: labels[profile] for profile in VOICE_PROFILES}


def voice_profile_style_text(conf: dict[str, Any], language: str = "en") -> str:
    """Return prompt guidance for the selected voice profile."""
    profile = normalize_voice_profile(conf.get(CONF_VOICE_PROFILE))
    lang = "nl" if str(language or "").lower().startswith("nl") else "en"
    return _STYLE_TEXT[lang][profile]


def voice_profile_style_text_for_payload(
    conf: dict[str, Any],
    payload: dict[str, Any] | None = None,
    language: str = "en",
) -> str:
    """Return prompt guidance for mood-resolved voice profile."""
    profile = voice_profile_for_mood_or_config(conf, payload)
    lang = "nl" if str(language or "").lower().startswith("nl") else "en"
    return _STYLE_TEXT[lang][profile]


def _language_key(language: str) -> str:
    value = str(language or "").lower()
    for lang in ("nl", "de", "fr", "es"):
        if value.startswith(lang):
            return lang
    return "en"
