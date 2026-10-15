"""Fail-closed source qualification for the selected credit-context contract."""

from __future__ import annotations

import importlib
import json
import types
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from tests.test_config_flow_helpers import install_homeassistant_stubs
from tests.test_spotify_backend import install_backend_stubs


_ALBUM_ID = "0123456789ABCDEFGHIJKL"
_NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


class CreditProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_homeassistant_stubs()
        install_backend_stubs()
        cls.credits = importlib.import_module("custom_components.djconnect.credit_provenance")
        cls.spotify = importlib.import_module("custom_components.djconnect.spotify_backend")
        cls.insight = importlib.import_module("custom_components.djconnect.track_insight")

    def _evidence(self, **changes):
        evidence = self.credits.CreditEvidence(
            field_id="spotify_album_release_date",
            source_provider="spotify_web_api",
            evidence_handle=f"spotify:album:{_ALBUM_ID}",
            value="1998-04-20",
            confidence=1.0,
            observed_at=_NOW,
            rights_reference="https://developer.spotify.com/policy",
            attribution_url=f"https://open.spotify.com/album/{_ALBUM_ID}",
            attribution_mark_visible=True,
            retention_class="runtime_only",
        )
        return replace(evidence, **changes)

    def _test_contract(self):
        return replace(
            self.credits.CREDIT_SOURCE_FIELDS["spotify_album_release_date"],
            session_ready=True,
            renderer_safe=True,
            public_safe=True,
            usage_rights_qualified=True,
        )

    def test_inventory_is_machine_readable_and_contains_only_real_source_fields(self) -> None:
        inventory = self.credits.credit_source_inventory()
        json.dumps(inventory)
        self.assertEqual(
            {item["field_id"] for item in inventory},
            {
                "spotify_playback_track_artists",
                "spotify_album_artists",
                "spotify_album_release_date",
            },
        )
        self.assertEqual(
            {item["category"] for item in inventory},
            {"track_performer", "album_artist", "album_release_date"},
        )
        self.assertTrue(all(item["source_provider"] == "spotify_web_api" for item in inventory))
        self.assertTrue(all(item["attribution_requirement"] == "spotify_link_and_mark" for item in inventory))
        self.assertTrue(all(not item["session_ready"] and not item["renderer_safe"] for item in inventory))
        self.assertTrue(all(not item["public_safe"] for item in inventory))
        self.assertTrue(all(not item["usage_rights_qualified"] for item in inventory))
        self.assertNotIn("producer", {item["category"] for item in inventory})
        self.assertNotIn("songwriter", {item["category"] for item in inventory})

    def test_current_sources_cannot_authorize_an_artist_or_album_moment(self) -> None:
        candidates = (
            self._evidence(),
            self._evidence(
                field_id="spotify_album_artists", value="Example Artist"
            ),
            self._evidence(
                field_id="spotify_playback_track_artists",
                evidence_handle=f"spotify:track:{_ALBUM_ID}",
                attribution_url=f"https://open.spotify.com/track/{_ALBUM_ID}",
                value="Example Artist",
            ),
        )
        for evidence in candidates:
            with self.subTest(field_id=evidence.field_id):
                decision = self.credits.qualify_current_moment_credit(
                    (evidence,), field_id=evidence.field_id, now=_NOW
                )
                self.assertFalse(decision.eligible)
                self.assertEqual(decision.reason, "producer_or_attribution_gate")
        self.assertFalse(
            self.credits.qualify_current_moment_credit(
                (self._evidence(field_id="producer"),), field_id="producer", now=_NOW
            ).eligible
        )

    def test_missing_unreliable_stale_or_unattributable_evidence_yields_no_fact(self) -> None:
        qualify = self.credits.qualify_credit_evidence
        policy = self._test_contract()
        self.assertEqual(qualify((), contract=policy, now=_NOW).reason, "no_source")
        invalid = (
            self._evidence(evidence_handle=""),
            self._evidence(evidence_handle=None),
            self._evidence(source_provider="generic_llm"),
            self._evidence(confidence=0.4),
            self._evidence(observed_at=_NOW - timedelta(days=2)),
            self._evidence(observed_at=_NOW + timedelta(minutes=1)),
            self._evidence(rights_reference=""),
            self._evidence(attribution_url=""),
            self._evidence(attribution_mark_visible=False),
            self._evidence(retention_class="persistent"),
            self._evidence(value="Unrelated producer fact"),
            self._evidence(value="  "),
            self._evidence(value=None),
        )
        for evidence in invalid:
            with self.subTest(evidence=evidence):
                self.assertFalse(qualify((evidence,), contract=policy, now=_NOW).eligible)
        self.assertTrue(qualify((self._evidence(),), contract=policy, now=_NOW).eligible)
        self.assertEqual(
            qualify(
                (self._evidence(),),
                contract=replace(policy, usage_rights_qualified=False),
                now=_NOW,
            ).reason,
            "rights_not_qualified",
        )

    def test_conflicting_provider_claims_are_suppressed_without_guessing(self) -> None:
        decision = self.credits.qualify_credit_evidence(
            (self._evidence(), self._evidence(value="1999-04-20")),
            contract=self._test_contract(),
            now=_NOW,
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.reason, "conflict")
        different_item = self._evidence(
            evidence_handle="spotify:album:ZYXWVUTSRQPONMLKJIHGFE",
            attribution_url="https://open.spotify.com/album/ZYXWVUTSRQPONMLKJIHGFE",
        )
        decision = self.credits.qualify_credit_evidence(
            (self._evidence(), different_item), contract=self._test_contract(), now=_NOW
        )
        self.assertEqual(decision.reason, "conflict")

    def test_decision_audit_never_serializes_value_or_provider_identity(self) -> None:
        decision = self.credits.qualify_credit_evidence(
            (self._evidence(),), contract=self._test_contract(), now=_NOW
        )
        serialized = json.dumps(decision.as_dict())
        self.assertNotIn(_ALBUM_ID, serialized)
        self.assertNotIn("1998", serialized)
        self.assertNotIn("spotify:album:", serialized)

    def test_catalog_date_extension_does_not_make_legacy_credits_qualified(self) -> None:
        playback = self.spotify._normalize_playback(
            {
                "is_playing": True,
                "item": {
                    "name": "Example Track",
                    "uri": f"spotify:track:{_ALBUM_ID}",
                    "artists": [{"name": "Example Artist", "id": _ALBUM_ID}],
                    "album": {
                        "name": "Example Album",
                        "uri": f"spotify:album:{_ALBUM_ID}",
                        "release_date": "1998-04-20",
                        "label": "Example Label",
                    },
                },
            }
        )
        self.assertEqual(playback["artist_ids"], [_ALBUM_ID])
        self.assertEqual(playback["release_date"], "1998-04-20")
        self.assertEqual(playback["album_uri"], f"spotify:album:{_ALBUM_ID}")
        self.assertEqual(playback["release_date_precision"], "")
        from custom_components.djconnect.session_facts import catalog_facts
        self.assertEqual(catalog_facts(playback), [])  # Missing precision remains ineligible.
        self.assertNotIn("label", playback)
        track = self.insight._track_contract(
            playback,
            types.SimpleNamespace(config={"music_backend": "spotify_direct"}),
            self.insight.TrackInsightRequest(),
        )
        for field in ("producer", "composer", "artist_ids", "uri", "release_date", "label"):
            self.assertNotIn(field, track)
        analysis = self.insight._normalize_analysis(
            {"producer": "Unverified Name", "production_notes": ["wide mix"]}, track, "en"
        )
        self.assertNotIn("producer", analysis)
        self.assertIn("production_notes", analysis)
        album = self.spotify._normalize_album_item(
            {"name": "Example Album", "uri": f"spotify:album:{_ALBUM_ID}", "release_date": "1998"}
        )
        self.assertEqual(album["release_date"], "1998")
        self.assertNotIn("label", album)


if __name__ == "__main__":
    unittest.main()
