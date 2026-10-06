"""Qualified facts, cadence, lifecycle and narrow receiver-end regressions."""

from __future__ import annotations
import asyncio
import sys
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
import unittest
from tests.test_session_runtime import _load_runtime_module


class SessionFactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()
        from custom_components.djconnect import session_facts

        cls.facts = session_facts

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("custom_components.djconnect.session_runtime", None)
        if cls.previous_const is not None:
            sys.modules["custom_components.djconnect.const"] = cls.previous_const
        else:
            sys.modules.pop("custom_components.djconnect.const", None)

    def catalog(self):
        return {
            "uri": "spotify:track:" + "A" * 22,
            "title": "Test recording",
            "artist": "Test artist",
            "album_name": "Test edition",
            "album_uri": "spotify:album:" + "B" * 22,
            "release_date": "2001-03-04",
            "release_date_precision": "day",
            "isrc": "USABC0100001",
        }

    def test_date_precision_binding_and_no_original_release_claim(self):
        for precision, value in [("year", "2001"), ("month", "2001-03"), ("day", "2001-03-04")]:
            catalog = {**self.catalog(), "release_date": value, "release_date_precision": precision}
            fact = self.facts.catalog_facts(catalog)[0]
            self.assertIn(value, dict(fact.contents)["nl"])
            self.assertIn("deze uitgave", dict(fact.contents)["nl"])
            self.assertEqual(set(dict(fact.contents)), set(self.facts.LANGUAGES))
            self.assertFalse(fact.eligible("spotify:track:wrong", time.monotonic()))
            self.assertFalse(fact.eligible(fact.media_identity, fact.observed_at + 1801))
        for value in ["2001-02-30", "2001-13-04", "anything"]:
            self.assertEqual(
                self.facts.catalog_facts({**self.catalog(), "release_date": value}), []
            )

    def test_unique_isrc_exact_title_and_artist_required(self):
        class Resolver(self.facts.SessionFactsResolver):
            async def _get(inner, path, params=None, **kwargs):
                return {"recordings": inner.recordings}

        resolver = Resolver(object())
        recording = {
            "id": "00000000-0000-0000-0000-000000000001",
            "title": "Different mix",
            "artist-credit": [{"artist": {"name": "Test artist"}}],
        }
        for recordings in [
            [],
            [recording, recording],
            [recording],
            [
                {
                    **recording,
                    "title": "Test recording",
                    "artist-credit": [{"artist": {"name": "Other artist"}}],
                }
            ],
        ]:
            resolver.recordings = recordings
            facts = asyncio.run(resolver.resolve(self.catalog()))
            self.assertEqual([f.key for f in facts], ["album_release"])

    def test_positive_resolver_chain_roles_composers_and_reciprocal_artist_identity(self):
        catalog = self.catalog()
        recording_id = "00000000-0000-0000-0000-000000000001"
        artist_id = "00000000-0000-0000-0000-000000000002"
        work_id = "00000000-0000-0000-0000-000000000003"
        credited = {"artist": {"id": artist_id, "name": "Test artist"}}
        recording = {"id": recording_id, "title": "Test recording", "artist-credit": [credited]}
        detailed = {
            **recording,
            "relations": [
                {"type": "producer", "target-type": "artist", "artist": {"name": "Test producer"}},
                {
                    "type": "performance",
                    "target-type": "work",
                    "work": {
                        "id": work_id,
                        "relations": [
                            {
                                "type": "composer",
                                "target-type": "artist",
                                "artist": {"name": "Test composer"},
                            }
                        ],
                    },
                },
            ],
        }
        person = {
            "id": artist_id,
            "name": "Test artist",
            "type": "Person",
            "life-span": {"begin": "1960-01-02"},
            "relations": [
                {"type": "wikidata", "url": {"resource": "https://www.wikidata.org/wiki/Q1"}}
            ],
        }

        class Resolver(self.facts.SessionFactsResolver):
            reciprocal = artist_id

            async def _get(inner, path, params=None, **kwargs):
                if path.startswith("isrc/"):
                    return {"recordings": [recording]}
                if path.startswith("recording/"):
                    return detailed
                if path.startswith("artist/"):
                    return person
                return {
                    "entities": {
                        "Q1": {
                            "descriptions": {
                                lang: {"value": "Description " + lang}
                                for lang in self.facts.LANGUAGES
                            },
                            "claims": {
                                "P434": [
                                    {
                                        "rank": "normal",
                                        "mainsnak": {"datavalue": {"value": inner.reciprocal}},
                                    }
                                ]
                            },
                        }
                    }
                }

        resolver = Resolver(object())
        facts = asyncio.run(resolver.resolve(catalog))
        self.assertEqual(
            {f.key for f in facts},
            {
                "album_release",
                "recording_credits",
                "work_composers",
                "artist_begin",
                "artist_description",
            },
        )
        self.assertIn(
            "Test producer",
            dict(next(f for f in facts if f.key == "recording_credits").contents)["nl"],
        )
        self.assertIn(
            "Test composer",
            dict(next(f for f in facts if f.key == "work_composers").contents)["nl"],
        )
        resolver.reciprocal = "00000000-0000-0000-0000-000000000004"
        self.assertNotIn(
            "artist_description", {f.key for f in asyncio.run(resolver.resolve(catalog))}
        )

    def test_four_independent_angles_publish_through_flow_and_broadcast_once(self):
        async def scenario():
            now = [100.0]
            manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: now[0])
            session = await manager.async_start(
                owner_profile_id="test-owner", locale="nl", music_backend="spotify_direct"
            )
            catalog = self.catalog()
            uri = catalog["uri"]
            artist = {
                "id": "00000000-0000-0000-0000-000000000002",
                "name": "Test artist",
                "type": "Person",
                "life-span": {"begin": "1960-01-02"},
            }
            recording = {
                "id": "00000000-0000-0000-0000-000000000001",
                "relations": [
                    {
                        "type": "producer",
                        "target-type": "artist",
                        "artist": {"name": "Test producer"},
                    }
                ],
            }
            facts = tuple(
                self.facts.catalog_facts(catalog)
                + self.facts.recording_facts(catalog, recording)
                + self.facts.artist_facts(catalog, artist)
                + [
                    self.facts.description_fact(
                        catalog,
                        {
                            "descriptions": {
                                lang: {"value": "Test description " + lang}
                                for lang in self.facts.LANGUAGES
                            }
                        },
                        "Q1",
                    )
                ]
            )

            async def observe(position):
                self._fixed_timestamp = (
                    self._capture_start + timedelta(milliseconds=position)
                ).isoformat()
                now[0] += 15
                await manager.async_update_playback_projection(
                    owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id,
                    state="playing",
                    media_identity=uri,
                    title=catalog["title"],
                    artist=catalog["artist"],
                    album=catalog["album_name"],
                    duration_ms=300000,
                    position_ms=position,
                )

            await observe(0)

            async def insight():
                return {"_qualified_facts": facts}

            first = await manager.async_process_track_started(
                owner_profile_id=session.owner_profile_id,
                session_id=session.session_id,
                media_identity=uri,
                insight_provider=insight,
                require_current_playback=True,
                allow_initial_facts=True,
            )
            moments = [first]
            before = session.broadcast.as_dict()
            events = []
            session.broadcast.subscribe(events.append)
            for position in range(15000, 151000, 15000):
                await observe(position)
                moment = await manager.async_maybe_publish_intra_track_moment(
                    owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id,
                    media_identity=uri,
                )
                if moment:
                    moments.append(moment)
            self.assertEqual(len(moments), 4)
            self.assertEqual({m.moment_type.value for m in moments}, {"album", "artist", "track"})
            self.assertEqual(len({m.content for m in moments}), 4)
            self.assertEqual(
                [m.moment_id for m in moments],
                [m.moment_id for m in session.broadcast.state.dj_moments],
            )
            self.assertEqual(
                [m.moment_id for m in moments],
                [m.moment_id for m in session.planner.output.session_flow.items if m.moment_id],
            )
            self.assertTrue(
                all(
                    m.as_dict()["source_attribution"]["url"].startswith("https://") for m in moments
                )
            )
            # No raw catalog ID, provider response or internal fact field enters Moment serialization.
            self.assertNotIn("_qualified_facts", str(session.broadcast.as_dict()))
            self.runtime_capture = {
                "simulator": True,
                "source": "Mocked qualified sources → Planner → Knowledge → Moment → Flow → Broadcast",
                "before": before,
                "after": session.broadcast.as_dict(),
                "events": events,
                "moment_receipts": [
                    {
                        "moment_id": m.moment_id,
                        "type": m.moment_type.value,
                        "created_at": m.created_at,
                        "summary": m.summary,
                        "content": m.content,
                    }
                    for m in moments
                ],
            }
            await observe(165000)
            self.assertIsNone(
                await manager.async_maybe_publish_intra_track_moment(
                    owner_profile_id=session.owner_profile_id,
                    session_id=session.session_id,
                    media_identity=uri,
                )
            )

        self._capture_start = datetime.now(UTC)
        self._fixed_timestamp = self._capture_start.isoformat()
        with patch.object(self.runtime, "_timestamp", lambda: self._fixed_timestamp):
            asyncio.run(scenario())

    def test_late_source_after_same_uri_output_change_and_unreadable_remaining_is_suppressed(self):
        async def scenario(change_output):
            manager = self.runtime.SessionRuntimeManager()
            session = await manager.async_start(owner_profile_id="owner", locale="nl")
            catalog = self.catalog()
            uri = catalog["uri"]

            async def observe(position, target):
                await manager.async_update_playback_projection(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    state="playing",
                    media_identity=uri,
                    title=catalog["title"],
                    artist=catalog["artist"],
                    target_name=target,
                    duration_ms=120000,
                    position_ms=position,
                )

            await observe(0, "A")
            entered = asyncio.Event()
            finish = asyncio.Event()

            async def source():
                entered.set()
                await finish.wait()
                return {"_qualified_facts": tuple(self.facts.catalog_facts(catalog))}

            pending = asyncio.create_task(
                manager.async_process_track_started(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    media_identity=uri,
                    insight_provider=source,
                    require_current_playback=True,
                    allow_initial_facts=True,
                )
            )
            await entered.wait()
            await observe(100000 if not change_output else 15000, "B" if change_output else "A")
            finish.set()
            self.assertIsNone(await pending)
            self.assertEqual(session.broadcast.state.dj_moments, ())
            self.assertEqual(session.moment_engine.moments, ())

        asyncio.run(scenario(True))
        asyncio.run(scenario(False))

    def test_next_item_update_never_rewinds_current_progress_or_crosses_output(self):
        async def scenario():
            manager = self.runtime.SessionRuntimeManager()
            session = await manager.async_start(owner_profile_id="owner")
            uri = self.catalog()["uri"]
            await manager.async_update_playback_projection(
                owner_profile_id="owner",
                session_id=session.session_id,
                state="playing",
                media_identity=uri,
                title="Current",
                target_name="Output",
                duration_ms=300000,
                position_ms=65000,
            )
            next_item = {
                "title": "Next",
                "artist": "Artist",
                "expires_at": "2099-01-01T00:00:00+00:00",
            }
            self.assertFalse(
                await manager.async_update_next_item_projection(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    media_identity="other",
                    target_name="Output",
                    up_next=next_item,
                )
            )
            self.assertFalse(
                await manager.async_update_next_item_projection(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    media_identity=uri,
                    target_name="Other output",
                    up_next=next_item,
                )
            )
            self.assertTrue(
                await manager.async_update_next_item_projection(
                    owner_profile_id="owner",
                    session_id=session.session_id,
                    media_identity=uri,
                    target_name="Output",
                    up_next=next_item,
                )
            )
            self.assertEqual(session.broadcast.state.playback.position_ms, 65000)
            self.assertEqual(dict(session.broadcast.state.playback.up_next)["title"], "Next")

        asyncio.run(scenario())

    def test_end_grant_is_session_scoped_expiring_revocable_and_not_broadcast_token(self):
        async def scenario():
            now = [100.0]
            manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: now[0])
            session = await manager.async_start(owner_profile_id="owner")
            self.assertIsNone(
                await manager.async_end_with_receiver_grant(
                    session_id=session.session_id, grant=session.broadcast.broadcast_token
                )
            )
            grant = await manager.async_issue_receiver_end_grant(
                owner_profile_id="owner", session_id=session.session_id
            )
            self.assertIsNone(
                await manager.async_end_with_receiver_grant(
                    session_id="another-session", grant=grant
                )
            )
            now[0] += 3601
            self.assertIsNone(
                await manager.async_end_with_receiver_grant(
                    session_id=session.session_id, grant=grant
                )
            )
            grant = await manager.async_issue_receiver_end_grant(
                owner_profile_id="owner", session_id=session.session_id
            )
            await manager.async_revoke_receiver_end_grants(
                owner_profile_id="owner", session_id=session.session_id
            )
            self.assertIsNone(
                await manager.async_end_with_receiver_grant(
                    session_id=session.session_id, grant=grant
                )
            )
            grant = await manager.async_issue_receiver_end_grant(
                owner_profile_id="owner", session_id=session.session_id
            )
            ended = await manager.async_end_with_receiver_grant(
                session_id=session.session_id, grant=grant
            )
            self.assertEqual(ended.runtime_state.value, "ended")
            self.assertIsNone(
                await manager.async_end_with_receiver_grant(
                    session_id=session.session_id, grant=grant
                )
            )
            self.assertIsNone(await manager.async_get_active("owner"))

        asyncio.run(scenario())
