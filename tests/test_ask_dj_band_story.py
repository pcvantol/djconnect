"""Declared source/model fixtures prove routing, never real prose quality."""
import json
import unittest
from unittest.mock import patch

from tests import test_ask_dj_contextual_dialogue as shared


class BandStoryTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def check_membership_route(self, question, *, explicit_task=None, task_failure=False):
        f = shared.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            from custom_components.djconnect.ask_dj import public_research as r
            excerpt = ("Example Band is a rock band. Example Band consists of Ava Example and Bo Sample. "
                       "Ava Example sings and Bo Sample plays guitar.")
            source = r._source("Wikipedia", "Example Band", "https://en.wikipedia.org/wiki/Example_Band",
                excerpt, "en", entity_id="Q123", original_text=excerpt,
                paragraph_ranges=((0, len(excerpt)),))
            async def research(subject, text, language, guard, **kwargs):
                await guard()
                self.assertEqual(subject, "Example Band")
                self.assertTrue(kwargs.get("original_paragraphs"), "membership needs original paragraphs on both paths")
                return [source], {"state": "available", "declared_synthetic_sources": True}
            answer = "Example Band bestaat uit Ava Example en Bo Sample. Ava Example zingt en Bo Sample speelt gitaar."
            projections = []
            typed_calls = []
            from custom_components.djconnect.structured_playback import TASK_CONFIG
            if explicit_task is not None:
                f.runtime.config[TASK_CONFIG] = explicit_task
            original_assist = f.core._assist_context
            def assist_without_task(*args, **kwargs):
                context = dict(original_assist(*args, **kwargs))
                context.pop(TASK_CONFIG, None)  # The observed missing-pipeline projection boundary.
                return context
            async def rejected_task(*args, **kwargs):
                typed_calls.append(kwargs.get("task_id"))
                raise ValueError("declared explicitly configured task failure")
            async def agent(hass, data, **kwargs):
                projection = json.loads(data["text"].split("\nData:\n", 1)[1])
                projections.append(projection)
                if "available" in projection:
                    reply = {"read": "research", "reference": "named", "subject": "Example Band",
                             "exclude_current": False, "angle": "members"}
                elif "drafts" in projection or "evidence" in projection:
                    reply = shared._research_assessment_fixture(projection)
                else:
                    self.assertEqual(projection.get("artist_draft_schema"), "artist_evidence_drafts_v1",
                                     "a direct membership question must get the same complete artist review route")
                    reply = shared._research_generation_fixture(projection, answer)
                    return {"response": {"speech": {"plain": {"speech": reply}}}}
                return {"response": {"speech": {"plain": {"speech": json.dumps(reply)}}}}
            from contextlib import nullcontext
            with patch.object(r, "research", research), patch.object(f.pipeline, "_call_conversation_process_transport", agent), \
                 (patch.object(f.core, "_assist_context", assist_without_task) if task_failure else nullcontext()), \
                 (patch.object(f.pipeline, "call_structured_artist", rejected_task) if task_failure else nullcontext()):
                result, status = await f.request(question, identifier="members-" + str(question.islower()), language="nl")
            if task_failure:
                self.assertEqual(typed_calls, [None], "explicit configured Task cannot disappear into ordinary generation")
                self.assertEqual(projections, [], "a failed explicit Task cannot buy another provider path")
                self.assertNotEqual(result.get("knowledge_basis"), "fetched_public_music_research_v1")
                return
            self.assertEqual(status, 200, result)
            self.assertEqual(result["text"], answer, result)
            self.assertEqual(result.get("knowledge_basis"), "fetched_public_music_research_v1")
            self.assertTrue(any(p.get("artist_draft_schema") for p in projections))
            self.assertFalse(result.get("clarification_required"))
            self.assertEqual(f.effects, [])
        finally:
            await f.asyncTearDown()

    async def test_explicit_membership_uses_complete_artist_route(self):
        await self.check_membership_route("Uit welke bandleden bestaat Example Band?")

    async def test_interpreted_membership_uses_complete_artist_route(self):
        await self.check_membership_route("uit welke bandleden bestaat example band?")

    async def test_explicit_task_lost_from_assist_projection_cannot_select_another_path(self):
        for task in ("ai_task.synthetic_explicit_owner", False):
            with self.subTest(task=task):
                await self.check_membership_route("Uit welke bandleden bestaat Example Band?",
                    explicit_task=task, task_failure=True)


class BandPhotoLeaseTests(unittest.IsolatedAsyncioTestCase):
    """Explicit synthetic owner/capability fixtures, not installed authority proof."""
    @classmethod
    def setUpClass(cls):
        shared.SharedDialogueTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        shared.SharedDialogueTest.tearDownClass()

    async def asyncSetUp(self):
        import asyncio
        from types import SimpleNamespace
        from custom_components.djconnect.ask_dj import band_story as b
        from custom_components.djconnect.const import DOMAIN
        import sys
        self.constants_patch = patch.dict(sys.modules, {
            "homeassistant.const": SimpleNamespace(EVENT_HOMEASSISTANT_STOP="homeassistant_stop")})
        self.constants_patch.start()  # Explicit light-unit SDK fixture, not actual HA evidence.
        self.b = b
        self.unloads = []
        self.allowed = True
        self.hass = SimpleNamespace(data={}, loop=asyncio.get_running_loop(),
            bus=SimpleNamespace(async_listen_once=lambda *_: lambda: None))
        self.runtime = SimpleNamespace(entry=SimpleNamespace(entry_id="synthetic-original-entry",
            async_on_unload=self.unloads.append))
        self.registry = b.images(self.hass)
        self.assertIs(self.hass.data[DOMAIN]["public_band_images"], self.registry)

    async def asyncTearDown(self):
        self.registry.close()
        self.constants_patch.stop()

    def asset(self, seconds=30, provider_entry=None, history=None, request_id="fixture-request"):
        import time
        return self.registry.commit(body=b"declared-validated-original-test-pixels", mime="image/png",
            allowed=lambda: self.allowed, runtime=self.runtime,
            wall_deadline=time.time() + seconds, mono_deadline=time.monotonic() + seconds, provider_entry=provider_entry or self.runtime.entry, history=history or self, scope="profile:unit", request_id=request_id,
            metadata={"title": "Example Band", "kind": "artist_image", "source": "wikimedia_commons",
                      "attribution": {"author": "Example Photographer", "license": "CC-BY-4.0"}})

    async def test_original_pixels_and_attribution_survive_normalization_without_refetch(self):
        from types import SimpleNamespace
        from custom_components.djconnect import ask_dj
        import aiohttp
        url = self.asset()
        token = url.rsplit("/", 1)[1]
        with patch.object(aiohttp.web, "Response", lambda **kw: SimpleNamespace(**kw)):
            response = await self.b.image_response(self.hass, SimpleNamespace(headers={}), token)
        self.assertEqual(response.body, b"declared-validated-original-test-pixels")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        normalized = ask_dj._provided_images(self.hass, [{"url": url, "attribution": {"author": "INJECTED"}}])
        self.assertEqual(normalized[0]["attribution"]["author"], "Example Photographer")
        normalized[0]["attribution"]["author"] = "LOCAL_MUTATION"
        self.assertEqual(self.b.projection_for_url(self.hass, url)["attribution"]["author"], "Example Photographer")

    async def test_observed_withdrawal_is_terminal_and_scrubs_original_bytes(self):
        url = self.asset()
        token = url.rsplit("/", 1)[1]
        original = self.registry.get(token)
        self.allowed = False
        self.assertIsNone(self.registry.get(token))
        self.assertEqual(original, {})
        self.allowed = True
        self.assertIsNone(self.registry.get(token))
        self.assertIsNone(self.b.projection_for_url(self.hass, url))

    async def test_expiry_and_actual_entry_unload_remove_assets(self):
        import time
        first = self.asset().rsplit("/", 1)[1]
        with patch.object(time, "monotonic", return_value=time.monotonic() + 31):
            self.assertIsNone(self.registry.get(first))
        second = self.asset().rsplit("/", 1)[1]
        self.assertEqual(len(self.unloads), 1)
        self.unloads[0]()
        self.assertIsNone(self.registry.get(second))
        self.assertEqual(self.registry.assets, {})

    async def test_distinct_provider_unload_scrubs_without_a_get(self):
        from types import SimpleNamespace
        provider_unloads = []
        provider = SimpleNamespace(entry_id="synthetic-distinct-provider",
            async_on_unload=provider_unloads.append)
        token = self.asset(provider_entry=provider).rsplit("/", 1)[1]
        original = self.registry.assets[token]
        self.assertEqual(len(provider_unloads), 1)
        provider_unloads[0]()
        self.assertEqual(original, {})
        self.assertEqual(self.registry.assets, {})

    async def test_empty_partial_duplicate_credentials_do_not_downgrade_to_headerless(self):
        from types import SimpleNamespace
        import aiohttp
        from custom_components.djconnect import request_auth
        token = self.asset().rsplit("/", 1)[1]
        class Headers(dict):
            def getall(self, key, default):
                value = self.get(key)
                return value if isinstance(value, list) else [value] if key in self else default
        bad = (Headers(Authorization=""), Headers(Authorization=["", ""]),
               Headers({"X-DJConnect-Device-ID": "only-partial"}))
        with patch.object(aiohttp.web, "Response", lambda **kw: SimpleNamespace(**kw)), \
             patch.object(request_auth, "authorize_runtime_device_request", return_value=False):
            for headers in bad:
                response = await self.b.image_response(self.hass, SimpleNamespace(headers=headers), token)
                self.assertEqual(response.status, 401)
            anonymous = await self.b.image_response(self.hass, SimpleNamespace(headers={}), token)
            self.assertEqual(anonymous.body, b"declared-validated-original-test-pixels")

    async def test_registry_capacity_is_bounded_and_stop_scrubs_all(self):
        for _ in range(self.b.MAX_ASSETS):
            self.assertTrue(self.asset())
        self.assertEqual(self.asset(), "")
        retained = list(self.registry.assets.values())
        self.registry.close()
        self.assertTrue(all(not asset for asset in retained))
        self.assertEqual(self.registry.assets, {})
        self.assertEqual(self.asset(), "")

    async def test_unified_erase_scrubs_original_pixels_after_store_ack_without_get(self):
        from copy import deepcopy
        from custom_components.djconnect.ask_dj_history import AskDJHistoryManager
        from custom_components.djconnect.const import DOMAIN
        class Store:
            def __init__(self):
                self.data = None
            async def async_load(self):
                return deepcopy(self.data)
            async def async_save(self, data):
                self.data = deepcopy(data)
        store = Store()
        history = AskDJHistoryManager(self.hass, store=store)
        await history.async_load()
        self.hass.data[DOMAIN]["ask_dj_history_manager"] = history
        url = self.asset(history=history, request_id="old-request")
        token = url.rsplit("/", 1)[1]
        original = self.registry.assets[token]
        await history.async_append_exchange("profile:unit", {"client_message_id": "old-request", "text": "Synthetic old"},
            {"success": True, "text": "Synthetic answer", "images": [{"url": url}]},
            session_turn={"turn_id": "original-turn", "context": {"session_id": "old-session"}})
        self.assertIs(self.registry.assets[token], original, "ordinary append must preserve the original lease")
        self.assertNotIn("/image_proxy/band-", json.dumps(store.data), "no expiring capability in Store")
        reply = await history.async_history("profile:unit")
        assistant = next(m for m in reply["messages"] if m["role"] == "assistant")
        self.assertEqual(assistant["images"][0]["url"], url)
        async def prepare(plan):
            self.assertTrue(original["body"], "the original lease exists before durable erasure")
            return plan
        await history.async_erase_archived_sessions("unit", frozenset({"old-session"}),
            prepare_intent=prepare, entry_index={})
        self.assertEqual(original, {}, "actual unified erase must scrub without another GET")
        self.assertNotIn(token, self.registry.assets)

    async def test_targeted_privacy_clear_is_not_hidden_by_dialogue_revision(self):
        f = shared.SharedDialogueTest()
        await f.asyncSetUp()
        try:
            h = f.history
            state = h._data.setdefault("users", {}).setdefault("profile:lease-test", {})
            state.update(clear_revision=3, targeted_clear_revision=1)
            dialogue = h.scope_revision("profile:lease-test")
            media = h.media_privacy_revision("profile:lease-test")
            state.update(clear_revision=4, targeted_clear_revision=2)
            self.assertEqual(h.scope_revision("profile:lease-test"), dialogue)
            self.assertNotEqual(h.media_privacy_revision("profile:lease-test"), media)
            media = h.media_privacy_revision("profile:lease-test")
            state["history_revision"] = 99  # Ordinary new messages do not renew/revoke the original image.
            self.assertEqual(h.media_privacy_revision("profile:lease-test"), media)
        finally:
            await f.asyncTearDown()


class BandStoryActualHAEvidenceTests(unittest.TestCase):
    def test_current_source_and_original_ha_receipt_are_exact_and_not_editorial_acceptance(self):
        from pathlib import Path
        import hashlib
        root = Path(__file__).resolve().parents[1]
        proof = json.loads((root / "examples/client_contracts/band_members_story_v1/actual-ha-current.json").read_text())
        self.assertEqual(len(proof["source_pins"]), 304)
        for name, digest in {**proof["source_pins"], **proof["original_common_harness_source_pins"],
                proof["harness"]: proof["harness_sha256"]}.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, name)
        self.assertTrue(proof["own_container_verified_absent"])
        extension = proof["original_receipt"]["extension"]
        self.assertEqual(len(extension["cases"]), 9)
        self.assertEqual({row["state"] for row in extension["cases"]}, {"PASS"})
        self.assertEqual((extension["paid_model_calls"], extension["external_network_calls"]), (0, 0))
        self.assertIn("Not real prose", proof["quality_scope"])
