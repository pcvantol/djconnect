"""Owner Session settings through the HTTP views and the real Runtime manager."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from tests.test_http_voice_helpers import install_http_stubs


class SessionSettingTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        install_http_stubs()
        from custom_components.djconnect import api_handlers, http, profile_context, session_runtime

        self.views = {
            "mood": http.DJConnectSessionMoodView,
            "presence": http.DJConnectSessionPresenceView,
            "persona": http.DJConnectSessionPersonaView,
        }
        self.manager = session_runtime.SessionRuntimeManager()
        self.owner = await self.manager.async_start(
            owner_profile_id="owner", selected_mood="groove",
        )
        self.other = await self.manager.async_start(
            owner_profile_id="other", selected_mood="chill",
        )
        self.device = "djconnect-ios-ABCDEFGHIJKL"
        self.headers = {
            "Authorization": "Bearer synthetic-pair-token",
            "X-DJConnect-Device-ID": self.device,
        }
        entry = SimpleNamespace(
            entry_id="entry", disabled_by=None, state=SimpleNamespace(value="loaded"),
            data={"device_id": self.device, "client_type": "ios",
                  "device_token": "synthetic-pair-token"}, options={},
        )
        self.runtime = SimpleNamespace(
            entry=entry, pairing_device_id=self.device, device_status={},
            device_token="synthetic-pair-token",
            authorize_device_request=lambda headers, device, client: (
                headers == self.headers and device == self.device and client == "ios"
            ),
        )
        self.hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_get_entry=lambda key: entry if key == "entry" else None),
            data={"djconnect": {"entry": self.runtime, "session_runtime_manager": self.manager}},
        )
        self.profile = SimpleNamespace(profile_id="owner", state=SimpleNamespace(value="active"))
        storage = SimpleNamespace(resolver=lambda: SimpleNamespace(
            resolve_bound_device=lambda device: self.profile,
        ))
        resolver = AsyncMock(side_effect=lambda *_args, **_kwargs: self.profile)
        self.enterContext(patch.object(api_handlers, "async_resolve_device_bound_request_context", resolver))
        self.enterContext(patch.object(profile_context, "profile_storage", return_value=storage))

    async def post(self, setting, choice, revision=0, *, session=None, headers=None, **extra):
        data = {
            "contract_version": 1, "device_id": self.device, "client_type": "ios",
            "session_id": (session or self.owner).session_id,
            f"selected_{setting}": choice, f"expected_{setting}_revision": revision,
            **extra,
        }
        request = SimpleNamespace(
            app={"hass": self.hass}, headers=self.headers if headers is None else headers,
            query_string="", json=AsyncMock(return_value=data),
        )
        reply = await self.views[setting](self.hass).post(request)
        return json.loads(reply.text), reply.status

    async def test_current_owner_updates_each_axis_once_with_independent_revisions(self):
        for setting, choice in (("mood", "energy"), ("presence", "music_only"), ("persona", "club_dj")):
            with self.subTest(setting=setting):
                scope = {"write_scope": "session_only"} if setting == "mood" else {}
                updated, status = await self.post(setting, choice, **scope)
                self.assertEqual(status, 200)
                self.assertTrue(updated["changed"])
                self.assertEqual(updated[f"{setting}_revision"], 1)
                self.assertEqual(updated[f"selected_{setting}"], choice)
                replay, status = await self.post(setting, choice, revision=1, **scope)
                self.assertEqual(status, 200)
                self.assertFalse(replay["changed"])
                conflict, status = await self.post(setting, choice, **scope)
                self.assertEqual(status, 409)
                self.assertEqual(conflict["error"], f"{setting}_revision_conflict")
                self.assertEqual(conflict["current"][f"{setting}_revision"], 1)
        owner = self.manager.current_active("owner")
        self.assertEqual((owner.selected_mood, owner.selected_presence, owner.dj_persona.value),
                         ("energy", "music_only", "club_dj"))
        self.assertIs(self.manager.current_active("other"), self.other)

    async def test_invalid_revision_wrong_bearer_and_other_profile_cannot_write(self):
        for kwargs, expected in (
            ({"revision": True}, (400, "invalid_mood_revision")),
            ({"headers": {"Authorization": "Bearer obsolete"}}, (401, "unauthorized")),
            ({"session": self.other}, (404, "active_session_not_found")),
        ):
            with self.subTest(kwargs=kwargs):
                result, status = await self.post("mood", "energy", **kwargs)
                self.assertEqual((status, result["error"]), expected)
        self.assertIs(self.manager.current_active("owner"), self.owner)
        self.assertIs(self.manager.current_active("other"), self.other)

    async def test_profile_rebind_withdraws_in_flight_reply_after_successful_commit(self):
        from custom_components.djconnect.transport_delivery import capture_delivery_admissions

        with capture_delivery_admissions() as admissions:
            result, status = await self.post("mood", "energy", write_scope="session_only")
        self.assertEqual(status, 200)
        self.assertTrue(result["changed"])
        self.assertEqual(result["write_scope"], "session_only")
        self.assertTrue(admissions)
        for admission in admissions:
            admission()

        self.profile = SimpleNamespace(profile_id="other", state=SimpleNamespace(value="active"))
        with self.assertRaisesRegex(PermissionError, "setting_result_withdrawn"):
            for admission in admissions:
                admission()
        self.assertEqual(self.manager.current_active("owner").selected_mood, "energy")
        self.assertIs(self.manager.current_active("other"), self.other)
