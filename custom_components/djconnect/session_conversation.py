"""Attach confirmed Session references to the existing Ask DJ authority and history."""

from __future__ import annotations

import hashlib
import json
import re

from .historical_projection_query import HistoricalProjectionQueryService
from .persistence import persistence_service
from .persistence.history import HistoricalProjectionRepository


class SessionConversationError(ValueError):
    def __init__(self, code: str, status: int = 409):
        super().__init__(code)
        self.code = code
        self.status = status


def history_question(text: str) -> str | None:
    """Bounded literal intent interpretation; no model, provider lookup or model SQL."""
    patterns = (
        r"(?:wanneer|heb ik).*?(?:naar|van)\s+(.+?)\s+(?:geluisterd|gehoord)(?:[?!.]|$)",
        r"(?:when|have i).*?(?:listen(?:ed)? to|hear(?:d)?)\s+(.+?)(?:[?!.]|$)",
        r"(?:wann).*?ich\s+(?:(?:zuletzt|früher|zuvor)\s+)?(?:(?:von|zu)\s+)?(.+?)\s+(?:gehört|zugehört)(?:[?!.]|$)",
        r"(?:quand).*?(?:écouté|entendu)\s+(.+?)(?:[?!.]|$)",
        r"(?:cuándo).*?(?:escuchado|escuché)\s+(?:a\s+)?(.+?)(?:[?!.]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text.strip(), re.IGNORECASE)
        if match:
            return match.group(1).strip(" \"'“”«»")[:200]
    return None


def _locale(payload: dict) -> str:
    family = str(payload.get("language") or payload.get("locale") or "en").split("-", 1)[0].lower()
    return family if family in {"en", "nl", "de", "fr", "es"} else "en"


def historical_answer(payload: dict, result: dict) -> dict:
    locale = _locale(payload)
    found = {
        "en": "Found in your saved sessions (observed playback; full listening is not proven):",
        "nl": "Gevonden in je bewaarde sessies (waargenomen playback; volledig beluisteren is niet bewezen):",
        "de": "In deinen gespeicherten Sessions gefunden (beobachtete Wiedergabe; vollständiges Anhören ist nicht belegt):",
        "fr": "Trouvé dans vos sessions conservées (lecture observée ; écoute complète non démontrée) :",
        "es": "Encontrado en tus sesiones guardadas (reproducción observada; no se demuestra una escucha completa):",
    }
    missing = {
        "en": "Not found in your saved sessions. This history does not cover all your listening.",
        "nl": "Niet gevonden in je bewaarde sessies. Deze geschiedenis dekt niet al je luistermomenten.",
        "de": "Nicht in deinen gespeicherten Sessions gefunden. Dieser Verlauf umfasst nicht alles, was du gehört hast.",
        "fr": "Non trouvé dans vos sessions conservées. Cet historique ne couvre pas toutes vos écoutes.",
        "es": "No encontrado en tus sesiones guardadas. Este historial no abarca todas tus escuchas.",
    }
    matches = result["matches"]
    lines = [found[locale]] if matches else [missing[locale]]
    if not result.get("complete", True):
        lines.append(
            {
                "en": "Only a bounded part of the saved history was searched.",
                "nl": "Er is een begrensd deel van de bewaarde geschiedenis doorzocht.",
                "de": "Nur ein begrenzter Teil des gespeicherten Verlaufs wurde durchsucht.",
                "fr": "Seule une partie limitée de l’historique conservé a été recherchée.",
                "es": "Solo se ha buscado en una parte limitada del historial guardado.",
            }[locale]
        )
    lines.extend(f"{m['occurred_at']} · {m['text']}" for m in matches)
    return {
        "success": True,
        "text": "\n".join(lines),
        "dj_text": "\n".join(lines),
        "intent": {"intent": "saved_session_playback_history"},
        "historical_matches": matches,
        "navigation_actions": [m["open_action"] for m in matches],
        "playback_actions": [],
        "sources": [{"source": "djconnect_observed_session_history"}],
        "history_coverage": result["coverage"],
        "history_query_complete": bool(result.get("complete", False)),
        "full_listens_proven": False,
        "repeat_counts_supported": False,
    }


async def async_qualify_history_source(hass, owner: str, row: dict) -> bool:
    """Recheck captured source binding; today's default never substitutes identity."""
    if row["kind"] != "playback_observed":
        try:
            retained = json.loads(row['body'])
        except (TypeError,ValueError):
            return False
        if row['kind'] != 'dj_moment' or retained.get('archive_basis') != 'owner_metadata_narration_v1':
            return True
    from .profile_context import profile_storage

    household = await profile_storage(hass).async_load()
    profile = household.profiles.get(owner)
    if profile is None or str(profile.state) != "active":
        return False
    try:
        body = json.loads(row["body"])
    except (TypeError, ValueError):
        return False
    if not isinstance(body, dict):
        return False
    captured = body.get("source_context") or {}
    if not isinstance(captured, dict):
        return False
    backend = household.music_backends.get(captured.get("backend_id"))
    if backend is None or str(backend.state) != "active":
        return False
    if body.get("provider") == "DJConnect":
        return str(backend.provider) == "future_provider"
    account = household.music_accounts.get(captured.get("music_account_id"))
    if (
        account is None
        or str(account.state) != "active"
        or owner not in account.linked_profile_ids
        or account.backend_id != backend.backend_id
        or str(account.provider_account_id) != str(captured.get("provider_account_id") or "")
    ):
        return False
    provider = {"Spotify": "spotify_direct", "Music Assistant": "music_assistant"}.get(
        body.get("provider")
    )
    if str(backend.provider) != provider:
        return False
    entry_id = captured.get("provider_entry_id")
    entries = getattr(getattr(hass, "config_entries", None), "async_entries", lambda _: [])(
        "djconnect"
    )
    source = next((entry for entry in entries if entry.entry_id == entry_id), None)
    from .client_retirement import is_retired_entry
    from .retired_provider import historical_successor

    if source is None or (
        is_retired_entry(source)
        and {**source.data, **source.options}.get("profile_backend_entry_id")
    ):
        source = historical_successor(hass, str(entry_id or ""), owner, captured)
    source_ids = {entry_id, getattr(source, "entry_id", None)}
    if source_ids.intersection(
        hass.data.get("djconnect", {}).get("spotify_reauth_issue_throttle", {})
    ):
        return False
    # HA's persisted typed Repair survives process restart; no error-text parsing.
    if body.get("provider") == "Spotify":
        try:
            from homeassistant.helpers import issue_registry

            registry = issue_registry.async_get(hass)
            issue = registry.async_get_issue("djconnect", "spotify_refresh_token_revoked")
        except (ImportError, AttributeError):
            issue = None  # SDK-only fixtures may omit HA Repairs; account checks still apply.
        if issue is not None and (issue.data or {}).get("entry_id") in source_ids:
            return False
    if source is None or getattr(source, "disabled_by", None) is not None:
        return False
    config = {**source.data, **source.options}
    if str(config.get("music_account_id") or "") != account.account_id:
        return False
    if body.get("provider") == "Spotify" and not config.get("spotify_refresh_token"):
        return False
    return True


async def async_qualify_summary_source(hass, owner: str, captured: dict) -> bool:
    """Current rights for compact counts; never fetch providers or save their IDs."""
    import hashlib
    from .profile_context import profile_storage

    household = await profile_storage(hass).async_load()
    backend = household.music_backends.get(captured.get("backend_id"))
    if backend is None:
        return False
    provider = {
        "spotify_direct": "Spotify",
        "music_assistant": "Music Assistant",
        "future_provider": "DJConnect",
    }.get(str(backend.provider))
    context = dict(captured)
    if provider != "DJConnect":
        account = household.music_accounts.get(captured.get("music_account_id"))
        if account is None or hashlib.sha256(
            str(account.provider_account_id).encode()
        ).hexdigest() != captured.get("account_fingerprint"):
            return False
        context["provider_account_id"] = str(account.provider_account_id)
    return await async_qualify_history_source(
        hass,
        owner,
        {
            "kind": "playback_observed",
            "body": json.dumps({"provider": provider, "source_context": context}),
        },
    )


async def async_history_grant_revision(hass, owner: str) -> str:
    """Revision covers source/owner withdrawal without hashing credentials."""
    from .profile_context import profile_storage

    household = await profile_storage(hass).async_load()
    return history_grant_revision(hass, owner, household)


async def async_metadata_archive_admission(hass, owner, captured, authorize):
    """Existing source owner qualifies a new exact-text archive before SQL."""
    authorize()
    revision = history_grant_revision(hass, owner)
    row = {'kind':'dj_moment','body':json.dumps({
        'archive_basis':'owner_metadata_narration_v1','provider':'Spotify','source_context':captured})}
    if not await async_qualify_history_source(hass, owner, row):
        return None
    revoked = False
    def guard():
        nonlocal revoked
        if revoked or history_grant_revision(hass, owner) != revision:
            revoked = True
            raise PermissionError('archive_source_withdrawn')
        authorize()
    guard()
    return guard


def history_grant_revision(hass, owner: str, household=None) -> str:
    """Same qualified rights revision from committed cache, without an await."""
    from .profile_context import profile_storage

    household = household or profile_storage(hass).household
    profile = household.profiles.get(owner)
    accounts = [
        (
            a.account_id,
            a.backend_id,
            str(a.state),
            owner in a.linked_profile_ids,
            str(a.provider_account_id),
        )
        for a in household.music_accounts.values()
    ]
    backends = [
        (b.backend_id, str(b.state), str(b.provider)) for b in household.music_backends.values()
    ]
    entries = getattr(getattr(hass, "config_entries", None), "async_entries", lambda _: [])(
        "djconnect"
    )
    sources = []
    for entry in entries:
        config = {**entry.data, **entry.options}
        sources.append(
            (
                entry.entry_id,
                bool(getattr(entry, "disabled_by", None)),
                str(config.get("music_account_id") or ""),
                bool(config.get("spotify_refresh_token")),
                config.get("retired_provider_history_bindings", {}),
            )
        )
    revoked = sorted(hass.data.get("djconnect", {}).get("spotify_reauth_issue_throttle", {}))
    try:
        from homeassistant.helpers import issue_registry

        issue = issue_registry.async_get(hass).async_get_issue(
            "djconnect", "spotify_refresh_token_revoked"
        )
    except (ImportError, AttributeError):
        issue = None
    repair_source = str((issue.data or {}).get("entry_id") or "") if issue else ""
    payload = (
        getattr(profile_storage(hass), "authority_revision", 0),
        str(profile.state) if profile else "missing",
        str(profile.privacy_mode) if profile else "",
        sorted(accounts),
        sorted(backends),
        sorted(sources),
        revoked,
        repair_source,
    )
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def query_service(hass, history_manager=None) -> HistoricalProjectionQueryService:
    domain = hass.data.setdefault("djconnect", {})
    query = domain.get("session_history_query")
    if query is None:
        query = HistoricalProjectionQueryService(
            HistoricalProjectionRepository(persistence_service(hass)),
            history_manager,
            source_validator=lambda owner, row: async_qualify_history_source(hass, owner, row),
            grant_revision=lambda owner: async_history_grant_revision(hass, owner),
            grant_revision_now=lambda owner: history_grant_revision(hass, owner),
            summary_validator=lambda owner, binding: async_qualify_summary_source(
                hass, owner, binding
            ),
        )
        domain["session_history_query"] = query
    elif history_manager is not None:
        query._conversation_history = history_manager
    from .session_artwork import project_history_media
    query.media_projector = lambda owner, row, entry: project_history_media(hass, owner, row, entry)
    return query


async def async_session_exchange(*args, **kwargs):
    """Compatibility import only; both screens invoke the same application service."""
    from .ask_dj.service import async_exchange

    return await async_exchange(*args, **kwargs)
