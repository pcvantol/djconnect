"""Reactive Ask DJ Golden cases; real paired Core route, no model judge."""
from __future__ import annotations

import hashlib
import json
import re
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
MAX_MODEL_CALLS = 40
MAX_OUTPUT_TOKENS = 700


def cases():
    return [
        {"id": f"ASKDJ-GOLDEN-001-{locale}-{kind}", "language": locale,
         "question": questions[index], "expected_person": person,
         "retain_selection": retained, "require_biography_source": retained,
         "reference_key": "selected_entry" if kind == "playback-partial" else "selected_moment"}
        for locale, questions in LANGUAGES.items()
        for index, kind, person, retained in (
            (0, "partial", "Peter Luts", True),
            (0, "playback-partial", "Peter Luts", True),
            (1, "deictic", "Peter Luts", True),
            (2, "new-topic", "Miles Davis", False),
        )
    ]


def manifest_digest():
    return hashlib.sha256(json.dumps(cases(), sort_keys=True).encode()).hexdigest()


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
        "Miles Davis": r"\b(?:trumpet(?:er)?|trompettist|trompeter|trompettiste|trompetista|trompette|trompeta)\b",
    }
    if not re.search(fact_terms[case["expected_person"]], text):
        failures.append("expected_public_fact_missing")
    if re.search(r"\b(?:not|geen|kein|keine|pas|no)\s+(?:(?:a|een|un|une|ein)\s+)?(?:musician|muzikant|musiker|musicien|músico|producer|dj|trumpeter)\b", text):
        failures.append("contradictory_biography")
    if case["require_biography_source"]:
        # Existing selected-credit attribution explicitly qualifies credits only.
        # Neither general knowledge nor a test-side Wikipedia fetch is biography evidence.
        supported = {"en.wikipedia.org", "nl.wikipedia.org", "de.wikipedia.org",
                     "fr.wikipedia.org", "es.wikipedia.org", "www.wikidata.org",
                     "wikidata.org", "musicbrainz.org"}
        qualified = False
        for source in response.get("sources") or []:
            if not isinstance(source, dict):
                continue
            url = urlsplit(str(source.get("url") or ""))
            qualified |= (url.scheme == "https" and url.hostname in supported
                          and url.username is None and url.password is None
                          and source.get("claim_scope") == "person_biography"
                          and source.get("subject") == {"kind": "person", "name": case["expected_person"]}
                          and url.path in {"/wiki/" + case["expected_person"].replace(" ", "_"),
                                           "/wiki/" + {"Peter Luts": "Q3376733", "Miles Davis": "Q93341"}[case["expected_person"]]})
        if not qualified:
            failures.append("qualified_biography_source_missing")
    return failures


async def run(*, ask, call, start, end, playback_reference, mutations, model_receipts):
    """Hook into the existing isolated HA harness after ordinary pairing."""
    active, moment, _ = await start("contextual-golden")
    selection = {"session_id": active.session_id, "moment_id": moment.moment_id}
    playback = await playback_reference(active)
    rows = []
    try:
        for case in cases():
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
    return {"schema_version": 1, "suite": "askdj_contextual_golden_v1",
            "manifest_sha256": manifest_digest(), "cases": rows,
            "paid_model_calls": len(model_receipts),
            "usage": [{k: r.get(k) for k in ("case_id", "model", "attempted", "completed", "input_tokens", "output_tokens")}
                      for r in model_receipts],
            "status": "PASS" if len(rows) == len(cases())
                      and all(r["status"] == "PASS" for r in rows)
                      and 0 < len(model_receipts) <= MAX_MODEL_CALLS else "FAIL",
            "native_installed_hardware": "NOT_RUN"}
