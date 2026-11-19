"""Versioned visual-only help, shared by both capability transports.

Examples describe the deterministic text grammar, not microphone permission,
STT availability, an active Session grant or successful native application.
"""

from __future__ import annotations

from copy import deepcopy

_EXAMPLES = {
    "en": (
        "Make it calmer and fluid",
        "Make it faster",
        "More depth",
        "More gold",
        "Make a variant",
        "Keep this style",
        "Go back",
        "Follow DJ",
    ),
    "nl": (
        "Maak het rustiger en vloeibaarder",
        "Maak het sneller",
        "Meer diepte",
        "Iets meer goud",
        "Maak een variant",
        "Hou deze stijl aan",
        "Ga een stap terug",
        "Terug naar de DJ",
    ),
    "de": (
        "Mach es ruhiger und flüssiger",
        "Mach es schneller",
        "Mehr Tiefe",
        "Mehr Gold",
        "Eine Variante",
        "Diesen Stil beibehalten",
        "Rückgängig",
        "Zurück zum DJ",
    ),
    "fr": (
        "Un peu calme et fluide",
        "Un peu rapide",
        "Plus de profondeur",
        "Plus doré",
        "Une variante",
        "Garde ce style",
        "Revenir en arrière",
        "Retour au DJ",
    ),
    "es": (
        "Haz lo tranquilo y fluido",
        "Haz lo rápido",
        "Más profundidad",
        "Más dorado",
        "Una variante",
        "Mantener este estilo",
        "Volver atrás",
        "Volver al DJ",
    ),
}
_IDS = ("calmer_fluid", "faster", "more_depth", "more_gold", "variant", "hold", "undo", "reset")
_SCOPES = {
    "en": ("Only this track", "This whole visit"),
    "nl": ("Alleen dit nummer", "Zolang ik hier ben"),
    "de": ("Nur dieses Lied", "Während dieses Besuchs"),
    "fr": ("Seulement ce morceau", "Pendant cette visite"),
    "es": ("Solo esta canción", "Durante esta visita"),
}


def capability():
    """Return fresh public metadata; no state, credentials or context admission."""
    return deepcopy(
        {
            "contract_version": 1,
            "input": "bounded_text_from_on_device_stt_or_text",
            "interpretation": "closed_visual_grammar",
            "application": "native_client_only",
            "microphone_readiness": "client_owned",
            "context_required": True,
            "endpoints": {
                kind: "/api/djconnect/v1/vibescape/" + kind
                for kind in ("context", "interpret", "revoke")
            },
            "limits": {
                "body_bytes": 8192,
                "text_utf8_bytes": 1024,
                "lease_ms": 15000,
                "visit_ms": 1800000,
                "turns_per_visit": 32,
            },
            "actions": ["patch", "undo", "reset", "variant", "hold"],
            "help": {
                locale: {
                    "examples": [
                        dict(id=key, text=text) for key, text in zip(_IDS, examples, strict=True)
                    ],
                    "scopes": [
                        dict(id=key, text=text)
                        for key, text in zip(
                            ("current_track", "while_in_vibescape"), _SCOPES[locale], strict=True
                        )
                    ],
                }
                for locale, examples in _EXAMPLES.items()
            },
        }
    )
