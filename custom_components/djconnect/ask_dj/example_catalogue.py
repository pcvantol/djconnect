"""One versioned Help/chip catalogue; pure, local eligibility and projection.

This is presentation eligibility, never execution authority or provider health.
Clients use existing discovery/status/Session evidence, not a render-time call.
"""
from copy import deepcopy
import hashlib
from .example_catalogue_data import CATALOGUE as _CATALOGUE, SOURCE_SHA256 as _HASH


def catalogue():
    return deepcopy(_CATALOGUE)


def capability():
    return {"schema_version": 1, "qualified": _CATALOGUE.get('status') == 'qualified_v1', "catalogue_id": _CATALOGUE["catalogue_id"],
            "revision": _CATALOGUE["revision"], "sha256": _HASH,
            "projection": "pinned_local_mirror", "network_per_render": False,
            "model_calls_per_render": False, "execution": "existing_ask_dj_message",
            "availability": "current_qualified_context_required"}


def _locale(language):
    value = str(language or "").replace("_", "-").lower().split("-", 1)[0]
    return value if value in _CATALOGUE["language_families"] else None


def compatible(context):
    """Exact pinned content/version, not a semver guess or old route boolean."""
    pin = context.get("catalogue")
    return (isinstance(pin, dict) and pin.get('qualified') is True
        and capability()['qualified'] is True
        and all(type(pin.get(k)) is int for k in ('schema_version','revision'))
        and all(pin.get(k) == v for k, v in capability().items()
            if k in {"schema_version", "catalogue_id", "revision", "sha256"}))


def eligible(context, surface, language, *, for_help=False):
    language = _locale(language)
    if not language or not isinstance(context, dict) or not compatible(context):
        return []
    if surface not in {"ask_dj", "active_session"}:
        return []
    if surface == "active_session" and context.get("active_session") is not True:
        return []
    result = []
    versions = context.get("contracts") or {}
    slots = context.get("slots") or {}
    configuration = context.get("entry_configuration")
    if (not isinstance(versions, dict) or not isinstance(slots, dict)
            or not isinstance(configuration, dict)):
        return []
    for entry in _CATALOGUE["entries"]:
        if configuration.get(entry["id"]) is not True:
            continue
        if entry["qualification"][_locale(language)]["state"] != "qualified_owner_route":
            continue
        if entry["publication"] != "qualified_v1" or surface not in entry["surfaces"]:
            continue
        if any(context.get(key) is not True for key in entry["requires"]):
            continue
        if any(type(versions.get(key)) is not int or versions[key] != value
               for key, value in entry["contracts"].items()):
            continue
        if not for_help and any(not _safe_slot(slots.get(key)) for key in entry["slots"]):
            continue
        result.append(deepcopy(entry))
    return result if _context_current(context) else []


def _context_current(context):
    """A server-local lifetime fence, never a wire field or client authority."""
    check = context.get("_help_current") if isinstance(context, dict) else None
    try:
        return check is None or (callable(check) and check() is True)
    except Exception:
        return False


def _safe_slot(value):
    return (isinstance(value, str) and 0 < len(value) <= 160 and value == value.strip()
            and not any(ord(c) < 32 or c in "{}[]" for c in value))


def prompt(entry, language, slots=None, *, for_help=False):
    language = _locale(language)
    if not language:
        raise ValueError('unsupported_catalogue_locale')
    values = ({key: _CATALOGUE["slot_labels"][key][language] for key in entry["slots"]}
              if for_help else (slots or {}))
    return entry["templates"][language].format(**values)


def help_sections(language, context):
    if not _locale(language):
        return []
    entries = eligible(context or {}, "ask_dj", language, for_help=True)
    sections = []
    for group in _CATALOGUE["groups"]:
        selected = sorted((e for e in entries if e["group"] == group["id"]),
                          key=lambda e: (e["help_rank"], e["id"]))[:2]
        if selected:
            sections.append((group["labels"][_locale(language)],
                             [prompt(e, language, for_help=True) for e in selected]))
    # In an active Session put qualified listening context first, without a
    # second independent Help surface or more examples.
    if context and context.get("active_session") is True and context.get("current_track") is True:
        title = _CATALOGUE["groups"][-1]["labels"][_locale(language)]
        sections.sort(key=lambda s: s[0] != title)
    return sections if _context_current(context) else []


def help_text(language, context=None):
    sections = help_sections(language, context)
    language = _locale(language) or 'en'
    blocks = [_CATALOGUE["intro"][language]]
    blocks += ["\n".join(["## " + title, *["- " + p for p in examples]])
               for title, examples in sections]
    if not sections:
        blocks.append(_CATALOGUE["unavailable"][language])
    if not _context_current(context):
        return _CATALOGUE["intro"][language] + "\n\n" + _CATALOGUE["unavailable"][language]
    return "\n\n".join(blocks)


def select(context, surface, language, *, epoch, recent=()):
    """Reference algorithm. Call on a viewing epoch, never a render or tick.

    Apple owns freezing its three values while editing/reading and withdrawing
    newly ineligible values. No server/global/RAM tracking or timer is created.
    """
    candidates = eligible(context, surface, language)
    recent = set(list(recent)[-6:])
    def rank(e):
        return (e["id"] in recent,
            hashlib.sha256((str(epoch)[:128] + ":" + e["id"]).encode()).hexdigest())
    candidates.sort(key=rank)
    chosen = []
    contextual = [e for e in candidates if e["contextual"]]
    if contextual:
        chosen.append(contextual[0])
    while len(chosen) < 3:
        rest = [e for e in candidates if e not in chosen and e["intent"] not in {c["intent"] for c in chosen}]
        if not rest:
            break
        rest.sort(key=lambda e: (e["group"] in {c["group"] for c in chosen}, *rank(e)))
        chosen.append(rest[0])
    # Never pad an unknown/offline backend with imaginary executable prompts.
    if len(chosen) != 3 or not _context_current(context):
        return {"state": "unavailable", "suggestions": [], "reason": "insufficient_qualified_examples"}
    return {"state": "ready", "suggestions": [
        {"id":e["id"], "intent":e["intent"], "group":e["group"],
         "prompt":prompt(e, language, context.get("slots")), "send":"existing_ask_dj_message_exact_prompt"}
        for e in chosen]}


def help_context(hass, runtime):
    """The same committed base predicate as R5, for this authorized turn only."""
    from .dialogue import current_turn
    from .help_observation import committed_context
    from ..capability_contract import _contract_versions
    turn = current_turn.get()
    closed = {"catalogue": capability(), "contracts": _contract_versions()}
    if turn is None or not turn.scope.startswith("profile:"):
        return closed
    try:
        entry = runtime.entry
        config = {**entry.data, **entry.options}
        captured = committed_context(hass, runtime, config.get("device_id"),
            config.get("client_type"), session_id=turn.session_id or None,
            owner=turn.scope.removeprefix("profile:"))
        return captured[0] if captured is not None else closed
    except Exception:
        return closed
