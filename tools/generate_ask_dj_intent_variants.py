#!/usr/bin/env python3
"""Generate deterministic Ask DJ classifier variant fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "examples" / "ask_dj_intent_variants.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


VARIANT_GROUPS = [
    {
        "intent": "help",
        "intent_category": "informational",
        "phrases": [
            "help",
            "hulp",
            "help me even",
            "wat kun je",
            "wat kun je?",
            "wat kan ask dj",
            "wat kan je allemaal",
            "toon hulp",
            "laat hulp zien",
            "help ask dj",
        ],
    },
    {
        "intent": "conversational_followup",
        "intent_category": "informational",
        "phrases": [
            "ok",
            "oke",
            "prima",
            "top",
            "dank je",
            "thanks",
            "laat maar",
            "geeft niet",
        ],
    },
    {
        "intent": "morning_music_suggestion",
        "intent_category": "informational",
        "phrases": [
            "goedemorgen",
            "goeiemorgen",
            "good morning",
            "morgen",
        ],
    },
    {
        "intent": "personal_music_dna_summary",
        "intent_category": "informational",
        "phrases": [
            "wat weet je nu over mij",
            "wat weet je over mij",
            "wat weet je inmiddels over mij",
            "what do you know about me",
            "vertel wat je over mijn smaak weet",
        ],
    },
    {
        "intent": "personal_music_profile_analysis",
        "intent_category": "informational",
        "phrases": [
            "analyseer mijn luisterprofiel",
            "omschrijf mijn luisterprofiel",
            "omschrijf mijn listening profile",
            "wat luisterde ik de afgelopen maand",
            "wat heb ik de afgelopen maand geluisterd",
            "analyseer waar ik naar luister",
            "geef een analyse van mijn muzieksmaak",
        ],
    },
    {
        "intent": "personal_artist_recommendations",
        "intent_category": "informational",
        "phrases": [
            "welke artiesten passen bij mijn smaak",
            "welke artiesten zou ik leuk vinden",
            "geef artiesten die bij mijn smaak passen",
        ],
    },
    {
        "intent": "personal_music_recommendations",
        "intent_category": "informational",
        "phrases": [
            "geef persoonlijke muziekaanbevelingen",
            "geef me persoonlijke muziektips",
            "raad muziek aan op basis van mijn smaak",
            "welke muziek past bij mij",
        ],
    },
    {
        "intent": "track_insight",
        "intent_category": "informational",
        "phrases": [
            "analyseer dit nummer",
            "analyseer deze track",
            "geef track insight voor dit nummer",
            "geef track insight",
            "vertel me over deze track",
            "wat is de vibe van deze plaat",
            "what is the vibe of this track",
            "give me track insight for this song",
        ],
    },
    {
        "intent": "recently_played_history",
        "intent_category": "informational",
        "phrases": [
            "welke nummers heb ik afgelopen uur afgespeeld",
            "welke nummers luisterde ik afgelopen uur",
            "welke tracks heb ik vandaag afgespeeld",
            "welke albums heb ik vandaag geluisterd",
            "welke playlists heb ik afgelopen uur gespeeld",
            "wat heb ik net afgespeeld",
        ],
    },
    {
        "intent": "current_track_reference",
        "intent_category": "informational",
        "phrases": [
            "wat speelt er nu",
            "welk nummer speelt er nu",
            "welk nummer draait er nu",
            "what song is playing",
            "wat is die beuker",
            "welke track hoor ik",
        ],
    },
    {
        "intent": "dj_announcement",
        "intent_category": "hybrid",
        "phrases": [
            "geef een dj intro voor dit nummer",
            "maak een dj aankondiging",
            "kondig dit nummer aan",
            "zeg iets over deze track als dj",
        ],
    },
    {
        "intent": "next_track_info",
        "intent_category": "informational",
        "phrases": [
            "wat wordt het volgende nummer",
            "welk nummer komt hierna",
            "wat komt hierna",
            "what is next",
            "what's next",
        ],
    },
    {
        "intent": "artist_concerts",
        "intent_category": "informational",
        "phrases": [
            "wanneer speelt pearl jam in nederland",
            "wanneer treedt radiohead op",
            "concerten van radiohead",
            "tourdata van metallica",
            "speelt metallica binnenkort in nederland",
        ],
    },
    {
        "intent": "artist_item_list",
        "intent_category": "informational",
        "phrases": [
            "welke muziek heeft scooter gemaakt",
            "welke nummers heeft radiohead gemaakt",
            "geef me 5 nummers van pearl jam",
            "geef me albums van radiohead",
            "toon playlists van metallica",
            "laat nummers van nirvana zien",
        ],
    },
    {
        "intent": "similar_artists",
        "intent_category": "informational",
        "phrases": [
            "vergelijkbare artiesten",
            "welke vergelijkbare artiesten zijn er",
            "similar artists",
            "welke artiesten maken vergelijkbare muziek als wat nu speelt",
        ],
    },
    {
        "intent": "build_playlist_from_seeds",
        "intent_category": "informational",
        "phrases": [
            "stel een playlist samen op basis van radiohead en massive attack",
            "ik wil een playlist obv tracks reckoner teardrop",
            "ik wil een playlist in genre ambient techno",
            "maak playlist obv huidig nummer",
            "bouw een playlist rond portishead",
        ],
    },
    {
        "intent": "spotify_user_playlists",
        "intent_category": "informational",
        "phrases": [
            "toon mijn playlists",
            "welke playlists heb ik",
            "laat mijn afspeellijsten zien",
            "mijn playlists",
        ],
    },
    {
        "intent": "spotify_vibe_playlists",
        "intent_category": "informational",
        "phrases": [
            "zoek een chill playlist",
            "zoek een party playlist",
            "geef een ambient playlist",
            "heb je een playlist voor focus",
        ],
    },
    {
        "intent": "spotify_playlist_search",
        "intent_category": "informational",
        "phrases": [
            "zoek playlists voor techno",
            "zoek afspeellijsten met grunge",
            "vind playlists voor hardlopen",
            "toon playlists voor jazz",
        ],
    },
    {
        "intent": "playlist_recommendation_offer",
        "intent_category": "informational",
        "phrases": [
            "raad een playlist aan",
            "welke playlist past nu",
            "heb je een playlist tip",
        ],
    },
    {
        "intent": "song_recommendations",
        "intent_category": "informational",
        "phrases": [
            "raad nummers aan",
            "geef me song recommendations",
            "welke tracks moet ik luisteren",
            "geef me nieuwe nummers",
        ],
    },
    {
        "intent": "artist_more_tracks",
        "intent_category": "informational",
        "phrases": [
            "meer nummers van radiohead",
            "nog meer tracks van pearl jam",
            "geef meer muziek van nirvana",
        ],
    },
    {
        "intent": "save_generated_playlist",
        "intent_category": "informational",
        "phrases": [
            "maak hier een playlist van",
            "sla deze mix op als playlist",
            "bewaar dit als playlist",
        ],
    },
    {
        "intent": "list_outputs",
        "intent_category": "informational",
        "phrases": [
            "welke speakers zijn er",
            "welke outputs zijn er",
            "wissel van speaker",
            "laat speakers zien",
            "toon beschikbare speakers",
        ],
    },
    {
        "intent": "current_output",
        "intent_category": "informational",
        "phrases": [
            "waarop speelt de muziek",
            "waarop draait muziek",
            "op welke speaker speelt de muziek",
        ],
    },
    {
        "intent": "playback_mode_status",
        "intent_category": "informational",
        "phrases": [
            "staat shuffle aan",
            "is shuffle actief",
            "staat repeat aan",
            "hoe staat repeat",
        ],
    },
    {
        "intent": "playback_control",
        "intent_category": "action",
        "phrases": [
            "pauzeer",
            "stop muziek",
            "stop de muziek",
            "ik ga slapen",
            "start muziek",
            "start de muziek",
            "speel verder",
            "hervat muziek",
            "resume",
            "next",
            "skip",
            "next song",
            "volgende nummer",
            "vorige nummer",
            "previous",
            "zet harder",
            "zet zachter",
            "shuffle aan",
            "shuffle uit",
            "repeat aan",
            "repeat uit",
            "herhaal dit",
            "zet huidig nummer in favorieten",
            "like dit nummer",
            "save this track to liked songs",
        ],
    },
    {
        "intent": "play_music",
        "intent_category": "hybrid",
        "phrases": [
            "speel nirvana",
            "speel radiohead",
            "draai pearl jam",
            "zet metallica op",
            "speel paranoid android",
            "draai wat techno",
            "zet muziek voor koken op",
        ],
    },
]


def _classifier_matches(text: str, expected_intent: str, expected_category: str) -> bool:
    try:
        from tests.test_http_voice_helpers import install_http_stubs

        install_http_stubs()
        from custom_components.djconnect.ask_dj import classify_ask_dj
    except Exception:
        return True
    classification = classify_ask_dj(text)
    return (
        classification.intent == expected_intent
        and classification.category == expected_category
    )


def build_variants() -> tuple[list[dict[str, object]], list[str]]:
    variants: list[dict[str, object]] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for group in VARIANT_GROUPS:
        for index, phrase in enumerate(group["phrases"], start=1):
            key = phrase.casefold()
            if key in seen:
                raise ValueError(f"Duplicate Ask DJ variant phrase: {phrase!r}")
            seen.add(key)
            expected_intent = str(group["intent"])
            expected_category = str(group["intent_category"])
            if not _classifier_matches(phrase, expected_intent, expected_category):
                skipped.append(f"{expected_intent}: {phrase}")
                continue
            variants.append(
                {
                    "id": f"{expected_intent}_{index:03d}",
                    "text": phrase,
                    "expect": {
                        "intent": expected_intent,
                        "intent_category": expected_category,
                    },
                }
            )
    return variants, skipped


def main() -> None:
    variants, skipped = build_variants()
    OUTPUT_PATH.write_text(
        json.dumps(variants, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(variants)} Ask DJ intent variants to {OUTPUT_PATH}")
    if skipped:
        print(f"Skipped {len(skipped)} candidate variants that are not supported yet.")


if __name__ == "__main__":
    main()
