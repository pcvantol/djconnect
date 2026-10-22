"""Real async reservation order/restart/races with synthetic model boundaries."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import unittest

from tests.test_bulletin_intake import NOW, rss
from custom_components.djconnect.bulletin_intake import SOURCES, parse_feed
from custom_components.djconnect.bulletin_builder import (
    BuilderError, BulletinBuilder, BulletinSession, possibly_same_story,
)


class Store:
    def __init__(self):
        self.data = None
        self.fail = False

    async def async_load(self):
        return deepcopy(self.data)

    async def async_save(self, data):
        if self.fail:
            raise OSError
        self.data = deepcopy(data)


class BulletinBuilderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = Store()
        self.clock = [NOW, 100.0]
        self.session = BulletinSession("synthetic-session", "owner-original", "source-original",
            "settings-original", 1, 1, 1, 1, "home_dj", "groove", "balanced", "nl")
        self.valid = True
        self.calls = []
        self.hook = None
        self.items = (
            parse_feed(SOURCES[0], rss(SOURCES[0], title="Synthetic statistics agency reports household incomes"), now=NOW)[0],
            parse_feed(SOURCES[1], rss(SOURCES[1], title="Weather institute opens coastal storm research station", suffix="two"), now=NOW)[0],
        )
        self.text = " ".join(["Een korte synthetische vertelling uitsluitend voor deze test zonder echte nieuwsclaims."] * 7)
        self.builder = BulletinBuilder(self.store, self.model,
            wall=lambda: self.clock[0], monotonic=lambda: self.clock[1])
        await self.builder.initialize()

    def guard(self):
        if not self.valid:
            raise PermissionError("original_context_changed")

    async def model(self, prompt, session, guard):
        self.assertIsNotNone(self.store.data)  # Durable reservation precedes BOTH calls.
        self.assertEqual(len(self.store.data["reservations"]), 4)
        self.calls.append(prompt)
        if self.hook:
            await self.hook()
        guard()
        if "Assess every" in prompt:
            return json.dumps({"supported": True, "independent_stories": True,
                "language_ok": True, "style_ok": True})
        return json.dumps({"text": self.text, "story_ids": [i.fingerprint for i in self.items]})

    async def prepare(self, **kwargs):
        return await self.builder.prepare(self.items, session=kwargs.get("session", self.session), guard=self.guard)

    async def test_two_distinct_stories_one_cached_candidate_no_poll_publication_or_repeat_generation(self):
        candidate = await self.prepare()
        self.assertIsNotNone(candidate)
        self.assertIs(await self.prepare(), candidate)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(candidate.session, self.session)
        self.assertEqual(candidate.expires_at, min(i.published_at + 1800 for i in self.items))
        self.assertFalse(hasattr(self.builder, "publish"))
        stored = json.dumps(self.store.data)
        self.assertNotIn(self.text, stored)
        self.assertNotIn(self.session.session_id, stored)
        self.assertNotIn(self.items[0].title, stored)
        self.assertNotIn(self.items[0].source_url, stored)

    async def test_one_story_two_publishers_is_not_enough(self):
        duplicate = replace(self.items[0], source_id=SOURCES[1].source_id,
            source_url="https://www.knmi.nl/different-url", fingerprint="f" * 64)
        self.assertTrue(possibly_same_story(self.items[0], duplicate))
        self.assertIsNone(await self.builder.prepare((self.items[0], duplicate), session=self.session, guard=self.guard))
        self.assertEqual(self.calls, [])

    async def test_music_only_never_calls_model_and_store_failure_never_falls_through(self):
        with self.assertRaises(BuilderError):
            await self.prepare(session=replace(self.session, presence="music_only"))
        self.assertEqual(self.calls, [])
        self.store.fail = True
        with self.assertRaises(BuilderError):
            await self.prepare()
        self.assertEqual(self.calls, [])

    async def test_restart_loses_ram_candidate_but_does_not_repeat_reserved_stories(self):
        self.assertIsNotNone(await self.prepare())
        restart = BulletinBuilder(self.store, self.model, wall=lambda: self.clock[0], monotonic=lambda: self.clock[1])
        await restart.initialize()
        self.assertIsNone(await restart.prepare(self.items, session=self.session, guard=self.guard))
        self.assertEqual(len(self.calls), 2)

    async def test_concurrency_generates_once_and_planner_can_take_once_only(self):
        a, b = await asyncio.gather(self.prepare(), self.prepare())
        self.assertIs(a, b)
        self.assertEqual(len(self.calls), 2)
        self.assertIs(await self.builder.take(a, session=self.session, guard=self.guard), a)
        self.assertIsNone(await self.builder.take(a, session=self.session, guard=self.guard))
        self.assertIsNone(await self.prepare())

    async def test_owner_loss_during_model_discards_without_release_or_late_candidate(self):
        async def lose():
            self.valid = False
        self.hook = lose
        self.assertIsNone(await self.prepare())
        self.assertEqual(len(self.calls), 1)
        self.valid, self.hook = True, None
        self.assertIsNone(await self.prepare())
        self.assertEqual(len(self.calls), 1)

    async def test_cancelled_model_does_not_auto_retry_after_restart(self):
        async def cancel():
            raise asyncio.CancelledError
        self.hook = cancel
        with self.assertRaises(asyncio.CancelledError):
            await self.prepare()
        self.hook = None
        restart = BulletinBuilder(self.store, self.model, wall=lambda: self.clock[0])
        await restart.initialize()
        self.assertIsNone(await restart.prepare(self.items, session=self.session, guard=self.guard))
        self.assertEqual(len(self.calls), 1)

    async def test_window_expires_during_model_and_ready_candidate_does_not_get_renewed(self):
        async def expire():
            self.clock[0] += 1800
            self.clock[1] += 1800
        self.hook = expire
        self.assertIsNone(await self.prepare())
        self.assertEqual(len(self.calls), 1)

    async def test_settings_source_owner_and_presence_revisions_fence_existing_candidate(self):
        candidate = await self.prepare()
        for field, value in (("persona_revision", 2), ("mood_revision", 2),
                ("presence_revision", 2), ("settings_revision", 2),
                ("owner_generation", "new-owner"), ("source_generation", "new-source"),
                ("session_id", "new-session"), ("presence", "music_only")):
            changed = replace(self.session, **{field: value})
            self.assertFalse(candidate.eligible(session=changed, now=NOW, monotonic=100))
        self.assertFalse(candidate.eligible(session=self.session, now=NOW, monotonic=candidate.monotonic_deadline))

    async def test_hallucinated_or_same_event_assessment_is_silent_without_retry(self):
        async def reject(prompt, session, guard):
            self.calls.append(prompt)
            if "Assess every" in prompt:
                return json.dumps({"supported": False, "independent_stories": False,
                    "language_ok": True, "style_ok": True})
            return json.dumps({"text": self.text, "story_ids": [i.fingerprint for i in self.items]})
        self.builder.generate = reject
        self.assertIsNone(await self.prepare())
        self.assertIsNone(await self.prepare())
        self.assertEqual(len(self.calls), 2)

    async def test_duplicate_json_keys_and_non_boolean_assessment_fail_closed(self):
        self.builder.generate = lambda *args: asyncio.sleep(0, result='{"text":"one","text":"two","story_ids":[]}')
        self.assertIsNone(await self.prepare())

    async def test_corrupt_dedup_store_is_not_silently_repaired(self):
        self.store.data = {"schema": True, "clock": 0, "reservations": {}}
        restart = BulletinBuilder(self.store, self.model)
        with self.assertRaises(BuilderError):
            await restart.initialize()

    async def test_model_sdk_failure_is_silent_and_does_not_release_reservation(self):
        async def unavailable(*args):
            raise RuntimeError("synthetic-provider-failure")
        self.builder.generate = unavailable
        self.assertIsNone(await self.prepare())
        self.assertIsNone(await self.prepare())
        self.assertEqual(len(self.store.data["reservations"]), 4)

    async def test_flat_wallclock_cannot_renew_original_monotonic_window_after_model(self):
        self.items = tuple(replace(i, published_at=NOW - 1790) for i in self.items)
        async def slow_with_flat_wall():
            self.clock[1] += 20  # UTC is frozen, genuine elapsed time is not.
        self.hook = slow_with_flat_wall
        self.assertIsNone(await self.prepare())
        self.assertEqual(len(self.calls), 1)

    async def test_queued_waiter_cannot_escape_a_store_failure_quarantine(self):
        entered, release = asyncio.Event(), asyncio.Event()
        saves = []
        async def save(data):
            saves.append(deepcopy(data))
            if len(saves) == 1:
                entered.set()
                await release.wait()
                raise OSError("synthetic-durable-store-failure")
            self.store.data = deepcopy(data)
        async def model(*args):
            self.calls.append("must-not-run")
            return "{}"
        self.store.async_save, self.builder.generate = save, model
        first = asyncio.create_task(self.prepare())
        await entered.wait()
        other = (replace(self.items[0], source_url="https://www.cbs.nl/other",
                    title="Archaeologists uncover ancient coastal settlement artifacts"),
                 replace(self.items[1], source_url="https://www.knmi.nl/other",
                    title="Astronomers release distant planetary observations archive"))
        second = asyncio.create_task(self.builder.prepare(other, session=self.session, guard=self.guard))
        await asyncio.sleep(0)
        release.set()
        results = await asyncio.gather(first, second, return_exceptions=True)
        self.assertTrue(all(isinstance(r, BuilderError) for r in results))
        self.assertEqual(len(saves), 1)
        self.assertEqual(self.calls, [])

    async def test_take_fails_closed_after_store_quarantine(self):
        candidate = await self.prepare()
        self.builder._failed = True
        with self.assertRaises(BuilderError):
            await self.builder.take(candidate, session=self.session, guard=self.guard)

    async def test_slow_reservation_save_cannot_restart_freshness_before_first_model(self):
        self.items = tuple(replace(i, published_at=NOW - 1790) for i in self.items)
        save = self.store.async_save
        async def delayed(data):
            await save(data)
            self.clock[1] += 20
        self.store.async_save = delayed
        self.assertIsNone(await self.prepare())
        self.assertEqual(self.calls, [])

    async def test_wait_for_lock_cannot_restart_the_original_candidate_deadline(self):
        self.items = tuple(replace(i, published_at=NOW - 1790) for i in self.items)
        await self.builder._lock.acquire()
        task = asyncio.create_task(self.prepare())
        await asyncio.sleep(0)
        self.clock[1] += 20
        self.builder._lock.release()
        with self.assertRaises(BuilderError):
            await task
        self.assertEqual(self.calls, [])

    async def test_candidate_cannot_exceed_existing_moment_speech_character_extent(self):
        self.text = " ".join(["abcdefghijklmnopqrst"] * 64)
        self.assertTrue(1200 < len(self.text) <= 1400)
        self.assertIsNone(await self.prepare())
