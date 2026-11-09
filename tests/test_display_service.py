"""B adapter unit chain with normal request helpers; not live HA proof."""
import importlib
from io import BytesIO
import secrets
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from tests import test_display_authority as authority_tests


class DisplayServiceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        authority_tests.DisplayOwnerPurposeTests.setUpClass()
        cls.module = importlib.import_module("custom_components.djconnect.display_service")

    @classmethod
    def tearDownClass(cls):
        authority_tests.DisplayOwnerPurposeTests.tearDownClass()

    async def asyncSetUp(self):
        self.fixture = authority_tests.DisplayOwnerPurposeTests()
        await self.fixture.asyncSetUp()
        self.manager = self.fixture.manager
        self.service = self.module.DisplayAdmissionService(self.fixture.hass, self.manager)
        self.origin = "https://ha.example.net"
        self.origin_patch = patch.object(self.module, "selected_ha_origin", side_effect=lambda _: self.origin)
        self.origin_patch.start()

    async def asyncTearDown(self):
        self.origin_patch.stop()
        await self.fixture.asyncTearDown()

    async def call(self, action, data=None, *, origins=None, headers=None, identity=None):
        body = {"contract_version": 1, **(data or {})}
        if action.startswith("owner/"):
            body["identity"] = self.fixture.identity if identity is None else identity
        return await self.service.post(action, body,
            headers=self.fixture.headers if headers is None else headers,
            origins=[self.origin] if origins is None else origins, source="unit-peer")

    async def admitted(self, share=None):
        nonce = secrets.token_urlsafe(32)
        claim = (await self.call("claim", {"browser_nonce": nonce})).payload
        owner_fields = {key: claim[key] for key in ("issuer_epoch", "claim_id", "browser_generation", "code")}
        await self.call("owner/approve", owner_fields | {"session_id": self.fixture.active.session_id,
            "share": share or {"mode": "create", "consent": True}})
        binding = {key: claim[key] for key in ("issuer_epoch", "claim_id", "browser_generation", "claim_secret")}
        result = await self.call("collect", binding | {"browser_nonce": nonce})
        return result

    async def test_owner_context_absent_origin_requires_real_pairing_and_is_pure(self):
        result = await self.call("owner/context", origins=[])
        self.assertEqual(result.payload["session_id"], self.fixture.active.session_id)
        self.assertEqual(result.payload["display_entry_url"], self.origin + "/djconnect/vibecast/display")
        self.assertEqual(result.payload["route_trust"], "paired_owner_response")
        self.assertNotIn("signature", result.payload)
        self.assertFalse(self.manager._display_admission._shares)
        with self.assertRaises(self.module.DisplayAdmissionError):
            await self.call("owner/context", origins=[], headers={})

    async def test_closed_shapes_versions_and_nested_owner_identity(self):
        for action, data in [("claim", {"browser_nonce": secrets.token_urlsafe(32), "profile_id": "other"}),
                             ("claim", {"contract_version": True, "browser_nonce": "x"}),
                             ("owner/resolve", {"code": "１２３４５６"}),
                             ("snapshot", {}), ("session_end", {})]:
            with self.subTest(action=action, data=data), self.assertRaises(self.module.DisplayAdmissionError):
                await self.call(action, data)
        self.assertFalse(self.manager._display_admission._claims)

    async def test_nested_share_malformed_types_are_errors_without_reservations(self):
        nonce = secrets.token_urlsafe(32)
        claim = (await self.call("claim", {"browser_nonce": nonce})).payload
        fields = {key: claim[key] for key in ("issuer_epoch", "claim_id", "browser_generation", "code")}
        for share in ({"mode": []}, {"mode": {}}, {"mode": 1}, {"mode": "create", "consent": 1},
                      {"mode": "existing", "share_id": [], "share_generation": 1}):
            with self.subTest(share=share), self.assertRaises(self.module.DisplayAdmissionError):
                await self.call("owner/approve", fields | {"session_id": self.fixture.active.session_id, "share": share})
        self.assertFalse(self.manager._display_admission._shares)
        self.assertFalse(self.manager._display_admission._displays)

    async def test_display_origin_absent_null_foreign_duplicate_denied(self):
        for origins in ([], ["null"], ["https://other.example.net"], [self.origin, self.origin]):
            with self.subTest(origins=origins), self.assertRaises(self.module.DisplayAdmissionError):
                await self.call("claim", {"browser_nonce": secrets.token_urlsafe(32)}, origins=origins)
        self.assertFalse(self.manager._display_admission._claims)

    async def test_real_unit_pairing_chain_and_renew_read_only_grant(self):
        result = await self.admitted()
        result.release()
        payload = result.payload
        self.assertIn("lease_expires_at", payload)
        self.assertNotIn("profile_id", payload)
        self.assertFalse(payload["capabilities"]["owner_controls"])
        binding = {key: payload[key] for key in ("issuer_epoch", "display_id")}
        headers = {"Authorization": "Bearer " + payload["grant_token"]}
        renewed = await self.call("renew", binding | {"renew_sequence": 1}, headers=headers)
        repeated = await self.call("renew", binding | {"renew_sequence": 1}, headers=headers)
        self.assertEqual(renewed.payload["lease_revision"], repeated.payload["lease_revision"])
        with self.assertRaises(self.module.DisplayAdmissionError):
            await self.call("owner/context", headers=headers)
        await self.call("leave", binding, headers=headers)
        with self.assertRaises(self.module.DisplayAdmissionError):
            result.release()
        self.assertIsNotNone(self.manager.current_active("profile-a"))

    async def test_origin_change_clears_old_grants_and_never_reuses_epoch(self):
        result = await self.admitted()
        epoch = result.payload["issuer_epoch"]
        self.origin = "https://new.example.net"
        with self.assertRaises(self.module.DisplayAdmissionError):
            result.release()
        await self.call("owner/context")
        self.assertNotEqual(self.manager._display_admission.issuer_epoch, epoch)
        self.assertFalse(self.manager._display_admission._displays)

    async def test_unavailable_external_origin_fails_closed_and_clears_authority(self):
        await self.admitted()
        self.origin = None
        with self.assertRaises(self.module.DisplayAdmissionError) as failure:
            await self.call("owner/context", origins=[])
        self.assertEqual(failure.exception.code, "display_external_url_unavailable")
        self.assertFalse(self.manager._display_admission._displays)

    async def test_pairing_rotates_between_commit_and_delivery_no_credential_release(self):
        result = await self.admitted()
        self.fixture.runtime.device_token = "rotated-unit"
        with self.assertRaises(self.module.DisplayAdmissionError):
            result.release()

    async def test_session_ends_between_commit_and_delivery(self):
        result = await self.admitted()
        await self.manager.async_end(owner_profile_id="profile-a", session_id=self.fixture.active.session_id)
        with self.assertRaises(self.module.DisplayAdmissionError):
            result.release()

    async def test_owner_can_revoke_approved_uncollected_reservation(self):
        nonce = secrets.token_urlsafe(32)
        claim = (await self.call("claim", {"browser_nonce": nonce})).payload
        fields = {key: claim[key] for key in ("issuer_epoch", "claim_id", "browser_generation", "code")}
        approved = await self.call("owner/approve", fields | {"session_id": self.fixture.active.session_id,
            "share": {"mode": "create", "consent": True}})
        await self.call("owner/revoke", {"session_id": self.fixture.active.session_id,
            "share_id": approved.payload["share_id"], "display_id": approved.payload["display_id"]})
        with self.assertRaises(self.module.DisplayAdmissionError):
            approved.release()
        self.assertFalse(self.manager._display_admission._claims)
        self.assertEqual(len(self.manager._display_admission._shares), 1)

    async def test_profile_devices_observe_and_stop_only_the_current_live_connection(self):
        import aiohttp

        with patch.object(aiohttp, "WSMsgType", create=True):
            from custom_components.djconnect import display_live

        entries = {self.fixture.entry.entry_id: self.fixture.entry}
        self.fixture.hass.config_entries.async_get_entry = entries.get
        await self.fixture.storage.async_create_profile("Other", profile_id="profile-b",
                                                       default_backend_id="later_manual")
        other_session = await self.manager.async_start(owner_profile_id="profile-b")

        async def paired_device(serial, profile):
            device_id = f"djconnect-ios-{serial}"
            identity = {"device_id": device_id, "client_type": "ios"}
            token = f"fixture-{serial}"
            headers = {"Authorization": f"Bearer {token}"}
            await self.fixture.storage.async_upsert_device(device_id, "ios", linked_profile_id=profile)
            entry = SimpleNamespace(entry_id=serial, data={**identity, "device_token": token},
                                    options={}, disabled_by=None, state="loaded")
            entries[serial] = entry
            self.fixture.hass.data["djconnect"][serial] = SimpleNamespace(
                entry=entry, device_token=token, config=identity, device_status=identity,
                authorize_device_request=lambda request_headers, device_id=None, client_type=None: (
                    request_headers == headers and identity == {"device_id": device_id, "client_type": client_type}
                ),
            )
            return {"identity": identity, "headers": headers}

        second = await paired_device("ABCDEF123457", "profile-a")
        other = await paired_device("ABCDEF123458", "profile-b")
        state = self.manager._display_admission
        hub = display_live.display_live_hub(self.manager)
        active = self.fixture.active
        await self.manager.async_update_playback_projection(
            owner_profile_id="profile-a", session_id=active.session_id,
            state="playing", media_identity="spotify:track:fixture", title="Track",
        )
        playback = active.broadcast.state.playback
        first = (await self.admitted()).payload
        share = {key: first[key] for key in ("share_id", "share_generation")}
        second_screen = (await self.admitted({"mode": "existing", **share})).payload
        context = await self.call("owner/context", **second)
        self.assertEqual(context.payload["share_id"], share["share_id"])
        self.assertEqual(context.payload["live_display_status"]["displays"], [])

        def connect(payload):
            display = state._displays[payload["display_id"]]
            if previous := hub.connections.get(display.display_id):
                previous.invalidate()
            display.connection_generation += 1
            connection = display_live._Connection(
                self.fixture.hass, hub, display, active, self.origin,
                SimpleNamespace(closed=False), SimpleNamespace(transport=Mock()),
            )
            hub.connections[display.display_id] = connection
            display.invalidated = connection.invalidate
            return connection

        def target(context, connection):
            return {"session_id": active.session_id, "share_id": connection.display.share_id,
                    "issuer_epoch": context.payload["issuer_epoch"],
                    "display_id": connection.display.display_id, "connection_generation": connection.generation}

        with patch.object(display_live, "selected_ha_origin", return_value=self.origin):
            original = connect(first)
            unrelated = connect(second_screen)
            observed = await self.call("owner/context", **second)
            observed.release()
            displays = observed.payload["live_display_status"]["displays"]
            self.assertEqual({item["display_id"] for item in displays},
                             {first["display_id"], second_screen["display_id"]})
            self.assertTrue(all(set(item) == {"display_id", "share_id", "connection_generation"} for item in displays))
            foreign = await self.call("owner/context", **other)
            self.assertEqual(foreign.payload["live_display_status"]["displays"], [])
            self.assertNotIn("share_id", foreign.payload)
            with self.assertRaises(self.module.DisplayAdmissionError):
                await self.call("owner/revoke", target(observed, original)
                                | {"session_id": other_session.session_id}, **other)

            replacement = connect(first)
            with self.assertRaises(self.module.DisplayAdmissionError):
                observed.release()
            with self.assertRaises(self.module.DisplayAdmissionError):
                await self.call("owner/revoke", target(observed, original), **second)
            self.assertTrue(replacement.current())
            fresh = await self.call("owner/context", **second)
            incomplete = target(fresh, replacement)
            del incomplete["issuer_epoch"]
            with self.assertRaises(self.module.DisplayAdmissionError) as missing:
                await self.call("owner/revoke", incomplete, **second)
            self.assertEqual(missing.exception.status, 400)
            with self.assertRaises(self.module.DisplayAdmissionError):
                await self.call("owner/revoke", target(fresh, replacement)
                                | {"issuer_epoch": secrets.token_urlsafe(32)}, **second)
            with self.assertRaises(self.module.DisplayAdmissionError) as wrong_share:
                await self.call("owner/revoke", target(fresh, replacement)
                                | {"share_id": secrets.token_urlsafe(32)}, **second)
            self.assertEqual(wrong_share.exception.status, 409)
            stopped = await self.call("owner/revoke", target(fresh, replacement), **second)
            stopped.release()
            self.assertFalse(replacement.current())
            replacement.request.transport.close.assert_called_once()
            self.assertTrue(unrelated.current())
            self.assertIs(self.manager.current_active("profile-a"), active)
            self.assertEqual(active.broadcast.state.playback, playback)
            with self.assertRaises(self.module.DisplayAdmissionError):
                fresh.release()
            after = (await self.call("owner/context")).payload
            self.assertEqual(after["share_id"], share["share_id"])
            self.assertEqual(after["live_display_status"]["displays"],
                             [{"display_id": unrelated.display.display_id, "share_id": second_screen["share_id"],
                               "connection_generation": unrelated.generation}])
            self.assertGreater(after["live_display_status"]["observation_revision"],
                               stopped.payload["observation_revision"])
            unrelated.ws.closed = True
            disconnected = (await self.call("owner/context", **second)).payload
            self.assertEqual(disconnected["live_display_status"]["displays"], [])
            self.assertIn(unrelated.display.display_id, state._displays)
            last = connect(second_screen)
            observed_last = await self.call("owner/context", **second)
            await self.call("owner/revoke", target(observed_last, last), **second)
            inactive = (await self.call("owner/context")).payload
            self.assertEqual(inactive["live_display_status"]["displays"], [])
            self.assertEqual(inactive["share_id"], share["share_id"])

    async def test_snapshot_is_closed_owner_private_free_and_does_not_renew_lease(self):
        result = await self.admitted()
        payload = result.payload
        binding = {key: payload[key] for key in ("issuer_epoch", "display_id")}
        headers = {"Authorization": "Bearer " + payload["grant_token"]}
        state = self.manager._display_admission
        deadline = state._displays[payload["display_id"]].lease_deadline
        snapshot = await self.call("snapshot", binding, headers=headers)
        snapshot.release()
        data = snapshot.payload["snapshot"]
        self.assertEqual(set(data["session_presentation"]) - {"mood", "persona", "presence"}, set())
        self.assertEqual(data["session"]["session_id"], self.fixture.active.session_id)
        self.assertEqual(state._displays[payload["display_id"]].lease_deadline, deadline)
        import json
        wire = json.dumps(data)
        for field in ("profile_id", "account_id", "device_id", "planner", "session_flow", "session_direction",
                      "voice", "history", "conversation", "up_next", "target_name", "artwork", "grant_token"):
            self.assertNotIn('"' + field + '"', wire)
        await self.manager.async_end(owner_profile_id="profile-a", session_id=self.fixture.active.session_id)
        with self.assertRaises(self.module.DisplayAdmissionError):
            snapshot.release()
        snapshot.complete()

    async def test_current_album_bytes_are_bound_to_one_display_and_track(self):
        from PIL import Image
        from homeassistant.helpers import aiohttp_client
        from custom_components.djconnect.display_delivery import _prepare_artwork
        from custom_components.djconnect.display_transport import _FencedResponse
        from custom_components.djconnect import image_proxy

        async def display_credentials(share=None):
            payload = (await self.admitted(share)).payload
            binding = {key: payload[key] for key in ("issuer_epoch", "display_id")}
            headers = {"Authorization": "Bearer " + payload["grant_token"]}
            return binding, headers

        async def observe(identifier):
            await self.manager.async_update_playback_projection(owner_profile_id="profile-a",
                session_id=self.fixture.active.session_id, state="playing",
                media_identity="spotify:track:" + identifier, title="Track", album="Album")
            return self.fixture.active.broadcast.state.playback

        async def prepare(playback, color):
            buf = BytesIO()
            Image.new("RGB", (32, 32), color).save(buf, format="PNG")
            body = buf.getvalue()

            class Content:
                async def iter_chunked(self, _size):
                    yield body[:32]
                    yield body[32:]

            class Response:
                status = 200
                content = Content()

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_error):
                    return None

            cdn = "https://i.scdn.co/image/" + "a" * 40

            def get(url, *, allow_redirects, timeout):
                self.assertEqual(url, cdn)
                self.assertFalse(allow_redirects)
                return Response()

            hass = self.fixture.hass
            decoder = AsyncMock(side_effect=lambda callback, data: callback(data))
            with (patch.object(aiohttp_client, "async_get_clientsession", return_value=SimpleNamespace(get=get)),
                  patch.object(image_proxy, "session_images", return_value=SimpleNamespace(decode=decoder))):
                await _prepare_artwork(hass, state, self.fixture.active.broadcast, playback.item_id,
                               playback.source_url, cdn,
                               lambda: True, lambda: True,
                               lambda: {(share.share_id, share.generation)}, state._clock())
            return body

        async def snapshot(binding, headers):
            result = await self.call("snapshot", binding, headers=headers)
            try:
                return result.payload["snapshot"]
            finally:
                result.complete()

        binding, headers = await display_credentials()
        state = self.manager._display_admission
        share = state._shares[state._displays[binding["display_id"]].share_id]
        other, other_headers = await display_credentials({
            "mode": "existing", "share_id": share.share_id, "share_generation": share.generation,
        })
        first_bytes = await prepare(await observe("A" * 22), "red")
        first = (await snapshot(binding, headers))["artwork"]
        with self.assertRaises(self.module.DisplayAdmissionError):
            await self.call("artwork", other | {"reference": first["reference"]}, headers=other_headers)
        media = await self.call("artwork", binding | {"reference": first["reference"]}, headers=headers)
        response = _FencedResponse(media)
        self.assertEqual(response.body, first_bytes)
        self.assertEqual(response.content_type, "image/png")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        try:
            media.release()
            playback = await observe("B" * 22)
            with self.assertRaises(self.module.DisplayAdmissionError):
                media.release()
            self.assertNotIn("artwork", await snapshot(binding, headers))
        finally:
            media.complete()
        second_bytes = await prepare(playback, "blue")
        second = (await snapshot(binding, headers))["artwork"]
        self.assertNotEqual(first["reference"], second["reference"])
        media = await self.call("artwork", binding | {"reference": second["reference"]}, headers=headers)
        self.assertEqual(media.media, (second_bytes, "image/png"))
        try:
            display = state._displays[binding["display_id"]]
            with patch.object(state, "_clock", return_value=display.lease_deadline):
                with self.assertRaises(self.module.DisplayAdmissionError):
                    media.release()
            await self.call("leave", binding, headers=headers)
            with self.assertRaises(self.module.DisplayAdmissionError):
                media.release()
        finally:
            media.complete()

    async def test_simultaneous_snapshot_reserves_before_projection_until_body_completes(self):
        result = await self.admitted()
        payload = result.payload
        binding = {key: payload[key] for key in ("issuer_epoch", "display_id")}
        headers = {"Authorization": "Bearer " + payload["grant_token"]}
        first = await self.call("snapshot", binding, headers=headers)
        with self.assertRaises(self.module.DisplayAdmissionError) as failure:
            await self.call("snapshot", binding, headers=headers)
        self.assertEqual(failure.exception.status, 429)
        first.complete()
        first.complete()
        second = await self.call("snapshot", binding, headers=headers)
        second.complete()
