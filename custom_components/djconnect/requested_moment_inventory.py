"""Loaded-only rich Moment catalogue; one original native owner subject capture."""

from __future__ import annotations
from dataclasses import dataclass
import copy
import secrets
import time

LANGUAGES = ("en", "nl", "de", "fr", "es")
FAMILIES = (
    (
        "recording_story",
        ("recording_credits",),
        (
            "Recording story",
            "Opnameverhaal",
            "Aufnahmegeschichte",
            "Histoire de l’enregistrement",
            "Historia de la grabación",
        ),
    ),
    (
        "work_composers",
        ("work_composers",),
        (
            "The composers",
            "De componisten",
            "Die Komponisten",
            "Les compositeurs",
            "Los compositores",
        ),
    ),
    (
        "artist_story",
        ("artist_begin", "artist_description"),
        (
            "Artist story",
            "Artiestenverhaal",
            "Künstlergeschichte",
            "Histoire de l’artiste",
            "Historia del artista",
        ),
    ),
    (
        "album_story",
        ("album_release",),
        (
            "Album story",
            "Albumverhaal",
            "Albumgeschichte",
            "Histoire de l’album",
            "Historia del álbum",
        ),
    ),
    (
        "genre_context",
        ("genre_context",),
        (
            "Genre context",
            "Genrecontext",
            "Genre-Kontext",
            "Contexte du genre",
            "Contexto del género",
        ),
    ),
    (
        "live_impression",
        ("artist_begin", "artist_description"),
        (
            "Live impression",
            "Live-impressie",
            "Live-Eindruck",
            "Impression live",
            "Impresión en vivo",
        ),
    ),
    (
        "shared_producer",
        ("shared_producer",),
        (
            "A shared producer",
            "Een gedeelde producer",
            "Ein gemeinsamer Produzent",
            "Un producteur en commun",
            "Un productor en común",
        ),
    ),
    (
        "producer_recommendation",
        ("producer_recommendation",),
        (
            "Explore a producer",
            "Ontdek een producer",
            "Einen Produzenten entdecken",
            "Découvrir un producteur",
            "Descubrir un productor",
        ),
    ),
    (
        "album_continuity",
        ("album_continuity",),
        (
            "Back to this album",
            "Terug naar dit album",
            "Zurück zu diesem Album",
            "Retour à cet album",
            "Volver a este álbum",
        ),
    ),
    (
        "dj_bulletin",
        (),
        ("DJ Bulletin", "DJ Bulletin", "DJ-Bulletin", "Bulletin du DJ", "Boletín del DJ"),
    ),
)
TYPE_KEYS = {name: keys for name, keys, _ in FAMILIES}
MOMENT_TYPES = {
    "recording_story": "track",
    "work_composers": "track",
    "artist_story": "artist",
    "album_story": "album",
    "genre_context": "genre",
    "live_impression": "live_impression",
    "shared_producer": "track",
    "producer_recommendation": "recommendation",
    "album_continuity": "track",
    "dj_bulletin": "dj_bulletin",
}
MAX_CAPTURES = 64
CAPTURE_SECONDS = 300


def capability():
    return {
        "available": True,
        "contract_version": 1,
        "inventory_operation": "ask_dj/moments",
        "request_operation": "ask_dj/moments/request",
        "status_operation": "ask_dj/moments/status",
        "cancel_operation": "ask_dj/moments/cancel",
        "read_path": "/api/djconnect/v1/transport/read",
        "operation_path": "/api/djconnect/v1/transport/operation",
        "owner_only": True,
        "client_types": ["ios", "macos"],
        "language_families": list(LANGUAGES),
        "requires_active_session": True,
        "inventory_has_provider_effects": False,
        "maximum_pending_per_profile_session": 1,
        "queue": False,
        "type_ids": [name for name, _, _ in FAMILIES],
    }


def language(active):
    value = active.locale.replace("_", "-").split("-")[0].lower()
    return value if value in LANGUAGES else "en"


def pending_text(active, title):
    """Curated feedback in the captured Session voice, never another model call."""
    # The original selected Persona/Mood choose only tone; this is not a fact.
    playful = active.dj_persona.value in {
        "club_dj",
        "festival_dj",
    } and active.selected_mood not in {"focus", "deep", "chill"}
    lines = (
        "I’ll find a well-supported contribution for you about {subject}.",
        "Ik zoek een goed onderbouwde bijdrage voor je over {subject}.",
        "Ich suche für dich einen gut belegten Beitrag über {subject}.",
        "Je cherche pour vous une contribution bien étayée sur {subject}.",
        "Busco para ti una aportación bien documentada sobre {subject}.",
    )
    if playful:
        lines = (
            "Let’s take a closer look at {subject}. I’m looking it up for you.",
            "Even verder kijken naar {subject}. Ik zoek het voor je uit.",
            "Schauen wir uns {subject} genauer an. Ich suche für dich nach.",
            "Regardons {subject} de plus près. Je cherche pour vous.",
            "Veamos {subject} más de cerca. Lo investigo para ti.",
        )
    return lines[LANGUAGES.index(language(active))].format(subject=title)


@dataclass
class Capture:
    reference: str
    profile: str
    device: str
    binding: str
    session_id: str
    scope: tuple
    captured_at: float
    playback: object
    facts: tuple
    catalog: dict
    source_guard: object
    narration_provider: object
    original_guard: object
    original_active: object
    recording_context: object = None
    album_context: object = None
    bulletin_provider: object = None

    def current(self, manager, authority):
        from .current_track_insight import session_scope

        current = manager.current_active(self.profile)
        authority.validate_now()
        if (
            (authority.context.profile_id, authority.device, authority.binding)
            != (self.profile, self.device, self.binding)
            or current is None
            or (*session_scope(current), current.allowed_capability_intents) != self.scope
            or time.monotonic() >= self.captured_at + CAPTURE_SECONDS
            or current.broadcast.content_pending
            or not current.publication_context_is_current()
        ):
            raise PermissionError("moment_request_context_changed")
        self.original_guard()
        if self.source_guard is not None and not self.source_guard():
            raise PermissionError("moment_request_source_changed")
        return current


def loaded_facts(manager, profile, active):
    """Only qualified facts joined to this exact already-observed recording."""
    import hashlib
    from .session_facts import QualifiedSessionFact

    opportunity = manager._intra_track_opportunities.get(profile)
    if (
        opportunity is None
        or opportunity.session_id != active.session_id
        or opportunity.item_id != active.broadcast.state.playback.item_id
        or hashlib.sha256(opportunity.media_identity.encode()).hexdigest()[:24]
        != opportunity.item_id
    ):
        return ()
    return tuple(
        f
        for f in opportunity.qualified_facts
        if isinstance(f, QualifiedSessionFact)
        and f.eligible(opportunity.media_identity, time.monotonic())
    )


def capture(hass, authority, manager, active):
    from .current_track_insight import session_scope
    from .pipeline import _assist_context
    from .api_handlers import _connect_session_narration

    profile = authority.context.profile_id
    owners = _connect_session_narration(
        hass,
        authority.runtime,
        authority.context,
        active,
        authority.identity,
        authority.headers,
        register=False,
    )
    provider, bulletin_provider = owners if owners is not None else (None, None)
    selected = copy.deepcopy(_assist_context(hass, authority.runtime.config))
    if not selected.get("agent_id"):
        provider = bulletin_provider = None
    original_authority = provider[3]() if provider is not None and provider[3] is not None else None

    def original_guard():
        authority.validate_now()
        if original_authority is not None:
            original_authority()
        elif provider is not None:
            provider[2]()
        if _assist_context(hass, authority.runtime.config) != selected:
            raise PermissionError("moment_request_provider_changed")

    facts = loaded_facts(manager, profile, active)
    # A bounded normalized observation, never caller metadata or a new GET lookup.
    observer = hass.data.get("djconnect", {}).get("playback_observation_manager")
    observed = observer._spotify_sessions.get(profile) if observer else None
    catalog = (
        copy.deepcopy(getattr(observed, "moment_catalog", {}))
        if (
            observed
            and observed.session_id == active.session_id
            and 0 <= time.monotonic() - getattr(observed, "moment_catalog_observed_at", 0) < 30
        )
        else {}
    )
    media = catalog.get("uri")
    if (
        media
        and active.broadcast.state.playback.item_id
        != __import__("hashlib").sha256(media.encode()).hexdigest()[:24]
    ):
        catalog = {}
    return Capture(
        secrets.token_urlsafe(24),
        profile,
        authority.device,
        authority.binding,
        active.session_id,
        (*session_scope(active), active.allowed_capability_intents),
        time.monotonic(),
        active.broadcast.state.playback,
        facts,
        catalog,
        None,
        provider,
        original_guard,
        active,
        copy.deepcopy(active.published_recording_context),
        copy.deepcopy(active.published_album_context),
        bulletin_provider,
    )


def candidate_facts(captured, active):
    from .session_facts import producer_recommendation

    facts = captured.facts
    if facts:
        recordings = captured.recording_context or active.published_recording_context
        albums = captured.album_context or active.published_album_context
        relation = recordings.candidate(facts, facts[0].media_identity, time.monotonic())
        if relation is not None:
            facts = (*facts, relation)
            recommendation = producer_recommendation(
                relation,
                recordings.published_moment_ids.get(relation.previous_evidence.media_identity, ""),
                time.monotonic(),
            )
            if recommendation is not None:
                facts = (*facts, recommendation)
        album = albums.candidate(facts, facts[0].media_identity, time.monotonic())
        if album is not None:
            facts = (*facts, album)
    return facts


def descriptors(captured, manager):
    active = captured.original_active
    facts = candidate_facts(captured, active)
    rows = []
    for order, (name, keys, labels) in enumerate(FAMILIES):
        candidates = [f for f in facts if f.key in keys]
        has_catalog = bool(captured.catalog) and name not in {
            "shared_producer",
            "producer_recommendation",
            "album_continuity",
        }
        intent = (
            "artist_story"
            if name in {"artist_story", "live_impression"}
            else "album_story"
            if name == "album_story"
            else "genre_story"
            if name == "genre_context"
            else "recommendation"
            if name == "producer_recommendation"
            else "track_context"
        )
        capable = (
            active.allowed_capability_intents is None or intent in active.allowed_capability_intents
        )
        available = (
            bool(candidates or has_catalog) and captured.narration_provider is not None and capable
        )
        reason = (
            None
            if available
            else "producer_unavailable"
            if captured.narration_provider is None
            else "capability_unavailable"
            if not capable
            else "subject_evidence_unavailable"
        )
        if name == "dj_bulletin":
            available = (
                manager._bulletin_service is not None and captured.bulletin_provider is not None
            )
            reason = None if available else "producer_unavailable"
        kind = (
            "session"
            if name == "dj_bulletin"
            else "album"
            if name in {"album_story", "album_continuity"}
            else "artist"
            if name in {"artist_story", "live_impression"}
            else "recording"
        )
        playback = captured.playback
        news_title = (
            "Current news",
            "Actuele berichten",
            "Aktuelle Nachrichten",
            "Actualités",
            "Noticias actuales",
        )[LANGUAGES.index(language(active))]
        title = (
            news_title
            if kind == "session"
            else playback.album
            if kind == "album"
            else playback.artist
            if kind == "artist"
            else playback.title
        ) or dict(zip(LANGUAGES, labels))[language(active)]
        rows.append(
            {
                "type_id": name,
                "moment_type": MOMENT_TYPES[name],
                "order": order,
                "label": dict(zip(LANGUAGES, labels)),
                "available": available,
                "reason": reason,
                "reason_text": reason_text(active, reason),
                "reason_labels": {
                    locale: reason_text(active, reason, locale=locale) for locale in LANGUAGES
                }
                if reason
                else None,
                "history_policy": "publication_metadata_only"
                if name == "dj_bulletin"
                else "original_source_and_profile_policy",
                "subject": {
                    "subject_ref": captured.reference,
                    "kind": kind,
                    "title": title,
                    "subtitle": "" if kind == "session" else playback.artist or "",
                },
                "pending_text": pending_text(active, title),
            }
        )
    return rows


def feedback(active, state):
    copies = {
        "not_found": (
            "I couldn’t find a well-supported contribution about this subject.",
            "Ik kon geen goed onderbouwde bijdrage over dit onderwerp vinden.",
            "Ich konnte keinen gut belegten Beitrag zu diesem Thema finden.",
            "Je n’ai pas trouvé de contribution bien étayée sur ce sujet.",
            "No he encontrado una aportación bien documentada sobre este tema.",
        ),
        "temporarily_unavailable": (
            "Searching is unavailable for a moment. Please try again later.",
            "Het zoeken lukt nu even niet. Probeer het later nog eens.",
            "Die Suche funktioniert gerade nicht. Versuche es später noch einmal.",
            "La recherche est momentanément indisponible. Réessayez plus tard.",
            "La búsqueda no funciona ahora. Inténtalo de nuevo más tarde.",
        ),
        "denied": (
            "This request is no longer available. Open Moments again.",
            "Deze aanvraag is niet meer beschikbaar. Open Moments opnieuw.",
            "Diese Anfrage ist nicht mehr verfügbar. Öffne Moments erneut.",
            "Cette demande n’est plus disponible. Ouvrez Moments à nouveau.",
            "Esta solicitud ya no está disponible. Abre Moments de nuevo.",
        ),
        "cancelled": ("Cancelled.", "Geannuleerd.", "Abgebrochen.", "Annulé.", "Cancelado."),
        "accepted_result_unavailable": (
            "The contribution was accepted, but can no longer be shown here.",
            "De bijdrage is geaccepteerd, maar kan hier niet meer worden getoond.",
            "Der Beitrag wurde angenommen, kann hier aber nicht mehr angezeigt werden.",
            "La contribution a été acceptée, mais ne peut plus être affichée ici.",
            "La aportación se ha aceptado, pero ya no se puede mostrar aquí.",
        ),
    }
    return copies[state][LANGUAGES.index(language(active))] if state in copies else None


def reason_text(active, reason, *, locale=None):
    values = {
        "subject_evidence_unavailable": (
            "A reliable contribution about this subject is not available right now.",
            "Over dit onderwerp is nu geen betrouwbare bijdrage beschikbaar.",
            "Zu diesem Thema ist gerade kein verlässlicher Beitrag verfügbar.",
            "Aucune contribution fiable sur ce sujet n’est disponible pour le moment.",
            "Ahora no hay una aportación fiable sobre este tema.",
        ),
        "producer_unavailable": (
            "Stories are currently unavailable. Try again later.",
            "Verhalen zijn nu niet beschikbaar. Probeer het later nog eens.",
            "Geschichten sind gerade nicht verfügbar. Versuche es später noch einmal.",
            "Les histoires sont momentanément indisponibles. Réessayez plus tard.",
            "Las historias no están disponibles ahora. Inténtalo más tarde.",
        ),
        "capability_unavailable": (
            "This type of contribution is not available here.",
            "Dit type bijdrage is hier niet beschikbaar.",
            "Diese Art von Beitrag ist hier nicht verfügbar.",
            "Ce type de contribution n’est pas disponible ici.",
            "Este tipo de aportación no está disponible aquí.",
        ),
    }
    return values[reason][LANGUAGES.index(locale or language(active))] if reason in values else None
