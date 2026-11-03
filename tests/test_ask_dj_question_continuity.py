"""Reported question shapes, source scheduling and clarification continuity.

These are routing/evidence regressions, never generated answer-quality proof.
"""

import json
import hashlib
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


class QuestionContinuityTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    def test_current_actual_ha_proof_keeps_all_dates_choices_and_conflicts_bound(self):
        root = Path(__file__).resolve().parents[1]
        proof = json.loads(
            (
                root
                / "examples/client_contracts/ask_dj_question_continuity_v1/actual-ha-current.json"
            ).read_text()
        )
        current = json.loads((root / 'examples/client_contracts/ask_dj_question_continuity_v1/actual-ha-requalification-1439-after-1429.json').read_text())
        self.assertTrue(current['source_before_after_equal'])
        self.assertEqual(current['harness'], proof['harness'])
        self.assertEqual(current['harness_sha256'], proof['harness_sha256'])
        self.assertEqual(len(current['source_pins']), 305)
        for name, digest in {
            **current['source_pins'],
            **proof["original_common_harness_source_pins"],
            proof["harness"]: proof["harness_sha256"],
        }.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)
        extension = current['receipt']['extension']
        self.assertEqual(len(extension["cases"]), 12)
        self.assertEqual({case["state"] for case in extension["cases"]}, {"PASS"})
        self.assertEqual(
            {case["language"] for case in extension["cases"] if "language" in case},
            {"en", "nl", "de", "fr", "es"},
        )
        self.assertIn("band_choice_preserves_purpose", {c.get("kind") for c in extension["cases"]})
        self.assertIn("same_group_date_conflict", {c.get("kind") for c in extension["cases"]})
        self.assertEqual(
            (extension["external_network_calls"], extension["paid_model_calls"]), (0, 0)
        )
        self.assertIn("not prose/native/installed", proof["quality_scope"])

    def test_explicit_basic_questions_keep_the_complete_public_subject(self):
        from custom_components.djconnect.ask_dj.public_research import explicit_public_subject

        cases = {
            "hoe oud is phil collins?": "phil collins",
            "wie zijn de muzikanten van band R.E.M.": "R.E.M.",
            "uit welke bandleden bestaat R.E.M.?": "R.E.M.",
            "wanneer is linkin park opgericht, welk jaar": "linkin park",
            "Quand a été Example Band fondé ?": "Example Band",
            "treden simon & garfunkel nog op": "simon & garfunkel",
        }
        for question, name in cases.items():
            with self.subTest(question=question):
                self.assertEqual(explicit_public_subject(question), name)

    def test_an_answer_to_band_clarification_does_not_ask_it_again(self):
        from custom_components.djconnect.ask_dj import public_research as r
        from custom_components.djconnect.ask_dj.exploration import band_age_question

        source = r._source(
            "Wikipedia",
            "Example Band",
            "https://en.wikipedia.org/wiki/Example_Band",
            "Example Band is an American rock band formed in 1996.",
            "en",
            entity_id="Q1",
        )
        research = r.research_projection("Example Band", [source], {"state": "available"})
        self.assertIsNotNone(band_age_question(research, "nl", question="Hoe oud is Example Band?"))
        for question in (
            "band",
            "hoe lang de band bestaat",
            "wanneer is Example Band opgericht, welk jaar",
        ):
            with self.subTest(question=question):
                self.assertIsNone(band_age_question(research, "nl", question=question))

    async def test_independent_source_is_not_starved_by_a_second_wikipedia_language(self):
        from custom_components.djconnect.ask_dj import public_research as r

        order = []

        async def guard():
            pass

        async def wiki(fetch, subject, question, locale, **kwargs):
            order.append(locale)
            return r._source(
                "Wikipedia",
                "Example Band",
                f"https://{locale}.wikipedia.org/wiki/Example_Band",
                "Example Band is a rock band.",
                locale,
                entity_id="Q1",
            )

        async def web(*args, **kwargs):
            order.append("independent-web")
            return []

        with patch.object(r, "wikipedia", wiki), patch.object(r, "web_references", web):
            await r.research("Example Band", "Wie zijn de bandleden?", "nl", guard)
        self.assertEqual(order, ["nl", "independent-web", "en"])

    async def test_empty_web_discovery_reformulates_once_inside_the_original_owner(self):
        from urllib.parse import parse_qs, urlsplit
        from custom_components.djconnect.ask_dj import public_research as r

        calls = []

        async def guard():
            pass

        async def network(fetch, url, **kwargs):
            await fetch.guard()
            self.assertLess(fetch.requests, fetch.maximum_requests)
            fetch.requests += 1
            calls.append(url)
            parsed = urlsplit(url)
            if parsed.path == "/robots.txt":
                return 200, "User-agent: *\nAllow: /", url
            if parsed.hostname == "html.duckduckgo.com":
                query = parse_qs(parsed.query)["q"][0]
                self.assertNotIn("my private note", query)
                body = (
                    '<a href="https://artist.example/about">Artist</a>'
                    if "lineup" in query
                    else "<html></html>"
                )
                return 200, body, url
            self.assertEqual(url, "https://artist.example/about")
            return 200, '<html lang="en"><p>Ada Reed is a singer and band member.</p></html>', url

        with patch.object(r.PublicFetch, "request", network):
            async with r.ResearchPublicFetch(guard) as fetch:
                sources = await r.web_references(
                    fetch, "Ada Reed", "Who are the members of Ada Reed?", "en"
                )
                self.assertEqual(len(sources), 1)
                self.assertEqual(fetch.requests, 6)
        searches = [
            url
            for url in calls
            if urlsplit(url).hostname == "html.duckduckgo.com"
            and urlsplit(url).path != "/robots.txt"
        ]
        self.assertEqual(len(searches), 2)

    def test_unverified_clear_question_does_not_request_the_same_question_again(self):
        from custom_components.djconnect.ask_dj.public_research import unavailable_answer

        for language in ("en", "nl", "de", "fr", "es"):
            self.assertNotIn("?", unavailable_answer(language, answer_unverified=True))

    def test_person_age_uses_exact_dates_and_rejects_ambiguous_or_wrong_identity(self):
        from custom_components.djconnect.ask_dj import public_research as r
        from custom_components.djconnect.ask_dj.person_age import age_answer, entity_url

        def statement(prop, value, kind="time"):
            return {
                "rank": "normal",
                "mainsnak": {
                    "property": prop,
                    "snaktype": "value",
                    "datatype": "time" if kind == "time" else "wikibase-item",
                    "datavalue": {"type": kind, "value": value},
                },
            }

        birthday = {
            "time": "+2000-02-29T00:00:00Z",
            "precision": 11,
            "before": 0,
            "after": 0,
            "timezone": 0,
            "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
        }
        document = {
            "entities": {
                "Q123": {
                    "id": "Q123",
                    "type": "item",
                    "sitelinks": {"enwiki": {"title": "Ada Reed"}},
                    "claims": {
                        "P31": [
                            statement(
                                "P31",
                                {"entity-type": "item", "numeric-id": 5, "id": "Q5"},
                                "wikibase-entityid",
                            )
                        ],
                        "P569": [statement("P569", birthday)],
                    },
                }
            }
        }
        wiki = r._source(
            "Wikipedia",
            "Ada Reed",
            "https://en.wikipedia.org/wiki/Ada_Reed",
            "Ada Reed is a singer.",
            "en",
            entity_id="Q123",
        )

        def data(value):
            return r._source(
                "Wikidata",
                "Ada Reed",
                entity_url("Q123", "en"),
                json.dumps(value),
                "en",
                entity_id="Q123",
                current=True,
            )

        sources = [wiki, data(document)]
        self.assertEqual(
            age_answer(sources, "Ada Reed", "nl", today=date(2024, 2, 28)),
            "Ada Reed is 23 jaar oud.",
        )
        self.assertEqual(
            age_answer(sources, "Ada Reed", "nl", today=date(2024, 2, 29)),
            "Ada Reed is 24 jaar oud.",
        )
        for change in (
            "year_only",
            "conflicting_birthdays",
            "wrong_person",
            "wrong_wiki",
            "unknown_death",
            "group",
            "qualified_date",
            "uncertain_date",
        ):
            bad = deepcopy(document)
            entity = bad["entities"]["Q123"]
            claim = entity["claims"]["P569"][0]
            if change == "year_only":
                claim["mainsnak"]["datavalue"]["value"]["precision"] = 9
            elif change == "conflicting_birthdays":
                entity["claims"]["P569"].append(deepcopy(claim))
            elif change == "wrong_person":
                entity["id"] = "Q999"
            elif change == "wrong_wiki":
                entity["sitelinks"]["enwiki"]["title"] = "Another Person"
            elif change == "unknown_death":
                entity["claims"]["P570"] = [
                    {"rank": "normal", "mainsnak": {"snaktype": "somevalue"}}
                ]
            elif change == "group":
                entity["claims"]["P31"][0]["mainsnak"]["datavalue"]["value"]["id"] = "Q215380"
            elif change == "qualified_date":
                claim["qualifiers"] = {"P1480": [{}]}
            else:
                claim["mainsnak"]["datavalue"]["value"]["before"] = 1
            with self.subTest(change=change):
                self.assertIsNone(age_answer([wiki, data(bad)], "Ada Reed", "en"))
        for original in (
            "Ada Reed was a singer who died in 2020.",
            "Ada Reed is a singer. She died in 2020.",
        ):
            self.assertIsNone(
                age_answer([replace(wiki, text=original), data(document)], "Ada Reed", "en")
            )
        for key, value in (("snaktype", "novalue"), ("property", "P279"), ("datatype", "string")):
            bad = deepcopy(document)
            bad["entities"]["Q123"]["claims"]["P31"][0]["mainsnak"][key] = value
            self.assertIsNone(age_answer([wiki, data(bad)], "Ada Reed", "en"))
        self.assertIsNone(
            age_answer(
                [replace(wiki, text="Ada Reed is a singer born in 1990."), data(document)],
                "Ada Reed",
                "en",
            )
        )
        deceased = deepcopy(document)
        deceased["entities"]["Q123"]["claims"]["P570"] = [
            statement("P570", {**birthday, "time": "+2020-02-28T00:00:00Z"})
        ]
        self.assertEqual(
            age_answer(
                [replace(wiki, text="Ada Reed was a singer who died."), data(deceased)],
                "Ada Reed",
                "nl",
            ),
            "Ada Reed is 19 jaar geworden.",
        )
        for source in (
            replace(sources[1], url="https://other.example/Q123.json"),
            replace(sources[1], expires_at="2001-01-01T00:00:00+00:00"),
            replace(
                sources[1],
                text=sources[1].text.replace('"id": "Q123"', '"id": "Q999", "id": "Q123"'),
            ),
        ):
            self.assertIsNone(age_answer([wiki, source], "Ada Reed", "en"))

    def test_initialism_inside_a_source_does_not_break_its_identity_sentence(self):
        from custom_components.djconnect.ask_dj.public_research import _sentences, safe_subject

        original = "R.E.M. is a rock band. Its members include Ada Reed."
        self.assertEqual(
            _sentences(original), ["R.E.M. is a rock band.", "Its members include Ada Reed."]
        )
        self.assertEqual(safe_subject("R.E.M."), "R.E.M.")
        self.assertEqual(
            _sentences("A sentence ends with R.E.M. Another sentence."),
            ["A sentence ends with R.E.M.", "Another sentence."],
        )

    def test_group_year_uses_inception_not_a_person_birthday_or_an_exact_anniversary(self):
        from custom_components.djconnect.ask_dj import public_research as r
        from custom_components.djconnect.ask_dj.biographical_dates import group_inception_answer
        from custom_components.djconnect.ask_dj.person_age import entity_url

        def claim(prop, value, datatype, kind):
            return {
                "rank": "normal",
                "mainsnak": {
                    "property": prop,
                    "snaktype": "value",
                    "datatype": datatype,
                    "datavalue": {"type": kind, "value": value},
                },
            }

        value = {
            "time": "+1996-00-00T00:00:00Z",
            "precision": 9,
            "before": 0,
            "after": 0,
            "timezone": 0,
            "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
        }
        document = {
            "entities": {
                "Q123": {
                    "id": "Q123",
                    "type": "item",
                    "sitelinks": {"enwiki": {"title": "Example Band"}},
                    "claims": {
                        "P31": [
                            claim(
                                "P31",
                                {"entity-type": "item", "numeric-id": 215380, "id": "Q215380"},
                                "wikibase-item",
                                "wikibase-entityid",
                            )
                        ],
                        "P571": [claim("P571", value, "time", "time")],
                    },
                }
            }
        }
        wiki = r._source(
            "Wikipedia",
            "Example Band",
            "https://en.wikipedia.org/wiki/Example_Band",
            "Example Band is a rock band.",
            "en",
            entity_id="Q123",
        )

        def source(body):
            return r._source(
                "Wikidata",
                "Example Band",
                entity_url("Q123", "en"),
                json.dumps(body),
                "en",
                entity_id="Q123",
                current=True,
            )

        self.assertEqual(
            group_inception_answer([wiki, source(document)], "Example Band", "nl"),
            "Example Band is opgericht in 1996.",
        )
        from custom_components.djconnect.ask_dj.biographical_dates import _group_source

        self.assertTrue(_group_source({
            "provider": "Wikipedia",
            "wikidata_id": "Q323187",
            "untrusted_excerpt": "Above & Beyond is een trancemuziekgroep.",
        }, "Above & Beyond"))
        conflicting = replace(
            wiki, text="Example Band is a rock band. Example Band was formed in 2005."
        )
        self.assertIsNone(
            group_inception_answer([conflicting, source(document)], "Example Band", "nl")
        )
        for change in (
            "wrong_kind",
            "qualified_date",
            "uncertain_date",
            "future",
            "wrong_property",
            "duplicate",
        ):
            bad = deepcopy(document)
            claims = bad["entities"]["Q123"]["claims"]
            row = claims["P571"][0]
            if change == "wrong_kind":
                claims["P31"][0]["mainsnak"]["datavalue"]["value"]["id"] = "Q5"
            elif change == "qualified_date":
                row["qualifiers"] = {"P1480": [{}]}
            elif change == "uncertain_date":
                row["mainsnak"]["datavalue"]["value"]["after"] = 1
            elif change == "future":
                row["mainsnak"]["datavalue"]["value"]["time"] = "+2099-00-00T00:00:00Z"
            elif change == "wrong_property":
                row["mainsnak"]["property"] = "P569"
            else:
                claims["P571"].append(deepcopy(row))
            with self.subTest(change=change):
                self.assertIsNone(group_inception_answer([wiki, source(bad)], "Example Band", "nl"))

    def test_name_slot_casing_never_turns_private_or_free_prose_into_a_public_query(self):
        from custom_components.djconnect.ask_dj.public_research import public_name_slot

        for name in (
            "Radiohead Anja’s chemotherapy",
            "phil collins met mijn collega jan uit eindhoven",
            "phil collins tijdens mijn scheiding",
            "phil collins mijn salaris",
            "my wife Anja",
            "my neighbour Sarah",
            "Radiohead with my wife Anja",
            "source https://private.example",
        ):
            self.assertEqual(public_name_slot(name), "", name)
        self.assertEqual(public_name_slot("phil collins"), "")

    async def test_band_selection_answers_the_original_question_in_the_same_thread(self):
        f = shared.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            from custom_components.djconnect.ask_dj import public_research as r
            from custom_components.djconnect.ask_dj.biographical_dates import candidates

            source = r._source(
                "Wikipedia",
                "Example Band",
                "https://en.wikipedia.org/wiki/Example_Band",
                "Example Band is a rock band. Example Band was formed in 1996.",
                "en",
                entity_id="Q1",
            )

            async def research(subject, question, language, guard, **kwargs):
                await guard()
                self.assertEqual(subject, "Example Band")
                return [source], {"state": "available", "synthetic_source": True}

            answer = "Example Band werd opgericht in 1996."
            calls = []

            async def agent(hass, data, **kwargs):
                projection = json.loads(data["text"].split("\nData:\n", 1)[1])
                calls.append(projection)
                if "available" in projection:
                    self.assertEqual(
                        projection["recent_public_query"]["previous_question_angle"], "age"
                    )
                    reply = {
                        "read": "research",
                        "reference": "recent",
                        "exclude_current": False,
                        "angle": "age",
                    }
                elif "evidence" in projection:
                    proof = candidates(projection["evidence"]["public_music_research"])[0]
                    reply = {
                        "supported": True,
                        "claim_checks": [
                            {
                                "text": answer,
                                "kind": "fact",
                                "evidence_ids": [proof["evidence_id"]],
                                "quote": proof["quote"],
                            }
                        ],
                        "temporal_claims": [{**proof, "claim": answer}],
                    }
                else:
                    return {"response": {"speech": {"plain": {"speech": answer}}}}
                return {"response": {"speech": {"plain": {"speech": json.dumps(reply)}}}}

            with (
                patch.object(r, "research", research),
                patch.object(f.pipeline, "_call_conversation_process_transport", agent),
            ):
                first, status = await f.request(
                    "Hoe oud is Example Band?", identifier="band-age-original", language="nl"
                )
                self.assertEqual(status, 200, first)
                self.assertTrue(first["clarification_required"])
                self.assertEqual(calls, [])
                second, status = await f.request(
                    "band", identifier="band-age-selection", language="nl"
                )
            self.assertEqual(status, 200, second)
            self.assertEqual(second["text"], answer, second)
            self.assertFalse(second.get("clarification_required"))
            self.assertEqual(len(calls), 3)
            self.assertFalse(second.get("playback_actions"))
            self.assertEqual(f.effects, [])
        finally:
            await f.asyncTearDown()
