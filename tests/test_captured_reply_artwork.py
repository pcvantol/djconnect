"""Original reply subject, persisted identity only and fresh guarded media preparation."""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from copy import deepcopy

from tests import test_history_playback_application as application


class CapturedReplyArtworkTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        application.HistoricalPlaybackApplicationTests.setUpClass()
        cls.reply = importlib.import_module("custom_components.djconnect.reply_artwork")
        cls.art = importlib.import_module("custom_components.djconnect.session_artwork")
        cls.core = application.HistoricalPlaybackApplicationTests.core
        cls.dialogue = application.HistoricalPlaybackApplicationTests.dialogue

    @classmethod
    def tearDownClass(cls):
        application.HistoricalPlaybackApplicationTests.tearDownClass()

    async def asyncSetUp(self):
        self.app = application.HistoricalPlaybackApplicationTests()
        await self.app.asyncSetUp()
        self.hass = self.app.hass
        self.hass.async_create_task = asyncio.create_task
        self.hass.loop = asyncio.get_running_loop()
        self.hass.bus = SimpleNamespace(async_listen_once=lambda event, callback: lambda: None)
        proxy = importlib.import_module("custom_components.djconnect.image_proxy")
        with patch.dict(
            sys.modules,
            {"homeassistant.const": SimpleNamespace(EVENT_HOMEASSISTANT_STOP="homeassistant_stop")},
        ):
            registry = proxy.ManagedSessionImages(self.hass)
        self.hass.data["djconnect"]["session_images"] = registry
        self.app.f.service.session_image_owner = registry
        self.source = {
            "backend_id": "source-spotify",
            "music_account_id": "source-account",
            "provider_entry_id": "source-entry",
            "provider_account_id": "provider-original",
        }
        self.media = {
            "uri": "spotify:track:" + "A" * 22,
            "album_uri": "spotify:album:" + "B" * 22,
            "title": "Synthetic original recording",
            "artist": "Synthetic original artist",
            "album_image_url": "https://i.scdn.co/image/" + "a" * 40,
        }

    async def asyncTearDown(self):
        registry = self.hass.data.get("djconnect", {}).get("session_images")
        if registry is not None:
            registry.close()
        await self.app.asyncTearDown()

    async def current_identification(self, *, second=None, question='Wie zijn dit?', active_session=True):
        reads=[]
        if active_session:
            await self.app.f.manager.async_update_playback_projection(
                owner_profile_id='profile-a', session_id=self.app.current.session_id,
                state='playing', media_identity=self.media['uri'], title=self.media['title'],
                artist=self.media['artist'], album_uri=self.media['album_uri'])
        else:
            await self.app.f.manager.async_end(owner_profile_id='profile-a',session_id=self.app.current.session_id)
        counter=getattr(self,'_current_art_counter',0)+1
        self._current_art_counter=counter
        async def provider(hass, runtime, command, *args, **kwargs):
            self.assertEqual(command, 'status')
            reads.append(command)
            media=self.media if len(reads)==1 or second is None else second
            return {'success':True, 'playback':deepcopy(media)}
        download=AsyncMock(return_value=(b'fixture-pixels','image/png'))
        with patch.object(self.core, 'run_music_command', provider), patch.object(
                self.reply, '_download_observed_cover', download), patch.object(
                self.core, '_call_dialogue_agent', side_effect=AssertionError('local identification is no model call')):
            result,status=await self.app.f.handlers.async_handle_ask_dj_message_payload(
                self.hass, {**self.app.identity, 'text':question, 'language':'nl',
                    'audio_response':'never', 'client_message_id':'current-identification-art-'+str(counter),
                    'conversation_context':{'session_id':self.app.current.session_id} if active_session else {}},
                headers=self.app.headers)
        self.current_cover_download=download
        return result,status,reads

    async def test_current_identification_returns_exact_observed_album_cover_without_archiving(self):
        result,status,reads=await self.current_identification()
        self.assertEqual(status,200,result)
        self.assertEqual(result['text'],'Dit is Synthetic original artist, met Synthetic original recording.')
        self.assertEqual(reads,['status','status'])
        self.assertEqual(len(result['images']),1)
        self.assertEqual(result['images'][0]['kind'],'album_art')
        self.assertIn('/api/djconnect/v1/session/media/image/',result['images'][0]['url'])
        self.assertTrue(result['images'][0]['requires_device_auth'])
        from datetime import datetime, UTC
        remaining=(datetime.fromisoformat(result['images'][0]['expires_at'])-datetime.now(UTC)).total_seconds()
        self.assertGreater(remaining,0)
        self.assertLessEqual(remaining,60)
        self.current_cover_download.assert_awaited_once()
        self.assertNotIn('i.scdn.co',json.dumps(result))
        self.assertFalse(result['history_persisted'])
        self.assertEqual(result['playback_actions'],[])
        self.assertNotIn('reply_media_reference',json.dumps(result))

    async def test_current_reply_cover_stays_out_of_attached_live_projection_even_after_expiry(self):
        self.art.attach_live_projection(self.hass,'profile-a',self.app.current.session_id)
        broadcast=self.app.current.broadcast
        before=broadcast.media_projector()
        result,status,_=await self.current_identification()
        self.assertEqual(status,200,result)
        self.assertEqual(len(result['images']),1)
        self.assertEqual(broadcast.media_projector(),before)
        broadcast.native_delivery()
        registry=self.hass.data['djconnect']['session_images']
        asset_id=result['images'][0]['url'].rsplit('/',1)[-1]
        key,asset=next((k,v) for k,v in registry.assets.items() if v['asset_id']==asset_id)
        registry.expire(key,asset_id)
        self.assertEqual(broadcast.media_projector(),before)
        broadcast.native_delivery()

    async def test_current_identification_different_edition_or_untrusted_cover_is_omitted(self):
        for replacement in [
            {**self.media,'album_uri':'spotify:album:'+'C'*22},
            {**self.media,'album_image_url':'https://untrusted.test/art.jpg'},
            {**self.media,'album_image_url':'https://i.scdn.co/image/'+'b'*40},
            {**self.media,'album_uri':''},
        ]:
            # Fresh client identity for each synthetic observation, no cached replay.
            with self.subTest(replacement=replacement):
                result,status,reads=await self.current_identification(second=replacement)
                self.assertEqual(status,200,result)
                self.assertEqual(reads,['status','status'])
                self.assertEqual(result['images'],[])
                self.current_cover_download.assert_not_awaited()
                self.assertFalse(result['history_persisted'])

    async def test_current_identification_changed_recording_rejects_cover_and_text(self):
        result,status,reads=await self.current_identification(
            second={**self.media,'uri':'spotify:track:'+'C'*22})
        self.assertEqual(status,409,result)
        self.assertEqual(result['error'],'playback_context_changed')
        self.assertEqual(reads,['status','status'])
        self.assertFalse(result.get('images'))
        self.assertNotIn('Synthetic original recording',json.dumps(result))

    async def image_http(self, result, *, headers=None):
        from custom_components.djconnect import http
        class Request(dict):
            pass
        request=Request()
        request.app={'hass':self.hass}
        request.query=dict(self.app.identity)
        request.headers=self.app.headers if headers is None else headers
        url=result['images'][0]['url']
        session_id,asset_id=url.rsplit('/',2)[-2:] if '/session/media/' in url else ('',url.rsplit('/',1)[-1])
        return await http.DJConnectSessionMediaImageView(self.hass).get(request,session_id,asset_id)

    async def test_general_current_reply_cover_creates_no_session_and_requires_auth(self):
        result,status,reads=await self.current_identification(active_session=False)
        self.assertEqual(status,200,result)
        self.assertEqual(reads,['status','status'])
        self.assertIsNone(self.app.f.manager.current_active('profile-a'))
        self.assertIn('/api/djconnect/v1/ask_dj/reply/image/',result['images'][0]['url'])
        image=await self.image_http(result)
        self.assertEqual(image.status,200)
        self.assertEqual(image.body,b'fixture-pixels')
        unauthenticated=await self.image_http(result,headers={})
        self.assertEqual(unauthenticated.status,401)
        self.assertFalse(result['history_persisted'])
        self.assertIsNone(self.app.f.manager.current_active('profile-a'))

    async def test_current_cover_actual_image_get_requires_auth_and_revokes_after_source_withdrawal(self):
        result,status,_=await self.current_identification()
        self.assertEqual(status,200,result)
        image=await self.image_http(result)
        self.assertEqual(image.status,200)
        self.assertEqual(image.body,b'fixture-pixels')
        self.assertEqual(image.headers['Cache-Control'],'no-store')
        unauthenticated=await self.image_http(result,headers={})
        self.assertEqual(unauthenticated.status,401)
        self.app.provider._receiver_end_generation+=1
        withdrawn=await self.image_http(result)
        self.assertEqual(withdrawn.status,404)
        self.assertNotIn(b'fixture-pixels',withdrawn.body or b'')

    async def test_current_cover_actual_image_get_expires_and_other_owner_cannot_read(self):
        result,status,_=await self.current_identification()
        self.assertEqual(status,200,result)
        session_id,asset_id=result['images'][0]['url'].rsplit('/',2)[-2:]
        other=await self.art.image(self.hass,SimpleNamespace(profile_id='other-owner'),
            session_id,asset_id,runtime=self.app.runtime)
        self.assertIsNone(other)
        registry=self.hass.data['djconnect']['session_images']
        asset=next(v for v in registry.assets.values() if v['asset_id']==asset_id)
        asset['deadline']=0
        expired=await self.image_http(result)
        self.assertEqual(expired.status,404)
        self.assertNotIn(b'fixture-pixels',expired.body or b'')

    async def accepted_reply(self, *, text_only=False, playback_fallback=False):
        async def provider_reply(*args, **kwargs):
            images = (
                self.core._images_from_context(
                    self.hass,
                    {
                        "text": "Unrelated named-subject reply",
                        **({"playback": self.media} if playback_fallback == "nested" else {}),
                    },
                    {} if playback_fallback == "nested" else self.media,
                )
                if playback_fallback
                else []
                if text_only
                else self.core._images_from_context(self.hass, {"resolved_media": self.media}, {})
            )
            return {
                "success": True,
                "text": "Synthetic reply about the original recording",
                "images": images,
                "sources": [],
                "links": [],
                "playback_actions": [],
                "action": "none",
            }

        f = self.app.f
        with patch.object(f.handlers.http_helpers, "async_handle_ask_dj", provider_reply):
            result, status = await f.handlers.async_handle_ask_dj_message_payload(
                self.hass,
                {
                    **self.app.identity,
                    "text": "Tell me about the named recording",
                    "audio_response": "never",
                    "client_message_id": "captured-reply",
                    "conversation_context": {"session_id": self.app.current.session_id},
                },
                headers=self.app.headers,
            )
        self.assertEqual(status, 200, result)
        self.assertTrue(result["success"], result)
        rows = await f.repo.async_entry_records("profile-a", self.app.current.session_id)
        row = next(r for r in rows if r["kind"] == "conversation_dj")
        return result, row

    def test_reference_is_identity_only_and_closed(self):
        value = self.reply.subject(self.media, self.source)
        self.assertEqual(
            value,
            {
                "schema_version": 1,
                "subject_uri": self.media["uri"],
                "album_uri": self.media["album_uri"],
                "source_context": self.source,
            },
        )
        self.assertNotIn("https:", json.dumps(value))
        self.assertNotIn("image_url", value)
        for extra in (
            {"url": "https://example.test"},
            {"schema_version": True},
            {"album_uri": ""},
            {"subject_uri": "spotify:track:" + "Z" * 22 + "?x"},
            {"source_context": {}},
        ):
            with self.subTest(extra=extra):
                self.assertIsNone(self.reply.checked({**value, **extra}))
        for media in (
            {"title": "Same text", "album_image_url": self.media["album_image_url"]},
            {**self.media, "album_uri": None},
            {**self.media, "album_image_url": "https://untrusted.test/a.jpg"},
        ):
            self.assertIsNone(self.reply.subject(media, self.source))

    async def test_captured_subject_survives_storage_but_never_leaks_internal_binding(self):
        result, row = await self.accepted_reply()
        self.assertNotIn("reply_media_reference", json.dumps(result))
        stored = await self.app.history.async_history("profile:profile-a")
        assistant = next(m for m in stored["messages"] if m["role"] == "assistant")
        ref = assistant["session_turn"]["reply_media_reference"]
        self.assertEqual(ref["subject_uri"], self.media["uri"])
        self.assertEqual(assistant["images"], [])
        self.assertNotIn("i.scdn.co", json.dumps(stored))
        history, status = await self.app.f.handlers.async_handle_ask_dj_history_payload(
            self.hass,
            {**self.app.identity, "conversation_scope": "profile"},
            headers=self.app.headers,
        )
        self.assertEqual(status, 200, history)
        self.assertNotIn("reply_media_reference", json.dumps(history))
        context = SimpleNamespace(profile_id="profile-a")
        resolved = await self.art.resolve_target(
            self.hass,
            self.app.runtime,
            context,
            self.app.current.session_id,
            {"entry_id": row["entry_id"]},
        )
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved[0], self.media["uri"])
        self.assertEqual(resolved[5], self.media["album_uri"])
        self.assertEqual(resolved[6], "captured_reply_subject")
        self.assertNotEqual(resolved[0], "spotify:track:" + "Z" * 22)

    async def test_text_only_and_legacy_replies_do_not_borrow_current_art(self):
        result, row = await self.accepted_reply(text_only=True)
        resolved = await self.art.resolve_target(
            self.hass,
            self.app.runtime,
            SimpleNamespace(profile_id="profile-a"),
            self.app.current.session_id,
            {"entry_id": row["entry_id"]},
        )
        self.assertIsNone(resolved)
        self.assertEqual(result["images"], [])

    async def test_current_playback_image_fallback_is_never_captured_as_reply_subject(self):
        result, row = await self.accepted_reply(playback_fallback=True)
        self.assertTrue(result["images"], result)  # Exercise actual legacy live fallback.
        stored = await self.app.history.async_history("profile:profile-a")
        self.assertNotIn("reply_media_reference", json.dumps(stored))
        target = await self.art.resolve_target(
            self.hass,
            self.app.runtime,
            SimpleNamespace(profile_id="profile-a"),
            self.app.current.session_id,
            {"entry_id": row["entry_id"]},
        )
        self.assertIsNone(target)

    async def test_embedded_current_playback_is_not_an_original_reply_subject(self):
        result, _ = await self.accepted_reply(playback_fallback="nested")
        self.assertTrue(result["images"], result)
        stored = await self.app.history.async_history("profile:profile-a")
        self.assertNotIn("reply_media_reference", json.dumps(stored))

    async def test_withdrawn_original_source_denies_art_and_no_other_account_substitution(self):
        _, row = await self.accepted_reply()
        self.app.source.disabled_by = "user"
        resolved = await self.art.resolve_target(
            self.hass,
            self.app.runtime,
            SimpleNamespace(profile_id="profile-a"),
            self.app.current.session_id,
            {"entry_id": row["entry_id"]},
        )
        self.assertIsNone(resolved)

    async def test_real_registry_preparation_rechecks_reply_and_clear_revokes_pixels(self):
        _, row = await self.accepted_reply()
        # Provider and CDN I/O are the only image fixture boundary; real registry,
        # authority, archive reads and existing prepare/image path run unchanged.
        fetch = AsyncMock(
            return_value=(
                b"fixture-pixels",
                "image/png",
                "https://open.spotify.com/track/" + "A" * 22,
                self.media["album_uri"],
                1,
                1,
                "Synthetic original recording",
            )
        )
        context = SimpleNamespace(profile_id="profile-a")
        with patch.object(self.art, "_fetch", fetch):
            prepared = await self.art.prepare(
                self.hass,
                self.app.runtime,
                context,
                session_id=self.app.current.session_id,
                target={"entry_id": row["entry_id"]},
            )
        self.assertEqual(prepared["artwork"]["state"], "ready", prepared)
        self.assertIs(prepared["artwork"]["reply_display_allowed"], True)
        self.assertIs(prepared["artwork"]["current_display_allowed"], False)
        self.assertIs(prepared["artwork"]["active_flow_display_allowed"], False)
        self.assertEqual(fetch.await_args.args[2], self.media["uri"])
        self.assertEqual(fetch.await_args.kwargs["expected_album_uri"], self.media["album_uri"])
        asset = prepared["artwork"]["url"].rsplit("/", 1)[-1]
        image = await self.art.image(
            self.hass, context, self.app.current.session_id, asset, runtime=self.app.runtime
        )
        self.assertEqual(image, (b"fixture-pixels", "image/png"))
        await self.app.history.async_clear("profile:profile-a")
        image = await self.art.image(
            self.hass, context, self.app.current.session_id, asset, runtime=self.app.runtime
        )
        self.assertIsNone(image)

    async def test_profile_export_never_exports_original_private_source_binding(self):
        await self.accepted_reply()
        result, status = await self.app.f.handlers.async_handle_ask_dj_history_export_payload(
            self.hass,
            {**self.app.identity, "conversation_scope": "profile"},
            headers=self.app.headers,
        )
        self.assertEqual(status, 200, result)
        self.assertNotIn("reply_media_reference", json.dumps(result))
        self.assertNotIn("provider-original", json.dumps(result))

    async def test_source_withdrawal_during_art_fetch_never_publishes_pixels(self):
        _, row = await self.accepted_reply()

        async def fetch(*args, **kwargs):
            self.app.source.disabled_by = "user"
            return (
                b"fixture-pixels",
                "image/png",
                "https://open.spotify.com/track/" + "A" * 22,
                self.media["album_uri"],
                1,
                1,
                "Synthetic",
            )

        with patch.object(self.art, "_fetch", fetch):
            result = await self.art.prepare(
                self.hass,
                self.app.runtime,
                SimpleNamespace(profile_id="profile-a"),
                session_id=self.app.current.session_id,
                target={"entry_id": row["entry_id"]},
            )
        self.assertNotEqual(result.get("artwork", {}).get("state"), "ready", result)
        self.assertEqual(self.hass.data["djconnect"]["session_images"].assets, {})

    async def test_reply_deletion_during_art_fetch_never_publishes_pixels(self):
        _, row = await self.accepted_reply()

        async def fetch(*args, **kwargs):
            await self.app.history.async_clear("profile:profile-a")
            return (
                b"fixture-pixels",
                "image/png",
                "https://open.spotify.com/track/" + "A" * 22,
                self.media["album_uri"],
                1,
                1,
                "Synthetic",
            )

        with patch.object(self.art, "_fetch", fetch):
            result = await self.art.prepare(
                self.hass,
                self.app.runtime,
                SimpleNamespace(profile_id="profile-a"),
                session_id=self.app.current.session_id,
                target={"entry_id": row["entry_id"]},
            )
        self.assertNotEqual(result.get("artwork", {}).get("state"), "ready", result)
        self.assertEqual(self.hass.data["djconnect"]["session_images"].assets, {})

    def test_public_sanitizer_also_closes_nested_duplicate_receipts(self):
        value = {
            "messages": [
                {
                    "session_turn": {
                        "turn_id": "t",
                        "reply_media_reference": {"secret": "do-not-export"},
                    }
                }
            ],
            "assistant_message": {
                "session_turn": {"reply_media_reference": {"secret": "do-not-export"}}
            },
        }
        public = self.reply.public(value)
        self.assertNotIn("do-not-export", json.dumps(public))
        self.assertIn("reply_media_reference", json.dumps(value))
