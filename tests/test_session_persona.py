"""Live Persona ordering, revocation and immutable prior-publication boundaries."""

import asyncio
import sys
import unittest

from tests.test_session_runtime import _load_runtime_module


class SessionPersonaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime, cls.previous_const = _load_runtime_module()

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("custom_components.djconnect.session_runtime", None)
        if cls.previous_const is None:
            sys.modules.pop("custom_components.djconnect.const", None)
        else:
            sys.modules["custom_components.djconnect.const"] = cls.previous_const

    def test_initial_identity_two_clients_cas_noop_and_independent_mood(self):
        async def scenario():
            r = self.runtime
            manager = r.SessionRuntimeManager()
            active = await manager.async_start(
                owner_profile_id="owner", selected_mood="groove", dj_persona=r.DJPersona.RADIO_DJ
            )
            self.assertEqual(active.broadcast.as_dict()["session"]["dj_persona"], "radio_dj")
            events = []
            await manager.async_subscribe(
                owner_profile_id="owner", session_id=active.session_id, callback=events.append
            )
            same = await manager.async_update_persona(
                owner_profile_id="owner",
                session_id=active.session_id,
                dj_persona=r.DJPersona.RADIO_DJ,
                expected_revision=0,
            )
            self.assertEqual(same.persona_revision, 0)
            self.assertEqual(events, [])
            answers = await asyncio.gather(
                *(
                    manager.async_update_persona(
                        owner_profile_id="owner",
                        session_id=active.session_id,
                        dj_persona=p,
                        expected_revision=0,
                    )
                    for p in (r.DJPersona.CLUB_DJ, r.DJPersona.FESTIVAL_DJ)
                ),
                return_exceptions=True,
            )
            self.assertEqual(sum(isinstance(x, r.PersonaRevisionConflictError) for x in answers), 1)
            now = manager.current_active("owner")
            self.assertEqual(now.persona_revision, 1)
            self.assertEqual(
                (
                    now.session_id,
                    now.selected_mood,
                    now.mood_revision,
                    now.selected_presence,
                    now.presence_revision,
                ),
                (active.session_id, "groove", 0, active.selected_presence, 0),
            )
            self.assertEqual(now.presence_ledger.total_published, 0)
            self.assertEqual(now.broadcast.state.dj_moments, ())
            self.assertEqual(events[-1]["event_type"], "persona_changed")
            self.assertEqual(events[-1]["payload"]["session"]["persona_revision"], 1)
            await manager.async_update_mood(
                owner_profile_id="owner",
                session_id=active.session_id,
                selected_mood="energy",
                expected_revision=0,
            )
            self.assertEqual(manager.current_active("owner").dj_persona, now.dj_persona)
            with self.assertRaises(r.PersonaRevisionConflictError):
                await manager.async_update_persona(
                    owner_profile_id="owner",
                    session_id=active.session_id,
                    dj_persona=now.dj_persona,
                    expected_revision=0,
                )

        asyncio.run(scenario())

    def test_revocation_while_waiting_for_runtime_lock_is_not_a_commit(self):
        async def scenario():
            r = self.runtime
            manager = r.SessionRuntimeManager()
            active = await manager.async_start(owner_profile_id="owner", selected_mood="groove")
            valid = [True]
            await manager._lock.acquire()
            task = asyncio.create_task(
                manager.async_update_persona(
                    owner_profile_id="owner",
                    session_id=active.session_id,
                    dj_persona=r.DJPersona.CLUB_DJ,
                    expected_revision=0,
                    authorize=lambda: valid[0],
                )
            )
            await asyncio.sleep(0)
            valid[0] = False
            manager._lock.release()
            with self.assertRaises(PermissionError):
                await task
            now = manager.current_active("owner")
            self.assertEqual((now.dj_persona, now.persona_revision), (r.DJPersona.HOME_DJ, 0))

        asyncio.run(scenario())
