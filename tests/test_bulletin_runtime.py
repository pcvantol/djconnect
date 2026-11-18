"""Actual Runtime/Planner/Flow/Presence/native/speech, synthetic feed/model only."""
from dataclasses import replace
from datetime import datetime, timezone
from email.utils import format_datetime
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from tests.test_persistence_platform import PersistenceService, SQLitePersistenceProvider
from tests.test_session_runtime import _load_runtime_module
from tests.test_bulletin_builder import Store
from tests.test_bulletin_intake import rss
from custom_components.djconnect.bulletin_intake import SOURCES, parse_feed
from custom_components.djconnect.bulletin_builder import BulletinBuilder
from custom_components.djconnect.bulletin_runtime import (
    capture_work, admitted,
)
from custom_components.djconnect.persistence.sessions import PersistentSessionRepository
from custom_components.djconnect.persistence.history import HistoricalProjectionRepository


class BulletinRuntimeTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # This synthetic Runtime loader must not leave parent aliases or early
        # transport imports in other test classes' differently configured SDKs.
        cls.previous_modules = {k: v for k, v in sys.modules.items()
            if k.startswith("custom_components.djconnect")}
        cls.package = sys.modules["custom_components.djconnect"]
        cls.previous_parent = cls.package.__dict__.copy()
        cls.core, cls.previous_const = _load_runtime_module()
        cls.package.session_runtime = cls.core

    @classmethod
    def tearDownClass(cls):
        for key in tuple(sys.modules):
            if key.startswith("custom_components.djconnect") and key not in cls.previous_modules:
                sys.modules.pop(key, None)
        sys.modules.update(cls.previous_modules)
        for key in tuple(cls.package.__dict__):
            if key not in cls.previous_parent:
                delattr(cls.package, key)
        cls.package.__dict__.update(cls.previous_parent)

    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.persistence = PersistenceService(Path(self.directory.name) / "news.sqlite", SQLitePersistenceProvider())
        await self.persistence.async_initialize()
        self.clock = [time.monotonic()]
        self.manager = self.core.SessionRuntimeManager(
            PersistentSessionRepository(self.persistence), HistoricalProjectionRepository(self.persistence),
            monotonic_source=lambda: self.clock[0])
        self.active = await self.manager.async_start(owner_profile_id="synthetic-owner", locale="nl")
        self.sid = self.active.session_id
        await self.observe()
        self.authorized = True
        self.revision = [0]
        self.calls = []
        self.hook = None
        now = time.time()
        stamp = format_datetime(datetime.fromtimestamp(now - 20, timezone.utc))
        self.items = (
            parse_feed(SOURCES[0], rss(SOURCES[0], date=stamp,
                title="Household income statistics released by institute"), now=now)[0],
            parse_feed(SOURCES[1], rss(SOURCES[1], date=stamp, suffix="two",
                title="Coastal weather research station opens for scientists"), now=now)[0])
        self.text = " ".join(["Dit is een synthetische nieuwstest met uitsluitend gecontroleerde voorbeeldgegevens voor de luisteraar."] * 6)
        def authorize():
            if not self.authorized:
                raise PermissionError("synthetic-owner-withdrawn")
        def capture():
            original = self.revision[0]
            def guard():
                authorize()
                if self.revision[0] != original:
                    raise PermissionError("synthetic-source-ABA")
            return guard
        async def model(prompt, session, guard):
            self.calls.append(prompt)
            if self.hook:
                await self.hook()
            guard()
            if "Assess every" in prompt:
                return json.dumps({"supported": True, "independent_stories": True,
                    "language_ok": True, "style_ok": True})
            return json.dumps({"text": self.text, "story_ids": [i.fingerprint for i in self.items]})
        self.manager.connect_bulletin("synthetic-owner", self.sid, model, authorize, capture)
        self.work = capture_work(self.manager, "synthetic-owner")
        self.builder = BulletinBuilder(Store(), model)
        await self.builder.initialize()
        self.candidate = await self.builder.prepare(self.items, session=self.work.session, guard=self.work.guard)
        self.assertIsNotNone(self.candidate)
        class Ready:
            closed = False
            def ready(inner, owner, sid):
                return (self.builder, self.candidate, self.work) if owner == self.work.owner and sid == self.sid else None
        self.service = Ready()
        self.manager._bulletin_service = self.service

    async def asyncTearDown(self):
        await self.persistence.async_close()
        self.directory.cleanup()

    async def observe(self, position=10000, duration=300000, state="playing"):
        await self.manager.async_update_playback_projection(owner_profile_id="synthetic-owner",
            session_id=self.sid, state=state, media_identity="synthetic-media",
            title="Synthetic track", artist="Synthetic artist", target_name="Synthetic output",
            position_ms=position, duration_ms=duration)

    async def publish(self):
        return await self.manager.async_maybe_publish_intra_track_moment(owner_profile_id="synthetic-owner",
            session_id=self.sid, media_identity="synthetic-media")

    async def test_one_normal_moment_same_ledger_and_shared_vibecast_flow(self):
        events, shared = [], []
        self.active.broadcast.subscribe(events.append)
        self.active.broadcast.subscribe_with_broadcast_token(self.active.broadcast.broadcast_token, shared.append)
        before = self.active.presence_ledger.total_published
        moment = await self.publish()
        self.assertIsNotNone(moment)
        self.assertEqual(moment.moment_type.value, "dj_bulletin")
        self.assertEqual(self.active.presence_ledger.total_published, before + 1)
        self.assertEqual(self.active.planner.last_decision.decision_type.value, "create_dj_bulletin")
        self.assertTrue(any(i.moment_id == moment.moment_id for i in self.active.planner.output.session_flow.items))
        owner = json.dumps(self.active.broadcast.as_dict(include_owner_only=True))
        guest = json.dumps(self.active.broadcast.as_dict(include_owner_only=False))
        self.assertIn(self.text, owner)
        for public in (self.text, moment.moment_id, self.items[0].title, self.items[0].source_url, "dj_bulletin"):
            self.assertIn(public, guest)
            self.assertIn(public, json.dumps(shared))
        self.assertEqual(moment.presentation_intent.visibility.value, "session_shared")
        self.assertEqual(tuple(c.value for c in moment.presentation_intent.delivery_channels),
                         ("broadcast", "owner", "shared"))
        self.assertEqual(self.active.broadcast.native_delivery(include_owner_only=False)["current_moment_id"],
                         moment.moment_id)
        # Viewer authority remains readonly and never acquires owner speech/settings.
        self.assertNotIn("session_speech", json.loads(guest))
        self.assertNotIn("session_media", json.loads(guest))
        self.assertTrue(any(e["event_type"] == "dj_moment_published" for e in events))
        self.assertIsNone(await self.publish())
        self.assertEqual(self.active.presence_ledger.total_published, before + 1)

    async def test_existing_music_priority_prevents_a_ready_bulletin_from_publishing(self):
        marker = object()
        async def music(**kwargs):
            return marker
        with patch.object(self.manager, "_async_maybe_publish_music_moment", music):
            self.assertIs(await self.publish(), marker)
        self.assertEqual(self.active.presence_ledger.total_published, 0)
        self.assertIs(self.builder._candidate, self.candidate)

    async def test_shared_reconnect_keeps_original_deadline_and_expiry_withdraws_content(self):
        moment = await self.publish()
        broadcast = self.active.broadcast
        token = broadcast.broadcast_token
        _, first = broadcast.subscribe_with_broadcast_token(token, lambda event: None)
        _, second = broadcast.subscribe_with_broadcast_token(token, lambda event: None)
        self.assertEqual(first["native_delivery"], second["native_delivery"])
        self.assertIn(self.text, json.dumps(second))
        with patch("time.time", return_value=moment.bulletin.candidate.expires_at + 1):
            _, expired = broadcast.subscribe_with_broadcast_token(token, lambda event: None)
            self.assertNotIn(self.text, json.dumps(expired))
            self.assertNotIn(moment.moment_id, json.dumps(expired["session_flow"]))
            self.assertIsNone(expired["native_delivery"]["current_moment_id"])

    async def test_pending_shared_frame_rechecks_original_owner_before_delivery(self):
        broadcast = self.active.broadcast
        events = []
        subscription, _ = broadcast.subscribe_with_broadcast_token(broadcast.broadcast_token, events.append)
        broadcast._pending_subscriptions[subscription] = []
        await self.publish()
        self.assertEqual(events, [])
        self.authorized = False
        broadcast.activate_subscription(subscription)
        self.assertNotIn(self.text, json.dumps(events))
        self.assertNotIn(self.items[0].source_url, json.dumps(events))

    async def test_tail_pause_pending_and_used_presence_ledger_suppress_without_consuming_candidate(self):
        for field in ("pending", "blocked"):
            opportunity = self.manager._intra_track_opportunities["synthetic-owner"]
            setattr(opportunity, field, True)
            self.assertIsNone(await self.publish())
            setattr(opportunity, field, False)
        await self.observe(position=295000)
        self.assertIsNone(await self.publish())
        self.assertIs(self.builder._candidate, self.candidate)
        await self.observe(position=296000, state="paused")
        self.assertIsNone(await self.publish())

    async def test_owner_loss_and_original_source_revision_ABA_reject_ready_candidate(self):
        self.authorized = False
        self.assertIsNone(await self.publish())
        self.authorized = True
        self.revision[0] += 2
        self.assertIsNone(await self.publish())
        self.assertEqual(self.active.presence_ledger.total_published, 0)

    async def test_settings_axis_ABA_rejects_without_false_runtime_object_equality_across_progress(self):
        # Normal progress can replace the Runtime value while keeping stable authority.
        updated = replace(self.active)
        self.manager._active_by_profile["synthetic-owner"] = updated
        self.work.guard()
        for field in ("mood_revision", "persona_revision", "presence_revision", "settings_revision"):
            changed = replace(updated, **{field: getattr(updated, field) + 2})
            self.manager._active_by_profile["synthetic-owner"] = changed
            with self.assertRaises(PermissionError):
                self.work.guard()
        self.manager._active_by_profile["synthetic-owner"] = updated
        self.assertIsNotNone(await self.publish())

    async def test_music_only_denies_publication_and_new_capture(self):
        updated = replace(self.active, selected_presence="music_only", presence_revision=1)
        self.manager._active_by_profile["synthetic-owner"] = updated
        self.active.broadcast.state = replace(self.active.broadcast.state,
            selected_presence="music_only", presence_revision=1)
        self.assertIsNone(capture_work(self.manager, "synthetic-owner"))
        self.assertIsNone(await self.publish())
        self.assertEqual(self.active.presence_ledger.total_published, 0)

    async def test_model_text_is_not_promoted_to_history_archive(self):
        moment = await self.publish()
        self.assertIsNotNone(moment)
        rows = await self.persistence.async_in_transaction(lambda tx: tx.fetchall(
            "SELECT body FROM djconnect_session_entries WHERE reference_id = ?", (moment.moment_id,)))
        self.assertEqual(len(rows), 1)
        self.assertNotIn(self.text, str(rows))
        self.assertIn("source_retention_not_qualified", str(rows))

    async def test_native_admission_expiry_speech_toggle_and_forged_proof_are_closed(self):
        moment = await self.publish()
        self.assertTrue(admitted(moment))
        from custom_components.djconnect.session_speech import moment_projection
        off = moment_projection(self.active.broadcast, moment, autoplay=False)
        on = moment_projection(self.active.broadcast, moment, autoplay=True)
        from custom_components.djconnect.bulletin_source_policy import source_notice
        notice = source_notice(self.candidate.items, self.candidate.session.locale)
        self.assertTrue(moment.content.endswith('\n\n' + notice))
        self.assertEqual(moment.as_dict()['content'], self.candidate.text)
        self.assertIn(notice, json.dumps(self.active.broadcast.as_dict(), ensure_ascii=False))
        self.assertIn(notice, json.dumps(on, ensure_ascii=False))
        self.assertTrue(off["manual_allowed"])
        self.assertFalse(off["autoplay_eligible"])
        self.assertTrue(on["autoplay_eligible"])
        self.assertEqual(off["expires_at"], on["expires_at"])
        self.assertFalse(admitted(replace(moment, content=moment.content + " forged")))
        self.assertFalse(admitted(moment, monotonic=self.candidate.monotonic_deadline))
        with patch("time.time", return_value=self.candidate.expires_at + 1):
            snapshot = json.dumps(self.active.broadcast.as_dict())
            self.assertNotIn(self.text, snapshot)
            self.assertFalse(moment_projection(self.active.broadcast, moment)["manual_allowed"])

    async def test_closed_service_and_ended_session_cannot_publish(self):
        self.service.closed = True
        self.assertIsNone(await self.publish())
        self.service.closed = False
        await self.manager.async_end(owner_profile_id="synthetic-owner", session_id=self.sid)
        self.assertIsNone(await self.publish())

    async def assert_withdrawn(self, moment):
        from custom_components.djconnect.session_speech import moment_projection
        self.assertFalse(admitted(moment))
        self.assertFalse(moment_projection(self.active.broadcast, moment)["manual_allowed"])
        self.assertNotIn(self.text, json.dumps(self.active.broadcast.as_dict()))
        self.assertNotIn(self.text, json.dumps(self.active.broadcast.as_dict(include_owner_only=False)))

    async def test_published_original_owner_revoke_withdraws_delivery_permanently(self):
        moment = await self.publish()
        self.authorized = False
        await self.assert_withdrawn(moment)
        self.authorized = True
        await self.assert_withdrawn(moment)

    async def test_published_original_authority_ABA_withdraws_delivery(self):
        moment = await self.publish()
        self.revision[0] += 2
        await self.assert_withdrawn(moment)

    async def test_published_service_close_withdraws_delivery(self):
        moment = await self.publish()
        self.service.closed = True
        await self.assert_withdrawn(moment)

    async def test_published_settings_revision_withdraws_delivery(self):
        moment = await self.publish()
        self.manager._active_by_profile["synthetic-owner"] = replace(self.active,
            settings_revision=self.active.settings_revision + 1)
        await self.assert_withdrawn(moment)
