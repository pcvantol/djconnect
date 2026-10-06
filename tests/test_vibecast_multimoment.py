"""Same-track Moment behavior through the existing Runtime and Broadcast."""

from __future__ import annotations

import asyncio
import sys
import unittest
from unittest.mock import patch

from tests.test_session_runtime import _load_runtime_module


class VibeCastMultiMomentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls) -> None:
        package = "custom_components.djconnect"
        sys.modules.pop(f"{package}.session_runtime", None)
        if cls.previous_const is None:
            sys.modules.pop(f"{package}.const", None)
        else:
            sys.modules[f"{package}.const"] = cls.previous_const

    async def _ready(
        self, *, genre: str = "soul", duration_ms: int = 240_000,
        content: str = "The bass and percussion leave space for the melody.",
        locale: str = "nl",
    ):
        now = [100.0]
        manager = self.runtime.SessionRuntimeManager(monotonic_source=lambda: now[0])
        session = await manager.async_start(
            owner_profile_id="profile-multimoment", selected_mood="groove",
            music_backend="spotify_direct", locale=locale,
        )
        first_id = "spotify:track:AAAAAAAA"
        media_id = "spotify:track:BBBBBBBB"
        await manager.async_update_playback_projection(
            owner_profile_id=session.owner_profile_id, session_id=session.session_id,
            state="playing", media_identity=first_id, title="Previous",
            artist="Artist", duration_ms=duration_ms, position_ms=0,
        )

        async def empty_insight():
            return {}

        await manager.async_process_track_started(
            owner_profile_id=session.owner_profile_id, session_id=session.session_id,
            insight_provider=empty_insight, media_identity=first_id,
            require_current_playback=True,
        )
        await manager.async_update_playback_projection(
            owner_profile_id=session.owner_profile_id, session_id=session.session_id,
            state="playing", media_identity=media_id, title="Current",
            artist="Artist", album="Album", duration_ms=duration_ms, position_ms=0,
            artwork_url="/api/djconnect/v1/image_proxy/test-cover",
        )

        async def current_insight():
            return {
                "track": {
                    "title": "Current", "artist": "Artist", "album": "Album",
                    "backend": "spotify_direct", "genres": [genre] if genre else [],
                },
                "analysis": {
                    "summary": "A measured bass line anchors the song.",
                    "full_text": content, "genre": genre,
                },
            }

        first = await manager.async_process_track_started(
            owner_profile_id=session.owner_profile_id, session_id=session.session_id,
            insight_provider=current_insight, media_identity=media_id,
            require_current_playback=True,
        )
        assert first is not None
        return manager, session, first, media_id, now

    async def _observe(
        self, manager, session, media_id, now, *, seconds: float,
        position_ms: int, duration_ms: int = 240_000, state: str = "playing",
        target_name: str = "",
    ) -> None:
        now[0] += seconds
        await manager.async_update_playback_projection(
            owner_profile_id=session.owner_profile_id, session_id=session.session_id,
            state=state, media_identity=media_id, title="Current",
            artist="Artist", album="Album", target_name=target_name,
            duration_ms=duration_ms, position_ms=position_ms,
            artwork_url="/api/djconnect/v1/image_proxy/test-cover",
        )

    async def _later(self, manager, session, media_id):
        return await manager.async_maybe_publish_intra_track_moment(
            owner_profile_id=session.owner_profile_id, session_id=session.session_id,
            media_identity=media_id,
        )

    def test_same_observed_track_emits_two_different_meaningful_types(self) -> None:
        async def scenario():
            manager, session, first, media_id, now = await self._ready()
            await self._observe(manager, session, media_id, now, seconds=15, position_ms=15_000)
            self.assertIsNone(await self._later(manager, session, media_id))
            await self._observe(manager, session, media_id, now, seconds=15, position_ms=30_000)
            second = await self._later(manager, session, media_id)
            duplicate = await self._later(manager, session, media_id)
            return session, first, second, duplicate

        session, first, second, duplicate = asyncio.run(scenario())
        self.assertIsNotNone(second)
        assert second is not None
        self.assertIsNone(duplicate)
        self.assertEqual({first.moment_type, second.moment_type}, {
            self.runtime.DJMomentType.TRACK, self.runtime.DJMomentType.GENRE,
        })
        self.assertNotEqual(first.moment_id, second.moment_id)
        self.assertNotEqual(first.content, second.content)
        self.assertEqual(session.broadcast.state.dj_moments[-2:], (first, second))
        self.assertEqual(
            [item.moment_id for item in session.planner.output.session_flow.items[-2:]],
            [first.moment_id, second.moment_id],
        )
        snapshot = session.broadcast.as_dict()
        self.assertEqual(snapshot["session"]["locale"], "nl")
        self.assertEqual(snapshot["dj_moments"][-1]["playback_item_id"], snapshot["playback"]["item_id"])
        self.assertEqual(snapshot["presentations"][-1]["source_moment_id"], second.moment_id)

    def test_missing_second_angle_and_short_track_do_not_fabricate_moments(self) -> None:
        async def scenario(genre, duration):
            manager, session, first, media_id, now = await self._ready(genre=genre, duration_ms=duration)
            await self._observe(manager, session, media_id, now, seconds=70, position_ms=70_000, duration_ms=duration)
            result = await self._later(manager, session, media_id)
            return session, first, result

        for genre, duration in (("", 240_000), ("soul", 120_000)):
            with self.subTest(genre=genre, duration=duration):
                session, first, result = asyncio.run(scenario(genre, duration))
                self.assertIsNone(result)
                self.assertEqual(session.broadcast.state.dj_moments[-1], first)

    def test_pause_resume_requires_a_fresh_interval_and_seek_blocks_old_slot(self) -> None:
        async def pause_resume():
            manager, session, _, media_id, now = await self._ready()
            await self._observe(manager, session, media_id, now, seconds=70, position_ms=70_000, state="paused")
            paused = await self._later(manager, session, media_id)
            await self._observe(manager, session, media_id, now, seconds=20, position_ms=70_000)
            immediate = await self._later(manager, session, media_id)
            await self._observe(manager, session, media_id, now, seconds=15, position_ms=85_000)
            resumed = await self._later(manager, session, media_id)
            return paused, immediate, resumed

        paused, immediate, resumed = asyncio.run(pause_resume())
        self.assertIsNone(paused)
        self.assertIsNone(immediate)
        self.assertIsNotNone(resumed)

        async def seek():
            manager, session, _, media_id, now = await self._ready()
            await self._observe(manager, session, media_id, now, seconds=80, position_ms=80_000)
            await self._observe(manager, session, media_id, now, seconds=10, position_ms=10_000)
            await self._observe(manager, session, media_id, now, seconds=120, position_ms=130_000)
            return await self._later(manager, session, media_id)

        self.assertIsNone(asyncio.run(seek()))

    def test_stale_observation_and_changed_source_do_not_publish(self) -> None:
        async def scenario():
            manager, session, _, media_id, now = await self._ready()
            now[0] += 120
            stale = await self._later(manager, session, media_id)
            await self._observe(manager, session, media_id, now, seconds=0, position_ms=120_000, target_name="Other output")
            changed = await self._later(manager, session, media_id)
            return stale, changed

        stale, changed = asyncio.run(scenario())
        self.assertIsNone(stale)
        self.assertIsNone(changed)

    def test_late_knowledge_for_previous_track_cannot_enter_flow(self) -> None:
        async def scenario():
            manager, session, first, media_id, now = await self._ready()
            await self._observe(manager, session, media_id, now, seconds=120, position_ms=120_000)
            started, finish = asyncio.Event(), asyncio.Event()
            original = self.runtime.DJKnowledgeEngine.async_assemble_track_context

            async def slow(engine, *args, **kwargs):
                started.set()
                await finish.wait()
                return await original(engine, *args, **kwargs)

            with patch.object(self.runtime.DJKnowledgeEngine, "async_assemble_track_context", slow):
                pending = asyncio.create_task(self._later(manager, session, media_id))
                await started.wait()
                now[0] += 1
                await manager.async_update_playback_projection(
                    owner_profile_id=session.owner_profile_id, session_id=session.session_id,
                    state="playing", media_identity="spotify:track:CCCCCCCC",
                    title="Next", artist="Artist", duration_ms=240_000,
                    position_ms=0,
                )
                finish.set()
                result = await pending
            return session, first, result

        session, first, result = asyncio.run(scenario())
        self.assertIsNone(result)
        self.assertEqual(session.broadcast.state.dj_moments[-1], first)

    def test_runtime_end_prevents_later_card(self) -> None:
        async def scenario():
            manager, session, _, media_id, now = await self._ready()
            await self._observe(manager, session, media_id, now, seconds=120, position_ms=120_000)
            await manager.async_end(owner_profile_id=session.owner_profile_id, session_id=session.session_id)
            return await self._later(manager, session, media_id)

        self.assertIsNone(asyncio.run(scenario()))


if __name__ == "__main__":
    unittest.main()
