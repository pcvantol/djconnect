"""Held-out free-wording cases: real HA/agent interpretation, external music fixtures.

These are evaluation inputs only, never runtime recognition rules or prompt examples.
"""

import hashlib
import json

WORDS = {
    "nl": (
        "hee wie zingdt er eigelijk wat nu opstaat?",
        "hoe heet dat liedjuh dat momenteel langskomt?",
        "uit welk releasejaar is de opname die opstaat eigelijk?",
        "wat zit er verder nog op de plaat die nu opstaat?",
        "wat staat er na deze in m'n muziekwachtrijtje?",
        "wat is jouw dj vooruitblik voor dit luisterblok?",
        "welke opname hoorde ik vlak vóór deze ook alweer?",
        "zelfde band, heb je nog een andere plaat voor me?",
        "even checken, wie maakt de musiek hierbij eigelijk?",
        "Wie is degene die hier nu staat te zingen?",
        "welke hits heeft armin van buuren nog meer",
    ),
    "en": (
        "remind me whose voice we're hearing rn?",
        "forgot the name of whats playing rn, help?",
        "how far back does the release of whats on now date?",
        "what else is tucked away on the record we're hearing?",
        "whats lined up behind this in my playback queue?",
        "give me your dj preview of the listening stretch ahead?",
        "which recording came just b4 this one again?",
        "same band, any different record you could offer me?",
        "quick check, who's making the music in this selected bit?",
        "Who is the person doing the vocals right now?",
        "what other hists has armin van buren got then?",
    ),
    "de": (
        "sag ma wer singt da grad?",
        "wie heisstn das stück was grad läuft?",
        "aus welchem veröffentlichungsjahr stammt was grad läuft?",
        "was steckt sonst noch auf der platte die grad läuft?",
        "was wartet hinter dem hier in meiner abspielreihe?",
        "gib mir deinen dj-ausblick auf den nächsten hörabschnitt?",
        "welche aufnahme lief direkt vorm jetzigen stück nochmal?",
        "von derselben band noch ne andere platte für mich?",
        "kurze frage, wer macht hier beim ausgewählten beitrag die musik?",
        "Wer ist der Mensch der da gerade singt?",
        "welche anderen hists hat armin van buren eigentlich?",
    ),
    "fr": (
        "c'est la voix de qui là, tu sais ?",
        "j'ai oublié le nom de ce qui passe là, tu me le rappelles ?",
        "ça remonte à quelle année de parution ce qui passe là ?",
        "y a quoi d'autre sur le disque qu'on entend là ?",
        "y a quoi derrière dans ma file de lecture là ?",
        "ton aperçu de dj pour la suite de cette écoute, ce serait quoi ?",
        "c'était quel enregistrement juste avant celui-là déjà ?",
        "du même groupe, un disque différent à me proposer ?",
        "petite vérif, qui fait la musique dans cette contribution sélectionnée ?",
        "Qui est la personne qui chante en ce moment ?",
        "il a quoi comme autres tubes armin van buren ?",
    ),
    "es": (
        "oye de kien es la voz k suena ahora?",
        "se me fue el nombre de lo k está sonando, me ayudas?",
        "a qué año de publicación se remonta lo que suena ahora?",
        "qué más viene en el disco k estamos oyendo?",
        "qué hay detrás de esto en mi cola de reproducción?",
        "cuál es tu adelanto de dj para el siguiente tramo de escucha?",
        "qué grabación sonó justo antes de esta, te acuerdas?",
        "de la misma banda, algún disco diferente para proponerme?",
        "una duda, quién hace la música de esta contribución seleccionada?",
        "¿Quién es la persona que está cantando ahora?",
        "qué otros exitoss tiene armin van buren?",
    ),
}
READS = ("artist", "recording", "release", "album_tracks", "queue", "forecast",
         "previous_track", "other_album", "artist", "artist", "artist_tracks")


def cases():
    return [{"id": f"semantic-{locale}-{index}", "language": locale, "question": question,
             "read": READS[index], "selected": index == 8, "unqualified_subject_capture": index == 9}
            for locale, questions in WORDS.items() for index, question in enumerate(questions)]


def manifest_digest():
    return hashlib.sha256(json.dumps(cases(), sort_keys=True).encode()).hexdigest()


def expected_plan(case):
    read = case["read"]
    reference = ("named" if read == "artist_tracks" else "selected" if case["selected"]
                 else "none" if read in {"queue", "forecast", "previous_track"} else "current")
    return {"read": read, "reference": reference, "exclude_current": read in {"album_tracks", "artist_tracks"},
            **({"artist": "Armin van Buuren"} if reference == "named" else {})}


async def run(*, hass, ask, call, start, end, selected_reference, state, tracks, model_receipts, mutations):
    from scripts.verification.askdj_contextual_golden import ACTIVE_CASE
    active, _, _ = await start("semantic")
    # Freeze this lab's external observation cadence before changing its provider
    # fixture A/B. Lifecycle/track races have separate negative owner tests.
    # Leaving the poller active makes a synthetic case transition race a model
    # question and correctly trips Core's production item fence.
    from custom_components.djconnect.playback_observation import playback_observation_manager
    await playback_observation_manager(hass).async_stop("profile-a", active.session_id)
    selection = await selected_reference(active)
    rows = []
    try:
        for case in cases():
            await call("ask_dj/history/clear", {}, label=case["id"] + "-clear")
            # Selected A must still resolve A while provider currently reports B.
            state["index"] = 1 if case["selected"] else 0
            state["named_artist_fixture"] = case["read"] == "artist_tracks"
            token = ACTIVE_CASE.set(case["id"])
            before = len(model_receipts)
            try:
                answer = await ask(case["question"], case["id"],
                                   {"selected_entry": selection} if case["selected"] else None,
                                   language=case["language"])
            finally:
                ACTIVE_CASE.reset(token)
            failures = []
            attempts = model_receipts[before:]
            try:
                actual_plan = json.loads(attempts[0]["generated_text"]) if len(attempts) == 1 else {}
            except (ValueError, KeyError):
                actual_plan = {}
            if actual_plan != expected_plan(case):
                failures.append("semantic_plan_wrong_or_missing")
            if answer.get("conversation", {}).get("metrics", {}).get("agent_calls") != 1 or len(model_receipts) - before != 1:
                failures.append("one_real_model_interpretation_required")
            expected_intent = {"artist": "current_artist_information", "recording": "current_track_reference",
                               "release": "current_release_information", "album_tracks": "album_tracks_information",
                               "forecast": "session_forecast_information", "previous_track": "previous_track_information"}.get(case["read"])
            if expected_intent and answer.get("intent", {}).get("intent") != expected_intent:
                failures.append("wrong_read")
            if case["read"] in {"artist", "recording"} and tracks[0]["name"] not in answer.get("text", ""):
                failures.append("wrong_or_missing_recording")
            if case["read"] == "album_tracks" and [i["title"] for i in answer.get("items", [])] != [t["name"] for t in tracks[1:]]:
                failures.append("wrong_album_tracks")
            if case["read"] == "release" and "2008-05-06" not in answer.get("text", ""):
                failures.append("missing_edition_date")
            if case["read"] == "queue" and answer.get("queue_observation", {}).get("state") != "known_empty":
                failures.append("wrong_queue_state")
            if case["read"] == "other_album":
                actions = answer.get("playback_actions", [])
                if len(actions) != 1 or actions[0].get("context_uri") != "spotify:album:" + "c" * 22:
                    failures.append("missing_frozen_album_offer")
            elif case["read"] == "artist_tracks":
                actions = answer.get("playback_actions", [])
                if ([a.get("uri") for a in actions] != ["spotify:track:" + c * 22 for c in ("e", "f")]
                        or [a.get("title") for a in actions] != ["Synthetic named recording 2", "Synthetic named recording 3"]
                        or any(not a.get("action_id") for a in actions)):
                    failures.append("missing_exact_named_artist_recordings")
                if (actual_plan.get("reference") != "named" or actual_plan.get("artist") != "Armin van Buuren"
                        or actual_plan.get("exclude_current") is not True):
                    failures.append("wrong_named_artist_plan")
            elif answer.get("playback_actions"):
                failures.append("unexpected_action")
            if case["selected"] and answer.get("conversation", {}).get("context", {}).get("selected_entry") != selection:
                failures.append("selection_lost")
            if mutations:
                failures.append("unexpected_effect")
            rows.append({**case, "status": "FAIL" if failures else "PASS", "findings": failures,
                         "answer": answer.get("text"), "metrics": answer.get("conversation", {}).get("metrics")})
    finally:
        state["index"] = 0
        state["named_artist_fixture"] = False
        await end(active, "semantic")
    return {"status": "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL",
            "qualification": "REAL_HA_SEMANTIC_CONTEXT_READS", "cases": rows,
            "manifest_sha256": manifest_digest(), "maximum_paid_attempts": len(cases()) + 2,
            "setup_paid_model_calls": sum(c.get("case_id") == "semantic-start" for c in model_receipts),
            "model_calls": model_receipts, "paid_model_calls": len(model_receipts),
            "native": "NOT_RUN", "installed": "NOT_RUN", "audible": "NOT_RUN",
            "narrative_quality": "NOT_ASSESSED"}
