"""Ordinary paired HA/history route, with explicit synthetic date sources.

No external network/model, installed state or generated prose-quality claim.
"""

import asyncio
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(os.environ.get("DJC_SOURCE_ROOT", Path(__file__).resolve().parents[2]))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/verification")]


async def qualify(hass, manager, history, request, client):
    from custom_components.djconnect import pipeline
    from custom_components.djconnect.ask_dj import public_research as r
    from custom_components.djconnect.ask_dj.person_age import age_answer, entity_url

    def claim(prop, value, kind="time"):
        return {
            "rank": "normal",
            "mainsnak": {
                "property": prop,
                "snaktype": "value",
                "datatype": "time" if kind == "time" else "wikibase-item",
                "datavalue": {"type": kind, "value": value},
            },
        }

    document = {
        "entities": {
            "Q123": {
                "id": "Q123",
                "type": "item",
                "sitelinks": {"enwiki": {"title": "Ada Reed"}},
                "claims": {
                    "P31": [
                        claim(
                            "P31",
                            {"entity-type": "item", "numeric-id": 5, "id": "Q5"},
                            "wikibase-entityid",
                        )
                    ],
                    "P569": [
                        claim(
                            "P569",
                            {
                                "time": "+2000-02-29T00:00:00Z",
                                "precision": 11,
                                "before": 0,
                                "after": 0,
                                "timezone": 0,
                                "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
                            },
                        )
                    ],
                },
            }
        }
    }
    sources = (
        r._source(
            "Wikipedia",
            "Ada Reed",
            "https://en.wikipedia.org/wiki/Ada_Reed",
            "Ada Reed is a singer.",
            "en",
            entity_id="Q123",
        ),
        r._source(
            "Wikidata",
            "Ada Reed",
            entity_url("Q123", "en"),
            json.dumps(document),
            "en",
            entity_id="Q123",
            current=True,
        ),
    )
    group_document = {
        "entities": {
            "Q124": {
                "id": "Q124",
                "type": "item",
                "sitelinks": {"enwiki": {"title": "Example Band"}},
                "claims": {
                    "P31": [
                        claim(
                            "P31",
                            {"entity-type": "item", "numeric-id": 215380, "id": "Q215380"},
                            "wikibase-entityid",
                        )
                    ],
                    "P571": [
                        claim(
                            "P571",
                            {
                                "time": "+1996-00-00T00:00:00Z",
                                "precision": 9,
                                "before": 0,
                                "after": 0,
                                "timezone": 0,
                                "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
                            },
                        )
                    ],
                },
            }
        }
    }
    group_sources = (
        r._source(
            "Wikipedia",
            "Example Band",
            "https://en.wikipedia.org/wiki/Example_Band",
            "Example Band is a rock band.",
            "en",
            entity_id="Q124",
        ),
        r._source(
            "Wikidata",
            "Example Band",
            entity_url("Q124", "en"),
            json.dumps(group_document),
            "en",
            entity_id="Q124",
            current=True,
        ),
    )
    reads = []

    async def research(subject, question, language, guard, **kwargs):
        await guard()
        assert subject in {"Ada Reed", "Example Band"}
        reads.append({"subject": subject, "language": language, "synthetic_sources": True})
        return list(sources if subject == "Ada Reed" else group_sources), {
            "state": "available",
            "fixture": "declared_synthetic_dates",
        }

    async def forbidden_model(*args, **kwargs):
        raise AssertionError("Exact calendar arithmetic needs no generated factual answer")

    cases = []
    questions = {
        "nl": "Hoe oud is Ada Reed?",
        "en": "How old is Ada Reed?",
        "de": "Wie alt ist Ada Reed?",
        "fr": "Quel âge a Ada Reed ?",
        "es": "¿Qué edad tiene Ada Reed?",
    }
    for language, question in questions.items():
        with (
            patch.object(r, "research", research),
            patch.object(pipeline, "_call_conversation_process_transport", forbidden_model),
        ):
            result, status = await request(
                "POST",
                "/api/djconnect/v1/ask_dj/message",
                {
                    "client_message_id": "exact-age-" + language,
                    "text": question,
                    "language": language,
                    "audio_response": "never",
                    "conversation_context": {"session_id": None},
                },
            )
        assert status == 200, result
        assert result["knowledge_basis"] == "public_person_age_v1", result
        assert result["text"] == age_answer(sources, "Ada Reed", language), result
        assert not result.get("playback_actions") and not result.get("audio_url")
        assert result["assistant_message"]["text"] == result["text"]
        cases.append({"language": language, "state": "PASS", "model_calls": 0})
    from custom_components.djconnect.ask_dj.biographical_dates import group_inception_answer

    group_questions = {
        "nl": "Wanneer is Example Band opgericht, welk jaar?",
        "en": "When was Example Band formed?",
        "de": "Wann wurde Example Band gegründet?",
        "fr": "Quand a été Example Band fondé ?",
        "es": "¿Cuándo fue Example Band fundado?",
    }
    for language, question in group_questions.items():
        with (
            patch.object(r, "research", research),
            patch.object(pipeline, "_call_conversation_process_transport", forbidden_model),
        ):
            result, status = await request(
                "POST",
                "/api/djconnect/v1/ask_dj/message",
                {
                    "client_message_id": "group-inception-" + language,
                    "text": question,
                    "language": language,
                    "audio_response": "never",
                    "conversation_context": {"session_id": None},
                },
            )
        assert status == 200 and result["knowledge_basis"] == "public_group_inception_v1", result
        assert result["text"] == group_inception_answer(group_sources, "Example Band", language)
        assert result["assistant_message"]["text"] == result["text"]
        assert not result.get("playback_actions") and not result.get("audio_url")
        cases.append(
            {"language": language, "kind": "group_inception", "state": "PASS", "model_calls": 0}
        )
    interpretation_calls = []

    async def interpretation(hass_arg, data, **kwargs):
        projection = json.loads(data["text"].split("\nData:\n", 1)[1])
        assert projection["question"] == "band"
        assert projection["recent_public_query"]["previous_question_angle"] == "age"
        interpretation_calls.append("declared_synthetic_read_plan")
        return {
            "response": {
                "speech": {
                    "plain": {
                        "speech": json.dumps(
                            {
                                "read": "research",
                                "reference": "recent",
                                "angle": "age",
                                "exclude_current": False,
                            }
                        )
                    }
                }
            }
        }

    with (
        patch.object(r, "research", research),
        patch.object(pipeline, "_call_conversation_process_transport", interpretation),
    ):
        first, status = await request(
            "POST",
            "/api/djconnect/v1/ask_dj/message",
            {
                "client_message_id": "group-age-choice",
                "text": "Hoe oud is Example Band?",
                "language": "nl",
                "audio_response": "never",
                "conversation_context": {"session_id": None},
            },
        )
        assert status == 200 and first["clarification_required"] and not interpretation_calls, first
        second, status = await request(
            "POST",
            "/api/djconnect/v1/ask_dj/message",
            {
                "client_message_id": "group-age-chosen",
                "text": "band",
                "language": "nl",
                "audio_response": "never",
                "conversation_context": {"session_id": None},
            },
        )
    assert status == 200 and second["knowledge_basis"] == "public_group_inception_v1", second
    assert second["text"] == group_inception_answer(group_sources, "Example Band", "nl")
    assert len(interpretation_calls) == 1 and not second.get("clarification_required")
    cases.append(
        {
            "kind": "band_choice_preserves_purpose",
            "state": "PASS",
            "declared_synthetic_interpretation_calls": 1,
            "paid_model_calls": 0,
        }
    )
    from dataclasses import replace

    conflict_wiki = replace(
        group_sources[0], text="Example Band is a rock band. Example Band was formed in 2005."
    )

    async def conflict_wikipedia(fetch, *args, **kwargs):
        await fetch.guard()
        assert fetch.requests < fetch.maximum_requests
        fetch.requests += 1
        return conflict_wiki

    async def conflict_wire(fetch, url, **kwargs):
        await fetch.guard()
        assert fetch.requests < fetch.maximum_requests and url == entity_url("Q124", "en")
        fetch.requests += 1
        return 200, json.dumps(group_document), url

    with (
        patch.object(r, "wikipedia", conflict_wikipedia),
        patch.object(r.PublicFetch, "request", conflict_wire),
        patch.object(pipeline, "_call_conversation_process_transport", forbidden_model),
    ):
        conflict, status = await request(
            "POST",
            "/api/djconnect/v1/ask_dj/message",
            {
                "client_message_id": "group-date-conflict",
                "text": "Wanneer is Example Band opgericht?",
                "language": "nl",
                "audio_response": "never",
                "conversation_context": {"session_id": None},
            },
        )
    assert status == 200 and conflict["knowledge_basis"] == "public_research_conflicting_dates", (
        conflict
    )
    assert "1996" not in conflict["text"] and "2005" not in conflict["text"]
    assert len(conflict["sources"]) == 2 and conflict["conversation"]["metrics"]["agent_calls"] == 0
    cases.append({"kind": "same_group_date_conflict", "state": "PASS", "model_calls": 0})
    return {
        "state": "PASS",
        "cases": cases,
        "source_reads": reads,
        "external_network_calls": 0,
        "paid_model_calls": 0,
        "scope": "Paired HTTP/history and exact date boundary only; sources synthetic, not prose/native/installed acceptance.",
    }


if __name__ == "__main__":
    from verify_session_conversation_history_http import main

    asyncio.run(main(qualification_extension=qualify))
