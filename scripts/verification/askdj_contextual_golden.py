"""Reactive Ask DJ Golden cases; real paired Core route, no model judge."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, UTC
from contextvars import ContextVar
from urllib.parse import urlsplit

LANGUAGES = {
    "en": ("Who is Peter?", "Who is that composer?", "Who is Miles Davis?"),
    "nl": ("Wie is Peter?", "Wie is die componist?", "Wie is Miles Davis?"),
    "de": ("Wer ist Peter?", "Wer ist der Komponist?", "Wer ist Miles Davis?"),
    "fr": ("Qui est Peter ?", "Qui est le compositeur ?", "Qui est Miles Davis ?"),
    "es": ("¿Quién es Peter?", "¿Quién es el compositor?", "¿Quién es Miles Davis?"),
}
ACTIVE_CASE = ContextVar("askdj_golden_case", default=None)
MAX_MODEL_CALLS = 42  # 20 question cases × 2, plus 2 bound publication-setup calls.
MAX_OUTPUT_TOKENS = 3000
SETUP_CASE = "ASKDJ-GOLDEN-SETUP-published-credit"


RELEASE_LANGUAGES = ("en", "nl")


def release_languages(value):
    if value is None:
        return None
    if value != ",".join(RELEASE_LANGUAGES):
        raise ValueError("invalid_askdj_release_languages")
    return RELEASE_LANGUAGES


def cases(languages=None):
    return [
        {"id": f"ASKDJ-GOLDEN-001-{locale}-{kind}", "language": locale,
         "question": questions[index], "expected_person": person,
         "retain_selection": retained, "require_biography_source": retained,
         "reference_key": "selected_entry" if kind == "playback-partial" else "selected_moment"}
        for locale, questions in LANGUAGES.items()
        if languages is None or locale in languages
        for index, kind, person, retained in (
            (0, "partial", "Peter Luts", True),
            (0, "playback-partial", "Peter Luts", True),
            (1, "deictic", "Peter Luts", True),
            (2, "new-topic", "Miles Davis", False),
        )
    ]


def manifest_digest(languages=None):
    return hashlib.sha256(json.dumps(cases(languages), sort_keys=True).encode()).hexdigest()


def check_response(case, response, selection):
    """Observe accepted response and evidence, not fixture prose or model scores."""
    failures = []
    if not response.get("success"):
        failures.append("response_not_accepted")
    conversation = response.get("conversation") or {}
    context = conversation.get("context") or {}
    if (context.get(case["reference_key"]) == selection) != case["retain_selection"]:
        failures.append("selected_context_boundary")
    text = str(response.get("text") or "").casefold()
    if case["expected_person"].casefold() not in text:
        failures.append("wrong_or_missing_person")
    calls = (conversation.get("metrics") or {}).get("agent_calls")
    if type(calls) is not int or not 1 <= calls <= 2:
        failures.append("real_model_path_missing")
    if response.get("playback_actions") or response.get("action") not in (None, "none"):
        failures.append("unexpected_action")
    fact_terms = {
        "Peter Luts": r"\b(?:dj|producer|producent|produzent|producteur|productor)\b",
        "Miles Davis": r"\b(?:trumpet(?:er)?|(?:jazz[- ]?)?trompettist|(?:jazz[- ]?)?trompeter|trompettiste|trompetista|trompette|trompeta)\b",
    }
    if not re.search(fact_terms[case["expected_person"]], text):
        failures.append("expected_public_fact_missing")
    if re.search(r"\b(?:not|geen|kein|keine|pas|no)\s+(?:(?:a|een|un|une|ein)\s+)?(?:musician|muzikant|musiker|musicien|músico|producer|dj|trumpeter|(?:jazz[- ]?)?trompeter|(?:jazz[- ]?)?trompettist)\b", text):
        failures.append("contradictory_biography")
    if case["require_biography_source"]:
        # Existing selected-credit attribution explicitly qualifies credits only.
        # Neither general knowledge nor a test-side Wikipedia fetch is biography evidence.
        supported = {"en.wikipedia.org", "nl.wikipedia.org", "de.wikipedia.org",
                     "fr.wikipedia.org", "es.wikipedia.org", "www.wikidata.org",
                     "wikidata.org"}
        qualified = False
        for source in response.get("sources") or []:
            if not isinstance(source, dict):
                continue
            url = urlsplit(str(source.get("url") or ""))
            expected_qid = {"Peter Luts": "Q3376733", "Miles Davis": "Q93341"}[case["expected_person"]]
            try:
                fetched = datetime.fromisoformat(source.get('fetched_at', ''))
                expires = datetime.fromisoformat(source.get('expires_at', ''))
                current = fetched.tzinfo is not None and expires.tzinfo is not None and fetched <= datetime.now(UTC) < expires
            except (TypeError, ValueError):
                current = False
            qualified |= (url.scheme == "https" and url.hostname in supported
                          and url.username is None and url.password is None
                          and source.get("claim_scope") == "fetched_public_music_reference"
                          and ((source.get('provider') == 'Wikipedia' and url.hostname.endswith('.wikipedia.org')
                                and source.get('license') == 'CC-BY-SA-4.0')
                               or (source.get('provider') == 'Wikidata' and url.hostname in {'wikidata.org', 'www.wikidata.org'}
                                   and source.get('license') == 'CC0-1.0'))
                          and source.get('wikidata_id') == expected_qid
                          and isinstance(source.get('content_hash'), str)
                          and re.fullmatch('[0-9a-f]{64}', source['content_hash']) is not None
                          and current
                          and response.get('knowledge_basis') == 'fetched_public_music_research_v1'
                          and response.get('is_generated_text') is True
                          and url.path in {"/wiki/" + case["expected_person"].replace(" ", "_"),
                                           "/wiki/" + expected_qid})
        if not qualified:
            failures.append("qualified_biography_source_missing")
    return failures


async def run(*, ask, call, start, end, playback_reference, mutations, model_receipts, languages=None):
    """Hook into the existing isolated HA harness after ordinary pairing."""
    expected_cases = cases(languages)
    setup_start = len(model_receipts)
    rows = []
    setup_findings = []
    def report():
        setup = [r for r in model_receipts if r.get("case_id") == SETUP_CASE]
        return {"schema_version": 1, "suite": "askdj_contextual_golden_v1",
                "manifest_sha256": manifest_digest(languages), "cases": rows,
                "setup_paid_model_calls": len(setup), "setup_findings": setup_findings,
                "paid_model_calls": len(model_receipts),
                "usage": [{k: r.get(k) for k in ("case_id", "model", "attempted", "completed", "input_tokens", "output_tokens",
                                                     "maximum_output_tokens", "terminal_event", "incomplete_reason")}
                          for r in model_receipts],
                "status": "PASS" if not setup_findings and len(rows) == len(expected_cases)
                          and all(r["status"] == "PASS" for r in rows)
                          and 0 < len(model_receipts) <= 2 * len(expected_cases) + 2 else "FAIL",
                "native_installed_hardware": "NOT_RUN"}
    try:
        active, moment, _ = await start("contextual-golden")
    except Exception as exc:
        setup_findings.append("selected_publication_unavailable:" + type(exc).__name__)
        return report()
    setup = model_receipts[setup_start:]
    if (len(setup) > 2 or any(r.get("case_id") != SETUP_CASE or not r.get("completed") for r in setup)):
        setup_findings.append("setup_attempt_binding_or_completion")
        await end(active, "contextual-golden-failed-setup")
        return report()
    selection = {"session_id": active.session_id, "moment_id": moment.moment_id}
    playback = await playback_reference(active)
    try:
        for case in expected_cases:
            await call("ask_dj/history/clear", {}, label=case["id"] + "-clear")
            before = len(mutations)
            before_models = len(model_receipts)
            case_token = ACTIVE_CASE.set(case["id"])
            selected = playback if case["reference_key"] == "selected_entry" else selection
            try:
                response = await ask(case["question"], case["id"],
                                     {"session_id": active.session_id,
                                      case["reference_key"]: selected},
                                     language=case["language"])
                findings = check_response(case, response, selected)
            except Exception as exc:  # Keep only a type, never provider text or credentials.
                findings = ["transport_or_core_failure:" + type(exc).__name__]
            finally:
                ACTIVE_CASE.reset(case_token)
            case_models = model_receipts[before_models:]
            if not 1 <= len(case_models) <= 2 or any(r.get("case_id") != case["id"] for r in case_models):
                findings.append("paid_attempt_case_binding")
            if any(not r.get("completed") for r in case_models):
                findings.append("paid_attempt_incomplete")
            if len(mutations) != before:
                findings.append("playback_mutation")
            rows.append({"id": case["id"], "status": "FAIL" if findings else "PASS",
                         "findings": findings, "paid_attempts": len(case_models)})
    finally:
        await end(active, "contextual-golden")
    return report()
