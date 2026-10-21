"""Shared allowlist qualification over actual unit Runtime/Moment publications."""
from dataclasses import replace
import importlib
import json
import secrets
import unittest
from unittest.mock import patch

from tests import test_expressive_dj_persona as source_tests


class DisplayProjectionTests(unittest.TestCase):
    setUpClass = source_tests.ExpressiveDJPersonaTest.__dict__["setUpClass"]
    tearDownClass = source_tests.ExpressiveDJPersonaTest.__dict__["tearDownClass"]
    source_pair = source_tests.ExpressiveDJPersonaTest.source_pair
    run_sequence = source_tests.ExpressiveDJPersonaTest.run_sequence

    def prepared(self):
        self.moments = self.run_sequence(self.runtime.DJPersona.RADIO_DJ, count=1)
        module = importlib.import_module("custom_components.djconnect.display_admission")
        self.projection = importlib.import_module("custom_components.djconnect.display_projection")
        self.state = module.DisplayAdmissionState(lambda: 101)
        self.owner_live = True
        self.owner = module.DisplayOwnerBinding("owner", self.session.session_id, "entry", "stamp", lambda: self.owner_live)
        nonce = secrets.token_urlsafe(32)
        claim = self.state.create_claim(source="unit", browser_nonce=nonce)
        self.state.approve(owner=self.owner, **{key: claim[key] for key in (
            "issuer_epoch", "claim_id", "browser_generation", "code")}, share={"mode": "create", "consent": True})
        collected = self.state.collect(**{key: claim[key] for key in (
            "issuer_epoch", "claim_id", "browser_generation", "claim_secret")}, browser_nonce=nonce)
        self.display = self.state._displays[collected["display_id"]]
        return self.moments[0]

    def snapshot(self, now=101):
        return self.projection.shared_snapshot(self.session, self.display, self.state, now=now)

    def test_public_reference_citation_exports_required_attribution_without_corpus_or_owner(self):
        self.prepared()
        base={'provider':'Public web','title':'Artist account','url':'https://artist.example/',
            'language':'en','license':'public_page_short_reference','revision_url':'',
            'usage_basis':'public_page_short_reference','attributed_author':'Nora Vale',
            'author_status':'publication_byline_not_independent_identity',
            'work_reference':{'title':'Paper Lanterns','artist':'Nora Vale',
                'url':'https://musicbrainz.org/release-group/'+'a'*36,'private':'forbidden'},
            'untrusted_excerpt':'never export the source body','owner_id':'private-owner'}
        result=self.projection.public_citation(base)
        self.assertEqual(result['attributed_author'],'Nora Vale')
        self.assertEqual(set(result['work_reference']),{'title','artist','url'})
        self.assertNotIn('untrusted_excerpt',result)
        self.assertNotIn('owner_id',result)

    def test_pending_content_erasure_withdraws_cached_guard_and_shared_text(self):
        moment = self.prepared()
        snapshot = self.snapshot()
        self.assertTrue(snapshot['dj_moments'])
        guard = self.projection.projection_release_guard(self.session, self.display, self.state, snapshot)
        self.session.broadcast.content_epoch += 1
        self.session.broadcast.content_pending = True
        self.session.broadcast.content_pending_moment_ids.add(moment.moment_id)
        self.assertFalse(guard())
        self.assertEqual(self.snapshot()['dj_moments'], [])

    def test_published_shared_fact_text_and_attribution_unchanged_no_private_fields(self):
        moment = self.prepared()
        before = moment.as_dict()
        snapshot = self.snapshot()
        self.assertEqual(len(snapshot["dj_moments"]), 1)
        card = snapshot["dj_moments"][0]
        self.assertEqual(card["content"], moment.content)
        self.assertEqual(card["source_attribution"], dict(moment.source_attribution))
        self.assertEqual(card["presentation_intent"]["dj_persona"], "radio_dj")
        self.assertEqual(before, moment.as_dict())
        wire = json.dumps(snapshot)
        for field in ("planner", "session_flow", "session_direction", "native_delivery", "source_fact",
                      "generation_metadata", "actions", "voice_style", "up_next", "target_name", "artwork_url",
                      "profile_id", "account_id", "device_id", "session_forecast"):
            self.assertNotIn('"' + field + '"', wire)

    def test_owner_visibility_or_owner_channel_never_becomes_shared_from_valid_source(self):
        moment = self.prepared()
        broadcast = self.session.broadcast
        for presentation in (replace(moment.presentation_intent, visibility=self.runtime.DJMomentVisibility.OWNER_ONLY),
                             replace(moment.presentation_intent, delivery_channels=(self.runtime.DeliveryChannel.OWNER,))):
            broadcast.state = replace(broadcast.state, dj_moments=(replace(moment, presentation_intent=presentation),))
            self.assertEqual(self.snapshot()["dj_moments"], [])

    def test_shared_label_without_field_proof_attribution_or_flow_is_insufficient(self):
        moment = self.prepared()
        broadcast = self.session.broadcast
        for malformed in (replace(moment, source_fact=None), replace(moment, source_attribution=()),
                          replace(moment, source_fact=replace(moment.source_fact, license="unknown"))):
            broadcast.state = replace(broadcast.state, dj_moments=(malformed,))
            self.assertEqual(self.snapshot()["dj_moments"], [])
        broadcast.state = replace(broadcast.state, dj_moments=(moment,),
            session_flow=replace(broadcast.state.session_flow, items=()))
        self.assertEqual(self.snapshot()["dj_moments"], [])

    def test_original_deadlines_expiry_pause_invalidation_and_revision(self):
        self.prepared()
        first, repeated = self.snapshot(), self.snapshot(now=102)
        self.assertEqual(first["projection_revision"], repeated["projection_revision"])
        self.assertEqual(first["dj_moments"][0]["display_expires_at"], repeated["dj_moments"][0]["display_expires_at"])
        self.assertEqual(self.snapshot(now=1901)["dj_moments"], [])
        self.session.broadcast.invalidate_current_delivery()
        after = self.snapshot()
        self.assertEqual(after["dj_moments"], [])
        self.assertNotEqual(first["projection_revision"], after["projection_revision"])

    def test_withdrawal_and_oversized_full_fact_fail_closed_without_truncation(self):
        moment = self.prepared()
        self.session.broadcast.state = replace(self.session.broadcast.state,
            dj_moments=(replace(moment, content="x" * (129 * 1024)),))
        with self.assertRaises(self.projection.DisplayAdmissionError) as failure:
            self.snapshot()
        self.assertEqual(failure.exception.code, "display_capacity")
        self.owner_live = False
        with self.assertRaises(self.projection.DisplayAdmissionError):
            self.snapshot()

    def test_final_content_release_uses_original_source_clock_after_serialization(self):
        moment = self.prepared()
        moment = replace(moment, source_fact=replace(moment.source_fact, source_expires_at=101.5))
        self.session.broadcast.state = replace(self.session.broadcast.state, dj_moments=(moment,))
        snapshot = self.snapshot(now=101)
        self.assertEqual(len(snapshot["dj_moments"]), 1)
        guard = self.projection.projection_release_guard(self.session, self.display, self.state, snapshot)
        with patch("time.monotonic", return_value=101):
            self.assertTrue(guard())
        # Causal gap: same serialized frame, unchanged owner/share/lease and
        # generation; ONLY the original source clock reaches equality.
        with patch("time.monotonic", return_value=101.5):
            self.assertFalse(guard())
