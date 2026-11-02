"""Explicit detail must obtain real CC0 facts without a Session publication."""
import asyncio
import importlib
import time
from dataclasses import replace
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from tests import test_current_track_insight_runtime_identity as fixture

URI = fixture.URI
RID = "11111111-1111-1111-1111-111111111111"


class CurrentKnowledgeTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixture.CurrentRuntimeValueTests.asyncSetUp(self)
        self.target = importlib.import_module("custom_components.djconnect.track_insight_target")
        self.facts = importlib.import_module("custom_components.djconnect.session_facts")
        await self.manager.async_update_playback_projection(owner_profile_id="synthetic-owner",
            session_id=self.active.session_id, state="playing", media_identity=URI,
            title="Synthetic track", artist="Synthetic artist", album="Synthetic album",
            duration_ms=180000, position_ms=10000)
        self.manager._intra_track_opportunities.pop("synthetic-owner", None)
        self.allowed = True
        self.revision = "original-grant"
        self.catalog = {"uri": URI, "title": "Synthetic track", "artist": "Synthetic artist",
                        "isrc": "USABC0100001"}
        observed = SimpleNamespace(catalog=self.catalog, target_name="")
        frame = self.module.observe(self.runtime, URI, "playing", 10000)
        def scope():
            return self.module.session_scope(self.manager.current_active("synthetic-owner"))
        self.current = self.module.CurrentSubject(self.runtime, frame, None,
            {"title": "Synthetic track", "artist": "Synthetic artist"}, None,
            scope, scope(), "en", observed, frame.observed_at+30,
            knowledge_authority=lambda: self.allowed)
        for seam in (patch.object(self.target, "session_runtime_manager", return_value=self.manager),
                     patch.object(self.target, "history_grant_revision", side_effect=lambda *_: self.revision)):
            seam.start()
            self.addCleanup(seam.stop)
        self.paths = []
        self.recording = {"id": RID, "title": "Synthetic track",
                          "artist-credit": [{"artist": {"name": "Synthetic artist"}}]}
        self.details = {**self.recording, "relations": [{"type": "producer", "target-type": "artist",
                                                       "artist": {"name": "Synthetic producer"}}]}
        test = self
        class Resolver(self.facts.SessionFactsResolver):
            async def _get(inner, path, params=None, **kwargs):
                test.paths.append(path)
                return {"recordings": [test.recording]} if path.startswith("isrc/") else test.details
        self.resolver = Resolver(self.hass)
        self.hass.data["djconnect"]["session_facts_resolver"] = self.resolver

    async def resolve(self):
        return await self.target.resolve_current_knowledge(self.hass, "synthetic-owner", self.current)

    async def test_real_two_step_cc0_lookup_without_opportunity_or_publication(self):
        before = dict(self.manager._intra_track_opportunities)
        result = await self.resolve()
        self.assertIsNotNone(result)
        self.assertEqual(self.paths, ["isrc/USABC0100001", "recording/"+RID])
        model, guard, fingerprint, active, deadline = result
        self.assertIn("Synthetic producer", str(model))
        self.assertNotIn("USABC", str(model))
        self.assertNotIn("Synthetic track", str(model))
        self.assertIn("CC0-1.0", str(model))
        self.assertEqual(len(fingerprint), 64)
        self.assertEqual(self.manager._intra_track_opportunities, before)
        self.assertLessEqual(deadline, self.current.frame.observed_at+30)
        guard()
        self.revision = "withdrawn"
        with self.assertRaises(self.target.TrackInsightError):
            guard()
        self.revision = "original-grant"
        with self.assertRaises(self.target.TrackInsightError):
            guard()

    async def test_no_original_authority_no_source_request(self):
        self.allowed = False
        self.assertIsNone(await self.resolve())
        self.assertEqual(self.paths, [])

    async def test_no_isrc_or_wrong_catalog_never_queries(self):
        for change in ({"isrc": ""}, {"uri": URI.replace("A", "B")},
                       {"title": "Other"}, {"artist": "Other"}):
            self.current.observed.catalog = {**self.catalog, **change}
            self.assertIsNone(await self.resolve())
        self.assertEqual(self.paths, [])

    async def test_missing_or_ambiguous_exact_credit_remains_unmeasured(self):
        self.details = {**self.recording, "relations": []}
        self.assertIsNone(await self.resolve())
        self.details = {**self.recording, "title": "Other version"}
        self.assertIsNone(await self.resolve())

    async def test_late_withdrawal_denies_before_second_lookup_and_latches(self):
        original = self.resolver._get
        async def withdraw(*args, **kwargs):
            result = await original(*args, **kwargs)
            self.allowed = False
            return result
        with patch.object(self.resolver, "_get", withdraw):
            with self.assertRaises(self.target.TrackInsightError):
                await self.resolve()
        self.assertEqual(self.paths, ["isrc/USABC0100001"])

    async def test_cancelled_lookup_is_not_soft_fallback(self):
        started = asyncio.Event()
        async def waiting(*args, **kwargs):
            started.set()
            await asyncio.Event().wait()
        with patch.object(self.resolver, "_get", waiting):
            task = asyncio.create_task(self.resolve())
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(self.manager._intra_track_opportunities, {})

    async def test_source_timeout_is_honest_absence_without_second_attempt(self):
        async def timeout(*args, **kwargs):
            self.paths.append(args[0])
            raise TimeoutError
        with patch.object(self.resolver, "_get", timeout):
            self.assertIsNone(await self.resolve())
        self.assertEqual(len(self.paths), 1)

    async def test_source_fact_expiry_only_shortens_original_deadline(self):
        original = self.resolver.resolve
        deadline = time.monotonic()+0.1
        async def near_expiry(*args, **kwargs):
            return tuple(replace(fact, source_expires_at=deadline) for fact in await original(*args, **kwargs))
        with patch.object(self.resolver, "resolve", near_expiry):
            result = await self.resolve()
        self.assertIsNotNone(result)
        self.assertEqual(result[4], deadline)
        self.assertEqual(self.current.original_deadline, deadline)
        with patch.object(self.module.time, "monotonic", return_value=deadline+0.01):
            with self.assertRaises(Exception):
                result[1]()

    async def test_withdrawn_authority_after_resolver_lock_wait_never_dispatches(self):
        resolver = self.facts.SessionFactsResolver(self.hass)
        await resolver.lock.acquire()
        task = asyncio.create_task(resolver._get("isrc/USABC0100001", authorize=self.current_guard))
        await asyncio.sleep(0)
        self.allowed = False
        resolver.lock.release()
        with self.assertRaises(PermissionError):
            await task

    def current_guard(self):
        if not self.allowed:
            raise PermissionError("synthetic_original_authority_withdrawn")

    async def test_rate_limiter_withdrawal_is_checked_before_http(self):
        rate = importlib.import_module("custom_components.djconnect.musicbrainz_rate")
        resolver = self.facts.SessionFactsResolver(self.hass)
        async def withdrawn(guard=None):
            self.assertIsNotNone(guard)
            self.allowed = False
            await guard()
            self.fail("withdrawn admission must not return")
        with patch.object(rate, "admit", withdrawn):
            with self.assertRaises(PermissionError):
                await resolver._get("isrc/USABC0100001", authorize=self.current_guard)

    async def test_returned_credit_has_no_audio_measurements(self):
        result = await self.resolve()
        insight = importlib.import_module("custom_components.djconnect.track_insight")
        detail = insight._qualified_detail_analysis({}, result[0], "en")
        self.assertFalse(detail["measured_audio"])
        for key in ("energy", "danceability", "intensity", "mood", "vibe", "texture"):
            self.assertIsNone(detail[key])
        self.assertIn("Synthetic producer", detail["verified_context"])

    async def test_observed_catalog_mutation_cannot_change_inflight_lookup_anchors(self):
        original = self.resolver._get
        async def mutate(*args, **kwargs):
            self.catalog["title"] = "Later replacement"
            self.catalog["isrc"] = "GBABC0200002"
            return await original(*args, **kwargs)
        with patch.object(self.resolver, "_get", mutate):
            self.assertIsNotNone(await self.resolve())
        self.assertEqual(self.paths, ["isrc/USABC0100001", "recording/"+RID])

    async def test_real_global_rate_lock_withdrawal_cannot_dispatch(self):
        rate = importlib.import_module("custom_components.djconnect.musicbrainz_rate")
        _, state = rate._state()
        await state.lock.acquire()
        resolver = self.facts.SessionFactsResolver(self.hass)
        task = asyncio.create_task(resolver._get("isrc/USABC0100001", authorize=self.current_guard))
        try:
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.allowed = False
        finally:
            state.lock.release()
        with self.assertRaises(PermissionError):
            await task

    async def test_late_http_body_withdrawal_denies_before_another_lookup(self):
        import json
        import sys
        rate = importlib.import_module("custom_components.djconnect.musicbrainz_rate")
        calls = []
        test = self
        class Body:
            async def iter_chunked(self, size):
                await asyncio.sleep(0)
                test.allowed = False
                yield json.dumps({"recordings": [test.recording]}).encode()
        class Response:
            status = 200
            content_length = None
            content = Body()
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
        def get(url, **kwargs):
            calls.append(url)
            return Response()
        async def admitted(guard=None):
            if guard is not None:
                await guard()
            return True
        client = SimpleNamespace(async_get_clientsession=lambda _: SimpleNamespace(get=get))
        self.hass.data["djconnect"]["session_facts_resolver"] = self.facts.SessionFactsResolver(self.hass)
        with patch.dict(sys.modules, {"homeassistant.helpers.aiohttp_client": client,
                "aiohttp": SimpleNamespace(ClientTimeout=lambda **kwargs: kwargs,
                                           ClientError=ConnectionError)}), \
                patch.object(rate, "admit", admitted):
            with self.assertRaises(self.target.TrackInsightError):
                await self.resolve()
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.manager._intra_track_opportunities, {})

    async def test_foreign_fact_cannot_authorize_model_context(self):
        original = self.resolver.resolve
        async def foreign(*args, **kwargs):
            return tuple(replace(fact, media_identity="spotify:track:"+"B"*22)
                         for fact in await original(*args, **kwargs))
        with patch.object(self.resolver, "resolve", foreign):
            self.assertIsNone(await self.resolve())
