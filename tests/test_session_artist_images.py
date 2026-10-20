"""Actual media owner/SQLite with explicit source/image/model fixtures.

No public-photo, live HA, native rendering or prose-quality PASS is implied.
"""

import asyncio
from copy import deepcopy
from dataclasses import replace
import io
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import unittest
from unittest.mock import patch

from tests import test_personal_dj_narration_public_artist as narration_fixtures
from custom_components.djconnect import artist_photo as photo


def image_bytes():
    from PIL import Image

    output = io.BytesIO()
    Image.new("RGB", (640, 360), (15, 60, 90)).save(output, format="PNG")
    return output.getvalue()


def page(title="File:Fixture band concert.png", *, live=True):
    def v(value):
        return {"value": value}

    return {
        "title": title,
        "ns": 6,
        "imageinfo": [
            {
                "mediatype": "BITMAP",
                "mime": "image/png",
                "sha1": "a" * 40,
                "width": 1920,
                "height": 1080,
                "thumbwidth": 640,
                "thumbheight": 360,
                "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Fixture.png/640px-Fixture.png",
                "descriptionurl": photo.file_url(title),
                "extmetadata": {
                    "Artist": v(
                        '<a href="https://commons.wikimedia.org/wiki/User:Fixture">Fixture Photographer</a>'
                    ),
                    "Credit": v("Own work"),
                    "LicenseShortName": v("CC BY-SA 4.0"),
                    "LicenseUrl": v("https://creativecommons.org/licenses/by-sa/4.0/"),
                    "ImageDescription": v(
                        "Fixture band performing live at a concert."
                        if live
                        else "Fixture band portrait."
                    ),
                    "Categories": v("Live music" if live else "Portraits"),
                },
            }
        ],
    }


def entity(qid="Q1", names=("Fixture band concert.png",)):
    return {
        "entities": {
            qid: {
                "id": qid,
                "claims": {
                    "P18": [
                        {
                            "rank": "normal",
                            "mainsnak": {"snaktype": "value", "datavalue": {"value": name}},
                        }
                        for name in names
                    ]
                },
            }
        }
    }


class ArtistPhotoSourceTests(unittest.IsolatedAsyncioTestCase):
    def test_exact_qid_bounded_file_selection_excludes_other_entities_unsafe_and_deprecated(self):
        e = entity()["entities"]["Q1"]
        self.assertEqual(photo.filenames(e, "Q1"), ["File:Fixture band concert.png"])
        self.assertEqual(photo.filenames(e, "Q2"), [])
        for name in (
            "https://attacker.invalid/x.jpg",
            "../other.jpg",
            "Logo.svg",
            "Band logo.png",
            "album_cover.jpg",
            "x|y.png",
        ):
            self.assertEqual(
                photo.filenames(entity(names=(name,))["entities"]["Q1"], "Q1"), [], name
            )
        e["claims"]["P18"][0]["rank"] = "deprecated"
        self.assertEqual(photo.filenames(e, "Q1"), [])
        e = entity(names=tuple("Band " + str(i) + ".jpg" for i in range(8)))["entities"]["Q1"]
        self.assertEqual(len(photo.filenames(e, "Q1")), 3)

    def test_live_source_hint_preferred_and_attribution_is_plain_not_executable_html(self):
        still = page("File:Fixture portrait.png", live=False)
        concert = page()
        choices = photo.candidates(
            {"query": {"pages": [still, concert]}}, [still["title"], concert["title"]]
        )
        self.assertEqual(choices[0].title, concert["title"])
        self.assertEqual(choices[0].author, "Fixture Photographer")
        self.assertEqual(choices[0].license_id, "CC-BY-SA-4.0")
        self.assertNotIn("<", json.dumps(choices[0].metadata()))
        self.assertEqual(
            photo.plain("<script>malicious()</script><b>Actual author</b>"), "Actual author"
        )
        self.assertFalse(photo.candidates({"query": {"pages": [still]}}, [concert["title"]]))
        tracked = deepcopy(concert)
        tracked["imageinfo"][0]["thumburl"] += (
            "?utm_source=commons.wikimedia.org&utm_content=thumbnail"
        )
        tracked["imageinfo"][0]["thumbmime"] = None
        normalized = photo.candidates({"query": {"pages": [tracked]}}, [tracked["title"]])[0]
        self.assertNotIn("?", normalized.url)
        intrinsic = deepcopy(concert)
        info = intrinsic["imageinfo"][0]
        original = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Fixture.png"
        info.update(
            width=367,
            height=346,
            thumbwidth=1024,
            thumbheight=965,
            url=original,
            thumburl=original + "?utm_content=thumbnail_unscaled",
        )
        original_candidate = photo.candidates(
            {"query": {"pages": [intrinsic]}}, [intrinsic["title"]]
        )[0]
        self.assertEqual((original_candidate.width, original_candidate.height), (367, 346))

    def test_missing_ambiguous_restricted_rights_and_untrusted_image_hosts_never_admit_pixels(self):
        base = page()
        for mutation in (
            "no_author",
            "nc",
            "wrong_license_url",
            "restrictions",
            "external_host",
            "userinfo",
            "redirect_host",
            "wrong_file_page",
            "tiny",
            "svg",
            "missing_revision",
            "missing_file",
            "tiny_original",
            "album_cover",
        ):
            p = deepcopy(base)
            info = p["imageinfo"][0]
            ext = info["extmetadata"]
            if mutation == "no_author":
                ext.pop("Artist")
            elif mutation == "nc":
                ext["LicenseShortName"]["value"] = "CC BY-NC 4.0"
            elif mutation == "wrong_license_url":
                ext["LicenseUrl"]["value"] = "https://attacker.invalid/by-sa/4.0/"
            elif mutation == "restrictions":
                ext["Restrictions"] = {"value": "No reuse"}
            elif mutation == "external_host":
                info["thumburl"] = "https://attacker.invalid/x.png"
            elif mutation == "userinfo":
                info["thumburl"] = "https://upload.wikimedia.org@attacker.invalid/x.png"
            elif mutation == "redirect_host":
                info["thumburl"] = "https://upload.wikimedia.org.attacker.invalid/x.png"
            elif mutation == "wrong_file_page":
                info["descriptionurl"] = photo.file_url("File:Another band.png")
            elif mutation == "tiny":
                info["thumbwidth"] = 32
            elif mutation == "svg":
                info["mime"] = "image/svg+xml"
            elif mutation == "missing_revision":
                info.pop("sha1")
            elif mutation == "missing_file":
                p["missing"] = True
            elif mutation == "tiny_original":
                info.update(width=367, height=346)
            elif mutation == "album_cover":
                ext["ImageDescription"]["value"] = "Album cover scanned for this concert."
            self.assertEqual(
                photo.candidates({"query": {"pages": [p]}}, [base["title"]]), [], mutation
            )

    async def test_actual_source_adapter_retrieves_one_exact_qid_batch_and_validated_image(self):
        calls = []

        async def guard():
            pass

        async def read(hass, url, owned_guard, *, json_body):
            await owned_guard()
            calls.append(url)
            if url.startswith(photo.WD):
                self.assertEqual(parse_qs(urlsplit(url).query)["ids"], ["Q1"])
                return entity()
            if url.startswith(photo.API):
                return {"query": {"pages": [page()]}}
            return image_bytes(), "image/png"

        from tests import test_session_artwork as fixtures

        fixtures.SessionArtworkTests.setUpClass()
        try:

            async def decode(body):
                return fixtures.SessionArtworkTests.art._decoded_size(body)

            with patch.object(photo, "_read", read):
                body, mime, selected = await photo.fetch(object(), "Q1", guard=guard, decode=decode)
            self.assertEqual(len(calls), 3)
            self.assertEqual(mime, "image/png")
            self.assertEqual(body, image_bytes())
            self.assertTrue(selected.live_hint)
        finally:
            fixtures.SessionArtworkTests.tearDownClass()

    async def test_small_p18_uses_structured_concert_with_exact_depicts_instead_of_name_search(
        self,
    ):
        calls = []

        async def guard():
            pass

        async def read(hass, url, owned_guard, *, json_body):
            await owned_guard()
            calls.append(url)
            q = parse_qs(urlsplit(url).query)
            if url.startswith(photo.WD):
                return entity(names=("Small band.png",))
            if q.get("generator") == ["search"]:
                self.assertEqual(
                    q["gsrsearch"],
                    [
                        'haswbstatement:P180=Q1 (concert OR "live performance" OR "on stage") filetype:bitmap'
                    ],
                )
                p = page("File:Exact band live.png")
                p["pageid"] = 42
                return {"query": {"pages": [p]}}
            if q.get("action") == ["wbgetentities"]:
                return {
                    "entities": {
                        "M42": {
                            "id": "M42",
                            "type": "mediainfo",
                            "statements": {
                                "P180": [
                                    {
                                        "rank": "normal",
                                        "mainsnak": {
                                            "property": "P180",
                                            "snaktype": "value",
                                            "datavalue": {
                                                "type": "wikibase-entityid",
                                                "value": {"id": "Q1"},
                                            },
                                        },
                                    }
                                ]
                            },
                        }
                    }
                }
            if url.startswith(photo.API):
                p = page("File:Small band.png")
                p["imageinfo"][0].update(width=128, height=128, thumbwidth=128, thumbheight=128)
                return {"query": {"pages": [p]}}
            return image_bytes(), "image/png"

        async def decode(body):
            from custom_components.djconnect.session_artwork import _decoded_size

            return _decoded_size(body)

        with patch.object(photo, "_read", read):
            _, _, selected = await photo.fetch(object(), "Q1", guard=guard, decode=decode)
        self.assertTrue(selected.live_hint)
        self.assertEqual(selected.title, "File:Exact band live.png")
        self.assertEqual(len(calls), 5)

    async def test_search_match_cannot_replace_exact_mediainfo_identity_or_depicts_claim(self):
        async def guard():
            pass

        for failure in ("wrong_media_id", "wrong_depicted_qid", "deprecated", "no_statements"):
            calls = []

            async def read(hass, url, owned_guard, *, json_body):
                await owned_guard()
                calls.append(url)
                q = parse_qs(urlsplit(url).query)
                if q.get("generator") == ["search"]:
                    p = page()
                    p["pageid"] = 42
                    return {"query": {"pages": [p]}}
                value = {
                    "id": "M43" if failure == "wrong_media_id" else "M42",
                    "type": "mediainfo",
                    "statements": {
                        "P180": [
                            {
                                "rank": "deprecated" if failure == "deprecated" else "normal",
                                "mainsnak": {
                                    "property": "P180",
                                    "snaktype": "value",
                                    "datavalue": {
                                        "type": "wikibase-entityid",
                                        "value": {
                                            "id": "Q2" if failure == "wrong_depicted_qid" else "Q1"
                                        },
                                    },
                                },
                            }
                        ]
                    },
                }
                if failure == "no_statements":
                    value["statements"] = {}
                return {"entities": {"M42": value}}

            with self.subTest(failure=failure), patch.object(photo, "_read", read):
                self.assertEqual(await photo._depicted_candidates(object(), "Q1", guard), [])
                self.assertEqual(len(calls), 2)

    async def test_wrong_entity_no_rights_changed_bytes_or_withdrawal_stop_without_next_photo_retry(
        self,
    ):
        from tests import test_session_artwork as fixtures

        fixtures.SessionArtworkTests.setUpClass()
        try:
            for mutation in ("wrong_qid", "no_rights", "bad_dimensions", "withdrawn"):
                calls = []

                async def guard():
                    if mutation == "withdrawn" and len(calls) == 2:
                        raise PermissionError("withdrawn")

                async def read(hass, url, owned_guard, *, json_body):
                    await owned_guard()
                    calls.append(url)
                    if url.startswith(photo.WD):
                        return entity("Q2" if mutation == "wrong_qid" else "Q1")
                    if url.startswith(photo.API):
                        p = page()
                        if mutation == "no_rights":
                            p["imageinfo"][0]["extmetadata"].pop("LicenseShortName")
                        return {"query": {"pages": [p]}}
                    return image_bytes(), "image/png"

                async def decode(body):
                    return (1, 1) if mutation == "bad_dimensions" else (640, 360)

                with self.subTest(mutation=mutation), patch.object(photo, "_read", read):
                    with self.assertRaises((photo.PhotoUnavailable, PermissionError)):
                        await photo.fetch(object(), "Q1", guard=guard, decode=decode)
                    self.assertLessEqual(len(calls), 3)
        finally:
            fixtures.SessionArtworkTests.tearDownClass()


class ArtistPhotoOwnerTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        narration_fixtures.PublicArtistNarrationTest.setUpClass()

    @classmethod
    def tearDownClass(cls):
        narration_fixtures.PublicArtistNarrationTest.tearDownClass()

    async def asyncSetUp(self):
        self.f = narration_fixtures.PublicArtistNarrationTest()
        await self.f.asyncSetUp()
        from custom_components.djconnect import session_artwork as art
        from custom_components.djconnect.session_facts import ArtistImageIdentity
        from custom_components.djconnect.image_proxy import ManagedSessionImages

        self.art = art
        self.identity = ArtistImageIdentity(
            "spotify:artist:" + "Z" * 22,
            "Q1",
            self.f.catalog["artist"],
            "00000000-0000-0000-0000-000000000042",
        )
        self.f.fact = replace(self.f.description(), artwork_artist_identity=self.identity)
        self.f.manager._history_source_contexts[self.f.session.session_id] = dict.fromkeys(
            ("backend_id", "music_account_id", "provider_entry_id", "provider_account_id"),
            "fixture",
        )
        self.f.hass.async_create_task = asyncio.create_task
        self.f.hass.async_add_executor_job = lambda callback, body: (
            asyncio.get_running_loop().run_in_executor(None, callback, body)
        )
        self.registry = ManagedSessionImages()
        self.registry.hass = self.f.hass
        self.f.hass.loop = asyncio.get_running_loop()
        self.f.hass.data["djconnect"]["session_images"] = self.registry
        self.context = SimpleNamespace(profile_id="profile-a")
        self.urls = []
        self.spotify = []
        self.withdraw_after_metadata = False
        self.authorized = True

    async def asyncTearDown(self):
        self.registry.close()
        await self.f.asyncTearDown()

    async def network(self, hass, url, guard, *, json_body):
        await guard()
        self.urls.append(url)
        if url.startswith(photo.WD):
            return entity()
        if url.startswith(photo.API):
            if self.withdraw_after_metadata:
                self.authorized = False
            return {"query": {"pages": [page()]}}
        return image_bytes(), "image/png"

    async def no_spotify_image(self, hass, backend, uri, **kwargs):
        await kwargs["guard"]()
        self.spotify.append(uri)
        raise ValueError("missing_image")

    def patches(self):
        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(
            patch.object(self.art, "artist_authority", return_value=lambda: self.authorized)
        )
        stack.enter_context(patch.object(self.art, "_fetch", self.no_spotify_image))
        stack.enter_context(patch.object(photo, "_read", self.network))
        stack.enter_context(
            patch(
                "custom_components.djconnect.spotify_backend.SpotifyBackend", return_value=object()
            )
        )
        return stack

    async def prepare(self, target, version=2):
        return await self.art.prepare(
            self.f.hass,
            self.f.runtime,
            self.context,
            session_id=self.f.session.session_id,
            target=target,
            contract_version=version,
        )

    async def test_real_owner_publication_active_image_history_refresh_and_version1_separation(
        self,
    ):
        moment = await self.f.publish()
        self.assertIsNotNone(moment, self.f.debug)
        target = {"moment_id": moment.moment_id}
        with self.patches():
            legacy = await self.prepare(target, 1)
            self.assertEqual(legacy["schema_version"], 1)
            self.assertEqual(legacy["artwork"]["state"], "missing")
            self.assertEqual(self.urls, [])
            ready = await self.prepare(target)
            art = ready["artwork"]
            self.assertEqual(ready["schema_version"], 2)
            self.assertEqual(art["state"], "ready", ready)
            self.assertEqual(art["subject"]["uri"], self.identity.spotify_uri)
            self.assertEqual(art["subject"]["wikidata_id"], "Q1")
            self.assertEqual(art["attribution"]["author"], "Fixture Photographer")
            self.assertEqual(art["attribution"]["license"], "CC-BY-SA-4.0")
            self.assertEqual(art["attribution"]["mark"], "wikimedia_commons")
            self.assertEqual(art["usage_basis"], "licensed_artist_image_owner_display")
            self.assertTrue(all(art["alt_text"][lang] for lang in ("en", "nl", "de", "fr", "es")))
            self.assertEqual((art["width"], art["height"]), (640, 360))
            self.assertFalse(art["upscale_allowed"])
            self.assertEqual(self.f.session.presence_ledger.total_published, 1)
            self.assertEqual(len(self.urls), 3)
            projected = self.art.delivery_projection(
                self.f.hass, "profile-a", self.f.session.session_id, target, ready
            )
            self.assertEqual(projected["artwork"]["url"], art["url"])
            self.assertEqual(await self.prepare(target), ready)
            self.assertEqual(len(self.urls), 3)
            self.assertEqual(
                await self.art.image(
                    self.f.hass,
                    self.context,
                    self.f.session.session_id,
                    art["url"].rsplit("/", 1)[-1],
                    runtime=self.f.runtime,
                ),
                (image_bytes(), "image/png"),
            )
            current = self.f.session.broadcast.as_dict()["session_media"]
            self.assertFalse(any(r["schema_version"] == 2 for r in current))
            self.assertTrue(any(r["schema_version"] == 1 for r in current))
            self.assertNotIn("https://upload.wikimedia.org", json.dumps(current))
            await self.f.manager.async_end(
                owner_profile_id="profile-a", session_id=self.f.session.session_id
            )
            await self.f.fixture.service.async_close()
            await self.f.fixture.service.async_initialize()
            from custom_components.djconnect.session_conversation import query_service

            query = query_service(self.f.hass, self.f.history)
            opened = await query.async_timeline_page("profile-a", self.f.session.session_id)
            entry = next(e for e in opened["entries"] if e.get("moment_id") == moment.moment_id)
            self.assertEqual(entry["text"], moment.content)
            self.assertTrue(entry["session_speech"]["manual_allowed"])
            retained = await self.prepare({"entry_id": entry["entry_id"]})
            self.assertEqual(retained["schema_version"], 2)
            self.assertEqual(retained["artwork"]["attribution"], art["attribution"])
            self.assertTrue(retained["artwork"]["historical_display_allowed"])
            self.assertFalse(retained["artwork"]["active_flow_display_allowed"])
            self.assertNotEqual(retained["artwork"]["url"], art["url"])
            self.assertEqual(len(self.urls), 6)
            self.assertEqual(len(self.f.calls), 2)  # No rewriting during image refresh/read/replay.
            page_after = await query.async_timeline_page("profile-a", self.f.session.session_id)
            self.assertEqual(len(self.urls), 6)
            self.assertEqual(
                next(e for e in page_after["entries"] if e.get("moment_id") == moment.moment_id)[
                    "text"
                ],
                moment.content,
            )
            raw = await query._repository.async_entry_record(
                "profile-a", self.f.session.session_id, entry["entry_id"]
            )
            self.assertNotIn("https://upload.wikimedia.org", raw["body"])
            self.assertNotIn("license_url", raw["body"])
            self.contract_samples = {"active": ready, "history": retained, "legacy_missing": legacy}

    async def test_paired_old_artist_card_keeps_original_identity_while_another_session_plays(self):
        from custom_components.djconnect.session_conversation import query_service

        moment=await self.f.publish()
        self.assertIsNotNone(moment,self.f.debug)
        old_session=self.f.session.session_id
        old_source=dict(self.f.manager._history_source_contexts[old_session])
        await self.f.manager.async_end(owner_profile_id='profile-a',session_id=old_session)
        await self.f.fixture.service.async_close()
        await self.f.fixture.service.async_initialize()
        query=query_service(self.f.hass,self.f.history)
        page_before=await query.async_timeline_page('profile-a',old_session)
        entry=next(e for e in page_before['entries'] if e.get('moment_id')==moment.moment_id)
        raw_before=await query._repository.async_entry_record('profile-a',old_session,entry['entry_id'])
        async def durable_session():
            # Summary read projections carry a fresh as_of timestamp. Compare
            # the actual stored lifecycle and counters, not that read clock.
            return await query._repository._async_in_transaction(lambda tx:(
                tx.fetchone('SELECT * FROM djconnect_persistent_sessions WHERE session_id=?',(old_session,)),
                tx.fetchone('SELECT * FROM djconnect_session_summaries WHERE session_id=?',(old_session,))))
        session_before=await durable_session()

        current=await self.f.manager.async_start(owner_profile_id='profile-a',locale='en',
            selected_mood='party',music_backend='spotify_direct',
            history_source_context=dict.fromkeys(old_source,'different-current-source'))
        await self.f.manager.async_update_playback_projection(owner_profile_id='profile-a',
            session_id=current.session_id,state='playing',media_identity='spotify:track:'+'Y'*22,
            title='Different current track',artist='Different current band')
        playback_before=current.broadcast.state.playback.as_dict()
        publications_before=current.presence_ledger.total_published
        authorities=[]
        def original_authority(*args,**kwargs):
            authorities.append(kwargs['expected_source'])
            return lambda:self.authorized
        request={**self.f.identity,'contract_version':2,'session_id':old_session,
                 'targets':[{'entry_id':entry['entry_id']}]}
        with self.patches(),patch.object(self.art,'artist_authority',original_authority):
            response,status=await self.art.handle_prepare(self.f.hass,request,headers=self.f.headers)
            self.assertEqual(status,200,response)
            artwork=response['session_media'][0]['artwork']
            self.assertEqual(artwork['state'],'ready',response)
            self.assertEqual(artwork['subject']['uri'],self.identity.spotify_uri)
            self.assertEqual(artwork['subject']['wikidata_id'],self.identity.wikidata_id)
            self.assertTrue(artwork['historical_display_allowed'])
            self.assertFalse(artwork['current_display_allowed'])
            self.assertFalse(artwork['active_flow_display_allowed'])
            pixels=await self.art.image(self.f.hass,self.context,old_session,
                artwork['url'].rsplit('/',1)[-1],runtime=self.f.runtime)
            self.assertEqual(pixels,(image_bytes(),'image/png'))
        self.assertTrue(authorities)
        self.assertTrue(all(source==old_source for source in authorities))
        self.assertEqual(self.spotify,[self.identity.spotify_uri])
        self.assertEqual(len(self.urls),3)
        self.assertEqual(len(self.f.calls),2)  # Only original fixture narration, no replay rewrite.
        self.assertEqual(current.broadcast.state.playback.as_dict(),playback_before)
        self.assertEqual(current.presence_ledger.total_published,publications_before)
        self.assertEqual(await durable_session(),session_before)
        self.assertEqual(await query._repository.async_entry_record('profile-a',old_session,entry['entry_id']),raw_before)

    async def test_concurrent_version2_preparations_coalesce_without_touching_version1_resource(
        self,
    ):
        moment = await self.f.publish()
        target = {"moment_id": moment.moment_id}
        with self.patches():
            one, two = await asyncio.gather(self.prepare(target), self.prepare(target))
        self.assertEqual(one["artwork"]["state"], "ready", one)
        self.assertEqual(one, two)
        self.assertEqual(len(self.urls), 3)
        self.assertNotEqual(
            self.art.target_key("profile-a", self.f.session.session_id, target, 1),
            self.art.target_key("profile-a", self.f.session.session_id, target, 2),
        )

    async def test_source_withdrawal_during_commons_metadata_never_publishes_pixels_or_new_moment(
        self,
    ):
        moment = await self.f.publish()
        self.withdraw_after_metadata = True
        with self.patches():
            result = await self.prepare({"moment_id": moment.moment_id})
        self.assertEqual(result["artwork"]["state"], "withdrawn", result)
        self.assertNotIn("url", result["artwork"])
        self.assertEqual(len(self.urls), 2)
        self.assertFalse(self.registry.assets)
        self.assertEqual(self.f.session.presence_ledger.total_published, 1)

    async def test_spotify_v2_keeps_its_own_attribution_without_commons_lookup(self):
        moment = await self.f.publish()

        async def spotify(hass, backend, uri, *, guard, expected_album_uri):
            await guard()
            return (
                image_bytes(),
                "image/png",
                "https://open.spotify.com/artist/" + "Z" * 22,
                "",
                640,
                360,
                self.identity.name,
            )

        with self.patches(), patch.object(self.art, "_fetch", spotify):
            result = await self.prepare({"moment_id": moment.moment_id})
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["artwork"]["state"], "ready", result)
        self.assertEqual(result["artwork"]["attribution"]["provider"], "Spotify")
        self.assertEqual(result["artwork"]["usage_basis"], "spotify_temporary_owner_display")
        self.assertEqual(self.urls, [])
        self.contract_samples = {"spotify_v2": result}

    async def test_only_missing_spotify_image_can_fall_back_not_identity_or_authority_errors(self):
        moment = await self.f.publish()
        for reason in ("subject_mismatch", "source_unavailable"):

            async def invalid(*args, **kwargs):
                await kwargs["guard"]()
                raise ValueError(reason)

            with (
                self.subTest(reason=reason),
                self.patches(),
                patch.object(self.art, "_fetch", invalid),
            ):
                self.registry.negative.clear()
                result = await self.prepare({"moment_id": moment.moment_id})
            self.assertNotEqual(result["artwork"]["state"], "ready")
            self.assertEqual(self.urls, [])
        self.assertEqual(self.f.session.presence_ledger.total_published, 1)

    async def test_explicit_version2_handler_uses_paired_context_and_rejects_unknown_versions(self):
        moment = await self.f.publish()
        request = {
            **self.f.identity,
            "contract_version": 2,
            "session_id": self.f.session.session_id,
            "targets": [{"moment_id": moment.moment_id}],
        }
        with self.patches():
            result, status = await self.art.handle_prepare(
                self.f.hass, request, headers=self.f.headers
            )
        self.assertEqual(status, 200, result)
        self.assertEqual(result["contract_version"], 2)
        self.assertEqual(result["session_media"][0]["schema_version"], 2)
        self.assertEqual(result["session_media"][0]["artwork"]["state"], "ready", result)
        for version in (True, 3, "2"):
            result, status = await self.art.handle_prepare(
                self.f.hass, {**request, "contract_version": version}, headers=self.f.headers
            )
            self.assertEqual(status, 400, result)
        _, status = await self.art.handle_prepare(
            self.f.hass, request, headers={"Authorization": "Bearer wrong"}
        )
        self.assertIn(status, (401, 403))

    def test_credit_story_v2_uses_primary_band_context_never_current_album_as_photo(self):
        from custom_components.djconnect.session_facts import recording_facts

        fact = recording_facts(
            self.f.catalog,
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "relations": [
                    {
                        "type": "instrument",
                        "target-type": "artist",
                        "artist": {"name": "Guest musician"},
                    }
                ],
            },
        )[0]
        self.assertEqual(self.art.subject_for_fact(fact), self.f.catalog["uri"])
        self.assertIsNone(self.art.subject_for_fact(fact, contract_version=2))
        bound = replace(fact, artwork_artist_identity=self.identity)
        self.assertEqual(
            self.art.subject_for_fact(bound, contract_version=2), self.identity.spotify_uri
        )
        self.assertEqual(self.art.subject_for_fact(bound), self.f.catalog["uri"])
