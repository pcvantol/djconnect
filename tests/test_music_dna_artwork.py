"""Music DNA display grants use existing owner proof, never labels or raw refs."""
from __future__ import annotations

from copy import deepcopy
import json
import time
import types
import unittest
from unittest.mock import AsyncMock, patch

from tests import test_discovery_artwork as fixtures
from tests.test_discovery_artwork import ALBUM_URI, ARTIST_URI, TRACK_URI, profile
from tests.test_http_voice_helpers import install_http_stubs

install_http_stubs()
from custom_components.djconnect import api_handlers as api  # noqa: E402


class MusicDNAArtworkTest(unittest.IsolatedAsyncioTestCase):
    # The shared fixture establishes opt-in and original normalized owner proof.
    async def asyncSetUp(self):
        await fixtures.ArtworkLifecycleTest.asyncSetUp(self)
        await self.manager.async_update_listening_profile(self.runtime, profile(), self.payload)
        self.record = self.manager.data["memories"]["profile:one"]
        self.record["recommendation_plays"] = [{"uri": ALBUM_URI, "title": "Fixture album"}]
        self.record["artist_play_counts"] = {"Artist": 3}

    async def response(self):
        provider = AsyncMock(side_effect=AssertionError("Unexpected extra provider request"))
        with (
            patch.object(api, "_music_dna_runtime_payload", return_value=(self.runtime, self.payload, None)),
            patch.object(api, "_apply_profile_or_error", AsyncMock(return_value=(None, None))),
            patch.object(api, "run_music_command", provider),
        ):
            result, status = await api.async_handle_music_dna_profile_payload(self.hass, self.payload)
        self.assertEqual(status, 200)
        provider.assert_not_awaited()
        return result

    @staticmethod
    def media_items(result):
        p = result["profile"]
        return [
            p["top_tracks_by_range"]["short_term"][0],
            p["recommendation_signals"][0],
            p["top_artists_by_range"]["short_term"][0],
        ]

    async def test_profile_projects_track_exact_album_and_artist_without_raw_refs(self):
        result = await self.response()
        for item, uri in zip(self.media_items(result), (TRACK_URI, ALBUM_URI, ARTIST_URI)):
            with self.subTest(uri=uri):
                self.assertTrue(item.get("image_url", "").startswith("/api/djconnect/v1/image_proxy/disc-"))
                self.assertEqual(item["image_subject_uri"], uri)
                self.assertLessEqual(item["image_expires_at"], item["image_reference_expires_at"])
                self.assertLessEqual(item["image_expires_at"], time.time() + 900)
                self.assertLess(item["image_captured_at"], item["image_reference_expires_at"])
                self.assertEqual(item["image_attribution"]["provider"], "spotify")
        self.assertNotIn("asset_id", json.dumps(result))
        self.assertNotIn("artwork", json.dumps(result))
        self.assertNotIn("disc-", json.dumps(self.store.data))

    async def test_plain_profile_has_no_private_refs_or_display_grants(self):
        result = await self.manager.async_profile(self.runtime, self.payload)
        for forbidden in ("asset_id", "artwork", "disc-"):
            self.assertNotIn(forbidden, json.dumps(result))
        self.assertTrue(self.record["listening_profile"]["top_artists_by_range"]["short_term"][0]["artwork"])

    async def test_original_reference_clock_survives_repeated_profile_reads(self):
        before = deepcopy(self.record["listening_profile"])
        first = self.media_items(await self.response())[0]
        second = self.media_items(await self.response())[0]
        self.assertEqual(first["image_captured_at"], second["image_captured_at"])
        self.assertEqual(first["image_reference_expires_at"], second["image_reference_expires_at"])
        self.assertEqual(before, self.record["listening_profile"])
        grants = self.hass.data["djconnect"]["discovery_image_grants"]
        self.assertTrue(grants)
        await self.manager.async_clear("profile:one")
        self.assertTrue(all(not grant["guard"].valid() for grant in grants.values()))

    async def test_same_name_aggregates_and_snapshots_do_not_gain_current_images(self):
        result = await self.response()
        for row in result["profile"]["favorite_artists"]:
            self.assertNotIn("image_url", row)
            self.assertNotIn("uri", row)
        self.assertNotIn("image_url", json.dumps(result["profile"].get("snapshot_history", [])))

    async def test_wrong_original_owner_does_not_gain_display_grant(self):
        self.runtime.profile_context_music_account_id = "different-account"
        result = await self.response()
        self.assertNotIn("image_url", json.dumps(result))
        self.assertNotIn("asset_id", json.dumps(result))

    async def test_expired_original_reference_does_not_gain_fresh_lease(self):
        listening = self.record["listening_profile"]
        for key in ("top_tracks_by_range", "top_artists_by_range"):
            for rows in listening[key].values():
                for item in rows:
                    item["artwork"]["expires_at"] = time.time() - 1
        result = await self.response()
        self.assertNotIn("image_url", json.dumps(result))
        self.assertNotIn("asset_id", json.dumps(result))

    async def test_export_and_import_strip_delivery_and_reference_fields(self):
        response = await self.response()
        exported = await self.manager.async_export_profile(self.runtime, self.payload)
        for value in (exported, fixtures.art.strip_artwork(response)):
            for forbidden in ("image_url", "image_subject_uri", "image_captured_at", "image_reference_expires_at", "asset_id", "disc-"):
                self.assertNotIn(forbidden, json.dumps(value))
        self.assertEqual(fixtures.art.strip_artwork({"imageSubjectURI": TRACK_URI, "imageCapturedAt": 12, "imageReferenceExpiresAt": 20}), {})

    async def test_only_current_response_and_original_guard_can_issue_images(self):
        guard = await fixtures.art.capture_refresh_guard(self.runtime, self.payload)
        response = await self.manager.async_profile(self.runtime, self.payload)
        for invalid in (None,):
            result = fixtures.art.project_music_dna_images(self.hass, self.runtime, response, invalid)
            self.assertNotIn("image_url", json.dumps(result))
        wrong = {**response, "music_dna_key": "profile:other"}
        self.assertNotIn("image_url", json.dumps(fixtures.art.project_music_dna_images(self.hass, self.runtime, wrong, guard)))
        await self.manager.async_clear("profile:one")
        await self.manager.async_set_enabled(self.runtime, True, self.payload)
        result = fixtures.art.project_music_dna_images(self.hass, self.runtime, response, guard)
        self.assertNotIn("image_url", json.dumps(result))
        self.assertNotIn("discovery_image_grants", self.hass.data["djconnect"])

    async def test_wrong_item_identity_and_edition_ignore_incoming_urls(self):
        guard = await fixtures.art.capture_refresh_guard(self.runtime, self.payload)
        response = {"enabled": True, "music_dna_key": guard.key, "profile": {"recent_tracks": [
            {"uri": TRACK_URI, "id": "D" * 22, "image_url": "https://fixture.invalid/forged"},
            {"uri": TRACK_URI, "album_uri": "spotify:album:" + "E" * 22},
            {"uri": "spotify:artist:" + "F" * 22, "name": "Artist"},
        ]}}
        result = fixtures.art.project_music_dna_images(self.hass, self.runtime, response, guard)
        self.assertNotIn("image_url", json.dumps(result))
        self.assertIn("forged", json.dumps(response))
        self.assertNotIn("forged", json.dumps(result))

    async def test_duplicate_subjects_share_lease_without_enriching_history_or_blocks(self):
        guard = await fixtures.art.capture_refresh_guard(self.runtime, self.payload)
        row = {"uri": TRACK_URI}
        response = {"enabled": True, "music_dna_key": guard.key, "profile": {
            "recent_tracks": [row, deepcopy(row)], "recent_favorite_tracks": [deepcopy(row)],
            "snapshot_history": [deepcopy(row)], "blocked_items": [deepcopy(row)],
        }}
        result = fixtures.art.project_music_dna_images(self.hass, self.runtime, response, guard)
        p = result["profile"]
        self.assertEqual(p["recent_tracks"][0]["image_url"], p["recent_tracks"][1]["image_url"])
        self.assertEqual(p["recent_tracks"][0]["image_url"], p["recent_favorite_tracks"][0]["image_url"])
        self.assertEqual(len(self.hass.data["djconnect"]["discovery_image_grants"]), 1)
        self.assertNotIn("image_url", json.dumps(p["snapshot_history"]))
        self.assertNotIn("image_url", json.dumps(p["blocked_items"]))

    async def test_duplicate_uri_never_overrides_each_rows_original_album(self):
        guard = await fixtures.art.capture_refresh_guard(self.runtime, self.payload)
        good = {"uri": TRACK_URI, "album_uri": ALBUM_URI}
        wrong = {"uri": TRACK_URI, "album_uri": "spotify:album:" + "E" * 22}
        for first, second in ((good, wrong), (wrong, good)):
            with self.subTest(first_album=first["album_uri"]):
                response = {"enabled": True, "music_dna_key": guard.key, "profile": {
                    "recent_tracks": [deepcopy(first)], "recent_favorite_tracks": [deepcopy(second)],
                }}
                result = fixtures.art.project_music_dna_images(self.hass, self.runtime, response, guard)
                rows = result["profile"]["recent_tracks"] + result["profile"]["recent_favorite_tracks"]
                for row in rows:
                    self.assertEqual("image_url" in row, row["album_uri"] == ALBUM_URI)

    async def test_original_clock_can_end_before_lease_ceiling(self):
        guard = await fixtures.art.capture_refresh_guard(self.runtime, self.payload)
        item = self.record["listening_profile"]["top_tracks_by_range"]["short_term"][0]
        item["artwork"]["expires_at"] = time.time() + 2
        response = await self.manager.async_profile(self.runtime, self.payload)
        result = fixtures.art.project_music_dna_images(self.hass, self.runtime, response, guard)
        public = result["profile"]["top_tracks_by_range"]["short_term"][0]
        self.assertEqual(public["image_expires_at"], item["artwork"]["expires_at"])
        with patch.object(fixtures.art.time, "time", return_value=time.time() + 3):
            self.assertNotIn("image_url", json.dumps(fixtures.art.project_music_dna_images(self.hass, self.runtime, response, guard)["profile"]["top_tracks_by_range"]))

    async def test_profile_withdrawal_after_projection_returns_conflict(self):
        original = api.project_music_dna_images

        def withdrawn(*args):
            result = original(*args)
            self.record["generation"] += 1
            return result

        with (
            patch.object(api, "_music_dna_runtime_payload", return_value=(self.runtime, self.payload, None)),
            patch.object(api, "_apply_profile_or_error", AsyncMock(return_value=(None, None))),
            patch.object(api, "project_music_dna_images", withdrawn),
        ):
            result, status = await api.async_handle_music_dna_profile_payload(self.hass, self.payload)
        self.assertEqual((status, result), (409, {"success": False, "error": "music_dna_context_changed"}))
        self.assertTrue(all(not grant["guard"].valid() for grant in self.hass.data["djconnect"]["discovery_image_grants"].values()))

    async def test_personal_read_withdrawal_creates_no_images(self):
        self.runtime.profile_context_privacy_policy = types.SimpleNamespace(allow_personal_read=False)
        result = await self.response()
        self.assertTrue(result["redacted"])
        self.assertEqual(result["profile"], {})
        self.assertNotIn("discovery_image_grants", self.hass.data["djconnect"])

    async def test_bounded_distinct_grants_and_scan_work(self):
        guard = await fixtures.art.capture_refresh_guard(self.runtime, self.payload)
        original = deepcopy(self.record["listening_profile"]["top_tracks_by_range"]["short_term"][0])
        rows = []
        for i in range(150):
            item = deepcopy(original)
            item["id"] = f"{i:022d}"
            item["uri"] = "spotify:track:" + item["id"]
            item["artwork"]["subject_uri"] = item["uri"]
            rows.append(item)
        self.record["listening_profile"]["top_tracks_by_range"] = {"short_term": rows}
        response = {"enabled": True, "music_dna_key": guard.key, "profile": {
            "recent_tracks": [{"uri": row["uri"]} for row in rows],
        }}
        result = fixtures.art.project_music_dna_images(self.hass, self.runtime, response, guard)
        self.assertEqual(sum("image_url" in item for item in result["profile"]["recent_tracks"]), 128)
        self.assertEqual(len(self.hass.data["djconnect"]["discovery_image_grants"]), 128)
        response["profile"]["recent_tracks"] = [{} for _ in range(1000)] + [{"uri": rows[0]["uri"]}]
        result = fixtures.art.project_music_dna_images(self.hass, self.runtime, response, guard)
        self.assertNotIn("image_url", json.dumps(result))

    async def test_legacy_accepted_discovery_reuses_only_current_exact_reference(self):
        from custom_components.djconnect import music_discovery as discovery
        from custom_components.djconnect.discovery_artwork import artwork_owner
        rows = [{"uri": TRACK_URI, "title": "Same title"}, {"uri": ALBUM_URI, "title": "Same title"}]
        self.record["recommendation_plays"] = deepcopy(rows)
        before = deepcopy(self.record)
        result = discovery._profile_from_memory(self.record, owner=artwork_owner(self.runtime))
        items = discovery._sections_from_profile(result)[0]["items"]
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertTrue(item.get("_artwork"))
            self.assertEqual(item["_artwork"]["subject_uri"], item["uri"])
            original = before["listening_profile"]["top_tracks_by_range"]["short_term"][0]["artwork"]
            self.assertEqual(item["_artwork"]["expires_at"], original["expires_at"])
            self.assertEqual(item["_artwork"]["captured_at"], original["captured_at"])
        self.assertEqual(before, self.record)

    async def test_legacy_accepted_discovery_never_joins_labels_wrong_edition_owner_or_expiry(self):
        from custom_components.djconnect import music_discovery as discovery
        from custom_components.djconnect.discovery_artwork import artwork_owner
        owner = artwork_owner(self.runtime)
        for row in [
            {"title": "Track"},
            {"uri": "spotify:track:" + "D" * 22, "title": "Track"},
            {"uri": TRACK_URI, "album_uri": "spotify:album:" + "D" * 22},
            {"uri": TRACK_URI, "id": "D" * 22},
        ]:
            self.record["recommendation_plays"] = [row]
            p = discovery._profile_from_memory(self.record, owner=owner)
            self.assertFalse(any(i.get("_artwork") for i in discovery._sections_from_profile(p)[0]["items"]))
        self.record["recommendation_plays"] = [{"uri": TRACK_URI}]
        for bad_owner in [None, {**owner, "account_id": "foreign"}]:
            p = discovery._profile_from_memory(self.record, owner=bad_owner)
            self.assertFalse(any(i.get("_artwork") for i in discovery._sections_from_profile(p)[0]["items"]))
        self.record["listening_profile"]["top_tracks_by_range"]["short_term"][0]["artwork"]["expires_at"] = time.time() - 1
        p = discovery._profile_from_memory(self.record, owner=owner)
        self.assertFalse(any(i.get("_artwork") for i in discovery._sections_from_profile(p)[0]["items"]))

    def test_actual_ha_fixture_binds_current_producer_and_original_clocks(self):
        import hashlib
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        path = root / "examples/client_contracts/music_dna_artwork_v1/profile-and-legacy-accepted.json"
        fixture = json.loads(path.read_text())
        for relative, expected in fixture["source_pins"].items():
            self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), expected)
        self.assertEqual(hashlib.sha256((root / fixture["harness"]).read_bytes()).hexdigest(), fixture["harness_sha256"])
        self.assertEqual(fixture["cases"]["unshown_recommendation_still_rejected"], "409_CHOICE_EXPIRED")
        self.assertEqual(fixture["cases"]["music_dna_actual_original_expiry"], "REAL_WALL_CLOCK_200_TO_404_THEN_OMITTED")
        self.assertEqual(fixture["cases"]["actual_browser_decode"], "NOT_RUN_ISOLATED_CONTAINER")
        self.assertNotIn("asset_id", json.dumps(fixture["music_dna_profile"]))
        album = fixture["music_dna_exact_album"]
        self.assertEqual(album["image_subject_uri"], album["uri"])
        self.assertLessEqual(album["image_expires_at"], album["image_reference_expires_at"])
        self.assertGreater(album["image_reference_expires_at"], album["image_captured_at"])
