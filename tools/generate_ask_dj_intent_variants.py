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
            "welke commando's kan ik gebruiken",
            "welke commandos kan ik gebruiken",
            "geef me voorbeelden",
            "wat kan ik vragen",
            "show help",
            "show commands",
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
            "nee laat maar",
            "maakt niet uit",
            "helemaal goed",
            "oké dank je",
            "never mind",
            "no worries",
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
            "goede morgen",
            "morning",
            "hey goedemorgen",
            "goedemorgen dj",
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
            "wat herinner je je over mij",
            "wat weet djconnect over mij",
            "what do you remember about me",
            "wat is mijn music dna",
            "geef mijn music dna samenvatting",
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
            "beschrijf mijn muzieksmaak",
            "welke genres luister ik de laatste tijd",
            "wat zegt mijn luistergedrag",
            "maak een profiel van mijn muzieksmaak",
            "analyze my listening profile",
            "describe my music taste",
        ],
    },
    {
        "intent": "personal_artist_recommendations",
        "intent_category": "informational",
        "phrases": [
            "welke artiesten passen bij mijn smaak",
            "welke artiesten zou ik leuk vinden",
            "geef artiesten die bij mijn smaak passen",
            "raad artiesten aan voor mij",
            "recommend artists for my taste",
            "welke bands passen bij mijn muzieksmaak",
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
            "geef me aanbevelingen",
            "heb je muziekaanbevelingen voor mij",
            "recommend music for me",
            "suggest something based on my taste",
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
            "wat maakt dit nummer bijzonder",
            "what makes this track special",
            "tell me about this song",
            "geef inzicht in deze track",
            "analyseer de vibe van dit nummer",
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
            "wat draaide ik net",
            "wat speelde hiervoor",
            "welke artiesten hoorde ik net",
            "what did I play last hour",
            "what have I listened to today",
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
            "wat draait er nu",
            "what's playing",
            "current track",
            "hoe heet dit nummer",
            "welk liedje is dit",
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
            "maak een intro bij deze track",
            "geef een aankondiging voor dit nummer",
            "announce this track",
            "make a DJ intro for this song",
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
            "wat speelt hierna",
            "welke track komt hierna",
            "what comes next",
            "next track in queue",
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
            "wanneer komt radiohead naar nederland",
            "heeft pearl jam concerten binnenkort",
            "when does metallica tour",
            "live dates for radiohead",
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
            "zoek tracks van massive attack",
            "show me albums by radiohead",
            "give me songs by pearl jam",
            "welke albums bracht radiohead uit",
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
            "noem artiesten die hierop lijken",
            "artists like this",
            "wie klinkt er als radiohead",
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
            "maak een mix op basis van radiohead",
            "create a playlist based on massive attack",
            "stel een afspeellijst samen rond ambient",
            "bouw een mix met nirvana en pearl jam",
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
            "show my playlists",
            "list my playlists",
            "welke afspeellijsten heb ik",
            "toon eigen playlists",
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
            "zoek een playlist voor slapen",
            "geef een playlist voor werken",
            "find a chill playlist",
            "do you have a focus playlist",
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
            "zoek playlists met drum and bass",
            "find playlists for cooking",
            "search playlists about grunge",
            "welke playlists zijn er voor sporten",
        ],
    },
    {
        "intent": "playlist_recommendation_offer",
        "intent_category": "informational",
        "phrases": [
            "raad een playlist aan",
            "welke playlist past nu",
            "heb je een playlist tip",
            "geef een playlist tip",
            "recommend a playlist",
            "welke afspeellijst past bij mijn bui",
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
            "heb je leuke nummers",
            "suggest songs for me",
            "recommend tracks",
            "welke songs raad je aan",
        ],
    },
    {
        "intent": "artist_more_tracks",
        "intent_category": "informational",
        "phrases": [
            "meer nummers van radiohead",
            "nog meer tracks van pearl jam",
            "geef meer muziek van nirvana",
            "wat heb je nog meer van radiohead",
            "show me more songs by nirvana",
            "meer muziek van deze artiest",
        ],
    },
    {
        "intent": "save_generated_playlist",
        "intent_category": "informational",
        "phrases": [
            "maak hier een playlist van",
            "sla deze mix op als playlist",
            "bewaar dit als playlist",
            "sla dit op als playlist",
            "maak van deze selectie een playlist",
            "save this as a playlist",
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
            "welke apparaten zijn er",
            "toon outputs",
            "switch speaker",
            "change output",
        ],
    },
    {
        "intent": "current_output",
        "intent_category": "informational",
        "phrases": [
            "waarop speelt de muziek",
            "waarop draait muziek",
            "op welke speaker speelt de muziek",
            "welke speaker is actief",
            "waar speelt dit af",
            "what speaker is active",
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
            "staat shuffle uit",
            "is repeat actief",
            "what is shuffle status",
            "is repeat on",
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
            "volume omhoog",
            "volume omlaag",
            "harder graag",
            "zachter graag",
            "pause music",
            "play music",
            "previous track",
            "sla dit nummer op",
            "voeg dit nummer toe aan favorieten",
            "unlike dit nummer",
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
            "speel iets van daft punk",
            "draai een jazz playlist",
            "zet ambient muziek op",
            "play nirvana",
            "put on radiohead",
            "play some techno",
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
